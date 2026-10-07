extends Node3D

## Voxel Gallop: an endless gallop. Switch lanes, jump the hurdles, and dodge
## the rock walls for as long as you can stay in the saddle.

enum State { READY, RUNNING, CRASHED }

const LANE_SPACING := 1.8
const LANE_SWITCH_RATE := 12.0
const START_SPEED := 9.0
const MAX_SPEED := 22.0
const SPEED_GAIN := 0.2  # extra m/s gained per second of running
const GRAVITY := 22.0
const JUMP_VELOCITY := 7.6  # peaks about 1.3 m high
const JUMP_BUFFER := 0.15  # seconds a jump press is remembered before landing
const SPAWN_Z := -80.0
const DESPAWN_Z := 10.0
const TILE_LENGTH := 10.0
const TILE_COUNT := 14
const SKY_COLOR := Color(0.55, 0.78, 0.95)
const COATS := [Color(0.45, 0.26, 0.13), Color(0.72, 0.38, 0.17), Color(0.84, 0.82, 0.78)]
const SCENERY := ["tree", "bush", "boulder"]
const OBSTACLE_HALF_WIDTH := 0.6
const HORSE_FRONT := -1.4  # muzzle, along z relative to the horse root
const HORSE_BACK := 0.8  # tail
const HORSE_LEGS_FRONT := -0.6  # the legs only: a hurdle can't reach the chest or head
const HORSE_LEGS_BACK := 0.6
const HORSE_HALF_WIDTH := 0.25
## height: top edge of the obstacle. half_depth: how far it reaches along z.
## front/back: the span of the horse that the obstacle can hit.
const OBSTACLES := {
	"hurdle": {"height": 0.7, "half_depth": 0.1, "front": HORSE_LEGS_FRONT, "back": HORSE_LEGS_BACK},
	"rock_wall": {"height": 1.5, "half_depth": 0.4, "front": HORSE_FRONT, "back": HORSE_BACK},
}

var _state := State.READY
var _horse: VoxelHorse
var _camera: Camera3D
var _world: Node3D
var _prototypes_root: Node3D
var _prototypes := {}
var _tiles: Array[Node3D] = []
var _dust: CPUParticles3D

var _lane := 0
var _horse_x := 0.0
var _height := 0.0
var _vertical_speed := 0.0
var _jump_buffer := 0.0
var _speed := 0.0
var _distance := 0.0
var _best := 0.0
var _elapsed := 0.0
var _crash_time := 0.0
var _obstacle_timer := 2.0
var _scenery_timer := 0.0

var _info_label: Label
var _message_label: Label


func _ready() -> void:
	_setup_input()
	_setup_environment()
	_build_track()

	_world = Node3D.new()
	add_child(_world)

	_prototypes_root = Node3D.new()
	_prototypes_root.visible = false  # hidden originals; the game only duplicates them
	add_child(_prototypes_root)
	for kind in ["hurdle", "rock_wall", "tree", "bush", "boulder"]:
		var proto := Props.build(kind)
		_prototypes_root.add_child(proto)
		_prototypes[kind] = proto

	_horse = VoxelHorse.new()
	_horse.coat_color = COATS.pick_random()
	add_child(_horse)

	_build_dust()
	_build_ui()
	_reset()


func _process(delta: float) -> void:
	if Input.is_action_just_pressed("restart"):
		_reset()

	match _state:
		State.READY:
			if Input.is_action_just_pressed("jump"):
				_start_run()
		State.RUNNING:
			_steer()
			_try_jump(delta)
			_elapsed += delta
			_speed = minf(MAX_SPEED, START_SPEED + _elapsed * SPEED_GAIN)
			_distance += _speed * delta
			_spawn_obstacles(delta)
		State.CRASHED:
			_speed = move_toward(_speed, 0.0, 12.0 * delta)
			_crash_time += delta
			if _crash_time > 0.8 and Input.is_action_just_pressed("jump"):
				_reset()
				_start_run()

	_integrate_height(delta)
	_scroll(delta)

	_scenery_timer -= delta
	if _scenery_timer <= 0.0:
		_scenery_timer = randf_range(0.15, 0.4)
		_spawn_scenery(SPAWN_Z)

	if _state == State.RUNNING:
		_check_collisions()

	_update_horse(delta)
	_update_camera(delta)
	_update_ui()


