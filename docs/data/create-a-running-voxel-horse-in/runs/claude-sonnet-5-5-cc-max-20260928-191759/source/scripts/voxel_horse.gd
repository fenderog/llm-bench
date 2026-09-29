extends Node3D
## A voxel horse assembled from rigid parts, with a procedural gait.
##
## The node faces -Z (Godot's forward) and its origin sits on the ground.
## A controller only has to set `speed`; the horse picks a gait (stand, walk,
## trot, canter, gallop), advances its stride phase and poses itself.
##
## How the animation works: every hoof follows a foot-target path in the
## horse's own frame - a straight stance line (so it stays planted while the
## world scrolls past) and a swing arc back to the front - and a two-bone IK
## solve bends knee or hock to reach it. Body bounce and pitch come from which
## legs are currently carrying weight, so they stay in step with the hooves
## for every gait.

signal hoof_struck(leg: int, ground_position: Vector3, strength: float)
signal landed(strength: float)

const VoxelModel := preload("res://scripts/voxel_model.gd")
const HorseModel := preload("res://scripts/horse_model.gd")

const VOXEL := HorseModel.VOXEL
const INV_VOXEL := 1.0 / VOXEL
const MANE_REST_ANGLE := deg_to_rad(55.0)

enum Leg { HIND_LEFT, HIND_RIGHT, FORE_LEFT, FORE_RIGHT }
enum Gait { STAND, WALK, TROT, CANTER, GALLOP }

## Per-gait tuning. Lengths are metres, angles radians.
##   stride   distance covered per full leg cycle
##   offsets  touchdown phase of [hind-left, hind-right, fore-left, fore-right]
##   duty     fraction of the cycle a hoof is on the ground [hind, fore]
##   sweep    how far a planted hoof travels back relative to the body [hind, fore]
##   reach    share of the sweep that lies ahead of the hip at touchdown
##   lift     peak hoof height above the ground during the swing [hind, fore]
##   match    how strongly the swing continues the backward stance motion
##   height   body height offset (negative crouches)
##   bounce   how far the body sinks per unit of leg support
##   pitch    nose-up per unit of hind support / nose-down per unit of fore support
##   neck, neck_bob, head   neck angle, its rocking amplitude, head angle
##   tail     tail base angle (negative streams backwards)
const GAITS := [
	{"name": "Standing", "stride": 1.0, "offsets": [0.0, 0.5, 0.25, 0.75], "duty": [1.0, 1.0],
		"sweep": [0.0, 0.0], "reach": 0.5, "lift": [0.0, 0.0], "match": 0.0, "height": -0.03,
		"bounce": 0.0, "pitch": [0.0, 0.0], "neck": 0.0, "neck_bob": 0.0, "head": 0.05,
		"tail": -0.08},
	{"name": "Walk", "stride": 1.5, "offsets": [0.0, 0.5, 0.25, 0.75], "duty": [0.66, 0.66],
		"sweep": [0.80, 0.80], "reach": 0.5, "lift": [0.09, 0.12], "match": 0.3, "height": -0.045,
		"bounce": 0.010, "pitch": [0.015, 0.015], "neck": -0.05, "neck_bob": 0.05, "head": 0.10,
		"tail": -0.15},
	{"name": "Trot", "stride": 2.4, "offsets": [0.5, 0.0, 0.0, 0.5], "duty": [0.42, 0.42],
		"sweep": [0.82, 0.82], "reach": 0.5, "lift": [0.16, 0.19], "match": 0.4, "height": -0.06,
		"bounce": 0.022, "pitch": [0.02, 0.02], "neck": -0.15, "neck_bob": 0.04, "head": 0.12,
		"tail": -0.55},
	{"name": "Canter", "stride": 3.1, "offsets": [0.0, 0.32, 0.36, 0.62], "duty": [0.34, 0.32],
		"sweep": [0.90, 0.90], "reach": 0.55, "lift": [0.22, 0.27], "match": 0.5, "height": -0.09,
		"bounce": 0.032, "pitch": [0.06, 0.05], "neck": -0.28, "neck_bob": 0.09, "head": 0.20,
		"tail": -0.9},
	{"name": "Gallop", "stride": 4.0, "offsets": [0.0, 0.14, 0.36, 0.50], "duty": [0.28, 0.26],
		"sweep": [0.98, 0.98], "reach": 0.55, "lift": [0.28, 0.34], "match": 0.55, "height": -0.12,
		"bounce": 0.05, "pitch": [0.10, 0.09], "neck": -0.46, "neck_bob": 0.10, "head": 0.25,
		"tail": -1.2},
]
## Speed (m/s) above which gait i steps up to i+1, and below which it steps down to i-1.
const GAIT_UP := [0.35, 2.7, 5.4, 8.0]
const GAIT_DOWN := [0.0, 0.2, 2.4, 4.9, 7.5]
const GAIT_BLEND_TIME := 0.3

