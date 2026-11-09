# SONIQ USB Serial Audio Protocol (SQAU/1)

**State:** Host receiver and parser implemented; firmware compatibility and physical audio remain **NOT TESTED**. The existing ESP32 sketch does not emit this protocol. The framing below turns Step 8's design candidate into a concrete host contract for future firmware work; it is not evidence that any current board can capture, convert, buffer, or sustain the transfer.

## Compatibility gate

The only verified firmware facts are the checked-in sketch's 16 kHz I2S setting, left-channel selection, 32-bit read container, pins, and 115200 baud console. The effective microphone bit depth, word alignment, PCM conversion, board identity, available memory, USB-UART behavior, and transfer throughput are unknown. The sketch currently discards I2S blocks after RMS/LED work and sends JSON over Wi-Fi; it does not send audio. Keep its event-only default unchanged until an identified board is tested and firmware deliberately adopts SQAU/1.

SQAU/1 requires firmware to capture exactly 16,000 mono frames as signed 16-bit little-endian PCM at 16 kHz, buffer or otherwise transfer the whole one-second capture, and emit only protocol records during an audio transfer (no interleaved free-form serial logs). A 1,024-byte DATA limit means 32 chunks for a 32,000-byte capture. CRC detects accidental corruption; it does not authenticate the sender.

## Wire format

Each record is `COBS(decoded_record) || 0x00`. COBS uses the standard code-byte algorithm. Integer fields below are unsigned big-endian unless stated. The CRC is standard reflected CRC-32/ISO-HDLC (Python `zlib.crc32`), stored as uint32 big-endian and calculated over header plus payload, excluding the CRC itself.

### Common header (28 bytes)

| Offset | Size | Field | Rule |
|---:|---:|---|---|
| 0 | 4 | Magic | ASCII `SQAU` |
| 4 | 1 | Version | `1` |
| 5 | 1 | Type | `1=START`, `2=DATA`, `3=END`, `4=ERROR` |
| 6 | 16 | Capture ID | Opaque UUID bytes; identical on all records in a capture |
| 22 | 4 | Sequence | START is `0`; DATA starts at `1`; END follows the last DATA |
| 26 | 2 | Payload length | Exact number of payload bytes; maximum payload is 1,024 |

The common header and payload are followed by the four-byte record CRC. The full decoded record may not exceed 1,056 bytes (header + 1,024 payload + CRC).

### Record payloads

- **START:** `sample_rate:u32, channels:u8, encoding:u8, frames:u32`; exactly `16000, 1, 1, 16000`. Encoding `1` means signed PCM16 little-endian. START with any other format is rejected.
- **DATA:** 1–1,024 PCM bytes, even length, and in capture order. Sequence numbers are contiguous. Do not split a 16-bit sample.
- **END:** `data_packet_count:u32, total_frames:u32, capture_crc32:u32`; frame count must equal 16,000. Capture CRC uses the same CRC-32/ISO-HDLC algorithm over the concatenated PCM bytes.
- **ERROR:** any payload indicates device-side failure; host discards the active capture.

The receiver rejects bad framing/CRC, unsupported version/format, oversized and empty DATA, sequence gaps/duplicates, capture-ID changes, invalid END counts, corrupt whole-capture CRC, incomplete samples, and an incomplete capture after ten seconds. A failed capture is discarded. A later record delimiter permits framing resynchronization. Memory use is capped at one 32,000-byte capture plus one bounded frame.

## Host use

The standard-library parser and WAV builder are in `tools/soniq_serial_audio_companion.py`. Parser tests run without pyserial or hardware:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tools.test_soniq_serial_audio_companion
```

Actual serial use additionally requires an identified COM device and pyserial installed in the selected environment. The receiver requires explicit `--port`, bench-verified `--baud`, and `--device-id`; it does not auto-select hardware. It sends only a complete validated capture as in-memory PCM WAV to the existing loopback classifier. It does not save audio. Event submission is opt-in (`--submit-event`) and uses the exact returned class/time, `confident=false`, unknown sensor status, and null sound level. It may report persistence only on HTTP 200 from the existing event API; database-unavailable and duplicate responses remain failures/duplicates.

Example after firmware and hardware are verified:

```powershell
.\.venv\Scripts\python.exe tools\soniq_serial_audio_companion.py --port COM4 --baud 921600 --device-id ESP32_CLASSROOM_01
```

The baud shown is a candidate only and has **not** been verified for this board; substitute only a measured, firmware-supported value. `pyserial` is optional and not installed by this repository change. The backend must run locally with its trusted model configured. Add `--submit-event` only when the intended existing PostgreSQL database and schema are verified. Confidence remains false and SPL null, so the event warning policy must fail closed.

## Required bench validation before a live claim

Identify the ESP32 variant, USB-UART interface, microphone and wiring; verify I2S bit alignment/sign and actual PCM against a trusted independent recording; measure free heap and sustained transfer rate under normal Wi-Fi/LED load; test disconnects and all parser errors; then classify one captured WAV. Test persistence separately against the existing approved PostgreSQL database. This protocol does not authorize changing the firmware or warning output by itself.
