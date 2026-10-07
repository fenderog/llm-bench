extends Node3D

## Endless voxel gallop. Steer with A/D or the arrow keys, speed up or slow
## down with W/S or Up/Down, and press Space to jump the hurdles. R restarts.

const CRUISE_SPEED := 9.0
const MIN_SPEED := 3.0
const MAX_SPEED := 14.0
const SPEED_RATE := 5.0  # how fast speed moves toward its target, per second
const STEER_RATE := 7.0  # lateral movement per second
const LANE_LIMIT := 6.0
const JUMP_TIME := 0.9  # seconds in the air
const JUMP_APEX := 1.5  # height at the top of a jump
const CLEAR_HEIGHT := 1.2  # hooves must be this high to clear the top rail
const HURDLE_REACH := 1.8  # lateral distance at which a hurdle is hit
const FRONT_REACH := 0.5  # how far ahead of the origin the front hooves are
const FIRST_HURDLE := 45.0
const HURDLE_GAP := Vector2(28.0, 46.0)
const HURDLE_AHEAD := 150.0
const CULL_BEHIND := 40.0

var _course: Course
var _horse: VoxelHorse
var _camera: Camera3D
var _camera_pos := Vector3.ZERO
var _info: Label
var _message: Label
var _hurdles: Array[Dictionary] = []
var _distance := 0.0
var _lane := 0.0
var _steer := 0.0
var _speed := CRUISE_SPEED
var _jump_time := -1.0  # negative when the horse is on the ground
var _height := 0.0
var _stumble := 0.0
var _shake := 0.0
var _cleared := 0
var _knocked := 0
var _next_hurdle := FIRST_HURDLE
var _message_time := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_course = Course.new()
	add_child(_course)
	_horse = VoxelHorse.new()
	add_child(_horse)
	_camera = Camera3D.new()
	_camera.fov = 65.0
	_camera.far = 600.0
	add_child(_camera)
	_camera.current = true
	_build_hud()
	_update_camera(1.0)


func _process(delta: float) -> void:
	_read_input(delta)
	_update_jump(delta)
	_distance += _speed * delta
	_course.follow(_distance)
	_update_hurdles()

	_horse.position = Vector3(_lane, _height, -_distance)
	_horse.rotation = Vector3(-0.2 if _stumble > 0.0 else 0.0, -_steer * 0.2, _steer * 0.1)
	_horse.animate(_speed, delta, _jump_time >= 0.0)

	_update_camera(delta)
	_update_hud(delta)


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key and key.pressed and not key.echo and key.keycode == KEY_R:
		get_tree().reload_current_scene()


func _read_input(delta: float) -> void:
	_steer = 0.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		_steer -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		_steer += 1.0
	_lane = clampf(_lane + _steer * STEER_RATE * delta, -LANE_LIMIT, LANE_LIMIT)

	var target := CRUISE_SPEED
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		target = MAX_SPEED
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		target = MIN_SPEED
	if _stumble > 0.0:
		_stumble -= delta
		target = MIN_SPEED
	_speed = move_toward(_speed, target, SPEED_RATE * delta)

	if Input.is_action_just_pressed("ui_accept") and _jump_time < 0.0 and _stumble <= 0.0:
		_jump_time = 0.0


func _update_jump(delta: float) -> void:
	if _jump_time < 0.0:
		_height = 0.0
		return
	_jump_time += delta
	var t := _jump_time / JUMP_TIME
	if t >= 1.0:
		_jump_time = -1.0
		_height = 0.0
	else:
		_height = 4.0 * JUMP_APEX * t * (1.0 - t)


func _update_hurdles() -> void:
	while _next_hurdle < _distance + HURDLE_AHEAD:
		var lane := _rng.randf_range(-LANE_LIMIT + 1.0, LANE_LIMIT - 1.0)
		_hurdles.append({
			"distance": _next_hurdle,
			"lane": lane,
			"node": _course.add_hurdle(_next_hurdle, lane),
			"resolved": false,
		})
		_next_hurdle += _rng.randf_range(HURDLE_GAP.x, HURDLE_GAP.y)

	# A hurdle is judged once the horse's front hooves reach it.
	for hurdle in _hurdles:
		if hurdle.resolved or _distance + FRONT_REACH < hurdle.distance:
			continue
		hurdle.resolved = true
		_judge(hurdle)

	var kept: Array[Dictionary] = []
	for hurdle in _hurdles:
		if hurdle.distance < _distance - CULL_BEHIND:
			hurdle.node.queue_free()
		else:
			kept.append(hurdle)
	_hurdles = kept


func _judge(hurdle: Dictionary) -> void:
	if absf(_lane - hurdle.lane) > HURDLE_REACH:
		return
	if _height >= CLEAR_HEIGHT:
		_cleared += 1
		_show_message("Clear!", 0.8)
		return

	_knocked += 1
	_stumble = 1.2
	_shake = 0.35
	_show_message("Knocked it down!", 1.2)
	var tween := create_tween()
	tween.tween_property(hurdle.node, "rotation:x", -1.2, 0.25)


func _update_camera(delta: float) -> void:
	var focus := _horse.position + Vector3(0.0, 1.2, 0.0)
	var target := focus + Vector3(_lane * 0.3 + 4.0, 2.4, 6.0)
	_camera_pos = _camera_pos.lerp(target, minf(1.0, delta * 6.0))

	var jitter := Vector3.ZERO
	if _shake > 0.0:
		_shake = maxf(0.0, _shake - delta)
		jitter = Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), 0.0) * _shake * 0.5
	_camera.position = _camera_pos + jitter
	_camera.look_at(focus + Vector3(0.0, 0.0, -6.0), Vector3.UP)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_info = _make_label(layer, Vector2(16.0, 12.0), 24)
	_message = _make_label(layer, Vector2(16.0, 52.0), 32)
	var help := _make_label(layer, Vector2(16.0, 672.0), 16)
	help.text = "A/D or arrows: steer   W/S or up/down: speed   Space: jump   R: restart"


func _make_label(layer: CanvasLayer, at: Vector2, font_size: int) -> Label:
	var label := Label.new()
	label.position = at
	label.add_theme_font_size_override("font_size", font_size)
	layer.add_child(label)
	return label


func _show_message(text: String, seconds: float) -> void:
	_message.text = text
	_message_time = seconds


func _update_hud(delta: float) -> void:
	_info.text = "Speed %d km/h   Cleared %d   Knocked %d" % [roundi(_speed * 5.0), _cleared, _knocked]
	_message_time = maxf(0.0, _message_time - delta)
	_message.modulate.a = minf(1.0, _message_time)
