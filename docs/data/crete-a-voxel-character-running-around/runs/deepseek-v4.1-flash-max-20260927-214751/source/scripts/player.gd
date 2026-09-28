extends CharacterBody3D
## The player: a blocky voxel character with a procedural run cycle.
##
## Movement is camera-relative, includes sprinting, coyote-time jumping and
## a small step-up helper so the character can climb one-block ledges.

const WALK_SPEED := 5.0
const SPRINT_SPEED := 8.0
const ACCELERATION := 30.0
const AIR_ACCELERATION := 14.0
const JUMP_VELOCITY := 6.6
const GRAVITY := 17.0
const STEP_HEIGHT := 1.15

var camera_yaw := 0.0
var spawn_point := Vector3.ZERO

var _visual: Node3D
var _torso: Node3D
var _head: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _dust: CPUParticles3D
var _phase := 0.0
var _coyote := 0.0
var _land := 0.0


func _ready() -> void:
	up_direction = Vector3.UP
	floor_snap_length = 0.4
	collision_layer = 2
	collision_mask = 1
	spawn_point = global_position

	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.36
	capsule.height = 1.95
	shape.shape = capsule
	shape.position = Vector3(0.0, 0.98, 0.0)
	add_child(shape)

	_build_model()
	_build_dust()


func reset_to_spawn() -> void:
	global_position = spawn_point + Vector3(0.0, 0.5, 0.0)
	velocity = Vector3.ZERO


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

