extends SceneTree
## Runtime checks of the rendering prototype, independent from the Python game.
const Data = preload("res://scripts/farm_data.gd")
var checks := 0
var failures := 0

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error("CHECK FAILED: " + message)

func run() -> void:
	var packed := load("res://scenes/main.tscn") as PackedScene
	check(packed != null, "Main scene loads")
	if packed == null:
		quit(1)
		return
	var view = packed.instantiate()
	root.add_child(view)
	await process_frame
	await physics_frame
	check(view.reference.columns == 100 and view.reference.rows == 80, "Original map dimensions")
	check(view.model_roots.size() == 5, "Five building models")
	check(view.layout.fields.size() == 3, "Three field sizes")
	for index in range(view.model_roots.size()):
		var record: Dictionary = view.layout.buildings[index]
		var definition: Dictionary = view.reference.buildings[record.type]
		check(view.model_roots[index].get_meta("logical_size") ==
			Vector2i(int(definition.width), int(definition.height)), "Footprint: " + str(record.type))
	check(Data.world_to_tile(Vector3(13.8, 7, 26.4), 100, 80) == Vector2i(13, 26), "World to tile conversion")
	check(Data.tile_center(Vector2i(13, 26)) == Vector3(13.5, 0, 26.5), "Tile center conversion")
	check(Data.world_to_tile(Vector3(-0.01, 0, 4), 100, 80) == Vector2i(-1, -1), "Negative boundary")
	check(Data.world_to_tile(Vector3(100, 0, 4), 100, 80) == Vector2i(-1, -1), "Right boundary")
	var rig = view.rig
	rig.orbit(Vector2(720, 1000))
	check(is_equal_approx(rig.yaw_degrees, 35.0), "360-degree orbit wraps")
	check(is_equal_approx(rig.pitch_degrees, 60.0), "Maximum tilt")
	rig.orbit(Vector2(-800, -1000))
	check(rig.yaw_degrees >= 0 and rig.yaw_degrees < 360, "Negative yaw wraps")
	check(is_equal_approx(rig.pitch_degrees, 35.0), "Minimum tilt")
	rig.zoom_by(0.0001)
	check(is_equal_approx(rig.zoom_size, 14.0), "Minimum zoom")
	rig.zoom_by(100000)
	check(is_equal_approx(rig.zoom_size, 120.0), "Maximum zoom")
	rig.pan(Vector2(100000, 100000))
	check(rig.focus.x >= 0 and rig.focus.x <= 100 and rig.focus.z >= 0 and rig.focus.z <= 80, "Pan boundaries")
	rig.reset_view()
	check(is_equal_approx(rig.zoom_size, 52.0) and is_equal_approx(rig.pitch_degrees, 50.0), "Reset")
	check(rig.camera.position.y > 50.0, "No ground-level camera")
	for yaw: float in [0, 90, 180, 270]:
		rig.yaw_degrees = yaw
		rig.update_pose()
		var point := Data.tile_center(Vector2i(31, 24))
		var projected: Vector2 = rig.camera.unproject_position(point)
		check(rig.ground_tile(projected, 100, 80) == Vector2i(31, 24), "Ray/tile roundtrip at yaw " + str(yaw))
	rig.reset_view()
	await physics_frame
	var warehouse_point := Vector3(27.5, 1.2, 18.0)
	view.select_at(rig.camera.unproject_position(warehouse_point))
	check(not view.selected_building.is_empty() and view.selected_building.type == "warehouse", "3D building ray selection")
	check(view.selection.visible, "Selection marker")
	var previous_tile: Vector2i = view.selected_tile
	var panel_click := InputEventMouseButton.new()
	panel_click.position = Vector2(50, 60)
	panel_click.button_index = MOUSE_BUTTON_LEFT
	panel_click.pressed = true
	root.push_input(panel_click, true)
	await physics_frame
	check(view.selected_tile == previous_tile, "HUD clicks do not fall through into farm")
	panel_click.pressed = false
	root.push_input(panel_click, true)
	view.select_at(Vector2(-10000, -10000))
	check(view.selected_tile == Vector2i(-1, -1), "Selection outside farm clears")
	view.toggle_demo()
	var before: Vector3 = view.tractor_model.position
	view.advance_demo(1.0)
	check(not before.is_equal_approx(view.tractor_model.position), "Demo tractor moves")
	check(view.roads.has(Data.world_to_tile(view.tractor_model.position, 100, 80)), "Demo tractor stays on road")
	view.advance_demo(100.0)
	check(view.roads.has(Data.world_to_tile(view.tractor_model.position, 100, 80)), "Demo loop stays on road")
	var toggle := InputEventKey.new()
	toggle.keycode = KEY_G
	toggle.pressed = true
	var was_visible: bool = view.grid.visible
	view._unhandled_input(toggle)
	check(view.grid.visible != was_visible, "Grid key toggle")
	check(view.grid_toggle.button_pressed == view.grid.visible, "Grid HUD stays in sync")
	var wheel := InputEventMouseButton.new()
	wheel.button_index = MOUSE_BUTTON_WHEEL_UP
	wheel.pressed = true
	rig._unhandled_input(wheel)
	check(rig.zoom_size < 52.0, "Wheel input zooms")
	var motion := InputEventMouseMotion.new()
	motion.button_mask = MOUSE_BUTTON_MASK_MIDDLE
	motion.relative = Vector2(40, 15)
	var previous_yaw: float = rig.yaw_degrees
	rig._unhandled_input(motion)
	check(not is_equal_approx(rig.yaw_degrees, previous_yaw), "Middle drag input orbits")
	motion.button_mask = MOUSE_BUTTON_MASK_RIGHT
	var previous_focus: Vector3 = rig.focus
	rig._unhandled_input(motion)
	check(not previous_focus.is_equal_approx(rig.focus), "Right drag input pans")
	check(view.selection_label.text.length() > 0 and view.camera_label.text.length() > 0, "HUD status")
	rig.reset_view()
	view.grid_toggle.button_pressed = false
	view.tractor_model.position = view.route[0].lerp(view.route[1], 0.5)
	view.selected_tile = Vector2i(27, 18)
	view.selected_building = view.layout.buildings[2]
	view.selection.visible = true
	view.selection.position = Data.tile_center(view.selected_tile)
	view.update_selection_label()
	if OS.get_cmdline_user_args().has("--capture"):
		await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		var result := image.save_png(ProjectSettings.globalize_path("res://../tmp/farmgame-3d-preview.png"))
		check(result == OK, "Rendered preview saved to isolated worktree tmp")
	print("3D CHECKS: %d passed, %d failed" % [checks - failures, failures])
	view.queue_free()
	await process_frame
	quit(0 if failures == 0 else 1)
