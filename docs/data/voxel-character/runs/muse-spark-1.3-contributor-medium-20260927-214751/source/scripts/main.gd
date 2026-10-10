extends Node3D
## Game root: builds environment, sandbox, player, follow camera and HUD.
## Single-threaded, GL Compatibility friendly — no threads, no external assets.

const PlayerScript := preload("res://scripts/player.gd")
const SandboxScript := preload("res://scripts/sandbox.gd")
const HudScript := preload("res://scripts/hud.gd")

var player: CharacterBody3D
var sandbox: Node3D
var hud: CanvasLayer

var cam_yaw: Node3D
var cam_pitch: Node3D
var spring: SpringArm3D
var camera: Camera3D

var coins_total := 0
var coins_got := 0
var spawn_pos := Vector3(0, 0.5, 5)

var _yaw := 0.0
var _pitch := -0.32
var _dist := 6.5
var _reset_cooldown := 0.0


func _ready() -> void:
	add_to_group("game")
	_build_environment()
	_build_sandbox()
	_build_player()
	_build_camera()
	_build_hud()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
				Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
				hud.show_message("", 0.1)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_dist = clampf(_dist - 0.6, 3.0, 12.0)
			spring.spring_length = _dist
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_dist = clampf(_dist + 0.6, 3.0, 12.0)
			spring.spring_length = _dist
	elif event is InputEventMouseMotion:
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			var mm := event as InputEventMouseMotion
			_yaw -= mm.relative.x * 0.0032
			_pitch = clampf(_pitch - mm.relative.y * 0.0028, -1.1, 0.45)
	elif event is InputEventKey:
		var k := event as InputEventKey
		if k.pressed and not k.echo:
			if k.physical_keycode == KEY_ESCAPE:
				Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
			elif k.physical_keycode == KEY_R:
				reset_player()


func _process(delta: float) -> void:
	_reset_cooldown -= delta
	# Camera follows the player smoothly.
	if is_instance_valid(player):
		var target: Vector3 = player.global_position + Vector3(0, 1.6, 0)
		cam_yaw.global_position = cam_yaw.global_position.lerp(target, 1.0 - exp(-10.0 * delta))
		cam_yaw.rotation.y = _yaw
		cam_pitch.rotation.x = _pitch

		if is_instance_valid(hud):
			var hv := Vector3(player.velocity.x, 0, player.velocity.z)
			hud.set_speed(hv.length())

		# Fell off (shouldn't happen with fence, but safe) or R held.
		if player.global_position.y < -12.0:
			reset_player()
		if Input.is_physical_key_pressed(KEY_R) and _reset_cooldown <= 0.0:
			reset_player()

	# Q / E keyboard camera orbit for trackpads / no-mouse users.
	if Input.is_physical_key_pressed(KEY_Q):
		_yaw += 2.2 * delta
	if Input.is_physical_key_pressed(KEY_E):
		_yaw -= 2.2 * delta


func collect_coin(coin: Node3D) -> void:
	coins_got += 1
	hud.set_coins(coins_got, coins_total)
	hud.show_message("All coins collected! You rock!" if coins_got >= coins_total else "+1 coin!", 2.0)


func reset_player() -> void:
	if not is_instance_valid(player):
		return
	_reset_cooldown = 0.5
	player.global_position = spawn_pos
	player.velocity = Vector3.ZERO
	hud.show_message("Back to start!", 1.5)


# --- construction ----------------------------------------------------------

func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.3, 0.55, 0.95)
	sky_mat.sky_horizon_color = Color(0.7, 0.85, 1.0)
	sky_mat.ground_bottom_color = Color(0.4, 0.35, 0.3)
	sky_mat.ground_horizon_color = Color(0.75, 0.82, 0.9)
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.75, 0.85, 0.95)
	env.fog_density = 0.008

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -35, 0)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-30, 140, 0)
	fill.light_energy = 0.25
	fill.light_color = Color(0.8, 0.88, 1.0)
	fill.shadow_enabled = false
	add_child(fill)


func _build_sandbox() -> void:
	sandbox = Node3D.new()
	sandbox.name = "Sandbox"
	sandbox.set_script(SandboxScript)
	add_child(sandbox)
	sandbox.call("build")
	coins_total = _count_coins()


func _count_coins() -> int:
	var n := 0
	_find_coins(sandbox, func() -> void: n += 1)
	return n


func _find_coins(node: Node, visit: Callable) -> void:
	if node.is_class("Area3D") and node.get_script() != null and String(node.get_script().resource_path).ends_with("coin.gd"):
		visit.call()
	for child in node.get_children():
		_find_coins(child, visit)


func _build_player() -> void:
	player = CharacterBody3D.new()
	player.name = "Player"
	player.set_script(PlayerScript)
	player.position = spawn_pos
	add_child(player)
	# player._ready() runs on add_child; assign camera anchor afterwards via call.
	await get_tree().process_frame
	if is_instance_valid(cam_yaw):
		player.set("camera_yaw", cam_yaw)


func _build_camera() -> void:
	cam_yaw = Node3D.new()
	cam_yaw.name = "CameraYaw"
	cam_yaw.add_to_group("camera_yaw")
	cam_yaw.position = spawn_pos + Vector3(0, 1.6, 0)
	add_child(cam_yaw)

	cam_pitch = Node3D.new()
	cam_pitch.name = "CameraPitch"
	cam_pitch.rotation.x = _pitch
	cam_yaw.add_child(cam_pitch)

	spring = SpringArm3D.new()
	spring.spring_length = _dist
	spring.margin = 0.3
	cam_pitch.add_child(spring)

	camera = Camera3D.new()
	camera.fov = 60.0
	camera.far = 200.0
	spring.add_child(camera)
	camera.current = true

	if is_instance_valid(player):
		player.set("camera_yaw", cam_yaw)


func _build_hud() -> void:
	hud = CanvasLayer.new()
	hud.set_script(HudScript)
	add_child(hud)
	await get_tree().process_frame
	hud.call("set_coins", coins_got, coins_total)
