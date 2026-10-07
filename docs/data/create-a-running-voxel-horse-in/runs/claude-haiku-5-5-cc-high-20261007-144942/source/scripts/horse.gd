class_name VoxelHorse
extends Node3D

## A blocky voxel horse. It faces -Z, with its hooves at y = 0. The game moves
## this root node; the script animates the legs, neck, head and tail.

const CHASSIS_CENTER := 1.05  # height of the body's middle, in meters
const STRIDE := 3.6  # meters covered by one full gallop cycle
const LEG_SWING := 0.7  # radians
const LEG_PHASES := [0.5, 0.62, 0.0, 0.12]  # front-left, front-right, hind-left, hind-right
const NECK_TILT := -0.45
const HEAD_TILT := -0.35
const HOOF := Color(0.12, 0.1, 0.09)
const EYE := Color(0.04, 0.03, 0.03)

@export var coat_color := Color(0.45, 0.26, 0.13)
@export var mane_color := Color(0.1, 0.07, 0.05)

var _tilt: Node3D  # rotates the whole horse when it falls over
var _chassis: Node3D
var _neck: Node3D
var _head: Node3D
var _tail: Node3D
var _legs: Array[Node3D] = []
var _cycle := 0.0  # position within the gallop cycle, 0..1
var _time := 0.0
var _fall_tween: Tween


func _ready() -> void:
	_build()
	reset_pose()


## Poses the horse for the given ground speed. While airborne the legs tuck.
func animate(delta: float, speed: float, airborne: bool) -> void:
	_time += delta
	_cycle = fposmod(_cycle + speed * delta / STRIDE, 1.0)
	var intensity := clampf(speed / 6.0, 0.0, 1.0)
	var wave := sin(TAU * _cycle)

	for i in _legs.size():
		var angle := sin(TAU * (_cycle + LEG_PHASES[i])) * LEG_SWING * intensity
		if airborne:
			angle = 0.8 if i < 2 else -0.7
		_legs[i].rotation.x = angle

	_chassis.position.y = -CHASSIS_CENTER + absf(wave) * 0.05 * intensity + sin(_time * 2.0) * 0.004
	_neck.rotation.x = NECK_TILT + wave * 0.04 * intensity
	_head.rotation.x = HEAD_TILT + wave * 0.03 * intensity
	_tail.rotation.x = -0.4 * intensity
	_tail.rotation.z = sin(TAU * _cycle * 0.5) * 0.3 * intensity + sin(_time * 2.0) * 0.04


func reset_pose() -> void:
	if _fall_tween:
		_fall_tween.kill()
	_tilt.rotation = Vector3.ZERO
	_tilt.position = Vector3(0.0, CHASSIS_CENTER, 0.0)


## Tips the horse onto its side, as when it stumbles.
func fall_over() -> void:
	_fall_tween = create_tween()
	_fall_tween.set_parallel(true)
	_fall_tween.tween_property(_tilt, "rotation:z", -PI / 2.0, 0.5)
	_fall_tween.tween_property(_tilt, "position:y", 0.2, 0.5)


func _build() -> void:
	var coat := coat_color
	var sock := coat.darkened(0.4)
	var muzzle := coat.lightened(0.25)

	_tilt = Node3D.new()
	_tilt.position = Vector3(0.0, CHASSIS_CENTER, 0.0)
	add_child(_tilt)
	_chassis = Node3D.new()
	_chassis.position = Vector3(0.0, -CHASSIS_CENTER, 0.0)
	_tilt.add_child(_chassis)

	var torso := {}
	VoxelBuilder.fill(torso, Vector3i(-2, 8, -5), Vector3i(2, 13, 4), coat)  # barrel
	VoxelBuilder.fill(torso, Vector3i(-2, 9, -8), Vector3i(2, 13, -5), coat)  # chest
	VoxelBuilder.fill(torso, Vector3i(-2, 8, 4), Vector3i(2, 13, 6), coat)  # rump
	VoxelBuilder.fill(torso, Vector3i(-2, 8, -5), Vector3i(2, 9, 4), coat.darkened(0.2))  # belly
	_chassis.add_child(VoxelBuilder.make_instance(torso))

	for at in [Vector3i(-1, 8, -4), Vector3i(1, 8, -4), Vector3i(-1, 8, 3), Vector3i(1, 8, 3)]:
		_legs.append(_pivot(_chassis, at, _leg_voxels(coat, sock)))

	var neck := {}
	VoxelBuilder.fill(neck, Vector3i(-1, 0, -2), Vector3i(1, 6, 1), coat)
	VoxelBuilder.fill(neck, Vector3i(-1, 1, 1), Vector3i(1, 6, 2), mane_color)  # mane
	_neck = _pivot(_chassis, Vector3i(0, 12, -6), neck)

	_head = _pivot(_neck, Vector3i(0, 6, -2), _head_voxels(coat, muzzle))

	var tail := {}
	VoxelBuilder.fill(tail, Vector3i(-1, -8, 0), Vector3i(1, 0, 2), mane_color)
	_tail = _pivot(_chassis, Vector3i(0, 12, 6), tail)


## Creates a joint at `at` (in voxel units) with its own mesh. The voxels are
## relative to that joint, so the node rotates around it.
func _pivot(parent: Node3D, at: Vector3i, voxels: Dictionary) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = Vector3(at) * VoxelBuilder.VOXEL_SIZE
	pivot.add_child(VoxelBuilder.make_instance(voxels))
	parent.add_child(pivot)
	return pivot


func _leg_voxels(coat: Color, sock: Color) -> Dictionary:
	var leg := {}
	VoxelBuilder.fill(leg, Vector3i(-1, -6, -1), Vector3i(1, 0, 1), coat)
	VoxelBuilder.fill(leg, Vector3i(-1, -7, -1), Vector3i(1, -6, 1), sock)
	VoxelBuilder.fill(leg, Vector3i(-1, -8, -1), Vector3i(1, -7, 1), HOOF)
	return leg


func _head_voxels(coat: Color, muzzle: Color) -> Dictionary:
	var head := {}
	VoxelBuilder.fill(head, Vector3i(-1, -2, -4), Vector3i(1, 3, 1), coat)  # skull
	VoxelBuilder.fill(head, Vector3i(-1, -4, -7), Vector3i(1, -1, -4), muzzle)  # muzzle
	VoxelBuilder.fill(head, Vector3i(-1, 3, -1), Vector3i(0, 5, 1), coat)  # left ear
	VoxelBuilder.fill(head, Vector3i(0, 3, -1), Vector3i(1, 5, 1), coat)  # right ear
	VoxelBuilder.fill(head, Vector3i(1, 0, -3), Vector3i(2, 1, -2), EYE)  # eye
	return head
