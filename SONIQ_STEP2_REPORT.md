# SONIQ Step 2 — ESP32, ML Classification, and Warning Integration

**Date:** 2026-11-09  
**Readiness:** **BLOCKED for complete integration.** Source inspection confirms that the ESP32 does not transmit audio or calibrated SPL. Existing software paths are separate. No firmware or API changes were made because an audio transport, privacy behavior, confidence rule, and calibrated measurement source must be agreed first.

## Data flow before this step

1. The ESP32 INMP441 interface uses I2S RX at 16,000 Hz, 32-bit container words, left channel. `readMicrophoneRMS()` reads up to 512 32-bit words (about 32 ms at 16 kHz), shifts them to the 24-bit sample, normalizes, and calculates RMS.
2. The firmware uses that RMS only for local QUIET/MODERATE/LOUD LEDs. It explicitly documents that its RMS thresholds are not calibrated dB SPL.
3. Every two seconds, firmware sends a JSON event to `POST /api/v1/events` containing schema version, event/device IDs, `sensor_status: online`, `classification: {label: null, confident: false, observed_at: null}`, and `sound_level: {value: null, unit: null, calibrated: false, observed_at: null}`. No sample bytes, features, RMS field, SPL value, or classification are transmitted.
4. The backend event route validates the event, runs warning policy on the fields supplied, persists the processed event, and returns the warning decision. Given the firmware's current null fields, the decision is fail-closed (`classification_unavailable`).
5. Separately, the backend's `POST /api/v1/classify` accepts one complete PCM WAV body (`Content-Type: audio/wav`), uses a configured local `SONIQ_AUDIO_MODEL_PATH`, and returns a label plus optional uncalibrated probability. It is restricted to loopback clients; it does not create an event or evaluate warning policy. Enabling the private-LAN listener in Step 1 does not remove this client restriction.

## Existing model and preprocessing contract

Three existing serialized artifacts were found and preserved:

- `ml/artifacts/experimental-demo-local/experimental_model.joblib`
- `ml/artifacts/experimental-demo-school-20261020/experimental_model.joblib`
- `ml/artifacts/expanded-local-demo-20261020/experimental_model.joblib`

Their metadata reports the same two labels, `Teacher Discussion` and `Student Conversation`, and `training_mode: experimental_full_fit_no_held_out_evaluation`. They report no held-out metrics; the dataset manifests/review fields are not formally cleared. They are experimental artifacts, not an evaluated or approved production model. This report does not replace or retrain them.

The inference adapter accepts a complete uncompressed PCM WAV (1, 2, 3, or 4 byte PCM sample widths are accepted by the WAV validator). For the expanded artifact, serialized preprocessing is:

- target mono waveform at 16,000 Hz;
- 1.0 second (16,000 frames), center crop or pad as needed;
- channel mix `mean`, linear resampling, no peak normalization;
- librosa MFCC mean/std feature vector: 20 MFCCs, 40 mel bins, 400-sample FFT/window, 160-sample hop, Hann window, 0–7,600 Hz.

The firmware currently supplies neither this one-second WAV nor an equivalent feature vector. Its 512-sample blocks would need to be accumulated into an approved window and encoded into a PCM WAV or handled by a separately designed compatible transport. The `classify` API is whole-WAV, not a streaming or raw I2S endpoint.

The model's optional `predict_proba` output is explicitly marked uncalibrated. It is not the event contract's `classification.confident` decision. `ml.inference.classification_result()` defaults `confident` to false; the team has not approved a confidence cutoff or policy for setting it true.

## Warning policy integration

The backend is the warning source of truth and calls the existing policy only through `POST /api/v1/events`. For an event to trigger, it requires:

- exact `Student Conversation` label and `classification.confident: true`;
- fresh timezone-aware classification and sound measurement timestamps;
- configured valid threshold and maximum input age (threshold at least 75 dB SPL, age no more than 30 seconds);
- finite sound value, `unit: dB_SPL`, and `calibrated: true`;
- sound strictly greater than the configured threshold. Exactly 75 dB does not trigger at the minimum threshold; `Teacher Discussion` never triggers.

The separate classification route returns `warning_evaluation: not_performed`. A future companion must map an actual label to the unchanged event contract and submit that event to `/api/v1/events`; it must not derive `confident=true` from the uncalibrated probability. The current firmware checks the event response's warning Boolean and resets authorization on false/error/stale connection. `ENABLE_PHYSICAL_BUZZER` is false, so physical activation remains locked off.

