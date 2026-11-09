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

## Run locally on Windows

The dashboard is static and has no build or package-install step. From the
repository root, run:

```powershell
.\start_soniq.bat
```

This opens the dashboard server in a separate window at
`http://127.0.0.1:8001/` and runs the backend in the current window at
`http://127.0.0.1:8000/`. The batch launcher does not invoke PowerShell or
change Windows execution policy. Its Python helper loads only documented
SONIQ variables from `.env` into the backend process without printing values.
Existing process environment values take precedence over `.env`.

The launcher uses a valid root `.venv` first, then `ml/.venv`. It does not
install packages, replace an environment, or silently use global Python. If
neither project environment is usable, create a fresh root environment and
install the declared backend/ML requirements:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
```

Configure a private `.env` from `.env.example` if PostgreSQL is ready; do not
commit real credentials. The backend starts in degraded mode when PostgreSQL
is unavailable: health can respond, while event history and submission show a
storage error. WAV classification requires `SONIQ_AUDIO_MODEL_PATH` to point
at a trusted compatible local artifact; this launcher does not auto-select a
model. The dashboard displays actual backend responses and explicit empty,
loading, stale, unavailable, and error states; it does not create events or
calculate classifications or warnings.

To stop the backend, press Ctrl+C in its window. Close the dashboard server
window to stop static serving. For database setup and migrations, see [the
PostgreSQL guide](../docs/POSTGRES_LOCAL.md). For ESP32 LAN setup, see [the LAN
guide](../docs/LAN_CONNECTIVITY.md).

The dashboard defaults to backend URL `http://127.0.0.1:8000`. For another
local backend URL, use the `api` query parameter, for example
`http://127.0.0.1:8001/?api=http://127.0.0.1:8002`. Browser CORS remains
loopback-only, and classification remains a loopback-only API route.

## Tests

```powershell
node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

Adapter tests use controlled response fixtures for API contract and UI logic;
they are not live database, ML artifact, or hardware integration tests.
