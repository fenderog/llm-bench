extends Node3D
## Endless voxel meadow, generated in chunks around the horse.
## Trees and rocks block the way, logs and rocks can be jumped, carrots can be collected.

signal carrot_collected
signal obstacle_cleared

const Voxel := preload("res://scripts/voxel.gd")

const CHUNK := 32 # chunk size in meters (one ground tile per meter)
const RADIUS := 3 # chunks kept loaded around the horse
const SPAWN_CLEAR := 14.0 # keep the start area free of obstacles
const HORSE_RADIUS := 0.35

const BARK := Color(0.4, 0.27, 0.16)
const WOOD := Color(0.78, 0.62, 0.4)
const LEAF := Color(0.24, 0.5, 0.16)
const LEAF_LIGHT := Color(0.34, 0.6, 0.2)
const PINE := Color(0.13, 0.36, 0.2)
const STONE := Color(0.52, 0.53, 0.55)
const STONE_DARK := Color(0.42, 0.43, 0.46)
const MOSS := Color(0.36, 0.52, 0.2)
const GRASS := Color(0.3, 0.56, 0.18)
const PATH := Color(0.66, 0.53, 0.35)

var _chunks := {} # Vector2i -> Dictionary
var _meshes := {} # prop name -> Mesh
var _collected := {} # carrot id -> true
var _path_noise := FastNoiseLite.new()
var _grass_noise := FastNoiseLite.new()
var _time := 0.0


func _ready() -> void:
	_path_noise.seed = 1337
	_path_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_path_noise.frequency = 0.011
	_grass_noise.seed = 42
	_grass_noise.frequency = 0.07
	_build_meshes()


func is_path(x: float, z: float) -> bool:
	return absf(_path_noise.get_noise_2d(x, z)) < 0.03


func chunk_of(pos: Vector3) -> Vector2i:
	return Vector2i(floori(pos.x / CHUNK), floori(pos.z / CHUNK))


## Loads missing chunks near `pos` (nearest first) and frees distant ones.
func update_around(pos: Vector3, load_all := false) -> void:
	var center := chunk_of(pos)
	var missing: Array[Vector2i] = []
	for dx in range(-RADIUS, RADIUS + 1):
		for dz in range(-RADIUS, RADIUS + 1):
			var c := center + Vector2i(dx, dz)
			if not _chunks.has(c):
				missing.append(c)
	missing.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return (a - center).length_squared() < (b - center).length_squared())
	var budget := missing.size() if load_all else 1
	for i in mini(budget, missing.size()):
		_chunks[missing[i]] = _make_chunk(missing[i])

	for c in _chunks.keys():
		var d: Vector2i = c - center
		if maxi(absi(d.x), absi(d.y)) > RADIUS + 1:
			_chunks[c].root.queue_free()
			_chunks.erase(c)


func _process(delta: float) -> void:
	_time += delta
	for ch in _chunks.values():
		for car in ch.carrots:
			var node: Node3D = car.node
			node.rotation.y = _time * 2.5
			node.position.y = 0.95 + sin(_time * 3.0 + car.bob) * 0.12


## Resolves collisions between the horse and nearby obstacles, and picks up carrots.
func handle_horse(horse: Node3D) -> void:
	var fwd: Vector3 = horse.forward()
	var center := chunk_of(horse.position)
	for dx in range(-1, 2):
		for dz in range(-1, 2):
			var ch = _chunks.get(center + Vector2i(dx, dz))
			if ch == null:
				continue
			for o in ch.obstacles:
				_collide(horse, o, fwd)
			var carrots: Array = ch.carrots
			for i in range(carrots.size() - 1, -1, -1):
				var car: Dictionary = carrots[i]
				var node: Node3D = car.node
				var chest: Vector3 = horse.position + fwd * 0.9
				var d := Vector2(chest.x - node.global_position.x, chest.z - node.global_position.z)
				if d.length() < 1.3 and horse.height < 1.6:
					_collected[car.id] = true
					node.queue_free()
					carrots.remove_at(i)
					carrot_collected.emit()


