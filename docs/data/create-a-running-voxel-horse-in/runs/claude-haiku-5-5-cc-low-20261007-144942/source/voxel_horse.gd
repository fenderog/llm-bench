extends Node3D
## A voxel horse built from small cubes, with a procedural gallop.
## Controls: W/Up accelerate, S/Down brake, A/D or Left/Right steer, Space jump.

const VOX := 0.1  # world size of one voxel
const MAX_SPEED := 12.0
const ACCEL := 9.0
const BRAKE := 14.0
const FRICTION := 3.0
const TURN_RATE := 2.0  # radians per second at full steering
const GRAVITY := 22.0
const JUMP_VELOCITY := 7.0
const BOUNDS := 140.0
# Diagonal pairs move together: front-left/back-right, then front-right/back-left
const LEG_PHASE := [0.0, PI, PI, 0.0]

var speed := 0.0
var phase := 0.0

var _vertical_velocity := 0.0
var _body: Node3D
var _head: Node3D
var _tail: Node3D
var _legs: Array[Node3D] = []
var _body_base_y := 0.47 * VOX  # lifts the feet so they rest on y = 0
var _mesh: BoxMesh
var _materials := {}
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.seed = 7
	_mesh = BoxMesh.new()
	_mesh.size = Vector3.ONE * VOX * 0.94  # small gaps give the blocky voxel look
	_build_horse()


func _process(delta: float) -> void:
	_steer(delta)
	_animate(delta)


func _steer(delta: float) -> void:
	var accelerate := Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP)
	var brake := Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN)
	var left := Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT)
	var right := Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT)

	if accelerate:
		speed = move_toward(speed, MAX_SPEED, ACCEL * delta)
	elif brake:
		speed = move_toward(speed, 0.0, BRAKE * delta)
	else:
		speed = move_toward(speed, 0.0, FRICTION * delta)

	# Positive yaw turns left; the horse can only steer properly while moving
	var turn := float(left) - float(right)
	rotation.y += turn * TURN_RATE * clampf(speed / 4.0, 0.0, 1.0) * delta

	var forward := -transform.basis.z
	position += forward * speed * delta
	position.x = clampf(position.x, -BOUNDS, BOUNDS)
	position.z = clampf(position.z, -BOUNDS, BOUNDS)

	# Simple jump: a vertical velocity under gravity, clamped to the ground
	if position.y <= 0.0:
		position.y = 0.0
		_vertical_velocity = 0.0
		if Input.is_key_pressed(KEY_SPACE):
			_vertical_velocity = JUMP_VELOCITY
	_vertical_velocity -= GRAVITY * delta
	position.y = maxf(position.y + _vertical_velocity * delta, 0.0)


func _animate(delta: float) -> void:
	var intensity := clampf(speed / MAX_SPEED, 0.0, 1.0)
	phase += delta * lerpf(0.0, 12.0, intensity)

	# Legs tuck up a little while airborne
	var swing := intensity * (0.3 if position.y > 0.01 else 0.7)
	for i in _legs.size():
		_legs[i].rotation.x = sin(phase + LEG_PHASE[i]) * swing

	# Body rises on each stride and leans into the gallop
	_body.position.y = _body_base_y + absf(sin(phase)) * 0.12 * intensity
	_body.rotation.x = -0.06 * intensity

	_head.rotation.x = -0.25 + sin(phase * 2.0) * 0.04 * intensity
	_tail.rotation.x = -0.3 - 0.3 * intensity + sin(phase) * 0.1 * intensity
	_tail.rotation.y = sin(phase * 0.5) * 0.2


func _build_horse() -> void:
	var brown := Color(0.5, 0.31, 0.16)
	var dark := Color(0.22, 0.13, 0.07)
	var light := Color(0.78, 0.6, 0.4)
	var red := Color(0.7, 0.12, 0.12)
	var black := Color(0.04, 0.04, 0.04)
	var hoof := Color(0.1, 0.08, 0.06)

	# Everything is addressed in voxel cell units; each part has a pivot origin
	_body = Node3D.new()
	_body.position.y = _body_base_y
	add_child(_body)

	# Torso, saddle, neck and mane are part of the body so they bob together
	_fill(_body, Vector3.ZERO, Vector3i(-3, 6, -6), Vector3i(2, 9, 4), brown)
	_fill(_body, Vector3.ZERO, Vector3i(-2, 10, -2), Vector3i(1, 10, 1), red)
	_fill(_body, Vector3.ZERO, Vector3i(-2, 9, -9), Vector3i(1, 13, -7), brown)
	_fill(_body, Vector3.ZERO, Vector3i(0, 14, -9), Vector3i(0, 14, -7), dark)

	# Head pivots at the base of the neck so it can nod
	var head_origin := Vector3(-0.5, 12.0, -8.0)
	var eyes := [Vector3i(-2, 14, -10), Vector3i(1, 14, -10)]
	_head = Node3D.new()
	_head.position = head_origin * VOX
	_body.add_child(_head)
	_fill(_head, head_origin, Vector3i(-2, 13, -11), Vector3i(1, 15, -9), brown, eyes)
	_fill(_head, head_origin, Vector3i(-1, 13, -13), Vector3i(0, 14, -12), light)
	_fill(_head, head_origin, Vector3i(-1, 16, -10), Vector3i(0, 16, -9), dark)
	for eye in eyes:
		_fill(_head, head_origin, eye, eye, black)

	# Four legs, each pivoting at the hip. Each entry is the leg's lower-left cell (x, z)
	for spec in [[-3, -5], [1, -5], [-3, 2], [1, 2]]:
		var x0: int = spec[0]
		var z0: int = spec[1]
		var origin := Vector3(x0 + 0.5, 5.5, z0 + 0.5)
		var leg := Node3D.new()
		leg.position = origin * VOX
		_body.add_child(leg)
		_legs.append(leg)
		_fill(leg, origin, Vector3i(x0, 1, z0), Vector3i(x0 + 1, 5, z0 + 1), brown)
		_fill(leg, origin, Vector3i(x0, 0, z0), Vector3i(x0 + 1, 0, z0 + 1), hoof)

	# Tail pivots at the top of the rump
	var tail_origin := Vector3(-0.5, 9.5, 4.5)
	_tail = Node3D.new()
	_tail.position = tail_origin * VOX
	_body.add_child(_tail)
	_fill(_tail, tail_origin, Vector3i(-1, 5, 5), Vector3i(0, 9, 6), dark)


## Places one voxel per cell in the inclusive range lo..hi, attached to `parent`.
## `origin` is the parent's pivot in cell units; cells in `skip` are left out.
func _fill(parent: Node3D, origin: Vector3, lo: Vector3i, hi: Vector3i, color: Color, skip: Array = []) -> void:
	for x in range(lo.x, hi.x + 1):
		for y in range(lo.y, hi.y + 1):
			for z in range(lo.z, hi.z + 1):
				var cell := Vector3i(x, y, z)
				if cell in skip:
					continue
				var voxel := MeshInstance3D.new()
				voxel.mesh = _mesh
				voxel.material_override = _material(color)
				voxel.position = (Vector3(cell) - origin) * VOX
				parent.add_child(voxel)


## Returns a cached material with one of three slight shade variations.
func _material(color: Color) -> StandardMaterial3D:
	var shade := _rng.randi_range(0, 2)
	var key := "%s_%d" % [color.to_html(), shade]
	if not _materials.has(key):
		var factor: float = [0.92, 1.0, 1.08][shade]
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(color.r * factor, color.g * factor, color.b * factor)
		mat.roughness = 0.9
		_materials[key] = mat
	return _materials[key]
