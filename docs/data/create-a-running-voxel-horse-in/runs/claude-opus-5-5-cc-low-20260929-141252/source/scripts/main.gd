extends Node3D
## Procedurally builds a voxel world and a running voxel horse.

const V := 0.25 # voxel size
var horse: Node3D
var legs: Array[Node3D] = []
var head_pivot: Node3D
var tail_pivot: Node3D
var cam: Camera3D
var mats := {}
var t := 0.0
var heading := 0.0
var speed := 8.0
var vy := 0.0
var y := 0.0
var trees: Array[Node3D] = []
var label: Label

func mat(c: Color) -> StandardMaterial3D:
	if not mats.has(c):
		var m := StandardMaterial3D.new()
		m.albedo_color = c
		mats[c] = m
	return mats[c]

func box(parent: Node3D, pos: Vector3, size: Vector3, c: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size * V
	mi.mesh = bm
	mi.material_override = mat(c)
	mi.position = pos * V
	parent.add_child(mi)
	return mi

func _ready() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.55, 0.78, 0.95)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.6, 0.65, 0.7)
	e.fog_enabled = true
	e.fog_light_color = Color(0.55, 0.78, 0.95)
	e.fog_density = 0.02
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	sun.shadow_enabled = true
	add_child(sun)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(400, 400)
	ground.mesh = pm
	ground.material_override = mat(Color(0.35, 0.65, 0.25))
	add_child(ground)
	randomize()
	for i in 60:
		var tr := Node3D.new()
		add_child(tr)
		tr.position = Vector3(randf_range(-40, 40), 0, randf_range(-40, 40))
		_make_tree(tr)
		trees.append(tr)

	_build_horse()
	cam = Camera3D.new()
	add_child(cam)

	label = Label.new()
	label.text = "Left/Right or A/D: steer   Up/Down or W/S: speed   Space: jump"
	label.position = Vector2(10, 10)
	var cl := CanvasLayer.new()
	cl.add_child(label)
	add_child(cl)

func _make_tree(tr: Node3D) -> void:
	var h := randi_range(3, 6)
	for i in h:
		box(tr, Vector3(0, i + 0.5, 0), Vector3(1, 1, 1), Color(0.45, 0.3, 0.15))
	var g := Color(0.15, randf_range(0.4, 0.55), 0.15)
	box(tr, Vector3(0, h + 1.5, 0), Vector3(5, 3, 5), g)
	box(tr, Vector3(0, h + 3.5, 0), Vector3(3, 1, 3), g)

