"""PostgreSQL storage for validated SONIQ event responses.

The caller remains responsible for request validation, timestamp freshness,
and warning decisions. This repository only stores the resulting response.
"""

from datetime import datetime
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

    def close(self) -> None:
        """Close this instance's connection pool during service shutdown."""
        self._pool.close()
