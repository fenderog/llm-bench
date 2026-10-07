extends Node3D
## Builds a voxel horse out of cubes, plus a grassy field, trees, rocks and a
## fence, all from code so the project needs no external assets.
##
## Controls: W/Up run, S/Down back up, A/D or Left/Right steer,
## Shift gallop, R reset.

const VOXEL := 0.1            # world size of one horse voxel (metres)
const SCENERY_VOXEL := 0.5    # world size of one tree voxel
const BODY_Y := 14.5          # body height in horse voxels, so hooves touch y = 0
const NECK_TILT := -0.5       # radians, neck leans forward from the withers
const HORSE_RADIUS := 0.8     # collision radius against trees and rocks
const GROUND_HALF := 50       # grass tiles span -50..50 on both axes
const FENCE_RADIUS := 46.0
const ROAM_RADIUS := 40.0

const MAX_SPEED := 9.0        # m/s
const BOOST_SPEED := 14.0     # m/s while holding Shift
const REVERSE_SPEED := 2.5
const ACCEL := 6.0
const DECEL := 5.0
const TURN_RATE := 1.8        # radians per second at full steer

const COAT := Color(0.55, 0.33, 0.17)
const LEG := Color(0.36, 0.22, 0.11)
const MANE := Color(0.12, 0.07, 0.04)
const MUZZLE := Color(0.82, 0.66, 0.5)
const SADDLE := Color(0.25, 0.12, 0.05)
const HOOF := Color(0.1, 0.08, 0.06)
const EYE := Color(0.05, 0.05, 0.05)
const WHITE := Color(0.95, 0.95, 0.93)
const GRASS := Color(0.33, 0.62, 0.26)
const WOOD := Color(0.5, 0.36, 0.2)
const TRUNK := Color(0.4, 0.26, 0.13)
const ROCK := Color(0.5, 0.5, 0.52)
const LEAVES := [
	Color(0.18, 0.45, 0.2),
	Color(0.22, 0.52, 0.24),
	Color(0.14, 0.38, 0.18),
]

var horse: Node3D
var body: Node3D
var neck: Node3D
var head: Node3D
var tail: Node3D
var legs: Array[Dictionary] = []
var camera: Camera3D
var hud: Label

var speed := 0.0
var heading := 0.0
var phase := 0.0   # stride position in cycles, 0..1
var time := 0.0

var rng := RandomNumberGenerator.new()
var _cube := BoxMesh.new()
var _materials: Dictionary = {}
var _scenery: Array[Dictionary] = []     # {"xform": Transform3D, "color": Color}
var _obstacles: Array[Dictionary] = []   # {"pos": Vector2, "radius": float}


func _ready() -> void:
	rng.seed = 2026
	_cube.size = Vector3.ONE
	_build_environment()
	_build_world()
	_build_horse()
	_build_camera()
	_build_hud()
	_reset()


func _process(delta: float) -> void:
	time += delta

	var throttle := 0.0
	if _held(KEY_W) or _held(KEY_UP):
		throttle += 1.0
	if _held(KEY_S) or _held(KEY_DOWN):
		throttle -= 1.0
	var steer := 0.0
	if _held(KEY_A) or _held(KEY_LEFT):
		steer += 1.0
	if _held(KEY_D) or _held(KEY_RIGHT):
		steer -= 1.0

	var target := 0.0
	if throttle > 0.0:
		target = BOOST_SPEED if _held(KEY_SHIFT) else MAX_SPEED
	elif throttle < 0.0:
		target = -REVERSE_SPEED
	var rate := ACCEL if absf(target) > absf(speed) else DECEL
	speed = move_toward(speed, target, rate * delta)

	# Turning is slower when standing still, and flips when backing up.
	var direction := 1.0 if speed >= 0.0 else -1.0
	var turn_factor := clampf(absf(speed) / 3.0, 0.35, 1.0)
	heading += steer * TURN_RATE * turn_factor * direction * delta

	_keep_in_field(delta)
	horse.position += Vector3(-sin(heading), 0.0, -cos(heading)) * speed * delta
	_push_out_of_obstacles()
	horse.rotation.y = heading

	_animate(delta, steer)
	_update_camera(delta)
	_update_hud()


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key and key.pressed and not key.echo and key.keycode == KEY_R:
		_reset()


