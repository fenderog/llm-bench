extends Node3D

## Builds a small voxel sandbox and spawns the playable voxel character.
## Everything (meshes, materials, environment) is generated at runtime, so the
## project stays completely self-contained with no external assets.

const GROUND_TILES := 24
const GROUND_EXTENT := 12.0            # half-size of the playable ground
const VOXEL_SIZE := 1.0

var _voxel_transforms: Array[Transform3D] = []
var _voxel_colors: Array[Color] = []

var _rng := RandomNumberGenerator.new()
var player: VoxelCharacter
var camera: Camera3D
var _camera_look := Vector3.ZERO
var _camera_offset := Vector3(10.0, 10.0, 10.0)


func _ready() -> void:
	_rng.seed = 20260927
	_setup_input()
	_setup_environment()
	_build_ground()
	_build_walls()
	_build_sandbox_props()
	_commit_voxels()
	_spawn_player()
	_setup_camera()
	_setup_hud()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
func _setup_input() -> void:
	_bind("move_left", [KEY_A, KEY_LEFT])
	_bind("move_right", [KEY_D, KEY_RIGHT])
	_bind("move_forward", [KEY_W, KEY_UP])
	_bind("move_back", [KEY_S, KEY_DOWN])
	_bind("jump", [KEY_SPACE])


func _bind(action: String, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for key in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		if not InputMap.action_has_event(action, ev):
			InputMap.action_add_event(action, ev)


# ---------------------------------------------------------------------------
# Rendering environment and lighting
# ---------------------------------------------------------------------------
func _setup_environment() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.28, 0.52, 0.90)
	sky_material.sky_horizon_color = Color(0.75, 0.87, 0.98)
	sky_material.ground_bottom_color = Color(0.30, 0.38, 0.30)
	sky_material.ground_horizon_color = Color(0.72, 0.82, 0.86)
	sky_material.sun_angle_max = 20.0

	var sky := Sky.new()
	sky.sky_material = sky_material

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.05
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.74, 0.85, 0.96)
	env.fog_density = 0.008

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52.0, -38.0, 0.0)
	sun.light_energy = 1.15
	sun.light_color = Color(1.0, 0.96, 0.87)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_max_distance = 60.0
	add_child(sun)


# ---------------------------------------------------------------------------
# Voxel accumulation helpers
# ---------------------------------------------------------------------------
func _add_voxel(pos: Vector3, color: Color, size: Vector3 = Vector3.ONE) -> void:
	_voxel_transforms.append(Transform3D(Basis().scaled(size), pos))
	_voxel_colors.append(color)


func _add_solid(center: Vector3, size: Vector3, color: Color) -> void:
	_add_voxel(center, color, size)
	var body := StaticBody3D.new()
	body.position = center
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	col.shape = box
	body.add_child(col)
	add_child(body)


func _commit_voxels() -> void:
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.92

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = mesh
	mm.instance_count = _voxel_transforms.size()
	for i in _voxel_transforms.size():
		mm.set_instance_transform(i, _voxel_transforms[i])
		mm.set_instance_color(i, _voxel_colors[i])

	var mmi := MultiMeshInstance3D.new()
	mmi.name = "VoxelWorld"
	mmi.multimesh = mm
	# Assign the material on the instance so the shared mesh keeps its default.
	mmi.material_override = mat
	add_child(mmi)


# ---------------------------------------------------------------------------
# Ground and boundary
# ---------------------------------------------------------------------------
func _build_ground() -> void:
	var grass_a := Color(0.34, 0.62, 0.27)
	var grass_b := Color(0.29, 0.56, 0.23)
	var grass_c := Color(0.40, 0.68, 0.31)

	for i in GROUND_TILES:
		for j in GROUND_TILES:
			var x: float = i - GROUND_TILES * 0.5 + 0.5
			var z: float = j - GROUND_TILES * 0.5 + 0.5
			var roll := _rng.randf()
			var color := grass_a
			if roll < 0.33:
				color = grass_b
			elif roll > 0.82:
				color = grass_c
			_add_voxel(Vector3(x, -0.5, z), color)

	# One solid collision slab under the whole play area.
	var ground := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(GROUND_TILES, 1.0, GROUND_TILES)
	col.shape = box
	ground.position = Vector3(0.0, -0.5, 0.0)
	ground.add_child(col)
	add_child(ground)


