extends RefCounted
## Sparse voxel grid that turns into a face-culled, ambient-occluded ArrayMesh.
## Voxel (x, y, z) occupies the unit cube [x, x+1] x [y, y+1] x [z, z+1].
## Colours are stored per voxel; shading (AO, per-voxel jitter and optionally a
## baked directional tint for unshaded materials) ends up in the vertex colours.

# Per face: outward normal and two tangents with u x v == normal.
const _NORMALS = [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]
const _AXIS_U = [
	Vector3i(0, 1, 0), Vector3i(0, 0, 1),
	Vector3i(0, 0, 1), Vector3i(1, 0, 0),
	Vector3i(1, 0, 0), Vector3i(0, 1, 0),
]
const _AXIS_V = [
	Vector3i(0, 0, 1), Vector3i(0, 1, 0),
	Vector3i(1, 0, 0), Vector3i(0, 0, 1),
	Vector3i(0, 1, 0), Vector3i(1, 0, 0),
]
const _FACE_LIGHT = [0.86, 0.74, 1.0, 0.56, 0.93, 0.68]
const _AO_LEVEL = [0.52, 0.70, 0.86, 1.0]

var cells: Dictionary = {}   # Vector3i -> Color
var jitter := 0.05           # per-voxel brightness noise (darkening only)
var face_light := false      # bake a fake sun direction into the colours


static func hash3(p: Vector3i, seed_value := 0) -> float:
	var h: int = p.x * 374761393 + p.y * 668265263 + p.z * 1103515245 + seed_value * 1274126177
	h = (h ^ (h >> 13)) * 1274126177
	h = h ^ (h >> 16)
	return float(h & 0xFFFF) / 65535.0


func set_voxel(p: Vector3i, color: Color) -> void:
	cells[p] = color


func has_voxel(p: Vector3i) -> bool:
	return cells.has(p)


func erase_voxel(p: Vector3i) -> void:
	cells.erase(p)


## Fills [from, to) with one colour.
func fill_box(from: Vector3i, to: Vector3i, color: Color) -> void:
	for x in range(from.x, to.x):
		for y in range(from.y, to.y):
			for z in range(from.z, to.z):
				cells[Vector3i(x, y, z)] = color


## Fills an ellipsoid; the colour of each voxel is picked from `colors` by hash.
func fill_ellipsoid(center: Vector3, radii: Vector3, colors: Array, seed_value := 0) -> void:
	var lo := (center - radii).floor()
	var hi := (center + radii).ceil()
	for x in range(int(lo.x), int(hi.x) + 1):
		for y in range(int(lo.y), int(hi.y) + 1):
			for z in range(int(lo.z), int(hi.z) + 1):
				var q := (Vector3(x + 0.5, y + 0.5, z + 0.5) - center) / radii
				if q.length_squared() > 1.0:
					continue
				var p := Vector3i(x, y, z)
				var pick := int(hash3(p, seed_value) * colors.size()) % colors.size()
				cells[p] = colors[pick]


func voxel_count() -> int:
	return cells.size()


func _corner_ao(pn: Vector3i, u: Vector3i, v: Vector3i, su: int, sv: int) -> int:
	var side_u := cells.has(pn + u * su)
	var side_v := cells.has(pn + v * sv)
	if side_u and side_v:
		return 0
	var corner := cells.has(pn + u * su + v * sv)
	return 3 - int(side_u) - int(side_v) - int(corner)


static func _shade(c: Color, k: float) -> Color:
	return Color(c.r * k, c.g * k, c.b * k, 1.0)


## Builds the mesh. `pivot` (in voxel units) becomes the mesh origin.
func build_mesh(pivot := Vector3.ZERO, voxel_size := 1.0) -> ArrayMesh:
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()

	for key in cells:
		var p: Vector3i = key
		var base: Color = cells[key]
		var tint := 1.0 - jitter * 2.0 * hash3(p)
		for f in 6:
			var n: Vector3i = _NORMALS[f]
			if cells.has(p + n):
				continue
			var u: Vector3i = _AXIS_U[f]
			var v: Vector3i = _AXIS_V[f]
			var pn := p + n
			var a0 := _corner_ao(pn, u, v, -1, -1)
			var a1 := _corner_ao(pn, u, v, 1, -1)
			var a2 := _corner_ao(pn, u, v, 1, 1)
			var a3 := _corner_ao(pn, u, v, -1, 1)
			var light := tint
			if face_light:
				light *= _FACE_LIGHT[f]

			var origin := Vector3(p + Vector3i(maxi(n.x, 0), maxi(n.y, 0), maxi(n.z, 0))) - pivot
			var uf := Vector3(u)
			var vf := Vector3(v)
			var i0 := verts.size()
			verts.push_back(origin * voxel_size)
			verts.push_back((origin + uf) * voxel_size)
			verts.push_back((origin + uf + vf) * voxel_size)
			verts.push_back((origin + vf) * voxel_size)
			var nf := Vector3(n)
			for k in 4:
				norms.push_back(nf)
			cols.push_back(_shade(base, light * _AO_LEVEL[a0]))
			cols.push_back(_shade(base, light * _AO_LEVEL[a1]))
			cols.push_back(_shade(base, light * _AO_LEVEL[a2]))
			cols.push_back(_shade(base, light * _AO_LEVEL[a3]))

			# Godot front faces are clockwise. Split along the brighter diagonal
			# so the AO gradient does not get a dark crease through it.
			if a0 + a2 > a1 + a3:
				idx.push_back(i0)
				idx.push_back(i0 + 2)
				idx.push_back(i0 + 1)
				idx.push_back(i0)
				idx.push_back(i0 + 3)
				idx.push_back(i0 + 2)
			else:
				idx.push_back(i0 + 1)
				idx.push_back(i0 + 3)
				idx.push_back(i0 + 2)
				idx.push_back(i0 + 1)
				idx.push_back(i0)
				idx.push_back(i0 + 3)

	var mesh := ArrayMesh.new()
	if verts.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
