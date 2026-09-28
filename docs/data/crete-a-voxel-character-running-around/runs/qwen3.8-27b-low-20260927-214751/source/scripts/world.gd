extends Node3D
## Procedurally builds the small voxel sandbox: ground, walls, trees,
## rocks, crates and flowers. No external assets required.

const SIZE := 28.0          # play area is SIZE x SIZE
const WALL_H := 1.5
const WALL_T := 0.5

var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 1337

	var grass := _make_mat(Color(0.36, 0.66, 0.3, 1.0), 0.9)
	var dirt := _make_mat(Color(0.45, 0.33, 0.22, 1.0), 1.0)
	var wall := _make_mat(Color(0.78, 0.72, 0.6, 1.0), 1.0)
	var trunk := _make_mat(Color(0.42, 0.29, 0.18, 1.0), 1.0)
	var rock := _make_mat(Color(0.55, 0.56, 0.58, 1.0), 1.0)
	var crate := _make_mat(Color(0.72, 0.55, 0.32, 1.0), 1.0)
	var stone := _make_mat(Color(0.62, 0.63, 0.65, 1.0), 1.0)
	var stem := _make_mat(Color(0.3, 0.5, 0.25, 1.0), 1.0)

	# Ground (dirt base with a grass top)
	_box(dirt, Vector3(SIZE + WALL_T * 2, 0.2, SIZE + WALL_T * 2), Vector3(0, -0.15, 0))
	_box(grass, Vector3(SIZE, 0.2, SIZE), Vector3(0, -0.1, 0))

	# Walls
	var half := SIZE / 2.0
	var wall_defs := [
		[Vector3(SIZE + WALL_T * 2, WALL_H, WALL_T), Vector3(0, WALL_H / 2.0, half + WALL_T / 2.0)],
		[Vector3(SIZE + WALL_T * 2, WALL_H, WALL_T), Vector3(0, WALL_H / 2.0, -half - WALL_T / 2.0)],
		[Vector3(WALL_T, WALL_H, SIZE), Vector3(half + WALL_T / 2.0, WALL_H / 2.0, 0)],
		[Vector3(WALL_T, WALL_H, SIZE), Vector3(-half - WALL_T / 2.0, WALL_H / 2.0, 0)],
	]
	for w in wall_defs:
		_box(wall, w[0], w[1])
	# Wall caps for a little voxel detail
	_box(stone, Vector3(SIZE + WALL_T * 2 + 0.1, 0.15, WALL_T + 0.1), Vector3(0, WALL_H + 0.075, half + WALL_T / 2.0))
	_box(stone, Vector3(SIZE + WALL_T * 2 + 0.1, 0.15, WALL_T + 0.1), Vector3(0, WALL_H + 0.075, -half - WALL_T / 2.0))
	_box(stone, Vector3(WALL_T + 0.1, 0.15, SIZE + 0.1), Vector3(half + WALL_T / 2.0, WALL_H + 0.075, 0))
	_box(stone, Vector3(WALL_T + 0.1, 0.15, SIZE + 0.1), Vector3(-half - WALL_T / 2.0, WALL_H + 0.075, 0))

	# Trees
	var tree_spots := [
		Vector3(-8.5, 0, -7.5), Vector3(7.5, 0, -9.0), Vector3(9.5, 0, 6.5),
		Vector3(-9.0, 0, 8.0), Vector3(0.5, 0, -10.5), Vector3(-3.0, 0, 10.0),
	]
	for s in tree_spots:
		_make_tree(s, trunk)

	# Crates (a few singles, one stacked pair)
	var crate_defs := [
		[Vector3(3.0, 0.5, 3.0), Vector3(1.0, 1.0, 1.0)],
		[Vector3(3.0, 1.475, 3.0), Vector3(0.95, 0.95, 0.95)],
		[Vector3(4.5, 0.5, 3.6), Vector3(1.0, 1.0, 1.0)],
		[Vector3(-5.5, 0.3, -2.0), Vector3(1.2, 0.6, 1.2)],
		[Vector3(6.0, 0.5, -3.5), Vector3(1.0, 1.0, 1.0)],
	]
	for c in crate_defs:
		_box_static(c[1], crate, c[0])

	# Rocks
	var rock_defs := [
		[Vector3(-6.5, 0.35, 4.5), Vector3(1.4, 0.7, 1.2)],
		[Vector3(2.0, 0.25, 8.5), Vector3(1.0, 0.5, 1.0)],
		[Vector3(-1.5, 0.4, -6.0), Vector3(1.6, 0.8, 1.4)],
		[Vector3(8.0, 0.28, 1.5), Vector3(1.1, 0.55, 1.1)],
		[Vector3(-8.0, 0.33, 0.5), Vector3(1.3, 0.65, 1.3)],
	]
	for r in rock_defs:
		_box_static(r[1], rock, r[0])

	# Flowers (stem + colored voxel head), scattered
	var flower_colors := [
		Color(0.9, 0.3, 0.35, 1.0), Color(0.95, 0.8, 0.3, 1.0),
		Color(0.85, 0.5, 0.9, 1.0), Color(0.98, 0.98, 0.98, 1.0),
	]
	for i in 46:
		var x := _rng.randf_range(-half + 1.5, half - 1.5)
		var z := _rng.randf_range(-half + 1.5, half - 1.5)
		if absf(x) < 1.6 and absf(z) < 1.6:
			continue
		var head_mat := _make_mat(flower_colors[i % flower_colors.size()], 0.0)
		_box(stem, Vector3(0.06, 0.3, 0.06), Vector3(x, 0.15, z))
		_box(head_mat, Vector3(0.16, 0.16, 0.16), Vector3(x, 0.38, z))


func _make_tree(pos: Vector3, trunk_mat: Material) -> void:
	var trunk_h := _rng.randf_range(1.4, 2.0)
	_box(trunk_mat, Vector3(0.5, trunk_h, 0.5), pos + Vector3(0, trunk_h / 2.0, 0))
	var leaf_a := _make_mat(Color(0.2, 0.55, 0.24, 1.0), 0.9)
	var leaf_b := _make_mat(Color(0.28, 0.62, 0.3, 1.0), 0.9)
	var s1 := _rng.randf_range(1.6, 2.2)
	_box(leaf_a, Vector3(s1, s1 * 0.8, s1), pos + Vector3(0, trunk_h + s1 * 0.35, 0))
	var s2 := s1 * _rng.randf_range(0.6, 0.8)
	_box(leaf_b, Vector3(s2, s2 * 0.8, s2), pos + Vector3(0, trunk_h + s1 * 0.35 + s2 * 0.45, 0))


func _make_mat(color: Color, roughness: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = roughness
	return m


func _box(mat: Material, size: Vector3, pos: Vector3) -> void:
	var mi := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.material = mat
	mesh.size = size
	mi.mesh = mesh
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mi)


func _box_static(size: Vector3, mat: Material, pos: Vector3) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	col.shape = shape
	body.add_child(col)
	_box(mat, size, Vector3.ZERO)
	add_child(body)
