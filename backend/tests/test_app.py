from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from io import BytesIO
import json
from pathlib import Path
import socket
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import wave
from urllib.parse import urlsplit

from backend.app import BackendConfig, ConfiguredHTTPServer, process_event
from backend.postgres_event_repository import DuplicateEventError, EventStorageError


NOW = datetime(2026, 10, 11, 4, 0, tzinfo=timezone.utc)


def event_payload(*, classification="Student Conversation", level=75.0):
    observed = NOW.isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "1.0",
        "event_id": "event-test",
        "device_id": "device-test",
        "sensor_status": "online",
        "classification": {
            "label": classification,
            "confident": True,
            "observed_at": observed,
        },
        "sound_level": {
            "value": level,
            "unit": "dB_SPL",
            "calibrated": True,
            "observed_at": observed,
        },
    }


def audio_fixture_bytes():
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\0\0" * 800)
    return output.getvalue()


def raw_post(base_url, path, headers, body=b"", *, shutdown_write=False):
    """Send low-level HTTP input for malformed and length-boundary tests."""
    parsed = urlsplit(base_url)
    connection = HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    try:
        connection.putrequest("POST", path)
        for name, value in headers:
            connection.putheader(name, value)
        connection.endheaders()
        if body:
            connection.send(body)
        if shutdown_write:
            connection.sock.shutdown(socket.SHUT_WR)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


