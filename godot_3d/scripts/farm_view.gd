extends Node3D
## Rendering laboratory only. None of the original simulation systems is replaced.
const Data = preload("res://scripts/farm_data.gd")
const Models = preload("res://scripts/primitive_models.gd")
const CameraRig = preload("res://scripts/camera_rig.gd")
var reference: Dictionary
var layout: Dictionary
var roads: Dictionary
var rig: Node3D
var grid: MeshInstance3D
var selection: Node3D
var selected_tile := Vector2i(-1, -1)
var selected_building: Dictionary = {}
var tractor_model: Node3D
var route: Array[Vector3] = []
var route_index := 1
var demo_running := true
var pending_pick := Vector2(-1, -1)
var camera_label: Label
var selection_label: Label
var pause_button: Button
var grid_toggle: CheckButton
var model_roots: Array[Node3D] = []

func _ready() -> void:
	reference = Data.read_json("res://data/reference.json")
	layout = Data.read_json("res://data/demo_layout.json")
	if reference.is_empty() or layout.is_empty():
		return
	roads = Data.road_tiles(layout)
	build_world()
	rig = CameraRig.new()
	rig.map_size = Vector2(reference.columns, reference.rows)
	add_child(rig)
	build_ui()

func add_collision(parent: Node3D, size: Vector3, center: Vector3, building_index: int = -1) -> void:
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	shape.position = center
	body.add_child(shape)
	if building_index >= 0:
		body.set_meta("building_index", building_index)
	parent.add_child(body)

func build_world() -> void:
	var columns := float(reference.columns)
	var rows := float(reference.rows)
	Models.box(self, Vector3(columns, 0.3, rows), Vector3(columns / 2, -0.15, rows / 2), Color("71a057"))
	add_collision(self, Vector3(columns, 0.3, rows), Vector3(columns / 2, -0.15, rows / 2))
	for tile: Vector2i in roads:
		Models.box(self, Vector3(0.98, 0.06, 0.98), Data.tile_center(tile) + Vector3(0, 0.03, 0), Color("bfa67b"))
	for index in range(layout.buildings.size()):
		var record: Dictionary = layout.buildings[index]
		var definition: Dictionary = reference.buildings[record.type]
		var model := Models.building(record.type, definition, reference)
		model.position = Vector3(record.col, 0, record.row)
		model.set_meta("logical_size", Vector2i(int(definition.width), int(definition.height)))
		add_child(model)
		model_roots.append(model)
		# Selection volume only; no gameplay collision or placement implementation.
		add_collision(model, Vector3(definition.width, 3.0, definition.height),
			Vector3(definition.width / 2.0, 1.5, definition.height / 2.0), index)
	for field: Dictionary in layout.fields:
		var definition: Dictionary = reference.fields[field.type]
		var width := int(definition.width)
		var height := int(definition.height)
		Models.box(self, Vector3(width, 0.08, height), Vector3(field.col + width / 2.0, 0.04, field.row + height / 2.0), Color("876143"))
		for row in range(height):
			for col in range(width):
				var pos := Vector3(field.col + col + 0.5, 0.3, field.row + row + 0.5)
				Models.box(self, Vector3(0.12, 0.5, 0.12), pos, Color("4b7f35"))
				var leaf := Models.box(self, Vector3(0.5, 0.1, 0.18), pos + Vector3(0, 0.1, 0), Color("8dbd4d"))
				leaf.rotation.y = float((row + col) % 3) * 0.6
	build_grid()
	selection = Node3D.new()
	selection.name = "SelectedLogicalTile"
	add_child(selection)
	for edge in [Vector3(0, 0.18, -0.5), Vector3(0, 0.18, 0.5)]:
		Models.box(selection, Vector3(1.0, 0.06, 0.06), edge, Color("ffe779"))
	for edge in [Vector3(-0.5, 0.18, 0), Vector3(0.5, 0.18, 0)]:
		Models.box(selection, Vector3(0.06, 0.06, 1.0), edge, Color("ffe779"))
	selection.visible = false
	tractor_model = Models.tractor()
	add_child(tractor_model)
	for point: Array in layout.demo_route:
		route.append(Data.tile_center(Vector2i(int(point[0]), int(point[1]))))
	tractor_model.position = route[0].lerp(route[1], 0.5)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -35, 0)
	sun.light_energy = 0.65
	sun.shadow_enabled = true
	add_child(sun)
	var environment_node := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("b4d2df")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d5e1d5")
	environment.ambient_light_energy = 0.3
	environment_node.environment = environment
	add_child(environment_node)

func build_grid() -> void:
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	for col in range(int(reference.columns) + 1):
		mesh.surface_add_vertex(Vector3(col, 0.09, 0))
		mesh.surface_add_vertex(Vector3(col, 0.09, reference.rows))
	for row in range(int(reference.rows) + 1):
		mesh.surface_add_vertex(Vector3(0, 0.09, row))
		mesh.surface_add_vertex(Vector3(reference.columns, 0.09, row))
	mesh.surface_end()
	grid = MeshInstance3D.new()
	grid.mesh = mesh
	var mat := Models.material(Color("456e45"))
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	grid.material_override = mat
	grid.visible = false
	add_child(grid)

