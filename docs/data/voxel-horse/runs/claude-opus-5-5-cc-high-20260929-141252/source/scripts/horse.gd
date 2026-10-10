extends Node3D
## A voxel horse assembled from code and animated procedurally.
## Legs use two-bone IK so hooves stay planted while the body moves.

signal jumped
signal bumped

const Voxel := preload("res://scripts/voxel.gd")

const S := 0.12 # voxel size in meters
const L1 := 5.0 * S # hip -> knee
const L2 := 5.0 * S # knee -> hoof bottom
const BODY_Y := 10.9 * S # body pivot height when standing
const JUMP_VELOCITY := 6.2
const GRAVITY := 18.0

# Gait tables, indexed by gait: stand, walk, trot, canter, gallop.
const GAIT_NAMES := ["Standing", "Walk", "Trot", "Canter", "Gallop"]
const GAIT_SPEED := [0.0, 1.8, 4.2, 7.5, 12.5] # m/s
const STRIDE := [1.4, 1.4, 2.1, 3.0, 4.4] # meters travelled per stride cycle
const DUTY := [0.62, 0.62, 0.46, 0.4, 0.34] # fraction of the cycle a hoof is grounded
const LIFT := [0.0, 0.12, 0.26, 0.32, 0.4] # hoof lift height during swing
const CROUCH := [0.0, 0.03, 0.06, 0.08, 0.11] # body lowered to lengthen reach
const BOB := [0.0, 0.015, 0.045, 0.06, 0.08]
const PITCH := [0.0, 0.0, 0.01, 0.06, 0.08]
const NOD := [0.0, 0.05, 0.03, 0.1, 0.14]
const NECK := [-0.75, -0.8, -0.85, -0.95, -1.1]
# Cycle phase at which each hoof touches down. Order: LF, RF, LH, RH.
const TOUCHDOWN := [
	[0.25, 0.75, 0.0, 0.5],
	[0.25, 0.75, 0.0, 0.5],
	[0.0, 0.5, 0.5, 0.0],
	[0.6, 0.33, 0.33, 0.0],
	[0.5, 0.4, 0.1, 0.0],
]

const COAT := Color(0.55, 0.31, 0.16)
const COAT_LIGHT := Color(0.63, 0.4, 0.24)
const DARK := Color(0.1, 0.07, 0.05)
const WHITE := Color(0.93, 0.91, 0.86)
const HOOF := Color(0.22, 0.2, 0.18)
const EYE := Color(0.02, 0.02, 0.02)
const NOSE := Color(0.24, 0.16, 0.12)

var world: Node = null

var speed := 0.0
var target_gait := 4
var distance := 0.0
var height := 0.0
var airborne := false
var gait_value := 0.0

var _vy := 0.0
var _yaw_rate := 0.0
var _phase := 0.0
var _time := 0.0
var _air := 0.0
var _stumble := 0.0
var _rear := 0.0
var _idle := 0.0
var _graze := 0.0

var _visual: Node3D
var _body: Node3D
var _neck: Node3D
var _head: Node3D
var _tail: Node3D
var _tail_tip: Node3D
var _legs: Array[Dictionary] = []
var _dust: CPUParticles3D


func _ready() -> void:
	_build()


func forward() -> Vector3:
	return -global_transform.basis.z


func gait_name() -> String:
	if speed < 0.05:
		return GAIT_NAMES[0]
	return GAIT_NAMES[clampi(roundi(gait_value), 1, 4)]


func bump() -> void:
	if _stumble > 0.0:
		return
	_stumble = 1.0
	speed *= 0.15
	bumped.emit()


# --- Construction -----------------------------------------------------------

