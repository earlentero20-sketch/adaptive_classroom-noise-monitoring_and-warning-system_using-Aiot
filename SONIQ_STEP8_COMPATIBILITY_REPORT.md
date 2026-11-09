# SONIQ Step 8 — USB-Serial Compatibility Report

**Inspection date:** 2026-11-09 (Asia/Manila)  
**Overall:** **PARTIALLY VERIFIED FROM SOURCE; PHYSICAL COMPATIBILITY NOT VERIFIED.** This was a read-only design review. No firmware, backend, API, model, database, or dashboard behavior was changed.

## Status key

- **VERIFIED** — directly confirmed from checked-in source or repository configuration only.
- **NOT VERIFIED** — requires hardware, runtime, or external evidence.
- **BLOCKED** — required tool, service, environment, or hardware was unavailable in the Step 7 test environment.
- **REQUIRES APPROVAL** — would change behavior, transport, or dependencies.

## Existing data flow

```text
I2S microphone -> 512-word RMS/LED calculation -> (samples discarded)
ESP32 Wi-Fi -> POST /api/v1/events (classification null, sound level null)
Host WAV -> loopback POST /api/v1/classify -> model response only
Host event -> POST /api/v1/events -> warning policy -> PostgreSQL -> dashboard history
```

The arrows are separate lifecycles today. There is no current path from ESP32 audio to classification, nor from classifier output automatically to event persistence. `POST /api/v1/classify` does not evaluate warnings or save events. The dashboard reads returned health and persisted history and does not calculate classifications or warnings.

## Hardware and firmware compatibility matrix

| Item | Source evidence / status |
|---|---|
| Firmware path | **VERIFIED:** `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` |
| Framework / I2S API | **VERIFIED:** Arduino sketch; includes legacy `driver/i2s.h`. Exact Arduino-ESP32 core/toolchain version **UNKNOWN**. |
| ESP32 board model/revision | **UNKNOWN.** Sketch does not identify it; no physical board was confirmed. |
| Microphone model/interface | **PARTLY VERIFIED:** source configures an I2S input and logs “INMP441 initialized”; exact module/wiring/physical identity **NOT VERIFIED**. |
| I2S pins | **VERIFIED in source:** WS 25, SCK 26, SD 33. Physical wiring **NOT VERIFIED**. |
| Sampling rate | **VERIFIED in source:** `SAMPLE_RATE=16000` and configured as I2S sample rate. Physical clock accuracy **NOT VERIFIED**. |
| Channel selection | **VERIFIED in source:** `I2S_CHANNEL_FMT_ONLY_LEFT`; one selected channel. Physical microphone/channel output **NOT VERIFIED**. |
| Container width | **VERIFIED in source:** I2S configured for 32-bit words. Effective ADC/microphone precision, alignment, sign-extension, and PCM conversion **UNKNOWN**. The current code shifts the word right 8 bits for RMS; that does not prove PCM audio conversion. |
| Existing capture buffer | **VERIFIED in source:** 512 × `int32_t` local array = 2,048 bytes (nominal 32 ms at 16 kHz); used for RMS only, then discarded. I2S DMA config is 4 buffers × 256 frames (source settings). |
| Available RAM / PSRAM | **UNKNOWN.** Board SKU and measured free heap/PSRAM unavailable. A proposed 32 KB PCM16 one-second buffer cannot be cleared as safe from source alone. |
| Existing serial rate | **VERIFIED in source:** `Serial.begin(115200)`. Serial currently carries text logs only. USB native CDC vs USB-UART bridge and sustained baud support **UNKNOWN**. |
| Existing network event endpoint | **VERIFIED in source:** Wi-Fi posts JSON to configured `/api/v1/events` URL, with null classification and sound measurement. Current URL is a sample private IP. |
| Buzzer | **VERIFIED in source:** physical buzzer operation disabled (`ENABLE_PHYSICAL_BUZZER=false`). Hardware output **NOT TESTED**. |
| Physical connection / COM port | **BLOCKED in Step 7 environment:** only COM1 was enumerated; no ESP32 port was identified. It does not establish that hardware is unavailable on another machine. |

## Audio size and serial rate