func panel(parent: Control, position_value: Vector2, width: float) -> VBoxContainer:
	var background := PanelContainer.new()
	background.position = position_value
	background.custom_minimum_size.x = width
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.14, 0.16, 0.94)
	style.set_corner_radius_all(10)
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 14
	style.content_margin_bottom = 14
	background.add_theme_stylebox_override("panel", style)
	parent.add_child(background)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 8)
	background.add_child(content)
	return content

func label(parent: Control, text: String, font_size: int = 18) -> Label:
	var item := Label.new()
	item.text = text
	item.add_theme_font_size_override("font_size", font_size)
	item.add_theme_color_override("font_color", Color("edf3e8"))
	parent.add_child(item)
	return item

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	var left := panel(root, Vector2(22, 22), 410)
	label(left, "FARMGAME / 3D LAB", 27)
	label(left, "Megjelenítési kísérlet • nem teljes játék", 16)
	label(left, "100 × 80 csempe • eredeti épületméretek", 16)
	camera_label = label(left, "", 16)
	var controls := HBoxContainer.new()
	left.add_child(controls)
	var reset := Button.new()
	reset.text = "Kamera alaphelyzet"
	reset.pressed.connect(rig.reset_view)
	controls.add_child(reset)
	var grid_button := CheckButton.new()
	grid_toggle = grid_button
	grid_button.text = "Rács (G)"
	grid_button.toggled.connect(func(value: bool): grid.visible = value)
	controls.add_child(grid_button)
	var details := panel(root, Vector2(22, 270), 410)
	label(details, "KIJELÖLÉS", 20)
	selection_label = label(details, "Bal kattintás: válassz csempét vagy épületet.", 16)
	pause_button = Button.new()
	pause_button.text = "Demótraktor megállítása"
	pause_button.pressed.connect(toggle_demo)
	details.add_child(pause_button)
	label(details, "A traktor csak bemutató útvonalon mozog.\nNincs termelés, vásárlás vagy feladatvégzés.", 15)
	var footer := PanelContainer.new()
	footer.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	footer.offset_top = -74
	root.add_child(footer)
	var help := label(footer, "WASD / nyilak: mozgatás   •   jobb egér húzása: pásztázás   •   görgő: zoom\nKözépső egér húzása: forgatás / döntés   •   Q/E: forgatás   •   R/Home: alaphelyzet   •   G: rács   •   Esc: kilépés", 17)
	help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label(left, "Referencia: FarmGame " + str(reference.game_version), 14)

func toggle_demo() -> void:
	demo_running = not demo_running
	pause_button.text = "Demótraktor megállítása" if demo_running else "Demótraktor indítása"

func advance_demo(delta: float) -> void:
	# Fixed visualization speed, NOT FarmGame vehicle speed or pathfinding.
	var remaining := delta * 3.0
	while remaining > 0.0:
		var target := route[route_index]
		var difference := target - tractor_model.position
		var distance := difference.length()
		if distance <= remaining:
			tractor_model.position = target
			remaining -= distance
			route_index = (route_index + 1) % route.size()
		else:
			tractor_model.position += difference.normalized() * remaining
			remaining = 0.0
		if distance > 0.001:
			tractor_model.rotation.y = atan2(-difference.x, -difference.z)

func select_at(screen_point: Vector2) -> void:
	var camera: Camera3D = rig.camera
	var origin := camera.project_ray_origin(screen_point)
	var query := PhysicsRayQueryParameters3D.create(origin, origin + camera.project_ray_normal(screen_point) * 350.0)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	selected_building = {}
	if hit.is_empty():
		selected_tile = Vector2i(-1, -1)
	else:
		selected_tile = Data.world_to_tile(hit.position, int(reference.columns), int(reference.rows))
		if hit.collider.has_meta("building_index"):
			selected_building = layout.buildings[hit.collider.get_meta("building_index")]
		else:
			selected_building = Data.building_at(selected_tile, layout.buildings, reference.buildings)
	selection.visible = selected_tile.x >= 0
	if selection.visible:
		selection.position = Data.tile_center(selected_tile)
	update_selection_label()

func update_selection_label() -> void:
	var text := "Nincs kijelölt csempe."
	if selected_tile.x >= 0:
		text = "Sor: %d   Oszlop: %d\n3D: X=%d, Z=%d" % [selected_tile.y, selected_tile.x, selected_tile.x, selected_tile.y]
		if not selected_building.is_empty():
			var definition: Dictionary = reference.buildings[selected_building.type]
			text += "\n%s\nTelek: %d × %d csempe" % [definition.name, definition.width, definition.height]
		else:
			text += "\nÚt" if roads.has(selected_tile) else "\nFarmterület / veteményes"
	selection_label.text = text

func _physics_process(_delta: float) -> void:
	if pending_pick.x >= 0:
		select_at(pending_pick)
		pending_pick = Vector2(-1, -1)

func _process(delta: float) -> void:
	if rig == null:
		return
	if demo_running:
		advance_demo(delta)
	camera_label.text = "Irány: %.0f°  •  Döntés: %.0f°\nZoom: %.1f  •  Középpont: %.1f, %.1f" % [rig.yaw_degrees, rig.pitch_degrees, rig.zoom_size, rig.focus.x, rig.focus.z]

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pending_pick = event.position
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_G: grid_toggle.button_pressed = not grid.visible
		if event.keycode == KEY_ESCAPE: get_tree().quit()
