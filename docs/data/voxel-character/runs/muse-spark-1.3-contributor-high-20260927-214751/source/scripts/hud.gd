class_name SandboxHUD
extends CanvasLayer
## Tiny HUD: coin counter, timed center messages. All labels live in main.tscn.

@onready var coins_label := $CoinsLabel as Label
@onready var msg := $MessageLabel as Label

var msg_left := 0.0


func set_coins(n: int, total: int) -> void:
	coins_label.text = "Coins: %d / %d" % [n, total]


func show_message(text: String, dur := 3.0) -> void:
	msg.text = text
	msg.visible = true
	msg_left = dur


func _process(delta: float) -> void:
	if msg_left > 0.0:
		msg_left -= delta
		if msg_left <= 0.0:
			msg.visible = false
