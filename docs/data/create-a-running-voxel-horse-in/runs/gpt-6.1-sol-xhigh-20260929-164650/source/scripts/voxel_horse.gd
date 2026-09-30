extends Node3D
class_name VoxelHorse

const COAT := Color("934f30")
const LIGHT_COAT := Color("ab633c")
const DARK_COAT := Color("713d2b")
const CREAM := Color("f3dfb8")
const MANE := Color("382f2a")
const HOOF := Color("3b3833")

var body: Node3D
var neck: Node3D
var tail: Node3D
var hips: Array[Node3D] = []
var knees: Array[Node3D] = []
var tail_sections: Array[Node3D] = []
var materials: Dictionary = {}
var flash_time := 0.0
var phase := 0.0

func _ready() -> void:
	body = Node3D.new()
	add_child(body)
	# A stepped, full-bodied silhouette. Every detail is a little wooden voxel.
	block(body, Vector3(0, 1.48, 0), Vector3(.86, .75, 1.72), COAT)
	block(body, Vector3(0, 1.72, .03), Vector3(.78, .34, 1.55), LIGHT_COAT)
	block(body, Vector3(0, 1.19, -.03), Vector3(.70, .28, 1.4), DARK_COAT)
	block(body, Vector3(0, 1.48, .72), Vector3(.92, .75, .57), COAT)
	block(body, Vector3(0, 1.53, -.67), Vector3(.81, .81, .51), LIGHT_COAT)
	# Irregular cream pinto patches on both flanks.
	for side in [-1.0, 1.0]:
		block(body, Vector3(side * .439, 1.54, .30), Vector3(.025, .41, .57), CREAM)
		block(body, Vector3(side * .444, 1.67, .05), Vector3(.025, .30, .25), CREAM)
		block(body, Vector3(side * .449, 1.37, .47), Vector3(.025, .21, .24), CREAM.darkened(.04))
		block(body, Vector3(side * .414, 1.68, -.70), Vector3(.025, .19, .27), COAT.darkened(.06))
	block(body, Vector3(.10, 1.907, .27), Vector3(.45, .015, .50), CREAM)
	# Neck leans naturally into the stride.
	neck = Node3D.new()
	neck.position = Vector3(0, 1.69, -.73)
	body.add_child(neck)
	block(neck, Vector3(0, .37, -.22), Vector3(.56, 1.04, .57), LIGHT_COAT, Vector3(-.43, 0, 0))
	block(neck, Vector3(0, .66, -.35), Vector3(.46, .55, .47), COAT, Vector3(-.38, 0, 0))
	# A long face, a white blaze, and a pale velvet muzzle.
	block(neck, Vector3(0, .92, -.59), Vector3(.46, .49, .64), LIGHT_COAT, Vector3(.13, 0, 0))
	block(neck, Vector3(0, .77, -.93), Vector3(.40, .33, .49), COAT, Vector3(.12, 0, 0))
	block(neck, Vector3(0, .745, -1.125), Vector3(.415, .265, .17), CREAM)
	block(neck, Vector3(0, .98, -.841), Vector3(.14, .31, .025), CREAM)
	block(neck, Vector3(0, .876, -.966), Vector3(.14, .025, .23), CREAM)
	for side in [-1.0, 1.0]:
		block(neck, Vector3(side * .179, 1.255, -.39), Vector3(.14, .27, .17), COAT, Vector3(-.12, 0, side * -.12))
		block(neck, Vector3(side * .18, 1.27, -.484), Vector3(.075, .17, .02), DARK_COAT)
		block(neck, Vector3(side * .237, 1.01, -.676), Vector3(.025, .082, .10), MANE)
		block(neck, Vector3(side * .254, 1.032, -.70), Vector3(.014, .028, .025), CREAM)
		block(neck, Vector3(side * .215, .782, -1.104), Vector3(.015, .052, .073), DARK_COAT)
	# The mane is built from staggered cubes, not a flat slab.
	for i in 7:
		var t := float(i) / 6.0
		block(neck, Vector3(0, .03 + t * 1.08, .065 - t * .46), Vector3(.25, .23, .22), MANE)
	block(neck, Vector3(0, 1.17, -.59), Vector3(.31, .17, .35), MANE)
	block(neck, Vector3(.035, 1.085, -.815), Vector3(.25, .15, .18), MANE)
	# Four articulated legs: upper leg, knee, cannon, sock, and hoof.
	for i in 4:
		var front := i < 2
		var side := -1.0 if i % 2 == 0 else 1.0
		var hip := Node3D.new()
		hip.position = Vector3(side * .32, 1.32, -.64 if front else .66)
		body.add_child(hip)
		hips.append(hip)
		block(hip, Vector3(0, -.25, 0), Vector3(.24 if front else .29, .58, .30), COAT if front else DARK_COAT)
		block(hip, Vector3(0, -.51, 0), Vector3(.22, .21, .24), LIGHT_COAT)
		var knee := Node3D.new()
		knee.position.y = -.55
		hip.add_child(knee)
		knees.append(knee)
		block(knee, Vector3(0, -.235, 0), Vector3(.16, .48, .18), COAT)
		block(knee, Vector3(0, -.435, 0), Vector3(.18, .25, .20), CREAM)
		block(knee, Vector3(0, -.595, -.035), Vector3(.25, .16, .31), HOOF)
		block(knee, Vector3(0, -.522, -.075), Vector3(.25, .055, .19), HOOF.lightened(.12))
	# A long, swishing, jointed tail.
	tail = Node3D.new()
	tail.position = Vector3(0, 1.72, 1.01)
	body.add_child(tail)
	for i in 4:
		var section := Node3D.new()
		section.position = Vector3(0, -.16 if i > 0 else 0.0, .22 if i > 0 else 0.0)
		(tail if i == 0 else tail_sections[i - 1]).add_child(section)
		block(section, Vector3(0, -.12, .12), Vector3(.24 + i * .035, .30, .34), MANE)
		tail_sections.append(section)

func block(parent: Node3D, pos: Vector3, size: Vector3, color: Color, rotation := Vector3.ZERO) -> MeshInstance3D:
	var key := color.to_html()
	if not materials.has(key):
		var mat := StandardMaterial3D.new()
		mat.albedo_color = color
		mat.roughness = .94
		materials[key] = mat
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh.material = materials[key]
	var piece := MeshInstance3D.new()
	piece.mesh = mesh
	piece.position = pos
	piece.rotation = rotation
	parent.add_child(piece)
	return piece

func animate(delta: float, pace: float, airborne: bool) -> void:
	phase += delta * pace
	var strength := .45 if airborne else 1.0
	body.position.y = .085 + sin(phase * 2.0) * .065 * strength
	body.rotation.x = sin(phase) * .035 * strength
	neck.rotation.x = sin(phase + .6) * .045
	var offsets := [0.0, .8, 2.8, 3.5]
	for i in 4:
		var p: float = phase + offsets[i]
		hips[i].rotation.x = sin(p) * .78 * strength + (-.20 if airborne and i < 2 else .0)
		knees[i].rotation.x = (-maxf(0, cos(p + .45)) * 1.15 + .12) * strength
		tail.rotation.z = sin(phase * .5) * .12
	for i in tail_sections.size():
		tail_sections[i].rotation.x = sin(phase * .75 - i * .6) * .09
		tail_sections[i].rotation.z = sin(phase * .6 - i * .8) * .08
	if flash_time > 0:
		flash_time -= delta
		visible = fmod(flash_time, .18) > .055
	else:
		visible = true

func hurt() -> void:
	flash_time = 1.8
