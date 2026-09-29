extends Node3D
## The endless world: scrolling ground, voxel trees / rocks / bushes, clouds and
## jumpable hurdles. The horse never moves; everything streams past it along +Z.

const VoxelBuilder = preload("res://voxel_builder.gd")
const GROUND_SHADER: Shader = preload("res://ground.gdshader")

signal hurdle_cleared
signal hurdle_hit

const DECOR_COUNT := 72
const CLOUD_COUNT := 14
const FAR_Z := -100.0
const NEAR_Z := 18.0
const HURDLE_POOL := 3
const HURDLE_CLEAR_LIFT := 0.45  # how high the horse must be to clear a hurdle
const GRAVITY := 14.0

var distance := 0.0

var _rng := RandomNumberGenerator.new()
var _ground_mat: ShaderMaterial
var _decor: Array[MeshInstance3D] = []
var _decor_kinds: Array = []  # Array of Array[ArrayMesh]
var _clouds: Array[MeshInstance3D] = []
var _hurdles: Array[Dictionary] = []
var _next_hurdle_at := 40.0


func _ready() -> void:
	_rng.randomize()
	_build_ground()
	_build_decor()
	_build_clouds()
	_build_hurdles()


func update(delta: float, speed: float, horse_lift: float) -> void:
	var step := speed * delta
	distance += step
	_ground_mat.set_shader_parameter("scroll", fmod(distance, 128.0))

	for mi in _decor:
		mi.position.z += step
		if mi.position.z > NEAR_Z:
			_respawn_decor(mi, false)

	for c in _clouds:
		c.position.z += step * 0.06 + delta * 1.5
		if c.position.z > 60.0:
			c.position.z = -170.0 - _rng.randf() * 30.0
			c.position.x = _rng.randf_range(-110.0, 110.0)

	_update_hurdles(delta, step, horse_lift)


# --- Ground --------------------------------------------------------------------

func _build_ground() -> void:
	_ground_mat = ShaderMaterial.new()
	_ground_mat.shader = GROUND_SHADER
	var plane := PlaneMesh.new()
	plane.size = Vector2(400, 400)
	plane.material = _ground_mat
	var mi := MeshInstance3D.new()
	mi.mesh = plane
	mi.position.z = -80.0
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)


# --- Scenery ---------------------------------------------------------------------

func _tint(base: Color, amount: float) -> Color:
	var k := 1.0 + _rng.randf_range(-amount, amount)
	return Color(base.r * k, base.g * k, base.b * k)


func _oak() -> ArrayMesh:
	var v := {}
	VoxelBuilder.add_box(v, Vector3i(-1, 0, -1), Vector3i(1, 7, 1), Color(0.36, 0.24, 0.14))
	var leaf := _tint(Color(0.22, 0.50, 0.18), 0.15)
	VoxelBuilder.add_box(v, Vector3i(-4, 6, -4), Vector3i(4, 11, 4), leaf, true)
	VoxelBuilder.add_box(v, Vector3i(-3, 11, -3), Vector3i(3, 14, 3), _tint(leaf, 0.08), true)
	for i in 3:
		var o := Vector3i(_rng.randi_range(-3, 1), _rng.randi_range(6, 9), _rng.randi_range(-3, 1))
		VoxelBuilder.add_box(v, o, o + Vector3i(4, 4, 4), _tint(leaf, 0.1), true)
	return VoxelBuilder.build(v, Vector3.ZERO, 0.2, 0.08)


func _pine() -> ArrayMesh:
	var v := {}
	VoxelBuilder.add_box(v, Vector3i(-1, 0, -1), Vector3i(1, 5, 1), Color(0.33, 0.22, 0.13))
	var leaf := _tint(Color(0.12, 0.36, 0.20), 0.12)
	var layers := _rng.randi_range(4, 6)
	for i in layers:
		var half := layers + 1 - i
		VoxelBuilder.add_box(v, Vector3i(-half, 4 + i * 2, -half), Vector3i(half, 6 + i * 2, half),
			_tint(leaf, 0.06), true)
	return VoxelBuilder.build(v, Vector3.ZERO, 0.2, 0.08)


func _bush() -> ArrayMesh:
	var v := {}
	var leaf := _tint(Color(0.25, 0.55, 0.20), 0.12)
	VoxelBuilder.add_box(v, Vector3i(-3, 0, -3), Vector3i(3, 3, 3), leaf, true)
	VoxelBuilder.add_box(v, Vector3i(-2, 3, -2), Vector3i(2, 4, 2), _tint(leaf, 0.08))
	if _rng.randf() < 0.5:
		var berry := Color(0.85, 0.2, 0.25) if _rng.randf() < 0.5 else Color(0.95, 0.85, 0.3)
		for i in 5:
			v[Vector3i(_rng.randi_range(-2, 1), _rng.randi_range(1, 3), 3 if _rng.randf() < 0.5 else -4)] = berry
	return VoxelBuilder.build(v, Vector3.ZERO, 0.2, 0.08)


func _rock() -> ArrayMesh:
	var v := {}
	var stone := _tint(Color(0.52, 0.52, 0.54), 0.12)
	VoxelBuilder.add_box(v, Vector3i(-3, 0, -2), Vector3i(3, 3, 3), stone, true)
	VoxelBuilder.add_box(v, Vector3i(-2, 3, -1), Vector3i(2, 5, 2), _tint(stone, 0.1), true)
	return VoxelBuilder.build(v, Vector3.ZERO, 0.22, 0.1)


