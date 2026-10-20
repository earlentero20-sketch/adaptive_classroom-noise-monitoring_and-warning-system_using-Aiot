import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { checkBackend, classifyAudioFile, describeAudioInference, describeEvent, describeHealth, evaluateDemoWarning, sendEmptyContractSample } from "./backend-adapter.mjs";

const emptyResponse = {
	schema_version: "1.0",
	event_id: "test-event",
	device_id: "test-device",
	received_at: "2026-10-11T04:00:00Z",
	connection_status: { backend: "online", sensor: "unknown" },
	classification: { label: null, confident: false, status: "unavailable", observed_at: null },
	sound_level: { value: null, unit: null, calibrated: false, status: "unavailable", observed_at: null },
	warning: { triggered: false, reason: "classification_unavailable" },
};

const inferenceResponse = {
	schema_version: "1.0",
	inference: { status: "complete", source: "experimental_model", evaluation_status: "not_evaluated" },
	classification: {
		label: "Student Conversation",
		model_confidence: { value: 0.73, method: "predict_proba", calibrated: false },
		artifact_reference: "local-experimental-artifact",
		observed_at: "2026-10-11T04:00:00Z",
	},
	warning_evaluation: { status: "not_performed" },
	connection_status: { backend: "online", hardware: "not_tested" },
};

function localWav(name = "sample.wav") {
	return Object.assign(new Blob(["controlled WAV request fixture"]), { name });
}

test("dashboard loads the current cache-busted backend adapter and its styles", async () => {
	const html = await readFile(new URL("./index.html", import.meta.url), "utf8");
	assert.match(html, /<script type="module" src="backend-adapter\.mjs\?v=audio-inference"><\/script>/);
	assert.match(html, /<link rel="stylesheet" href="backend-adapter\.css">/);
	const adapter = await readFile(new URL("./backend-adapter.mjs", import.meta.url), "utf8");
	assert.match(adapter, /data-demo-threshold type="number" min="0" step="any" value="75"/);
});

test("health response distinguishes reachable service from unready warning settings", () => {
	const health = describeHealth({
		schema_version: "1.0",
		service: "soniq-backend",
		status: "online",
		warning_configuration: "not_configured",
		warning_configuration_status: "not_ready",
		warning_configuration_reasons: ["threshold_missing", "freshness_window_missing"],
	});
	assert.equal(health.ok, true);
	assert.equal(health.warningReady, false);
	assert.match(health.message, /Backend reachable/);
	assert.match(health.configurationMessage, /NOT READY/);
	assert.match(health.configurationMessage, /threshold is missing/);
	const invalid = describeHealth({
		schema_version: "1.0",
		service: "soniq-backend",
		status: "online",
		warning_configuration: "not_configured",
		warning_configuration_status: "not_ready",
		warning_configuration_reasons: ["threshold_invalid", "freshness_window_invalid"],
	});
	assert.equal(invalid.warningReady, false);
	assert.match(invalid.configurationMessage, /threshold is invalid/);
	assert.equal(describeHealth({ status: "online" }).ok, false);
});

test("empty contract response clearly reports missing sensor data and no warning", () => {
	const view = describeEvent(emptyResponse);
	assert.equal(view.ok, true);
	assert.equal(view.sensor, "unknown (no hardware data)");
	assert.equal(view.classification, "Unavailable (no model data)");
	assert.equal(view.soundLevel, "Unavailable (no microphone data)");
	assert.equal(view.warning, "Not triggered");
});

test("event adapter rejects malformed backend responses and qualifies reported hardware state", () => {
	assert.equal(describeEvent({ ...emptyResponse, sound_level: { value: "75", unit: "dB_SPL" } }).ok, false);
	assert.equal(describeEvent({ ...emptyResponse, received_at: "not-a-zoned-time" }).ok, false);
	const reported = describeEvent({
		...emptyResponse,
		connection_status: { backend: "online", sensor: "online" },
	});
	assert.match(reported.sensor, /not physically verified/);
});