func _build_walls() -> void:
	var stone := Color(0.55, 0.55, 0.60)
	var stone_dark := Color(0.45, 0.45, 0.51)
	var length := GROUND_TILES + 1.2
	var h := 1.6
	var edge := GROUND_EXTENT + 0.3

	_add_solid(Vector3(0.0, h * 0.5, -edge), Vector3(length, h, 0.6), stone)
	_add_solid(Vector3(0.0, h * 0.5, edge), Vector3(length, h, 0.6), stone_dark)
	_add_solid(Vector3(-edge, h * 0.5, 0.0), Vector3(0.6, h, GROUND_TILES - 0.6), stone)
	_add_solid(Vector3(edge, h * 0.5, 0.0), Vector3(0.6, h, GROUND_TILES - 0.6), stone_dark)

	# Chunky crenellations along the top of the walls for texture.
	for i in range(-GROUND_TILES / 2, GROUND_TILES / 2, 3):
		_add_voxel(Vector3(i + 0.5, h + 0.3, -edge), stone)
		_add_voxel(Vector3(i + 0.5, h + 0.3, edge), stone_dark)
		_add_voxel(Vector3(-edge, h + 0.3, i + 0.5), stone)
		_add_voxel(Vector3(edge, h + 0.3, i + 0.5), stone_dark)


# ---------------------------------------------------------------------------
# Sandbox props: platforms, trees, crates, decorations
# ---------------------------------------------------------------------------
func _build_sandbox_props() -> void:
	_build_pyramid(Vector3(-5.5, 0.0, -5.5))
	_build_ramp()
	_build_tree(Vector3(6.5, 0.0, -6.0), 1.0)
	_build_tree(Vector3(7.5, 0.0, 5.5), 1.25)
	_build_tree(Vector3(-7.5, 0.0, 6.0), 0.9)
	_build_crates()
	_scatter_flowers()


func _build_pyramid(base: Vector3) -> void:
	var stone_a := Color(0.66, 0.63, 0.58)
	var stone_b := Color(0.58, 0.55, 0.50)
	var tiers := [
		{"inset": 0.0, "height": 0.5, "half": 2.5, "color": stone_a},
		{"inset": 0.9, "height": 0.5, "half": 1.6, "color": stone_b},
		{"inset": 1.7, "height": 0.5, "half": 0.8, "color": stone_a},
	]
	var y := 0.0
	for tier in tiers:
		var half: float = tier["half"]
		var h: float = tier["height"]
		var size := Vector3(half * 2.0, h, half * 2.0)
		_add_solid(base + Vector3(0.0, y + h * 0.5, 0.0), size, tier["color"])
		y += h


func _build_ramp() -> void:
	# A gentle walkable ramp leading up onto a small platform.
	var wood := Color(0.62, 0.44, 0.26)
	var wood_dark := Color(0.52, 0.36, 0.21)

	var platform_center := Vector3(5.0, 0.75, -1.0)
	_add_solid(platform_center, Vector3(4.0, 1.5, 4.0), wood_dark)

	var angle := deg_to_rad(20.0)
	var ramp_center := Vector3(1.7, 0.75, -1.0)
	var ramp_size := Vector3(3.6, 0.3, 3.0)
	var basis := Basis(Vector3.BACK, angle).scaled(ramp_size)
	_voxel_transforms.append(Transform3D(basis, ramp_center))
	_voxel_colors.append(wood)

	var body := StaticBody3D.new()
	body.transform = Transform3D(basis, ramp_center)
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = ramp_size
	col.shape = box
	body.add_child(col)
	add_child(body)