func _mat(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	return mat


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = mat
	mi.mesh = bm
	mi.position = pos
	parent.add_child(mi)
	return mi


func _build_model() -> void:
	_visual = Node3D.new()
	add_child(_visual)

	var skin := _mat(Color(0.9, 0.68, 0.48))
	var shirt := _mat(Color(0.16, 0.5, 0.85))
	var pants := _mat(Color(0.18, 0.2, 0.38))
	var shoes := _mat(Color(0.14, 0.14, 0.17))
	var hair := _mat(Color(0.2, 0.13, 0.08))
	var dark := _mat(Color(0.08, 0.08, 0.1))

	# Legs (pivot at the hips).
	_leg_l = Node3D.new()
	_leg_l.position = Vector3(-0.17, 0.78, 0.0)
	_visual.add_child(_leg_l)
	_box(_leg_l, Vector3(0.22, 0.62, 0.24), Vector3(0.0, -0.31, 0.0), pants)
	_box(_leg_l, Vector3(0.26, 0.14, 0.32), Vector3(0.0, -0.69, -0.02), shoes)

	_leg_r = Node3D.new()
	_leg_r.position = Vector3(0.17, 0.78, 0.0)
	_visual.add_child(_leg_r)
	_box(_leg_r, Vector3(0.22, 0.62, 0.24), Vector3(0.0, -0.31, 0.0), pants)
	_box(_leg_r, Vector3(0.26, 0.14, 0.32), Vector3(0.0, -0.69, -0.02), shoes)

	# Torso group (bobs while running).
	_torso = Node3D.new()
	_visual.add_child(_torso)
	_box(_torso, Vector3(0.62, 0.66, 0.36), Vector3(0.0, 1.11, 0.0), shirt)

	# Arms (pivot at the shoulders).
	_arm_l = Node3D.new()
	_arm_l.position = Vector3(-0.4, 1.36, 0.0)
	_torso.add_child(_arm_l)
	_box(_arm_l, Vector3(0.18, 0.52, 0.2), Vector3(0.0, -0.26, 0.0), shirt)
	_box(_arm_l, Vector3(0.2, 0.16, 0.22), Vector3(0.0, -0.58, 0.0), skin)

	_arm_r = Node3D.new()
	_arm_r.position = Vector3(0.4, 1.36, 0.0)
	_torso.add_child(_arm_r)
	_box(_arm_r, Vector3(0.18, 0.52, 0.2), Vector3(0.0, -0.26, 0.0), shirt)
	_box(_arm_r, Vector3(0.2, 0.16, 0.22), Vector3(0.0, -0.58, 0.0), skin)

	# Head with a tiny face pointing down -Z (the character's forward).
	_head = Node3D.new()
	_head.position = Vector3(0.0, 1.44, 0.0)
	_torso.add_child(_head)
	_box(_head, Vector3(0.52, 0.52, 0.52), Vector3(0.0, 0.26, 0.0), skin)
	_box(_head, Vector3(0.56, 0.16, 0.56), Vector3(0.0, 0.52, 0.0), hair)
	_box(_head, Vector3(0.11, 0.11, 0.06), Vector3(-0.13, 0.3, -0.27), dark)
	_box(_head, Vector3(0.11, 0.11, 0.06), Vector3(0.13, 0.3, -0.27), dark)


func _build_dust() -> void:
	_dust = CPUParticles3D.new()
	_dust.amount = 12
	_dust.lifetime = 0.5
	_dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	_dust.emission_sphere_radius = 0.3
	_dust.direction = Vector3.UP
	_dust.spread = 45.0
	_dust.initial_velocity_min = 0.4
	_dust.initial_velocity_max = 1.2
	_dust.gravity = Vector3(0.0, -3.0, 0.0)
	_dust.scale_amount_min = 0.06
	_dust.scale_amount_max = 0.14
	_dust.color = Color(0.75, 0.68, 0.52, 0.7)
	_dust.local_coords = false

	var bm := BoxMesh.new()
	bm.size = Vector3.ONE
	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bm.material = mat
	_dust.mesh = bm

	_dust.position = Vector3(0.0, 0.1, 0.0)
	_dust.emitting = false
	add_child(_dust)


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var dir := Vector3(input.x, 0.0, input.y).rotated(Vector3.UP, camera_yaw)
	if dir.length_squared() > 0.0001:
		dir = dir.normalized()

	var speed := SPRINT_SPEED if Input.is_action_pressed("sprint") else WALK_SPEED
	var horizontal := Vector3(velocity.x, 0.0, velocity.z)
	var accel := ACCELERATION if is_on_floor() else AIR_ACCELERATION
	horizontal = horizontal.move_toward(dir * speed, accel * delta)
	velocity.x = horizontal.x
	velocity.z = horizontal.z

	if is_on_floor():
		_coyote = 0.12
	else:
		_coyote = maxf(0.0, _coyote - delta)
		velocity.y = maxf(velocity.y - GRAVITY * delta, -28.0)

	if Input.is_action_just_pressed("jump") and _coyote > 0.0:
		velocity.y = JUMP_VELOCITY
		_coyote = 0.0

	var was_on_floor := is_on_floor()
	move_and_slide()
	if is_on_floor() and not was_on_floor:
		_land = 1.0
	if is_on_floor():
		_step_up(delta)

	_animate(delta, dir)


func _step_up(delta: float) -> void:
	# Lets the character walk up single-block voxel steps.
	var horizontal := Vector3(velocity.x, 0.0, velocity.z) * delta
	if horizontal.length_squared() < 0.000001 or not is_on_wall():
		return
	var t := global_transform
	if not test_move(t, horizontal):
		return
	var lift := Vector3.UP * STEP_HEIGHT
	if test_move(t, lift):
		return
	var lifted := t.translated(lift)
	if test_move(lifted, horizontal):
		return
	global_position += lift


func _animate(delta: float, dir: Vector3) -> void:
	var k := 1.0 - exp(-12.0 * delta)
	var speed := Vector3(velocity.x, 0.0, velocity.z).length()

	if dir.length_squared() > 0.0001:
		var target_yaw := atan2(-dir.x, -dir.z)
		_visual.rotation.y = lerp_angle(_visual.rotation.y, target_yaw, 1.0 - exp(-14.0 * delta))

	_land = maxf(0.0, _land - delta * 4.5)

	if is_on_floor() and speed > 0.5:
		# Run cycle.
		_phase += delta * (4.0 + speed * 1.7)
		var amp := clampf(speed / SPRINT_SPEED, 0.0, 1.0)
		var swing := sin(_phase) * amp
		var kk := 1.0 - exp(-18.0 * delta)
		_arm_l.rotation.x = lerpf(_arm_l.rotation.x, swing, kk)
		_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -swing, kk)
		_leg_l.rotation.x = lerpf(_leg_l.rotation.x, -swing, kk)
		_leg_r.rotation.x = lerpf(_leg_r.rotation.x, swing, kk)
		_torso.position.y = absf(sin(_phase * 2.0)) * 0.05 - _land * 0.14
		_head.rotation.x = sin(_phase * 2.0) * 0.04
		_dust.emitting = speed > 3.5
	elif not is_on_floor():
		# Airborne pose.
		_dust.emitting = false
		_arm_l.rotation.x = lerpf(_arm_l.rotation.x, -2.2, k * 0.7)
		_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -2.2, k * 0.7)
		_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.4, k * 0.7)
		_leg_r.rotation.x = lerpf(_leg_r.rotation.x, -0.3, k * 0.7)
		_torso.position.y = lerpf(_torso.position.y, 0.02, k)
		_head.rotation.x = lerpf(_head.rotation.x, 0.0, k)
	else:
		# Idle breathing.
		_dust.emitting = false
		_phase += delta * 1.4
		var breathe := sin(_phase) * 0.04
		_arm_l.rotation.x = lerpf(_arm_l.rotation.x, breathe, k * 0.5)
		_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -breathe, k * 0.5)
		_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.0, k * 0.5)
		_leg_r.rotation.x = lerpf(_leg_r.rotation.x, 0.0, k * 0.5)
		_torso.position.y = lerpf(_torso.position.y, sin(_phase * 2.0) * 0.02 - _land * 0.14, k)
		_head.rotation.x = lerpf(_head.rotation.x, 0.0, k)
