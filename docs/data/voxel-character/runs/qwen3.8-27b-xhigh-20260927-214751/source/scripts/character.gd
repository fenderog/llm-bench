extends CharacterBody3D
## "Vex" - a little voxel character built entirely from boxes.
## Wanders on AI by default; hands over to the player when a movement key is pressed.

const SPEED := 6.5
const SPRINT_MULT := 1.55
const ACCEL := 40.0
const AIR_ACCEL := 22.0
const GRAVITY := 24.0
const JUMP_SPEED := 9.5
const ARENA := 13.0
const WANDER_RADIUS := 9.5
const SPAWN := Vector3(0.0, 0.0, 6.5)

# (0, 0, 0) is a sentinel meaning "orbit the central pillar".
const ORBIT_TARGET := Vector3.ZERO

const PALETTE := [
	{"hat": 0xd9482f, "shirt": 0x3f7f5f, "pants": 0x41528f, "shoe": 0x743326},
	{"hat": 0x4a90d9, "shirt": 0xc9a227, "pants": 0x6b4f9e, "shoe": 0x33383f},
]

var ai_mode := true
var palette_index := 0
var wander_target := Vector3.ZERO
var wander_timer := 0.0
var vel_h := Vector2.ZERO
var anim_t := 0.0
var spin := 0.0
var jump_queued := false

# Body parts.
var root: Node3D
var torso: MeshInstance3D
var head: MeshInstance3D
var hat: MeshInstance3D
var hat_crown: MeshInstance3D
var eye_l: MeshInstance3D
var eye_r: MeshInstance3D
var arm_l: Node3D
var arm_r: Node3D
var leg_l: Node3D
var leg_r: Node3D


func _ready() -> void:
	_build_body()
	wander_timer = 6.0


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("jump"):
		jump_queued = true
	elif event.is_action_pressed("reset"):
		position = SPAWN
		velocity = Vector3.ZERO
		spin = 0.0
		root.rotation = Vector3.ZERO


func _physics_process(delta: float) -> void:
	# --- Who drives: AI, or the player once they touch a control.
	var player_active := Input.is_action_pressed("move_left") \
		or Input.is_action_pressed("move_right") \
		or Input.is_action_pressed("move_forward") \
		or Input.is_action_pressed("move_back") \
		or jump_queued
	if player_active and ai_mode:
		ai_mode = false

	# --- Input direction.
	var input_dir := Vector3.ZERO
	if player_active:
		var raw := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		input_dir = Vector3(raw.x, 0.0, raw.y)
		if input_dir.length() > 1.0:
			input_dir = input_dir.normalized()
	else:
		input_dir = _ai_dir()

	# --- Horizontal movement.
	var on_floor := is_on_floor()
	var target_speed := SPEED * (SPRINT_MULT if Input.is_key_pressed(KEY_SHIFT) else 1.0)
	var accel := ACCEL if on_floor else AIR_ACCEL
	vel_h = vel_h.move_toward(Vector2(input_dir.x, input_dir.z) * target_speed, accel * delta)
	velocity.x = vel_h.x
	velocity.z = vel_h.y

	# --- Gravity + jump.
	if on_floor and jump_queued:
		velocity.y = JUMP_SPEED
	velocity.y -= GRAVITY * delta
	jump_queued = false
	move_and_slide()

	# Keep the character inside the arena at all times.
	position.x = clampf(position.x, -ARENA, ARENA)
	position.z = clampf(position.z, -ARENA, ARENA)

	# --- Procedural animation.
	_update_animation(delta, input_dir, on_floor)

	# --- Lean/tilt while running: readable even without contact shadows.
	var speed := vel_h.length()
	var target_roll := 0.0
	var target_pitch := 0.0
	if speed > 0.4:
		target_roll = clampf(-speed * 0.02, -0.1, 0.1)
		target_pitch = clampf(speed * 0.012, 0.0, 0.09)
	spin = lerp_angle(spin, target_roll, 1.0 - exp(-8.0 * delta))
	root.rotation.z = spin
	root.rotation.x = lerp(root.rotation.x, target_pitch, 1.0 - exp(-8.0 * delta))

	# --- AI flair: cycle colors every few seconds while wandering.
	if ai_mode:
		wander_timer -= delta
		if wander_timer <= 0.0:
			palette_index = (palette_index + 1) % PALETTE.size()
			_apply_palette()
			wander_timer = 7.0


