# SONIQ Final Demo Readiness Report

**Date:** 2026-11-09 (Asia/Manila)  
**Final decision: NOT READY — CRITICAL BLOCKERS REMAIN.**  
The requested system workflow cannot be demonstrated end to end based on the tests and current environment. The ESP32 does not send audio or calibrated SPL, the backend/model/database could not be started here, and no physical hardware or live dashboard test was available.

## 1. Executive summary

Steps 1–4 improved the private-LAN bind configuration, added database-degraded startup, and added a Windows launcher/documentation. Step 5 review found that this checkout still has no usable Python interpreter, `.env`, database URL, model path, PostgreSQL listener, Node.js, browser session, or identifiable ESP32 serial device. The launcher was exercised and correctly stopped with setup guidance because both project interpreters were unusable; this is a successful guard check, not a successful backend startup.

The source contains a backend, ML preprocessing/inference adapter, warning policy, PostgreSQL repository/schema, static dashboard, and ESP32 firmware. Those components do not yet form a verified data path. Firmware sends JSON events with null classification and sound fields; it does not transmit captured audio. The separate WAV classifier only returns inference and does not create an event or evaluate warning policy. SPL calibration is absent. Thus there is no tested path from microphone to model, warning, stored event, and dashboard.

## 2. Final architecture and connection status

| Workflow link | Status | Evidence / limitation |
|---|---|---|
| ESP32 microphone acquisition | **NOT TESTED** | Source reads I2S at 16 kHz, 32-bit, left channel and computes local RMS. No device was identified; only COM1 was enumerated. |
| Audio transmission | **FAILED** | Firmware source does not transmit PCM/WAV or features. Its HTTP JSON contains only IDs/status and null classification/SPL fields. |
| LAN communication | **NOT TESTED** | Step 1 permits `0.0.0.0` or private IPv4 and preserves loopback default, but no backend was running and no second LAN client/device test occurred. `SERVER_URL` remains device-configured. |
| Backend startup and API | **BLOCKED** | No runnable Python. The launcher exits before startup. Routes/source are present; no endpoint was reached in this step. |
| WAV preprocessing | **NOT TESTED** | Source supports complete uncompressed PCM WAV and uses artifact metadata. No actual inference invocation ran. |
| Existing model load/classification | **BLOCKED** | Three `.joblib` artifacts exist and were preserved. Their metadata says experimental full fit, no held-out evaluation, and dataset review/readiness not passed. Model load and classification were not run. |
| Warning policy | **NOT TESTED end to end** | Backend policy source requires a fresh confident `Student Conversation` classification and fresh calibrated dB SPL above configured threshold (at least 75 dB SPL; maximum age at most 30 seconds). Firmware supplies neither input. Confidence handling is not approved; model probability is uncalibrated. |
| PostgreSQL | **BLOCKED** | No `SONIQ_DATABASE_URL` or `.env`; localhost port 5432 refused a TCP connection. Live tables, insert, and retrieval were not tested. |
| Dashboard health/events/classification | **NOT TESTED** | Static UI and adapter are wired to backend endpoints, but no browser, Node runtime, live backend, or API responses were available. |
| Physical warning/buzzer | **NOT TESTED** | No hardware test; firmware constant `ENABLE_PHYSICAL_BUZZER` is false. |

The backend/API paths are separate today: `/api/v1/classify` accepts one complete WAV and returns a class; it does not persist an event or call warning policy. `POST /api/v1/events` applies warning policy to supplied event fields and persists only when PostgreSQL is available. Dashboard renders backend responses; it does not join these paths.

## 3. Verified features

### PASSED — tested behavior

- The Windows launcher’s missing-interpreter guard was run. It detected there was no usable project virtualenv, printed recovery commands, and exited without starting services or changing environments.
- The Step 4 PowerShell helper parser check passed at that time; that helper was subsequently replaced with the current Python standard-library helper. The current helper could not be syntax-checked because Python is unavailable.
- A direct TCP check to `127.0.0.1:5432` found no PostgreSQL listener.

### Source-level findings only — not runtime verification

- Backend routes exist for health, event create/list, and WAV classification. Step 3 adds degraded startup; when no repository is available, event handlers return the existing `storage_unavailable` response.
- Step 1 host validation accepts loopback, `0.0.0.0`, and RFC1918 private IPv4 addresses; default remains `127.0.0.1:8000`. Public bind addresses are rejected.
- Dashboard uses backend URL configuration, health/events/classify endpoints, and explicit loading, empty, stale, unavailable, error, and invalid-response states. Warning policy is not duplicated in JavaScript.
- PostgreSQL migration source defines `events`; migration runner tracks checksums in `schema_migrations`. No migration was run and no live tables were inspected.
- Existing experimental model artifacts and actual WAV files are present. Artifact metadata reports no held-out evaluation and incomplete formal data readiness; file presence does not verify artifact compatibility or prediction quality.

