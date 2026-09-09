import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from game_logger import get_logger
from user_data import get_player_profile_path


PROFILE_VERSION = 1
MAX_PLAYER_NAME_LENGTH = 24


class PlayerProfileError(RuntimeError):
    """A profil olvasásának vagy mentésének diagnosztizálható hibája."""


class PlayerProfileValidationError(PlayerProfileError):
    """Létező, de sérült vagy nem támogatott profilfájlt jelez."""


@dataclass(frozen=True)
class PlayerProfile:
    profile_version: int
    player_id: str
    player_name: str
    created_at: str


def normalize_player_name(name):
    return str(name).strip()


def validate_player_name(name):
    normalized = normalize_player_name(name)
    if not normalized:
        raise ValueError("A játékosnév nem lehet üres.")
    if len(normalized) > MAX_PLAYER_NAME_LENGTH:
        raise ValueError(
            f"A játékosnév legfeljebb {MAX_PLAYER_NAME_LENGTH} karakter lehet."
        )
    return normalized


def _validate_profile_data(data):
    if not isinstance(data, dict):
        raise PlayerProfileValidationError("A player.json gyökéreleme nem objektum.")
    required_types = {
        "profile_version": int,
        "player_id": str,
        "player_name": str,
        "created_at": str,
    }
    for field, expected_type in required_types.items():
        if not isinstance(data.get(field), expected_type):
            raise PlayerProfileValidationError(
                f"A player.json '{field}' mezője hiányzik vagy hibás típusú."
            )
    if data["profile_version"] != PROFILE_VERSION:
        raise PlayerProfileValidationError("A player.json profilverziója nem támogatott.")
    try:
        uuid.UUID(data["player_id"])
    except (ValueError, AttributeError) as error:
        raise PlayerProfileValidationError("A player_id nem érvényes UUID.") from error
    try:
        player_name = validate_player_name(data["player_name"])
    except ValueError as error:
        raise PlayerProfileValidationError(str(error)) from error
    try:
        datetime.fromisoformat(data["created_at"])
    except ValueError as error:
        raise PlayerProfileValidationError("A created_at nem érvényes ISO 8601 időpont.") from error
    return PlayerProfile(
        profile_version=data["profile_version"],
        player_id=data["player_id"],
        player_name=player_name,
        created_at=data["created_at"],
    )


def load_player_profile():
    """Betölti a közös helyi profilt; hiányzó fájlnál None értéket ad."""
    path = get_player_profile_path()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as profile_file:
            profile = _validate_profile_data(json.load(profile_file))
    except PlayerProfileValidationError:
        raise
    except (OSError, json.JSONDecodeError) as error:
        raise PlayerProfileValidationError(
            f"A játékosprofil nem olvasható: {error}"
        ) from error
    get_logger().log(f"Profile loaded: {profile.player_name}", "PlayerProfile")
    return profile


def save_player_profile(profile):
    """Ideiglenes fájlon át, atomikusan menti a validált profilt."""
    profile = _validate_profile_data(asdict(profile))
    path = get_player_profile_path()
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8", newline="\n") as profile_file:
            json.dump(asdict(profile), profile_file, ensure_ascii=False, indent=4)
            profile_file.write("\n")
            profile_file.flush()
            os.fsync(profile_file.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PlayerProfileError(f"A játékosprofil nem menthető: {error}") from error
    return profile


def _archive_corrupt_profile(path):
    if not path.exists():
        return None
    suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"player.corrupt-{suffix}.json")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"player.corrupt-{suffix}-{counter}.json")
        counter += 1
    try:
        os.replace(path, backup)
    except OSError as error:
        raise PlayerProfileError(
            f"A sérült játékosprofil nem archiválható: {error}"
        ) from error
    return backup


def create_player_profile(name, recover_corrupt=False):
    """Egyszer hoz létre UUID-alapú profilt; felülíráshoz explicit recovery kell."""
    player_name = validate_player_name(name)
    path = get_player_profile_path()
    if path.exists():
        if not recover_corrupt:
            raise PlayerProfileError("A játékosprofil már létezik.")
        archived_path = _archive_corrupt_profile(path)
        get_logger().log(
            f"Corrupt profile archived: {archived_path.name}",
            "PlayerProfile", level="WARNING",
        )
    profile = PlayerProfile(
        profile_version=PROFILE_VERSION,
        player_id=str(uuid.uuid4()),
        player_name=player_name,
        created_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    )
    save_player_profile(profile)
    get_logger().log("New player profile created.", "PlayerProfile")
    return profile


def update_player_name(profile, new_name):
    """A tartós player_id és létrehozási idő megtartásával módosítja a nevet."""
    updated = PlayerProfile(
        profile_version=profile.profile_version,
        player_id=profile.player_id,
        player_name=validate_player_name(new_name),
        created_at=profile.created_at,
    )
    return save_player_profile(updated)


def get_player_name(profile):
    return profile.player_name if profile is not None else None


def get_player_id(profile):
    return profile.player_id if profile is not None else None
