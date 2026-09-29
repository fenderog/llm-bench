extends Node3D
## A voxel horse built from articulated voxel parts and animated procedurally.
##
## Design space: 1 unit = 1 voxel, +Z is forward, +Y is up, y = 0 is the ground and
## x = 0.5 is the centre line. The model is rotated by 180 degrees underneath this
## node so that the horse runs along Godot's -Z axis.
##
## Call step() every frame with the current speed; the gait (stand, walk, trot,
## canter, gallop) is blended from keyframes and the body height is derived from
## the feet, so hooves stay on the ground.

const VoxelBuilder = preload("res://scripts/voxel_builder.gd")

const VOXEL := 0.085

# Leg order used throughout: left/right front, left/right hind.
const LF := 0
const RF := 1
const LH := 2
const RH := 3

# Gait keyframe slots.
const P_FREQ := 0        # strides per second
const P_DUTY := 1        # fraction of the stride spent on the ground
const P_REACH_F := 2     # forward swing of the front legs (rad)
const P_BACK_F := 3
const P_REACH_H := 4
const P_BACK_H := 5
const P_KNEE := 6        # knee fold while swinging (rad)
const P_HOCK := 7
const P_HOP := 8         # extra lift during suspension (voxels)
const P_HOP_PHASE := 9
const P_BOB := 10        # two-beat body bounce (voxels)
const P_PITCH := 11      # body rocking (rad)
const P_NECK := 12       # neck lowering (rad)
const P_HEAD := 13
const P_NOD := 14        # neck pumping with the stride (rad)
const P_TAIL := 15       # how far the tail streams out behind
const P_OFF := 16        # 4 phase offsets: LF, RF, LH, RH
const P_COUNT := 20
const P_CIRCULAR := [P_HOP_PHASE, P_OFF, P_OFF + 1, P_OFF + 2, P_OFF + 3]

const GAIT_SPEEDS := [0.0, 1.6, 4.2, 7.0, 11.0]
const GAIT_TABLE := [
	# freq duty rF bF rH bH knee hock hop hopPh bob pitch neck head nod tail  offsets
	[1.00, 0.60, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.0, 0.00, 0.0, 0.00, 0.00, 0.00, 0.00, 0.00, 0.25, 0.75, 0.00, 0.50],  # stand
	[1.05, 0.66, 0.55, 0.50, 0.42, 0.48, 0.90, 0.60, 0.0, 0.00, 0.3, 0.02, 0.00, 0.00, 0.06, 0.12, 0.25, 0.75, 0.00, 0.50],  # walk
	[1.90, 0.46, 0.55, 0.45, 0.42, 0.50, 1.25, 0.90, 0.0, 0.00, 0.6, 0.03, 0.06, -0.04, 0.05, 0.40, 0.00, 0.50, 0.50, 0.00],  # trot
	[2.05, 0.38, 0.75, 0.55, 0.55, 0.65, 1.40, 1.00, 1.2, 0.02, 0.0, 0.07, 0.18, -0.12, 0.10, 0.75, 0.36, 0.68, 0.00, 0.33],  # canter
	[2.25, 0.30, 0.95, 0.60, 0.60, 0.80, 1.50, 1.20, 2.2, 0.95, 0.0, 0.11, 0.32, -0.25, 0.14, 1.10, 0.50, 0.60, 0.00, 0.10],  # gallop
]

# Pivots (design space).
const PIVOT_BODY := Vector3(0.5, 15.0, 0.0)
const PIVOT_NECK := Vector3(0.5, 15.0, 7.0)
const PIVOT_HEAD := Vector3(0.5, 24.3, 12.6)
const PIVOT_TAIL1 := Vector3(0.5, 17.0, -9.0)
const PIVOT_TAIL2 := Vector3(0.5, 12.0, -10.0)

const NECK_START := Vector2(15.5, 6.5)      # (y, z)
const NECK_DIR := Vector2(0.819, 0.574)     # (dy, dz), 55 degrees up
const NECK_LEN := 11.0
const HEAD_START := Vector2(24.3, 12.6)
const HEAD_DIR := Vector2(-0.707, 0.707)    # 45 degrees down
const HEAD_LEN := 10.5

