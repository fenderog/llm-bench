extends RefCounted
## Sparse voxel volume that can be sculpted with a few primitive fills and then
## baked into a single vertex-coloured ArrayMesh.
##
## Coordinates are continuous "voxel units": voxel (i, j, k) occupies the cube
## [i, i+1] x [j, j+1] x [k, k+1]. The fill helpers include a voxel when its
## centre lies inside the primitive.
##
## The mesher only emits faces that are exposed to air and bakes a cheap
## per-vertex ambient occlusion term plus a tiny per-voxel brightness jitter
## into the vertex colours, which is what gives the blocks their depth.

## Tangent axes for a face whose normal is along axis a: (u, v) = (a+1, a+2),
## so that u x v = +a.
const _AXIS_U := [1, 2, 0]
const _AXIS_V := [2, 0, 1]
## Brightness for ambient-occlusion levels 0 (fully boxed in) .. 3 (open).
const _AO_CURVE: Array[float] = [0.0, 0.55, 0.8, 1.0]
## Quad corners as (u, v) steps, clockwise seen from outside (Godot's front
## face) for faces pointing along +axis and -axis respectively.
const _CORNERS_POS := [[0, 0], [0, 1], [1, 1], [1, 0]]
const _CORNERS_NEG := [[0, 0], [1, 0], [1, 1], [0, 1]]

var voxels: Dictionary = {}  # Vector3i -> Color


func set_voxel(p: Vector3i, c: Color) -> void:
	voxels[p] = c


func erase_voxel(p: Vector3i) -> void:
	voxels.erase(p)


func has_voxel(p: Vector3i) -> bool:
	return voxels.has(p)


func count() -> int:
	return voxels.size()


## Copies every voxel of `other` into this model, shifted by `offset` voxels.
func merge(other: RefCounted, offset: Vector3i = Vector3i.ZERO) -> void:
	for p: Vector3i in other.voxels:
		voxels[p + offset] = other.voxels[p]


## Axis-aligned box from `lo` to `hi` (continuous voxel units).
func fill_box(lo: Vector3, hi: Vector3, c: Color) -> void:
	var x0 := int(floor(lo.x))
	var y0 := int(floor(lo.y))
	var z0 := int(floor(lo.z))
	for x in range(x0, int(ceil(hi.x)) + 1):
		var cx := x + 0.5
		if cx < lo.x or cx > hi.x:
			continue
		for y in range(y0, int(ceil(hi.y)) + 1):
			var cy := y + 0.5
			if cy < lo.y or cy > hi.y:
				continue
			for z in range(z0, int(ceil(hi.z)) + 1):
				var cz := z + 0.5
				if cz < lo.z or cz > hi.z:
					continue
				voxels[Vector3i(x, y, z)] = c


func fill_ellipsoid(center: Vector3, radii: Vector3, c: Color) -> void:
	var lo := (center - radii).floor()
	var hi := (center + radii).ceil()
	for x in range(int(lo.x), int(hi.x) + 1):
		for y in range(int(lo.y), int(hi.y) + 1):
			for z in range(int(lo.z), int(hi.z) + 1):
				var d := (Vector3(x + 0.5, y + 0.5, z + 0.5) - center) / radii
				if d.length_squared() <= 1.0:
					voxels[Vector3i(x, y, z)] = c


## Tapered elliptical "bone" running from `a` to `b`. The axis has to lie in a
## constant-z plane (the horse's sagittal plane). `r_a` / `r_b` are
## (in-plane radius, lateral radius) at each end. With `flat_ends` the tube is
## cut square at both ends, otherwise the ends are rounded.
func fill_taper(a: Vector3, b: Vector3, r_a: Vector2, r_b: Vector2, c: Color,
		flat_ends: bool = false) -> void:
	var axis := Vector2(b.x - a.x, b.y - a.y)
	var len_sq := maxf(axis.length_squared(), 0.0001)
	var rmax := maxf(maxf(r_a.x, r_b.x), maxf(r_a.y, r_b.y))
	var pad := ceilf(rmax)
	var lo := Vector3(minf(a.x, b.x) - pad, minf(a.y, b.y) - pad, a.z - pad).floor()
	var hi := Vector3(maxf(a.x, b.x) + pad, maxf(a.y, b.y) + pad, a.z + pad).ceil()
	for x in range(int(lo.x), int(hi.x) + 1):
		for y in range(int(lo.y), int(hi.y) + 1):
			var rel := Vector2(x + 0.5 - a.x, y + 0.5 - a.y)
			var t := rel.dot(axis) / len_sq
			if flat_ends and (t < 0.0 or t > 1.0):
				continue
			t = clampf(t, 0.0, 1.0)
			var inplane := (rel - axis * t).length()
			var rad := r_a.lerp(r_b, t).max(Vector2(0.01, 0.01))
			var qa := inplane / rad.x
			for z in range(int(lo.z), int(hi.z) + 1):
				var dz := (z + 0.5 - a.z) / rad.y
				var q := qa * qa + dz * dz
				if q <= 1.0:
					voxels[Vector3i(x, y, z)] = c


## Fills every voxel whose centre has a non-positive value of `sdf(p: Vector3)`
## inside the box `lo`..`hi`. Combine the sd_* helpers below with smin() for
## soft, organic blends between primitives.
func fill_sdf(lo: Vector3, hi: Vector3, sdf: Callable, c: Color) -> void:
	for x in range(int(floor(lo.x)), int(ceil(hi.x)) + 1):
		for y in range(int(floor(lo.y)), int(ceil(hi.y)) + 1):
			for z in range(int(floor(lo.z)), int(ceil(hi.z)) + 1):
				if sdf.call(Vector3(x + 0.5, y + 0.5, z + 0.5)) <= 0.0:
					voxels[Vector3i(x, y, z)] = c


