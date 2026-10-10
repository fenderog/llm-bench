extends Node3D

# No imported models, textures, sound files, or plugins: the trail is built here.
enum Mode { TITLE, RUNNING, PAUSED, ENDED }
const LANES := [-2.45, 0.0, 2.45]
const HORSE_Z := 1.4
var mode := Mode.TITLE
var horse: VoxelHorse
var landscape: TrailLandscape
var camera: Camera3D
var ui: TrailInterface
var audio: TrailAudio
var rng := RandomNumberGenerator.new()
var objects: Array[Dictionary] = []
var particles: Array[Dictionary] = []
var particle_materials: Dictionary = {}
var distance := 0.0
var carrots := 0
var best := 0
var life := 3
var target_lane := 1
var jump_y := 0.0
var jump_velocity := 0.0
var jump_buffer := 0.0
var speed := 10.5
var invulnerable := 0.0
var slow_time := 0.0
var next_spawn := 24.0
var row_number := 0
var dust_time := 0.0
var hoof_time := 0.0
var world_time := 0.0
var milestone := 100
var camera_shake := 0.0
var title_spawn := 0.0
var title_step := 0

func _ready() -> void:
	rng.seed = 84879
	make_environment()
	landscape = TrailLandscape.new()
	add_child(landscape)
	horse = VoxelHorse.new()
	horse.position.z = HORSE_Z
	add_child(horse)
	camera = Camera3D.new()
	camera.current = true
	camera.fov = 43
	camera.near = .5
	camera.far = 240
	camera.position = Vector3(-7.8, 4.3, 9)
	add_child(camera)
	camera.look_at(Vector3(-1.7, 1.15, -3.2))
	audio = TrailAudio.new()
	add_child(audio)
	ui = TrailInterface.new()
	add_child(ui)
	ui.start_requested.connect(start_run)
	ui.pause_requested.connect(pause_run)
	ui.resume_requested.connect(resume_run)
	ui.menu_requested.connect(return_to_title)
	ui.sound_requested.connect(toggle_sound)
	ui.left_requested.connect(func(): steer(-1))
	ui.right_requested.connect(func(): steer(1))
	ui.jump_requested.connect(request_jump)
	setup_title_trail()

func make_environment() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	var sky := Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("7ba5a0")
	sky_material.sky_horizon_color = Color("e4d9b8")
	sky_material.ground_bottom_color = Color("849163")
	sky_material.ground_horizon_color = Color("dfd4b3")
	sky_material.sky_curve = .19
	sky_material.sun_angle_max = 12
	sky_material.sun_curve = .1
	sky.sky_material = sky_material
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("e2e6d8")
	environment.ambient_light_energy = .38
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment.fog_enabled = true
	environment.fog_light_color = Color("c7cdb1")
	environment.fog_light_energy = .85
	environment.fog_density = .0032
	environment.fog_sky_affect = .15
	world.environment = environment
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-36, -38, 0)
	sun.light_color = Color("fff0d6")
	sun.light_energy = .95
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 45
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.shadow_bias = .8
	sun.shadow_normal_bias = 3.0
	add_child(sun)

func _process(delta: float) -> void:
	delta = minf(delta, .05)
	if mode != Mode.PAUSED:
		world_time += delta
		var move_speed := speed
		if mode == Mode.TITLE: move_speed = 7.5
		if mode == Mode.ENDED: move_speed = 2.7
		if slow_time > 0:
			slow_time -= delta
			move_speed *= .65
		landscape.scroll(move_speed * delta)
		update_objects(delta, move_speed)
		update_horse(delta, move_speed)
		update_particles(delta)
		if mode == Mode.RUNNING:
			distance += move_speed * delta
			speed = minf(19.5, 10.5 + distance * .008)
			invulnerable = maxf(0, invulnerable - delta)
			if distance >= next_spawn:
				spawn_row(-100.0, row_number)
				row_number += 1
				next_spawn += rng.randf_range(23, 29)
			if int(distance) >= milestone:
				ui.feedback("%d m  /  FINDING YOUR STRIDE" % milestone)
				milestone += 100
			ui.update_run(distance, carrots, life, target_lane, speed)
		elif mode == Mode.TITLE:
			title_spawn += move_speed * delta
			if title_spawn > 25:
				title_spawn = 0
				spawn_row(-74, title_step)
				title_step += 1
			# A living title screen: our horse jumps the centre-lane fences.
			for item in objects:
				if item.type != "carrot" and item.lane == target_lane and item.node.position.z > -2.8 and item.node.position.z < -1.8 and jump_y < .01:
					jump_velocity = 8.4
			if target_lane != 1: target_lane = 1
	update_camera(delta)

