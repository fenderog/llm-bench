extends Node3D

# The horse faces +X. Each limb has a shoulder/hip pivot and a separately swinging knee.
const COAT := Color("a65b32")
const COAT_LIGHT := Color("c47a43")
const COAT_DARK := Color("713a28")
const MANE := Color("34251f")
const HOOVES := Color("282a2c")
const MUZZLE := Color("dfb18b")
const WHITE := Color("f6eee0")
const SKY := Color("a7d5e8")

var horse: Node3D
var head_pivot: Node3D
var tail_pivot: Node3D
var legs: Array[Node3D] = []
var knees: Array[Node3D] = []
var time := 0.0


func _ready() -> void:
	_make_world()
	_make_horse()


func _process(delta: float) -> void:
	time += delta
	var stride := time * 9.0
	horse.position.y = 0.10 + 0.12 * sin(stride * 2.0)
	horse.rotation.z = 0.025 * sin(stride * 2.0 + 0.7)
	# Diagonal pairs alternate, with a bent knee during the lifted half of each step.
	for i in range(4):
		var phase := stride + (0.0 if i == 0 or i == 3 else PI)
		legs[i].rotation.z = 0.54 * sin(phase)
		knees[i].rotation.z = -0.15 - 0.48 * maxf(0.0, sin(phase + 0.6))
	head_pivot.rotation.z = 0.045 * sin(stride * 2.0 + 1.0)
	tail_pivot.rotation.z = 0.18 * sin(stride + 1.0)


func _make_world() -> void:
	RenderingServer.set_default_clear_color(SKY)
	var ground := _box(self, "Grass", Vector3(0, -0.23, 0), Vector3(200, 0.3, 200), Color("71975e"))
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-48, -32, -20)
	sun.light_energy = 1.7
	sun.shadow_enabled = true
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.name = "Fill"
	fill.rotation_degrees = Vector3(-25, 135, 0)
	fill.light_energy = 0.5
	add_child(fill)
	var camera := Camera3D.new()
	camera.name = "Camera"
	camera.position = Vector3(4.7, 2.8, 7.7)
	add_child(camera)
	camera.look_at(Vector3(0, 1.45, 0))
	camera.fov = 38.0
	camera.current = true
	# Small ground markings make the fixed-camera running-in-place gait readable.
	for i in range(-8, 9):
		_box(self, "GroundMark", Vector3(i * 2.2, -0.065, -1.9), Vector3(0.75, 0.015, 0.07), Color("d1bb83"))


func _make_horse() -> void:
	horse = Node3D.new()
	horse.name = "Horse"
	add_child(horse)
	_box(horse, "Torso", Vector3(0, 1.69, 0), Vector3(2.45, 0.95, 0.86), COAT)
	_box(horse, "Chest", Vector3(0.86, 1.65, 0), Vector3(0.69, 1.04, 0.91), COAT_LIGHT)
	_box(horse, "Rump", Vector3(-0.91, 1.68, 0), Vector3(0.64, 0.96, 0.91), COAT_LIGHT)
	_box(horse, "BackHighlight", Vector3(-0.05, 2.19, 0), Vector3(1.55, 0.11, 0.78), COAT_DARK)

	# The neck rises diagonally toward the head, rather than resembling a second torso.
	var neck := Node3D.new()
	neck.name = "Neck"
	neck.position = Vector3(0.94, 1.99, 0)
	neck.rotation.z = -0.46
	horse.add_child(neck)
	_box(neck, "NeckBlock", Vector3(0.18, 0.47, 0), Vector3(0.65, 1.27, 0.68), COAT_LIGHT)
	for j in range(4):
		_box(neck, "Mane%d" % j, Vector3(-0.21, 0.18 + j * 0.27, 0), Vector3(0.22, 0.23, 0.73), MANE)
	head_pivot = Node3D.new()
	head_pivot.name = "HeadPivot"
	head_pivot.position = Vector3(0.35, 1.04, 0)
	neck.add_child(head_pivot)
	_box(head_pivot, "Head", Vector3(0.21, 0.10, 0), Vector3(0.85, 0.65, 0.61), COAT)
	_box(head_pivot, "LongMuzzle", Vector3(0.73, -0.14, 0), Vector3(0.61, 0.40, 0.55), MUZZLE)
	_box(head_pivot, "Nose", Vector3(1.04, -0.19, 0), Vector3(0.10, 0.20, 0.57), COAT_DARK)
	for side in [-1.0, 1.0]:
		_box(head_pivot, "EyeWhite", Vector3(0.36, 0.20, side * 0.317), Vector3(0.16, 0.17, 0.035), WHITE)
		_box(head_pivot, "Pupil", Vector3(0.41, 0.19, side * 0.344), Vector3(0.085, 0.095, 0.026), MANE)
		_box(head_pivot, "Ear", Vector3(-0.04, 0.57, side * 0.22), Vector3(0.19, 0.38, 0.19), COAT_DARK)

	tail_pivot = Node3D.new()
	tail_pivot.name = "TailPivot"
	tail_pivot.position = Vector3(-1.21, 1.93, 0)
	horse.add_child(tail_pivot)
	_box(tail_pivot, "TailRoot", Vector3(-0.28, 0.05, 0), Vector3(0.6, 0.25, 0.30), MANE)
	_box(tail_pivot, "TailTip", Vector3(-0.62, -0.23, 0), Vector3(0.39, 0.63, 0.35), MANE)

	for x in [-0.87, 0.87]:
		for z in [-0.30, 0.30]:
			var leg := Node3D.new()
			leg.name = ("Front" if x > 0 else "Rear") + ("Near" if z > 0 else "Far")
			leg.position = Vector3(x, 1.28, z)
			horse.add_child(leg)
			_box(leg, "UpperLeg", Vector3(0, -0.27, 0), Vector3(0.34, 0.64, 0.29), COAT_DARK if z < 0 else COAT)
			var knee := Node3D.new()
			knee.name = "Knee"
			knee.position.y = -0.57
			leg.add_child(knee)
			_box(knee, "LowerLeg", Vector3(0, -0.27, 0), Vector3(0.25, 0.59, 0.24), COAT_LIGHT)
			_box(knee, "Hoof", Vector3(0.07, -0.60, 0), Vector3(0.43, 0.23, 0.33), HOOVES)
			legs.append(leg)
			knees.append(knee)


func _box(parent: Node3D, part_name: String, center: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var part := MeshInstance3D.new()
	part.name = part_name
	part.position = center
	var mesh := BoxMesh.new()
	mesh.size = size
	part.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 1.0
	part.material_override = material
	parent.add_child(part)
	return part
