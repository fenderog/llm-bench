class_name VoxelBuilder
## Helper that turns a dictionary of `{Vector3i cell: Color}` into an `ArrayMesh`
## made of unit cubes. Faces that are shared between two neighbouring cells are
## culled, every emitted face gets a flat outward normal, and the colour is
## baked into vertex colours (one shared white material renders it).

const _DIRS := [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]

# For each direction in _DIRS: two tangent axes (u, v) with u x v = dir,
# so the emitted triangles wind counter-clockwise seen from outside.
const _TANGENTS := [
	[Vector3(0, 1, 0), Vector3(0, 0, 1)], # +X : Y x Z = X
	[Vector3(0, 0, 1), Vector3(0, 1, 0)], # -X : Z x Y = -X
	[Vector3(0, 0, 1), Vector3(1, 0, 0)], # +Y : Z x X = Y
	[Vector3(1, 0, 0), Vector3(0, 0, 1)], # -Y : X x Z = -Y
	[Vector3(1, 0, 0), Vector3(0, 1, 0)], # +Z : X x Y = Z
	[Vector3(0, 1, 0), Vector3(1, 0, 0)], # -Z : Y x X = -Z
]

static var _shared_material: StandardMaterial3D

## One material shared by every voxel mesh in the project (vertex-coloured).
static func shared_material() -> StandardMaterial3D:
	if _shared_material == null:
		var mat := StandardMaterial3D.new()
		mat.vertex_color_use_as_albedo = true
		mat.albedo_color = Color.WHITE
		mat.roughness = 0.92
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		_shared_material = mat
	return _shared_material

## Builds an ArrayMesh from `cells` ({Vector3i: Color}).
## `origin` subtracts a pivot point from every cell, `voxel_scale` scales the cubes.
static func build_mesh(cells: Dictionary, origin: Vector3 = Vector3.ZERO, voxel_scale: float = 1.0) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()

	var cell_set := {}
	for c in cells.keys():
		cell_set[c] = true

	for cell: Vector3i in cells.keys():
		var color: Color = cells[cell]
		var base := (Vector3(cell) - origin) * voxel_scale
		for i in 6:
			var d: Vector3i = _DIRS[i]
			if cell_set.has(cell + d):
				continue # internal face, hidden inside the model
			var n := Vector3(d)
			var u: Vector3 = _TANGENTS[i][0]
			var v: Vector3 = _TANGENTS[i][1]
			var off := Vector3.ZERO
			if d.x > 0:
				off.x = voxel_scale
			elif d.y > 0:
				off.y = voxel_scale
			elif d.z > 0:
				off.z = voxel_scale
			var p0 := base + off
			var p1 := p0 + u * voxel_scale
			var p2 := p0 + (u + v) * voxel_scale
			var p3 := p0 + v * voxel_scale
			var idx := verts.size()
			verts.append(p0)
			verts.append(p1)
			verts.append(p2)
			verts.append(p3)
			normals.append(n)
			normals.append(n)
			normals.append(n)
			normals.append(n)
			colors.append(color)
			colors.append(color)
			colors.append(color)
			colors.append(color)
			uvs.append(Vector2(0, 0))
			uvs.append(Vector2(1, 0))
			uvs.append(Vector2(1, 1))
			uvs.append(Vector2(0, 1))
			indices.append(idx)
			indices.append(idx + 1)
			indices.append(idx + 2)
			indices.append(idx)
			indices.append(idx + 2)
			indices.append(idx + 3)

	var mesh := ArrayMesh.new()
	if verts.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
