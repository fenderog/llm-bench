extends "res://scripts/main.gd"
## TEMPORARY capture harness (deleted before finishing).

var _frame := 0
var _jumped_first := false


func _ready() -> void:
	super._ready()
	hurdles._until_next = 5.0


func _process(delta: float) -> void:
	super._process(delta)
	_frame += 1
	if not _jumped_first:
		for h in hurdles._live:
			if h["node"].position.x < 4.3 and h["node"].position.x > 0.0:
				horse.jump()
				_jumped_first = true
	if _frame == 300:
		_change_gait(-1)
	if _frame == 420:
		_change_gait(-1)
