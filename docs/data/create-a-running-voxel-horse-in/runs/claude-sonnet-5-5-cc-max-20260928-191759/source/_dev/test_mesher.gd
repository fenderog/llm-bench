extends Node3D

const VoxelModel := preload("res://scripts/voxel_model.gd")
const DevUtil := preload("res://_dev/dev_util.gd")

func _ready() -> void:
	var t0 := Time.get_ticks_usec()
	var m := VoxelModel.new()
	m.fill_ellipsoid(Vector3(0, 6, 0), Vector3(7, 5, 5), Color("#a0522d"))
	m.fill_box(Vector3(-3, 0, -3), Vector3(3, 3, 3), Color("#f0f0f0"))
	m.fill_taper(Vector3(6, 8, 0), Vector3(12, 14, 0), Vector2(2.5, 2.0), Vector2(1.5, 1.2), Color("#4488cc"))
	var mesh := m.build_mesh(0.1, Vector3(0, 0, 0))
	print("voxels: %d  build ms: %.1f  surfaces: %d" % [m.count(), (Time.get_ticks_usec() - t0) / 1000.0, mesh.get_surface_count()])
	var mat := DevUtil.voxel_material()
	mesh.surface_set_material(0, mat)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	add_child(mi)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, 35, 0)
	light.shadow_enabled = true
	add_child(light)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#9fd0ff")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.6, 0.65, 0.75)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var cam := Camera3D.new()
	add_child(cam)
	cam.position = Vector3(2.2, 1.9, 2.8)
	cam.look_at(Vector3(0.4, 0.7, 0))
	for i in 4:
		await get_tree().process_frame
	DevUtil.save_shot(get_viewport(), "mesher.png")
	get_tree().quit()
