extends Node3D
## Main scene: builds the whole sandbox procedurally (no external assets)
## and hands over to the voxel character, who wanders on AI until the
## player presses "Interact".

const CharacterScript := preload("res://scripts/character.gd")

var arena_extents := Vector2(13.0, 13.0)
var camera: Camera3D
var camera_rig: Node3D
var hint_label: Label
var hint_delay := 8.0
var player_hint := false
var player_active := false
var character: Node3D


func _ready() -> void:
	# Deterministic world layout.
	seed(42)
	_build_lighting()
	_build_ground()
	_build_walls()
	_build_props()
	_build_character()
	_build_camera()
	_build_hud()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and not player_active:
		_give_control()


func _give_control() -> void:
	player_active = true
	player_hint = true  # latch the hint so it never reappears
	if hint_label:
		hint_label.text = "You have control - good running!"


func _build_lighting() -> void:
	# Sky-tinted ambient light via a WorldEnvironment (this engine build
	# ships without the AmbientLight3D node, so we use the environment API).
	var env := Environment.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.72, 0.8, 0.98)
	env.ambient_light_energy = 0.55
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48.0, -35.0, 0.0)
	sun.light_color = Color(1.0, 0.96, 0.85)
	sun.light_energy = 1.15
	sun.shadow_enabled = true
	add_child(sun)


func _mat(hex: int) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color8(hex >> 16 & 255, hex >> 8 & 255, hex & 255)
	m.roughness = 0.9
	return m


func _box(w: float, h: float, d: float, mat: Material, pos: Vector3, shadow: bool = true) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = Vector3(w, h, d)
	var s := MeshInstance3D.new()
	s.mesh = b
	s.material_override = mat
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow \
		else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	s.position = pos
	add_child(s)
	return b


func _collide(pos: Vector3, size: Vector3) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	col.shape = shape
	body.add_child(col)
	add_child(body)


func _build_ground() -> void:
	# Tiled, unshaded checkerboard ground (classic voxel-sandbox look).
	var light := _mat(0x9ad15f)
	light.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var dark := _mat(0x7cb84b)
	dark.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var ts := 2.0
	var n := int(arena_extents.x / ts) * 2  # tiles span the whole arena, centered
	var start := -arena_extents.x
	for i in range(n):
		for j in range(n):
			var m := light if (i + j) % 2 == 0 else dark
			_box(ts, 0.5, ts, m,
				Vector3(start + i * ts + ts * 0.5, -0.25, start + j * ts + ts * 0.5), false)
	_collide(Vector3(0, -0.25, 0), Vector3(30, 0.5, 30))  # invisible floor slab


func _build_walls() -> void:
	var brick := _mat(0xc98a5a)
	var brick_top := _mat(0xd9a06b)
	var hx := arena_extents.x + 0.5  # inner face flush with the outermost tiles
	var hz := arena_extents.y + 0.5
	var h := 2.4
	_box(hx * 2.0, h, 1.0, brick, Vector3(0, h * 0.5, -hz))
	_box(hx * 2.0, h, 1.0, brick, Vector3(0, h * 0.5, hz))
	_box(1.0, h, hz * 2.0, brick, Vector3(-hx, h * 0.5, 0.0))
	_box(1.0, h, hz * 2.0, brick, Vector3(hx, h * 0.5, 0.0))
	_collide(Vector3(0, h * 0.5, -hz), Vector3(hx * 2.0, h, 1.0))
	_collide(Vector3(0, h * 0.5, hz), Vector3(hx * 2.0, h, 1.0))
	_collide(Vector3(-hx, h * 0.5, 0.0), Vector3(1.0, h, hz * 2.0))
	_collide(Vector3(hx, h * 0.5, 0.0), Vector3(1.0, h, hz * 2.0))
	# Decorative crenellations along the back wall.
	for x in range(int(hx * 2.0) / 4):
		_box(2.0, 1.0, 1.0, brick_top, Vector3(-hx + 2.0 + x * 4.0, h + 0.5, -hz))


func _prop_tree(pos: Vector3) -> void:
	_box(0.7, 2.2, 0.7, _mat(0x8a5a33), pos + Vector3(0, 1.1, 0))
	_box(3.0, 1.3, 3.0, _mat(0x4f9e40), pos + Vector3(0, 2.75, 0))
	_box(2.0, 1.1, 2.0, _mat(0x5fb34d), pos + Vector3(0, 3.8, 0))
	_collide(pos + Vector3(0, 1.1, 0), Vector3(0.7, 2.2, 0.7))
	_collide(pos + Vector3(0, 2.75, 0), Vector3(3.0, 1.3, 3.0))