const JUMP_VELOCITY := 5.6
const GRAVITY := 13.5
const HIND_STAND_DX := -1.5          # hind hooves sit slightly behind the hip (voxels)
const HOOF_SWING_ANGLE := -0.6       # hoof trails backwards while the leg is in the air

# Layout of the pose vector (all angles in radians, body offset in metres).
const P_BODY_Y := 0
const P_BODY_PITCH := 1
const P_NECK := 2
const P_HEAD := 3
const P_TAIL := 4
const P_MANE := P_TAIL + HorseModel.TAIL_SEGMENTS
const P_LEG := P_MANE + HorseModel.MANE_TUFTS
const POSE_SIZE := P_LEG + 12

var model: Node3D          # rotated so the model's +X points along -Z
var body: MeshInstance3D
var neck: MeshInstance3D
var head: MeshInstance3D
var tail: Array[MeshInstance3D] = []
var mane: Array[MeshInstance3D] = []
## One entry per Leg: {hip, knee, hoof: MeshInstance3D, front: bool, side: float}
var legs: Array[Dictionary] = []

## Forward speed in m/s; set by whoever drives the horse.
var speed := 0.0
var gait: int = Gait.STAND
var phase := 0.0
## Height of the horse above the ground while jumping.
var height := 0.0

var _material: StandardMaterial3D
var _time := 0.0
var _pose := PackedFloat32Array()
var _from_pose := PackedFloat32Array()
var _blend := 1.0
var _prev_u := PackedFloat32Array([0.0, 0.0, 0.0, 0.0])
var _airborne := false
var _air_time := 0.0
var _air_total := 1.0
var _vy := 0.0
var _manual := false


func _init() -> void:
	_build()
	_pose.resize(POSE_SIZE)
	_from_pose.resize(POSE_SIZE)


# ---- Construction -----------------------------------------------------------

func _part(vm: RefCounted, pivot: Vector3, parent: Node3D, offset_vox: Vector3,
		part_name: String, mesh: ArrayMesh = null) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = part_name
	if mesh == null:
		mesh = vm.build_mesh(VOXEL, pivot)
		mesh.surface_set_material(0, _material)
	mi.mesh = mesh
	mi.position = offset_vox * VOXEL
	parent.add_child(mi)
	return mi


func _build() -> void:
	_material = VoxelModel.make_material()
	model = Node3D.new()
	model.name = "Model"
	model.rotation_degrees.y = 90.0
	# Model +X runs along -Z; shift so the body pivot sits over the node origin.
	model.position = Vector3(0.0, 0.0, HorseModel.BODY_PIVOT.x * VOXEL)
	add_child(model)

	var bp := HorseModel.BODY_PIVOT
	body = _part(HorseModel.build_torso(), bp, model, bp, "Body")

	var np := HorseModel.NECK_PIVOT
	var hp := HorseModel.HEAD_PIVOT
	neck = _part(HorseModel.build_neck(), np, body, np - bp, "Neck")
	head = _part(HorseModel.build_head(), hp, neck, hp - np, "Head")
	_build_mane(np)

	# Tail: a chain of segments hanging from the croup.
	var tp := HorseModel.TAIL_PIVOT
	var parent: Node3D = body
	for i in HorseModel.TAIL_SEGMENTS:
		var off := (tp - bp) if i == 0 else Vector3(0.0, -HorseModel.TAIL_SEG_LEN, 0.0)
		var seg := _part(HorseModel.build_tail_segment(i), Vector3.ZERO, parent, off, "Tail%d" % i)
		tail.append(seg)
		parent = seg

	_build_legs()


