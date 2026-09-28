class_name CameraRig
extends Node3D
## Third-person follow camera. Drag with mouse (or one finger on touch) to
## orbit, wheel to zoom, Q/E to rotate. A SpringArm3D keeps it out of walls.

var yaw := 0.0
var pitch := -0.38
var dist := 6.0
var dragging := false
var snapped := false

@onready var arm := $SpringArm3D as SpringArm3D


func _ready() -> void:
	add_to_group("camera_rig")
	arm.spring_length = dist
	_snap_to_player()


func _snap_to_player() -> void:
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p != null:
		global_position = p.global_position + Vector3(0, 1.5, 0)
		rotation = Vector3(pitch, yaw, 0)
		snapped = true


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			dist = clampf(dist - 0.6, 3.0, 10.0)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			dist = clampf(dist + 0.6, 3.0, 10.0)
		elif mb.button_index == MOUSE_BUTTON_LEFT or mb.button_index == MOUSE_BUTTON_RIGHT or mb.button_index == MOUSE_BUTTON_MIDDLE:
			dragging = mb.pressed
	elif event is InputEventMouseMotion and dragging:
		var mm := event as InputEventMouseMotion
		yaw -= mm.relative.x * 0.0055
		pitch = clampf(pitch - mm.relative.y * 0.005, -1.15, -0.08)
	elif event is InputEventScreenDrag:
		var sd := event as InputEventScreenDrag
		yaw -= sd.relative.x * 0.006
		pitch = clampf(pitch - sd.relative.y * 0.006, -1.15, -0.08)


func _process(delta: float) -> void:
	if Input.is_physical_key_pressed(KEY_Q):
		yaw += 1.9 * delta
	if Input.is_physical_key_pressed(KEY_E):
		yaw -= 1.9 * delta
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p != null:
		var want := p.global_position + Vector3(0, 1.5, 0)
		if not snapped:
			global_position = want
			snapped = true
		else:
			global_position = global_position.lerp(want, 1.0 - exp(-10.0 * delta))
	rotation = Vector3(pitch, yaw, 0)
	arm.spring_length = lerpf(arm.spring_length, dist, 1.0 - exp(-8.0 * delta))
