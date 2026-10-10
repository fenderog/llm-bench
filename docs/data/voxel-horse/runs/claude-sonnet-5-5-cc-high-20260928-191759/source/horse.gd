extends Node3D
## A voxel horse built entirely from code, with a procedural walk / trot / gallop
## cycle and a jump. The horse stays at the origin facing -Z; the world scrolls by.

const VoxelBuilder = preload("res://voxel_builder.gd")

const VS := 0.1  # metres per voxel
const BODY_PIVOT := Vector3(0, 10, 0)  # voxel coords of the body's rotation centre
const UPPER_LEN := 0.6
const LOWER_LEN := 0.4
const HIP_Z := 0.5  # front/back hip offset from the body centre, metres

const JUMP_TIME := 0.85
const JUMP_HEIGHT := 1.15
const STUMBLE_TIME := 0.8

const COAT := Color(0.60, 0.33, 0.15)
const COAT_DARK := Color(0.52, 0.27, 0.12)
const BELLY := Color(0.72, 0.47, 0.27)
const LOWER_LEG := Color(0.30, 0.17, 0.09)
const SOCK := Color(0.93, 0.90, 0.84)
const HOOF := Color(0.12, 0.10, 0.10)
const HAIR := Color(0.20, 0.11, 0.06)
const MUZZLE := Color(0.38, 0.22, 0.14)
const BLAZE := Color(0.95, 0.93, 0.88)

# Leg order: front-left, front-right, hind-left, hind-right.
# "td" is when in the stride cycle each leg touches down.
const GAITS := {
	"Walk": {"duty": 0.65, "amp": 0.5, "kf": 0.6, "kh": 0.5, "b1": 0.0, "b2": 0.02, "pitch": 0.02,
		"td": [0.25, 0.75, 0.0, 0.5]},
	"Trot": {"duty": 0.45, "amp": 0.5, "kf": 1.1, "kh": 0.9, "b1": 0.0, "b2": 0.05, "pitch": 0.03,
		"td": [0.0, 0.5, 0.5, 0.0]},
	"Gallop": {"duty": 0.32, "amp": 0.6, "kf": 1.7, "kh": 1.1, "b1": 0.10, "b2": 0.0, "pitch": 0.09,
		"td": [0.52, 0.40, 0.12, 0.0]},
}
const TRACKED := ["duty", "amp", "kf", "kh", "b1", "b2", "pitch"]

var gait_name := "Stand"
var lift := 0.0  # metres the horse is currently above the ground (jumping)
var airborne := false

var _body: Node3D
var _neck: Node3D
var _head: Node3D
var _tail1: Node3D
var _tail2: Node3D
var _legs: Array[Dictionary] = []
var _params: Dictionary = {}
var _td: Array[float] = [0.52, 0.40, 0.12, 0.0]
var _phase := 0.0
var _time := 0.0
var _jump_t := -1.0
var _stumble_t := -1.0


func _ready() -> void:
	for key: String in TRACKED:
		_params[key] = GAITS["Gallop"][key]
	_build()


func jump() -> bool:
	if _jump_t >= 0.0 or _stumble_t >= 0.0:
		return false
	_jump_t = 0.0
	return true


func stumble() -> void:
	_stumble_t = 0.0


func _mesh_node(vox: Dictionary, pivot: Vector3, parent: Node3D, attach: Vector3, parent_pivot: Vector3) -> Node3D:
	# Creates a pivot Node3D positioned at `attach` (voxel coords, relative to
	# parent_pivot) holding a mesh built around `pivot`.
	var node := Node3D.new()
	node.position = (attach - parent_pivot) * VS
	var mi := MeshInstance3D.new()
	mi.mesh = VoxelBuilder.build(vox, pivot, VS)
	node.add_child(mi)
	parent.add_child(node)
	return node


