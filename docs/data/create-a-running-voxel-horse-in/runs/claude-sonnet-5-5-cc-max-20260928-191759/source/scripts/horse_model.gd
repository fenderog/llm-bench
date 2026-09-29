extends RefCounted
## Voxel sculpt of the horse, split into rigid parts for animation.
##
## Model space: +X is forward, +Y up, +Z the horse's right; one voxel is
## VOXEL metres and the hooves stand on y = 0. Every builder returns a
## VoxelModel positioned in that shared space; the rig constants below say
## where each part pivots. The animation code turns those into a node tree.

const VoxelModel := preload("res://scripts/voxel_model.gd")

const VOXEL := 0.06

# ---- Rig layout (voxel units, model space) --------------------------------
const BODY_PIVOT := Vector3(14.0, 18.0, 0.0)
const NECK_PIVOT := Vector3(21.5, 20.5, 0.0)
const HEAD_PIVOT := Vector3(30.0, 29.5, 0.0)
const TAIL_PIVOT := Vector3(1.4, 22.0, 0.0)
## Shoulder / hip joint of the right-hand legs (left legs mirror z).
const FORE_PIVOT := Vector3(22.5, 17.5, 2.6)
const HIND_PIVOT := Vector3(4.5, 17.5, 3.0)

## Bone lengths: pivot -> knee (hock) -> fetlock; the hoof piece hangs below.
const FORE_UPPER := 10.5
const FORE_LOWER := 5.0
const HIND_UPPER := 9.0
const HIND_LOWER := 6.5
const HOOF_LEN := 3.0

const TAIL_SEGMENTS := 3
const TAIL_SEG_LEN := 6.0
const MANE_TUFTS := 7

# ---- Palette (sRGB) ---------------------------------------------------------
const COAT := Color("#a4552a")
const COAT_DARK := Color("#7f3f1e")
const COAT_LIGHT := Color("#c8814a")
const MANE := Color("#2a1911")
const HOOF := Color("#2b2624")
const SOCK := Color("#efe7da")
const MUZZLE := Color("#b9806c")
const EYE := Color("#0c0908")
const NOSTRIL := Color("#3a231c")
const EAR := Color("#8a4523")  # marker colour, repainted with a gradient

const HEAD_ANGLE_DEG := -48.0
const HEAD_LENGTH := 11.5


static func _coat_for_height(y: float) -> Color:
	var t := clampf((y - 12.0) / 12.5, 0.0, 1.0)
	return COAT_LIGHT.lerp(COAT_DARK, smoothstep(0.05, 0.95, t))


static func _sd_torso(p: Vector3) -> float:
	var q := Vector3(p.x, p.y, absf(p.z))
	# Deep chest, tucked-up waist, high rounded croup, a dip in the back. The
	# boxy superellipsoids keep flanks flat and edges chamfered - very voxel.
	var chest := VoxelModel.sd_superellipsoid(q, Vector3(22.2, 18.2, 0.0), Vector3(5.8, 6.4, 4.0), 2.8)
	var barrel := VoxelModel.sd_superellipsoid(q, Vector3(14.0, 17.7, 0.0), Vector3(8.8, 5.2, 4.3), 3.2)
	var rump := VoxelModel.sd_superellipsoid(q, Vector3(6.0, 19.0, 0.0), Vector3(6.4, 5.5, 4.5), 2.8)
	var withers := VoxelModel.sd_ellipsoid(q, Vector3(19.6, 24.2, 0.0), Vector3(3.6, 1.9, 1.5))
	var d := VoxelModel.smin(chest, barrel, 2.5)
	d = VoxelModel.smin(d, rump, 2.5)
	return VoxelModel.smin(d, withers, 1.5)


static func build_torso() -> VoxelModel:
	var m := VoxelModel.new()
	m.fill_sdf(Vector3(-2, 10, -7), Vector3(31, 28, 7), _sd_torso, COAT)
	m.recolor(func(p: Vector3i, _c: Color) -> Color: return _coat_for_height(p.y + 0.5))
	return m


static func neck_end() -> Vector3:
	return HEAD_PIVOT + Vector3(-0.6, -0.6, 0.0)


