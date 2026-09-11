"""Central saved-state baseline for lossless session exit checks."""

from save_system import create_save_state_signature


class UnsavedChangesTracker:
    """Compares current save data with the last successful save or load."""

    def __init__(self):
        self._saved_signature = None
        self.current_slot_id = None
        self.current_save_name = None

    def start_new_game(self):
        self._saved_signature = None
        self.current_slot_id = None
        self.current_save_name = None

    def mark_saved(self, game_state, slot_id, save_name):
        self._saved_signature = create_save_state_signature(game_state)
        self.current_slot_id = slot_id
        self.current_save_name = save_name

    def mark_loaded(self, game_state, slot_id, save_name):
        self.mark_saved(game_state, slot_id, save_name)

    def has_unsaved_changes(self, game_state):
        if game_state is None:
            return False
        if self._saved_signature is None:
            return True
        return create_save_state_signature(game_state) != self._saved_signature
