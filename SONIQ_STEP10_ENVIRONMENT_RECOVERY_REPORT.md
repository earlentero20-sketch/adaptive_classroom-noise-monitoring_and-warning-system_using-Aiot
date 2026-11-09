# SONIQ Step 10 — Environment Recovery Report

**Date:** 2026-11-09 (Asia/Manila)  
**Status:** **PARTIALLY RECOVERED; full integration remains BLOCKED.** With approval, Python 3.13.17 and Node.js LTS 24.20.0 were installed, and a new root `.venv` was created because the old one is tied to a missing executable under another Windows account. The backend suite now passes after correcting one test-only assertion; dashboard tests pass. PostgreSQL and ESP32 are still unavailable, and one ML test hits Windows Application Control. No application/API, firmware, model, database, or dashboard code was modified.

## Summary

The existing ML virtual environment remains nonportable: its `pyvenv.cfg` points to Python 3.13.15 at `[LOCAL_PATH]`, which does not exist on this PC. Its launcher still cannot start. The approved current-user Python 3.13.17 installation now runs directly at `[LOCAL_PATH]`; a new root `.venv` was created with it. The `py` launcher is still unavailable and the current shell's `python` command still resolves to the nonfunctional Windows Store alias, so use `.\.venv\Scripts\python.exe` directly. Existing ML package files were reused read-only via a process-scoped `PYTHONPATH` for tests; they were not reinstalled.

Node.js LTS 24.20.0 was installed with approval. Its package directory is outside the sandbox's readable paths and the current shell PATH was not refreshed, so the test runner required an approved out-of-sandbox invocation using the explicit installed executable. All 25 existing dashboard tests passed. The static dashboard has no package manifest or build system; Node is required for the existing tests, not to build the dashboard.

No PostgreSQL service/local listener or configured connection URL was found. The queried Windows serial-device classes returned no matching device/COM port. Step 8 leaves audio bridge/protocol implementation pending approval and hardware identification; neither is safe to implement without those prerequisites.

## Python inspection

| Check | Result |
|---|---|
| `[LOCAL_PATH] --version` | **PASSED:** `Python 3.13.17`. |
| `.\.venv\Scripts\python.exe --version` | **PASSED:** `Python 3.13.17`; root virtual environment created because the old environment targets another user's missing base interpreter. |
| `ml\.venv\Scripts\python.exe --version` | **BLOCKED:** launcher reports missing base executable at `[LOCAL_PATH]`. |
| `ml\.venv\pyvenv.cfg` | **VERIFIED:** records Python `3.13.15` and a base path under the other `admin` profile. |
| `py -0p` / `where.exe py` | **BLOCKED:** `py` command/launcher not found. |
| `where.exe python` | **BLOCKED:** no normal executable path found. `Get-Command python` points to the WindowsApps execution alias; attempting `python --version`/tests fails with “The file cannot be accessed by the system.” |
| Common Python install locations and registry roots | **PASSED after recovery:** no earlier install existed at current-user LocalAppData or standard Program Files; Python is now installed under current-user LocalAppData. The old admin-profile path remains absent. |
| Existing ML package imports | **PARTIAL:** numpy, scipy, librosa, sklearn, and joblib import via process-only `PYTHONPATH` pointing to the old venv's site-packages. Full MFCC extraction fails when Numba loads its compiled `_internal` extension; Windows reports “An Application Control policy has blocked this file.” |
| PostgreSQL driver directories | **MISSING:** `psycopg` and `psycopg_pool` not found in the old venv; no DB driver installed into the new venv. `backend/requirements.txt` declares `psycopg[binary,pool]>=3.2,<4`. No driver install was made because no PostgreSQL service/URL is configured. |
| New root `.venv` package list | **INSPECTED:** only `pip==26.2.2` is installed. `numpy`, `librosa`, and `psycopg_pool` imports fail there. The backend module itself imports successfully because optional inference/storage packages load later. |

Creating a usable new root `.venv` was necessary and completed after Python installation was approved. Existing ML package files were not copied or reinstalled; test runs reused them using process-only `PYTHONPATH`. No Python requirements were installed into the new root venv. Consequently the launcher can start degraded and pass health, but new-venv model inference needs the declared ML dependencies and database persistence needs psycopg plus a configured PostgreSQL server.

## Dashboard environment

