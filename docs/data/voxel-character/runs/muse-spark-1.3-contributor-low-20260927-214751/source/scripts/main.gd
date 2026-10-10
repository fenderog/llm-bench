extends Node3D
## Builds the voxel sandbox (ground, fence, trees, rocks, crates, gems)
## and runs the collect-the-gems game loop.

const GEM_TOTAL := 8

var _mats: Dictionary = {}
var _gems: Array[Node3D] = []
var _gem_base_y: Dictionary = {}
var _collected := 0
var _time := 0.0
var _best := -1.0
var _won := false
var _spin := 0.0

@onready var player: CharacterBody3D = $Player
@onready var hud: CanvasLayer = $HUD
@onready var sandbox: Node3D = $Sandbox


func _ready() -> void:
	_build_ground()
	_build_fence()
	_build_trees()
	_build_rocks()
	_build_crates()
	_build_flowers()
	_build_clouds()
	_spawn_gems()
	hud.set_gems(_collected, GEM_TOTAL)
	hud.set_time(_time, _best)


func _process(delta: float) -> void:
	if Input.is_physical_key_pressed(KEY_R) and _reset_cooldown <= 0.0:
		_reset_game()
	_reset_cooldown = maxf(0.0, _reset_cooldown - delta)
	if not _won:
		_time += delta
		hud.set_time(_time, _best)
	# Spin + bob gems.
	_spin += delta * 2.2
	for i in _gems.size():
		var g: Node3D = _gems[i]
		if not is_instance_valid(g) or g.visible == false:
			continue
		g.rotation.y = _spin + float(i) * 0.7
		var base_y: float = _gem_base_y.get(g.get_instance_id(), 1.0)
		g.position.y = base_y + sin(_spin * 1.6 + float(i)) * 0.15
	hud.set_speed(player.get_horizontal_speed(), player.is_sprinting_now())


var _reset_cooldown := 0.0


func _on_gem_collected(gem: Node3D) -> void:
	if _won or not gem.visible:
		return
	gem.visible = false
	# Move it far away so its Area3D stops firing.
	gem.position.y = -50.0
	_collected += 1
	hud.set_gems(_collected, GEM_TOTAL)
	if _collected >= GEM_TOTAL:
		_won = true
		if _best < 0.0 or _time < _best:
			_best = _time
		hud.show_win(_time, _best)
		hud.set_time(_time, _best)


func _reset_game() -> void:
	_reset_cooldown = 0.5
	_collected = 0
	_time = 0.0
	_won = false
	for g in _gems:
		if is_instance_valid(g):
			g.visible = true
			var base_y: float = _gem_base_y.get(g.get_instance_id(), 1.0)
			g.position.y = base_y
	player.reset_to_spawn()
	hud.hide_win()
	hud.set_gems(_collected, GEM_TOTAL)
	hud.set_time(_time, _best)


# ---------------------------------------------------------------- voxel helper

func _mat(color: Color, emission: float = 0.0) -> StandardMaterial3D:
	var key := str(color.to_html()) + "|" + str(emission)
	if _mats.has(key):
		return _mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.9
	m.specular_mode = StandardMaterial3D.SPECULAR_DISABLED
	if emission > 0.0:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = emission
	_mats[key] = m
	return m


func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, emission: float = 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(color, emission)
	mi.mesh = bm
	mi.position = pos
	parent.add_child(mi)
	return mi


func _solid_box(parent: Node3D, size: Vector3, pos: Vector3, color: Color) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	col.shape = shape
	body.add_child(col)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(color)
	mi.mesh = bm
	body.add_child(mi)
	parent.add_child(body)
	return body


# ---------------------------------------------------------------- builders

func _build_ground() -> void:
	# Thick sandbox slab + grass top + checker of light tufts.
	_solid_box(sandbox, Vector3(26, 1, 26), Vector3(0, -0.5, 0), Color(0.55, 0.38, 0.25))
	_solid_box(sandbox, Vector3(26, 0.12, 26), Vector3(0, 0.06, 0), Color(0.42, 0.68, 0.35))
	# Sandy play patch in the middle.
	_box(sandbox, Vector3(10, 0.14, 10), Vector3(0, 0.08, 0), Color(0.85, 0.76, 0.55))
	# Corner grass tufts (flat voxels, no collision).
	var tuft := Color(0.35, 0.6, 0.3)
	for x in range(-11, 12, 2):
		for z in range(-11, 12, 2):
			if absf(float(x)) < 5.5 and absf(float(z)) < 5.5:
				continue
			if (x + z) % 4 == 0:
				_box(sandbox, Vector3(0.5, 0.18, 0.5), Vector3(float(x), 0.18, float(z)), tuft)