func _collide(horse: Node3D, o: Dictionary, fwd: Vector3) -> void:
	if o.type == "bush":
		return
	var points := [horse.position + fwd * 0.85, horse.position, horse.position - fwd * 0.7]
	var over := false
	for i in points.size():
		var p: Vector3 = points[i]
		var p2 := Vector2(p.x, p.z)
		if o.type == "log":
			var rel: Vector2 = p2 - o.pos
			var side := Vector2(-o.dir.y, o.dir.x)
			var along := rel.dot(o.dir)
			var across := rel.dot(side)
			var reach: float = o.half_w + HORSE_RADIUS
			if absf(along) > o.half_len + HORSE_RADIUS or absf(across) > reach:
				continue
			if horse.height > o.top:
				over = true
				continue
			var s := 1.0 if across >= 0.0 else -1.0
			var push := side * s * (reach - absf(across))
			horse.position += Vector3(push.x, 0.0, push.y)
			if i == 0 and horse.speed > 2.5:
				horse.bump()
		else:
			var d: Vector2 = p2 - o.pos
			var r: float = o.r + HORSE_RADIUS
			if d.length_squared() >= r * r:
				continue
			if horse.height > o.top:
				over = true
				continue
			var n := d.normalized() if d.length_squared() > 0.0001 else Vector2(-fwd.x, -fwd.z)
			var push := n * (r - d.length())
			horse.position += Vector3(push.x, 0.0, push.y)
			if i == 0 and horse.speed > 2.5 and Vector2(fwd.x, fwd.z).dot(-n) > 0.6:
				horse.bump()
	if over and horse.airborne and not o.cleared:
		o.cleared = true
		obstacle_cleared.emit()


## Fraction (0..1) of the way from `from` to `to` that is clear of tree crowns and bushes.
## Used to keep the camera from ending up inside foliage.
func camera_clearance(from: Vector3, to: Vector3) -> float:
	var a := Vector2(from.x, from.z)
	var d := Vector2(to.x, to.z) - a
	var dd := d.length_squared()
	if dd < 0.0001:
		return 1.0
	var best := 1.0
	var center := chunk_of(from)
	for dx in range(-1, 2):
		for dz in range(-1, 2):
			var ch = _chunks.get(center + Vector2i(dx, dz))
			if ch == null:
				continue
			for o in ch.obstacles:
				if not o.has("crown"):
					continue
				var f: Vector2 = a - o.pos
				var c: float = f.length_squared() - o.crown * o.crown
				if c < 0.0:
					continue # the horse itself is under this tree
				var b := 2.0 * f.dot(d)
				var disc := b * b - 4.0 * dd * c
				if disc < 0.0:
					continue
				var t := (-b - sqrt(disc)) / (2.0 * dd)
				if t >= 0.0 and t < best:
					best = t
	return best


# --- Chunk generation ---------------------------------------------------------

func _ground_color(x: int, z: int) -> Color:
	var r := Voxel.noise01(Vector3i(x, 7, z))
	if is_path(x + 0.5, z + 0.5):
		return PATH * (0.93 + r * 0.1)
	var g := _grass_noise.get_noise_2d(x + 0.5, z + 0.5) * 0.5 + 0.5
	var c := GRASS.lerp(Color(0.42, 0.66, 0.22), g)
	if r > 0.97:
		c = c.lerp(Color(0.6, 0.7, 0.25), 0.5)
	return c * (0.95 + r * 0.08)


func _ground_mesh(c: Vector2i) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	var ox := c.x * CHUNK
	var oz := c.y * CHUNK
	for x in CHUNK:
		for z in CHUNK:
			var col := _ground_color(ox + x, oz + z)
			col.a = 1.0
			Voxel.add_quad(verts, normals, colors, indices, Vector3(x, 0, z),
					Vector3(0, 0, 1), Vector3(1, 0, 0), Vector3.UP, col)
	return Voxel.commit(verts, normals, colors, indices)


