extends RefCounted
## Development-only helpers (not part of the shipped game).

const SHOT_DIR := "res://_shots/"

static func shot_path(name: String) -> String:
	return ProjectSettings.globalize_path(SHOT_DIR + name)

static func save_shot(vp: Viewport, name: String) -> void:
	var img := vp.get_texture().get_image()
	var err := img.save_png(shot_path(name))
	print("saved %s (%dx%d) err=%d" % [name, img.get_width(), img.get_height(), err])

static func voxel_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 0.9
	return mat
