extends Node3D

const HUD_SCRIPT = preload("res://scripts/hud.gd")
var rng := RandomNumberGenerator.new()
var mats: Dictionary = {}
var horse: Node3D
var torso: Node3D
var neck: Node3D
var tail: Node3D
var legs: Array[Node3D] = []
var knees: Array[Node3D] = []
var scenery: Array[Node3D] = []
var objects: Array[Node3D] = []
var dust: Array[Node3D] = []
var camera: Camera3D
var hud: Control
var lane := 0
var speed := 12.0
var distance := 0.0
var shards := 0
var lives := 3
var phase := 0.0
var jump_y := 0.0
var jump_v := 0.0
var spawn_clock := 0.0
var dust_clock := 0.0
var invincible := 0.0
var paused := false
var ended := false
var sprint := false
var stamina := 1.0
var best := 0
var sound_on := true
var sound_player: AudioStreamPlayer
var sound_phase := 0.0
var hoof_clock := 0.0
var hint := "Follow the trail. Find your rhythm."
var hint_timer := 6.0

func material(hex: String, rough: float = 1.0) -> StandardMaterial3D:
	if mats.has(hex):
		return mats[hex]
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(hex)
	m.roughness = rough
	mats[hex] = m
	return m

func block(parent: Node3D, pos: Vector3, size: Vector3, color: String) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.material_override = material(color)
	node.position = pos
	parent.add_child(node)
	return node

func _ready() -> void:
	rng.seed = 24719
	make_environment()
	make_landscape()
	make_horse()
	camera = Camera3D.new()
	camera.position = Vector3(8.2, 5.4, 9.6)
	add_child(camera)
	camera.look_at(Vector3(0, 2.1, -3.0))
	camera.fov = 50
	camera.current = true
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Control.new()
	hud.set_script(HUD_SCRIPT)
	hud.game = self
	hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layer.add_child(hud)
	setup_audio()
	spawn_pattern(-31, 0)
	spawn_pattern(-55, 1)

func make_environment() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ShaderMaterial.new()
	sm.shader = preload("res://shaders/valley_sky.gdshader")
	sky.sky_material = sm
	e.sky = sky
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color("d7e5e8")
	e.ambient_light_energy = 0.4
	e.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	e.tonemap_exposure = 0.8
	e.fog_enabled = true
	e.fog_light_color = Color("e0d6b2")
	e.fog_density = 0.0038
	e.fog_sky_affect = 0.15
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, -32, 0)
	sun.light_color = Color("fff4e5")
	sun.light_energy = 0.65
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 85
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	add_child(sun)