func _build() -> void:
	var model := Node3D.new()
	model.rotation.y = PI  # authored facing +Z, moves towards -Z
	add_child(model)

	# --- Body ---------------------------------------------------------------
	var vox := {}
	VoxelBuilder.add_box(vox, Vector3i(-3, 9, -7), Vector3i(3, 15, 7), COAT, true)
	VoxelBuilder.add_box(vox, Vector3i(-2, 9, -6), Vector3i(2, 11, 6), BELLY)
	VoxelBuilder.add_box(vox, Vector3i(-2, 14, -6), Vector3i(2, 15, -2), COAT_DARK)  # back
	_body = Node3D.new()
	_body.position = BODY_PIVOT * VS
	var body_mi := MeshInstance3D.new()
	body_mi.mesh = VoxelBuilder.build(vox, BODY_PIVOT, VS)
	_body.add_child(body_mi)
	model.add_child(_body)

	# --- Neck and mane --------------------------------------------------------
	var neck_pivot := Vector3(0, 13, 4)
	vox = {}
	for k in 6:
		VoxelBuilder.add_box(vox, Vector3i(-1, 13 + k, 4 + k), Vector3i(1, 16 + k, 7 + k), COAT)
		VoxelBuilder.add_box(vox, Vector3i(-1, 15 + k, 3 + k), Vector3i(1, 17 + k, 4 + k), HAIR)
	_neck = _mesh_node(vox, neck_pivot, _body, neck_pivot, BODY_PIVOT)

	# --- Head -----------------------------------------------------------------
	var head_pivot := Vector3(0.5, 19, 10)  # x = .5 because the head is 3 voxels wide
	vox = {}
	VoxelBuilder.add_box(vox, Vector3i(-1, 19, 10), Vector3i(2, 22, 13), COAT)  # skull
	VoxelBuilder.add_box(vox, Vector3i(-1, 17, 13), Vector3i(2, 21, 16), COAT)  # face
	VoxelBuilder.add_box(vox, Vector3i(-1, 16, 16), Vector3i(2, 19, 19), MUZZLE)  # muzzle
	for z in range(13, 16):
		vox[Vector3i(0, 20, z)] = BLAZE
	for z in range(16, 19):
		vox[Vector3i(0, 18, z)] = BLAZE
	vox[Vector3i(0, 18, 18)] = MUZZLE
	vox[Vector3i(-1, 20, 12)] = Color(0.05, 0.04, 0.04)  # eyes
	vox[Vector3i(1, 20, 12)] = Color(0.05, 0.04, 0.04)
	vox[Vector3i(-1, 22, 10)] = COAT_DARK  # ears
	vox[Vector3i(-1, 23, 10)] = COAT_DARK
	vox[Vector3i(1, 22, 10)] = COAT_DARK
	vox[Vector3i(1, 23, 10)] = COAT_DARK
	vox[Vector3i(0, 22, 11)] = HAIR  # forelock
	vox[Vector3i(0, 22, 12)] = HAIR
	vox[Vector3i(0, 21, 13)] = HAIR
	_head = Node3D.new()
	_head.position = (Vector3(0, 19, 10) - neck_pivot) * VS
	var head_mi := MeshInstance3D.new()
	head_mi.mesh = VoxelBuilder.build(vox, head_pivot, VS)
	_head.add_child(head_mi)
	_neck.add_child(_head)

	# --- Tail -----------------------------------------------------------------
	vox = {}
	VoxelBuilder.add_box(vox, Vector3i(-1, -5, -2), Vector3i(1, 1, 0), HAIR)
	_tail1 = _mesh_node(vox, Vector3.ZERO, _body, Vector3(0, 14, -7), BODY_PIVOT)
	vox = {}
	VoxelBuilder.add_box(vox, Vector3i(-1, -7, -1), Vector3i(1, 0, 1), HAIR)
	VoxelBuilder.add_box(vox, Vector3i(-2, -5, -1), Vector3i(2, -2, 1), HAIR, true)
	_tail2 = _mesh_node(vox, Vector3.ZERO, _tail1, Vector3(0, -5, -1), Vector3.ZERO)

	# --- Legs -----------------------------------------------------------------
	var specs := [
		{"x": 2, "z": 5, "front": true, "sock": true},
		{"x": -2, "z": 5, "front": true, "sock": false},
		{"x": 2, "z": -5, "front": false, "sock": false},
		{"x": -2, "z": -5, "front": false, "sock": true},
	]
	for spec: Dictionary in specs:
		_legs.append(_make_leg(spec))