func _build_mane(np: Vector3) -> void:
	var a := np + Vector3(-1.5, -1.5, 0.0)
	var b := HorseModel.neck_end()
	var neck_vec := Vector2(b.x - a.x, b.y - a.y)
	var axis := neck_vec.normalized()
	var up_back := Vector2(-axis.y, axis.x)          # from the throat over the crest
	var lengths := [3.2, 3.8, 3.8, 3.6, 3.4, 3.2, 3.0]
	var meshes: Dictionary = {}
	for i in HorseModel.MANE_TUFTS:
		var t := 0.95 - float(i) * 0.125             # 0 = base of neck, 1 = poll
		var crest := Vector2(a.x, a.y) + neck_vec * t + up_back * (lerpf(4.9, 2.8, t) - 0.7)
		var key: float = lengths[i]
		if not meshes.has(key):
			var mesh := HorseModel.build_mane_tuft(key, 1.2).build_mesh(VOXEL, Vector3.ZERO)
			mesh.surface_set_material(0, _material)
			meshes[key] = mesh
		var mi := _part(null, Vector3.ZERO, neck, Vector3(crest.x - np.x, crest.y - np.y, 0.0),
				"Mane%d" % i, meshes[key])
		mi.rotation.z = MANE_REST_ANGLE
		mane.append(mi)


func _build_legs() -> void:
	var bp := HorseModel.BODY_PIVOT
	var shared: Dictionary = {}
	for front: bool in [false, true]:
		var upper := HorseModel.build_upper_leg(front).build_mesh(VOXEL, Vector3.ZERO)
		var lower := HorseModel.build_lower_leg(front).build_mesh(VOXEL, Vector3.ZERO)
		upper.surface_set_material(0, _material)
		lower.surface_set_material(0, _material)
		shared[front] = [upper, lower]
	var hoof_mesh := HorseModel.build_hoof().build_mesh(VOXEL, Vector3.ZERO)
	hoof_mesh.surface_set_material(0, _material)

	legs.resize(4)
	for leg: int in [Leg.HIND_LEFT, Leg.HIND_RIGHT, Leg.FORE_LEFT, Leg.FORE_RIGHT]:
		var front := leg >= Leg.FORE_LEFT
		var side := -1.0 if (leg == Leg.HIND_LEFT or leg == Leg.FORE_LEFT) else 1.0
		var pivot: Vector3 = HorseModel.FORE_PIVOT if front else HorseModel.HIND_PIVOT
		pivot.z *= side
		var upper_len := HorseModel.FORE_UPPER if front else HorseModel.HIND_UPPER
		var lower_len := HorseModel.FORE_LOWER if front else HorseModel.HIND_LOWER
		var tag := ("Fore" if front else "Hind") + ("L" if side < 0.0 else "R")
		var hip := _part(null, Vector3.ZERO, body, pivot - bp, tag + "Hip", shared[front][0])
		var knee := _part(null, Vector3.ZERO, hip, Vector3(0.0, -upper_len, 0.0), tag + "Knee", shared[front][1])
		var hoof := _part(null, Vector3.ZERO, knee, Vector3(0.0, -lower_len, 0.0), tag + "Hoof", hoof_mesh)
		legs[leg] = {"hip": hip, "knee": knee, "hoof": hoof, "front": front, "side": side}


# ---- Public API -------------------------------------------------------------

func gait_name() -> String:
	return GAITS[gait]["name"]


## Strides (full leg cycles) per second at the current speed.
func cadence() -> float:
	return speed / float(GAITS[gait]["stride"])


func is_airborne() -> bool:
	return _airborne


func jump() -> void:
	if _airborne or _manual:
		return
	_airborne = true
	_air_time = 0.0
	_vy = JUMP_VELOCITY
	_air_total = 2.0 * JUMP_VELOCITY / GRAVITY


## Freezes the horse in a specific pose (used by the debugging tools).
func apply_debug_pose(gait_id: int, ph: float, spd: float) -> void:
	_manual = true
	gait = gait_id
	phase = ph
	speed = spd
	_pose = _compute_pose(GAITS[gait], phase, speed, 0.5)
	_apply_pose(_pose)


## Freezes the horse mid-jump (used by the debugging tools).
func apply_debug_leap(tn: float, spd: float) -> void:
	_manual = true
	speed = spd
	_pose = _leap_pose(tn, 0.5)
	_apply_pose(_pose)


