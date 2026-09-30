extends Node3D

const INK = Color("352d30")
var materials: Dictionary = {}
var horse: Node3D
var legs: Array[Node3D] = []
var shins: Array[Node3D] = []
var tail: Node3D
var head: Node3D
var scenery: Array[Node3D] = []
var hazards: Array[Node3D] = []
var dust: Array[Node3D] = []
var rng = RandomNumberGenerator.new()
var phase = 0.0
var distance = 0.0
var best = 0.0
var carrots = 0
var lane = 0
var speed = 13.0
var vertical_speed = 0.0
var jump_height = 0.0
var spawn_timer = 1.0
var active = false
var crashed = false
var paused = false
var flash = 0.0
var dust_timer = 0.0
var camera: Camera3D

func mat(hex: String) -> StandardMaterial3D:
	if not materials.has(hex):
		var m = StandardMaterial3D.new()
		m.albedo_color = Color(hex)
		m.roughness = 1.0
		materials[hex] = m
	return materials[hex]

func box(parent: Node3D, pos: Vector3, scale_v: Vector3, color: String) -> MeshInstance3D:
	var n = MeshInstance3D.new()
	var mesh = BoxMesh.new()
	mesh.size = scale_v
	n.mesh = mesh
	n.material_override = mat(color)
	n.position = pos
	parent.add_child(n)
	return n

func _ready() -> void:
	rng.seed = 73482
	var environment = WorldEnvironment.new()
	var env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("b7d1d2")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("ffe7cf")
	env.ambient_light_energy = 0.65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env
	add_child(environment)
	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -32, 0)
	sun.light_color = Color("fff0ce")
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 95
	add_child(sun)
	camera = Camera3D.new()
	camera.position = Vector3(12, 8.5, 15)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 19.5
	camera.far = 220
	add_child(camera)
	camera.look_at(Vector3(0, 1.2, -6))
	box(self, Vector3(0, -0.4, -36), Vector3(200, 0.6, 200), "a5ad82")
	box(self, Vector3(0, -0.08, -38), Vector3(10.5, 0.16, 145), "ceaa7d")
	box(self, Vector3(-5.35, -0.02, -38), Vector3(0.25, 0.08, 145), "e3c397")
	box(self, Vector3(5.35, -0.02, -38), Vector3(0.25, 0.08, 145), "e3c397")
	# Far-away stepped mesas, deliberately built from chunky blocks.
	for i in range(13):
		var x = float(i - 6) * 14.0
		var h = rng.randf_range(7, 17)
		for level in range(4):
			box(self, Vector3(x, h * float(level) / 4.0, -83), Vector3(19 - level * 3, h / 4.0, 13 - level * 2), ["9aab98", "a6b5a2", "b2beab", "c1c7b2"][level])
	box(self, Vector3(-27, 25, -85), Vector3(7, 7, 1), "fff0be")
	build_horse()
	for i in range(28):
		var chunk = Node3D.new()
		add_child(chunk)
		chunk.position.z = -float(i) * 5.5 + 15
		decorate(chunk, i)
		scenery.append(chunk)
	for i in range(18):
		var p = box(self, Vector3(0, -5, 0), Vector3(0.15, 0.15, 0.15), "e9c798")
		dust.append(p)

