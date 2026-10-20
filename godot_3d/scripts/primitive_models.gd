extends RefCounted
## Every visible model is a built-in primitive. No gameplay state lives here.

static func material(color: Color) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.9
	return result

static func box(parent: Node3D, size: Vector3, center: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = material(color)
	instance.position = center
	parent.add_child(instance)
	return instance

static func cylinder(parent: Node3D, radius: float, height: float, center: Vector3, color: Color) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 12
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = material(color)
	instance.position = center
	parent.add_child(instance)
	return instance

static func hall(parent: Node3D, origin: Vector2, size: Vector2, wall: Color, roof_color: Color) -> void:
	var center := Vector3(origin.x + size.x / 2.0, 1.0, origin.y + size.y / 2.0)
	box(parent, Vector3(size.x, 2.0, size.y), center, wall)
	var roof := PrismMesh.new()
	roof.size = Vector3(size.x + 0.25, 0.8, size.y + 0.25)
	var top := MeshInstance3D.new()
	top.mesh = roof
	top.material_override = material(roof_color)
	top.position = center + Vector3(0, 1.4, 0)
	parent.add_child(top)
	box(parent, Vector3(1.0, 1.35, 0.06),
		Vector3(center.x, 0.68, origin.y + size.y + 0.04), Color("563f32"))
	for offset: float in [0.7, size.x - 0.7]:
		box(parent, Vector3(0.55, 0.55, 0.07),
			Vector3(origin.x + offset, 1.35, origin.y + size.y + 0.05), Color("a5dce3"))

static func fence(parent: Node3D, start: Vector2, finish: Vector2) -> void:
	var length := start.distance_to(finish)
	var center := (start + finish) / 2.0
	var horizontal := is_equal_approx(start.y, finish.y)
	var dimensions := Vector3(length, 0.09, 0.09) if horizontal else Vector3(0.09, 0.09, length)
	for height: float in [0.45, 0.85]:
		box(parent, dimensions, Vector3(center.x, height, center.y), Color("775c3e"))
	var count := maxi(1, ceili(length / 2.0))
	for index in range(count + 1):
		var point := start.lerp(finish, float(index) / count)
		box(parent, Vector3(0.12, 1.0, 0.12), Vector3(point.x, 0.5, point.y), Color("8e7450"))

static func building(kind: String, definition: Dictionary, reference: Dictionary) -> Node3D:
	var root := Node3D.new()
	root.name = "Model_" + kind
	var width := float(definition.width)
	var depth := float(definition.height)
	if kind != "farmhouse" and kind != "feed_mill":
		box(root, Vector3(width, 0.12, depth), Vector3(width / 2.0, 0.06, depth / 2.0), Color("b6b1a1"))
	match kind:
		"farmhouse":
			var body: Array = reference.farmhouse_level_one_body
			var size := Vector2(float(body[0]), float(body[1]))
			hall(root, Vector2(width - size.x, depth - size.y), size, Color("f0cf9b"), Color("b45135"))
			box(root, Vector3(1.0, 0.05, depth), Vector3(width - size.x - 0.6, 0.03, depth / 2.0), Color("c4bfa7"))
			for point: Vector2 in [Vector2(1.2, 1.3), Vector2(1.2, depth - 1.4)]:
				cylinder(root, 0.13, 1.1, Vector3(point.x, 0.55, point.y), Color("876440"))
				cylinder(root, 0.65, 1.25, Vector3(point.x, 1.65, point.y), Color("52934d"))
		"warehouse":
			hall(root, Vector2(0.2, 0.2), Vector2(width - 0.4, depth - 0.4), Color("d2bb8e"), Color("607c80"))
			box(root, Vector3(2.0, 1.45, 0.08), Vector3(width / 2.0, 0.75, depth - 0.12), Color("677a7c"))
		"garage":
			hall(root, Vector2(0.15, 0.15), Vector2(width - 0.3, depth - 0.3), Color("c1c9c2"), Color("596c73"))
			box(root, Vector3(width - 0.8, 1.6, 0.1), Vector3(width / 2.0, 0.8, depth - 0.07), Color("708d9a"))
		"processing_plant":
			hall(root, Vector2(0.2, 0.2), Vector2(width - 1.5, depth - 0.4), Color("e2d8ba"), Color("728b84"))
			cylinder(root, 0.5, 3.3, Vector3(width - 0.7, 1.65, 1.0), Color("bfc8c7"))
			cylinder(root, 0.35, 2.5, Vector3(width - 0.7, 1.25, 2.5), Color("a5b7bb"))
		"feed_mill":
			# Whole plot = 12x8. Hall occupies the bottom-left 4x4, yard is L-shaped.
			hall(root, Vector2(0.1, 4.1), Vector2(2.7, 3.8), Color("d7c99c"), Color("7c8d51"))
			for z: float in [5.0, 7.0]:
				cylinder(root, 0.48, 2.8, Vector3(3.35, 1.4, z), Color("c7cdb4"))
			var points := [Vector2(0.1, 0.1), Vector2(width - 0.1, 0.1),
				Vector2(width - 0.1, depth - 0.1), Vector2(4, depth - 0.1),
				Vector2(4, 4), Vector2(0.1, 4), Vector2(0.1, 0.1)]
			for index in range(points.size() - 1):
				fence(root, points[index], points[index + 1])
			box(root, Vector3(0.65, 0.22, 0.28), Vector3(0.8, 0.11, 0.6), Color("b39d64"))
			box(root, Vector3(0.65, 0.22, 0.28), Vector3(1.7, 0.11, 0.6), Color("73a9bd"))
	return root

static func tractor() -> Node3D:
	var root := Node3D.new()
	root.name = "DemoTractor_NOT_A_GAME_TASK"
	box(root, Vector3(0.8, 0.4, 1.35), Vector3(0, 0.55, 0), Color("c6553d"))
	box(root, Vector3(0.65, 0.55, 0.62), Vector3(0, 0.98, 0.25), Color("89bdc8"))
	box(root, Vector3(0.85, 0.1, 0.8), Vector3(0, 1.3, 0.25), Color("e3dfbf"))
	for x: float in [-0.48, 0.48]:
		for z: float in [-0.42, 0.43]:
			var wheel := cylinder(root, 0.3, 0.2, Vector3(x, 0.32, z), Color("303b3c"))
			wheel.rotation.z = PI / 2.0
	return root