class ProcessEventTests(unittest.TestCase):
    def setUp(self):
        self.config = BackendConfig(warning_threshold_db_spl=70.0, max_input_age_seconds=30.0)

    def test_valid_student_conversation_and_level_above_fixture_threshold_warns(self):
        response = process_event(event_payload(), self.config, now=NOW)
        self.assertTrue(response["warning"]["triggered"])
        self.assertEqual(response["classification"]["label"], "Student Conversation")
        self.assertEqual(response["sound_level"]["unit"], "dB_SPL")
        self.assertEqual(response["connection_status"]["sensor"], "online")

    def test_student_conversation_without_measurement_does_not_warn(self):
        payload = event_payload()
        payload["sound_level"] = None
        response = process_event(payload, self.config, now=NOW)
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["sound_level"]["status"], "unavailable")
        self.assertEqual(response["warning"]["reason"], "sound_level_unavailable")

    def test_missing_classification_does_not_warn(self):
        payload = event_payload()
        payload["classification"] = None
        response = process_event(payload, self.config, now=NOW)
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["classification"]["status"], "unavailable")
        self.assertEqual(response["warning"]["reason"], "classification_unavailable")

    def test_student_conversation_without_threshold_does_not_warn(self):
        response = process_event(
            event_payload(), BackendConfig(max_input_age_seconds=30.0), now=NOW
        )
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["warning"]["reason"], "threshold_unconfigured")

    def test_non_positive_direct_configuration_cannot_trigger_warning(self):
        for config, expected_reason in (
            (BackendConfig(warning_threshold_db_spl=0, max_input_age_seconds=30), "threshold_invalid"),
            (BackendConfig(warning_threshold_db_spl=-1, max_input_age_seconds=30), "threshold_invalid"),
            (BackendConfig(warning_threshold_db_spl=70, max_input_age_seconds=0), "freshness_window_invalid"),
            (BackendConfig(warning_threshold_db_spl=70, max_input_age_seconds=-1), "freshness_window_invalid"),
        ):
            with self.subTest(config=config):
                response = process_event(event_payload(), config, now=NOW)
                self.assertFalse(response["warning"]["triggered"])
                self.assertEqual(response["warning"]["reason"], expected_reason)

    def test_configuration_marked_invalid_cannot_trigger_even_if_numeric_values_exist(self):
        config = BackendConfig(
            warning_threshold_db_spl=70,
            max_input_age_seconds=30,
            warning_threshold_status="configured",
            freshness_window_status="invalid",
        )
        response = process_event(event_payload(), config, now=NOW)
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["warning"]["reason"], "freshness_window_invalid")

    def test_warning_stays_off_when_freshness_window_is_unconfigured(self):
        response = process_event(
            event_payload(), BackendConfig(warning_threshold_db_spl=70.0), now=NOW
        )
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["warning"]["reason"], "freshness_window_unconfigured")

    def test_stale_classification_or_sound_level_does_not_warn(self):
        for field in ("classification", "sound_level"):
            payload = event_payload()
            payload[field]["observed_at"] = (NOW - timedelta(seconds=31)).isoformat()
            with self.subTest(field=field):
                response = process_event(payload, self.config, now=NOW)
                self.assertFalse(response["warning"]["triggered"])
                self.assertEqual(response[field]["status"], "stale")

    def test_future_or_malformed_timestamps_do_not_warn(self):
        payload = event_payload()
        payload["sound_level"]["observed_at"] = (NOW + timedelta(seconds=1)).isoformat()
        response = process_event(payload, self.config, now=NOW)
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["sound_level"]["status"], "invalid_time")
        payload["sound_level"]["observed_at"] = "not-a-timestamp"
        with self.assertRaises(ValueError):
            process_event(payload, self.config, now=NOW)

    def test_teacher_discussion_does_not_warn_at_high_fixture_level(self):
        response = process_event(
            event_payload(classification="Teacher Discussion", level=90.0),
            self.config,
            now=NOW,
        )
        self.assertFalse(response["warning"]["triggered"])
        self.assertEqual(response["warning"]["reason"], "teacher_discussion")

    def test_invalid_class_and_sound_units_are_rejected(self):
        payload = event_payload(classification="Other")
        with self.assertRaises(ValueError):
            process_event(payload, self.config, now=NOW)
        payload = event_payload()
        payload["sound_level"]["unit"] = "dB"
        with self.assertRaises(ValueError):
            process_event(payload, self.config, now=NOW)

    def test_invalid_measurement_values_and_timestamps_are_rejected(self):
        for mutate in (
            lambda payload: payload["classification"].update(observed_at="bad-time"),
            lambda payload: payload["sound_level"].update(value=float("nan")),
            lambda payload: payload["sound_level"].update(value=float("inf")),
            lambda payload: payload["sound_level"].update(observed_at="bad-time"),
        ):
            payload = event_payload()
            mutate(payload)
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    process_event(payload, self.config, now=NOW)

    def test_invalid_environment_configuration_fails_closed(self):
        invalid_values = ("not-a-number", "nan", "inf", "-inf", "0", "-1")
        environment_fields = (
            ("WARNING_THRESHOLD_DB_SPL", "MAX_INPUT_AGE_SECONDS"),
            ("MAX_INPUT_AGE_SECONDS", "WARNING_THRESHOLD_DB_SPL"),
        )
        for field, other_field in environment_fields:
            for invalid_value in invalid_values:
                with self.subTest(field=field, value=invalid_value):
                    with patch.dict("os.environ", {
                        field: invalid_value,
                        other_field: "30" if other_field == "MAX_INPUT_AGE_SECONDS" else "70",
                    }, clear=True):
                        config = BackendConfig.from_environment()
                    self.assertIsNone(getattr(config, "warning_threshold_db_spl" if field == "WARNING_THRESHOLD_DB_SPL" else "max_input_age_seconds"))
                    self.assertEqual(
                        getattr(config, "warning_threshold_status" if field == "WARNING_THRESHOLD_DB_SPL" else "freshness_window_status"),
                        "invalid",
                    )
                    response = process_event(event_payload(), config, now=NOW)
                    self.assertFalse(response["warning"]["triggered"])

    def test_missing_environment_configuration_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            config = BackendConfig.from_environment()
        self.assertIsNone(config.warning_threshold_db_spl)
        self.assertIsNone(config.max_input_age_seconds)
        self.assertEqual(config.warning_threshold_status, "missing")
        self.assertEqual(config.freshness_window_status, "missing")
        response = process_event(event_payload(), config, now=NOW)
        self.assertFalse(response["warning"]["triggered"])


class FakeEventRepository:
    def __init__(self):
        self.events = []
        self.error = None

    def save_event(self, event):
        if self.error is not None:
            raise self.error
        self.events.append(event)


class HTTPHandlerTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeEventRepository()
        self.server = ConfiguredHTTPServer(
            ("127.0.0.1", 0), BackendConfig(warning_threshold_db_spl=None),
            event_repository=self.repository,
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def post_event(self, payload):
        request = Request(
            f"{self.base_url}/api/v1/events",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request)

    def test_health_endpoint_returns_structured_status(self):
        with urlopen(f"{self.base_url}/health") as response:
            body = json.loads(response.read())
        self.assertEqual(body["status"], "online")
        self.assertEqual(body["warning_configuration"], "not_configured")
        self.assertEqual(body["warning_configuration_status"], "not_ready")
        self.assertEqual(body["warning_configuration_reasons"], [
            "threshold_missing", "freshness_window_missing"
        ])

    def test_health_endpoint_explains_invalid_configuration(self):
        self.server.backend_config = BackendConfig(
            warning_threshold_db_spl=None,
            max_input_age_seconds=30,
            warning_threshold_status="invalid",
            freshness_window_status="configured",
        )
        with urlopen(f"{self.base_url}/health") as response:
            body = json.loads(response.read())
        self.assertEqual(body["status"], "online")
        self.assertEqual(body["warning_configuration_status"], "not_ready")
        self.assertEqual(body["warning_configuration_reasons"], ["threshold_invalid"])

    def test_event_endpoint_saves_processed_event_and_keeps_success_response(self):
        with self.post_event(event_payload()) as response:
            body = json.loads(response.read())
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(body["schema_version"], "1.0")
        self.assertEqual(body["event_id"], "event-test")
        self.assertTrue(body["classification"]["confident"])
        self.assertTrue(body["sound_level"]["calibrated"])
        self.assertEqual(self.repository.events, [body])

    def test_null_classification_label_cannot_be_confident(self):
        payload = event_payload()
        payload["classification"]["label"] = None
        with self.post_event(payload) as response:
            body = json.loads(response.read())
        self.assertIsNone(body["classification"]["label"])
        self.assertFalse(body["classification"]["confident"])
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(self.repository.events, [body])

    def test_null_sound_measurement_cannot_be_calibrated(self):
        payload = event_payload()
        payload["sound_level"]["value"] = None
        with self.post_event(payload) as response:
            body = json.loads(response.read())
        self.assertIsNone(body["sound_level"]["value"])
        self.assertFalse(body["sound_level"]["calibrated"])
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(self.repository.events, [body])

    def test_missing_measurements_are_saved_with_processed_status_and_reason(self):
        self.server.backend_config = BackendConfig(max_input_age_seconds=10_000_000)
        payload = event_payload()
        payload["sound_level"] = None
        with self.post_event(payload) as response:
            body = json.loads(response.read())
        self.assertEqual(self.repository.events, [body])
        self.assertEqual(body["sound_level"]["status"], "unavailable")
        self.assertEqual(body["warning"]["reason"], "sound_level_unavailable")

    def test_stale_measurements_are_saved_with_processed_status(self):
        self.server.backend_config = BackendConfig(max_input_age_seconds=30)
        with self.post_event(event_payload()) as response:
            body = json.loads(response.read())
        self.assertEqual(self.repository.events, [body])
        self.assertEqual(body["classification"]["status"], "stale")
        self.assertEqual(body["sound_level"]["status"], "stale")
        self.assertEqual(body["warning"]["reason"], "measurement_stale")

    def test_duplicate_event_returns_provisional_conflict_and_no_success(self):
        self.repository.error = DuplicateEventError("duplicate")
        with self.assertRaises(HTTPError) as caught:
            self.post_event(event_payload())
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 409)
        self.assertEqual(body, {
            "schema_version": "1.0", "error": {"code": "duplicate_event"}
        })

    def test_database_failure_returns_provisional_unavailable_and_no_success(self):
        self.repository.error = EventStorageError("database unavailable")
        with self.assertRaises(HTTPError) as caught:
            self.post_event(event_payload())
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(body, {
            "schema_version": "1.0", "error": {"code": "storage_unavailable"}
        })

    def test_unexpected_repository_error_returns_safe_storage_response(self):
        self.repository.error = RuntimeError("private path or connection detail")
        with self.assertRaises(HTTPError) as caught:
            self.post_event(event_payload())
        body = caught.exception.read().decode("utf-8")
        self.assertEqual(caught.exception.code, 503)
        self.assertIn('"code":"storage_unavailable"', body)
        self.assertNotIn("private path", body)
        self.assertNotIn("connection detail", body)
        self.assertEqual(self.repository.events, [])

    def test_event_content_length_must_be_single_nonnegative_integer(self):
        invalid_headers = (
            [("Content-Type", "application/json")],
            [("Content-Type", "application/json"), ("Content-Length", "bad")],
            [("Content-Type", "application/json"), ("Content-Length", "-1")],
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Content-Length", "3"),
            ],
        )
        for headers in invalid_headers:
            with self.subTest(headers=headers):
                status, response_body = raw_post(
                    self.base_url, "/api/v1/events", headers
                )
                body = json.loads(response_body)
                self.assertEqual(status, 400)
                self.assertEqual(body["error"]["code"], "invalid_event")
        self.assertEqual(self.repository.events, [])

    def test_event_rejects_oversized_body_before_reading_it(self):
        status, response_body = raw_post(
            self.base_url,
            "/api/v1/events",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(1024 * 1024 + 1)),
            ],
        )
        body = json.loads(response_body)
        self.assertEqual(status, 413)
        self.assertEqual(body["error"]["code"], "event_too_large")
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(self.repository.events, [])

    def test_truncated_event_body_is_rejected(self):
        status, response_body = raw_post(
            self.base_url,
            "/api/v1/events",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "5"),
            ],
            body=b"{}",
            shutdown_write=True,
        )
        body = json.loads(response_body)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "invalid_event")
        self.assertEqual(self.repository.events, [])

    def test_malformed_json_returns_structured_client_error(self):
        request = Request(
            f"{self.base_url}/api/v1/events",
            data=b"{bad json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 400)
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(body["error"]["code"], "invalid_event")
        self.assertEqual(self.repository.events, [])

    def test_malformed_measurement_returns_client_error_and_no_warning(self):
        payload = event_payload()
        payload["sound_level"]["observed_at"] = "not-a-timestamp"
        request = Request(
            f"{self.base_url}/api/v1/events",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 400)
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(body["error"]["code"], "invalid_event")
        self.assertEqual(self.repository.events, [])

    def test_event_endpoint_rejects_non_json_content_type(self):
        request = Request(
            f"{self.base_url}/api/v1/events",
            data=b"{}",
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 415)
        self.assertEqual(body["error"]["code"], "unsupported_media_type")
        self.assertFalse(body["warning"]["triggered"])

    def test_unsupported_content_type_does_not_wait_for_declared_body(self):
        rejected_requests = (
            ("/api/v1/events", "text/plain"),
            ("/api/v1/classify", "application/octet-stream"),
        )
        for path, content_type in rejected_requests:
            with self.subTest(path=path):
                status, response_body = raw_post(
                    self.base_url,
                    path,
                    [
                        ("Content-Type", content_type),
                        ("Content-Length", "5"),
                    ],
                )
                self.assertEqual(status, 415)
                self.assertEqual(
                    json.loads(response_body)["error"]["code"],
                    "unsupported_media_type",
                )

        with urlopen(f"{self.base_url}/health", timeout=3) as health:
            self.assertEqual(health.status, 200)

    def test_local_dashboard_origin_can_read_health(self):
        request = Request(f"{self.base_url}/health", headers={"Origin": "http://127.0.0.1:8001"})
        with urlopen(request) as response:
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:8001")

    def test_event_preflight_allows_loopback_dashboard_and_json(self):
        request = Request(
            f"{self.base_url}/api/v1/events",
            headers={
                "Origin": "http://localhost:8001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            method="OPTIONS",
        )
        with urlopen(request) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:8001")
            self.assertEqual(response.headers.get("Access-Control-Allow-Methods"), "POST, OPTIONS")
            self.assertIsNone(response.headers.get("Content-Length"))

    def test_remote_origin_is_not_granted_browser_access(self):
        request = Request(f"{self.base_url}/health", headers={"Origin": "https://example.com"})
        with urlopen(request) as response:
            self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))


class AudioClassificationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = ConfiguredHTTPServer(("127.0.0.1", 0), BackendConfig())
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request_audio(self, body, *, content_type="audio/wav"):
        request = Request(
            f"{self.base_url}/api/v1/classify",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        return urlopen(request)

    def test_valid_audio_returns_test_classifier_prediction_without_warning_evaluation(self):
        class ControlledTestModel:
            def classify_wav_bytes(self, payload):
                self.received_length = len(payload)
                return {
                    "label": "Student Conversation",
                    "model_confidence": {
                        "value": 0.81,
                        "method": "predict_proba",
                        "calibrated": False,
                    },
                    "artifact_reference": "test-only",
                    "training_mode": "experimental_full_fit_no_held_out_evaluation",
                }

        self.server.audio_model = ControlledTestModel()
        with self.request_audio(audio_fixture_bytes()) as response:
            body = json.loads(response.read())
        self.assertEqual(body["inference"]["source"], "experimental_model")
        self.assertEqual(body["inference"]["evaluation_status"], "not_evaluated")
        self.assertEqual(body["classification"]["label"], "Student Conversation")
        self.assertEqual(body["classification"]["model_confidence"]["value"], 0.81)
        self.assertEqual(body["warning_evaluation"]["status"], "not_performed")
        self.assertEqual(body["connection_status"]["hardware"], "not_tested")

    def test_missing_model_returns_clear_service_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(HTTPError) as caught:
                self.request_audio(audio_fixture_bytes())
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(body["error"]["code"], "model_unavailable")
        self.assertEqual(body["warning_evaluation"]["status"], "not_performed")

    def test_malformed_audio_is_rejected_before_missing_model_response(self):
        with self.assertRaises(HTTPError) as caught:
            self.request_audio(b"not a wav")
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(body["error"]["code"], "invalid_audio")

    def test_wrong_audio_content_type_is_rejected(self):
        with self.assertRaises(HTTPError) as caught:
            self.request_audio(audio_fixture_bytes(), content_type="application/octet-stream")
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 415)
        self.assertEqual(body["error"]["code"], "unsupported_media_type")

    def test_audio_content_length_must_be_single_nonnegative_integer(self):
        invalid_headers = (
            [("Content-Type", "audio/wav")],
            [("Content-Type", "audio/wav"), ("Content-Length", "bad")],
            [("Content-Type", "audio/wav"), ("Content-Length", "-1")],
            [
                ("Content-Type", "audio/wav"),
                ("Content-Length", "1"),
                ("Content-Length", "2"),
            ],
        )
        for headers in invalid_headers:
            with self.subTest(headers=headers):
                status, response_body = raw_post(
                    self.base_url, "/api/v1/classify", headers
                )
                body = json.loads(response_body)
                self.assertEqual(status, 400)
                self.assertEqual(body["error"]["code"], "invalid_audio")

    def test_oversized_wav_is_rejected_before_reading_it(self):
        status, response_body = raw_post(
            self.base_url,
            "/api/v1/classify",
            [
                ("Content-Type", "audio/wav"),
                ("Content-Length", str(32 * 1024 * 1024 + 1)),
            ],
        )
        body = json.loads(response_body)
        self.assertEqual(status, 413)
        self.assertEqual(body["error"]["code"], "audio_sample_too_large")

    def test_full_oversized_wav_upload_result_and_server_responsiveness(self):
        recording = (
            Path(__file__).resolve().parents[2]
            / "ml/data/expanded_local_demo_20261020/audio/recordings/"
              "11_504669__bpayri__group-of-students-talking-loud-in-classroom-valencian-and-spanish.wav"
        )
        payload = recording.read_bytes()
        self.assertGreater(len(payload), 32 * 1024 * 1024)
        request = Request(
            f"{self.base_url}/api/v1/classify",
            data=payload,
            headers={"Content-Type": "audio/wav"},
            method="POST",
        )
        status = None
        response_body = b""
        client_error = None
        try:
            with urlopen(request, timeout=15) as response:
                status = response.status
                response_body = response.read()
        except HTTPError as error:
            status = error.code
            response_body = error.read()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError) as error:
            client_error = error

        if status is not None:
            self.assertEqual(status, 413)
            self.assertEqual(
                json.loads(response_body)["error"]["code"],
                "audio_sample_too_large",
            )
        else:
            self.assertIsInstance(
                client_error,
                (ConnectionAbortedError, ConnectionResetError, BrokenPipeError),
            )

        with urlopen(f"{self.base_url}/health", timeout=3) as health:
            self.assertEqual(health.status, 200)

    def test_incomplete_wav_body_is_rejected(self):
        status, response_body = raw_post(
            self.base_url,
            "/api/v1/classify",
            [
                ("Content-Type", "audio/wav"),
                ("Content-Length", "8"),
            ],
            body=b"RIFF",
            shutdown_write=True,
        )
        body = json.loads(response_body)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "invalid_audio")

    def test_unexpected_inference_error_does_not_expose_internal_details(self):
        class BrokenModel:
            def classify_wav_bytes(self, payload):
                raise RuntimeError("C:\\private\\model-directory")

        self.server.audio_model = BrokenModel()
        with self.assertRaises(HTTPError) as caught:
            self.request_audio(audio_fixture_bytes())
        body = json.loads(caught.exception.read())
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(
            body["error"],
            {
                "code": "inference_unavailable",
                "message": "audio inference failed",
            },
        )
        self.assertNotIn("private", json.dumps(body))


if __name__ == "__main__":
    unittest.main()
