extends Node3D
## Voxel horse gallop: sets up the scene, reads input and drives the frame loop.
##
## The horse never moves along the track. Each frame the horse is animated, its
## gait decides a ground speed, and the world (scenery, hurdles, dust) is pulled
## backwards at that speed.

const GAIT_NAMES: Array[String] = ["Walk", "Trot", "Gallop"]
const ORBIT_SPEED := 1.6
const HINT := "Up/Down or W/S: gait   |   Space or click: jump   |   A/D or right-drag: orbit   |   wheel: zoom"

var horse: VoxelHorse
var world: VoxelWorld
var dust: Dust
var hurdles: Hurdles
var camera: Camera3D

var _gait_index := 2
var _yaw := 0.35
var _pitch := 0.13
var _cam_distance := 5.0
var _focus_lift := 0.0
var _time := 0.0
var _distance_run := 0.0
var _cleared := 0
var _knocked := 0
var _streak := 0
var _best_streak := 0
var _shake := 0.0
var _rng := RandomNumberGenerator.new()

var _gait_label: Label
var _speed_label: Label
var _distance_label: Label
var _score_label: Label
var _message_label: Label
var _message_tween: Tween


func _ready() -> void:
	_rng.randomize()
	_setup_input()
	_build_environment()

	world = VoxelWorld.new()
	add_child(world)
	horse = VoxelHorse.new()
	add_child(horse)
	dust = Dust.new()
	add_child(dust)
	hurdles = Hurdles.new()
	add_child(hurdles)

	camera = Camera3D.new()
	camera.far = 500.0
	add_child(camera)
	camera.make_current()

	horse.hoof_strike.connect(_on_hoof_strike)
	horse.landed.connect(_on_landed)
	hurdles.cleared.connect(_on_cleared)
	hurdles.knocked.connect(_on_knocked)

	_build_hud()
	_update_camera(0.0)


func _process(delta: float) -> void:
	delta = minf(delta, 0.05)
	_time += delta
	_yaw += Input.get_axis("orbit_left", "orbit_right") * ORBIT_SPEED * delta

	horse.step(delta)
	var speed := horse.ground_speed() * _stumble_slowdown()
	var distance := speed * delta
	_distance_run += distance
	world.scroll(distance, delta)
	dust.scroll_speed = speed
	hurdles.update(distance, delta, horse)

	_update_camera(delta)
	_update_hud(speed)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("jump"):
		horse.jump()
	elif event.is_action_pressed("gait_up"):
		_change_gait(1)
	elif event.is_action_pressed("gait_down"):
		_change_gait(-1)
	elif event is InputEventMouseButton and event.pressed:
		match event.button_index:
			MOUSE_BUTTON_LEFT:
				horse.jump()
			MOUSE_BUTTON_WHEEL_UP:
				_cam_distance = maxf(_cam_distance - 0.4, 3.5)
			MOUSE_BUTTON_WHEEL_DOWN:
				_cam_distance = minf(_cam_distance + 0.4, 12.0)
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_RIGHT) != 0:
		_yaw -= event.relative.x * 0.006
		_pitch = clampf(_pitch + event.relative.y * 0.005, 0.02, 1.2)


func _change_gait(step: int) -> void:
	_gait_index = clampi(_gait_index + step, 0, 2)
	horse.target_gait = float(_gait_index)


func _stumble_slowdown() -> float:
	if horse.stumble_time <= 0.0:
		return 1.0
	return 1.0 - 0.6 * sin(PI * (1.0 - horse.stumble_time / VoxelHorse.STUMBLE_DURATION))


# --- events ---------------------------------------------------------------

func _on_hoof_strike(leg_index: int) -> void:
	var count := 0
	if horse.gait > 1.5:
		count = 2
	elif horse.gait > 0.6:
		count = 1
	if count > 0:
		dust.emit(horse.hoof_position(leg_index), count)


func _on_landed() -> void:
	for i in horse.legs.size():
		dust.emit(horse.hoof_position(i), 2)


func _on_cleared() -> void:
	_cleared += 1
	_streak += 1
	_best_streak = maxi(_best_streak, _streak)
	var text := "Cleared!"
	if _streak >= 3:
		text = "Cleared! x%d in a row" % _streak
	_show_message(text, Color(0.75, 1.0, 0.55))


func _on_knocked() -> void:
	_knocked += 1
	_streak = 0
	_shake = 1.0
	_show_message("Knocked it!", Color(1.0, 0.55, 0.45))


# --- setup ----------------------------------------------------------------

func _setup_input() -> void:
	var bindings := {
		"jump": [KEY_SPACE],
		"gait_up": [KEY_UP, KEY_W],
		"gait_down": [KEY_DOWN, KEY_S],
		"orbit_left": [KEY_LEFT, KEY_A],
		"orbit_right": [KEY_RIGHT, KEY_D],
	}
	for action: String in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in bindings[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)