func _part(parent: Node3D, vox: Dictionary, pos: Vector3, pivot := Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = Voxel.build(vox, S, pivot)
	mi.position = pos
	parent.add_child(mi)
	return mi


func _build() -> void:
	_visual = Node3D.new()
	add_child(_visual)

	# Body: x across, y up, z along the body (front is -z).
	var b := {}
	Voxel.box(b, Vector3i(-3, 1, -8), Vector3i(3, 6, 8), COAT)
	for z in range(-8, 8):
		for x in [-3, 2]:
			b.erase(Vector3i(x, 5, z))
			b.erase(Vector3i(x, 1, z))
	Voxel.box(b, Vector3i(-2, 0, -7), Vector3i(2, 1, 7), COAT_LIGHT)
	Voxel.box(b, Vector3i(-2, 2, -9), Vector3i(2, 6, -8), COAT)
	Voxel.box(b, Vector3i(-1, 6, -8), Vector3i(1, 7, -4), COAT)
	Voxel.box(b, Vector3i(-2, 6, 3), Vector3i(2, 7, 8), COAT)
	_body = _part(_visual, b, Vector3(0, BODY_Y, 0), Vector3(0, 3, 0))

	# Neck with mane.
	var n := {}
	Voxel.box(n, Vector3i(-2, -1, -2), Vector3i(2, 8, 2), COAT)
	Voxel.box(n, Vector3i(-1, -1, 2), Vector3i(1, 9, 3), DARK)
	for y in range(0, 8, 2):
		Voxel.box(n, Vector3i(-1, y, 3), Vector3i(1, y + 1, 4), DARK)
	_neck = _part(_body, n, Vector3(0, 2 * S, -7 * S))

	# Head: skull, muzzle, ears, eyes, blaze.
	var h := {}
	Voxel.box(h, Vector3i(-2, -2, -3), Vector3i(2, 2, 2), COAT)
	Voxel.box(h, Vector3i(-2, -2, -7), Vector3i(2, 0, -3), COAT)
	Voxel.box(h, Vector3i(-1, 0, -7), Vector3i(1, 1, -3), COAT)
	Voxel.box(h, Vector3i(-2, -2, -7), Vector3i(2, 0, -6), NOSE)
	Voxel.box(h, Vector3i(-1, 0, -7), Vector3i(1, 1, -2), WHITE)
	Voxel.box(h, Vector3i(-1, 1, -3), Vector3i(1, 2, -1), WHITE)
	h[Vector3i(-2, -1, -7)] = EYE
	h[Vector3i(1, -1, -7)] = EYE
	h[Vector3i(-2, 1, -2)] = EYE
	h[Vector3i(1, 1, -2)] = EYE
	Voxel.box(h, Vector3i(-2, 2, 0), Vector3i(-1, 4, 1), COAT)
	Voxel.box(h, Vector3i(1, 2, 0), Vector3i(2, 4, 1), COAT)
	Voxel.box(h, Vector3i(-1, 2, -1), Vector3i(1, 3, 1), DARK)
	Voxel.box(h, Vector3i(-1, 1, 1), Vector3i(1, 3, 3), DARK)
	_head = _part(_neck, h, Vector3(0, 8 * S, 0))

	# Tail in two segments so it can flow.
	var t := {}
	Voxel.box(t, Vector3i(-1, -3, 0), Vector3i(1, 1, 2), DARK)
	_tail = _part(_body, t, Vector3(0, 3 * S, 8 * S))
	var tt := {}
	Voxel.box(tt, Vector3i(-1, -7, 0), Vector3i(1, 1, 2), DARK)
	Voxel.box(tt, Vector3i(-1, -8, 0), Vector3i(1, -7, 1), DARK)
	_tail_tip = _part(_tail, tt, Vector3(0, -3 * S, 0))

	# Legs: LF, RF, LH, RH. The horse's right side is +x.
	_add_leg(true, -1, true)
	_add_leg(true, 1, false)
	_add_leg(false, -1, false)
	_add_leg(false, 1, true)

	# Dust kicked up by the hooves.
	_dust = CPUParticles3D.new()
	_dust.amount = 48
	_dust.lifetime = 0.9
	_dust.local_coords = false
	_dust.emitting = false
	_dust.position = Vector3(0, 0.05, 0.4)
	_dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_dust.emission_box_extents = Vector3(0.35, 0.05, 0.9)
	_dust.direction = Vector3(0, 1, 0.6)
	_dust.spread = 35.0
	_dust.initial_velocity_min = 0.6
	_dust.initial_velocity_max = 1.8
	_dust.gravity = Vector3(0, -1.2, 0)
	_dust.damping_min = 1.0
	_dust.damping_max = 2.0
	_dust.scale_amount_min = 0.6
	_dust.scale_amount_max = 1.3
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1))
	curve.add_point(Vector2(1, 0))
	_dust.scale_amount_curve = curve
	var dm := BoxMesh.new()
	dm.size = Vector3.ONE * 0.1
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.72, 0.64, 0.5)
	mat.roughness = 1.0
	dm.material = mat
	_dust.mesh = dm
	_dust.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_dust)


