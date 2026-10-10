extends CharacterBody3D
## Third-person voxel runner: procedural blocky rig, spring-arm orbit camera,
## coyote-time + jump-buffer jumping, squash & stretch, dust puffs, blip SFX.
## Single-threaded, GL-Compatibility friendly (no particles nodes, no threads).

const Sfx := preload("res://scripts/sfx.gd")

const WALK_SPEED: float = 6.0
const SPRINT_SPEED: float = 9.5
const ACCEL: float = 30.0
const FRICTION: float = 34.0
const JUMP_VELOCITY: float = 7.5
const GRAVITY: float = 22.0
const COYOTE_TIME: float = 0.12
const JUMP_BUFFER: float = 0.14
const MOUSE_SENS: float = 0.0035
const DUST_COLOR := Color(0.85, 0.78, 0.62)

var yaw: float = 0.0
var pitch: float = -0.32
var cam_dist: float = 6.0
var run_phase: float = 0.0
var coyote: float = 0.0
var jump_buffer: float = 0.0
var was_on_floor: bool = false
var squash: float = 0.0 # >0 squashed, <0 stretched
var move_axis := Vector2.ZERO # touch joystick input
var touch_sprint: bool = false
var puff_timer: float = 0.0

var rig: Node3D
var cam_pivot: Node3D
var spring: SpringArm3D
var arm_l: Node3D
var arm_r: Node3D
var leg_l: Node3D
var leg_r: Node3D
var mats: Dictionary = {}
var puffs: Array = []
var fx_root: Node3D
var puff_mesh: BoxMesh
var jump_player: AudioStreamPlayer
var land_player: AudioStreamPlayer


func _ready() -> void:
	add_to_group("player")
	floor_snap_length = 0.4
	rig = $Rig
	cam_pivot = $CameraPivot
	spring = $CameraPivot/SpringArm3D
	fx_root = get_parent().get_node("FX")
	puff_mesh = BoxMesh.new()
	puff_mesh.size = Vector3.ONE
	_build_rig()
	jump_player = AudioStreamPlayer.new()
	jump_player.stream = Sfx.tone(320.0, 720.0, 0.18, 0.45)
	jump_player.volume_db = -6.0
	add_child(jump_player)
	land_player = AudioStreamPlayer.new()
	land_player.stream = Sfx.tone(200.0, 90.0, 0.12, 0.4)
	land_player.volume_db = -8.0
	add_child(land_player)


func get_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()


func touch_jump() -> void:
	jump_buffer = JUMP_BUFFER


func celebrate_burst() -> void:
	var colors: Array = [
		Color(1.0, 0.4, 0.4), Color(1.0, 0.85, 0.3), Color(0.4, 1.0, 0.5),
		Color(0.4, 0.8, 1.0), Color(0.85, 0.5, 1.0),
	]
	for c in colors:
		_spawn_puffs(global_position + Vector3(0, 1.2, 0), c, 10, 4.0, 5.0, 0.16, 0.9)


func _mat(color: Color) -> StandardMaterial3D:
	var key := color.to_html()
	if mats.has(key):
		return mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.9
	mats[key] = m
	return m


