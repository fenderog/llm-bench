extends Node3D
## Builds a small voxel sandbox world and a voxel character that runs
## around it. The character auto-patrols a loop; hold WASD / arrow keys
## to steer it yourself, release to resume the patrol.

const RUN_SPEED := 4.2
const TURN_SPEED := 12.0
const HEIGHT_LERP := 6.0

var character: Node3D
var left_leg: Node3D
var right_leg: Node3D
var left_arm: Node3D
var right_arm: Node3D
var head: Node3D
var sun: DirectionalLight3D
var camera: Camera3D

var run_time := 0.0
var facing := 0.0
var waypoints: Array[Vector2] = []
var wp_index := 0

func _ready() -> void:
	randomize()
	sun = $Sun
	sun.rotation_degrees = Vector3(-52, -35, 0)
	camera = $Camera3D

	build_ground()
	build_boundary()
	build_platforms()
	build_trees()
	build_decorations()
	_build_character()

	waypoints = [
		Vector2(-8, -8), Vector2(8, -8), Vector2(8, 2),
		Vector2(2, 8), Vector2(-4, 8), Vector2(-8, 2),
	]
	character.position = Vector3(waypoints[0].x, 0.0, waypoints[0].y)
	facing = 0.0

# ---------- World building ----------

func _mat(color: Color, rough := 0.85) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	return m

