extends Node3D

var horse: Node3D
var legs: Array[Node3D] = []
var scenery: Array[Node3D] = []
var items: Array[Node3D] = []
var mats: Dictionary = {}
var lane := 0
var jump_y := 0.0
var velocity := 0.0
var clock := 0.0
var distance := 0.0
var carrots := 0
var hearts := 3
var speed := 12.0
var spawn_timer := 1.8
var hurt := 0.0
var ended := false
var paused := false
var hud: Control
var info: Label
var score: Label
var status: Label
var message: Label
var rng := RandomNumberGenerator.new()

func material(name_: String, color: String) -> void:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(color)
	m.roughness = 0.92
	mats[name_] = m

func box(parent: Node3D, position: Vector3, size: Vector3, color: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var cube := BoxMesh.new()
	cube.size = size
	mesh.mesh = cube
	mesh.material_override = mats[color]
	mesh.position = position
	parent.add_child(mesh)
	return mesh

func _ready() -> void:
	rng.seed = 8421
	material("coat", "#a95b37")
	material("light", "#d28b51")
	material("dark", "#392c32")
	material("cream", "#fff0cf")
	material("grass", "#779c69")
	material("sage", "#9db886")
	material("trail", "#cfb58b")
	material("wood", "#856346")
	material("leaf", "#4e8062")
	material("leaf2", "#6a9870")
	material("orange", "#ff9c38")
	material("rock", "#91a89b")
	material("mountain", "#91b9b4")
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color("#b4d9dc")
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color("#e0ede0")
	e.ambient_light_energy = 0.65
	e.fog_enabled = true
	e.fog_light_color = Color("#b4d9dc")
	e.fog_density = 0.009
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -35, 0)
	sun.light_color = Color("#fff1d4")
	sun.light_energy = 1.4
	sun.shadow_enabled = true
	add_child(sun)
	var camera := Camera3D.new()
	add_child(camera)
	camera.position = Vector3(10, 8, 14)
	camera.look_at(Vector3(0, 1, -10))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 23
	camera.current = true
	box(self, Vector3(0, -0.3, -35), Vector3(180, 0.5, 180), "grass")
	box(self, Vector3(0, -0.015, -35), Vector3(8.8, 0.08, 150), "trail")
	for side in [-1, 1]:
		box(self, Vector3(side * 4.6, 0.02, -35), Vector3(0.18, 0.08, 150), "cream")
	for i in range(15):
		var mountain := box(self, Vector3(rng.randf_range(-65, 65), 1, -80 - rng.randf_range(0, 20)), Vector3(rng.randf_range(10, 22), rng.randf_range(8, 20), 12), "mountain")
		mountain.rotation.z = PI / 4
	for i in range(55):
		var decor := Node3D.new()
		add_child(decor)
		decor.position = Vector3((1 if i % 2 == 0 else -1) * rng.randf_range(6, 30), 0, rng.randf_range(-85, 15))
		if i % 3 == 0:
			box(decor, Vector3(0, 1.3, 0), Vector3(0.5, 2.6, 0.5), "wood")
			box(decor, Vector3(0, 3, 0), Vector3(2.6, 2.5, 2.5), "leaf")
			box(decor, Vector3(0.4, 4.2, 0), Vector3(1.8, 1, 1.7), "leaf2")
		else:
			box(decor, Vector3(0, 0.2, 0), Vector3(0.8, 0.4, 0.7), "sage" if i % 2 == 0 else "rock")
		scenery.append(decor)
	build_horse()
	build_ui()

func build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	box(horse, Vector3(0, 1.65, 0), Vector3(1.0, 0.95, 2.0), "coat")
	box(horse, Vector3(0, 2.02, -0.8), Vector3(0.75, 1.25, 0.7), "light")
	box(horse, Vector3(0, 2.75, -1.1), Vector3(0.7, 0.65, 1.05), "coat")
	box(horse, Vector3(0, 2.55, -1.65), Vector3(0.65, 0.45, 0.5), "light")
	box(horse, Vector3(0, 2.85, -1.64), Vector3(0.19, 0.35, 0.08), "cream")
	for x in [-0.24, 0.24]:
		box(horse, Vector3(x, 3.2, -0.88), Vector3(0.18, 0.45, 0.22), "coat")
		box(horse, Vector3(x * 1.48, 2.85, -1.27), Vector3(0.06, 0.12, 0.13), "dark")
	for i in range(5):
		box(horse, Vector3(0, 2.05 + i * 0.17, -0.42 - i * 0.065), Vector3(0.25, 0.3, 0.3), "dark")
	var tail := box(horse, Vector3(0, 1.5, 1.32), Vector3(0.28, 0.9, 0.35), "dark")
	tail.rotation.x = -0.5
	for x in [-0.36, 0.36]:
		for z in [-0.65, 0.65]:
			var pivot := Node3D.new()
			horse.add_child(pivot)
			pivot.position = Vector3(x, 1.4, z)
			box(pivot, Vector3(0, -0.52, 0), Vector3(0.27, 1.04, 0.28), "coat")
			box(pivot, Vector3(0, -1.05, -0.04), Vector3(0.32, 0.28, 0.4), "dark")
			legs.append(pivot)

