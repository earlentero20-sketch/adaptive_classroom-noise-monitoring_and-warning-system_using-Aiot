"""Small standard-library HTTP backend for provisional sensor events.

Run from the repository root with ``python -m backend.app``. The service is
local-only by default and never enables warnings without explicit settings.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import math
import os
from numbers import Real
from typing import Any
from urllib.parse import urlsplit

from ml.audio_inference import (
    InvalidAudioSample,
    ModelUnavailableError,
    load_audio_model,
    validate_wav_sample,
)
from ml.warning_policy import (
    STUDENT_CONVERSATION,
    TEACHER_DISCUSSION,
    WarningDecision,
    evaluate_warning,
)


SCHEMA_VERSION = "1.0"
SOUND_LEVEL_UNIT = "dB_SPL"
SENSOR_STATUSES = ("online", "offline", "unknown")
MAX_AUDIO_REQUEST_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class BackendConfig:
    warning_threshold_db_spl: float | None = None
    max_input_age_seconds: float | None = None
    warning_threshold_status: str | None = None
    freshness_window_status: str | None = None

    @classmethod
    def from_environment(cls) -> "BackendConfig":
        """Read positive limits and retain why each value is unavailable."""
        threshold, threshold_status = _environment_positive_number("WARNING_THRESHOLD_DB_SPL")
        max_age, freshness_status = _environment_positive_number("MAX_INPUT_AGE_SECONDS")
        return cls(threshold, max_age, threshold_status, freshness_status)


class RequestError(ValueError):
    """An event does not match the versioned request contract."""


def process_event(
    payload: Any,
    config: BackendConfig,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one event and return a dashboard-consumable response."""
    event = _object(payload, "event")
    if event.get("schema_version") != SCHEMA_VERSION:
        raise RequestError("schema_version must be '1.0'")
    event_id = _required_text(event, "event_id")
    device_id = _required_text(event, "device_id")
    received_at = _aware_datetime(now or datetime.now(timezone.utc), "server time")

    classification = _parse_classification(event.get("classification"))
    sound_level = _parse_sound_level(event.get("sound_level"))
    sensor_status = event.get("sensor_status", "unknown")
    if sensor_status not in SENSOR_STATUSES:
        raise RequestError("sensor_status must be online, offline, or unknown")

    class_status, class_freshness_reason = _freshness_status(
        classification["observed_at"],
        config.max_input_age_seconds,
        received_at,
        config.freshness_window_status,
    )
    sound_status, sound_freshness_reason = _freshness_status(
        sound_level["observed_at"],
        config.max_input_age_seconds,
        received_at,
        config.freshness_window_status,
    )

    decision = _warning_decision(
        classification,
        sound_level,
        class_status,
        sound_status,
        class_freshness_reason,
        sound_freshness_reason,
        config,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "device_id": device_id,
        "received_at": _format_datetime(received_at),
        "connection_status": {
            "backend": "online",
            "sensor": sensor_status,
        },
        "classification": {
            "label": classification["label"],
            "confident": classification["confident"],
            "observed_at": _format_optional_datetime(classification["observed_at"]),
            "status": class_status,
        },
        "sound_level": {
            "value": sound_level["value"],
            "unit": sound_level["unit"],
            "calibrated": sound_level["calibrated"],
            "observed_at": _format_optional_datetime(sound_level["observed_at"]),
            "status": sound_status,
        },
        "warning": {
            "triggered": decision.should_warn,
            "reason": decision.reason,
        },
    }


