extends Node3D
## Presentation-only orbit camera. No simulation time or game rules.
var camera: Camera3D
var focus := Vector3(28.0, 0.0, 24.0)
var yaw_degrees := 35.0
var pitch_degrees := 50.0
var zoom_size := 52.0
var map_size := Vector2(100.0, 80.0)

func _ready() -> void:
	camera = Camera3D.new()
	camera.name = "FarmCamera"
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.near = 0.1
	camera.far = 350.0
	camera.current = true
	add_child(camera)
	update_pose()

func reset_view() -> void:
	focus = Vector3(28.0, 0.0, 24.0)
	yaw_degrees = 35.0
	pitch_degrees = 50.0
	zoom_size = 52.0
	update_pose()

func orbit(delta: Vector2) -> void:
	yaw_degrees = fposmod(yaw_degrees + delta.x, 360.0)
	pitch_degrees = clampf(pitch_degrees + delta.y, 35.0, 60.0)
	update_pose()

func zoom_by(factor: float) -> void:
	zoom_size = clampf(zoom_size * factor, 14.0, 120.0)
	update_pose()

func pan(delta: Vector2) -> void:
	var angle := deg_to_rad(yaw_degrees)
	var right := Vector3(cos(angle), 0.0, -sin(angle))
	var forward := Vector3(-sin(angle), 0.0, -cos(angle))
	focus += right * delta.x + forward * delta.y
	update_pose()

func update_pose() -> void:
	focus.x = clampf(focus.x, 0.0, map_size.x)
	focus.z = clampf(focus.z, 0.0, map_size.y)
	focus.y = 0.0
	if camera == null:
		return
	var yaw := deg_to_rad(yaw_degrees)
	var pitch := deg_to_rad(pitch_degrees)
	var offset := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * 110.0
	camera.position = focus + offset
	camera.look_at(focus, Vector3.UP)
	camera.size = zoom_size

func ground_tile(screen_point: Vector2, columns: int, rows: int) -> Vector2i:
	var origin := camera.project_ray_origin(screen_point)
	var direction := camera.project_ray_normal(screen_point)
	var point: Variant = Plane(Vector3.UP, 0.0).intersects_ray(origin, direction)
	if point == null:
		return Vector2i(-1, -1)
	return preload("res://scripts/farm_data.gd").world_to_tile(point, columns, rows)

func _process(delta: float) -> void:
	var movement := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): movement.y += 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): movement.y -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): movement.x += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): movement.x -= 1.0
	if movement != Vector2.ZERO:
		pan(movement.normalized() * delta * zoom_size * 0.6)
	if Input.is_physical_key_pressed(KEY_Q): orbit(Vector2(-50.0 * delta, 0.0))
	if Input.is_physical_key_pressed(KEY_E): orbit(Vector2(50.0 * delta, 0.0))

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP: zoom_by(0.9)
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN: zoom_by(1.0 / 0.9)
	if event is InputEventMouseMotion:
		if event.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			orbit(Vector2(-event.relative.x * 0.3, event.relative.y * 0.2))
		elif event.button_mask & MOUSE_BUTTON_MASK_RIGHT:
			pan(Vector2(-event.relative.x, event.relative.y) * zoom_size / get_viewport().get_visible_rect().size.y)
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_R or event.keycode == KEY_HOME: reset_view()
