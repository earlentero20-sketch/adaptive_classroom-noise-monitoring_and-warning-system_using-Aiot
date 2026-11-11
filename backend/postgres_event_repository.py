"""PostgreSQL storage for validated SONIQ event responses.

The caller remains responsible for request validation, timestamp freshness,
and warning decisions. This repository only stores the resulting response.
"""

from datetime import datetime, timezone
import os
from typing import Any, Mapping


class PostgresRepositoryConfigError(ValueError):
    """PostgreSQL connection or pool configuration is missing or invalid."""


class DuplicateEventError(Exception):
    """An event with this globally unique ID has already been stored."""


class EventStorageError(RuntimeError):
    """The repository could not commit an event to PostgreSQL."""


def _positive_integer_environment_value(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise PostgresRepositoryConfigError(f"{name} must be an integer") from error
    if value < 1:
        raise PostgresRepositoryConfigError(f"{name} must be greater than zero")
    return value


def _database_timestamp(value: str | None) -> datetime | None:
    """Convert an already-validated contract timestamp for PostgreSQL storage."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PostgresEventRepository:
    """Store processed event responses in a shared PostgreSQL database."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_min_size: int = 1,
        pool_max_size: int = 5,
    ):
        if not database_url or not database_url.strip():
            raise PostgresRepositoryConfigError("database_url must not be empty")
        if pool_min_size < 1:
            raise PostgresRepositoryConfigError("pool_min_size must be greater than zero")
        if pool_max_size < pool_min_size:
            raise PostgresRepositoryConfigError("pool_max_size must be at least pool_min_size")

        try:
            from psycopg_pool import ConnectionPool
        except ImportError as error:
            raise RuntimeError(
                "PostgreSQL support requires the packages in backend/requirements.txt"
            ) from error

        self._pool = ConnectionPool(
            conninfo=database_url,
            min_size=pool_min_size,
            max_size=pool_max_size,
            open=False,
        )
        try:
            self._pool.open(wait=True)
        except Exception:
            # The application cannot close a repository whose constructor failed.
            self._pool.close()
            raise

    @classmethod
    def from_environment(cls) -> "PostgresEventRepository":
        """Create the pool from deployment-provided environment settings."""
        database_url = os.environ.get("SONIQ_DATABASE_URL")
        if not database_url or not database_url.strip():
            raise PostgresRepositoryConfigError("SONIQ_DATABASE_URL is required")
        minimum = _positive_integer_environment_value("SONIQ_DB_POOL_MIN_SIZE", 1)
        maximum = _positive_integer_environment_value("SONIQ_DB_POOL_MAX_SIZE", 5)
        if maximum < minimum:
            raise PostgresRepositoryConfigError(
                "SONIQ_DB_POOL_MAX_SIZE must be at least SONIQ_DB_POOL_MIN_SIZE"
            )
        return cls(database_url, pool_min_size=minimum, pool_max_size=maximum)

    def save_event(self, event: Mapping[str, Any]) -> None:
        """Insert one processed event atomically; leave API error mapping to caller."""
        classification = event["classification"]
        sound_level = event["sound_level"]
        warning = event["warning"]

        values = (
            event["event_id"],
            event["device_id"],
            event["schema_version"],
            _database_timestamp(event["received_at"]),
            event["connection_status"]["sensor"],
            classification["label"],
            classification["confident"],
            _database_timestamp(classification["observed_at"]),
            classification["status"],
            sound_level["value"],
            sound_level["unit"],
            sound_level["calibrated"],
            _database_timestamp(sound_level["observed_at"]),
            sound_level["status"],
            warning["triggered"],
            warning["reason"],
        )

        try:
            with self._pool.connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO events (
                        event_id, device_id, schema_version, received_at,
                        sensor_status, classification_label,
                        classification_confident, classification_observed_at,
                        classification_status, sound_level_value, sound_level_unit,
                        sound_level_calibrated, sound_level_observed_at,
                        sound_level_status, warning_triggered, warning_reason
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (event_id) DO NOTHING
                    RETURNING event_id
                    """,
                    values,
                )
                if cursor.fetchone() is None:
                    raise DuplicateEventError(
                        f"event_id {event['event_id']!r} has already been stored"
                    )
        except DuplicateEventError:
            raise
        except Exception as error:
            # The pool context rolls back failed inserts before this translation.
            raise EventStorageError("could not commit the event to PostgreSQL") from error

    def list_events(
        self, *, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        """Return persisted events newest first and the total matching row count."""
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("limit must be an integer between 1 and 100")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")

        try:
            with self._pool.connection() as connection:
                with connection.transaction():
                    connection.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                    total = connection.execute(
                        "SELECT COUNT(*) FROM events"
                    ).fetchone()[0]
                    rows = connection.execute(
                        """
                        SELECT event_id, device_id, schema_version, received_at,
                               sensor_status, classification_label,
                               classification_confident, classification_observed_at,
                               classification_status, sound_level_value,
                               sound_level_unit, sound_level_calibrated,
                               sound_level_observed_at, sound_level_status,
                               warning_triggered, warning_reason
                        FROM events
                        ORDER BY received_at DESC, event_id ASC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    ).fetchall()
        except Exception as error:
            raise EventStorageError("could not retrieve events from PostgreSQL") from error

        events = [
            {
                "schema_version": row[2],
                "event_id": row[0],
                "device_id": row[1],
                "received_at": _format_timestamp(row[3]),
                "connection_status": {"backend": "online", "sensor": row[4]},
                "classification": {
                    "label": row[5],
                    "confident": row[6],
                    "observed_at": _format_optional_timestamp(row[7]),
                    "status": row[8],
                },
                "sound_level": {
                    "value": row[9],
                    "unit": row[10],
                    "calibrated": row[11],
                    "observed_at": _format_optional_timestamp(row[12]),
                    "status": row[13],
                },
                "warning": {"triggered": row[14], "reason": row[15]},
            }
            for row in rows
        ]
        return events, total

    def close(self) -> None:
        """Close this instance's connection pool during service shutdown."""
        self._pool.close()


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_optional_timestamp(value: datetime | None) -> str | None:
    return _format_timestamp(value) if value is not None else None