## 4. Modified files from Steps 1–4

The following project changes are recorded in the prior step reports:

- `backend/app.py` — private-LAN bind support (Step 1) and degraded startup on PostgreSQL initialization failure (Step 3).
- `backend/tests/test_app.py` — bind/degraded-startup tests added, but not executable in this environment.
- `.env.example` — backend host/port settings documented.
- `docs/INTERFACE_CONTRACT.md`, `docs/LAN_CONNECTIVITY.md`, `docs/INTEGRATION_PLAN.md`, `docs/POSTGRES_LOCAL.md` — network, transport, and database behavior documented.
- `start_soniq.bat`, `backend/start_backend.py` — local Windows launcher and allowlisted `.env` loader.
- `dashboard/README.md` — static dashboard startup instructions corrected.
- `SONIQ_AUDIT_REPORT.md`, `SONIQ_INTEGRATION_REPORT.md`, `SONIQ_STEP1_REPORT.md`, `SONIQ_STEP2_REPORT.md`, `SONIQ_STEP3_REPORT.md`, `SONIQ_STEP4_REPORT.md` — prior audit/step reports.
- `SONIQ_FINAL_DEMO_READINESS_REPORT.md` — this report.

No Step 5 source changes were made. No model, audio, database, schema, dashboard runtime component, or firmware file was deleted or replaced. Nothing was staged, committed, reset, or pushed. The repository already showed a large staged-deletion/untracked-copy state in prior checks; it was left untouched.

## 5. Test results

| Test | Status | Actual result |
|---|---|---|
| Backend startup | **BLOCKED** | `start_soniq.bat` exited before starting services because no usable project virtualenv exists. The root `.venv` is absent; `ml/.venv` references missing `[LOCAL_PATH]`. |
| Backend unit tests | **BLOCKED** | `python -B -m unittest discover -s backend/tests -v` could not launch; the Windows Store Python alias was inaccessible. |
| Backend LAN accessibility | **NOT TESTED** | No backend process, second device, or LAN request. |
| ESP32 connection | **BLOCKED** | No ESP32 was identified; serial enumeration reported COM1 only. No firmware toolchain/device test. |
| Actual audio transmission | **FAILED** | Source inspection shows the firmware sends no audio payload. This link is not implemented in the current sketch. |
| Model loading / actual classification | **BLOCKED** | Python/dependencies unavailable; no model load or prediction was performed. No classification result is claimed. |
| Warning policy | **NOT TESTED** | Source was reviewed, but no real inference plus calibrated SPL event reached the policy. |
| PostgreSQL connection | **FAILED / UNAVAILABLE** | No URL/configuration; TCP `127.0.0.1:5432` had no listener. |
| Event insertion/retrieval | **NOT TESTED** | No database request or event record was created. |
| Dashboard health/events/classification | **NOT TESTED** | No live backend/browser. |
| Dashboard JavaScript syntax and tests | **BLOCKED** | `node` is unavailable; `node --check` and Node test suite could not run. |
| Error handling | **PARTIALLY WORKING** | Launcher missing-runtime path was exercised and produced a useful message. Backend/dashboard error handling is present in source but was not run. |

No fabricated readings, classifications, warnings, or event records were used.

## 6. Remaining problems

1. **Runtime:** Install/use supported Python and create a fresh root `.venv`; do not reuse the copied virtualenv with the missing base interpreter. Node is needed only for the existing dashboard tests, not to run the dashboard.
2. **Database:** Configure an approved private `SONIQ_DATABASE_URL`, start PostgreSQL, verify the target database/role, and apply the existing migration only after confirming the target. The launcher can start degraded, but event storage will return 503.
3. **Model/data:** Obtain owner approval for a labeled demo use of an existing experimental artifact. Its metadata has no held-out evaluation and the dataset manifest is unreviewed/not formally ready. Verify loading and actual WAV inference before reporting classification.
4. **Audio transport:** Implement and test an approved transport that sends enough audio for the classifier. Current firmware only computes short-window RMS locally. Existing `POST /api/v1/classify` is loopback-only and accepts a complete PCM WAV, not an ESP32 LAN stream.
5. **Confidence:** Approve a rule for mapping model output to the event’s Boolean `classification.confident`; uncalibrated `predict_proba` cannot be treated as calibrated confidence.
6. **SPL:** Add an independently calibrated measurement source or calibrate the physical sensor with a documented reference procedure. RMS is not dB SPL.
7. **Warning/event lifecycle:** Join classification and calibrated SPL into the existing event request so the backend policy evaluates and persists one event. No such joined path currently exists.
8. **Hardware/network:** Configure the correct private host IP, firewall, SSID, and device URL, then test actual packets, timing, memory, sensor output, and fail-safe behavior. Keep the buzzer disabled until separately authorized hardware safety testing.
9. **Git:** Preserve the existing staged deletions and untracked copies for owner review. No Git cleanup or staging was performed.

