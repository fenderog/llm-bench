extends Node3D
## Builds a small voxel sandbox procedurally: ground, fence, trees, rocks,
## crates, steps, coins to collect, and a HUD label.

var coins := 0
var total_coins := 6
var hud: Label
var player_scene := preload("res://player.tscn")

func _ready() -> void:
	_build_lighting()
	_build_ground()
	_build_fence(11.0)
	_build_trees()
	_build_rocks_and_crates()
	_build_steps()
	_build_coins()
	var player: CharacterBody3D = player_scene.instantiate()
	player.position = Vector3(0, 1.0, 6.0)
	add_child(player)
	_build_hud()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _process(_delta: float) -> void:
	for c in get_children():
		if c.is_in_group("coin"):
			c.rotate_y(0.03)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

# --- helpers ---

func _mat(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.95
	return m

func _cube(size: Vector3, color: Color, pos: Vector3, solid: bool = false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(color)
	mi.position = pos
	add_child(mi)
	if solid:
		var body := StaticBody3D.new()
		body.position = pos
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		cs.shape = shape
		body.add_child(cs)
		add_child(body)
	return mi

# --- pieces ---

func _build_lighting() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.35, 0.55, 0.8)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.7, 0.75, 0.85)
	e.ambient_light_energy = 0.9
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-0.9, 0.6, 0)
	sun.shadow_enabled = true
	add_child(sun)

func _build_ground() -> void:
	var body := StaticBody3D.new()
	add_child(body)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(24, 1, 24)
	cs.shape = shape
	cs.position = Vector3(0, -0.5, 0)
	body.add_child(cs)
	# Checkerboard voxel tiles (flat boxes, no collision needed)
	var c1 := Color("62b34e")
	var c2 := Color("55a346")
	for x in range(-11, 11):
		for z in range(-11, 11):
			var mi := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(1, 0.1, 1)
			mi.mesh = bm
			mi.material_override = _mat(c1 if (x + z) % 2 == 0 else c2)
			mi.position = Vector3(x + 0.5, -0.05, z + 0.5)
			add_child(mi)

func _build_fence(half: float) -> void:
	var wood := Color("9a6a3b")
	for i in range(-10, 11, 2):
		_cube(Vector3(0.3, 1.2, 0.3), wood, Vector3(i, 0.6, -half), true)
		_cube(Vector3(0.3, 1.2, 0.3), wood, Vector3(i, 0.6, half), true)
		_cube(Vector3(0.3, 1.2, 0.3), wood, Vector3(-half, 0.6, i), true)
		_cube(Vector3(0.3, 1.2, 0.3), wood, Vector3(half, 0.6, i), true)
	for z in [-half, half]:
		_cube(Vector3(22, 0.18, 0.12), wood, Vector3(0, 1.0, z), false)
	for x in [-half, half]:
		_cube(Vector3(0.12, 0.18, 22), wood, Vector3(x, 1.0, 0), false)

func _tree(pos: Vector3) -> void:
	_cube(Vector3(0.6, 1.6, 0.6), Color("7a5230"), pos + Vector3(0, 0.8, 0), true)
	_cube(Vector3(2.0, 1.2, 2.0), Color("2e8b3a"), pos + Vector3(0, 2.2, 0), false)
	_cube(Vector3(1.3, 0.9, 1.3), Color("37a144"), pos + Vector3(0, 3.1, 0), false)

func _build_trees() -> void:
	_tree(Vector3(-7, 0, -6))
	_tree(Vector3(7.5, 0, -4))
	_tree(Vector3(-8, 0, 5))
	_tree(Vector3(6, 0, 7))

func _build_rocks_and_crates() -> void:
	_cube(Vector3(0.9, 0.6, 0.8), Color("8d8d99"), Vector3(3, 0.3, -1), true)
	_cube(Vector3(0.6, 0.45, 0.6), Color("a3a3ae"), Vector3(3.8, 0.22, -0.4), true)
	_cube(Vector3(1.0, 1.0, 1.0), Color("c98f4e"), Vector3(-3.5, 0.5, -2.5), true)
	_cube(Vector3(0.8, 0.8, 0.8), Color("c98f4e"), Vector3(-3.4, 1.4, -2.4), true)
	_cube(Vector3(1.2, 0.5, 2.0), Color("7c5a36"), Vector3(0, 0.25, -8), true)

func _build_steps() -> void:
	# Small climbable platform pyramid
	_cube(Vector3(3.0, 0.5, 3.0), Color("b0874f"), Vector3(-4, 0.25, 3.5), true)
	_cube(Vector3(2.0, 0.5, 2.0), Color("bd9260"), Vector3(-4, 0.75, 3.5), true)
	_cube(Vector3(1.0, 0.5, 1.0), Color("c9a06c"), Vector3(-4, 1.25, 3.5), true)

func _build_coins() -> void:
	var spots := [Vector3(0, 1, 0), Vector3(5, 1, 2), Vector3(-6, 1, -3),
		Vector3(2, 1, -7), Vector3(-4, 2.2, 3.5), Vector3(-8, 1, 0)]
	for s in spots:
		var area := Area3D.new()
		area.position = s
		area.add_to_group("coin")
		var cs := CollisionShape3D.new()
		var sph := SphereShape3D.new()
		sph.radius = 0.8
		cs.shape = sph
		area.add_child(cs)
		var mi := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.35
		cyl.bottom_radius = 0.35
		cyl.height = 0.12
		mi.mesh = cyl
		var gold := StandardMaterial3D.new()
		gold.albedo_color = Color("ffd23f")
		gold.metallic = 0.7
		gold.roughness = 0.3
		gold.emission_enabled = true
		gold.emission = Color("ffd23f")
		gold.emission_energy_multiplier = 0.4
		mi.material_override = gold
		mi.rotation.z = PI / 2.0
		area.add_child(mi)
		area.body_entered.connect(_on_coin.bind(area))
		add_child(area)

func _on_coin(body: Node3D, area: Area3D) -> void:
	if body is CharacterBody3D and is_instance_valid(area):
		area.queue_free()
		coins += 1
		_update_hud()

func _build_hud() -> void:
	hud = Label.new()
	hud.add_theme_font_size_override("font_size", 22)
	hud.add_theme_color_override("font_color", Color.WHITE)
	hud.add_theme_color_override("font_shadow_color", Color.BLACK)
	hud.add_theme_constant_override("shadow_offset_x", 2)
	hud.add_theme_constant_override("shadow_offset_y", 2)
	hud.position = Vector2(16, 12)
	var layer := CanvasLayer.new()
	add_child(layer)
	layer.add_child(hud)
	var help := Label.new()
	help.text = "Click to capture mouse | WASD move | Space jump | Shift sprint | Esc release"
	help.add_theme_font_size_override("font_size", 15)
	help.add_theme_color_override("font_color", Color.WHITE)
	help.add_theme_color_override("font_shadow_color", Color.BLACK)
	help.add_theme_constant_override("shadow_offset_x", 2)
	help.add_theme_constant_override("shadow_offset_y", 2)
	help.position = Vector2(16, 580)
	hud.get_parent().add_child(help)
	_update_hud()

func _update_hud() -> void:
	if hud:
		hud.text = "Coins: %d / %d" % [coins, total_coins]
		if coins >= total_coins:
			hud.text += "  - All collected!"
