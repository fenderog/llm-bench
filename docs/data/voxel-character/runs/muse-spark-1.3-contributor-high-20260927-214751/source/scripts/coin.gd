class_name Coin
extends Area3D
## A spinning voxel coin. Faces sideways so the spin reads, bobs gently,
## and pops away with a tween when the player touches it.
signal picked(coin: Node3D)

var base_y := 0.8
var t := 0.0
var taken := false
var spin := 2.2
var phase := 0.0


func _ready() -> void:
	add_to_group("coins")
	collision_layer = 4
	collision_mask = 2
	base_y = position.y
	phase = fposmod(abs(position.x * 1.7 + position.z * 2.3), 6.28)

	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.32
	cm.bottom_radius = 0.32
	cm.height = 0.1
	cm.radial_segments = 18
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(1.0, 0.78, 0.15)
	m.metallic = 0.75
	m.roughness = 0.28
	m.emission_enabled = true
	m.emission = Color(1.0, 0.7, 0.1)
	m.emission_energy_multiplier = 0.35
	cm.material = m
	mi.mesh = cm
	mi.rotation_degrees = Vector3(0, 0, 90)
	add_child(mi)

	# Chunky voxel rim so it reads as a voxel coin.
	var rim := MeshInstance3D.new()
	var rb := BoxMesh.new()
	rb.size = Vector3(0.12, 0.72, 0.72)
	var rm := StandardMaterial3D.new()
	rm.albedo_color = Color(0.95, 0.65, 0.10)
	rm.metallic = 0.6
	rm.roughness = 0.35
	rb.material = rm
	rim.mesh = rb
	add_child(rim)

	var cs := CollisionShape3D.new()
	var ss := SphereShape3D.new()
	ss.radius = 0.6
	cs.shape = ss
	add_child(cs)
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	t += delta
	rotate_y(spin * delta)
	position.y = base_y + sin(t * 2.0 + phase) * 0.15


func _on_body_entered(body: Node3D) -> void:
	if taken:
		return
	if body.is_in_group("player"):
		taken = true
		set_deferred("monitoring", false)
		picked.emit(self)
		var tw := create_tween()
		tw.tween_property(self, "scale", Vector3.ONE * 1.6, 0.1)
		tw.tween_property(self, "scale", Vector3.ZERO, 0.12)
		tw.tween_callback(queue_free)
