import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.event_repository import DuplicateEventError, SQLiteEventRepository


class SQLiteEventRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temporary_directory.name) / "events.sqlite3")
        self.repository = SQLiteEventRepository(self.database_path)
        self.repository.initialize()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def event_response(self, **updates):
        event = {
            "schema_version": "1.0",
            "event_id": "event-1",
            "device_id": "device-1",
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
        event.update(updates)
        return event

    def fetch_event(self, event_id="event-1"):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
        finally:
            connection.close()

    def test_initialize_creates_events_table_and_can_be_repeated(self):
        self.repository.initialize()
        connection = sqlite3.connect(self.database_path)
        try:
            names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
                )
            }
        finally:
            connection.close()

        self.assertIn("events", names)
        self.assertIn("idx_events_received_at", names)
        self.assertIn("idx_events_device_received_at", names)

    def test_events_table_rejects_null_event_id(self):
        connection = sqlite3.connect(self.database_path)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "event_id"):
                connection.execute("INSERT INTO events (event_id) VALUES (NULL)")
        finally:
            connection.close()

    def test_save_event_preserves_fields_and_distinct_timestamps(self):
        self.repository.save_event(self.event_response())
        row = self.fetch_event()

        self.assertEqual(row["schema_version"], "1.0")
        self.assertEqual(row["device_id"], "device-1")
        self.assertEqual(row["received_at"], "2026-10-11T04:00:01Z")
        self.assertEqual(row["classification_observed_at"], "2026-10-11T04:00:00Z")
        self.assertEqual(row["sound_level_observed_at"], "2026-10-11T03:59:59Z")
        self.assertEqual(row["sound_level_value"], 75.5)
        self.assertEqual(row["warning_triggered"], 1)
        self.assertEqual(row["warning_reason"], "student_conversation_above_threshold")

    def test_save_event_preserves_null_and_unavailable_measurements(self):
        event = self.event_response()
        event["classification"] = {
            "label": None,
            "confident": False,
            "observed_at": None,
            "status": "unavailable",
        }
        event["sound_level"] = {
            "value": None,
            "unit": None,
            "calibrated": False,
            "observed_at": None,
            "status": "unavailable",
        }
        event["warning"] = {"triggered": False, "reason": "classification_unavailable"}

        self.repository.save_event(event)
        row = self.fetch_event()

        self.assertIsNone(row["classification_label"])
        self.assertIsNone(row["classification_observed_at"])
        self.assertEqual(row["classification_status"], "unavailable")
        self.assertIsNone(row["sound_level_value"])
        self.assertIsNone(row["sound_level_unit"])
        self.assertIsNone(row["sound_level_observed_at"])
        self.assertEqual(row["sound_level_status"], "unavailable")
        self.assertEqual(row["warning_triggered"], 0)

    def test_duplicate_event_id_raises_clear_repository_exception(self):
        event = self.event_response()
        self.repository.save_event(event)

        with self.assertRaisesRegex(DuplicateEventError, "event-1"):
            self.repository.save_event(event)

        connection = sqlite3.connect(self.database_path)
        try:
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 1)

    def test_invalid_record_reusing_existing_event_id_keeps_integrity_error(self):
        self.repository.save_event(self.event_response())
        invalid_event = self.event_response()
        invalid_event["connection_status"]["sensor"] = "not-a-contract-status"

        with self.assertRaises(sqlite3.IntegrityError) as raised:
            self.repository.save_event(invalid_event)

        self.assertNotIsInstance(raised.exception, DuplicateEventError)
        row = self.fetch_event()
        self.assertEqual(row["sensor_status"], "online")
        self.assertEqual(row["warning_triggered"], 1)

    def test_constraint_failure_rolls_back_without_storing_a_row(self):
        event = self.event_response()
        event["connection_status"]["sensor"] = "not-a-contract-status"

        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.save_event(event)

        connection = sqlite3.connect(self.database_path)
        try:
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
