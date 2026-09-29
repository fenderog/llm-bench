class_name VoxelHorse
extends Node3D
## A horse assembled from voxel meshes on a small skeleton of pivots.
## Faces +X, is Y-up, and its feet touch y = 0. Everything lateral is on Z.

const V := 0.1          # edge length of one voxel in metres
const UPPER := 5        # voxel rows from the hip pivot down to the knee
const LOWER := 5        # voxel rows from the knee down to the hoof sole
const HIP_Y := 1.0      # hip pivot height inside the body, in voxels
const STAND_HEIGHT := 9.0  # body origin above the ground when standing, in voxels

const COAT := Color(0.56, 0.32, 0.15)
const COAT_DARK := Color(0.40, 0.22, 0.10)
const BELLY := Color(0.70, 0.47, 0.27)
const MANE := Color(0.12, 0.07, 0.05)
const BLAZE := Color(0.96, 0.93, 0.86)
const SOCK := Color(0.93, 0.90, 0.82)
const HOOF := Color(0.13, 0.12, 0.12)
const NOSE := Color(0.30, 0.19, 0.14)
const EYE := Color(0.03, 0.03, 0.04)
const SADDLE := Color(0.72, 0.13, 0.14)
const LEATHER := Color(0.33, 0.17, 0.09)
const TRIM := Color(0.92, 0.74, 0.24)

var body: Node3D
var neck: Node3D
var head: Node3D
var tail: Node3D
var tail_tip: Node3D
## One entry per leg: name, front, side, hip, knee, hip_x.
var legs: Array[Dictionary] = []


func _ready() -> void:
	_build()
	_ready_animation()


func _build() -> void:
	body = _make_pivot(self, Vector3(0, STAND_HEIGHT, 0))
	_attach_mesh(body, _body_voxels())

	neck = _make_pivot(body, Vector3(5, 4, 0))
	_attach_mesh(neck, _neck_voxels())

	head = _make_pivot(neck, Vector3(4, 7, 0))
	_attach_mesh(head, _head_voxels())

	tail = _make_pivot(body, Vector3(-7, 4, 0))
	_attach_mesh(tail, _tail_voxels(false))
	tail_tip = _make_pivot(tail, Vector3(0, -4, 0))
	_attach_mesh(tail_tip, _tail_voxels(true))

	# Order matters for the gait tables: LF, RF, LH, RH.
	_add_leg("LF", true, -1, 5)
	_add_leg("RF", true, 1, 5)
	_add_leg("LH", false, -1, -4)
	_add_leg("RH", false, 1, -4)


func _make_pivot(parent: Node3D, pos_in_voxels: Vector3) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = pos_in_voxels * V
	parent.add_child(pivot)
	return pivot


func _attach_mesh(pivot: Node3D, voxels: Dictionary) -> void:
	var instance := VoxelMesh.make_instance(voxels, V)
	# Cells are designed symmetric around the z = 0 cell, so centre it.
	instance.position = Vector3(0, 0, -0.5 * V)
	pivot.add_child(instance)


func _add_leg(leg_name: String, front: bool, side: int, hip_x: int) -> void:
	var hip := _make_pivot(body, Vector3(hip_x, HIP_Y, 0))
	var knee := _make_pivot(hip, Vector3(0, -UPPER, 0))
	var parts := _leg_voxels(front, side)
	_attach_mesh(hip, parts[0])
	_attach_mesh(knee, parts[1])
	legs.append({"name": leg_name, "front": front, "side": side, "hip": hip, "knee": knee, "hip_x": float(hip_x)})


# --- voxel shapes ---------------------------------------------------------