func _box(parent_node: Node3D, size: Vector3, pos: Vector3, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(color)
	mi.mesh = bm
	mi.position = pos
	parent_node.add_child(mi)
	return mi


func _build_rig() -> void:
	var skin := Color(0.96, 0.77, 0.60)
	var hair := Color(0.36, 0.23, 0.13)
	var hoodie := Color(0.18, 0.77, 0.71)
	var denim := Color(0.27, 0.32, 0.58)
	var shoe_c := Color(0.90, 0.36, 0.22)
	var pack := Color(0.62, 0.36, 0.78)
	var eye := Color(0.08, 0.08, 0.10)
	# Torso + backpack.
	_box(rig, Vector3(0.55, 0.6, 0.32), Vector3(0, 1.05, 0), hoodie)
	_box(rig, Vector3(0.32, 0.42, 0.16), Vector3(0, 1.05, -0.24), pack)
	# Head: skin cube, eyes, hair, sporty headband.
	_box(rig, Vector3(0.45, 0.45, 0.45), Vector3(0, 1.62, 0), skin)
	_box(rig, Vector3(0.07, 0.10, 0.03), Vector3(-0.10, 1.65, 0.226), eye)
	_box(rig, Vector3(0.07, 0.10, 0.03), Vector3(0.10, 1.65, 0.226), eye)
	_box(rig, Vector3(0.47, 0.14, 0.47), Vector3(0, 1.90, 0), hair)
	_box(rig, Vector3(0.47, 0.09, 0.47), Vector3(0, 1.79, 0), Color(0.90, 0.30, 0.25))
	# Arms on shoulder pivots.
	arm_l = Node3D.new()
	arm_l.position = Vector3(-0.37, 1.28, 0)
	rig.add_child(arm_l)
	arm_r = Node3D.new()
	arm_r.position = Vector3(0.37, 1.28, 0)
	rig.add_child(arm_r)
	_box(arm_l, Vector3(0.18, 0.55, 0.20), Vector3(0, -0.27, 0), hoodie)
	_box(arm_l, Vector3(0.17, 0.16, 0.19), Vector3(0, -0.60, 0), skin)
	_box(arm_r, Vector3(0.18, 0.55, 0.20), Vector3(0, -0.27, 0), hoodie)
	_box(arm_r, Vector3(0.17, 0.16, 0.19), Vector3(0, -0.60, 0), skin)
	# Legs on hip pivots, chunky shoes.
	leg_l = Node3D.new()
	leg_l.position = Vector3(-0.15, 0.75, 0)
	rig.add_child(leg_l)
	leg_r = Node3D.new()
	leg_r.position = Vector3(0.15, 0.75, 0)
	rig.add_child(leg_r)
	_box(leg_l, Vector3(0.22, 0.62, 0.24), Vector3(0, -0.31, 0), denim)
	_box(leg_l, Vector3(0.22, 0.15, 0.32), Vector3(0, -0.675, 0.04), shoe_c)
	_box(leg_r, Vector3(0.22, 0.62, 0.24), Vector3(0, -0.31, 0), denim)
	_box(leg_r, Vector3(0.22, 0.15, 0.32), Vector3(0, -0.675, 0.04), shoe_c)
	rig.rotation.y = PI


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED or mm.button_mask != 0:
			yaw -= mm.relative.x * MOUSE_SENS
			pitch = clampf(pitch - mm.relative.y * MOUSE_SENS, -1.15, 0.6)
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed:
			match mb.button_index:
				MOUSE_BUTTON_WHEEL_UP:
					cam_dist = clampf(cam_dist - 0.6, 3.0, 10.0)
				MOUSE_BUTTON_WHEEL_DOWN:
					cam_dist = clampf(cam_dist + 0.6, 3.0, 10.0)
				MOUSE_BUTTON_LEFT:
					if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
						Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		var w := get_viewport().get_visible_rect().size.x
		if drag.position.x > w * 0.4:
			yaw -= drag.relative.x * 0.006
			pitch = clampf(pitch - drag.relative.y * 0.006, -1.15, 0.6)


func _physics_process(delta: float) -> void:
	var grounded := is_on_floor()
	if grounded:
		coyote = COYOTE_TIME
	else:
		coyote -= delta
		velocity.y -= GRAVITY * delta
	jump_buffer -= delta
	if Input.is_action_just_pressed("jump"):
		jump_buffer = JUMP_BUFFER
	var ix := Input.get_axis("move_left", "move_right") + move_axis.x
	var iz := Input.get_axis("move_forward", "move_back") + move_axis.y
	ix = clampf(ix, -1.0, 1.0)
	iz = clampf(iz, -1.0, 1.0)
	var fwd := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var right := Vector3(-fwd.z, 0.0, fwd.x)
	var wish := right * ix + fwd * (-iz)
	var sprinting := Input.is_action_pressed("sprint") or touch_sprint
	var speed := SPRINT_SPEED if (sprinting and wish.length() > 0.1) else WALK_SPEED
	var hv := Vector3(velocity.x, 0.0, velocity.z)
	if wish.length() > 0.1:
		hv = hv.move_toward(wish.normalized() * speed, ACCEL * delta)
	else:
		hv = hv.move_toward(Vector3.ZERO, FRICTION * delta)
	velocity.x = hv.x
	velocity.z = hv.z
	if jump_buffer > 0.0 and (grounded or coyote > 0.0):
		velocity.y = JUMP_VELOCITY
		jump_buffer = 0.0
		coyote = 0.0
		squash = -0.7
		jump_player.play()
		_spawn_puffs(global_position + Vector3(0, 0.1, 0), DUST_COLOR, 6, 2.0, 1.5, 0.16, 0.45)
	var prev_vy := velocity.y
	var was := was_on_floor
	move_and_slide()
	var now := is_on_floor()
	if now and not was:
		_on_landed(prev_vy)
	was_on_floor = now
	if now and hv.length() > SPRINT_SPEED * 0.85:
		puff_timer -= delta
		if puff_timer <= 0.0:
			puff_timer = 0.16
			_spawn_puffs(global_position + Vector3(0, 0.08, 0), DUST_COLOR, 2, 1.2, 1.0, 0.13, 0.4)


func _on_landed(fall_speed: float) -> void:
	var hard := fall_speed < -9.0
	squash = 1.0
	land_player.play()
	_spawn_puffs(global_position, DUST_COLOR, 14 if hard else 6, 3.0, 2.0, 0.15, 0.5)


func _process(delta: float) -> void:
	# Keyboard camera (Q/E) as a no-mouse fallback.
	if Input.is_physical_key_pressed(KEY_Q):
		yaw += 1.9 * delta
	if Input.is_physical_key_pressed(KEY_E):
		yaw -= 1.9 * delta
	cam_pivot.rotation.y = yaw
	spring.rotation.x = pitch
	spring.spring_length = cam_dist
	_animate(delta)
	_update_puffs(delta)


func _animate(delta: float) -> void:
	var hspeed := Vector2(velocity.x, velocity.z).length()
	var grounded := is_on_floor()
	var intensity := clampf(hspeed / SPRINT_SPEED, 0.0, 1.0)
	if grounded and hspeed > 0.5:
		run_phase += delta * (4.0 + hspeed * 1.35)
	elif grounded:
		run_phase += delta * 2.0 # idle breathing
	var s := sin(run_phase)
	if grounded:
		var swing := lerpf(0.08, 0.95, intensity)
		if hspeed < 0.5:
			swing = 0.06
		leg_l.rotation.x = s * swing
		leg_r.rotation.x = -s * swing
		arm_l.rotation.x = -s * swing * 0.9
		arm_r.rotation.x = s * swing * 0.9
	else:
		var air := clampf(-velocity.y * 0.06, -0.5, 0.6)
		leg_l.rotation.x = lerpf(leg_l.rotation.x, 0.45, 10.0 * delta)
		leg_r.rotation.x = lerpf(leg_r.rotation.x, -0.3, 10.0 * delta)
		arm_l.rotation.x = lerpf(arm_l.rotation.x, -0.7 + air, 8.0 * delta)
		arm_r.rotation.x = lerpf(arm_r.rotation.x, -0.7 + air, 8.0 * delta)
	var lean := 0.0
	if grounded:
		lean = clampf(hspeed * 0.028, 0.0, 0.28)
	else:
		lean = clampf(-velocity.y * 0.02, -0.2, 0.3)
	rig.rotation.x = lerpf(rig.rotation.x, lean, 8.0 * delta)
	var bob := 0.0
	if grounded:
		bob = abs(cos(run_phase)) * 0.07 * intensity
	rig.position.y = bob
	squash = move_toward(squash, 0.0, delta * 5.0)
	var sx := 1.0 + squash * 0.22
	var sy := 1.0 - squash * 0.28
	rig.scale = Vector3(sx, sy, sx)
	if hspeed > 0.6:
		var want := atan2(velocity.x, velocity.z)
		rig.rotation.y = lerp_angle(rig.rotation.y, want, 1.0 - exp(-12.0 * delta))


func _spawn_puffs(pos: Vector3, color: Color, count: int, speed: float, up: float, size: float, life: float) -> void:
	if fx_root == null:
		return
	for i in range(count):
		var mi := MeshInstance3D.new()
		mi.mesh = puff_mesh
		mi.material_override = _mat(color)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		fx_root.add_child(mi)
		mi.global_position = pos + Vector3(randf_range(-0.2, 0.2), randf_range(0.0, 0.3), randf_range(-0.2, 0.2))
		var a := randf() * TAU
		var v := Vector3(cos(a) * speed * randf_range(0.4, 1.0), randf_range(up * 0.5, up), sin(a) * speed * randf_range(0.4, 1.0))
		puffs.append({"n": mi, "v": v, "life": life * randf_range(0.7, 1.2), "max": life, "s": size * randf_range(0.7, 1.3)})


func _update_puffs(delta: float) -> void:
	for i in range(puffs.size() - 1, -1, -1):
		var p: Dictionary = puffs[i]
		var life: float = float(p["life"]) - delta
		var n: MeshInstance3D = p["n"]
		if life <= 0.0 or not is_instance_valid(n):
			if is_instance_valid(n):
				n.queue_free()
			puffs.remove_at(i)
			continue
		var v: Vector3 = p["v"]
		v.y -= 7.0 * delta
		p["v"] = v
		n.global_position += v * delta
		var k: float = life / float(p["max"])
		var sc: float = float(p["s"]) * k
		n.scale = Vector3(sc, sc, sc)
		p["life"] = life
