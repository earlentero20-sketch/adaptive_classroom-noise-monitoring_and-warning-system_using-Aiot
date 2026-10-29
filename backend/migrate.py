"""Run versioned PostgreSQL migrations as an explicit deployment step.

Backend instances must not call this module during normal service startup.
Run ``python -m backend.migrate`` once before starting or updating instances.
"""

import hashlib
import os
from pathlib import Path
import re
from typing import Any


MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_LOCK_ID = 735129416782340123
MIGRATION_FILENAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")


def apply_migrations(connection: Any, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply unapplied SQL files in order and reject edits to applied files."""
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"no SQL migrations found in {migrations_dir}")

    applied_now = []
    for migration_path in migration_files:
        if not MIGRATION_FILENAME.fullmatch(migration_path.name):
            raise RuntimeError(f"invalid migration filename: {migration_path.name}")
        version = migration_path.stem
        migration_sql = migration_path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(migration_sql.encode("utf-8")).hexdigest()

        with connection.transaction():
            # This protects against two operators accidentally starting the
            # migration command at the same time. It is not called by the app.
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            row = connection.execute(
                "SELECT checksum FROM schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if row is not None:
                if row[0] != checksum:
                    raise RuntimeError(
                        f"applied migration {version} was changed; add a new migration instead"
                    )
                continue

            # Migration files contain plain DDL statements and no parameters.
            # Psycopg sends this script in simple-query mode.
            connection.execute(migration_sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                (version, checksum),
            )
            applied_now.append(version)

    return applied_now


def main() -> None:
    database_url = os.environ.get("SONIQ_DATABASE_URL")
    if not database_url or not database_url.strip():
        raise SystemExit("SONIQ_DATABASE_URL is required to run migrations")
    try:
        import psycopg
    except ImportError as error:
        raise SystemExit("Install backend/requirements.txt before running migrations") from error

    with psycopg.connect(database_url) as connection:
        applied = apply_migrations(connection)
    if applied:
        print("Applied PostgreSQL migrations:", ", ".join(applied))
    else:
        print("PostgreSQL schema is already up to date")


if __name__ == "__main__":
    main()