# ---- Per-frame update -------------------------------------------------------

func _process(delta: float) -> void:
	if _manual:
		return
	_time += delta
	_select_gait()
	var g: Dictionary = GAITS[gait]
	phase = fposmod(phase + cadence() * delta, 1.0)
	_update_jump(delta)

	var live := _compute_pose(g, phase, speed, _time)
	if _airborne:
		var tn := clampf(_air_time / _air_total, 0.0, 1.0)
		var w := smoothstep(0.0, 0.15, tn) * (1.0 - smoothstep(0.82, 1.0, tn))
		live = _lerp_pose(live, _leap_pose(tn, _time), w)
	if _blend < 1.0:
		_blend = minf(1.0, _blend + delta / GAIT_BLEND_TIME)
		live = _lerp_pose(_from_pose, live, smoothstep(0.0, 1.0, _blend))
	_pose = live
	_apply_pose(_pose)
	_detect_strikes(g)


func _select_gait() -> void:
	var new_gait := gait
	while new_gait < Gait.GALLOP and speed > GAIT_UP[new_gait]:
		new_gait += 1
	while new_gait > Gait.STAND and speed < GAIT_DOWN[new_gait]:
		new_gait -= 1
	if new_gait == gait:
		return
	_from_pose = _pose.duplicate()
	_blend = 0.0
	gait = new_gait
	_reset_strike_tracking()


func _update_jump(delta: float) -> void:
	if not _airborne:
		return
	_air_time += delta
	_vy -= GRAVITY * delta
	height += _vy * delta
	if height <= 0.0 and _vy < 0.0:
		height = 0.0
		_airborne = false
		landed.emit(clampf(speed / 10.0, 0.3, 1.0))
	position.y = height


func _reset_strike_tracking() -> void:
	var offsets: Array = GAITS[gait]["offsets"]
	for i in 4:
		_prev_u[i] = fposmod(phase - float(offsets[i]), 1.0)


func _detect_strikes(g: Dictionary) -> void:
	var offsets: Array = g["offsets"]
	for i in 4:
		var u := fposmod(phase - float(offsets[i]), 1.0)
		if u < _prev_u[i] - 0.5 and not _airborne and gait != Gait.STAND:
			var hoof: Node3D = legs[i]["hoof"]
			var p := hoof.global_position
			p.y = global_position.y
			hoof_struck.emit(i, p, clampf(speed / 10.0, 0.25, 1.0))
		_prev_u[i] = u


# ---- Pose computation ---------------------------------------------------------

## Weight carried by (hind pair, fore pair) at cycle position `ph`.
func _support(g: Dictionary, ph: float) -> Vector2:
	var offsets: Array = g["offsets"]
	var duty: Array = g["duty"]
	var out := Vector2.ZERO
	for i in 4:
		var d: float = duty[1] if i >= 2 else duty[0]
		var u := fposmod(ph - float(offsets[i]), 1.0)
		if u < d:
			var s := sin(PI * u / d)
			if i >= 2:
				out.y += s
			else:
				out.x += s
	return out


static func _hermite(p0: float, p1: float, m0: float, m1: float, w: float) -> float:
	var w2 := w * w
	var w3 := w2 * w
	return (2.0 * w3 - 3.0 * w2 + 1.0) * p0 + (w3 - 2.0 * w2 + w) * m0 \
			+ (-2.0 * w3 + 3.0 * w2) * p1 + (w3 - w2) * m1


## Two-bone IK in the sagittal plane. `target` is relative to the hip (x
## forward, y up). Returns (upper angle, lower angle relative to upper); angles
## are measured from straight down, positive swinging the foot forward. `bend`
## is +1 for a knee that points forwards, -1 for a hock that points backwards.
static func _solve_leg(target: Vector2, a: float, b: float, bend: float) -> Vector2:
	var dist := clampf(target.length(), absf(a - b) + 0.05, a + b - 0.02)
	var toward := atan2(target.x, -target.y)
	var cos_g := (a * a + dist * dist - b * b) / (2.0 * a * dist)
	var gamma := acos(clampf(cos_g, -1.0, 1.0))
	var upper := toward + bend * gamma
	var knee := Vector2(sin(upper), -cos(upper)) * a
	var shin := target - knee
	var lower := atan2(shin.x, -shin.y)
	return Vector2(upper, lower - upper)


