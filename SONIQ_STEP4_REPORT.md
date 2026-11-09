# SONIQ Step 4 — Windows Startup, Environment, and Dashboard

**Date:** 2026-11-09  
**Status:** Startup path and instructions added; end-to-end startup **BLOCKED** by the unavailable project Python interpreter. Dashboard behavior was reviewed from source; browser/live API verification was not possible.

At inspection time, `.env`, `SONIQ_DATABASE_URL`, and `SONIQ_AUDIO_MODEL_PATH` were absent. The root `.venv` executable was absent; `ml/.venv` existed but could not launch because its base Python path is missing.

## Startup changes

Added `start_soniq.bat` and `backend/start_backend.py`.

- The batch file resolves the repository root from its own location.
- It uses a runnable root `.venv` first and then a runnable `ml/.venv`. It does not silently use global Python, install packages, or overwrite an environment. If neither works, it prints a fresh-environment command and stops.
- It checks that the selected Python can import `backend.app` before opening services.
- It starts the static dashboard on `127.0.0.1:8001` in its own window, then runs the backend in the current window.
- The Python helper loads only documented SONIQ environment keys from `.env` into the backend child process; explicit process environment values take precedence. It does not print values or run migrations.
- The batch file invokes the selected Python directly; it does not call PowerShell or change Windows execution policy.
- If the database URL is missing, the helper warns and the backend uses the Step 3 degraded mode. If no model path is configured, the helper says WAV classification will be unavailable. No experimental model is auto-selected.

No frontend framework or package dependency was added. No private credential was introduced.

## Dashboard integration review

The existing static frontend is preserved. Source inspection confirms:

- Base URL priority is injected `window.SONIQ_API_BASE_URL`, HTML meta setting, `?api=` query parameter, then `http://127.0.0.1:8000`.
- Health comes from `GET /health`; event history uses paginated `GET /api/v1/events`; selected WAV files are posted to `POST /api/v1/classify`.
- Classification labels/probabilities and warning fields are rendered from backend responses. JavaScript does not implement model classification or warning policy.
- The UI has loading, empty, stale, unavailable, invalid-response, backend-error, and refresh-error handling. Network calls use timeouts; it keeps last successful history marked stale if a later refresh fails.
- A warning shown in the UI comes from a backend event. It does not claim that physical hardware or a buzzer responded.
- Local dashboard origin `127.0.0.1:8001` is accepted by existing loopback CORS. LAN dashboard browsing remains outside this step and the existing CORS allowlist.
- The classification endpoint still requires a loopback client and a configured trusted model artifact; the startup launcher does not weaken that access restriction.

The dashboard's adapter and UI tests use controlled fixtures; they are not proof of live PostgreSQL, model, or hardware integration.

## Files changed

- `start_soniq.bat` — Windows entry point for both local services.
- `backend/start_backend.py` — standard-library `.env` loader and backend starter.
- `dashboard/README.md` — corrected the run instructions and documents the new launcher, URLs, environment behavior, and setup path.
- `SONIQ_STEP4_REPORT.md` — this report.

No dashboard HTML, CSS, or JavaScript, API, database schema, or model was changed.

## Verification

| Check | Result | Detail |
|---|---|---|
| Python helper syntax/import | **BLOCKED** | Could not run `py_compile` or import check because the available project Python interpreter cannot start. |
| Batch launcher missing-runtime path | **PASSED** | Ran `start_soniq.bat`; it detected that neither project interpreter was runnable, displayed the expected setup instructions, and exited before starting services. |
| Python environment | **BLOCKED** | Root `.venv` is absent. `ml/.venv` exists but points to missing `[LOCAL_PATH]`. Python import check could not run. |
| Backend startup | **NOT TESTED** | No runnable interpreter. |
| Dashboard server/browser | **NOT TESTED** | No runnable Python web server or browser was available. |
| JavaScript syntax checks | **BLOCKED** | `node` is not installed/available; `node --check` could not run. |
| Dashboard/API fixture tests | **BLOCKED** | Node test runner unavailable. No live backend was started. |
| Dashboard/API live communication | **NOT TESTED** | No backend/browser session; no live health/events/classification request was made. |
| Dependencies installed | **NO** | No package installation was attempted. |

## Exact startup commands

From PowerShell or File Explorer, at the repository root:

```powershell
.\start_soniq.bat
```

Then open `http://127.0.0.1:8001/`. The backend health endpoint is
`http://127.0.0.1:8000/health`. Press Ctrl+C in the backend window to stop it;
close the dashboard window to stop static serving.

If the launcher reports there is no usable project environment, first install
a supported Python version, then create a fresh root environment and install
the declared backend/ML requirements:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
```

Configure `.env` privately from `.env.example` if PostgreSQL is available; do
not commit real credentials. Run the existing migration as a separate,
intentional database setup step using the configured interpreter and approved
database. No migration is run by the launcher.

For a separate/manual backend launch after creating `.venv`:

```powershell
.\.venv\Scripts\python.exe backend\start_backend.py
```

For the dashboard alone in another terminal:

```powershell
.\.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

## Remaining blockers

- The project needs a valid Python installation and an environment with its declared dependencies before the launcher can start.
- PostgreSQL, model artifact loading, and event history depend on the corresponding local configuration and are not verified here.
- Install/provide Node.js only if running the existing dashboard test suite is required; no frontend build tool is needed.
- Browser and live API checks remain to be performed on the demonstration computer.
