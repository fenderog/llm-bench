extends Node3D
## Voxel Runner
##
## A small, fully procedural voxel sandbox. A blocky character runs, jumps
## and collects spinning coins. Nothing is loaded from disk: the terrain,
## props, character and camera are all assembled in code so the project stays
## completely self-contained and web friendly (no threads, GL Compatibility).

const PLAYER_SCRIPT := preload("res://scripts/player.gd")
const COIN_SCRIPT := preload("res://scripts/coin.gd")

const WORLD_SIZE := 40
const HALF_SIZE := WORLD_SIZE / 2.0
const SPAWN_HEIGHT := 2
const WATER_LEVEL := 0.0
const TOTAL_COINS := 12
const POND_CENTER := Vector2(9.0, -7.0)
const POND_RADIUS := 5.0
const BLOCK_DEPTH := 4.0

var rng := RandomNumberGenerator.new()
var noise := FastNoiseLite.new()

var heights := PackedFloat32Array()
var terrain_body: StaticBody3D

var player
var camera_rig: Node3D
var spring_arm: SpringArm3D

var clouds: Array[Node3D] = []
var cloud_speeds: Array[float] = []

var active_coins: Array[Area3D] = []

var yaw := -0.5
var pitch := -0.3
var score := 0

var hud_score: Label
var hud_message: Label

var leaf_materials: Array[StandardMaterial3D] = []
var flower_materials: Array[StandardMaterial3D] = []
var trunk_material: StandardMaterial3D
var rock_material: StandardMaterial3D
var stem_material: StandardMaterial3D


func _ready() -> void:
	rng.randomize()
	noise.seed = rng.randi()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.055
	noise.fractal_type = FastNoiseLite.FRACTAL_FBM
	noise.fractal_octaves = 3
	noise.fractal_gain = 0.5

	_setup_input()
	_build_environment()
	_generate_heights()
	_build_terrain()
	_build_props()
	_build_clouds()
	_build_player()
	_build_camera()
	_build_hud()
	_spawn_coins(TOTAL_COINS)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _setup_input() -> void:
	_add_key_action("move_forward", [KEY_W])
	_add_key_action("move_back", [KEY_S])
	_add_key_action("move_left", [KEY_A])
	_add_key_action("move_right", [KEY_D])
	_add_key_action("jump", [KEY_SPACE])
	_add_key_action("sprint", [KEY_SHIFT])
	_add_key_action("cam_left", [KEY_Q])
	_add_key_action("cam_right", [KEY_E])


func _add_key_action(action: String, keycodes: Array) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, 0.2)
	for code in keycodes:
		var ev := InputEventKey.new()
		ev.physical_keycode = code
		InputMap.action_add_event(action, ev)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * 0.0035
		pitch = clampf(pitch - event.relative.y * 0.0026, -1.35, -0.06)
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

func _build_environment() -> void:
	var world_env := WorldEnvironment.new()
	var env := Environment.new()

	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.17, 0.42, 0.86)
	sky_mat.sky_horizon_color = Color(0.76, 0.89, 0.98)
	sky_mat.sky_curve = 0.12
	sky_mat.ground_bottom_color = Color(0.25, 0.3, 0.24)
	sky_mat.ground_horizon_color = Color(0.76, 0.89, 0.98)
	sky_mat.sun_angle_max = 25.0
	sky_mat.sun_curve = 0.08
	sky.sky_material = sky_mat
	env.sky = sky

	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.55
	env.ambient_light_sky_contribution = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 0.9
	env.fog_enabled = true
	env.fog_light_color = Color(0.76, 0.89, 0.98)
	env.fog_light_energy = 1.0
	env.fog_density = 0.0045

	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52.0, -38.0, 0.0)
	sun.light_color = Color(1.0, 0.97, 0.9)
	sun.light_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 75.0
	sun.shadow_bias = 0.04
	add_child(sun)


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

func _world_coord(i: int) -> float:
	return float(i) - HALF_SIZE + 0.5


func _column_height(x: int, z: int) -> float:
	return heights[z * WORLD_SIZE + x]


