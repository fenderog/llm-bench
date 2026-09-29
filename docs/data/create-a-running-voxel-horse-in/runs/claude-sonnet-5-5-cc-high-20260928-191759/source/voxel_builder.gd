extends RefCounted
## Helpers for turning a Dictionary of voxels (Vector3i -> Color) into a
## face-culled ArrayMesh with per-vertex colours.

const DIRS: Array[Vector3i] = [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]
# Baked light/dark per face direction, so blocks read well even in flat light.
const SHADE: Array[float] = [0.86, 0.86, 1.0, 0.62, 0.8, 0.8]

static var _material: StandardMaterial3D


static func material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.vertex_color_is_srgb = true
		_material.roughness = 1.0
	return _material


## Fills the half-open box [from, to) with `color`. With `rounded`, voxels on
## the box's edges and corners are skipped to give a softer silhouette.
static func add_box(vox: Dictionary, from: Vector3i, to: Vector3i, color: Color, rounded := false) -> void:
	for x in range(from.x, to.x):
		for y in range(from.y, to.y):
			for z in range(from.z, to.z):
				if rounded:
					var extremes := 0
					if x == from.x or x == to.x - 1:
						extremes += 1
					if y == from.y or y == to.y - 1:
						extremes += 1
					if z == from.z or z == to.z - 1:
						extremes += 1
					if extremes >= 2:
						continue
				vox[Vector3i(x, y, z)] = color


static func _hash(v: Vector3i) -> float:
	var h := (v.x * 73856093) ^ (v.y * 19349663) ^ (v.z * 83492791)
	return float(h & 1023) / 1023.0


## Builds a mesh. `pivot` (in voxel units) becomes the mesh origin.
static func build(vox: Dictionary, pivot := Vector3.ZERO, size := 0.1, jitter := 0.06) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var axes: Array[Vector3] = [Vector3.RIGHT, Vector3.UP, Vector3.BACK]
	for cell: Vector3i in vox:
		var base: Color = vox[cell]
		var k := 1.0 + (_hash(cell) - 0.5) * 2.0 * jitter
		for i in DIRS.size():
			var n := DIRS[i]
			if vox.has(cell + n):
				continue
			var a := 0 if n.x != 0 else (1 if n.y != 0 else 2)
			var u: Vector3 = axes[(a + 1) % 3]
			var w: Vector3 = axes[(a + 2) % 3]
			var origin := Vector3(cell) - pivot
			if n[a] > 0:
				origin += axes[a]
			var c0 := origin * size
			var c1 := (origin + u) * size
			var c2 := (origin + u + w) * size
			var c3 := (origin + w) * size
			var shade := SHADE[i] * k
			var col := Color(base.r * shade, base.g * shade, base.b * shade, base.a)
			var normal := Vector3(n)
			# Godot treats clockwise triangles as front-facing.
			var ccw := (c1 - c0).cross(c2 - c0).dot(normal) > 0.0
			var tris := PackedVector3Array()
			if ccw:
				tris.append_array(PackedVector3Array([c0, c2, c1, c0, c3, c2]))
			else:
				tris.append_array(PackedVector3Array([c0, c1, c2, c0, c2, c3]))
			for p in tris:
				st.set_color(col)
				st.set_normal(normal)
				st.add_vertex(p)
	var mesh := st.commit()
	mesh.surface_set_material(0, material())
	return mesh