func _held(key: Key) -> bool:
	return Input.is_key_pressed(key)


func _reset() -> void:
	horse.position = Vector3.ZERO
	horse.rotation = Vector3.ZERO
	heading = 0.0
	speed = 0.0
	camera.global_position = horse.global_transform * Vector3(0.0, 3.0, 7.0)


# --- Movement -------------------------------------------------------------

func _keep_in_field(delta: float) -> void:
	var flat := Vector2(horse.position.x, horse.position.z)
	if flat.length() > ROAM_RADIUS:
		# Smoothly turn the horse back toward the middle of the field.
		var want := atan2(flat.x, flat.y)
		heading = lerp_angle(heading, want, clampf(delta * 2.0, 0.0, 1.0))
		flat = flat.limit_length(ROAM_RADIUS)
		horse.position = Vector3(flat.x, 0.0, flat.y)


func _push_out_of_obstacles() -> void:
	var p := Vector2(horse.position.x, horse.position.z)
	for o in _obstacles:
		var offset: Vector2 = p - o["pos"]
		var min_dist: float = o["radius"] + HORSE_RADIUS
		if offset.length() < min_dist:
			var n := offset.normalized() if offset.length() > 0.001 else Vector2.RIGHT
			p = o["pos"] + n * min_dist
			speed *= 0.5
	horse.position = Vector3(p.x, 0.0, p.y)


# --- Animation ------------------------------------------------------------

func _animate(delta: float, steer: float) -> void:
	# gait is 0 when standing and 1 at trot speed or faster, so the legs
	# settle smoothly instead of snapping.
	var gait := clampf(absf(speed) / 4.0, 0.0, 1.0)
	phase = fmod(phase + delta * (0.8 + absf(speed) * 0.12), 1.0)

	# Gallop footfall: fore pair and hind pair each move together, with a
	# small lag between left and right.
	for leg in legs:
		var a: float = TAU * (phase + leg["offset"])
		leg["upper"].rotation.x = sin(a) * leg["swing"] * gait
		leg["lower"].rotation.x = -maxf(cos(a), 0.0) * 0.6 * gait

	var s := sin(TAU * phase)
	body.position.y = BODY_Y * VOXEL + 0.05 * gait * absf(s)
	body.rotation.x = 0.03 * gait * s
	neck.rotation.x = NECK_TILT + 0.05 * gait * s
	tail.rotation.x = -0.3 - 0.5 * gait
	tail.rotation.z = sin(time * 4.0) * 0.15 * (0.4 + gait)
	horse.rotation.z = lerpf(horse.rotation.z, steer * 0.06 * gait, 1.0 - exp(-delta * 6.0))


func _update_camera(delta: float) -> void:
	var gait := clampf(absf(speed) / 4.0, 0.0, 1.0)
	var target := horse.global_transform * Vector3(0.0, 3.0, 7.0)
	camera.global_position = camera.global_position.lerp(target, 1.0 - exp(-delta * 5.0))
	camera.look_at(horse.global_transform * Vector3(0.0, 1.4, -2.0), Vector3.UP)
	camera.fov = lerpf(camera.fov, 60.0 + 12.0 * gait, 1.0 - exp(-delta * 3.0))


func _update_hud() -> void:
	hud.text = "%s  |  %.0f km/h\nW/Up run   S/Down back   A/D steer   Shift gallop   R reset" % [_gait_name(), absf(speed) * 3.6]


func _gait_name() -> String:
	var s := absf(speed)
	if s < 0.2:
		return "Standing"
	if s < 3.0:
		return "Walking"
	if s < 6.5:
		return "Trotting"
	if s < 10.0:
		return "Cantering"
	return "Galloping"


# --- Horse construction ---------------------------------------------------

