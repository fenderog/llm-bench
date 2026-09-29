extends RefCounted
## Growable buffer of vertex-coloured quads that can be committed to an ArrayMesh.

var verts := PackedVector3Array()
var normals := PackedVector3Array()
var colors := PackedColorArray()
var indices := PackedInt32Array()


## Adds a quad spanning corner .. corner + u + v. `u x v` must point along `n`
## so the face winds clockwise (Godot's front face) when seen from outside.
func add_quad(corner: Vector3, u: Vector3, v: Vector3, n: Vector3, c: Color) -> void:
	add_quad_gradient(corner, u, v, n, c, c)


## Like add_quad, but vertices on the `corner + v` edge get colour `top`.
func add_quad_gradient(corner: Vector3, u: Vector3, v: Vector3, n: Vector3, bottom: Color, top: Color) -> void:
	var i := verts.size()
	verts.push_back(corner)
	verts.push_back(corner + v)
	verts.push_back(corner + u + v)
	verts.push_back(corner + u)
	for k in 4:
		normals.push_back(n)
	# Colours are authored in sRGB; store them linear so every renderer agrees.
	var b := bottom.srgb_to_linear()
	var t := top.srgb_to_linear()
	colors.push_back(b)
	colors.push_back(t)
	colors.push_back(t)
	colors.push_back(b)
	indices.push_back(i)
	indices.push_back(i + 1)
	indices.push_back(i + 2)
	indices.push_back(i)
	indices.push_back(i + 2)
	indices.push_back(i + 3)


## Axis-aligned box whose minimum corner is `pos`. The bottom face is usually
## hidden against the ground, so it is skipped unless requested.
func add_box(pos: Vector3, size: Vector3, c: Color, bottom_face := false) -> void:
	var sx := Vector3(size.x, 0, 0)
	var sy := Vector3(0, size.y, 0)
	var sz := Vector3(0, 0, size.z)
	add_quad(pos + sx, sy, sz, Vector3.RIGHT, c)
	add_quad(pos, sz, sy, Vector3.LEFT, c)
	add_quad(pos + sy, sz, sx, Vector3.UP, c)
	if bottom_face:
		add_quad(pos, sx, sz, Vector3.DOWN, c)
	add_quad(pos + sz, sx, sy, Vector3.BACK, c)
	add_quad(pos, sy, sx, Vector3.FORWARD, c)


## Copies another buffer into this one, transformed by `xform`.
func append(other, xform: Transform3D) -> void:
	var base := verts.size()
	var basis := xform.basis
	var src_verts: PackedVector3Array = other.verts
	var src_normals: PackedVector3Array = other.normals
	for k in src_verts.size():
		verts.push_back(xform * src_verts[k])
		normals.push_back((basis * src_normals[k]).normalized())
	colors.append_array(other.colors)
	var src_indices: PackedInt32Array = other.indices
	for idx in src_indices:
		indices.push_back(idx + base)


func is_empty() -> bool:
	return verts.is_empty()


func commit(material: Material) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	if verts.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, material)
	return mesh


## Shared look for everything built from vertex colours.
static func make_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.9
	return mat
