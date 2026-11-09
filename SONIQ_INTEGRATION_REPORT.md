# SONIQ Integration Report

**Date:** 2026-11-09 (Asia/Manila)  
**Readiness:** **PARTIALLY READY** — backend, persistence, dashboard, ML runtime, and firmware code are present, but runtime, live database, full audio/event lifecycle, and hardware verification remain incomplete.  
**Detailed inventory:** [SONIQ_AUDIT_REPORT.md](SONIQ_AUDIT_REPORT.md)

## Verified features

**Code-level verified by inspection:**

- The backend implements health, persisted event listing/creation, and a separate local WAV classification route.
- Event validation and warning decisions live in the backend. Missing or invalid warning configuration fails closed.
- PostgreSQL credentials are read from `SONIQ_DATABASE_URL`; the schema migration creates the events table without a destructive recreate.
- The dashboard consumes backend health/events/classification and represents failure or missing information explicitly.
- The firmware reads I2S audio and computes normalized RMS, but does not mislabel it as calibrated dB SPL. Physical buzzer operation is locked off.
- Three existing experimental `.joblib` model artifacts and their run metadata are present. They remain preserved.

These are source and file inspections, not runtime proof.

## Files changed

No existing files were modified.

## New files

- `SONIQ_AUDIT_REPORT.md`
- `SONIQ_INTEGRATION_REPORT.md`

## Existing components preserved

All existing source, APIs, SQL schema/migration, datasets, audio, model artifacts, dashboard, firmware, dependencies, and configuration files were left unchanged. No model was retrained, replaced, or loaded during this run.

## Integration status

| Area | Status | Evidence / remaining work |
|---|---|---|
| API | **NOT TESTED** | Routes and validation are present in `backend/app.py`; backend could not be started here. |
| ML integration | **PARTIALLY READY** | Runtime supports metadata-coupled artifacts. Three artifacts are experimental full-fit/no-held-out-evaluation; dataset review is not formally cleared. Load and actual WAV inference were not executed. |
| PostgreSQL | **NOT TESTED** | Repository and migration exist. No DB connection, insert, retrieval, or migration was run. |
| Dashboard | **NOT TESTED** | Static frontend is wired to the backend and has test files. No Node executable or browser session was available. |
| ESP32 | **NOT TESTED** | Firmware source implements I2S/RMS/event POST and fail-safe buzzer behavior. No board/toolchain test was possible. Sketch sends placeholder classification and sound fields, not audio. |
| Full end-to-end path | **BLOCKED** | ESP32 audio is not sent to the classifier; classify does not persist an event; current firmware targets a LAN address but backend is loopback-only. No approved transport joining these paths is implemented. |

## Test results

| Test | Result | Reason |
|---|---|---|
| Backend unit suite (`python -B -m unittest discover -s backend/tests -v`) | **BLOCKED** | Windows Store `python.exe` alias could not run. |
| ML unit suite (`python -B -m unittest discover -s ml/tests -v`) | **BLOCKED** | Same unavailable Python runtime. |
| Bundled `ml/.venv` attempt | **BLOCKED** | Virtualenv points to missing `[LOCAL_PATH]`. |
| Dashboard tests (`node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs`) | **BLOCKED** | Node executable not installed/available. |
| Backend startup / API requests | **NOT TESTED** | No runnable Python interpreter. |
| Model deserialization / WAV inference | **NOT TESTED** | No runnable compatible Python/dependencies; dataset/model approval is also unresolved. |
| PostgreSQL connectivity / migration / event round trip | **NOT TESTED** | No database test URL or `psql` command was available; no live DB was contacted. |
| Firmware compile / physical microphone / LED / buzzer test | **NOT TESTED** | No Arduino CLI/PlatformIO executable or physical device was available. |

No test passed in this session. No fake reading, event, classification, or test result was generated.

## Remaining blockers

1. A clean, supported Python environment and reviewed dependency installation.
2. Owner decision on whether the existing experimental artifact is suitable for a labeled demonstration; its metadata has no held-out evaluation and incomplete formal dataset clearance.
3. Approved PostgreSQL target, environment configuration, and database execution.
4. Approved end-to-end transport architecture and network binding/authentication decision. Existing docs identify USB serial as a proposal, not implemented behavior.
5. A real audio-to-classification-to-event workflow and a separately calibrated dB SPL measurement source.
6. Board/toolchain and physical device testing.
7. Review of the existing Git index state: staged deletions are reported for files also present as untracked working-tree content. No cleanup or staging was attempted.

## Exact local run instructions

These steps require a supported Python installation, dependencies from `backend/requirements.txt`, an approved PostgreSQL database, and approved warning configuration. They are instructions only; they were not executed here.

1. From the repository root, create a fresh environment and install backend dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend\requirements.txt
   ```

2. Set `SONIQ_DATABASE_URL` to the approved PostgreSQL connection string. Set `WARNING_THRESHOLD_DB_SPL` to the approved value (at least `75`) and `MAX_INPUT_AGE_SECONDS` to the approved value (positive and no more than `30`). Keep credentials in the process environment, not source files.

3. Apply the existing migration against the approved database:

   ```powershell
   python -m backend.migrate
   ```

4. To enable the existing experimental artifact for a clearly labeled local inference demonstration, first obtain model/data-owner approval. Then set:

   ```powershell
   $env:SONIQ_AUDIO_MODEL_PATH = (Resolve-Path .\ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib).Path
   ```

   The artifact remains marked experimental and not evaluated. Do not describe its prediction as validated accuracy. If not configured, classification should return model unavailable.

5. Start the backend in one terminal:

   ```powershell
   python -m backend.app
   ```

   It is intended for local access on `127.0.0.1:8000`. Check `http://127.0.0.1:8000/health`.

6. In another terminal, serve the static dashboard:

   ```powershell
   python -m http.server 8001 --bind 127.0.0.1 --directory dashboard
   ```

   Open `http://127.0.0.1:8001/`. The dashboard reads health and persisted event history from the backend. The ESP32 sketch cannot reach a loopback-only backend from the device and has no audio classification transport; do not treat these local steps as a complete hardware demo.

7. Once tools are installed, run existing tests from the repository root:

   ```powershell
   python -B -m unittest discover -s backend/tests -v
   python -B -m unittest discover -s ml/tests -v
   node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
   ```

   PostgreSQL integration tests need a dedicated test database configured through `SONIQ_TEST_DATABASE_URL`. Firmware compilation and device tests require the correct board, Arduino core, libraries, microphone wiring, and physical testing.