func make_landscape() -> void:
	block(self, Vector3(0, -0.65, -65), Vector3(230, 1, 240), "8a9a64")
	block(self, Vector3(0, -0.13, -55), Vector3(8.7, 0.23, 180), "c4b486")
	block(self, Vector3(29, -0.27, -60), Vector3(15, 0.15, 200), "709fa1")
	block(self, Vector3(23, -0.21, -60), Vector3(2, 0.2, 200), "b7b486")
	# Terraced, deliberately blocky silhouettes on the skyline.
	for i in range(24):
		var x := -105.0 + i * 9.0
		var height := rng.randf_range(8, 19)
		var base := Vector3(x, 0, -110 - rng.randf_range(0, 22))
		for tier in range(5):
			var width := 18.0 - tier * 2.6
			var col: String = ["799393", "89a09a", "98aca0", "a7b7a7", "b8c2b2"][tier]
			block(self, base + Vector3(0, height * (float(tier) + 0.5) / 5.0, 0), Vector3(width, height / 5.0, width), col)
	# Soft voxel clouds and a warm, low sun frame the distant valley.
	for i in range(6):
		var cloud_pos := Vector3(-92 + i * 22, 19 + (i % 3) * 3, -95 - (i % 2) * 15)
		block(self, cloud_pos, Vector3(13, 1.1, 3.4), "ede9d7")
		block(self, cloud_pos + Vector3(-2, 1.0, 0), Vector3(6, 1.1, 3), "ede9d7")
	var sun_mesh := SphereMesh.new()
	sun_mesh.radius = 3.7
	sun_mesh.height = 7.4
	sun_mesh.radial_segments = 32
	sun_mesh.rings = 12
	var sun_disc := MeshInstance3D.new()
	sun_disc.mesh = sun_mesh
	var sun_mat := StandardMaterial3D.new()
	sun_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sun_mat.albedo_color = Color("fff0b4")
	sun_disc.material_override = sun_mat
	sun_disc.position = Vector3(-47, 28, -105)
	sun_disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sun_disc)
	# Recycled landscape strips keep the world endless.
	for i in range(20):
		var chunk := Node3D.new()
		chunk.position.z = 24.0 - i * 8.0
		add_child(chunk)
		scenery.append(chunk)
		for side in [-1, 1]:
			for j in range(2):
				var x: float = side * rng.randf_range(8.4, 20.0)
				var z := rng.randf_range(-3.6, 3.6)
				if rng.randf() > 0.3:
					make_tree(chunk, Vector3(x, 0, z), rng.randf_range(0.7, 1.5))
				else:
					make_rock(chunk, Vector3(x, 0, z))
			for j in range(10):
				var x: float = side * rng.randf_range(4.8, 21.0)
				var p := Vector3(x, 0.13, rng.randf_range(-4, 4))
				block(chunk, p, Vector3(0.13, rng.randf_range(0.25, 0.55), 0.13), ["6e854f", "879448", "a3a557"][rng.randi_range(0, 2)])
				if j % 3 == 0:
					block(chunk, p + Vector3(0, 0.28, 0), Vector3(0.23, 0.14, 0.23), "f1cf73")
			for j in range(4):
				block(chunk, Vector3(side * 4.45, 0.04, j * 2 - 3), Vector3(0.2, 0.12, 0.75), "e0d2a5")
		for divider in [-1.2, 1.2]:
			for mark in range(2):
				block(chunk, Vector3(divider, 0.018, mark * 4 - 2), Vector3(0.035, 0.018, 1.7), "b9ac83")
		for j in range(7):
			block(chunk, Vector3(rng.randf_range(-3.9, 3.9), 0.008, rng.randf_range(-4, 4)), Vector3(rng.randf_range(0.2, 0.8), 0.016, rng.randf_range(0.3, 1.3)), ["b5a77c", "d0be8c", "cabc92"][j % 3])
		# Telegraph poles and fence posts provide a strong sense of motion.
		if i % 2 == 0:
			for side in [-1, 1]:
				block(chunk, Vector3(side * 5.4, 0.55, 0), Vector3(0.19, 1.1, 0.19), "817052")
				block(chunk, Vector3(side * 5.4, 0.8, 0), Vector3(0.13, 0.12, 7.5), "a9956b")
				block(chunk, Vector3(side * 5.4, 0.4, 0), Vector3(0.13, 0.12, 7.5), "a9956b")

func make_tree(parent: Node3D, p: Vector3, size: float) -> void:
	var t := Node3D.new()
	t.position = p
	t.scale = Vector3.ONE * size
	parent.add_child(t)
	block(t, Vector3(0, 1.15, 0), Vector3(0.35, 2.3, 0.35), "77664b")
	var c: String = ["687d4a", "7c8a4e", "899652", "9a9c55"][rng.randi_range(0, 3)]
	block(t, Vector3(0, 2.35, 0), Vector3(2.25, 1.1, 2.05), c)
	block(t, Vector3(-0.25, 3.14, 0.14), Vector3(1.65, 0.8, 1.6), c)
	block(t, Vector3(0.15, 3.7, 0), Vector3(0.9, 0.4, 0.95), "a2ab62")
	block(t, Vector3(0.95, 2.1, 0.35), Vector3(0.6, 0.7, 1.0), c)

func make_rock(parent: Node3D, p: Vector3) -> void:
	block(parent, p + Vector3(0, 0.26, 0), Vector3(1.3, 0.65, 1), "939887")
	block(parent, p + Vector3(-0.15, 0.65, 0), Vector3(0.8, 0.3, 0.65), "b0b19a")

