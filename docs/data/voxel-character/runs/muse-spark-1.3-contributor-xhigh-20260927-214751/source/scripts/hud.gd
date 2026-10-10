extends CanvasLayer
## HUD: title, shard counter, speed/FPS readout, toasts, help panel,
## click-to-capture hint, and touch controls (stick + jump/run buttons).

var player = null
var game = null
var is_touch: bool = false
var coins_label: Label
var info_label: Label
var toast_label: Label
var hint_label: Label
var help_box: PanelContainer
var toast_time: float = 0.0
var info_time: float = 0.0
var elapsed: float = 0.0


class Stick extends Control:
	var radius: float = 80.0
	var knob := Vector2.ZERO
	var value := Vector2.ZERO
	var active: bool = false
	var touch_id: int = -1
	signal moved(v: Vector2)

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP

	func _draw() -> void:
		var c := size * 0.5
		draw_circle(c, radius, Color(1, 1, 1, 0.14))
		draw_arc(c, radius, 0.0, TAU, 48, Color(1, 1, 1, 0.5), 3.0)
		draw_circle(c + knob, 30.0, Color(1, 1, 1, 0.5))

	func gui_input(event: InputEvent) -> void:
		if event is InputEventScreenTouch:
			var st := event as InputEventScreenTouch
			if st.pressed:
				touch_id = st.index
				active = true
				_drag(st.position)
			elif st.index == touch_id:
				active = false
				touch_id = -1
				knob = Vector2.ZERO
				value = Vector2.ZERO
				moved.emit(value)
				queue_redraw()
		elif event is InputEventScreenDrag:
			var dr := event as InputEventScreenDrag
			if active and dr.index == touch_id:
				_drag(dr.position)
		elif event is InputEventMouseButton:
			var mb := event as InputEventMouseButton
			if mb.button_index == MOUSE_BUTTON_LEFT:
				if mb.pressed:
					active = true
					_drag(mb.position)
				else:
					active = false
					knob = Vector2.ZERO
					value = Vector2.ZERO
					moved.emit(value)
					queue_redraw()
		elif event is InputEventMouseMotion:
			var mm := event as InputEventMouseMotion
			if active and mm.button_mask != 0:
				_drag(mm.position)

	func _drag(p: Vector2) -> void:
		var d := p - size * 0.5
		if d.length() > radius:
			d = d.normalized() * radius
		knob = d
		value = d / radius
		moved.emit(value)
		queue_redraw()


func _ready() -> void:
	is_touch = DisplayServer.is_touchscreen_available()
	player = get_parent().get_node("Player")
	game = get_parent()
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_make_label("VOXEL RUNNER", 30, Vector2(16, 10), root)
	coins_label = _make_label("", 22, Vector2(16, 52), root)
	info_label = _make_label("", 16, Vector2(16, 86), root)
	set_coins(0, 12)
	# Toast (top center).
	toast_label = _make_label("", 24, Vector2.ZERO, root)
	toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	toast_label.anchor_left = 0.5
	toast_label.anchor_right = 0.5
	toast_label.offset_left = -340.0
	toast_label.offset_right = 340.0
	toast_label.offset_top = 90.0
	toast_label.modulate = Color(1, 1, 1, 0)
	# Click-to-play hint (center).
	hint_label = _make_label("CLICK TO PLAY  -  WASD run - SPACE jump", 22, Vector2.ZERO, root)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_label.anchor_left = 0.5
	hint_label.anchor_right = 0.5
	hint_label.anchor_top = 0.5
	hint_label.anchor_bottom = 0.5
	hint_label.offset_left = -340.0
	hint_label.offset_right = 340.0
	hint_label.offset_top = 60.0
	hint_label.offset_bottom = 100.0
	_build_help(root)
	_make_label("Godot 4.7 - GL Compatibility - single thread", 13, Vector2.ZERO, root, true)
	if is_touch:
		_build_touch(root)


