# SONIQ Step 8 — USB-Serial Audio Bridge Implementation Plan

**Status:** DESIGN ONLY — **REQUIRES APPROVAL** before firmware, companion, backend, API, dashboard, or database behavior changes. Inspected 2026-11-09 (Asia/Manila). No implementation or hardware test was performed.

## Recommendation

For a local demonstration, evaluate a host-side serial companion as the smallest path that keeps the trained model, current classifier route, event contract, database schema, and dashboard intact. The companion would own the ESP32 COM port and run beside (not inside) the existing backend process. It would receive framed PCM, assemble a valid WAV in memory, call `http://127.0.0.1:8000/api/v1/classify`, then—only after a valid inference response—submit one event through the existing `POST /api/v1/events` route. The event must use the exact returned label and observation timestamp, set `confident=false` until a confidence rule is approved, and keep sound level null/uncalibrated. The current backend must be bound on loopback for this topology; no LAN audio endpoint is needed.

This is a conditional recommendation, not a finding that a particular ESP32/USB-UART combination can sustain the transfer. Board model, serial bridge capability, effective microphone sample alignment, free RAM, and real throughput are unknown. A physical throughput/capture test is a gate before choosing this transport.

## Existing behavior verified from source

- Firmware: `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino`. It is Arduino-framework source using the legacy ESP-IDF I2S driver. The sketch selects I2S RX, 16,000 samples/s, one left channel, 32-bit sample containers, pins 25/26/33, and reads blocks of 512 32-bit words (2,048 bytes, nominally 32 ms). It shifts each word right 8 bits, normalizes it as a signed 24-bit value, computes RMS, and discards the samples after updating local LED level. The log calls the microphone INMP441; that is not physical verification. Board variant and effective microphone resolution are **UNKNOWN**.
- Firmware serial: `Serial.begin(115200)` is used for human-readable logs. There is no audio framing or serial receiver. The current sketch continues posting its existing JSON event to the Wi-Fi event URL; it sends no PCM. Physical buzzer is disabled.
- Backend classifier: `backend/app.py`, `POST /api/v1/classify`, accepts one complete `audio/wav` request up to 32 MiB, validates PCM WAV, classifies it using the configured artifact, and is loopback-client-only. It returns a label, optional explicitly uncalibrated model probability, artifact/evaluation metadata, and `warning_evaluation.status=not_performed`; it does not persist an event.
- Backend event API: same module, `POST /api/v1/events`, validates the existing v1 event contract, applies the existing fail-closed warning policy, and writes through `backend/postgres_event_repository.py`. PostgreSQL unavailable means event storage is unavailable; the existing handler returns `503 storage_unavailable`. Duplicate event IDs are conflicts. No database/API/schema change is proposed.
- ML: `ml/audio_inference.py` and `ml/data_pipeline.py` validate/decode PCM WAV and apply the loaded artifact's serialized preprocessing. Current artifact metadata inspected in the prior Step 7 report targets mono 16 kHz, one second (16,000 frames); the runtime should take the selected artifact metadata as authoritative and reject incompatibility. Do not manufacture confidence or SPL.
- Warning policy: `ml/warning_policy.py` requires a valid class, `confident is True`, calibrated sound level, and threshold; the backend also enforces freshness and warning configuration. With the proposed bridge's unapproved confidence and absent calibration, warning must remain false.
- Dashboard: `dashboard/backend-adapter.mjs` reads actual health/events and can classify WAVs. It does not calculate warnings. It can display a saved event only after event persistence. It polls event history; no dashboard contract change is proposed.
- Environment: `backend/start_backend.py` reads root `.env` as UTF-8, accepts only an allowlist of SONIQ settings, does not print values, and passes them to `backend.app`. Root `.env.example` already contains placeholders, so no replacement template is needed. Backend event storage requires `SONIQ_DATABASE_URL`; there is no automatic DB creation/migration. The migration must not be run until target schema/ledger is inspected.

