extends RefCounted
## Helpers for building meshes out of colored voxels.
## A voxel model is a Dictionary mapping Vector3i -> Color.

# Face normal, and two edge axes (u, v) with u x v == normal.
const FACES := [
	[Vector3i(1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, 1)],
	[Vector3i(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 0)],
	[Vector3i(0, 1, 0), Vector3(0, 0, 1), Vector3(1, 0, 0)],
	[Vector3i(0, -1, 0), Vector3(1, 0, 0), Vector3(0, 0, 1)],
	[Vector3i(0, 0, 1), Vector3(1, 0, 0), Vector3(0, 1, 0)],
	[Vector3i(0, 0, -1), Vector3(0, 1, 0), Vector3(1, 0, 0)],
]

static var _material: StandardMaterial3D


static func material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.vertex_color_is_srgb = true
		_material.roughness = 0.95
	return _material


## Fills the half-open box [from, to) with a color.
static func box(vox: Dictionary, from: Vector3i, to: Vector3i, color: Color) -> void:
	for x in range(from.x, to.x):
		for y in range(from.y, to.y):
			for z in range(from.z, to.z):
				vox[Vector3i(x, y, z)] = color


## Fills voxels whose centers lie inside an ellipsoid.
static func ellipsoid(vox: Dictionary, center: Vector3, radii: Vector3, color: Color, min_y := -1000) -> void:
	var lo := Vector3i((center - radii).floor())
	var hi := Vector3i((center + radii).ceil())
	for x in range(lo.x, hi.x + 1):
		for y in range(maxi(lo.y, min_y), hi.y + 1):
			for z in range(lo.z, hi.z + 1):
				var d := (Vector3(x, y, z) + Vector3(0.5, 0.5, 0.5) - center) / radii
				if d.length_squared() <= 1.0:
					vox[Vector3i(x, y, z)] = color


## Deterministic 0..1 value for a voxel coordinate.
static func noise01(v: Vector3i) -> float:
	var h := (v.x * 73856093) ^ (v.y * 19349663) ^ (v.z * 83492791)
	return float(posmod(h, 1009)) / 1008.0


## Adds one quad (clockwise front face, as Godot expects) to the arrays.
static func add_quad(verts: PackedVector3Array, normals: PackedVector3Array, colors: PackedColorArray,
		indices: PackedInt32Array, p0: Vector3, u: Vector3, v: Vector3, n: Vector3, c: Color) -> void:
	var i := verts.size()
	verts.append(p0)
	verts.append(p0 + u)
	verts.append(p0 + u + v)
	verts.append(p0 + v)
	for k in 4:
		normals.append(n)
		colors.append(c)
	indices.append_array([i, i + 2, i + 1, i, i + 3, i + 2])


static func commit(verts: PackedVector3Array, normals: PackedVector3Array, colors: PackedColorArray,
		indices: PackedInt32Array) -> ArrayMesh:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, material())
	return mesh


## Builds a mesh with hidden faces culled. `pivot` (in voxel units) becomes the mesh origin.
static func build(vox: Dictionary, size: float, pivot := Vector3.ZERO, jitter := 0.06) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	for key in vox:
		var v: Vector3i = key
		var c: Color = vox[v]
		var shade := 1.0 + (noise01(v) - 0.5) * 2.0 * jitter
		c = Color(c.r * shade, c.g * shade, c.b * shade)
		for f in FACES:
			var n: Vector3i = f[0]
			if vox.has(v + n):
				continue
			var base := Vector3(v) + Vector3(maxi(n.x, 0), maxi(n.y, 0), maxi(n.z, 0))
			add_quad(verts, normals, colors, indices, (base - pivot) * size, f[1] * size, f[2] * size, Vector3(n), c)
	return commit(verts, normals, colors, indices)
