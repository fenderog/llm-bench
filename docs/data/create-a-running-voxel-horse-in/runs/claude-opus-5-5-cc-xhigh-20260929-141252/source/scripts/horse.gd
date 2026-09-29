extends Node3D
## The voxel horse: builds its part rig, reads player input, moves over the
## terrain and animates a procedural walk / trot / canter / gallop cycle.
## The horse faces +Z in its own space.

signal hoof_down(strength: float)

const HorseModel = preload("res://scripts/horse_model.gd")
const MeshData = preload("res://scripts/mesh_data.gd")
const Terrain = preload("res://scripts/terrain.gd")

const GAIT_NAMES := ["Standing", "Walk", "Trot", "Canter", "Gallop"]
const GAIT_SPEEDS := [0.0, 1.8, 4.2, 7.5, 12.0]
const SPRINT_SPEED := 16.0

## Gait keyframes, blended by speed: stride frequency (Hz), duty factor (share
## of the stride a hoof is on the ground), knee flex, body bob, whether the bob
## happens twice per stride (walk/trot) or once (canter/gallop), body rocking
## and the phase offset of each leg in the order FL, FR, HL, HR.
const GAITS := [
	{"speed": 0.0, "freq": 0.8, "duty": 0.65, "flex": 0.0, "bob": 0.0, "double": 1.0, "rock": 0.0,
		"offsets": [0.25, 0.75, 0.0, 0.5]},
	{"speed": 1.8, "freq": 0.95, "duty": 0.62, "flex": 0.8, "bob": 0.02, "double": 1.0, "rock": 0.015,
		"offsets": [0.25, 0.75, 0.0, 0.5]},
	{"speed": 4.2, "freq": 1.45, "duty": 0.45, "flex": 1.2, "bob": 0.05, "double": 1.0, "rock": 0.02,
		"offsets": [0.0, 0.5, 0.5, 0.0]},
	{"speed": 7.5, "freq": 1.75, "duty": 0.38, "flex": 1.4, "bob": 0.08, "double": 0.0, "rock": 0.07,
		"offsets": [0.45, 0.25, 0.22, 0.0]},
	{"speed": 12.0, "freq": 2.2, "duty": 0.3, "flex": 1.6, "bob": 0.1, "double": 0.0, "rock": 0.09,
		"offsets": [0.5, 0.38, 0.1, 0.0]},
	{"speed": 16.0, "freq": 2.5, "duty": 0.27, "flex": 1.7, "bob": 0.11, "double": 0.0, "rock": 0.1,
		"offsets": [0.5, 0.38, 0.1, 0.0]},
]
const LEGS := ["fl", "fr", "hl", "hr"]
## Leg pose while airborne: (upper, lower) rotation per leg.
const TUCK: Array[Vector2] = [Vector2(-1.0, 2.0), Vector2(-0.8, 1.8), Vector2(-0.35, -1.1), Vector2(-0.3, -1.0)]
const LEG_LENGTH := 1.25
const MAX_SWING := 0.8
const ACCEL := 5.0
const BRAKE := 8.0
const GRAVITY := 22.0
const JUMP_SPEED := 7.0
const RADIUS := 0.9
const NECK_REST := 0.0

var terrain: Terrain
var coat_index := 0
var gait_level := 4
var speed := 0.0
var heading := 0.0
var turn_rate := 0.0
var distance := 0.0
var vel_y := 0.0
var grounded := true
var in_water := false
var sprinting := false

var _phase := 0.0
var _offsets: Array[float] = [0.25, 0.75, 0.0, 0.5]
var _prev_leg_phase: Array[float] = [0.0, 0.0, 0.0, 0.0]
var _air := 0.0
var _idle_time := 0.0
var _time := 0.0
var _slope := 0.0
var _parts := {}
var _upper: Array[MeshInstance3D] = []
var _lower: Array[MeshInstance3D] = []
var _model: Node3D
var _material: StandardMaterial3D
var _dust: CPUParticles3D
var _dust_material: StandardMaterial3D


