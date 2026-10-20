const BACKEND_URL = "http://127.0.0.1:8000";
const VALID_MEASUREMENT_STATUSES = ["fresh", "stale", "unavailable", "unknown", "invalid_time"];
const DEMO_CLASSES = ["Teacher Discussion", "Student Conversation"];

export function evaluateDemoWarning({ classification, soundLevel, threshold, measurementState }) {
	const result = (triggered, reason) => ({ triggered, reason, simulated: true });
	if (!DEMO_CLASSES.includes(classification)) return result(false, "classification_unavailable");
	if (classification === "Teacher Discussion") return result(false, "teacher_discussion");
	if (measurementState === "unavailable") return result(false, "sound_level_unavailable");
	if (measurementState === "stale") return result(false, "measurement_stale");
	if (measurementState === "invalid") return result(false, "sound_level_invalid");
	if (measurementState === "uncalibrated") return result(false, "sound_level_uncalibrated");
	if (measurementState !== "fresh_calibrated") return result(false, "measurement_status_invalid");

	if (soundLevel === null || soundLevel === undefined || (typeof soundLevel === "string" && !soundLevel.trim())) {
		return result(false, "sound_level_unavailable");
	}
	const level = parseDemoNumber(soundLevel);
	if (level === null) return result(false, "sound_level_invalid");
	if (threshold === null || threshold === undefined || (typeof threshold === "string" && !threshold.trim())) {
		return result(false, "threshold_unconfigured");
	}
	const limit = parseDemoNumber(threshold);
	if (limit === null || limit <= 0) return result(false, "threshold_invalid");
	if (level <= limit) return result(false, "below_threshold");
	return result(true, "student_conversation_above_threshold");
}

function parseDemoNumber(value) {
	if (typeof value === "number") return Number.isFinite(value) ? value : null;
	if (typeof value !== "string" || !value.trim()) return null;
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : null;
}

class BackendResponseError extends Error {
	constructor(message, body = null, status = null) {
		super(message);
		this.body = body;
		this.status = status;
	}
}

export function describeHealth(payload) {
	const reasons = payload?.warning_configuration_reasons;
	if (
		!payload ||
		payload.schema_version !== "1.0" ||
		payload.service !== "soniq-backend" ||
		payload.status !== "online" ||
		!["configured", "not_configured"].includes(payload.warning_configuration) ||
		!["ready", "not_ready"].includes(payload.warning_configuration_status) ||
		!Array.isArray(reasons) ||
		(reasons.length === 0) !== (payload.warning_configuration_status === "ready") ||
		(payload.warning_configuration === "configured") !== (payload.warning_configuration_status === "ready")
	) {
		return { ok: false, reachable: true, message: "Backend reachable, but its health response is invalid." };
	}
	const reasonLabels = {
		threshold_missing: "warning threshold is missing",
		threshold_invalid: "warning threshold is invalid",
		freshness_window_missing: "freshness window is missing",
		freshness_window_invalid: "freshness window is invalid",
	};
	const detail = reasons.map((reason) => reasonLabels[reason] || `unrecognized configuration reason (${reason})`);
	return {
		ok: true,
		reachable: true,
		warningReady: payload.warning_configuration_status === "ready",
		configurationMessage: payload.warning_configuration_status === "ready"
			? "Warning configuration: ready. Hardware connection is still unknown."
			: `Warning configuration: NOT READY (${detail.join("; ")}). Warnings remain disabled.`,
		message: "Backend reachable. Hardware connection has not been verified.",
	};
}

function validTimestamp(value) {
	return value === null || (
		typeof value === "string" &&
		/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
		Number.isFinite(Date.parse(value))
	);
}