func update_horse(delta: float, move_speed: float) -> void:
	var target_x: float = LANES[target_lane]
	var difference := target_x - horse.position.x
	horse.position.x = lerpf(horse.position.x, target_x, 1.0 - exp(-delta * 11))
	horse.rotation.y = lerpf(horse.rotation.y, -difference * .075, delta * 9)
	horse.rotation.z = lerpf(horse.rotation.z, -difference * .045, delta * 9)
	jump_buffer = maxf(0, jump_buffer - delta)
	if jump_y > 0 or jump_velocity > 0:
		jump_velocity -= 21.0 * delta
		jump_y += jump_velocity * delta
		if jump_y <= 0:
			jump_y = 0
			jump_velocity = 0
			if mode == Mode.RUNNING:
				audio.play("hoof", -18, .8)
				make_dust(7)
			if jump_buffer > 0: request_jump()
	horse.position.y = jump_y
	horse.animate(delta, 7.8 + move_speed * .32, jump_y > .1)
	hoof_time += delta
	dust_time += delta
	if jump_y < .1:
		if dust_time > .13:
			dust_time = 0
			make_dust(2)
		if hoof_time > .19 and mode == Mode.RUNNING:
			hoof_time = 0
			audio.play("hoof", -25, rng.randf_range(.88, 1.14))

func update_camera(delta: float) -> void:
	var showcasing := mode == Mode.TITLE or mode == Mode.ENDED
	var target := Vector3(-7.8, 4.3, 9) if showcasing else Vector3(-6.8, 6.0, 11)
	target.x += horse.position.x * .25
	camera.position = camera.position.lerp(target, 1.0 - exp(-delta * 3))
	camera.fov = lerpf(camera.fov, 43.0 if showcasing else 49.0, delta * 3)
	var focus := Vector3(-1.7, 1.15, -3.2) if showcasing else Vector3(0, .85, -5.3)
	focus.x += horse.position.x * .23
	focus.y += jump_y * .10
	camera.look_at(focus)
	if camera_shake > 0:
		camera_shake = maxf(0, camera_shake - delta * 1.7)
		camera.h_offset = rng.randf_range(-.10, .10) * camera_shake
		camera.v_offset = rng.randf_range(-.08, .08) * camera_shake
	else:
		camera.h_offset = 0
		camera.v_offset = 0

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo: return
	match event.keycode:
		KEY_ENTER, KEY_KP_ENTER:
			if mode == Mode.TITLE or mode == Mode.ENDED: start_run()
			elif mode == Mode.PAUSED: resume_run()
		KEY_A, KEY_LEFT:
			steer(-1)
		KEY_D, KEY_RIGHT:
			steer(1)
		KEY_SPACE, KEY_UP, KEY_W:
			if mode == Mode.TITLE or mode == Mode.ENDED: start_run()
			else: request_jump()
		KEY_ESCAPE, KEY_P:
			if mode == Mode.RUNNING: pause_run()
			elif mode == Mode.PAUSED: resume_run()
		KEY_R:
			if mode != Mode.TITLE: start_run()
		KEY_M:
			toggle_sound()
	get_viewport().set_input_as_handled()

func start_run() -> void:
	best = maxi(best, int(distance))
	audio.stop_all()
	clear_objects()
	rng.seed = 84879
	mode = Mode.RUNNING
	distance = 0
	carrots = 0
	life = 3
	target_lane = 1
	jump_y = 0
	jump_velocity = 0
	jump_buffer = 0
	horse.position.x = 0
	horse.flash_time = 0
	horse.visible = true
	speed = 10.5
	invulnerable = 0
	slow_time = 0
	next_spawn = 24
	milestone = 100
	row_number = 4
	for i in 4:
		spawn_row(-28.0 - i * 24, i)
	for z in [-4.0, -8.0, -12.0]:
		spawn_carrot(1, z, 1.1)
	ui.show_play()
	ui.update_run(0, 0, 3, 1, speed)
	ui.feedback("FOLLOW THE CARROTS. RUN FREE.")
	audio.play("start", -17)

func pause_run() -> void:
	if mode != Mode.RUNNING: return
	mode = Mode.PAUSED
	audio.stop_all()
	ui.show_pause(int(distance), carrots)

func resume_run() -> void:
	if mode != Mode.PAUSED: return
	mode = Mode.RUNNING
	ui.show_play()

