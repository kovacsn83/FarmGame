"""Export read-only 2D catalog metadata; never open a player save or backend."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from buildings import BUILDING_TYPES, FARMHOUSE_LEVELS
from constants import WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES, TILE_SIZE
from game_rules import FIELD_TYPES
from game_version import get_game_version


def reference():
    ids = ("farmhouse", "warehouse", "garage", "processing_plant", "feed_mill")
    return {
        "source": "src/buildings.py, src/constants.py, src/game_rules.py, src/game_version.py",
        "game_version": get_game_version(),
        "columns": WORLD_WIDTH_TILES, "rows": WORLD_HEIGHT_TILES,
        "source_tile_pixels": TILE_SIZE,
        "buildings": {key: {field: BUILDING_TYPES[key][field]
                             for field in ("name", "width", "height", "build_cost")}
                      for key in ids},
        "farmhouse_level_one_body": list(FARMHOUSE_LEVELS[1]["size"]),
        "fields": {key: {field: value[field] for field in ("name", "width", "height")}
                   for key, value in FIELD_TYPES.items()},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "godot_3d" / "data" / "reference.json"
    data = reference()
    if args.check:
        if json.loads(target.read_text(encoding="utf-8")) != data:
            raise SystemExit("3D reference is stale; regenerate from the unchanged 2D catalog")
        print("3D catalog matches the 2D source")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(target)