## Approximate signed distance to an axis-aligned ellipsoid.
static func sd_ellipsoid(p: Vector3, center: Vector3, radii: Vector3) -> float:
	var q := (p - center) / radii
	return (q.length() - 1.0) * minf(radii.x, minf(radii.y, radii.z))


## Approximate signed distance to a "squarish" ellipsoid: power 2 is a normal
## ellipsoid, larger values approach a box with chamfered edges.
static func sd_superellipsoid(p: Vector3, center: Vector3, radii: Vector3, power: float) -> float:
	var q := ((p - center) / radii).abs()
	var n := pow(pow(q.x, power) + pow(q.y, power) + pow(q.z, power), 1.0 / power)
	return (n - 1.0) * minf(radii.x, minf(radii.y, radii.z))


## Approximate signed distance to a tapered elliptical tube (see fill_taper).
static func sd_taper(p: Vector3, a: Vector3, b: Vector3, r_a: Vector2, r_b: Vector2) -> float:
	var axis := Vector2(b.x - a.x, b.y - a.y)
	var rel := Vector2(p.x - a.x, p.y - a.y)
	var t := clampf(rel.dot(axis) / maxf(axis.length_squared(), 0.0001), 0.0, 1.0)
	var inplane := (rel - axis * t).length()
	var rad := r_a.lerp(r_b, t)
	var qa := inplane / rad.x
	var qz := (p.z - a.z) / rad.y
	return (sqrt(qa * qa + qz * qz) - 1.0) * minf(rad.x, rad.y)


## Polynomial smooth minimum: a union whose seam is rounded over width `k`.
static func smin(a: float, b: float, k: float) -> float:
	var h := clampf(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
	return lerpf(b, a, h) - k * h * (1.0 - h)


## Rewrites every voxel colour with `fn(p: Vector3i, c: Color) -> Color`.
func recolor(fn: Callable) -> void:
	for p: Vector3i in voxels.keys():
		voxels[p] = fn.call(p, voxels[p])


func get_bounds() -> AABB:
	var lo := Vector3i(1 << 30, 1 << 30, 1 << 30)
	var hi := Vector3i(-(1 << 30), -(1 << 30), -(1 << 30))
	for p: Vector3i in voxels:
		lo = lo.min(p)
		hi = hi.max(p)
	return AABB(Vector3(lo), Vector3(hi - lo + Vector3i.ONE))


## Matte, vertex-coloured material shared by every voxel mesh.
static func make_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 1.0
	mat.metallic_specular = 0.2
	return mat


static func hash01(p: Vector3i) -> float:
	var h: int = (p.x * 374761393 + p.y * 668265263 + p.z * 2147483629) & 0x7fffffff
	h = ((h ^ (h >> 13)) * 1274126177) & 0x7fffffff
	return float(h % 1021) / 1020.0


func _solid(p: Vector3i) -> int:
	return 1 if voxels.has(p) else 0


## Bakes the volume into a mesh. `pivot` (in voxel units) becomes the origin of
## the mesh, `ao_strength` scales the darkening in creases and `jitter` is the
## +/- brightness variation between neighbouring voxels.
func build_mesh(voxel_size: float, pivot: Vector3 = Vector3.ZERO, ao_strength: float = 0.5,
		jitter: float = 0.05) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()
	var ao := [0, 0, 0, 0]
	var vi := 0

	for p: Vector3i in voxels:
		var base: Color = voxels[p]
		var tint := 1.0 + (hash01(p) - 0.5) * 2.0 * jitter
		for face in 6:
			var axis := face >> 1
			var positive := (face & 1) == 0
			var n := Vector3i.ZERO
			n[axis] = 1 if positive else -1
			if voxels.has(p + n):
				continue
			var u_axis: int = _AXIS_U[axis]
			var v_axis: int = _AXIS_V[axis]
			var du := Vector3i.ZERO
			var dv := Vector3i.ZERO
			du[u_axis] = 1
			dv[v_axis] = 1
			var corners: Array = _CORNERS_POS if positive else _CORNERS_NEG
			var outside := p + n
			var origin := Vector3(p)
			if positive:
				origin[axis] += 1.0
			for i in 4:
				var cu: int = corners[i][0]
				var cv: int = corners[i][1]
				var su := du * (cu * 2 - 1)
				var sv := dv * (cv * 2 - 1)
				var s1 := _solid(outside + su)
				var s2 := _solid(outside + sv)
				var s3 := _solid(outside + su + sv)
				ao[i] = 0 if (s1 == 1 and s2 == 1) else 3 - (s1 + s2 + s3)
				var shade: float = 1.0 - ao_strength * (1.0 - _AO_CURVE[ao[i]])
				shade *= tint
				verts.append((origin + Vector3(du) * cu + Vector3(dv) * cv - pivot) * voxel_size)
				normals.append(Vector3(n))
				colors.append(Color(base.r * shade, base.g * shade, base.b * shade, base.a))
			if ao[0] + ao[2] >= ao[1] + ao[3]:
				indices.append_array([vi, vi + 1, vi + 2, vi, vi + 2, vi + 3])
			else:
				indices.append_array([vi + 1, vi + 2, vi + 3, vi + 1, vi + 3, vi])
			vi += 4

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	if vi > 0:
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