func _add_leg(front: bool, side: int, sock: bool) -> void:
	var up := {}
	Voxel.box(up, Vector3i(-1, -5, -1), Vector3i(1, 1, 1), COAT)
	if front:
		Voxel.box(up, Vector3i(-1, -2, -2), Vector3i(1, 1, 1), COAT)
	else:
		Voxel.box(up, Vector3i(-1, -3, -1), Vector3i(1, 1, 2), COAT)
	var lo := {}
	Voxel.box(lo, Vector3i(-1, -4, -1), Vector3i(1, 1, 1), DARK)
	if sock:
		Voxel.box(lo, Vector3i(-1, -4, -1), Vector3i(1, -2, 1), WHITE)
	Voxel.box(lo, Vector3i(-1, -5, -1), Vector3i(1, -4, 1), HOOF)
	var hip := Vector3(side * 2 * S, -S, (-6 if front else 6) * S)
	var upper := _part(_body, up, hip)
	var lower := _part(upper, lo, Vector3(0, -L1, 0))
	_legs.append({"upper": upper, "lower": lower, "front": front, "hip": hip})


# --- Simulation --------------------------------------------------------------

func _process(delta: float) -> void:
	delta = minf(delta, 0.05)
	_time += delta
	_handle_input()
	_move(delta)
	if world:
		world.handle_horse(self)
	_animate(delta)


func _handle_input() -> void:
	if Input.is_action_just_pressed("faster"):
		target_gait = mini(target_gait + 1, 4)
	if Input.is_action_just_pressed("slower"):
		target_gait = maxi(target_gait - 1, 0)
	if Input.is_action_just_pressed("jump") and not airborne and _rear <= 0.0:
		if speed > 1.0 and _stumble <= 0.0:
			airborne = true
			_vy = JUMP_VELOCITY
			jumped.emit()
		elif speed <= 1.0:
			_rear = 1.0


func _move(delta: float) -> void:
	var target: float = GAIT_SPEED[target_gait]
	if _stumble > 0.0:
		_stumble = maxf(0.0, _stumble - delta)
		target = minf(target, GAIT_SPEED[1])
	if _rear > 0.0:
		_rear = maxf(0.0, _rear - delta / 1.6)
		target = 0.0
	if not airborne:
		speed = move_toward(speed, target, (4.0 if target > speed else 8.0) * delta)

	var steer := Input.get_axis("steer_right", "steer_left")
	var turn := lerpf(2.0, 1.2, clampf(speed / 12.5, 0.0, 1.0))
	if airborne:
		turn *= 0.5
	_yaw_rate = lerpf(_yaw_rate, steer * turn, 1.0 - exp(-8.0 * delta))
	rotation.y += _yaw_rate * delta
	position += forward() * speed * delta
	distance += speed * delta

	if airborne:
		_vy -= GRAVITY * delta
		height += _vy * delta
		if height <= 0.0:
			height = 0.0
			_vy = 0.0
			airborne = false


func _table(table: Array, i: int, f: float) -> float:
	return lerpf(table[i], table[i + 1], f)


func _solve_leg(leg: Dictionary, target: Vector3) -> Vector2:
	# Two-bone IK in the leg's plane. Angle 0 points straight down; positive swings forward.
	var d: Vector3 = target - leg.hip
	var dist := clampf(Vector2(d.z, d.y).length(), 0.25, (L1 + L2) * 0.999)
	var theta := atan2(-d.z, -d.y)
	var a := acos(clampf((L1 * L1 + dist * dist - L2 * L2) / (2.0 * L1 * dist), -1.0, 1.0))
	var k := PI - acos(clampf((L1 * L1 + L2 * L2 - dist * dist) / (2.0 * L1 * L2), -1.0, 1.0))
	if leg.front:
		return Vector2(theta + a, -k) # knee points forward
	return Vector2(theta - a, k) # hock points backward