func _ready() -> void:
	_material = MeshData.make_material()
	_model = Node3D.new()
	_model.name = "Model"
	add_child(_model)
	for part_name: String in HorseModel.PARTS:
		var parent_name: String = HorseModel.PARTS[part_name][0]
		var pivot: Vector3 = HorseModel.PARTS[part_name][1]
		var mi := MeshInstance3D.new()
		mi.name = part_name
		var parent: Node3D = _model
		var parent_pivot := Vector3.ZERO
		if parent_name != "":
			parent = _parts[parent_name]
			parent_pivot = HorseModel.PARTS[parent_name][1]
		mi.position = (pivot - parent_pivot) * HorseModel.VOXEL_SIZE
		parent.add_child(mi)
		_parts[part_name] = mi
	for leg: String in LEGS:
		_upper.append(_parts[leg + "_upper"])
		_lower.append(_parts[leg + "_lower"])
	set_coat(coat_index)
	_create_dust()


func set_coat(index: int) -> void:
	coat_index = posmod(index, HorseModel.COATS.size())
	var meshes := HorseModel.build_meshes(HorseModel.COATS[coat_index], _material)
	for part_name: String in meshes:
		(_parts[part_name] as MeshInstance3D).mesh = meshes[part_name]


func next_coat() -> void:
	set_coat(coat_index + 1)


func coat_name() -> String:
	return HorseModel.COATS[coat_index]["name"]


func forward() -> Vector3:
	return Vector3(sin(heading), 0.0, cos(heading))


func gait_name() -> String:
	if not grounded:
		return "Jump!"
	if speed < 0.3:
		return "Grazing" if _idle_time > 4.0 else "Standing"
	if speed < 3.0:
		return "Walk"
	if speed < 5.8:
		return "Trot"
	if speed < 9.5:
		return "Canter"
	return "Full gallop" if speed > 13.5 else "Gallop"


func place_at(pos: Vector3, yaw: float) -> void:
	heading = yaw
	rotation.y = yaw
	position = Vector3(pos.x, _ground_height(pos.x, pos.z), pos.z)


func _process(delta: float) -> void:
	delta = minf(delta, 0.05)
	_time += delta
	_read_input(delta)
	_move(delta)
	_animate(delta)
	_update_dust()


func _read_input(delta: float) -> void:
	if Input.is_action_just_pressed("faster"):
		gait_level = mini(gait_level + 1, GAIT_SPEEDS.size() - 1)
	if Input.is_action_just_pressed("slower"):
		gait_level = maxi(gait_level - 1, 0)
	var target: float = GAIT_SPEEDS[gait_level]
	sprinting = Input.is_action_pressed("sprint") and gait_level > 0
	if sprinting:
		target = SPRINT_SPEED
	if in_water:
		target = minf(target, 4.5)
	if grounded:
		speed = move_toward(speed, target, (ACCEL if target > speed else BRAKE) * delta)

	var steer := Input.get_axis("turn_right", "turn_left")
	var max_turn := lerpf(1.8, 1.0, clampf(speed / SPRINT_SPEED, 0.0, 1.0))
	turn_rate = lerpf(turn_rate, steer * max_turn, 1.0 - exp(-8.0 * delta))

	if Input.is_action_just_pressed("jump") and grounded:
		vel_y = JUMP_SPEED * lerpf(0.55, 1.0, clampf(speed / GAIT_SPEEDS[4], 0.0, 1.0))
		grounded = false


func _move(delta: float) -> void:
	heading = wrapf(heading + turn_rate * delta, -PI, PI)
	rotation.y = heading
	var fwd := forward()
	var pos := position + fwd * speed * delta
	if terrain:
		# Obstacles are tested a little ahead of the centre, where the chest is.
		var probe := terrain.push_out(pos + fwd * 0.5, RADIUS) - fwd * 0.5
		pos.x = probe.x
		pos.z = probe.z
	distance += Vector2(pos.x - position.x, pos.z - position.z).length()

	var ground := _ground_height(pos.x, pos.z)
	if grounded:
		pos.y = lerpf(position.y, ground, 1.0 - exp(-14.0 * delta))
	else:
		vel_y -= GRAVITY * delta
		pos.y = position.y + vel_y * delta
		if pos.y <= ground and vel_y < 0.0:
			pos.y = ground
			vel_y = 0.0
			grounded = true
			hoof_down.emit(1.6)
	position = pos

	# Tilt the whole model to follow the slope under the horse.
	var front := _ground_height(pos.x + fwd.x * 1.1, pos.z + fwd.z * 1.1)
	var back := _ground_height(pos.x - fwd.x * 1.1, pos.z - fwd.z * 1.1)
	_slope = lerpf(_slope, atan2(front - back, 2.2), 1.0 - exp(-8.0 * delta))