# Leg rows: [y, z_from, z_to_exclusive].
const FRONT_UPPER := [[14, 4, 9], [13, 4, 9], [12, 4, 9], [11, 5, 9], [10, 5, 9], [9, 5, 8], [8, 5, 8], [7, 5, 8], [6, 5, 8]]
const FRONT_LOWER := [[5, 5, 8], [4, 6, 8], [3, 6, 8], [2, 6, 8], [1, 6, 8], [0, 6, 9]]
const HIND_UPPER := [[14, -9, -3], [13, -9, -3], [12, -9, -3], [11, -9, -4], [10, -9, -4], [9, -9, -5], [8, -9, -5], [7, -9, -6]]
const HIND_LOWER := [[6, -8, -6], [5, -8, -6], [4, -8, -6], [3, -8, -6], [2, -8, -6], [1, -8, -6], [0, -8, -5]]
# Tail 2 rows: [y, half_width, z_from, z_to_exclusive].
const TAIL2_ROWS := [[11, 1, -11, -9], [10, 1, -11, -9], [9, 1, -11, -9], [8, 1, -11, -9], [7, 0, -11, -9], [6, 0, -11, -9], [5, 0, -11, -10]]

const GROUND_SOFTNESS := 6.0   # sharpness of the smooth-max used to plant the feet
const INFLATE := 1.012        # child parts are a hair larger so overlaps never z-fight

const HOOF := Color(0.13, 0.11, 0.11)
const EYE := Color(0.02, 0.02, 0.03)
const NOSTRIL := Color(0.10, 0.07, 0.07)
const WHITE := Color(0.95, 0.94, 0.90)
const NONE := Color(0, 0, 0, 0)


class Coat:
	var label: String
	var body: Color
	var belly: Color
	var leg: Color
	var mane: Color
	var sock: Color        # alpha 0: no socks
	var blaze: bool
	var patch: Color       # alpha 0: no patches
	var patch_freq: float
	var patch_cut: float

	func _init(n: String, b: Color, bl: Color, l: Color, m: Color, s: Color, bz: bool,
			p := Color(0, 0, 0, 0), pf := 0.1, pc := 0.3) -> void:
		label = n
		body = b
		belly = bl
		leg = l
		mane = m
		sock = s
		blaze = bz
		patch = p
		patch_freq = pf
		patch_cut = pc


var _coats: Array = []
var _coat_index := 0
var _coat: Coat
var _noise := FastNoiseLite.new()
var _material := StandardMaterial3D.new()

var _model: Node3D
var _body: Node3D
var _neck: Node3D
var _head: Node3D
var _tail1: Node3D
var _tail2: Node3D
var _mane: Node3D
var _upper: Array[Node3D] = []
var _lower: Array[Node3D] = []
var _dust: CPUParticles3D

var _g := PackedFloat32Array()
var _keys: Array[PackedFloat32Array] = []
var _phase := 0.0
var _time := 0.0


func _ready() -> void:
	_g.resize(P_COUNT)
	for row: Array in GAIT_TABLE:
		_keys.append(PackedFloat32Array(row))

	_material.vertex_color_use_as_albedo = true
	_material.vertex_color_is_srgb = true
	_material.roughness = 0.95
	_material.metallic_specular = 0.12

	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_noise.seed = 11

	_coats = _make_coats()
	_coat = _coats[0]
	_build_nodes()
	_rebuild_meshes()
	_make_dust()
	step(0.0, 0.0, 0.0, 0.0, 0.0)


func _make_coats() -> Array:
	return [
		Coat.new("Chestnut", Color(0.63, 0.34, 0.16), Color(0.73, 0.45, 0.25), Color(0.56, 0.29, 0.13),
				Color(0.30, 0.15, 0.07), WHITE, true),
		Coat.new("Bay", Color(0.47, 0.24, 0.12), Color(0.57, 0.33, 0.18), Color(0.12, 0.08, 0.07),
				Color(0.08, 0.06, 0.05), NONE, false),
		Coat.new("Palomino", Color(0.89, 0.67, 0.30), Color(0.96, 0.79, 0.47), Color(0.83, 0.61, 0.27),
				Color(0.97, 0.93, 0.82), NONE, true),
		Coat.new("Black", Color(0.11, 0.11, 0.13), Color(0.17, 0.17, 0.19), Color(0.09, 0.09, 0.11),
				Color(0.05, 0.05, 0.06), WHITE, true),
		Coat.new("Grey", Color(0.73, 0.74, 0.78), Color(0.84, 0.85, 0.88), Color(0.56, 0.57, 0.61),
				Color(0.40, 0.41, 0.45), NONE, false, Color(0.56, 0.57, 0.63), 0.55, 0.30),
		Coat.new("Pinto", Color(0.44, 0.25, 0.15), Color(0.52, 0.31, 0.19), Color(0.39, 0.22, 0.13),
				Color(0.16, 0.10, 0.08), NONE, true, Color(0.95, 0.94, 0.91), 0.085, 0.10),
	]