func _free_spot(rng: RandomNumberGenerator, origin: Vector3, taken: Array, min_dist: float,
		want_path := false, avoid_path := true) -> Variant:
	for attempt in 24:
		var local := Vector3(rng.randf() * CHUNK, 0.0, rng.randf() * CHUNK)
		var world := local + origin
		if Vector2(world.x, world.z).length() < SPAWN_CLEAR:
			continue
		var on_path := is_path(world.x, world.z)
		if want_path and not on_path and attempt < 20:
			continue
		if avoid_path and on_path:
			continue
		var ok := true
		for t in taken:
			if (t as Vector3).distance_to(local) < min_dist:
				ok = false
				break
		if ok:
			taken.append(local)
			return local
	return null


func _make_chunk(c: Vector2i) -> Dictionary:
	var origin := Vector3(c.x * CHUNK, 0, c.y * CHUNK)
	var root := Node3D.new()
	root.position = origin
	add_child(root)

	var ground := MeshInstance3D.new()
	ground.mesh = _ground_mesh(c)
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(ground)

	var rng := RandomNumberGenerator.new()
	rng.seed = hash(c) ^ 0x5EED
	var data := {"root": root, "obstacles": [], "carrots": []}
	var xforms := {}
	for k in _meshes:
		xforms[k] = []
	var taken := []

	# Trees.
	for i in rng.randi_range(3, 8):
		var p = _free_spot(rng, origin, taken, 3.5)
		if p == null:
			continue
		var kind := "pine" if rng.randf() < 0.4 else "oak"
		var sc := rng.randf_range(0.8, 1.3)
		xforms[kind].append(Transform3D(Basis(Vector3.UP, rng.randi_range(0, 3) * PI * 0.5).scaled(Vector3.ONE * sc), p))
		data.obstacles.append({"type": "tree", "pos": Vector2(p.x + origin.x, p.z + origin.z),
				"r": 0.32 * sc, "top": 999.0, "crown": (1.6 if kind == "pine" else 1.5) * sc, "cleared": false})

	# Rocks (jumpable).
	for i in rng.randi_range(1, 3):
		var p = _free_spot(rng, origin, taken, 3.0)
		if p == null:
			continue
		var sc := rng.randf_range(0.7, 1.2)
		xforms.rock.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * sc), p))
		data.obstacles.append({"type": "rock", "pos": Vector2(p.x + origin.x, p.z + origin.z),
				"r": 0.55 * sc, "top": 0.4 * sc, "cleared": false})

	# Fallen logs, preferably across the path.
	if rng.randf() < 0.7:
		var p = _free_spot(rng, origin, taken, 4.0, true, false)
		if p != null:
			var yaw := rng.randf() * PI
			xforms.log.append(Transform3D(Basis(Vector3.UP, yaw), p))
			data.obstacles.append({"type": "log", "pos": Vector2(p.x + origin.x, p.z + origin.z),
					"dir": Vector2(cos(yaw), -sin(yaw)), "half_len": 1.65, "half_w": 0.3,
					"top": 0.4, "cleared": false})

	# Decoration without collision.
	for i in rng.randi_range(2, 5):
		var p = _free_spot(rng, origin, taken, 2.0)
		if p != null:
			var sc := rng.randf_range(0.7, 1.2)
			xforms.bush.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * sc), p))
			data.obstacles.append({"type": "bush", "pos": Vector2(p.x + origin.x, p.z + origin.z), "crown": 0.8 * sc})
	for i in 70:
		var p := Vector3(rng.randf() * CHUNK, 0, rng.randf() * CHUNK)
		if not is_path(p.x + origin.x, p.z + origin.z):
			xforms.grass.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * rng.randf_range(0.8, 1.4)), p))
	for i in 12:
		var p := Vector3(rng.randf() * CHUNK, 0, rng.randf() * CHUNK)
		if not is_path(p.x + origin.x, p.z + origin.z):
			xforms.flowers.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU), p))
	if rng.randf() < 0.3:
		var p := Vector3(rng.randf() * CHUNK, rng.randf_range(28.0, 40.0), rng.randf() * CHUNK)
		xforms.cloud.append(Transform3D(Basis(Vector3.UP, rng.randi_range(0, 1) * PI * 0.5).scaled(Vector3.ONE * rng.randf_range(0.8, 1.5)), p))

	for k in xforms:
		var list: Array = xforms[k]
		if list.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = _meshes[k]
		mm.instance_count = list.size()
		for i in list.size():
			mm.set_instance_transform(i, list[i])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		if k in ["grass", "flowers", "cloud"]:
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mmi)

	# Carrots to collect, mostly along the path.
	for i in rng.randi_range(1, 3):
		var id := "%d,%d,%d" % [c.x, c.y, i]
		var p = _free_spot(rng, origin, taken, 2.0, rng.randf() < 0.6, false)
		if p == null or _collected.has(id):
			continue
		var mi := MeshInstance3D.new()
		mi.mesh = _meshes.carrot_single
		mi.position = p + Vector3(0, 0.95, 0)
		mi.rotation.z = 0.35
		mi.scale = Vector3.ONE * 1.5
		root.add_child(mi)
		data.carrots.append({"node": mi, "id": id, "bob": rng.randf() * TAU})

	return data