## Proposed audio format and framing (not implemented)

The preferred candidate payload is **16 kHz, mono, signed PCM16 little-endian, exactly 16,000 frames for one second**: 32,000 raw audio bytes. This is a transport candidate aligned with the inspected experimental artifact's declared input shape, not proof the sketch's I2S words can be converted correctly. Verify I2S slot alignment/sign extension and compare captured audio with an independent recorder before using it for inference. Build the WAV header on the host with `wave`; serial bytes alone are raw PCM, not a WAV file.

Candidate binary record format, bounded to small chunks (for example, at most 1,024 payload bytes):

| Field | Purpose |
|---|---|
| COBS-encoded record + `0x00` delimiter | Unambiguous frame boundary and resynchronization after noise |
| Magic `SQAU`, protocol version, record type (`START`, `DATA`, `END`, `ERROR`) | Reject unrelated console text and incompatible protocol versions |
| 128-bit capture ID | Correlate all chunks and make retries recognizable |
| Sequence number, payload length, total expected frames | Detect loss, duplication, reordering, truncation, and oversized records |
| `START` metadata: sample rate, channels, encoding, frame count | Host validates the exact negotiated format before accepting data |
| `DATA` payload: PCM16LE bytes | Bounded transfer chunks; each chunk ends on a sample-frame boundary |
| CRC-32 over decoded header and payload | Detect accidental packet corruption; not authentication |
| `END`: packet count, frame count, whole-capture CRC-32 | Validate complete capture before writing WAV or sending HTTP |

The receiver must reject unsupported versions/formats, invalid lengths, CRC errors, missing/duplicate/out-of-order chunks, mismatched capture IDs, timeout, and incomplete sample counts. On any error, discard the entire capture, report the reason, resynchronize at a later delimiter, and never classify partial audio. Proposed initial capture timeout: 10 seconds, configurable after bench measurements. Binary audio mode must not interleave current free-form `Serial.print` diagnostics; either use framed diagnostic records or suppress text only in an explicitly selected audio mode. The existing event-only mode remains the default and unchanged unless approval explicitly authorizes a mode switch.

## Payload, RAM, and transfer calculations

The source guarantees a configured **32-bit container**, not the microphone's effective bit depth. The 512-word I2S local read array occupies 2,048 bytes. If each sample is converted to PCM16 during capture and retained for post-capture transfer, one second requires a 32,000-byte static buffer plus stack/driver/protocol headroom. Retaining the configured 32-bit words for the whole second would require 64,000 bytes. Available free heap/PSRAM is **UNKNOWN**; do not allocate a 32 KB local stack array without measuring the actual board. Streaming without a full buffer reduces memory, but requires the serial writer and receiver to keep up concurrently with I2S and existing Wi-Fi/event/LED work, with bounded queues and explicit dropped-sample detection.

At 16,000 frames/s × 1 channel × 16 bits, raw PCM rate is 256,000 bit/s = 32,000 bytes/s. UART 8-N-1 uses approximately 10 wire bits per byte, so the payload needs at least 320,000 bit/s before packet overhead. At existing 115,200 baud, ideal throughput is 11,520 bytes/s and transferring 32,000 bytes has a lower-bound time of **2.78 seconds**, excluding COBS/header/CRC/USB-UART/driver delays. Thus 115,200 baud cannot stream this PCM in real time; it may transfer a buffered one-second capture after capture if memory and stall effects are acceptable. A 921,600-baud setting would provide an ideal 92,160 bytes/s (about 0.35 seconds for raw payload) but is only a bench candidate, not verified capability. Packet overhead, scheduling, retries, and host behavior increase these estimates.

## Host receiver and classifier/event sequence

