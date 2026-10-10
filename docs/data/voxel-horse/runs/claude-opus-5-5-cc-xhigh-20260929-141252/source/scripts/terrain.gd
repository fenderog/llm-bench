extends Node3D
## Endless voxel meadow streamed in 16 x 16 m chunks around a focus point.
## Block tops are quantised to 0.25 m terraces. Trees, rocks, flowers and grass
## are baked into each chunk's mesh so a whole chunk is a single draw call.

const MeshData = preload("res://scripts/mesh_data.gd")
const VoxelModel = preload("res://scripts/voxel_model.gd")

const CHUNK := 16
const VIEW_RADIUS := 5
const STEP := 0.25
const WATER_LEVEL := -1.4
const CHUNKS_PER_FRAME := 2
const SPAWN_CLEARING := 14.0

const GRASS := Color(0.4, 0.6, 0.27)
const GRASS_DRY := Color(0.58, 0.64, 0.33)
const GRASS_SIDE := Color(0.36, 0.52, 0.24)
const DIRT := Color(0.47, 0.34, 0.22)
const SAND := Color(0.87, 0.8, 0.56)
const WET_SAND := Color(0.6, 0.53, 0.38)
const STONE := Color(0.56, 0.56, 0.55)
const TRUNK := Color(0.4, 0.27, 0.16)
const FLOWER_COLORS: Array[Color] = [
	Color(0.95, 0.25, 0.2), Color(1.0, 0.85, 0.2), Color(0.98, 0.97, 0.95),
	Color(0.7, 0.4, 0.9), Color(1.0, 0.55, 0.75), Color(0.35, 0.55, 1.0),
]

var world_seed := 0
var spawn := Vector2.ZERO
var _hills := FastNoiseLite.new()
var _detail := FastNoiseLite.new()
var _forest := FastNoiseLite.new()
var _material: StandardMaterial3D
var _water: MeshInstance3D
var _chunks := {}      # Vector2i -> MeshInstance3D
var _obstacles := {}   # Vector2i -> Array[Vector3] of (x, z, radius)
var _queue: Array[Vector2i] = []
var _center := Vector2i(1 << 20, 1 << 20)
var _oaks: Array[MeshData] = []
var _pines: Array[MeshData] = []
var _birches: Array[MeshData] = []
var _rocks: Array[MeshData] = []


func setup(seed_value: int) -> void:
	world_seed = seed_value
	_hills.seed = seed_value
	_hills.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_hills.frequency = 0.007
	_hills.fractal_octaves = 3
	_detail.seed = seed_value + 1
	_detail.frequency = 0.05
	_detail.fractal_type = FastNoiseLite.FRACTAL_NONE
	_forest.seed = seed_value + 2
	_forest.frequency = 0.012
	_forest.fractal_octaves = 2
	_material = MeshData.make_material()
	_build_props()
	_create_water()
	spawn = _find_spawn()


# --- Height field -----------------------------------------------------------

## Smooth height before quantisation. Lakes are squashed so they stay shallow.
func raw_height(x: float, z: float) -> float:
	var h := _hills.get_noise_2d(x, z) * 8.0 + _detail.get_noise_2d(x, z) * 0.9 + 1.0
	if h < WATER_LEVEL:
		h = WATER_LEVEL - (WATER_LEVEL - h) * 0.15
	return h


## Top of the block column at integer coordinates.
func column_height(ix: int, iz: int) -> float:
	return floorf(raw_height(ix + 0.5, iz + 0.5) / STEP) * STEP


## Ground height for walking: bilinear between neighbouring block tops.
func ground_at(x: float, z: float) -> float:
	var fx := x - 0.5
	var fz := z - 0.5
	var ix := floori(fx)
	var iz := floori(fz)
	var tx := fx - ix
	var tz := fz - iz
	var h0 := lerpf(column_height(ix, iz), column_height(ix + 1, iz), tx)
	var h1 := lerpf(column_height(ix, iz + 1), column_height(ix + 1, iz + 1), tx)
	return lerpf(h0, h1, tz)


func _find_spawn() -> Vector2:
	for r in range(0, 400, 4):
		for k in 12:
			var a := TAU * k / 12.0
			var p := Vector2(cos(a), sin(a)) * r
			if raw_height(p.x, p.y) > WATER_LEVEL + 1.0:
				return p
	return Vector2.ZERO


# --- Obstacles ---------------------------------------------------------------

