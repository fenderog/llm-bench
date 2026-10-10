class_name SandboxPlayer
extends CharacterBody3D
## Third-person runner controller. Reads keys directly (no custom InputMap
## needed): WASD/arrows to run, SHIFT to sprint, SPACE to jump.

@export var walk_speed := 5.5
@export var run_speed := 9.0
@export var accel := 26.0
@export var air_control := 8.0
@export var jump_velocity := 7.5
@export var gravity := 24.0
@export var turn_speed := 14.0
@export var arena_half := 11.8

const SPAWN := Vector3(0, 0.4, 6.0)

var facing := PI
var coyote := 0.0
var jump_buffer := 0.0
var jump_held := false
var was_on_floor := true

@onready var rig := $Rig as VoxelCharacter
@onready var dust := $Dust as CPUParticles3D


func _ready() -> void:
	add_to_group("player")
	position = SPAWN
	facing = PI
	rig.rotation.y = facing
	_setup_dust()


func _setup_dust() -> void:
	dust.amount = 28
	dust.lifetime = 0.55
	dust.local_coords = false
	dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	dust.emission_sphere_radius = 0.25
	dust.direction = Vector3(0, 1, 0)
	dust.spread = 35.0
	dust.gravity = Vector3(0, -3, 0)
	dust.initial_velocity_min = 1.0
	dust.initial_velocity_max = 2.5
	dust.scale_amount_min = 0.08
	dust.scale_amount_max = 0.16
	dust.color = Color(0.9, 0.85, 0.75, 1)
	var bm := BoxMesh.new()
	bm.size = Vector3(0.12, 0.12, 0.12)
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.85, 0.8, 0.7, 1)
	m.roughness = 1.0
	bm.material = m
	dust.mesh = bm
	dust.emitting = false


func _physics_process(delta: float) -> void:
	var ix := 0.0
	var iz := 0.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		ix -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		ix += 1.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		iz -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		iz += 1.0
	var wish := Vector2(ix, iz)
	if wish.length() > 1.0:
		wish = wish.normalized()

	var yaw := facing
	var cam := get_tree().get_first_node_in_group("camera_rig") as CameraRig
	if cam != null:
		yaw = cam.yaw
	var dir := Vector3.ZERO
	if wish != Vector2.ZERO:
		dir = (Basis(Vector3.UP, yaw) * Vector3(wish.x, 0.0, wish.y)).normalized()

	var sprint := Input.is_physical_key_pressed(KEY_SHIFT)
	var target_speed := 0.0
	if dir != Vector3.ZERO:
		target_speed = run_speed if sprint else walk_speed
	var target := dir * target_speed
	var h := Vector3(velocity.x, 0.0, velocity.z)
	var rate := accel if is_on_floor() else air_control
	h = h.move_toward(target, rate * delta)
	velocity.x = h.x
	velocity.z = h.z

	if is_on_floor():
		coyote = 0.12
		if velocity.y < 0.0:
			velocity.y = -0.5
	else:
		coyote -= delta
		velocity.y -= gravity * delta

	var jump_down := Input.is_physical_key_pressed(KEY_SPACE)
	var jump_pressed := jump_down and not jump_held
	jump_held = jump_down
	if jump_pressed:
		jump_buffer = 0.12
	else:
		jump_buffer -= delta
	if jump_buffer > 0.0 and coyote > 0.0:
		velocity.y = jump_velocity
		jump_buffer = 0.0
		coyote = 0.0

	move_and_slide()

	# Safety: stay inside the fenced sandbox, recover from falls.
	position.x = clampf(position.x, -arena_half, arena_half)
	position.z = clampf(position.z, -arena_half, arena_half)
	if position.y < -8.0:
		position = SPAWN
		velocity = Vector3.ZERO

	var hspeed := Vector2(velocity.x, velocity.z).length()
	if hspeed > 0.6:
		facing = lerp_angle(facing, atan2(velocity.x, velocity.z), 1.0 - exp(-turn_speed * delta))
		rig.rotation.y = facing

	rig.animate(delta, clampf(hspeed / run_speed, 0.0, 1.0), is_on_floor())

	var running := is_on_floor() and hspeed > 3.5
	if running and not dust.emitting:
		dust.emitting = true
	elif not running and dust.emitting:
		dust.emitting = false

	if not was_on_floor and is_on_floor():
		rig.land()
	was_on_floor = is_on_floor()
