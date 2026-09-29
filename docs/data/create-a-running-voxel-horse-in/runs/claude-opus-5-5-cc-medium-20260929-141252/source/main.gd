extends Node3D
## Running voxel horse: builds the horse, an endless procedurally-populated
## meadow, camera, lighting and HUD entirely from code.

const Vox = preload("res://voxel.gd")

const V := 0.1                 # horse voxel size (metres)
const CHUNK := 24.0            # world chunk size (metres)
const VIEW_CHUNKS := 3         # chunks kept loaded around the horse
const UPPER_LEN := 0.5
const LOWER_LEN := 0.6
const GRAVITY := 16.0
const JUMP_SPEED := 5.5
const TURN_RATE := 1.8

const GAIT_NAMES := ["Stand", "Walk", "Trot", "Canter", "Gallop"]
const GAIT_SPEEDS := [0.0, 2.0, 5.0, 9.0, 14.0]
const SPRINT_SPEED := 18.0

# Leg order: LF, RF, LH, RH. Phase offsets (fraction of a stride).
const WALK_OFFSETS := [0.25, 0.75, 0.0, 0.5]
const TROT_OFFSETS := [0.0, 0.5, 0.5, 0.0]
const GALLOP_OFFSETS := [0.55, 0.65, 0.0, 0.1]

const COAT := Color(0.56, 0.32, 0.16)
const DARK := Color(0.14, 0.09, 0.07)
const SOCK := Color(0.93, 0.91, 0.87)
const HOOF := Color(0.2, 0.18, 0.16)

var mat: StandardMaterial3D
var horse: Node3D
var body: Node3D
var neck: Node3D
var head: Node3D
var tail: Node3D
var legs: Array[Dictionary] = []
var camera: Camera3D
var ground: MeshInstance3D
var sun: DirectionalLight3D
var dust: CPUParticles3D
var hud: Label

var gait := 3
var speed := 0.0
var yaw := 0.0
var height := 0.0
var vel_y := 0.0
var phase := 0.0
var lean := 0.0
var air := 0.0
var cam_mode := 0
var time := 0.0
var distance := 0.0

var chunks := {}      # Vector2i -> Node3D
var obstacles := {}   # Vector2i -> Array[Vector3] (x, z, radius)
var props := {}       # prop kind -> Array[ArrayMesh]


func _ready() -> void:
	randomize()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--cam="):
			cam_mode = int(arg.substr(6)) % 4
	_setup_input()
	mat = StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 0.9
	_setup_environment()
	_build_ground()
	_build_props()
	_build_horse()
	_build_dust()
	camera = Camera3D.new()
	camera.fov = 65.0
	camera.far = 200.0
	add_child(camera)
	camera.position = Vector3(0, 3.5, 8)
	camera.look_at(Vector3(0, 1.2, 0))
	_build_hud()
	_update_chunks()


# ---------------------------------------------------------------- setup

func _setup_input() -> void:
	_add_action("forward", [KEY_W, KEY_UP])
	_add_action("back", [KEY_S, KEY_DOWN])
	_add_action("left", [KEY_A, KEY_LEFT])
	_add_action("right", [KEY_D, KEY_RIGHT])
	_add_action("sprint", [KEY_SHIFT])
	_add_action("jump", [KEY_SPACE])
	_add_action("camera", [KEY_C, KEY_V])


func _add_action(action: String, keys: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


func _setup_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.3, 0.52, 0.85)
	sky_mat.sky_horizon_color = Color(0.72, 0.84, 0.95)
	sky_mat.ground_horizon_color = Color(0.72, 0.84, 0.95)
	sky_mat.ground_bottom_color = Color(0.35, 0.45, 0.3)
	var sky := Sky.new()
	sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.45
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.fog_enabled = true
	env.fog_light_color = Color(0.72, 0.84, 0.95)
	env.fog_density = 0.008
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.light_energy = 0.8
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 45.0
	add_child(sun)


