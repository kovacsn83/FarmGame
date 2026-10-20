extends RefCounted
## col -> +X, row -> +Z, up -> +Y. One logical tile = one Godot metre.
## No player-save reads/writes and no network APIs.

static func read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Missing prototype fixture: " + path)
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_error("Invalid prototype fixture: " + path)
		return {}
	return parsed

static func tile_center(tile: Vector2i) -> Vector3:
	return Vector3(tile.x + 0.5, 0.0, tile.y + 0.5)

static func world_to_tile(point: Vector3, columns: int, rows: int) -> Vector2i:
	var tile := Vector2i(floori(point.x), floori(point.z))
	if tile.x < 0 or tile.y < 0 or tile.x >= columns or tile.y >= rows:
		return Vector2i(-1, -1)
	return tile

static func building_at(tile: Vector2i, buildings: Array, catalog: Dictionary) -> Dictionary:
	for building: Dictionary in buildings:
		var definition: Dictionary = catalog[building.type]
		if tile.x >= int(building.col) and tile.x < int(building.col + definition.width) \
			and tile.y >= int(building.row) and tile.y < int(building.row + definition.height):
			return building
	return {}

static func road_tiles(layout: Dictionary) -> Dictionary:
	var result := {}
	for segment: Dictionary in layout.road_segments:
		var start := Vector2i(int(segment.from[0]), int(segment.from[1]))
		var finish := Vector2i(int(segment.to[0]), int(segment.to[1]))
		var step := Vector2i(signi(finish.x - start.x), signi(finish.y - start.y))
		var tile := start
		result[tile] = true
		while tile != finish:
			tile += step
			result[tile] = true
	return result