func _process(delta: float) -> void:
	elapsed += delta
	if toast_time > 0.0:
		toast_time -= delta
		toast_label.modulate = Color(1, 1, 1, clampf(toast_time, 0.0, 1.0))
	hint_label.visible = (not is_touch) and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED
	if hint_label.visible:
		hint_label.modulate = Color(1, 1, 1, 0.55 + 0.4 * sin(elapsed * 4.0))
	info_time -= delta
	if info_time <= 0.0:
		info_time = 0.25
		var spd := 0.0
		if player != null:
			spd = player.get_speed()
		info_label.text = "Speed %4.1f m/s    %d FPS" % [spd, int(Engine.get_frames_per_second())]


func set_coins(got: int, total: int) -> void:
	if coins_label != null:
		coins_label.text = "◆ %d / %d shards" % [got, total]


func toast(msg: String, dur: float = 3.0) -> void:
	toast_label.text = msg
	toast_time = dur
	toast_label.modulate = Color(1, 1, 1, 1)


func toggle_help() -> void:
	help_box.visible = not help_box.visible


func _on_stick(v: Vector2) -> void:
	if player != null:
		player.move_axis = v


func _make_label(text: String, fsize: int, pos: Vector2, parent: Control, bottom_right: bool = false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", fsize)
	l.add_theme_color_override("font_color", Color.WHITE)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("outline_size", 6)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if bottom_right:
		l.anchor_left = 1.0
		l.anchor_right = 1.0
		l.anchor_top = 1.0
		l.anchor_bottom = 1.0
		l.offset_left = -430.0
		l.offset_right = -12.0
		l.offset_top = -30.0
		l.offset_bottom = -8.0
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	else:
		l.position = pos
	parent.add_child(l)
	return l


func _build_help(root: Control) -> void:
	help_box = PanelContainer.new()
	help_box.anchor_left = 0.0
	help_box.anchor_right = 0.0
	help_box.anchor_top = 1.0
	help_box.anchor_bottom = 1.0
	help_box.offset_left = 16.0
	help_box.offset_top = -296.0
	help_box.offset_right = 452.0
	help_box.offset_bottom = -16.0
	help_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0.5)
	sb.set_corner_radius_all(10)
	sb.content_margin_left = 14.0
	sb.content_margin_right = 14.0
	sb.content_margin_top = 10.0
	sb.content_margin_bottom = 10.0
	help_box.add_theme_stylebox_override("panel", sb)
	var l := Label.new()
	l.text = "RUN  WASD / arrows  (SHIFT = sprint)\nLOOK  drag mouse, or click to capture - wheel zooms\nJUMP  Space   -   RESET  R   -   HELP  H\n\nCollect all 12 sky shards!\nSome hide on the platform, steps and crates."
	l.add_theme_font_size_override("font_size", 16)
	l.add_theme_color_override("font_color", Color.WHITE)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	help_box.add_child(l)
	root.add_child(help_box)


func _build_touch(root: Control) -> void:
	var stick := Stick.new()
	stick.anchor_left = 0.0
	stick.anchor_right = 0.0
	stick.anchor_top = 1.0
	stick.anchor_bottom = 1.0
	stick.offset_left = 24.0
	stick.offset_top = -244.0
	stick.offset_right = 244.0
	stick.offset_bottom = -24.0
	root.add_child(stick)
	stick.moved.connect(_on_stick)
	var jump_b := _make_button("JUMP", -140.0, -250.0, -24.0, -170.0, root)
	jump_b.button_down.connect(_on_jump_pressed)
	var run_b := _make_button("RUN", -140.0, -150.0, -24.0, -70.0, root)
	run_b.button_down.connect(_on_run_down)
	run_b.button_up.connect(_on_run_up)


func _make_button(text: String, l: float, t: float, r: float, b: float, parent: Control) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.focus_mode = Control.FOCUS_NONE
	btn.add_theme_font_size_override("font_size", 22)
	btn.anchor_left = 1.0
	btn.anchor_right = 1.0
	btn.anchor_top = 1.0
	btn.anchor_bottom = 1.0
	btn.offset_left = l
	btn.offset_top = t
	btn.offset_right = r
	btn.offset_bottom = b
	parent.add_child(btn)
	return btn


func _on_jump_pressed() -> void:
	if player != null:
		player.touch_jump()


func _on_run_down() -> void:
	if player != null:
		player.touch_sprint = true


func _on_run_up() -> void:
	if player != null:
		player.touch_sprint = false
