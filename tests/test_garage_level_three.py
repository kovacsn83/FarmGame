import tempfile
from pathlib import Path
from copy import deepcopy
import test_garage_fleet as fleet_tests
from buildings import get_garage_capacity, get_garage_parking_position, place_building, remove_building
from game_state import GameState
from game_rules import get_upgrade_status
from time_system import GameTime
from save_system import save_game, load_game
from garage_view import parking_slot_rects, parking_view_height, is_parked_in_garage
from vehicle_types import VehicleType
from financial_history import EXPENSE_UPGRADE
import pygame


class GarageLevelThreeTests(fleet_tests.GarageFleetTests):
    def state(self, level=3):
        self.house = place_building(self.world, self.buildings, 15, 2, "farmhouse")
        self.house["farmhouse_level"] = level
        return GameState(self.world, [], self.buildings, self.economy,
                         GameTime(start_ticks=0), vehicles=self.manager)

    def test_prerequisites_price_value_and_new_garage(self):
        state = self.state(2)
        self.assertFalse(self.economy.purchase_upgrade(state, "garage_level_3"))
        self.assertTrue(self.economy.purchase_upgrade(state, "garage_level_2"))
        self.assertFalse(self.economy.purchase_upgrade(state, "garage_level_3"))
        self.house["farmhouse_level"] = 3
        self.assertEqual(get_upgrade_status("garage_level_3", state.purchased_upgrades, 3), "Fejleszthető")
        previous_positions = [get_garage_parking_position(self.garages[0], i) for i in range(8)]
        money = self.economy.money
        value = self.economy.calculate_net_farm_value(state)
        self.assertTrue(self.economy.purchase_upgrade(state, "garage_level_3"))
        self.assertEqual(self.economy.money, money - 6000)
        record = self.economy.financial_history_save_record()[-1]
        self.assertEqual(record["category"], EXPENSE_UPGRADE)
        self.assertEqual(record["amount"], 6000)
        self.assertEqual(record["subcategory"], "garage_level_3")
        self.assertEqual(self.economy.calculate_net_farm_value(state), value)
        self.assertTrue(all(get_garage_capacity(g) == 12 for g in self.garages))
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 36)
        self.assertEqual(previous_positions, [get_garage_parking_position(self.garages[0], i) for i in range(8)])
        self.assertEqual(len({get_garage_parking_position(self.garages[0], i) for i in range(12)}), 12)
        self.assertFalse(self.economy.purchase_upgrade(state, "garage_level_3"))
        remove_building(self.world, self.buildings, self.garages[-1])
        new = place_building(self.world, self.buildings, 15, 25, "garage")
        state.synchronize_processing_upgrades()
        self.assertEqual(get_garage_capacity(new), 12)

    def test_automatic_compaction_active_preservation_and_roundtrip(self):
        state = self.state()
        self.economy.purchase_upgrade(state, "garage_level_2")
        for i in range(20):
            self.assertTrue(self.buy(VehicleType.TRAILER if i % 2 else VehicleType.TRACTOR))
        active = self.manager.vehicles[-1]
        active.state = "returning_home"
        active.path = [active.parking_tile]
        before = (active.world_x, active.world_y, active.path.copy(), active.current_task)
        self.economy.purchase_upgrade(state, "garage_level_3")
        self.assertEqual(before, (active.world_x, active.world_y, active.path, active.current_task))
        self.assertEqual([len(self.manager.assets_in_garage(g)) for g in self.garages], [12,8,0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "level3.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 36)
        self.assertEqual(len(self.manager.managed_assets), 20)
        homes = [(id(a.assigned_parking_building), a.parking_slot_id) for a in self.manager.managed_assets]
        self.assertEqual(len(set(homes)), 20)
        self.garages = [b for b in self.buildings if b["type"] == "garage"]
        # A populated garage is removable when the remaining 24 slots suffice.
        self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[0]))
        remove_building(self.world, self.buildings, self.garages[0])
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 24)
        self.assertFalse(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[1]))

    def test_twelve_slot_layout_and_full_capacity(self):
        state = self.state()
        self.economy.purchase_upgrade(state, "garage_level_2")
        self.economy.purchase_upgrade(state, "garage_level_3")
        slots = parking_slot_rects(pygame.Rect(0, 0, 400, parking_view_height(12)), 12)
        self.assertEqual(len({s.x for s in slots}), 4)
        self.assertEqual(len({s.y for s in slots}), 3)
        self.assertTrue(all(s.size == (36,36) for s in slots))
        for _ in range(36):
            self.assertTrue(self.buy())
        self.manager.vehicles[0].state = "returning_home"
        before = self.economy.money
        self.assertFalse(self.buy())
        self.assertEqual(before, self.economy.money)
