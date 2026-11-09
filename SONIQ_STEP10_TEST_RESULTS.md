# SONIQ Step 10 — Test Results

**Date:** 2026-11-09 (Asia/Manila)  
**Overall:** Python and Node runtimes were restored with approval; the backend suite passes after a test-only assertion repair, the dashboard suite passes, and backend health/static serving were smoke-checked. PostgreSQL, actual model inference, and hardware remain blocked. ML has one Application Control error. Tests reused existing ML package files via process-only `PYTHONPATH`; no Python packages were installed.

## Python and existing suites

| Command/check | Status | Result |
|---|---|---|
| `& '[LOCAL_PATH]' --version` | **PASSED** | Python 3.13.17 installed with approval. |
| `& .\.venv\Scripts\python.exe --version` | **PASSED** | Python 3.13.17 in new root venv; creation was necessary because old venv targets another user's missing base executable. |
| `& .\ml\.venv\Scripts\python.exe --version` | **BLOCKED** | Existing launcher still cannot find `[LOCAL_PATH]`. |
| `py -0p` / `where.exe py` | **BLOCKED** | `py` is not recognized / no executable found. |
| `where.exe python` | **BLOCKED** | No normal Python executable found. `Get-Command python` resolves to `[LOCAL_PATH]` (Store alias); it cannot launch. |
| Initial backend suite with process-only ML `PYTHONPATH` | **FAILED, then repaired** | 67 tests ran: 65 passed, 1 skipped, 1 errored. `test_main_binds_to_private_lan_address_from_environment` replaced `ConfiguredHTTPServer` with a `StubServer` class, then read `server_class.call_args`; the class has no `call_args`. |
| Corrected backend suite: `& .\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests` | **PASSED** | 67 tests ran; `OK (skipped=1)`. The existing test now asserts the address recorded by its stub. No production code/API changed. |
| ML suite with process-only ML `PYTHONPATH`: `& .\.venv\Scripts\python.exe -B -m unittest discover -s ml/tests -v` | **FAILED / BLOCKED BY POLICY** | 67 tests ran: 65 passed, 1 skipped, 1 errored. `test_synthetic_baseline_artifact_round_trips_through_backend_runtime` reaches MFCC extraction, then Windows Application Control blocks Numba's compiled `numba.np.ufunc._internal` extension (“An Application Control policy has blocked this file”). No security control was bypassed. |
| Import probe with old ML site-packages on process-only `PYTHONPATH` | **PARTIAL** | numpy, scipy, librosa, sklearn, and joblib imports succeeded; psycopg import failed because package is absent. Numba's lazy compiled path is blocked at MFCC use. |
| New root `.venv` `pip list --format=freeze` / import probes | **PASSED (inspection)** | Only `pip==26.2.2` is installed. `import backend.app` passes; imports for numpy, librosa, and psycopg_pool fail. No packages were installed. |

Python 3.13.17 and Node.js LTS 24.20.0 were installed using the user's approval. The new root `.venv` is ignored by Git. No Python dependency package was installed. The old ML package files were reused read-only through `PYTHONPATH` for the ML suite and initial backend run; the final backend suite ran without it.

### Exact commands used

The first Python suite runs exposed the old ML package directory only to each process. After the backend test-only assertion fix, the full backend suite also passed without that `PYTHONPATH`:

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
.\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -B -m unittest discover -s ml/tests -v
Remove-Item Env:PYTHONPATH
.\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests
```

The dashboard tests used the installed Node 24.20.0 executable directly because its WinGet package directory was not accessible inside the sandbox:

```powershell
& '[LOCAL_PATH]' --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

The backend smoke used the new venv on loopback port 18124 with `BACKEND_HOST=127.0.0.1` and `BACKEND_PORT=18124`, queried `/health` and `/api/v1/events`, then stopped the temporary process. The dashboard/CORS smoke used:

```powershell
& .\.venv\Scripts\python.exe -m http.server 18126 --bind 127.0.0.1 --directory dashboard
Invoke-WebRequest -UseBasicParsing -Headers @{Origin='http://127.0.0.1:18126'} http://127.0.0.1:18125/health
Invoke-WebRequest -UseBasicParsing -Headers @{Origin='http://127.0.0.1:18126'} http://127.0.0.1:18125/api/v1/events
```

The page request returned 200, health returned 200 with the expected loopback CORS header, and event history returned the expected 503 without a database. Both temporary servers were stopped; no persistent listener remains. The documented everyday launcher is `.\start_soniq.bat`; it was not invoked because it opens a separate dashboard window. Its Python preflight import was checked directly and passed.

## Dashboard