static func build_neck() -> VoxelModel:
	var m := VoxelModel.new()
	var a := NECK_PIVOT + Vector3(-1.5, -1.5, 0.0)
	var b := neck_end()
	var ra := Vector2(4.9, 3.3)
	var rb := Vector2(2.8, 2.0)
	m.fill_sdf(Vector3(a.x - 6, a.y - 6, -5), Vector3(b.x + 5, b.y + 5, 5),
			func(p: Vector3) -> float: return VoxelModel.sd_taper(p, a, b, ra, rb), COAT)
	var axis := Vector2(b.x - a.x, b.y - a.y).normalized()
	m.recolor(func(p: Vector3i, _c: Color) -> Color:
		# Darker along the crest (up/back side of the neck), lighter underneath.
		var rel := Vector2(p.x + 0.5 - a.x, p.y + 0.5 - a.y)
		var side := rel.x * -axis.y + rel.y * axis.x  # +: away from the throat
		var t := clampf(0.5 + side / 7.0, 0.0, 1.0)
		return COAT_LIGHT.lerp(COAT_DARK, smoothstep(0.1, 0.95, t)))
	return m


static func head_axis() -> Vector3:
	var ang := deg_to_rad(HEAD_ANGLE_DEG)
	return Vector3(cos(ang), sin(ang), 0.0)


## Recolours the outermost existing voxel of the column at (x, y) on one side.
static func _paint_outer(m: VoxelModel, x: int, y: int, side: int, col: Color) -> void:
	for step in range(5, -1, -1):
		var z := step if side > 0 else -step - 1
		if m.has_voxel(Vector3i(x, y, z)):
			m.set_voxel(Vector3i(x, y, z), col)
			return


static func build_head() -> VoxelModel:
	var m := VoxelModel.new()
	var p0 := HEAD_PIVOT
	var dir := head_axis()
	var perp := Vector3(-dir.y, dir.x, 0.0)  # towards the bridge of the nose
	var sk_a := p0 - dir * 1.0
	var sk_b := p0 + dir * 5.0
	var fc_a := p0 + dir * 3.5
	var fc_b := p0 + dir * 10.0
	var mz_a := p0 + dir * 9.0
	var mz_b := p0 + dir * 11.5
	m.fill_sdf(p0 - Vector3(8, 14, 5), p0 + Vector3(12, 8, 5), func(p: Vector3) -> float:
		var skull := VoxelModel.sd_taper(p, sk_a, sk_b, Vector2(3.6, 2.5), Vector2(3.1, 2.4))
		var face := VoxelModel.sd_taper(p, fc_a, fc_b, Vector2(3.0, 2.3), Vector2(1.75, 1.3))
		var muzzle := VoxelModel.sd_taper(p, mz_a, mz_b, Vector2(2.0, 1.3), Vector2(1.6, 1.2))
		return VoxelModel.smin(VoxelModel.smin(skull, face, 1.6), muzzle, 1.0), COAT)
	# Ears.
	for sz in [-1.5, 1.5]:
		m.fill_taper(Vector3(p0.x + 0.1, p0.y + 2.4, sz), Vector3(p0.x - 1.2, p0.y + 7.0, sz),
				Vector2(1.05, 0.6), Vector2(0.5, 0.5), EAR)
	# Forelock falling between the ears onto the forehead.
	m.fill_taper(Vector3(p0.x + 1.8, p0.y + 2.0, 0.0), Vector3(p0.x + 3.2, p0.y - 2.6, 0.0),
			Vector2(1.0, 1.0), Vector2(0.9, 1.0), MANE)

	var length := HEAD_LENGTH
	m.recolor(func(p: Vector3i, c: Color) -> Color:
		if c == MANE:
			return MANE
		if c == EAR:
			return COAT_DARK.lerp(MANE, clampf((p.y + 0.5 - p0.y - 4.6) / 2.2, 0.0, 1.0))
		var rel := Vector3(p.x + 0.5 - p0.x, p.y + 0.5 - p0.y, 0.0)
		var t := rel.dot(dir) / length
		var s := rel.dot(perp)
		var col := COAT_LIGHT.lerp(COAT, clampf(0.55 + s / 5.0, 0.0, 1.0))
		if t > 0.84:
			col = MUZZLE
		if s > 1.3 and absf(p.z + 0.5) < 1.0 and t > 0.1 and t < 0.86:
			col = SOCK  # white blaze down the nose
		return col)
	var eye_c := p0 + dir * 3.2 + perp * 0.5
	_paint_outer(m, int(floor(eye_c.x)), int(floor(eye_c.y)), 1, EYE)
	_paint_outer(m, int(floor(eye_c.x)), int(floor(eye_c.y)), -1, EYE)
	var nose_c := p0 + dir * 10.6 + perp * 0.2
	_paint_outer(m, int(floor(nose_c.x)), int(floor(nose_c.y)), 1, NOSTRIL)
	_paint_outer(m, int(floor(nose_c.x)), int(floor(nose_c.y)), -1, NOSTRIL)
	return m


