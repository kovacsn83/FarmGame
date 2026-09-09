import tempfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.main import create_app
from app.models import ChallengeResult


def payload(index=1, farm_value=100_000, **overrides):
    data = {
        "player_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"player-{index}")),
        "player_name": f"Játékos {index}",
        "game_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"game-{index}")),
        "game_version": "0.1.0",
        "farm_value": farm_value,
        "challenge_years": 10,
        "completed_at": f"2026-09-{min(index, 28):02d}T12:00:00+02:00",
    }
    data.update(overrides)
    return data


class ChallengeApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "api.db"
        self.app = create_app(f"sqlite:///{database_path.as_posix()}")
        Base.metadata.create_all(self.app.state.engine)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.state.engine.dispose()
        self.temporary_directory.cleanup()

    def test_health_checks_database(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_valid_submission_persists_all_fields_and_server_timestamp(self):
        request = payload(player_name="  Árvíztűrő Norbi  ")
        response = self.client.post(
            "/api/v1/challenges/ten-year/submit", json=request,
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["game_id"], request["game_id"])
        self.assertEqual(body["farm_value"], request["farm_value"])
        self.assertEqual(body["rank"], 1)

        with self.app.state.session_factory() as session:
            record = session.get(ChallengeResult, body["result_id"])
            self.assertEqual(record.player_id, request["player_id"])
            self.assertEqual(record.player_name, "Árvíztűrő Norbi")
            self.assertEqual(record.game_id, request["game_id"])
            self.assertEqual(record.game_version, request["game_version"])
            self.assertEqual(float(record.farm_value), request["farm_value"])
            self.assertIsNotNone(record.completed_at)
            self.assertIsNotNone(record.submitted_at)

    def test_invalid_requests_have_consistent_errors(self):
        cases = (
            {"player_id": None},
            {"game_id": None},
            {"player_id": "not-a-uuid"},
            {"game_id": "not-a-uuid"},
            {"player_name": "   "},
            {"player_name": "x" * 25},
            {"farm_value": -1},
            {"game_version": "version-one"},
            {"challenge_years": 9},
            {"completed_at": "2026-09-09T12:00:00"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                response = self.client.post(
                    "/api/v1/challenges/ten-year/submit",
                    json=payload(**changes),
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "request_validation_error",
                )
        for missing_field in ("player_id", "game_id"):
            with self.subTest(missing_field=missing_field):
                request = payload()
                request.pop(missing_field)
                response = self.client.post(
                    "/api/v1/challenges/ten-year/submit", json=request,
                )
                self.assertEqual(response.status_code, 422)

    def test_duplicate_is_immutable_and_other_game_is_allowed(self):
        first = payload(farm_value=200_000)
        url = "/api/v1/challenges/ten-year/submit"
        self.assertEqual(self.client.post(url, json=first).status_code, 201)
        duplicate = dict(first, farm_value=900_000)
        response = self.client.post(url, json=duplicate)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error"]["code"],
            "challenge_result_already_submitted",
        )
        other = payload(2, player_id=first["player_id"])
        self.assertEqual(self.client.post(url, json=other).status_code, 201)
        with self.app.state.session_factory() as session:
            records = session.query(ChallengeResult).all()
            self.assertEqual(len(records), 2)
            self.assertEqual(float(records[0].farm_value), 200_000)

    def test_database_unique_constraint_protects_against_duplicates(self):
        data = payload()
        values = {
            **data, "challenge_type": "ten_year",
            "completed_at": datetime.fromisoformat(data["completed_at"]),
        }
        with self.app.state.session_factory() as session:
            session.execute(insert(ChallengeResult).values(**values))
            session.commit()
            with self.assertRaises(IntegrityError):
                session.execute(insert(ChallengeResult).values(**values))
                session.commit()

    def test_leaderboard_top_ten_rank_tie_break_and_public_fields(self):
        url = "/api/v1/challenges/ten-year/submit"
        for index in range(1, 13):
            value = 500_000 if index in (3, 4) else index * 10_000
            completed = (
                "2026-08-01T12:00:00+00:00" if index == 4
                else f"2026-09-{index:02d}T12:00:00+00:00"
            )
            response = self.client.post(
                url, json=payload(index, value, completed_at=completed),
            )
            self.assertEqual(response.status_code, 201)

        response = self.client.get(
            "/api/v1/challenges/ten-year/leaderboard",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["challenge"], "ten_year")
        self.assertEqual(body["challenge_years"], 10)
        self.assertEqual(len(body["results"]), 10)
        self.assertEqual([item["rank"] for item in body["results"]], list(range(1, 11)))
        self.assertEqual(body["results"][0]["player_name"], "Játékos 4")
        self.assertEqual(body["results"][1]["player_name"], "Játékos 3")
        self.assertNotIn("player_id", body["results"][0])
        self.assertNotIn("game_id", body["results"][0])
        self.assertTrue(body["results"][0]["completed_at"].endswith("Z"))
        values = [item["farm_value"] for item in body["results"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_limit_is_bounded(self):
        path = "/api/v1/challenges/ten-year/leaderboard"
        self.assertEqual(self.client.get(path + "?limit=0").status_code, 422)
        self.assertEqual(self.client.get(path + "?limit=101").status_code, 422)


if __name__ == "__main__":
    unittest.main()