func make_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	torso = Node3D.new()
	horse.add_child(torso)
	# Chestnut body: stepped silhouette, with individual coat voxels.
	block(torso, Vector3(0, 2.36, 0), Vector3(1.02, 0.92, 1.94), "a7522b")
	block(torso, Vector3(0, 2.84, 0.04), Vector3(0.82, 0.22, 1.7), "c8783f")
	block(torso, Vector3(0, 1.91, 0), Vector3(0.74, 0.24, 1.55), "8e4328")
	block(torso, Vector3(0, 2.42, -0.91), Vector3(0.9, 0.86, 0.42), "b66333")
	block(torso, Vector3(0, 2.43, 0.82), Vector3(1.1, 0.87, 0.48), "b96134")
	for side in [-1, 1]:
		for i in range(15):
			block(torso, Vector3(side * 0.519, 2.07 + (i % 3) * 0.235, -0.75 + floori(i / 3.0) * 0.33), Vector3(0.022, 0.22, 0.31), ["a9532c", "b45c2f", "bd6837", "ad572d", "a04c29"][i % 5])
	# A slim saddle blanket and leather tack.
	block(torso, Vector3(0, 2.98, 0.19), Vector3(0.84, 0.12, 0.88), "ded4ad")
	block(torso, Vector3(0, 3.07, 0.23), Vector3(0.62, 0.12, 0.7), "354d49")
	for side in [-1, 1]:
		block(torso, Vector3(side * 0.54, 2.61, 0.2), Vector3(0.055, 0.57, 0.79), "354d49")
		block(torso, Vector3(side * 0.576, 2.34, 0.2), Vector3(0.025, 0.08, 0.8), "e2bc6c")
		block(torso, Vector3(side * 0.56, 2.34, -0.15), Vector3(0.07, 0.68, 0.1), "62452f")
		block(torso, Vector3(side * 0.6, 2.0, -0.15), Vector3(0.11, 0.15, 0.18), "d2ad67")
	neck = Node3D.new()
	neck.position = Vector3(0, 2.58, -0.82)
	torso.add_child(neck)
	block(neck, Vector3(0, 0.39, -0.22), Vector3(0.68, 0.85, 0.69), "b76333")
	block(neck, Vector3(0, 0.87, -0.45), Vector3(0.53, 0.61, 0.54), "c0713b")
	block(neck, Vector3(0, 1.18, -0.65), Vector3(0.59, 0.56, 0.71), "bc6a37")
	block(neck, Vector3(0, 0.99, -1.05), Vector3(0.51, 0.39, 0.49), "c77e47")
	block(neck, Vector3(0, 0.92, -1.32), Vector3(0.5, 0.3, 0.21), "694638")
	# White blaze, eyes, nostrils and upright voxel ears.
	block(neck, Vector3(0, 1.23, -1.015), Vector3(0.14, 0.4, 0.035), "f0dfb4")
	block(neck, Vector3(0, 1.09, -1.29), Vector3(0.16, 0.16, 0.035), "f0dfb4")
	for side in [-1, 1]:
		block(neck, Vector3(side * 0.3, 1.25, -0.79), Vector3(0.04, 0.105, 0.12), "262d29")
		block(neck, Vector3(side * 0.325, 1.28, -0.815), Vector3(0.02, 0.03, 0.03), "fff0ca")
		block(neck, Vector3(side * 0.258, 0.98, -1.31), Vector3(0.023, 0.07, 0.1), "2f2b27")
		var ear := block(neck, Vector3(side * 0.22, 1.57, -0.55), Vector3(0.18, 0.27, 0.22), "a9522c")
		ear.rotation.z = side * -0.13
		block(neck, Vector3(side * 0.22, 1.6, -0.67), Vector3(0.09, 0.15, 0.025), "db9865")
		block(neck, Vector3(side * 0.28, 1.06, -1.15), Vector3(0.04, 0.11, 0.21), "4e4030")
		block(neck, Vector3(side * 0.31, 1.16, -0.5), Vector3(0.04, 0.42, 0.09), "4e4030")
	for i in range(7):
		block(neck, Vector3(0, 0.16 + i * 0.2, 0.13 - i * 0.085), Vector3(0.26, 0.25, 0.27), "3d352b")
	block(neck, Vector3(0, 1.49, -0.79), Vector3(0.27, 0.17, 0.43), "3d352b")
	for i in range(4):
		var front := i < 2
		var leg := Node3D.new()
		leg.position = Vector3(-0.4 if i % 2 == 0 else 0.4, 2.15, -0.76 if front else 0.76)
		torso.add_child(leg)
		legs.append(leg)
		block(leg, Vector3(0, -0.29, 0), Vector3(0.3, 0.69, 0.34), "a8552d")
		block(leg, Vector3(0, -0.64, 0), Vector3(0.25, 0.2, 0.27), "874129")
		var knee := Node3D.new()
		knee.position.y = -0.66
		leg.add_child(knee)
		knees.append(knee)
		block(knee, Vector3(0, -0.36, 0), Vector3(0.19, 0.73, 0.21), "bf7847")
		block(knee, Vector3(0, -0.87, 0), Vector3(0.22, 0.36, 0.25), "ecdbb5")
		block(knee, Vector3(0, -1.1, -0.055), Vector3(0.29, 0.2, 0.37), "393830")
	tail = Node3D.new()
	tail.position = Vector3(0, 2.66, 1.05)
	torso.add_child(tail)
	for i in range(5):
		block(tail, Vector3(0, -i * 0.23, 0.17 + i * 0.18), Vector3(0.29 - i * 0.022, 0.34, 0.38), "3d352b")