func _build_fence() -> void:
	var wood := Color(0.6, 0.42, 0.26)
	var wood_dark := Color(0.48, 0.33, 0.2)
	var h := 12.4  # half-size of play area
	# Rails (long solid boxes keep the player inside).
	_solid_box(sandbox, Vector3(26, 0.25, 0.4), Vector3(0, 0.9, -h), wood)
	_solid_box(sandbox, Vector3(26, 0.25, 0.4), Vector3(0, 0.9, h), wood)
	_solid_box(sandbox, Vector3(0.4, 0.25, 26), Vector3(-h, 0.9, 0), wood)
	_solid_box(sandbox, Vector3(0.4, 0.25, 26), Vector3(h, 0.9, 0), wood)
	# Posts with caps.
	var p := -12.0
	while p <= 12.01:
		_box(sandbox, Vector3(0.45, 1.3, 0.45), Vector3(p, 0.65, -h), wood_dark)
		_box(sandbox, Vector3(0.6, 0.2, 0.6), Vector3(p, 1.38, -h), wood)
		_box(sandbox, Vector3(0.45, 1.3, 0.45), Vector3(p, 0.65, h), wood_dark)
		_box(sandbox, Vector3(0.6, 0.2, 0.6), Vector3(p, 1.38, h), wood)
		_box(sandbox, Vector3(0.45, 1.3, 0.45), Vector3(-h, 0.65, p), wood_dark)
		_box(sandbox, Vector3(0.6, 0.2, 0.6), Vector3(-h, 1.38, p), wood)
		_box(sandbox, Vector3(0.45, 1.3, 0.45), Vector3(h, 0.65, p), wood_dark)
		_box(sandbox, Vector3(0.6, 0.2, 0.6), Vector3(h, 1.38, p), wood)
		p += 3.0


func _tree(pos: Vector3, leaf: Color) -> void:
	var trunk := Color(0.45, 0.3, 0.18)
	var tb := StaticBody3D.new()
	tb.position = pos
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(0.7, 2.2, 0.7)
	col.shape = shape
	col.position = Vector3(0, 1.1, 0)
	tb.add_child(col)
	sandbox.add_child(tb)
	_box(tb, Vector3(0.7, 2.2, 0.7), Vector3(0, 1.1, 0), trunk)
	# Chunky voxel canopy.
	_box(tb, Vector3(2.2, 1.2, 2.2), Vector3(0, 2.8, 0), leaf)
	_box(tb, Vector3(1.4, 1.0, 1.4), Vector3(0, 3.7, 0), leaf.lightened(0.08))
	_box(tb, Vector3(0.7, 0.6, 0.7), Vector3(0.6, 2.3, 0.4), leaf.darkened(0.08))
	_box(tb, Vector3(0.6, 0.5, 0.6), Vector3(-0.7, 4.0, -0.3), leaf.lightened(0.15))


func _build_trees() -> void:
	_tree(Vector3(-9, 0, -8), Color(0.25, 0.55, 0.28))
	_tree(Vector3(9, 0, -7), Color(0.3, 0.6, 0.3))
	_tree(Vector3(-8.5, 0, 8.5), Color(0.22, 0.5, 0.26))
	_tree(Vector3(8.5, 0, 9), Color(0.28, 0.58, 0.3))


func _build_rocks() -> void:
	var rock := Color(0.55, 0.57, 0.6)
	var rock_dark := Color(0.45, 0.47, 0.5)
	_box(sandbox, Vector3(1.2, 0.7, 1.0), Vector3(-4, 0.35, -3), rock)
	_box(sandbox, Vector3(0.7, 0.5, 0.7), Vector3(-3.4, 0.85, -2.8), rock_dark)
	_box(sandbox, Vector3(1.0, 0.6, 1.3), Vector3(5, 0.3, 2), rock_dark)
	_box(sandbox, Vector3(0.8, 0.9, 0.8), Vector3(4.2, 0.45, -5.5), rock)
	_box(sandbox, Vector3(1.4, 0.5, 0.9), Vector3(-6, 0.25, 3.5), rock)


