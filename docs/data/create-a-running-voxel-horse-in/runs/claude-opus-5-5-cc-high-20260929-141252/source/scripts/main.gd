extends Node3D
## Sets up the scene: environment, world, horse, camera and HUD.

const HorseScript := preload("res://scripts/horse.gd")
const WorldScript := preload("res://scripts/world.gd")

const CAMERA_NAMES := ["Chase", "Side", "Front", "Orbit"]
const SKY_HORIZON := Color(0.74, 0.84, 0.95)

var _horse: Node3D
var _world: Node3D
var _camera: Camera3D
var _cam_mode := 0
var _cam_yaw := 0.0
var _zoom := 1.0
var _time := 0.0
var _carrots := 0
var _jumps := 0
var _stats: Label
var _message: Label
var _message_time := 0.0


func _ready() -> void:
	# Run after the horse so the camera never lags a frame behind.
	process_priority = 100
	_setup_input()
	_setup_environment()

	_world = WorldScript.new()
	add_child(_world)
	_horse = HorseScript.new()
	_horse.world = _world
	add_child(_horse)
	_world.update_around(_horse.position, true)

	_camera = Camera3D.new()
	_camera.fov = 60.0
	_camera.far = 250.0
	add_child(_camera)
	_camera.make_current()
	_camera.position = Vector3(0, 2.3, 6.8)
	_cam_yaw = _horse.rotation.y

	_setup_hud()
	_horse.bumped.connect(func(): _show_message("Whoa! Watch where you're going!"))
	_world.carrot_collected.connect(func():
		_carrots += 1
		_show_message("Carrot! (%d)" % _carrots))
	_world.obstacle_cleared.connect(func():
		_jumps += 1
		_show_message("Nice jump!"))
	_show_message("Ride on! Collect carrots and jump the logs.", 4.0)


func _add_action(action: String, keys: Array, joy_buttons: Array = [], joy_axis := -1, axis_dir := 0.0) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)
	for b in joy_buttons:
		var jb := InputEventJoypadButton.new()
		jb.button_index = b
		InputMap.action_add_event(action, jb)
	if joy_axis >= 0:
		var jm := InputEventJoypadMotion.new()
		jm.axis = joy_axis
		jm.axis_value = axis_dir
		InputMap.action_add_event(action, jm)


func _setup_input() -> void:
	_add_action("faster", [KEY_W, KEY_UP], [JOY_BUTTON_DPAD_UP, JOY_BUTTON_RIGHT_SHOULDER])
	_add_action("slower", [KEY_S, KEY_DOWN], [JOY_BUTTON_DPAD_DOWN, JOY_BUTTON_LEFT_SHOULDER])
	_add_action("steer_left", [KEY_A, KEY_LEFT], [JOY_BUTTON_DPAD_LEFT], JOY_AXIS_LEFT_X, -1.0)
	_add_action("steer_right", [KEY_D, KEY_RIGHT], [JOY_BUTTON_DPAD_RIGHT], JOY_AXIS_LEFT_X, 1.0)
	_add_action("jump", [KEY_SPACE], [JOY_BUTTON_A])
	_add_action("camera", [KEY_C], [JOY_BUTTON_Y])


func _setup_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.3, 0.52, 0.88)
	sky_mat.sky_horizon_color = SKY_HORIZON
	sky_mat.ground_horizon_color = SKY_HORIZON
	sky_mat.ground_bottom_color = Color(0.35, 0.5, 0.3)
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.6, 0.68, 0.8)
	env.ambient_light_energy = 0.4
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_light_color = SKY_HORIZON
	env.fog_depth_begin = 45.0
	env.fog_depth_end = 100.0
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -38, 0)
	sun.light_energy = 0.55
	sun.light_color = Color(1.0, 0.96, 0.88)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 45.0
	add_child(sun)


func _make_label(size: int) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(1, 1, 0.96))
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.08, 0.05))
	l.add_theme_constant_override("outline_size", 6)
	return l


func _setup_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_stats = _make_label(22)
	_stats.position = Vector2(18, 14)
	layer.add_child(_stats)

	var help := _make_label(17)
	help.text = "W/S or Up/Down: change gait    A/D or Left/Right: steer    Space: jump (rear when standing)    C: camera    Mouse wheel: zoom"
	layer.add_child(help)
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT, Control.PRESET_MODE_MINSIZE, 16)

	_message = _make_label(30)
	_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	layer.add_child(_message)
	_message.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_message.offset_top = 90


func _show_message(text: String, duration := 2.0) -> void:
	_message.text = text
	_message_time = duration


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("camera"):
		_cam_mode = (_cam_mode + 1) % CAMERA_NAMES.size()
		_show_message("Camera: " + CAMERA_NAMES[_cam_mode], 1.2)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_zoom = maxf(0.5, _zoom * 0.9)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_zoom = minf(2.5, _zoom / 0.9)


func _process(delta: float) -> void:
	_time += delta
	_world.update_around(_horse.position)
	_update_camera(delta)
	_update_hud(delta)


func _update_camera(delta: float) -> void:
	var hp: Vector3 = _horse.position
	var run := clampf(_horse.speed / 12.5, 0.0, 1.0)
	_cam_yaw = lerp_angle(_cam_yaw, _horse.rotation.y, 1.0 - exp(-3.0 * delta))
	var offset: Vector3
	match _cam_mode:
		0:
			offset = Vector3(0, 2.3, 6.8)
		1:
			offset = Vector3(6.5, 1.3, -0.4)
		2:
			offset = Vector3(-2.5, 1.5, -7.5)
		_:
			offset = Vector3(sin(_time * 0.3) * 8.0, 3.0, cos(_time * 0.3) * 8.0)
	var desired := hp + (offset * _zoom).rotated(Vector3.UP, _cam_yaw)
	var clear: float = _world.camera_clearance(hp, desired)
	if clear < 1.0:
		var pulled := hp + (desired - hp) * maxf(clear - 0.1, 0.25)
		desired = Vector3(pulled.x, desired.y, pulled.z)
	desired.y = maxf(desired.y, 0.4)
	_camera.position = _camera.position.lerp(desired, 1.0 - exp(-8.0 * delta))
	_camera.look_at(hp + Vector3(0, 1.2 + _horse.height * 0.6, 0), Vector3.UP)
	_camera.fov = lerpf(_camera.fov, lerpf(60.0, 70.0, run), 1.0 - exp(-3.0 * delta))


func _update_hud(delta: float) -> void:
	var target: String = _horse.GAIT_NAMES[_horse.target_gait]
	_stats.text = "Gait: %s  (target: %s)\nSpeed: %d km/h\nDistance: %d m\nCarrots: %d    Jumps: %d" % [
		_horse.gait_name(), target, roundi(_horse.speed * 3.6), int(_horse.distance), _carrots, _jumps]
	if _message_time > 0.0:
		_message_time -= delta
		_message.modulate.a = clampf(_message_time * 2.0, 0.0, 1.0)