func spawn_pattern(z: float, pattern: int = -1) -> void:
	if pattern < 0:
		pattern = rng.randi_range(0, 3)
	var open_lane := rng.randi_range(-1, 1)
	if pattern == 0:
		open_lane = 0
	for i in range(4):
		spawn_shard(Vector3(open_lane * 2.4, 1.5, z - i * 2.4))
	if pattern > 0:
		var obstacle_lane := rng.randi_range(-1, 1)
		if pattern == 2:
			obstacle_lane = open_lane
		spawn_obstacle(Vector3(obstacle_lane * 2.4, 0, z - 11), pattern == 3)

func spawn_shard(pos: Vector3) -> void:
	var obj := Node3D.new()
	obj.position = pos
	obj.set_meta("kind", "shard")
	obj.set_meta("origin_y", pos.y)
	add_child(obj)
	objects.append(obj)
	var crystal := block(obj, Vector3.ZERO, Vector3(0.34, 0.45, 0.34), "ffda74")
	crystal.rotation_degrees = Vector3(0, 45, 35)
	block(obj, Vector3(0, 0.42, 0), Vector3(0.07, 0.13, 0.07), "fff1bf")
	var halo := TorusMesh.new()
	halo.inner_radius = 0.43
	halo.outer_radius = 0.47
	halo.rings = 16
	halo.ring_segments = 6
	var ring := MeshInstance3D.new()
	ring.mesh = halo
	ring.material_override = material("edc166")
	ring.rotation_degrees.x = 90
	obj.add_child(ring)

func spawn_obstacle(pos: Vector3, rock: bool) -> void:
	var obj := Node3D.new()
	obj.position = pos
	obj.set_meta("kind", "obstacle")
	add_child(obj)
	objects.append(obj)
	if rock:
		block(obj, Vector3(0, 0.46, 0), Vector3(1.7, 0.92, 1.3), "7f8877")
		block(obj, Vector3(-0.18, 1.02, 0.12), Vector3(1.1, 0.25, 0.9), "a2a78f")
	else:
		for side in [-1, 1]:
			block(obj, Vector3(side * 0.87, 0.61, 0), Vector3(0.17, 1.22, 0.21), "675740")
		block(obj, Vector3(0, 0.73, 0), Vector3(2, 0.38, 0.35), "aa7944")
		block(obj, Vector3(0, 0.94, 0), Vector3(2.04, 0.07, 0.4), "d4b36e")
		for i in range(5):
			var stripe := block(obj, Vector3(-0.76 + i * 0.38, 0.74, 0.185), Vector3(0.13, 0.28, 0.025), "e8c87c")
			stripe.rotation.z = -0.35

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_A, KEY_LEFT:
				lane = maxi(-1, lane - 1)
			KEY_D, KEY_RIGHT:
				lane = mini(1, lane + 1)
			KEY_SPACE, KEY_W, KEY_UP:
				if jump_y <= 0.01 and not paused and not ended:
					jump_v = 9.2
			KEY_P, KEY_ESCAPE:
				paused = not paused
			KEY_R:
				restart()
			KEY_M:
				sound_on = not sound_on

func restart() -> void:
	best = maxi(best, int(distance))
	distance = 0
	shards = 0
	lives = 3
	lane = 0
	jump_y = 0
	jump_v = 0
	stamina = 1
	invincible = 2
	ended = false
	paused = false
	spawn_clock = 0
	for obj in objects:
		obj.queue_free()
	objects.clear()
	hint = "A fresh trail. A little farther this time."
	hint_timer = 4
	spawn_pattern(-35, 0)

