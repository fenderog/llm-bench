class_name VoxelHorse
extends Node3D

## A voxel horse assembled from boxes at runtime. Legs, neck and tail sit on
## pivots so update_gait() can drive a procedural gallop. The horse faces -Z
## and its hooves rest on y = 0.

const VOXEL := 0.15

const COAT := Color(0.52, 0.32, 0.17)
const COAT_DARK := Color(0.36, 0.21, 0.11)
const MANE := Color(0.12, 0.08, 0.06)
const MUZZLE := Color(0.8, 0.66, 0.5)
const HOOF := Color(0.1, 0.08, 0.07)
const EYE := Color(0.02, 0.02, 0.03)
const SADDLE := Color(0.7, 0.14, 0.12)

# Front-left, front-right, back-left, back-right. Offsets are fractions of a stride.
const LEG_PIVOTS := [Vector3(-1, 6, -2), Vector3(1, 6, -2), Vector3(-1, 6, 3), Vector3(1, 6, 3)]
const LEG_OFFSETS := [0.0, 0.12, 0.42, 0.54]

# Boxes are [min corner, size, colour] in voxel units.
const LEG_BOXES := [
	[Vector3(-1, -5, -1), Vector3(2, 6, 2), COAT_DARK],
	[Vector3(-1, -6, -1), Vector3(2, 1, 2), HOOF],
]
const TORSO_BOXES := [
	[Vector3(-2, 6, -4), Vector3(4, 5, 9), COAT],
	[Vector3(-2, 11, -1), Vector3(4, 1, 3), SADDLE],
]
const NECK_BOXES := [
	[Vector3(-1, -1, -2), Vector3(2, 5, 2), COAT],
	[Vector3(-1, 4, -2), Vector3(2, 1, 2), MANE],
]
const HEAD_BOXES := [
	[Vector3(-1, 3, -6), Vector3(2, 3, 4), COAT],
	[Vector3(-1, 2, -8), Vector3(2, 2, 2), MUZZLE],
	[Vector3(-1, 6, -4), Vector3(2, 2, 1), COAT_DARK],
	[Vector3(-2, 4, -5), Vector3(1, 1, 1), EYE],
	[Vector3(1, 4, -5), Vector3(1, 1, 1), EYE],
]
const TAIL_BOXES := [
	[Vector3(-0.5, -6, 0), Vector3(1, 7, 1), MANE],
	[Vector3(-1, -7, 0), Vector3(2, 3, 2), MANE],
]

const BOB_AMOUNT := 0.4  # voxels

var _body: Node3D
var _neck: Node3D
var _tail: Node3D
var _legs: Array[Node3D] = []
var _phase := 0.0


func _ready() -> void:
	_build()


func _build() -> void:
	_body = _add_part(self, Vector3.ZERO, TORSO_BOXES)
	# The neck pivots at the top-front of the torso, so the head moves with it.
	_neck = _add_part(_body, Vector3(0, 9, -3), NECK_BOXES)
	_add_part(_neck, Vector3.ZERO, HEAD_BOXES)
	_tail = _add_part(_body, Vector3(0, 9, 5), TAIL_BOXES)
	for pivot in LEG_PIVOTS:
		_legs.append(_add_part(self, pivot, LEG_BOXES))
	_neck.rotation.x = -0.25


## Advances the gallop. speed_ratio runs from 0 (standing) to 1 (top speed).
## While airborne the legs tuck forward and back.
func update_gait(delta: float, speed_ratio: float, airborne: bool) -> void:
	var ratio := clampf(speed_ratio, 0.0, 1.0)
	_phase = fmod(_phase + delta * (5.0 + 8.0 * ratio), TAU)
	var amplitude := lerpf(0.2, 0.85, ratio)

	for i in _legs.size():
		var target: float
		if airborne:
			target = 0.9 if i < 2 else -0.8
		else:
			target = sin(_phase + LEG_OFFSETS[i] * TAU) * amplitude
		_legs[i].rotation.x = lerpf(_legs[i].rotation.x, target, minf(1.0, delta * 14.0))

	_body.position.y = (1.0 - cos(_phase * 2.0)) * 0.5 * BOB_AMOUNT * VOXEL
	_neck.rotation.x = -0.25 + sin(_phase * 2.0) * 0.05
	_tail.rotation.x = -0.35 - 0.35 * ratio
	_tail.rotation.z = sin(_phase) * 0.15


## Creates a pivot node at `pivot` (voxel units) holding one mesh built from
## `boxes`. Box coordinates are relative to the pivot.
func _add_part(parent: Node3D, pivot: Vector3, boxes: Array) -> Node3D:
	var node := Node3D.new()
	node.position = pivot * VOXEL
	parent.add_child(node)

	var st := VoxelBuilder.new_surface_tool()
	for box in boxes:
		VoxelBuilder.add_box(st, box[0] * VOXEL, box[1] * VOXEL, box[2])
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.mesh = st.commit()
	mesh_instance.material_override = VoxelBuilder.make_material()
	node.add_child(mesh_instance)
	return node
