# SONIQ Step 10 — Remaining Blockers and Required Actions

**Current decision:** **BLOCKED for full integration.** Python and Node were installed with approval, a root venv was created, the backend suite passes after a test-only repair, backend health works in degraded mode, and dashboard tests pass. PostgreSQL and ESP32 remain unavailable; one ML test is blocked by Windows Application Control. Nothing here claims that SONIQ is fully running.

## 1. Python runtime (recovered; ML policy blocker remains)

### Evidence

- Root `.venv` now exists with Python 3.13.17; it was created after installation approval because the old environment is not portable.
- Existing `ml/.venv` was created under Windows user `admin`; its `pyvenv.cfg` requires Python 3.13.15 at `[LOCAL_PATH]`, which is absent on this `PC-21` machine.
- `py -0p` and `where.exe py` fail because the launcher is not installed. `where.exe python` finds no executable; `python` resolves to the Windows Store alias and cannot launch. Use `& .\.venv\Scripts\python.exe`.
- The old ML venv has package directories for NumPy, SciPy, librosa, scikit-learn, and joblib. These import through process-only `PYTHONPATH`, but MFCC extraction fails when Application Control blocks Numba's compiled `_internal` extension. `psycopg`/`psycopg_pool` are absent; no dependencies are installed in the new root venv.

### Recovery completed and remaining dependency work

1. **Completed with user approval:** Python 3.13.17 installed for the current user using:

   ```powershell
   winget install --id Python.Python.3.13 --exact --scope user --accept-package-agreements --accept-source-agreements
   ```

2. **Completed:** because the existing venv points at another user's missing Python and cannot be relocated safely, create a new root `.venv`:

   ```powershell
   & '[LOCAL_PATH]' -m venv .venv
   .\.venv\Scripts\python.exe --version
   ```

3. Existing ML package files were reused read-only through process-only `PYTHONPATH` for test runs; basic imports pass, but MFCC use hits the Application Control restriction. Do not bypass the policy. Resolve it through the device administrator or an approved package location, then rerun ML/inference. No Python requirements were installed into the new root venv.

The Python installation and new venv creation were completed under the user's approval. Additional Python package installation, security-policy change, or test-source edit requires separate approval where applicable.

## 2. Node runtime (recovered for dashboard tests)

The dashboard itself is static and requires no Node build/install to serve. Its existing test suite uses Node's built-in `node:test` and `node:assert/strict`, so Node is required only to run those tests and syntax tooling. Node.js LTS 24.20.0 was installed with approval and the existing suite passed 25/25 using its explicit WinGet path. The current shell PATH needs a refresh before the plain `node` command is available. Run:

```powershell
node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

No frontend framework or npm dependencies are needed.

## 3. Restore the existing PostgreSQL connection (owner configuration required)

- No local PostgreSQL Windows service or default install root was found; local TCP `127.0.0.1:5432` failed.
- `SONIQ_DATABASE_URL` and `SONIQ_TEST_DATABASE_URL` are unset; root `.env` is absent. A remote configured server cannot be checked without the approved URL.
- Backend driver requirements are `psycopg[binary,pool]>=3.2,<4`; driver directories are absent from the broken venv. Do not switch to SQLite or another database.

Required actions: database owner identifies/starts the already-existing PostgreSQL server and database, privately configures a dedicated least-privilege `SONIQ_DATABASE_URL` in root `.env`, and confirms the existing `events` table and `schema_migrations` ledger. The URL shape is `postgresql://USER:PASSWORD@HOST:5432/soniq_db`; use actual approved details locally and URL-encode reserved characters. Never send the password in chat. `backend/start_backend.py` reads allowlisted `.env` settings without printing values. Do not run migration 001 until the live schema/ledger is inspected; it creates `events` without `IF NOT EXISTS`.

After runtime/config are available, launch via `start_soniq.bat`, check `GET /health`, then check event history and an actual event write/read. Health alone is not DB readiness. No event should be fabricated for this check.

## 4. Detect and identify actual ESP32 (hardware/user action required)

This session found no matching present devices in `Get-PnpDevice -PresentOnly`, no rows in `Win32_SerialPort`, and no matching ESP32/USB-serial rows in `Win32_PnPEntity`. Thus there is no COM port to configure now. Troubleshoot on the demonstration PC:

1. Use a known data-capable USB cable and connect directly to the PC (avoid a charge-only cable/hub for initial detection). Observe Windows connection sound and Device Manager refresh.
2. Run the same PnP/CIM queries again; inspect **Other devices** and Device Manager status/details for hardware IDs (VID/PID) and error codes. Do not infer the board or adapter from its firmware's INMP441 log.
3. Only after identifying the USB-UART chip from its hardware ID, install its vendor driver if Windows reports one missing. Do not guess CH340/CP210x/FTDI.
4. Re-run `Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,PNPDeviceID`, record the observed COM number, and close Arduino Serial Monitor before another program opens it.
5. Identify ESP32 board revision, microphone/interface, wiring, I2S sample alignment, free RAM/PSRAM, Arduino core, and supported baud. Test real microphone PCM conversion and throughput before any bridge implementation.

Step 8's serial format, opt-in firmware mode, optional pyserial receiver, and audio retention need explicit project approval. Actual hardware compatibility has not been established, so do not modify firmware or add a receiver yet. Preserve the current event-only behavior and buzzer-disabled state.

## 5. Resume integration only after prerequisites

1. Resolve the native Numba DLL Application Control block through approved device-admin policy; rerun ML tests and inference only with approved model/audio data. The backend test's stub assertion has been corrected and all 67 backend tests now pass (one skipped). The backend health smoke also passed.
2. Restore the existing PostgreSQL service/config and verify safe event insert/read using a genuine source event; dashboard must show the stored response. Install the declared psycopg driver only after DB availability/configuration and separate approval.
3. Obtain Step 8 transport/protocol/privacy approval and verify actual hardware. Then implement the narrowest opt-in serial bridge and test packet corruption, loss, timeout, incomplete frame, reconnect, and duplicate capture.
4. Keep `classification.confident=false` and SPL null/uncalibrated without approved confidence semantics and reference-meter calibration; verify warnings stay off and physical buzzer remains disabled.

## 6. Git preservation

The 9,416 staged deletions and all prior untracked files are preserved. Step 10 adds only its three report files as untracked. The new `.venv` is ignored. No Git mutation command was run. Review the exact `git status --short` before any future operation; do not mass-stage or clean this tree.