func _ai_dir() -> Vector3:
	if wander_target == ORBIT_TARGET:
		# Orbit the central pillar.
		var p := Vector3(position.x, 0.0, position.z)
		var dist_c := p.length()
		if dist_c < 0.05:
			wander_target = _pick_wander_point()
			return Vector3.ZERO
		var to_center := -p / dist_c
		var tangent := Vector3(p.z, 0.0, -p.x) / dist_c
		var dir := (tangent * 0.85 + to_center * 0.2).normalized()
		if dist_c > 4.5:
			dir = to_center  # steer back toward the pillar
		return dir * 0.85

	# Walk to the current wander point.
	var to_t := wander_target - position
	to_t.y = 0.0
	var dist_t := to_t.length()
	if dist_t < 0.9:
		wander_target = _pick_wander_point()
		return Vector3.ZERO
	var ease := 0.55 + 0.45 * minf(dist_t / 4.0, 1.0)
	return (to_t / dist_t) * ease


func _pick_wander_point() -> Vector3:
	var ang := randf() * TAU
	var r := randf_range(2.5, WANDER_RADIUS)
	var p := Vector3(cos(ang) * r, 0.0, sin(ang) * r)
	p.x = clampf(p.x, -ARENA + 1.0, ARENA - 1.0)
	p.z = clampf(p.z, -ARENA + 1.0, ARENA - 1.0)
	# Nudge away from obvious prop spots (trees, crates, pillar).
	var blocked := [Vector3(-8.5, 0, -8.5), Vector3(9.0, 0, -7.5), Vector3(-9.5, 0, 8.0),
		Vector3(8.0, 0, 8.0), Vector3(-7.5, 0, 2.0), Vector3(3.5, 0, 6.5),
		Vector3(-3.0, 0, -6.0), Vector3(0, 0, 0)]
	for b in blocked:
		if p.distance_to(b) < 2.5:
			ang += PI * 0.7
			r = randf_range(3.5, WANDER_RADIUS)
			p = Vector3(clampf(cos(ang) * r, -ARENA + 1.0, ARENA - 1.0), 0.0,
				clampf(sin(ang) * r, -ARENA + 1.0, ARENA - 1.0))
	return p


func _update_animation(delta: float, input_dir: Vector3, on_floor: bool) -> void:
	var speed := vel_h.length()
	if on_floor:
		if speed > 0.6:
			# Run cycle: swinging limbs + bouncy torso, facing travel direction.
			var dir_now := input_dir if input_dir.length() > 0.1 \
				else Vector3(vel_h.x, 0.0, vel_h.y).normalized()
			root.rotation.y = lerp_angle(root.rotation.y, atan2(dir_now.x, dir_now.z),
				1.0 - exp(-10.0 * delta))
			var f := speed * 1.55
			anim_t += delta * f
			var s := sin(anim_t)
			var swing := clampf(speed / SPEED, 0.35, 1.4) * 0.95
			arm_l.rotation.x = -s * swing
			arm_r.rotation.x = s * swing
			leg_l.rotation.x = s * swing
			leg_r.rotation.x = -s * swing
			torso.position.y = 1.68 + absf(sin(anim_t)) * 0.07
			torso.rotation.x = 0.12
			head.rotation.x = -0.05
		else:
			# Idle: settle limbs, gentle breathing bob.
			anim_t += delta * 2.0
			arm_l.rotation.x = lerp(arm_l.rotation.x, 0.05, 0.15)
			arm_r.rotation.x = lerp(arm_r.rotation.x, -0.05, 0.15)
			leg_l.rotation.x = lerp(leg_l.rotation.x, 0.0, 0.2)
			leg_r.rotation.x = lerp(leg_r.rotation.x, 0.0, 0.2)
			torso.position.y = 1.68 + sin(anim_t) * 0.02
			torso.rotation.x = lerp(torso.rotation.x, 0.0, 0.15)
			head.rotation.x = lerp(head.rotation.x, 0.0, 0.15)
	else:
		# Airborne: tuck legs, raise arms.
		leg_l.rotation.x = lerp(leg_l.rotation.x, -0.6, 0.25)
		leg_r.rotation.x = lerp(leg_r.rotation.x, 0.45, 0.25)
		arm_l.rotation.x = lerp(arm_l.rotation.x, -2.6, 0.2)
		arm_r.rotation.x = lerp(arm_r.rotation.x, 2.6, 0.2)
		torso.rotation.x = lerp(torso.rotation.x, 0.0, 0.2)


