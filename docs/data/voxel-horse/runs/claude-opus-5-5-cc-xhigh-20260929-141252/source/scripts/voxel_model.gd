extends RefCounted
## Sparse voxel grid (Vector3i -> Color). Voxel (x, y, z) fills the unit cell
## [x, x+1) x [y, y+1) x [z, z+1); shapes are tested at voxel centres, so a
## shape centred on an integer coordinate comes out symmetric.

const MeshData = preload("res://scripts/mesh_data.gd")

const NONE := Vector3i(-9999, -9999, -9999)
const HALF := Vector3(0.5, 0.5, 0.5)

# Per face direction: neighbour offset, corner offset and the two edges (u x v = normal).
const DIRS: Array[Vector3i] = [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]
const FACE_CORNER: Array[Vector3] = [
	Vector3(1, 0, 0), Vector3(0, 0, 0),
	Vector3(0, 1, 0), Vector3(0, 0, 0),
	Vector3(0, 0, 1), Vector3(0, 0, 0),
]
const FACE_U: Array[Vector3] = [
	Vector3(0, 1, 0), Vector3(0, 0, 1),
	Vector3(0, 0, 1), Vector3(1, 0, 0),
	Vector3(1, 0, 0), Vector3(0, 1, 0),
]
const FACE_V: Array[Vector3] = [
	Vector3(0, 0, 1), Vector3(0, 1, 0),
	Vector3(1, 0, 0), Vector3(0, 0, 1),
	Vector3(0, 1, 0), Vector3(1, 0, 0),
]

var voxels: Dictionary = {}


func set_voxel(p: Vector3i, c: Color) -> void:
	voxels[p] = c


func has_voxel(p: Vector3i) -> bool:
	return voxels.has(p)


## Fills the inclusive box a..b.
func fill_box(a: Vector3i, b: Vector3i, c: Color) -> void:
	for x in range(mini(a.x, b.x), maxi(a.x, b.x) + 1):
		for y in range(mini(a.y, b.y), maxi(a.y, b.y) + 1):
			for z in range(mini(a.z, b.z), maxi(a.z, b.z) + 1):
				voxels[Vector3i(x, y, z)] = c


## Super-ellipsoid: power 2 is an ellipsoid, higher powers get boxier.
func fill_blob(center: Vector3, radii: Vector3, c: Color, power := 2.0) -> void:
	var lo := Vector3i((center - radii).floor()) - Vector3i.ONE
	var hi := Vector3i((center + radii).ceil())
	for x in range(lo.x, hi.x + 1):
		for y in range(lo.y, hi.y + 1):
			for z in range(lo.z, hi.z + 1):
				var d := (Vector3(x, y, z) + HALF - center) / radii
				if pow(absf(d.x), power) + pow(absf(d.y), power) + pow(absf(d.z), power) <= 1.0:
					voxels[Vector3i(x, y, z)] = c


## Tapered capsule from a (radius ra) to b (radius rb).
func fill_tube(a: Vector3, b: Vector3, ra: float, rb: float, c: Color) -> void:
	var r := maxf(ra, rb)
	var lo := Vector3i(Vector3(minf(a.x, b.x) - r, minf(a.y, b.y) - r, minf(a.z, b.z) - r).floor()) - Vector3i.ONE
	var hi := Vector3i(Vector3(maxf(a.x, b.x) + r, maxf(a.y, b.y) + r, maxf(a.z, b.z) + r).ceil())
	var ab := b - a
	var len2 := maxf(ab.length_squared(), 0.0001)
	for x in range(lo.x, hi.x + 1):
		for y in range(lo.y, hi.y + 1):
			for z in range(lo.z, hi.z + 1):
				var p := Vector3(x, y, z) + HALF
				var t := clampf((p - a).dot(ab) / len2, 0.0, 1.0)
				if p.distance_to(a + ab * t) <= lerpf(ra, rb, t):
					voxels[Vector3i(x, y, z)] = c


## Recolours every voxel for which `pred.call(pos, colour)` returns true.
func recolor(pred: Callable, c: Color) -> void:
	for p: Vector3i in voxels.keys():
		if pred.call(p, voxels[p]):
			voxels[p] = c


## Outermost voxel along `axis` (0=x, 1=y, 2=z) in direction `dir` (+1/-1) on
## the line through `line` (its `axis` component is ignored). NONE if empty.
func surface(axis: int, dir: int, line: Vector3i) -> Vector3i:
	var best := NONE
	for p: Vector3i in voxels:
		var on_line := true
		for k in 3:
			if k != axis and p[k] != line[k]:
				on_line = false
				break
		if on_line and (best == NONE or p[axis] * dir > best[axis] * dir):
			best = p
	return best


func paint_surface(axis: int, dir: int, line: Vector3i, c: Color) -> Vector3i:
	var p := surface(axis, dir, line)
	if p != NONE:
		voxels[p] = c
	return p


## Emits every face that touches empty space. `origin` (in voxel units) ends up
## at the mesh origin; `jitter` adds a per-voxel brightness variation.
func bake(md: MeshData, voxel_size: float, origin: Vector3, jitter := 0.05) -> void:
	for p: Vector3i in voxels:
		var c: Color = voxels[p]
		if jitter > 0.0:
			var h := float(posmod(hash(p), 1024)) / 1023.0
			var k := 1.0 + (h - 0.5) * 2.0 * jitter
			c = Color(c.r * k, c.g * k, c.b * k, c.a)
		var base := (Vector3(p) - origin) * voxel_size
		for d in 6:
			if not voxels.has(p + DIRS[d]):
				md.add_quad(base + FACE_CORNER[d] * voxel_size, FACE_U[d] * voxel_size,
						FACE_V[d] * voxel_size, Vector3(DIRS[d]), c)


func build_mesh(voxel_size: float, origin: Vector3, material: Material, jitter := 0.05) -> ArrayMesh:
	var md := MeshData.new()
	bake(md, voxel_size, origin, jitter)
	return md.commit(material)
