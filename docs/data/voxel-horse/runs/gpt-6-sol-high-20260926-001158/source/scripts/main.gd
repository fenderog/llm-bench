extends Node3D

# The horse is assembled at startup so the project needs no imported assets.
const COAT := Color("a86338")
const COAT_LIGHT := Color("c78348")
const COAT_DARK := Color("814523")
const MANE := Color("35251f")
const HOOF := Color("302b2a")
const MUZZLE := Color("d49b78")
const EYE := Color("171614")

const STRIDE_SPEED := 8.5

var horse: Node3D
var neck: Node3D
var tail: Node3D
var upper_legs: Array[Node3D] = []
var lower_legs: Array[Node3D] = []
var leg_phases: Array[float] = [0.0, PI * 0.8, PI * 1.3, PI * 0.3]
var elapsed := 0.0
var materials: Dictionary = {}


func _ready() -> void:
	_make_setting()
	_make_horse()


func _process(delta: float) -> void:
	elapsed += delta * STRIDE_SPEED
	horse.position.y = 1.66 + 0.06 * cos(2.0 * elapsed)
	horse.rotation.z = 0.035 * sin(elapsed)
	horse.rotation.x = 0.025 * sin(elapsed + 0.4)
	neck.rotation.z = -0.045 * sin(elapsed + 0.6)
	tail.rotation.y = 0.22 * sin(elapsed + 0.5)
	tail.rotation.z = 0.15 * sin(elapsed - 0.3)
	for i in range(upper_legs.size()):
		var phase := elapsed + leg_phases[i]
		upper_legs[i].rotation.z = 0.55 * sin(phase)
		lower_legs[i].rotation.z = 0.15 + 0.55 * maxf(0.0, sin(phase - 0.7))


func _make_setting() -> void:
	var world := WorldEnvironment.new()
	world.name = "Daylight"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("bad9ed")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("e4ecf1")
	environment.ambient_light_energy = 0.65
	world.environment = environment
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-55.0, -35.0, 0.0)
	sun.light_energy = 1.7
	sun.shadow_enabled = true
	add_child(sun)

	var camera := Camera3D.new()
	camera.name = "Camera"
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 5.4
	camera.position = Vector3(3.6, 3.2, 6.7)
	add_child(camera)
	camera.look_at(Vector3(0.0, 1.25, 0.0))
	camera.current = true

	_box(self, "Grass", Vector3(60.0, 0.4, 60.0), Vector3(0.0, -0.22, 0.0), Color("689857"))
	_box(self, "Running track", Vector3(18.0, 0.05, 3.8), Vector3(0.0, -0.007, 0.0), Color("c49a64"))
	for side in [-1.0, 1.0]:
		for x in range(-8, 9, 2):
			_box(self, "Lane dash", Vector3(0.8, 0.012, 0.045), Vector3(float(x), 0.025, side * 1.65), Color("f4dbac"))


