export const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
const VALID_MEASUREMENT_STATUSES = ["fresh", "stale", "unavailable", "unknown", "invalid_time"];
const EVENT_CLASSES = ["Teacher Discussion", "Student Conversation"];
const BACKEND_REQUEST_TIMEOUT_MS = 15_000;
const CLASSIFICATION_REQUEST_TIMEOUT_MS = 120_000;

/**
 * Resolve the backend base URL without hardcoding credentials.
 *
 * Priority:
 * 1. `window.SONIQ_API_BASE_URL` for deployments that inject configuration.
 * 2. `<meta name="soniq-api-base" content="...">` for static hosting.
 * 3. `?api=http://127.0.0.1:8000` for local development.
 * 4. The loopback development default.
 */
export function resolveBackendUrl(search = typeof location !== "undefined" ? location.search : "") {
	let candidate = "";
	const injected = typeof window !== "undefined" && typeof window.SONIQ_API_BASE_URL === "string"
		? window.SONIQ_API_BASE_URL.trim()
		: "";
	if (injected) {
		candidate = injected;
	} else if (typeof document !== "undefined") {
		const meta = document.querySelector('meta[name="soniq-api-base"]');
		candidate = meta?.getAttribute("content") || "";
	}
	if (!candidate && search) {
		try {
			candidate = new URLSearchParams(search).get("api") || "";
		} catch {
			candidate = "";
		}
	}
	return normalizeBaseUrl(candidate) || DEFAULT_BACKEND_URL;
}

function normalizeBaseUrl(value) {
	if (typeof value !== "string" || !value.trim()) return null;
	try {
		const url = new URL(value.trim());
		if (!["http:", "https:"].includes(url.protocol)) return null;
		if (url.username || url.password) return null;
		url.hash = "";
		url.search = "";
		return url.toString().replace(/\/$/, "");
	} catch {
		return null;
	}
}

class BackendResponseError extends Error {
	constructor(message, body = null, status = null) {
		super(message);
		this.body = body;
		this.status = status;
	}
}

