# SONIQ PostgreSQL backend storage

The PostgreSQL repository is separate from the HTTP handler. It stores the
processed event response supplied by `backend.app.process_event()` and does
not repeat validation, timestamp freshness checks, or warning calculations.
Normal backend startup does not run schema migrations.

## Windows PostgreSQL installation

The repository does not specify a PostgreSQL database name or application
role. Its current migration creates `events` plus the migration runner's
`schema_migrations` table in whichever database is selected by
`SONIQ_DATABASE_URL`; it does not create a database or login role.

As of November 2026, PostgreSQL 18.6 is the current supported major release.
The official PostgreSQL Windows download page links to the EDB interactive
installer. After confirming that PostgreSQL is not already installed, an
administrator can install the current 18.x package with:

```powershell
winget install --id PostgreSQL.PostgreSQL.18 --exact --version 18.6-5
```

In the installer, keep the default local port `5432`, install the command-line
tools and pgAdmin, and set a private password for the initial `postgres`
administrator. Do not put that password in a command, source file, or chat.
PostgreSQL's supported versions and Windows installer are listed at
[PostgreSQL versioning](https://www.postgresql.org/support/versioning/) and
[PostgreSQL for Windows](https://www.postgresql.org/download/windows/).

For the application connection, create a non-superuser login role named
`soniq_app` and a database named `soniq_local` owned by that role (these are
local setup choices, not names mandated by the code). Set the role's password
in pgAdmin's role dialog. In pgAdmin, create the database with owner
`soniq_app`. Do not use the `postgres` administrator login for the app. The
database role needs to be able to create the tables in its own database so the
project migration can run.

Confirm the service is running in Windows Services and that port 5432 is
listening. For a database connection check, use pgAdmin's Query Tool or run
`psql -h 127.0.0.1 -p 5432 -U soniq_app -d soniq_local -c "select current_database();"`
and enter the password only at the prompt.

## Dependencies

Install the existing ML dependencies and the backend database driver from the
repository root:

```powershell
py -m venv ml/.venv
.\ml\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r backend/requirements.txt
```

The repository's root `.venv` may be used if it already exists; the
`run_local_demo.ps1` helper specifically expects a separate `ml/.venv`.
Activate the chosen environment before running `python -m backend.app`. The
backend requirement uses Psycopg 3 with its binary implementation and
connection-pool extra. The synchronous pool suits the current synchronous
backend. Pool connection contexts commit on success and roll back on errors.

## Environment file and connection settings

Copy `.env.example` to `.env`, then replace the URL's `USER`, `PASSWORD`, and
`DATABASE` with the actual local role, its password, and database name. URL
encode reserved characters in the username or password. `.env` is ignored by
Git; `.env.example` is the safe placeholder template.

The Python backend does **not** automatically load `.env`. In each PowerShell
window where you run the migration or backend, load its simple `KEY=value`
entries into that process without echoing their values:

```powershell
Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
if ([string]::IsNullOrWhiteSpace($env:SONIQ_DATABASE_URL)) {
    throw "SONIQ_DATABASE_URL was not loaded"
}
```

Keep the `.env` file private and do not paste its contents into chat or
terminal commands. To verify configuration without disclosing it, print only
whether `SONIQ_DATABASE_URL` is set.

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

Set `SONIQ_DATABASE_URL` from the local `.env` instructions above. Never put a
real password in source control. Use the actual host, port, role, and database
you created; the repository does not choose a database name.

```text
postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Optional pool settings are `SONIQ_DB_POOL_MIN_SIZE` (default `1`) and
`SONIQ_DB_POOL_MAX_SIZE` (default `5`). Set each instance's pool limits so the
sum across instances stays within PostgreSQL's connection limit. Use the
hosting provider's TLS settings for remote database connections.

## Create or update the schema

Run the migration command once before starting the backend. From the project
root, activate `.venv` if it is the existing configured environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.migrate
```

It applies ordered SQL files from `backend/migrations/`, records each filename
and checksum in `schema_migrations`, and rejects edits to an already-applied
migration. A PostgreSQL advisory lock prevents two migration commands from
applying the same change simultaneously. Do not run this command independently
from each application instance.

The existing `backend/migrations/001_create_events.sql` creates the
`events` table and its history indexes. The migration runner records applied
versions and checksums in `schema_migrations`. It does not delete old events.

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

After the migration has completed, load `.env` in the same PowerShell window,
activate `.venv`, and launch from the repository root:

    python -m backend.app

The direct backend entry point requires the database connection, but the
model is loaded only when classification is requested. The helper script
`backend/run_local_demo.ps1` also performs a model-artifact preflight and
expects `ml/.venv`; the command above uses the existing root `.venv` instead.
Startup is successful only after the PostgreSQL pool opens and the server
reports its listening address. In another terminal, check health:

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
