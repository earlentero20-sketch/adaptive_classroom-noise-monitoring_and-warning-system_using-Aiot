# SONIQ Step 7 — Critical Demonstration Blockers

**Date:** 2026-11-09 (Asia/Manila)  
**Status:** **BLOCKED.** PostgreSQL cannot be restored from this checkout because no connection URL, local service, listener, or database tools are available. The current ESP32 firmware has no audio transmission path. No firmware/API changes were made pending the approval gate in the Step 7 request.

## 1. PostgreSQL root cause

### Verified current-machine findings

- Process `SONIQ_DATABASE_URL`: **not set**.
- Private `.env`: **absent**.
- `SONIQ_TEST_DATABASE_URL`: **not set**.
- `TCP 127.0.0.1:5432`: **no connection**.
- Windows service query for names matching `*postgres*`: **no service returned**.
- Standard `C:\Program Files\PostgreSQL` install root: **absent**.
- `psql` / `pg_isready`: **not available**.
- `GET http://127.0.0.1:8000/health`: **failed** with connection-level `WebException`; no backend was listening in this environment.

The exact immediate configuration cause is that the backend has no `SONIQ_DATABASE_URL` in this process or `.env`. `PostgresEventRepository.from_environment()` therefore raises its missing-URL configuration error before it can connect. In addition, no PostgreSQL server is accepting connections on the expected local port. The machine checks do not prove whether PostgreSQL is installed in a nonstandard location or whether a remote `soniq_db` exists. Authentication, database existence, schema, and saved event history are **NOT TESTED**; no connection attempt with credentials was possible.

The example URL in `.env.example` is only a placeholder (`USER:PASSWORD@127.0.0.1:5432/soniq_db`). It is not usable configuration. No password was read, printed, requested in chat, or changed.

### Backend behavior and repair status

The current backend catches PostgreSQL initialization failure, prints a generic degraded-mode warning, and starts HTTP health without a repository. Existing event create/list handlers then return HTTP 503 `storage_unavailable`. A health response means the process answered; it does not establish database readiness. The user-provided report that event history returned 503 is consistent with this path, but no live 503 response was observed in this run because the backend itself was not running.

No service/configuration repair was possible without an identified PostgreSQL installation/service or approved database credentials. Nothing was installed, started, migrated, or modified. To proceed, the owner must start/provision PostgreSQL and privately configure `.env` with the approved `SONIQ_DATABASE_URL`. Do not send its password in chat. Then test connection and inspect the target schema before migrating.

Migration safety: `001_create_events.sql` creates `events` without `IF NOT EXISTS`. Confirm that `schema_migrations` records this migration or that the target does not already contain `events`. If an existing table is present without a matching ledger record, stop for schema-owner review; do not run the migration blindly. No tables or data were changed.

## 2. ESP32 audio transmission findings

### Current firmware contract

- The sketch names its microphone in a setup log as INMP441, but no physical module/board was available to confirm it. The exact ESP32 board variant is not identified by the sketch.
- Source configures I2S RX for 16,000 samples/second, 32-bit containers, left channel. `readMicrophoneRMS()` reads up to 512 32-bit values (~32 ms), converts them to normalized RMS, and uses them for local QUIET/MODERATE/LOUD LEDs.
- Firmware posts JSON to `/api/v1/events` every two seconds. The payload has event/device IDs and sensor status; class is null/confident false and sound level is null/uncalibrated. It transmits no PCM, WAV, RMS field, or model feature vector.
- `Serial.begin(115200)` is present, but serial audio framing/transmission is not.
- Physical buzzer enable remains false. No device or audio transmission was tested.

### Existing classifier compatibility

- `POST /api/v1/classify` accepts one complete uncompressed PCM WAV request body with `Content-Type: audio/wav`, maximum 32 MiB. It is restricted to loopback clients and returns a model result only; it does not persist an event or evaluate warning policy.
- The expanded experimental artifact metadata specifies mono preprocessing to 16 kHz and 1 second (16,000 frames), centered crop/padding, mean channel mix, linear resampling, no peak normalization, then librosa MFCC mean/std features (20 MFCCs, 40 mel bins, 400-sample FFT/window, 160-sample hop, Hann window, 0–7,600 Hz).
- The I2S stream could be encoded as PCM WAV only after the actual sample alignment/quantization and microphone channel are verified on the hardware. Existing firmware computes RMS and discards each sample block; its current JSON cannot be classified.
- Three model artifacts remain present and unchanged. Their metadata marks them experimental full-fit, without held-out evaluation, and with formal data readiness/review not passed. The prompt reports an actual WAV classification passed in another environment; this run could not load or independently verify the artifact.

## 3. Proposed smallest compatible audio path — approval required

