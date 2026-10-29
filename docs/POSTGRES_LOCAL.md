# SONIQ PostgreSQL backend storage

The PostgreSQL repository is separate from the HTTP handler. It stores the
processed event response supplied by `backend.app.process_event()` and does
not repeat validation, timestamp freshness checks, or warning calculations.
Normal backend startup does not run schema migrations.

## Dependencies

Install the existing ML dependencies and the backend database driver from the
repository root:

```powershell
py -m venv ml/.venv
.\ml\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r backend/requirements.txt
```

The backend requirement uses Psycopg 3 with its binary implementation and
connection-pool extra. The synchronous pool suits the current synchronous
backend. Pool connection contexts commit on success and roll back on errors.

## Local preflight without connecting to PostgreSQL

From the repository root, run:

    .\backend\run_local_demo.ps1 -PreflightOnly

This checks the project Python environment, required Python imports, and the
configured local model artifact. It checks whether SONIQ_DATABASE_URL is set
without printing its value. The preflight does not connect to PostgreSQL,
start the HTTP server, run migrations, or prove that the database is reachable.
It exits with an explanation if required local setup or configuration is
missing.

After a preflight passes and the database owner has approved the target, use
the normal launcher to start the service. Startup is successful only after the
PostgreSQL connection pool opens and the server reports its listening address.

## Connection settings

Provide `SONIQ_DATABASE_URL` through a local environment variable or deployment
secret. Do not put a real password in source control. The URL format is:

```text
postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Optional pool settings are `SONIQ_DB_POOL_MIN_SIZE` (default `1`) and
`SONIQ_DB_POOL_MAX_SIZE` (default `5`). Set each instance's pool limits so the
sum across instances stays within PostgreSQL's connection limit. Use the
hosting provider's TLS settings for remote database connections.

## Create or update the schema

Run the migration command once as a deployment step, before starting or
updating backend instances:

```powershell
.\ml\.venv\Scripts\python.exe -m backend.migrate
```

It applies ordered SQL files from `backend/migrations/`, records each filename
and checksum in `schema_migrations`, and rejects edits to an already-applied
migration. A PostgreSQL advisory lock prevents two migration commands from
applying the same change simultaneously. Do not run this command independently
from each application instance.

The current migration creates event storage and history indexes. It does not
delete old events.

### Retention proposal (no cleanup implemented)

The one-semester requirement does not yet define an exact cutoff. Until the
team approves one, retain events and do not delete them. Before cleanup is
implemented, agree on:

- The authoritative semester start and end dates, and whether retention means
  a calendar semester or a rolling duration.
- The timezone used to calculate the cutoff.
- Whether age is measured from the event's observation time or the server's
  `received_at` time.
- Whether cleanup is manual or scheduled.

A cautious first design would use an administrator-triggered cleanup with a
preview count after the cutoff rule is approved. Using indexed `received_at` as
the time basis is a recommendation only; the team must approve the time basis.
Any automated schedule and actual deletion remain pending approval.

## Start the backend and check health

After the database owner approves the database target and the migration has
completed, launch from the repository root:

    .\backend\run_local_demo.ps1

The launcher uses the same project interpreter at ml/.venv, checks the local
model, then starts backend.app. It requires SONIQ_DATABASE_URL and startup is
not verified until the connection pool opens and the listening message appears.
In another PowerShell terminal, check the process endpoint:

    Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 5

A successful health response confirms that the HTTP process answered. It does
not independently prove database readiness, hardware connectivity, or warning
readiness; inspect the response's warning configuration fields separately.

## PostgreSQL integration tests

These tests require a dedicated PostgreSQL database. They skip unless
`SONIQ_TEST_DATABASE_URL` is set, and refuse a database name without a
separate `test` segment (for example, `soniq_test`). The test suite creates a
uniquely named temporary schema in that database and drops that schema when the
run ends. Never point the test URL at production or a database containing data
to keep.

Set the URL using local-only configuration, then run:

```powershell
.\ml\.venv\Scripts\python.exe -B -m unittest backend.tests.test_postgres_event_repository
```

The normal backend and SQLite unit tests do not need PostgreSQL:

```powershell
.\ml\.venv\Scripts\python.exe -B -m unittest backend.tests.test_app backend.tests.test_event_repository
```

## API integration behavior (provisional)

`POST /api/v1/events` processes requests with the existing `process_event()`
function, then saves the processed response. The existing HTTP 200 response is
sent only after the repository transaction commits. Invalid requests are not
stored. Missing and stale readings are stored with the statuses and warning
reasons produced by `process_event()`.

Because duplicate and database-failure HTTP behavior has not been approved,
the integration currently uses provisional mappings: duplicate event IDs
return HTTP 409 with `error.code=duplicate_event`; event write failures after
the server starts return HTTP 503 with `error.code=storage_unavailable`. The
normal `main()` startup path requires `SONIQ_DATABASE_URL` and opens the
connection pool before listening. Missing configuration or a connection
failure at startup prevents the server from starting; it cannot return an HTTP
503. The handler also returns 503 if constructed without a repository, but
that is not the normal `main()` startup path.

The proposed API response section is recorded in
`docs/INTERFACE_CONTRACT.md`; component owners and the dashboard owner still need
to approve these mappings before they are treated as stable. The dashboard
shows a duplicate-specific message, a storage-unavailable message, and keeps
validation errors described as rejected events.

Migrations remain an explicit, separate deployment step. The application does
not apply migrations when it starts. Configure SONIQ_DATABASE_URL in the local
PowerShell session, install the listed dependencies using the project
ml/.venv interpreter, run the migration once with that interpreter, then start
the service using backend/run_local_demo.ps1. The service creates and closes
its own connection pool during startup and shutdown.
