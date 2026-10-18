from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import wave

from backend.app import BackendConfig, ConfiguredHTTPServer, process_event


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


class HTTPHandlerTests(unittest.TestCase):
    def setUp(self):
        self.server = ConfiguredHTTPServer(
            ("127.0.0.1", 0), BackendConfig(warning_threshold_db_spl=None)
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

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

    def test_event_endpoint_returns_structured_safe_response(self):
        payload = event_payload()
        request = Request(
            f"{self.base_url}/api/v1/events",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            body = json.loads(response.read())
        self.assertFalse(body["warning"]["triggered"])
        self.assertEqual(body["schema_version"], "1.0")

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


if __name__ == "__main__":
    unittest.main()
