extends Node3D
## Builds the whole voxel sandbox procedurally (no assets):
## ground tiles, fence, trees, rocks, crates, coins, grass, flowers,
## drifting clouds and distant scenery. Uses MultiMesh for repeated bits
## so the web export stays fast.

const CoinScene := preload("res://scripts/coin.gd")

const HALF := 12.0

const TREE_POS := [
	Vector3(-8.5, 0, -7.5),
	Vector3(8.0, 0, -8.0),
	Vector3(-9.0, 0, 3.5),
	Vector3(8.5, 0, 5.5),
	Vector3(3.5, 0, -6.5),
	Vector3(-3.0, 0, 8.5),
]

const ROCK_DATA := [
	[Vector3(5.0, 0, 0.5), 0.7],
	[Vector3(-5.5, 0, 7.0), 0.9],
	[Vector3(2.0, 0, -9.0), 0.55],
	[Vector3(9.0, 0, -1.0), 0.8],
	[Vector3(-2.5, 0, -4.5), 0.5],
]

const COIN_POS := [
	Vector3(-4, 0.8, 0),
	Vector3(4, 0.8, 0),
	Vector3(0, 0.8, -4),
	Vector3(-8, 0.8, -3),
	Vector3(8, 0.8, -2),
	Vector3(-8, 0.8, 8),
	Vector3(8, 0.8, 7),
	Vector3(3, 0.8, -8.5),
	Vector3(-3, 0.8, -8.5),
	Vector3(-2, 2.7, 2),
	Vector3(6.5, 1.8, -4.5),
	Vector3(1.5, 1.8, 8),
]

var mats: Dictionary = {}
var rng := RandomNumberGenerator.new()
var clouds: Array = [] # Dictionaries: { "node": Node3D, "speed": float }


func _ready() -> void:
	rng.seed = 20260927
	_build_ground()
	_build_fence()
	_build_trees()
	_build_rocks()
	_build_crates()
	_build_coins()
	_build_grass_and_flowers()
	_build_clouds()
	_build_outer_scenery()


func _process(delta: float) -> void:
	for c in clouds:
		var d := c as Dictionary
		var n := d["node"] as Node3D
		n.position.x += float(d["speed"]) * delta
		if n.position.x > 26.0:
			n.position.x = -26.0


func mat(key: String, color: Color, rough := 0.9) -> StandardMaterial3D:
	if mats.has(key):
		return mats[key] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	mats[key] = m
	return m


