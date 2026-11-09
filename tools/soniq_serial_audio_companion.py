"""Optional host receiver for the SONIQ SQAU/1 USB audio protocol.

This module defines a host-side protocol candidate from the Step 8 design.
Firmware does not currently emit SQAU frames; use only after firmware adopts
the documented layout and physical capture/throughput tests pass.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import struct
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave
from io import BytesIO
import zlib


MAGIC = b"SQAU"
VERSION = 1
START, DATA, END, ERROR = 1, 2, 3, 4
PCM16LE = 1
SAMPLE_RATE_HZ = 16_000
CHANNELS = 1
EXPECTED_FRAMES = 16_000
MAX_DATA_BYTES = 1_024
CAPTURE_TIMEOUT_SECONDS = 10.0
HEADER = struct.Struct(">4sBB16sIH")
START_META = struct.Struct(">IBBI")
END_META = struct.Struct(">III")
CRC = struct.Struct(">I")
MAX_DECODED_FRAME = HEADER.size + max(MAX_DATA_BYTES, START_META.size, END_META.size) + CRC.size
MAX_ENCODED_FRAME = MAX_DECODED_FRAME + MAX_DECODED_FRAME // 254 + 2


class ProtocolError(ValueError):
    """Malformed or incompatible serial audio data."""


@dataclass(frozen=True)
class Capture:
    capture_id: bytes
    pcm16le: bytes


@dataclass
class _ActiveCapture:
    capture_id: bytes
    expected_frames: int
    started_at: float
    next_sequence: int = 1
    packet_count: int = 0
    pcm: bytearray | None = None


def cobs_encode(data: bytes) -> bytes:
    """Encode one non-delimited record using Consistent Overhead Byte Stuffing."""
    output = bytearray([0])
    code_index = 0
    code = 1
    for value in data:
        if value == 0:
            output[code_index] = code
            code_index = len(output)
            output.append(0)
            code = 1
        else:
            output.append(value)
            code += 1
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1
    output[code_index] = code
    return bytes(output)


def cobs_decode(data: bytes) -> bytes:
    if not data or 0 in data:
        raise ProtocolError("invalid COBS record")
    output = bytearray()
    index = 0
    while index < len(data):
        code = data[index]
        if code == 0:
            raise ProtocolError("invalid COBS code")
        index += 1
        end = index + code - 1
        if end > len(data):
            raise ProtocolError("truncated COBS record")
        output.extend(data[index:end])
        index = end
        if code != 0xFF and index < len(data):
            output.append(0)
    return bytes(output)


def encode_record(kind: int, capture_id: bytes, sequence: int, payload: bytes = b"") -> bytes:
    """Encode a protocol record; exposed for firmware conformance tooling/tests."""
    if len(capture_id) != 16:
        raise ValueError("capture_id must contain exactly 16 bytes")
    if not 0 <= sequence <= 0xFFFFFFFF:
        raise ValueError("sequence is outside uint32 range")
    if len(payload) > MAX_DATA_BYTES:
        raise ValueError("record payload exceeds the protocol limit")
    header = HEADER.pack(MAGIC, VERSION, kind, capture_id, sequence, len(payload))
    raw = header + payload
    raw += CRC.pack(zlib.crc32(raw) & 0xFFFFFFFF)
    return cobs_encode(raw) + b"\x00"


class CaptureAssembler:
    """Bounded streaming decoder that yields only complete, CRC-verified PCM."""

    def __init__(self, *, capture_timeout: float = CAPTURE_TIMEOUT_SECONDS):
        if capture_timeout <= 0:
            raise ValueError("capture_timeout must be positive")
        self.capture_timeout = capture_timeout
        self._frame = bytearray()
        self._active: _ActiveCapture | None = None

    def reset(self) -> None:
        self._frame.clear()
        self._active = None

    def feed(self, data: bytes, *, now: float | None = None) -> list[Capture]:
        current_time = time.monotonic() if now is None else now
        completed: list[Capture] = []
        for value in data:
            if value == 0:
                if not self._frame:
                    continue
                frame = bytes(self._frame)
                self._frame.clear()
                try:
                    result = self._accept_frame(cobs_decode(frame), current_time)
                except ProtocolError:
                    self._active = None
                    raise
                if result is not None:
                    completed.append(result)
            else:
                self._frame.append(value)
                if len(self._frame) > MAX_ENCODED_FRAME:
                    self._frame.clear()
                    self._active = None
                    raise ProtocolError("encoded frame exceeds the protocol limit")
        if self._active and current_time - self._active.started_at > self.capture_timeout:
            self._active = None
            raise ProtocolError("capture timed out before a complete END record")
        return completed

    def _accept_frame(self, raw: bytes, now: float) -> Capture | None:
        if len(raw) < HEADER.size + CRC.size:
            raise ProtocolError("record is shorter than its header and CRC")
        magic, version, kind, capture_id, sequence, payload_length = HEADER.unpack_from(raw)
        if magic != MAGIC:
            raise ProtocolError("record magic does not match SQAU")
        if version != VERSION:
            raise ProtocolError("unsupported serial protocol version")
        if payload_length > MAX_DATA_BYTES or len(raw) != HEADER.size + payload_length + CRC.size:
            raise ProtocolError("record payload length is invalid")
        expected_crc = CRC.unpack_from(raw, len(raw) - CRC.size)[0]
        if zlib.crc32(raw[:-CRC.size]) & 0xFFFFFFFF != expected_crc:
            raise ProtocolError("record CRC-32 mismatch")
        payload = raw[HEADER.size:-CRC.size]

        if kind == START:
            if sequence != 0 or len(payload) != START_META.size:
                raise ProtocolError("START sequence or metadata length is invalid")
            sample_rate, channels, encoding, expected_frames = START_META.unpack(payload)
            if (sample_rate, channels, encoding, expected_frames) != (
                SAMPLE_RATE_HZ, CHANNELS, PCM16LE, EXPECTED_FRAMES
            ):
                raise ProtocolError("START format is not the supported 16 kHz mono PCM16LE window")
            self._active = _ActiveCapture(
                capture_id, expected_frames, now, pcm=bytearray()
            )
            return None

        active = self._active
        if active is None:
            raise ProtocolError("record arrived without an active capture")
        if now - active.started_at > self.capture_timeout:
            self._active = None
            raise ProtocolError("capture timed out")
        if capture_id != active.capture_id:
            raise ProtocolError("record capture ID changed before END")
        if sequence != active.next_sequence:
            raise ProtocolError("record sequence is missing, duplicated, or out of order")

        if kind == DATA:
            if not payload or len(payload) > MAX_DATA_BYTES or len(payload) % 2:
                raise ProtocolError("DATA payload must be non-empty, bounded, and sample-aligned")
            assert active.pcm is not None
            if len(active.pcm) + len(payload) > active.expected_frames * 2:
                raise ProtocolError("DATA exceeds the declared capture frame count")
            active.pcm.extend(payload)
            active.packet_count += 1
            active.next_sequence += 1
            return None

        if kind == ERROR:
            self._active = None
            raise ProtocolError("device reported a capture error")

        if kind == END:
            if len(payload) != END_META.size:
                raise ProtocolError("END metadata length is invalid")
            packet_count, frame_count, capture_crc = END_META.unpack(payload)
            assert active.pcm is not None
            pcm = bytes(active.pcm)
            if (packet_count != active.packet_count or frame_count != active.expected_frames
                    or len(pcm) != frame_count * 2):
                raise ProtocolError("END counts do not match received PCM")
            if zlib.crc32(pcm) & 0xFFFFFFFF != capture_crc:
                raise ProtocolError("whole-capture CRC-32 mismatch")
            self._active = None
            return Capture(active.capture_id, pcm)

        raise ProtocolError("unknown record type")


def pcm_to_wav(pcm16le: bytes) -> bytes:
    if len(pcm16le) != EXPECTED_FRAMES * 2:
        raise ProtocolError("capture does not contain exactly one supported window")
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE_HZ)
        wav.writeframes(pcm16le)
    return output.getvalue()


def _post_json(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise RuntimeError("backend connection failed") from error
    with response:
        try:
            body = json.loads(response.read())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("backend returned an invalid JSON response") from error
        if not isinstance(body, dict):
            raise RuntimeError("backend response must be a JSON object")
        return response.status, body


def classify_capture(wav_bytes: bytes, backend_url: str) -> dict[str, Any]:
    request = Request(
        backend_url.rstrip("/") + "/api/v1/classify",
        data=wav_bytes,
        headers={"Content-Type": "audio/wav"},
        method="POST",
    )
    try:
        response = urlopen(request, timeout=120)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise RuntimeError("backend connection failed") from error
    with response:
        try:
            body = json.loads(response.read())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("classifier returned invalid JSON") from error
        if not isinstance(body, dict):
            raise RuntimeError("classifier response must be a JSON object")
        if response.status != 200:
            error_body = body.get("error")
            error_code = error_body.get("code", "unknown_error") if isinstance(error_body, dict) else "unknown_error"
            raise RuntimeError(
                f"classifier returned HTTP {response.status}: {error_code}"
            )
        classification = body.get("classification")
        if (not isinstance(classification, dict)
                or classification.get("label") not in ("Teacher Discussion", "Student Conversation")
                or not isinstance(classification.get("observed_at"), str)):
            raise RuntimeError("classifier response does not satisfy the existing response contract")
        return body


def submit_fail_closed_event(
    classification_response: dict[str, Any], *, backend_url: str, device_id: str, capture_id: bytes
) -> tuple[int, dict[str, Any]]:
    classification = classification_response["classification"]
    event_id = f"{device_id}:{capture_id.hex()}"
    event = {
        "schema_version": "1.0",
        "event_id": event_id,
        "device_id": device_id,
        "sensor_status": "unknown",
        "classification": {
            "label": classification["label"],
            "confident": False,
            "observed_at": classification["observed_at"],
        },
        "sound_level": None,
    }
    return _post_json(backend_url.rstrip("/") + "/api/v1/events", event)


def _read_one_capture(port: str, baud: int) -> Capture:
    try:
        import serial
    except ImportError as error:
        raise RuntimeError("serial reception requires the optional pyserial package") from error
    assembler = CaptureAssembler()
    # Windows CreateFile opens COM ports exclusively; pyserial's explicit
    # `exclusive` argument is POSIX-specific.
    with serial.Serial(port, baudrate=baud, timeout=0.1) as link:
        print(f"Listening on explicitly selected {port} at {baud} baud; waiting for SQAU/1 capture.")
        while True:
            chunk = link.read(4096)
            for value in chunk:
                try:
                    captures = assembler.feed(bytes((value,)))
                except ProtocolError as error:
                    print(f"Discarded invalid or incomplete serial capture: {error}", file=sys.stderr)
                    continue
                if captures:
                    return captures[0]
            try:
                assembler.feed(b"")
            except ProtocolError as error:
                print(f"Discarded invalid or incomplete serial capture: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="explicit serial port, such as COM4")
    parser.add_argument("--baud", required=True, type=int, help="bench-verified serial baud rate")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--submit-event", action="store_true", help="submit one fail-closed event after classification")
    args = parser.parse_args(argv)
    if not args.device_id.strip() or not 1 <= args.baud <= 4_000_000:
        parser.error("device-id must be non-empty and baud must be between 1 and 4000000")
    try:
        capture = _read_one_capture(args.port, args.baud)
        result = classify_capture(pcm_to_wav(capture.pcm16le), args.backend)
        print(json.dumps({"capture_id": capture.capture_id.hex(), "classification_response": result}, indent=2))
        if args.submit_event:
            status, body = submit_fail_closed_event(
                result, backend_url=args.backend, device_id=args.device_id, capture_id=capture.capture_id
            )
            print(json.dumps({"event_http_status": status, "event_response": body}, indent=2))
            if status != 200:
                return 3
        return 0
    except (ProtocolError, RuntimeError, OSError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            print("Interrupted; incomplete capture discarded.", file=sys.stderr)
        else:
            print(f"Receiver stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