func _build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	var brown := Color(0.55, 0.32, 0.15)
	var dark := Color(0.2, 0.12, 0.06)
	var hoof := Color(0.1, 0.1, 0.1)
	# Body (horse faces -Z)
	box(horse, Vector3(0, 8, 0), Vector3(4, 4, 9), brown)
	box(horse, Vector3(0, 7.5, 0), Vector3(3.6, 3.6, 9.4), brown.darkened(0.1))
	# Legs: pivots at hip/shoulder
	for p in [Vector3(-1.2, 6.5, -3.5), Vector3(1.2, 6.5, -3.5), Vector3(-1.2, 6.5, 3.5), Vector3(1.2, 6.5, 3.5)]:
		var pivot := Node3D.new()
		pivot.position = p * V
		horse.add_child(pivot)
		box(pivot, Vector3(0, -2.5, 0), Vector3(1.4, 5, 1.4), brown)
		box(pivot, Vector3(0, -5.5, 0), Vector3(1.2, 1, 1.2), Color(0.9, 0.9, 0.85))
		box(pivot, Vector3(0, -6.25, 0), Vector3(1.4, 0.5, 1.6), hoof)
		legs.append(pivot)
	# Neck + head
	head_pivot = Node3D.new()
	head_pivot.position = Vector3(0, 9, -4) * V
	horse.add_child(head_pivot)
	var neck := box(head_pivot, Vector3(0, 2.5, -1), Vector3(2, 5, 2.4), brown)
	neck.rotation_degrees.x = -30
	box(head_pivot, Vector3(0, 5, -2.8), Vector3(2.2, 2.2, 4), brown)
	box(head_pivot, Vector3(0, 4.7, -4.9), Vector3(1.8, 1.6, 0.4), dark)
	box(head_pivot, Vector3(-0.6, 6.4, -1.6), Vector3(0.5, 1, 0.5), brown)
	box(head_pivot, Vector3(0.6, 6.4, -1.6), Vector3(0.5, 1, 0.5), brown)
	box(head_pivot, Vector3(-1.15, 5.4, -3.2), Vector3(0.2, 0.5, 0.5), Color.BLACK)
	box(head_pivot, Vector3(1.15, 5.4, -3.2), Vector3(0.2, 0.5, 0.5), Color.BLACK)
	# Mane
	for i in 5:
		box(head_pivot, Vector3(0, 1.2 + i * 1.0, 0.3 - i * 0.55), Vector3(0.6, 1.2, 1), dark)
	# Tail
	tail_pivot = Node3D.new()
	tail_pivot.position = Vector3(0, 9.5, 4.5) * V
	horse.add_child(tail_pivot)
	box(tail_pivot, Vector3(0, -1.5, 1), Vector3(1, 4, 1), dark)
	box(tail_pivot, Vector3(0, -3.5, 1.4), Vector3(1.2, 2, 1.2), dark)

func _process(delta: float) -> void:
	var turn := Input.get_axis("ui_right", "ui_left")
	if Input.is_key_pressed(KEY_A): turn += 1
	if Input.is_key_pressed(KEY_D): turn -= 1
	heading += clamp(turn, -1, 1) * 1.8 * delta
	var acc := Input.get_axis("ui_down", "ui_up")
	if Input.is_key_pressed(KEY_W): acc += 1
	if Input.is_key_pressed(KEY_S): acc -= 1
	speed = clamp(speed + acc * 6.0 * delta, 2.0, 16.0)
	if (Input.is_action_just_pressed("ui_accept") or Input.is_key_pressed(KEY_SPACE)) and y <= 0.0:
		vy = 7.0
	vy -= 20.0 * delta
	y = max(0.0, y + vy * delta)
	if y == 0.0: vy = 0.0

	var fwd := Vector3(-sin(heading), 0, -cos(heading))
	horse.position += fwd * speed * delta
	horse.rotation.y = heading
	horse.rotation.z = lerp(horse.rotation.z, -turn * 0.12, 5 * delta)

	# Gallop animation
	t += delta * speed * 0.9
	var amp := 0.5 + speed * 0.03
	var phases := [0.0, 0.4, PI, PI + 0.4]
	for i in 4:
		legs[i].rotation.x = sin(t + phases[i]) * amp if y == 0.0 else (0.6 if i < 2 else -0.6)
	horse.position.y = y + abs(sin(t)) * 0.12
	horse.rotation.x = sin(t) * 0.05
	head_pivot.rotation.x = sin(t + 1.0) * 0.15
	tail_pivot.rotation.x = 0.5 + sin(t * 1.3) * 0.25

	# Recycle trees around the horse for an endless world
	for tr in trees:
		var d := tr.position - Vector3(horse.position.x, 0, horse.position.z)
		if d.length() > 45:
			tr.position = Vector3(horse.position.x, 0, horse.position.z) + fwd * 40 + fwd.cross(Vector3.UP) * randf_range(-40, 40)
	$".".get_child(2).position = Vector3(horse.position.x, 0, horse.position.z) # ground follows

	var target := horse.position - fwd * 7 + Vector3(0, 3.5, 0)
	cam.position = cam.position.lerp(target, 4 * delta)
	cam.look_at(horse.position + Vector3(0, 1.5, 0))
