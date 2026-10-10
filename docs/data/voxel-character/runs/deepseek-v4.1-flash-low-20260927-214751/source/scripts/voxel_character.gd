extends CharacterBody3D
class_name VoxelCharacter

## A blocky character built entirely from unit cubes.
## The character is playable: move with WASD / arrows, jump with Space.

const SPEED := 6.5
const JUMP_VELOCITY := 8.2
const GRAVITY := 22.0
const GROUND_ACCEL := 55.0
const AIR_ACCEL := 22.0
const GROUND_FRICTION := 45.0
const TURN_SPEED := 14.0

var model: Node3D
var head: Node3D
var left_arm: Node3D
var right_arm: Node3D
var left_leg: Node3D
var right_leg: Node3D

var run_phase := 0.0
var _target_yaw := 0.0
var _was_on_floor := true


func _ready() -> void:
	_build_model()
	_build_collider()
	floor_max_angle = deg_to_rad(52.0)
	floor_snap_length = 0.35


func _build_collider() -> void:
	var col := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.38
	capsule.height = 1.5
	col.shape = capsule
	col.position = Vector3(0.0, 0.75, 0.0)
	add_child(col)


func _build_model() -> void:
	model = Node3D.new()
	add_child(model)

	var skin := Color(0.96, 0.78, 0.58)
	var shirt := Color(0.20, 0.52, 0.92)
	var shirt_dark := Color(0.14, 0.40, 0.76)
	var pants := Color(0.20, 0.24, 0.34)
	var shoe := Color(0.10, 0.10, 0.13)
	var hair := Color(0.24, 0.14, 0.07)

	# Torso and belt.
	_box(model, Vector3(0.0, 1.06, 0.0), Vector3(0.72, 0.70, 0.40), shirt)
	_box(model, Vector3(0.0, 0.74, 0.0), Vector3(0.76, 0.12, 0.44), shirt_dark)

	# Head hangs from a pivot so it can bob independently.
	head = Node3D.new()
	head.position = Vector3(0.0, 1.41, 0.0)
	model.add_child(head)
	_box(head, Vector3(0.0, 0.28, 0.0), Vector3(0.56, 0.56, 0.56), skin)
	_box(head, Vector3(0.0, 0.54, 0.0), Vector3(0.60, 0.12, 0.60), hair)
	_box(head, Vector3(0.0, 0.56, -0.16), Vector3(0.60, 0.14, 0.28), hair)
	# Eyes on +Z (the direction the character faces).
	_box(head, Vector3(-0.14, 0.30, 0.285), Vector3(0.10, 0.10, 0.06), Color(0.10, 0.10, 0.12))
	_box(head, Vector3(0.14, 0.30, 0.285), Vector3(0.10, 0.10, 0.06), Color(0.10, 0.10, 0.12))

	# Arms: pivot at the shoulder, mesh hangs below.
	left_arm = _limb(model, Vector3(-0.47, 1.34, 0.0), Vector3(0.18, 0.62, 0.18), skin)
	right_arm = _limb(model, Vector3(0.47, 1.34, 0.0), Vector3(0.18, 0.62, 0.18), skin)
	_box(left_arm, Vector3(0.0, -0.66, 0.0), Vector3(0.20, 0.14, 0.22), shirt_dark)
	_box(right_arm, Vector3(0.0, -0.66, 0.0), Vector3(0.20, 0.14, 0.22), shirt_dark)

	# Legs: pivot at the hip, shoe at the bottom.
	left_leg = _limb(model, Vector3(-0.19, 0.70, 0.0), Vector3(0.24, 0.70, 0.24), pants)
	right_leg = _limb(model, Vector3(0.19, 0.70, 0.0), Vector3(0.24, 0.70, 0.24), pants)
	_box(left_leg, Vector3(0.0, -0.68, 0.05), Vector3(0.26, 0.14, 0.34), shoe)
	_box(right_leg, Vector3(0.0, -0.68, 0.05), Vector3(0.26, 0.14, 0.34), shoe)