**Proposal:** add a USB-serial PCM stream from the ESP32 to a small host companion. The companion assembles one 16 kHz, mono, one-second PCM WAV in memory and calls the existing loopback-only `/api/v1/classify` endpoint. It then posts a classification event through the existing `POST /api/v1/events` contract. This leaves the backend routes/response formats and trained model unchanged and avoids exposing the classifier to LAN clients.

Expected changes if approved:

1. Modify `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` to frame an audio window with a capture ID, sequence/window length, and integrity check. Keep the current event-only mode available; provide an explicit audio mode to avoid duplicate event rows.
2. Add a host companion script (for example, `tools/soniq_serial_audio_companion.py`) to read the serial frames, validate a complete window, make the WAV, call existing loopback classification, and submit one event with the exact returned label. New serial dependency/use and privacy/retention handling must be reviewed.
3. Preserve fail-closed warning behavior. Until the confidence rule is approved, set event `confident=false`; until calibrated SPL is available, send null/un calibrated sound fields. This permits a real classification/event record but cannot generate a warning.

Memory/network considerations:

- The model needs 16,000 mono frames per window. PCM16 is 32,000 bytes per second. Buffering a full PCM16 second costs about 32 KB plus overhead; streaming 512-frame chunks would keep each payload around 1 KB and let the host assemble the window.
- UART 8-N-1 framing needs about 320 kbit/s for 32 KB/s before protocol overhead. The sketch currently initializes serial at 115200, which is insufficient for sustained PCM16 audio. A higher rate such as 921600 is only a candidate; the actual board, USB-UART bridge, cable, host COM driver, buffer headroom, and dropped-frame behavior must be measured.
- Actual ESP32 memory/flash budget, board variant, USB-UART capability, I2S sample alignment, and reliable throughput are unknown until the hardware is identified and tested. No successful hardware claim is made.
- A direct ESP32-to-backend HTTP upload would require allowing non-loopback clients on `/api/v1/classify` and designing authentication/authorization for audio/classification. That expands network/API security and is not recommended without a separate approved design.

Compatibility risks: firmware behavior changes, a new serial framing contract/tool, possible serial bandwidth/memory constraints, audio privacy/retention exposure, and a mode switch are required. No backend API or database schema change is proposed. Event-only mode must remain available. A positive warning/physical buzzer remains outside this proposal until SPL calibration, confidence approval, and hardware safety testing exist.

**No firmware or companion implementation has been made.** Per the requested approval gate, implementation must wait for approval of this concrete plan and identification of the actual board/serial connection.

## 4. Warning workflow status

Source policy remains backend-owned and fail-closed. It requires a valid fresh classification marked confident, a fresh calibrated `dB_SPL` value, configured valid threshold/freshness values, and a reading strictly greater than the configured threshold (minimum 75 dB; maximum age 30 seconds). Teacher Discussion does not trigger. Invalid/missing values suppress warnings.

The classifier response marks `warning_evaluation: not_performed`; probability, if present, is uncalibrated. The firmware currently sends no class or SPL and keeps the buzzer disabled. Classification-to-warning, event persistence of a real classified sample, warning generation, and physical output are **NOT TESTED**. No SPL or confidence values were fabricated.

## 5. Dashboard status

Dashboard remains a static app that uses real health/events/classification endpoint responses and backend warning fields. Existing source has loading/error/unavailable states. No current backend process or browser was available, so health/history/classification rendering and dashboard event connection are **NOT TESTED**. If the database is down, its actual event request should surface storage unavailable rather than synthetic history.

## 6. Git and preservation

Before Step 7 work, status was `main...origin/main`, 9,416 staged deletions, 21 untracked paths, and zero other status entries. No source, firmware, model, data, schema, or Git index changes were made. The two Step 7 reports account for the expected untracked-path increase. No reset, clean, staging, commit, or push was run.

## 7. Exact next steps

1. On the demonstration host, identify whether PostgreSQL exists and its actual Windows service name/path. Start/provision it; create/verify the intended `soniq_db` database and least-privilege role. Privately enter the connection URL in `.env` and tell the operator only that it is configured—do not share the password.
2. Confirm port connectivity and authenticate with `psql`/pgAdmin. Inspect `events` and `schema_migrations` before applying any migration.
3. Re-run backend tests and live health/event API checks in a usable Python environment; insert only an event produced by an actual source. Verify retrieval through API/dashboard.
4. Approve or revise the USB-serial proposal above and identify the exact ESP32 board and host serial port before firmware edits.
5. Obtain SPL calibration/source and approve a confidence rule. Without these, the new audio path can produce an experimental class/event but warnings must remain off.
6. Compile, stream real microphone audio, run actual classification, test persistence and failure recovery, then separately test any physical warning hardware. Keep buzzer disabled until approved safety tests pass.