func coat_name() -> String:
	return _coat.label


func next_coat() -> void:
	_coat_index = (_coat_index + 1) % _coats.size()
	_coat = _coats[_coat_index]
	_rebuild_meshes()


# ---------------------------------------------------------------------------
# Scene graph
# ---------------------------------------------------------------------------

func _pivot_node(parent: Node3D, pivot: Vector3, parent_pivot: Vector3, inflate := true) -> Node3D:
	var node := Node3D.new()
	node.position = (pivot - parent_pivot) * VOXEL
	parent.add_child(node)
	var mi := MeshInstance3D.new()
	mi.material_override = _material
	if inflate:
		mi.scale = Vector3.ONE * INFLATE
	node.add_child(mi)
	return node


func _leg_pivot(front: bool, side: int, upper: bool) -> Vector3:
	if upper:
		return Vector3(-1.5 if side < 0 else 2.5, 13.0, 6.5 if front else -6.0)
	return Vector3(-2.0 if side < 0 else 3.0, 6.0 if front else 7.0, 7.0 if front else -7.0)


func _build_nodes() -> void:
	_model = Node3D.new()
	_model.rotation.y = PI
	add_child(_model)

	_body = _pivot_node(_model, PIVOT_BODY, Vector3(0.5, 0.0, 0.0), false)
	_neck = _pivot_node(_body, PIVOT_NECK, PIVOT_BODY)
	_mane = _pivot_node(_neck, PIVOT_NECK, PIVOT_NECK)
	_head = _pivot_node(_neck, PIVOT_HEAD, PIVOT_NECK)
	_tail1 = _pivot_node(_body, PIVOT_TAIL1, PIVOT_BODY)
	_tail2 = _pivot_node(_tail1, PIVOT_TAIL2, PIVOT_TAIL1)

	for i in 4:
		var front := i < 2
		var side := -1 if i % 2 == 0 else 1
		var up := _leg_pivot(front, side, true)
		var low := _leg_pivot(front, side, false)
		var upper := _pivot_node(_body, up, PIVOT_BODY)
		_upper.append(upper)
		_lower.append(_pivot_node(upper, low, up))


func _set_mesh(node: Node3D, builder: VoxelBuilder, pivot: Vector3) -> void:
	var mi := node.get_child(0) as MeshInstance3D
	mi.mesh = builder.build_mesh(pivot, VOXEL)


func _rebuild_meshes() -> void:
	_noise.frequency = _coat.patch_freq
	var neck := _build_neck()
	_set_mesh(_body, _build_torso(), PIVOT_BODY)
	_set_mesh(_neck, neck, PIVOT_NECK)
	_set_mesh(_mane, _build_mane(neck), PIVOT_NECK)
	_set_mesh(_head, _build_head(), PIVOT_HEAD)
	_set_mesh(_tail1, _build_tail(true), PIVOT_TAIL1)
	_set_mesh(_tail2, _build_tail(false), PIVOT_TAIL2)
	for i in 4:
		var front := i < 2
		var side := -1 if i % 2 == 0 else 1
		_set_mesh(_upper[i], _build_leg(front, true, side), _leg_pivot(front, side, true))
		_set_mesh(_lower[i], _build_leg(front, false, side), _leg_pivot(front, side, false))


# ---------------------------------------------------------------------------
# Voxel geometry
# ---------------------------------------------------------------------------

func _new_builder() -> VoxelBuilder:
	var b := VoxelBuilder.new()
	b.jitter = 0.04
	return b


func _apply_patches(b: VoxelBuilder) -> void:
	if _coat.patch.a <= 0.0:
		return
	for key in b.cells.keys():
		var p: Vector3i = key
		if _noise.get_noise_3d(p.x, p.y, p.z) > _coat.patch_cut:
			b.cells[p] = _coat.patch