# --- Prop meshes ----------------------------------------------------------------

func _build_meshes() -> void:
	# Oak tree.
	var v := {}
	Voxel.ellipsoid(v, Vector3(0, 10.5, 0), Vector3(4.6, 3.6, 4.6), LEAF)
	Voxel.ellipsoid(v, Vector3(1.5, 12.5, -1), Vector3(3, 2.4, 3), LEAF_LIGHT)
	Voxel.ellipsoid(v, Vector3(-2, 9, 1.5), Vector3(2.6, 2.2, 2.6), LEAF)
	Voxel.box(v, Vector3i(-1, 0, -1), Vector3i(1, 9, 1), BARK)
	Voxel.box(v, Vector3i(1, 6, 0), Vector3i(3, 7, 1), BARK)
	Voxel.box(v, Vector3i(-1, 0, -2), Vector3i(0, 1, 2), BARK)
	_meshes.oak = Voxel.build(v, 0.3, Vector3.ZERO, 0.12)

	# Pine tree.
	v = {}
	Voxel.box(v, Vector3i(-1, 0, -1), Vector3i(1, 5, 1), BARK)
	for k in 4:
		for dy in 4:
			var r := (4.4 - k * 0.9) * (1.0 - dy / 4.0) + 0.9
			for x in range(-6, 6):
				for z in range(-6, 6):
					if Vector2(x + 0.5, z + 0.5).length() <= r:
						v[Vector3i(x, 3 + k * 3 + dy, z)] = PINE if dy > 0 else PINE.darkened(0.2)
	Voxel.box(v, Vector3i(-1, 15, -1), Vector3i(1, 17, 1), PINE)
	_meshes.pine = Voxel.build(v, 0.3, Vector3.ZERO, 0.1)

	# Rock.
	v = {}
	Voxel.ellipsoid(v, Vector3(0, 0, 0), Vector3(3.2, 2.6, 2.7), STONE, 0)
	Voxel.ellipsoid(v, Vector3(1.2, 0, 1.0), Vector3(2.2, 2.9, 2.0), STONE_DARK, 0)
	for key in v.keys():
		if key.y >= 2 and Voxel.noise01(key) < 0.3:
			v[key] = MOSS
	_meshes.rock = Voxel.build(v, 0.2, Vector3.ZERO, 0.1)

	# Bush with berries.
	v = {}
	Voxel.ellipsoid(v, Vector3(0, 1, 0), Vector3(2.8, 2.4, 2.8), LEAF.darkened(0.1), 0)
	for key in v.keys():
		if Voxel.noise01(key) < 0.06:
			v[key] = Color(0.8, 0.15, 0.15)
	_meshes.bush = Voxel.build(v, 0.25, Vector3.ZERO, 0.12)

	# Grass tuft.
	v = {}
	for b in [[0, 0, 5], [2, 1, 4], [-2, 1, 3], [1, -2, 4], [-1, -1, 6], [3, -1, 3], [-3, -2, 2], [0, 2, 3]]:
		var col := GRASS.lerp(Color(0.5, 0.72, 0.25), Voxel.noise01(Vector3i(b[0], b[1], b[2])))
		Voxel.box(v, Vector3i(b[0], 0, b[1]), Vector3i(b[0] + 1, b[2], b[1] + 1), col)
	_meshes.grass = Voxel.build(v, 0.08, Vector3.ZERO, 0.15)

	# Flower clump.
	v = {}
	var petals := [Color(0.95, 0.3, 0.35), Color(1.0, 0.85, 0.2), Color(0.95, 0.95, 0.95), Color(0.65, 0.4, 0.9)]
	var spots := [Vector3i(0, 3, 0), Vector3i(4, 2, 1), Vector3i(-3, 4, 3), Vector3i(1, 2, -4)]
	for i in spots.size():
		var s: Vector3i = spots[i]
		Voxel.box(v, Vector3i(s.x, 0, s.z), Vector3i(s.x + 1, s.y, s.z + 1), Color(0.25, 0.5, 0.15))
		for d in [Vector3i(1, 0, 0), Vector3i(-1, 0, 0), Vector3i(0, 0, 1), Vector3i(0, 0, -1)]:
			v[s + d] = petals[i]
		v[s] = Color(1.0, 0.8, 0.2) if i != 1 else Color(0.5, 0.3, 0.1)
	_meshes.flowers = Voxel.build(v, 0.1, Vector3.ZERO, 0.05)

	# Fallen log.
	v = {}
	for x in range(-11, 11):
		for y in 4:
			for z in range(-2, 2):
				if (y == 0 or y == 3) and (z == -2 or z == 1):
					continue
				var inner := (y == 1 or y == 2) and (z == -1 or z == 0)
				v[Vector3i(x, y, z)] = WOOD if inner and (x == -11 or x == 10) else BARK
	for x in range(-8, 8, 3):
		v[Vector3i(x, 4, -1)] = MOSS
	_meshes.log = Voxel.build(v, 0.15, Vector3.ZERO, 0.12)

	# Cloud.
	v = {}
	Voxel.box(v, Vector3i(-4, 0, -2), Vector3i(4, 2, 2), Color.WHITE)
	Voxel.box(v, Vector3i(-2, 2, -1), Vector3i(3, 3, 2), Color.WHITE)
	Voxel.box(v, Vector3i(-6, 0, -1), Vector3i(-4, 1, 1), Color.WHITE)
	Voxel.box(v, Vector3i(4, 0, -1), Vector3i(6, 1, 2), Color.WHITE)
	_meshes.cloud = Voxel.build(v, 1.6, Vector3.ZERO, 0.02)

	# Carrot (placed individually, not in a MultiMesh).
	v = {}
	for y in 7:
		var r := 0.5 + y * 0.28
		for x in range(-3, 3):
			for z in range(-3, 3):
				if Vector2(x + 0.5, z + 0.5).length() <= r:
					v[Vector3i(x, y, z)] = Color(1.0, 0.5, 0.1)
	var green := Color(0.3, 0.7, 0.2)
	Voxel.box(v, Vector3i(-1, 7, -1), Vector3i(1, 8, 1), green)
	Voxel.box(v, Vector3i(-1, 8, 0), Vector3i(0, 10, 1), green)
	Voxel.box(v, Vector3i(0, 8, -1), Vector3i(1, 9, 0), green)
	_meshes.carrot_single = Voxel.build(v, 0.1, Vector3(0, 4, 0), 0.08)