func _generate_heights() -> void:
	heights.resize(WORLD_SIZE * WORLD_SIZE)
	for z in WORLD_SIZE:
		for x in WORLD_SIZE:
			var wx := _world_coord(x)
			var wz := _world_coord(z)
			var n := noise.get_noise_2d(wx, wz)
			var n2 := noise.get_noise_2d(wx * 2.7 + 31.0, wz * 2.7 - 17.0)
			var h := 2.0 + n * 3.2 + n2 * 1.1

			# Keep the spawn area flat and comfortable.
			var d_spawn := Vector2(wx, wz).length()
			if d_spawn < 6.5:
				var t := smoothstep(0.0, 1.0, 1.0 - d_spawn / 6.5)
				h = lerpf(h, float(SPAWN_HEIGHT), t)

			# Carve a little pond.
			var d_pond := Vector2(wx - POND_CENTER.x, wz - POND_CENTER.y).length()
			if d_pond < POND_RADIUS:
				var t := smoothstep(0.0, 1.0, 1.0 - d_pond / POND_RADIUS)
				h = lerpf(h, -2.0, t)

			# Raise a blocky rim around the sandbox so it feels enclosed.
			var edge := maxf(absf(wx), absf(wz))
			var rim_start := HALF_SIZE - 4.0
			if edge > rim_start:
				var t := (edge - rim_start) / (HALF_SIZE - rim_start)
				h = maxf(h, 2.0 + t * 3.0)

			heights[z * WORLD_SIZE + x] = roundf(clampf(h, -2.0, 6.0))


func _make_multimesh(count: int, color: Color, transparent := false) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true

	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.95
	mat.vertex_color_use_as_albedo = true
	if transparent:
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.metallic = 0.15
		mat.roughness = 0.15
		mat.vertex_color_use_as_albedo = false
	mesh.material = mat

	mm.mesh = mesh
	mm.instance_count = count

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	if transparent:
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)
	return mm


func _place_instance(mm: MultiMesh, idx: int, pos: Vector3, size: Vector3) -> void:
	mm.set_instance_transform(idx, Transform3D(Basis().scaled(size), pos))
	var s := rng.randf_range(0.82, 1.02)
	mm.set_instance_color(idx, Color(
		s * rng.randf_range(0.97, 1.03),
		s * rng.randf_range(0.97, 1.03),
		s * rng.randf_range(0.97, 1.03),
		1.0))


func _add_static_box(shape_size: Vector3, xform: Transform3D) -> void:
	var shape := BoxShape3D.new()
	shape.size = shape_size
	var owner_id := terrain_body.create_shape_owner(self)
	terrain_body.shape_owner_add_shape(owner_id, shape)
	terrain_body.shape_owner_set_transform(owner_id, xform)


