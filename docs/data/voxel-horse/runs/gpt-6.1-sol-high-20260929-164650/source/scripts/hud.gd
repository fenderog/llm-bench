extends Control

var game: Node3D
var font: Font
var heavy: FontVariation
const INK = Color("293e38")
const MUTED = Color("758075")
const PAPER = Color("f3edda")
const AMBER = Color("be683b")
var ui_scale := Vector2.ONE

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_PASS
	font = ThemeDB.fallback_font
	heavy = FontVariation.new()
	heavy.base_font = font
	heavy.variation_embolden = 0.7

func panel(rect: Rect2, color: Color, radius: int = 12, border: Color = Color.TRANSPARENT) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	if border.a > 0:
		style.border_color = border
		style.set_border_width_all(1)
	style.draw(get_canvas_item(), rect)

func text(value: String, p: Vector2, size: int, color: Color = INK, bold: bool = false) -> void:
	draw_string(heavy if bold else font, p, value, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)

func spaced(value: String, p: Vector2, size: int, color: Color, spacing: float = 2.0) -> void:
	for letter in value:
		text(letter, p, size, color)
		p.x += font.get_string_size(letter, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x + spacing

func center(value: String, x: float, y: float, size: int, color: Color = INK, bold: bool = false) -> void:
	var f: Font = heavy if bold else font
	var w := f.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	text(value, Vector2(x - w / 2, y), size, color, bold)

func keycap(value: String, rect: Rect2, wide: bool = false) -> void:
	panel(rect, Color("e4e3d2"), 7)
	center(value, rect.get_center().x, rect.position.y + (24 if wide else 25), 14, INK, true)

func diamond(p: Vector2, radius: float, color: Color) -> void:
	draw_colored_polygon(PackedVector2Array([p + Vector2(0, -radius), p + Vector2(radius * 0.72, 0), p + Vector2(0, radius), p + Vector2(-radius * 0.72, 0)]), color)

func _draw() -> void:
	if not is_instance_valid(game) or font == null:
		return
	ui_scale = get_viewport_rect().size / Vector2(1440, 900)
	draw_set_transform(Vector2.ZERO, 0, ui_scale)
	# Editorial masthead.
	panel(Rect2(40, 37, 43, 43), INK, 9)
	# A miniature voxel horse mark.
	draw_rect(Rect2(48, 53, 21, 10), PAPER)
	draw_rect(Rect2(65, 46, 7, 14), PAPER)
	draw_rect(Rect2(65, 44, 12, 6), PAPER)
	draw_rect(Rect2(65, 41, 3, 5), PAPER)
	for x in [49, 56, 64]:
		draw_rect(Rect2(x, 62, 3, 9), PAPER)
	draw_rect(Rect2(45, 50, 4, 10), PAPER)
	spaced("FIELD NOTES / 001", Vector2(98, 54), 12, INK, 1.8)
	spaced("A VOXEL ADVENTURE", Vector2(98, 76), 11, INK, 1.4)
	text("COPPER", Vector2(39, 151), 64, INK, true)
	spaced("W I L D   R U N", Vector2(44, 179), 15, INK, 1)
	draw_line(Vector2(43, 204), Vector2(235, 204), Color("89917d"), 1)
	draw_circle(Vector2(49, 227), 4, AMBER)
	spaced("GOLDEN VALLEY", Vector2(63, 232), 12, INK, 1.7)
	text("An endless trail. An untamed spirit.", Vector2(43, 258), 14, Color("536753"))
	# Compact live statistics.
	panel(Rect2(1010, 38, 388, 103), Color(0.95, 0.93, 0.86, 0.92), 12)
	spaced("DISTANCE", Vector2(1032, 65), 10, MUTED, 1.5)
	text("%04d" % int(game.distance), Vector2(1031, 108), 34, INK, true)
	text("m", Vector2(1137, 106), 15, MUTED)
	draw_line(Vector2(1171, 57), Vector2(1171, 122), Color("d7d8c7"), 1)
	spaced("SUNSHARDS", Vector2(1193, 65), 10, MUTED, 1.3)
	diamond(Vector2(1206, 96), 12, AMBER)
	text("%02d" % game.shards, Vector2(1229, 108), 33, INK, true)
	for i in range(3):
		var c: Color = AMBER if i < game.lives else Color("d4d5c6")
		diamond(Vector2(1333 + i * 19, 97), 7, c)
	spaced("SPIRIT", Vector2(1324, 66), 9, MUTED, 0.7)
	panel(Rect2(1273, 155, 58, 33), Color(0.95, 0.93, 0.86, 0.8), 7)
	center("II  P", 1302, 177, 13)
	panel(Rect2(1342, 155, 56, 33), Color(0.95, 0.93, 0.86, 0.8), 7)
	center("♪" if game.sound_on else "× ♪", 1370, 178, 17)
	# A small top-center mode indicator.
	panel(Rect2(624, 40, 192, 33), Color(0.17, 0.24, 0.20, 0.82), 16)
	draw_circle(Vector2(644, 56), 3, Color("d5c17e"))
	spaced("FREE RIDE", Vector2(658, 61), 11, PAPER, 2)
	# Bottom instrument strip.
	panel(Rect2(40, 790, 1358, 75), Color(0.96, 0.94, 0.87, 0.96), 12)
	spaced("PACE", Vector2(62, 815), 10, MUTED, 1.8)
	text("%02d" % int(game.speed * 2.4), Vector2(60, 850), 28, INK, true)
	text("km/h", Vector2(104, 849), 12, MUTED)
	draw_line(Vector2(161, 808), Vector2(161, 848), Color("d1d4c3"), 1)
	spaced("GALLOP" if game.sprint else "STEADY", Vector2(185, 815), 10, AMBER if game.sprint else MUTED, 1.6)
	for i in range(22):
		var c: Color = AMBER if game.sprint else INK
		if float(i) / 22 > game.stamina:
			c = Color("d5d7c8")
		draw_rect(Rect2(186 + i * 6, 828, 3, 18), c)
	text("ENERGY", Vector2(335, 842), 10, MUTED)
	draw_line(Vector2(412, 808), Vector2(412, 848), Color("d1d4c3"), 1)
	keycap("A", Rect2(439, 810, 34, 35))
	keycap("D", Rect2(478, 810, 34, 35))
	text("STEER", Vector2(525, 833), 12, MUTED)
	keycap("SPACE", Rect2(613, 810, 80, 35), true)
	text("JUMP", Vector2(707, 833), 12, MUTED)
	keycap("SHIFT", Rect2(789, 810, 72, 35), true)
	text("SPRINT", Vector2(875, 833), 12, MUTED)
	draw_line(Vector2(963, 808), Vector2(963, 848), Color("d1d4c3"), 1)
	spaced("NEXT MILESTONE", Vector2(986, 815), 10, MUTED, 1.2)
	var progress: float = fmod(game.distance, 500) / 500.0
	panel(Rect2(986, 831, 274, 5), Color("d5d7c8"), 2)
	panel(Rect2(986, 831, maxf(5, 274 * progress), 5), AMBER, 2)
	text("%d m" % ((int(game.distance) / 500 + 1) * 500), Vector2(1273, 839), 15, INK, true)
	# Floating status, out of the horse's silhouette.
	if game.hint_timer > 0 and not game.ended:
		panel(Rect2(467, 735, 506, 36), Color(0.17, 0.24, 0.20, 0.8), 18)
		center(game.hint, 720, 759, 14, PAPER)
	elif game.sprint:
		spaced("LET THE WORLD FALL AWAY", Vector2(550, 759), 12, PAPER, 2)
	text("R  restart", Vector2(43, 886), 11, Color("dde0c9"))
	center("COLLECT SUNSHARDS  ·  CLEAR THE FENCES  ·  KEEP RUNNING", 720, 886, 10, Color("dde0c9"))
	if game.paused or game.ended:
		draw_rect(Rect2(0, 0, 1440, 900), Color(0.1, 0.18, 0.15, 0.45))
		panel(Rect2(470, 280, 500, 324), PAPER, 18)
		spaced("COPPER / FIELD NOTES", Vector2(598, 319), 11, MUTED, 1.6)
		center("A moment of quiet." if game.paused else "A beautiful run.", 720, 386, 36, INK, true)
		center("The valley will be here when you're ready." if game.paused else "%d metres  ·  %d sunshards" % [int(game.distance), game.shards], 720, 427, 17, MUTED)
		if game.ended:
			center("BEST TRAIL   %d m" % game.best, 720, 458, 12, AMBER)
		panel(Rect2(564, 495, 312, 52), INK, 9)
		center("P  /  RESUME" if game.paused and not game.ended else "R  /  RIDE AGAIN", 720, 527, 15, PAPER, true)
		center("A / D  steer     SPACE  jump     SHIFT  sprint", 720, 579, 12, MUTED)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var p: Vector2 = event.position / ui_scale
		if Rect2(1273, 155, 58, 33).has_point(p):
			game.paused = not game.paused
		elif Rect2(1342, 155, 56, 33).has_point(p):
			game.sound_on = not game.sound_on
		elif (game.paused or game.ended) and Rect2(564, 495, 312, 52).has_point(p):
			if game.ended:
				game.restart()
			else:
				game.paused = false
		elif Rect2(439, 810, 34, 35).has_point(p):
			game.lane = maxi(-1, game.lane - 1)
		elif Rect2(478, 810, 34, 35).has_point(p):
			game.lane = mini(1, game.lane + 1)
		elif Rect2(613, 810, 80, 35).has_point(p) and game.jump_y <= 0.01:
			game.jump_v = 9.2
