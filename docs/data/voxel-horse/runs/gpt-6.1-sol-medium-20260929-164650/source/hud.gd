extends Control

var game: Node3D
var font = ThemeDB.fallback_font
var ink = Color("303e3c")
var cream = Color("fff1d6")
var muted = Color("68776b")
var unit = 1.0
var origin = Vector2.ZERO
var button = Rect2(990, 625, 242, 54)
var left_button = Rect2(48, 625, 66, 54)
var right_button = Rect2(125, 625, 66, 54)
var jump_button = Rect2(212, 625, 126, 54)

func _ready() -> void:
	game = get_tree().current_scene

func _process(_delta: float) -> void:
	queue_redraw()

func text(value: String, pos: Vector2, size_px: int, color: Color = ink) -> void:
	draw_string(font, pos, value, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, color)

func panel(rect: Rect2, color: Color, radius: int = 8) -> void:
	var style = StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	draw_style_box(style, rect)

func _draw() -> void:
	if not is_instance_valid(game):
		return
	unit = minf(size.x / 1280.0, size.y / 720.0)
	origin = (size - Vector2(1280, 720) * unit) * 0.5
	draw_set_transform(origin, 0, Vector2.ONE * unit)
	text("D U S T  &  T H U N D E R", Vector2(48, 58), 30)
	text("A  V O X E L  T R A I L  R U N N E R", Vector2(50, 83), 12, muted)
	draw_line(Vector2(48, 103), Vector2(383, 103), Color("8eaa98"), 1)
	panel(Rect2(540, 34, 200, 36), Color("e8e6c8"), 18)
	draw_circle(Vector2(562, 52), 4, Color("608975"))
	text("01   /   COPPER CANYON", Vector2(576, 57), 12)
	panel(Rect2(990, 32, 242, 110), Color(0.98, 0.95, 0.84, 0.92))
	text("DISTANCE", Vector2(1008, 57), 11, muted)
	text("%04d" % int(game.distance), Vector2(1008, 99), 38)
	text("m", Vector2(1116, 99), 16, muted)
	draw_line(Vector2(1008, 111), Vector2(1214, 111), Color("d6d5b9"))
	text("BEST  %04d m" % int(game.best), Vector2(1008, 130), 11, muted)
	text("%02d  /  SHOES" % game.carrots, Vector2(1140, 130), 11)
	if not game.active and not game.crashed:
		text("WILD HEART.", Vector2(48, 155), 28)
		text("OPEN TRAIL.", Vector2(48, 188), 28)
		text("Find your rhythm. Leave the dust behind.", Vector2(50, 219), 14, muted)
		text("Dodge the rails and gather golden horseshoes.", Vector2(50, 242), 14, muted)
	elif game.active:
		text("GALLOPING  /  %02d km/h" % int(game.speed * 3.6), Vector2(50, 134), 12, muted)
		text("JUMP THE RAILS. CHASE THE GOLD.", Vector2(50, 155), 11, muted)
	# Minimal compass / trail signature.
	text("N", Vector2(1202, 197), 13, muted)
	draw_line(Vector2(1207, 207), Vector2(1207, 240), muted, 1)
	draw_colored_polygon(PackedVector2Array([Vector2(1207, 201), Vector2(1201, 213), Vector2(1213, 213)]), ink)
	if game.crashed or game.paused:
		panel(Rect2(442, 257, 396, 180), Color(0.14, 0.23, 0.22, 0.95), 12)
		text("TRAIL PAUSED" if game.paused else "BACK IN THE SADDLE", Vector2(474, 302), 24, cream)
		text("Take a breath. The canyon can wait." if game.paused else "Every great run starts with another try.", Vector2(474, 338), 14, Color("b9c5ae"))
		text("P / ESC  to resume" if game.paused else "%d METERS    /    %d HORSESHOES" % [int(game.distance), game.carrots], Vector2(474, 372), 14, cream)
		text("" if game.paused else "SPACE or R  to ride again", Vector2(474, 407), 13, Color("e7bb7c"))
	# Bottom instrument strip.
	panel(Rect2(32, 605, 1216, 91), Color("2f4541"), 12)
	panel(left_button, Color("49615a"), 6)
	panel(right_button, Color("49615a"), 6)
	panel(jump_button, Color("49615a"), 6)
	text("←", Vector2(68, 661), 26, cream)
	text("→", Vector2(145, 661), 26, cream)
	text("↑  JUMP", Vector2(231, 660), 17, cream)
	text("A / D   SWITCH LANES", Vector2(365, 644), 12, cream)
	text("SPACE   JUMP     •     P   PAUSE", Vector2(365, 668), 11, Color("b7c4ad"))
	text("TRAIL RHYTHM", Vector2(669, 641), 11, Color("b7c4ad"))
	for i in range(3):
		panel(Rect2(670 + i * 58, 653, 47, 7), Color("eac286") if game.lane == i - 1 else Color("61766a"), 3)
	panel(button, Color("eac286"), 6)
	var action = "RIDE THE TRAIL  →"
	if game.crashed:
		action = "RIDE AGAIN  →"
	elif game.active:
		action = "RESUME  →" if game.paused else "PAUSE  / /"
	text(action, Vector2(1012, 659), 17, ink)
	if game.flash > 0 and not game.crashed:
		text("+1  GOLDEN SHOE", Vector2(540, 547), 20, cream)
	draw_set_transform(Vector2.ZERO, 0, Vector2.ONE)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var point = (event.position - origin) / unit
		if button.has_point(point):
			if not game.active:
				game.start()
			else:
				game.paused = not game.paused
		elif left_button.has_point(point) and game.active:
			game.lane = maxi(-1, game.lane - 1)
		elif right_button.has_point(point) and game.active:
			game.lane = mini(1, game.lane + 1)
		elif jump_button.has_point(point):
			game.jump()