Candidate format, subject to artifact metadata and actual capture verification: PCM16LE, mono, 16 kHz, 16,000 frames (1 second) = **32,000 audio bytes**. This is not current firmware output. The current source's I2S container would occupy 64,000 bytes for one second if retained as 32-bit words, but effective sensor precision is unknown.

At 115,200 baud, UART 8-N-1 ideal application-byte capacity is roughly 11,520 bytes/s. A 32,000-byte payload has a raw lower-bound serialization time of **2.78 seconds**, before framing/CRC/USB/driver overhead. Therefore, existing baud is insufficient for live streaming at a 32 kB/s PCM rate. A buffered capture could be transferred later only if RAM and firmware scheduling allow it. A faster baud (921,600 is a possible test point) is **NOT VERIFIED** on the unidentified board, cable, USB-UART interface, and Windows driver.

## Host/backend/software compatibility

| Component | Finding |
|---|---|
| Classifier input | **VERIFIED from source:** `backend/app.py` accepts a complete `audio/wav` PCM body, validates content length and WAV format, then calls `ml/audio_inference.py`. Maximum request is 32 MiB. It is limited to loopback clients. |
| Model preprocessing | **VERIFIED from existing artifact metadata reviewed in Step 7:** experimental artifacts target mono 16 kHz / 1 second plus serialized preprocessing/features. Runtime metadata is authoritative; no artifact was loaded in this Step 8 review. Model compatibility with real ESP32-converted PCM is **NOT VERIFIED**. |
| Classifier response | **VERIFIED from source:** exact label, observed time, artifact/evaluation metadata, optional probability marked uncalibrated, `warning_evaluation=not_performed`; no event save. |
| Event integration | **VERIFIED from source:** host can separately POST the existing v1 event with the returned label, but setting `confident=false` and null/un-calibrated sound measurement is necessary until approved confidence/calibration inputs exist. That event cannot trigger warning. |
| Database | **BLOCKED per Step 7:** `SONIQ_DATABASE_URL` and private `.env` absent in tested environment; no listener on `127.0.0.1:5432`. No live database connection, schema inspection, insert, or retrieval was tested. Existing schema/data remain untouched. |
| Dashboard | **VERIFIED from source:** `dashboard/backend-adapter.mjs` calls actual health/events and WAV classify endpoints; event history represents persisted records. Browser/live UI was not tested in Step 7. |
| Python serial dependency | **VERIFIED:** neither `backend/requirements.txt` nor `ml/requirements.txt` includes `pyserial`; no existing firmware/host serial receiver was found. `pyserial` would be a new optional companion dependency and **REQUIRES APPROVAL**. |
| Environment loading | **VERIFIED:** `backend/start_backend.py` reads root `.env` as UTF-8, accepts allowlisted `SONIQ_DATABASE_URL`, host/port, warning, model, and pool variables, and does not display values. Root `.env.example` already has placeholder-only URL/configuration; no template modification is needed. |
| Tests/tools | **BLOCKED in Step 7 environment:** Python virtualenv base interpreter was missing, Node unavailable, Arduino CLI/PlatformIO unavailable. No Step 8 runtime/hardware test was run. |

## Compatibility conclusion

The host/backend/model **interfaces are software-compatible in principle** with a one-second PCM WAV delivered to the host, followed by the existing classifier and event endpoints. This does not prove the ESP32 can safely allocate/convert the window or that the serial link can deliver it reliably. The existing 115,200 baud is too slow for real-time PCM16; buffered transfer is a candidate only after RAM and timing tests. The direct Wi-Fi path is not compatible with the current classifier allowlist/contract without added endpoint or security behavior.

**Decision:** **REQUIRES APPROVAL** for the proposed opt-in firmware mode, separate receiver, and optional dependency; **BLOCKED** for any claim of hardware reliability or end-to-end integration until actual board, capture conversion, serial transfer, inference, persistence, and dashboard are tested.

## Git preservation

Step 7 recorded 9,416 pre-existing staged deletions and 21 untracked paths before its two reports. This inspection did not modify the index. The Step 8 reports are new untracked documentation; no reset, clean, stage, commit, push, or mass-staging operation was performed.