func _body_voxels() -> Dictionary:
	var v := {}
	VoxelMesh.fill_box(v, Vector3i(-7, 0, -2), Vector3i(6, 5, 2), COAT, 0.05)
	# Round off the barrel: narrower belly and spine, tapered rump.
	VoxelMesh.erase_box(v, Vector3i(-7, 0, -2), Vector3i(6, 0, -2))
	VoxelMesh.erase_box(v, Vector3i(-7, 0, 2), Vector3i(6, 0, 2))
	VoxelMesh.erase_box(v, Vector3i(-7, 5, -2), Vector3i(6, 5, -2))
	VoxelMesh.erase_box(v, Vector3i(-7, 5, 2), Vector3i(6, 5, 2))
	VoxelMesh.erase_box(v, Vector3i(-7, 0, -2), Vector3i(-7, 5, -2))
	VoxelMesh.erase_box(v, Vector3i(-7, 0, 2), Vector3i(-7, 5, 2))
	VoxelMesh.erase_box(v, Vector3i(-7, 0, -1), Vector3i(-7, 0, 1))
	VoxelMesh.erase_box(v, Vector3i(-7, 5, -1), Vector3i(-7, 5, 1))
	VoxelMesh.erase_box(v, Vector3i(6, 5, -1), Vector3i(6, 5, 1))
	# Lighter belly.
	VoxelMesh.fill_box(v, Vector3i(-6, 0, -1), Vector3i(5, 0, 1), BELLY, 0.04)
	# Saddle blanket, trim and seat.
	VoxelMesh.fill_box(v, Vector3i(-1, 5, -1), Vector3i(3, 5, 1), SADDLE, 0.03)
	VoxelMesh.fill_box(v, Vector3i(-1, 4, -2), Vector3i(3, 4, -2), SADDLE, 0.03)
	VoxelMesh.fill_box(v, Vector3i(-1, 4, 2), Vector3i(3, 4, 2), SADDLE, 0.03)
	VoxelMesh.fill_box(v, Vector3i(-1, 3, -2), Vector3i(3, 3, -2), TRIM)
	VoxelMesh.fill_box(v, Vector3i(-1, 3, 2), Vector3i(3, 3, 2), TRIM)
	VoxelMesh.fill_box(v, Vector3i(0, 6, -1), Vector3i(2, 6, 1), LEATHER, 0.04)
	return v


func _neck_voxels() -> Dictionary:
	var v := {}
	for i in 7:
		var xs := int(i * 0.7) - 1
		var thick := 3 if i < 4 else 2
		VoxelMesh.fill_box(v, Vector3i(xs, i, -1), Vector3i(xs + thick - 1, i, 1), COAT, 0.05)
		# Mane runs down the crest of the neck.
		v[Vector3i(xs - 1, i, 0)] = VoxelMesh.jittered(MANE, Vector3i(xs, i, 0), 0.12)
	return v


func _head_voxels() -> Dictionary:
	var v := {}
	# Cranium, cheek and muzzle, built pointing along +X.
	VoxelMesh.fill_box(v, Vector3i(-2, -2, -1), Vector3i(1, 1, 1), COAT, 0.05)
	VoxelMesh.fill_box(v, Vector3i(-1, -3, -1), Vector3i(1, -3, 1), COAT, 0.05)
	VoxelMesh.fill_box(v, Vector3i(2, -2, -1), Vector3i(5, 0, 1), COAT, 0.05)
	VoxelMesh.fill_box(v, Vector3i(6, -2, -1), Vector3i(6, -1, 1), NOSE)
	# White blaze down the face.
	VoxelMesh.fill_box(v, Vector3i(0, 1, 0), Vector3i(1, 1, 0), BLAZE)
	VoxelMesh.fill_box(v, Vector3i(2, 0, 0), Vector3i(5, 0, 0), BLAZE)
	# Eyes on both sides, ears and forelock.
	v[Vector3i(1, 0, -1)] = EYE
	v[Vector3i(1, 0, 1)] = EYE
	VoxelMesh.fill_box(v, Vector3i(-1, 2, -1), Vector3i(-1, 3, -1), COAT_DARK)
	VoxelMesh.fill_box(v, Vector3i(-1, 2, 1), Vector3i(-1, 3, 1), COAT_DARK)
	VoxelMesh.fill_box(v, Vector3i(0, 2, 0), Vector3i(1, 2, 0), MANE)
	v[Vector3i(2, 1, 0)] = MANE
	return v


func _tail_voxels(tip: bool) -> Dictionary:
	var v := {}
	if not tip:
		VoxelMesh.fill_box(v, Vector3i(-2, -1, -1), Vector3i(-1, 0, 1), MANE, 0.1)
		VoxelMesh.fill_box(v, Vector3i(-2, -4, 0), Vector3i(-1, -2, 0), MANE, 0.1)
	else:
		VoxelMesh.fill_box(v, Vector3i(-2, -4, 0), Vector3i(-1, -1, 0), MANE, 0.1)
		VoxelMesh.fill_box(v, Vector3i(-2, -6, 0), Vector3i(-2, -5, 0), COAT_DARK, 0.1)
	return v


