class_name Dust
extends Node3D
## A small pool of cube-shaped dust puffs kicked up by the hooves. Puffs live in
## world space, so they are carried backwards with the scrolling ground.

const POOL_SIZE := 40
const LIFETIME := 0.55

## Ground scroll speed in m/s; set every frame by the owner.
var scroll_speed := 0.0

var _puffs: Array[MeshInstance3D] = []
var _velocity: Array[Vector3] = []
var _age: Array[float] = []
var _size: Array[float] = []
var _next := 0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE * 0.1
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.82, 0.68, 0.48)
	material.roughness = 1.0
	mesh.material = material
	for i in POOL_SIZE:
		var puff := MeshInstance3D.new()
		puff.mesh = mesh
		puff.visible = false
		puff.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(puff)
		_puffs.append(puff)
		_velocity.append(Vector3.ZERO)
		_age.append(LIFETIME)
		_size.append(1.0)


func emit(pos: Vector3, count: int = 2) -> void:
	for n in count:
		var i := _next
		_next = (_next + 1) % POOL_SIZE
		var puff := _puffs[i]
		puff.position = Vector3(pos.x, 0.05, pos.z)
		puff.rotation = Vector3(_rng.randf() * TAU, _rng.randf() * TAU, 0.0)
		_size[i] = _rng.randf_range(0.8, 1.6)
		puff.scale = Vector3.ONE * _size[i]
		puff.visible = true
		_velocity[i] = Vector3(_rng.randf_range(-0.6, 0.4), _rng.randf_range(0.7, 1.5), _rng.randf_range(-0.6, 0.6))
		_age[i] = 0.0


func _process(delta: float) -> void:
	for i in POOL_SIZE:
		if _age[i] >= LIFETIME:
			continue
		_age[i] += delta
		var puff := _puffs[i]
		if _age[i] >= LIFETIME:
			puff.visible = false
			continue
		_velocity[i].y -= 4.0 * delta
		puff.position += (_velocity[i] + Vector3(-scroll_speed, 0.0, 0.0)) * delta
		puff.position.y = maxf(puff.position.y, 0.03)
		puff.scale = Vector3.ONE * _size[i] * (1.0 - _age[i] / LIFETIME)
