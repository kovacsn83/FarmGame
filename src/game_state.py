class GameState:
    """Ez az osztály fogja össze a játék teljes állapotát."""

    def __init__(
            self, world, fields, buildings, economy, game_time,
            purchased_upgrades=None, tractor=None, vehicles=None,
            animals=None, bank_system=None, quest_manager=None):
        # A meglévő objektumokat referenciaként tároljuk, másolatok nélkül.
        self.world = world
        self.fields = fields
        self.buildings = buildings
        self.economy = economy
        self.game_time = game_time
        if hasattr(self.economy, "bind_game_time"):
            self.economy.bind_game_time(game_time)
        self.purchased_upgrades = set(purchased_upgrades or ())
        self.tractor = tractor
        self.vehicles = vehicles
        self.animals = animals if animals is not None else []
        self.bank_system = bank_system
        self.quest_manager = quest_manager

    @property
    def time_speed(self):
        """Az idősebességet másolat készítése nélkül teszi elérhetővé."""
        return self.game_time.current_time_speed
