"""Reproducible, headless environment render benchmark; never loads user saves.

Run with --source pointing at a baseline src copy for a before/after comparison.
--output optionally writes a preview outside the game's asset pipeline.
Times measure CPU rendering, not presented FPS or simulation performance.
"""
import argparse
import os
from pathlib import Path
import statistics
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'src')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--frames', type=int, default=120)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error('--frames must be positive')
    sys.path.insert(0, str(args.source.resolve()))
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    import pygame
    from asset_loader import load_grass_tiles
    from buildings import BUILDING_TYPES
    from camera import Camera
    from constants import BUILDING, FIELD, ROAD
    from orchards import draw_orchard_trees
    from screen_layout import get_play_area_rect, set_camera, set_screen_size
    from world import create_world, draw_world, draw_orchard_fences, draw_animal_pen_fences

    # A baseline source copy must still read the original project's assets.
    import asset_loader
    asset_loader.get_asset_root = lambda: Path(__file__).resolve().parents[1] / 'assets'
    pygame.init()
    pygame.display.set_mode((1, 1))
    set_screen_size(1500, 1000)
    camera = Camera()
    set_camera(camera)
    screen = pygame.Surface((1500, 1000))
    tiles = load_grass_tiles(20)
    world, fields, buildings = create_world(), [], []

    def stamp(record, tile):
        for row in range(record['row'], record['row'] + record['height']):
            for col in range(record['col'], record['col'] + record['width']):
                world[row][col] = tile

    # Dense but non-overlapping farm: buildings, ponds, merged plots and 120 trees.
    for index, kind in enumerate(('farmhouse', 'warehouse', 'market', 'garage', 'processing_plant', 'pond', 'animal_pen')):
        b = dict(BUILDING_TYPES[kind], type=kind, row=2, col=index * 10 + 1, farmhouse_level=3)
        buildings.append(b)
        stamp(b, BUILDING)
    for row in (12, 17, 22):
        for col in range(1, 61, 6):
            b = dict(type='orchard', row=row, col=col, width=4, height=4, trees=[])
            for index, (dr, dc) in enumerate(((0, 0), (0, 2), (2, 0), (2, 2))):
                b['trees'].append(dict(type=('apple', 'cherry', 'plum')[index % 3], row=row+dr, col=col+dc, annual_harvest_state='ripe' if index % 2 else 'waiting'))
            buildings.append(b)
            stamp(b, BUILDING)
    for index, crop in enumerate(('wheat', 'corn', 'tomato', 'alfalfa', 'hops')):
        for phase, growth in enumerate((0, 20, 70, 100)):
            f = dict(row=29+phase*4, col=1+index*6, width=4, height=4, crop=crop, growth=growth)
            fields.append(f)
            stamp(f, FIELD)
    for row in range(80):
        for col in range(100):
            if world[row][col] == 0 and (row in (0, 10, 27, 46) or col in (0, 65)):
                world[row][col] = ROAD

    def render():
        screen.set_clip(None)
        screen.fill((235, 235, 230))
        screen.set_clip(get_play_area_rect())
        draw_world(screen, world, fields, buildings, tiles)
        draw_orchard_trees(screen, buildings)
        draw_orchard_fences(screen, buildings)
        draw_animal_pen_fences(screen, buildings)

    start = time.perf_counter()
    render()
    cold_ms = (time.perf_counter() - start) * 1000
    for _ in range(20):
        render()
    samples = []
    for batch in range(5):
        start = time.perf_counter()
        for _ in range(args.frames):
            render()
        samples.append((time.perf_counter() - start) * 1000 / args.frames)
    print(f'cold_ms={cold_ms:.3f} warm_median_ms={statistics.median(samples):.3f} batches_ms={[round(x, 3) for x in samples]}')
    # Exercise nonzero camera offsets separately from the fixed benchmark scene.
    camera.camera_x, camera.camera_y = 137, 93
    render()
    camera.camera_x = camera.camera_y = 0
    render()
    if args.output:
        pygame.image.save(screen, str(args.output))
    pygame.quit()


if __name__ == '__main__':
    main()
