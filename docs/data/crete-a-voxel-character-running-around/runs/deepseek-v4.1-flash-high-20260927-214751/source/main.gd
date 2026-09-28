extends Node3D
## Builds a small voxel sandbox and spawns the player character.
## Everything is generated procedurally so the project stays self-contained.

const GROUND_SIZE := 30.0
const WALL_HEIGHT := 2.0

var _player: CharacterBody3D
var _camera: Camera3D
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	_setup_input()
	_build_environment()
	_build_ground()
	_build_props()
	_build_player()
	_build_camera()
	_build_hud()

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
func _setup_input() -> void:
	var actions := {
		"move_forward": [KEY_W, KEY_UP],
		"move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT],
		"jump": [KEY_SPACE],
	}
	for action_name in actions:
		if not InputMap.has_action(action_name):
			InputMap.add_action(action_name)
		for key in actions[action_name]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action_name, event)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
func _build_environment() -> void:
	var world_env := WorldEnvironment.new()
	world_env.name = "WorldEnvironment"
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC

	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.25, 0.5, 0.85)
	sky_mat.sky_horizon_color = Color(0.75, 0.87, 0.95)
	sky_mat.ground_bottom_color = Color(0.3, 0.35, 0.3)
	sky_mat.ground_horizon_color = Color(0.75, 0.87, 0.95)
	sky.sky_material = sky_mat
	env.sky = sky
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	add_child(sun)

# ---------------------------------------------------------------------------
# Ground + walls
# ---------------------------------------------------------------------------
func _build_ground() -> void:
	var ground := StaticBody3D.new()
	ground.name = "Ground"
	add_child(ground)

	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(GROUND_SIZE, 1.0, GROUND_SIZE)
	mesh.mesh = box
	mesh.position = Vector3(0, -0.5, 0)
	mesh.material_override = _make_material(Color(0.42, 0.66, 0.34), 1.0)
	ground.add_child(mesh)

	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = Vector3(GROUND_SIZE, 1.0, GROUND_SIZE)
	shape.shape = box_shape
	shape.position = Vector3(0, -0.5, 0)
	ground.add_child(shape)

	# Low voxel border so the character can't wander off the sandbox.
	var half := GROUND_SIZE * 0.5
	var border_color := Color(0.5, 0.38, 0.26)
	var sides := [
		[Vector3(0, WALL_HEIGHT * 0.5, -half), Vector3(GROUND_SIZE, WALL_HEIGHT, 0.5)],
		[Vector3(0, WALL_HEIGHT * 0.5, half), Vector3(GROUND_SIZE, WALL_HEIGHT, 0.5)],
		[Vector3(-half, WALL_HEIGHT * 0.5, 0), Vector3(0.5, WALL_HEIGHT, GROUND_SIZE)],
		[Vector3(half, WALL_HEIGHT * 0.5, 0), Vector3(0.5, WALL_HEIGHT, GROUND_SIZE)],
	]
	for side in sides:
		var wall := StaticBody3D.new()
		add_child(wall)
		var wall_mesh := MeshInstance3D.new()
		var wall_box := BoxMesh.new()
		wall_box.size = side[1]
		wall_mesh.mesh = wall_box
		wall_mesh.position = side[0]
		wall_mesh.material_override = _make_material(border_color, 1.0)
		wall.add_child(wall_mesh)
		var wall_shape := CollisionShape3D.new()
		var wall_shape_res := BoxShape3D.new()
		wall_shape_res.size = side[1]
		wall_shape.shape = wall_shape_res
		wall_shape.position = side[0]
		wall.add_child(wall_shape)

# ---------------------------------------------------------------------------
# Scattered voxel props
# ---------------------------------------------------------------------------
func _build_props() -> void:
	_rng.seed = 20260927
	var palette := [
		Color(0.85, 0.35, 0.3),
		Color(0.95, 0.72, 0.25),
		Color(0.35, 0.55, 0.85),
		Color(0.6, 0.4, 0.75),
		Color(0.3, 0.7, 0.6),
		Color(0.9, 0.55, 0.3),
	]

	var props_root := Node3D.new()
	props_root.name = "Props"
	add_child(props_root)

	# A handful of stacked voxel clusters scattered around the arena.
	for i in range(26):
		var cell_x := _rng.randi_range(-6, 6) * 2.0
		var cell_z := _rng.randi_range(-6, 6) * 2.0
		if abs(cell_x) < 3.0 and abs(cell_z) < 3.0:
			continue
		var height := _rng.randi_range(1, 3)
		var base_color: Color = palette[_rng.randi_range(0, palette.size() - 1)]
		for h in range(height):
			var block_size := Vector3(1.0, 1.0, 1.0)
			var body := StaticBody3D.new()
			body.position = Vector3(cell_x, 0.5 + h, cell_z)
			props_root.add_child(body)
			var mi := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = block_size
			mi.mesh = bm
			var c := base_color.lightened(h * 0.06)
			mi.material_override = _make_material(c, 1.0)
			body.add_child(mi)
			var cs := CollisionShape3D.new()
			var bs := BoxShape3D.new()
			bs.size = block_size
			cs.shape = bs
			body.add_child(cs)

	# A few tall accent pillars.
	for pos in [Vector3(-10, 0, -10), Vector3(10, 0, -10), Vector3(-10, 0, 10), Vector3(10, 0, 10)]:
		for h in range(4):
			var pillar := StaticBody3D.new()
			pillar.position = pos + Vector3(0, 0.5 + h, 0)
			props_root.add_child(pillar)
			var mi := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(1.4, 1.0, 1.4)
			mi.mesh = bm
			mi.material_override = _make_material(Color(0.55, 0.55, 0.6).lightened(h * 0.05), 1.0)
			pillar.add_child(mi)
			var cs := CollisionShape3D.new()
			var bs := BoxShape3D.new()
			bs.size = Vector3(1.4, 1.0, 1.4)
			cs.shape = bs
			pillar.add_child(cs)

# ---------------------------------------------------------------------------
# Player + camera + HUD
# ---------------------------------------------------------------------------
func _build_player() -> void:
	_player = load("res://player.gd").new()
	_player.name = "VoxelPlayer"
	_player.position = Vector3(0, 1.0, 0)
	add_child(_player)

func _build_camera() -> void:
	_camera = Camera3D.new()
	_camera.name = "Camera"
	_camera.current = true
	_camera.fov = 65.0
	_camera.position = Vector3(0, 3.2, 5.5)
	add_child(_camera)

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	layer.name = "HUD"
	add_child(layer)

	var panel := PanelContainer.new()
	panel.position = Vector2(16, 16)
	layer.add_child(panel)

	var label := Label.new()
	label.text = "Voxel Runner\nWASD / Arrows - Move\nSpace - Jump"
	label.add_theme_font_size_override("font_size", 18)
	panel.add_child(label)

func _process(delta: float) -> void:
	if _player == null or _camera == null:
		return
	var focus := _player.global_position + Vector3(0, 1.4, 0)
	var desired := focus + Vector3(0, 2.2, 5.0)
	var weight := 1.0 - exp(-6.0 * delta)
	_camera.global_position = _camera.global_position.lerp(desired, weight)
	_camera.look_at(focus, Vector3.UP)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
func _make_material(color: Color, roughness: float) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = roughness
	mat.metallic = 0.0
	return mat
