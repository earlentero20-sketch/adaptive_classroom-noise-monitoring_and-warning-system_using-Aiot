from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import tempfile
from threading import Barrier
import unittest
from uuid import uuid4
from unittest.mock import patch

from backend.migrate import apply_migrations
from backend.postgres_event_repository import (
    DuplicateEventError,
    EventStorageError,
    PostgresEventRepository,
    PostgresRepositoryConfigError,
)


class PostgresRepositoryConfigurationTests(unittest.TestCase):
    def test_environment_requires_database_url(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(PostgresRepositoryConfigError, "SONIQ_DATABASE_URL"):
                PostgresEventRepository.from_environment()


class PostgresEventRepositoryIntegrationTests(unittest.TestCase):
    """Integration tests run only against a dedicated *test* PostgreSQL DB."""

    @classmethod
    def setUpClass(cls):
        database_url = os.environ.get("SONIQ_TEST_DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("set SONIQ_TEST_DATABASE_URL to a dedicated PostgreSQL test DB")
        try:
            import psycopg
            from psycopg import conninfo, sql
            import psycopg_pool  # noqa: F401 - check the configured pool dependency too
        except ImportError as error:
            raise unittest.SkipTest("PostgreSQL integration tests require psycopg and psycopg_pool") from error

        db_name = conninfo.conninfo_to_dict(database_url).get("dbname", "")
        if not re.search(r"(^|[_-])test($|[_-])", db_name, re.IGNORECASE):
            raise RuntimeError(
                "SONIQ_TEST_DATABASE_URL must name a dedicated database with a "
                "separate 'test' name segment, such as soniq_test"
            )

        cls._psycopg = psycopg
        cls._sql = sql
        cls._database_url = database_url
        cls._schema = f"soniq_test_{uuid4().hex}"
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls._schema))
            )

        cls._test_database_url = conninfo.make_conninfo(
            database_url, options=f"-c search_path={cls._schema}"
        )
        with psycopg.connect(cls._test_database_url) as connection:
            apply_migrations(connection)

    @classmethod
    def tearDownClass(cls):
        if not hasattr(cls, "_schema"):
            return
        with cls._psycopg.connect(cls._database_url, autocommit=True) as connection:
            connection.execute(
                cls._sql.SQL("DROP SCHEMA {} CASCADE").format(
                    cls._sql.Identifier(cls._schema)
                )
            )

    def setUp(self):
        self.repository = PostgresEventRepository(
            self._test_database_url, pool_min_size=1, pool_max_size=4
        )
        with self._psycopg.connect(self._test_database_url) as connection:
            connection.execute("TRUNCATE TABLE events")

    def tearDown(self):
        self.repository.close()

    @staticmethod
    def event_response(event_id="event-1", device_id="device-1"):
        return {
            "schema_version": "1.0",
            "event_id": event_id,
            "device_id": device_id,
            "received_at": "2026-10-11T04:00:01Z",
            "connection_status": {"backend": "online", "sensor": "online"},
            "classification": {
                "label": "Student Conversation",
                "confident": True,
                "observed_at": "2026-10-11T04:00:00Z",
                "status": "fresh",
            },
            "sound_level": {
                "value": 75.5,
                "unit": "dB_SPL",
                "calibrated": True,
                "observed_at": "2026-10-11T03:59:59Z",
                "status": "fresh",
            },
            "warning": {
                "triggered": True,
                "reason": "student_conversation_above_threshold",
            },
        }

    def query_one(self, query, params=()):
        with self._psycopg.connect(self._test_database_url) as connection:
            return connection.execute(query, params).fetchone()

    def test_migration_applies_once_and_records_its_checksum(self):
        with self._psycopg.connect(self._test_database_url) as connection:
            self.assertEqual(apply_migrations(connection), [])
            versions = connection.execute(
                "SELECT version, checksum FROM schema_migrations"
            ).fetchall()
            tables = connection.execute(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = current_schema() AND table_name = 'events'"""
            ).fetchall()

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0][0], "001_create_events")
        self.assertTrue(versions[0][1])
        self.assertEqual(tables, [("events",)])

    def test_migration_runner_rejects_changed_applied_migration(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            migration_path = Path(temporary_directory) / "001_probe.sql"
            migration_path.write_text(
                "CREATE TABLE migration_probe (id INTEGER);", encoding="utf-8"
            )
            with self._psycopg.connect(self._test_database_url) as connection:
                self.assertEqual(
                    apply_migrations(connection, Path(temporary_directory)),
                    ["001_probe"],
                )
                self.assertEqual(
                    apply_migrations(connection, Path(temporary_directory)), []
                )
                migration_path.write_text(
                    "CREATE TABLE migration_probe (id BIGINT);", encoding="utf-8"
                )
                with self.assertRaisesRegex(RuntimeError, "was changed"):
                    apply_migrations(connection, Path(temporary_directory))

    def test_save_event_preserves_fields_and_all_event_timestamps(self):
        self.repository.save_event(self.event_response())
        row = self.query_one(
            """SELECT schema_version, device_id, received_at,
                      classification_label, classification_confident,
                      classification_observed_at, classification_status,
                      sound_level_value, sound_level_unit, sound_level_calibrated,
                      sound_level_observed_at, sound_level_status,
                      warning_triggered, warning_reason
               FROM events WHERE event_id = %s""",
            ("event-1",),
        )

        self.assertEqual(row[0:2], ("1.0", "device-1"))
        self.assertEqual(row[2], datetime(2026, 10, 11, 4, 0, 1, tzinfo=timezone.utc))
        self.assertEqual(row[3:7], (
            "Student Conversation", True,
            datetime(2026, 10, 11, 4, 0, tzinfo=timezone.utc), "fresh",
        ))
        self.assertEqual(row[7:12], (
            75.5, "dB_SPL", True,
            datetime(2026, 10, 11, 3, 59, 59, tzinfo=timezone.utc), "fresh",
        ))
        self.assertEqual(row[12:], (True, "student_conversation_above_threshold"))

    def test_duplicate_global_event_id_from_another_device_is_rejected(self):
        self.repository.save_event(self.event_response())
        with self.assertRaisesRegex(DuplicateEventError, "event-1"):
            self.repository.save_event(
                self.event_response(event_id="event-1", device_id="device-2")
            )

        self.assertEqual(
            self.query_one("SELECT COUNT(*) FROM events")[0], 1
        )

    def test_constraint_failure_rolls_back_event_insert(self):
        invalid = self.event_response(event_id="invalid-event")
        invalid["connection_status"]["sensor"] = "bad-status"

        with self.assertRaises(EventStorageError):
            self.repository.save_event(invalid)

        self.assertEqual(
            self.query_one("SELECT COUNT(*) FROM events WHERE event_id = %s", ("invalid-event",))[0],
            0,
        )

    def test_concurrent_insert_of_same_global_id_creates_one_row(self):
        second_repository = PostgresEventRepository(
            self._test_database_url, pool_min_size=1, pool_max_size=2
        )
        barrier = Barrier(2)

        def submit(repository):
            barrier.wait(timeout=10)
            try:
                repository.save_event(self.event_response())
                return "inserted"
            except DuplicateEventError:
                return "duplicate"

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(submit, (self.repository, second_repository)))
        finally:
            second_repository.close()

        self.assertCountEqual(results, ["inserted", "duplicate"])
        self.assertEqual(self.query_one("SELECT COUNT(*) FROM events")[0], 1)


if __name__ == "__main__":
    unittest.main()