test("event view handles warning and non-warning responses from the contract", () => {
	const warningResponse = {
		...emptyResponse,
		classification: { label: "Student Conversation", confident: true, status: "fresh", observed_at: "2026-10-11T04:00:00Z" },
		sound_level: { value: 75, unit: "dB_SPL", calibrated: true, status: "fresh", observed_at: "2026-10-11T04:00:00Z" },
		warning: { triggered: true, reason: "sound_level_above_threshold" },
	};
	assert.equal(describeEvent(warningResponse).warning, "Triggered");
	assert.equal(describeEvent({ ...warningResponse, warning: { triggered: false, reason: "teacher_discussion" } }).warning, "Not triggered");
	assert.equal(describeEvent({ schema_version: "1.0" }).ok, false);
});

test("health adapter reports backend unavailability", async () => {
	const result = await checkBackend(async () => { throw new Error("connection refused"); });
	assert.equal(result.ok, false);
	assert.match(result.message, /Backend unavailable/);
});

test("health adapter marks malformed payload as reachable but not ready", async () => {
	const result = await checkBackend(async () => ({ ok: true, json: async () => ({ status: "online" }) }));
	assert.equal(result.ok, false);
	assert.equal(result.reachable, true);
	assert.match(result.message, /response is invalid/);
});

test("sample request is explicitly empty and consumes backend response", async () => {
	let sent;
	const result = await sendEmptyContractSample(async (_url, options) => {
		sent = JSON.parse(options.body);
		return { ok: true, json: async () => emptyResponse };
	}, "http://127.0.0.1:8000", "test-check");
	assert.equal(sent.event_id, "test-check");
	assert.equal(sent.sensor_status, "unknown");
	assert.equal(sent.classification.label, null);
	assert.equal(sent.sound_level.value, null);
	assert.equal(result.warning, "Not triggered");
});

test("demo policy triggers only for simulated student conversation above a fresh calibrated threshold", () => {
	const result = evaluateDemoWarning({
		classification: "Student Conversation",
		soundLevel: "76",
		threshold: "75",
		measurementState: "fresh_calibrated",
	});
	assert.deepEqual(result, { triggered: true, reason: "student_conversation_above_threshold", simulated: true });
	assert.equal(evaluateDemoWarning({
		classification: "Teacher Discussion",
		soundLevel: "99",
		threshold: "75",
		measurementState: "fresh_calibrated",
	}).triggered, false);
});

test("demo policy uses a strict threshold comparison and refuses invalid threshold settings", () => {
	for (const [soundLevel, threshold, reason] of [
		["75", "75", "below_threshold"],
		["74", "75", "below_threshold"],
		["76", "", "threshold_unconfigured"],
		["76", "0", "threshold_invalid"],
		["not-a-number", "75", "sound_level_invalid"],
		["", "75", "sound_level_unavailable"],
	]) {
		const result = evaluateDemoWarning({
			classification: "Student Conversation",
			soundLevel,
			threshold,
			measurementState: "fresh_calibrated",
		});
		assert.equal(result.triggered, false);
		assert.equal(result.reason, reason);
		assert.equal(result.simulated, true);
	}
});

test("demo policy never warns for stale, unavailable, invalid, or uncalibrated readings", () => {
	for (const [measurementState, reason] of [
		["stale", "measurement_stale"],
		["unavailable", "sound_level_unavailable"],
		["invalid", "sound_level_invalid"],
		["uncalibrated", "sound_level_uncalibrated"],
	]) {
		const result = evaluateDemoWarning({
			classification: "Student Conversation",
			soundLevel: "99",
			threshold: "70",
			measurementState,
		});
		assert.equal(result.triggered, false);
		assert.equal(result.reason, reason);
	}
	assert.equal(evaluateDemoWarning({
		classification: null,
		soundLevel: "99",
		threshold: "75",
		measurementState: "fresh_calibrated",
	}).triggered, false);
});

