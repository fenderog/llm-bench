extends Node3D
## The meadow around the horse: sky, fog, ground, voxel trees / rocks / flowers, clouds
## and distant mountains.
##
## Props live in MultiMeshes whose instances wrap around the horse (a torus of tiles),
## so a fixed amount of geometry gives an endless world. Instances shrink to nothing
## near the wrap radius, which hides the pop-in inside the fog.

const VoxelBuilder = preload("res://scripts/voxel_builder.gd")
const GROUND_SHADER = preload("res://shaders/ground.gdshader")

const HAZE := Color(0.74, 0.86, 0.96)
const SLICES := 4                 # every prop is refreshed once per SLICES frames
const CLOUD_TILE := 700.0

class PropGroup:
	var mmi: MultiMeshInstance3D
	var count := 0
	var tile := 200.0
	var radius := 90.0            # instances further away than this are hidden
	var fade := 14.0              # ...and scale up over this distance
	var solid := 0.0              # collision radius at scale 1 (0 = not solid)
	var jumpable := false         # the horse can hop over it
	var base := PackedVector2Array()
	var yaw := PackedFloat32Array()
	var size := PackedFloat32Array()
	var cur_pos := PackedVector2Array()
	var cur_scale := PackedFloat32Array()
	var cursor := 0

var _rng := RandomNumberGenerator.new()
var _prop_material := StandardMaterial3D.new()
var _groups: Array[PropGroup] = []
var _solid_groups: Array[PropGroup] = []
var _big_spots := PackedVector2Array()   # keeps trees, rocks and bushes apart
var _ground: MeshInstance3D
var _mountains: MeshInstance3D
var _clouds: Array[MeshInstance3D] = []
var _cloud_base: Array[Vector3] = []
var _time := 0.0


func _ready() -> void:
	_rng.seed = 20240607
	_prop_material.vertex_color_use_as_albedo = true
	_prop_material.vertex_color_is_srgb = true
	_prop_material.roughness = 1.0
	_prop_material.metallic_specular = 0.1

	_build_environment()
	_build_ground()
	_build_mountains()
	_build_clouds()
	_build_props()
	update_focus(Vector3.ZERO, 0.0, true)


# ---------------------------------------------------------------------------
# Sky, light, fog
# ---------------------------------------------------------------------------

func _build_environment() -> void:
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.22, 0.47, 0.86)
	sky_material.sky_horizon_color = HAZE
	sky_material.sky_curve = 0.22
	sky_material.ground_horizon_color = HAZE
	sky_material.ground_bottom_color = HAZE
	sky_material.ground_curve = 0.05
	sky_material.sun_angle_max = 25.0
	sky_material.sun_curve = 0.12

	var sky := Sky.new()
	sky.sky_material = sky_material

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.72, 0.80, 0.92)
	env.ambient_light_energy = 0.55
	env.fog_enabled = true
	env.fog_light_color = HAZE
	env.fog_density = 0.011
	env.fog_sky_affect = 0.0

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-46.0, 36.0, 0.0)
	sun.light_color = Color(1.0, 0.96, 0.88)
	sun.light_energy = 0.95
	sun.shadow_enabled = true
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 45.0
	add_child(sun)


# ---------------------------------------------------------------------------
# Ground, mountains, clouds
# ---------------------------------------------------------------------------

func _build_ground() -> void:
	var plane := PlaneMesh.new()
	plane.size = Vector2(700.0, 700.0)
	var mat := ShaderMaterial.new()
	mat.shader = GROUND_SHADER
	_ground = MeshInstance3D.new()
	_ground.mesh = plane
	_ground.material_override = mat
	_ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_ground)


func _flat_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.disable_fog = true
	return mat


func _build_mountains() -> void:
	const VOXEL_SIZE := 8.0
	var b := VoxelBuilder.new()
	b.face_light = true
	b.jitter = 0.03
	var noise := FastNoiseLite.new()
	noise.seed = 4
	noise.frequency = 0.3
	noise.fractal_octaves = 3
	var palette := [
		HAZE.lerp(Color(0.62, 0.80, 0.84), 0.5),
		Color(0.62, 0.80, 0.84),
		Color(0.64, 0.76, 0.88),
		Color(0.72, 0.78, 0.92),
		Color(1.0, 1.0, 1.0),
	]
	for ix in range(-42, 42):
		for iz in range(-42, 42):
			var cx := ix + 0.5
			var cz := iz + 0.5
			var r := Vector2(cx, cz).length()
			if r < 33.0 or r > 40.0:
				continue
			var n := clampf(0.5 + 0.9 * noise.get_noise_2d(cx, cz), 0.0, 1.0)
			var ridge := clampf(1.2 - absf(r - 36.0) / 4.0, 0.15, 1.0)
			var h := int(1.0 + n * 8.0 * ridge)
			for y in h:
				var c: Color = palette[mini(y, 4)]
				if y >= 6:
					c = palette[4]
				b.set_voxel(Vector3i(ix, y, iz), c)
	_mountains = MeshInstance3D.new()
	_mountains.mesh = b.build_mesh(Vector3.ZERO, VOXEL_SIZE)
	_mountains.material_override = _flat_material()
	_mountains.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_mountains.extra_cull_margin = 1000.0
	add_child(_mountains)


