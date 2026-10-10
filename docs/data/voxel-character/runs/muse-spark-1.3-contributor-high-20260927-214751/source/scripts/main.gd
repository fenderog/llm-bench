extends Node3D
## Game glue: counts coins, plays a procedurally generated pickup ding
## (no audio assets needed), and resets the sandbox with R.

var total := 0
var collected := 0
var ding: AudioStreamPlayer

@onready var hud := $HUD as SandboxHUD


func _ready() -> void:
	add_to_group("game")
	var coins := get_tree().get_nodes_in_group("coins")
	total = coins.size()
	for c in coins:
		c.connect("picked", _on_coin_picked)
	hud.set_coins(collected, total)
	hud.show_message("Collect all %d coins!" % total, 3.5)
	ding = AudioStreamPlayer.new()
	ding.stream = _make_tone(1174.0, 0.18)
	add_child(ding)


func _on_coin_picked(_coin: Node3D) -> void:
	collected += 1
	hud.set_coins(collected, total)
	ding.pitch_scale = 1.0 + float(collected) * 0.03
	ding.play()
	if collected >= total:
		hud.show_message("All coins collected! Press R to play again.", 8.0)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var k := event as InputEventKey
		if k.pressed and not k.echo and k.physical_keycode == KEY_R:
			get_tree().reload_current_scene()


## Builds a short decaying sine "ding" in memory so the project needs no audio files.
func _make_tone(freq: float, dur: float) -> AudioStreamWAV:
	var rate := 22050
	var frames := int(float(rate) * dur)
	var data := PackedByteArray()
	data.resize(frames)
	for i in range(frames):
		var t := float(i) / float(rate)
		var env := exp(-6.0 * t / dur)
		var s := sin(TAU * freq * t) * 0.7 + sin(TAU * freq * 2.0 * t) * 0.2
		data[i] = int(clampf(128.0 + s * env * 90.0, 0.0, 255.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = rate
	wav.data = data
	return wav
