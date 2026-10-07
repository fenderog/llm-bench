extends Node3D

## A voxel horse gallops round a circular track. Steer, set the pace and jump
## the hurdles. Everything, including the scenery, is built in code.

const TRACK_RADIUS := 60.0
const TRACK_HALF_WIDTH := 5.0
const TRACK_HEIGHT := 0.08
const TRACK_TILES := 420
const TRACK_LENGTH := TAU * TRACK_RADIUS
const LANE_LIMIT := 3.8
const STEER_RATE := 5.5

const CRUISE_SPEED := 11.0
const TOP_SPEED := 22.0
const ACCEL := 8.0
const BRAKE := 14.0
const DRAG := 2.5
const STUMBLE_SPEED := 4.0

const GRAVITY := 22.0
const JUMP_SPEED := 8.5
const CLEAR_HEIGHT := 1.0
const HURDLE_HALF_WIDTH := 1.5
const HURDLE_LANES := [-1.5, 1.0, -0.5, 2.0, -2.0, 0.5, 1.5, -1.0]

const GRASS := Color(0.3, 0.55, 0.2)
const DIRT_A := Color(0.62, 0.45, 0.28)
const DIRT_B := Color(0.58, 0.41, 0.25)
const CHALK := Color(0.95, 0.95, 0.92)
const RED := Color(0.85, 0.12, 0.12)
const POST := Color(0.3, 0.3, 0.32)
const TRUNK := Color(0.4, 0.26, 0.14)
const LEAF_A := Color(0.2, 0.5, 0.2)
const LEAF_B := Color(0.26, 0.6, 0.24)

var _distance := 0.0
var _lane := 0.0
var _lean := 0.0
var _speed := CRUISE_SPEED
var _height := 0.0
var _vertical_speed := 0.0
var _jump_queued := false
var _cleared := 0
var _faults := 0
var _message_time := 0.0
var _hurdle_distances: Array[float] = []

var _horse: VoxelHorse
var _camera: Camera3D
var _stats_label: Label
var _message_label: Label


func _ready() -> void:
	for k in HURDLE_LANES.size():
		_hurdle_distances.append(TRACK_LENGTH * (k + 0.5) / HURDLE_LANES.size())

	_build_environment()
	_build_ground()
	_build_track()
	_build_hurdles()
	_build_trees()

	_horse = VoxelHorse.new()
	add_child(_horse)

	_camera = Camera3D.new()
	_camera.fov = 60.0
	add_child(_camera)
	_camera.current = true

	_build_hud()
	_place_horse()
	_update_camera(1.0)


func _process(delta: float) -> void:
	_update_speed(delta)
	_update_steering(delta)
	_update_jump(delta)

	var previous := _distance
	_distance += _speed * delta
	_check_hurdles(previous, _distance)

	_place_horse()
	_horse.update_gait(delta, _speed / TOP_SPEED, _height > 0.0)
	_update_camera(delta)
	_update_hud(delta)


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	if key.keycode == KEY_SPACE:
		_jump_queued = true
	elif key.keycode == KEY_R:
		_reset()


func _held(a: Key, b: Key) -> bool:
	return Input.is_key_pressed(a) or Input.is_key_pressed(b)


func _update_speed(delta: float) -> void:
	var target := CRUISE_SPEED
	var rate := DRAG
	if _held(KEY_W, KEY_UP):
		target = TOP_SPEED
		rate = ACCEL
	elif _held(KEY_S, KEY_DOWN):
		target = 0.0
		rate = BRAKE
	_speed = move_toward(_speed, target, rate * delta)


func _update_steering(delta: float) -> void:
	# Right is towards the centre of the track, so steering right lowers the lane value.
	var steer := (1.0 if _held(KEY_D, KEY_RIGHT) else 0.0) - (1.0 if _held(KEY_A, KEY_LEFT) else 0.0)
	_lane = clampf(_lane - steer * STEER_RATE * delta, -LANE_LIMIT, LANE_LIMIT)
	_lean = lerpf(_lean, -steer * 0.12, minf(1.0, delta * 8.0))


