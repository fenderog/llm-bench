extends CharacterBody3D
## Cute voxel character: WASD runs around, Space jumps, Shift sprints.
## Limbs swing procedurally for a lively run cycle.

@export var walk_speed := 4.5
@export var run_speed := 7.5
@export var accel := 14.0
@export var jump_velocity := 7.5
@export var turn_speed := 12.0

var _spawn := Vector3(0, 1.2, 6)
var _run_phase := 0.0
var _sprinting := false
var _h_speed := 0.0

var _rig: Node3D
var _torso: MeshInstance3D
var _head: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _dust: CPUParticles3D


func _ready() -> void:
	add_to_group("player")
	_rig = $Rig
	_dust = $Dust
	_build_body()


func reset_to_spawn() -> void:
	global_position = _spawn
	velocity = Vector3.ZERO
	_rig.rotation.y = PI


func get_horizontal_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()


func is_sprinting_now() -> bool:
	return _sprinting and get_horizontal_speed() > walk_speed + 0.5


func _physics_process(delta: float) -> void:
	# --- Input (keys read directly so no InputMap setup is needed).
	var iv := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		iv.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		iv.y += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		iv.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		iv.x += 1.0
	if iv.length() > 1.0:
		iv = iv.normalized()
	_sprinting = Input.is_physical_key_pressed(KEY_SHIFT)

	# Camera-relative move direction.
	var yaw := _camera_yaw()
	var dir := Vector3(iv.x, 0, iv.y).rotated(Vector3.UP, yaw)
	var target_speed := run_speed if _sprinting else walk_speed
	var target_vel := dir * target_speed if dir.length() > 0.1 else Vector3.ZERO

	velocity.x = move_toward(velocity.x, target_vel.x, accel * delta)
	velocity.z = move_toward(velocity.z, target_vel.z, accel * delta)

	if not is_on_floor():
		velocity.y -= ProjectSettings.get_setting("physics/3d/default_gravity", 20.0) * delta
	elif Input.is_action_just_pressed("ui_accept") or Input.is_physical_key_pressed(KEY_SPACE):
		# Edge-trigger jump: require fresh press via echo guard.
		if _jump_pressed():
			velocity.y = jump_velocity

	move_and_slide()

	# Face movement direction.
	_h_speed = Vector2(velocity.x, velocity.z).length()
	var flat := Vector3(velocity.x, 0, velocity.z)
	if flat.length() > 0.5:
		var want := atan2(flat.x, flat.z)
		_rig.rotation.y = lerp_angle(_rig.rotation.y, want, minf(1.0, turn_speed * delta))

	_animate(delta)
	_dust.emitting = is_on_floor() and _h_speed > 3.0


func _jump_pressed() -> bool:
	# Debounce holding space: only jump shortly after key state flips.
	# Input.is_physical_key_pressed has no edge API, so track it here.
	if not Input.is_physical_key_pressed(KEY_SPACE) and not Input.is_action_pressed("ui_accept"):
		_space_was_down = false
		return Input.is_action_just_pressed("ui_accept")
	if _space_was_down:
		return false
	_space_was_down = true
	return true


var _space_was_down := false


func _camera_yaw() -> float:
	var rig := get_parent().get_node_or_null("CameraRig")
	if rig != null and "yaw" in rig:
		return rig.yaw
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return 0.0
	var fwd := -cam.global_transform.basis.z
	return atan2(fwd.x, fwd.z)


# ------------------------------------------------------------------ animation

func _animate(delta: float) -> void:
	_run_phase += delta * (4.0 + _h_speed * 1.9)
	var amp := clampf(_h_speed / run_speed, 0.0, 1.0) * 0.85
	var swing := sin(_run_phase) * amp
	if is_on_floor():
		_leg_l.rotation.x = swing
		_leg_r.rotation.x = -swing
		_arm_l.rotation.x = -swing * 0.9
		_arm_r.rotation.x = swing * 0.9
		_arm_l.rotation.z = 0.12
		_arm_r.rotation.z = -0.12
		_rig.position.y = absf(sin(_run_phase)) * 0.07 * amp
		_rig.rotation.x = amp * 0.12
		_head.rotation.x = -amp * 0.08
	else:
		# Airborne: legs split, arms up.
		_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.45, delta * 8.0)
		_leg_r.rotation.x = lerpf(_leg_r.rotation.x, -0.35, delta * 8.0)
		_arm_l.rotation.x = lerpf(_arm_l.rotation.x, -0.9, delta * 8.0)
		_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -0.9, delta * 8.0)
		_arm_l.rotation.z = 0.5
		_arm_r.rotation.z = -0.5
		_rig.rotation.x = -0.06