func build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	horse.position.z = 2.0
	# Chunky chestnut body, haunches and luminous flank accents.
	box(horse, Vector3(0, 1.65, 0), Vector3(1.02, 0.95, 2.12), "a55332")
	box(horse, Vector3(0, 1.96, 0.12), Vector3(0.89, 0.45, 1.85), "bd6c3d")
	box(horse, Vector3(0, 1.51, 0.82), Vector3(1.12, 0.85, 0.72), "b66338")
	box(horse, Vector3(0, 1.5, -0.83), Vector3(0.96, 0.92, 0.65), "ae5834")
	for side in [-1, 1]:
		box(horse, Vector3(side * 0.52, 1.82, 0.52), Vector3(0.06, 0.22, 0.5), "cc8249")
	# Saddle blanket and leather saddle.
	box(horse, Vector3(0, 2.12, 0.12), Vector3(1.12, 0.15, 0.95), "3c7775")
	for side in [-1, 1]:
		box(horse, Vector3(side * 0.56, 1.89, 0.12), Vector3(0.08, 0.48, 0.94), "3c7775")
		box(horse, Vector3(side * 0.61, 1.71, 0.12), Vector3(0.06, 0.07, 0.9), "efc783")
	box(horse, Vector3(0, 2.24, 0.1), Vector3(0.8, 0.17, 0.68), "513a30")
	box(horse, Vector3(0, 2.35, 0.43), Vector3(0.78, 0.19, 0.14), "69442f")
	# Forward-sloping neck, head, muzzle, ears and square blaze.
	head = Node3D.new()
	horse.add_child(head)
	box(head, Vector3(0, 2.25, -0.99), Vector3(0.64, 1.05, 0.68), "b8663b")
	box(head, Vector3(0, 2.68, -1.22), Vector3(0.59, 0.72, 0.6), "c27746")
	box(head, Vector3(0, 3.02, -1.55), Vector3(0.66, 0.56, 0.89), "b9683e")
	box(head, Vector3(0, 2.83, -1.99), Vector3(0.56, 0.38, 0.43), "e0b687")
	box(head, Vector3(0, 3.08, -1.995), Vector3(0.18, 0.35, 0.04), "f6dfae")
	for side in [-1, 1]:
		box(head, Vector3(side * 0.22, 3.48, -1.3), Vector3(0.18, 0.48, 0.23), "aa5a36")
		box(head, Vector3(side * 0.22, 3.5, -1.43), Vector3(0.08, 0.25, 0.035), "dfaa78")
		box(head, Vector3(side * 0.342, 3.09, -1.7), Vector3(0.045, 0.12, 0.14), "272b2c")
		box(head, Vector3(side * 0.369, 3.12, -1.72), Vector3(0.015, 0.035, 0.04), "fff4d8")
		box(head, Vector3(side * 0.285, 2.84, -2.09), Vector3(0.025, 0.065, 0.09), "694737")
	for i in range(6):
		box(head, Vector3(0, 3.21 - i * 0.18, -1.03 + i * 0.09), Vector3(0.26, 0.3, 0.24), "43332c")
	for i in range(4):
		var leg = Node3D.new()
		leg.position = Vector3(-0.37 if i % 2 == 0 else 0.37, 1.52, -0.73 if i < 2 else 0.76)
		horse.add_child(leg)
		box(leg, Vector3(0, -0.36, 0), Vector3(0.29, 0.72, 0.32), "a85633")
		var shin = Node3D.new()
		shin.position.y = -0.68
		leg.add_child(shin)
		box(shin, Vector3(0, -0.3, 0), Vector3(0.2, 0.6, 0.22), "cc9466")
		box(shin, Vector3(0, -0.57, -0.025), Vector3(0.27, 0.23, 0.35), "393332")
		legs.append(leg)
		shins.append(shin)
	tail = Node3D.new()
	tail.position = Vector3(0, 1.95, 1.02)
	horse.add_child(tail)
	for i in range(5):
		box(tail, Vector3(0, -i * 0.17, 0.18 + i * 0.19), Vector3(0.31 - i * 0.025, 0.32, 0.36), "43332c")

func decorate(chunk: Node3D, index: int) -> void:
	for side in [-1, 1]:
		var x = side * rng.randf_range(7.5, 23)
		if index % 3 == 0:
			var height = rng.randf_range(2.2, 4.8)
			box(chunk, Vector3(x, height / 2, 0), Vector3(0.65, height, 0.65), "638474")
			box(chunk, Vector3(x + 0.6, height * 0.52, 0), Vector3(1.5, 0.48, 0.48), "638474")
			box(chunk, Vector3(x + 1.1, height * 0.67, 0), Vector3(0.45, height * 0.3, 0.45), "73917c")
		else:
			box(chunk, Vector3(x, 0.22, 0), Vector3(1.3, 0.65, 1.1), "93977a")
			box(chunk, Vector3(x + 0.2, 0.65, 0), Vector3(0.8, 0.25, 0.7), "b4b294")
		# Low trail fence with regular upright posts.
		box(chunk, Vector3(side * 6.4, 0.62, 0), Vector3(0.18, 1.25, 0.2), "80674e")
		box(chunk, Vector3(side * 6.4, 0.83, 0), Vector3(0.12, 0.14, 5.5), "b69b70")
		for j in range(3):
			box(chunk, Vector3(side * rng.randf_range(5.7, 20), 0.12, rng.randf_range(-2, 2)), Vector3(0.12, 0.3, 0.12), "c6bc83")
	for x in [-1.65, 1.65]:
		box(chunk, Vector3(x, 0.018, 0), Vector3(0.065, 0.018, 1.8), "dfbf91")

