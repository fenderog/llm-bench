extends CharacterBody3D
## Voxel character: built entirely from BoxMesh parts, animated procedurally.

const SPEED := 6.0
const SPRINT_MULT := 1.5
const JUMP_VELOCITY := 7.0
const MOUSE_SENS := 0.004

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
var yaw := 0.0
var pitch := -0.55
var run_phase := 0.0

var rig: Node3D
var cam_pivot: Node3D
var torso: MeshInstance3D
var head: MeshInstance3D
var arm_l: Node3D
var arm_r: Node3D
var leg_l: Node3D
var leg_r: Node3D

func _ready() -> void:
	rig = $Rig
	cam_pivot = $CamPivot
	_build_voxel_body()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * MOUSE_SENS
		pitch = clampf(pitch - event.relative.y * MOUSE_SENS, -1.2, 0.35)
	if event is InputEventMouseButton and event.pressed:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _physics_process(delta: float) -> void:
	# Gravity
	if not is_on_floor():
		velocity.y -= gravity * delta
	# Jump
	if Input.is_action_just_pressed("ui_accept") or Input.is_key_pressed(KEY_SPACE):
		if is_on_floor():
			velocity.y = JUMP_VELOCITY
	# WASD / arrows
	var ix := Input.get_axis("ui_left", "ui_right")
	var iz := Input.get_axis("ui_up", "ui_down")
	var sprint := 1.0
	if Input.is_key_pressed(KEY_SHIFT):
		sprint = SPRINT_MULT
	# Camera-relative movement
	var sin_y := sin(yaw)
	var cos_y := cos(yaw)
	var dir := Vector3(
		(ix * cos_y - iz * sin_y),
		0.0,
		(ix * -sin_y + iz * -cos_y) * -1.0)
	# NOTE: forward is -Z of yaw; compute cleanly:
	var fwd := Vector3(-sin_y, 0, -cos_y)
	var right := Vector3(cos_y, 0, -sin_y)
	dir = (right * ix - fwd * iz)
	if dir.length() > 1.0:
		dir = dir.normalized()
	velocity.x = dir.x * SPEED * sprint
	velocity.z = dir.z * SPEED * sprint
	move_and_slide()
	# Face movement direction
	var planar := Vector3(velocity.x, 0, velocity.z)
	if planar.length() > 0.5:
		var target := atan2(-planar.x, -planar.z)
		rig.rotation.y = lerp_angle(rig.rotation.y, target, 12.0 * delta)
		run_phase += delta * planar.length() * 2.2
	else:
		run_phase += delta * 2.0
	_animate(planar.length())
	# Camera
	cam_pivot.rotation = Vector3(pitch, yaw, 0)

func _animate(speed: float) -> void:
	var amp := clampf(speed / SPEED, 0.0, 1.6)
	var s := sin(run_phase * 1.0)
	leg_l.rotation.x = s * 0.9 * amp
	leg_r.rotation.x = -s * 0.9 * amp
	arm_l.rotation.x = -s * 0.8 * amp
	arm_r.rotation.x = s * 0.8 * amp
	var airborne := not is_on_floor()
	if airborne:
		leg_l.rotation.x = 0.45
		leg_r.rotation.x = -0.35
		arm_l.rotation.x = -0.9
		arm_r.rotation.x = 0.9
	elif amp < 0.05:
		var b := sin(run_phase) * 0.05
		leg_l.rotation.x = b
		leg_r.rotation.x = -b
		arm_l.rotation.x = b
		arm_r.rotation.x = -b
	# Bouncy torso
	rig.position.y = absf(cos(run_phase)) * 0.06 * amp

# --- voxel construction ---

func _box(size: Vector3, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	mi.material_override = mat
	return mi

func _build_voxel_body() -> void:
	# Torso (blue jacket)
	torso = _box(Vector3(0.6, 0.6, 0.35), Color("3f7de0"))
	torso.position = Vector3(0, 1.0, 0)
	rig.add_child(torso)
	# Belt stripe
	var belt := _box(Vector3(0.62, 0.12, 0.37), Color("2b2b38"))
	belt.position = Vector3(0, 0.74, 0)
	rig.add_child(belt)
	# Head (skin) + eyes + cap
	head = _box(Vector3(0.45, 0.42, 0.42), Color("f2c38f"))
	head.position = Vector3(0, 1.55, 0)
	rig.add_child(head)
	var eye_l := _box(Vector3(0.07, 0.09, 0.02), Color.BLACK)
	eye_l.position = Vector3(-0.11, 1.58, -0.22)
	rig.add_child(eye_l)
	var eye_r := _box(Vector3(0.07, 0.09, 0.02), Color.BLACK)
	eye_r.position = Vector3(0.11, 1.58, -0.22)
	rig.add_child(eye_r)
	var cap := _box(Vector3(0.5, 0.14, 0.47), Color("e04a3f"))
	cap.position = Vector3(0, 1.82, 0)
	rig.add_child(cap)
	var brim := _box(Vector3(0.5, 0.06, 0.25), Color("e04a3f"))
	brim.position = Vector3(0, 1.76, -0.33)
	rig.add_child(brim)
	# Arms with shoulder pivots
	arm_l = Node3D.new()
	arm_l.position = Vector3(-0.4, 1.25, 0)
	rig.add_child(arm_l)
	var a_l := _box(Vector3(0.2, 0.6, 0.2), Color("3f7de0"))
	a_l.position = Vector3(0, -0.28, 0)
	arm_l.add_child(a_l)
	var hand_l := _box(Vector3(0.2, 0.16, 0.2), Color("f2c38f"))
	hand_l.position = Vector3(0, -0.62, 0)
	arm_l.add_child(hand_l)
	arm_r = Node3D.new()
	arm_r.position = Vector3(0.4, 1.25, 0)
	rig.add_child(arm_r)
	var a_r := _box(Vector3(0.2, 0.6, 0.2), Color("3f7de0"))
	a_r.position = Vector3(0, -0.28, 0)
	arm_r.add_child(a_r)
	var hand_r := _box(Vector3(0.2, 0.16, 0.2), Color("f2c38f"))
	hand_r.position = Vector3(0, -0.62, 0)
	arm_r.add_child(hand_r)
	# Legs with hip pivots
	leg_l = Node3D.new()
	leg_l.position = Vector3(-0.16, 0.7, 0)
	rig.add_child(leg_l)
	var l_l := _box(Vector3(0.24, 0.55, 0.24), Color("33415c"))
	l_l.position = Vector3(0, -0.28, 0)
	leg_l.add_child(l_l)
	var shoe_l := _box(Vector3(0.26, 0.16, 0.34), Color("e8e8ec"))
	shoe_l.position = Vector3(0, -0.6, -0.04)
	leg_l.add_child(shoe_l)
	leg_r = Node3D.new()
	leg_r.position = Vector3(0.16, 0.7, 0)
	rig.add_child(leg_r)
	var l_r := _box(Vector3(0.24, 0.55, 0.24), Color("33415c"))
	l_r.position = Vector3(0, -0.28, 0)
	leg_r.add_child(l_r)
	var shoe_r := _box(Vector3(0.26, 0.16, 0.34), Color("e8e8ec"))
	shoe_r.position = Vector3(0, -0.6, -0.04)
	leg_r.add_child(shoe_r)