# ------------------------------------------------------------------ voxel body

func _part(parent: Node, size: Vector3, offset: Vector3, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.85
	m.specular_mode = StandardMaterial3D.SPECULAR_DISABLED
	bm.material = m
	mi.mesh = bm
	mi.position = offset
	parent.add_child(mi)
	return mi


func _build_body() -> void:
	var skin := Color(1.0, 0.85, 0.66)
	var shirt := Color(0.24, 0.43, 0.96)
	var pants := Color(0.17, 0.23, 0.33)
	var hair := Color(0.36, 0.22, 0.13)
	var shoe := Color(0.85, 0.3, 0.25)
	var dark := Color(0.13, 0.14, 0.2)

	# Torso + belt.
	_torso = _part(_rig, Vector3(0.52, 0.6, 0.32), Vector3(0, 0.35, 0), shirt)
	_part(_rig, Vector3(0.54, 0.1, 0.34), Vector3(0, 0.08, 0), dark)

	# Head group (bobs slightly when sprinting).
	_head = Node3D.new()
	_head.position = Vector3(0, 0.65, 0)
	_rig.add_child(_head)
	_part(_head, Vector3(0.46, 0.42, 0.42), Vector3(0, 0.24, 0), skin)
	_part(_head, Vector3(0.5, 0.16, 0.46), Vector3(0, 0.44, 0), hair) # hair cap
	_part(_head, Vector3(0.5, 0.1, 0.46), Vector3(0, 0.36, -0.01), hair) # back hair
	_part(_head, Vector3(0.09, 0.11, 0.03), Vector3(-0.11, 0.24, 0.22), dark) # eyes
	_part(_head, Vector3(0.09, 0.11, 0.03), Vector3(0.11, 0.24, 0.22), dark)
	_part(_head, Vector3(0.12, 0.05, 0.03), Vector3(0, 0.1, 0.22), Color(0.7, 0.4, 0.35)) # smile

	# Arms hang from shoulder pivots.
	_arm_l = Node3D.new()
	_arm_l.position = Vector3(-0.35, 0.6, 0)
	_rig.add_child(_arm_l)
	_part(_arm_l, Vector3(0.17, 0.24, 0.2), Vector3(0, -0.1, 0), shirt) # sleeve
	_part(_arm_l, Vector3(0.15, 0.34, 0.17), Vector3(0, -0.38, 0), skin)

	_arm_r = Node3D.new()
	_arm_r.position = Vector3(0.35, 0.6, 0)
	_rig.add_child(_arm_r)
	_part(_arm_r, Vector3(0.17, 0.24, 0.2), Vector3(0, -0.1, 0), shirt)
	_part(_arm_r, Vector3(0.15, 0.34, 0.17), Vector3(0, -0.38, 0), skin)

	# Legs hang from hip pivots.
	_leg_l = Node3D.new()
	_leg_l.position = Vector3(-0.14, 0.05, 0)
	_rig.add_child(_leg_l)
	_part(_leg_l, Vector3(0.2, 0.4, 0.22), Vector3(0, -0.22, 0), pants)
	_part(_leg_l, Vector3(0.21, 0.14, 0.3), Vector3(0, -0.46, 0.03), shoe)

	_leg_r = Node3D.new()
	_leg_r.position = Vector3(0.14, 0.05, 0)
	_rig.add_child(_leg_r)
	_part(_leg_r, Vector3(0.2, 0.4, 0.22), Vector3(0, -0.22, 0), pants)
	_part(_leg_r, Vector3(0.21, 0.14, 0.3), Vector3(0, -0.46, 0.03), shoe)

	# Scarf that flutters behind while sprinting is static here, still cute.
	_part(_rig, Vector3(0.3, 0.1, 0.08), Vector3(0, 0.62, -0.2), shoe)
