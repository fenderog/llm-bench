extends Node3D
## Voxel Horse: a running horse built from procedurally generated voxels.
## Drives the horse (speed, steering, jump), the chase camera and the HUD.

const VoxelHorse = preload("res://scripts/voxel_horse.gd")
const VoxelWorld = preload("res://scripts/voxel_world.gd")

const MAX_SPEED := 12.0
const GAIT_PRESETS := [1.6, 4.2, 7.0, 11.0]
const GRAVITY := 15.0
const JUMP_SPEED := 5.6
const HORSE_RADIUS := 0.45
const CAMERA_CLEARANCE := 1.8    # keeps the camera out of tree canopies

var _world: VoxelWorld
var _horse_root: Node3D
var _horse: VoxelHorse
var _camera: Camera3D

var _pos := Vector3.ZERO
var _yaw := 0.0
var _speed := 0.0
var _target_speed := 11.0
var _turn := 0.0
var _roll := 0.0
var _height := 0.0
var _vy := 0.0

var _cam_yaw_offset := 1.15     # 0 = straight behind the horse
var _cam_pitch := 0.20
var _cam_dist := 5.4
var _cam_heading := 0.0
var _cam_focus := Vector3.ZERO

var _stats: Label
var _hint: Label


func _ready() -> void:
	_world = VoxelWorld.new()
	add_child(_world)

	_horse_root = Node3D.new()
	add_child(_horse_root)
	_horse = VoxelHorse.new()
	_horse_root.add_child(_horse)

	_camera = Camera3D.new()
	_camera.fov = 55.0
	_camera.near = 0.1
	_camera.far = 700.0
	add_child(_camera)
	_camera.make_current()

	_build_hud()
	_speed = _target_speed
	_place_camera(1.0)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_SPACE:
				_jump()
			KEY_1, KEY_2, KEY_3, KEY_4:
				_target_speed = GAIT_PRESETS[event.physical_keycode - KEY_1]
			KEY_C:
				_horse.next_coat()
			KEY_R:
				_cam_yaw_offset = 1.15
				_cam_pitch = 0.20
				_cam_dist = 5.4
			KEY_H:
				_hint.visible = not _hint.visible
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
		_cam_yaw_offset -= event.relative.x * 0.006
		_cam_pitch = clampf(_cam_pitch + event.relative.y * 0.005, -0.05, 1.2)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_cam_dist = clampf(_cam_dist * 0.92, 2.5, 16.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_cam_dist = clampf(_cam_dist * 1.08, 2.5, 16.0)


func _key(physical: Key, alt: Key) -> bool:
	return Input.is_physical_key_pressed(physical) or Input.is_physical_key_pressed(alt)


func _jump() -> void:
	if _height <= 0.0 and _vy == 0.0:
		_vy = JUMP_SPEED


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	delta = minf(delta, 0.05)

	if _key(KEY_W, KEY_UP):
		_target_speed = minf(_target_speed + 5.0 * delta, MAX_SPEED)
	if _key(KEY_S, KEY_DOWN):
		_target_speed = maxf(_target_speed - 7.0 * delta, 0.0)
	var steer := 0.0
	if _key(KEY_A, KEY_LEFT):
		steer += 1.0
	if _key(KEY_D, KEY_RIGHT):
		steer -= 1.0

	_speed = move_toward(_speed, _target_speed, (4.5 if _target_speed > _speed else 9.0) * delta)
	_turn = move_toward(_turn, steer, 6.0 * delta)
	var turn_rate := lerpf(1.7, 0.95, _speed / MAX_SPEED) * clampf(0.25 + _speed / 2.5, 0.25, 1.0)
	_yaw += _turn * turn_rate * delta
	_pos += Vector3(-sin(_yaw), 0.0, -cos(_yaw)) * _speed * delta

	if _vy != 0.0 or _height > 0.0:
		_vy -= GRAVITY * delta
		_height += _vy * delta
		if _height <= 0.0:
			_height = 0.0
			_vy = 0.0

	var fixed := _world.resolve_collisions(Vector2(_pos.x, _pos.z), HORSE_RADIUS, _height > 0.45)
	_pos.x = fixed.x
	_pos.z = fixed.y

	var lean := clampf(_turn * turn_rate * _speed * 0.03, -0.3, 0.3)
	_roll = lerpf(_roll, lean, 1.0 - exp(-8.0 * delta))
	_horse_root.position = Vector3(_pos.x, _height, _pos.z)
	_horse_root.rotation = Vector3(0.0, _yaw, _roll)

	var air := 1.0 if _height > 0.06 else 0.0
	_horse.step(delta, _speed, _turn, air, clampf(_vy / JUMP_SPEED, -1.0, 1.0))
	_world.update_focus(_pos, delta)
	_place_camera(delta)
	_update_hud()


func _place_camera(delta: float) -> void:
	_cam_heading = lerp_angle(_cam_heading, _yaw, 1.0 - exp(-2.5 * delta))
	var target := Vector3(_pos.x, 1.15 + _height * 0.6, _pos.z)
	_cam_focus = _cam_focus.lerp(target, 1.0 - exp(-10.0 * delta))
	var a := _cam_heading + _cam_yaw_offset
	var dir := Vector3(sin(a) * cos(_cam_pitch), sin(_cam_pitch), cos(a) * cos(_cam_pitch))
	var cam_pos := _cam_focus + dir * _cam_dist
	var clear := _world.resolve_collisions(Vector2(cam_pos.x, cam_pos.z), CAMERA_CLEARANCE, false)
	_camera.position = Vector3(clear.x, cam_pos.y, clear.y)
	_camera.look_at(_cam_focus, Vector3.UP)


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var settings := LabelSettings.new()
	settings.font_size = 20
	settings.font_color = Color.WHITE
	settings.outline_size = 6
	settings.outline_color = Color(0.05, 0.08, 0.12, 0.8)

	_stats = Label.new()
	_stats.label_settings = settings
	_stats.position = Vector2(20.0, 14.0)
	layer.add_child(_stats)

	_hint = Label.new()
	_hint.label_settings = settings
	_hint.text = "W/S  speed     A/D  steer     Space  jump     1-4  gaits     C  coat\nDrag  orbit camera     Wheel  zoom     R  reset camera     H  hide help"
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_hint.offset_top = -66.0
	_hint.offset_bottom = -12.0
	layer.add_child(_hint)


func _gait_name() -> String:
	if _speed < 0.3:
		return "Standing"
	if _speed < 2.9:
		return "Walk"
	if _speed < 5.6:
		return "Trot"
	if _speed < 9.0:
		return "Canter"
	return "Gallop"


func _update_hud() -> void:
	_stats.text = "Voxel Horse - %s\n%s  |  %d km/h" % [_horse.coat_name(), _gait_name(), roundi(_speed * 3.6)]