func _compute_pose(g: Dictionary, ph: float, spd: float, t: float) -> PackedFloat32Array:
	var pose := PackedFloat32Array()
	pose.resize(POSE_SIZE)
	var offsets: Array = g["offsets"]
	var duty: Array = g["duty"]
	var pitch_k: Array = g["pitch"]
	var sweep: Array = g["sweep"]
	var lift: Array = g["lift"]

	var u := PackedFloat32Array([0.0, 0.0, 0.0, 0.0])
	for i in 4:
		u[i] = fposmod(ph - float(offsets[i]), 1.0)
	var sup := _support(g, ph)          # (hind, fore) weight now
	var idle := clampf(1.0 - spd / 1.2, 0.0, 1.0)
	var wind := clampf(spd / 9.0, 0.0, 1.0)

	# --- Body ---
	var body_y: float = float(g["height"]) - float(g["bounce"]) * (sup.x + sup.y)
	body_y += 0.004 * sin(t * 2.2) * idle
	var body_pitch: float = float(pitch_k[0]) * sup.x - float(pitch_k[1]) * sup.y
	pose[P_BODY_Y] = body_y
	pose[P_BODY_PITCH] = body_pitch

	# --- Neck and head: rock with the weight shifting fore/aft, slightly late. ---
	var lag := _support(g, ph - 0.12)
	var neck_a: float = float(g["neck"]) + float(g["neck_bob"]) * (lag.x - lag.y)
	neck_a += 0.035 * sin(t * 0.9) * idle
	pose[P_NECK] = neck_a
	pose[P_HEAD] = float(g["head"]) - neck_a - 0.7 * body_pitch + 0.03 * sin(t * 1.3 + 1.0) * idle

	# --- Tail: streams back with speed and ripples along its length. ---
	var tail_base: float = float(g["tail"]) + 0.5 * body_pitch
	tail_base += 0.10 * sin(t * 1.3) * idle
	pose[P_TAIL] = tail_base + (0.05 + 0.10 * wind) * sin(t * 5.0)
	for i in range(1, HorseModel.TAIL_SEGMENTS):
		var amp := (0.06 + 0.16 * wind) * float(i)
		pose[P_TAIL + i] = 0.12 * wind + amp * sin(t * 6.0 - float(i) * 1.2) \
				+ 0.08 * sin(t * 1.3 - float(i)) * idle

	# --- Mane: lies back in the wind and flutters. ---
	for i in HorseModel.MANE_TUFTS:
		var stream := 0.5 * wind
		var flutter := (0.04 + 0.14 * wind) * sin(t * 9.0 - float(i) * 0.9)
		pose[P_MANE + i] = MANE_REST_ANGLE + stream + flutter - 0.6 * neck_a * wind

	# --- Legs ---
	var bp := HorseModel.BODY_PIVOT
	var body_pos := Vector2(bp.x, bp.y + body_y * INV_VOXEL)
	for i in 4:
		var front := i >= 2
		var pivot: Vector3 = HorseModel.FORE_PIVOT if front else HorseModel.HIND_PIVOT
		var d: float = duty[1] if front else duty[0]
		var sweep_v: float = float(sweep[1] if front else sweep[0]) * INV_VOXEL
		var lift_v: float = float(lift[1] if front else lift[0]) * INV_VOXEL
		var x_touch: float = pivot.x + (0.0 if front else HIND_STAND_DX) + sweep_v * float(g["reach"])
		var x_lift: float = x_touch - sweep_v
		var uu := u[i]
		var fx := x_touch
		var fy := HorseModel.HOOF_LEN
		var swing := 0.0
		if uu < d:
			fx = x_touch - sweep_v * (uu / d)
		else:
			var w := (uu - d) / (1.0 - d)
			var m := -sweep_v * (1.0 - d) / d * float(g["match"])
			fx = _hermite(x_lift, x_touch, m, m, w)
			fy += lift_v * pow(sin(PI * w), 0.8)
			swing = smoothstep(0.0, 0.3, w) * (1.0 - smoothstep(0.75, 1.0, w))
		var upper_len := HorseModel.FORE_UPPER if front else HorseModel.HIND_UPPER
		var lower_len := HorseModel.FORE_LOWER if front else HorseModel.HIND_LOWER
		_pose_leg(pose, i, Vector2(fx, fy), pivot, body_pos, body_pitch, upper_len, lower_len,
				front, swing)
	return pose


