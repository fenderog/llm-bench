extends Node
class_name TrailAudio

var enabled := true
var sounds: Dictionary = {}
var players: Array[AudioStreamPlayer] = []
var next_player := 0
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	rng.seed = 505
	for kind in ["hoof", "carrot", "jump", "hit", "start"]:
		sounds[kind] = make_sound(kind)
	for i in 8:
		var player := AudioStreamPlayer.new()
		add_child(player)
		players.append(player)

func play(kind: String, volume := -14.0, pitch := 1.0) -> void:
	if not enabled: return
	var player := players[next_player]
	next_player = (next_player + 1) % players.size()
	player.stream = sounds[kind]
	player.volume_db = volume
	player.pitch_scale = pitch
	player.play()

func stop_all() -> void:
	for player in players:
		player.stop()
		player.stream = null

func _exit_tree() -> void:
	stop_all()

func make_sound(kind: String) -> AudioStreamWAV:
	var rate := 22050
	var duration := .12 if kind == "hoof" else .32
	if kind == "start": duration = .65
	if kind == "hit": duration = .4
	var samples := int(duration * rate)
	var bytes := PackedByteArray()
	bytes.resize(samples * 2)
	for i in samples:
		var t := float(i) / rate
		var progress := t / duration
		var envelope := sin(minf(t * 90.0, PI / 2)) * pow(1.0 - progress, 2.2)
		var wave := 0.0
		match kind:
			"hoof":
				wave = sin(TAU * (125 * t - 170 * t * t)) * .6 + rng.randf_range(-1, 1) * exp(-t * 65) * .5
			"carrot":
				var frequency := 880.0 if t < .12 else 1320.0
				wave = sin(TAU * frequency * t) * .55 + sin(TAU * frequency * 2 * t) * .13
			"jump":
				wave = sin(TAU * (260 * t + 470 * t * t)) * .4 + rng.randf_range(-.08, .08)
			"hit":
				wave = sin(TAU * (100 * t - 65 * t * t)) * .6 + rng.randf_range(-.4, .4) * (1 - progress)
			"start":
				var notes := [330.0, 440.0, 554.37, 660.0]
				var frequency: float = notes[mini(3, int(progress * 4))]
				wave = sin(TAU * frequency * t) * .35 + sin(TAU * frequency * 2 * t) * .1
		bytes.encode_s16(i * 2, int(clampf(wave * envelope, -1, 1) * 32767))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.data = bytes
	return stream