func _build_crates() -> void:
	var crate := Color(0.72, 0.53, 0.3)
	var edge := Color(0.55, 0.39, 0.2)
	var spots: Array = [
		[Vector3(-2.5, 0.5, -7), 1.0],
		[Vector3(-1.3, 0.4, -7.1), 0.8],
		[Vector3(6.5, 0.5, 5.5), 1.0],
		[Vector3(6.5, 1.4, 5.5), 0.8],
		[Vector3(-7, 0.5, -1), 1.0],
	]
	for s in spots:
		var pos: Vector3 = s[0]
		var sc: float = s[1]
		var b := _solid_box(sandbox, Vector3(sc, sc, sc), pos + Vector3(0, 0, 0), crate)
		# Edge trim so it reads as a voxel crate.
		_box(b, Vector3(sc * 1.04, sc * 0.15, sc * 1.04), Vector3(0, sc * 0.42, 0), edge)
		_box(b, Vector3(sc * 1.04, sc * 0.15, sc * 1.04), Vector3(0, -sc * 0.42, 0), edge)


func _build_flowers() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1234
	var cols: Array[Color] = [Color(0.95, 0.3, 0.35), Color(0.95, 0.8, 0.25), Color(0.9, 0.9, 0.95), Color(0.7, 0.35, 0.85)]
	for i in 14:
		var x := rng.randf_range(-11.0, 11.0)
		var z := rng.randf_range(-11.0, 11.0)
		if absf(x) < 5.5 and absf(z) < 5.5:
			continue
		_box(sandbox, Vector3(0.12, 0.35, 0.12), Vector3(x, 0.3, z), Color(0.3, 0.55, 0.3))
		_box(sandbox, Vector3(0.3, 0.22, 0.3), Vector3(x, 0.55, z), cols[i % cols.size()])


func _build_clouds() -> void:
	var white := Color(0.97, 0.98, 1.0)
	var spots: Array = [
		Vector3(-8, 12, -10), Vector3(6, 13.5, -6),
		Vector3(0, 11.5, 8), Vector3(10, 12.5, 9), Vector3(-11, 13, 6),
	]
	for s in spots:
		var p: Vector3 = s
		_box(sandbox, Vector3(3.0, 1.0, 1.8), p, white)
		_box(sandbox, Vector3(1.8, 0.8, 1.4), p + Vector3(1.2, 0.6, 0.3), white)
		_box(sandbox, Vector3(1.5, 0.7, 1.2), p + Vector3(-1.3, 0.5, -0.2), white)


func _spawn_gems() -> void:
	var spots: Array[Vector3] = [
		Vector3(-9, 1.0, -3), Vector3(9.5, 1.0, -2.5),
		Vector3(-4, 1.0, 8.5), Vector3(4, 1.0, -8.5),
		Vector3(0, 1.0, 0.5), Vector3(-8, 1.0, 4.5),
		Vector3(8, 1.0, 8), Vector3(0, 1.9, -4.5),
	]
	var gem_col := Color(0.3, 0.9, 1.0)
	for i in spots.size():
		var gem := Node3D.new()
		gem.name = "Gem%d" % i
		gem.position = spots[i]
		sandbox.add_child(gem)
		# Voxel gem: small base cube + big rotated octahedron-ish cube.
		_box(gem, Vector3(0.35, 0.2, 0.35), Vector3(0, -0.35, 0), Color(0.5, 0.4, 0.3))
		var top := _box(gem, Vector3(0.55, 0.55, 0.55), Vector3.ZERO, gem_col, 0.9)
		top.rotation = Vector3(0.6, 0.6, 0.0)
		var area := Area3D.new()
		var col := CollisionShape3D.new()
		var sphere := SphereShape3D.new()
		sphere.radius = 1.0
		col.shape = sphere
		area.add_child(col)
		gem.add_child(area)
		area.body_entered.connect(_on_gem_body.bind(gem))
		_gems.append(gem)
		_gem_base_y[gem.get_instance_id()] = gem.position.y


func _on_gem_body(body: Node3D, gem: Node3D) -> void:
	if body.is_in_group("player"):
		_on_gem_collected(gem)
