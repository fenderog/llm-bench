extends Node3D
## Dev tool: renders the horse from a handful of camera angles.
## Usage: godot --path . res://_dev/view_horse.tscn -- views=side,front prefix=rest

const DevUtil := preload("res://_dev/dev_util.gd")
const VoxelHorse := preload("res://scripts/voxel_horse.gd")

const VIEWS := {
	"side": {"yaw": 90.0, "pitch": 4.0, "dist": 3.6, "target": Vector3(0, 0.95, 0)},
	"left": {"yaw": -90.0, "pitch": 4.0, "dist": 3.6, "target": Vector3(0, 0.95, 0)},
	"front": {"yaw": 180.0, "pitch": 6.0, "dist": 3.6, "target": Vector3(0, 1.0, 0)},
	"rear": {"yaw": 0.0, "pitch": 8.0, "dist": 3.6, "target": Vector3(0, 1.0, 0)},
	"q34": {"yaw": 140.0, "pitch": 14.0, "dist": 3.6, "target": Vector3(0, 0.95, 0)},
	"q34r": {"yaw": 40.0, "pitch": 14.0, "dist": 3.6, "target": Vector3(0, 0.95, 0)},
	"head": {"yaw": 115.0, "pitch": 8.0, "dist": 1.6, "target": Vector3(0, 1.55, -0.45)},
	"top": {"yaw": 90.0, "pitch": 80.0, "dist": 4.0, "target": Vector3(0, 0.9, 0)},
}

func _ready() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	var views: PackedStringArray = String(args.get("views", "side,q34")).split(",")
	var prefix: String = args.get("prefix", "horse")

	var horse := VoxelHorse.new()
	add_child(horse)

	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(60, 60)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("#6fae3f")
	gm.roughness = 1.0
	ground.material_override = gm
	add_child(ground)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-52, 35, 0)
	light.shadow_enabled = true
	light.light_energy = 1.0
	add_child(light)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#b6dcff")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.68, 0.8)
	env.ambient_light_energy = 0.6
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var cam := Camera3D.new()
	cam.fov = 40
	add_child(cam)

	if horse.has_method("apply_debug_pose") and args.has("phase"):
		horse.apply_debug_pose(args.get("gait", "gallop"), float(args["phase"]), float(args.get("speed", "9")))

	for i in 3:
		await get_tree().process_frame
	for v in views:
		var cfg: Dictionary = VIEWS[v]
		var yaw := deg_to_rad(cfg["yaw"])
		var pitch := deg_to_rad(cfg["pitch"])
		var d: float = cfg["dist"]
		var tgt: Vector3 = cfg["target"]
		cam.position = tgt + Vector3(cos(pitch) * sin(yaw), sin(pitch), cos(pitch) * cos(yaw)) * d
		cam.look_at(tgt)
		for i in 3:
			await get_tree().process_frame
		DevUtil.save_shot(get_viewport(), "%s_%s.png" % [prefix, v])
	get_tree().quit()