func return_to_title() -> void:
	mode = Mode.TITLE
	clear_objects()
	target_lane = 1
	horse.flash_time = 0
	setup_title_trail()
	ui.show_title(best)

func end_run() -> void:
	mode = Mode.ENDED
	best = maxi(best, int(distance))
	ui.show_end(int(distance), carrots, best)

func toggle_sound() -> void:
	audio.enabled = not audio.enabled
	if not audio.enabled: audio.stop_all()
	ui.set_sound(audio.enabled)

func steer(direction: int) -> void:
	if mode != Mode.RUNNING: return
	target_lane = clampi(target_lane + direction, 0, 2)

func request_jump() -> void:
	if mode != Mode.RUNNING: return
	if jump_y < .05 and jump_velocity <= 0:
		jump_velocity = 9.0
		jump_buffer = 0
		audio.play("jump", -22)
	else:
		jump_buffer = .16

func setup_title_trail() -> void:
	title_spawn = 0
	title_step = 3
	for i in 3:
		spawn_row(-20.0 - i * 25, i)
	for z in [-3.0, -7.0, -11.0]:
		spawn_carrot(1, z, 1.1)

func spawn_row(z: float, index: int) -> void:
	var obstacle_lane := 1 if index == 0 else rng.randi_range(0, 2)
	var kind: String = ["fence", "hay", "log"][index % 3]
	spawn_obstacle(obstacle_lane, z, kind)
	var carrot_lane := obstacle_lane
	if index % 3 == 1:
		carrot_lane = (obstacle_lane + 1) % 3
	if index > 4 and index % 4 == 0:
		var other := (obstacle_lane + 1) % 3
		spawn_obstacle(other, z, "hay")
		carrot_lane = (obstacle_lane + 2) % 3
	for j in 4:
		var y := 1.12
		if carrot_lane == obstacle_lane and j >= 2: y = 2.0 if j == 2 else 2.3
		spawn_carrot(carrot_lane, z + 10 - j * 3.1, y)
	spawn_carrot(carrot_lane, z - 5.0, 1.12)

func spawn_obstacle(lane: int, z: float, kind: String) -> void:
	var node := Node3D.new()
	node.position = Vector3(LANES[lane], 0, z)
	add_child(node)
	var b := VoxelBuilder.new()
	var threshold := .85
	match kind:
		"fence":
			for x in [-.85, .85]:
				b.box(Vector3(x, .59, 0), Vector3(.21, 1.18, .24), Color("a36b44"))
				b.box(Vector3(x, 1.17, 0), Vector3(.26, .12, .28), Color("df995a"))
			for y in [.43, .91]:
				b.box(Vector3(0, y, 0), Vector3(1.88, .19, .17), Color("e5c69a"))
			b.box(Vector3(0, .68, .03), Vector3(1.6, .12, .13), Color("b78755"), Vector3(0, 0, .29))
		"hay":
			b.box(Vector3(0, .48, 0), Vector3(1.56, .95, 1.02), Color("c69b4f"))
			b.box(Vector3(0, .97, 0), Vector3(1.48, .075, .94), Color("e3bd71"))
			for x in [-.42, .42]:
				b.box(Vector3(x, .50, 0), Vector3(.075, 1.02, 1.04), Color("7e7950"))
			for j in 6:
				b.box(Vector3(-.67 + j * .25, .46, .52), Vector3(.095, .82, .02), Color("d8b165"))
		"log":
			threshold = .63
			b.box(Vector3(0, .32, 0), Vector3(1.9, .59, .68), Color("7e6046"))
			b.box(Vector3(0, .63, 0), Vector3(1.82, .12, .47), Color("9a7951"))
			for x in [-.96, .96]:
				b.box(Vector3(x, .33, 0), Vector3(.045, .48, .52), Color("dbbb82"))
				b.box(Vector3(x * 1.03, .33, 0), Vector3(.012, .22, .26), Color("b38b59"))
			b.box(Vector3(.08, .70, .08), Vector3(.25, .25, .25), Color("806247"))
	b.build(node)
	objects.append({"node": node, "lane": lane, "type": kind, "threshold": threshold, "resolved": false, "phase": 0.0, "y": 0.0})