func _build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	body = _pivot(horse, Vector3(0.0, BODY_Y, 0.0))

	# Torso, rump and saddle.
	_block(body, Vector3(0, 0, -1), Vector3(7, 6, 10), COAT)
	_block(body, Vector3(0, 0.25, 3.5), Vector3(8, 6.5, 5), COAT)
	_block(body, Vector3(0, 3.6, -0.5), Vector3(4.6, 0.8, 4.2), SADDLE)

	tail = _pivot(body, Vector3(0, 1.5, 6.2))
	_block(tail, Vector3(0, -2.2, 0.4), Vector3(1.2, 4.4, 1.0), MANE)
	_block(tail, Vector3(0, -4.9, 0.6), Vector3(1.8, 1.6, 1.6), MANE)

	# Neck, mane and head. The head is a child of the neck, so it follows
	# the neck's bob.
	neck = _pivot(body, Vector3(0, 2.5, -5.5))
	neck.rotation.x = NECK_TILT
	_block(neck, Vector3(0, 2.25, 0), Vector3(3, 4.5, 3), COAT)
	_block(neck, Vector3(0, 2.6, 1.9), Vector3(0.8, 4.8, 0.9), MANE)

	head = _pivot(neck, Vector3(0, 4.5, 0))
	head.rotation.x = 0.25
	_block(head, Vector3(0, 0.6, -1.2), Vector3(2.8, 2.8, 4.0), COAT)
	_block(head, Vector3(0, -0.4, -3.8), Vector3(2.4, 2.2, 2.0), MUZZLE)
	_block(head, Vector3(0, 0.3, -4.85), Vector3(0.9, 1.2, 0.2), WHITE)
	for side in [-1.0, 1.0]:
		_block(head, Vector3(1.45 * side, 0.9, -2.0), Vector3(0.2, 0.7, 0.7), EYE)
		_block(head, Vector3(0.7 * side, 2.2, -0.2), Vector3(0.6, 1.3, 0.6), COAT)

	# Legs: each has an upper pivot at the hip or shoulder and a lower pivot
	# at the knee, so the lower leg bends with the stride. The hoof touches
	# the ground when the leg is straight.
	var leg_specs := [
		{"pos": Vector3(-2.5, -2.5, -4.5), "offset": 0.0, "swing": 0.55},
		{"pos": Vector3(2.5, -2.5, -4.5), "offset": 0.04, "swing": 0.55},
		{"pos": Vector3(-2.5, -2.5, 4.0), "offset": 0.42, "swing": 0.5},
		{"pos": Vector3(2.5, -2.5, 4.0), "offset": 0.46, "swing": 0.5},
	]
	for spec in leg_specs:
		var upper := _pivot(body, spec["pos"])
		_block(upper, Vector3(0, -3, 0), Vector3(2, 6, 2), COAT)
		var lower := _pivot(upper, Vector3(0, -6, 0))
		_block(lower, Vector3(0, -2.5, 0), Vector3(1.8, 5, 1.8), LEG)
		_block(lower, Vector3(0, -5.5, 0), Vector3(2.0, 1.0, 2.2), HOOF)
		legs.append({"upper": upper, "lower": lower, "offset": spec["offset"], "swing": spec["swing"]})


# --- World construction ---------------------------------------------------

func _build_environment() -> void:
	var sky := Color(0.56, 0.78, 0.96)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.9, 0.93, 1.0)
	env.ambient_light_energy = 0.8
	env.fog_enabled = true
	env.fog_light_color = sky
	env.fog_density = 0.008

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -35, 0)
	sun.shadow_enabled = true
	add_child(sun)


func _build_world() -> void:
	# Grass: one tile per metre with a little colour variation.
	for x in range(-GROUND_HALF, GROUND_HALF + 1):
		for z in range(-GROUND_HALF, GROUND_HALF + 1):
			_scenery_box(Vector3(x, -0.25, z), Vector3(1, 0.5, 1), _jitter(GRASS, rng.randf_range(0.9, 1.08)))

	# Fence ring: a post per segment, two rails between posts.
	var segments := 64
	for i in segments:
		var a0 := TAU * i / segments
		var a1 := TAU * (i + 1) / segments
		var p0 := Vector3(cos(a0), 0.0, sin(a0)) * FENCE_RADIUS
		var p1 := Vector3(cos(a1), 0.0, sin(a1)) * FENCE_RADIUS
		var dir := p1 - p0
		var yaw := atan2(dir.x, dir.z)
		_scenery_box(p0 + Vector3(0, 0.6, 0), Vector3(0.2, 1.2, 0.2), WOOD)
		for h in [0.4, 0.9]:
			_scenery_box((p0 + p1) * 0.5 + Vector3(0, h, 0), Vector3(0.12, 0.14, dir.length() + 0.05), WOOD, yaw)

	# Scatter trees and rocks, keeping the start area clear.
	for i in 30:
		var angle := rng.randf() * TAU
		var dist := rng.randf_range(10.0, 38.0)
		var spot := Vector3(cos(angle), 0.0, sin(angle)) * dist
		if rng.randf() < 0.75:
			_scenery_tree(spot)
		else:
			_scenery_rock(spot)

	_flush_scenery()


