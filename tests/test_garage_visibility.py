import tempfile
from pathlib import Path
from unittest.mock import patch
import test_garage_fleet as fleet_tests
from garage_view import is_world_visible, is_parked_in_garage
from vehicle_types import VehicleType
from game_state import GameState
from time_system import GameTime, TIME_SLOW, TIME_NORMAL
from save_system import save_game, load_game
from world import tile_to_world_center
import pygame


class GarageVisibilityTests(fleet_tests.GarageFleetTests):
    def departure(self, vehicle):
        vehicle.state = "leaving_parking"
        vehicle._state_after_parking_exit = "awaiting_assignment"
        vehicle.last_update_ticks = 0
        vehicle.movement_accumulator_ms = 0

    def test_types_speeds_departure_and_arrival(self):
        for kind in (VehicleType.TRACTOR, VehicleType.COMBINE, VehicleType.FRUIT_HARVESTER):
            for speed in (TIME_SLOW, TIME_NORMAL):
                self.setUp()
                self.assertTrue(self.buy(kind))
                vehicle = self.manager.vehicles[0]
                clock = GameTime(start_ticks=0)
                clock.set_time_speed(speed)
                self.assertFalse(is_world_visible(vehicle))
                self.departure(vehicle)
                self.assertFalse(is_parked_in_garage(vehicle))
                self.assertFalse(is_world_visible(vehicle))
                reached = False
                for now in range(20, 2000, 20):
                    vehicle.update(self.world, self.buildings, self.economy, clock, current_ticks=now)
                    if vehicle.state != "leaving_parking":
                        self.assertEqual((vehicle.world_x, vehicle.world_y), tile_to_world_center(vehicle.row, vehicle.col))
                        self.assertTrue(is_world_visible(vehicle))
                        reached = True
                        break
                    self.assertFalse(is_world_visible(vehicle))
                self.assertTrue(reached)
                vehicle._arrive_home(self.world, self.economy, now)
                self.assertTrue(is_world_visible(vehicle))  # Still on the road.
                vehicle._move_world_toward(vehicle.parking_world_position, max_distance=1)
                self.assertFalse(is_world_visible(vehicle))
                self.assertFalse(is_parked_in_garage(vehicle))
                vehicle._finish_parking(self.world, self.economy, now)
                self.assertFalse(is_world_visible(vehicle))
                self.assertTrue(is_parked_in_garage(vehicle))

    def test_attached_implements_share_visibility_and_render_gate(self):
        pygame.display.init()
        for kind in (VehicleType.TRAILER, VehicleType.WATER_TANK):
            self.setUp()
            self.buy()
            self.buy(kind)
            vehicle, implement = self.manager.vehicles[0], self.manager.implements[0]
            implement.attach_to(vehicle)
            self.departure(vehicle)
            self.assertFalse(is_world_visible(implement))
            screen = pygame.Surface((500, 500), pygame.SRCALPHA)
            self.manager.draw(screen)
            self.assertEqual(screen.get_bounding_rect().width, 0)
            vehicle.world_x, vehicle.world_y = tile_to_world_center(vehicle.row, vehicle.col)
            self.assertTrue(is_world_visible(vehicle))
            self.assertTrue(is_world_visible(implement))
            vehicle.state = "entering_parking"
            vehicle.world_x += 1
            self.assertFalse(is_world_visible(vehicle))
            self.assertFalse(is_world_visible(implement))

    def test_visibility_roundtrip_at_every_transition_without_new_save_field(self):
        self.buy()
        vehicle = self.manager.vehicles[0]
        state = GameState(self.world, [], self.buildings, self.economy, GameTime(start_ticks=0), vehicles=self.manager)
        for phase in ("leaving_parking", "entering_parking", "returning_home"):
            vehicle = self.manager.vehicles[0]
            vehicle.state = phase
            vehicle._state_after_parking_exit = "awaiting_assignment" if phase == "leaving_parking" else None
            vehicle.world_x, vehicle.world_y = tile_to_world_center(vehicle.row, vehicle.col)
            if phase != "returning_home":
                vehicle.world_y += 2
            before = is_world_visible(vehicle)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "visibility.json"
                self.assertTrue(save_game(state, path))
                self.assertTrue(load_game(state, path))
            self.assertEqual(is_world_visible(self.manager.vehicles[0]), before)

    def test_non_garage_departure_is_unchanged(self):
        self.buy()
        vehicle = self.manager.vehicles[0]
        self.departure(vehicle)
        vehicle.parking_building_type = "farmhouse"
        self.assertTrue(is_world_visible(vehicle))