| Command/check | Status | Result |
|---|---|---|
| Read `dashboard/README.md` and test imports | **PASSED (inspection)** | Static HTML/CSS/ES modules; no build step; tests use Node built-ins `node:test`, `node:assert/strict`, and `node:fs/promises`. Node is required for these tests. |
| `Test-Path` for dashboard HTML/modules/test files | **PASSED (structural check)** | `index.html`, `dashboard.mjs`, `backend-adapter.mjs`, and both test files exist. |
| Check `dashboard/package.json` | **PASSED (inspection)** | No package manifest/build system exists. No framework/dependency introduced. |
| Adapter route/default inspection | **PASSED (source check)** | Loopback default `http://127.0.0.1:8000`; paths include `/health`, `/api/v1/events`, `/api/v1/classify`. This is not a live API check. |
| Node.js version | **PASSED** | Installed Node.js LTS `v24.20.0`; current shell PATH is stale, so invoked the executable from its WinGet package location. |
| `node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs` via installed Node executable | **PASSED** | 25 passed, 0 failed. These are browser-independent tests, not live backend/database integration. |
| Static dashboard/backend health CORS smoke | **PASSED (partial)** | Static page served HTTP 200 on loopback port 18126; health at backend port 18125 returned HTTP 200 and matching `Access-Control-Allow-Origin`. Temporary servers were stopped. |
| Browser/dashboard event rendering | **NOT TESTED** | No browser session and no persisted events available. |

## PostgreSQL and API

| Check | Status | Result |
|---|---|---|
| Process `SONIQ_DATABASE_URL`, `SONIQ_TEST_DATABASE_URL`, root `.env` | **PASSED (inspection)** | Both variables unset; `.env` absent. No credentials exposed. |
| `Get-Service -Name '*postgres*'` | **BLOCKED / NOT FOUND** | No matching local Windows service. A nonstandard or remote server remains unverified. |
| `Test-NetConnection 127.0.0.1 -Port 5432` | **FAILED (availability check)** | `False`; no local listener accepted the connection. |
| `where.exe psql`; standard PostgreSQL install root | **BLOCKED / NOT FOUND** | No client executable or `C:\Program Files\PostgreSQL` path found. |
| Database authentication/schema/events | **NOT TESTED** | No URL/credentials/client/listener. No schema inspection, insert, retrieval, or migration occurred. |
| Direct backend import using new root venv | **PASSED** | `& .\.venv\Scripts\python.exe -c "import backend.app"` exited 0. |
| Backend smoke on loopback port 18124 | **PASSED (degraded-mode health only)** | `GET /health` returned `status=online`, warning status `not_ready`. Temporary process was stopped after the check. |
| `GET http://127.0.0.1:18124/api/v1/events` during smoke | **PASSED (degraded-mode behavior)** | Returned the expected HTTP 503 because no repository/DB URL was configured. No event was generated. A second dashboard/CORS smoke on port 18125 also observed 503. |
| Event history/persistence | **BLOCKED** | No PostgreSQL connection. No event was fabricated or inserted. |

## ESP32 / Windows device checks

| Command/check | Status | Result |
|---|---|---|
| `Get-PnpDevice -PresentOnly` filtered for Ports/ESP32/USB serial bridge names | **PASSED (inspection)** | No matching present device rows. |
| `Get-CimInstance Win32_SerialPort` | **PASSED (inspection)** | No rows; no COM port identified. |
| `Get-CimInstance Win32_PnPEntity` filtered for ESP32/USB Serial/CH340/CP210/FTDI/UART | **PASSED (inspection)** | No rows. |
| Board identity, serial baud, microphone, memory, real capture | **NOT TESTED** | No hardware detected. Source settings are not physical verification. |
| Step 8 USB receiver/firmware | **BLOCKED / REQUIRES APPROVAL** | Protocol is not implemented or approved; no firmware change made. |

## Model, warning, and end-to-end integration

| Check | Status | Result |
|---|---|---|
| Load existing trained artifact | **NOT TESTED** | No `SONIQ_AUDIO_MODEL_PATH` configured; new venv also lacks the declared ML dependencies. Artifacts unchanged. |
| Classify a real WAV using existing model | **BLOCKED** | MFCC extraction hits the Numba Application Control block. The active manifest identifies its dataset as `local_only_expanded_school_demo_unreviewed` and has `evaluation=null`; those WAVs were not used for a demonstration prediction. No classification was generated. |
| Transfer ESP32 audio / assemble WAV | **NOT TESTED** | Firmware currently sends event JSON only; no serial bridge exists and no device was detected. |
| Persist an actual classification event and retrieve it | **BLOCKED** | No model result, database connection, or backend. |
| Dashboard displays a real persisted event | **NOT TESTED** | No event/backend/browser runtime. |
| Warning policy evaluation | **NOT TESTED** | No actual classification with verified confidence and calibrated SPL. Preserve `confident=false`, SPL null/uncalibrated, and buzzer disabled. |
| Complete hardware-to-dashboard demonstration | **BLOCKED** | Prerequisite runtime, database, hardware, transport approval, and live tests are missing. |

## Git state check

**PASSED:** final status retains the existing 9,416 staged deletions, has 32 untracked paths and zero other entries. The new `.venv` is ignored; the already-untracked `backend/tests/test_app.py` working copy was edited only to correct its failing assertion. Nothing was staged.