func spawn_item() -> void:
	var n = Node3D.new()
	add_child(n)
	n.position = Vector3(rng.randi_range(-1, 1) * 3.2, 0, -47)
	var collectible = rng.randf() < 0.42
	n.set_meta("collectible", collectible)
	n.set_meta("passed", false)
	if collectible:
		# A voxel horseshoe, floating upright over the trail.
		for side in [-1, 1]:
			box(n, Vector3(side * 0.35, 1.5, 0), Vector3(0.2, 0.8, 0.2), "ffd479")
			box(n, Vector3(side * 0.24, 1.1, 0), Vector3(0.23, 0.2, 0.2), "ffd479")
		box(n, Vector3(0, 1.02, 0), Vector3(0.35, 0.2, 0.2), "ffd479")
	else:
		for x in [-1.15, 1.15]:
			box(n, Vector3(x, 0.63, 0), Vector3(0.2, 1.26, 0.25), "514c40")
			box(n, Vector3(x, 1.3, 0), Vector3(0.3, 0.12, 0.35), "f1dfb3")
		box(n, Vector3(0, 0.84, 0), Vector3(2.5, 0.38, 0.35), "e7cd9c")
		for x in [-0.85, 0.0, 0.85]:
			box(n, Vector3(x, 0.84, 0.185), Vector3(0.34, 0.38, 0.025), "c17a50")
	hazards.append(n)

func start() -> void:
	for n in hazards:
		n.queue_free()
	hazards.clear()
	distance = 0
	carrots = 0
	lane = 0
	speed = 13
	jump_height = 0
	vertical_speed = 0
	spawn_timer = 1.2
	active = true
	crashed = false
	paused = false

func jump() -> void:
	if not active:
		start()
	elif jump_height <= 0.01 and not paused:
		vertical_speed = 9.5

func _unhandled_key_input(event: InputEvent) -> void:
	if not event.is_pressed() or event.is_echo():
		return
	if event.keycode in [KEY_SPACE, KEY_UP, KEY_W]:
		jump()
	elif event.keycode in [KEY_LEFT, KEY_A] and active:
		lane = maxi(-1, lane - 1)
	elif event.keycode in [KEY_RIGHT, KEY_D] and active:
		lane = mini(1, lane + 1)
	elif event.keycode == KEY_R:
		start()
	elif event.keycode in [KEY_P, KEY_ESCAPE] and active:
		paused = not paused

func _process(delta: float) -> void:
	if paused:
		return
	var running = not crashed
	var movement = speed if running else 0.0
	phase += delta * (14.0 if running else 2.0)
	flash = maxf(0, flash - delta)
	if active:
		distance += speed * delta
		best = maxf(best, distance)
		speed = minf(23, 13 + distance / 160)
		spawn_timer -= delta
		if spawn_timer <= 0:
			spawn_item()
			spawn_timer = rng.randf_range(1.4, 2.0)
	vertical_speed -= 24 * delta
	jump_height = maxf(0, jump_height + vertical_speed * delta)
	if jump_height == 0:
		vertical_speed = maxf(vertical_speed, 0)
	horse.position.x = lerpf(horse.position.x, lane * 3.2, minf(1, delta * 9))
	horse.position.y = jump_height + (absf(sin(phase)) * 0.11 if running else 0.0)
	horse.rotation.z = lerpf(horse.rotation.z, -(lane * 3.2 - horse.position.x) * 0.06, delta * 8)
	horse.rotation.x = -0.08 if jump_height > 0.1 else sin(phase) * 0.025
	for i in range(4):
		var offset = [0.0, 0.65, PI, PI + 0.65][i]
		legs[i].rotation.x = sin(phase + offset) * 0.75 if running else 0.0
		shins[i].rotation.x = maxf(0, cos(phase + offset)) * 1.0 if running else 0.0
	tail.rotation.x = sin(phase * 0.5) * 0.14 - 0.15
	tail.rotation.z = sin(phase * 0.4) * 0.18
	head.rotation.x = sin(phase) * 0.025
	for n in scenery:
		n.position.z += movement * delta
		if n.position.z > 22:
			n.position.z -= 154
	for n in hazards.duplicate():
		n.position.z += movement * delta
		if n.get_meta("collectible"):
			n.rotation.y += delta * 2
		if active and not n.get_meta("passed") and absf(n.position.z - 2) < 0.75:
			if absf(n.position.x - horse.position.x) < 1.25:
				if n.get_meta("collectible"):
					carrots += 1
					flash = 0.35
					n.set_meta("passed", true)
					n.hide()
				elif jump_height < 1.05:
					crashed = true
					active = false
					flash = 0.6
			if n.position.z > 2.7:
				n.set_meta("passed", true)
		if n.position.z > 24:
			hazards.erase(n)
			n.queue_free()
	dust_timer += delta
	if running and jump_height < 0.2 and dust_timer > 0.045:
		dust_timer = 0
		for p in dust:
			if p.position.y < 0:
				p.position = Vector3(horse.position.x + rng.randf_range(-0.5, 0.5), 0.12, 3)
				p.scale = Vector3.ONE * rng.randf_range(0.6, 1.5)
				break
	for p in dust:
		if p.position.y >= 0:
			p.position.z += delta * 4
			p.position.y += delta * 0.6
			p.scale *= 1 - delta * 1.7
			if p.scale.x < 0.18:
				p.position.y = -5