func _build_torso() -> VoxelBuilder:
	var b := _new_builder()
	for z in range(-9, 10):
		var end := 1.0
		if absi(z) == 9:
			end = 0.80
		elif absi(z) == 8:
			end = 0.93
		var tuck := clampf((-1.0 - z) / 8.0, 0.0, 1.0)     # belly rises towards the flank
		var croup := clampf((-4.0 - z) / 5.0, 0.0, 1.0)    # back dips over the rump
		var cy := 15.0 + 0.5 * tuck - 0.3 * croup
		var ry := 4.3 * end - 0.9 * tuck - 0.7 * croup
		var rx := 3.75 * end
		for y in range(10, 20):
			for x in range(-3, 4):
				var q := Vector2(x / rx, (y + 0.5 - cy) / ry)
				if q.length_squared() > 1.0:
					continue
				b.set_voxel(Vector3i(x, y, z), _coat.belly if y <= 12 else _coat.body)
	# Withers.
	for z in range(3, 7):
		for x in range(-1, 2):
			b.set_voxel(Vector3i(x, 19, z), _coat.body)
	_apply_patches(b)
	return b


func _leg_color(y: int, upper: bool) -> Color:
	if upper:
		return _coat.body
	if y == 0:
		return HOOF
	if y <= 2 and _coat.sock.a > 0.0:
		return _coat.sock
	return _coat.leg


func _build_leg(front: bool, upper: bool, side: int) -> VoxelBuilder:
	var b := _new_builder()
	var rows: Array
	if upper:
		rows = FRONT_UPPER if front else HIND_UPPER
	else:
		rows = FRONT_LOWER if front else HIND_LOWER
	var x0: int
	var width: int
	if upper:
		x0 = -3 if side < 0 else 1
		width = 3
	else:
		x0 = -3 if side < 0 else 2
		width = 2
	for row: Array in rows:
		var y: int = row[0]
		var color := _leg_color(y, upper)
		for x in range(x0, x0 + width):
			for z in range(int(row[1]), int(row[2])):
				b.set_voxel(Vector3i(x, y, z), color)
	if upper:
		_apply_patches(b)
	return b


func _build_neck() -> VoxelBuilder:
	var b := _new_builder()
	for y in range(11, 28):
		for z in range(2, 17):
			var p := Vector2(y + 0.5, z + 0.5) - NECK_START
			var along := p.dot(NECK_DIR)
			if along < -1.0 or along > NECK_LEN:
				continue
			var perp := p.x * NECK_DIR.y - p.y * NECK_DIR.x
			var t := clampf(along / NECK_LEN, 0.0, 1.0)
			if absf(perp) > lerpf(3.0, 1.7, t):
				continue
			var half := 2 if t < 0.15 else 1
			for x in range(-half, half + 1):
				b.set_voxel(Vector3i(x, y, z), _coat.body)
	_apply_patches(b)
	return b


func _build_mane(neck: VoxelBuilder) -> VoxelBuilder:
	var b := _new_builder()
	var out := Vector2(NECK_DIR.y, -NECK_DIR.x)     # up and back, away from the crest
	var t := 1.0
	while t <= NECK_LEN + 0.6:
		var r := lerpf(3.0, 1.7, clampf(t / NECK_LEN, 0.0, 1.0))
		var cell := Vector3i.ZERO
		var found := false
		for k in 6:
			var c := NECK_START + NECK_DIR * t + out * (r + 0.2 * k)
			cell = Vector3i(0, floori(c.x), floori(c.y))
			if not neck.has_voxel(cell):
				found = true
				break
		if found:
			b.set_voxel(cell, _coat.mane)
			var back := cell + Vector3i(0, 0, -1)
			if not neck.has_voxel(back) and VoxelBuilder.hash3(cell, 5) < 0.6:
				b.set_voxel(back, _coat.mane)
		t += 0.5
	return b