func _prop_crates(pos: Vector3) -> void:
	_box(1.5, 1.5, 1.5, _mat(0xb5793f), pos + Vector3(0, 0.75, 0))
	_box(1.0, 1.0, 1.0, _mat(0xc98a5a), pos + Vector3(0.2, 2.0, 0.1))
	_collide(pos + Vector3(0, 0.75, 0), Vector3(1.5, 1.5, 1.5))
	_collide(pos + Vector3(0.2, 2.0, 0.1), Vector3(1.0, 1.0, 1.0))


func _build_props() -> void:
	# Pillar in the middle: the AI's favorite orbit target.
	_box(2.4, 0.5, 2.4, _mat(0xb0a58f), Vector3(0, 0.25, 0))
	_box(1.2, 2.2, 1.2, _mat(0xcfc4ab), Vector3(0, 1.6, 0))
	_box(1.8, 0.4, 1.8, _mat(0xb0a58f), Vector3(0, 2.9, 0))
	_collide(Vector3(0, 0.25, 0), Vector3(2.4, 0.5, 2.4))
	_collide(Vector3(0, 1.6, 0), Vector3(1.2, 2.2, 1.2))

	_prop_tree(Vector3(-8.5, 0.0, -8.5))
	_prop_tree(Vector3(9.0, 0.0, -7.5))
	_prop_tree(Vector3(-9.5, 0.0, 8.0))
	_prop_crates(Vector3(8.0, 0.0, 8.0))
	_box(1.8, 0.9, 1.8, _mat(0x9aa0a6), Vector3(-7.5, 0.45, 2.0))  # stone block
	_collide(Vector3(-7.5, 0.45, 2.0), Vector3(1.8, 0.9, 1.8))
	_box(0.9, 0.9, 0.9, _mat(0xe06a4e), Vector3(3.5, 0.45, 6.5))   # red voxel
	_collide(Vector3(3.5, 0.45, 6.5), Vector3(0.9, 0.9, 0.9))
	_box(1.2, 0.6, 1.2, _mat(0x6fb3d9), Vector3(-3.0, 0.3, -6.0))  # blue voxel
	_collide(Vector3(-3.0, 0.3, -6.0), Vector3(1.2, 0.6, 1.2))


func _build_character() -> void:
	character = CharacterScript.new()
	character.position = Vector3(0.0, 0.0, 6.5)
	add_child(character)


func _build_camera() -> void:
	camera_rig = Node3D.new()
	camera_rig.name = "CameraRig"
	add_child(camera_rig)

	var spring := SpringArm3D.new()
	spring.name = "SpringArm"
	spring.rotation_degrees = Vector3(-16.0, 0.0, 0.0)
	spring.spring_length = 11.0
	spring.margin = 1.2
	camera_rig.add_child(spring)

	camera = Camera3D.new()
	camera.name = "FollowCamera"
	camera.fov = 55.0
	camera.position = Vector3(0, 0, 11.0)
	spring.add_child(camera)


func _build_hud() -> void:
	var overlay := CanvasLayer.new()
	overlay.layer = 10
	add_child(overlay)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_TOP_WIDE)
	overlay.add_child(center)

	var panel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.1, 0.16, 0.55)
	sb.border_color = Color(1, 1, 1, 0.15)
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(10)
	sb.content_margin_left = 16.0
	sb.content_margin_right = 16.0
	sb.content_margin_top = 8.0
	sb.content_margin_bottom = 8.0
	panel.add_theme_stylebox_override("panel", sb)
	center.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	panel.add_child(vbox)

	hint_label = Label.new()
	hint_label.text = "Meet Vex! Watch him run around the sandbox..."
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(hint_label)

	var keys := Label.new()
	keys.text = "WASD / Arrows: run   Shift: sprint   Space: jump   I: take over   R: reset"
	keys.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	keys.add_theme_font_size_override("font_size", 12)
	keys.modulate = Color(1, 1, 1, 0.75)
	vbox.add_child(keys)


func _process(delta: float) -> void:
	# Let the AI run the show for a few seconds, then invite the player in.
	if not player_active and not player_hint:
		hint_delay -= delta
		if hint_delay <= 0.0:
			player_hint = true
			if hint_label:
				hint_label.text = "Press any of: WASD / Arrows / Space / I  to take over!"


func _physics_process(delta: float) -> void:
	# Follow-cam: pan the rig with the pointer when it sits at the screen edge.
	var look := Vector2.ZERO
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		look = get_viewport().get_mouse_position() - Vector2(640, 360)
		var d := look.length()
		if d > 560.0:
			look = (look / d) * (d - 560.0)
	if camera_rig and character and not character.is_queued_for_deletion():
		var target := character.global_position
		camera_rig.position.x = target.x + look.x * 0.015
		camera_rig.position.z = target.z + look.y * 0.015
