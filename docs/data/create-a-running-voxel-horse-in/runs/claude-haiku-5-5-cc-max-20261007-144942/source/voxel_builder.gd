class_name VoxelBuilder
extends RefCounted

## Turns voxel cells into MultiMesh cubes.
##
## A cell is a Vector3i key in a Dictionary whose value is its Color. Cell
## (x, y, z) fills the unit box from (x, y, z) to (x + 1, y + 1, z + 1) in voxel
## units. The box() helper takes inclusive ranges, so box(-2, 1, ...) covers
## x = -2, -1, 0 and 1, which spans [-2, 2) and is centred on zero.

## World size of one voxel.
const SIZE := 0.12

const WOOD := Color(0.42, 0.27, 0.14)
const ROCK := Color(0.50, 0.50, 0.54)
const STEM := Color(0.25, 0.55, 0.20)
const RED := Color(0.78, 0.14, 0.12)
const WHITE := Color(0.95, 0.95, 0.92)
const LEAF_COLORS := [
	Color(0.22, 0.52, 0.18),
	Color(0.30, 0.60, 0.22),
	Color(0.16, 0.42, 0.16),
]
const FLOWER_COLORS := [
	Color(0.95, 0.85, 0.20),
	Color(0.90, 0.35, 0.55),
	Color(0.95, 0.95, 0.95),
	Color(0.55, 0.45, 0.90),
]

## Height of a hurdle's top rail in world units.
const HURDLE_HEIGHT := 9 * SIZE
## Half the width of a hurdle in world units.
const HURDLE_HALF_WIDTH := 12 * SIZE

static var _cube: BoxMesh


## Fills the inclusive range of cells with `color`.
static func box(cells: Dictionary, x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, color: Color) -> void:
	for x in range(x0, x1 + 1):
		for y in range(y0, y1 + 1):
			for z in range(z0, z1 + 1):
				cells[Vector3i(x, y, z)] = color


## Adds a child node under `parent` that draws `cells`. The new node's origin
## is `pivot` and `parent_pivot` is the parent's origin, both in voxel units.
static func part(parent: Node3D, parent_pivot: Vector3, pivot: Vector3, cells: Dictionary) -> Node3D:
	var node := Node3D.new()
	node.position = (pivot - parent_pivot) * SIZE
	parent.add_child(node)

	# One MultiMesh per colour keeps the draw-call count low.
	var by_color := {}
	for cell in cells:
		var color: Color = cells[cell]
		if not by_color.has(color):
			by_color[color] = []
		by_color[color].append(cell)

	for color in by_color:
		var list: Array = by_color[color]
		var multimesh := MultiMesh.new()
		multimesh.transform_format = MultiMesh.TRANSFORM_3D
		multimesh.mesh = _cube_mesh()
		multimesh.instance_count = list.size()
		for i in list.size():
			var center := Vector3(list[i]) + Vector3.ONE * 0.5
			multimesh.set_instance_transform(i, Transform3D(Basis(), (center - pivot) * SIZE))
		var drawn := MultiMeshInstance3D.new()
		drawn.multimesh = multimesh
		drawn.material_override = _material(color)
		node.add_child(drawn)
	return node


## A small voxel tree standing on the ground at the origin of `parent`.
static func tree(parent: Node3D, rng: RandomNumberGenerator) -> void:
	var trunk := {}
	box(trunk, -1, 0, 0, 8, -1, 0, WOOD)
	part(parent, Vector3.ZERO, Vector3.ZERO, trunk)

	var leaves := {}
	var color: Color = LEAF_COLORS[rng.randi() % LEAF_COLORS.size()]
	box(leaves, -3, 2, 6, 10, -3, 2, color)
	box(leaves, -2, 1, 11, 13, -2, 1, color)
	box(leaves, -1, 0, 14, 14, -1, 0, color)
	part(parent, Vector3.ZERO, Vector3.ZERO, leaves)


## A lumpy grey boulder on the ground at the origin of `parent`.
static func rock(parent: Node3D, rng: RandomNumberGenerator) -> void:
	var cells := {}
	var color := ROCK.darkened(rng.randf_range(0.0, 0.2))
	box(cells, -2, 1, 0, 2, -2, 1, color)
	box(cells, -1, 0, 3, 3, -1, 0, color)
	part(parent, Vector3.ZERO, Vector3.ZERO, cells)


## A few flowers on short green stems at the origin of `parent`.
static func flowers(parent: Node3D, rng: RandomNumberGenerator) -> void:
	var stems := {}
	var petals := {}
	for i in 3:
		var x := rng.randi_range(-3, 2)
		var z := rng.randi_range(-3, 2)
		stems[Vector3i(x, 0, z)] = STEM
		stems[Vector3i(x, 1, z)] = STEM
		petals[Vector3i(x, 2, z)] = FLOWER_COLORS[rng.randi() % FLOWER_COLORS.size()]
	part(parent, Vector3.ZERO, Vector3.ZERO, stems)
	part(parent, Vector3.ZERO, Vector3.ZERO, petals)


## A show-jumping hurdle standing on the origin of `parent`, centred on x = 0.
static func hurdle(parent: Node3D) -> void:
	var posts := {}
	box(posts, -12, -11, 0, 8, 0, 1, WHITE)
	box(posts, 10, 11, 0, 8, 0, 1, WHITE)
	part(parent, Vector3.ZERO, Vector3.ZERO, posts)

	var rails := {}
	for x in range(-10, 10):
		var color: Color = RED if x % 2 == 0 else WHITE
		box(rails, x, x, 3, 4, 0, 1, color)
		box(rails, x, x, 7, 8, 0, 1, color)
	part(parent, Vector3.ZERO, Vector3.ZERO, rails)


static func _material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.9
	return material


static func _cube_mesh() -> BoxMesh:
	if _cube == null:
		_cube = BoxMesh.new()
		# A touch smaller than SIZE so neighbouring cubes show a thin seam.
		_cube.size = Vector3.ONE * SIZE * 0.96
	return _cube
