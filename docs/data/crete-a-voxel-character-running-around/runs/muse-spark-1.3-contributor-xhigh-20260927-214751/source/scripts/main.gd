extends Node3D
## Builds the voxel sandbox (island, fence, trees, rocks, crates, platform,
## pond, flowers, clouds, shard pickups), wires up input actions at runtime,
## and tracks shard collection. No threads, no external assets.

const Sfx := preload("res://scripts/sfx.gd")
const PickupScript := preload("res://scripts/pickup.gd")

var player = null
var hud = null
var decor: Node3D
var pickups_root: Node3D
var mats: Dictionary = {}
var rng := RandomNumberGenerator.new()
var clouds: Array = []
var pickup_list: Array = []
var coins_got: int = 0
var coins_total: int = 0
var celebrated: bool = false
var spawn_point := Vector3(0, 1.2, 8)
var coin_player: AudioStreamPlayer
var fanfare_player: AudioStreamPlayer


func _enter_tree() -> void:
	_ensure_input()


func _ready() -> void:
	rng.seed = 20260927
	player = $Player
	hud = $HUD
	decor = $Decor
	pickups_root = $Pickups
	_build_island()
	_build_fence()
	_build_trees()
	_build_rocks()
	_build_crates()
	_build_platform()
	_build_pond()
	_build_flowers()
	_build_clouds()
	_build_coins()
	coin_player = AudioStreamPlayer.new()
	coin_player.stream = Sfx.tone(880.0, 1560.0, 0.14, 0.4)
	coin_player.volume_db = -6.0
	add_child(coin_player)
	fanfare_player = AudioStreamPlayer.new()
	fanfare_player.stream = Sfx.arpeggio([523.0, 659.0, 784.0, 1046.0], 0.13, 0.45)
	fanfare_player.volume_db = -6.0
	add_child(fanfare_player)
	hud.set_coins(coins_got, coins_total)
	hud.toast("Find all %d sky shards!" % coins_total, 4.0)


func _process(delta: float) -> void:
	for c in clouds:
		var n: Node3D = c["n"]
		if is_instance_valid(n):
			n.position.x += float(c["speed"]) * delta
			if n.position.x > 24.0:
				n.position.x = -24.0
	if player != null and player.position.y < -12.0:
		respawn_player()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("reset"):
		respawn_player()
	elif event.is_action_pressed("help"):
		hud.toggle_help()


func respawn_player() -> void:
	if player == null:
		return
	player.global_position = spawn_point
	player.velocity = Vector3.ZERO
	player.yaw = 0.0
	player.pitch = -0.32


func _on_coin_collected(_pickup) -> void:
	coins_got += 1
	coin_player.play()
	hud.set_coins(coins_got, coins_total)
	if coins_got >= coins_total and not celebrated:
		_celebrate()


func _celebrate() -> void:
	celebrated = true
	fanfare_player.play()
	hud.toast("All %d shards collected! Nice running!" % coins_total, 4.0)
	player.celebrate_burst()
	await get_tree().create_timer(5.0).timeout
	for c in pickup_list:
		c.respawn_now()
	coins_got = 0
	celebrated = false
	hud.set_coins(coins_got, coins_total)


# ---------------------------------------------------------------- input map

func _ensure_input() -> void:
	_add_key_action("move_forward", [KEY_W, KEY_UP])
	_add_key_action("move_back", [KEY_S, KEY_DOWN])
	_add_key_action("move_left", [KEY_A, KEY_LEFT])
	_add_key_action("move_right", [KEY_D, KEY_RIGHT])
	_add_key_action("jump", [KEY_SPACE])
	_add_key_action("sprint", [KEY_SHIFT])
	_add_key_action("reset", [KEY_R])
	_add_key_action("help", [KEY_H])
	# Gamepad buttons: A = jump, X = sprint, Start = reset.
	_add_joy_button("jump", JOY_BUTTON_A)
	_add_joy_button("sprint", JOY_BUTTON_X)
	_add_joy_button("reset", JOY_BUTTON_START)
	# Gamepad left stick for movement.
	_add_joy_motion("move_left", JOY_AXIS_LEFT_X, -1.0)
	_add_joy_motion("move_right", JOY_AXIS_LEFT_X, 1.0)
	_add_joy_motion("move_forward", JOY_AXIS_LEFT_Y, -1.0)
	_add_joy_motion("move_back", JOY_AXIS_LEFT_Y, 1.0)


func _add_key_action(action: String, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for key in keys:
		var exists := false
		for e in InputMap.action_get_events(action):
			if e is InputEventKey and e.physical_keycode == key:
				exists = true
		if not exists:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)


func _add_joy_button(action: String, button: JoyButton) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventJoypadButton.new()
	ev.button_index = button
	InputMap.action_add_event(action, ev)


func _add_joy_motion(action: String, axis: JoyAxis, value: float) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventJoypadMotion.new()
	ev.axis = axis
	ev.axis_value = value
	InputMap.action_add_event(action, ev)


# ---------------------------------------------------------------- builders

