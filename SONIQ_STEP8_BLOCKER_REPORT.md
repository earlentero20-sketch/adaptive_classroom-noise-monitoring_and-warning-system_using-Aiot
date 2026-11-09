# SONIQ Step 8 — USB-Serial Audio Bridge Blockers

**Date:** 2026-11-09 (Asia/Manila)  
**Status:** **BLOCKED for hardware verification; REQUIRES APPROVAL before implementation.** The investigation is complete from available source. No firmware, backend, API, model, database, dashboard, or hardware behavior was changed.

## 1. Critical blockers

### Board, microphone, RAM, and transport not identified

- Firmware source configures 16 kHz I2S, one left channel, 32-bit sample containers, and a 512-word/2,048-byte read buffer. It currently converts each block to normalized RMS and discards the audio samples.
- The source log names INMP441, but there is no verified physical board/module. ESP32 model/revision, actual microphone, I2S alignment, effective bit depth, available RAM/PSRAM, USB connector mode, USB-UART bridge, cable, Windows COM port, and reliable maximum serial rate are **UNKNOWN / NOT TESTED**.
- Only COM1 was enumerated in the Step 7 environment. Arduino CLI/PlatformIO were unavailable. No physical capture, firmware compile, or throughput test was performed.
- A candidate one-second mono PCM16 capture is 32,000 bytes. Existing 115,200 baud needs at least 2.78 seconds in ideal 8-N-1 transfer, excluding framing and delays; it cannot sustain a live 32 kB/s stream. A 32 KB buffer plus runtime overhead may or may not fit; memory has not been measured. The existing 512-word block is only ~32 ms and cannot hold a full second.

**Needed:** exact board and microphone identification; measured free RAM; test capture/quantization; and CRC/sequence-checked throughput measurements at candidate baud under existing Wi-Fi, LED, event, and audio load. Until then USB serial is a proposal, not a verified reliable transport.

### Current backend is not a serial receiver

- No host serial receiver exists and `pyserial` is not in the backend or ML requirements.
- The backend is an HTTP service, not a serial reader. The COM port should be owned by a separate companion to avoid blocking or competing with the server.
- The classifier accepts complete PCM WAV only from loopback. Raw serial PCM must be assembled and wrapped with a valid WAV header by the host; sending serial bytes directly to the classifier would not satisfy the contract.
- Serial currently carries human-readable logs at 115,200 baud. Binary framing requires an explicit audio mode and diagnostic handling so log text cannot corrupt packets. Existing event-only behavior should remain default.

**Needed:** approve a packet contract, new companion, optional `pyserial`, Windows COM selection, retry/timeout policy, and audio retention/privacy behavior before implementation.

### Database and event history unavailable

Step 7 found `SONIQ_DATABASE_URL` unset, root `.env` absent, no local listener on `127.0.0.1:5432`, and no psql tools in the tested environment. The backend can start in degraded mode but its event endpoints report `storage_unavailable`; event history/dashboard persistence cannot be verified without the existing approved database. Host classification alone can work separately from event persistence, but it must not be reported as saved or visible in event history.

**Needed:** owner-configured private `.env` using the real approved connection URL; database owner verifies the existing `soniq_db`, schema, and `schema_migrations` ledger. Do not create/reset a DB or run migration 001 against an uninspected schema.

### Confidence, SPL, and warning safety

- Model probability is explicitly uncalibrated; classifier returns `warning_evaluation=not_performed`.
- Current microphone RMS is relative normalized amplitude, not calibrated dB SPL. No SPL calibration exists in the firmware path.
- The event warning policy needs a fresh confident class and a fresh calibrated `dB_SPL` value above the configured threshold. The proposed bridge cannot satisfy those gates from current data.
- Buzzer operation is disabled. No warning/buzzer path should be enabled from an audio label alone.

**Needed:** a reviewed confidence rule and model/data approval, independent SPL calibration against a reference meter at documented levels/positions, threshold/freshness policy approval, then fault and physical safety tests. Until those are complete, event confidence remains false, sound reading remains null/uncalibrated, warnings remain suppressed, and physical buzzer remains disabled.

## 2. Database configuration details

`backend/postgres_event_repository.py` requires `SONIQ_DATABASE_URL` in libpq URL form, represented in existing `.env.example` as:

```text
SONIQ_DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/soniq_db
```

The example uses placeholders, not credentials. Reserved URL characters in actual credentials must be URL-encoded. `backend/start_backend.py` reads root `.env` as UTF-8, accepts a fixed allowlist, and withholds values from output; direct `backend.app` startup reads the process environment and does not parse `.env` itself. Existing schema/migration files must be preserved. `001_create_events.sql` creates `events` without `IF NOT EXISTS`; inspect the live table and migration ledger before running it. No DB setup, migration, event insert, or credential use occurred here.

## 3. Network option blocker

ESP32 Wi-Fi already exists for event JSON, but direct audio upload is **not** supported by the current classifier route: `/api/v1/classify` is loopback-client-only and accepts one complete WAV. Exposing it to LAN devices or adding an audio route requires a separate authenticated, size-limited, privacy-reviewed API design and explicit approval. Keep the current allowlist intact. USB serial has a narrower backend/API change but depends on unverified physical USB/UART capability and sustained transfer.

## 4. Tests and verification

The Step 8 work performed source/report inspection only. It did not run runtime, audio, model, network, database, browser, or hardware tests. Step 7's environment blockers still apply: Python launcher/virtualenv unavailable, Node unavailable, Arduino toolchain unavailable, no identified ESP32, no private DB URL, and no PostgreSQL listener. See `SONIQ_STEP8_COMPATIBILITY_REPORT.md` and `SONIQ_STEP8_USB_SERIAL_IMPLEMENTATION_PLAN.md` for exact source evidence, transfer calculations, proposed tests, and rollback steps.

## 5. Approval and next inputs

Before any implementation, obtain explicit approval for:

1. USB-serial transport and proposed framed PCM16LE, mono, 16 kHz, one-second protocol (or a revised protocol).
2. An opt-in audio mode in `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` and a separate `tools/soniq_serial_audio_companion.py` with optional `pyserial` dependency.
3. The companion's ability to submit real model labels to the existing event API while setting confidence false and SPL null/uncalibrated.
4. Audio privacy, in-memory-only handling, deletion/retention, and whether any capture may be written to disk for troubleshooting.

Also identify the exact ESP32 board, microphone/module, USB/USB-UART chip, and COM port, and provide a privately configured approved database environment before claiming persistence. The team must separately approve confidence semantics and SPL calibration before any warning can be enabled. No password should be shared in chat.

## Final status

**NOT READY for a complete audio-to-warning demonstration.** The current source has no audio transport and required hardware/database checks are blocked. The design is documented; all behavior changes remain behind explicit approval.
