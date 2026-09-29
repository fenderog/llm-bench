class_name Scenery
extends RefCounted
## Builds the shared voxel meshes used by the scrolling world.

const CELL := 0.25            # voxel size of the ground and most props, metres
const TILE_CELLS := 32        # cells along X per ground tile
const TILE_LENGTH := TILE_CELLS * CELL
const Z_CELLS := 36           # half-width of a ground tile, in cells
const PATH_HALF_WIDTH := 1.5  # the dirt track the horse runs on, metres

const GRASS := Color(0.28, 0.50, 0.19)
const GRASS_LIGHT := Color(0.34, 0.57, 0.22)
const GRASS_DARK := Color(0.19, 0.40, 0.16)
const DIRT := Color(0.56, 0.41, 0.27)
const DIRT_DARK := Color(0.45, 0.32, 0.20)
const PEBBLE := Color(0.60, 0.56, 0.50)
const WOOD := Color(0.55, 0.40, 0.26)
const TRUNK := Color(0.40, 0.26, 0.14)
const STONE := Color(0.52, 0.53, 0.56)
const FLOWERS: Array[Color] = [
	Color(0.97, 0.97, 0.92), Color(0.98, 0.84, 0.25), Color(0.93, 0.45, 0.62), Color(0.55, 0.60, 0.95),
]


static func ground_tile(seed_value: int) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var v := {}
	for i in TILE_CELLS:
		for k in range(-Z_CELLS, Z_CELLS):
			var z := (k + 0.5) * CELL
			var az := absf(z)
			var cell := Vector3i(i, -1, k)
			var patch := ((i >> 2) + (k >> 2)) & 1
			if az < PATH_HALF_WIDTH:
				var c := DIRT_DARK if az > PATH_HALF_WIDTH - CELL else DIRT
				if rng.randf() < 0.05:
					c = PEBBLE
				v[cell] = VoxelMesh.jittered(c, cell, 0.06)
				continue
			v[cell] = VoxelMesh.jittered(GRASS_LIGHT if patch == 1 else GRASS, cell, 0.07)
			# Tufts and flowers only on the far side; on the near side they would
			# loom in front of the camera.
			if az < 2.0 or z > 0.0:
				continue
			var r := rng.randf()
			var above := Vector3i(i, 0, k)
			if r < 0.05:
				v[above] = VoxelMesh.jittered(GRASS_DARK, above, 0.1)
			elif r < 0.062:
				v[above] = FLOWERS[rng.randi() % FLOWERS.size()]
	return VoxelMesh.build(v, CELL, true)


## A 8 m stretch of post-and-rail fence along +X (one tile long).
static func fence() -> ArrayMesh:
	var v := {}
	for post in 4:
		var x := post * 16
		VoxelMesh.fill_box(v, Vector3i(x, 0, 0), Vector3i(x + 1, 8, 1), WOOD, 0.08)
	for y in [3, 6]:
		VoxelMesh.fill_box(v, Vector3i(0, y, 0), Vector3i(63, y + 1, 0), WOOD, 0.06)
	return VoxelMesh.build(v, CELL * 0.5)


static func tree(leaf: Color) -> ArrayMesh:
	var v := {}
	VoxelMesh.fill_box(v, Vector3i(-1, 0, -1), Vector3i(0, 5, 0), TRUNK, 0.08)
	VoxelMesh.fill_box(v, Vector3i(-4, 6, -4), Vector3i(3, 8, 3), leaf, 0.10)
	for corner in [Vector3i(-4, 0, -4), Vector3i(3, 0, -4), Vector3i(-4, 0, 3), Vector3i(3, 0, 3)]:
		VoxelMesh.erase_box(v, Vector3i(corner.x, 6, corner.z), Vector3i(corner.x, 8, corner.z))
	VoxelMesh.fill_box(v, Vector3i(-3, 9, -3), Vector3i(2, 11, 2), leaf, 0.10)
	VoxelMesh.fill_box(v, Vector3i(-2, 12, -2), Vector3i(1, 13, 1), leaf, 0.10)
	return VoxelMesh.build(v, CELL)


static func pine() -> ArrayMesh:
	var v := {}
	var leaf := Color(0.14, 0.38, 0.22)
	VoxelMesh.fill_box(v, Vector3i(-1, 0, -1), Vector3i(0, 3, 0), TRUNK, 0.08)
	VoxelMesh.fill_box(v, Vector3i(-4, 3, -4), Vector3i(3, 4, 3), leaf, 0.10)
	VoxelMesh.fill_box(v, Vector3i(-3, 5, -3), Vector3i(2, 6, 2), leaf, 0.10)
	VoxelMesh.fill_box(v, Vector3i(-2, 7, -2), Vector3i(1, 8, 1), leaf, 0.10)
	VoxelMesh.fill_box(v, Vector3i(-1, 9, -1), Vector3i(0, 11, 0), leaf, 0.10)
	return VoxelMesh.build(v, CELL)


static func bush(leaf: Color) -> ArrayMesh:
	var v := {}
	VoxelMesh.fill_box(v, Vector3i(-2, 0, -2), Vector3i(1, 1, 1), leaf, 0.10)
	VoxelMesh.fill_box(v, Vector3i(-1, 2, -1), Vector3i(0, 2, 0), leaf, 0.10)
	return VoxelMesh.build(v, CELL)


static func rock() -> ArrayMesh:
	var v := {}
	VoxelMesh.fill_box(v, Vector3i(-2, 0, -1), Vector3i(1, 1, 1), STONE, 0.08)
	VoxelMesh.fill_box(v, Vector3i(-1, 2, -1), Vector3i(0, 2, 0), STONE, 0.08)
	return VoxelMesh.build(v, CELL)


static func cloud(rng: RandomNumberGenerator) -> ArrayMesh:
	var v := {}
	var white := Color(0.98, 0.99, 1.0)
	VoxelMesh.fill_box(v, Vector3i(0, 0, 0), Vector3i(rng.randi_range(7, 11), 1, rng.randi_range(3, 5)), white, 0.03)
	for n in 3:
		var x := rng.randi_range(1, 6)
		var z := rng.randi_range(0, 2)
		VoxelMesh.fill_box(v, Vector3i(x, 2, z), Vector3i(x + rng.randi_range(2, 4), 2, z + rng.randi_range(1, 2)), white, 0.03)
	return VoxelMesh.build(v, 1.6)


## A ridge of hills, `cells` columns long, that dips to nothing at both ends
## so neighbouring segments join up.
static func mountains(rng: RandomNumberGenerator, cells: int, cell_size: float) -> ArrayMesh:
	var v := {}
	var phase_a := rng.randf() * TAU
	var phase_b := rng.randf() * TAU
	for i in cells:
		var edge := minf(1.0, minf(i / 10.0, (cells - 1 - i) / 10.0))
		var h := (5.0 + 4.0 * absf(sin(i * 0.09 + phase_a)) + 2.5 * sin(i * 0.31 + phase_b)) * edge
		var top := maxi(1, int(h))
		for y in top:
			var color := Color(0.30, 0.45, 0.40) if y < 2 else Color(0.44, 0.50, 0.62)
			if top > 8 and y >= top - 2:
				color = Color(0.94, 0.96, 1.0)
			for z in 4:
				var cell := Vector3i(i, y, z)
				v[cell] = VoxelMesh.jittered(color, cell, 0.05)
	return VoxelMesh.build(v, cell_size)