## Pushes a circle at `pos` out of any tree trunks or boulders it overlaps.
func push_out(pos: Vector3, radius: float) -> Vector3:
	var c := Vector2i(floori(pos.x / CHUNK), floori(pos.z / CHUNK))
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var list: Array = _obstacles.get(c + Vector2i(dx, dz), [])
			for o: Vector3 in list:
				var d := Vector2(pos.x - o.x, pos.z - o.y)
				var min_d := radius + o.z
				var l := d.length()
				if l < min_d and l > 0.0001:
					d = d / l * min_d
					pos.x = o.x + d.x
					pos.z = o.y + d.y
	return pos


# --- Streaming ---------------------------------------------------------------

## Queues chunks around `pos`; builds a few per call (all of them if `immediate`).
func update_around(pos: Vector3, immediate := false) -> void:
	_water.position = Vector3(roundf(pos.x), WATER_LEVEL, roundf(pos.z))
	var c := Vector2i(floori(pos.x / CHUNK), floori(pos.z / CHUNK))
	if c != _center:
		_center = c
		for key: Vector2i in _chunks.keys():
			if (key - c).length_squared() > (VIEW_RADIUS + 1) * (VIEW_RADIUS + 1):
				(_chunks[key] as Node).queue_free()
				_chunks.erase(key)
				_obstacles.erase(key)
		_queue.clear()
		var limit := (VIEW_RADIUS + 0.5) * (VIEW_RADIUS + 0.5)
		for dz in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
			for dx in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
				var key := c + Vector2i(dx, dz)
				if dx * dx + dz * dz <= limit and not _chunks.has(key):
					_queue.append(key)
		_queue.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
			return (a - c).length_squared() < (b - c).length_squared())
	var budget := _queue.size() if immediate else CHUNKS_PER_FRAME
	while budget > 0 and not _queue.is_empty():
		_build_chunk(_queue.pop_front())
		budget -= 1


func _build_chunk(key: Vector2i) -> void:
	var ox := key.x * CHUNK
	var oz := key.y * CHUNK
	var n := CHUNK + 2
	var hs := PackedFloat32Array()
	hs.resize(n * n)
	for j in n:
		for i in n:
			hs[j * n + i] = column_height(ox + i - 1, oz + j - 1)

	var md := MeshData.new()
	for j in CHUNK:
		for i in CHUNK:
			var h := hs[(j + 1) * n + i + 1]
			var x := float(i)
			var z := float(j)
			md.add_quad(Vector3(x, h, z), Vector3(0, 0, 1), Vector3(1, 0, 0), Vector3.UP,
					_top_color(ox + i, oz + j, h))
			var side := _side_color(h)
			var h_px := hs[(j + 1) * n + i + 2]
			var h_nx := hs[(j + 1) * n + i]
			var h_pz := hs[(j + 2) * n + i + 1]
			var h_nz := hs[j * n + i + 1]
			if h_px < h:
				md.add_quad_gradient(Vector3(x + 1, h_px, z + 1), Vector3(0, 0, -1), Vector3(0, h - h_px, 0),
						Vector3.RIGHT, _low_side(side, h - h_px), side)
			if h_nx < h:
				md.add_quad_gradient(Vector3(x, h_nx, z), Vector3(0, 0, 1), Vector3(0, h - h_nx, 0),
						Vector3.LEFT, _low_side(side, h - h_nx), side)
			if h_pz < h:
				md.add_quad_gradient(Vector3(x, h_pz, z + 1), Vector3(1, 0, 0), Vector3(0, h - h_pz, 0),
						Vector3.BACK, _low_side(side, h - h_pz), side)
			if h_nz < h:
				md.add_quad_gradient(Vector3(x + 1, h_nz, z), Vector3(-1, 0, 0), Vector3(0, h - h_nz, 0),
						Vector3.FORWARD, _low_side(side, h - h_nz), side)

	var obstacles: Array[Vector3] = []
	_decorate(key, hs, md, obstacles)
	_obstacles[key] = obstacles

	var mi := MeshInstance3D.new()
	mi.mesh = md.commit(_material)
	mi.position = Vector3(ox, 0, oz)
	add_child(mi)
	_chunks[key] = mi


func _top_color(wx: int, wz: int, h: float) -> Color:
	var jitter := 1.0 + (float(posmod(hash(Vector2i(wx, wz)), 1000)) / 999.0 - 0.5) * 0.12
	var c: Color
	if h < WATER_LEVEL - 0.01:
		c = WET_SAND
	elif h < WATER_LEVEL + 0.4:
		c = SAND
	elif h > 5.5:
		c = STONE if h > 6.5 else GRASS_DRY.lerp(STONE, 0.4)
	else:
		var dry := clampf(_detail.get_noise_2d(wx * 0.3, wz * 0.3) * 0.8 + h * 0.08, 0.0, 1.0)
		c = GRASS.lerp(GRASS_DRY, dry)
	return Color(c.r * jitter, c.g * jitter, c.b * jitter)