def _warning_decision(
    classification: dict[str, Any],
    sound_level: dict[str, Any],
    class_status: str,
    sound_status: str,
    class_freshness_reason: str,
    sound_freshness_reason: str,
    config: BackendConfig,
) -> WarningDecision:
    if classification["label"] is None:
        return WarningDecision(False, "classification_unavailable")
    if class_status != "fresh":
        return WarningDecision(False, class_freshness_reason)
    if sound_level["value"] is None:
        return WarningDecision(False, "sound_level_unavailable")
    if sound_status != "fresh":
        return WarningDecision(False, sound_freshness_reason)
    freshness_status = _configuration_value_status(
        config.max_input_age_seconds, config.freshness_window_status
    )
    if freshness_status != "configured":
        reason = "freshness_window_unconfigured" if freshness_status == "missing" else "freshness_window_invalid"
        return WarningDecision(False, reason)
    threshold_status = _configuration_value_status(
        config.warning_threshold_db_spl, config.warning_threshold_status
    )
    if threshold_status != "configured":
        reason = "threshold_unconfigured" if threshold_status == "missing" else "threshold_invalid"
        return WarningDecision(False, reason)
    return evaluate_warning(
        classification=classification["label"],
        classification_is_confident=classification["confident"],
        sound_level_db=sound_level["value"],
        threshold_db=config.warning_threshold_db_spl,
        level_is_calibrated=(
            sound_level["calibrated"] and sound_level["unit"] == SOUND_LEVEL_UNIT
        ),
    )


def _parse_classification(value: Any) -> dict[str, Any]:
    if value is None:
        return {"label": None, "confident": False, "observed_at": None}
    record = _object(value, "classification")
    label = record.get("label")
    if label is not None and label not in (TEACHER_DISCUSSION, STUDENT_CONVERSATION):
        raise RequestError("classification.label must be a confirmed model class or null")
    confident = record.get("confident", False)
    if type(confident) is not bool:
        raise RequestError("classification.confident must be a boolean")
    observed_at = _optional_datetime(record.get("observed_at"), "classification.observed_at")
    return {"label": label, "confident": confident, "observed_at": observed_at}


def _parse_sound_level(value: Any) -> dict[str, Any]:
    if value is None:
        return {"value": None, "unit": None, "calibrated": False, "observed_at": None}
    record = _object(value, "sound_level")
    reading = record.get("value")
    if reading is not None and not _finite_number(reading):
        raise RequestError("sound_level.value must be a finite number or null")
    unit = record.get("unit")
    if unit is not None and unit != SOUND_LEVEL_UNIT:
        raise RequestError(f"sound_level.unit must be '{SOUND_LEVEL_UNIT}' or null")
    calibrated = record.get("calibrated", False)
    if type(calibrated) is not bool:
        raise RequestError("sound_level.calibrated must be a boolean")
    observed_at = _optional_datetime(record.get("observed_at"), "sound_level.observed_at")
    return {
        "value": float(reading) if reading is not None else None,
        "unit": unit,
        "calibrated": calibrated,
        "observed_at": observed_at,
    }


def _freshness_status(
    observed_at: datetime | None,
    max_age_seconds: Real | None,
    now: datetime,
    configured_status: str | None = None,
) -> tuple[str, str]:
    if observed_at is None:
        return "unavailable", "measurement_unavailable"
    if max_age_seconds is None:
        reason = "freshness_window_invalid" if configured_status == "invalid" else "freshness_window_unconfigured"
        return "unknown", reason
    if not _finite_number(max_age_seconds) or max_age_seconds <= 0:
        return "unknown", "freshness_window_invalid"
    age_seconds = (now - observed_at).total_seconds()
    if age_seconds < 0:
        return "invalid_time", "measurement_time_in_future"
    if age_seconds > max_age_seconds:
        return "stale", "measurement_stale"
    return "fresh", "measurement_fresh"


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RequestError(f"{field} must be a JSON object")
    return value


def _required_text(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"{field} must be a non-empty string")
    return value


