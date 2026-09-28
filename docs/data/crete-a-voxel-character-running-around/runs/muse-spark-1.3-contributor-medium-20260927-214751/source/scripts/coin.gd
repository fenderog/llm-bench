extends Area3D
## Spinning collectible voxel coin. Calls `collect_coin(self)` on the "game" group.

var base_y := 0.0
var _t := 0.0
var _taken := false
var _mesh: MeshInstance3D

func _ready() -> void:
	base_y = position.y
	_t = randf() * TAU
	collision_layer = 0
	collision_mask = 1
	monitoring = true
	monitorable = true

	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.7
	shape.shape = sphere
	add_child(shape)

	_mesh = MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.5, 0.5, 0.12)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.78, 0.15)
	mat.metallic = 0.6
	mat.roughness = 0.3
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.7, 0.1)
	mat.emission_energy_multiplier = 0.6
	box.material = mat
	_mesh.mesh = box
	add_child(_mesh)

	# Inner gem stripe so it reads as a coin from all sides.
	var stripe := MeshInstance3D.new()
	var sbox := BoxMesh.new()
	sbox.size = Vector3(0.2, 0.52, 0.14)
	var smat := StandardMaterial3D.new()
	smat.albedo_color = Color(1.0, 0.95, 0.6)
	smat.emission_enabled = true
	smat.emission = Color(1.0, 0.9, 0.4)
	smat.emission_energy_multiplier = 0.8
	sbox.material = smat
	stripe.mesh = sbox
	_mesh.add_child(stripe)

	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	if _taken:
		return
	_t += delta
	_mesh.rotation.y = _t * 2.5
	position.y = base_y + sin(_t * 2.0) * 0.15


func _on_body_entered(body: Node3D) -> void:
	if _taken:
		return
	if not body.is_in_group("player"):
		return
	_taken = true
	get_tree().call_group("game", "collect_coin", self)
	queue_free()