Proposed new file: `tools/soniq_serial_audio_companion.py` (not created). Keep it separate from the HTTP server so serial reads/timeouts cannot block request handling. Use the existing selected Python interpreter and standard library (`argparse`, `wave`, `struct`, `zlib`, `urllib` or an already approved HTTP client). Add `pyserial` only as a separate optional dependency (for example, `tools/requirements-serial.txt`) after approval; the backend and ML requirements currently do not include it.

Windows setup should list ports with `python -m serial.tools.list_ports`, then require explicit `--port COMx` and a tested baud setting. Do not auto-select a port or open it concurrently from Arduino Serial Monitor. Receiver opens the selected port exclusively, validates packet bounds and CRCs, buffers at most one accepted 32 KB capture, wraps it into a PCM WAV with one channel, 16,000 Hz, 2-byte sample width, then locally POSTs to classifier with `Content-Type: audio/wav`. Verify response schema/status, class, artifact metadata, and timestamp. Only then build one event with capture-derived unique ID and device ID, exact model class/time, `confident=false`, null/uncalibrated sound measurement and actual sensor status, and POST to events. Do not report persistence unless event API returns successful storage; a database error must be shown as a persistence failure while retaining the inference result as a separate state.

For duplicate prevention, retain recent capture IDs in the receiver process and derive event ID from device ID + capture ID. The backend's unique event ID prevents a duplicate insert, but duplicate requests currently yield a conflict; companion recovery should query history to establish whether that ID already exists before treating a retry as complete. The classifier itself has no idempotency key, so repeat classification is possible and must be documented. Persisting a local dedup ledger would add another file/state lifecycle and is not proposed for the first version.

## Database prerequisite

The Step 7 findings still apply: no URL, private `.env`, local listener, or verified database was present in that environment. `SONIQ_DATABASE_URL` has the format `postgresql://USER:PASSWORD@HOST:5432/soniq_db` in the existing placeholder template; URL-encode reserved credential characters and keep the actual value private. The backend launcher loads the allowlisted setting from `.env`; `backend.app` itself reads the process environment. PostgreSQL must already be running and the correct schema/`schema_migrations` ledger inspected. Do not create a replacement DB or run migration 001 blindly. A companion may classify audio while storage is unavailable, but it cannot claim a saved/dashboard event until the real event API and database succeed.

## USB serial versus direct local-network audio

| Option | Fit with current code | Tradeoffs |
|---|---|---|
| USB serial + host companion | Reuses loopback-only classifier and existing event endpoint without adding a backend route. Works locally without exposing an audio endpoint to Wi-Fi. Requires a verified USB/USB-UART path, COM receiver, framing, sufficient RAM/throughput, and handling of serial text/logging. | Smaller network/API security change; more embedded/host transport engineering. Current 115,200 baud is too slow for live PCM16 but may support buffered post-capture transfer. Hardware unknown. |
| ESP32 Wi-Fi upload | Wi-Fi is already used for event JSON, but the current classifier rejects non-loopback clients and accepts a complete WAV request, not the firmware's current event JSON. Keeping contracts intact means a local host relay/stream protocol would still be needed; direct upload needs a new authenticated audio endpoint or a reviewed allowlist/auth change. | Potentially higher throughput and less dependence on UART baud; requires API/security/firmware changes, audio access control, resource limits, LAN privacy review, and likely network firewall/CORS review. Current `/api/v1/classify` must not simply be opened to unauthenticated LAN audio. |

For an upcoming local demonstration, USB is the narrower API/security change **if actual hardware sustains it**. Direct Wi-Fi is more appropriate only if board USB serial proves unreliable and the project approves an authenticated audio-upload design. Neither route is currently demonstrated.

## Exact files expected to change after approval

1. `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` — add opt-in capture/framing while preserving existing default Wi-Fi event, local LED/RMS, and buzzer-disabled behavior.
2. New `tools/soniq_serial_audio_companion.py` — receiver, validation, WAV creation, loopback inference, optional v1 event submit with fail-closed fields.
3. New optional `tools/requirements-serial.txt` — pin/constraint for `pyserial`, separate from backend requirements.
4. `README.md` or a new `docs/USB_SERIAL_AUDIO_BRIDGE.md` — operator setup, privacy, protocol, recovery, and tested hardware configuration.
5. Tests for packet parser, CRC, truncation/reordering/timeout, WAV validation, HTTP failures, duplicate IDs, and no-warning safety fields; test files depend on agreed framework.