## Returns [upper_voxels, lower_voxels] for one leg. Voxels are relative to
## the hip pivot and the knee pivot respectively.
func _leg_voxels(front: bool, side: int) -> Array[Dictionary]:
	var z0 := 1 if side > 0 else -2
	# Far-side legs are a touch darker so the four legs read separately.
	var dim := 1.0 if side > 0 else 0.82
	var coat := _dimmed(COAT, dim)
	var dark := _dimmed(COAT_DARK, dim)
	var sock := _dimmed(SOCK, dim)

	var upper := {}
	VoxelMesh.fill_box(upper, Vector3i(-1, -UPPER, z0), Vector3i(0, 0, z0 + 1), coat, 0.05)
	if not front:
		# Bulkier haunch on the hind legs.
		VoxelMesh.fill_box(upper, Vector3i(-2, -2, z0), Vector3i(0, 0, z0 + 1), coat, 0.05)

	var lower := {}
	VoxelMesh.fill_box(lower, Vector3i(-1, -LOWER + 1, z0), Vector3i(0, -1, z0 + 1), dark, 0.04)
	var sock_rows := 3 if front else 2
	VoxelMesh.fill_box(lower, Vector3i(-1, -LOWER + 1, z0), Vector3i(0, -LOWER + sock_rows, z0 + 1), sock, 0.03)
	VoxelMesh.fill_box(lower, Vector3i(-1, -LOWER, z0), Vector3i(0, -LOWER, z0 + 1), HOOF)
	return [upper, lower]


func _dimmed(color: Color, factor: float) -> Color:
	return Color(color.r * factor, color.g * factor, color.b * factor, color.a)


# --- animation ------------------------------------------------------------

signal jumped
signal landed
## Emitted when a hoof touches down on the ground. Passes the leg index.
signal hoof_strike(leg_index: int)

const JUMP_DURATION := 0.8
const JUMP_PEAK := 1.0
const STUMBLE_DURATION := 0.7

## Gait presets: 0 = walk, 1 = trot, 2 = gallop. Phase offsets are in the
## leg order LF, RF, LH, RH (a cycle is 0..1).
const GAITS: Array[Dictionary] = [
	{"freq": 1.15, "amp": 0.42, "duty": 0.68, "flex": 0.70, "hop": 0.0, "pitch": 0.01,
	 "neck": 0.05, "head": -0.75, "bob": 0.03, "phase": [0.25, 0.75, 0.0, 0.5]},
	{"freq": 1.95, "amp": 0.52, "duty": 0.50, "flex": 1.00, "hop": 0.02, "pitch": 0.03,
	 "neck": -0.12, "head": -0.60, "bob": 0.05, "phase": [0.0, 0.5, 0.5, 0.0]},
	{"freq": 2.40, "amp": 0.92, "duty": 0.34, "flex": 1.50, "hop": 0.14, "pitch": 0.13,
	 "neck": -0.38, "head": -0.20, "bob": 0.10, "phase": [0.45, 0.58, 0.0, 0.12]},
]

## Smoothed gait: 0 = walk .. 2 = gallop. Move `target_gait` to change gait.
var gait := 2.0
var target_gait := 2.0
## Stride cycle position, 0..1.
var phase := 0.0
var stumble_time := 0.0
## Height of the hooves above the ground during a jump, in metres.
var jump_height := 0.0

var _jump_time := -1.0
var _jump_u := 1.0
var _air := 0.0
var _prev_leg_phase: Array[float] = [0.0, 0.0, 0.0, 0.0]

var is_airborne: bool:
	get:
		return _jump_time >= 0.0


func _ready_animation() -> void:
	_apply_pose()


## Ground speed in m/s that keeps the planted hooves from sliding.
func ground_speed() -> float:
	var stride := 2.0 * (UPPER + LOWER) * V * sin(_sample("amp"))
	return stride * _sample("freq") / _sample("duty") * 0.95


func jump() -> bool:
	if _jump_time >= 0.0 or stumble_time > 0.0:
		return false
	_jump_time = 0.0
	jumped.emit()
	return true


func stumble() -> void:
	stumble_time = STUMBLE_DURATION


func hoof_position(leg_index: int) -> Vector3:
	var knee: Node3D = legs[leg_index]["knee"]
	return knee.to_global(Vector3(0, -LOWER * V, 0))


func step(delta: float) -> void:
	gait = move_toward(gait, target_gait, delta * 1.6)
	phase = fposmod(phase + delta * _sample("freq") * (1.0 - 0.75 * _air), 1.0)
	stumble_time = maxf(stumble_time - delta, 0.0)

	if _jump_time >= 0.0:
		_jump_time += delta
		_jump_u = clampf(_jump_time / JUMP_DURATION, 0.0, 1.0)
		jump_height = 4.0 * JUMP_PEAK * _jump_u * (1.0 - _jump_u)
		if _jump_time >= JUMP_DURATION:
			_jump_time = -1.0
			jump_height = 0.0
			landed.emit()
	var air_target := 1.0 if _jump_time >= 0.0 else 0.0
	_air = move_toward(_air, air_target, delta * (10.0 if air_target > 0.0 else 6.0))
	_apply_pose()