func _build_head() -> VoxelBuilder:
	var b := _new_builder()
	var nrm := Vector2(HEAD_DIR.y, -HEAD_DIR.x)     # towards the face line
	var muzzle := _coat.body.lerp(Color(0.24, 0.17, 0.16), 0.5)
	for y in range(14, 30):
		for z in range(8, 25):
			var p := Vector2(y + 0.5, z + 0.5) - HEAD_START
			var along := p.dot(HEAD_DIR)
			if along < -1.8 or along > HEAD_LEN:
				continue
			var perp := p.dot(nrm)
			var t := clampf(along / HEAD_LEN, 0.0, 1.0)
			var r := lerpf(2.6, 1.4, pow(t, 0.7))
			if absf(perp) > r:
				continue
			var color := _coat.body
			if along > HEAD_LEN - 2.2:
				color = muzzle
			for x in range(-1, 2):
				var c := color
				if _coat.blaze and x == 0 and perp > r - 1.05 and along > 1.5 and along < HEAD_LEN - 1.4:
					c = WHITE
				b.set_voxel(Vector3i(x, y, z), c)
	_apply_patches(b)

	# Eyes, nostrils, ears and forelock.
	var eye := HEAD_START + HEAD_DIR * 2.4 + nrm * 0.5
	var nose := HEAD_START + HEAD_DIR * (HEAD_LEN - 0.7) + nrm * 0.2
	for x: int in [-1, 1]:
		var eye_cell := Vector3i(x, floori(eye.x), floori(eye.y))
		if b.has_voxel(eye_cell):
			b.set_voxel(eye_cell, EYE)
		var nose_cell := Vector3i(x, floori(nose.x), floori(nose.y))
		if b.has_voxel(nose_cell):
			b.set_voxel(nose_cell, NOSTRIL)
	var ear := HEAD_START + HEAD_DIR * -0.8 + nrm * 2.2
	var ey := floori(ear.x)
	var ez := floori(ear.y)
	for x: int in [-1, 1]:
		b.set_voxel(Vector3i(x, ey, ez), _coat.body)
		b.set_voxel(Vector3i(x, ey + 1, ez), _coat.body)
		b.set_voxel(Vector3i(x, ey + 2, ez - 1), _coat.mane)
	for lock: float in [-0.6, 0.5, 1.5]:
		var c := HEAD_START + HEAD_DIR * lock + nrm * 2.35
		b.set_voxel(Vector3i(0, floori(c.x), floori(c.y)), _coat.mane)
	return b


func _build_tail(upper: bool) -> VoxelBuilder:
	var b := _new_builder()
	if upper:
		for y in range(12, 17):
			for x in range(-1, 2):
				for z in range(-11, -9):
					b.set_voxel(Vector3i(x, y, z), _coat.mane)
	else:
		for row: Array in TAIL2_ROWS:
			var half: int = row[1]
			for x in range(-half, half + 1):
				for z in range(int(row[2]), int(row[3])):
					b.set_voxel(Vector3i(x, int(row[0]), z), _coat.mane)
	return b


# ---------------------------------------------------------------------------
# Dust
# ---------------------------------------------------------------------------

func _make_dust() -> void:
	_dust = CPUParticles3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE * 0.11
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(0.82, 0.72, 0.54)
	mesh.material = mat
	_dust.mesh = mesh
	_dust.amount = 56
	_dust.lifetime = 0.8
	_dust.local_coords = false
	_dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_dust.emission_box_extents = Vector3(0.3, 0.02, 0.9)
	_dust.direction = Vector3(0, 1, 0.6)
	_dust.spread = 30.0
	_dust.gravity = Vector3(0, -4.0, 0)
	_dust.initial_velocity_min = 0.5
	_dust.initial_velocity_max = 1.6
	_dust.scale_amount_min = 0.5
	_dust.scale_amount_max = 1.3
	var curve := Curve.new()
	curve.add_point(Vector2(0.0, 1.0))
	curve.add_point(Vector2(1.0, 0.0))
	_dust.scale_amount_curve = curve
	_dust.position = Vector3(0, 0.03, 0.2)
	_dust.emitting = false
	add_child(_dust)


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

## Stride curve: 1 = leg fully forward (touchdown), -1 = fully back (lift-off).
## The warp gives the stance phase `duty` of the cycle; velocity is zero at both
## turning points so the motion stays smooth.
static func _stride(p: float, duty: float) -> float:
	var q := 0.5 * p / duty if p < duty else 0.5 + 0.5 * (p - duty) / (1.0 - duty)
	return cos(TAU * q)


static func _swing_bump(p: float, duty: float) -> float:
	if p < duty:
		return 0.0
	return sin(PI * (p - duty) / (1.0 - duty))


func _blend_gait(speed: float) -> void:
	var top: float = GAIT_SPEEDS[GAIT_SPEEDS.size() - 1]
	var s := clampf(speed, 0.0, top)
	var i := 0
	while i < GAIT_SPEEDS.size() - 2 and s > float(GAIT_SPEEDS[i + 1]):
		i += 1
	var t := smoothstep(float(GAIT_SPEEDS[i]), float(GAIT_SPEEDS[i + 1]), s)
	var a := _keys[i]
	var b := _keys[i + 1]
	for k in P_COUNT:
		if k in P_CIRCULAR:
			var d := fposmod(b[k] - a[k] + 0.5, 1.0) - 0.5
			_g[k] = fposmod(a[k] + d * t, 1.0)
		else:
			_g[k] = lerpf(a[k], b[k], t)


