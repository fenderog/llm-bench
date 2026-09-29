class_name VoxelWorld
extends Node3D
## Endless scrolling scenery. The horse stays at the origin and the world is
## pulled past it: ground tiles recycle, clouds and mountains drift slower.

const TILE_COUNT := 7
const TILE_LENGTH := Scenery.TILE_LENGTH
const VIEW_MIN_X := -24.0
const FENCE_Z := -2.6
const CLOUD_COUNT := 10
const CLOUD_SPAN := 200.0
const MOUNTAIN_SEGMENTS := 3
const MOUNTAIN_LENGTH := 120.0

var _rng := RandomNumberGenerator.new()
var _tiles: Array[Node3D] = []
var _tile_props: Array = []  # per tile: Array of {node, kind}
var _clouds: Array[MeshInstance3D] = []
var _mountains: Array[MeshInstance3D] = []
var _tree_meshes: Array[Mesh] = []
var _low_meshes: Array[Mesh] = []


func _ready() -> void:
	_rng.seed = 20240607
	_build_meshes()
	_build_far_ground()
	_build_tiles()
	_build_clouds()
	_build_mountains()


## Moves the world backwards by `distance` metres; `delta` drives the idle
## cloud drift.
func scroll(distance: float, delta: float) -> void:
	for i in _tiles.size():
		var tile := _tiles[i]
		tile.position.x -= distance
		if tile.position.x + TILE_LENGTH < VIEW_MIN_X:
			tile.position.x += TILE_COUNT * TILE_LENGTH
			_scatter(i)
	for cloud in _clouds:
		cloud.position.x -= distance * 0.08 + delta * 0.6
		if cloud.position.x < -CLOUD_SPAN * 0.5:
			cloud.position.x += CLOUD_SPAN
			cloud.position.z = _rng.randf_range(-90.0, -30.0)
	for ridge in _mountains:
		ridge.position.x -= distance * 0.04
		if ridge.position.x + MOUNTAIN_LENGTH < -MOUNTAIN_LENGTH * 1.5:
			ridge.position.x += MOUNTAIN_LENGTH * MOUNTAIN_SEGMENTS


func _build_meshes() -> void:
	_tree_meshes = [
		Scenery.tree(Color(0.26, 0.55, 0.22)),
		Scenery.tree(Color(0.34, 0.62, 0.24)),
		Scenery.tree(Color(0.86, 0.48, 0.14)),
		Scenery.pine(),
		Scenery.pine(),
	]
	_low_meshes = [
		Scenery.bush(Color(0.24, 0.50, 0.20)),
		Scenery.bush(Color(0.30, 0.58, 0.22)),
		Scenery.rock(),
	]


func _build_far_ground() -> void:
	var plane := MeshInstance3D.new()
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(700, 700)
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.30, 0.53, 0.20)
	material.roughness = 1.0
	mesh.material = material
	plane.mesh = mesh
	plane.position = Vector3(0, -0.28, 0)
	plane.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(plane)


func _build_tiles() -> void:
	var ground_variants: Array[Mesh] = [Scenery.ground_tile(11), Scenery.ground_tile(23)]
	var fence_mesh := Scenery.fence()
	for i in TILE_COUNT:
		var tile := Node3D.new()
		tile.position.x = VIEW_MIN_X - TILE_LENGTH + i * TILE_LENGTH
		add_child(tile)
		_tiles.append(tile)

		var ground := MeshInstance3D.new()
		ground.mesh = ground_variants[i % ground_variants.size()]
		ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		tile.add_child(ground)

		var fence := MeshInstance3D.new()
		fence.mesh = fence_mesh
		fence.position = Vector3(0, 0, FENCE_Z)
		tile.add_child(fence)

		var props: Array[Dictionary] = []
		for n in 3:
			props.append(_make_prop(tile, _tree_meshes[_rng.randi() % _tree_meshes.size()], "tree", true))
		for n in 3:
			props.append(_make_prop(tile, _tree_meshes[_rng.randi() % _tree_meshes.size()], "far", true))
		for n in 4:
			props.append(_make_prop(tile, _low_meshes[_rng.randi() % _low_meshes.size()], "low", false))
		_tile_props.append(props)
		_scatter(i)


func _make_prop(tile: Node3D, mesh: Mesh, kind: String, casts_shadow: bool) -> Dictionary:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	if not casts_shadow:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	tile.add_child(node)
	return {"node": node, "kind": kind}


## Re-rolls where a tile's trees, bushes and rocks stand.
func _scatter(tile_index: int) -> void:
	for prop: Dictionary in _tile_props[tile_index]:
		var node: MeshInstance3D = prop["node"]
		var x := _rng.randf_range(0.0, TILE_LENGTH)
		var z: float
		var s: float
		match prop["kind"]:
			"tree":
				z = -_rng.randf_range(3.8, 8.0)
				s = _rng.randf_range(0.85, 1.35)
			"far":
				z = -_rng.randf_range(8.5, 14.0)
				s = _rng.randf_range(1.5, 2.4)
			_:
				z = -_rng.randf_range(3.2, 7.5)
				s = _rng.randf_range(0.7, 1.15)
		node.position = Vector3(x, 0, z)
		node.scale = Vector3.ONE * s
		node.rotation.y = _rng.randi_range(0, 3) * PI * 0.5


func _build_clouds() -> void:
	for i in CLOUD_COUNT:
		var cloud := MeshInstance3D.new()
		cloud.mesh = Scenery.cloud(_rng)
		cloud.position = Vector3(
			_rng.randf_range(-CLOUD_SPAN * 0.5, CLOUD_SPAN * 0.5),
			_rng.randf_range(16.0, 28.0),
			_rng.randf_range(-90.0, -30.0))
		cloud.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(cloud)
		_clouds.append(cloud)


func _build_mountains() -> void:
	var meshes: Array[Mesh] = [
		Scenery.mountains(_rng, 60, 2.0),
		Scenery.mountains(_rng, 60, 2.0),
	]
	for i in MOUNTAIN_SEGMENTS:
		var ridge := MeshInstance3D.new()
		ridge.mesh = meshes[i % meshes.size()]
		ridge.position = Vector3(-MOUNTAIN_LENGTH * 1.5 + i * MOUNTAIN_LENGTH, -0.5, -85.0)
		ridge.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(ridge)
		_mountains.append(ridge)
