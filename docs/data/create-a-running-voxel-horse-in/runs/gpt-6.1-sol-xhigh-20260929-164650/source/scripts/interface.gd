extends CanvasLayer
class_name TrailInterface

signal start_requested
signal pause_requested
signal resume_requested
signal menu_requested
signal sound_requested
signal left_requested
signal right_requested
signal jump_requested

const INK := Color("293e34")
const MUTED := Color("68725d")
const PAPER := Color("f5efdF")
const ORANGE := Color("c97843")

var root: Control
var title_group: Control
var play_group: Control
var modal_group: Control
var fade: ColorRect
var distance_label: Label
var carrot_label: Label
var best_label: Label
var speed_label: Label
var feedback_label: Label
var sound_button: Button
var hearts: Array[TrailGlyph] = []
var lane_marks: Array[ColorRect] = []
var modal_title: Label
var modal_subtitle: Label
var modal_stats: Label
var modal_action: Button
var modal_back: Button
var feedback_time := 0.0
var hit_wash: ColorRect
var wash_time := 0.0
var bold: FontVariation
var paused_modal := false

func _ready() -> void:
	bold = FontVariation.new()
	bold.base_font = ThemeDB.fallback_font
	bold.variation_embolden = 1.15
	root = Control.new()
	root.size = Vector2(1440, 900)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	fade = ColorRect.new()
	fade.size = root.size
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shader := Shader.new()
	shader.code = "shader_type canvas_item; void fragment() { float a = (1.0-smoothstep(0.20,0.64,UV.x))*0.95; COLOR=vec4(0.965,0.948,0.887,a); }"
	var material := ShaderMaterial.new()
	material.shader = shader
	fade.material = material
	root.add_child(fade)
	# Compact signature in the upper left.
	var logo := panel(root, Vector2(38, 30), Vector2(43, 43), INK, 11)
	glyph(logo, "horse", Vector2(7, 6), Vector2(30, 30), PAPER)
	label(root, "WILDSTRIDE", Vector2(94, 29), 22, INK, true)
	label(root, "THE VOXEL TRAIL", Vector2(96, 58), 10, MUTED, true)
	sound_button = button(root, "SOUND  ON", Vector2(1243, 30), Vector2(153, 43), false)
	sound_button.pressed.connect(func(): sound_requested.emit())
	build_title()
	build_play()
	build_modal()
	hit_wash = ColorRect.new()
	hit_wash.size = root.size
	hit_wash.color = Color(0.75, .25, .13, 0)
	hit_wash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(hit_wash)
	feedback_label = label(root, "", Vector2(725, 265), 23, PAPER, true)
	feedback_label.size = Vector2(500, 40)
	feedback_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	feedback_label.add_theme_color_override("font_shadow_color", Color(0.12, .2, .15, .4))
	feedback_label.add_theme_constant_override("shadow_offset_y", 2)
	show_title(0)

func _process(delta: float) -> void:
	var view := get_viewport().get_visible_rect().size
	var factor := minf(view.x / 1440.0, view.y / 900.0)
	root.scale = Vector2.ONE * factor
	root.position = (view - Vector2(1440, 900) * factor) * .5
	feedback_time = maxf(0, feedback_time - delta)
	feedback_label.modulate.a = minf(1, feedback_time * 2.5)
	feedback_label.position.y = 255 - (1.6 - feedback_time) * 12
	wash_time = maxf(0, wash_time - delta)
	hit_wash.color.a = wash_time * .26

func build_title() -> void:
	title_group = group(root)
	var accent := ColorRect.new()
	accent.position = Vector2(76, 205)
	accent.size = Vector2(42, 4)
	accent.color = ORANGE
	title_group.add_child(accent)
	label(title_group, "NO REINS. NO FINISH LINE.", Vector2(76, 227), 12, ORANGE, true)
	var heading := label(title_group, "WILD\nSTRIDE.", Vector2(68, 250), 88, INK, true)
	heading.add_theme_constant_override("line_spacing", -13)
	label(title_group, "A small horse. A wide-open world.\nHow far will your hooves take you?", Vector2(77, 465), 19, MUTED)
	var start := button(title_group, "HIT THE TRAIL    →", Vector2(76, 550), Vector2(294, 64), true)
	start.pressed.connect(func(): start_requested.emit())
	label(title_group, "PRESS ENTER TO RUN", Vector2(78, 631), 11, MUTED, true)
	best_label = label(title_group, "", Vector2(78, 664), 13, MUTED)
	# A quiet location caption is part of the landscape, not another menu.
	var location := panel(title_group, Vector2(1090, 730), Vector2(304, 88), Color(PAPER, .87), 13)
	label(location, "01  /  SUNSET VALLEY", Vector2(22, 15), 16, INK, true)
	label(location, "GOLDEN HOUR • ENDLESS TRAIL", Vector2(22, 47), 10, MUTED, true)
	keycap(title_group, "A", Vector2(76, 785))
	keycap(title_group, "D", Vector2(119, 785))
	label(title_group, "STEER", Vector2(169, 797), 11, MUTED, true)
	keycap(title_group, "SPACE", Vector2(256, 785), 76)
	label(title_group, "JUMP", Vector2(348, 797), 11, MUTED, true)
	keycap(title_group, "ESC", Vector2(434, 785), 54)
	label(title_group, "PAUSE", Vector2(503, 797), 11, MUTED, true)
	label(title_group, "BUILT OF BLOCKS. MADE TO ROAM.", Vector2(76, 856), 10, MUTED)