func _build_body() -> void:
	collision_layer = 1
	collision_mask = 1
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.45
	cap.height = 3.4  # covers feet (y=0) to the top of the head
	col.shape = cap
	col.position = Vector3(0, 1.7, 0)
	add_child(col)

	root = Node3D.new()
	root.name = "Rig"
	add_child(root)

	var skin := _mat(0xfad5a3)
	var hat_m := _mat(0xd9482f)
	var shirt := _mat(0x3f7f5f)
	var pants := _mat(0x41528f)
	var shoe := _mat(0x743326)
	var eye_m := _mat(0x22242a)
	var nose_m := _mat(0xe88b5a)

	torso = _box(1.1, 0.9, 0.65, shirt, Vector3(0, 1.68, 0), root)
	_box(1.12, 0.18, 0.67, _mat(0x4a3222), Vector3(0, 1.27, 0), root)  # belt
	head = _box(1.0, 1.0, 1.0, skin, Vector3(0, 2.6, 0), root)
	hat = _box(1.12, 0.3, 1.12, hat_m, Vector3(0, 3.18, 0), root)
	hat_crown = _box(0.7, 0.22, 0.7, hat_m.duplicate(), Vector3(0, 3.37, 0), root)
	_box(0.16, 0.16, 0.16, nose_m, Vector3(0, 2.55, 0.52), root)
	eye_l = _box(0.14, 0.2, 0.1, eye_m, Vector3(-0.24, 2.68, 0.52), root)
	eye_r = _box(0.14, 0.2, 0.1, eye_m, Vector3(0.24, 2.68, 0.52), root)

	# Limbs are pivoted at the shoulder/hip so they swing naturally.
	arm_l = _limb(0.3, 0.85, 0.3, Vector3(-0.72, 2.05, 0.0), root, skin, pants)
	arm_r = _limb(0.3, 0.85, 0.3, Vector3(0.72, 2.05, 0.0), root, skin, pants)
	leg_l = _limb(0.38, 0.85, 0.38, Vector3(-0.3, 1.05, 0.0), root, pants, shoe)
	leg_r = _limb(0.38, 0.85, 0.38, Vector3(0.3, 1.05, 0.0), root, pants, shoe)


func _limb(w: float, h: float, d: float, pos: Vector3, parent: Node, mat: Material, end_mat: Material) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = pos
	parent.add_child(pivot)
	_box(w, h, d, mat, Vector3(0, -h * 0.5, 0), pivot)
	# Hands / feet at the end of the limb.
	_box(w * 1.05, h * 0.22, d * 1.15, end_mat, Vector3(0, -h * 0.86, 0), pivot)
	return pivot


func _box(w: float, h: float, d: float, mat: Material, pos: Vector3, parent: Node) -> MeshInstance3D:
	var b := BoxMesh.new()
	b.size = Vector3(w, h, d)
	var s := MeshInstance3D.new()
	s.mesh = b
	s.material_override = mat
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	s.position = pos
	parent.add_child(s)
	return s


func _mat(hex: int) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color8(hex >> 16 & 255, hex >> 8 & 255, hex & 255)
	m.roughness = 0.85
	return m


func _apply_palette() -> void:
	var p = PALETTE[palette_index]
	torso.material_override.albedo_color = Color8(p.shirt >> 16 & 255, p.shirt >> 8 & 255, p.shirt & 255)
	hat.material_override.albedo_color = Color8(p.hat >> 16 & 255, p.hat >> 8 & 255, p.hat & 255)
	hat_crown.material_override.albedo_color = hat.material_override.albedo_color
	for leg in [leg_l, leg_r]:
		leg.get_child(0).material_override.albedo_color = Color8(
			p.pants >> 16 & 255, p.pants >> 8 & 255, p.pants & 255)
