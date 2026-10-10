extends CharacterBody3D

const MOVE_SPEED := 5.0
const ACCEL_GROUND := 40.0
const ACCEL_AIR := 12.0
const GRAVITY := 22.0
const FACING_LERP_SPEED := 12.0
const ARM_SPEED := 11.0
const BOUNCE_SCALE := 0.03

@onready var body: Node3D = $Body
@onready var arm_l: Node3D = $Body/ArmL
@onready var arm_r: Node3D = $Body/ArmR
@onready var leg_l: Node3D = $Body/LegL
@onready var leg_r: Node3D = $Body/LegR

var _run_time := 0.0


func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()

	# Gravity
	if on_floor:
		velocity.y = 0.0
	elif velocity.y > 0.0:
		velocity.y = 0.0
	else:
		velocity.y -= GRAVITY * delta

	# Read input relative to the camera's facing direction
	var cam_basis: Basis = get_viewport().get_camera_3d().global_transform.basis
	var input_vec := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var wish_dir := (cam_basis * Vector3(input_vec.x, 0.0, input_vec.y))
	wish_dir.y = 0.0
	if wish_dir.length_squared() > 1.0:
		wish_dir = wish_dir.normalized()

	var accel := ACCEL_GROUND if on_floor else ACCEL_AIR
	var target_hvel := wish_dir * MOVE_SPEED
	velocity.x = move_toward(velocity.x, target_hvel.x, accel * delta)
	velocity.z = move_toward(velocity.z, target_hvel.z, accel * delta)

	move_and_slide()

	# Face the movement direction (smooth turn)
	var hvel := Vector3(velocity.x, 0.0, velocity.z)
	if hvel.length() > 0.25:
		var target_yaw := atan2(velocity.x, velocity.z)
		var current_yaw := rotation.y
		var diff := wrapf(target_yaw - current_yaw, -PI, PI)
		rotation.y = current_yaw + diff * clampf(FACING_LERP_SPEED * delta, 0.0, 1.0)

	_update_animation(delta, on_floor)


func _update_animation(delta: float, on_floor: bool) -> void:
	var speed := Vector3(velocity.x, 0.0, velocity.z).length()

	if on_floor and speed > 0.3:
		_run_time += delta * ARM_SPEED
		var swing := sin(_run_time)
		leg_l.rotation.x = swing * 0.95
		leg_r.rotation.x = -swing * 0.95
		arm_l.rotation.x = -swing * 0.85
		arm_r.rotation.x = swing * 0.85
		# Light vertical bob so the run feels lively
		body.position.y = abs(sin(_run_time)) * 0.06 * min(speed / MOVE_SPEED, 1.2)
	else:
		# Ease limbs back to rest
		var t := clampf(10.0 * delta, 0.0, 1.0)
		leg_l.rotation.x = lerpf(leg_l.rotation.x, 0.0, t)
		leg_r.rotation.x = lerpf(leg_r.rotation.x, 0.0, t)
		arm_l.rotation.x = lerpf(arm_l.rotation.x, 0.0, t)
		arm_r.rotation.x = lerpf(arm_r.rotation.x, 0.0, t)
		body.position.y = lerpf(body.position.y, 0.0, t)
