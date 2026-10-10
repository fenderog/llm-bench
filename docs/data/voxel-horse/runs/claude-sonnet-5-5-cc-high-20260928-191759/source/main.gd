extends Node3D
## Wires the horse, world, camera and HUD together and handles input.

const Horse = preload("res://horse.gd")
const World = preload("res://world.gd")

const MAX_SPEED := 13.0
const ACCEL := 4.0
const SPEED_STEP := 5.0  # m/s per second while W/S is held

const HORIZON := Color(0.68, 0.80, 0.92)

var target_speed := 9.0
var speed := 8.0

var _horse: Node3D
var _world: Node3D
var _camera: Camera3D
var _focus := Vector3(0, 1.0, 0)
var _yaw := deg_to_rad(125.0)
var _pitch := deg_to_rad(11.0)
var _dist := 5.2
var _shake := 0.0
var _press_pos := Vector2.ZERO
var _press_moved := false
var _cleared := 0
var _hit := 0
var _stats: Label


func _ready() -> void:
	_build_environment()

	_world = World.new()
	add_child(_world)
	_world.hurdle_cleared.connect(func() -> void: _cleared += 1)
	_world.hurdle_hit.connect(_on_hurdle_hit)

	_horse = Horse.new()
	add_child(_horse)

	_camera = Camera3D.new()
	_camera.far = 300.0
	_camera.fov = 55.0
	add_child(_camera)
	_camera.make_current()

	_build_hud()
	_horse.update(0.0, speed)
	_update_camera(0.0)


func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.24, 0.48, 0.85)
	sky_mat.sky_horizon_color = HORIZON
	sky_mat.ground_horizon_color = HORIZON
	sky_mat.ground_bottom_color = HORIZON
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.6
	env.fog_enabled = true
	env.fog_light_color = HORIZON
	env.fog_density = 0.012
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, 150, 0)
	sun.light_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 45.0
	add_child(sun)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_stats = _make_label(layer, 22)
	_stats.position = Vector2(20, 14)

	var help := _make_label(layer, 16)
	help.text = "W / S  faster / slower     SPACE  jump the hurdles     A / D or drag  look around     wheel  zoom"
	help.anchor_top = 1.0
	help.anchor_bottom = 1.0
	help.offset_left = 20
	help.offset_top = -40


func _make_label(parent: Node, size: int) -> Label:
	var label := Label.new()
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_outline_color", Color(0.05, 0.1, 0.15, 0.9))
	label.add_theme_constant_override("outline_size", 6)
	parent.add_child(label)
	return label


func _on_hurdle_hit() -> void:
	_hit += 1
	_horse.stumble()
	speed *= 0.5
	_shake = 0.25


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE or event.keycode == KEY_ENTER:
			_horse.jump()
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_press_pos = event.position
				_press_moved = false
			elif not _press_moved:
				_horse.jump()  # a plain click / tap also jumps
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_dist = clampf(_dist - 0.5, 2.5, 14.0)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_dist = clampf(_dist + 0.5, 2.5, 14.0)
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
		if not _press_moved and event.position.distance_to(_press_pos) > 6.0:
			_press_moved = true
		if _press_moved:
			_yaw -= event.relative.x * 0.006
			_pitch = clampf(_pitch + event.relative.y * 0.005, deg_to_rad(-2.0), deg_to_rad(70.0))


func _process(delta: float) -> void:
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		target_speed += SPEED_STEP * delta
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		target_speed -= SPEED_STEP * delta
	target_speed = clampf(target_speed, 0.0, MAX_SPEED)
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		_yaw += 1.6 * delta
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		_yaw -= 1.6 * delta

	speed = move_toward(speed, target_speed, ACCEL * delta)
	_horse.update(delta, speed)
	_world.update(delta, speed, _horse.lift)
	_update_camera(delta)

	_stats.text = "%s   %d km/h   %d m   cleared %d   knocked %d" % [
		_horse.gait_name, roundi(speed * 3.6), roundi(_world.distance), _cleared, _hit]


func _update_camera(delta: float) -> void:
	var goal := Vector3(0, 1.0 + _horse.lift * 0.5, 0)
	_focus = _focus.lerp(goal, 1.0 - exp(-8.0 * delta))
	var dir := Vector3(sin(_yaw) * cos(_pitch), sin(_pitch), cos(_yaw) * cos(_pitch))
	_shake = maxf(_shake - delta * 0.5, 0.0)
	var jitter := Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * _shake * 0.3
	_camera.position = _focus + dir * _dist + jitter
	_camera.look_at(_focus)
	_camera.fov = 55.0 + speed * 0.6
