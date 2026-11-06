import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
	checkBackend,
	classifyAudioFile,
	DEFAULT_BACKEND_URL,
	describeAudioInference,
	describeHealth,
	fetchEvents,
	isStale,
	normalizeEventRecord,
	resolveBackendUrl,
	serializeEventReportCsv,
	summarizeEvents,
} from "./backend-adapter.mjs";

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

const warningEvent = {
	...emptyResponse,
	event_id: "event-warning",
	received_at: "2026-10-11T04:05:00Z",
	classification: {
		label: "Student Conversation",
		confident: true,
		status: "fresh",
		observed_at: "2026-10-11T04:05:00Z",
	},
	sound_level: {
		value: 76,
		unit: "dB_SPL",
		calibrated: true,
		status: "fresh",
		observed_at: "2026-10-11T04:05:00Z",
	},
	warning: { triggered: true, reason: "sound_level_above_threshold" },
};

const teacherEvent = {
	...warningEvent,
	event_id: "event-teacher",
	received_at: "2026-10-11T04:03:00Z",
	classification: {
		label: "Teacher Discussion",
		confident: true,
		status: "fresh",
		observed_at: "2026-10-11T04:03:00Z",
	},
	warning: { triggered: false, reason: "teacher_discussion" },
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

test("dashboard loads the backend-driven UI and contains no sample or warning-simulation controls", async () => {
	const html = await readFile(new URL("./index.html", import.meta.url), "utf8");
	assert.match(html, /<script type="module" src="dashboard\.mjs"><\/script>/);
	assert.match(html, /<link rel="stylesheet" href="backend-adapter\.css">/);
	assert.match(html, /<link rel="stylesheet" href="dashboard\.css">/);
	assert.match(html, /id="data-source-badge">BACKEND DATA ONLY</);
	assert.match(html, /id="connection-banner" data-state="idle" role="status" aria-live="polite"/);
	assert.match(html, /id="integration-events"/);
	assert.match(html, /GET \/api\/v1\/events\?limit=10&amp;offset=0/);
	assert.doesNotMatch(html, /Send empty sample|Warning policy simulation|data-demo-/);
	assert.doesNotMatch(html, /Math\.random/);
	assert.doesNotMatch(html, /data-level="46"/);
	const adapter = await readFile(new URL("./backend-adapter.mjs", import.meta.url), "utf8");
	assert.doesNotMatch(adapter, /evaluateDemoWarning|sendEmptyContractSample/);
	assert.match(adapter, /"Teacher Discussion", "Student Conversation"/);
});

test("dashboard delegates behavior to modules and contains no fabricated refresh loop", async () => {
	const html = await readFile(new URL("./index.html", import.meta.url), "utf8");
	const script = await readFile(new URL("./dashboard.mjs", import.meta.url), "utf8");
	assert.doesNotMatch(html, /<script>[\s\S]*?setInterval/);
	assert.doesNotMatch(html, /Math\.random/);
	assert.doesNotMatch(html, /campus-db/);
	assert.doesNotMatch(html, /historyByRange/);
	assert.match(script, /document\.querySelectorAll\("\.nav-link"\)/);
	assert.match(script, /setInterval\(\(\) => loadDashboard\(\{ quiet: true \}\), REFRESH_INTERVAL_MS\)/);
	assert.match(script, /loadDashboard\(\{ quiet: true \}\)/);
	assert.match(script, /clearInterval\(refreshTimer\)/);
	assert.match(script, /clearInterval\(freshnessTimer\)/);
	assert.match(script, /addEventListener\("pagehide"/);
	assert.match(script, /addEventListener\("visibilitychange"/);
	assert.match(script, /fetchEvents\(\{ fetchImpl: fetch, baseUrl: state\.baseUrl/);
	assert.match(script, /classifyAudioFile\(file, fetch, state\.baseUrl\)/);
});

test("Live and History tabs expose linked panels and automatic keyboard navigation", async () => {
	const html = await readFile(new URL("./index.html", import.meta.url), "utf8");
	const script = await readFile(new URL("./dashboard.mjs", import.meta.url), "utf8");
	const styles = await readFile(new URL("./colors.css", import.meta.url), "utf8");
	assert.match(html, /role="tablist" aria-label="Monitoring view"/);
	assert.match(html, /id="live-tab" type="button" role="tab" aria-selected="true" aria-controls="live-summary" tabindex="0" data-view="live"/);
	assert.match(html, /id="history-tab" type="button" role="tab" aria-selected="false" aria-controls="history-summary" tabindex="-1" data-view="history"/);
	assert.match(html, /id="live-summary" role="tabpanel" aria-labelledby="live-tab" tabindex="0"/);
	assert.match(html, /id="history-summary" role="tabpanel" aria-labelledby="history-tab" tabindex="0"[^>]*hidden/);
	const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
	assert.equal(ids.filter((id) => id === "live-tab").length, 1);
	assert.equal(ids.filter((id) => id === "history-tab").length, 1);
	assert.equal(ids.filter((id) => id === "live-summary").length, 1);
	assert.equal(ids.filter((id) => id === "history-summary").length, 1);
	assert.match(script, /button\.addEventListener\('click', \(\) => selectView\(button\)\)/);
	assert.match(script, /event\.key === 'ArrowRight'/);
	assert.match(script, /event\.key === 'ArrowLeft'/);
	assert.match(script, /event\.key === 'Home'/);
	assert.match(script, /event\.key === 'End'/);
	assert.match(script, /tab\.setAttribute\('aria-selected', active\)/);
	assert.match(script, /tab\.setAttribute\('tabindex', active \? '0' : '-1'\)/);
	assert.match(script, /document\.querySelector\('\.live-summary'\)\.hidden = history/);
	assert.match(script, /document\.querySelector\('\.history-summary'\)\.hidden = !history/);
	assert.match(styles, /button:focus-visible[^}]*outline: 3px solid/);
});

test("integration section documents only real endpoints and its responsive status layout", async () => {
	const html = await readFile(new URL("./index.html", import.meta.url), "utf8");
	const css = await readFile(new URL("./backend-adapter.css", import.meta.url), "utf8");
	assert.match(html, /id="integration" aria-labelledby="integration-title"/);
	assert.match(html, /id="integration-health"/);
	assert.match(html, /id="integration-events"/);
	assert.match(html, /id="integration-classification"/);
	assert.match(html, /refreshed every 30 seconds while this page is visible/);
	assert.match(html, /does not verify physical buzzer operation/);
	assert.match(css, /\.integration-list/);
	assert.match(css, /@media \(max-width: 560px\)/);
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

test("event adapter validates actual warning, sound, and reported sensor values", () => {
	assert.equal(normalizeEventRecord({ ...emptyResponse, sound_level: { value: "75", unit: "dB_SPL" } }), null);
	assert.equal(normalizeEventRecord({ ...emptyResponse, received_at: "not-a-zoned-time" }), null);
	const reported = normalizeEventRecord({
		...emptyResponse,
		connection_status: { backend: "online", sensor: "online" },
	});
	assert.equal(reported.sensorStatus, "online");
	assert.equal(reported.warningTriggered, false);
	assert.equal(reported.warningReason, "classification_unavailable");
});

test("health adapter reports backend unavailability", async () => {
	const result = await checkBackend(async () => { throw new Error("connection refused"); });
	assert.equal(result.ok, false);
	assert.match(result.message, /Backend unavailable/);
});

test("event history request times out and reports the timeout explicitly", async (t) => {
	t.mock.timers.enable({ apis: ["setTimeout"] });
	const pending = fetchEvents({
		fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => {
			signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
		}),
	});

	t.mock.timers.tick(15_000);
	const result = await pending;
	assert.equal(result.ok, false);
	assert.equal(result.code, "request_timeout");
	assert.match(result.message, /timed out after 15 seconds/);
});

test("health adapter marks malformed payload as reachable but not ready", async () => {
	const result = await checkBackend(async () => ({ ok: true, json: async () => ({ status: "online" }) }));
	assert.equal(result.ok, false);
	assert.equal(result.reachable, true);
	assert.match(result.message, /response is invalid/);
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
	assert.match(unavailable.message, /No prediction was produced/);
});

test("WAV classification timeout does not produce a prediction", async (t) => {
	t.mock.timers.enable({ apis: ["setTimeout"] });
	const pending = classifyAudioFile(localWav(), (_url, { signal }) => new Promise((_resolve, reject) => {
		signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
	}));

	t.mock.timers.tick(120_000);
	const result = await pending;
	assert.equal(result.ok, false);
	assert.equal(result.state, "request-timeout");
	assert.equal(result.code, "request_timeout");
	assert.match(result.message, /timed out after 120 seconds/);
	assert.match(result.message, /No prediction was produced/);
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
	assert.match(offline.message, /No prediction was produced/);
});

test("event history adapter uses GET, preserves pagination, and validates contract records", async () => {
	let request;
	const result = await fetchEvents({
		fetchImpl: async (url, options) => {
			request = { url, options };
			return {
				ok: true,
				json: async () => ({
					total: 2,
					events: [warningEvent, teacherEvent],
					pagination: { limit: 5, offset: 0, total: 2, has_more: false },
				}),
			};
		},
		baseUrl: "http://127.0.0.1:8000",
		limit: 5,
		offset: 0,
	});
	assert.equal(request.options.method, undefined);
	assert.match(request.url, /\/api\/v1\/events\?limit=5&offset=0$/);
	assert.equal(result.ok, true);
	assert.equal(result.state, "success");
	assert.equal(result.events.length, 2);
	assert.equal(result.events[0].classificationLabel, "Student Conversation");
	assert.equal(result.events[0].warningTriggered, true);
	assert.deepEqual(result.pagination, { limit: 5, offset: 0, total: 2, hasMore: false });
});

test("event history adapter accepts an actual empty page and preserves backend pagination", async () => {
	const result = await fetchEvents({
		fetchImpl: async (url) => {
			assert.match(url, /\/api\/v1\/events\?limit=3&offset=6$/);
			return {
				ok: true,
				json: async () => ({
					schema_version: "1.0",
					events: [],
					total: 8,
					pagination: { limit: 3, offset: 6, total: 8, has_more: false },
				}),
			};
		},
		baseUrl: "http://127.0.0.1:8000",
		limit: 3,
		offset: 6,
	});
	assert.equal(result.ok, true);
	assert.deepEqual(result.events, []);
	assert.deepEqual(result.pagination, { limit: 3, offset: 6, total: 8, hasMore: false });
});

test("event history adapter reports a missing backend route as unavailable, not empty", async () => {
	const result = await fetchEvents({
		fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({ error: { code: "not_found" } }) }),
		baseUrl: "http://127.0.0.1:8000",
	});
	assert.equal(result.ok, false);
	assert.equal(result.state, "unavailable");
	assert.match(result.message, /GET \/api\/v1\/events/);
});

test("event history adapter distinguishes network, malformed, and invalid-record failures", async () => {
	const offline = await fetchEvents({
		fetchImpl: async () => { throw new Error("connection refused"); },
		baseUrl: "http://127.0.0.1:8000",
	});
	assert.equal(offline.state, "error");
	assert.match(offline.message, /Backend unavailable/);

	const malformed = await fetchEvents({
		fetchImpl: async () => ({ ok: true, json: async () => ({ message: "ok" }) }),
		baseUrl: "http://127.0.0.1:8000",
	});
	assert.equal(malformed.state, "error");
	assert.match(malformed.message, /without an events array/);

	const invalid = await fetchEvents({
		fetchImpl: async () => ({ ok: true, json: async () => ({ events: [{ schema_version: "1.0" }] }) }),
		baseUrl: "http://127.0.0.1:8000",
	});
	assert.equal(invalid.state, "error");
	assert.match(invalid.message, /do not match the event contract/);

	const unavailableStorage = await fetchEvents({
		fetchImpl: async () => ({
			ok: false,
			status: 503,
			json: async () => ({ error: { code: "storage_unavailable" } }),
		}),
		baseUrl: "http://127.0.0.1:8000",
	});
	assert.equal(unavailableStorage.state, "error");
	assert.match(unavailableStorage.message, /HTTP 503/);
});

test("event history summary counts actual labels, warnings, readings, and latest event", () => {
	const summary = summarizeEvents([teacherEvent, warningEvent, emptyResponse].map(normalizeEventRecord));
	assert.equal(summary.total, 3);
	assert.equal(summary.warningsTriggered, 1);
	assert.equal(summary.teacherDiscussion, 1);
	assert.equal(summary.studentConversation, 1);
	assert.equal(summary.soundReadings, 2);
	assert.equal(summary.latestEvent.eventId, "event-warning");
});

test("event report CSV keeps the event contract and neutralizes formula-like fields", () => {
	const event = normalizeEventRecord({
		...warningEvent,
		event_id: "=1+1",
		device_id: '@SUM("x")',
		warning: { triggered: true, reason: "first line\r\nsecond,line" },
	});
	const csv = serializeEventReportCsv([event]);
	assert.match(csv, /^event_id,device_id,received_at,classification,/);
	assert.match(csv, /\r\n'=1\+1,"'@SUM\(""x""\)"/);
	assert.match(csv, /"first line\r\nsecond,line"$/);
	assert.throws(() => serializeEventReportCsv(null), /must be an array/);
});

test("stale and backend URL helpers fail closed", () => {
	assert.equal(isStale("2026-10-11T04:00:00Z", Date.parse("2026-10-11T04:01:30Z"), 60000), true);
	assert.equal(isStale("2026-10-11T04:00:00Z", Date.parse("2026-10-11T04:00:30Z"), 60000), false);
	assert.equal(isStale("not-a-time"), true);
	assert.equal(resolveBackendUrl(""), DEFAULT_BACKEND_URL);
	assert.equal(resolveBackendUrl("?api=http://127.0.0.1:9000"), "http://127.0.0.1:9000");
	assert.equal(resolveBackendUrl("?api=javascript:alert(1)"), DEFAULT_BACKEND_URL);
	assert.equal(resolveBackendUrl("?api=http://user:pass@127.0.0.1:8000"), DEFAULT_BACKEND_URL);

	const originalWindow = globalThis.window;
	const originalDocument = globalThis.document;
	globalThis.window = { SONIQ_API_BASE_URL: "   " };
	globalThis.document = {
		querySelector: () => ({ getAttribute: () => "http://127.0.0.1:9100" }),
	};
	try {
		assert.equal(resolveBackendUrl(""), "http://127.0.0.1:9100");
	} finally {
		if (originalWindow === undefined) delete globalThis.window;
		else globalThis.window = originalWindow;
		if (originalDocument === undefined) delete globalThis.document;
		else globalThis.document = originalDocument;
	}
});

test("event normalization preserves the two exact classification labels and rejects renamed classes", () => {
	assert.equal(normalizeEventRecord(warningEvent).classificationLabel, "Student Conversation");
	assert.equal(normalizeEventRecord(teacherEvent).classificationLabel, "Teacher Discussion");
	assert.equal(normalizeEventRecord({
		...warningEvent,
		classification: { ...warningEvent.classification, label: "Excessive Noise" },
	}), null);
	assert.equal(normalizeEventRecord({ ...warningEvent, warning: { triggered: "yes", reason: "x" } }), null);
});
