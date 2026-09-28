extends CharacterBody3D
## Voxel character: third-person runner with procedural run animation.
## Movement input is read relative to `camera_yaw` (assigned by main.gd).

const WALK_SPEED := 6.0
const SPRINT_SPEED := 9.5
const ACCEL := 22.0
const AIR_CONTROL := 8.0
const JUMP_VELOCITY := 7.5
const GRAVITY := 22.0

var camera_yaw: Node3D

var rig: Node3D
var torso: MeshInstance3D
var head_pivot: Node3D
var arm_l: Node3D
var arm_r: Node3D
var leg_l: Node3D
var leg_r: Node3D
var dust: CPUParticles3D

var _phase := 0.0
var _facing_yaw := 0.0
var _was_on_floor := true

func _ready() -> void:
	add_to_group("player")
	collision_layer = 1
	collision_mask = 1
	floor_snap_length = 0.35
	_build_collision()
	_build_rig()


func bounce(power: float = 12.0) -> void:
	velocity.y = power


func _physics_process(delta: float) -> void:
	var input_dir := _read_input_dir()

	var speed := 0.0
	var wish := Vector3.ZERO
	if input_dir.length() > 0.01:
		var yaw := 0.0
		if is_instance_valid(camera_yaw):
			yaw = camera_yaw.global_rotation.y
		var basis_y := Basis(Vector3.UP, yaw)
		wish = (basis_y * Vector3(input_dir.x, 0.0, input_dir.y)).normalized()
		var sprinting := Input.is_physical_key_pressed(KEY_SHIFT)
		speed = SPRINT_SPEED if sprinting else WALK_SPEED

	# Horizontal velocity with acceleration.
	var hv := Vector3(velocity.x, 0.0, velocity.z)
	var accel := ACCEL if is_on_floor() else AIR_CONTROL
	if wish.length() > 0.01:
		hv = hv.move_toward(wish * speed, accel * delta)
	else:
		var friction := ACCEL if is_on_floor() else 2.0
		hv = hv.move_toward(Vector3.ZERO, friction * delta)
	velocity.x = hv.x
	velocity.z = hv.z

	# Gravity + jump (Space / Enter via ui_accept).
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif Input.is_action_just_pressed("ui_accept"):
		velocity.y = JUMP_VELOCITY
		_spawn_jump_puff()

	move_and_slide()
	_animate(delta, hv.length(), wish)


func _read_input_dir() -> Vector2:
	# x = strafe (+right), y = forward axis (+backward, since -Z is forward).
	var x := 0.0
	var y := 0.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_action_pressed("ui_left"):
		x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_action_pressed("ui_right"):
		x += 1.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_action_pressed("ui_up"):
		y -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_action_pressed("ui_down"):
		y += 1.0
	var v := Vector2(x, y)
	if v.length() > 1.0:
		v = v.normalized()
	return v


func _animate(delta: float, planar_speed: float, wish: Vector3) -> void:
	# Face movement direction smoothly.
	if wish.length() > 0.05:
		var target := atan2(wish.x, wish.z)
		_facing_yaw = lerp_angle(_facing_yaw, target, 1.0 - exp(-12.0 * delta))
	rig.rotation.y = _facing_yaw

	var run_amount := clampf(planar_speed / SPRINT_SPEED, 0.0, 1.0)
	_phase += delta * (4.0 + planar_speed * 1.9)

	if is_on_floor():
		if planar_speed > 0.5:
			var swing: float = sin(_phase) * lerpf(0.35, 1.0, run_amount)
			arm_l.rotation.x = swing
			arm_r.rotation.x = -swing
			leg_l.rotation.x = -swing
			leg_r.rotation.x = swing
			# Slight bounce + forward lean while running.
			rig.position.y = abs(cos(_phase)) * 0.07 * run_amount
			rig.rotation.x = lerp(0.0, 0.14, run_amount)
		else:
			# Idle: gentle breathing.
			var t := Time.get_ticks_msec() / 1000.0
			arm_l.rotation.x = lerpf(arm_l.rotation.x, 0.0, 10.0 * delta)
			arm_r.rotation.x = lerpf(arm_r.rotation.x, 0.0, 10.0 * delta)
			leg_l.rotation.x = lerpf(leg_l.rotation.x, 0.0, 10.0 * delta)
			leg_r.rotation.x = lerpf(leg_r.rotation.x, 0.0, 10.0 * delta)
			rig.position.y = sin(t * 2.2) * 0.02
			rig.rotation.x = lerpf(rig.rotation.x, 0.0, 10.0 * delta)
		_was_on_floor = true
		if dust:
			dust.emitting = planar_speed > 6.5
	else:
		# Airborne pose: legs tucked, arms up.
		arm_l.rotation.x = lerpf(arm_l.rotation.x, -0.9, 8.0 * delta)
		arm_r.rotation.x = lerpf(arm_r.rotation.x, -0.9, 8.0 * delta)
		leg_l.rotation.x = lerpf(leg_l.rotation.x, 0.45, 8.0 * delta)
		leg_r.rotation.x = lerpf(leg_r.rotation.x, -0.25, 8.0 * delta)
		rig.rotation.x = lerpf(rig.rotation.x, -0.06, 8.0 * delta)
		_was_on_floor = false
		if dust:
			dust.emitting = false