- **VERIFIED:** `dashboard/README.md` documents a static HTML/CSS/ES-module app, no frontend build/package dependency, and `node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs` for tests.
- **VERIFIED:** those tests import Node built-ins (`node:test`, `node:assert/strict`, `node:fs/promises`); no `dashboard/package.json` exists. Node is required for this existing test runner, not for the page's static architecture.
- **PASSED (structural check only):** `dashboard/index.html`, `dashboard/dashboard.mjs`, `dashboard/backend-adapter.mjs`, and both existing test modules exist. Adapter defaults to `http://127.0.0.1:8000` and references `/health`, `/api/v1/events`, and `/api/v1/classify`.
- **PASSED:** Node.js LTS `24.20.0` ran the existing dashboard tests from its installed path; 25 passed, 0 failed. The command needed elevated access to the WinGet package directory because sandbox access was denied. No browser/live API check was performed.
- **PASSED (local integration smoke):** static dashboard served HTTP 200 on loopback port 18126; a health request carrying `Origin: http://127.0.0.1:18126` returned HTTP 200 with matching `Access-Control-Allow-Origin`. Event history returned expected HTTP 503 due to no DB. Both temporary servers were stopped. This checks static serving and CORS, not browser rendering or persistence.

## PostgreSQL

- Process `SONIQ_DATABASE_URL`: **unset**; `SONIQ_TEST_DATABASE_URL`: **unset**; root `.env`: **absent**.
- `Get-Service -Name '*postgres*'`: no matching service. `Test-NetConnection 127.0.0.1 -Port 5432`: false. `C:\Program Files\PostgreSQL` and `where.exe psql` did not resolve an installation/client.
- A remote/nonstandard server cannot be checked without an approved URL; its status is **NOT TESTED**, not assumed absent.
- `.env.example` already supplies a placeholder URL format, not real credentials. `backend/start_backend.py` loads allowlisted settings from the root `.env`; `backend.app` uses process environment. No secret was read or printed.
- Existing schema/data were not connected, read, migrated, or changed. The database owner must supply the already-approved existing server/database/role privately and confirm `events`/`schema_migrations` before any migration.
- **Backend smoke:** the new root `.venv` imported and launched `backend.app` without `PYTHONPATH` on loopback port 18124; `/health` returned `status=online`, warning status `not_ready`; `/api/v1/events` returned HTTP 503. The process was stopped after the check. This verifies process health only, not persistence.
- **Backend tests:** initially exposed a faulty assertion in `backend/tests/test_app.py`; after the test-only correction, 67 tests passed with 1 skip.

## ESP32 / Windows device detection

The following read-only checks yielded no matching present serial/ESP32-class device:

- `Get-PnpDevice -PresentOnly` filtered for Ports, ESP32, USB Serial, CH340, CP210, FTDI, UART, and COM names: no rows.
- `Get-CimInstance Win32_SerialPort`: no rows.
- `Get-CimInstance Win32_PnPEntity` filtered for ESP32/USB Serial/CH340/CP210/FTDI/UART: no rows.

Thus no COM port or board identity is available to configure. This is a Windows enumeration result for this session; it does not establish what hardware may be available elsewhere. Existing source configuration is not physical evidence. Do not implement Step 8 serial firmware/receiver until the board, microphone, driver/COM port, I2S data alignment, free memory, baud support, and approved packet protocol are confirmed.

## Next actions requiring external configuration or approved software handling

1. Resolve the ML native extension Application Control block through the device administrator/approved software policy; do not bypass security controls. Then rerun the ML suite and actual inference only with approved model/audio data.
2. Backend tests now pass after correcting the stub-server assertion in `backend/tests/test_app.py`; no production route or behavior changed.
3. After the ML Application Control issue is resolved and package installation is approved, install the declared ML requirements into the new root `.venv` for model inference. For persistence, first configure the existing PostgreSQL service/URL, then install the declared psycopg driver if absent and approved.
4. Restart the shell so the approved Node installation's PATH changes take effect; direct Node executable was used successfully for the tests.
5. Configure the existing PostgreSQL service/database and private `.env` without sharing credentials. Do not install a replacement DB or reset/migrate blindly.
6. Connect the actual ESP32 and repeat PnP/CIM checks; then follow the Step 8 approval gate before any audio bridge implementation.

## Preservation

No backend application, firmware, model/data, schema, `.env`, or dashboard code was changed; Python and Node were installed with approval and a new ignored root venv was created. One existing backend test assertion was corrected; no Python package dependencies were installed. No Git reset/clean/restore/staging/commit/push was run. Final `git status --short` shows 9,416 staged deletions, 32 untracked paths, and zero other entries.

Step 10 deliverables are the three reports in the repository root. The only existing source file edited was the already-untracked working copy `backend/tests/test_app.py`, to make its private-bind test assert the address recorded by its stub rather than a nonexistent `call_args` attribute. The original staged deletion remains untouched; nothing was staged.
