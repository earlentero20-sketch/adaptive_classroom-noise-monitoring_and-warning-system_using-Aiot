# SONIQ Dashboard

The dashboard is a static HTML/CSS/ES-module application with no frontend
build step or package dependencies. It reads event history and health from the
SONIQ backend and sends user-selected WAV files to the existing classifier.
It does not create example events, calculate warning decisions, or simulate
readings.

## API configuration

The dashboard resolves the backend base URL in this order:

1. `window.SONIQ_API_BASE_URL` (injected by a deployment).
2. `<meta name="soniq-api-base" content="...">` in `index.html`.
3. The `api` query parameter (for example `?api=http://127.0.0.1:8000`).
4. `http://127.0.0.1:8000`.

Only `http:` and `https:` URLs without embedded credentials are accepted.
No credentials are stored in the dashboard. The local backend grants browser
CORS access only to loopback origins; serve this dashboard over HTTP rather
than opening `index.html` as a `file:` URL.

## Backend integration

| Endpoint | Method | Dashboard use |
|---|---|---|
| `/health` | `GET` | Backend reachability and warning-configuration readiness. |
| `/api/v1/events?limit=10&offset=0` | `GET` | Persisted PostgreSQL event history, newest first; pagination uses `limit` and `offset`. |
| `/api/v1/classify` | `POST` | Selected WAV bytes with `Content-Type: audio/wav`; displays the exact returned class, optional uncalibrated model probability, model/evaluation state, and observation time. |

The classify endpoint does not return a sound-level reading or evaluate
warnings. Event warning decisions and reasons are displayed only from stored
event responses. A warning shown in the UI is not evidence that an ESP32 or
physical buzzer received it. Sensor status is shown only when an event provides
it, and is not physical verification.
CSV export is enabled only when actual event records are loaded. Spreadsheet
formula-like text fields are exported as text.

The backend has no WebSocket or Server-Sent Events stream. The dashboard polls
health and the current event-history page every 30 seconds while visible.
Health and event-history requests abort after 15 seconds; WAV classification
requests abort after 120 seconds. Requests do not overlap; polling and stale-age
timers stop when the page is hidden or left. Event data older than 60 seconds is
marked stale. If a refresh fails after a successful read, the last successful
records remain visible and are explicitly marked stale/refresh-failed.

## UI states

- **Loading** — requests are in progress.
- **Empty** — the backend returned an empty event list.
- **Error** — a request failed or the response was malformed.
- **Unavailable** — the endpoint is missing or does not provide the required data.
- **Stale** — retained data is old or the latest refresh failed.
- **Success** — actual backend data is displayed.
- **Unknown** — the backend did not provide a value or decision.

## Run locally

The backend requires a configured PostgreSQL database and its schema migration.
Follow [the PostgreSQL setup guide](../docs/POSTGRES_LOCAL.md) to create the
project environment, install dependencies, configure `SONIQ_DATABASE_URL`, and
apply migrations. Python does not load `.env` automatically; load the URL into
the current PowerShell session without printing it:

```powershell
$databaseLine = Get-Content .env | Where-Object { $_ -match '^SONIQ_DATABASE_URL=' } | Select-Object -First 1
if (-not $databaseLine) { throw "SONIQ_DATABASE_URL is missing from .env" }
$env:SONIQ_DATABASE_URL = $databaseLine.Substring('SONIQ_DATABASE_URL='.Length)
.\.venv\Scripts\python.exe -m backend.app
```

This starts the database-backed API from the root project environment. Warning
decisions remain disabled until Romeo confirms and configures the approved
threshold and freshness window. WAV classification also remains unavailable
until Earl supplies a compatible local model artifact and
`SONIQ_AUDIO_MODEL_PATH` points to it. The optional `run_local_demo.ps1`
launcher currently expects a separate `ml\.venv` and model artifact that are
not present in this checkout; its hard-coded demo warning values also require
project approval before use.

In another terminal, serve the dashboard from the repository root:

```powershell
.\backend\run_local_demo.ps1
```

In another terminal, serve the dashboard:

```powershell
python -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8001/`. Confirm backend readiness at
`http://127.0.0.1:8000/health`. PostgreSQL must be reachable for event-history
requests; an unavailable database produces an API error, not an empty history.
No real ESP32/hardware integration is implied by these local software checks.

## Tests

```powershell
node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

Adapter tests use controlled response fixtures for API contract and UI logic;
they are not live database, ML artifact, or hardware integration tests.