func _build_terrain() -> void:
	terrain_body = StaticBody3D.new()
	terrain_body.collision_layer = 1
	terrain_body.collision_mask = 0
	add_child(terrain_body)

	# Count each material class first so each MultiMesh can be sized exactly.
	var c_dirt := 0
	var c_stone := 0
	var c_grass := 0
	var c_rock := 0
	var c_snow := 0
	var c_sand := 0
	var c_water := 0
	for z in WORLD_SIZE:
		for x in WORLD_SIZE:
			var h := _column_height(x, z)
			if h <= WATER_LEVEL:
				c_dirt += 1
				c_sand += 1
				c_water += 1
			elif h <= 3.0:
				c_dirt += 1
				c_grass += 1
			elif h <= 5.0:
				c_stone += 1
				c_rock += 1
			else:
				c_stone += 1
				c_snow += 1

	var mm_dirt := _make_multimesh(c_dirt, Color(0.4, 0.27, 0.15))
	var mm_stone := _make_multimesh(c_stone, Color(0.42, 0.43, 0.46))
	var mm_grass := _make_multimesh(c_grass, Color(0.24, 0.6, 0.17))
	var mm_rock := _make_multimesh(c_rock, Color(0.46, 0.46, 0.5))
	var mm_snow := _make_multimesh(c_snow, Color(0.9, 0.93, 0.97))
	var mm_sand := _make_multimesh(c_sand, Color(0.8, 0.72, 0.45))
	var mm_water := _make_multimesh(c_water, Color(0.1, 0.4, 0.8, 0.6), true)

	var terrain_shape := BoxShape3D.new()
	terrain_shape.size = Vector3(1.0, BLOCK_DEPTH, 1.0)

	var i_dirt := 0
	var i_stone := 0
	var i_grass := 0
	var i_rock := 0
	var i_snow := 0
	var i_sand := 0
	var i_water := 0

	for z in WORLD_SIZE:
		for x in WORLD_SIZE:
			var h := _column_height(x, z)
			var wx := _world_coord(x)
			var wz := _world_coord(z)

			# Column body extends downward so cliffs have solid sides.
			if h <= 3.0:
				_place_instance(mm_dirt, i_dirt, Vector3(wx, h - BLOCK_DEPTH * 0.5 - 0.3, wz), Vector3(1.0, BLOCK_DEPTH, 1.0))
				i_dirt += 1
			else:
				_place_instance(mm_stone, i_stone, Vector3(wx, h - BLOCK_DEPTH * 0.5 - 0.3, wz), Vector3(1.0, BLOCK_DEPTH, 1.0))
				i_stone += 1

			# Visible top cap.
			if h <= WATER_LEVEL:
				_place_instance(mm_sand, i_sand, Vector3(wx, h - 0.15, wz), Vector3(1.0, 0.3, 1.0))
				i_sand += 1
				_place_instance(mm_water, i_water, Vector3(wx, WATER_LEVEL - 0.15, wz), Vector3(1.0, 0.3, 1.0))
				i_water += 1
			elif h <= 3.0:
				_place_instance(mm_grass, i_grass, Vector3(wx, h - 0.15, wz), Vector3(1.0, 0.3, 1.0))
				i_grass += 1
			elif h <= 5.0:
				_place_instance(mm_rock, i_rock, Vector3(wx, h - 0.15, wz), Vector3(1.0, 0.3, 1.0))
				i_rock += 1
			else:
				_place_instance(mm_snow, i_snow, Vector3(wx, h - 0.15, wz), Vector3(1.0, 0.3, 1.0))
				i_snow += 1

			# Collision: one box per column, top surface exactly at height h.
			var owner_id := terrain_body.create_shape_owner(self)
			terrain_body.shape_owner_add_shape(owner_id, terrain_shape)
			terrain_body.shape_owner_set_transform(owner_id, Transform3D(Basis.IDENTITY, Vector3(wx, h - BLOCK_DEPTH * 0.5, wz)))

	# Invisible walls just inside the rim, as a safety net.
	var wall_shape := BoxShape3D.new()
	wall_shape.size = Vector3(1.0, 24.0, WORLD_SIZE + 2.0)
	for i in 2:
		var side := -1.0 if i == 0 else 1.0
		var owner_a := terrain_body.create_shape_owner(self)
		terrain_body.shape_owner_add_shape(owner_a, wall_shape)
		terrain_body.shape_owner_set_transform(owner_a, Transform3D(Basis.IDENTITY, Vector3(side * (HALF_SIZE + 0.6), 6.0, 0.0)))
	var wall_shape_z := BoxShape3D.new()
	wall_shape_z.size = Vector3(WORLD_SIZE + 2.0, 24.0, 1.0)
	for i in 2:
		var side := -1.0 if i == 0 else 1.0
		var owner_b := terrain_body.create_shape_owner(self)
		terrain_body.shape_owner_add_shape(owner_b, wall_shape_z)
		terrain_body.shape_owner_set_transform(owner_b, Transform3D(Basis.IDENTITY, Vector3(0.0, 6.0, side * (HALF_SIZE + 0.6))))


# ---------------------------------------------------------------------------
# Props (trees, rocks, flowers)
# ---------------------------------------------------------------------------

