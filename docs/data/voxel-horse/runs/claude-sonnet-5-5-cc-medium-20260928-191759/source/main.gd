extends Node3D
## Running voxel horse: everything is built procedurally from colored cubes.

const V := 0.1  # voxel size in meters

var speed := 1.0
var cam_angle := 0.0
var t := 0.0
var scenery: Node3D
var horse: Node3D
var body: Node3D
var neck: Node3D
var tail: Node3D
var legs := []  # each: {upper, lower, phase}
var cam: Camera3D
var label: Label

func _ready() -> void:
	_setup_world()
	_build_horse()
	_build_scenery()
	label = Label.new()
	label.position = Vector2(12, 8)
	label.text = "Up/Down: speed    Left/Right: orbit camera"
	add_child(label)

# ---------- voxel helpers ----------

func _noise(p: Vector3i) -> float:
	return float(hash(p) % 1000) / 1000.0

func _box(d: Dictionary, from: Vector3i, size: Vector3i, col: Color, jitter := 0.05) -> void:
	for x in size.x:
		for y in size.y:
			for z in size.z:
				var p := from + Vector3i(x, y, z)
				var k := 1.0 + (_noise(p) - 0.5) * jitter * 2.0
				d[p] = Color(col.r * k, col.g * k, col.b * k)

func _mesh(d: Dictionary) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var dirs := [Vector3i.RIGHT, Vector3i.LEFT, Vector3i.UP, Vector3i.DOWN, Vector3i.BACK, Vector3i.FORWARD]
	for p: Vector3i in d:
		st.set_color(d[p])
		for n: Vector3i in dirs:
			if d.has(p + n):
				continue
			var nf := Vector3(n)
			var u := Vector3(n.y, n.z, n.x)
			var w := nf.cross(u)
			var c := (Vector3(p) + Vector3(0.5, 0.5, 0.5) + nf * 0.5) * V
			var h := 0.5 * V
			var q := [c - u * h - w * h, c + u * h - w * h, c + u * h + w * h, c - u * h + w * h]
			st.set_normal(nf)
			for i in [0, 2, 1, 0, 3, 2]:
				st.add_vertex(q[i])
	var mi := MeshInstance3D.new()
	var mesh := st.commit()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 1.0
	mesh.surface_set_material(0, mat)
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return mi

func _pivot(parent: Node3D, pos: Vector3) -> Node3D:
	var n := Node3D.new()
	n.position = pos
	parent.add_child(n)
	return n

# ---------- world ----------

func _setup_world() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.55, 0.78, 0.95)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.75, 0.8, 0.9)
	env.ambient_light_energy = 0.6
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.shadow_enabled = true
	add_child(sun)
	cam = Camera3D.new()
	cam.fov = 50
	add_child(cam)
	scenery = Node3D.new()
	add_child(scenery)

func _build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	var coat := Color(0.55, 0.3, 0.14)
	var dark := Color(0.12, 0.08, 0.06)
	var white := Color(0.95, 0.93, 0.88)
	# Horse faces +X. Body node origin is the hip-height center.
	body = _pivot(horse, Vector3(0, 1.1, 0))
	var d := {}
	_box(d, Vector3i(-6, -1, -2), Vector3i(12, 5, 4), coat)
	_box(d, Vector3i(-6, 3, -2), Vector3i(12, 1, 4), coat.lightened(0.08))  # back
	_box(d, Vector3i(-1, 0, -2), Vector3i(3, 2, 4), dark, 0.02)  # saddle blanket
	_box(d, Vector3i(-1, 4, -2), Vector3i(3, 1, 4), dark, 0.02)
	body.add_child(_mesh(d))
	# Neck + head
	neck = _pivot(body, Vector3(5 * V, 3 * V, 0))
	d = {}
	for i in 5:
		_box(d, Vector3i(i, i, -1), Vector3i(3, 3, 2), coat)
		_box(d, Vector3i(i - 1, i + 1, 0), Vector3i(1, 3, 1), dark, 0.02)  # mane
	_box(d, Vector3i(4, 5, -2), Vector3i(6, 3, 4), coat)  # skull
	_box(d, Vector3i(9, 4, -2), Vector3i(4, 3, 4), coat.lightened(0.1))  # muzzle
	_box(d, Vector3i(12, 4, -2), Vector3i(1, 2, 4), white, 0.02)  # nose
	_box(d, Vector3i(5, 8, -2), Vector3i(1, 2, 1), dark, 0.02)  # ears
	_box(d, Vector3i(5, 8, 1), Vector3i(1, 2, 1), dark, 0.02)
	_box(d, Vector3i(8, 7, -3), Vector3i(1, 1, 1), Color.BLACK, 0.0)  # eyes
	_box(d, Vector3i(8, 7, 2), Vector3i(1, 1, 1), Color.BLACK, 0.0)
	neck.add_child(_mesh(d))
	# Tail
	tail = _pivot(body, Vector3(-6 * V, 3 * V, 0))
	d = {}
	_box(d, Vector3i(-2, -1, -1), Vector3i(2, 2, 2), dark, 0.03)
	_box(d, Vector3i(-3, -6, -1), Vector3i(2, 5, 2), dark, 0.03)
	_box(d, Vector3i(-3, -8, 0), Vector3i(1, 2, 1), dark, 0.03)
	tail.add_child(_mesh(d))
	# Legs: [x offset (voxels), z offset, phase, hind?]
	var specs := [[4, -2, 0.0, false], [4, 1, 0.35, false], [-6, -2, 3.1, true], [-6, 1, 3.45, true]]
	for s in specs:
		var hip := _pivot(horse, Vector3(s[0] * V, 1.1, s[1] * V))
		var ud := {}
		_box(ud, Vector3i(0, -5, 0), Vector3i(2, 5, 2), coat)
		hip.add_child(_mesh(ud))
		var knee := _pivot(hip, Vector3(0, -5 * V, 0))
		var ld := {}
		_box(ld, Vector3i(0, -5, 0), Vector3i(2, 5, 2), coat.darkened(0.1))
		_box(ld, Vector3i(0, -6, 0), Vector3i(2, 1, 2), dark, 0.02)  # hoof
		_box(ld, Vector3i(0, -4, 0), Vector3i(2, 1, 2), white, 0.02)  # sock
		knee.add_child(_mesh(ld))
		legs.append({"upper": hip, "lower": knee, "phase": s[2], "hind": s[3]})