func _ground_height(x: float, z: float) -> float:
	if terrain == null:
		return 0.0
	var g := terrain.ground_at(x, z)
	in_water = g < Terrain.WATER_LEVEL - 0.1
	return maxf(g, Terrain.WATER_LEVEL - 0.75)


## Blends the gait keyframes around the current speed.
func _gait_params(s: float) -> Dictionary:
	var k := 0
	while k < GAITS.size() - 2 and s > float(GAITS[k + 1]["speed"]):
		k += 1
	var a: Dictionary = GAITS[k]
	var b: Dictionary = GAITS[k + 1]
	var t := clampf(inverse_lerp(a["speed"], b["speed"], s), 0.0, 1.0)
	var out := {}
	for key in ["freq", "duty", "flex", "bob", "double", "rock"]:
		out[key] = lerpf(a[key], b[key], t)
	var offsets: Array[float] = []
	for i in 4:
		var oa: float = a["offsets"][i]
		var ob: float = b["offsets"][i]
		offsets.append(fposmod(oa + wrapf(ob - oa, -0.5, 0.5) * t, 1.0))
	out["offsets"] = offsets
	return out


func _animate(delta: float) -> void:
	var g := _gait_params(speed)
	var move := clampf(speed / 1.2, 0.0, 1.0)
	var freq: float = g["freq"]
	var duty: float = g["duty"]
	if speed > 0.05:
		_phase = fposmod(_phase + freq * delta, 1.0)
	if speed < 0.2 and grounded:
		_idle_time += delta
	else:
		_idle_time = 0.0
	_air = move_toward(_air, 0.0 if grounded else 1.0, delta * 6.0)

	# Drift each leg's phase offset toward the current gait's footfall pattern.
	var target_offsets: Array[float] = g["offsets"]
	for i in 4:
		var d := wrapf(target_offsets[i] - _offsets[i], -0.5, 0.5)
		_offsets[i] = fposmod(_offsets[i] + clampf(d, -delta * 1.5, delta * 1.5), 1.0)

	# Swing just far enough that planted hooves keep pace with the ground.
	var stance_len := speed * duty / maxf(freq, 0.01)
	var amp := minf(asin(clampf(stance_len / (2.0 * LEG_LENGTH), 0.0, 0.99)), MAX_SWING)
	var flex: float = g["flex"] * move

	for i in 4:
		var p := fposmod(_phase + _offsets[i], 1.0)
		var upper: float
		var lower: float
		if p < duty:
			upper = lerpf(-amp, amp, p / duty)
			lower = 0.0
		else:
			var s := (p - duty) / (1.0 - duty)
			upper = lerpf(amp, -amp * 1.05, smoothstep(0.0, 1.0, s))
			lower = sin(s * PI) * flex
		if i >= 2:
			lower = -lower * 0.75  # hocks fold the other way
		upper = lerpf(upper, TUCK[i].x, _air)
		lower = lerpf(lower, TUCK[i].y, _air)
		_upper[i].rotation.x = upper
		_lower[i].rotation.x = lower

		if grounded and speed > 0.4 and p < _prev_leg_phase[i] - 0.5:
			hoof_down.emit(0.5 + speed / SPRINT_SPEED)
		_prev_leg_phase[i] = p

	# Body bob and rocking-horse pitch.
	var cycle := TAU * _phase
	var dbl: float = g["double"]
	var bob: float = g["bob"] * move * (dbl * cos(2.0 * cycle) + (1.0 - dbl) * sin(cycle + 0.6))
	var rock: float = g["rock"] * move * sin(cycle - 0.9)
	var graze := smoothstep(3.0, 5.5, _idle_time)
	var body: MeshInstance3D = _parts["body"]
	body.position.y = HorseModel.PARTS["body"][1].y * HorseModel.VOXEL_SIZE + bob - graze * 0.04
	body.rotation.x = rock + graze * 0.06

	# Whole-model pose: slope, jump pitch and leaning into turns.
	var lean := clampf(turn_rate * speed * 0.03, -0.3, 0.3)
	_model.rotation.x = -_slope - clampf(vel_y * 0.045, -0.35, 0.35) * _air
	_model.rotation.z = lerpf(_model.rotation.z, -lean, 1.0 - exp(-6.0 * delta))

	# Neck and head: counter the rocking, stretch out at speed, graze when idle.
	var neck: MeshInstance3D = _parts["neck"]
	var head: MeshInstance3D = _parts["head"]
	neck.rotation.x = NECK_REST - rock * 1.3 + move * 0.25 + graze * 1.55 - _air * 0.2 \
			+ sin(_time * 0.7) * 0.03 * (1.0 - move)
	neck.rotation.y = lerpf(neck.rotation.y, turn_rate * 0.18, 1.0 - exp(-6.0 * delta))
	head.rotation.x = sin(cycle + 1.5) * 0.08 * move + graze * (0.75 + sin(_time * 3.0) * 0.08)

	# Tail streams out behind at speed and swishes lazily when idle.
	var swish := sin(_time * 1.7) * 0.35 * (1.0 - move)
	var tail_a: MeshInstance3D = _parts["tail_a"]
	var tail_b: MeshInstance3D = _parts["tail_b"]
	var stream := clampf(speed / 10.0, 0.0, 1.0)
	tail_a.rotation.x = stream * 0.75 + sin(cycle - 0.5) * 0.08 * move + _air * 0.4
	tail_a.rotation.z = swish + sin(_time * 7.0) * 0.06 * stream
	tail_b.rotation.x = stream * 0.5 + sin(cycle - 1.5) * 0.15 * move
	tail_b.rotation.z = swish * 1.2 + sin(_time * 7.0 - 1.0) * 0.12 * stream


