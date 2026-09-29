extends Node
## Procedurally synthesised hoof clops and a wind loop, so the project needs
## no audio files. Uses AudioStreamWAV, which plays fine on single-threaded web.

const RATE := 22050

var _clops: Array[AudioStreamWAV] = []
var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _wind: AudioStreamPlayer
var _wind_db := -60.0


func _ready() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	for i in 3:
		_clops.append(_make_clop(rng, 0.85 + i * 0.15))
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)
	_wind = AudioStreamPlayer.new()
	_wind.stream = _make_wind(rng)
	_wind.volume_db = _wind_db
	add_child(_wind)
	_wind.play()


func _exit_tree() -> void:
	_wind.stop()
	for p in _players:
		p.stop()


func play_clop(strength: float) -> void:
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = _clops[randi() % _clops.size()]
	p.pitch_scale = randf_range(0.85, 1.15)
	p.volume_db = linear_to_db(clampf(0.3 * strength, 0.05, 1.0))
	p.play()


## Wind rush grows with speed.
func set_speed(speed: float, delta: float) -> void:
	var target := lerpf(-38.0, -14.0, clampf(speed / 16.0, 0.0, 1.0))
	_wind_db = lerpf(_wind_db, target, 1.0 - exp(-3.0 * delta))
	_wind.volume_db = _wind_db


func toggle_mute() -> bool:
	var muted := not AudioServer.is_bus_mute(0)
	AudioServer.set_bus_mute(0, muted)
	return muted


func _make_clop(rng: RandomNumberGenerator, tone: float) -> AudioStreamWAV:
	var n := int(RATE * 0.12)
	var data := PackedByteArray()
	data.resize(n * 2)
	var lp := 0.0
	for i in n:
		var t := float(i) / RATE
		lp += (rng.randf_range(-1.0, 1.0) - lp) * 0.3
		var knock := lp * exp(-t * 60.0) * 1.2
		var thump := sin(TAU * 130.0 * tone * t) * exp(-t * 32.0)
		var click := sin(TAU * 820.0 * tone * t) * exp(-t * 140.0) * 0.35
		var s := clampf((knock + thump + click) * 0.7, -1.0, 1.0)
		data.encode_s16(i * 2, int(s * 32000.0))
	return _wav(data, false)


func _make_wind(rng: RandomNumberGenerator) -> AudioStreamWAV:
	var seconds := 4.0
	var n := int(RATE * seconds)
	var data := PackedByteArray()
	data.resize(n * 2)
	var lp1 := 0.0
	var lp2 := 0.0
	for i in n:
		var t := float(i) / RATE
		lp1 += (rng.randf_range(-1.0, 1.0) - lp1) * 0.08
		lp2 += (lp1 - lp2) * 0.08
		# Whole-number cycles over the loop so the gusts wrap seamlessly.
		var gust := 0.65 + 0.35 * sin(TAU * t * 2.0 / seconds) * sin(TAU * t * 3.0 / seconds)
		data.encode_s16(i * 2, int(clampf(lp2 * 4.0 * gust, -1.0, 1.0) * 30000.0))
	return _wav(data, true)


func _wav(data: PackedByteArray, loop: bool) -> AudioStreamWAV:
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.stereo = false
	wav.data = data
	if loop:
		wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
		wav.loop_begin = 0
		wav.loop_end = data.size() / 2
	return wav
