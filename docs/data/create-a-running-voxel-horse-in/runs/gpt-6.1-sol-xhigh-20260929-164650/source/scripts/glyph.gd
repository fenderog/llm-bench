extends Control
class_name TrailGlyph

var kind := "heart"
var ink := Color("c77946")

func _draw() -> void:
	var s := size / 32.0
	if kind == "heart":
		var points := PackedVector2Array([Vector2(3, 8), Vector2(7, 4), Vector2(13, 4), Vector2(16, 8), Vector2(19, 4), Vector2(25, 4), Vector2(29, 8), Vector2(29, 16), Vector2(16, 29), Vector2(3, 16)])
		for i in points.size():
			points[i] *= s
		draw_colored_polygon(points, ink)
	elif kind == "carrot":
		draw_colored_polygon(PackedVector2Array([Vector2(8, 12) * s, Vector2(23, 10) * s, Vector2(19, 22) * s, Vector2(8, 31) * s]), ink)
		draw_rect(Rect2(Vector2(13, 2) * s, Vector2(5, 10) * s), Color("74915f"))
		draw_rect(Rect2(Vector2(19, 4) * s, Vector2(7, 5) * s), Color("88a26b"))
		draw_line(Vector2(10, 19) * s, Vector2(15, 21) * s, Color("e4a361"), 2.0 * s.x)
	elif kind == "horse":
		draw_rect(Rect2(Vector2(2, 13) * s, Vector2(18, 9) * s), ink)
		draw_rect(Rect2(Vector2(17, 7) * s, Vector2(7, 13) * s), ink)
		draw_rect(Rect2(Vector2(20, 5) * s, Vector2(10, 7) * s), ink)
		draw_rect(Rect2(Vector2(21, 2) * s, Vector2(3, 6) * s), ink)
		draw_rect(Rect2(Vector2(4, 20) * s, Vector2(4, 10) * s), ink)
		draw_rect(Rect2(Vector2(15, 20) * s, Vector2(4, 10) * s), ink)
		draw_rect(Rect2(Vector2(0, 12) * s, Vector2(3, 11) * s), ink)
		draw_rect(Rect2(Vector2(25, 7) * s, Vector2(2, 2) * s), Color("f7efd9"))
