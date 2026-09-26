import tempfile
import json
import math
import unittest
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.main import create_app
from app.models import ChallengeResult
from app.schemas import ChallengeSubmission, SubmissionResponse, LeaderboardEntry
from psycopg.adapt import Transformer, PyFormat
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg


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
        self.assertEqual(body["farm_value"], "100000.00")
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
        self.assertEqual([item["rank"] for item in body["results"]], [1, 1, *range(3, 11)])
        self.assertEqual(body["results"][0]["player_name"], "Játékos 3")
        self.assertEqual(body["results"][1]["player_name"], "Játékos 4")
        self.assertNotIn("player_id", body["results"][0])
        self.assertNotIn("game_id", body["results"][0])
        self.assertTrue(body["results"][0]["completed_at"].endswith("Z"))
        values = [Decimal(item["farm_value"]) for item in body["results"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_limit_is_bounded(self):
        path = "/api/v1/challenges/ten-year/leaderboard"
        self.assertEqual(self.client.get(path + "?limit=0").status_code, 422)
        self.assertEqual(self.client.get(path + "?limit=101").status_code, 422)

    def assert_validation_error(self, response):
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "request_validation_error")
        text = response.text.lower()
        for forbidden in ("traceback", "sqlalchemy", "psycopg", "insert into"):
            self.assertNotIn(forbidden, text)

    def test_unicode_names_and_whitespace_remain_supported(self):
        for index, name in enumerate(("Gazda", "Árvíztűrő Norbi", "農夫 🌾",
                                      "Kovács Gazda", "<b>Gazda</b>", "x" * 24), 1):
            with self.subTest(name=name):
                response = self.client.post(
                    "/api/v1/challenges/ten-year/submit",
                    json=payload(index, player_name="  " + name + "  "),
                )
                self.assertEqual(response.status_code, 201)
                with self.app.state.session_factory() as session:
                    record = session.get(ChallengeResult, response.json()["result_id"])
                    self.assertEqual(record.player_name, name)

    def test_control_names_are_rejected_before_storage(self):
        for control in ("\0", "\n", "\r", "\t", "\x1f", "\x7f", "\x85"):
            for name in (control + "Gazda", "Gaz" + control + "da", "Gazda" + control):
                with self.subTest(name=repr(name)):
                    self.assert_validation_error(self.client.post(
                        "/api/v1/challenges/ten-year/submit",
                        json=payload(player_name=name),
                    ))
        with self.app.state.session_factory() as session:
            self.assertEqual(session.query(ChallengeResult).count(), 0)

    def test_numeric_storage_boundary_is_accepted(self):
        # SQLite does not enforce Numeric precision; these assert API acceptance,
        # not exact PostgreSQL storage. Decimal adaptation is tested separately.
        values = (0, 1234.56, math.nextafter(1e22, 0),
                  9999999999999999999999, "9999999999999999999999.99",
                  "9999999999999999999999.994", "123.456", "1e-1000")
        for index, value in enumerate(values, 1):
            with self.subTest(value=value):
                response = self.client.post(
                    "/api/v1/challenges/ten-year/submit", json=payload(index, value),
                )
                self.assertEqual(response.status_code, 201)

    def test_numeric_overflow_is_validation_error(self):
        values = ("9999999999999999999999.995", "10000000000000000000000.00",
                  1e22, math.nextafter(1e22, math.inf), 1e30, 1e308,
                  10**400, "1e100000")
        for value in values:
            with self.subTest(value=str(value)):
                self.assert_validation_error(self.client.post(
                    "/api/v1/challenges/ten-year/submit", json=payload(farm_value=value),
                ))
        with self.app.state.session_factory() as session:
            self.assertEqual(session.query(ChallengeResult).count(), 0)

    def test_nonfinite_values_remain_validation_errors(self):
        for value in (float("nan"), float("inf"), -float("inf"),
                      "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=str(value)):
                # Raw JSON also exercises nonstandard numeric tokens, rather
                # than having httpx reject them before the request reaches API.
                self.assert_validation_error(self.client.post(
                    "/api/v1/challenges/ten-year/submit",
                    content=json.dumps(payload(farm_value=value)),
                    headers={"Content-Type": "application/json"},
                ))

    def test_validation_passes_cent_precision_decimal_to_postgresql(self):
        for text in ("123.456", "1.005", "9999999999999999999999.99",
                     "9999999999999999999999.994"):
            with self.subTest(value=text):
                submission = ChallengeSubmission.model_validate(payload(farm_value=text))
                self.assertIsInstance(submission.farm_value, Decimal)
                expected = Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                self.assertEqual(submission.farm_value, expected)
                # Numeric binds Decimal unchanged with the actual psycopg dialect.
                dialect = PGDialect_psycopg()
                processor = ChallengeResult.__table__.c.farm_value.type.dialect_impl(
                    dialect,
                ).bind_processor(dialect)
                bound = (processor(submission.farm_value) if processor
                         else submission.farm_value)
                self.assertEqual(bound, expected)
                dumper = Transformer().get_dumper(bound, PyFormat.TEXT)
                self.assertEqual(dumper.oid, 1700)  # PostgreSQL numeric, not float8.
                self.assertEqual(Decimal(bytes(dumper.dump(bound)).decode()), expected)

    def leaderboard(self, **params):
        response = self.client.get("/api/v1/challenges/ten-year/leaderboard", params=params)
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def submit_values(self, values):
        ranks = []
        for index, value in enumerate(values, 1):
            response = self.client.post(
                "/api/v1/challenges/ten-year/submit", json=payload(index, value),
            )
            self.assertEqual(response.status_code, 201)
            ranks.append(response.json()["rank"])
        return ranks

    def test_negative_values_and_symmetric_storage_bounds(self):
        self.submit_values((100000, 0, -1, -1000, -50000,
                            "-9999999999999999999999.99",
                            "-9999999999999999999999.994"))
        records = self.leaderboard()
        self.assertEqual([row["rank"] for row in records], [1, 2, 3, 4, 5, 6, 6])
        for value in ("-9999999999999999999999.995", "-10000000000000000000000",
                      -1e22, -1e308, -(10**400), "-1e100000", True, False, "not a number"):
            with self.subTest(value=str(value)):
                self.assert_validation_error(self.client.post(
                    "/api/v1/challenges/ten-year/submit", json=payload(99, value),
                ))

    def test_distinct_scores_use_ordinary_ranks(self):
        self.assertEqual(self.submit_values((1000, 900, 800)), [1, 2, 3])
        self.assertEqual([row["rank"] for row in self.leaderboard()], [1, 2, 3])

    def test_competition_ranking_skips_places_after_ties(self):
        self.assertEqual(self.submit_values((1000, 900, 900, 800)), [1, 2, 2, 4])
        self.assertEqual([row["rank"] for row in self.leaderboard()], [1, 2, 2, 4])

    def test_three_first_places_are_followed_by_fourth_place(self):
        self.assertEqual(self.submit_values((1000, 1000, 1000, 900)), [1, 1, 1, 4])
        self.assertEqual([row["rank"] for row in self.leaderboard()], [1, 1, 1, 4])

    def test_negative_scores_participate_in_competition_ranking(self):
        self.assertEqual(self.submit_values((100, 0, -100, -100, -500)), [1, 2, 3, 3, 5])
        records = self.leaderboard()
        self.assertEqual([row["farm_value"] for row in records],
                         ["100.00", "0.00", "-100.00", "-100.00", "-500.00"])
        self.assertEqual([row["rank"] for row in records], [1, 2, 3, 3, 5])

    def test_timestamp_metadata_does_not_break_ties(self):
        self.submit_values((900, 900))
        with self.app.state.session_factory() as session:
            records = session.query(ChallengeResult).order_by(ChallengeResult.id).all()
            records[0].completed_at = datetime(2099, 1, 1)
            records[1].completed_at = datetime(2000, 1, 1)
            records[0].submitted_at = datetime(2026, 2, 1)
            records[1].submitted_at = datetime(2026, 1, 1)
            session.commit()
        records = self.leaderboard()
        self.assertEqual([row["rank"] for row in records], [1, 1])
        self.assertEqual([row["player_name"] for row in records], ["Játékos 2", "Játékos 1"])

    def test_tenth_place_includes_every_tied_record(self):
        self.submit_values((*range(2000, 1100, -100), 500, 500, 500, 400))
        records = self.leaderboard()
        self.assertEqual(len(records), 12)
        self.assertEqual([row["rank"] for row in records], [*range(1, 10), 10, 10, 10])
        self.assertEqual([row["farm_value"] for row in records[-3:]], ["500.00"] * 3)

    def test_tenth_place_without_ties_still_returns_ten_records(self):
        self.submit_values(range(1200, 0, -100))
        records = self.leaderboard()
        self.assertEqual(len(records), 10)
        self.assertEqual([row["rank"] for row in records], list(range(1, 11)))

    def test_cent_precision_not_float_remainders_decides_ties(self):
        self.assertEqual(self.submit_values(("100.003", "100.004", "99.995", "99.994")),
                         [1, 1, 1, 4])
        records = self.leaderboard()
        self.assertEqual([row["farm_value"] for row in records], ["100.00"] * 3 + ["99.99"])
        self.assertEqual([row["rank"] for row in records], [1, 1, 1, 4])

    def test_version_filter_ranks_only_matching_records(self):
        self.submit_values((1000, 900, 900))
        with self.app.state.session_factory() as session:
            record = session.query(ChallengeResult).filter_by(player_name="Játékos 1").one()
            record.game_version = "0.1.2"
            session.commit()
        records = self.leaderboard(game_version="0.1.0", limit=1)
        self.assertEqual(len(records), 2)
        self.assertEqual([row["rank"] for row in records], [1, 1])

    def test_extra_server_controlled_fields_remain_forbidden(self):
        for field, value in (("submitted_at", "2026-01-01T00:00:00Z"),
                             ("rank", 1), ("id", 1), ("unexpected", "value"),
                             ("challenge_type", "ten_year")):
            with self.subTest(field=field):
                self.assert_validation_error(self.client.post(
                    "/api/v1/challenges/ten-year/submit", json=payload(**{field: value}),
                ))

    def test_duplicate_cannot_change_score_or_identity(self):
        url = "/api/v1/challenges/ten-year/submit"
        original = payload(farm_value=1234.56)
        response = self.client.post(url, json=original)
        self.assertEqual(response.status_code, 201)
        result_id = response.json()["result_id"]
        for changes in ({"farm_value": 9999}, {"farm_value": 1},
                        {"player_name": "Másik Gazda"},
                        {"player_id": str(uuid.uuid4())}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post(url, json={**original, **changes}).status_code, 409)
        with self.app.state.session_factory() as session:
            self.assertEqual(session.query(ChallengeResult).count(), 1)
            record = session.get(ChallengeResult, result_id)
            self.assertEqual(record.farm_value, Decimal("1234.56"))
            self.assertEqual(record.player_id, original["player_id"])
            self.assertEqual(record.player_name, original["player_name"])

    def test_response_models_serialize_exact_decimal_bounds_without_float(self):
        for text in ("1234.56", "0.00", "-50000.25",
                     "9999999999999999999999.99", "-9999999999999999999999.99"):
            with self.subTest(value=text):
                score = Decimal(text)
                submission = SubmissionResponse(status="accepted", result_id=1,
                    game_id=payload()["game_id"], farm_value=score, rank=1)
                entry = LeaderboardEntry(rank=1, player_name="Gazda", farm_value=score,
                    game_version="0.1.2", completed_at=datetime.fromisoformat(payload()["completed_at"]))
                for model in (submission, entry):
                    self.assertEqual(model.farm_value, score)
                    encoded = json.loads(model.model_dump_json())["farm_value"]
                    self.assertIsInstance(encoded, str)
                    self.assertEqual(encoded, text)

    def test_submission_and_leaderboard_return_decimal_text(self):
        for index, value in enumerate((1234.56, 0, -50000.25), 1):
            response = self.client.post("/api/v1/challenges/ten-year/submit",
                                        json=payload(index, value))
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["farm_value"], format(Decimal(str(value)), ".2f"))
        self.assertEqual([row["farm_value"] for row in self.leaderboard()],
                         ["1234.56", "0.00", "-50000.25"])


if __name__ == "__main__":
    unittest.main()