func _build_ground() -> void:
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode specular_disabled;
varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
void fragment() {
	vec2 cell = floor(wpos.xz);
	float h = hash(mod(cell, 512.0));
	float patch = hash(mod(floor(wpos.xz / 7.0), 512.0));
	vec3 grass_a = vec3(0.30, 0.52, 0.22);
	vec3 grass_b = vec3(0.36, 0.60, 0.25);
	vec3 col = mix(grass_a, grass_b, h);
	col = mix(col, vec3(0.45, 0.62, 0.24), step(0.8, patch) * 0.6);
	ALBEDO = pow(col, vec3(2.2));
	ROUGHNESS = 1.0;
}
"""
	var smat := ShaderMaterial.new()
	smat.shader = shader
	var plane := PlaneMesh.new()
	plane.size = Vector2(400, 400)
	plane.material = smat
	ground = MeshInstance3D.new()
	ground.mesh = plane
	add_child(ground)


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Label.new()
	hud.position = Vector2(16, 12)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_color", Color.WHITE)
	hud.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	hud.add_theme_constant_override("outline_size", 5)
	layer.add_child(hud)


func _build_dust() -> void:
	dust = CPUParticles3D.new()
	var box := BoxMesh.new()
	box.size = Vector3.ONE * 0.14
	var dmat := StandardMaterial3D.new()
	dmat.albedo_color = Color(0.72, 0.62, 0.45)
	dmat.roughness = 1.0
	box.material = dmat
	dust.mesh = box
	dust.amount = 48
	dust.lifetime = 0.8
	dust.local_coords = false
	dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	dust.emission_box_extents = Vector3(0.35, 0.05, 0.8)
	dust.direction = Vector3(0, 1, 0)
	dust.spread = 50.0
	dust.initial_velocity_min = 0.6
	dust.initial_velocity_max = 1.6
	dust.gravity = Vector3(0, -2.0, 0)
	dust.scale_amount_min = 0.6
	dust.scale_amount_max = 1.3
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1))
	curve.add_point(Vector2(1, 0))
	dust.scale_amount_curve = curve
	dust.emitting = false
	add_child(dust)


# ---------------------------------------------------------------- horse

func _part(parent: Node3D, pos: Vector3, v: RefCounted) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = pos
	parent.add_child(pivot)
	var mi := MeshInstance3D.new()
	mi.mesh = v.build(V, mat)
	pivot.add_child(mi)
	return pivot


func _build_horse() -> void:
	horse = Node3D.new()
	add_child(horse)
	body = Node3D.new()
	body.position.y = UPPER_LEN + LOWER_LEN
	horse.add_child(body)

	# Torso with rounded top/bottom edges, and a saddle blanket.
	var t := Vox.new(11)
	t.box(Vector3i(-3, -3, -8), Vector3i(2, 3, 7), COAT)
	for z in range(-8, 8):
		for c in [Vector2i(-3, 3), Vector2i(2, 3), Vector2i(-3, -3), Vector2i(2, -3)]:
			t.erase(Vector3i(c.x, c.y, z))
	for c in [Vector2i(-3, 3), Vector2i(2, 3), Vector2i(-3, -3), Vector2i(2, -3)]:
		for z in [-8, 7]:
			for dy in [0, -1 if c.y > 0 else 1]:
				t.erase(Vector3i(c.x, c.y + dy, z))
	t.box(Vector3i(-3, 4, -3), Vector3i(2, 4, 1), Color(0.7, 0.12, 0.1), 0.02)
	t.box(Vector3i(-4, 0, -3), Vector3i(-4, 3, 1), Color(0.7, 0.12, 0.1), 0.02)
	t.box(Vector3i(3, 0, -3), Vector3i(3, 3, 1), Color(0.7, 0.12, 0.1), 0.02)
	t.box(Vector3i(-2, 5, -2), Vector3i(1, 5, 0), Color(0.35, 0.2, 0.1), 0.02)
	t.box(Vector3i(-4, 0, -3), Vector3i(-4, 0, 1), Color(0.95, 0.8, 0.3), 0.0)
	t.box(Vector3i(3, 0, -3), Vector3i(3, 0, 1), Color(0.95, 0.8, 0.3), 0.0)
	_part(body, Vector3.ZERO, t)

	# Neck with mane.
	var n := Vox.new(12)
	n.box(Vector3i(-2, 0, -2), Vector3i(1, 3, 1), COAT)
	n.box(Vector3i(-2, 4, -2), Vector3i(1, 7, 0), COAT)
	n.box(Vector3i(-1, 1, 2), Vector3i(0, 3, 2), DARK)
	n.box(Vector3i(-1, 4, 1), Vector3i(0, 8, 1), DARK)
	neck = _part(body, Vector3(0, 0.25, -0.65), n)
	neck.rotation.x = -0.6

	# Head: skull, snout, eyes, ears, forelock.
	var h := Vox.new(13)
	h.box(Vector3i(-2, -1, -2), Vector3i(1, 2, 1), COAT)
	h.box(Vector3i(-2, -1, -5), Vector3i(1, 1, -3), COAT)
	h.box(Vector3i(-2, -1, -6), Vector3i(1, 0, -6), Color(0.3, 0.2, 0.15))
	h.box(Vector3i(-1, 2, -5), Vector3i(0, 2, -3), SOCK, 0.0)    # white blaze
	h.put(Vector3i(-2, 1, -2), Color.BLACK, 0.0)
	h.put(Vector3i(1, 1, -2), Color.BLACK, 0.0)
	h.box(Vector3i(-2, 3, 0), Vector3i(-2, 4, 0), COAT)
	h.box(Vector3i(1, 3, 0), Vector3i(1, 4, 0), COAT)
	h.box(Vector3i(-1, 3, -1), Vector3i(0, 3, 0), DARK)
	head = _part(neck, Vector3(0, 0.72, 0.0), h)
	head.rotation.x = -0.35

	# Tail.
	var tl := Vox.new(14)
	tl.box(Vector3i(-1, -4, 0), Vector3i(0, 0, 1), DARK)
	tl.box(Vector3i(-2, -8, -1), Vector3i(1, -5, 1), DARK)
	tl.box(Vector3i(-1, -9, 0), Vector3i(0, -9, 0), DARK)
	tail = _part(body, Vector3(0, 0.25, 0.78), tl)

	# Legs: [name, x, z, hind, white sock]
	var defs := [
		[-0.18, -0.6, false, true],
		[0.18, -0.6, false, false],
		[-0.18, 0.6, true, false],
		[0.18, 0.6, true, true],
	]
	for i in defs.size():
		var d: Array = defs[i]
		var hind: bool = d[2]
		var up := Vox.new(20 + i)
		if hind:
			up.box(Vector3i(-1, -4, -1), Vector3i(0, 1, 1), COAT)
			up.box(Vector3i(-1, -5, -1), Vector3i(0, -5, 0), COAT)
		else:
			up.box(Vector3i(-1, -5, -1), Vector3i(0, 1, 0), COAT)
		var upper := _part(body, Vector3(d[0], 0.0, d[1]), up)
		var lo := Vox.new(30 + i)
		lo.box(Vector3i(-1, -4, -1), Vector3i(0, -1, 0), COAT)
		lo.box(Vector3i(-1, -5, -1), Vector3i(0, -5, 0), SOCK if d[3] else COAT)
		lo.box(Vector3i(-1, -6, -1), Vector3i(0, -6, 0), HOOF, 0.02)
		var lower := _part(upper, Vector3(0, -UPPER_LEN, 0), lo)
		legs.append({"upper": upper, "lower": lower, "z": float(d[1]), "hind": hind})


# ---------------------------------------------------------------- props

func _build_props() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 4242
	props["tree"] = []
	for i in 3:
		var v := Vox.new(100 + i)
		var trunk_h := rng.randi_range(7, 11)
		v.box(Vector3i(-1, 0, -1), Vector3i(0, trunk_h, 0), Color(0.42, 0.28, 0.16))
		var r := rng.randf_range(3.2, 4.4)
		v.blob(Vector3i(0, trunk_h + int(r) - 1, 0), r, Color(0.2, 0.5, 0.18), 0.07, 1.2)
		v.blob(Vector3i(rng.randi_range(-2, 2), trunk_h + int(r) + 1, rng.randi_range(-2, 2)), r * 0.7, Color(0.25, 0.56, 0.2), 0.07, 1.0)
		props["tree"].append(v.build(0.25, mat))
	props["pine"] = []
	for i in 2:
		var v := Vox.new(110 + i)
		var trunk_h := 4
		v.box(Vector3i(-1, 0, -1), Vector3i(0, trunk_h, 0), Color(0.36, 0.24, 0.14))
		var layers := 5 + i * 2
		for l in layers:
			var rad := int(round(lerp(4.0, 0.0, float(l) / float(layers - 1))))
			v.box(Vector3i(-1 - rad, trunk_h + l * 2, -1 - rad), Vector3i(rad, trunk_h + l * 2 + 1, rad), Color(0.12, 0.38, 0.2), 0.05)
		props["pine"].append(v.build(0.25, mat))
	props["rock"] = []
	for i in 3:
		var v := Vox.new(120 + i)
		v.blob(Vector3i(0, 0, 0), rng.randf_range(1.6, 2.8), Color(0.55, 0.55, 0.53), 0.06, 1.0)
		props["rock"].append(v.build(0.3, mat, Vector3(0, -0.2, 0)))
	props["bush"] = []
	for i in 2:
		var v := Vox.new(130 + i)
		v.blob(Vector3i(0, 1, 0), rng.randf_range(2.0, 3.0), Color(0.24, 0.5, 0.2), 0.07, 1.0)
		v.put(Vector3i(1, 3, 2), Color(0.85, 0.15, 0.2), 0.0)
		v.put(Vector3i(-2, 2, 1), Color(0.85, 0.15, 0.2), 0.0)
		props["bush"].append(v.build(0.2, mat, Vector3(0, -0.2, 0)))
	props["flowers"] = []
	var petals := [Color(0.95, 0.9, 0.3), Color(0.9, 0.35, 0.5), Color(0.95, 0.95, 0.95), Color(0.55, 0.45, 0.9)]
	for i in 3:
		var v := Vox.new(140 + i)
		for f in 14:
			var p := Vector3i(rng.randi_range(-10, 10), 0, rng.randi_range(-10, 10))
			var stem := rng.randi_range(1, 3)
			v.box(p, p + Vector3i(0, stem - 1, 0), Color(0.2, 0.5, 0.15), 0.03)
			v.put(p + Vector3i(0, stem, 0), petals[rng.randi_range(0, petals.size() - 1)], 0.03)
		props["flowers"].append(v.build(0.1, mat))


func _update_chunks() -> void:
	var c := _chunk_of(horse.position)
	var needed := {}
	for dx in range(-VIEW_CHUNKS, VIEW_CHUNKS + 1):
		for dz in range(-VIEW_CHUNKS, VIEW_CHUNKS + 1):
			var key := Vector2i(c.x + dx, c.y + dz)
			needed[key] = true
			if not chunks.has(key):
				_make_chunk(key)
	for key in chunks.keys():
		if not needed.has(key):
			chunks[key].queue_free()
			chunks.erase(key)
			obstacles.erase(key)


func _chunk_of(p: Vector3) -> Vector2i:
	return Vector2i(int(floor(p.x / CHUNK)), int(floor(p.z / CHUNK)))


func _make_chunk(key: Vector2i) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key) ^ 0x5eed
	var node := Node3D.new()
	node.position = Vector3(key.x * CHUNK, 0, key.y * CHUNK)
	add_child(node)
	chunks[key] = node
	var obs: Array[Vector3] = []
	var count := rng.randi_range(4, 9)
	for i in count:
		var local := Vector3(rng.randf() * CHUNK, 0, rng.randf() * CHUNK)
		var world := node.position + local
		if Vector2(world.x, world.z).length() < 8.0:
			continue
		var roll := rng.randf()
		var kind := "flowers"
		var radius := 0.0
		if roll < 0.28:
			kind = "tree"
			radius = 0.7
		elif roll < 0.42:
			kind = "pine"
			radius = 0.7
		elif roll < 0.58:
			kind = "rock"
			radius = 0.9
		elif roll < 0.75:
			kind = "bush"
		var list: Array = props[kind]
		var mi := MeshInstance3D.new()
		mi.mesh = list[rng.randi_range(0, list.size() - 1)]
		mi.position = local
		mi.rotation.y = rng.randi_range(0, 3) * PI * 0.5
		var s := rng.randf_range(0.85, 1.3)
		mi.scale = Vector3.ONE * s
		if kind == "flowers" or kind == "bush":
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)
		if radius > 0.0:
			obs.append(Vector3(world.x, world.z, radius * s))
	obstacles[key] = obs


# ---------------------------------------------------------------- update

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("forward"):
		gait = mini(gait + 1, GAIT_NAMES.size() - 1)
	elif event.is_action_pressed("back"):
		gait = maxi(gait - 1, 0)
	elif event.is_action_pressed("camera"):
		cam_mode = (cam_mode + 1) % 4
	elif event is InputEventKey and event.pressed and not event.echo:
		var k: int = event.physical_keycode
		if k >= KEY_1 and k <= KEY_5:
			gait = k - KEY_1


func _process(delta: float) -> void:
	delta = minf(delta, 0.05)
	time += delta
	_move(delta)
	_animate(delta)
	_update_camera(delta)
	_update_chunks()
	ground.position = Vector3(round(horse.position.x), 0, round(horse.position.z))
	sun.position = horse.position
	var kmh := speed * 3.6
	hud.text = "Gait: %s   Speed: %d km/h   Distance: %d m\nW/S or 1-5: change gait   A/D: steer   Shift: sprint   Space: jump   C: camera" % [
		GAIT_NAMES[gait] if not (Input.is_action_pressed("sprint") and gait > 0) else "Sprint!", int(kmh), int(distance)]


func _move(delta: float) -> void:
	var target: float = GAIT_SPEEDS[gait]
	if Input.is_action_pressed("sprint") and gait > 0:
		target = SPRINT_SPEED
	speed = move_toward(speed, target, (6.0 if target > speed else 9.0) * delta)

	var steer := Input.get_axis("right", "left")
	var turn_scale := clampf(0.4 + speed / 10.0, 0.4, 1.3)
	yaw += steer * TURN_RATE * turn_scale * delta
	lean = lerpf(lean, steer * clampf(speed / 14.0, 0.0, 1.0) * 0.22, 1.0 - exp(-6.0 * delta))

	var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
	horse.position += fwd * speed * delta
	distance += speed * delta

	# Jumping.
	if height <= 0.0 and Input.is_action_just_pressed("jump"):
		vel_y = JUMP_SPEED + speed * 0.08
	vel_y -= GRAVITY * delta
	height += vel_y * delta
	if height <= 0.0:
		height = 0.0
		vel_y = 0.0
	air = move_toward(air, 1.0 if height > 0.05 else 0.0, delta * 6.0)

	# Push out of trees and rocks.
	var c := _chunk_of(horse.position)
	for dx in range(-1, 2):
		for dz in range(-1, 2):
			var key := Vector2i(c.x + dx, c.y + dz)
			if not obstacles.has(key):
				continue
			for o in obstacles[key]:
				if height > 1.2:
					continue
				var diff := Vector2(horse.position.x - o.x, horse.position.z - o.y)
				var min_d: float = o.z + 0.7
				if diff.length() < min_d and diff.length() > 0.001:
					var push := diff.normalized() * min_d
					horse.position.x = o.x + push.x
					horse.position.z = o.y + push.y
					speed *= 0.97

	horse.rotation.y = yaw


func _animate(delta: float) -> void:
	var freq := clampf(0.55 + speed * 0.13, 0.9, 2.8)
	if speed < 0.05:
		freq = 0.0
	phase = fmod(phase + freq * delta, 1.0)

	var move_amt := clampf(speed / 5.0, 0.0, 1.0)
	var gallop := clampf((speed - 6.0) / 4.0, 0.0, 1.0)
	var trot := clampf((speed - 2.5) / 2.0, 0.0, 1.0)
	var swing_amp := move_amt * lerpf(0.35, 0.7, gallop)
	var knee_amp := move_amt * lerpf(0.7, 1.3, gallop)

	var pitch := sin(phase * TAU + 0.8) * 0.08 * gallop * (1.0 - air)
	pitch += -vel_y * 0.03 * air

	var lowest := 0.0
	for i in legs.size():
		var leg: Dictionary = legs[i]
		var off := lerpf(lerpf(WALK_OFFSETS[i], TROT_OFFSETS[i], trot), GALLOP_OFFSETS[i], gallop)
		var p := (phase + off) * TAU
		var u := sin(p) * swing_amp
		var l := -maxf(0.0, cos(p)) * knee_amp
		# Tuck legs while airborne.
		if leg["hind"]:
			u = lerpf(u, -0.7, air)
			l = lerpf(l, 1.0, air)
		else:
			u = lerpf(u, 0.9, air)
			l = lerpf(l, -1.6, air)
		leg["upper"].rotation.x = u
		leg["lower"].rotation.x = l
		# How far below the body this hoof reaches (for ground contact).
		var reach: float = leg["z"] * sin(pitch) + UPPER_LEN * cos(u + pitch) + LOWER_LEN * cos(u + l + pitch)
		lowest = maxf(lowest, reach)

	var suspension := maxf(0.0, sin(phase * TAU * (2.0 - gallop))) * 0.05 * move_amt
	body.position.y = lowest + suspension + height
	body.rotation = Vector3(pitch, 0, lean)

	neck.rotation.x = -0.6 - 0.25 * gallop + sin(phase * TAU + 1.2) * 0.1 * move_amt + (0.05 * sin(time * 1.3) if speed < 0.1 else 0.0)
	head.rotation.x = -0.35 + 0.2 * gallop + sin(phase * TAU) * 0.08 * move_amt
	tail.rotation.x = lerpf(-0.25, -1.1, move_amt) + sin(phase * TAU * 2.0) * 0.12 * move_amt
	tail.rotation.z = sin(time * (1.5 + speed * 0.3)) * lerpf(0.12, 0.2, move_amt)

	dust.position = horse.position + horse.basis.z * 0.2 + Vector3(0, 0.05, 0)
	dust.rotation.y = yaw
	dust.emitting = speed > 7.0 and air < 0.5


func _update_camera(delta: float) -> void:
	var target := horse.position + Vector3(0, 1.3 + height * 0.5, 0)
	var desired: Vector3
	match cam_mode:
		0:
			desired = horse.position + horse.basis.z * 6.0 + Vector3(0, 2.6, 0)
		1:
			desired = horse.position + horse.basis.x * 7.0 - horse.basis.z * 1.0 + Vector3(0, 1.6, 0)
		2:
			desired = horse.position - horse.basis.z * 8.0 + Vector3(0, 2.2, 0)
		_:
			var a := time * 0.35
			desired = horse.position + Vector3(cos(a) * 9.0, 3.5, sin(a) * 9.0)
	camera.position = camera.position.lerp(desired, 1.0 - exp(-5.0 * delta))
	camera.look_at(target)