func _make_material(color: Color, unshaded := false) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.95
	if unshaded:
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return mat


func _add_box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = mat
	mi.mesh = bm
	mi.position = pos
	parent.add_child(mi)
	return mi


func _build_props() -> void:
	trunk_material = _make_material(Color(0.35, 0.23, 0.12))
	rock_material = _make_material(Color(0.36, 0.37, 0.41))
	stem_material = _make_material(Color(0.15, 0.45, 0.12))
	leaf_materials = [
		_make_material(Color(0.13, 0.45, 0.12)),
		_make_material(Color(0.18, 0.52, 0.15)),
		_make_material(Color(0.1, 0.4, 0.18)),
		_make_material(Color(0.24, 0.58, 0.2)),
	]
	flower_materials = [
		_make_material(Color(1.0, 0.85, 0.3)),
		_make_material(Color(1.0, 0.45, 0.5)),
		_make_material(Color(0.65, 0.5, 1.0)),
		_make_material(Color(1.0, 0.6, 0.8)),
		_make_material(Color(0.4, 0.9, 0.9)),
	]

	# A few hand-placed landmarks so the view around the spawn always reads well.
	_try_tree_at(-5.5, -6.0)
	_try_tree_at(7.5, -4.5)
	_try_tree_at(-9.5, 1.5)
	_try_tree_at(6.0, 8.5)
	_try_rock_at(-3.5, -4.5)
	_try_rock_at(4.5, -7.5)
	_try_flower_at(2.0, -4.0)
	_try_flower_at(-2.5, -3.5)
	_try_flower_at(3.5, -2.5)

	var prop_spots: Array[Vector2] = []

	var placed := 0
	var attempts := 0
	while placed < 30 and attempts < 900:
		attempts += 1
		var x := rng.randi_range(0, WORLD_SIZE - 1)
		var z := rng.randi_range(0, WORLD_SIZE - 1)
		var h := _column_height(x, z)
		var wx := _world_coord(x)
		var wz := _world_coord(z)
		if h < 1.0 or h > 3.0:
			continue
		if absf(wx) > HALF_SIZE - 5.0 or absf(wz) > HALF_SIZE - 5.0:
			continue
		if Vector2(wx, wz).length() < 7.0:
			continue
		if Vector2(wx + 3.4, wz - 6.3).length() < 5.0:
			continue
		if Vector2(wx - POND_CENTER.x, wz - POND_CENTER.y).length() < POND_RADIUS + 1.5:
			continue
		var too_close := false
		for spot in prop_spots:
			if Vector2(wx, wz).distance_to(spot) < 3.0:
				too_close = true
				break
		if too_close:
			continue
		prop_spots.append(Vector2(wx, wz))
		_spawn_tree(wx, wz, h)
		placed += 1

	# Rocks, sprinkled anywhere on open ground.
	placed = 0
	attempts = 0
	while placed < 14 and attempts < 600:
		attempts += 1
		var x := rng.randi_range(0, WORLD_SIZE - 1)
		var z := rng.randi_range(0, WORLD_SIZE - 1)
		var h := _column_height(x, z)
		var wx := _world_coord(x)
		var wz := _world_coord(z)
		if h < 1.0 or h > 4.0:
			continue
		if absf(wx) > HALF_SIZE - 5.0 or absf(wz) > HALF_SIZE - 5.0:
			continue
		if Vector2(wx, wz).length() < 8.5:
			continue
		if Vector2(wx + 3.4, wz - 6.3).length() < 5.0:
			continue
		if Vector2(wx - POND_CENTER.x, wz - POND_CENTER.y).length() < POND_RADIUS + 1.0:
			continue
		_spawn_rock(wx, wz, h)
		placed += 1

	# Flowers on the grass.
	placed = 0
	attempts = 0
	while placed < 55 and attempts < 900:
		attempts += 1
		var x := rng.randi_range(0, WORLD_SIZE - 1)
		var z := rng.randi_range(0, WORLD_SIZE - 1)
		var h := _column_height(x, z)
		var wx := _world_coord(x)
		var wz := _world_coord(z)
		if h < 1.0 or h > 3.0:
			continue
		if absf(wx) > HALF_SIZE - 5.0 or absf(wz) > HALF_SIZE - 5.0:
			continue
		_spawn_flower(wx, wz, h)
		placed += 1


