extends CharacterBody3D
## A blocky (voxel) character controller with a procedural run cycle.

@export var move_speed := 6.0
@export var jump_velocity := 6.0
@export var gravity := 20.0
@export var turn_speed := 12.0

const U := 0.25 # one voxel unit

var _visual: Node3D
var _torso: Node3D
var _head: Node3D
var _left_arm: Node3D
var _right_arm: Node3D
var _left_leg: Node3D
var _right_leg: Node3D

var _run_time := 0.0
var _move_amount := 0.0

func _ready() -> void:
	_build_body()
	_build_collision()

# ---------------------------------------------------------------------------
# Procedural voxel model
# ---------------------------------------------------------------------------
func _build_body() -> void:
	# The whole model hangs off a Visual node so it can bob and lean.
	_visual = Node3D.new()
	_visual.name = "Visual"
	add_child(_visual)

	# Torso
	var torso_color := Color(0.87, 0.33, 0.25)
	var torso := _make_box("TorsoMesh", Vector3(0, 0, 0), Vector3(2 * U, 3 * U, 1 * U), torso_color)
	_visual.add_child(torso)
	torso.position = Vector3(0, 4.5 * U, 0)

	# Head with a simple face block
	var head := Node3D.new()
	head.name = "Head"
	head.position = Vector3(0, 6 * U, 0)
	_visual.add_child(head)
	head.add_child(_make_box("HeadMesh", Vector3.ZERO, Vector3(2 * U, 2 * U, 2 * U), Color(0.95, 0.76, 0.58)))
	head.add_child(_make_box("EyeL", Vector3(-0.42 * U, 0.15 * U, 1.01 * U), Vector3(0.32 * U, 0.32 * U, 0.06 * U), Color(0.1, 0.1, 0.12)))
	head.add_child(_make_box("EyeR", Vector3(0.42 * U, 0.15 * U, 1.01 * U), Vector3(0.32 * U, 0.32 * U, 0.06 * U), Color(0.1, 0.1, 0.12)))

	# Arms pivot at the shoulder; the mesh hangs below the pivot.
	_left_arm = _make_limb_pivot("LeftArm", Vector3(-1.55 * U, 5.7 * U, 0))
	_visual.add_child(_left_arm)
	_left_arm.add_child(_make_box("ArmMesh", Vector3(0, -1.4 * U, 0), Vector3(0.8 * U, 2.8 * U, 0.8 * U), Color(0.95, 0.76, 0.58)))
	_left_arm.add_child(_make_box("Sleeve", Vector3(0, -0.25 * U, 0), Vector3(0.9 * U, 0.9 * U, 0.9 * U), torso_color))

	_right_arm = _make_limb_pivot("RightArm", Vector3(1.55 * U, 5.7 * U, 0))
	_visual.add_child(_right_arm)
	_right_arm.add_child(_make_box("ArmMesh", Vector3(0, -1.4 * U, 0), Vector3(0.8 * U, 2.8 * U, 0.8 * U), Color(0.95, 0.76, 0.58)))
	_right_arm.add_child(_make_box("Sleeve", Vector3(0, -0.25 * U, 0), Vector3(0.9 * U, 0.9 * U, 0.9 * U), torso_color))

	# Legs pivot at the hip; base of the leg rests on the ground.
	_left_leg = _make_limb_pivot("LeftLeg", Vector3(-0.55 * U, 3 * U, 0))
	_visual.add_child(_left_leg)
	_left_leg.add_child(_make_box("LegMesh", Vector3(0, -1.5 * U, 0), Vector3(0.9 * U, 3 * U, 0.9 * U), Color(0.22, 0.33, 0.55)))
	_left_leg.add_child(_make_box("Foot", Vector3(0, -2.8 * U, 0.4 * U), Vector3(0.9 * U, 0.5 * U, 1.3 * U), Color(0.15, 0.15, 0.18)))

	_right_leg = _make_limb_pivot("RightLeg", Vector3(0.55 * U, 3 * U, 0))
	_visual.add_child(_right_leg)
	_right_leg.add_child(_make_box("LegMesh", Vector3(0, -1.5 * U, 0), Vector3(0.9 * U, 3 * U, 0.9 * U), Color(0.22, 0.33, 0.55)))
	_right_leg.add_child(_make_box("Foot", Vector3(0, -2.8 * U, 0.4 * U), Vector3(0.9 * U, 0.5 * U, 1.3 * U), Color(0.15, 0.15, 0.18)))

func _build_collision() -> void:
	var shape := CollisionShape3D.new()
	shape.name = "BodyShape"
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.32
	capsule.height = 1.9
	shape.shape = capsule
	shape.position = Vector3(0, 0.95, 0)
	add_child(shape)

# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------
func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta

	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction := Vector3(input_dir.x, 0.0, input_dir.y)
	var target_amount := direction.length()
	if target_amount > 0.01:
		direction = direction.normalized()
		var target_yaw := atan2(direction.x, direction.z)
		rotation.y = lerp_angle(rotation.y, target_yaw, turn_speed * delta)
	_move_amount = move_toward(_move_amount, target_amount, delta * 4.0)

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = jump_velocity

	velocity.x = direction.x * move_speed
	velocity.z = direction.z * move_speed
	move_and_slide()

	_animate(delta)

func _animate(delta: float) -> void:
	var moving := _move_amount > 0.05
	if moving:
		_run_time += delta * (8.0 + 4.0 * _move_amount)
		var swing := sin(_run_time) * 0.95 * _move_amount
		_left_leg.rotation.x = swing
		_right_leg.rotation.x = -swing
		_left_arm.rotation.x = -swing * 0.8
		_right_arm.rotation.x = swing * 0.8
		_left_arm.rotation.z = 0.08
		_right_arm.rotation.z = -0.08
		# Vertical bob and a slight forward lean.
		var bob: float = absf(sin(_run_time)) * 0.05 * _move_amount
		_visual.position.y = bob
		_visual.rotation.x = -0.08 * _move_amount
		_head.rotation.z = sin(_run_time * 0.5) * 0.03
	else:
		# Idle breathing.
		_run_time = 0.0
		var idle := sin(Time.get_ticks_msec() * 0.002) * 0.03
		_left_leg.rotation.x = lerp(_left_leg.rotation.x, 0.0, delta * 8.0)
		_right_leg.rotation.x = lerp(_right_leg.rotation.x, 0.0, delta * 8.0)
		_left_arm.rotation.x = lerp(_left_arm.rotation.x, idle, delta * 8.0)
		_right_arm.rotation.x = lerp(_right_arm.rotation.x, idle, delta * 8.0)
		_left_arm.rotation.z = lerp(_left_arm.rotation.z, 0.06, delta * 8.0)
		_right_arm.rotation.z = lerp(_right_arm.rotation.z, -0.06, delta * 8.0)
		_visual.position.y = lerp(_visual.position.y, 0.0, delta * 8.0)
		_visual.rotation.x = lerp(_visual.rotation.x, 0.0, delta * 8.0)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
func _make_box(node_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = node_name
	var mesh := BoxMesh.new()
	mesh.size = size
	mi.mesh = mesh
	mi.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 1.0
	mat.metallic = 0.0
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return mi

func _make_limb_pivot(node_name: String, pos: Vector3) -> Node3D:
	var pivot := Node3D.new()
	pivot.name = node_name
	pivot.position = pos
	return pivot
