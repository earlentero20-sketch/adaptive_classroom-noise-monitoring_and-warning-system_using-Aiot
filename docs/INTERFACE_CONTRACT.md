# Provisional Component Interface Contract

**Contract version:** `1.0` (proposed; not yet approved by all component owners)

This contract is a software starting point for Jann (firmware), Earl (ML),
Romeo (backend), and Audey (dashboard). It does not assert that the current
hardware can produce calibrated sound levels or that an ML model is available.

## Event request

`POST /api/v1/events` with `Content-Type: application/json`:

```json
{
  "schema_version": "1.0",
  "event_id": "event-unique-id",
  "device_id": "device-unique-id",
  "sensor_status": "unknown",
  "classification": {
    "label": null,
    "confident": false,
    "observed_at": null
  },
  "sound_level": {
    "value": null,
    "unit": null,
    "calibrated": false,
    "observed_at": null
  }
}
```

The example deliberately has no sound reading; it is not a real sensor event.

| Field | Type and meaning |
|---|---|
| `schema_version` | Required string. This contract accepts `1.0`. |
| `event_id`, `device_id` | Required non-empty strings; no student identity belongs here. |
| `sensor_status` | Optional `online`, `offline`, or `unknown`; device-reported status, not proof of physical health. |
| `classification.label` | Optional/null or exactly `Teacher Discussion` / `Student Conversation`. No third class. |
| `classification.confident` | Boolean gate from the ML adapter. Its confidence rule is not set by this contract; false or missing suppresses warnings. No numeric confidence is fabricated. |
| `classification.observed_at` | ISO-8601 timestamp with timezone for that result; missing/null prevents a warning. |
| `sound_level.value` | Finite number or null, measured independently from classification. |
| `sound_level.unit` | `dB_SPL` only when the source can support that unit; otherwise null. |
| `sound_level.calibrated` | Boolean hardware/calibration assertion; false or missing suppresses warnings. |
| `sound_level.observed_at` | ISO-8601 timestamp with timezone for the measurement; missing/null prevents a warning. |

## Backend response

`GET /health` reports process reachability separately from warning readiness:

```json
{
  "schema_version": "1.0",
  "service": "soniq-backend",
  "status": "online",
  "warning_configuration": "not_configured",
  "warning_configuration_status": "not_ready",
  "warning_configuration_reasons": ["threshold_missing", "freshness_window_missing"]
}
```

`status: "online"` means only that the backend process answered. It does not
mean warning logic is ready or that hardware is connected. The legacy
`warning_configuration` field remains `configured` / `not_configured`;
`warning_configuration_status` is `ready` / `not_ready`, and the reasons list
contains `threshold_missing`, `threshold_invalid`, `freshness_window_missing`,
or `freshness_window_invalid` as applicable. Invalid health responses must
not be treated as ready.

The backend returns JSON with the same `schema_version`, event/device IDs,
`received_at`, and separate `classification`, `sound_level`,
`connection_status`, and `warning` objects. Each measurement object has a
`status` such as `fresh`, `stale`, `unavailable`, `unknown`, or `invalid_time`.
`connection_status.backend` reports this process as `online`; `sensor` reflects
the event's reported status or `unknown`. `warning.triggered` is a Boolean and
`warning.reason` explains the fail-closed result.

Because the example provides no model result or sound reading, it returns this
warning object:

```json
{
  "triggered": false,
  "reason": "classification_unavailable"
}
```

No threshold value is returned to the dashboard. A warning can be requested
only when the class is a confident `Student Conversation`, the sound reading
is fresh, calibrated, and in `dB_SPL`, and the backend has an explicitly
configured threshold that the reading strictly exceeds. `Teacher Discussion`
never triggers this buzzer rule.

## Freshness and configuration