func _mat(color: Color) -> StandardMaterial3D:
	var key := color.to_html()
	if mats.has(key):
		return mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.95
	mats[key] = m
	return m


func _add_solid(size: Vector3, pos: Vector3, color: Color, rot_y: float = 0.0) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.rotation.y = rot_y
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(color)
	mi.mesh = bm
	body.add_child(mi)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	body.add_child(cs)
	decor.add_child(body)
	return body


func _add_visual(size: Vector3, pos: Vector3, color: Color, rot_y: float = 0.0, no_shadow: bool = false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(color)
	mi.mesh = bm
	mi.position = pos
	mi.rotation.y = rot_y
	if no_shadow:
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	decor.add_child(mi)
	return mi


func _add_wall(size: Vector3, pos: Vector3) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	body.add_child(cs)
	decor.add_child(body)


func _build_island() -> void:
	# Chunky voxel island layers under the grass slab from the scene file.
	_add_visual(Vector3(30, 1.6, 30), Vector3(0, -1.8, 0), Color(0.45, 0.32, 0.20))
	_add_visual(Vector3(22, 1.6, 22), Vector3(0, -3.2, 0), Color(0.55, 0.55, 0.60))
	_add_visual(Vector3(12, 1.6, 12), Vector3(0, -4.6, 0), Color(0.40, 0.40, 0.45))


func _build_fence() -> void:
	var wood := Color(0.50, 0.36, 0.20)
	var wood_dark := Color(0.42, 0.29, 0.16)
	for i in range(15):
		var d := -14.0 + 2.0 * float(i)
		_add_visual(Vector3(0.35, 1.2, 0.35), Vector3(d, 0.6, -14), wood)
		_add_visual(Vector3(0.35, 1.2, 0.35), Vector3(d, 0.6, 14), wood)
		if i > 0 and i < 14:
			_add_visual(Vector3(0.35, 1.2, 0.35), Vector3(-14, 0.6, d), wood)
			_add_visual(Vector3(0.35, 1.2, 0.35), Vector3(14, 0.6, d), wood)
	for y in [0.5, 0.95]:
		_add_visual(Vector3(28.7, 0.14, 0.14), Vector3(0, y, -14), wood_dark)
		_add_visual(Vector3(28.7, 0.14, 0.14), Vector3(0, y, 14), wood_dark)
		_add_visual(Vector3(0.14, 0.14, 28.7), Vector3(-14, y, 0), wood_dark)
		_add_visual(Vector3(0.14, 0.14, 28.7), Vector3(14, y, 0), wood_dark)
	# Invisible walls keep the player inside (visual fence has no collision).
	_add_wall(Vector3(29, 3, 0.6), Vector3(0, 1.5, -14.2))
	_add_wall(Vector3(29, 3, 0.6), Vector3(0, 1.5, 14.2))
	_add_wall(Vector3(0.6, 3, 29), Vector3(-14.2, 1.5, 0))
	_add_wall(Vector3(0.6, 3, 29), Vector3(14.2, 1.5, 0))


func _build_trees() -> void:
	var spots: Array = [
		Vector3(-9, 0, -7), Vector3(8, 0, -9), Vector3(-6, 0, 8),
		Vector3(10, 0, 7), Vector3(0, 0, -12),
	]
	for s in spots:
		_add_solid(Vector3(0.5, 1.8, 0.5), s + Vector3(0, 0.9, 0), Color(0.42, 0.28, 0.15))
		var r := rng.randf() * TAU
		_add_visual(Vector3(2.4, 1.1, 2.4), s + Vector3(0, 2.3, 0), Color(0.25, 0.60, 0.28), r)
		_add_visual(Vector3(1.5, 0.9, 1.5), s + Vector3(0, 3.2, 0), Color(0.33, 0.68, 0.32), r + 0.4)


func _build_rocks() -> void:
	var spots: Array = [
		Vector3(-3, 0, -9), Vector3(11, 0, -3), Vector3(-12, 0, 1),
		Vector3(3, 0, 10), Vector3(-1, 0, -5), Vector3(12, 0, 11),
	]
	var gray := Color(0.60, 0.62, 0.65)
	for s in spots:
		var w := rng.randf_range(0.5, 1.0)
		var h := rng.randf_range(0.4, 0.8)
		_add_solid(Vector3(w, h, w * rng.randf_range(0.8, 1.1)), s + Vector3(0, h * 0.5, 0), gray, rng.randf() * TAU)


func _build_crates() -> void:
	var wood := Color(0.78, 0.55, 0.26)
	var trim := Color(0.60, 0.40, 0.18)
	_add_solid(Vector3(1, 1, 1), Vector3(5, 0.5, 2), wood)
	_add_visual(Vector3(1.04, 0.12, 1.04), Vector3(5, 0.95, 2), trim)
	_add_solid(Vector3(1, 1, 1), Vector3(6.05, 0.5, 2.1), wood, 0.15)
	_add_solid(Vector3(1, 1, 1), Vector3(5, 1.5, 2), wood, 0.3)


func _build_platform() -> void:
	var plank := Color(0.60, 0.42, 0.25)
	_add_solid(Vector3(4, 0.5, 4), Vector3(-9, 1.25, 3), plank)
	_add_solid(Vector3(1, 0.5, 2.4), Vector3(-6.5, 0.25, 3), Color(0.55, 0.55, 0.58))
	_add_solid(Vector3(1, 1.0, 2.4), Vector3(-5.5, 0.5, 3), Color(0.55, 0.55, 0.58))
	for lx in [-10.6, -7.4]:
		for lz in [1.4, 4.6]:
			_add_visual(Vector3(0.3, 1.0, 0.3), Vector3(lx, 0.5, lz), Color(0.45, 0.31, 0.18))
	# Little flag so the platform reads as a goal.
	_add_visual(Vector3(0.12, 1.6, 0.12), Vector3(-9, 2.3, 1.6), Color(0.30, 0.30, 0.32))
	_add_visual(Vector3(0.9, 0.5, 0.08), Vector3(-8.5, 2.85, 1.6), Color(0.90, 0.30, 0.25))


func _build_pond() -> void:
	var c := Vector3(7, 0, -3)
	_add_visual(Vector3(4, 0.1, 3), c + Vector3(0, 0.05, 0), Color(0.25, 0.65, 0.85))
	var sand := Color(0.90, 0.82, 0.60)
	_add_visual(Vector3(4.5, 0.14, 0.3), c + Vector3(0, 0.07, 1.65), sand)
	_add_visual(Vector3(4.5, 0.14, 0.3), c + Vector3(0, 0.07, -1.65), sand)
	_add_visual(Vector3(0.3, 0.14, 3.0), c + Vector3(2.25, 0.07, 0), sand)
	_add_visual(Vector3(0.3, 0.14, 3.0), c + Vector3(-2.25, 0.07, 0), sand)
	_add_visual(Vector3(0.4, 0.06, 0.4), c + Vector3(-0.5, 0.12, 0), Color(0.25, 0.60, 0.28))
	_add_visual(Vector3(0.2, 0.12, 0.2), c + Vector3(-0.5, 0.18, 0), Color(0.95, 0.55, 0.70))


func _build_flowers() -> void:
	var palette: Array = [
		Color(0.90, 0.25, 0.30), Color(0.95, 0.80, 0.25),
		Color(0.95, 0.95, 0.95), Color(0.70, 0.40, 0.90),
	]
	var stem_c := Color(0.25, 0.55, 0.25)
	for i in range(46):
		var x := rng.randf_range(-13.0, 13.0)
		var z := rng.randf_range(-13.0, 13.0)
		if absf(x - 7.0) < 2.8 and absf(z + 3.0) < 2.3:
			continue # pond
		if x > -11.5 and x < -4.5 and z > 1.0 and z < 5.0:
			continue # platform / steps
		var p := Vector3(x, 0, z)
		_add_visual(Vector3(0.09, 0.35, 0.09), p + Vector3(0, 0.17, 0), stem_c)
		_add_visual(Vector3(0.24, 0.2, 0.24), p + Vector3(0, 0.42, 0), palette[rng.randi() % palette.size()])
	for i in range(24):
		var g := Vector3(rng.randf_range(-13.0, 13.0), 0.14, rng.randf_range(-13.0, 13.0))
		_add_visual(Vector3(0.34, 0.28, 0.12), g, Color(0.33, 0.62, 0.28), rng.randf() * TAU)


func _build_clouds() -> void:
	var white := Color(0.97, 0.98, 1.0)
	var defs: Array = [
		{"p": Vector3(-12, 12, -8), "s": 0.5}, {"p": Vector3(-2, 14, 6), "s": 0.35},
		{"p": Vector3(8, 13, -2), "s": 0.65}, {"p": Vector3(14, 15, 10), "s": 0.4},
		{"p": Vector3(-6, 11.5, 12), "s": 0.55},
	]
	for d in defs:
		var root := Node3D.new()
		root.position = d["p"]
		decor.add_child(root)
		for part in [Vector3(0, 0, 0), Vector3(1.6, -0.1, 0.4), Vector3(-1.5, -0.15, -0.3)]:
			var mi := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(2.6, 0.8, 1.8)
			bm.material = _mat(white)
			mi.mesh = bm
			mi.position = part
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			root.add_child(mi)
		clouds.append({"n": root, "speed": float(d["s"])})


func _build_coins() -> void:
	var spots: Array = [
		Vector3(-4, 0.9, -4), Vector3(4, 0.9, -6), Vector3(-10, 0.9, -2),
		Vector3(10, 0.9, 2), Vector3(0, 0.9, -11), Vector3(-2, 0.9, 5),
		Vector3(6, 0.9, 8), Vector3(-11, 0.9, 9), Vector3(11, 0.9, -7),
		Vector3(-9, 2.35, 3), Vector3(-5.5, 1.85, 3), Vector3(5, 2.75, 2),
	]
	for s in spots:
		var p: Area3D = PickupScript.new()
		p.position = s
		pickups_root.add_child(p)
		p.collected.connect(_on_coin_collected)
		pickup_list.append(p)
	coins_total = spots.size()
