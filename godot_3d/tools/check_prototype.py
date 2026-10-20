"""Static contract checks: demo layout, source parity and isolation."""
import json
import unittest
from pathlib import Path
from export_reference import reference

PROJECT = Path(__file__).resolve().parents[1]


class PrototypeContractTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((PROJECT / "data/reference.json").read_text(encoding="utf-8"))
        self.layout = json.loads((PROJECT / "data/demo_layout.json").read_text(encoding="utf-8"))

    def road_tiles(self):
        result = set()
        for segment in self.layout["road_segments"]:
            a, b = segment["from"], segment["to"]
            self.assertTrue(a[0] == b[0] or a[1] == b[1])
            for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1):
                for z in range(min(a[1], b[1]), max(a[1], b[1]) + 1):
                    result.add((x, z))
        return result

    def test_reference_matches_python_source_without_overriding_it(self):
        self.assertEqual(self.catalog, reference())

    def test_buildings_are_nonoverlapping_in_bounds_and_have_road_access(self):
        occupied = set()
        roads = self.road_tiles()
        for record in self.layout["buildings"]:
            definition = self.catalog["buildings"][record["type"]]
            col, row = record["col"], record["row"]
            width, height = definition["width"], definition["height"]
            tiles = {(x, z) for x in range(col, col + width) for z in range(row, row + height)}
            self.assertFalse(occupied & tiles)
            self.assertFalse(roads & tiles)
            self.assertTrue(all(0 <= x < self.catalog["columns"] and 0 <= z < self.catalog["rows"] for x, z in tiles))
            border = {(x + dx, z + dz) for x, z in tiles for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))} - tiles
            self.assertTrue(border & roads, record["type"])
            occupied |= tiles

    def test_demo_route_uses_existing_fixture_roads_only(self):
        roads = self.road_tiles()
        route = self.layout["demo_route"]
        for a, b in zip(route, route[1:] + route[:1]):
            self.assertTrue(a[0] == b[0] or a[1] == b[1])
            for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1):
                for z in range(min(a[1], b[1]), max(a[1], b[1]) + 1):
                    self.assertIn((x, z), roads)

    def test_no_game_data_writes_network_or_external_models_in_runtime(self):
        for script in (PROJECT / "scripts").glob("*.gd"):
            text = script.read_text(encoding="utf-8")
            for forbidden in ("FileAccess.WRITE", "user://", "HTTPRequest", "HTTPClient", "Railway", "save_game(", ".glb", ".fbx"):
                self.assertNotIn(forbidden, text, str(script))

    def test_project_is_separately_openable_and_has_separate_user_directory(self):
        text = (PROJECT / "project.godot").read_text(encoding="utf-8")
        self.assertIn('run/main_scene="res://scenes/main.tscn"', text)
        self.assertIn('config/custom_user_dir_name="FarmGame3DPrototype"', text)
        self.assertTrue((PROJECT / "scenes/main.tscn").exists())


if __name__ == "__main__":
    unittest.main()