The backend has no default sound threshold and no default input freshness
window. Configure them explicitly using `WARNING_THRESHOLD_DB_SPL` and
`MAX_INPUT_AGE_SECONDS`. Both must be finite, positive numbers. Missing,
malformed, non-finite, zero, or negative values are reported as missing or
invalid, and warning decisions remain off. `/health` still reports the
reachable backend process as online while separately reporting that warning
configuration is not ready.
The max-age setting is an operational freshness choice, not a calibrated sound
threshold. Readings with missing timestamps, stale timestamps, future times,
unknown units, invalid numbers, or uncalibrated status cannot trigger a
warning. Invalid request shapes receive a structured HTTP 400 response;
requests without the `application/json` media type receive HTTP 415.

## Provisional local audio inference adapter

The separate `POST /api/v1/classify` route is a local development adapter for
one complete WAV sample. It is loopback-client-only, accepts
`Content-Type: audio/wav`, and currently validates uncompressed PCM WAV. The request body is
the WAV bytes; there is no JSON wrapper, streaming behavior, sensor reading,
or device identity. The request body limit is 32 MiB. The sample's source
sample rate and channel count are read from its header; inference applies the
preprocessing settings saved in the model artifact. This route describes the
current host-side software only. It is not an ESP32 transport or audio-format
decision and must not be treated as one.

Successful response example (the probability is present only when the loaded
classifier supports it):

```json
{
  "schema_version": "1.0",
  "inference": {
    "status": "complete",
    "source": "experimental_model",
    "evaluation_status": "not_evaluated"
  },
  "classification": {
    "label": "Student Conversation",
    "model_confidence": null,
    "artifact_reference": "<actual artifact reference>",
    "observed_at": "2026-10-15T00:00:00Z"
  },
  "warning_evaluation": {"status": "not_performed"},
  "connection_status": {"backend": "online", "hardware": "not_tested"}
}
```

The label and placeholder above illustrate response shape only; they are not
SONIQ model results. `model_confidence` is the predicted class probability from
`predict_proba`, not calibrated confidence. It does not set the existing
`classification.confident` field and cannot trigger a warning. This endpoint
does not evaluate sound level or warning policy. A missing model returns HTTP
503 with `error.code=model_unavailable`; malformed WAV bytes return HTTP 400,
and unsupported media types return HTTP 415. The adapter loads a model only
from the locally configured `SONIQ_AUDIO_MODEL_PATH` or an injected in-process
model. Only project-owned, trusted model artifacts may be loaded because
joblib/pickle artifacts can execute code during loading.

`inference.source` distinguishes `trained_model` from `experimental_model`;
`evaluation_status` is `held_out_evaluated` for the normal baseline or
`not_evaluated` for the explicitly experimental full-fit artifact.

`ml.audio_inference` accepts complete WAV bytes and a model runtime without
knowing about HTTP, the ESP32, sensors, or buzzer policy. Firmware transport,
microphone format, and the path for a calibrated sound-level reading remain
open team decisions. Do not connect this classifier response to a warning
until confidence handling and the independent calibrated measurement source
are approved.

The server binds to `127.0.0.1:8000` by default for local development. This is
not a secured network deployment and does not connect to firmware or the
dashboard automatically. Team review is required before treating this
contract, the freshness setting, confidence rule, or warning threshold as
final.

For the local dashboard adapter, serve `dashboard/` on a loopback HTTP origin
(for example, `http://127.0.0.1:8001`). The backend grants browser CORS access
only to `localhost`, `127.0.0.1`, or `::1` origins; the event endpoint accepts
the JSON `POST` preflight from those origins. Opening the HTML as a `file:` URL
is not supported for API access. This local-development allowance does not
make the server suitable for network deployment.

## Local development

From the repository root, start the backend in one terminal:

```powershell
python -m backend.app
```

Serve the dashboard from a second terminal:

```powershell
python -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8001/`. The dashboard's existing SAMPLE DATA values
remain simulated. The integration panel's health status is an actual response
from the local backend; its empty contract request contains no audio or sensor
readings, and its response does not prove that hardware is present. Interpret
backend reachability, warning-configuration readiness, and device-reported
sensor status as three separate things. In this provisional phase, hardware
status remains unknown unless an event explicitly reports a sensor state, and
even a reported state is not physical verification.
