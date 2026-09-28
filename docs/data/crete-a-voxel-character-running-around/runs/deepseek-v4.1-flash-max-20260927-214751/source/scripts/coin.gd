extends Area3D
## A spinning, bobbing voxel coin. The game connects to `body_entered`.

var _spin := 0.0
var _base_y := 0.0


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	monitoring = true
	monitorable = false

	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.9, 1.1, 0.9)
	shape.shape = box
	add_child(shape)

	var gold := StandardMaterial3D.new()
	gold.albedo_color = Color(1.0, 0.78, 0.16)
	gold.metallic = 0.85
	gold.roughness = 0.25
	gold.emission_enabled = true
	gold.emission = Color(0.4, 0.28, 0.03)
	gold.emission_energy_multiplier = 1.4

	var outer := MeshInstance3D.new()
	var outer_mesh := BoxMesh.new()
	outer_mesh.size = Vector3(0.5, 0.5, 0.14)
	outer_mesh.material = gold
	outer.mesh = outer_mesh
	add_child(outer)

	var core := MeshInstance3D.new()
	var core_mesh := BoxMesh.new()
	core_mesh.size = Vector3(0.26, 0.26, 0.2)
	core_mesh.material = gold
	core.mesh = core_mesh
	add_child(core)

	_base_y = position.y


func _process(delta: float) -> void:
	_spin += delta
	rotation.y = _spin * 2.6
	position.y = _base_y + sin(_spin * 2.4) * 0.12