func _update_jump(delta: float) -> void:
	if _jump_queued and _height <= 0.0:
		_vertical_speed = JUMP_SPEED
	_jump_queued = false
	if _height > 0.0 or _vertical_speed > 0.0:
		_vertical_speed -= GRAVITY * delta
		_height = maxf(_height + _vertical_speed * delta, 0.0)
		if _height == 0.0:
			_vertical_speed = 0.0


func _check_hurdles(previous: float, current: float) -> void:
	var before := fmod(previous, TRACK_LENGTH)
	var after := fmod(current, TRACK_LENGTH)
	for k in _hurdle_distances.size():
		if not _is_crossed(_hurdle_distances[k], before, after):
			continue
		if absf(_lane - HURDLE_LANES[k]) > HURDLE_HALF_WIDTH:
			continue
		if _height >= CLEAR_HEIGHT:
			_cleared += 1
			_show_message("Clear!")
		else:
			_faults += 1
			_speed = minf(_speed, STUMBLE_SPEED)
			_show_message("Stumble!")


func _is_crossed(point: float, previous: float, current: float) -> bool:
	if current >= previous:
		return previous < point and point <= current
	# The horse passed the start line during this frame.
	return point > previous or point <= current


func _place_horse() -> void:
	var angle := _distance / TRACK_RADIUS
	var radius := TRACK_RADIUS + _lane
	_horse.position = Vector3(cos(angle) * radius, TRACK_HEIGHT + _height, sin(angle) * radius)
	_horse.rotation = Vector3(0.0, PI - angle, _lean)


func _update_camera(delta: float) -> void:
	var angle := _distance / TRACK_RADIUS
	var forward := Vector3(-sin(angle), 0.0, cos(angle))
	var desired := _horse.position - forward * 9.0 + Vector3.UP * 3.8
	_camera.global_position = _camera.global_position.lerp(desired, 1.0 - exp(-6.0 * delta))
	_camera.look_at(_horse.position + forward * 2.0 + Vector3.UP * 1.2, Vector3.UP)


func _show_message(text: String) -> void:
	_message_label.text = text
	_message_time = 1.2


func _reset() -> void:
	_distance = 0.0
	_lane = 0.0
	_lean = 0.0
	_speed = CRUISE_SPEED
	_height = 0.0
	_vertical_speed = 0.0
	_jump_queued = false
	_cleared = 0
	_faults = 0
	_message_time = 0.0
	_message_label.text = ""


func _update_hud(delta: float) -> void:
	_stats_label.text = "Speed %d km/h    Hurdles cleared %d    Faults %d    Laps %d" % [
		roundi(_speed * 3.6), _cleared, _faults, int(_distance / TRACK_LENGTH)]
	if _message_time > 0.0:
		_message_time -= delta
		if _message_time <= 0.0:
			_message_label.text = ""


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_stats_label = Label.new()
	_stats_label.position = Vector2(20, 16)
	_stats_label.add_theme_font_size_override("font_size", 22)
	layer.add_child(_stats_label)

	_message_label = Label.new()
	_message_label.position = Vector2(20, 56)
	_message_label.add_theme_font_size_override("font_size", 36)
	layer.add_child(_message_label)

	var help := Label.new()
	help.text = "W/Up faster    S/Down slower    A/D or Left/Right steer    Space jump    R restart"
	help.add_theme_font_size_override("font_size", 18)
	help.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	help.grow_vertical = Control.GROW_DIRECTION_BEGIN
	help.offset_left = 20.0
	help.offset_bottom = -16.0
	layer.add_child(help)


func _build_environment() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.25, 0.5, 0.85)
	sky_material.sky_horizon_color = Color(0.72, 0.84, 0.94)
	sky_material.ground_horizon_color = Color(0.72, 0.84, 0.94)
	sky_material.ground_bottom_color = Color(0.25, 0.4, 0.2)

	var sky := Sky.new()
	sky.sky_material = sky_material

	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY

	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, -30.0, 0.0)
	sun.shadow_enabled = true
	add_child(sun)


func _build_ground() -> void:
	var st := VoxelBuilder.new_surface_tool()
	# A thick slab whose top face sits at y = 0.
	VoxelBuilder.add_box(st, Vector3(-400.0, -2.0, -400.0), Vector3(800.0, 2.0, 800.0), GRASS)
	_add_static_mesh(st, "Ground")


