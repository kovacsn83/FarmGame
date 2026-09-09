"""A konkrét farmot azonosító, profiltól és mentési slottól független ID."""

import uuid


def generate_game_id():
    return str(uuid.uuid4())


def is_valid_game_id(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def restore_or_generate_game_id(saved_game_id, current_game_id=None):
    """Mentett ID-t állít vissza, legacy/hibás adatnál sessionönként egyet készít."""
    if is_valid_game_id(saved_game_id):
        return saved_game_id, False
    if is_valid_game_id(current_game_id):
        return current_game_id, True
    return generate_game_id(), True
