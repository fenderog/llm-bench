extends RefCounted
class_name VoxelBuilder

var transforms: Array[Transform3D] = []
var colors: Array[Color] = []

func box(center: Vector3, size: Vector3, color: Color, rotation := Vector3.ZERO) -> void:
	transforms.append(Transform3D(Basis.from_euler(rotation).scaled(size), center))
	colors.append(color)

func build(parent: Node3D) -> MultiMeshInstance3D:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 1.0
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	mesh.material = material
	var multimesh := MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.mesh = mesh
	multimesh.instance_count = transforms.size()
	for i in transforms.size():
		multimesh.set_instance_transform(i, transforms[i])
		multimesh.set_instance_color(i, colors[i].srgb_to_linear())
	var instance := MultiMeshInstance3D.new()
	instance.multimesh = multimesh
	parent.add_child(instance)
	return instance
