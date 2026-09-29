class_name Hurdles
extends Node3D
## Jump hurdles that scroll towards the horse. Jump to clear them; hit one at a
## trot or gallop and it is knocked flying and the horse stumbles. At a walk the
## horse just nudges them aside, and none are spawned.

signal cleared
signal knocked

const HEIGHT := 0.6         # top of the rails, metres
const CELL := 0.1
const SPAWN_X := 34.0
const DESPAWN_X := -22.0
const MIN_GAIT := 0.75      # below this gait hurdles carry no penalty
const GRAVITY := 12.0

var enabled := true

var _mesh: ArrayMesh
var _live: Array[Dictionary] = []    # {node, resolved}
var _flying: Array[Dictionary] = []  # {node, vel, spin, age}
var _until_next := 24.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_mesh = _build_mesh()


## Advances everything by `distance` metres of ground scroll.
func update(distance: float, delta: float, horse: VoxelHorse) -> void:
	if enabled and horse.target_gait >= 1.0:
		_until_next -= distance
		if _until_next <= 0.0:
			_spawn()
			_until_next = _rng.randf_range(20.0, 32.0)

	var reach := _hoof_range(horse)
	for i in range(_live.size() - 1, -1, -1):
		var hurdle := _live[i]
		var node: Node3D = hurdle["node"]
		node.position.x -= distance
		var x := node.position.x
		if not hurdle["resolved"]:
			if x + 0.12 > reach.x and x - 0.12 < reach.y and horse.jump_height < HEIGHT - 0.05:
				_knock(hurdle, horse, distance / maxf(delta, 0.0001))
				_live.remove_at(i)
				continue
		if not hurdle["resolved"] and x < reach.x - 0.3:
			hurdle["resolved"] = true
			if horse.gait >= MIN_GAIT:
				cleared.emit()
		if x < DESPAWN_X:
			node.queue_free()
			_live.remove_at(i)

	_update_flying(distance / maxf(delta, 0.0001), delta)


func _spawn() -> void:
	var node := MeshInstance3D.new()
	node.mesh = _mesh
	node.position = Vector3(SPAWN_X, 0.0, 0.0)
	add_child(node)
	_live.append({"node": node, "resolved": false})


## Sends a hurdle tumbling. At a walk it is only nudged aside, at a trot or
## gallop it costs the horse a stumble.
func _knock(hurdle: Dictionary, horse: VoxelHorse, speed: float) -> void:
	var node: Node3D = hurdle["node"]
	var hard := horse.gait >= MIN_GAIT
	var power := 1.0 if hard else 0.35
	_flying.append({
		"node": node,
		"vel": Vector3(2.0 + speed * 0.3, 3.5 + _rng.randf() * 1.5, _rng.randf_range(-1.0, 1.0)) * power,
		"spin": Vector3(_rng.randf_range(-3.0, 3.0), _rng.randf_range(-2.0, 2.0), _rng.randf_range(-9.0, -4.0)) * power,
		"age": 0.0,
	})
	if hard:
		horse.stumble()
		knocked.emit()


func _update_flying(speed: float, delta: float) -> void:
	for i in range(_flying.size() - 1, -1, -1):
		var item := _flying[i]
		var node: Node3D = item["node"]
		var vel: Vector3 = item["vel"]
		vel.y -= GRAVITY * delta
		node.position += (vel + Vector3(-speed, 0.0, 0.0)) * delta
		node.rotation += item["spin"] * delta
		if node.position.y < 0.05 and vel.y < 0.0:
			node.position.y = 0.05
			vel.y *= -0.35
			vel.x *= 0.6
		item["vel"] = vel
		item["age"] += delta
		if item["age"] > 2.2 or node.position.x < DESPAWN_X:
			node.queue_free()
			_flying.remove_at(i)


## World-space X extent of the four hooves as (min, max).
func _hoof_range(horse: VoxelHorse) -> Vector2:
	var lo := INF
	var hi := -INF
	for i in horse.legs.size():
		var x := horse.hoof_position(i).x
		lo = minf(lo, x)
		hi = maxf(hi, x)
	return Vector2(lo, hi)


func _build_mesh() -> ArrayMesh:
	var v := {}
	var red := Color(0.80, 0.15, 0.15)
	var white := Color(0.96, 0.95, 0.90)
	# Posts at both ends, rails striped in red and white in between.
	VoxelMesh.fill_box(v, Vector3i(-1, 0, -13), Vector3i(0, 6, -12), white, 0.03)
	VoxelMesh.fill_box(v, Vector3i(-1, 0, 11), Vector3i(0, 6, 12), white, 0.03)
	VoxelMesh.fill_box(v, Vector3i(-1, 6, -13), Vector3i(0, 6, -12), red)
	VoxelMesh.fill_box(v, Vector3i(-1, 6, 11), Vector3i(0, 6, 12), red)
	for z in range(-11, 11):
		var stripe_is_red := (((z + 11) >> 2) & 1) == 0
		# The two rails are offset by one stripe so they alternate.
		VoxelMesh.fill_box(v, Vector3i(-1, 1, z), Vector3i(0, 2, z), red if stripe_is_red else white, 0.02)
		VoxelMesh.fill_box(v, Vector3i(-1, 4, z), Vector3i(0, 5, z), white if stripe_is_red else red, 0.02)
	return VoxelMesh.build(v, CELL)
