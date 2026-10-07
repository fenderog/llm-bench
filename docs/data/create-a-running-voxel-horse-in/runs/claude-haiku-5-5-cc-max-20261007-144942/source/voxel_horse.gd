class_name VoxelHorse
extends Node3D

## A chestnut voxel horse with a procedural gallop. The head faces -Z.
##
## Coordinates are in voxel units with the origin on the ground under the
## middle of the body. Legs hang from hip pivots at the belly and bend at knee
## pivots, so the gait can be driven by rotating those pivots.

const COAT := Color(0.62, 0.37, 0.20)
const COAT_DARK := Color(0.42, 0.24, 0.13)
const MANE := Color(0.12, 0.08, 0.05)
const HOOF := Color(0.10, 0.08, 0.07)
const SADDLE := Color(0.30, 0.16, 0.08)
const BLANKET := Color(0.70, 0.12, 0.12)
const MUZZLE := Color(0.88, 0.78, 0.66)
const BLAZE := Color(0.96, 0.95, 0.92)
const EYE := Color(0.02, 0.02, 0.02)

const HIP_HEIGHT := 9.0
const KNEE_HEIGHT := 4.0
const NECK_PIVOT := Vector3(0, 12, -5)
const TAIL_PIVOT := Vector3(0, 13, 5)
const STRIDE := 3.5  # world units covered by one full gallop cycle
const SWING := 0.6  # hip swing amplitude, in radians
const FLEX := 1.0  # knee bend amplitude, in radians

var _body: Node3D
var _neck: Node3D
var _tail: Node3D
var _hips: Array[Node3D] = []
var _knees: Array[Node3D] = []
var _phase := 0.0
var _air := 0.0
# Each leg's offset into the gallop cycle. The front pair leads, the rear trails.
var _offsets := [0.0, 0.2, 2.2, 2.4]


func _ready() -> void:
	_body = Node3D.new()
	add_child(_body)

	var torso := {}
	VoxelBuilder.box(torso, -3, 2, 9, 14, -5, 4, COAT)
	VoxelBuilder.box(torso, -3, 2, 9, 9, -5, 4, COAT_DARK)  # darker belly
	VoxelBuilder.part(_body, Vector3.ZERO, Vector3.ZERO, torso)

	var saddle := {}
	VoxelBuilder.box(saddle, -3, 2, 15, 15, -2, 1, BLANKET)
	VoxelBuilder.box(saddle, -2, 1, 16, 16, -1, 0, SADDLE)
	VoxelBuilder.part(_body, Vector3.ZERO, Vector3.ZERO, saddle)

	# Front legs first, then hind legs. _offsets relies on this order.
	_build_leg(-3, -2, -5, -4)
	_build_leg(1, 2, -5, -4)
	_build_leg(-3, -2, 3, 4)
	_build_leg(1, 2, 3, 4)

	_build_neck()
	_build_tail()


## One leg: an upper section hanging from the hip, then a lower section and a
## hoof hanging from the knee.
func _build_leg(x0: int, x1: int, z0: int, z1: int) -> void:
	var hip_pivot := Vector3((x0 + x1 + 1) / 2.0, HIP_HEIGHT, (z0 + z1 + 1) / 2.0)
	var upper := {}
	VoxelBuilder.box(upper, x0, x1, 4, 8, z0, z1, COAT)
	var hip := VoxelBuilder.part(_body, Vector3.ZERO, hip_pivot, upper)

	var knee_pivot := Vector3(hip_pivot.x, KNEE_HEIGHT, hip_pivot.z)
	var lower := {}
	VoxelBuilder.box(lower, x0, x1, 1, 3, z0, z1, COAT_DARK)
	VoxelBuilder.box(lower, x0, x1, 0, 0, z0, z1, HOOF)
	var knee := VoxelBuilder.part(hip, hip_pivot, knee_pivot, lower)

	_hips.append(hip)
	_knees.append(knee)


func _build_neck() -> void:
	var neck := {}
	# Stepped neck rising towards the head.
	VoxelBuilder.box(neck, -2, 1, 12, 15, -8, -5, COAT)
	VoxelBuilder.box(neck, -2, 1, 15, 18, -10, -7, COAT)
	VoxelBuilder.box(neck, -2, 1, 18, 21, -12, -9, COAT)
	# Head: skull, muzzle, white blaze, ears and eyes.
	VoxelBuilder.box(neck, -2, 1, 20, 23, -15, -12, COAT)
	VoxelBuilder.box(neck, -1, 0, 18, 20, -17, -15, MUZZLE)
	VoxelBuilder.box(neck, -1, 0, 21, 22, -15, -15, BLAZE)
	VoxelBuilder.box(neck, -1, 0, 24, 25, -13, -12, COAT_DARK)
	VoxelBuilder.box(neck, -2, -2, 22, 22, -14, -14, EYE)
	VoxelBuilder.box(neck, 1, 1, 22, 22, -14, -14, EYE)
	# Mane forms a ridge on the crest of each neck section. Painted last so it wins.
	VoxelBuilder.box(neck, -1, 0, 16, 16, -8, -5, MANE)
	VoxelBuilder.box(neck, -1, 0, 19, 19, -10, -7, MANE)
	VoxelBuilder.box(neck, -1, 0, 22, 22, -12, -9, MANE)
	_neck = VoxelBuilder.part(_body, Vector3.ZERO, NECK_PIVOT, neck)


func _build_tail() -> void:
	# Two voxels wide at the root, tapering to one at the tip.
	var tail := {}
	VoxelBuilder.box(tail, -1, 0, 11, 14, 5, 6, MANE)
	VoxelBuilder.box(tail, 0, 0, 8, 11, 7, 8, MANE)
	VoxelBuilder.box(tail, 0, 0, 5, 8, 9, 10, MANE)
	_tail = VoxelBuilder.part(_body, Vector3.ZERO, TAIL_PIVOT, tail)


## Advances the gallop by `delta` seconds at `speed` world units per second.
## While `airborne`, the legs blend into a tucked jumping pose.
func animate(speed: float, delta: float, airborne: bool) -> void:
	_phase = fposmod(_phase + TAU * speed * delta / STRIDE, TAU)
	_air = move_toward(_air, 1.0 if airborne else 0.0, delta * 5.0)
	var amp := clampf(speed / 9.0, 0.3, 1.3)

	for i in _hips.size():
		var p: float = _phase + _offsets[i]
		var front := i < 2
		var swing := sin(p) * SWING * amp
		var flex := -maxf(0.0, cos(p)) * FLEX * amp
		# Jumping pose: front legs reach forward, hind legs stretch back.
		var pose_hip := 0.9 if front else -0.8
		var pose_knee := -0.9 if front else 0.0
		_hips[i].rotation.x = lerpf(swing, pose_hip, _air)
		_knees[i].rotation.x = lerpf(flex, pose_knee, _air)

	# The body lifts on each footfall and the head nods with the stride.
	_body.position.y = (1.0 - cos(_phase * 2.0)) * 0.03 * amp
	_body.rotation.x = -0.04 + sin(_phase * 2.0) * 0.02
	_neck.rotation.x = -0.3 + sin(_phase * 2.0) * 0.05 * amp
	_tail.rotation.x = -0.35 + sin(_phase) * 0.05
	_tail.rotation.y = sin(_phase) * 0.25 * amp
