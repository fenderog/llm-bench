extends Area3D
## Bouncy pad: launches the player upward on touch.

@export var power := 13.0

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1
	monitoring = true

	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = Vector3(1.6, 1.0, 1.6)
	shape.shape = box_shape
	shape.position = Vector3(0, 0.5, 0)
	add_child(shape)

	# Base slab (red) + white chevron stripes + dark rim.
	_add_box(Vector3(1.6, 0.25, 1.6), Color(0.8, 0.16, 0.2), Vector3(0, 0.12, 0))
	_add_box(Vector3(1.7, 0.1, 1.7), Color(0.15, 0.15, 0.18), Vector3(0, 0.03, 0))
	_add_box(Vector3(0.35, 0.28, 1.2), Color(0.95, 0.95, 0.95), Vector3(-0.35, 0.14, 0))
	_add_box(Vector3(0.35, 0.28, 1.2), Color(0.95, 0.95, 0.95), Vector3(0.35, 0.14, 0))

	body_entered.connect(_on_body_entered)


func _process(_delta: float) -> void:
	# Gentle pulse so players notice it.
	var s := 1.0 + sin(Time.get_ticks_msec() / 280.0) * 0.03
	scale = Vector3(s, 1.0, s)


func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player") and body.has_method("bounce"):
		body.bounce(power)


func _add_box(size: Vector3, color: Color, pos: Vector3) -> void:
	var mesh := BoxMesh.new()
	mesh.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.7
	mesh.material = mat
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.position = pos
	add_child(mi)