func _build_scenery() -> void:
	var g := {}
	_box(g, Vector3i(-400, -4, -200), Vector3i(800, 4, 400), Color(0.36, 0.62, 0.25), 0.06)
	var ground := _mesh(g)
	ground.scale = Vector3(1, 1, 1)
	ground.position.y = 0.0
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ground)
	# Dirt track
	var tr := {}
	_box(tr, Vector3i(-400, -1, -12), Vector3i(800, 1, 24), Color(0.62, 0.5, 0.33), 0.05)
	var track := _mesh(tr)
	track.position.y = 0.0
	track.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(track)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in 60:
		var kind := rng.randi() % 3
		var node: MeshInstance3D
		if kind == 0:
			node = _mesh(_tree(rng))
		elif kind == 1:
			node = _mesh(_rock(rng))
		else:
			node = _mesh(_flowers(rng))
		var z := rng.randf_range(2.5, 12.0) * (1 if rng.randi() % 2 == 0 else -1)
		if kind == 2:
			z = rng.randf_range(-2.5, 2.5) + (1.6 if rng.randi() % 2 == 0 else -1.6)
		node.position = Vector3(-15.0 + 40.0 * i / 60.0, 0, z)
		node.rotation.y = rng.randf() * TAU
		scenery.add_child(node)
	# Track markers so the ground visibly moves
	for i in 20:
		var m := {}
		_box(m, Vector3i(0, 0, 0), Vector3i(8, 1, 2), Color(0.5, 0.4, 0.26), 0.02)
		var mm := _mesh(m)
		mm.position = Vector3(-15.0 + 2.0 * i, 0, 0.9 if i % 2 == 0 else -1.1)
		mm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		scenery.add_child(mm)

func _tree(rng: RandomNumberGenerator) -> Dictionary:
	var d := {}
	var h := rng.randi_range(8, 14)
	_box(d, Vector3i(0, 0, 0), Vector3i(2, h, 2), Color(0.4, 0.26, 0.14))
	var r := rng.randi_range(4, 6)
	_box(d, Vector3i(1 - r, h, 1 - r), Vector3i(r * 2, 4, r * 2), Color(0.2, 0.5, 0.2), 0.1)
	_box(d, Vector3i(2 - r, h + 4, 2 - r), Vector3i(r * 2 - 2, 3, r * 2 - 2), Color(0.25, 0.56, 0.22), 0.1)
	return d

func _rock(rng: RandomNumberGenerator) -> Dictionary:
	var d := {}
	var s := rng.randi_range(3, 5)
	_box(d, Vector3i(0, 0, 0), Vector3i(s, s - 1, s), Color(0.5, 0.5, 0.52), 0.1)
	_box(d, Vector3i(1, s - 1, 1), Vector3i(s - 2, 1, s - 2), Color(0.55, 0.55, 0.57), 0.1)
	return d

func _flowers(rng: RandomNumberGenerator) -> Dictionary:
	var d := {}
	var cols := [Color(0.95, 0.3, 0.4), Color(0.98, 0.85, 0.2), Color(0.9, 0.9, 0.98)]
	for i in 4:
		var p := Vector3i(rng.randi_range(0, 5), 0, rng.randi_range(0, 5))
		_box(d, p, Vector3i(1, 2, 1), Color(0.2, 0.5, 0.2), 0.02)
		_box(d, p + Vector3i(0, 2, 0), Vector3i(1, 1, 1), cols[rng.randi() % 3], 0.02)
	return d

# ---------- update ----------

func _process(delta: float) -> void:
	if Input.is_key_pressed(KEY_UP):
		speed = minf(speed + delta, 2.0)
	if Input.is_key_pressed(KEY_DOWN):
		speed = maxf(speed - delta, 0.0)
	if Input.is_key_pressed(KEY_LEFT):
		cam_angle -= delta
	if Input.is_key_pressed(KEY_RIGHT):
		cam_angle += delta

	var stride := 11.0 * speed
	t += delta * stride
	var world_speed := 9.0 * speed
	for c: Node3D in scenery.get_children():
		c.position.x -= world_speed * delta
		if c.position.x < -15.0:
			c.position.x += 40.0

	for l in legs:
		var a: float = t + l.phase
		var swing := 0.7 if l.hind else 0.8
		l.upper.rotation.z = sin(a) * swing * minf(speed, 1.2)
		var bend := maxf(0.0, sin(a + 1.6)) * 1.5 * minf(speed, 1.2)
		l.lower.rotation.z = -bend
	horse.position.y = absf(sin(t * 0.5 + 0.5)) * 0.12 * speed
	body.rotation.z = sin(t) * 0.05 * speed
	neck.rotation.z = -0.25 + sin(t + 0.6) * 0.1 * speed
	tail.rotation.z = -0.5 * speed + sin(t * 1.0 + 1.0) * 0.15 * speed

	var target := Vector3(0, 0.9, 0)
	cam.position = target + Vector3(sin(cam_angle) * 4.5, 0.7, cos(cam_angle) * 4.5)
	cam.look_at(target)