func _side_color(h: float) -> Color:
	if h < WATER_LEVEL + 0.4:
		return SAND.darkened(0.12)
	if h > 6.5:
		return STONE.darkened(0.1)
	return GRASS_SIDE


func _low_side(top: Color, drop: float) -> Color:
	return top.lerp(DIRT, clampf((drop - 0.25) * 1.5, 0.0, 1.0)).darkened(0.1)


# --- Decoration ---------------------------------------------------------------

func _decorate(key: Vector2i, hs: PackedFloat32Array, md: MeshData, obstacles: Array[Vector3]) -> void:
	var n := CHUNK + 2
	var ox := key.x * CHUNK
	var oz := key.y * CHUNK
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(key.x, key.y, world_seed))
	var forest := clampf(_forest.get_noise_2d(ox + 8, oz + 8) * 2.2 + 0.3, 0.0, 1.0)

	# Trees
	var tree_count := int(round(forest * 5.0 * rng.randf_range(0.4, 1.2) + rng.randf() * 0.7))
	for t in tree_count:
		var i := rng.randi_range(1, CHUNK - 2)
		var j := rng.randi_range(1, CHUNK - 2)
		var h := hs[(j + 1) * n + i + 1]
		var wx := ox + i + 0.5
		var wz := oz + j + 0.5
		if h < WATER_LEVEL + 0.6 or Vector2(wx, wz).distance_to(spawn) < SPAWN_CLEARING:
			continue
		var pool := _pines if h > 2.5 and rng.randf() < 0.75 else (_birches if rng.randf() < 0.3 else _oaks)
		var turn := Basis(Vector3.UP, rng.randi_range(0, 3) * PI * 0.5)
		md.append(pool[rng.randi() % pool.size()], Transform3D(turn, Vector3(i + 0.5, h, j + 0.5)))
		obstacles.append(Vector3(wx, wz, 0.5))

	# Rocks and boulders
	var rock_count := rng.randi_range(0, 2)
	for r in rock_count:
		var i := rng.randi_range(0, CHUNK - 1)
		var j := rng.randi_range(0, CHUNK - 1)
		var h := hs[(j + 1) * n + i + 1]
		var big := rng.randf() < 0.35
		if big and Vector2(ox + i + 0.5, oz + j + 0.5).distance_to(spawn) < SPAWN_CLEARING:
			continue
		var s := rng.randf_range(1.2, 1.8) if big else rng.randf_range(0.4, 0.7)
		var xf := Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * s), Vector3(i + 0.5, h - 0.1, j + 0.5))
		md.append(_rocks[rng.randi() % _rocks.size()], xf)
		if big:
			obstacles.append(Vector3(ox + i + 0.5, oz + j + 0.5, 0.55 * s))

	# Flowers, grass tufts and reeds
	var flower_count := rng.randi_range(3, 16)
	var patch_color := FLOWER_COLORS[rng.randi() % FLOWER_COLORS.size()]
	for f in flower_count:
		var x := rng.randf_range(0.2, CHUNK - 0.2)
		var z := rng.randf_range(0.2, CHUNK - 0.2)
		var h := hs[(int(z) + 1) * n + int(x) + 1]
		if h < WATER_LEVEL + 0.4 or h > 5.5:
			continue
		var col := patch_color if rng.randf() < 0.6 else FLOWER_COLORS[rng.randi() % FLOWER_COLORS.size()]
		var stem := rng.randf_range(0.14, 0.28)
		md.add_box(Vector3(x - 0.02, h, z - 0.02), Vector3(0.04, stem, 0.04), GRASS_SIDE)
		md.add_box(Vector3(x - 0.07, h + stem, z - 0.07), Vector3(0.14, 0.1, 0.14), col)

	var tuft_count := rng.randi_range(10, 22)
	for f in tuft_count:
		var x := rng.randf_range(0.3, CHUNK - 0.3)
		var z := rng.randf_range(0.3, CHUNK - 0.3)
		var h := hs[(int(z) + 1) * n + int(x) + 1]
		if h < WATER_LEVEL - 0.3 or h > 6.5:
			continue
		var reed := h < WATER_LEVEL + 0.3
		for b in 3:
			var bx := x + rng.randf_range(-0.12, 0.12)
			var bz := z + rng.randf_range(-0.12, 0.12)
			if reed:
				var tall := rng.randf_range(0.8, 1.3)
				md.add_box(Vector3(bx - 0.03, h, bz - 0.03), Vector3(0.06, tall, 0.06), Color(0.42, 0.55, 0.24))
				if b == 0:
					md.add_box(Vector3(bx - 0.05, h + tall - 0.25, bz - 0.05), Vector3(0.1, 0.22, 0.1), Color(0.4, 0.25, 0.12))
			else:
				var col := GRASS.darkened(rng.randf_range(0.05, 0.25))
				md.add_box(Vector3(bx - 0.035, h, bz - 0.035), Vector3(0.07, rng.randf_range(0.18, 0.38), 0.07), col)