export function describeEvent(payload) {
	if (payload?.error) {
		return { ok: false, message: `Backend rejected the event: ${payload.error.code || "request error"}.` };
	}
	if (
		!payload ||
		payload.schema_version !== "1.0" ||
		typeof payload.event_id !== "string" || !payload.event_id.trim() ||
		typeof payload.device_id !== "string" || !payload.device_id.trim() ||
		!validTimestamp(payload.received_at) ||
		payload.connection_status?.backend !== "online" ||
		!["online", "offline", "unknown"].includes(payload.connection_status?.sensor) ||
		!payload.classification ||
		!payload.sound_level ||
		!["Teacher Discussion", "Student Conversation", null].includes(payload.classification?.label) ||
		typeof payload.classification?.confident !== "boolean" ||
		!VALID_MEASUREMENT_STATUSES.includes(payload.classification?.status) ||
		!validTimestamp(payload.classification?.observed_at) ||
		!(payload.sound_level?.value === null || Number.isFinite(payload.sound_level?.value)) ||
		!["dB_SPL", null].includes(payload.sound_level?.unit) ||
		typeof payload.sound_level?.calibrated !== "boolean" ||
		!VALID_MEASUREMENT_STATUSES.includes(payload.sound_level?.status) ||
		!validTimestamp(payload.sound_level?.observed_at) ||
		typeof payload.warning?.triggered !== "boolean" ||
		typeof payload.warning?.reason !== "string"
	) {
		return { ok: false, message: "Backend returned an incomplete event response." };
	}

	const label = ["Teacher Discussion", "Student Conversation"].includes(payload.classification.label)
		? payload.classification.label
		: "Unavailable (no model data)";
	const reading = Number.isFinite(payload.sound_level.value) && payload.sound_level.unit === "dB_SPL"
		? `${payload.sound_level.value} ${payload.sound_level.unit}`
		: payload.sound_level.value === null
			? "Unavailable (no microphone data)"
			: "Reading provided; unit unavailable (not used for warning)";
	const sensor = payload.connection_status.sensor === "unknown"
		? "unknown (no hardware data)"
		: `reported ${payload.connection_status.sensor} (not physically verified)`;
	return {
		ok: true,
		backend: payload.connection_status.backend === "online" ? "online" : "unknown",
		sensor,
		classification: label,
		soundLevel: reading,
		warning: payload.warning.triggered ? "Triggered" : "Not triggered",
		reason: typeof payload.warning.reason === "string" ? payload.warning.reason : "unspecified",
	};
}

async function fetchJson(url, options, fetchImpl) {
	const response = await fetchImpl(url, { cache: "no-store", ...options });
	let body;
	try {
		body = await response.json();
	} catch {
		throw new BackendResponseError(`Backend returned a non-JSON response (HTTP ${response.status}).`, null, response.status);
	}
	if (!response.ok) {
		throw new BackendResponseError(`Backend request failed (HTTP ${response.status}).`, body, response.status);
	}
	return body;
}

export async function checkBackend(fetchImpl = fetch, baseUrl = BACKEND_URL) {
	try {
		const payload = await fetchJson(`${baseUrl}/health`, undefined, fetchImpl);
		return describeHealth(payload);
	} catch (error) {
		if (error instanceof BackendResponseError) {
			return { ok: false, reachable: true, message: error.message };
		}
		return { ok: false, message: "Backend unavailable. Start it on 127.0.0.1:8000 and retry." };
	}
}

export async function sendEmptyContractSample(fetchImpl = fetch, baseUrl = BACKEND_URL, id = `dashboard-check-${Date.now()}`) {
	const event = {
		schema_version: "1.0",
		event_id: id,
		device_id: "dashboard-contract-check",
		sensor_status: "unknown",
		classification: { label: null, confident: false, observed_at: null },
		sound_level: { value: null, unit: null, calibrated: false, observed_at: null },
	};
	try {
		const payload = await fetchJson(`${baseUrl}/api/v1/events`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(event),
		}, fetchImpl);
		return describeEvent(payload);
	} catch (error) {
		if (error.body) return describeEvent(error.body);
		return { ok: false, message: error.message || "Backend unavailable; the request did not complete." };
	}
}