func spawn_carrot(lane: int, z: float, y: float) -> void:
	var node := Node3D.new()
	node.position = Vector3(LANES[lane], y, z)
	add_child(node)
	var b := VoxelBuilder.new()
	b.box(Vector3(0, .02, 0), Vector3(.29, .40, .29), Color("ed9a48"))
	b.box(Vector3(0, -.25, 0), Vector3(.20, .19, .20), Color("db7e33"))
	b.box(Vector3(0, -.40, 0), Vector3(.105, .13, .105), Color("db7e33"))
	b.box(Vector3(-.08, .40, 0), Vector3(.11, .34, .11), Color("5a854d"), Vector3(0, 0, .28))
	b.box(Vector3(.09, .36, 0), Vector3(.12, .27, .12), Color("81a460"), Vector3(0, 0, -.42))
	b.box(Vector3(.04, .34, .13), Vector3(.11, .21, .12), Color("719855"), Vector3(.5, 0, 0))
	b.box(Vector3(0, .08, .155), Vector3(.18, .035, .015), Color("ffd494"))
	b.build(node)
	node.rotation.z = -.22
	objects.append({"node": node, "lane": lane, "type": "carrot", "threshold": 0.0, "resolved": false, "phase": rng.randf_range(0, TAU), "y": y})

func update_objects(delta: float, move_speed: float) -> void:
	for i in range(objects.size() - 1, -1, -1):
		var item := objects[i]
		var node: Node3D = item.node
		node.position.z += move_speed * delta
		if item.type == "carrot":
			node.rotation.y += delta * 1.8
			node.position.y = item.y + sin(world_time * 3 + item.phase) * .10
		if mode == Mode.TITLE and item.type == "carrot" and node.position.z > HORSE_Z - .6:
			burst(node.position, Color("e4b56a"), 3)
			node.queue_free()
			objects.remove_at(i)
			continue
		if mode == Mode.RUNNING and not item.resolved:
			var z_difference := node.position.z - HORSE_Z
			var x_difference := absf(node.position.x - horse.position.x)
			if item.type == "carrot":
				if absf(z_difference) < .85 and x_difference < .85 and absf(jump_y + 1.05 - node.position.y) < 1.02:
					carrots += 1
					audio.play("carrot", -21, 1.0 + (carrots % 4) * .08)
					burst(node.position, Color("efb05d"), 8)
					if carrots % 5 == 0: ui.feedback("%d CARROTS  /  SWEET STRIDE" % carrots, Color("ffe0a7"))
					node.queue_free()
					objects.remove_at(i)
					continue
			elif absf(z_difference) < .73 and x_difference < 1.00:
				if jump_y < float(item.threshold) and invulnerable <= 0:
					life -= 1
					invulnerable = 1.85
					slow_time = .8
					camera_shake = .65
					horse.hurt()
					ui.hurt()
					audio.play("hit", -16)
					burst(node.position + Vector3(0, .7, 0), Color("c3a47a"), 13)
					item.resolved = true
					if life <= 0:
						end_run()
				elif jump_y >= float(item.threshold):
					item.resolved = true
					ui.feedback("CLEAR!", Color("ffe0a7"))
				objects[i] = item
		if node.position.z > 16:
			node.queue_free()
			objects.remove_at(i)

func clear_objects() -> void:
	for item in objects:
		item.node.queue_free()
	objects.clear()

func make_dust(count: int) -> void:
	for i in count:
		var pos := horse.position + Vector3(rng.randf_range(-.45, .45), .16, rng.randf_range(.5, 1.1))
		particle(pos, Vector3(rng.randf_range(-.6, .6), rng.randf_range(.6, 1.1), rng.randf_range(.8, 2)), Color("dbbc91"), rng.randf_range(.09, .17), .6)

func burst(pos: Vector3, color: Color, count: int) -> void:
	for i in count:
		particle(pos, Vector3(rng.randf_range(-2.3, 2.3), rng.randf_range(1, 3), rng.randf_range(-1, 2)), color, rng.randf_range(.07, .17), .7)

func particle(pos: Vector3, velocity: Vector3, color: Color, size: float, lifetime: float) -> void:
	if particles.size() > 90: return
	var key := color.to_html()
	if not particle_materials.has(key):
		var mat := StandardMaterial3D.new()
		mat.albedo_color = color
		mat.roughness = 1
		particle_materials[key] = mat
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE * size
	mesh.material = particle_materials[key]
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = pos
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(node)
	particles.append({"node": node, "velocity": velocity, "age": 0.0, "life": lifetime})

func update_particles(delta: float) -> void:
	for i in range(particles.size() - 1, -1, -1):
		var p := particles[i]
		p.age += delta
		if p.age > p.life:
			p.node.queue_free()
			particles.remove_at(i)
			continue
		p.velocity.y -= delta * 3.2
		p.node.position += p.velocity * delta
		p.node.scale = Vector3.ONE * (1 - p.age / p.life)
		p.node.rotation.x += delta
		particles[i] = p