func _make_leg(spec: Dictionary) -> Dictionary:
	var front: bool = spec["front"]
	var sock: bool = spec["sock"]
	var vox := {}
	VoxelBuilder.add_box(vox, Vector3i(-1, -6, -1), Vector3i(1, 0, 1), COAT)
	if not front:
		VoxelBuilder.add_box(vox, Vector3i(-1, -4, -2), Vector3i(1, 0, 2), COAT)  # thigh
	var upper := _mesh_node(vox, Vector3.ZERO, _body,
		Vector3(spec["x"], 10, spec["z"]), BODY_PIVOT)

	vox = {}
	VoxelBuilder.add_box(vox, Vector3i(-1, -4, -1), Vector3i(1, 0, 1), LOWER_LEG)
	if sock:
		VoxelBuilder.add_box(vox, Vector3i(-1, -3, -1), Vector3i(1, -1, 1), SOCK)
	VoxelBuilder.add_box(vox, Vector3i(-1, -4, -1), Vector3i(1, -3, 1), HOOF)
	var lower := _mesh_node(vox, Vector3.ZERO, upper, Vector3(0, -6, 0), Vector3.ZERO)

	var foot := Node3D.new()
	foot.position = Vector3(0, -4, 0) * VS
	lower.add_child(foot)

	return {
		"upper": upper, "lower": lower, "foot": foot, "front": front,
		"prev_u": 0.0, "dust": _make_dust(),
	}


func _make_dust() -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.emitting = false
	p.one_shot = true
	p.amount = 6
	p.lifetime = 0.6
	p.explosiveness = 1.0
	p.local_coords = false
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE * 0.09
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.66, 0.53, 0.36)
	mat.roughness = 1.0
	mesh.material = mat
	p.mesh = mesh
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.06
	p.direction = Vector3(0, 0.35, 1)
	p.spread = 35.0
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 4.0
	p.gravity = Vector3(0, -7, 0)
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1))
	curve.add_point(Vector2(1, 0))
	p.scale_amount_curve = curve
	add_child(p)
	return p


func _puff(leg: Dictionary, speed: float) -> void:
	var p: CPUParticles3D = leg["dust"]
	var foot: Node3D = leg["foot"]
	p.global_position = foot.global_position
	p.initial_velocity_min = speed * 0.5
	p.initial_velocity_max = speed * 0.9
	p.restart()


func _gait_for(speed: float) -> Dictionary:
	var gait := "Gallop"
	if speed < 0.3:
		gait = "Stand"
	elif speed < 3.0:
		gait = "Walk"
	elif speed < 7.0:
		gait = "Trot"
	gait_name = gait
	var g: Dictionary = GAITS["Walk" if gait == "Stand" else gait].duplicate()
	if gait == "Trot":
		g["amp"] = 0.5 + 0.03 * (speed - 3.0)
	elif gait == "Gallop":
		g["amp"] = clampf(0.6 + 0.04 * (speed - 7.0), 0.6, 0.85)
	return g