func _sample(key: String) -> float:
	var g := clampf(gait, 0.0, 2.0)
	var i := mini(int(g), 1)
	var a: float = GAITS[i][key]
	var b: float = GAITS[i + 1][key]
	return lerpf(a, b, g - i)


func _sample_phase(leg_index: int) -> float:
	var g := clampf(gait, 0.0, 2.0)
	var i := mini(int(g), 1)
	var a: float = GAITS[i]["phase"][leg_index]
	var b: float = GAITS[i + 1]["phase"][leg_index]
	return lerpf(a, b, g - i)


func _apply_pose() -> void:
	var g := clampf(gait, 0.0, 2.0)
	var amp := _sample("amp")
	var duty := _sample("duty")
	var flex := _sample("flex")
	var stumble_amount := 0.0
	if stumble_time > 0.0:
		stumble_amount = sin(PI * (1.0 - stumble_time / STUMBLE_DURATION))

	var pitch := _sample("pitch") * cos(TAU * (phase - 0.25))
	pitch = lerpf(pitch, 0.30 * cos(PI * _jump_u), _air)
	pitch -= 0.30 * stumble_amount
	body.rotation.z = pitch

	# Pose the legs and find the lowest hoof so the body can be seated on it.
	var lowest := INF
	for i in legs.size():
		var leg := legs[i]
		var front: bool = leg["front"]
		var p := fposmod(phase + _sample_phase(i), 1.0)
		var hip_angle: float
		var knee_angle: float
		if p < duty:
			# Stance: the hoof sweeps from forward to back at constant speed, so
			# it stays put on the scrolling ground instead of sliding.
			hip_angle = asin(sin(amp) * (1.0 - 2.0 * p / duty))
			knee_angle = 0.0
		else:
			# Swing: fold the lower leg and bring the foot forward again.
			var u := (p - duty) / (1.0 - duty)
			hip_angle = amp * (-1.0 + 2.0 * smoothstep(0.0, 1.0, u))
			knee_angle = -flex * sin(PI * u)
		if not front:
			hip_angle += 0.30
			knee_angle -= 0.40
		else:
			hip_angle += 0.35 * stumble_amount

		if _air > 0.0:
			var jump_hip := 0.75 if front else lerpf(-0.75, 0.25, _jump_u)
			var jump_knee := -1.45 if front else -1.10
			hip_angle = lerpf(hip_angle, jump_hip, _air)
			knee_angle = lerpf(knee_angle, jump_knee, _air)

		var hip: Node3D = leg["hip"]
		var knee: Node3D = leg["knee"]
		hip.rotation.z = hip_angle
		knee.rotation.z = knee_angle

		# Forward kinematics of the hoof sole in body space, in voxels.
		var lower_angle := hip_angle + knee_angle
		var foot := Vector2(leg["hip_x"], HIP_Y)
		foot += Vector2(sin(hip_angle), -cos(hip_angle)) * UPPER
		foot += Vector2(sin(lower_angle), -cos(lower_angle)) * LOWER
		var foot_y := foot.x * sin(pitch) + foot.y * cos(pitch)
		foot_y -= absf(sin(lower_angle + pitch))  # tilted hoof: lowest corner
		lowest = minf(lowest, foot_y)

		# Report touch-downs (phase wrapping through 0 starts the stance).
		if p < _prev_leg_phase[i] and _air < 0.5:
			hoof_strike.emit(i)
		_prev_leg_phase[i] = p

	var hop := _sample("hop") * pow(maxf(0.0, cos(TAU * (phase - 0.97))), 3.0)
	body.position.y = -lowest * V + hop + jump_height

	# Neck and head counter-bob against the body; both stretch out at speed.
	var bob := sin(TAU * (phase - 0.1))
	var neck_angle := _sample("neck") + _sample("bob") * bob - 0.30 * stumble_amount
	var head_angle := _sample("head") - 0.5 * _sample("bob") * bob - 0.25 * stumble_amount
	neck_angle = lerpf(neck_angle, -0.30, _air)
	head_angle = lerpf(head_angle, -0.25, _air)
	neck.rotation.z = neck_angle
	head.rotation.z = head_angle

	# The tail streams out behind at speed and flutters along the stride.
	var speed_t := g * 0.5
	tail.rotation.z = -lerpf(0.10, 1.05, speed_t) - 0.10 * _air + 0.06 * sin(TAU * (phase - 0.2))
	tail.rotation.y = 0.12 * sin(TAU * phase * 2.0)
	tail_tip.rotation.z = -0.25 * speed_t + (0.15 + 0.35 * speed_t) * sin(TAU * (phase - 0.35))