func _build_environment() -> void:
	var horizon := Color(0.72, 0.86, 0.96)
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.22, 0.47, 0.86)
	sky_material.sky_horizon_color = horizon
	sky_material.ground_horizon_color = horizon
	sky_material.ground_bottom_color = Color(0.40, 0.62, 0.35)
	var sky := Sky.new()
	sky.sky_material = sky_material

	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.66, 0.75, 0.92)
	environment.ambient_light_energy = 0.5
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.fog_enabled = true
	environment.fog_light_color = horizon
	environment.fog_density = 0.010
	environment.fog_sky_affect = 0.0
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	add_child(world_environment)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48.0, 28.0, 0.0)
	sun.light_color = Color(1.0, 0.96, 0.88)
	sun.light_energy = 0.8
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_max_distance = 22.0
	sun.shadow_bias = 0.04
	sun.shadow_normal_bias = 1.0
	add_child(sun)


# --- camera ---------------------------------------------------------------

func _update_camera(delta: float) -> void:
	_focus_lift = lerpf(_focus_lift, horse.jump_height * 0.5, 1.0 - exp(-6.0 * delta))
	_shake = maxf(_shake - delta * 2.5, 0.0)
	var focus := Vector3(0.35, 0.85 + _focus_lift, 0.0)
	var yaw := _yaw + 0.05 * sin(_time * 0.35)
	var direction := Vector3(sin(yaw) * cos(_pitch), sin(_pitch), cos(yaw) * cos(_pitch))
	var shake := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), 0.0) * 0.06 * _shake
	camera.position = focus + direction * _cam_distance + shake
	camera.look_at(focus)
	camera.fov = 48.0 + 8.0 * clampf(horse.gait * 0.5, 0.0, 1.0)


# --- HUD ------------------------------------------------------------------

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)

	var panel := PanelContainer.new()
	panel.position = Vector2(16, 16)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.08, 0.12, 0.45)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(12)
	panel.add_theme_stylebox_override("panel", style)
	root.add_child(panel)
	var stats := VBoxContainer.new()
	panel.add_child(stats)
	_add_label(stats, "VOXEL HORSE", 26, Color(1.0, 0.86, 0.5))
	_gait_label = _add_label(stats, "", 20)
	_speed_label = _add_label(stats, "", 20)
	_distance_label = _add_label(stats, "", 20)
	_score_label = _add_label(stats, "", 20)

	_message_label = Label.new()
	_message_label.set_anchors_preset(Control.PRESET_TOP_WIDE)
	_message_label.offset_top = 90.0
	_message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_message_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_message_label.add_theme_font_size_override("font_size", 40)
	_message_label.add_theme_constant_override("outline_size", 8)
	_message_label.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.12, 0.8))
	_message_label.modulate.a = 0.0
	root.add_child(_message_label)

	var bottom := VBoxContainer.new()
	bottom.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 16)
	bottom.grow_horizontal = Control.GROW_DIRECTION_BOTH
	bottom.grow_vertical = Control.GROW_DIRECTION_BEGIN
	bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(bottom)
	var hint := _add_label(bottom, HINT, 16, Color(1, 1, 1, 0.9))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_constant_override("outline_size", 6)
	hint.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.12, 0.8))
	var buttons := HBoxContainer.new()
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	buttons.add_theme_constant_override("separation", 12)
	bottom.add_child(buttons)
	_add_button(buttons, "< Slower", _change_gait.bind(-1))
	_add_button(buttons, "Jump", func() -> void: horse.jump())
	_add_button(buttons, "Faster >", _change_gait.bind(1))


func _add_label(parent: Control, text: String, font_size: int, color: Color = Color.WHITE) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	parent.add_child(label)
	return label


func _add_button(parent: Control, text: String, callback: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE  # keep Space for jumping
	button.custom_minimum_size = Vector2(130, 48)
	button.add_theme_font_size_override("font_size", 20)
	button.pressed.connect(callback)
	parent.add_child(button)


func _update_hud(speed: float) -> void:
	_gait_label.text = "Gait: %s" % GAIT_NAMES[clampi(roundi(horse.gait), 0, 2)]
	_speed_label.text = "Speed: %.1f m/s" % speed
	_distance_label.text = "Distance: %d m" % int(_distance_run)
	_score_label.text = "Cleared: %d   Knocked: %d   Best streak: %d" % [_cleared, _knocked, _best_streak]


func _show_message(text: String, color: Color) -> void:
	_message_label.text = text
	_message_label.add_theme_color_override("font_color", color)
	if _message_tween:
		_message_tween.kill()
	_message_label.modulate.a = 1.0
	_message_tween = create_tween()
	_message_tween.tween_interval(0.6)
	_message_tween.tween_property(_message_label, "modulate:a", 0.0, 0.6)