## Solves one leg for a foot target given in model space (voxels) and writes the
## three joint angles into the pose vector.
func _pose_leg(pose: PackedFloat32Array, leg: int, foot: Vector2, pivot: Vector3, body_pos: Vector2,
		body_pitch: float, upper_len: float, lower_len: float, front: bool, swing: float) -> void:
	var bp := HorseModel.BODY_PIVOT
	var local := (foot - body_pos).rotated(-body_pitch)
	var rel := local - Vector2(pivot.x - bp.x, pivot.y - bp.y)
	var ang := _solve_leg(rel, upper_len, lower_len, 1.0 if front else -1.0)
	# The hoof stays flat while planted and trails backwards in the air.
	var hoof_abs := lerpf(0.0, HOOF_SWING_ANGLE, swing)
	pose[P_LEG + leg * 3] = ang.x
	pose[P_LEG + leg * 3 + 1] = ang.y
	pose[P_LEG + leg * 3 + 2] = hoof_abs - (body_pitch + ang.x + ang.y)


## Pose while clearing an obstacle. `tn` runs 0..1 from take-off to landing.
func _leap_pose(tn: float, t: float) -> PackedFloat32Array:
	var pose := PackedFloat32Array()
	pose.resize(POSE_SIZE)
	var bp := HorseModel.BODY_PIVOT
	var body_pitch := lerpf(0.30, -0.24, smoothstep(0.1, 0.95, tn))
	var arch := sin(PI * tn)
	pose[P_BODY_Y] = 0.0
	pose[P_BODY_PITCH] = body_pitch
	var neck_a := lerpf(-0.10, -0.55, arch)
	pose[P_NECK] = neck_a
	pose[P_HEAD] = 0.15 - neck_a - 0.7 * body_pitch
	pose[P_TAIL] = -1.0 + 0.05 * sin(t * 5.0)
	for i in range(1, HorseModel.TAIL_SEGMENTS):
		pose[P_TAIL + i] = 0.1 + 0.1 * sin(t * 6.0 - float(i) * 1.2)
	for i in HorseModel.MANE_TUFTS:
		pose[P_MANE + i] = MANE_REST_ANGLE + 0.45 - 0.5 * neck_a
	var body_pos := Vector2(bp.x, bp.y)
	for i in 4:
		var front := i >= 2
		var pivot: Vector3 = HorseModel.FORE_PIVOT if front else HorseModel.HIND_PIVOT
		var foot: Vector2
		if front:
			foot = Vector2(pivot.x + lerpf(6.5, 4.0, arch), lerpf(6.0, 10.5, arch))
		else:
			foot = Vector2(pivot.x - lerpf(4.0, 5.5, arch), lerpf(7.5, 9.5, arch))
		var upper_len := HorseModel.FORE_UPPER if front else HorseModel.HIND_UPPER
		var lower_len := HorseModel.FORE_LOWER if front else HorseModel.HIND_LOWER
		_pose_leg(pose, i, foot, pivot, body_pos, body_pitch, upper_len, lower_len, front, 1.0)
	return pose


static func _lerp_pose(a: PackedFloat32Array, b: PackedFloat32Array, w: float) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	out.resize(a.size())
	for i in a.size():
		out[i] = lerpf(a[i], b[i], w)
	return out


func _apply_pose(p: PackedFloat32Array) -> void:
	body.position.y = HorseModel.BODY_PIVOT.y * VOXEL + p[P_BODY_Y]
	body.rotation.z = p[P_BODY_PITCH]
	neck.rotation.z = p[P_NECK]
	head.rotation.z = p[P_HEAD]
	for i in tail.size():
		tail[i].rotation.z = p[P_TAIL + i]
	for i in mane.size():
		mane[i].rotation.z = p[P_MANE + i]
	for i in 4:
		var l: Dictionary = legs[i]
		(l["hip"] as Node3D).rotation.z = p[P_LEG + i * 3]
		(l["knee"] as Node3D).rotation.z = p[P_LEG + i * 3 + 1]
		(l["hoof"] as Node3D).rotation.z = p[P_LEG + i * 3 + 2]