func _animate(delta: float) -> void:
	# Continuous gait value derived from speed (0 = stand ... 4 = gallop).
	var g := 4.0
	for i in 4:
		if speed <= GAIT_SPEED[i + 1]:
			g = i + inverse_lerp(GAIT_SPEED[i], GAIT_SPEED[i + 1], speed)
			break
	gait_value = g
	var gi := mini(int(g), 3)
	var gf := g - gi
	var duty := _table(DUTY, gi, gf)
	var crouch := _table(CROUCH, gi, gf)
	var lift := _table(LIFT, gi, gf)
	var settle := clampf(g, 0.0, 1.0)
	var run := clampf(speed / 12.5, 0.0, 1.0)
	var canter := clampf(g - 2.0, 0.0, 1.0) # blends 2-beat body motion into 1-beat

	var hip_h := BODY_Y - S - crouch
	var max_reach := sqrt(maxf(0.0, pow((L1 + L2) * 0.985, 2.0) - hip_h * hip_h))
	var reach := minf(duty * _table(STRIDE, gi, gf) * 0.5, max_reach) * settle
	if reach > 0.005 and not airborne:
		_phase = fposmod(_phase + speed * duty / (2.0 * reach) * delta, 1.0)

	_air = move_toward(_air, 1.0 if airborne else 0.0, delta * 7.0)
	var rear := sin(_rear * PI) if _rear > 0.0 else 0.0

	# Idle grazing.
	if speed < 0.05 and _rear <= 0.0:
		_idle += delta
	else:
		_idle = 0.0
	var graze_target := 1.0 if _idle > 3.0 and fmod(_idle, 11.0) < 7.5 else 0.0
	_graze = move_toward(_graze, graze_target, delta * 0.8)
	var graze := smoothstep(0.0, 1.0, _graze)

	# Body bob, pitch and lean.
	var bob_wave := lerpf(cos(TAU * 2.0 * (_phase - 0.48)), cos(TAU * (_phase - 0.92)), canter)
	var stumble := sin(_stumble * PI)
	_body.position.y = BODY_Y - crouch + _table(BOB, gi, gf) * bob_wave * (1.0 - _air) \
			+ rear * 6.0 * S * sin(0.7) - stumble * 0.08
	_body.rotation.x = _table(PITCH, gi, gf) * cos(TAU * (_phase - 0.3)) * canter * (1.0 - _air) \
			+ clampf(_vy * 0.045, -0.3, 0.3) * _air + rear * 0.7 - stumble * 0.15
	_visual.position.y = height
	_visual.rotation.z = lerpf(_visual.rotation.z, clampf(_yaw_rate * speed * 0.012, -0.2, 0.2), 1.0 - exp(-6.0 * delta))

	# Neck and head.
	var nod_wave := lerpf(cos(TAU * 2.0 * (_phase - 0.23)), cos(TAU * (_phase - 0.7)), canter)
	var nod := _table(NOD, gi, gf) * nod_wave * (1.0 - _air)
	var neck := _table(NECK, gi, gf) - nod + sin(_time * 0.9) * 0.03 * (1.0 - run)
	neck = lerpf(neck, -2.3, graze) + rear * 0.6 - _air * 0.15 + stumble * 0.4
	var head_pitch := lerpf(-0.8, -0.5, run) + nod * 0.5
	head_pitch = lerpf(head_pitch, -1.35, graze) + rear * 0.3
	_neck.rotation.x = neck
	_head.rotation.x = head_pitch - neck
	_head.rotation.y = sin(_time * 0.7) * 0.08 * (1.0 - run) * (1.0 - graze)

	# Tail streams out behind at speed and swishes when idle.
	_tail.rotation.x = lerpf(-0.3, -1.2, run) + sin(TAU * _phase) * 0.12 * run - _air * 0.3
	_tail.rotation.z = sin(_time * 1.6) * 0.25 * (1.0 - run) + sin(_time * 9.0) * 0.05 * run
	_tail_tip.rotation.x = -0.1 * run + sin(TAU * _phase + 1.2) * 0.3 * run + sin(_time * 1.6 - 0.8) * 0.05

	# Legs.
	var inv := (_visual.transform * _body.transform).affine_inverse()
	for i in 4:
		var leg: Dictionary = _legs[i]
		var td := _table([TOUCHDOWN[gi][i], TOUCHDOWN[gi + 1][i]], 0, gf)
		var p := fposmod(_phase - td, 1.0)
		var fz := 0.0
		var fy := 0.0
		if p < duty:
			fz = lerpf(-reach, reach, p / duty)
		else:
			var s := (p - duty) / (1.0 - duty)
			fz = lerpf(reach, -reach, smoothstep(0.0, 1.0, s))
			fy = sin(s * PI) * lift * settle
			if leg.front:
				fz += sin(s * PI) * lift * 0.4
		var hip: Vector3 = leg.hip
		var ang := _solve_leg(leg, inv * Vector3(hip.x, fy, hip.z + fz))
		var tuck := Vector2(1.0, -2.0) if leg.front else Vector2(-0.35, 1.5)
		ang = ang.lerp(tuck, _air)
		if leg.front and rear > 0.0:
			var paw := Vector2(0.9 + sin(_time * 10.0 + i) * 0.35, -1.7)
			ang = ang.lerp(paw, clampf(rear * 1.5, 0.0, 1.0))
		leg.upper.rotation.x = ang.x
		leg.lower.rotation.x = ang.y

	_dust.emitting = not airborne and speed > 5.0
