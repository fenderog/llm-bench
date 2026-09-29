extends CanvasLayer
## On-screen help, current gait, speed and distance.

const Horse = preload("res://scripts/horse.gd")

const HELP := """VOXEL HORSE
W / Up  -  faster gait
S / Down  -  slower gait
A D / Left Right  -  steer
Shift  -  sprint      Space  -  jump
C  -  camera      H  -  coat colour
M  -  mute      F  -  fullscreen
Drag mouse  -  orbit      Wheel  -  zoom
Tab  -  hide this help"""

var horse: Horse
var camera_name := ""

var _help: Label
var _gait: Label
var _stats: Label
var _pips: Array[ColorRect] = []
var _status: Label
var _status_time := 0.0


func _ready() -> void:
	_help = _make_label(15)
	_help.text = HELP
	_help.position = Vector2(16, 12)
	add_child(_help)

	_status = _make_label(18)
	_status.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_status.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_status.offset_left = -400
	_status.offset_right = -16
	_status.offset_top = 12
	add_child(_status)

	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	box.offset_top = -120
	box.offset_bottom = -16
	box.alignment = BoxContainer.ALIGNMENT_END
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(box)

	_gait = _make_label(36)
	_gait.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_gait)

	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 6)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(row)
	for i in Horse.GAIT_SPEEDS.size() - 1:
		var pip := ColorRect.new()
		pip.custom_minimum_size = Vector2(26, 12)
		pip.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_child(pip)
		_pips.append(pip)

	_stats = _make_label(18)
	_stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_stats)


func toggle_help() -> void:
	_help.visible = not _help.visible


func flash(text: String) -> void:
	_status.text = text
	_status_time = 2.0


func _process(delta: float) -> void:
	if horse == null:
		return
	_gait.text = horse.gait_name()
	var lit := Color(1.0, 0.85, 0.3) if horse.sprinting else Color(1, 1, 1, 0.95)
	for i in _pips.size():
		_pips[i].color = lit if i < horse.gait_level else Color(0, 0, 0, 0.35)
	_stats.text = "%d km/h   -   %d m travelled   -   %s" % [
		roundi(horse.speed * 3.6), roundi(horse.distance), horse.coat_name()]
	_status_time -= delta
	_status.modulate.a = clampf(_status_time, 0.0, 1.0)


func _make_label(size: int) -> Label:
	var label := Label.new()
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.05, 0.85))
	label.add_theme_constant_override("outline_size", 6)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label
