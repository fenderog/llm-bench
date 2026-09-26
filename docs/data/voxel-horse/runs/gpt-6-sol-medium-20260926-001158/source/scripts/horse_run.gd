extends Node3D
## A horse assembled entirely from colored cubes. All positions are local to its body.

const COAT := Color("#a75b34")
const COAT_LIGHT := Color("#c47b47")
const COAT_DARK := Color("#854125")
const MANE := Color("#442a24")
const HOOVES := Color("#33323a")
const CREAM := Color("#e9d9ae")

var horse: Node3D
var neck: Node3D
var head: Node3D
var tail: Node3D
var upper_legs: Array[Node3D] = []
var lower_legs: Array[Node3D] = []
var time_running := 0.0


func _ready() -> void:
	_make_world()
	_make_horse()


func _process(delta: float) -> void:
	time_running += delta * 8.0
	var stride := time_running
	# Diagonal pairs alternate, and bent knees lift clear of the turf.
	for i in range(4):
		var phase := 0.0 if i == 0 or i == 3 else PI
		var cycle := sin(stride + phase)
		upper_legs[i].rotation.z = cycle * 0.43
		lower_legs[i].rotation.z = -0.13 - maxf(0.0, cycle) * 0.50
	var beat := stride * 2.0
	horse.position.y = 1.85 + 0.055 * cos(beat)
	horse.rotation.z = 0.025 * sin(beat)
	neck.rotation.z = 0.035 * sin(beat + 0.6)
	head.rotation.z = 0.055 * sin(beat + 1.1)
	tail.rotation.z = -0.13 + 0.19 * sin(stride + 0.8)


func _make_world() -> void:
	var environment := WorldEnvironment.new()
	var settings := Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color("#a9cfe9")
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color("#e1edff")
	settings.ambient_light_energy = 0.75
	environment.environment = settings
	add_child(environment)

	_cube(self, "Grass", Vector3(200, 0.18, 200), Vector3(0, -0.12, 0), Color("#81a96a"))
	# A few fixed bands give the otherwise empty ground a sense of scale.
	for x in range(-5, 6):
		_cube(self, "Grass patch", Vector3(0.10, 0.015, 0.7), Vector3(float(x) * 1.8, -0.015, -1.9), Color("#9cbb79"))

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-42, -35, -20)
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	add_child(sun)

	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 7.3
	camera.position = Vector3(4.8, 3.2, 8.5)
	add_child(camera)
	camera.look_at(Vector3(0, 1.5, 0), Vector3.UP)
	camera.current = true


func _make_horse() -> void:
	horse = Node3D.new()
	horse.name = "RunningHorse"
	horse.position.y = 1.85
	add_child(horse)

	_cube(horse, "Barrel", Vector3(2.35, 0.90, 0.82), Vector3(0, 0, 0), COAT)
	_cube(horse, "Rump", Vector3(0.69, 0.95, 0.89), Vector3(-0.88, 0.03, 0), COAT_LIGHT)
	_cube(horse, "Shoulders", Vector3(0.74, 1.02, 0.91), Vector3(0.77, 0, 0), COAT)
	_cube(horse, "Chest blaze", Vector3(0.08, 0.45, 0.50), Vector3(1.18, -0.20, 0), CREAM)

	# The upward neck and long muzzle distinguish the silhouette from a generic quadruped.
	neck = Node3D.new()
	neck.name = "NeckPivot"
	neck.position = Vector3(0.91, 0.30, 0)
	horse.add_child(neck)
	_cube(neck, "Neck", Vector3(0.69, 1.04, 0.64), Vector3(0.20, 0.43, 0), COAT)
	_cube(neck, "Crest", Vector3(0.25, 0.84, 0.68), Vector3(-0.20, 0.56, 0), MANE)
	for j in range(4):
		_cube(neck, "Mane tuft %d" % j, Vector3(0.29, 0.24, 0.70), Vector3(-0.31 - 0.12 * j, 0.85 - 0.16 * j, 0), MANE)

	head = Node3D.new()
	head.name = "HeadPivot"
	head.position = Vector3(0.45, 0.88, 0)
	neck.add_child(head)
	_cube(head, "Skull", Vector3(0.88, 0.52, 0.57), Vector3(0.19, 0.09, 0), COAT_LIGHT)
	_cube(head, "Long muzzle", Vector3(0.55, 0.36, 0.50), Vector3(0.70, -0.13, 0), COAT)
	_cube(head, "Soft nose", Vector3(0.27, 0.23, 0.52), Vector3(0.92, -0.16, 0), CREAM)
	_cube(head, "Forelock", Vector3(0.37, 0.19, 0.62), Vector3(0.23, 0.38, 0), MANE)
	for side in [-1, 1]:
		var z := float(side)
		_cube(head, "Ear %d" % side, Vector3(0.23, 0.44, 0.20), Vector3(-0.09, 0.52, 0.21 * z), COAT_DARK)
		_cube(head, "Eye %d" % side, Vector3(0.13, 0.13, 0.035), Vector3(0.43, 0.16, 0.302 * z), HOOVES)
		_cube(head, "Nostril %d" % side, Vector3(0.09, 0.07, 0.035), Vector3(0.98, -0.10, 0.277 * z), HOOVES)

	tail = Node3D.new()
	tail.name = "TailPivot"
	tail.position = Vector3(-1.16, 0.32, 0)
	horse.add_child(tail)
	_cube(tail, "Tail root", Vector3(0.48, 0.22, 0.29), Vector3(-0.20, 0.03, 0), MANE)
	_cube(tail, "Tail middle", Vector3(0.50, 0.26, 0.32), Vector3(-0.56, -0.13, 0), MANE)
	_cube(tail, "Tail tip", Vector3(0.28, 0.42, 0.27), Vector3(-0.78, -0.39, 0), MANE)

	for front in [true, false]:
		for side in [-1, 1]:
			var x := 0.79 if front else -0.83
			var z := float(side) * 0.32
			var upper := Node3D.new()
			upper.name = ("Front" if front else "Hind") + ("Near" if side == 1 else "Far") + "Leg"
			upper.position = Vector3(x, -0.36, z)
			horse.add_child(upper)
			_cube(upper, "Upper leg", Vector3(0.34, 0.76, 0.31), Vector3(0, -0.38, 0), COAT_DARK if side == -1 else COAT)
			var lower := Node3D.new()
			lower.name = "KneeAndShin"
			lower.position.y = -0.76
			upper.add_child(lower)
			_cube(lower, "Shin", Vector3(0.25, 0.57, 0.26), Vector3(0, -0.29, 0), COAT_LIGHT)
			_cube(lower, "Dark hoof", Vector3(0.37, 0.21, 0.34), Vector3(0.07, -0.63, 0), HOOVES)
			upper_legs.append(upper)
			lower_legs.append(lower)


func _cube(parent: Node3D, label: String, dimensions: Vector3, offset: Vector3, color: Color) -> MeshInstance3D:
	var cube := MeshInstance3D.new()
	cube.name = label
	var mesh := BoxMesh.new()
	mesh.size = dimensions
	cube.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 1.0
	cube.material_override = material
	cube.position = offset
	parent.add_child(cube)
	return cube