No change to `backend/app.py`, API contracts, `backend/migrations/*`, model artifacts, dashboard, `.env.example`, or root requirements is currently needed. If design testing finds an API change is required, stop and request separate approval.

## Windows operator setup (future, after implementation and approval)

1. Use the same verified Python virtual environment as the project; install the normal project requirements and only the optional serial dependency file.
2. Keep private settings in root `.env`; at minimum set trusted model path and database URL. Do not share credentials. Confirm PostgreSQL and schema first.
3. Start the backend locally using `start_soniq.bat`; classifier should remain on loopback, and event storage must be healthy for persisted history.
4. Close Arduino Serial Monitor. Identify the port with `python -m serial.tools.list_ports`; run the companion with an explicit tested COM port and baud.
5. Select the explicit audio mode on the ESP32 only after board compatibility is verified. Check packet/capture status, classifier response, event storage response, and dashboard history independently. No firewall rule is required for serial; do not add router forwarding.

The current `start_soniq.bat` starts the dashboard and backend, but does not start a serial receiver. Its dashboard server and dashboard API default to loopback. Do not imply the above steps are presently executable: the receiver is not implemented.

## Testing strategy and approval gates

1. Identify exact board/USB interface, microphone module, ESP32 Arduino core, USB-UART chip, and Windows COM driver. Record free heap/PSRAM and existing stack/task budget.
2. Bench-test I2S samples and conversion against a known PCM capture; verify sign/alignment, clipping, sample count/rate, and 16 kHz mono one-second WAV compatibility. Do not substitute generated audio.
3. Bench-test sustained framed serial traffic at candidate baud rates with CRC and sequence checks under Wi-Fi, LED, and current event-loop load. Measure loss, latency, free heap, recovery, and retry behavior. Test disconnect/reconnect and invalid/incomplete frames.
4. Use one actual microphone capture, run the existing model artifact without changes, check exact response metadata, and verify invalid audio is rejected. No accuracy claim from an experimental full-fit artifact.
5. With the pre-existing DB configured and schema inspected, test actual event insertion, retrieval and duplicate handling; verify dashboard shows that returned row. If DB is unavailable, mark persistence BLOCKED.
6. Assert event confidence remains false and sound reading null/uncalibrated; prove warning stays off. SPL calibration and confidence-rule review are separate approval gates. Keep buzzer disabled.

### Approval required before implementation

Approve or revise the USB-serial topology and binary protocol, identify the actual ESP32 board/microphone and COM device, authorize an opt-in firmware audio mode plus separate host companion/optional pyserial dependency, and agree on one-second PCM16 encoding/window. Separately approve the audio privacy/retention plan and whether the companion may submit classification events with `confident=false`. No warning activation or SPL/confidence invention is requested or permitted by this proposal.

## Rollback plan

Keep the existing firmware event-only behavior as default and guard audio mode behind an explicit compile-time/runtime selection. If any transport, memory, latency, privacy, or integration test fails, disable audio mode, close the companion, remove only newly added code/dependency/docs after review, and return to the existing event-only firmware. Do not alter model artifacts, database records/schema, or Git index during rollback. Preserve captured audio only if separately authorized; default receiver behavior should keep it in memory and discard it after request completion/error.

## Current gate result

**REQUIRES APPROVAL / HARDWARE BLOCKED.** Design complete; no firmware/backend/API/hardware behavior changed. USB serial reliability, actual model inference on device audio, PostgreSQL persistence, and dashboard end-to-end behavior remain unverified. This is not a demonstration-readiness claim.