func _try_tree_at(wx: float, wz: float) -> void:
	var x := int(wx + HALF_SIZE - 0.5)
	var z := int(wz + HALF_SIZE - 0.5)
	if x < 0 or z < 0 or x >= WORLD_SIZE or z >= WORLD_SIZE:
		return
	var h := _column_height(x, z)
	if h < 1.0 or h > 3.0:
		return
	_spawn_tree(_world_coord(x), _world_coord(z), h)


func _try_rock_at(wx: float, wz: float) -> void:
	var x := int(wx + HALF_SIZE - 0.5)
	var z := int(wz + HALF_SIZE - 0.5)
	if x < 0 or z < 0 or x >= WORLD_SIZE or z >= WORLD_SIZE:
		return
	var h := _column_height(x, z)
	if h < 1.0 or h > 4.0:
		return
	_spawn_rock(_world_coord(x), _world_coord(z), h)


func _try_flower_at(wx: float, wz: float) -> void:
	var x := int(wx + HALF_SIZE - 0.5)
	var z := int(wz + HALF_SIZE - 0.5)
	if x < 0 or z < 0 or x >= WORLD_SIZE or z >= WORLD_SIZE:
		return
	var h := _column_height(x, z)
	if h < 1.0 or h > 3.0:
		return
	_spawn_flower(_world_coord(x), _world_coord(z), h)


func _spawn_tree(wx: float, wz: float, h: float) -> void:
	var s := rng.randf_range(0.85, 1.25)
	var root := Node3D.new()
	root.position = Vector3(wx, h, wz)
	root.rotation.y = rng.randf() * TAU
	root.scale = Vector3(s, s, s)
	add_child(root)

	_add_box(root, Vector3(0.46, 1.9, 0.46), Vector3(0.0, 0.95, 0.0), trunk_material)
	var leaves: StandardMaterial3D = leaf_materials[rng.randi_range(0, leaf_materials.size() - 1)]
	_add_box(root, Vector3(2.1, 0.9, 2.1), Vector3(0.0, 2.2, 0.0), leaves)
	_add_box(root, Vector3(1.6, 0.9, 1.6), Vector3(0.18, 2.9, -0.12), leaves)
	_add_box(root, Vector3(1.0, 0.8, 1.0), Vector3(-0.12, 3.5, 0.14), leaves)

	_add_static_box(Vector3(0.46 * s, 1.9 * s, 0.46 * s),
		Transform3D(Basis.IDENTITY, Vector3(wx, h + 0.95 * s, wz)))


func _spawn_rock(wx: float, wz: float, h: float) -> void:
	var size := Vector3(
		rng.randf_range(0.5, 1.1),
		rng.randf_range(0.4, 0.9),
		rng.randf_range(0.5, 1.1))
	var rot := Vector3(rng.randf_range(-0.2, 0.2), rng.randf() * TAU, rng.randf_range(-0.2, 0.2))
	var root := Node3D.new()
	root.position = Vector3(wx, h, wz)
	root.rotation = rot
	add_child(root)
	_add_box(root, size, Vector3(0.0, size.y * 0.35, 0.0), rock_material)
	_add_static_box(size, Transform3D(Basis.from_euler(rot), Vector3(wx, h + size.y * 0.35, wz)))


func _spawn_flower(wx: float, wz: float, h: float) -> void:
	var root := Node3D.new()
	root.position = Vector3(wx, h, wz)
	add_child(root)
	_add_box(root, Vector3(0.06, 0.28, 0.06), Vector3(0.0, 0.14, 0.0), stem_material)
	var mat: StandardMaterial3D = flower_materials[rng.randi_range(0, flower_materials.size() - 1)]
	_add_box(root, Vector3(0.18, 0.18, 0.18), Vector3(0.0, 0.34, 0.0), mat)


