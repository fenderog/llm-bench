extends Node3D
class_name TrailLandscape

const LENGTH := 24.0
const GRASS := Color("8c9a61")
const PATH := Color("c8a074")
var chunks: Array[Node3D] = []
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	rng.seed = 73481
	for i in 7:
		var chunk := make_chunk(i)
		chunk.position.z = 24.0 - i * LENGTH
		add_child(chunk)
		chunks.append(chunk)
	make_distance()

func scroll(amount: float) -> void:
	for chunk in chunks:
		chunk.position.z += amount
		if chunk.position.z > 42.0:
			chunk.position.z -= LENGTH * chunks.size()

func make_chunk(index: int) -> Node3D:
	var node := Node3D.new()
	var b := VoxelBuilder.new()
	b.box(Vector3(0, -.39, 0), Vector3(78, .7, LENGTH + .03), GRASS)
	b.box(Vector3(0, -.035, 0), Vector3(9.2, .09, LENGTH + .03), Color("af885d"))
	b.box(Vector3(0, .005, 0), Vector3(8.5, .06, LENGTH + .03), PATH)
	# Wide, sun-bleached footpaths, with irregular little pebbles.
	for j in 48:
		var x := rng.randf_range(-4.2, 4.2)
		var z := rng.randf_range(-12, 12)
		b.box(Vector3(x, .049, z), Vector3(rng.randf_range(.08, .30), .025, rng.randf_range(.13, .48)), PATH.lightened(rng.randf_range(.02, .12)))
	for x in [-1.23, 1.23]:
		for z in [-10.0, -6.0, -2.0, 2.0, 6.0, 10.0]:
			b.box(Vector3(x, .045, z), Vector3(.055, .025, .7), Color("ddbd91"))
	for side in [-1.0, 1.0]:
		# A hand-built split-rail fence traces the trail.
		for z in [-12.0, -6.0, 0.0, 6.0, 12.0]:
			b.box(Vector3(side * 5.75, .65, z), Vector3(.19, 1.35, .20), Color("897657"))
			b.box(Vector3(side * 5.75, 1.35, z), Vector3(.25, .10, .25), Color("c1ad81"))
		for y in [.55, 1.02]:
			b.box(Vector3(side * 5.75, y, 0), Vector3(.12, .12, LENGTH), Color("b8a078"))
		for j in 80:
			var x: float = side * rng.randf_range(4.9, 27.0)
			var z := rng.randf_range(-12, 12)
			var col: Color = [Color("9fac70"), Color("7d915d"), Color("b4b67a")][rng.randi_range(0, 2)]
			if j < 18:
				b.box(Vector3(x, -.01, z), Vector3(rng.randf_range(.7, 2.8), .075, rng.randf_range(.6, 2.0)), col)
			else:
				var h := rng.randf_range(.13, .37)
				b.box(Vector3(x, h / 2, z), Vector3(.09, h, .10), col)
				if j % 7 == 0:
					b.box(Vector3(x, h, z), Vector3(.15, .11, .15), Color("f3d99a") if j % 2 == 0 else Color("e6a568"))
		for j in 5:
			var x: float = side * rng.randf_range(9.0 if side < 0 else 13.0, 27.0)
			var z := rng.randf_range(-11, 11)
			make_tree(b, Vector3(x, 0, z), rng.randf_range(.75, 1.4), (j + index) % 3)
		for j in 4:
			var x: float = side * rng.randf_range(6.5, 18.0)
			var z := rng.randf_range(-12, 12)
			b.box(Vector3(x, .13, z), Vector3(.6, .29, .48), Color("a3a28a"))
			b.box(Vector3(x - .13, .32, z + .05), Vector3(.35, .18, .34), Color("b9b49a"))
	b.build(node)
	return node

func make_tree(b: VoxelBuilder, p: Vector3, s: float, kind: int) -> void:
	var bark := Color("78674c")
	b.box(p + Vector3(0, 1.15 * s, 0), Vector3(.34, 2.3, .38) * s, bark)
	if kind == 0:
		for i in 5:
			var w := (2.1 - i * .32) * s
			b.box(p + Vector3(0, (1.7 + i * .51) * s, 0), Vector3(w, .68 * s, w), Color("4e7862").lightened(i * .032))
	else:
		b.box(p + Vector3(0, 2.6 * s, 0), Vector3(2.3, 1.25, 2.0) * s, Color("5e8461"))
		b.box(p + Vector3(-.25 * s, 3.32 * s, -.06 * s), Vector3(1.7, .54, 1.6) * s, Color("83a071"))
		b.box(p + Vector3(.80 * s, 2.62 * s, .25 * s), Vector3(.8, .84, 1.1) * s, Color("769568"))
		b.box(p + Vector3(-.80 * s, 2.45 * s, .42 * s), Vector3(.75, .65, .94) * s, Color("557b5c"))
		b.box(p + Vector3(.1 * s, 2.0 * s, .25 * s), Vector3(1.8, .45, 1.65) * s, Color("557a59"))

func make_distance() -> void:
	var b := VoxelBuilder.new()
	# Layered, square-cut mesas dissolve into the morning haze.
	for i in 17:
		var x := -95.0 + i * 12.0
		var height := rng.randf_range(7, 18)
		var depth := rng.randf_range(16, 25)
		var color := Color("84a291").lerp(Color("aebaa0"), rng.randf())
		for tier in 4:
			b.box(Vector3(x, height * (tier + .5) / 4 - 2, -115 - i % 3 * 9), Vector3(18 - tier * 3, height / 4, depth - tier * 3), color.lightened(tier * .025))
	for i in 10:
		var x := rng.randf_range(-60, 65)
		var z := rng.randf_range(-125, -75)
		var y := rng.randf_range(16, 25)
		b.box(Vector3(x, y, z), Vector3(6, 1.1, 2.8), Color("eee5cf"))
		b.box(Vector3(x - 1.6, y + .7, z), Vector3(2.8, .65, 2.5), Color("f4edda"))
		b.box(Vector3(x + 2.0, y + .5, z), Vector3(2.0, .7, 2.3), Color("f4edda"))
	b.build(self)