func build_play() -> void:
	play_group = group(root)
	var distance_card := panel(play_group, Vector2(455, 26), Vector2(240, 86), Color(PAPER, .93), 14)
	label(distance_card, "TRAIL DISTANCE", Vector2(20, 11), 10, MUTED, true)
	distance_label = label(distance_card, "0000", Vector2(18, 28), 34, INK, true)
	label(distance_card, "m", Vector2(195, 47), 15, MUTED)
	var carrot_card := panel(play_group, Vector2(708, 26), Vector2(164, 86), Color(PAPER, .93), 14)
	glyph(carrot_card, "carrot", Vector2(18, 36), Vector2(30, 30), ORANGE)
	label(carrot_card, "CARROTS", Vector2(20, 11), 10, MUTED, true)
	carrot_label = label(carrot_card, "0", Vector2(61, 29), 32, INK, true)
	var heart_card := panel(play_group, Vector2(885, 26), Vector2(190, 86), Color(PAPER, .93), 14)
	label(heart_card, "SPIRIT", Vector2(19, 11), 10, MUTED, true)
	for i in 3:
		hearts.append(glyph(heart_card, "heart", Vector2(20 + i * 47, 39), Vector2(27, 27), ORANGE))
	var pause := button(play_group, "Ⅱ", Vector2(1178, 30), Vector2(51, 43), false)
	pause.add_theme_font_size_override("font_size", 21)
	pause.pressed.connect(func(): pause_requested.emit())
	var info := panel(play_group, Vector2(38, 126), Vector2(295, 65), Color(PAPER, .88), 12)
	label(info, "SUNSET VALLEY", Vector2(16, 10), 11, INK, true)
	speed_label = label(info, "Leap fences. Follow the carrots.", Vector2(16, 32), 13, MUTED)
	# Mouse/touch controls remain available alongside the keyboard.
	var left := button(play_group, "←", Vector2(40, 795), Vector2(62, 59), false)
	var right := button(play_group, "→", Vector2(114, 795), Vector2(62, 59), false)
	left.add_theme_font_size_override("font_size", 25)
	right.add_theme_font_size_override("font_size", 25)
	left.pressed.connect(func(): left_requested.emit())
	right.pressed.connect(func(): right_requested.emit())
	label(play_group, "A / D  TO STEER", Vector2(195, 814), 11, PAPER, true)
	var jump := button(play_group, "SPACE   /   JUMP ↑", Vector2(1175, 795), Vector2(220, 59), true)
	jump.pressed.connect(func(): jump_requested.emit())
	label(play_group, "YOUR LINE", Vector2(681, 800), 9, PAPER, true)
	for i in 3:
		var mark := ColorRect.new()
		mark.position = Vector2(682 + i * 27, 828)
		mark.size = Vector2(19, 5)
		mark.color = Color(PAPER, .5)
		play_group.add_child(mark)
		lane_marks.append(mark)

func build_modal() -> void:
	modal_group = group(root)
	var p := panel(modal_group, Vector2(65, 230), Vector2(463, 462), PAPER, 22)
	label(p, "TAKE A BREATH", Vector2(31, 28), 11, ORANGE, true)
	modal_title = label(p, "TRAIL'S END.", Vector2(27, 59), 45, INK, true)
	modal_subtitle = label(p, "Dust off. There’s more trail ahead.", Vector2(32, 127), 16, MUTED)
	modal_stats = label(p, "", Vector2(32, 184), 22, INK, true)
	modal_action = button(p, "RUN AGAIN    →", Vector2(32, 308), Vector2(399, 62), true)
	modal_action.pressed.connect(func():
		if paused_modal: resume_requested.emit()
		else: start_requested.emit()
	)
	modal_back = button(p, "BACK TO THE VALLEY", Vector2(32, 387), Vector2(399, 43), false)
	modal_back.pressed.connect(func(): menu_requested.emit())