# ---------------------------------------------------------------------------
# Clouds
# ---------------------------------------------------------------------------

func _build_clouds() -> void:
	var cloud_mat := _make_material(Color(1.0, 1.0, 1.0), true)
	for i in 7:
		var root := Node3D.new()
		root.position = Vector3(
			rng.randf_range(-45.0, 45.0),
			rng.randf_range(24.0, 32.0),
			rng.randf_range(-45.0, 45.0))
		add_child(root)
		var base := rng.randf_range(2.0, 3.5)
		for j in rng.randi_range(3, 5):
			var mi := _add_box(root,
				Vector3(
					base * rng.randf_range(0.8, 1.6),
					rng.randf_range(0.5, 0.9),
					base * rng.randf_range(0.7, 1.3)),
				Vector3(
					rng.randf_range(-1.5, 1.5) * base * 0.4,
					rng.randf_range(-0.2, 0.3),
					rng.randf_range(-1.0, 1.0) * base * 0.3),
				cloud_mat)
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		clouds.append(root)
		cloud_speeds.append(rng.randf_range(0.3, 0.9))


# ---------------------------------------------------------------------------
# Player, camera, HUD
# ---------------------------------------------------------------------------

func _build_player() -> void:
	player = PLAYER_SCRIPT.new()
	player.position = Vector3(0.0, SPAWN_HEIGHT + 0.15, 0.0)
	add_child(player)


func _build_camera() -> void:
	camera_rig = Node3D.new()
	add_child(camera_rig)

	spring_arm = SpringArm3D.new()
	spring_arm.spring_length = 7.5
	spring_arm.margin = 0.3
	spring_arm.collision_mask = 1
	spring_arm.rotation.x = pitch
	spring_arm.add_excluded_object(player.get_rid())
	camera_rig.add_child(spring_arm)

	var cam := Camera3D.new()
	cam.fov = 72.0
	cam.current = true
	spring_arm.add_child(cam)

	camera_rig.position = player.global_position + Vector3(0.0, 1.35, 0.0)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	var panel := PanelContainer.new()
	panel.position = Vector2(16.0, 16.0)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.07, 0.1, 0.72)
	style.set_corner_radius_all(10)
	style.set_content_margin_all(14.0)
	panel.add_theme_stylebox_override("panel", style)
	layer.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "VOXEL RUNNER"
	title.add_theme_font_size_override("font_size", 22)
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.4))
	vbox.add_child(title)

	hud_score = Label.new()
	hud_score.text = "Coins   0 / %d" % TOTAL_COINS
	hud_score.add_theme_font_size_override("font_size", 18)
	hud_score.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0))
	vbox.add_child(hud_score)

	var help := Label.new()
	help.text = "WASD  move      Shift  sprint\nSpace  jump     Mouse / Q E  camera\nLeft-click grabs the mouse, Esc releases it"
	help.add_theme_font_size_override("font_size", 15)
	help.add_theme_color_override("font_color", Color(0.85, 0.9, 0.95))
	vbox.add_child(help)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(center)

	hud_message = Label.new()
	hud_message.add_theme_font_size_override("font_size", 32)
	hud_message.add_theme_color_override("font_color", Color(1.0, 0.9, 0.45))
	hud_message.add_theme_color_override("font_outline_color", Color(0.05, 0.05, 0.08))
	hud_message.add_theme_constant_override("outline_size", 8)
	hud_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center.add_child(hud_message)


# ---------------------------------------------------------------------------
# Coins & pickups
# ---------------------------------------------------------------------------

func _spawn_coins(count: int) -> void:
	if count <= 0:
		return
	# Seed one coin near the spawn point when possible, then fill the rest at random.
	var before := active_coins.size()
	_try_coin_at(-0.5, -5.5)
	var seeded := active_coins.size() - before
	for i in count - seeded:
		_spawn_one_coin()