func _make_horse() -> void:
	horse = Node3D.new()
	horse.name = "RunningHorse"
	horse.position.y = 1.66
	add_child(horse)

	_box(horse, "Barrel", Vector3(1.9, 0.82, 0.72), Vector3.ZERO, COAT)
	_box(horse, "Chest", Vector3(0.49, 0.86, 0.7), Vector3(0.68, 0.01, 0.0), COAT_LIGHT)
	_box(horse, "Rump", Vector3(0.44, 0.76, 0.69), Vector3(-0.72, 0.0, 0.0), COAT)
	_box(horse, "Back highlight", Vector3(1.34, 0.07, 0.56), Vector3(-0.05, 0.44, 0.0), COAT_LIGHT)

	# Each leg has a hip and knee, so both the stride and the knee tuck move.
	for front in [true, false]:
		for side in [1.0, -1.0]:
			var upper := Node3D.new()
			upper.name = ("Front" if front else "Hind") + ("Near" if side > 0.0 else "Far") + "Hip"
			upper.position = Vector3(0.68 if front else -0.68, -0.37, side * 0.275)
			horse.add_child(upper)
			_box(upper, "Upper leg", Vector3(0.28 if front else 0.34, 0.63, 0.24), Vector3(0.0, -0.315, 0.0), COAT_DARK if side < 0.0 else COAT)
			var lower := Node3D.new()
			lower.name = "Knee"
			lower.position.y = -0.63
			upper.add_child(lower)
			_box(lower, "Lower leg", Vector3(0.19, 0.53, 0.19), Vector3(0.0, -0.265, 0.0), COAT_DARK)
			_box(lower, "Hoof", Vector3(0.28, 0.17, 0.26), Vector3(0.045, -0.615, 0.0), HOOF)
			upper_legs.append(upper)
			lower_legs.append(lower)

	neck = Node3D.new()
	neck.name = "NeckAndHead"
	neck.position = Vector3(0.59, 0.26, 0.0)
	horse.add_child(neck)
	var neck_mesh := _box(neck, "Neck", Vector3(0.49, 0.9, 0.52), Vector3(0.16, 0.32, 0.0), COAT)
	neck_mesh.rotation.z = -0.33
	_box(neck, "Head", Vector3(0.68, 0.38, 0.5), Vector3(0.6, 0.86, 0.0), COAT_LIGHT)
	_box(neck, "Long muzzle", Vector3(0.43, 0.27, 0.43), Vector3(1.02, 0.72, 0.0), MUZZLE)
	_box(neck, "Nose", Vector3(0.055, 0.11, 0.33), Vector3(1.25, 0.67, 0.0), COAT_DARK)
	_box(neck, "Blaze", Vector3(0.11, 0.24, 0.13), Vector3(0.9, 1.005, 0.0), Color("efd8ae"))
	for side in [-1.0, 1.0]:
		_box(neck, "Ear", Vector3(0.18, 0.32, 0.14), Vector3(0.39, 1.2, side * 0.18), COAT_DARK)
		_box(neck, "Inner ear", Vector3(0.1, 0.17, 0.015), Vector3(0.42, 1.22, side * 0.255), MUZZLE)
		_box(neck, "Eye", Vector3(0.11, 0.105, 0.035), Vector3(0.74, 0.94, side * 0.262), EYE)
		_box(neck, "Eye glint", Vector3(0.025, 0.025, 0.009), Vector3(0.755, 0.965, side * 0.285), Color.WHITE)
	for i in range(4):
		_box(neck, "Mane tuft", Vector3(0.2, 0.23, 0.42), Vector3(-0.12 + i * 0.105, 0.44 + i * 0.18, 0.0), MANE)

	tail = Node3D.new()
	tail.name = "SwishingTail"
	tail.position = Vector3(-0.96, 0.23, 0.0)
	horse.add_child(tail)
	var tail_base := _box(tail, "Tail base", Vector3(0.49, 0.2, 0.23), Vector3(-0.22, -0.04, 0.0), COAT_DARK)
	tail_base.rotation.z = -0.25
	var tail_hair := _box(tail, "Tail hair", Vector3(0.6, 0.24, 0.29), Vector3(-0.64, -0.22, 0.0), MANE)
	tail_hair.rotation.z = 0.35
	_box(tail, "Tail tip", Vector3(0.26, 0.29, 0.23), Vector3(-0.89, -0.35, 0.0), MANE)


func _box(parent: Node3D, part_name: String, dimensions: Vector3, location: Vector3, color: Color) -> MeshInstance3D:
	var part := MeshInstance3D.new()
	part.name = part_name
	var mesh := BoxMesh.new()
	mesh.size = dimensions
	part.mesh = mesh
	if not materials.has(color):
		var material := StandardMaterial3D.new()
		material.albedo_color = color
		material.roughness = 1.0
		materials[color] = material
	part.material_override = materials[color]
	part.position = location
	parent.add_child(part)
	return part
