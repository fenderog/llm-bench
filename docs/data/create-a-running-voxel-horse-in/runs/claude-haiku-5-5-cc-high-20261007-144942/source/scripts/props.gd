class_name Props
extends RefCounted

## Voxel obstacles and scenery. The game builds each kind once and duplicates it.

const WOOD := Color(0.55, 0.36, 0.2)
const WHITE := Color(0.95, 0.94, 0.9)
const RED := Color(0.82, 0.16, 0.14)
const STONE := Color(0.52, 0.52, 0.55)
const STONE_DARK := Color(0.36, 0.36, 0.39)
const MOSS := Color(0.3, 0.52, 0.24)
const BARK := Color(0.36, 0.24, 0.14)
const LEAF := Color(0.18, 0.5, 0.2)
const LEAF_LIGHT := Color(0.3, 0.64, 0.28)
const FLOWER := Color(0.95, 0.8, 0.2)


static func build(kind: String) -> Node3D:
	var voxels := {}
	match kind:
		"hurdle":
			_add_hurdle(voxels)
		"rock_wall":
			_add_rock_wall(voxels)
		"tree":
			_add_tree(voxels)
		"bush":
			_add_bush(voxels)
		"boulder":
			_add_boulder(voxels)
	var root := Node3D.new()
	root.add_child(VoxelBuilder.make_instance(voxels))
	return root


## A show-jumping fence, 1.2 m wide and 0.7 m tall. Its feet are at y = 0.
static func _add_hurdle(v: Dictionary) -> void:
	VoxelBuilder.fill(v, Vector3i(-6, 0, -1), Vector3i(-4, 7, 1), WOOD)  # left post
	VoxelBuilder.fill(v, Vector3i(4, 0, -1), Vector3i(6, 7, 1), WOOD)  # right post
	VoxelBuilder.fill(v, Vector3i(-6, 2, -1), Vector3i(6, 4, 1), WHITE)  # lower rail
	VoxelBuilder.fill(v, Vector3i(-6, 5, -1), Vector3i(6, 7, 1), RED)  # top rail


## A tall stone wall that can't be jumped. Horses have to change lanes.
static func _add_rock_wall(v: Dictionary) -> void:
	VoxelBuilder.fill(v, Vector3i(-6, 0, -4), Vector3i(6, 12, 4), STONE_DARK)
	VoxelBuilder.fill(v, Vector3i(-5, 12, -3), Vector3i(5, 15, 3), STONE)
	VoxelBuilder.fill(v, Vector3i(-5, 14, -3), Vector3i(5, 15, 3), MOSS)


static func _add_tree(v: Dictionary) -> void:
	VoxelBuilder.fill(v, Vector3i(-1, 0, -1), Vector3i(1, 9, 1), BARK)
	VoxelBuilder.fill(v, Vector3i(-4, 7, -4), Vector3i(4, 14, 4), LEAF)
	VoxelBuilder.fill(v, Vector3i(-3, 14, -3), Vector3i(3, 16, 3), LEAF_LIGHT)


static func _add_bush(v: Dictionary) -> void:
	VoxelBuilder.fill(v, Vector3i(-3, 0, -3), Vector3i(3, 4, 3), LEAF)
	VoxelBuilder.fill(v, Vector3i(-2, 4, -2), Vector3i(2, 5, 2), LEAF_LIGHT)
	VoxelBuilder.fill(v, Vector3i(-2, 2, 3), Vector3i(-1, 3, 4), FLOWER)
	VoxelBuilder.fill(v, Vector3i(1, 1, 3), Vector3i(2, 2, 4), RED)


static func _add_boulder(v: Dictionary) -> void:
	VoxelBuilder.fill(v, Vector3i(-2, 0, -2), Vector3i(2, 3, 2), STONE)
	VoxelBuilder.fill(v, Vector3i(-1, 3, -1), Vector3i(1, 4, 1), STONE_DARK)
