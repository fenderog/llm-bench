extends RefCounted
## Tiny voxel model builder: fill a grid with coloured cubes, then bake it
## into a single ArrayMesh with hidden (interior) faces culled.

const FACE_DIRS := [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]
const FACE_CORNERS := [
	[Vector3(1, 0, 0), Vector3(1, 1, 0), Vector3(1, 1, 1), Vector3(1, 0, 1)],
	[Vector3(0, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 1), Vector3(0, 1, 0)],
	[Vector3(0, 1, 0), Vector3(0, 1, 1), Vector3(1, 1, 1), Vector3(1, 1, 0)],
	[Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(1, 0, 1), Vector3(0, 0, 1)],
	[Vector3(0, 0, 1), Vector3(1, 0, 1), Vector3(1, 1, 1), Vector3(0, 1, 1)],
	[Vector3(0, 0, 0), Vector3(0, 1, 0), Vector3(1, 1, 0), Vector3(1, 0, 0)],
]

var voxels := {}
var rng := RandomNumberGenerator.new()


func _init(seed_value: int = 1) -> void:
	rng.seed = seed_value


func put(p: Vector3i, col: Color, jitter: float = 0.04) -> void:
	var j := rng.randf_range(-jitter, jitter)
	voxels[p] = Color(clampf(col.r + j, 0.0, 1.0), clampf(col.g + j, 0.0, 1.0), clampf(col.b + j, 0.0, 1.0))


func erase(p: Vector3i) -> void:
	voxels.erase(p)


func box(a: Vector3i, b: Vector3i, col: Color, jitter: float = 0.04) -> void:
	for x in range(mini(a.x, b.x), maxi(a.x, b.x) + 1):
		for y in range(mini(a.y, b.y), maxi(a.y, b.y) + 1):
			for z in range(mini(a.z, b.z), maxi(a.z, b.z) + 1):
				put(Vector3i(x, y, z), col, jitter)


func blob(c: Vector3i, r: float, col: Color, jitter: float = 0.06, roughness: float = 0.6) -> void:
	var ri := int(ceil(r + roughness))
	for x in range(-ri, ri + 1):
		for y in range(-ri, ri + 1):
			for z in range(-ri, ri + 1):
				var d := Vector3(x, y, z).length()
				if d <= r + rng.randf_range(-roughness, roughness) * 0.5:
					put(c + Vector3i(x, y, z), col, jitter)


func build(size: float, material: Material, offset: Vector3 = Vector3.ZERO) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for key in voxels:
		var p: Vector3i = key
		var col: Color = voxels[p]
		var base := Vector3(p)
		for f in 6:
			var d: Vector3i = FACE_DIRS[f]
			if voxels.has(p + d):
				continue
			var n := Vector3(d)
			var q: Array[Vector3] = []
			for c in FACE_CORNERS[f]:
				q.append((base + c) * size + offset)
			# Godot treats clockwise triangles as front-facing.
			var idx := [0, 1, 2, 0, 2, 3]
			if (q[1] - q[0]).cross(q[2] - q[0]).dot(n) > 0.0:
				idx = [0, 2, 1, 0, 3, 2]
			for i in idx:
				st.set_color(col)
				st.set_normal(n)
				st.add_vertex(q[i])
	st.set_material(material)
	return st.commit()
