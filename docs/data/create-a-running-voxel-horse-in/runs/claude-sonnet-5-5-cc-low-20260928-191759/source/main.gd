extends Node3D

const V := 0.2
const BODY := Color(0.55, 0.32, 0.15)
const DARK := Color(0.25, 0.14, 0.07)
const LIGHT := Color(0.9, 0.85, 0.75)

var horse := Node3D.new()
var legs: Array[Node3D] = []
var tail := Node3D.new()
var head := Node3D.new()
var scenery := Node3D.new()
var t := 0.0
var speed := 1.0

func _ready() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.55, 0.8, 0.95)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.6, 0.6, 0.65)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -30, 0)
	add_child(sun)
	var cam := Camera3D.new()
	cam.position = Vector3(4.5, 2.2, 5.5)
	add_child(cam)
	cam.look_at(Vector3(0, 1.1, 0))
	add_child(scenery)
	add_child(horse)
	_build_ground()
	_build_horse()
	var l := Label.new()
	l.text = "Up/Down (or W/S): change speed"
	l.position = Vector2(10, 10)
	add_child(l)

func _voxels(parent: Node3D, cells: Array, col: Color, origin := Vector3.ZERO) -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	var box := BoxMesh.new()
	box.size = Vector3.ONE * V * 0.98
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	box.material = mat
	mm.mesh = box
	mm.instance_count = cells.size()
	for i in cells.size():
		mm.set_instance_transform(i, Transform3D(Basis(), origin + Vector3(cells[i]) * V))
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = mm
	parent.add_child(mi)

func _block(x0: int, x1: int, y0: int, y1: int, z0: int, z1: int) -> Array:
	var a := []
	for x in range(x0, x1 + 1):
		for y in range(y0, y1 + 1):
			for z in range(z0, z1 + 1):
				a.append(Vector3i(x, y, z))
	return a

func _build_horse() -> void:
	# +x is forward. Body 10 long, 4 wide, 4 tall.
	_voxels(horse, _block(-5, 4, 0, 3, -2, 1), BODY, Vector3(0, 1.0, 0))
	# neck (slanted) and head
	var neck := []
	for i in 4:
		neck.append_array(_block(5 + i / 2, 6 + i / 2, 3 + i, 3 + i, -1, 0))
	_voxels(horse, neck, BODY, Vector3(0, 1.0, 0))
	head.position = Vector3(0, 1.0, 0)
	horse.add_child(head)
	_voxels(head, _block(7, 10, 7, 8, -1, 0), BODY)
	_voxels(head, _block(10, 10, 7, 7, -1, 0), LIGHT)
	_voxels(head, _block(7, 8, 9, 10, -1, -1) + _block(7, 8, 9, 10, 0, 0), DARK)
	_voxels(head, [Vector3i(9, 8, -2), Vector3i(9, 8, 1)], Color.BLACK)
	# mane
	var mane := []
	for i in 5:
		mane.append(Vector3i(4 + i / 2, 4 + i, -1))
		mane.append(Vector3i(4 + i / 2, 4 + i, 0))
	_voxels(horse, mane, DARK, Vector3(0, 1.0, 0) + Vector3(0, 0, 0))
	# tail pivot at rump
	tail.position = Vector3(-5 * V - 0.1, 1.0 + 3 * V, -0.1)
	horse.add_child(tail)
	_voxels(tail, _block(-1, -1, -4, 0, 0, 0) + _block(-2, -2, -5, -2, 0, 0), DARK)
	# legs: pivots at hip
	var hips := [Vector3i(3, 0, 1), Vector3i(3, 0, -2), Vector3i(-5, 0, 1), Vector3i(-5, 0, -2)]
	for h in hips:
		var p := Node3D.new()
		p.position = Vector3(h.x * V + V * 0.5, 1.0, h.z * V)
		horse.add_child(p)
		_voxels(p, _block(0, 0, -4, -1, 0, 0), BODY)
		_voxels(p, _block(0, 0, -5, -5, 0, 0), DARK)
		_voxels(p, _block(0, 0, -5, -5, 0, 0), DARK)
		legs.append(p)
	horse.position.y = 0.0

func _build_ground() -> void:
	for i in 30:
		var m := MeshInstance3D.new()
		var b := BoxMesh.new()
		b.size = Vector3(2, 0.2, 8)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.3, 0.65, 0.25) if i % 2 == 0 else Color(0.35, 0.72, 0.3)
		b.material = mat
		m.mesh = b
		m.position = Vector3(i * 2.0 - 30.0, -0.1, 0)
		m.set_meta("tile", true)
		scenery.add_child(m)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in 24:
		var tr := Node3D.new()
		var z := rng.randf_range(-6.0, -2.5) if i % 2 == 0 else rng.randf_range(2.5, 6.0)
		tr.position = Vector3(i * 2.5 - 30.0, 0, z)
		_voxels(tr, _block(0, 0, 0, 5, 0, 0), Color(0.4, 0.25, 0.1))
		_voxels(tr, _block(-2, 2, 6, 8, -2, 2), Color(0.15, 0.5, 0.18))
		tr.set_meta("tree", true)
		scenery.add_child(tr)

func _process(dt: float) -> void:
	if Input.is_key_pressed(KEY_UP) or Input.is_key_pressed(KEY_W):
		speed = minf(speed + dt, 2.0)
	if Input.is_key_pressed(KEY_DOWN) or Input.is_key_pressed(KEY_S):
		speed = maxf(speed - dt, 0.0)
	t += dt * speed * 11.0
	# gallop: front pair in phase, back pair offset
	var amp := 0.9 * minf(speed, 1.0)
	legs[0].rotation.z = sin(t) * amp
	legs[1].rotation.z = sin(t + 0.4) * amp
	legs[2].rotation.z = sin(t + PI + 0.3) * amp
	legs[3].rotation.z = sin(t + PI + 0.7) * amp
	horse.position.y = absf(sin(t * 0.5 + 0.5)) * 0.15 * speed
	horse.rotation.z = sin(t) * 0.04 * speed
	head.rotation.z = sin(t + 1.0) * 0.06
	tail.rotation.z = 0.5 + sin(t - 1.0) * 0.2
	for c in scenery.get_children():
		c.position.x -= dt * speed * 9.0
		if c.position.x < -30.0:
			c.position.x += 60.0 if c.has_meta("tile") else 60.0