func update(delta: float, speed: float) -> void:
	_time += delta

	# Ease the gait parameters towards the current gait so switches look smooth.
	var g := _gait_for(speed)
	var k := 1.0 - exp(-5.0 * delta)
	for key: String in TRACKED:
		_params[key] = lerpf(_params[key], g[key], k)
	var target_td: Array = g["td"]
	for i in 4:
		_td[i] = lerpf(_td[i], target_td[i], k)

	var duty: float = _params["duty"]
	var amp: float = _params["amp"]
	var move := clampf(speed / 1.5, 0.0, 1.0)
	var freq := clampf(speed * duty / (2.0 * maxf(amp, 0.1) * 0.95) * 0.85, 0.0, 4.0)
	_phase = fposmod(_phase + freq * delta, 1.0)

	# Jump / stumble state.
	var jump_pose := 0.0
	var jump_pitch := 0.0
	var landed := false
	if _jump_t >= 0.0:
		_jump_t += delta / JUMP_TIME
		if _jump_t >= 1.0:
			_jump_t = -1.0
			landed = true
		else:
			lift = JUMP_HEIGHT * 4.0 * _jump_t * (1.0 - _jump_t)
			jump_pose = clampf(sin(_jump_t * PI) * 3.0, 0.0, 1.0)
			jump_pitch = -0.35 * cos(_jump_t * PI) * jump_pose
	if _jump_t < 0.0:
		lift = 0.0
	airborne = lift > 0.05
	var stumble_pitch := 0.0
	if _stumble_t >= 0.0:
		_stumble_t += delta / STUMBLE_TIME
		if _stumble_t >= 1.0:
			_stumble_t = -1.0
		else:
			stumble_pitch = 0.4 * sin(_stumble_t * PI)

	# Body rocking.
	var pitch_run: float = -float(_params["pitch"]) * cos(TAU * (_phase - 0.1)) + stumble_pitch
	var speed_f := clampf(speed / 13.0, 0.0, 1.0)
	_body.rotation.x = pitch_run + jump_pitch
	_body.rotation.z = 0.025 * sin(TAU * _phase) * move

	# Legs. Contact height is worked out from the running pose so the hooves
	# stay planted; the jump pose is blended in on top for the visuals.
	var root_y := 0.0
	var kf: float = _params["kf"]
	var kh: float = _params["kh"]
	for i in 4:
		var leg := _legs[i]
		var front: bool = leg["front"]
		var u := fposmod(_phase - _td[i], 1.0)
		if u < float(leg["prev_u"]) and move > 0.5 and speed > 2.5 and jump_pose < 0.3:
			_puff(leg, speed)
		leg["prev_u"] = u

		var swing: float
		var flex: float
		if u < duty:
			var w := u / duty
			swing = amp * (1.0 - 2.0 * w)
			flex = 0.12 * sin(w * PI)
		else:
			var w := (u - duty) / (1.0 - duty)
			swing = -amp + 2.0 * amp * (0.5 - 0.5 * cos(w * PI))
			flex = (kf if front else kh) * sin(w * PI)
		swing += 0.1 if front else -0.05
		swing *= move
		flex *= move

		var phi_u := -swing + pitch_run
		var drop := UPPER_LEN * cos(phi_u) + LOWER_LEN * cos(phi_u + flex)
		root_y = maxf(root_y, drop + (HIP_Z if front else -HIP_Z) * sin(pitch_run))

		var swing_v := lerpf(swing, 0.9 if front else -0.6, jump_pose)
		var flex_v := lerpf(flex, 1.7 if front else 0.9, jump_pose)
		var upper: Node3D = leg["upper"]
		var lower: Node3D = leg["lower"]
		upper.rotation.x = -swing_v
		lower.rotation.x = flex_v

	if landed:
		for leg in _legs:
			_puff(leg, maxf(speed, 4.0))

	# Airborne bounce from the gait, plus a gentle idle breathing when standing.
	var b1: float = _params["b1"]
	var b2: float = _params["b2"]
	var bounce := b1 * (0.5 + 0.5 * cos(TAU * (_phase - 0.92))) \
		+ b2 * (0.5 + 0.5 * cos(2.0 * TAU * (_phase - 0.975)))
	_body.position.y = root_y + bounce * move + lift + 0.006 * sin(_time * 2.0) * (1.0 - move)

	# Neck, head and tail follow along.
	var nod := 0.09 * speed_f * sin(TAU * (_phase - 0.25))
	_neck.rotation.x = 0.02 + 0.12 * speed_f + nod - 0.6 * (pitch_run + jump_pitch) \
		+ 0.02 * sin(_time * 1.3) * (1.0 - move)
	_head.rotation.x = -0.15 * speed_f + 0.05 * sin(TAU * (_phase - 0.4)) * speed_f

	var stream := clampf(0.15 + 0.9 * speed_f + 0.25 * jump_pose, 0.0, 1.3)
	_tail1.rotation.x = stream + 0.08 * sin(_time * 7.0)
	_tail1.rotation.z = 0.12 * sin(_time * 4.0) * (0.4 + speed_f)
	_tail2.rotation.x = 0.1 + 0.3 * speed_f * sin(_time * 9.0 - 1.0) + 0.1 * speed_f
	_tail2.rotation.z = 0.15 * sin(_time * 6.0 - 0.5)