func _build_clouds() -> void:
	var meshes: Array[ArrayMesh] = []
	for variant in 3:
		var b := VoxelBuilder.new()
		b.face_light = true
		b.jitter = 0.02
		var lumps := 3 + variant
		for k in lumps:
			var c := Vector3(_rng.randf_range(-5.0, 5.0), 0.0, _rng.randf_range(-3.0, 3.0))
			var rad := Vector3(_rng.randf_range(3.0, 5.0), _rng.randf_range(1.2, 1.8), _rng.randf_range(2.0, 3.2))
			b.fill_ellipsoid(c, rad, [Color(1, 1, 1)], variant * 10 + k)
		meshes.append(b.build_mesh(Vector3.ZERO, 4.5))
	var mat := _flat_material()
	for i in 14:
		var mi := MeshInstance3D.new()
		mi.mesh = meshes[i % 3]
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.rotation.y = _rng.randf() * TAU
		mi.scale = Vector3.ONE * _rng.randf_range(0.8, 1.6)
		add_child(mi)
		_clouds.append(mi)
		_cloud_base.append(Vector3(
				_rng.randf_range(0.0, CLOUD_TILE),
				_rng.randf_range(75.0, 115.0),
				_rng.randf_range(0.0, CLOUD_TILE)))


# ---------------------------------------------------------------------------
# Props
# ---------------------------------------------------------------------------

func _build_props() -> void:
	var oak_green := [Color(0.22, 0.48, 0.16), Color(0.27, 0.56, 0.19), Color(0.19, 0.42, 0.14)]
	var oak_lime := [Color(0.45, 0.62, 0.17), Color(0.52, 0.70, 0.20), Color(0.40, 0.56, 0.15)]
	var oak_autumn := [Color(0.80, 0.42, 0.13), Color(0.87, 0.55, 0.16), Color(0.70, 0.30, 0.11)]
	var pine_green := [Color(0.11, 0.33, 0.20), Color(0.14, 0.39, 0.23), Color(0.09, 0.28, 0.17)]
	var stones := [Color(0.50, 0.51, 0.53), Color(0.58, 0.59, 0.60), Color(0.43, 0.44, 0.47)]

	#            mesh                             count tile  radius fade  size range         spacing solid clear
	_add_group(_make_oak(oak_green, 1),           20, 200.0, 95.0, 14.0, Vector2(0.85, 1.35), 12.0, 0.4, 16.0)
	_add_group(_make_oak(oak_lime, 2),            14, 200.0, 95.0, 14.0, Vector2(0.8, 1.2), 12.0, 0.4, 16.0)
	_add_group(_make_oak(oak_autumn, 3),           8, 200.0, 95.0, 14.0, Vector2(0.8, 1.2), 12.0, 0.4, 16.0)
	_add_group(_make_pine(pine_green, 4),         24, 200.0, 95.0, 14.0, Vector2(0.8, 1.4), 10.0, 0.4, 16.0)
	_add_group(_make_rock(stones, 5, 1.0),        20, 200.0, 90.0, 12.0, Vector2(0.7, 1.5), 8.0, 0.9, 10.0, true)
	_add_group(_make_rock(stones, 6, 0.65),       16, 200.0, 90.0, 12.0, Vector2(0.7, 1.4), 6.0, 0.0, 8.0, true)
	_add_group(_make_bush(oak_green, 7),          40, 200.0, 80.0, 12.0, Vector2(0.8, 1.3), 6.0, 0.0, 6.0)
	_add_group(_make_flowers(8),                 130, 80.0, 36.0, 10.0, Vector2(0.8, 1.3), 0.0, 0.0, 0.0)
	_add_group(_make_tuft(9),                    300, 70.0, 32.0, 10.0, Vector2(0.7, 1.4), 0.0, 0.0, 0.0)