func _build_decor() -> void:
	# Kinds are weighted by how many variants exist for each.
	var kinds: Array = [[], [], [], []]
	for i in 3:
		kinds[0].append(_oak())
	for i in 2:
		kinds[1].append(_pine())
	for i in 2:
		kinds[2].append(_bush())
	for i in 2:
		kinds[3].append(_rock())
	_decor_kinds = kinds
	for i in DECOR_COUNT:
		var mi := MeshInstance3D.new()
		add_child(mi)
		_decor.append(mi)
		_respawn_decor(mi, true)


func _respawn_decor(mi: MeshInstance3D, initial: bool) -> void:
	var r := _rng.randf()
	var kind: Array = _decor_kinds[0] if r < 0.40 else (_decor_kinds[1] if r < 0.68 else (_decor_kinds[2] if r < 0.88 else _decor_kinds[3]))
	mi.mesh = kind[_rng.randi() % kind.size()]
	var side := 1.0 if _rng.randf() < 0.5 else -1.0
	mi.position.x = side * (7.0 + pow(_rng.randf(), 1.7) * 32.0)
	if initial:
		mi.position.z = _rng.randf_range(FAR_Z, NEAR_Z)
	else:
		mi.position.z = FAR_Z - _rng.randf() * 12.0
	mi.position.y = 0.0
	var s := _rng.randf_range(0.8, 1.5)
	mi.scale = Vector3(s, s * _rng.randf_range(0.9, 1.25), s)
	mi.rotation.y = _rng.randi_range(0, 3) * PI * 0.5


func _build_clouds() -> void:
	var meshes: Array[ArrayMesh] = []
	for i in 3:
		var v := {}
		var white := Color(1, 1, 1)
		VoxelBuilder.add_box(v, Vector3i(-6, 0, -3), Vector3i(6, 2, 3), white, true)
		VoxelBuilder.add_box(v, Vector3i(-4, 2, -2), Vector3i(3, 4, 2), white, true)
		var o := Vector3i(_rng.randi_range(-8, 2), 0, _rng.randi_range(-2, 1))
		VoxelBuilder.add_box(v, o, o + Vector3i(6, 2, 4), white, true)
		meshes.append(VoxelBuilder.build(v, Vector3.ZERO, 1.6, 0.03))
	for i in CLOUD_COUNT:
		var mi := MeshInstance3D.new()
		mi.mesh = meshes[i % meshes.size()]
		mi.position = Vector3(_rng.randf_range(-110, 110), _rng.randf_range(28, 50), _rng.randf_range(-190, 40))
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		_clouds.append(mi)


# --- Hurdles ------------------------------------------------------------------------

func _hurdle_mesh() -> ArrayMesh:
	var v := {}
	var post := Color(0.85, 0.82, 0.75)
	for side in [-1, 1]:
		var x0: int = 30 if side > 0 else -32
		VoxelBuilder.add_box(v, Vector3i(x0, 0, -1), Vector3i(x0 + 2, 10, 1), post)
	for x in range(-30, 30):
		var stripe := (x + 30) / 6 % 2 == 0
		var col := Color(0.85, 0.2, 0.2) if stripe else Color(0.95, 0.95, 0.95)
		var col2 := Color(0.95, 0.95, 0.95) if stripe else Color(0.85, 0.2, 0.2)
		VoxelBuilder.add_box(v, Vector3i(x, 4, -1), Vector3i(x + 1, 6, 1), col)
		VoxelBuilder.add_box(v, Vector3i(x, 6, -1), Vector3i(x + 1, 8, 1), col2)
	return VoxelBuilder.build(v, Vector3.ZERO, 0.1, 0.03)


func _build_hurdles() -> void:
	var mesh := _hurdle_mesh()
	for i in HURDLE_POOL:
		var node := MeshInstance3D.new()
		node.mesh = mesh
		node.visible = false
		add_child(node)
		_hurdles.append({"node": node, "state": "idle", "vel": Vector3.ZERO, "spin": Vector3.ZERO})


func _spawn_hurdle() -> void:
	for h in _hurdles:
		if h["state"] == "idle":
			var node: MeshInstance3D = h["node"]
			node.position = Vector3(0, 0, FAR_Z + 10.0)
			node.rotation = Vector3.ZERO
			node.visible = true
			h["state"] = "coming"
			return


func _update_hurdles(delta: float, step: float, horse_lift: float) -> void:
	_next_hurdle_at -= step
	if _next_hurdle_at <= 0.0:
		_next_hurdle_at = _rng.randf_range(35.0, 60.0)
		_spawn_hurdle()

	for h in _hurdles:
		var state: String = h["state"]
		if state == "idle":
			continue
		var node: MeshInstance3D = h["node"]
		node.position.z += step
		var z := node.position.z
		if state == "coming":
			if absf(z) < 0.7 and horse_lift < HURDLE_CLEAR_LIFT:
				h["state"] = "hit"
				h["vel"] = Vector3(_rng.randf_range(-2, 2), 4.5, -_rng.randf_range(5, 8))
				h["spin"] = Vector3(_rng.randf_range(-6, 6), _rng.randf_range(-3, 3), _rng.randf_range(-3, 3))
				hurdle_hit.emit()
			elif z > 0.7:
				h["state"] = "cleared"
				hurdle_cleared.emit()
		elif state == "hit":
			var vel: Vector3 = h["vel"]
			vel.y -= GRAVITY * delta
			node.position += Vector3(vel.x, vel.y, vel.z) * delta
			node.rotation += (h["spin"] as Vector3) * delta
			if node.position.y < 0.0:
				node.position.y = 0.0
				vel = Vector3(vel.x * 0.4, absf(vel.y) * 0.3 if absf(vel.y) > 1.5 else 0.0, vel.z * 0.4)
				h["spin"] = (h["spin"] as Vector3) * 0.5
			h["vel"] = vel
		if node.position.z > NEAR_Z:
			node.visible = false
			h["state"] = "idle"
