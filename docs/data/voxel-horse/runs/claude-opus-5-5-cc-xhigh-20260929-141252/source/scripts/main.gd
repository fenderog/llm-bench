extends Node3D
## Sets up input, lighting, sky, the streamed voxel world, the horse, clouds,
## camera, HUD and sound. Everything is generated in code.

const Terrain = preload("res://scripts/terrain.gd")
const Horse = preload("res://scripts/horse.gd")
const FollowCamera = preload("res://scripts/follow_camera.gd")
const Hud = preload("res://scripts/hud.gd")
const Sfx = preload("res://scripts/sfx.gd")
const MeshData = preload("res://scripts/mesh_data.gd")

const WORLD_SEED := 20260929
const SKY_TOP := Color(0.3, 0.52, 0.88)
const SKY_HORIZON := Color(0.74, 0.85, 0.95)
const CLOUD_AREA := 320.0
const WIND := Vector3(2.0, 0.0, 0.8)

var terrain: Terrain
var horse: Horse
var camera: FollowCamera
var hud: Hud
var sfx: Sfx
var _clouds: Array[MeshInstance3D] = []


func _ready() -> void:
	_setup_input()
	_setup_environment()

	terrain = Terrain.new()
	terrain.name = "Terrain"
	add_child(terrain)
	terrain.setup(WORLD_SEED)

	horse = Horse.new()
	horse.name = "Horse"
	horse.terrain = terrain
	add_child(horse)
	var spawn := Vector3(terrain.spawn.x, 0.0, terrain.spawn.y)
	terrain.update_around(spawn, true)
	horse.place_at(spawn, 0.6)

	camera = FollowCamera.new()
	camera.target = horse
	camera.terrain = terrain
	add_child(camera)
	camera.make_current()
	camera.snap()

	_create_clouds()

	sfx = Sfx.new()
	add_child(sfx)
	horse.hoof_down.connect(sfx.play_clop)

	hud = Hud.new()
	hud.horse = horse
	add_child(hud)
	_apply_user_args()


## Optional start-up overrides: godot --path . -- --camera=1 --coat=2 --gait=3 --zoom=0.6
func _apply_user_args() -> void:
	for arg in OS.get_cmdline_user_args():
		var parts := arg.trim_prefix("--").split("=")
		if parts.size() != 2 or not parts[1].is_valid_float():
			continue
		var value := parts[1].to_int()
		match parts[0]:
			"zoom":
				camera.set_zoom(parts[1].to_float())
				camera.snap()
			"camera":
				for i in value:
					camera.cycle_mode()
				camera.snap()
			"coat":
				horse.set_coat(value)
			"gait":
				horse.gait_level = clampi(value, 0, Horse.GAIT_SPEEDS.size() - 1)


func _process(delta: float) -> void:
	terrain.update_around(horse.global_position)
	sfx.set_speed(horse.speed, delta)
	_move_clouds(delta)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("camera"):
		camera.cycle_mode()
		hud.flash("Camera: " + camera.mode_name())
	elif event.is_action_pressed("coat"):
		horse.next_coat()
		hud.flash("Coat: " + horse.coat_name())
	elif event.is_action_pressed("mute"):
		hud.flash("Sound off" if sfx.toggle_mute() else "Sound on")
	elif event.is_action_pressed("help"):
		hud.toggle_help()
	elif event.is_action_pressed("fullscreen"):
		var full := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if full else DisplayServer.WINDOW_MODE_FULLSCREEN)


func _setup_input() -> void:
	_add_action("faster", [KEY_W, KEY_UP], [JOY_BUTTON_DPAD_UP])
	_add_action("slower", [KEY_S, KEY_DOWN], [JOY_BUTTON_DPAD_DOWN])
	_add_action("turn_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT])
	_add_action("turn_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT])
	_add_action("sprint", [KEY_SHIFT], [JOY_BUTTON_RIGHT_SHOULDER])
	_add_action("jump", [KEY_SPACE], [JOY_BUTTON_A])
	_add_action("camera", [KEY_C], [JOY_BUTTON_Y])
	_add_action("coat", [KEY_H], [JOY_BUTTON_X])
	_add_action("mute", [KEY_M], [])
	_add_action("help", [KEY_TAB], [JOY_BUTTON_BACK])
	_add_action("fullscreen", [KEY_F], [])
	# Left stick steers too.
	for axis_dir in [["turn_left", -1.0], ["turn_right", 1.0]]:
		var motion := InputEventJoypadMotion.new()
		motion.axis = JOY_AXIS_LEFT_X
		motion.axis_value = axis_dir[1]
		InputMap.action_add_event(axis_dir[0], motion)


func _add_action(action: String, keys: Array, buttons: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.2)
	for key: Key in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		InputMap.action_add_event(action, ev)
	for button: JoyButton in buttons:
		var jb := InputEventJoypadButton.new()
		jb.button_index = button
		InputMap.action_add_event(action, jb)


func _setup_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = SKY_TOP
	sky_mat.sky_horizon_color = SKY_HORIZON
	sky_mat.ground_horizon_color = SKY_HORIZON
	sky_mat.ground_bottom_color = Color(0.45, 0.55, 0.5)
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.66, 0.72, 0.84)
	env.ambient_light_energy = 1.3
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.1
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_light_color = SKY_HORIZON
	env.fog_density = 1.0
	env.fog_depth_begin = 30.0
	env.fog_depth_end = 82.0
	env.fog_depth_curve = 1.4
	env.fog_sky_affect = 0.0
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52.0, -140.0, 0.0)
	sun.light_color = Color(1.0, 0.95, 0.86)
	sun.light_energy = 1.3
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 60.0
	add_child(sun)

	# Soft shadowless fill from the opposite side keeps shaded faces readable.
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25.0, 40.0, 0.0)
	fill.light_color = Color(0.75, 0.82, 1.0)
	fill.light_energy = 0.45
	fill.light_specular = 0.0
	fill.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	add_child(fill)


func _create_clouds() -> void:
	var mat := MeshData.make_material()
	mat.disable_fog = true
	mat.roughness = 1.0
	var rng := RandomNumberGenerator.new()
	rng.seed = WORLD_SEED + 7
	for i in 16:
		var md := MeshData.new()
		var puffs := rng.randi_range(3, 7)
		for p in puffs:
			var size := Vector3(rng.randf_range(6, 14), rng.randf_range(2, 4), rng.randf_range(5, 10))
			var at := Vector3(rng.randf_range(-10, 10), rng.randf_range(0, 2.5), rng.randf_range(-6, 6))
			md.add_box(at - size * 0.5, size, Color(1, 1, 1).darkened(rng.randf_range(0.0, 0.05)), true)
		var cloud := MeshInstance3D.new()
		cloud.mesh = md.commit(mat)
		cloud.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		cloud.position = horse.position + Vector3(
				rng.randf_range(-0.5, 0.5) * CLOUD_AREA, rng.randf_range(45, 70), rng.randf_range(-0.5, 0.5) * CLOUD_AREA)
		add_child(cloud)
		_clouds.append(cloud)


## Drift clouds with the wind and wrap them around the horse.
func _move_clouds(delta: float) -> void:
	var half := CLOUD_AREA * 0.5
	for cloud in _clouds:
		var p := cloud.position + WIND * delta
		p.x = horse.position.x + wrapf(p.x - horse.position.x, -half, half)
		p.z = horse.position.z + wrapf(p.z - horse.position.z, -half, half)
		cloud.position = p