func label_at(text: String, pos: Vector2, font_size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	hud.add_child(l)
	return l

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Control.new()
	layer.add_child(hud)
	var panel := ColorRect.new()
	panel.color = Color("#243d3c")
	panel.position = Vector2(28, 25)
	panel.size = Vector2(280, 97)
	hud.add_child(panel)
	label_at("W I L D S T R I D E", Vector2(46, 37), 25, Color("#fff0cf"))
	label_at("THE VOXEL TRAIL  /  ENDLESS RUN", Vector2(47, 79), 12, Color("#b5cec1"))
	score = label_at("", Vector2(960, 32), 25, Color("#243d3c"))
	status = label_at("", Vector2(960, 70), 17, Color("#243d3c"))
	info = label_at("A / D  or  ← / →    CHANGE LANE       SPACE    JUMP       P    PAUSE", Vector2(30, 665), 17, Color("#243d3c"))
	label_at("Collect carrots. Clear the fences. Find your stride.", Vector2(30, 635), 15, Color("#243d3c"))
	message = label_at("", Vector2(405, 260), 32, Color("#fff0cf"))
	var restart := Button.new()
	restart.text = "↻  Restart"
	restart.position = Vector2(1130, 656)
	restart.size = Vector2(120, 40)
	restart.pressed.connect(reset)
	hud.add_child(restart)

func spawn_item() -> void:
	var n := Node3D.new()
	add_child(n)
	var l := rng.randi_range(-1, 1)
	n.position = Vector3(l * 2.7, 0, -58)
	var fence := rng.randf() < 0.55
	n.set_meta("fence", fence)
	n.set_meta("hit", false)
	if fence:
		for x in [-1.05, 1.05]:
			box(n, Vector3(x, 0.65, 0), Vector3(0.18, 1.3, 0.2), "wood")
		for y in [0.45, 1.0]:
			box(n, Vector3(0, y, 0), Vector3(2.4, 0.18, 0.18), "cream")
	else:
		box(n, Vector3(0, 1.0, 0), Vector3(0.4, 0.8, 0.4), "orange")
		box(n, Vector3(0, 1.58, 0), Vector3(0.15, 0.4, 0.15), "leaf")
		box(n, Vector3(0, 0.5, 0), Vector3(0.2, 0.25, 0.2), "orange")
	items.append(n)

func reset() -> void:
	for n in items:
		n.queue_free()
	items.clear()
	distance = 0
	carrots = 0
	hearts = 3
	lane = 0
	jump_y = 0
	velocity = 0
	hurt = 0
	ended = false
	paused = false
	spawn_timer = 1.5

func _unhandled_key_input(event: InputEvent) -> void:
	if not event.is_pressed() or event.is_echo():
		return
	if event.keycode == KEY_R:
		reset()
	if event.keycode == KEY_P or event.keycode == KEY_ESCAPE:
		paused = not paused
	if ended or paused:
		return
	if event.keycode == KEY_A or event.keycode == KEY_LEFT:
		lane = maxi(-1, lane - 1)
	if event.keycode == KEY_D or event.keycode == KEY_RIGHT:
		lane = mini(1, lane + 1)
	if event.keycode == KEY_SPACE and jump_y <= 0.01:
		velocity = 8.8

func _process(delta: float) -> void:
	score.text = "%05d m   /   %02d carrots" % [int(distance), carrots]
	status.text = "ENERGY  " + "● ".repeat(hearts) + "○ ".repeat(3 - hearts)
	message.text = "TRAIL COMPLETE\n%d m  ·  %d carrots\nPress R to ride again" % [int(distance), carrots] if ended else ("PAUSED\nPress P to resume" if paused else "")
	if ended or paused:
		return
	clock += delta
	distance += speed * delta
	speed = minf(21, 12 + distance / 180)
	hurt = maxf(0, hurt - delta)
	velocity -= 23 * delta
	jump_y = maxf(0, jump_y + velocity * delta)
	if jump_y == 0:
		velocity = maxf(0, velocity)
	horse.position.x = lerpf(horse.position.x, lane * 2.7, 10 * delta)
	horse.position.y = jump_y + 0.07 * sin(clock * 18)
	horse.rotation.z = clampf((lane * 2.7 - horse.position.x) * -0.07, -0.15, 0.15)
	horse.visible = hurt <= 0 or int(clock * 16) % 2 == 0
	for i in range(legs.size()):
		legs[i].rotation.x = sin(clock * 15 + (0 if i == 0 or i == 3 else PI)) * 0.7 if jump_y < 0.1 else -0.6
	for n in scenery:
		n.position.z += speed * delta
		if n.position.z > 22:
			n.position.z -= 110
	spawn_timer -= delta
	if spawn_timer < 0:
		spawn_item()
		spawn_timer = rng.randf_range(0.85, 1.35)
	for n in items.duplicate():
		n.position.z += speed * delta
		if not n.get_meta("fence"):
			n.rotation.y += delta * 2
		if absf(n.position.z) < 0.9 and absf(n.position.x - horse.position.x) < 1.1 and not n.get_meta("hit"):
			if n.get_meta("fence"):
				if jump_y < 1.05 and hurt <= 0:
					hearts -= 1
					hurt = 1.6
					if hearts <= 0:
						ended = true
			else:
				carrots += 1
				n.visible = false
			n.set_meta("hit", true)
		if n.position.z > 18:
			items.erase(n)
			n.queue_free()