func _try_coin_at(wx: float, wz: float) -> void:
	var x := int(wx + HALF_SIZE - 0.5)
	var z := int(wz + HALF_SIZE - 0.5)
	if x < 0 or z < 0 or x >= WORLD_SIZE or z >= WORLD_SIZE:
		return
	var h := _column_height(x, z)
	if h < 0.5:
		return
	var pos := Vector3(wx, h + 0.85, wz)
	if player and pos.distance_to(player.global_position) < 3.0:
		return
	var coin: Area3D = COIN_SCRIPT.new()
	coin.position = pos
	add_child(coin)
	coin.body_entered.connect(_on_coin_collected.bind(coin))
	active_coins.append(coin)


func _spawn_one_coin() -> void:
	for attempt in 90:
		var x := rng.randi_range(0, WORLD_SIZE - 1)
		var z := rng.randi_range(0, WORLD_SIZE - 1)
		var h := _column_height(x, z)
		if h < 0.5:
			continue
		var wx := _world_coord(x)
		var wz := _world_coord(z)
		if absf(wx) > HALF_SIZE - 4.0 or absf(wz) > HALF_SIZE - 4.0:
			continue
		var pos := Vector3(wx, h + 0.85, wz)
		if player and pos.distance_to(player.global_position) < 5.0:
			continue
		var too_close := false
		for c in active_coins:
			if is_instance_valid(c) and pos.distance_to(c.global_position) < 3.0:
				too_close = true
				break
		if too_close:
			continue

		var coin: Area3D = COIN_SCRIPT.new()
		coin.position = pos
		add_child(coin)
		coin.body_entered.connect(_on_coin_collected.bind(coin))
		active_coins.append(coin)
		return


func _update_score() -> void:
	hud_score.text = "Coins   %d / %d" % [score, TOTAL_COINS]


func _on_coin_collected(_body: Node3D, coin: Area3D) -> void:
	if not is_instance_valid(coin):
		return
	var pos := coin.global_position
	active_coins.erase(coin)
	coin.queue_free()
	score += 1
	_update_score()
	_spawn_burst(pos)
	if score >= TOTAL_COINS:
		hud_message.text = "All %d coins collected!" % TOTAL_COINS
		await get_tree().create_timer(2.5).timeout
		if not is_inside_tree():
			return
		hud_message.text = ""
		score = 0
		_update_score()
		_spawn_coins(TOTAL_COINS)


func _spawn_burst(pos: Vector3) -> void:
	var particles := CPUParticles3D.new()
	particles.amount = 22
	particles.lifetime = 0.7
	particles.one_shot = true
	particles.explosiveness = 1.0
	particles.direction = Vector3.UP
	particles.spread = 180.0
	particles.initial_velocity_min = 2.0
	particles.initial_velocity_max = 4.5
	particles.gravity = Vector3(0.0, -9.0, 0.0)
	particles.scale_amount_min = 0.06
	particles.scale_amount_max = 0.16
	particles.color = Color(1.0, 0.82, 0.25)

	var bm := BoxMesh.new()
	bm.size = Vector3.ONE
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bm.material = mat
	particles.mesh = bm

	particles.position = pos
	particles.local_coords = false
	add_child(particles)
	particles.emitting = true
	get_tree().create_timer(1.2).timeout.connect(particles.queue_free)


# ---------------------------------------------------------------------------
# Frame update
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	if player and is_instance_valid(player):
		var look := Input.get_axis("cam_right", "cam_left")
		if absf(look) > 0.01:
			yaw += look * 2.1 * delta
		player.camera_yaw = yaw
		camera_rig.rotation.y = yaw
		spring_arm.rotation.x = pitch

		var target: Vector3 = player.global_position + Vector3(0.0, 1.35, 0.0)
		camera_rig.position = camera_rig.position.lerp(target, 1.0 - exp(-12.0 * delta))

		if player.global_position.y < -20.0:
			player.reset_to_spawn()

	for i in clouds.size():
		var cloud: Node3D = clouds[i]
		cloud.position.x += cloud_speeds[i] * delta
		if cloud.position.x > HALF_SIZE + 12.0:
			cloud.position.x = -HALF_SIZE - 12.0