export function describeAudioInference(payload) {
	const classification = payload?.classification;
	const score = classification?.model_confidence;
	const validScore = score === null || (
		score && typeof score === "object" &&
		Number.isFinite(score.value) && score.value >= 0 && score.value <= 1 &&
		score.method === "predict_proba" && score.calibrated === false
	);
	const sourceValid = payload?.inference?.source === "trained_model" || payload?.inference?.source === "experimental_model";
	const evaluationValid = payload?.inference?.evaluation_status === "held_out_evaluated" ||
		payload?.inference?.evaluation_status === "not_evaluated";
	const evaluationMatchesSource =
		(payload?.inference?.source === "trained_model" && payload?.inference?.evaluation_status === "held_out_evaluated") ||
		(payload?.inference?.source === "experimental_model" && payload?.inference?.evaluation_status === "not_evaluated");
	if (
		!payload || payload.schema_version !== "1.0" || payload.inference?.status !== "complete" ||
		!sourceValid || !evaluationValid || !evaluationMatchesSource ||
		!(["Teacher Discussion", "Student Conversation"].includes(classification?.label)) ||
		!validScore || typeof classification?.artifact_reference !== "string" ||
		!classification.artifact_reference.trim() || !validTimestamp(classification?.observed_at) ||
		payload.warning_evaluation?.status !== "not_performed" ||
		payload.connection_status?.backend !== "online" ||
		payload.connection_status?.hardware !== "not_tested"
	) {
		return { ok: false, state: "invalid-response", message: "Backend returned an incomplete or invalid model-inference response." };
	}
	return {
		ok: true,
		state: "actual-inference",
		classification: classification.label,
		classProbability: score === null ? null : score.value,
		source: payload.inference.source,
		evaluationStatus: payload.inference.evaluation_status,
		observedAt: classification.observed_at,
	};
}

export async function classifyAudioFile(file, fetchImpl = fetch, baseUrl = BACKEND_URL) {
	if (!file || typeof file.name !== "string" || !/\.wav$/i.test(file.name) || typeof file.arrayBuffer !== "function") {
		return { ok: false, state: "invalid-audio", code: "invalid_audio", message: "Choose a local WAV file." };
	}
	try {
		const payload = await fetchJson(`${baseUrl}/api/v1/classify`, {
			method: "POST",
			headers: { "Content-Type": "audio/wav" },
			body: file,
		}, fetchImpl);
		return describeAudioInference(payload);
	} catch (error) {
		const code = error?.body?.error?.code;
		if (code === "model_unavailable") {
			return { ok: false, state: "model-unavailable", code, message: "MODEL NOT AVAILABLE. No prediction was produced; DEMO MODE was not started." };
		}
		if (code === "invalid_audio") {
			return { ok: false, state: "invalid-audio", code, message: "The backend rejected this WAV as invalid or unsupported audio." };
		}
		if (error instanceof BackendResponseError) {
			return { ok: false, state: "request-error", code: code || "inference_error", message: error.message };
		}
		return { ok: false, state: "backend-unavailable", code: "backend_unavailable", message: "Backend unavailable. No prediction was produced; DEMO MODE was not started." };
	}
}