def _optional_datetime(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RequestError(f"{field} must be an ISO-8601 timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RequestError(f"{field} must be an ISO-8601 timestamp or null") from error
    return _aware_datetime(parsed, field)


def _aware_datetime(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RequestError(f"{field} must include a timezone")
    return value.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _format_optional_datetime(value: datetime | None) -> str | None:
    return _format_datetime(value) if value is not None else None


def _finite_number(value: Any) -> bool:
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _environment_positive_number(name: str) -> tuple[float | None, str]:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return None, "missing"
    try:
        value = float(raw_value)
    except ValueError:
        return None, "invalid"
    if not math.isfinite(value) or value <= 0:
        return None, "invalid"
    return value, "configured"


def _configuration_value_status(value: Any, source_status: str | None) -> str:
    if source_status in ("missing", "invalid"):
        return source_status
    if value is None:
        return "missing"
    if not _finite_number(value) or value <= 0:
        return "invalid"
    return "configured"


def _warning_configuration(config: BackendConfig) -> dict[str, Any]:
    threshold_status = _configuration_value_status(
        config.warning_threshold_db_spl, config.warning_threshold_status
    )
    freshness_status = _configuration_value_status(
        config.max_input_age_seconds, config.freshness_window_status
    )
    reasons = []
    if threshold_status != "configured":
        reasons.append(f"threshold_{threshold_status}")
    if freshness_status != "configured":
        reasons.append(f"freshness_window_{freshness_status}")
    return {
        "warning_configuration": "configured" if not reasons else "not_configured",
        "warning_configuration_status": "ready" if not reasons else "not_ready",
        "warning_configuration_reasons": reasons,
    }


class BackendHandler(BaseHTTPRequestHandler):
    server_version = "SONIQBackend/0.1"
    backend_config: BackendConfig

    def do_GET(self) -> None:
        if self.path != "/health":
            self._send_json(404, {"error": {"code": "not_found"}})
            return
        self._send_json(200, {
            "schema_version": SCHEMA_VERSION,
            "service": "soniq-backend",
            "status": "online",
            **_warning_configuration(self.server.backend_config),
        })

    def do_OPTIONS(self) -> None:
        if self.path not in ("/api/v1/events", "/api/v1/classify"):
            self._send_json(404, {"error": {"code": "not_found"}})
            return
        origin = self.headers.get("Origin", "")
        requested_method = self.headers.get("Access-Control-Request-Method", "")
        requested_headers = {
            name.strip().lower()
            for name in self.headers.get("Access-Control-Request-Headers", "").split(",")
            if name.strip()
        }
        if (
            not _is_loopback_origin(origin)
            or requested_method != "POST"
            or not requested_headers.issubset({"content-type"})
        ):
            self._send_json(403, {"error": {"code": "origin_or_preflight_not_allowed"}})
            return
        self.send_response(204)
        self._add_cors_headers(origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/v1/classify":
            self._classify_audio()
            return
        if self.path != "/api/v1/events":
            self._send_json(404, {"error": {"code": "not_found"}})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {
                "schema_version": SCHEMA_VERSION,
                "error": {"code": "unsupported_media_type"},
                "connection_status": {"backend": "online", "sensor": "unknown"},
                "warning": {"triggered": False, "reason": "invalid_event"},
            })
            return
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
            if content_length < 0:
                raise RequestError("Content-Length is required")
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body)
            response = process_event(payload, self.server.backend_config)
        except (RequestError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self._send_json(400, {
                "schema_version": SCHEMA_VERSION,
                "error": {"code": "invalid_event", "message": str(error)},
                "connection_status": {"backend": "online", "sensor": "unknown"},
                "warning": {"triggered": False, "reason": "invalid_event"},
            })
            return
        except (ValueError, OverflowError):
            self._send_json(400, {
                "schema_version": SCHEMA_VERSION,
                "error": {"code": "invalid_event", "message": "invalid request body"},
                "connection_status": {"backend": "online", "sensor": "unknown"},
                "warning": {"triggered": False, "reason": "invalid_event"},
            })
            return
        self._send_json(200, response)

    def _classify_audio(self) -> None:
        """Loopback-only adapter for one complete WAV sample and a local model."""
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                self._send_json(403, {"error": {"code": "loopback_only"}})
                return
        except ValueError:
            self._send_json(403, {"error": {"code": "loopback_only"}})
            return
        if self.headers.get_content_type() != "audio/wav":
            self._send_json(415, {"error": {"code": "unsupported_media_type"}})
            return
        try:
            try:
                content_length = int(self.headers.get("Content-Length", "-1"))
            except ValueError as error:
                raise InvalidAudioSample("Content-Length must be a positive integer") from error
            if content_length <= 0:
                raise InvalidAudioSample("Content-Length must describe a non-empty WAV sample")
            if content_length > MAX_AUDIO_REQUEST_BYTES:
                self._send_json(413, {"error": {"code": "audio_sample_too_large"}})
                return
            audio_bytes = self.rfile.read(content_length)
            if len(audio_bytes) != content_length:
                raise InvalidAudioSample("audio request body is incomplete")
            validate_wav_sample(audio_bytes)
            model = getattr(self.server, "audio_model", None)
            if model is None:
                artifact_path = os.environ.get("SONIQ_AUDIO_MODEL_PATH")
                if not artifact_path:
                    raise ModelUnavailableError("SONIQ_AUDIO_MODEL_PATH is not configured")
                model = load_audio_model(artifact_path)
                self.server.audio_model = model
            prediction = model.classify_wav_bytes(audio_bytes)
            label = prediction["label"]
            if label not in (TEACHER_DISCUSSION, STUDENT_CONVERSATION):
                raise ModelUnavailableError("model returned a label outside the two-class contract")
            training_mode = prediction.get("training_mode", "evaluated_baseline")
            experimental = training_mode == "experimental_full_fit_no_held_out_evaluation"
            self._send_json(200, {
                "schema_version": SCHEMA_VERSION,
                "inference": {
                    "status": "complete",
                    "source": "experimental_model" if experimental else "trained_model",
                    "evaluation_status": "not_evaluated" if experimental else "held_out_evaluated",
                },
                "classification": {
                    "label": label,
                    "model_confidence": prediction.get("model_confidence"),
                    "artifact_reference": prediction.get("artifact_reference"),
                    "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
                "warning_evaluation": {"status": "not_performed"},
                "connection_status": {"backend": "online", "hardware": "not_tested"},
            })
        except InvalidAudioSample as error:
            self._send_json(400, {"error": {"code": "invalid_audio", "message": str(error)}})
        except ModelUnavailableError as error:
            self._send_json(503, {
                "inference": {"status": "unavailable"},
                "model_status": "missing_or_unavailable",
                "error": {"code": "model_unavailable", "message": str(error)},
                "warning_evaluation": {"status": "not_performed"},
                "connection_status": {"backend": "online", "hardware": "not_tested"},
            })
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            self._send_json(503, {
                "inference": {"status": "unavailable"},
                "model_status": "inference_error",
                "error": {"code": "inference_unavailable", "message": str(error)},
                "warning_evaluation": {"status": "not_performed"},
                "connection_status": {"backend": "online", "hardware": "not_tested"},
            })

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        origin = self.headers.get("Origin", "")
        if _is_loopback_origin(origin):
            self._add_cors_headers(origin)
        self.end_headers()
        self.wfile.write(encoded)

    def _add_cors_headers(self, origin: str) -> None:
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")

    def log_message(self, format_string: str, *args: Any) -> None:
        print("backend:", format_string % args)


def _is_loopback_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme in ("http", "https")
            and parsed.hostname in ("localhost", "127.0.0.1", "::1")
            and parsed.username is None
            and parsed.password is None
            and parsed.path == ""
            and parsed.query == ""
            and parsed.fragment == ""
        )
    except ValueError:
        return False


class ConfiguredHTTPServer(HTTPServer):
    def __init__(
        self, address: tuple[str, int], config: BackendConfig, *, audio_model: Any = None
    ):
        self.backend_config = config
        self.audio_model = audio_model
        super().__init__(address, BackendHandler)


def main() -> None:
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port_text = os.environ.get("BACKEND_PORT", "8000")
    try:
        port = int(port_text)
        if not 0 < port < 65536:
            raise ValueError
    except ValueError as error:
        raise SystemExit("BACKEND_PORT must be between 1 and 65535") from error

    config = BackendConfig.from_environment()
    with ConfiguredHTTPServer((host, port), config) as server:
        print(f"SONIQ backend listening at http://{host}:{port}")
        configuration = _warning_configuration(config)
        if configuration["warning_configuration_status"] != "ready":
            reasons = ", ".join(configuration["warning_configuration_reasons"])
            print(f"warning configuration is not ready ({reasons}); buzzer decisions stay off")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping SONIQ backend")


if __name__ == "__main__":
    main()
