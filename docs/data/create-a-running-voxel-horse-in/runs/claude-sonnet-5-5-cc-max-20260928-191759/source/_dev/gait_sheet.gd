extends Node3D
## Dev tool: renders N horses side by side, one per stride phase.
## Usage: godot --path . res://_dev/gait_sheet.tscn -- gait=4 speed=10 count=8 out=sheet.png [leap=1]

const DevUtil := preload("res://_dev/dev_util.gd")
const VoxelHorse := preload("res://scripts/voxel_horse.gd")

func _ready() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	var gait_id := int(args.get("gait", "4"))
	var spd := float(args.get("speed", "10"))
	var count := int(args.get("count", "8"))
	var out: String = args.get("out", "sheet.png")
	var leap := args.has("leap")
	var spacing := 3.3
	var phase0 := float(args.get("phase0", "0"))
	var phase_span := float(args.get("span", "1"))

	var sv := SubViewport.new()
	sv.size = Vector2i(int(count * 460), 500)
	sv.msaa_3d = Viewport.MSAA_4X
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(sv)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(200, 200)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("#7fbf4a")
	ground.material_override = gm
	sv.add_child(ground)

	for i in count:
		var horse := VoxelHorse.new()
		sv.add_child(horse)
		horse.position = Vector3(0, 0, -i * spacing)
		var f := float(i) / float(count)
		if leap:
			horse.apply_debug_leap(f, spd)
			horse.position.y = 4.0 * 0.0 + sin(PI * f) * 1.1
		else:
			horse.apply_debug_pose(gait_id, fposmod(phase0 + f * phase_span, 1.0), spd)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45, 60, 0)
	light.shadow_enabled = true
	sv.add_child(light)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#cfe8ff")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.7, 0.72, 0.8)
	env.ambient_light_energy = 0.7
	var we := WorldEnvironment.new()
	we.environment = env
	sv.add_child(we)

	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	var width := count * spacing
	cam.size = width * float(sv.size.y) / float(sv.size.x)
	sv.add_child(cam)
	var zc := -(count - 1) * spacing * 0.5
	var cy := 1.3 + (0.35 if leap else 0.0)
	cam.position = Vector3(30, cy, zc)
	cam.look_at(Vector3(0, cy, zc))

	for i in 5:
		await get_tree().process_frame
	var img := sv.get_texture().get_image()
	img.save_png(DevUtil.shot_path(out))
	print("saved ", out, " ", img.get_size())
	get_tree().quit()