func _process(delta: float) -> void:
	hud.queue_redraw()
	if paused or ended:
		return
	sprint = Input.is_physical_key_pressed(KEY_SHIFT) and stamina > 0.03
	stamina = clampf(stamina + delta * (-0.23 if sprint else 0.13), 0, 1)
	speed = lerpf(speed, (19.5 if sprint else 12.0) if invincible <= 0 else 8.0, delta * 3)
	distance += speed * delta
	phase += delta * speed * 0.8
	invincible = maxf(0, invincible - delta)
	hint_timer = maxf(0, hint_timer - delta)
	jump_v -= delta * 21
	jump_y = maxf(0, jump_y + jump_v * delta)
	if jump_y <= 0:
		jump_v = maxf(0, jump_v)
	horse.position.x = lerpf(horse.position.x, lane * 2.4, 1 - exp(-delta * 9))
	horse.position.y = jump_y
	horse.rotation.z = lerpf(horse.rotation.z, -(lane * 2.4 - horse.position.x) * 0.07, delta * 7)
	torso.position.y = 0.11 + sin(phase * 2) * 0.085
	torso.rotation.x = cos(phase) * 0.035
	neck.rotation.x = -0.2 + sin(phase + 0.4) * 0.06
	tail.rotation.x = sin(phase - 0.7) * 0.16 - 0.2
	tail.rotation.z = sin(phase * 0.55) * 0.12
	for i in range(4):
		var offset: float = [0.0, 0.65, 2.8, 3.4][i]
		legs[i].rotation.x = sin(phase + offset) * 0.72
		knees[i].rotation.x = maxf(0, cos(phase + offset + 0.7)) * 1.1
		if jump_y > 0.2:
			legs[i].rotation.x = lerpf(legs[i].rotation.x, -0.65 if i < 2 else 0.7, minf(1, jump_y))
			knees[i].rotation.x = 0.9
	for chunk in scenery:
		chunk.position.z += speed * delta
		if chunk.position.z > 32:
			chunk.position.z -= 160
	for obj in objects.duplicate():
		obj.position.z += speed * delta
		var is_shard: bool = obj.get_meta("kind") == "shard"
		if is_shard:
			obj.rotation.y += delta * 1.6
			obj.position.y = float(obj.get_meta("origin_y")) + sin(phase * 0.3 + obj.position.z) * 0.12
		if absf(obj.position.z) < 0.85 and absf(obj.position.x - horse.position.x) < 0.95:
			if is_shard and jump_y < 2.0:
				shards += 1
				chime()
				objects.erase(obj)
				obj.queue_free()
				continue
			elif not is_shard and jump_y < 1.05 and invincible <= 0:
				lives -= 1
				invincible = 2.2
				hint = "Easy, Copper! Jump or take another lane."
				hint_timer = 3
				if lives <= 0:
					ended = true
					best = maxi(best, int(distance))
		if obj.position.z > 19:
			objects.erase(obj)
			obj.queue_free()
	spawn_clock += delta * speed
	if spawn_clock > 29:
		spawn_clock = 0
		spawn_pattern(-85)
	update_dust(delta)
	var target_pos := Vector3(8.2 + horse.position.x * 0.15, 5.4 + jump_y * 0.25, 9.6)
	camera.position = camera.position.lerp(target_pos, delta * 3)
	camera.look_at(Vector3(horse.position.x * 0.25, 2.1 + jump_y * 0.18, -3.0))
	camera.fov = lerpf(camera.fov, 54 if sprint else 50, delta * 2)
	hoof_clock += delta
	if hoof_clock > (0.19 if sprint else 0.27) and jump_y < 0.1:
		hoof_clock = 0
		hoof_sound()

func update_dust(delta: float) -> void:
	dust_clock += delta
	if dust_clock > 0.065 and jump_y < 0.15:
		dust_clock = 0
		var p := block(self, Vector3(horse.position.x + rng.randf_range(-0.6, 0.6), 0.15, 1.3), Vector3.ONE * rng.randf_range(0.12, 0.28), "dbca9c")
		p.set_meta("age", 0.0)
		dust.append(p)
	for p in dust.duplicate():
		var age: float = p.get_meta("age") + delta
		p.set_meta("age", age)
		p.position.z += speed * delta * 0.65
		p.position.y += delta * 0.7
		p.rotation += Vector3(delta, delta * 2, 0)
		p.scale = Vector3.ONE * maxf(0.01, 1 - age / 0.8)
		if age > 0.8:
			dust.erase(p)
			p.queue_free()

# Tiny generated sounds; no audio assets or background threads.
func setup_audio() -> void:
	sound_player = AudioStreamPlayer.new()
	add_child(sound_player)

func play_tone(frequency: float, length: float, volume: float, noise: bool = false) -> void:
	if not sound_on:
		return
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = 22050
	var data := PackedByteArray()
	data.resize(int(22050 * length) * 2)
	for i in range(data.size() / 2):
		var t := float(i) / 22050.0
		var wave := sin(t * frequency * TAU)
		if noise:
			wave = wave * 0.6 + rng.randf_range(-0.4, 0.4)
		var sample := int(wave * exp(-t * (40 if noise else 13)) * volume * 32767)
		data.encode_s16(i * 2, sample)
	stream.data = data
	sound_player.stream = stream
	sound_player.play()

func hoof_sound() -> void:
	play_tone(115, 0.08, 0.13, true)

func chime() -> void:
	play_tone(880 + (shards % 4) * 110, 0.2, 0.16)
