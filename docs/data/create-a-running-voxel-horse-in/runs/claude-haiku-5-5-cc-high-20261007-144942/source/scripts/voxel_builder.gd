class_name VoxelBuilder
extends RefCounted

## Turns a dictionary of voxels into one mesh. Keys are integer voxel
## coordinates and values are colors. Only faces that border empty space are
## emitted, so solid models stay cheap to draw.

const VOXEL_SIZE := 0.1

## Outward direction of each face, and the four corners of that face on the unit cube.
const FACES := [
	[Vector3i(1, 0, 0), [Vector3(1, 0, 0), Vector3(1, 1, 0), Vector3(1, 1, 1), Vector3(1, 0, 1)]],
	[Vector3i(-1, 0, 0), [Vector3(0, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 1), Vector3(0, 1, 0)]],
	[Vector3i(0, 1, 0), [Vector3(0, 1, 0), Vector3(0, 1, 1), Vector3(1, 1, 1), Vector3(1, 1, 0)]],
	[Vector3i(0, -1, 0), [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(1, 0, 1), Vector3(0, 0, 1)]],
	[Vector3i(0, 0, 1), [Vector3(0, 0, 1), Vector3(1, 0, 1), Vector3(1, 1, 1), Vector3(0, 1, 1)]],
	[Vector3i(0, 0, -1), [Vector3(0, 0, 0), Vector3(0, 1, 0), Vector3(1, 1, 0), Vector3(1, 0, 0)]],
]

static var _material: StandardMaterial3D


## Fills the voxels in [from, to) with a color. Each voxel gets a slight random
## brightness shift so big blocks don't look flat.
static func fill(voxels: Dictionary, from: Vector3i, to: Vector3i, color: Color) -> void:
	for x in range(from.x, to.x):
		for y in range(from.y, to.y):
			for z in range(from.z, to.z):
				var shade := randf_range(-0.05, 0.05)
				voxels[Vector3i(x, y, z)] = color.lightened(shade) if shade > 0.0 else color.darkened(-shade)


static func build_mesh(voxels: Dictionary) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for pos: Vector3i in voxels.keys():
		var color: Color = voxels[pos]
		for face in FACES:
			var dir: Vector3i = face[0]
			if voxels.has(pos + dir):
				continue
			var quad: Array[Vector3] = []
			for corner: Vector3 in face[1]:
				quad.append((Vector3(pos) + corner) * VOXEL_SIZE)
			_add_quad(st, quad, Vector3(dir), color)
	var mesh := st.commit()
	mesh.surface_set_material(0, _get_material())
	return mesh


static func make_instance(voxels: Dictionary) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = build_mesh(voxels)
	return instance


static func _add_quad(st: SurfaceTool, quad: Array[Vector3], normal: Vector3, color: Color) -> void:
	# Godot treats clockwise triangles as front-facing, so flip any quad that winds counter-clockwise.
	var order := [0, 1, 2, 0, 2, 3]
	if (quad[1] - quad[0]).cross(quad[2] - quad[0]).dot(normal) > 0.0:
		order = [0, 2, 1, 0, 3, 2]
	for i in order:
		st.set_normal(normal)
		st.set_color(color)
		st.add_vertex(quad[i])


static func _get_material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.roughness = 0.95
	return _material