## Height (in voxels) the body must be raised so this foot just touches the ground.
func _foot_raise(i: int, s: float, fold: float, pitch: float) -> float:
	var front := i < 2
	var l_up := 7.0 if front else 6.0
	var l_low := 6.0 if front else 7.0
	var hip_z := 6.5 if front else -6.0
	var lower_angle := s - fold if front else s + fold
	var y_b := -2.0 - l_up * cos(s) - l_low * cos(lower_angle)
	var z_b := hip_z + l_up * sin(s) + l_low * sin(lower_angle)
	var y_r := y_b * cos(pitch) - z_b * sin(pitch)
	return -(PIVOT_BODY.y + y_r)


## speed: m/s. turn: -1..1 (positive = left). air: 0..1 jump pose blend.
## vy: vertical velocity normalised to -1..1.
func step(delta: float, speed: float, turn: float, air: float, vy: float) -> void:
	if _body == null:
		return
	_time += delta
	_blend_gait(speed)
	var g := _g
	_phase = fposmod(_phase + g[P_FREQ] * delta, 1.0)
	var ph := _phase
	var duty := g[P_DUTY]

	var pitch := g[P_PITCH] * sin(TAU * (ph - 0.45)) - 0.22 * air * clampf(vy, -1.0, 1.0)

	var soft := 0.0
	for i in 4:
		var front := i < 2
		var p := fposmod(ph + g[P_OFF + i], 1.0)
		var reach := g[P_REACH_F] if front else g[P_REACH_H]
		var back := g[P_BACK_F] if front else g[P_BACK_H]
		var flex := g[P_KNEE] if front else g[P_HOCK]
		var s := (reach - back) * 0.5 + (reach + back) * 0.5 * _stride(p, duty)
		var fold := flex * _swing_bump(p, duty)
		if air > 0.0:
			s = lerpf(s, 0.85 if front else -0.6, air)
			fold = lerpf(fold, 1.35 if front else 0.55, air)
		_upper[i].rotation.x = -s
		_lower[i].rotation.x = fold if front else -fold
		soft += exp(GROUND_SOFTNESS * _foot_raise(i, s, fold, pitch))
	var ground := (log(soft) / GROUND_SOFTNESS - 0.15) * (1.0 - air)
	var hop := g[P_HOP] * maxf(0.0, cos(TAU * (ph - g[P_HOP_PHASE])))
	var bob := g[P_BOB] * cos(TAU * 2.0 * (ph - 0.975))
	_body.position.y = (PIVOT_BODY.y + ground + hop + bob) * VOXEL
	_body.rotation.x = pitch

	# Neck, head and mane.
	var idle := 1.0 - clampf(speed / 1.5, 0.0, 1.0)
	var nod := sin(TAU * (ph - 0.25))
	_neck.rotation.x = g[P_NECK] + g[P_NOD] * nod - 0.6 * pitch - 0.25 * air \
			+ idle * 0.04 * sin(_time * 0.9)
	_head.rotation.x = g[P_HEAD] - 0.5 * g[P_NOD] * nod - 0.3 * pitch \
			+ idle * (0.05 + 0.05 * sin(_time * 0.6 + 1.0))
	_neck.rotation.y = turn * 0.30
	_head.rotation.y = turn * 0.25
	var stream := g[P_TAIL]
	_mane.rotation.x = -0.05 * stream + 0.03 * stream * sin(_time * 9.0)

	# Tail streams out with speed and swishes when idle.
	var wave := 0.35 + stream
	_tail1.rotation.x = 0.10 + stream * 0.80 + 0.04 * sin(TAU * ph + 1.0)
	_tail2.rotation.x = 0.08 + stream * 0.35 + 0.16 * wave * sin(_time * (3.0 + stream * 6.0) + 1.5)
	_tail1.rotation.y = -turn * 0.35 + 0.10 * sin(_time * 1.7) * (1.0 - stream * 0.6)
	_tail2.rotation.y = 0.14 * wave * sin(_time * (2.5 + stream * 7.0) + 0.7)

	_dust.emitting = speed > 2.2 and air < 0.5
	_dust.initial_velocity_max = 1.0 + speed * 0.12