function mountPanel() {
	const panel = document.createElement("aside");
	panel.className = "backend-check-panel";
	panel.setAttribute("aria-labelledby", "backend-check-title");
	panel.innerHTML = `
		<div class="backend-check-heading">
			<div><span class="backend-check-kicker">LOCAL INTEGRATION</span><h2 id="backend-check-title">Backend contract check</h2></div>
			<span class="backend-check-mode">SAMPLE DATA / NO HARDWARE</span>
		</div>
		<p class="backend-check-note">The dashboard values above are simulated sample data. This panel shows actual local-backend responses, not simulated API responses. Its empty sample request contains no audio or sensor readings.</p>
		<section class="backend-check-demo" aria-labelledby="backend-demo-title">
			<div class="backend-check-demo-heading"><span class="backend-check-mode">DEMO MODE</span><h3 id="backend-demo-title">Warning policy simulation</h3></div>
			<p class="backend-check-demo-note">Simulated inputs only; no trained model, microphone, ESP32 connection, or buzzer. The local demo threshold is preset to 75 dB SPL.</p>
			<label>Selected class (simulated)
				<select data-demo-class>
					<option>Teacher Discussion</option>
					<option>Student Conversation</option>
				</select>
			</label>
			<div class="backend-check-demo-fields">
				<label>Sound level (simulated dB SPL)<input data-demo-level type="number" step="any" placeholder="Enter demo reading"></label>
				<label>Warning threshold (dB SPL)<input data-demo-threshold type="number" min="0" step="any" value="75"></label>
			</div>
			<label>Measurement scenario (simulated)
				<select data-demo-measurement>
					<option value="fresh_calibrated">Fresh and calibrated</option>
					<option value="stale">Stale</option>
					<option value="unavailable">Unavailable</option>
					<option value="invalid">Invalid</option>
					<option value="uncalibrated">Not calibrated</option>
				</select>
			</label>
			<button type="button" data-action="demo">Evaluate simulated case</button>
			<p class="backend-check-demo-result" data-demo-result data-state="idle" role="status" aria-live="polite">No demo case evaluated.</p>
		</section>
		<section class="backend-check-inference" aria-labelledby="backend-inference-title">
			<div class="backend-check-inference-heading"><span class="backend-check-mode">ACTUAL MODEL INFERENCE</span><h3 id="backend-inference-title">Classify a local WAV</h3></div>
			<p class="backend-check-inference-note">Uploads the selected WAV to the local backend. No ESP32, laptop microphone, warning decision, or buzzer is used. This does not fall back to DEMO MODE.</p>
			<label class="backend-check-file-label" for="backend-audio-file">Local WAV file
				<input id="backend-audio-file" data-audio-file type="file" accept=".wav,audio/wav">
			</label>
			<button type="button" data-action="classify">Run actual inference</button>
			<p class="backend-check-inference-status" data-inference-status data-state="idle" role="status" aria-live="polite">Model status not checked. Select a WAV file and request inference.</p>
			<dl class="backend-check-inference-result" data-inference-result hidden>
				<div><dt>Predicted class</dt><dd data-inference-field="class"></dd></div>
				<div><dt>Class probability</dt><dd data-inference-field="probability"></dd></div>
				<div><dt>Model state</dt><dd data-inference-field="model-state"></dd></div>
				<div><dt>Warning policy</dt><dd>Not evaluated by audio inference</dd></div>
				<div><dt>Hardware</dt><dd>Not tested</dd></div>
			</dl>
		</section>
		<div class="backend-check-actions">
			<button type="button" data-action="health">Check backend</button>
			<button type="button" data-action="event">Send empty sample</button>
		</div>
		<p class="backend-check-status" data-status role="status" aria-live="polite">Backend: not checked. Expected local service: 127.0.0.1:8000.</p>
		<p class="backend-check-config" data-config>Warning configuration: not checked.</p>
		<p class="backend-check-hardware">Hardware: unknown; no physical device connection is made by this panel.</p>
		<div class="backend-check-response-label" data-response-label hidden>ACTUAL BACKEND RESPONSE TO EMPTY SAMPLE</div>
		<dl class="backend-check-result" data-result hidden>
			<div><dt>Connection</dt><dd data-field="connection"></dd></div>
			<div><dt>Classification</dt><dd data-field="classification"></dd></div>
			<div><dt>Sound level</dt><dd data-field="sound-level"></dd></div>
			<div><dt>Warning</dt><dd data-field="warning"></dd></div>
			<div><dt>Reason</dt><dd data-field="reason"></dd></div>
		</dl>`;
	document.body.append(panel);
	const status = panel.querySelector("[data-status]");
	const configuration = panel.querySelector("[data-config]");
	const responseLabel = panel.querySelector("[data-response-label]");
	const result = panel.querySelector("[data-result]");
	const buttons = panel.querySelectorAll("button");
	const inferenceStatus = panel.querySelector("[data-inference-status]");
	const inferenceResult = panel.querySelector("[data-inference-result]");
	const setBusy = (busy) => buttons.forEach((button) => { button.disabled = busy; });
	panel.querySelector('[data-action="demo"]').addEventListener("click", () => {
		const outcome = evaluateDemoWarning({
			classification: panel.querySelector("[data-demo-class]").value,
			soundLevel: panel.querySelector("[data-demo-level]").value,
			threshold: panel.querySelector("[data-demo-threshold]").value,
			measurementState: panel.querySelector("[data-demo-measurement]").value,
		});
		const display = panel.querySelector("[data-demo-result]");
		const decision = outcome.triggered ? "POLICY WOULD WARN" : "NO WARNING";
		display.textContent = `DEMO RESULT — ${decision}. Reason: ${outcome.reason}. Simulated only; no physical warning was sent.`;
		display.dataset.state = outcome.triggered ? "warn" : "safe";
	});

	panel.querySelector('[data-action="health"]').addEventListener("click", async () => {
		setBusy(true);
		const health = await checkBackend();
		status.textContent = health.message;
		status.dataset.state = health.ok ? "ok" : health.reachable ? "invalid" : "error";
		configuration.textContent = health.configurationMessage || "Warning configuration: unavailable.";
		configuration.dataset.state = health.ok ? (health.warningReady ? "ready" : "not-ready") : "error";
		setBusy(false);
	});
	panel.querySelector('[data-action="event"]').addEventListener("click", async () => {
		setBusy(true);
		status.textContent = "Backend: checking local service...";
		const health = await checkBackend();
		status.textContent = health.message;
		status.dataset.state = health.ok ? "ok" : health.reachable ? "invalid" : "error";
		configuration.textContent = health.configurationMessage || "Warning configuration: unavailable.";
		configuration.dataset.state = health.ok ? (health.warningReady ? "ready" : "not-ready") : "error";
		if (!health.ok) {
			result.hidden = true;
			responseLabel.hidden = true;
			setBusy(false);
			return;
		}
		status.textContent = "Sending empty sample request to the reachable backend...";
		const event = await sendEmptyContractSample();
		status.textContent = event.ok ? "Backend response received for empty sample." : event.message;
		status.dataset.state = event.ok ? "ok" : "error";
		result.hidden = !event.ok;
		responseLabel.hidden = !event.ok;
		if (event.ok) {
			const values = {
				connection: `Backend ${event.backend}; sensor ${event.sensor}`,
				classification: event.classification,
				"sound-level": event.soundLevel,
				warning: event.warning,
				reason: event.reason,
			};
			for (const [field, value] of Object.entries(values)) {
				panel.querySelector(`[data-field="${field}"]`).textContent = value;
			}
		}
		setBusy(false);
	});
	panel.querySelector('[data-action="classify"]').addEventListener("click", async () => {
		const file = panel.querySelector("[data-audio-file]").files?.[0];
		inferenceResult.hidden = true;
		inferenceStatus.textContent = "ACTUAL MODEL INFERENCE: sending selected WAV to the local backend...";
		inferenceStatus.dataset.state = "loading";
		setBusy(true);
		const inference = await classifyAudioFile(file);
		inferenceStatus.textContent = inference.ok
			? inference.source === "experimental_model"
				? "ACTUAL MODEL INFERENCE completed with an experimental model; it has no held-out evaluation."
				: "ACTUAL MODEL INFERENCE completed using the loaded model artifact."
			: inference.state === "model-unavailable"
				? inference.message
				: inference.message;
		inferenceStatus.dataset.state = inference.ok ? "ok" : inference.state;
		if (inference.ok) {
			const values = {
				class: inference.classification,
				probability: inference.classProbability === null
					? "Not returned by this model"
					: `${(inference.classProbability * 100).toFixed(1)}% (uncalibrated predict_proba)`,
				"model-state": inference.source === "experimental_model" ? "Experimental; not evaluated" : "Held-out evaluated baseline",
			};
			for (const [field, value] of Object.entries(values)) {
				panel.querySelector(`[data-inference-field="${field}"]`).textContent = value;
			}
			inferenceResult.hidden = false;
		}
		setBusy(false);
	});
}

if (typeof document !== "undefined") mountPanel();
