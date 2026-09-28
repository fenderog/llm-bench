extends Node3D
## Builds the small voxel sandbox: ground, fence, crates, platform, trees, coins, pads, clouds.

const CoinScript := preload("res://scripts/coin.gd")
const PadScript := preload("res://scripts/bounce_pad.gd")

const HALF := 12.0  # Sandbox half-extent; fence sits at +/- HALF.

var _mats := {}
var clouds: Array[Node3D] = []
var coin_positions: Array[Vector3] = []

var _rng := RandomNumberGenerator.new()


func build() -> void:
	_rng.seed = 12345
	_build_ground()
	_build_fence()
	_build_crates()
	_build_platform_with_steps()
	_build_trees()
	_build_lamps()
	_build_details()
	_build_coins()
	_build_pads()
	_build_clouds()


func _process(delta: float) -> void:
	for c in clouds:
		if is_instance_valid(c):
			c.position.x += delta * 0.6
			if c.position.x > 22.0:
				c.position.x = -22.0


# --- materials / helpers -------------------------------------------------

func mat(color: Color) -> StandardMaterial3D:
	var key := color.to_html()
	if _mats.has(key):
		return _mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.9
	_mats[key] = m
	return m


func visual_box(parent: Node3D, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh.material = mat(color)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.position = pos
	parent.add_child(mi)
	return mi


func solid_box(pos: Vector3, size: Vector3, color: Color, parent: Node3D = self) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.collision_layer = 1
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = size
	shape.shape = box_shape
	body.add_child(shape)
	parent.add_child(body)
	visual_box(body, Vector3.ZERO, size, color)
	return body


# --- builders ------------------------------------------------------------

func _build_ground() -> void:
	# Thick dirt slab with grass top.
	solid_box(Vector3(0, -0.55, 0), Vector3(27, 1.1, 27), Color(0.45, 0.3, 0.18))
	visual_box(self, Vector3(0, -0.02, 0), Vector3(27, 0.06, 27), Color(0.35, 0.68, 0.3))

	# Voxel checker tiles (visual only).
	var tile := 2.0
	var n := 6
	var c_a := Color(0.36, 0.7, 0.31)
	var c_b := Color(0.33, 0.65, 0.29)
	for ix in range(-n, n + 1):
		for iz in range(-n, n + 1):
			var x := float(ix) * tile
			var z := float(iz) * tile
			if absf(x) > HALF + 1.0 or absf(z) > HALF + 1.0:
				continue
			var c := c_a if (ix + iz) % 2 == 0 else c_b
			visual_box(self, Vector3(x, 0.015, z), Vector3(tile - 0.06, 0.05, tile - 0.06), c)

	# Stone rim around the sandbox.
	var rim := Color(0.55, 0.56, 0.6)
	solid_box(Vector3(0, 0.25, HALF + 1.6), Vector3(28.5, 0.5, 1.2), rim)
	solid_box(Vector3(0, 0.25, -HALF - 1.6), Vector3(28.5, 0.5, 1.2), rim)
	solid_box(Vector3(HALF + 1.6, 0.25, 0), Vector3(1.2, 0.5, 28.5), rim)
	solid_box(Vector3(-HALF - 1.6, 0.25, 0), Vector3(1.2, 0.5, 28.5), rim)


func _build_fence() -> void:
	var post := Color(0.5, 0.34, 0.2)
	var rail := Color(0.58, 0.4, 0.24)
	var h := HALF
	# Posts.
	var x := -h
	while x <= h + 0.01:
		for z in [-h, h]:
			solid_box(Vector3(x, 0.6, z), Vector3(0.3, 1.2, 0.3), post)
		x += 2.0
	var z := -h
	while z <= h + 0.01:
		for xx in [-h, h]:
			solid_box(Vector3(xx, 0.6, z), Vector3(0.3, 1.2, 0.3), post)
		z += 2.0
	# Rails (long thin boxes).
	solid_box(Vector3(0, 1.0, h), Vector3(h * 2.0, 0.15, 0.15), rail)
	solid_box(Vector3(0, 0.55, h), Vector3(h * 2.0, 0.15, 0.15), rail)
	solid_box(Vector3(0, 1.0, -h), Vector3(h * 2.0, 0.15, 0.15), rail)
	solid_box(Vector3(0, 0.55, -h), Vector3(h * 2.0, 0.15, 0.15), rail)
	solid_box(Vector3(h, 1.0, 0), Vector3(0.15, 0.15, h * 2.0), rail)
	solid_box(Vector3(h, 0.55, 0), Vector3(0.15, 0.15, h * 2.0), rail)
	solid_box(Vector3(-h, 1.0, 0), Vector3(0.15, 0.15, h * 2.0), rail)
	solid_box(Vector3(-h, 0.55, 0), Vector3(0.15, 0.15, h * 2.0), rail)


func _build_crates() -> void:
	var wood := Color(0.72, 0.52, 0.3)
	var wood_dark := Color(0.6, 0.42, 0.24)
	_add_crate(Vector3(-6, 0.5, -4), 1.0, wood, wood_dark)
	_add_crate(Vector3(-5, 0.5, -4), 1.0, wood, wood_dark)
	_add_crate(Vector3(-5.5, 1.5, -4), 1.0, wood, wood_dark)
	_add_crate(Vector3(6.5, 0.5, 3.5), 1.0, wood, wood_dark)
	_add_crate(Vector3(6.5, 1.5, 3.5), 1.0, wood, wood_dark)
	_add_crate(Vector3(2.5, 0.4, -7.5), 0.8, wood, wood_dark)
	_add_crate(Vector3(-2.0, 0.6, 6.5), 1.2, wood, wood_dark)
	# Big block staircase toy.
	_add_crate(Vector3(8.5, 0.4, -6.5), 0.8, Color(0.85, 0.4, 0.35), wood_dark)
	_add_crate(Vector3(8.5, 1.2, -6.5), 0.8, Color(0.35, 0.6, 0.85), wood_dark)


func _add_crate(pos: Vector3, size: float, color: Color, trim: Color) -> void:
	var body := solid_box(pos, Vector3(size, size, size), color)
	visual_box(body, Vector3.ZERO, Vector3(size + 0.04, size * 0.18, size + 0.04), trim)


func _build_platform_with_steps() -> void:
	var top := Color(0.62, 0.6, 0.66)
	var side := Color(0.5, 0.48, 0.55)
	# Raised lookout platform in the back-left corner.
	solid_box(Vector3(-8, 1.0, 7.5), Vector3(6, 2.0, 5), side)
	visual_box(self, Vector3(-8, 2.02, 7.5), Vector3(6.1, 0.08, 5.1), top)
	# Steps up to it (each a solid box).
	solid_box(Vector3(-4.2, 0.25, 7.5), Vector3(1.4, 0.5, 2.0), top)
	solid_box(Vector3(-2.9, 0.75, 7.5), Vector3(1.2, 1.5, 2.0), side)
	visual_box(self, Vector3(-2.9, 1.52, 7.5), Vector3(1.25, 0.06, 2.05), top)
	# Flag on the platform.
	var pole := MeshInstance3D.new()
	var pole_mesh := BoxMesh.new()
	pole_mesh.size = Vector3(0.15, 3.0, 0.15)
	pole_mesh.material = mat(Color(0.3, 0.3, 0.35))
	pole.mesh = pole_mesh
	pole.position = Vector3(-9.5, 3.5, 8.5)
	add_child(pole)
	visual_box(self, Vector3(-8.9, 4.6, 8.5), Vector3(1.1, 0.7, 0.1), Color(0.9, 0.25, 0.3))
	coin_positions.append(Vector3(-8, 3.0, 7.0))


func _build_trees() -> void:
	_add_tree(Vector3(9, 0, 7.5))
	_add_tree(Vector3(-9.5, 0, -8))
	_add_tree(Vector3(4, 0, 8.8))
	_add_tree(Vector3(-3.5, 0, -8.5))


func _add_tree(pos: Vector3) -> void:
	var trunk := Color(0.45, 0.3, 0.18)
	var leaf := Color(0.25, 0.55, 0.28)
	var leaf2 := Color(0.3, 0.62, 0.32)
	solid_box(pos + Vector3(0, 0.9, 0), Vector3(0.6, 1.8, 0.6), trunk)
	# Leafy voxel blob (visual only).
	visual_box(self, pos + Vector3(0, 2.3, 0), Vector3(2.0, 1.0, 2.0), leaf)
	visual_box(self, pos + Vector3(0, 3.0, 0), Vector3(1.4, 0.8, 1.4), leaf2)
	visual_box(self, pos + Vector3(0.5, 2.0, 0.4), Vector3(0.9, 0.7, 0.9), leaf2)
	visual_box(self, pos + Vector3(-0.5, 2.0, -0.3), Vector3(0.8, 0.6, 0.8), leaf)


func _build_lamps() -> void:
	for pos in [Vector3(0, 0, -10), Vector3(10, 0, 0), Vector3(-10, 0, 0.5)]:
		solid_box(pos + Vector3(0, 1.25, 0), Vector3(0.25, 2.5, 0.25), Color(0.2, 0.2, 0.24))
		var bulb_holder := MeshInstance3D.new()
		var bulb_mesh := BoxMesh.new()
		bulb_mesh.size = Vector3(0.55, 0.45, 0.55)
		var bm := StandardMaterial3D.new()
		bm.albedo_color = Color(1.0, 0.9, 0.6)
		bm.emission_enabled = true
		bm.emission = Color(1.0, 0.85, 0.5)
		bm.emission_energy_multiplier = 1.2
		bulb_mesh.material = bm
		bulb_holder.mesh = bulb_mesh
		bulb_holder.position = pos + Vector3(0, 2.6, 0)
		add_child(bulb_holder)


func _build_details() -> void:
	# Flowers, rocks, grass tufts (visual only voxels).
	var flowers := [Color(0.95, 0.35, 0.5), Color(0.95, 0.85, 0.3), Color(0.7, 0.4, 0.9)]
	for i in 24:
		var x := _rng.randf_range(-11.0, 11.0)
		var z := _rng.randf_range(-11.0, 11.0)
		if Vector2(x, z).length() < 2.0:
			continue
		var pick := _rng.randi_range(0, 2)
		visual_box(self, Vector3(x, 0.12, z), Vector3(0.12, 0.24, 0.12), Color(0.3, 0.6, 0.3))
		visual_box(self, Vector3(x, 0.3, z), Vector3(0.28, 0.2, 0.28), flowers[pick])
	for i in 10:
		var x := _rng.randf_range(-11.0, 11.0)
		var z := _rng.randf_range(-11.0, 11.0)
		visual_box(self, Vector3(x, 0.1, z), Vector3(0.5, 0.2, 0.4), Color(0.6, 0.61, 0.64))


func _build_coins() -> void:
	var spots := [
		Vector3(0, 1.0, 0), Vector3(1.5, 1.0, 0), Vector3(-1.5, 1.0, 0),
		Vector3(-5.5, 2.4, -4), Vector3(6.5, 2.6, 3.5),
		Vector3(2.5, 1.2, -7.5), Vector3(-2.0, 1.6, 6.5),
		Vector3(9, 1.0, -3), Vector3(-9, 1.0, 3),
		Vector3(0, 1.0, -9), Vector3(4, 1.0, 5),
	]
	spots.append_array(coin_positions)
	for p in spots:
		var coin := Area3D.new()
		coin.set_script(CoinScript)
		coin.position = p
		add_child(coin)


func _build_pads() -> void:
	for data in [[Vector3(0, 0, 9), 13.0], [Vector3(9.5, 0, -8.5), 15.0]]:
		var pad := Area3D.new()
		pad.set_script(PadScript)
		pad.position = data[0]
		pad.set("power", data[1])
		add_child(pad)


func _build_clouds() -> void:
	var white := Color(0.96, 0.97, 1.0)
	for i in 6:
		var cloud := Node3D.new()
		cloud.position = Vector3(_rng.randf_range(-20, 20), _rng.randf_range(9, 14), _rng.randf_range(-18, 18))
		add_child(cloud)
		visual_box(cloud, Vector3(0, 0, 0), Vector3(2.6, 0.9, 1.6), white)
		visual_box(cloud, Vector3(1.2, -0.2, 0.3), Vector3(1.6, 0.7, 1.2), white)
		visual_box(cloud, Vector3(-1.2, -0.15, -0.2), Vector3(1.4, 0.6, 1.1), white)
		clouds.append(cloud)
