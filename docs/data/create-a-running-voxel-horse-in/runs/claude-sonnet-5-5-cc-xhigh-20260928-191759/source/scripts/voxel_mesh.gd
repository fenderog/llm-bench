class_name VoxelMesh
extends RefCounted
## Turns a sparse set of voxels (Vector3i cell -> Color) into one ArrayMesh.
## Faces hidden between neighbouring voxels are culled, and every face gets a
## small baked shade so the blocks read well even without shadows.

# Per face: outward normal, u axis, v axis (u x v == normal) and the corner
# offset inside the cell that the quad starts from.
const NORMALS: Array[Vector3i] = [
	Vector3i(1, 0, 0), Vector3i(-1, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1),
]
const U_AXES: Array[Vector3i] = [
	Vector3i(0, 1, 0), Vector3i(0, 0, 1),
	Vector3i(0, 0, 1), Vector3i(1, 0, 0),
	Vector3i(1, 0, 0), Vector3i(0, 1, 0),
]
const V_AXES: Array[Vector3i] = [
	Vector3i(0, 0, 1), Vector3i(0, 1, 0),
	Vector3i(1, 0, 0), Vector3i(0, 0, 1),
	Vector3i(0, 1, 0), Vector3i(1, 0, 0),
]
const CORNERS: Array[Vector3i] = [
	Vector3i(1, 0, 0), Vector3i(0, 0, 0),
	Vector3i(0, 1, 0), Vector3i(0, 0, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, 0),
]
const FACE_SHADE: Array[float] = [0.92, 0.92, 1.0, 0.72, 0.86, 0.86]

static var _material: StandardMaterial3D


static func material() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.vertex_color_use_as_albedo = true
		_material.roughness = 1.0
		_material.metallic_specular = 0.1
	return _material


## Builds a mesh from `voxels`. One voxel is `voxel_size` units wide and the
## cell (0, 0, 0) spans (0..1) * voxel_size. `skip_bottom` drops downward
## faces for things that are never seen from below, like the ground.
static func build(voxels: Dictionary, voxel_size: float, skip_bottom: bool = false) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for cell: Vector3i in voxels:
		var color: Color = voxels[cell]
		for face in 6:
			if skip_bottom and face == 3:
				continue
			if voxels.has(cell + NORMALS[face]):
				continue
			_add_face(st, cell, face, color, voxel_size)
	var mesh := st.commit()
	if mesh.get_surface_count() > 0:
		mesh.surface_set_material(0, material())
	return mesh


static func _add_face(st: SurfaceTool, cell: Vector3i, face: int, color: Color, size: float) -> void:
	var shade: float = FACE_SHADE[face]
	var shaded := Color(color.r * shade, color.g * shade, color.b * shade, color.a)
	var normal := Vector3(NORMALS[face])
	var base := Vector3(cell + CORNERS[face])
	var u := Vector3(U_AXES[face])
	var v := Vector3(V_AXES[face])
	var p0 := base * size
	var p1 := (base + u) * size
	var p2 := (base + u + v) * size
	var p3 := (base + v) * size
	# The quad above is counter-clockwise seen from outside; Godot wants clockwise.
	for p: Vector3 in [p0, p2, p1, p0, p3, p2]:
		st.set_color(shaded)
		st.set_normal(normal)
		st.add_vertex(p)


## Fills the inclusive box `from`..`to` with `color` (optionally jittered).
static func fill_box(voxels: Dictionary, from: Vector3i, to: Vector3i, color: Color, jitter: float = 0.0) -> void:
	for x in range(from.x, to.x + 1):
		for y in range(from.y, to.y + 1):
			for z in range(from.z, to.z + 1):
				var cell := Vector3i(x, y, z)
				voxels[cell] = jittered(color, cell, jitter)


static func erase_box(voxels: Dictionary, from: Vector3i, to: Vector3i) -> void:
	for x in range(from.x, to.x + 1):
		for y in range(from.y, to.y + 1):
			for z in range(from.z, to.z + 1):
				voxels.erase(Vector3i(x, y, z))


## Deterministic per-cell brightness noise so flat areas look hand-made.
static func jittered(color: Color, cell: Vector3i, amount: float) -> Color:
	if amount <= 0.0:
		return color
	var h := (cell.x * 73856093) ^ (cell.y * 19349663) ^ (cell.z * 83492791)
	var n := float(h & 0xFF) / 255.0 - 0.5
	var f := 1.0 + n * 2.0 * amount
	return Color(color.r * f, color.g * f, color.b * f, color.a)


## Convenience: wraps a voxel set in a ready-to-use MeshInstance3D.
static func make_instance(voxels: Dictionary, voxel_size: float, skip_bottom: bool = false) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = build(voxels, voxel_size, skip_bottom)
	return instance
