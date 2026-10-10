extends RefCounted
## The voxel horse design. Every shape is authored in one "model space"
## (1 unit = one voxel, +Z = nose, +X = the horse's left, y = 0 under the
## hooves) and assigned to an animated part whose pivot is in the same space.

const VoxelModel = preload("res://scripts/voxel_model.gd")

const VOXEL_SIZE := 0.1

## Part name -> [parent part, pivot]. Parents are listed before children.
const PARTS := {
	"body": ["", Vector3(0, 13, 0)],
	"neck": ["body", Vector3(0, 15, 8)],
	"head": ["neck", Vector3(0, 22, 14)],
	"tail_a": ["body", Vector3(0, 16.5, -10.5)],
	"tail_b": ["tail_a", Vector3(0, 13, -13.5)],
	"fl_upper": ["body", Vector3(3, 12, 7)],
	"fl_lower": ["fl_upper", Vector3(3, 6, 7)],
	"fr_upper": ["body", Vector3(-3, 12, 7)],
	"fr_lower": ["fr_upper", Vector3(-3, 6, 7)],
	"hl_upper": ["body", Vector3(3, 13, -7)],
	"hl_lower": ["hl_upper", Vector3(3, 6, -8)],
	"hr_upper": ["body", Vector3(-3, 13, -7)],
	"hr_lower": ["hr_upper", Vector3(-3, 6, -8)],
}

const COATS := [
	{
		"name": "Bay", "coat": Color(0.6, 0.34, 0.17), "mane": Color(0.09, 0.06, 0.05),
		"points": Color(0.12, 0.08, 0.06), "muzzle": Color(0.22, 0.14, 0.1),
		"face": "star", "socks": [],
	},
	{
		"name": "Chestnut", "coat": Color(0.72, 0.36, 0.15), "mane": Color(0.55, 0.24, 0.09),
		"points": Color(0.72, 0.36, 0.15), "muzzle": Color(0.42, 0.24, 0.15),
		"face": "blaze", "socks": ["hl", "hr"],
	},
	{
		"name": "Palomino", "coat": Color(0.88, 0.68, 0.37), "mane": Color(0.98, 0.94, 0.83),
		"points": Color(0.88, 0.68, 0.37), "muzzle": Color(0.52, 0.4, 0.3),
		"face": "blaze", "socks": ["fl"],
	},
	{
		"name": "Black", "coat": Color(0.1, 0.09, 0.1), "mane": Color(0.04, 0.035, 0.04),
		"points": Color(0.1, 0.09, 0.1), "muzzle": Color(0.07, 0.06, 0.06),
		"face": "star", "socks": [],
	},
	{
		"name": "Grey", "coat": Color(0.84, 0.84, 0.82), "mane": Color(0.56, 0.56, 0.58),
		"points": Color(0.6, 0.6, 0.6), "muzzle": Color(0.36, 0.33, 0.33),
		"face": "none", "socks": [],
	},
	{
		"name": "Pinto", "coat": Color(0.95, 0.93, 0.88), "mane": Color(0.22, 0.13, 0.08),
		"points": Color(0.95, 0.93, 0.88), "muzzle": Color(0.55, 0.42, 0.4),
		"face": "blaze", "socks": [], "patches": Color(0.5, 0.27, 0.12),
	},
]

const WHITE := Color(0.96, 0.95, 0.92)
const EYE := Color(0.03, 0.02, 0.02)
const NOSTRIL := Color(0.05, 0.03, 0.03)
const HOOF := Color(0.2, 0.17, 0.15)
const PALE_HOOF := Color(0.55, 0.5, 0.42)


## Returns part name -> ArrayMesh, each mesh centred on its part's pivot.
static func build_meshes(coat: Dictionary, material: Material) -> Dictionary:
	var parts := build_voxels(coat)
	var meshes := {}
	for part_name: String in PARTS:
		var model: VoxelModel = parts[part_name]
		var pivot: Vector3 = PARTS[part_name][1]
		meshes[part_name] = model.build_mesh(VOXEL_SIZE, pivot, material, 0.05)
	return meshes


static func build_voxels(coat: Dictionary) -> Dictionary:
	var parts := {}
	for part_name: String in PARTS:
		parts[part_name] = VoxelModel.new()
	_build_body(parts["body"], coat)
	_build_neck(parts["neck"], coat)
	_build_head(parts["head"], coat)
	_build_tail(parts["tail_a"], parts["tail_b"], coat)
	var socks: Array = coat["socks"]
	for side in [1, -1]:
		var tag := "l" if side == 1 else "r"
		_build_front_leg(parts["f%s_upper" % tag], parts["f%s_lower" % tag], 3 * side, coat, socks.has("f" + tag))
		_build_hind_leg(parts["h%s_upper" % tag], parts["h%s_lower" % tag], 3 * side, coat, socks.has("h" + tag))
	if coat.has("patches"):
		_paint_patches(parts, coat)
	return parts


static func _build_body(m: VoxelModel, coat: Dictionary) -> void:
	var c: Color = coat["coat"]
	m.fill_blob(Vector3(0, 13, 0), Vector3(4.5, 4.2, 10.5), c, 3.0)   # barrel
	m.fill_blob(Vector3(0, 13.5, 7), Vector3(4.2, 4.6, 4.5), c, 2.5)  # chest
	m.fill_blob(Vector3(0, 14, -7), Vector3(4.8, 4.4, 5.0), c, 2.5)   # hindquarters
	m.fill_blob(Vector3(0, 17.2, 6), Vector3(1.6, 1.4, 3.5), c, 2.0)  # withers


