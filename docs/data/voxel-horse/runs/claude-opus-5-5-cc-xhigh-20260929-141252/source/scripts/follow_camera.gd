extends Camera3D
## Smooth follow camera with several framings. Drag the mouse to orbit and
## scroll to zoom.

const Horse = preload("res://scripts/horse.gd")
const Terrain = preload("res://scripts/terrain.gd")

const MODE_NAMES := ["Chase", "Side", "Front", "Orbit"]
## Per mode: distance, height above the ground, yaw relative to the heading.
const MODE_SETUP: Array[Vector3] = [
	Vector3(6.5, 2.6, PI),
	Vector3(7.0, 1.7, PI * 0.5),
	Vector3(8.0, 2.2, 0.0),
	Vector3(10.0, 3.6, 0.0),
]

var target: Horse
var terrain: Terrain
var mode := 0

var _yaw := 0.0
var _dist := 7.5
var _height := 2.8
var _orbit := 0.0
var _user_yaw := 0.0
var _user_height := 0.0
var _zoom := 1.0
var _dragging := false
var _focus := Vector3.ZERO


func cycle_mode() -> void:
	mode = (mode + 1) % MODE_SETUP.size()
	_user_yaw = 0.0
	_user_height = 0.0


func set_zoom(zoom: float) -> void:
	_zoom = clampf(zoom, 0.5, 2.5)


func mode_name() -> String:
	return MODE_NAMES[mode]


## Jumps straight to the desired framing (used on start-up).
func snap() -> void:
	_focus = target.global_position + Vector3(0, 1.3, 0)
	_yaw = target.heading + MODE_SETUP[mode].z
	_process(1.0)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT or mb.button_index == MOUSE_BUTTON_RIGHT:
			_dragging = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			_zoom = clampf(_zoom * 0.9, 0.5, 2.5)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			_zoom = clampf(_zoom * 1.1, 0.5, 2.5)
	elif event is InputEventMouseMotion and _dragging:
		var mm := event as InputEventMouseMotion
		_user_yaw -= mm.relative.x * 0.006
		_user_height = clampf(_user_height + mm.relative.y * 0.02, -1.5, 6.0)


func _process(delta: float) -> void:
	if target == null:
		return
	var setup := MODE_SETUP[mode]
	if mode == 3:
		_orbit += delta * 0.25
	var want_yaw := target.heading + setup.z + _user_yaw + (_orbit if mode == 3 else 0.0)
	var k := 1.0 - exp(-4.0 * delta)
	_yaw = lerp_angle(_yaw, want_yaw, k)
	_dist = lerpf(_dist, setup.x * _zoom, k)
	_height = lerpf(_height, setup.y * _zoom + _user_height, k)

	# Follow tightly sideways but soften vertical terrace steps.
	var goal := target.global_position + Vector3(0, 1.3, 0)
	var kh := 1.0 - exp(-12.0 * delta)
	_focus.x = lerpf(_focus.x, goal.x, kh)
	_focus.z = lerpf(_focus.z, goal.z, kh)
	_focus.y = lerpf(_focus.y, goal.y, 1.0 - exp(-5.0 * delta))

	var pos := _focus + Vector3(sin(_yaw), 0.0, cos(_yaw)) * _dist
	pos.y = _focus.y - 1.3 + _height
	if terrain:
		pos.y = maxf(pos.y, maxf(terrain.ground_at(pos.x, pos.z), Terrain.WATER_LEVEL) + 0.6)
	global_position = pos
	look_at(_focus + Vector3(0, 0.1, 0), Vector3.UP)
	fov = lerpf(fov, 68.0 + clampf(target.speed / Horse.SPRINT_SPEED, 0.0, 1.0) * 10.0, k)
