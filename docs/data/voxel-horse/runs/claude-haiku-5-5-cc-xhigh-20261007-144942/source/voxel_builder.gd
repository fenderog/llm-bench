class_name VoxelBuilder
extends RefCounted

## Builds voxel-style meshes from axis-aligned boxes. Every box is emitted as
## six quads with per-vertex colours, so a whole model can live in one surface
## and no external assets are needed.


static func new_surface_tool() -> SurfaceTool:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	return st


static func make_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.9
	return mat


## Adds a box spanning [min_corner, min_corner + size], transformed by xform.
static func add_box(st: SurfaceTool, min_corner: Vector3, size: Vector3, color: Color, xform: Transform3D = Transform3D.IDENTITY) -> void:
	var hi := min_corner + size
	# Corner i uses bit 0 for x, bit 1 for y and bit 2 for z (0 = min, 1 = max).
	var c: Array[Vector3] = []
	for i in 8:
		var p := Vector3(
			hi.x if (i & 1) != 0 else min_corner.x,
			hi.y if (i & 2) != 0 else min_corner.y,
			hi.z if (i & 4) != 0 else min_corner.z)
		c.append(xform * p)

	var basis := xform.basis
	_add_quad(st, c[1], c[3], c[7], c[5], (basis * Vector3.RIGHT).normalized(), color)
	_add_quad(st, c[0], c[4], c[6], c[2], (basis * Vector3.LEFT).normalized(), color)
	_add_quad(st, c[2], c[6], c[7], c[3], (basis * Vector3.UP).normalized(), color)
	_add_quad(st, c[0], c[1], c[5], c[4], (basis * Vector3.DOWN).normalized(), color)
	_add_quad(st, c[4], c[5], c[7], c[6], (basis * Vector3.BACK).normalized(), color)
	_add_quad(st, c[0], c[2], c[3], c[1], (basis * Vector3.FORWARD).normalized(), color)


static func _add_quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, normal: Vector3, color: Color) -> void:
	# Godot treats clockwise triangles as front-facing, so reverse any quad
	# whose winding points inward relative to its normal.
	if (b - a).cross(c - a).dot(normal) > 0.0:
		var swap := b
		b = d
		d = swap
	for p in [a, b, c, a, c, d]:
		st.set_normal(normal)
		st.set_color(color)
		st.add_vertex(p)