func _add_group(mesh: Mesh, count: int, tile: float, radius: float, fade: float, size_range: Vector2,
		spacing: float, solid: float, clear: float, jumpable := false) -> void:
	var g := PropGroup.new()
	g.count = count
	g.tile = tile
	g.radius = radius
	g.fade = fade
	g.solid = solid
	g.jumpable = jumpable
	g.base.resize(count)
	g.yaw.resize(count)
	g.size.resize(count)
	g.cur_pos.resize(count)
	g.cur_scale.resize(count)
	for i in count:
		var pos := Vector2.ZERO
		for attempt in 40:
			pos = Vector2(_rng.randf_range(-0.5, 0.5), _rng.randf_range(-0.5, 0.5)) * tile
			if pos.length() < clear:
				continue
			if spacing > 0.0 and not _spot_free(pos, spacing, tile):
				continue
			break
		if spacing > 0.0:
			_big_spots.append(pos)
		g.base[i] = pos
		g.yaw[i] = _rng.randf() * TAU
		g.size[i] = _rng.randf_range(size_range.x, size_range.y)
		g.cur_scale[i] = -1.0

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = count
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = _prop_material
	mmi.extra_cull_margin = 1000.0
	add_child(mmi)
	g.mmi = mmi
	_groups.append(g)
	if solid > 0.0:
		_solid_groups.append(g)


func _spot_free(pos: Vector2, spacing: float, tile: float) -> bool:
	for other in _big_spots:
		var dx := absf(pos.x - other.x)
		var dy := absf(pos.y - other.y)
		dx = minf(dx, tile - dx)
		dy = minf(dy, tile - dy)
		if dx * dx + dy * dy < spacing * spacing:
			return false
	return true


func _make_oak(leaves: Array, seed_value: int) -> ArrayMesh:
	var b := VoxelBuilder.new()
	var bark := [Color(0.36, 0.24, 0.14), Color(0.31, 0.20, 0.12)]
	b.fill_box(Vector3i(-1, 0, -1), Vector3i(1, 10, 1), bark[0])
	b.fill_box(Vector3i(-2, 0, -1), Vector3i(-1, 1, 1), bark[1])
	b.fill_box(Vector3i(1, 0, -1), Vector3i(2, 1, 1), bark[1])
	b.fill_box(Vector3i(-1, 0, -2), Vector3i(1, 1, -1), bark[1])
	b.fill_box(Vector3i(-1, 0, 1), Vector3i(1, 1, 2), bark[1])
	b.fill_ellipsoid(Vector3(0, 11.0, 0), Vector3(4.6, 3.8, 4.6), leaves, seed_value)
	b.fill_ellipsoid(Vector3(2.6, 9.6, 1.2), Vector3(2.8, 2.2, 2.8), leaves, seed_value + 1)
	b.fill_ellipsoid(Vector3(-2.4, 10.0, -1.6), Vector3(3.0, 2.4, 2.8), leaves, seed_value + 2)
	b.fill_ellipsoid(Vector3(0.6, 14.0, -0.4), Vector3(2.6, 1.8, 2.6), leaves, seed_value + 3)
	return b.build_mesh(Vector3.ZERO, 0.25)


func _make_pine(leaves: Array, seed_value: int) -> ArrayMesh:
	var b := VoxelBuilder.new()
	b.fill_box(Vector3i(-1, 0, -1), Vector3i(1, 6, 1), Color(0.33, 0.22, 0.13))
	for y in range(3, 21):
		var tier := (y - 3) / 4
		var row := (y - 3) % 4
		var radius := 4.6 - tier * 0.85 - row * 0.35
		if radius < 0.6:
			radius = 0.6
		for x in range(-6, 6):
			for z in range(-6, 6):
				var d := Vector2(x + 0.5, z + 0.5).length()
				if d <= radius:
					var pick := int(VoxelBuilder.hash3(Vector3i(x, y, z), seed_value) * leaves.size())
					b.set_voxel(Vector3i(x, y, z), leaves[pick % leaves.size()])
	return b.build_mesh(Vector3.ZERO, 0.25)


func _make_rock(colors: Array, seed_value: int, scale_factor: float) -> ArrayMesh:
	var b := VoxelBuilder.new()
	b.fill_ellipsoid(Vector3(0, 1.5, 0), Vector3(2.8, 1.7, 2.3) * scale_factor, colors, seed_value)
	b.fill_ellipsoid(Vector3(1.6, 1.0, 0.8) * scale_factor, Vector3(1.8, 1.2, 1.6) * scale_factor, colors, seed_value + 1)
	return b.build_mesh(Vector3.ZERO, 0.25)


func _make_bush(leaves: Array, seed_value: int) -> ArrayMesh:
	var b := VoxelBuilder.new()
	b.fill_ellipsoid(Vector3(0, 1.4, 0), Vector3(2.4, 1.5, 2.4), leaves, seed_value)
	b.fill_ellipsoid(Vector3(1.8, 1.0, 0.6), Vector3(1.6, 1.1, 1.6), leaves, seed_value + 1)
	return b.build_mesh(Vector3.ZERO, 0.2)


