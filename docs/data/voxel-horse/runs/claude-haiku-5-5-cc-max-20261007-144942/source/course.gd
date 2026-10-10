class_name Course
extends Node3D

## The scenery for the gallop: sky, a grassy field with a dirt track, and trees,
## rocks and flowers that stream past. The horse runs toward -Z, so anything at
## travel distance d sits at z = -d.

const ROW_SPACING := 4.0
const SPAWN_AHEAD := 170.0
const CULL_BEHIND := 40.0

var _ground: MeshInstance3D
var _track: MeshInstance3D
var _scenery: Node3D
var _next_row := -10.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_build_sky()
	_ground = _slab(Vector3(200.0, 1.0, 1000.0), Color(0.36, 0.62, 0.28), -0.5)
	_track = _slab(Vector3(14.0, 0.02, 1000.0), Color(0.64, 0.50, 0.33), 0.01)
	_scenery = Node3D.new()
	add_child(_scenery)
	follow(0.0)


## Moves the ground under the horse and streams scenery in and out.
func follow(distance: float) -> void:
	_ground.position.z = -distance
	_track.position.z = -distance
	while _next_row < distance + SPAWN_AHEAD:
		_spawn_row(_next_row)
		_next_row += ROW_SPACING
	for node in _scenery.get_children():
		if node.get_meta("row") < distance - CULL_BEHIND:
			node.queue_free()


## Places a hurdle across the track at travel `distance`, centred on `lane`.
func add_hurdle(distance: float, lane: float) -> Node3D:
	var hurdle := Node3D.new()
	hurdle.position = Vector3(lane, 0.0, -distance)
	add_child(hurdle)
	VoxelBuilder.hurdle(hurdle)
	return hurdle


func _build_sky() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.30, 0.55, 0.90)
	sky_material.sky_horizon_color = Color(0.75, 0.86, 0.95)
	sky_material.ground_horizon_color = Color(0.55, 0.72, 0.45)
	sky_material.ground_bottom_color = Color(0.30, 0.45, 0.25)
	var sky := Sky.new()
	sky.sky_material = sky_material

	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	add_child(world_environment)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, 30.0, 0.0)
	sun.shadow_enabled = true
	add_child(sun)


func _slab(size: Vector3, color: Color, height: float) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	var slab := MeshInstance3D.new()
	slab.mesh = mesh
	slab.material_override = material
	slab.position.y = height
	add_child(slab)
	return slab


func _spawn_row(row: float) -> void:
	for side in [-1.0, 1.0]:
		if _rng.randf() < 0.4:
			continue
		var node := Node3D.new()
		node.position = Vector3(side * _rng.randf_range(8.0, 18.0), 0.0, -row)
		node.set_meta("row", row)
		_scenery.add_child(node)
		var roll := _rng.randf()
		if roll < 0.5:
			VoxelBuilder.tree(node, _rng)
		elif roll < 0.7:
			VoxelBuilder.rock(node, _rng)
		else:
			VoxelBuilder.flowers(node, _rng)