## SPL calibration status

**No SPL calibration exists in the firmware.** The code calculates normalized digital RMS and applies local relative LED thresholds. No microphone sensitivity, acoustic reference, A-weighting/time weighting, RMS-to-SPL transfer calibration, uncertainty, or calibration record is implemented. These values must not be labeled dB SPL and cannot activate the backend warning policy.

Before reporting SPL from this sensor, the hardware owner should select a measurement definition (including frequency and time weighting), fix the microphone/module, enclosure, gain, and placement, compare against a suitable calibrated reference over the intended level range, derive and validate conversion parameters, document uncertainty and calibration date, and repeat calibration after hardware/gain/placement changes. A calibrated independent meter can instead supply the reading, but it must be time-aligned to the classification and explicitly identified as the source. No calibration values were invented here.

## Smallest compatible path

The already documented local-demonstration proposal in `docs/INTEGRATION_PLAN.md` is the least disruptive current option:

1. With firmware-owner approval, accumulate a bounded 1-second (16,000-sample) mono capture and transfer samples plus device/capture identifiers to a host companion over USB serial. Agree framing, sample quantization, buffering, timestamps, and audio privacy/retention before changing firmware.
2. The companion creates a valid PCM WAV at 16 kHz and calls the existing loopback-only `/api/v1/classify` endpoint. This preserves the current inference API and avoids exposing model inference to LAN clients.
3. Obtain an approved independent calibrated SPL reading and approved classification confidence rule. Without either input, warning must remain off.
4. The companion posts one event through the existing `/api/v1/events` contract. The backend performs the existing policy decision and persists it. Any returned hardware authorization needs separate review; the current sketch's buzzer remains disabled.

No code integration was implemented because the present hardware payload lacks the necessary audio and SPL, and the transport, confidence gate, calibration source, and privacy requirements are unresolved. Directly sending PCM audio to the LAN backend would require a separately reviewed/authenticated inference transport; `/api/v1/classify` intentionally remains loopback-only.

## Files modified

- `docs/INTEGRATION_PLAN.md` — corrected the model availability note: experimental artifacts are present, but are unevaluated and not formally cleared.
- `SONIQ_STEP2_REPORT.md` — this inspection, compatibility, test, and blocker report.

No firmware, backend route, API contract, model, dataset, database schema, or warning policy code was changed.

## Integration tests and results

| Check | Result | Detail |
|---|---|---|
| Firmware acquisition/payload inspection | **CODE REVIEWED** | 16 kHz I2S RMS acquisition; 512-sample blocks; event JSON has null classification and SPL. No audio transport exists in the sketch. |
| Existing audio/model artifacts | **FOUND; LOAD NOT TESTED** | PCM WAV recordings and three experimental `.joblib` artifacts exist. Artifact metadata identifies them as no-held-out-evaluation and data review incomplete. |
| Actual WAV model inference | **NOT TESTED** | Could not run because the Python alias is inaccessible and the bundled `ml/.venv` points to a missing Python installation. No actual classification result is reported. |
| Warning-policy tests / event integration | **NOT TESTED AT RUNTIME** | Source path and fail-closed conditions were inspected. Existing tests were not executable in this environment. No fabricated event or warning result was created. |
| Invalid WAV rejection | **NOT TESTED AT RUNTIME** | Source validates complete uncompressed PCM WAV and returns `invalid_audio` for malformed/unsupported input; test suite could not be run. |
| SPL calibration | **NOT PRESENT / NOT TESTED** | No calibrated measurement source or calibration coefficients/procedure exist in firmware. |
| ESP32 compilation and physical capture/network test | **NOT TESTED** | No supported board toolchain/device was available. |

## Remaining hardware and project requirements

- Approve serial framing/window format and whether the ESP32 can buffer/send a one-second sample reliably.
- Approve audio handling, privacy, retention, and local companion behavior.
- Restore a valid Python environment and dependencies; verify the selected existing artifact loads, then run inference on actual available WAV clips. Treat outputs as experimental and not performance claims.
- Agree an explicit confidence rule before mapping model output to `classification.confident`.
- Provide calibrated SPL readings or complete and document sensor calibration against an appropriate reference.
- Test backend event persistence and warning behavior with valid approved inputs; test fail-closed cases.
- Compile and test the firmware on the actual ESP32/microphone; confirm network, timing, memory, returned warning, and keep the physical buzzer disabled until separately authorized safety tests pass.
