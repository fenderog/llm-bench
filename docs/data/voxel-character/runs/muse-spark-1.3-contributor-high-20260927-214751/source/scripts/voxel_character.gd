class_name VoxelCharacter
extends Node3D
## Builds a blocky voxel runner out of boxes and animates it procedurally.
## The node itself is rotated by the player to face the run direction;
## the inner "offset" node handles lean, bob and landing squash.

var offset: Node3D
var leg_l: Node3D
var leg_r: Node3D
var arm_l: Node3D
var arm_r: Node3D

var phase := 0.0
var idle_t := 0.0
var squash := 0.0
var mats: Dictionary = {}


func _ready() -> void:
	_build()


func _get_mat(key: String, color: Color) -> StandardMaterial3D:
	if mats.has(key):
		return mats[key] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.85
	mats[key] = m
	return m


func _box(parent: Node3D, size: Vector3, pos: Vector3, key: String, color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _get_mat(key, color)
	mi.mesh = bm
	mi.position = pos
	parent.add_child(mi)
	return mi


func _pivot(parent: Node3D, pos: Vector3) -> Node3D:
	var p := Node3D.new()
	p.position = pos
	parent.add_child(p)
	return p


func _build() -> void:
	offset = Node3D.new()
	add_child(offset)
	var skin := Color(0.96, 0.76, 0.58)
	var shirt := Color(0.15, 0.59, 0.65)
	var pants := Color(0.20, 0.28, 0.55)
	var shoe_c := Color(0.85, 0.27, 0.27)
	var hair := Color(0.30, 0.20, 0.12)
	var dark := Color(0.08, 0.08, 0.10)
	# Legs (pivots at the hips so they swing).
	leg_l = _pivot(offset, Vector3(-0.15, 0.58, 0.0))
	leg_r = _pivot(offset, Vector3(0.15, 0.58, 0.0))
	for leg in [leg_l, leg_r]:
		var node := leg as Node3D
		_box(node, Vector3(0.24, 0.46, 0.26), Vector3(0, -0.23, 0), "pants", pants)
		_box(node, Vector3(0.26, 0.14, 0.36), Vector3(0, -0.51, 0.04), "shoe", shoe_c)
	# Torso with a zipper stripe and a little backpack.
	_box(offset, Vector3(0.62, 0.56, 0.36), Vector3(0, 0.87, 0), "shirt", shirt)
	_box(offset, Vector3(0.18, 0.40, 0.02), Vector3(0, 0.87, 0.19), "stripe", Color(1.0, 0.85, 0.25))
	_box(offset, Vector3(0.42, 0.40, 0.16), Vector3(0, 0.90, -0.26), "pack", Color(0.85, 0.45, 0.20))
	# Arms (pivots at the shoulders).
	arm_l = _pivot(offset, Vector3(-0.41, 1.10, 0.0))
	arm_r = _pivot(offset, Vector3(0.41, 1.10, 0.0))
	for arm in [arm_l, arm_r]:
		var anode := arm as Node3D
		_box(anode, Vector3(0.18, 0.40, 0.20), Vector3(0, -0.20, 0), "shirt", shirt)
		_box(anode, Vector3(0.17, 0.16, 0.19), Vector3(0, -0.47, 0), "skin", skin)
	# Head, hair, eyes and a red cap brim.
	_box(offset, Vector3(0.48, 0.44, 0.44), Vector3(0, 1.37, 0), "skin", skin)
	_box(offset, Vector3(0.52, 0.16, 0.48), Vector3(0, 1.63, 0), "hair", hair)
	_box(offset, Vector3(0.52, 0.34, 0.10), Vector3(0, 1.48, -0.22), "hair", hair)
	_box(offset, Vector3(0.09, 0.12, 0.03), Vector3(-0.11, 1.39, 0.225), "dark", dark)
	_box(offset, Vector3(0.09, 0.12, 0.03), Vector3(0.11, 1.39, 0.225), "dark", dark)
	_box(offset, Vector3(0.50, 0.08, 0.30), Vector3(0, 1.68, 0.30), "cap", Color(0.85, 0.25, 0.25))


func land() -> void:
	## Called by the player on landing to trigger a squash-and-stretch pop.
	squash = 1.0


func animate(delta: float, run_ratio: float, on_floor: bool) -> void:
	var r := clampf(run_ratio, 0.0, 1.0)
	idle_t += delta
	squash = maxf(0.0, squash - delta * 4.0)
	if on_floor and r > 0.05:
		phase += delta * (7.0 + 7.0 * r)
	var swing := sin(phase)
	var amp := lerpf(0.06, 0.95, r)
	var k := minf(1.0, delta * 10.0)
	if not on_floor:
		# Airborne: tuck the legs, throw the arms up, lean forward.
		leg_l.rotation.x = lerpf(leg_l.rotation.x, -0.55, k)
		leg_r.rotation.x = lerpf(leg_r.rotation.x, 0.40, k)
		arm_l.rotation.x = lerpf(arm_l.rotation.x, -2.4, minf(1.0, delta * 6.0))
		arm_r.rotation.x = lerpf(arm_r.rotation.x, -2.4, minf(1.0, delta * 6.0))
		offset.rotation.x = lerpf(offset.rotation.x, 0.28, minf(1.0, delta * 6.0))
		offset.position.y = lerpf(offset.position.y, 0.0, minf(1.0, delta * 8.0))
	else:
		# Grounded: swing limbs, bob, lean into the run; breathe when idle.
		leg_l.rotation.x = swing * amp
		leg_r.rotation.x = -swing * amp
		arm_l.rotation.x = -swing * amp * 0.85
		arm_r.rotation.x = swing * amp * 0.85
		arm_l.rotation.z = 0.08
		arm_r.rotation.z = -0.08
		offset.position.y = abs(cos(phase)) * 0.09 * r + sin(idle_t * 2.2) * 0.015
		offset.rotation.x = lerpf(0.02, 0.24, r)
	var s := squash
	offset.scale = Vector3(1.0 + 0.18 * s, 1.0 - 0.22 * s, 1.0 + 0.18 * s)
