extends Node3D

const DIST := 9.0
const SENS_X := 0.004
const SENS_Y := 0.004
const MIN_PITCH := -1.1
const MAX_PITCH := 0.35
const FOCUS_HEIGHT := 1.4

var _yaw := 0.0
var _pitch := -0.55
var _dragging := false

@onready var player: Node3D = get_parent().get_node_or_null("Player")
@onready var camera: Camera3D = $Camera3D


func _ready() -> void:
	_update_camera()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			_dragging = event.pressed
			get_viewport().set_input_as_handled()
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			camera.fov = clampf(camera.fov - 3.0, 30.0, 90.0)
			get_viewport().set_input_as_handled()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			camera.fov = clampf(camera.fov + 3.0, 30.0, 90.0)
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _dragging:
		_yaw -= event.relative.x * SENS_X
		_pitch = clampf(_pitch + event.relative.y * SENS_Y, MIN_PITCH, MAX_PITCH)
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			get_tree().quit()


func _physics_process(_delta: float) -> void:
	_update_camera()


func _update_camera() -> void:
	if not player:
		return
	var offset := Vector3(
		sin(_yaw) * cos(_pitch),
		sin(_pitch),
		cos(_yaw) * cos(_pitch)
	) * DIST
	global_position = player.global_position + Vector3(0.0, FOCUS_HEIGHT, 0.0) + offset
	look_at(player.global_position + Vector3(0.0, FOCUS_HEIGHT, 0.0), Vector3.UP)