## 7. Hardware requirements

- ESP32 model/board and Arduino toolchain/libraries matching the existing sketch.
- INMP441 (or the actual specified microphone) with verified I2S pinout, channel selection, gain, and stable mounting.
- One-second capture/buffer and an approved transport/framing approach to the host; current firmware samples 512-word blocks at 16 kHz but sends no audio.
- A documented SPL measurement definition and suitable calibrated reference or independent calibrated meter; record calibration date, setup, range, and uncertainty.
- Same trusted LAN/subnet, correct host private IPv4, and narrowly scoped Windows Firewall rule. No router port forwarding.
- Physical LED/buzzer tests and loss-of-network/backend authorization tests. Buzzer remains locked off in current firmware.

## 8. Database requirements

- Running PostgreSQL and a privately configured `SONIQ_DATABASE_URL` in `postgresql://USER:PASSWORD@HOST:PORT/DATABASE` form.
- Confirm the actual host, port (commonly 5432), database (project history used `soniq_db`), least-privilege role, and authentication privately; no current values are configured here.
- Apply existing migration `backend/migrations/001_create_events.sql` through `python -m backend.migrate` against the approved target; do not drop/recreate tables.
- Use `SONIQ_TEST_DATABASE_URL` only with a dedicated test database if running PostgreSQL integration tests.
- No data retention/cleanup or fabricated test events should be added for the demo.

## 9. Exact startup and demonstration procedure

These commands are for the demonstration computer after Python is installed and database/model approvals are resolved. They were **not successfully completed in this environment**.

1. From the repository root, create the isolated environment and install only declared project requirements:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
   ```

2. Create a private `.env` using `.env.example` as a template. Replace placeholders with approved local settings. Do not commit or print the real database URL. Set `SONIQ_AUDIO_MODEL_PATH` only after the model/data owner approves using that existing artifact. Set warning parameters only according to the approved policy.

3. Before migration, load `.env` into the current PowerShell process without displaying values, then apply the existing migration to the verified database:

   ```powershell
   Get-Content .env | ForEach-Object {
       $line = $_.Trim()
       if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
           [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
       }
   }
   .\.venv\Scripts\python.exe -m backend.migrate
   ```

4. Start both local services:

   ```powershell
   .\start_soniq.bat
   ```

   Open `http://127.0.0.1:8001/`; verify backend health at
   `http://127.0.0.1:8000/health`. If PostgreSQL is unavailable, the backend
   may start degraded, but event history/write requests will not work.

5. For an approved manual WAV model check, upload an actual available PCM WAV
   through the dashboard or use the existing loopback endpoint:

   ```powershell
   Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/classify' `
       -Method Post -ContentType 'audio/wav' -InFile '<approved-local-wav-path>'
   ```

   This tests classification only. It does not exercise the warning policy,
   persist an event, or prove ESP32 integration. Do not report accuracy from
   the experimental no-held-out-evaluation artifact.

6. A full physical demonstration remains blocked until the approved audio
   transport and calibrated SPL/confidence inputs are implemented. After that,
   capture real audio, confirm the backend’s actual classification, submit one
   real event through the existing event contract, verify the returned warning
   decision and PostgreSQL history, then refresh the dashboard. Do not use a
   fabricated event to fill the history. Physical buzzer testing is a separate
   safety gate.

## 10. Known limitations

- The app can show backend process health while the database is unavailable; check event history separately.
- The classifier route is loopback-only and separate from event persistence/warning evaluation.
- Dashboard LAN-origin access is not enabled by the current CORS policy.
- The experimental model artifacts have not been verified in this environment and are not evaluated.
- Classification confidence is not calibrated/approved; raw microphone RMS is not calibrated SPL.
- Current firmware has no audio transport and physical buzzer operation is disabled.
- No live browser, database, backend, network, or hardware verification was available.

## Final readiness assessment

**NOT READY — CRITICAL BLOCKERS REMAIN.** The decision is based on actual environment checks: the launcher stops because no project Python can run; Node is unavailable; no database URL exists and localhost port 5432 refuses connections; no ESP32 was identified; and the firmware source has no audio transmission path. The existing source contains useful individual components, but no end-to-end workflow has been demonstrated. Do not present the system as a functioning live classifier/warning system until the listed runtime, data transport, model, SPL, database, and hardware checks pass.