func _setup_input() -> void:
	_add_action("lane_left", [KEY_A, KEY_LEFT])
	_add_action("lane_right", [KEY_D, KEY_RIGHT])
	_add_action("jump", [KEY_SPACE, KEY_W, KEY_UP])
	_add_action("restart", [KEY_R])


func _add_action(action: String, keys: Array) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	for key in keys:
		var event := InputEventKey.new()
		event.keycode = key
		InputMap.action_add_event(action, event)


func _setup_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = SKY_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.7, 0.75, 0.8)
	env.fog_enabled = true
	env.fog_light_color = SKY_COLOR
	env.fog_density = 0.006

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50.0, 30.0, 0.0)
	sun.shadow_enabled = true
	add_child(sun)

	_camera = Camera3D.new()
	_camera.fov = 65.0
	add_child(_camera)
	_camera.make_current()


func _build_track() -> void:
	var grass_colors := [Color(0.38, 0.68, 0.3), Color(0.33, 0.61, 0.26)]
	var dirt := Color(0.7, 0.55, 0.36)
	var line := Color(0.95, 0.95, 0.92)
	for i in TILE_COUNT:
		var tile := Node3D.new()
		tile.position.z = (i - TILE_COUNT + 1) * TILE_LENGTH
		tile.add_child(_box(Vector3(60.0, 0.2, TILE_LENGTH), grass_colors[i % 2], Vector3(0.0, -0.1, 0.0)))
		tile.add_child(_box(Vector3(7.6, 0.22, TILE_LENGTH), dirt, Vector3(0.0, -0.09, 0.0)))
		for x in [-3.8, -0.9, 0.9, 3.8]:
			tile.add_child(_box(Vector3(0.08, 0.02, TILE_LENGTH), line, Vector3(x, 0.03, 0.0)))
		add_child(tile)
		_tiles.append(tile)


func _box(size: Vector3, color: Color, at: Vector3) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	mesh.material = material
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.position = at
	return instance


func _build_dust() -> void:
	var puff := BoxMesh.new()
	puff.size = Vector3.ONE * 0.12
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.82, 0.74, 0.6)
	puff.material = material

	_dust = CPUParticles3D.new()
	_dust.mesh = puff
	_dust.amount = 24
	_dust.lifetime = 0.7
	_dust.emitting = false
	_dust.direction = Vector3(0.0, 1.0, 0.4)  # kicked up and behind the horse
	_dust.spread = 35.0
	_dust.initial_velocity_min = 0.6
	_dust.initial_velocity_max = 1.4
	_dust.gravity = Vector3(0.0, -2.0, 0.0)
	_dust.scale_amount_min = 0.5
	_dust.scale_amount_max = 1.2
	add_child(_dust)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	_info_label = Label.new()
	_info_label.position = Vector2(20.0, 14.0)
	_style_label(_info_label, 26)
	layer.add_child(_info_label)

	var help := Label.new()
	help.text = "A / D or Left / Right: change lane     Space / W / Up: jump     R: restart"
	help.position = Vector2(20.0, 52.0)
	_style_label(help, 18)
	layer.add_child(help)

	_message_label = Label.new()
	_message_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_message_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_style_label(_message_label, 40)
	layer.add_child(_message_label)


func _style_label(label: Label, font_size: int) -> void:
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 8)


func _reset() -> void:
	_best = maxf(_best, _distance)
	_state = State.READY
	_lane = 0
	_horse_x = 0.0
	_height = 0.0
	_vertical_speed = 0.0
	_jump_buffer = 0.0
	_speed = 0.0
	_distance = 0.0
	_elapsed = 0.0
	_crash_time = 0.0
	_obstacle_timer = 2.0

	for node in _world.get_children():
		node.queue_free()
	for i in 30:
		_spawn_scenery(randf_range(-100.0, 0.0))

	_horse.reset_pose()
	_message_label.text = "Press SPACE to gallop!"


func _start_run() -> void:
	_state = State.RUNNING
	_speed = START_SPEED
	_message_label.text = ""


func _crash() -> void:
	_state = State.CRASHED
	_crash_time = 0.0
	_best = maxf(_best, _distance)
	_horse.fall_over()
	_message_label.text = "Stumbled!\nPress SPACE to gallop again"