## A tuft of mane growing along +Y from its pivot at the origin.
static func build_mane_tuft(length: float, radius: float) -> VoxelModel:
	var m := VoxelModel.new()
	m.fill_taper(Vector3(0.0, -0.5, 0.0), Vector3(0.0, length, 0.0), Vector2(radius, 1.2),
			Vector2(radius * 0.5, 0.9), MANE)
	return m


## Tail segment hanging along -Y from its pivot at the origin.
static func build_tail_segment(index: int) -> VoxelModel:
	var m := VoxelModel.new()
	var f := float(index) / float(TAIL_SEGMENTS - 1)
	var top_r := Vector2(lerpf(1.6, 2.1, f), lerpf(1.6, 1.6, f))
	var bot_r := Vector2(lerpf(1.9, 0.9, f), lerpf(1.6, 0.9, f))
	m.fill_taper(Vector3(0.0, 0.8, 0.0), Vector3(0.0, -TAIL_SEG_LEN, 0.0), top_r, bot_r, MANE)
	return m


static func build_upper_leg(front: bool) -> VoxelModel:
	var m := VoxelModel.new()
	var len_up := FORE_UPPER if front else HIND_UPPER
	var top := Vector3(0.0, 2.5, 0.0)
	var bottom := Vector3(0.0, -len_up, 0.0)
	# Wide muscle mass hidden inside the body, slimming to a 2-wide limb.
	var r_top := Vector2(2.6, 2.0) if front else Vector2(3.4, 2.0)
	var r_bot := Vector2(1.5, 1.3) if front else Vector2(1.55, 1.3)
	m.fill_sdf(Vector3(-5, bottom.y - 3, -4), Vector3(5, top.y + 3, 4), func(p: Vector3) -> float:
		var d := VoxelModel.sd_taper(p, top, bottom, r_top, r_bot)
		return maxf(d, -(p.y - bottom.y - 1.0)), COAT)
	m.recolor(func(p: Vector3i, _c: Color) -> Color:
		return _coat_for_height(14.0 + (p.y + 0.5) * 0.4))
	return m


static func build_lower_leg(front: bool) -> VoxelModel:
	var m := VoxelModel.new()
	var len_low := FORE_LOWER if front else HIND_LOWER
	# Knee / hock cap, then the slender cannon with a fetlock ball at its foot.
	m.fill_taper(Vector3(0.0, 1.2, 0.0), Vector3(0.0, -len_low * 0.5, 0.0), Vector2(1.9, 1.3),
			Vector2(1.25, 1.2), COAT)
	m.fill_taper(Vector3(0.0, -len_low * 0.3, 0.0), Vector3(0.0, -len_low - 0.5, 0.0),
			Vector2(1.25, 1.2), Vector2(1.7, 1.6), COAT)
	m.recolor(func(p: Vector3i, _c: Color) -> Color:
		var y := p.y + 0.5
		if y < -len_low * 0.5:
			return SOCK
		return _coat_for_height(13.0 + y * 0.5))
	return m


static func build_hoof() -> VoxelModel:
	var m := VoxelModel.new()
	# Pastern angled slightly forward, then the hoof capsule flat on the ground.
	m.fill_taper(Vector3(0.0, 0.6, 0.0), Vector3(0.6, -1.6, 0.0), Vector2(1.5, 1.4),
			Vector2(1.5, 1.5), SOCK)
	m.fill_box(Vector3(-1.4, -HOOF_LEN, -1.9), Vector3(2.4, -1.4, 1.9), HOOF)
	m.fill_box(Vector3(-0.6, -1.4, -1.5), Vector3(1.6, -0.9, 1.5), SOCK)
	return m