func _build_collision() -> void:
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.5
	shape.shape = capsule
	shape.position = Vector3(0.0, 0.85, 0.0)
	add_child(shape)


func _mat(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.9
	return m


func _box(size: Vector3, color: Color, pos: Vector3, parent: Node3D) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh.material = _mat(color)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.position = pos
	parent.add_child(mi)
	return mi


func _build_rig() -> void:
	rig = Node3D.new()
	rig.name = "Rig"
	add_child(rig)

	var skin := Color(1.0, 0.85, 0.66)
	var shirt := Color(0.25, 0.5, 0.85)
	var pants := Color(0.2, 0.25, 0.36)
	var hair := Color(0.35, 0.22, 0.12)
	var shoe := Color(0.85, 0.3, 0.25)

	# Torso.
	torso = _box(Vector3(0.6, 0.6, 0.36), shirt, Vector3(0, 1.0, 0), rig)
	# Belt.
	_box(Vector3(0.62, 0.1, 0.38), Color(0.16, 0.18, 0.24), Vector3(0, 0.74, 0), rig)

	# Head group.
	head_pivot = Node3D.new()
	head_pivot.position = Vector3(0, 1.3, 0)
	rig.add_child(head_pivot)
	_box(Vector3(0.46, 0.42, 0.42), skin, Vector3(0, 0.25, 0), head_pivot)
	# Hair cap + fringe.
	_box(Vector3(0.5, 0.14, 0.46), hair, Vector3(0, 0.47, 0), head_pivot)
	_box(Vector3(0.5, 0.1, 0.08), hair, Vector3(0, 0.38, 0.2), head_pivot)
	# Eyes (face toward +Z, rig faces movement via yaw).
	_box(Vector3(0.07, 0.09, 0.03), Color(0.1, 0.1, 0.12), Vector3(-0.11, 0.26, 0.215), head_pivot)
	_box(Vector3(0.07, 0.09, 0.03), Color(0.1, 0.1, 0.12), Vector3(0.11, 0.26, 0.215), head_pivot)
	# Smile.
	_box(Vector3(0.14, 0.04, 0.03), Color(0.4, 0.2, 0.2), Vector3(0, 0.12, 0.215), head_pivot)

	# Arms (pivot at shoulder).
	for side in [-1.0, 1.0]:
		var pivot := Node3D.new()
		pivot.position = Vector3(0.41 * side, 1.24, 0)
		rig.add_child(pivot)
		_box(Vector3(0.22, 0.42, 0.24), shirt, Vector3(0, -0.2, 0), pivot)
		_box(Vector3(0.2, 0.22, 0.22), skin, Vector3(0, -0.5, 0), pivot)
		if side < 0.0:
			arm_l = pivot
		else:
			arm_r = pivot

	# Legs (pivot at hip).
	for side in [-1.0, 1.0]:
		var pivot := Node3D.new()
		pivot.position = Vector3(0.16 * side, 0.7, 0)
		rig.add_child(pivot)
		_box(Vector3(0.26, 0.45, 0.28), pants, Vector3(0, -0.22, 0), pivot)
		_box(Vector3(0.27, 0.16, 0.34), shoe, Vector3(0, -0.5, 0.03), pivot)
		if side < 0.0:
			leg_l = pivot
		else:
			leg_r = pivot

	# Scarf: knot + trailing tail for a sense of speed.
	_box(Vector3(0.4, 0.12, 0.12), Color(0.9, 0.25, 0.3), Vector3(0, 1.32, -0.14), rig)
	_box(Vector3(0.22, 0.08, 0.4), Color(0.9, 0.25, 0.3), Vector3(0.1, 1.26, -0.36), rig)

	# Running dust puffs.
	dust = CPUParticles3D.new()
	dust.amount = 18
	dust.lifetime = 0.5
	dust.emitting = false
	dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	dust.emission_sphere_radius = 0.25
	dust.direction = Vector3(0, 1, 0)
	dust.spread = 35.0
	dust.initial_velocity_min = 1.0
	dust.initial_velocity_max = 2.5
	dust.gravity = Vector3(0, -2, 0)
	dust.scale_amount_min = 0.06
	dust.scale_amount_max = 0.14
	dust.color = Color(1, 1, 1, 0.8)
	var puff := BoxMesh.new()
	puff.size = Vector3(0.12, 0.12, 0.12)
	puff.material = _mat(Color(0.95, 0.93, 0.88))
	dust.mesh = puff
	dust.position = Vector3(0, 0.15, 0)
	add_child(dust)


func _spawn_jump_puff() -> void:
	if dust:
		dust.restart()
