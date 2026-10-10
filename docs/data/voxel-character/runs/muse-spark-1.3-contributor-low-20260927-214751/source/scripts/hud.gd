extends CanvasLayer
## HUD: gem counter, timer, speed readout, win panel.

@onready var _top: Label = $TopBar
@onready var _timer: Label = $TimerLabel
@onready var _speed: Label = $SpeedLabel
@onready var _win: PanelContainer = $WinPanel
@onready var _win_text: Label = $WinPanel/WinText


func set_gems(got: int, total: int) -> void:
	_top.text = "💎 Gems: %d / %d" % [got, total]


func set_time(t: float, best: float) -> void:
	var b := "--" if best < 0.0 else "%.1fs" % best
	_timer.text = "Time: %.1fs   Best: %s" % [t, b]


func set_speed(s: float, sprinting: bool) -> void:
	_speed.text = ("⚡ %.1f (sprint)" % s) if sprinting else ("Speed: %.1f" % s)


func show_win(t: float, best: float) -> void:
	_win.visible = true
	_win_text.text = "🎉 All gems collected in %.1fs!\nBest: %.1fs — press R to run again" % [t, best]


func hide_win() -> void:
	_win.visible = false