func _build_track() -> void:
	var st := VoxelBuilder.new_surface_tool()
	var tile_length := TRACK_LENGTH / TRACK_TILES
	var size := Vector3(TRACK_HALF_WIDTH * 2.0, TRACK_HEIGHT, tile_length)
	var edge := Vector3(0.2, TRACK_HEIGHT + 0.01, tile_length)
	for i in TRACK_TILES:
		var xform := _ring_transform(TAU * i / TRACK_TILES, TRACK_RADIUS)
		var dirt := DIRT_A if i % 2 == 0 else DIRT_B
		var origin := Vector3(-TRACK_HALF_WIDTH, 0.0, -tile_length * 0.5)
		VoxelBuilder.add_box(st, origin, size, dirt, xform)
		VoxelBuilder.add_box(st, origin, edge, CHALK, xform)
		VoxelBuilder.add_box(st, origin + Vector3(size.x - edge.x, 0.0, 0.0), edge, CHALK, xform)
	_add_static_mesh(st, "Track")


func _build_hurdles() -> void:
	var st := VoxelBuilder.new_surface_tool()
	var segments := 12
	var segment_width := HURDLE_HALF_WIDTH * 2.0 / segments
	for k in HURDLE_LANES.size():
		var xform := _ring_transform(_hurdle_distances[k] / TRACK_RADIUS, TRACK_RADIUS + HURDLE_LANES[k], TRACK_HEIGHT)
		# Local X runs across the track, so the fence spans the lane width.
		for s in segments:
			var x := -HURDLE_HALF_WIDTH + s * segment_width
			var stripe := RED if s % 2 == 0 else CHALK
			VoxelBuilder.add_box(st, Vector3(x, 0.75, -0.06), Vector3(segment_width, 0.15, 0.12), stripe, xform)
			VoxelBuilder.add_box(st, Vector3(x, 0.35, -0.06), Vector3(segment_width, 0.12, 0.12), stripe, xform)
		for post_x in [-HURDLE_HALF_WIDTH, HURDLE_HALF_WIDTH]:
			VoxelBuilder.add_box(st, Vector3(post_x - 0.08, 0.0, -0.1), Vector3(0.16, 0.9, 0.2), POST, xform)
	_add_static_mesh(st, "Hurdles")


func _build_trees() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var st := VoxelBuilder.new_surface_tool()
	for i in 90:
		var angle := rng.randf() * TAU
		var offset := rng.randf_range(TRACK_HALF_WIDTH + 6.0, TRACK_HALF_WIDTH + 40.0)
		var radius := TRACK_RADIUS + offset * (1.0 if rng.randf() < 0.6 else -1.0)
		var tree_scale := rng.randf_range(0.9, 1.5)
		var xform := Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * tree_scale),
			Vector3(cos(angle) * radius, 0.0, sin(angle) * radius))
		VoxelBuilder.add_box(st, Vector3(-0.25, 0.0, -0.25), Vector3(0.5, 2.0, 0.5), TRUNK, xform)
		VoxelBuilder.add_box(st, Vector3(-1.2, 1.6, -1.2), Vector3(2.4, 1.0, 2.4), LEAF_A, xform)
		VoxelBuilder.add_box(st, Vector3(-0.8, 2.6, -0.8), Vector3(1.6, 1.0, 1.6), LEAF_B, xform)
		VoxelBuilder.add_box(st, Vector3(-0.4, 3.6, -0.4), Vector3(0.8, 0.8, 0.8), LEAF_A, xform)
	_add_static_mesh(st, "Trees")


## Places local +Z along the track and local X across it, at the given angle
## and radius from the centre. Local origin sits at `height`.
func _ring_transform(angle: float, radius: float, height: float = 0.0) -> Transform3D:
	var origin := Vector3(cos(angle) * radius, height, sin(angle) * radius)
	return Transform3D(Basis(Vector3.UP, PI - angle), origin)


func _add_static_mesh(st: SurfaceTool, node_name: String) -> void:
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = node_name
	mesh_instance.mesh = st.commit()
	mesh_instance.material_override = VoxelBuilder.make_material()
	add_child(mesh_instance)