func _scenery_tree(base: Vector3) -> void:
	var trunk_h := rng.randi_range(4, 6)
	for y in trunk_h:
		_scenery_box(base + Vector3(0, (y + 0.5) * SCENERY_VOXEL, 0), Vector3.ONE * SCENERY_VOXEL, TRUNK)

	# Leaves form a rough ball on top of the trunk.
	var crown := base + Vector3(0, (trunk_h + 0.5) * SCENERY_VOXEL, 0)
	for x in range(-2, 3):
		for y in range(-1, 3):
			for z in range(-2, 3):
				var offset := Vector3(x, y, z)
				if offset.length() < 2.7 and rng.randf() > 0.1:
					var leaf: Color = LEAVES[rng.randi_range(0, LEAVES.size() - 1)]
					_scenery_box(crown + offset * SCENERY_VOXEL, Vector3.ONE * SCENERY_VOXEL, leaf)

	_obstacles.append({"pos": Vector2(base.x, base.z), "radius": 0.35})


func _scenery_rock(base: Vector3) -> void:
	var s := rng.randf_range(0.5, 0.9)
	_scenery_box(base + Vector3(0, s * 0.35, 0), Vector3(s * 1.4, s * 0.7, s * 1.1), ROCK, rng.randf_range(0.0, TAU))
	_obstacles.append({"pos": Vector2(base.x, base.z), "radius": s * 0.7})


# --- Helpers --------------------------------------------------------------

func _build_camera() -> void:
	camera = Camera3D.new()
	camera.fov = 60.0
	camera.current = true
	add_child(camera)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Label.new()
	hud.position = Vector2(16, 12)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_color", Color.WHITE)
	hud.add_theme_color_override("font_outline_color", Color.BLACK)
	hud.add_theme_constant_override("outline_size", 6)
	layer.add_child(hud)


## Pivot node at a voxel-space position, so limbs can rotate around a joint.
func _pivot(parent: Node3D, pos: Vector3) -> Node3D:
	var node := Node3D.new()
	node.position = pos * VOXEL
	parent.add_child(node)
	return node


## Horse voxel: a cube whose centre and size are given in horse voxels.
func _block(parent: Node3D, center: Vector3, size: Vector3, color: Color) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = _cube
	mi.material_override = _material(color)
	mi.position = center * VOXEL
	mi.scale = size * VOXEL
	parent.add_child(mi)


## Queues a box for the shared scenery MultiMesh. Positions and sizes are in metres.
func _scenery_box(pos: Vector3, size: Vector3, color: Color, yaw: float = 0.0) -> void:
	_scenery.append({
		"xform": Transform3D(Basis(Vector3.UP, yaw).scaled(size), pos),
		"color": color,
	})


## Puts every queued scenery box into one MultiMesh, which keeps draw calls low.
func _flush_scenery() -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = _cube
	mm.instance_count = _scenery.size()
	for i in _scenery.size():
		mm.set_instance_transform(i, _scenery[i]["xform"])
		mm.set_instance_color(i, _scenery[i]["color"])

	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.95

	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	add_child(mmi)
	_scenery.clear()


func _material(color: Color) -> StandardMaterial3D:
	if not _materials.has(color):
		var mat := StandardMaterial3D.new()
		mat.albedo_color = color
		mat.roughness = 0.9
		_materials[color] = mat
	return _materials[color]


func _jitter(color: Color, amount: float) -> Color:
	return Color(color.r * amount, color.g * amount, color.b * amount)