func _build_tree(base: Vector3, scale_factor: float) -> void:
	var trunk := Color(0.42, 0.28, 0.15)
	var trunk_dark := Color(0.34, 0.22, 0.12)
	var leaf_a := Color(0.22, 0.52, 0.22)
	var leaf_b := Color(0.29, 0.62, 0.27)
	var leaf_c := Color(0.17, 0.44, 0.19)

	var trunk_h := int(round(3.0 * scale_factor))
	_add_solid(base + Vector3(0.0, trunk_h * 0.5 + 0.5, 0.0), Vector3(0.7, trunk_h, 0.7), trunk)
	for i in trunk_h:
		if i % 2 == 1:
			_add_voxel(base + Vector3(0.36, i + 0.5, 0.0), trunk_dark, Vector3(0.12, 1.0, 0.7))

	var crown_radius := 2 if scale_factor < 1.1 else 3
	var crown_y := trunk_h + 1
	for dx in range(-crown_radius, crown_radius + 1):
		for dz in range(-crown_radius, crown_radius + 1):
			for dy in range(-1, 2):
				var dist := absi(dx) + absi(dz) + absi(dy)
				if dist > crown_radius + 1:
					continue
				var roll := _rng.randf()
				var color := leaf_a
				if roll < 0.3:
					color = leaf_b
				elif roll > 0.78:
					color = leaf_c
				var p := base + Vector3(float(dx), float(crown_y + dy), float(dz))
				_add_voxel(p, color)


func _build_crates() -> void:
	var crate := Color(0.76, 0.53, 0.26)
	var crate_dark := Color(0.62, 0.41, 0.19)
	var positions := [
		[Vector3(-3.0, 0.6, 4.0), 1.2],
		[Vector3(-1.6, 0.6, 4.6), 1.2],
		[Vector3(-2.4, 1.8, 4.2), 1.2],
		[Vector3(3.5, 0.7, 3.0), 1.4],
		[Vector3(4.6, 0.45, 4.4), 0.9],
	]
	for entry in positions:
		var center: Vector3 = entry[0]
		var s: float = entry[1]
		_add_solid(center, Vector3(s, s, s), crate)
		# A darker rim so each crate reads as a box.
		_add_voxel(center + Vector3(0.0, s * 0.5, 0.0), crate_dark, Vector3(s * 1.02, 0.08, s * 1.02))


func _scatter_flowers() -> void:
	var colors := [
		Color(0.95, 0.85, 0.25),
		Color(0.92, 0.35, 0.42),
		Color(0.85, 0.85, 0.95),
		Color(0.45, 0.80, 0.95),
	]
	for i in 40:
		var x := _rng.randf_range(-GROUND_EXTENT + 1.5, GROUND_EXTENT - 1.5)
		var z := _rng.randf_range(-GROUND_EXTENT + 1.5, GROUND_EXTENT - 1.5)
		if Vector2(x, z).length() < 2.0:
			continue
		var stem := Color(0.30, 0.52, 0.22)
		_add_voxel(Vector3(x, 0.15, z), stem, Vector3(0.1, 0.3, 0.1))
		_add_voxel(Vector3(x, 0.36, z), colors[_rng.randi() % colors.size()], Vector3(0.24, 0.16, 0.24))


# ---------------------------------------------------------------------------
# Player and camera
# ---------------------------------------------------------------------------
func _spawn_player() -> void:
	player = VoxelCharacter.new()
	player.name = "VoxelCharacter"
	player.position = Vector3(0.0, 0.05, 0.0)
	add_child(player)
	_camera_look = player.global_position + Vector3(0.0, 1.0, 0.0)


func _setup_camera() -> void:
	camera = Camera3D.new()
	camera.name = "FollowCamera"
	camera.fov = 55.0
	camera.current = true
	add_child(camera)
	camera.position = _camera_look + _camera_offset
	camera.look_at(_camera_look, Vector3.UP)


func _process(delta: float) -> void:
	if player == null or camera == null:
		return
	# Smooth third-person follow that keeps the character centred on screen.
	var target_look := player.global_position + Vector3(0.0, 1.0, 0.0)
	_camera_look = _camera_look.lerp(target_look, 1.0 - exp(-6.0 * delta))
	var desired := _camera_look + _camera_offset
	camera.global_position = camera.global_position.lerp(desired, 1.0 - exp(-7.0 * delta))
	camera.look_at(_camera_look, Vector3.UP)


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
func _setup_hud() -> void:
	var layer := CanvasLayer.new()
	layer.name = "HUD"
	add_child(layer)

	var label := Label.new()
	label.text = "Voxel Sandbox Runner\nWASD / Arrows to run   •   Space to jump"
	label.add_theme_font_size_override("font_size", 22)
	label.add_theme_color_override("font_color", Color(1, 1, 1))
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.65))
	label.add_theme_constant_override("outline_size", 6)
	label.position = Vector2(24, 20)
	layer.add_child(label)
