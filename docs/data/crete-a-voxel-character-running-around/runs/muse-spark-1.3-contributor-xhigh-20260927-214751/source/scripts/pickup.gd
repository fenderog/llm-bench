extends Area3D
## Floating voxel "sky shard" pickup: spins and bobs, gently magnetizes
## toward the player, hides on collect and respawns a few seconds later.

signal collected(pickup)

const RESPAWN_TIME: float = 6.0
const MAGNET_DIST: float = 1.7

var base_y: float = 0.0
var t: float = 0.0
var taken: bool = false
var respawn_in: float = 0.0
var spin: Node3D
var player_node: Node3D


func _ready() -> void:
	base_y = position.y
	t = randf() * TAU
	collision_layer = 0
	collision_mask = 1
	monitoring = true
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.7
	shape.shape = sphere
	add_child(shape)
	spin = Node3D.new()
	add_child(spin)
	var outer := MeshInstance3D.new()
	var outer_mesh := BoxMesh.new()
	outer_mesh.size = Vector3(0.34, 0.7, 0.34)
	var outer_mat := StandardMaterial3D.new()
	outer_mat.albedo_color = Color(0.30, 0.88, 1.0)
	outer_mat.roughness = 0.35
	outer_mesh.material = outer_mat
	outer.mesh = outer_mesh
	spin.add_child(outer)
	var inner := MeshInstance3D.new()
	var inner_mesh := BoxMesh.new()
	inner_mesh.size = Vector3(0.36, 0.4, 0.36)
	var inner_mat := StandardMaterial3D.new()
	inner_mat.albedo_color = Color(0.80, 0.97, 1.0)
	inner_mat.roughness = 0.2
	inner_mesh.material = inner_mat
	inner.mesh = inner_mesh
	spin.add_child(inner)
	spin.rotation.y = randf() * TAU
	player_node = get_tree().get_first_node_in_group("player")
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	if taken:
		respawn_in -= delta
		if respawn_in <= 0.0:
			respawn_now()
		return
	t += delta
	spin.rotation.y += 2.2 * delta
	position.y = base_y + sin(t * 2.0) * 0.12
	if player_node != null and is_instance_valid(player_node):
		var target: Vector3 = player_node.global_position + Vector3(0, 0.7, 0)
		if global_position.distance_to(target) < MAGNET_DIST:
			global_position = global_position.move_toward(target, 6.0 * delta)


func _on_body_entered(body: Node3D) -> void:
	if taken:
		return
	if body.is_in_group("player"):
		taken = true
		visible = false
		set_deferred("monitoring", false)
		respawn_in = RESPAWN_TIME
		collected.emit(self)


func respawn_now() -> void:
	taken = false
	position.y = base_y
	visible = true
	set_deferred("monitoring", true)