func _create_dust() -> void:
	_dust_material = StandardMaterial3D.new()
	_dust_material.vertex_color_use_as_albedo = true
	_dust_material.roughness = 1.0
	var cube := BoxMesh.new()
	cube.size = Vector3.ONE * 0.12
	cube.material = _dust_material

	var curve := Curve.new()
	curve.add_point(Vector2(0.0, 0.4))
	curve.add_point(Vector2(0.25, 1.0))
	curve.add_point(Vector2(1.0, 0.0))

	_dust = CPUParticles3D.new()
	_dust.mesh = cube
	_dust.amount = 40
	_dust.lifetime = 0.7
	_dust.local_coords = false
	_dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_dust.emission_box_extents = Vector3(0.45, 0.05, 0.8)
	_dust.direction = Vector3(0, 1, -1)
	_dust.spread = 35.0
	_dust.initial_velocity_min = 0.8
	_dust.initial_velocity_max = 1.8
	_dust.gravity = Vector3(0, 0.6, 0)
	_dust.damping_min = 1.5
	_dust.damping_max = 2.5
	_dust.angle_min = -45.0
	_dust.angle_max = 45.0
	_dust.scale_amount_min = 0.6
	_dust.scale_amount_max = 1.4
	_dust.scale_amount_curve = curve
	_dust.position = Vector3(0, 0.1, -0.3)
	_dust.emitting = false
	add_child(_dust)


func _update_dust() -> void:
	if in_water:
		_dust.color = Color(0.85, 0.93, 1.0).srgb_to_linear()
		_dust.emitting = grounded and speed > 1.0
	else:
		_dust.color = Color(0.66, 0.6, 0.5).srgb_to_linear()
		_dust.emitting = grounded and speed > 6.0