test("audio inference adapter accepts only a genuine two-class model response with uncalibrated probability", () => {
	assert.deepEqual(describeAudioInference(inferenceResponse), {
		ok: true,
		state: "actual-inference",
		classification: "Student Conversation",
		classProbability: 0.73,
		source: "experimental_model",
		evaluationStatus: "not_evaluated",
		observedAt: "2026-10-11T04:00:00Z",
	});
	assert.equal(describeAudioInference({
		...inferenceResponse,
		inference: { status: "complete", source: "trained_model", evaluation_status: "not_evaluated" },
	}).ok, false);
	assert.equal(describeAudioInference({
		...inferenceResponse,
		classification: { ...inferenceResponse.classification, label: "Excessive Noise" },
	}).ok, false);
	assert.equal(describeAudioInference({
		...inferenceResponse,
		classification: { ...inferenceResponse.classification, model_confidence: { value: 1.1, method: "predict_proba", calibrated: false } },
	}).ok, false);
	assert.equal(describeAudioInference({
		...inferenceResponse,
		classification: { ...inferenceResponse.classification, model_confidence: { value: 0.73, method: "predict_proba", calibrated: true } },
	}).ok, false);
	const noProbability = describeAudioInference({
		...inferenceResponse,
		classification: { ...inferenceResponse.classification, label: "Teacher Discussion", model_confidence: null },
	});
	assert.equal(noProbability.ok, true);
	assert.equal(noProbability.classification, "Teacher Discussion");
	assert.equal(noProbability.classProbability, null);
	assert.equal(describeAudioInference({
		...inferenceResponse,
		warning_evaluation: { status: "performed" },
	}).ok, false);
});

test("WAV upload posts the selected file as audio/wav and displays the actual backend result", async () => {
	let request;
	const file = localWav();
	const result = await classifyAudioFile(file, async (url, options) => {
		request = { url, options };
		return { ok: true, json: async () => inferenceResponse };
	}, "http://127.0.0.1:8000");
	assert.equal(request.url, "http://127.0.0.1:8000/api/v1/classify");
	assert.equal(request.options.method, "POST");
	assert.equal(request.options.headers["Content-Type"], "audio/wav");
	assert.equal(request.options.body, file);
	assert.equal(result.classification, "Student Conversation");
	assert.equal(result.classProbability, 0.73);
});

test("WAV upload rejects non-WAV input before sending and reports missing model without fallback", async () => {
	let requests = 0;
	const rejectFetch = async () => { requests += 1; throw new Error("must not be called"); };
	assert.equal((await classifyAudioFile(localWav("clip.mp3"), rejectFetch)).code, "invalid_audio");
	assert.equal((await classifyAudioFile(null, rejectFetch)).state, "invalid-audio");
	assert.equal(requests, 0);
	const unavailable = await classifyAudioFile(localWav(), async () => ({
		ok: false,
		status: 503,
		json: async () => ({ error: { code: "model_unavailable" } }),
	}));
	assert.equal(unavailable.state, "model-unavailable");
	assert.match(unavailable.message, /DEMO MODE was not started/);
});

test("WAV upload reports invalid audio, malformed responses, and network errors without predictions", async () => {
	const invalid = await classifyAudioFile(localWav(), async () => ({
		ok: false,
		status: 400,
		json: async () => ({ error: { code: "invalid_audio" } }),
	}));
	assert.equal(invalid.state, "invalid-audio");
	const malformed = await classifyAudioFile(localWav(), async () => ({ ok: true, json: async () => ({}) }));
	assert.equal(malformed.state, "invalid-response");
	assert.equal(Object.hasOwn(malformed, "classification"), false);
	const offline = await classifyAudioFile(localWav(), async () => { throw new Error("connection refused"); });
	assert.equal(offline.state, "backend-unavailable");
	assert.match(offline.message, /DEMO MODE was not started/);
});