func _block(parent: Node, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _mat(color)
	mi.position = pos
	parent.add_child(mi)
	return mi

func build_ground() -> void:
	var root := Node3D.new()
	root.name = "Ground"
	add_child(root)
	var half := 12
	var greens := [Color(0.42, 0.62, 0.30), Color(0.46, 0.66, 0.32), Color(0.39, 0.58, 0.29)]
	for x in range(-half, half):
		for z in range(-half, half):
			var c: Color = greens[(x * 7 + z * 13) % greens.size()]
			_block(root, Vector3(x, -0.5, z), Vector3(1, 1, 1), c)

func build_boundary() -> void:
	var root := Node3D.new()
	root.name = "Boundary"
	add_child(root)
	var wall := Color(0.55, 0.42, 0.30)
	var half := 12
	for i in range(-half, half + 1):
		_block(root, Vector3(i, 0.5, -half - 0.5), Vector3(1, 1, 0.5), wall)
		_block(root, Vector3(i, 0.5, half + 0.5), Vector3(1, 1, 0.5), wall)
		_block(root, Vector3(-half - 0.5, 0.5, i), Vector3(0.5, 1, 1), wall)
		_block(root, Vector3(half + 0.5, 0.5, i), Vector3(0.5, 1, 1), wall)

## Raised voxel platforms the character runs up onto.
var _platforms: Array = [
	# [center, radius, height]
	[Vector2(-5, -5), 2, 1.0],
	[Vector2(5, 5), 2, 2.0],
	[Vector2(0, 0), 1, 0.5],
]

func build_platforms() -> void:
	var root := Node3D.new()
	root.name = "Platforms"
	add_child(root)
	var stone := Color(0.62, 0.60, 0.55)
	var stone_top := Color(0.68, 0.70, 0.62)
	for p in _platforms:
		var c: Vector2 = p[0]
		var r: int = p[1]
		var h: float = p[2]
		for x in range(-r, r + 1):
			for z in range(-r, r + 1):
				_block(root, Vector3(c.x + x, h / 2.0 - 0.5 + 0.0, c.y + z), Vector3(1, 1, 1), stone)
				_block(root, Vector3(c.x + x, h, c.y + z), Vector3(1, 0.2, 1), stone_top)

## Ground height at a world xz position (top of platforms / ground).
func ground_height(xz: Vector2) -> float:
	var h := 0.0
	for p in _platforms:
		var c: Vector2 = p[0]
		var r: int = p[1]
		if absf(xz.x - c.x) <= r + 0.5 and absf(xz.y - c.y) <= r + 0.5:
			h = maxf(h, p[2] as float)
	return h

func build_trees() -> void:
	var root := Node3D.new()
	root.name = "Trees"
	add_child(root)
	var trunk := Color(0.45, 0.31, 0.18)
	var leaf := Color(0.25, 0.5, 0.22)
	var spots := [Vector2(-9, 6), Vector2(9, -4), Vector2(-3, -9), Vector2(9, 9)]
	for s in spots:
		_block(root, Vector3(s.x, 0.5, s.y), Vector3(0.6, 1, 0.6), trunk)
		_block(root, Vector3(s.x, 1.5, s.y), Vector3(0.6, 1, 0.6), trunk)
		_block(root, Vector3(s.x, 2.4, s.y), Vector3(2.2, 1.4, 2.2), leaf)
		_block(root, Vector3(s.x, 3.4, s.y), Vector3(1.4, 0.8, 1.4), Color(0.3, 0.58, 0.25))

func build_decorations() -> void:
	var root := Node3D.new()
	root.name = "Decorations"
	add_child(root)
	var crate := Color(0.72, 0.55, 0.33)
	_block(root, Vector3(3, 0.5, -3), Vector3(1, 1, 1), crate)
	_block(root, Vector3(-7, 0.5, 5), Vector3(1, 1, 1), crate)
	var rock := Color(0.55, 0.55, 0.58)
	_block(root, Vector3(-1, 0.25, -6), Vector3(0.8, 0.5, 0.8), rock)
	_block(root, Vector3(6, 0.2, 1), Vector3(0.6, 0.4, 0.6), rock)
	var flowers := [Color(0.9, 0.3, 0.35), Color(0.95, 0.8, 0.2), Color(0.85, 0.5, 0.9)]
	for i in 14:
		var a := randf() * TAU
		var r := randf_range(3, 10)
		var f := Vector2(cos(a) * r, sin(a) * r)
		_block(root, Vector3(f.x, 0.1, f.y), Vector3(0.2, 0.2, 0.2), flowers[i % flowers.size()])

# ---------- Character ----------

func _build_character() -> void:
	character = Node3D.new()
	character.name = "Character"
	add_child(character)

	var body_c := Color(0.2, 0.5, 0.85)
	var limb_c := Color(0.16, 0.42, 0.72)
	var skin_c := Color(0.95, 0.8, 0.65)
	var pants_c := Color(0.3, 0.3, 0.35)

	# Torso
	_block(character, Vector3(0, 1.1, 0), Vector3(0.8, 0.9, 0.5), body_c)

	# Head (as pivot node so it can tilt)
	head = Node3D.new()
	head.position = Vector3(0, 1.65, 0)
	character.add_child(head)
	_block(head, Vector3(0, 0.25, 0), Vector3(0.65, 0.6, 0.65), skin_c)
	_block(head, Vector3(0, 0.5, 0.32), Vector3(0.65, 0.15, 0.06), Color(0.35, 0.25, 0.2)) # hair
	_block(head, Vector3(-0.14, 0.28, 0.34), Vector3(0.1, 0.12, 0.02), Color(0.1, 0.1, 0.12)) # eye L
	_block(head, Vector3(0.14, 0.28, 0.34), Vector3(0.1, 0.12, 0.02), Color(0.1, 0.1, 0.12)) # eye R

	# Arms pivot at shoulders
	left_arm = _limb(character, Vector3(-0.55, 1.45, 0), Vector3(0.28, 0.8, 0.34), limb_c, skin_c)
	right_arm = _limb(character, Vector3(0.55, 1.45, 0), Vector3(0.28, 0.8, 0.34), limb_c, skin_c)

	# Legs pivot at hips
	left_leg = _limb(character, Vector3(-0.22, 0.75, 0), Vector3(0.34, 0.75, 0.4), pants_c, Color(0.25, 0.2, 0.15))
	right_leg = _limb(character, Vector3(0.22, 0.75, 0), Vector3(0.34, 0.75, 0.4), pants_c, Color(0.25, 0.2, 0.15))

func _limb(parent: Node, pivot: Vector3, size: Vector3, main_c: Color, tip_c: Color) -> Node3D:
	var n := Node3D.new()
	n.position = pivot
	parent.add_child(n)
	_block(n, Vector3(0, -size.y / 2.0 + 0.05, 0), size, main_c)
	_block(n, Vector3(0, -size.y + 0.1, 0), Vector3(size.x, 0.2, size.z + 0.08), tip_c)
	return n

# ---------- Update loop ----------

func _process(delta: float) -> void:
	var steer := Vector2(
		Input.get_axis("ui_left", "ui_right"),
		Input.get_axis("ui_up", "ui_down")
	)
	var dir: Vector2
	if steer.length() > 0.1:
		dir = steer.normalized()
	else:
		var target := Vector2(waypoints[wp_index])
		var to_wp := target - Vector2(character.position.x, character.position.z)
		if to_wp.length() < 0.4:
			wp_index = (wp_index + 1) % waypoints.size()
		else:
			dir = to_wp.normalized()

	# Move & clamp to sandbox
	var pos := character.position
	pos.x = clampf(pos.x + dir.x * RUN_SPEED * delta, -11.0, 11.0)
	pos.z = clampf(pos.z + dir.y * RUN_SPEED * delta, -11.0, 11.0)
	facing = lerpf(facing, facing + _wrap_angle(atan2(dir.x, dir.y) - facing), clampf(TURN_SPEED * delta, 0.0, 1.0))
	pos.y = lerpf(pos.y, ground_height(Vector2(pos.x, pos.z)) + 0.05, clampf(HEIGHT_LERP * delta, 0.0, 1.0))
	character.position = pos
	character.rotation.y = facing

	# Run cycle animation
	run_time += delta * 13.0
	var swing := sin(run_time)
	var amp := deg_to_rad(52.0)
	left_leg.rotation.x = swing * amp
	right_leg.rotation.x = -swing * amp
	left_arm.rotation.x = -swing * amp * 0.9
	right_arm.rotation.x = swing * amp * 0.9
	character.position.y += absf(cos(run_time)) * 0.09
	head.rotation.x = 0.06 * sin(run_time * 0.5)

	# Camera follows behind
	var cam_target := pos + Vector3(0, 8.5, 9.5)
	camera.position = camera.position.lerp(cam_target, clampf(4.0 * delta, 0.0, 1.0))
	camera.look_at(pos + Vector3(0, 1.2, 0), Vector3.UP)

func _wrap_angle(a: float) -> float:
	while a > PI:
		a -= TAU
	while a < -PI:
		a += TAU
	return a
