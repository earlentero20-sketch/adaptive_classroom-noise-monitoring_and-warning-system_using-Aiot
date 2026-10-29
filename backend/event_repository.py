"""SQLite storage for validated SONIQ event responses.

This module stores the response produced by ``backend.app.process_event``. It
does not validate incoming requests or calculate freshness and warning policy.

The interface contract calls ``event_id`` an event-unique ID but does not say
whether uniqueness is global or per device. This first schema provisionally
uses a global ``event_id`` primary key; confirm that choice with the team.
"""

import sqlite3
from typing import Any, Mapping


class DuplicateEventError(Exception):
    """An event with the same provisional global event ID is already stored."""


class SQLiteEventRepository:
    """Save validated event response dictionaries in an explicit SQLite file."""

    def __init__(self, database_path: str):
        if not database_path:
            raise ValueError("database_path must be an explicit non-empty path")
        self.database_path = database_path

    def initialize(self) -> None:
        """Create the event table and indexes if they do not already exist."""
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT NOT NULL PRIMARY KEY,
                        device_id TEXT NOT NULL CHECK (length(trim(device_id)) > 0),
                        schema_version TEXT NOT NULL,
                        received_at TEXT NOT NULL,
                        sensor_status TEXT NOT NULL
                            CHECK (sensor_status IN ('online', 'offline', 'unknown')),
                        classification_label TEXT
                            CHECK (classification_label IS NULL OR classification_label IN (
                                'Teacher Discussion', 'Student Conversation'
                            )),
                        classification_confident INTEGER NOT NULL
                            CHECK (classification_confident IN (0, 1)),
                        classification_observed_at TEXT,
                        classification_status TEXT NOT NULL
                            CHECK (classification_status IN (
                                'fresh', 'stale', 'unavailable', 'unknown', 'invalid_time'
                            )),
                        sound_level_value REAL,
                        sound_level_unit TEXT
                            CHECK (sound_level_unit IS NULL OR sound_level_unit = 'dB_SPL'),
                        sound_level_calibrated INTEGER NOT NULL
                            CHECK (sound_level_calibrated IN (0, 1)),
                        sound_level_observed_at TEXT,
                        sound_level_status TEXT NOT NULL
                            CHECK (sound_level_status IN (
                                'fresh', 'stale', 'unavailable', 'unknown', 'invalid_time'
                            )),
                        warning_triggered INTEGER NOT NULL
                            CHECK (warning_triggered IN (0, 1)),
                        warning_reason TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_received_at "
                    "ON events (received_at DESC, event_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_device_received_at "
                    "ON events (device_id, received_at DESC, event_id)"
                )
        finally:
            connection.close()

    def save_event(self, event: Mapping[str, Any]) -> None:
        """Insert one already-validated backend response in a transaction.

        SQLite commits the insert when the connection context exits normally
        and rolls it back if an insert or constraint check fails. The event's
        observation times and server ``received_at`` are stored independently.
        """
        classification = event["classification"]
        sound_level = event["sound_level"]
        warning = event["warning"]
        sensor_status = event["connection_status"]["sensor"]

        values = (
            event["event_id"],
            event["device_id"],
            event["schema_version"],
            event["received_at"],
            sensor_status,
            classification["label"],
            int(classification["confident"]),
            classification["observed_at"],
            classification["status"],
            sound_level["value"],
            sound_level["unit"],
            int(sound_level["calibrated"]),
            sound_level["observed_at"],
            sound_level["status"],
            int(warning["triggered"]),
            warning["reason"],
        )

        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO events (
                        event_id, device_id, schema_version, received_at,
                        sensor_status, classification_label,
                        classification_confident, classification_observed_at,
                        classification_status, sound_level_value,
                        sound_level_unit, sound_level_calibrated,
                        sound_level_observed_at, sound_level_status,
                        warning_triggered, warning_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_id) DO NOTHING
                    """,
                    values,
                )
                if cursor.rowcount == 0:
                    raise DuplicateEventError(
                        f"event_id {event['event_id']!r} has already been stored"
                    )
        finally:
            connection.close()
