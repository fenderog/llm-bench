extends CanvasLayer
## Minimal HUD: coin counter, speed readout, help text, transient messages.

var coin_label: Label
var speed_label: Label
var msg_label: Label
var _msg_time := 0.0

func _ready() -> void:
	layer = 10

	coin_label = _make_label(Vector2(16, 12), 26, HORIZONTAL_ALIGNMENT_LEFT)
	speed_label = _make_label(Vector2(16, 48), 18, HORIZONTAL_ALIGNMENT_LEFT)
	speed_label.modulate = Color(1, 1, 1, 0.85)

	var help := _make_label(Vector2(-16, 12), 16, HORIZONTAL_ALIGNMENT_RIGHT)
	help.anchor_left = 1.0
	help.anchor_right = 1.0
	help.offset_left = -560.0
	help.offset_right = -16.0
	help.text = "WASD / Arrows: run   Mouse: look (click to capture)   Space: jump   Shift: sprint   R: reset"
	help.modulate = Color(1, 1, 1, 0.85)

	msg_label = _make_label(Vector2(0, 120), 30, HORIZONTAL_ALIGNMENT_CENTER)
	msg_label.anchor_left = 0.0
	msg_label.anchor_right = 1.0
	msg_label.offset_left = 0.0
	msg_label.offset_right = 0.0
	msg_label.text = "Click to capture the mouse!"

	set_coins(0, 1)


func _process(delta: float) -> void:
	if _msg_time > 0.0:
		_msg_time -= delta
		if _msg_time <= 0.0:
			msg_label.text = ""


func set_coins(got: int, total: int) -> void:
	coin_label.text = "Coins: %d / %d" % [got, total]


func set_speed(v: float) -> void:
	speed_label.text = "Speed: %.1f m/s" % v


func show_message(text: String, duration: float = 3.0) -> void:
	msg_label.text = text
	_msg_time = duration


func _make_label(pos: Vector2, font_size: int, align: HorizontalAlignment) -> Label:
	var l := Label.new()
	l.position = pos
	l.horizontal_alignment = align
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", Color.WHITE)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	l.add_theme_constant_override("outline_size", 8)
	add_child(l)
	return l