func show_title(best: int) -> void:
	title_group.show()
	play_group.hide()
	modal_group.hide()
	fade.show()
	best_label.text = "PERSONAL BEST  /  %d m" % best if best > 0 else ""

func show_play() -> void:
	title_group.hide()
	modal_group.hide()
	play_group.show()
	fade.hide()

func show_pause(distance: int, carrots: int) -> void:
	paused_modal = true
	title_group.hide()
	play_group.hide()
	modal_group.show()
	fade.show()
	modal_title.text = "EASY, NOW."
	modal_subtitle.text = "The trail will be right here."
	modal_stats.text = "%d m  explored\n%d carrots  collected" % [distance, carrots]
	modal_action.text = "KEEP RUNNING    →"

func show_end(distance: int, carrots: int, best: int) -> void:
	paused_modal = false
	title_group.hide()
	play_group.hide()
	modal_group.show()
	fade.show()
	modal_title.text = "TRAIL'S END."
	modal_subtitle.text = "Dust off. There’s more trail ahead."
	modal_stats.text = "%d m  explored   /   %d carrots\nPersonal best   %d m" % [distance, carrots, best]
	modal_action.text = "RUN AGAIN    →"

func update_run(distance: float, carrots: int, life: int, lane: int, speed: float) -> void:
	distance_label.text = "%04d" % int(distance)
	carrot_label.text = str(carrots)
	for i in 3:
		hearts[i].ink = ORANGE if i < life else Color("d8d1bf")
		hearts[i].queue_redraw()
		lane_marks[i].color = ORANGE if i == lane else Color(PAPER, .6)
	speed_label.text = "%d km/h   /   Leap fences. Find carrots." % int(speed * 3.6)

func feedback(text: String, color := PAPER) -> void:
	feedback_label.text = text
	feedback_label.add_theme_color_override("font_color", color)
	feedback_time = 1.6

func hurt() -> void:
	wash_time = .55
	feedback("WATCH YOUR STEP", Color("f7d39c"))

func set_sound(enabled: bool) -> void:
	sound_button.text = "SOUND  ON" if enabled else "SOUND  OFF"

func group(parent: Node) -> Control:
	var control := Control.new()
	control.size = Vector2(1440, 900)
	control.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(control)
	return control

func label(parent: Node, text: String, pos: Vector2, font_size: int, color := INK, heavy := false) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	if heavy: l.add_theme_font_override("font", bold)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func panel(parent: Node, pos: Vector2, dimensions: Vector2, color: Color, radius: int) -> Panel:
	var p := Panel.new()
	p.position = pos
	p.size = dimensions
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(radius)
	p.add_theme_stylebox_override("panel", style)
	parent.add_child(p)
	return p

func button(parent: Node, text: String, pos: Vector2, dimensions: Vector2, primary: bool) -> Button:
	var b := Button.new()
	b.position = pos
	b.size = dimensions
	b.text = text
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.add_theme_font_override("font", bold)
	b.add_theme_font_size_override("font_size", 16 if primary else 12)
	b.add_theme_color_override("font_color", PAPER if primary else INK)
	b.add_theme_color_override("font_hover_color", PAPER if primary else INK)
	b.add_theme_color_override("font_pressed_color", PAPER if primary else INK)
	b.add_theme_color_override("font_focus_color", PAPER if primary else INK)
	for state in ["normal", "hover", "pressed", "focus"]:
		var style := StyleBoxFlat.new()
		style.bg_color = ORANGE if primary else Color(PAPER, .92)
		if state == "hover": style.bg_color = style.bg_color.lightened(.09)
		if state == "pressed": style.bg_color = style.bg_color.darkened(.1)
		style.set_corner_radius_all(11)
		if state == "focus":
			style.bg_color.a = 0
			style.set_border_width_all(2)
			style.border_color = INK
		b.add_theme_stylebox_override(state, style)
	b.focus_mode = Control.FOCUS_NONE
	parent.add_child(b)
	return b

func keycap(parent: Node, text: String, pos: Vector2, width := 35) -> void:
	var p := panel(parent, pos, Vector2(width, 37), Color(PAPER, .65), 6)
	var style := p.get_theme_stylebox("panel") as StyleBoxFlat
	style.set_border_width_all(1)
	style.border_color = Color(MUTED, .3)
	var l := label(p, text, Vector2.ZERO, 11, INK, true)
	l.size = p.size
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER

func glyph(parent: Node, type: String, pos: Vector2, dimensions: Vector2, color: Color) -> TrailGlyph:
	var g := TrailGlyph.new()
	g.kind = type
	g.ink = color
	g.position = pos
	g.size = dimensions
	g.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(g)
	return g