func vbox(parent: Node3D, size: Vector3, pos: Vector3, key: String, color: Color, rot_y := 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = mat(key, color)
	mi.mesh = bm
	mi.position = pos
	mi.rotation.y = rot_y
	parent.add_child(mi)
	return mi


func solid(size: Vector3, pos: Vector3, key: String, color: Color, rot_y := 0.0) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.rotation.y = rot_y
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	body.add_child(cs)
	add_child(body)
	vbox(body, size, Vector3.ZERO, key, color)
	return body


func _multimesh_boxes(positions: Array, colors: Array, size: Vector3) -> MultiMeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = mesh
	mm.instance_count = positions.size()
	for i in range(positions.size()):
		mm.set_instance_transform(i, Transform3D(Basis(), positions[i] as Vector3))
		mm.set_instance_color(i, colors[i] as Color)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.roughness = 0.95
	mmi.material_override = m
	return mmi


func _build_ground() -> void:
	var g := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(28, 1, 28)
	cs.shape = bs
	cs.position = Vector3(0, -0.44, 0) # Collision top at y = 0.06.
	g.add_child(cs)
	add_child(g)
	vbox(g, Vector3(28, 1, 28), Vector3(0, -0.56, 0), "dirt", Color(0.35, 0.24, 0.15))
	# Voxel tile quilt on top (24x24, one draw call).
	var positions: Array = []
	var colors: Array = []
	var n := 24
	for gx in range(n):
		for gz in range(n):
			var x := float(gx) - float(n - 1) * 0.5
			var z := float(gz) - float(n - 1) * 0.5
			positions.append(Vector3(x, 0.0, z))
			var v := rng.randf()
			colors.append(Color(0.30 + v * 0.10, 0.60 + v * 0.12, 0.26 + v * 0.06))
	add_child(_multimesh_boxes(positions, colors, Vector3(0.94, 0.12, 0.94)))


func _build_fence() -> void:
	var h := HALF + 0.6
	# Invisible collision walls (the pretty rails sit just inside them).
	var wall_defs := [
		[Vector3(0, 1.5, -h), Vector3(2 * h + 1, 3.0, 0.5)],
		[Vector3(0, 1.5, h), Vector3(2 * h + 1, 3.0, 0.5)],
		[Vector3(-h, 1.5, 0), Vector3(0.5, 3.0, 2 * h + 1)],
		[Vector3(h, 1.5, 0), Vector3(0.5, 3.0, 2 * h + 1)],
	]
	for w in wall_defs:
		var body := StaticBody3D.new()
		body.position = w[0] as Vector3
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = w[1] as Vector3
		cs.shape = bs
		body.add_child(cs)
		add_child(body)
	# Wooden posts via MultiMesh (one draw call).
	var positions: Array = []
	var colors: Array = []
	var per_side := 9
	for side in range(4):
		for i in range(per_side):
			var t := lerpf(-h, h, float(i) / float(per_side - 1))
			var p := Vector3(t, 0.575, -h)
			if side == 1:
				p = Vector3(t, 0.575, h)
			elif side == 2:
				p = Vector3(-h, 0.575, t)
			elif side == 3:
				p = Vector3(h, 0.575, t)
			positions.append(p)
			var v := rng.randf() * 0.08
			colors.append(Color(0.55 + v, 0.36 + v, 0.20 + v * 0.5))
	add_child(_multimesh_boxes(positions, colors, Vector3(0.26, 1.15, 0.26)))
	# Two rails per side.
	var rail_len := 2.0 * h + 0.4
	for y in [0.5, 0.95]:
		var yy := float(y)
		vbox(self, Vector3(rail_len, 0.14, 0.12), Vector3(0, yy, -h), "rail", Color(0.48, 0.31, 0.17))
		vbox(self, Vector3(rail_len, 0.14, 0.12), Vector3(0, yy, h), "rail", Color(0.48, 0.31, 0.17))
		vbox(self, Vector3(0.12, 0.14, rail_len), Vector3(-h, yy, 0), "rail", Color(0.48, 0.31, 0.17))
		vbox(self, Vector3(0.12, 0.14, rail_len), Vector3(h, yy, 0), "rail", Color(0.48, 0.31, 0.17))


func _build_trees() -> void:
	var leaf1 := Color(0.22, 0.52, 0.22)
	var leaf2 := Color(0.28, 0.60, 0.25)
	for i in range(TREE_POS.size()):
		var base := TREE_POS[i] as Vector3
		var trunk_h := 1.1 + 0.25 * float(i % 3)
		solid(Vector3(0.42, trunk_h, 0.42), base + Vector3(0, trunk_h * 0.5, 0), "trunk", Color(0.45, 0.30, 0.16))
		vbox(self, Vector3(1.7, 0.9, 1.7), base + Vector3(0, trunk_h + 0.45, 0), "leaf", leaf1, float(i) * 0.35)
		vbox(self, Vector3(1.15, 0.8, 1.15), base + Vector3(0, trunk_h + 1.2, 0), "leaf2", leaf2, float(i) * 0.7 + 0.3)


func _build_rocks() -> void:
	for r in ROCK_DATA:
		var entry := r as Array
		var base := entry[0] as Vector3
		var s := float(entry[1])
		var shade := 0.45 + rng.randf() * 0.12
		solid(Vector3(s, s * 0.7, s), base + Vector3(0, s * 0.35, 0), "rock", Color(shade, shade, shade + 0.03), rng.randf() * 1.2)


func _crate_at(pos: Vector3) -> void:
	solid(Vector3(0.9, 0.9, 0.9), pos + Vector3(0, 0.45, 0), "crate", Color(0.75, 0.52, 0.28))
	vbox(self, Vector3(0.94, 0.1, 0.94), pos + Vector3(0, 0.86, 0), "crate_dark", Color(0.55, 0.36, 0.18))


func _build_crates() -> void:
	_crate_at(Vector3(4, 0, 3))
	_crate_at(Vector3(-6, 0, -3))
	_crate_at(Vector3(1.5, 0, 8))
	_crate_at(Vector3(6.5, 0, -4.5))
	# A two-high stack to climb (coins on top).
	_crate_at(Vector3(-2, 0, 2))
	_crate_at(Vector3(-2, 0.9, 2))


func _build_coins() -> void:
	for p in COIN_POS:
		var coin := CoinScene.new() as Area3D
		coin.position = p as Vector3
		add_child(coin)


func _build_grass_and_flowers() -> void:
	var blade_pos: Array = []
	var blade_col: Array = []
	for i in range(90):
		var x := rng.randf_range(-11.5, 11.5)
		var z := rng.randf_range(-11.5, 11.5)
		blade_pos.append(Vector3(x, 0.21, z))
		var v := rng.randf()
		blade_col.append(Color(0.25 + v * 0.1, 0.55 + v * 0.15, 0.22))
	add_child(_multimesh_boxes(blade_pos, blade_col, Vector3(0.10, 0.30, 0.10)))
	# Flowers: green stems + colored heads.
	var stem_pos: Array = []
	var stem_col: Array = []
	var head_pos: Array = []
	var head_col: Array = []
	var palette := [Color(0.95, 0.35, 0.55), Color(1.0, 0.85, 0.25), Color(0.95, 0.95, 0.95), Color(0.95, 0.45, 0.20)]
	for i in range(26):
		var x := rng.randf_range(-11.0, 11.0)
		var z := rng.randf_range(-11.0, 11.0)
		stem_pos.append(Vector3(x, 0.20, z))
		stem_col.append(Color(0.25, 0.5, 0.22))
		head_pos.append(Vector3(x, 0.42, z))
		head_col.append(palette[i % palette.size()] as Color)
	add_child(_multimesh_boxes(stem_pos, stem_col, Vector3(0.06, 0.30, 0.06)))
	add_child(_multimesh_boxes(head_pos, head_col, Vector3(0.16, 0.18, 0.16)))


func _build_clouds() -> void:
	for i in range(4):
		var c := Node3D.new()
		c.position = Vector3(-15.0 + float(i) * 8.0, 11.0 + float(i) * 1.2, -6.0 + float(i) * 4.0)
		var w := 2.5 + float(i) * 0.5
		vbox(c, Vector3(w, 0.9, 1.6), Vector3.ZERO, "cloud", Color(0.96, 0.97, 1.0))
		vbox(c, Vector3(w * 0.6, 0.8, 1.2), Vector3(w * 0.25, 0.7, 0.2), "cloud", Color(0.94, 0.95, 1.0))
		vbox(c, Vector3(w * 0.5, 0.7, 1.0), Vector3(-w * 0.3, 0.55, -0.15), "cloud", Color(0.98, 0.98, 1.0))
		add_child(c)
		clouds.append({"node": c, "speed": 0.35 + 0.12 * float(i)})


func _build_outer_scenery() -> void:
	# Big ground skirt so the horizon is not void.
	vbox(self, Vector3(220, 0.5, 220), Vector3(0, -1.0, 0), "outer", Color(0.24, 0.45, 0.22))
	# Distant voxel hills.
	vbox(self, Vector3(14, 5, 12), Vector3(26, -1.5, -12), "hill", Color(0.25, 0.48, 0.28), 0.4)
	vbox(self, Vector3(12, 4, 14), Vector3(-27, -1.8, -6), "hill", Color(0.27, 0.50, 0.26), -0.3)
	vbox(self, Vector3(16, 6, 10), Vector3(4, -2.0, 28), "hill", Color(0.24, 0.46, 0.27), 0.2)
	# A few chunky trees outside the fence (visual only).
	var outer := [Vector3(18, 0, 6), Vector3(-17, 0, 12), Vector3(10, 0, -18), Vector3(-12, 0, -17)]
	for i in range(outer.size()):
		var base := (outer[i] as Vector3) + Vector3(0, -0.6, 0)
		vbox(self, Vector3(0.9, 2.6, 0.9), base + Vector3(0, 1.3, 0), "trunk", Color(0.45, 0.30, 0.16))
		vbox(self, Vector3(3.4, 1.8, 3.4), base + Vector3(0, 3.4, 0), "leaf", Color(0.22, 0.50, 0.24), float(i) * 0.5)
		vbox(self, Vector3(2.2, 1.4, 2.2), base + Vector3(0, 4.8, 0), "leaf2", Color(0.28, 0.58, 0.26), float(i) * 0.9)