func _box(parent: Node3D, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.85
	mesh.material = mat
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.position = pos
	parent.add_child(mi)
	return mi


func _limb(parent: Node3D, joint: Vector3, size: Vector3, color: Color) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = joint
	parent.add_child(pivot)
	_box(pivot, Vector3(0.0, -size.y * 0.5, 0.0), size, color)
	return pivot


func _physics_process(delta: float) -> void:
	# --- Gravity / jumping -------------------------------------------------
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif _was_on_floor == false and velocity.y < 0.0:
		velocity.y = 0.0

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY

	# --- Camera-relative movement input -----------------------------------
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var dir := Vector3.ZERO
	var cam := get_viewport().get_camera_3d()
	if cam and input.length() > 0.01:
		var cb := cam.global_transform.basis
		var forward := Vector3(-cb.z.x, 0.0, -cb.z.z).normalized()
		var right := Vector3(cb.x.x, 0.0, cb.x.z).normalized()
		dir = (right * input.x + forward * -input.y).normalized()

	# --- Horizontal acceleration / friction -------------------------------
	var horizontal := Vector3(velocity.x, 0.0, velocity.z)
	if dir.length() > 0.01:
		horizontal = horizontal.move_toward(dir * SPEED, GROUND_ACCEL * delta)
		_target_yaw = atan2(dir.x, dir.z)
	else:
		var friction := GROUND_FRICTION if is_on_floor() else AIR_ACCEL * 0.35
		horizontal = horizontal.move_toward(Vector3.ZERO, friction * delta)

	velocity.x = horizontal.x
	velocity.z = horizontal.z

	# --- Turn the body towards the running direction ----------------------
	model.rotation.y = lerp_angle(model.rotation.y, _target_yaw, 1.0 - exp(-TURN_SPEED * delta))

	move_and_slide()
	_animate(delta, horizontal.length() / SPEED)
	_was_on_floor = is_on_floor()


func _animate(delta: float, speed_ratio: float) -> void:
	if is_on_floor() and speed_ratio > 0.06:
		# Running: swing arms and legs in opposite phase.
		run_phase += delta * (9.0 + speed_ratio * 7.0)
		var swing: float = sin(run_phase) * 0.95 * speed_ratio
		left_arm.rotation.x = swing
		right_arm.rotation.x = -swing
		left_leg.rotation.x = -swing
		right_leg.rotation.x = swing
		model.position.y = abs(sin(run_phase)) * 0.07 * speed_ratio
		head.rotation.x = -0.05 * speed_ratio
	elif not is_on_floor():
		# Airborne: tuck the legs, raise the arms.
		left_arm.rotation.x = lerp_angle(left_arm.rotation.x, -0.9, 10.0 * delta)
		right_arm.rotation.x = lerp_angle(right_arm.rotation.x, -0.9, 10.0 * delta)
		left_leg.rotation.x = lerp_angle(left_leg.rotation.x, 0.45, 10.0 * delta)
		right_leg.rotation.x = lerp_angle(right_leg.rotation.x, 0.25, 10.0 * delta)
		model.position.y = lerp(model.position.y, 0.0, 10.0 * delta)
	else:
		# Idle: gentle breathing and a small head bob.
		run_phase += delta * 2.2
		var breathe: float = sin(run_phase) * 0.05
		left_arm.rotation.x = lerp_angle(left_arm.rotation.x, breathe * 0.6, 8.0 * delta)
		right_arm.rotation.x = lerp_angle(right_arm.rotation.x, -breathe * 0.6, 8.0 * delta)
		left_leg.rotation.x = lerp_angle(left_leg.rotation.x, 0.0, 8.0 * delta)
		right_leg.rotation.x = lerp_angle(right_leg.rotation.x, 0.0, 8.0 * delta)
		model.position.y = lerp(model.position.y, 0.0, 8.0 * delta)
		head.rotation.x = lerp_angle(head.rotation.x, 0.0, 8.0 * delta)