static func _build_neck(m: VoxelModel, coat: Dictionary) -> void:
	m.fill_tube(Vector3(0, 14.5, 7.5), Vector3(0, 22, 13.5), 3.3, 2.3, coat["coat"])
	# Two-voxel-wide crest of mane along the top of the neck.
	m.fill_tube(Vector3(0, 16.4, 5.2), Vector3(0, 24, 12.3), 1.3, 1.3, coat["mane"])


static func _build_head(m: VoxelModel, coat: Dictionary) -> void:
	var c: Color = coat["coat"]
	m.fill_tube(Vector3(0, 22.3, 14.3), Vector3(0, 18.8, 19.3), 2.5, 1.9, c)
	m.fill_blob(Vector3(0, 20.8, 15.3), Vector3(2.3, 2.4, 2.3), c, 2.5)  # cheeks
	var muzzle: Color = coat["muzzle"]
	m.recolor(func(p: Vector3i, _c: Color) -> bool: return p.z >= 19, muzzle)

	# Face marking down the front of the head.
	var face: String = coat["face"]
	if face != "none":
		var z_end := 17 if face == "star" else 20
		for x in [-1, 0]:
			for z in range(16, z_end + 1):
				m.paint_surface(1, 1, Vector3i(x, 0, z), WHITE)

	# Eyes, nostrils and ears on both sides.
	for side in [1, -1]:
		m.paint_surface(0, side, Vector3i(0, 21, 16), EYE)
		m.paint_surface(2, 1, Vector3i(1 if side == 1 else -2, 19, 0), NOSTRIL)
		var ex := 1 if side == 1 else -2
		var top := m.surface(1, 1, Vector3i(ex, 0, 14))
		var ty := top.y if top != VoxelModel.NONE else 24
		var tip: Color = coat["points"]
		m.fill_box(Vector3i(ex, ty + 1, 13), Vector3i(ex, ty + 2, 14), c)
		m.set_voxel(Vector3i(ex, ty + 3, 14), tip)

	# Forelock between the ears.
	for x in [-1, 0]:
		for z in [14, 15]:
			var top := m.surface(1, 1, Vector3i(x, 0, z))
			if top != VoxelModel.NONE:
				m.set_voxel(top + Vector3i.UP, coat["mane"])
				m.set_voxel(top, coat["mane"])


static func _build_tail(a: VoxelModel, b: VoxelModel, coat: Dictionary) -> void:
	var c: Color = coat["mane"]
	a.fill_tube(Vector3(0, 16.5, -10.5), Vector3(0, 13, -13.5), 1.3, 1.6, c)
	b.fill_tube(Vector3(0, 13, -13.5), Vector3(0, 5.5, -15), 1.8, 1.3, c)
	b.fill_box(Vector3i(-1, 4, -16), Vector3i(0, 5, -15), c)


static func _build_front_leg(upper: VoxelModel, lower: VoxelModel, cx: int, coat: Dictionary, sock: bool) -> void:
	# Upper legs are 3 voxels wide and sit half a voxel inboard, so their outer
	# faces never share a plane with the body surface (no z-fighting).
	var ux := cx - signf(cx) * 0.5
	upper.fill_tube(Vector3(ux, 13.5, 7), Vector3(ux, 6.5, 7), 1.9, 1.3, coat["coat"])
	_build_cannon(lower, cx, 6, coat, sock)


static func _build_hind_leg(upper: VoxelModel, lower: VoxelModel, cx: int, coat: Dictionary, sock: bool) -> void:
	var c: Color = coat["coat"]
	var ux := cx - signf(cx) * 0.5
	upper.fill_tube(Vector3(ux, 14, -6.5), Vector3(ux, 6.5, -8), 1.9, 1.3, c)
	upper.fill_blob(Vector3(ux, 12, -6.5), Vector3(1.9, 3.5, 3.2), c, 2.2)  # thigh
	upper.fill_box(Vector3i(cx - 1, 6, -10), Vector3i(cx, 7, -9), c)        # point of hock
	_build_cannon(lower, cx, -9, coat, sock)


## Cannon bone, pastern and hoof; z0 is the rear voxel row of the leg.
static func _build_cannon(m: VoxelModel, cx: int, z0: int, coat: Dictionary, sock: bool) -> void:
	var leg: Color = coat["points"]
	m.fill_box(Vector3i(cx - 1, 2, z0), Vector3i(cx, 6, z0 + 1), leg)
	if sock:
		m.fill_box(Vector3i(cx - 1, 2, z0), Vector3i(cx, 4, z0 + 1), WHITE)
	var hoof := PALE_HOOF if sock else HOOF
	m.fill_box(Vector3i(cx - 1, 0, z0), Vector3i(cx, 1, z0 + 1), hoof)
	m.fill_box(Vector3i(cx - 1, 0, z0 + 2), Vector3i(cx, 0, z0 + 2), hoof)


static func _paint_patches(parts: Dictionary, coat: Dictionary) -> void:
	var noise := FastNoiseLite.new()
	noise.seed = 11
	noise.frequency = 0.07
	var base: Color = coat["coat"]
	var patch: Color = coat["patches"]
	for part_name in ["body", "neck", "head", "fl_upper", "fr_upper", "hl_upper", "hr_upper"]:
		var m: VoxelModel = parts[part_name]
		m.recolor(func(p: Vector3i, col: Color) -> bool:
			return col == base and noise.get_noise_3d(p.x * 1.4, p.y, p.z) > 0.12, patch)