func _steer() -> void:
	if Input.is_action_just_pressed("lane_left"):
		_lane = maxi(_lane - 1, -1)
	if Input.is_action_just_pressed("lane_right"):
		_lane = mini(_lane + 1, 1)


func _try_jump(delta: float) -> void:
	if Input.is_action_just_pressed("jump"):
		_jump_buffer = JUMP_BUFFER
	_jump_buffer = maxf(_jump_buffer - delta, 0.0)
	if _jump_buffer > 0.0 and _height <= 0.0:
		_vertical_speed = JUMP_VELOCITY
		_jump_buffer = 0.0


func _integrate_height(delta: float) -> void:
	_vertical_speed -= GRAVITY * delta
	_height += _vertical_speed * delta
	if _height <= 0.0:
		_height = 0.0
		_vertical_speed = 0.0


func _scroll(delta: float) -> void:
	# The world flows toward the camera while the horse stays near z = 0.
	var step := _speed * delta
	for tile in _tiles:
		tile.position.z += step
		if tile.position.z > TILE_LENGTH:
			tile.position.z -= TILE_COUNT * TILE_LENGTH
	for node: Node3D in _world.get_children():
		node.position.z += step
		if node.position.z > DESPAWN_Z:
			node.queue_free()


func _spawn_obstacles(delta: float) -> void:
	_obstacle_timer -= delta
	if _obstacle_timer > 0.0:
		return
	_obstacle_timer = randf_range(1.2, 1.9)

	# Each row always leaves at least one lane the horse can get through.
	var lanes := [-1, 0, 1]
	lanes.shuffle()
	var roll := randf()
	if roll < 0.45:
		_spawn_obstacle("hurdle", lanes[0])
	elif roll < 0.8:
		_spawn_obstacle("rock_wall", lanes[0])
	else:
		_spawn_obstacle("rock_wall", lanes[0])
		_spawn_obstacle("hurdle", lanes[1])


func _spawn_obstacle(kind: String, lane: int) -> void:
	var obstacle := _spawn(kind, Vector3(lane * LANE_SPACING, 0.0, SPAWN_Z))
	obstacle.set_meta("kind", kind)


func _spawn_scenery(z: float) -> void:
	var side := 1.0 if randf() < 0.5 else -1.0
	var node := _spawn(SCENERY.pick_random(), Vector3(side * randf_range(6.0, 14.0), 0.0, z))
	node.rotation.y = randf() * TAU
	node.scale = Vector3.ONE * randf_range(1.5, 2.2)


func _spawn(kind: String, at: Vector3) -> Node3D:
	var node := _prototypes[kind].duplicate() as Node3D
	node.position = at
	_world.add_child(node)
	return node


func _check_collisions() -> void:
	for node: Node3D in _world.get_children():
		if not node.has_meta("kind"):
			continue
		var info: Dictionary = OBSTACLES[node.get_meta("kind")]
		var z := node.position.z
		var half_depth: float = info["half_depth"]
		var along_horse: bool = z + half_depth > info["front"] and z - half_depth < info["back"]
		var same_lane := absf(node.position.x - _horse_x) < OBSTACLE_HALF_WIDTH + HORSE_HALF_WIDTH
		if along_horse and same_lane and _height < info["height"]:
			_crash()
			return


func _update_horse(delta: float) -> void:
	_horse_x = lerpf(_horse_x, _lane * LANE_SPACING, minf(1.0, delta * LANE_SWITCH_RATE))
	_horse.position = Vector3(_horse_x, _height, 0.0)
	_horse.animate(delta, _speed, _height > 0.0)
	_dust.position = Vector3(_horse_x, 0.05, 0.4)
	_dust.emitting = _state == State.RUNNING and _height <= 0.0


func _update_camera(delta: float) -> void:
	var target := Vector3(_horse_x * 0.5, 2.6 + _height * 0.5, 6.5)
	_camera.position = _camera.position.lerp(target, minf(1.0, delta * 6.0))
	_camera.look_at(Vector3(_horse_x * 0.5, 1.2 + _height * 0.5, -4.0))


func _update_ui() -> void:
	_info_label.text = "Distance: %d m   Best: %d m   Speed: %d km/h" % [
		int(_distance), int(_best), int(_speed * 3.6)
	]