func _build_props() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = world_seed + 99
	for v in 3:
		_oaks.append(_make_oak(rng, Color(0.25, 0.52, 0.2).lerp(Color(0.35, 0.6, 0.18), v * 0.4)))
	_oaks.append(_make_oak(rng, Color(0.88, 0.52, 0.16)))
	for v in 3:
		_pines.append(_make_pine(rng))
	for v in 2:
		_birches.append(_make_birch(rng))
	for v in 4:
		_rocks.append(_make_rock(rng))


func _make_oak(rng: RandomNumberGenerator, leaf: Color) -> MeshData:
	var m := VoxelModel.new()
	var trunk_h := rng.randi_range(6, 8)
	m.fill_box(Vector3i(-1, 0, -1), Vector3i(0, trunk_h, 0), TRUNK)
	var crown := Vector3(0, trunk_h + 3.0, 0)
	m.fill_blob(crown, Vector3(4.5, 3.5, 4.5), leaf, 2.2)
	for k in 3:
		var off := Vector3(rng.randf_range(-3, 3), rng.randf_range(-1, 1.5), rng.randf_range(-3, 3))
		m.fill_blob(crown + off, Vector3.ONE * rng.randf_range(2.0, 3.0), leaf, 2.0)
	var md := MeshData.new()
	m.bake(md, 0.4, Vector3.ZERO, 0.12)
	return md


func _make_pine(rng: RandomNumberGenerator) -> MeshData:
	var m := VoxelModel.new()
	var leaf := Color(0.15, 0.38, 0.22).lerp(Color(0.2, 0.45, 0.25), rng.randf())
	var layers := rng.randi_range(4, 5)
	m.fill_box(Vector3i(-1, 0, -1), Vector3i(0, 4 + layers * 3, 0), TRUNK.darkened(0.2))
	for k in layers:
		var r := 4.6 - k * 0.9
		m.fill_blob(Vector3(0, 5 + k * 3, 0), Vector3(r, 1.8, r), leaf, 1.6)
	m.fill_box(Vector3i(-1, 5 + layers * 3, -1), Vector3i(0, 6 + layers * 3, 0), leaf)
	var md := MeshData.new()
	m.bake(md, 0.4, Vector3.ZERO, 0.1)
	return md


func _make_birch(rng: RandomNumberGenerator) -> MeshData:
	var m := VoxelModel.new()
	var trunk_h := rng.randi_range(12, 15)
	m.fill_box(Vector3i(-1, 0, -1), Vector3i(0, trunk_h, 0), Color(0.9, 0.9, 0.86))
	m.recolor(func(_p: Vector3i, _c: Color) -> bool: return rng.randf() < 0.18, Color(0.15, 0.14, 0.13))
	var leaf := Color(0.56, 0.74, 0.26)
	m.fill_blob(Vector3(0, trunk_h + 1.5, 0), Vector3(3.8, 6.0, 3.8), leaf, 2.0)
	m.fill_blob(Vector3(rng.randf_range(-2, 2), trunk_h - 2.0, rng.randf_range(-2, 2)), Vector3(3, 3, 3), leaf, 2.0)
	var md := MeshData.new()
	m.bake(md, 0.3, Vector3.ZERO, 0.12)
	return md


func _make_rock(rng: RandomNumberGenerator) -> MeshData:
	var m := VoxelModel.new()
	var grey := STONE.darkened(rng.randf_range(0.0, 0.2))
	m.fill_blob(Vector3(0, 0.5, 0), Vector3(rng.randf_range(2.5, 3.5), rng.randf_range(2.0, 3.0), rng.randf_range(2.5, 3.5)), grey, 2.2)
	m.fill_blob(Vector3(rng.randf_range(-1.5, 1.5), 1.5, rng.randf_range(-1.5, 1.5)), Vector3(2.0, 2.0, 2.0), grey.lightened(0.08), 2.0)
	var md := MeshData.new()
	m.bake(md, 0.25, Vector3.ZERO, 0.1)
	return md


func _create_water() -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.22, 0.5, 0.78, 0.7)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.roughness = 0.15
	mat.metallic_specular = 0.8
	var plane := PlaneMesh.new()
	plane.size = Vector2(1, 1) * CHUNK * (VIEW_RADIUS * 2 + 3)
	plane.material = mat
	_water = MeshInstance3D.new()
	_water.mesh = plane
	_water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_water)
