class_name VoxelSfx
extends RefCounted
## Procedural retro sound effects (no audio files needed).
## Generates tiny 8-bit PCM WAV streams at runtime.


static func tone(f0: float, f1: float, dur: float, vol: float = 0.5, rate: int = 22050) -> AudioStreamWAV:
	var n := int(rate * dur)
	var data := PackedByteArray()
	data.resize(n)
	var phase := 0.0
	for i in range(n):
		var t := float(i) / float(maxi(n - 1, 1))
		var f := lerpf(f0, f1, t)
		phase += TAU * f / float(rate)
		var env := (1.0 - t) * (1.0 - t)
		var s := sin(phase) * env * vol
		data[i] = int(clampf(s * 127.0 + 128.0, 0.0, 255.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = rate
	wav.stereo = false
	wav.data = data
	return wav


static func arpeggio(freqs: Array, note_dur: float, vol: float = 0.5, rate: int = 22050) -> AudioStreamWAV:
	var per := int(rate * note_dur)
	var data := PackedByteArray()
	data.resize(per * freqs.size())
	for idx in range(freqs.size()):
		var f := float(freqs[idx])
		var phase := 0.0
		for i in range(per):
			var t := float(i) / float(maxi(per - 1, 1))
			phase += TAU * f / float(rate)
			var env := 1.0 - t
			var s := sin(phase) * env * vol
			data[idx * per + i] = int(clampf(s * 127.0 + 128.0, 0.0, 255.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = rate
	wav.stereo = false
	wav.data = data
	return wav