func _make_flowers(seed_value: int) -> ArrayMesh:
	var b := VoxelBuilder.new()
	var petals := [Color(0.92, 0.22, 0.24), Color(0.98, 0.84, 0.20), Color(0.96, 0.96, 0.92),
			Color(0.86, 0.42, 0.80), Color(0.30, 0.50, 0.92)]
	var stem := Color(0.20, 0.45, 0.14)
	for k in 7:
		var p := Vector3i(_rng.randi_range(-5, 4), 0, _rng.randi_range(-5, 4))
		var height := _rng.randi_range(2, 4)
		var petal: Color = petals[_rng.randi() % petals.size()]
		for y in height:
			b.set_voxel(p + Vector3i(0, y, 0), stem)
		b.set_voxel(p + Vector3i(0, height, 0), petal.lerp(Color(1.0, 0.9, 0.3), 0.5))
		for off in [Vector3i(1, 0, 0), Vector3i(-1, 0, 0), Vector3i(0, 0, 1), Vector3i(0, 0, -1)]:
			b.set_voxel(p + Vector3i(0, height, 0) + off, petal)
	return b.build_mesh(Vector3.ZERO, 0.06)


func _make_tuft(seed_value: int) -> ArrayMesh:
	var b := VoxelBuilder.new()
	var greens := [Color(0.20, 0.44, 0.13), Color(0.27, 0.55, 0.17), Color(0.36, 0.64, 0.21)]
	for k in 6:
		var p := Vector3i(_rng.randi_range(-3, 2), 0, _rng.randi_range(-3, 2))
		var height := _rng.randi_range(3, 6)
		for y in height:
			b.set_voxel(p + Vector3i(0, y, 0), greens[mini(2, y * 3 / height)])
	return b.build_mesh(Vector3.ZERO, 0.08)


# ---------------------------------------------------------------------------
# Per-frame
# ---------------------------------------------------------------------------

## Keeps everything centred on the horse. `full` refreshes every prop at once.
func update_focus(focus: Vector3, delta: float, full := false) -> void:
	_time += delta
	var f2 := Vector2(focus.x, focus.z)
	_ground.position = Vector3(focus.x, 0.0, focus.z)
	_mountains.position = Vector3(focus.x, -2.0, focus.z)

	for g in _groups:
		var n := g.count if full else ceili(float(g.count) / SLICES)
		_refresh_group(g, f2, n)

	for i in _clouds.size():
		var b := _cloud_base[i]
		var x := fposmod(b.x + _time * 3.0 - focus.x + CLOUD_TILE * 0.5, CLOUD_TILE) - CLOUD_TILE * 0.5
		var z := fposmod(b.z + _time * 1.2 - focus.z + CLOUD_TILE * 0.5, CLOUD_TILE) - CLOUD_TILE * 0.5
		_clouds[i].position = Vector3(focus.x + x, b.y, focus.z + z)


func _refresh_group(g: PropGroup, focus: Vector2, n: int) -> void:
	var mm := g.mmi.multimesh
	for k in n:
		var i := g.cursor
		g.cursor = (g.cursor + 1) % g.count
		var b := g.base[i]
		var wx := b.x + g.tile * floorf((focus.x - b.x) / g.tile + 0.5)
		var wz := b.y + g.tile * floorf((focus.y - b.y) / g.tile + 0.5)
		var d := Vector2(wx - focus.x, wz - focus.y).length()
		var s := maxf(g.size[i] * clampf((g.radius - d) / g.fade, 0.0, 1.0), 0.001)
		var cur := g.cur_pos[i]
		if s == g.cur_scale[i] and cur.x == wx and cur.y == wz:
			continue
		g.cur_pos[i] = Vector2(wx, wz)
		g.cur_scale[i] = s
		var basis := Basis(Vector3.UP, g.yaw[i]).scaled(Vector3(s, s, s))
		mm.set_instance_transform(i, Transform3D(basis, Vector3(wx, 0.0, wz)))


## Pushes a circle (the horse) out of trees and boulders. Returns the corrected position.
func resolve_collisions(pos: Vector2, radius: float, airborne: bool) -> Vector2:
	for g in _solid_groups:
		if airborne and g.jumpable:
			continue
		for i in g.count:
			var p := g.cur_pos[i]
			var dx := pos.x - p.x
			var dz := pos.y - p.y
			var reach := g.solid * g.cur_scale[i] + radius
			var d2 := dx * dx + dz * dz
			if d2 >= reach * reach:
				continue
			var d := sqrt(d2)
			if d < 0.0001:
				pos.x += reach
			else:
				pos += Vector2(dx, dz) / d * (reach - d)
	return pos
