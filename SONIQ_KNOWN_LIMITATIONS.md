# SONIQ Known Limitations

These limitations reflect the current repository and checks made on 2026-11-09. They are not all runtime-tested because required tools, services, and hardware are unavailable.

## Critical integration gaps

- **No complete ESP32-to-ML path:** Firmware reads the microphone locally and computes short-window normalized RMS for LEDs; it sends no audio, extracted model features, or RMS in its event JSON.
- **Classifier is separate:** `POST /api/v1/classify` accepts a complete PCM WAV from loopback clients and returns classification only. It does not persist an event or evaluate warning policy. It is not an ESP32 streaming endpoint.
- **No calibrated SPL:** Firmware values are relative RMS; no SPL calibration or independent calibrated measurement source is implemented.
- **No approved confidence mapping:** Existing model probability, when present, is uncalibrated. It must not be converted into event `classification.confident=true` without an approved rule.
- **Warning workflow cannot be triggered from the existing firmware:** Backend warning policy requires a fresh confident `Student Conversation` class and fresh calibrated `dB_SPL` strictly above configured threshold (minimum 75 dB), within the configured freshness limit (maximum 30 seconds). The firmware sends null classification/SPL fields. Physical buzzer remains disabled.
- **Model artifacts are experimental:** Three `.joblib` artifacts exist, but metadata marks them as full-fit/no-held-out-evaluation and data review/readiness incomplete. They are not evidence of validated accuracy or formal dataset clearance.

## Environment and live verification

- The root `.venv` does not exist. `ml/.venv` points to a Python installation path for another Windows user that is missing. The launcher correctly refuses to start with that interpreter state.
- No `.env`, `SONIQ_DATABASE_URL`, `SONIQ_TEST_DATABASE_URL`, or `SONIQ_AUDIO_MODEL_PATH` was present at the last check.
- PostgreSQL did not accept a TCP connection on `127.0.0.1:5432`; no live table, insertion, or retrieval check was possible.
- Node.js was unavailable, so JavaScript syntax checks and dashboard fixture tests could not run. No browser/live API check occurred.
- No ESP32 was identified (serial enumeration returned COM1 only); no firmware compile, LAN transfer, microphone, LED, or buzzer test occurred.
- The Step 4 launcher guard is tested, but backend/dashboard service startup is not. No end-to-end connection has passed.

## Network and dashboard constraints

- Backend listener defaults to `127.0.0.1:8000`. `BACKEND_HOST` can be set to `0.0.0.0` or a private IPv4 for a trusted LAN; use a narrowly scoped Private-profile Windows Firewall rule and no router port forwarding.
- The LAN event endpoint has no application authentication. Keep it on a trusted private subnet.
- Dashboard browser CORS remains loopback-origin-only. Opening the dashboard from a separate LAN client is not enabled.
- `/api/v1/classify` remains loopback-client-only even when the backend listens on LAN.
- Dashboard history reflects persisted backend events only. It does not generate demo records or simulate readings.

## Data, schema, and repository state

- The existing `events` schema and migration were source-reviewed but not queried in a live database. Migration `001_create_events.sql` creates `events` without `IF NOT EXISTS`; if an `events` table predates `schema_migrations` bookkeeping, applying the migration can fail with a table-exists error. Verify the live schema and migration ledger before running it. No schema change or live migration was performed.
- `.gitignore` excludes environment files and virtualenvs; `ml/.gitignore` excludes data and generated artifact directories. LFS attributes exist for audio and selected binaries.
- Git already reports thousands of staged deletions alongside untracked working-tree copies. No reset, clean, staging, commit, or push was run. This pre-existing index state must be reviewed by the owner before release.
- `SONIQ_STEP5_REPORT.md` and `docs/INTEGRATION_TEST_RESULTS.md` were not present; the prior final readiness document is `SONIQ_FINAL_DEMO_READINESS_REPORT.md`.

## Safe presentation scope

After installing a valid Python environment and configuring services, a limited software demonstration may show actual health, genuine stored history, explicit unavailable/error states, and a manually uploaded WAV classification only if the model owner approves it. That classification remains experimental and independent of warning evaluation. A live warning/buzzer demonstration remains blocked until transport, calibrated SPL, confidence policy, persistence, and physical safety tests are completed.