class BackendRequestTimeoutError extends Error {
	constructor(timeoutMs) {
		super(`Backend request timed out after ${Math.ceil(timeoutMs / 1000)} seconds.`);
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
		warningConfigurationStatus: payload.warning_configuration_status,
		reasons: [...reasons],
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

/**
 * Validate one backend event response and return the fields the dashboard
 * needs. Returns null when the payload does not match the event contract.
 */
export function normalizeEventRecord(payload) {
	if (
		!payload ||
		typeof payload !== "object" ||
		Array.isArray(payload) ||
		payload.schema_version !== "1.0" ||
		typeof payload.event_id !== "string" || !payload.event_id.trim() ||
		typeof payload.device_id !== "string" || !payload.device_id.trim() ||
		typeof payload.received_at !== "string" || !validTimestamp(payload.received_at) ||
		payload.connection_status?.backend !== "online" ||
		!["online", "offline", "unknown"].includes(payload.connection_status?.sensor) ||
		!payload.classification ||
		!payload.sound_level ||
		(!EVENT_CLASSES.includes(payload.classification?.label) && payload.classification?.label !== null) ||
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
		return null;
	}
	return {
		schemaVersion: payload.schema_version,
		eventId: payload.event_id,
		deviceId: payload.device_id,
		receivedAt: payload.received_at,
		sensorStatus: payload.connection_status.sensor,
		classificationLabel: payload.classification.label,
		classificationConfident: payload.classification.confident,
		classificationStatus: payload.classification.status,
		classificationObservedAt: payload.classification.observed_at,
		soundLevelValue: payload.sound_level.value,
		soundLevelUnit: payload.sound_level.unit,
		soundLevelCalibrated: payload.sound_level.calibrated,
		soundLevelStatus: payload.sound_level.status,
		soundLevelObservedAt: payload.sound_level.observed_at,
		warningTriggered: payload.warning.triggered,
		warningReason: payload.warning.reason,
	};
}

async function fetchJson(url, options, fetchImpl, timeoutMs = BACKEND_REQUEST_TIMEOUT_MS) {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const response = await fetchImpl(url, {
			cache: "no-store",
			...options,
			signal: controller.signal,
		});
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
	} catch (error) {
		if (controller.signal.aborted) {
			throw new BackendRequestTimeoutError(timeoutMs);
		}
		throw error;
	} finally {
		clearTimeout(timeoutId);
	}
}

export async function checkBackend(fetchImpl = fetch, baseUrl = resolveBackendUrl()) {
	try {
		const payload = await fetchJson(`${baseUrl}/health`, undefined, fetchImpl);
		return describeHealth(payload);
	} catch (error) {
		if (error instanceof BackendResponseError) {
			return { ok: false, reachable: true, message: error.message };
		}
		if (error instanceof BackendRequestTimeoutError) {
			return { ok: false, code: "request_timeout", message: error.message };
		}
		return { ok: false, message: `Backend unavailable. Start it at ${baseUrl} and retry.` };
	}
}

/**
 * Read event history from the backend.
 *
 * The backend returns persisted PostgreSQL events ordered newest first, with
 * `limit`/`offset` pagination metadata.
 */
export async function fetchEvents({ fetchImpl = fetch, baseUrl = resolveBackendUrl(), limit = 10, offset = 0 } = {}) {
	const safeLimit = Number.isInteger(limit) && limit > 0 ? Math.min(limit, 100) : 10;
	const safeOffset = Number.isInteger(offset) && offset >= 0 ? offset : 0;
	let url;
	try {
		url = new URL(`${baseUrl}/api/v1/events`);
	} catch {
		return { ok: false, state: "error", code: "invalid_base_url", message: "The configured backend URL is invalid." };
	}
	url.searchParams.set("limit", String(safeLimit));
	url.searchParams.set("offset", String(safeOffset));

	let body;
	try {
		body = await fetchJson(url.toString(), undefined, fetchImpl);
	} catch (error) {
		if (error instanceof BackendRequestTimeoutError) {
			return {
				ok: false,
				state: "error",
				code: "request_timeout",
				message: error.message,
			};
		}
		if (error instanceof BackendResponseError) {
			if ([404, 405, 501].includes(error.status)) {
				return {
					ok: false,
					state: "unavailable",
					code: "event_history_unavailable",
					status: error.status,
					message: "Event history is unavailable. The backend does not expose GET /api/v1/events.",
				};
			}
			return {
				ok: false,
				state: "error",
				code: "request_error",
				status: error.status,
				message: error.message,
			};
		}
		return {
			ok: false,
			state: "error",
			code: "backend_unavailable",
			message: "Backend unavailable; event history could not be loaded.",
		};
	}

	const rawEvents = Array.isArray(body) ? body : Array.isArray(body?.events) ? body.events : null;
	if (!rawEvents) {
		return {
			ok: false,
			state: "error",
			code: "invalid_response",
			message: "Backend returned an event-history response without an events array.",
		};
	}

	const events = [];
	let invalidCount = 0;
	for (const item of rawEvents) {
		const record = normalizeEventRecord(item);
		if (record) events.push(record);
		else invalidCount += 1;
	}
	if (rawEvents.length > 0 && events.length === 0) {
		return {
			ok: false,
			state: "error",
			code: "invalid_response",
			message: "Backend returned event records that do not match the event contract.",
		};
	}

	const pagination = body?.pagination;
	const total = Number.isInteger(pagination?.total)
		? pagination.total
		: Number.isInteger(body?.total)
			? body.total
			: null;
	const hasMore = typeof pagination?.has_more === "boolean"
		? pagination.has_more
		: total !== null
			? safeOffset + events.length < total
			: false;
	return {
		ok: true,
		state: "success",
		events,
		invalidCount,
		pagination: { limit: safeLimit, offset: safeOffset, total, hasMore },
	};
}

export function summarizeEvents(events) {
	const records = Array.isArray(events) ? events : [];
	const sorted = [...records].sort((left, right) => {
		const leftTime = Date.parse(left.receivedAt);
		const rightTime = Date.parse(right.receivedAt);
		return (Number.isFinite(rightTime) ? rightTime : 0) - (Number.isFinite(leftTime) ? leftTime : 0);
	});
	return {
		total: records.length,
		warningsTriggered: records.filter((event) => event.warningTriggered === true).length,
		teacherDiscussion: records.filter((event) => event.classificationLabel === "Teacher Discussion").length,
		studentConversation: records.filter((event) => event.classificationLabel === "Student Conversation").length,
		soundReadings: records.filter((event) => Number.isFinite(event.soundLevelValue) && event.soundLevelUnit === "dB_SPL").length,
		latestEvent: sorted[0] || null,
	};
}

export function serializeEventReportCsv(events) {
	if (!Array.isArray(events)) {
		throw new TypeError("Event report data must be an array.");
	}
	const header = [
		"event_id",
		"device_id",
		"received_at",
		"classification",
		"classification_confident",
		"classification_status",
		"classification_observed_at",
		"sound_level_value",
		"sound_level_unit",
		"sound_level_calibrated",
		"sound_level_status",
		"sound_level_observed_at",
		"warning_triggered",
		"warning_reason",
	];
	const escape = (value) => {
		let text = value === null || value === undefined ? "" : String(value);
		if (typeof value === "string" && /^\s*[=+\-@]/.test(text)) {
			text = `'${text}`;
		}
		return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
	};
	const rows = events.map((event) => [
		event.eventId,
		event.deviceId,
		event.receivedAt,
		event.classificationLabel ?? "",
		event.classificationConfident,
		event.classificationStatus,
		event.classificationObservedAt ?? "",
		event.soundLevelValue ?? "",
		event.soundLevelUnit ?? "",
		event.soundLevelCalibrated,
		event.soundLevelStatus,
		event.soundLevelObservedAt ?? "",
		event.warningTriggered,
		event.warningReason,
	].map(escape).join(","));
	return [header.join(","), ...rows].join("\r\n");
}

export function isStale(timestamp, now = Date.now(), maxAgeMs = 60000) {
	const time = Date.parse(timestamp);
	if (!Number.isFinite(time)) return true;
	return now - time > maxAgeMs;
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

export async function classifyAudioFile(file, fetchImpl = fetch, baseUrl = resolveBackendUrl()) {
	if (!file || typeof file.name !== "string" || !/\.wav$/i.test(file.name) || typeof file.arrayBuffer !== "function") {
		return { ok: false, state: "invalid-audio", code: "invalid_audio", message: "Choose a local WAV file." };
	}
	try {
		const payload = await fetchJson(`${baseUrl}/api/v1/classify`, {
			method: "POST",
			headers: { "Content-Type": "audio/wav" },
			body: file,
		}, fetchImpl, CLASSIFICATION_REQUEST_TIMEOUT_MS);
		return describeAudioInference(payload);
	} catch (error) {
		if (error instanceof BackendRequestTimeoutError) {
			return {
				ok: false,
				state: "request-timeout",
				code: "request_timeout",
				message: `Classification request timed out after ${Math.ceil(CLASSIFICATION_REQUEST_TIMEOUT_MS / 1000)} seconds. No prediction was produced.`,
			};
		}
		const code = error?.body?.error?.code;
		if (code === "model_unavailable") {
			return { ok: false, state: "model-unavailable", code, message: "Model unavailable. No prediction was produced; provide a compatible model artifact." };
		}
		if (code === "invalid_audio") {
			return { ok: false, state: "invalid-audio", code, message: "The backend rejected this WAV as invalid or unsupported audio." };
		}
		if (error instanceof BackendResponseError) {
			return { ok: false, state: "request-error", code: code || "inference_error", message: error.message };
		}
		return { ok: false, state: "backend-unavailable", code: "backend_unavailable", message: "Backend unavailable. No prediction was produced." };
	}
}
