extends Node3D
## World setup: sky, sun, voxel scenery, collectible carrots, camera and HUD.

const HorseScript := preload("res://voxel_horse.gd")
const CARROT_COUNT := 8
const PICKUP_RADIUS := 1.6
const WORLD_HALF_SIZE := 140.0
const TREE_COUNT := 70
const TUFT_COUNT := 1500
const SCENERY_VOX := 0.5  # size of one tree voxel

var horse
var camera: Camera3D
var carrots: Array[Node3D] = []
var score := 0

var _hud_label: Label
var _time := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 2026
	_build_environment()
	_build_ground()
	_build_scenery()

	horse = HorseScript.new()
	add_child(horse)

	for i in CARROT_COUNT:
		var carrot := _make_carrot()
		add_child(carrot)
		_respawn_carrot(carrot)
		carrots.append(carrot)

	camera = Camera3D.new()
	camera.fov = 70.0
	add_child(camera)
	camera.position = Vector3(0.0, 3.0, 7.0)

	_build_hud()


func _process(delta: float) -> void:
	_time += delta
	_update_carrots()
	_update_camera(delta)
	_hud_label.text = "Carrots: %d    Speed: %.1f" % [score, horse.speed]


func _build_environment() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.3, 0.55, 0.9)
	sky_material.sky_horizon_color = Color(0.75, 0.85, 0.95)
	sky_material.ground_horizon_color = Color(0.75, 0.85, 0.95)
	sky_material.ground_bottom_color = Color(0.2, 0.35, 0.15)

	var sky := Sky.new()
	sky.sky_material = sky_material

	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.7

	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	add_child(world_environment)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, -35.0, 0.0)
	sun.shadow_enabled = true
	add_child(sun)


func _build_ground() -> void:
	var plane := PlaneMesh.new()
	plane.size = Vector2(300.0, 300.0)
	plane.material = _solid(Color(0.3, 0.58, 0.25))
	var ground := MeshInstance3D.new()
	ground.mesh = plane
	add_child(ground)


## Trees and grass tufts are batched into a single MultiMesh for performance.
func _build_scenery() -> void:
	var cubes: Array = []  # entries of [Transform3D, Color]
	var trunk := Color(0.42, 0.26, 0.13)
	var leaves := [Color(0.18, 0.46, 0.2), Color(0.24, 0.55, 0.22)]

	for i in TREE_COUNT:
		var base := Vector3(
			_rng.randf_range(-WORLD_HALF_SIZE, WORLD_HALF_SIZE),
			0.0,
			_rng.randf_range(-WORLD_HALF_SIZE, WORLD_HALF_SIZE))
		if absf(base.x) < 8.0 and absf(base.z) < 8.0:
			continue  # keep the start area clear
		for y in 4:
			_add_cube(cubes, base + Vector3(0.0, (y + 0.5) * SCENERY_VOX, 0.0), trunk)
		for y in range(4, 7):
			var radius := 2 if y == 5 else 1
			for dx in range(-radius, radius + 1):
				for dz in range(-radius, radius + 1):
					var pos := base + Vector3(dx, y + 0.5, dz) * SCENERY_VOX
					_add_cube(cubes, pos, leaves[_rng.randi_range(0, 1)])

	for i in TUFT_COUNT:
		var pos := Vector3(
			_rng.randf_range(-WORLD_HALF_SIZE, WORLD_HALF_SIZE),
			0.05,
			_rng.randf_range(-WORLD_HALF_SIZE, WORLD_HALF_SIZE))
		_add_cube(cubes, pos, leaves[_rng.randi_range(0, 1)].darkened(_rng.randf_range(0.0, 0.2)), 0.12)

	_add_multimesh(cubes)


func _add_cube(cubes: Array, pos: Vector3, color: Color, size: float = SCENERY_VOX) -> void:
	var basis := Basis.from_scale(Vector3.ONE * size * 0.95)
	cubes.append([Transform3D(basis, pos), color])


func _add_multimesh(cubes: Array) -> void:
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.9
	mesh.material = mat

	var multimesh := MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.mesh = mesh
	multimesh.instance_count = cubes.size()
	for i in cubes.size():
		multimesh.set_instance_transform(i, cubes[i][0])
		multimesh.set_instance_color(i, cubes[i][1])

	var node := MultiMeshInstance3D.new()
	node.multimesh = multimesh
	add_child(node)


func _make_carrot() -> Node3D:
	var carrot := Node3D.new()
	carrot.set_meta("bob_phase", _rng.randf() * TAU)

	var root := MeshInstance3D.new()
	var root_box := BoxMesh.new()
	root_box.size = Vector3(0.22, 0.22, 0.6)
	root.mesh = root_box
	root.material_override = _solid(Color(1.0, 0.5, 0.1))
	carrot.add_child(root)

	var leaf := MeshInstance3D.new()
	var leaf_box := BoxMesh.new()
	leaf_box.size = Vector3(0.2, 0.3, 0.2)
	leaf.mesh = leaf_box
	leaf.material_override = _solid(Color(0.2, 0.7, 0.2))
	leaf.position = Vector3(0.0, 0.2, 0.4)
	carrot.add_child(leaf)
	return carrot


func _respawn_carrot(carrot: Node3D) -> void:
	var angle := _rng.randf() * TAU
	var dist := _rng.randf_range(12.0, 30.0)
	var center: Vector3 = horse.position
	var x := clampf(center.x + cos(angle) * dist, -WORLD_HALF_SIZE, WORLD_HALF_SIZE)
	var z := clampf(center.z + sin(angle) * dist, -WORLD_HALF_SIZE, WORLD_HALF_SIZE)
	carrot.position = Vector3(x, 0.6, z)
	carrot.rotation.y = _rng.randf() * TAU


func _update_carrots() -> void:
	for carrot in carrots:
		# Gentle bob so the pickups are easy to spot
		var phase: float = carrot.get_meta("bob_phase")
		carrot.position.y = 0.6 + sin(_time * 3.0 + phase) * 0.1
		carrot.rotation.y += 0.02

		var offset: Vector3 = horse.position - carrot.position
		offset.y = 0.0
		if offset.length() < PICKUP_RADIUS:
			score += 1
			_respawn_carrot(carrot)


func _update_camera(delta: float) -> void:
	# Local +Z points behind the horse, so the camera trails it and lags on turns
	var behind: Vector3 = horse.transform.basis.z
	var target: Vector3 = horse.position + behind * 7.0 + Vector3.UP * 3.0
	camera.position = camera.position.lerp(target, 1.0 - exp(-6.0 * delta))
	camera.look_at(horse.position + Vector3.UP * 1.2, Vector3.UP)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_hud_label = Label.new()
	_hud_label.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	_hud_label.position = Vector2(16.0, 12.0)
	_hud_label.add_theme_font_size_override("font_size", 24)
	_hud_label.add_theme_color_override("font_outline_color", Color.BLACK)
	_hud_label.add_theme_constant_override("outline_size", 6)
	layer.add_child(_hud_label)

	var help := Label.new()
	help.text = "W/Up: gallop   S/Down: brake   A/D or Left/Right: steer   Space: jump"
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	help.position.y -= 36.0
	help.position.x = 16.0
	help.add_theme_font_size_override("font_size", 18)
	help.add_theme_color_override("font_outline_color", Color.BLACK)
	help.add_theme_constant_override("outline_size", 5)
	layer.add_child(help)


func _solid(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	return mat
