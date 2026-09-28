extends Node3D
## Smooth third-person orbit camera with collision (via SpringArm3D).
## Click to capture the mouse; Esc releases; wheel zooms.

var yaw := 0.0
var pitch := -0.32
var dist := 6.0

@onready var _arm: SpringArm3D = $SpringArm3D
@onready var _target: Node3D = get_parent().get_node("Player")


func _ready() -> void:
	_arm.spring_length = dist


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			dist = clampf(dist - 0.6, 3.0, 10.0)
			_arm.spring_length = dist
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			dist = clampf(dist + 0.6, 3.0, 10.0)
			_arm.spring_length = dist
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var mm := event as InputEventMouseMotion
		yaw -= mm.relative.x * 0.0035
		pitch = clampf(pitch - mm.relative.y * 0.003, -1.1, 0.35)
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _process(delta: float) -> void:
	if _target == null:
		return
	# Keyboard look (also handy on web before first click).
	if Input.is_physical_key_pressed(KEY_Q):
		yaw += 2.0 * delta
	if Input.is_physical_key_pressed(KEY_E):
		yaw -= 2.0 * delta
	var focus := _target.global_position + Vector3(0, 1.3, 0)
	global_position = global_position.lerp(focus, minf(1.0, 10.0 * delta))
	_arm.rotation = Vector3(pitch, yaw, 0)
