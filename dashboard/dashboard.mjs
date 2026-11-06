import {
	checkBackend,
	classifyAudioFile,
	fetchEvents,
	isStale,
	resolveBackendUrl,
	serializeEventReportCsv,
	summarizeEvents,
} from "./backend-adapter.mjs";

const PAGE_SIZE = 10;
const STALE_AFTER_MS = 60000;
const REFRESH_INTERVAL_MS = 30000;

const state = {
	baseUrl: resolveBackendUrl(),
	health: null,
	healthAt: null,
	events: null,
	latestEvent: null,
	eventsState: "idle",
	eventsAt: null,
	offset: 0,
	limit: PAGE_SIZE,
	total: null,
	hasMore: false,
	invalidCount: 0,
	lastInference: null,
	busy: false,
};

let refreshTimer = null;
let freshnessTimer = null;
let pageActive = true;

const byId = (id) => document.getElementById(id);

function setText(id, value) {
	const element = byId(id);
	if (element) element.textContent = value;
}

function setState(id, value) {
	const element = byId(id);
	if (element) element.dataset.state = value;
}

function setMetric(valueId, value, stateValue, detailId, detail) {
	setText(valueId, value);
	setState(valueId, stateValue);
	if (detailId) setText(detailId, detail);
}

function setIntegrationStatus(id, value, stateValue) {
	setText(id, value);
	setState(id, stateValue);
}

function formatTimestamp(value) {
	if (!value) return "Unavailable";
	const time = Date.parse(value);
	if (!Number.isFinite(time)) return "Invalid timestamp";
	return new Intl.DateTimeFormat(undefined, {
		dateStyle: "medium",
		timeStyle: "medium",
	}).format(new Date(time));
}

function formatTime(value) {
	const time = Date.parse(value);
	if (!Number.isFinite(time)) return "unknown time";
	return new Intl.DateTimeFormat(undefined, {
		hour: "numeric",
		minute: "2-digit",
		second: "2-digit",
	}).format(new Date(time));
}

function showToast(message) {
	const toast = byId("toast");
	if (!toast) return;
	toast.textContent = message;
	toast.classList.add("visible");
	clearTimeout(showToast.timer);
	showToast.timer = setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setBanner(stateValue, title, message) {
	const banner = byId("connection-banner");
	if (!banner) return;
	banner.dataset.state = stateValue;
	setText("connection-title", title);
	setText("connection-message", message);
}

function setSidebar(stateValue, label, detail) {
	setText("sidebar-backend-label", label);
	setText("sidebar-backend-detail", detail);
	setState("sidebar-backend-pip", stateValue);
}

function updateLastUpdated() {
	const last = state.eventsAt || state.healthAt;
	if (!last) {
		setText("last-updated-text", "Not checked");
		setState("live-pip", "unknown");
		return;
	}
	const stale = isStale(last, Date.now(), STALE_AFTER_MS);
	if (state.health && !state.health.ok) {
		const checkedAt = state.healthAt || last;
		const dataStatus = state.eventsAt
			? ` · event data ${isStale(state.eventsAt, Date.now(), STALE_AFTER_MS) ? "stale" : "last loaded"} ${formatTime(state.eventsAt)}`
			: "";
		setText("last-updated-text", `${state.health.reachable ? "Invalid response" : "Unreachable"} · checked ${formatTime(checkedAt)}${dataStatus}`);
		setState("live-pip", "error");
		return;
	}
	if (state.health?.ok && !state.health.warningReady) {
		setText(
			"last-updated-text",
			`${stale ? "Stale" : "Updated"} ${formatTime(last)} · warnings not ready`,
		);
		setState("live-pip", "warn");
		return;
	}
	setText("last-updated-text", `${stale ? "Stale" : "Updated"} ${formatTime(last)}`);
	setState("live-pip", stale ? "warn" : "ok");
}

function renderHealth(health, checkedAt) {
	state.health = health;
	state.healthAt = checkedAt;
	setText("health-api-url", state.baseUrl);

	if (!health) {
		setIntegrationStatus("integration-health", "Not checked", "idle");
		setIntegrationStatus("integration-state", "Not checked", "idle");
		setBanner("idle", "Backend status not checked", `Use Refresh data to check the SONIQ backend at ${state.baseUrl}.`);
		setMetric("backend-status-value", "Not checked", "idle", "backend-status-detail", "GET /health has not been called yet.");
		setMetric("warning-config-value", "Not checked", "idle", "warning-config-detail", "Warning readiness has not been checked.");
		setText("health-state", "Not checked");
		setState("health-state", "idle");
		setText("health-process", "Not checked");
		setState("health-process", "");
		setText("health-warning", "Not checked");
		setState("health-warning", "");
		setText("health-reasons", "Not checked");
		setState("health-reasons", "");
		setSidebar("unknown", "Backend status", "Not checked");
		return;
	}

	if (health.ok) {
		setIntegrationStatus("integration-health", "Online · warning configuration " + (health.warningReady ? "ready" : "not ready"), health.warningReady ? "ok" : "warn");
		setIntegrationStatus("integration-state", "Backend online", "ok");
		setBanner(
			"ok",
			"Backend online",
			`Actual response from GET /health. Hardware connection has not been verified.`,
		);
		setMetric(
			"backend-status-value",
			"Online",
			"ok",
			"backend-status-detail",
			`Checked ${formatTimestamp(checkedAt)}. This only means the backend process answered.`,
		);
		setMetric(
			"warning-config-value",
			health.warningReady ? "Ready" : "Not ready",
			health.warningReady ? "ok" : "warn",
			"warning-config-detail",
			health.configurationMessage || "Warning configuration status unavailable.",
		);
		setText("health-state", health.warningReady ? "Online · ready" : "Online · not ready");
		setState("health-state", health.warningReady ? "ok" : "warn");
		setText("health-process", "Online");
		setState("health-process", "ok");
		setText("health-warning", health.warningReady ? "Ready" : "Not ready");
		setState("health-warning", health.warningReady ? "ok" : "warn");
		setText("health-reasons", health.reasons?.length ? health.reasons.join(", ") : "None");
		setState("health-reasons", health.warningReady ? "ok" : "warn");
		setSidebar(
			health.warningReady ? "ok" : "warn",
			"Backend online",
			health.warningReady ? "Warning configuration ready" : "Warning configuration not ready",
		);
		return;
	}

	if (health.reachable) {
		setIntegrationStatus("integration-health", "Reachable · invalid response", "error");
		setIntegrationStatus("integration-state", "Invalid response", "error");
		setBanner("error", "Backend response invalid", health.message);
		setMetric("backend-status-value", "Invalid response", "error", "backend-status-detail", health.message);
		setMetric("warning-config-value", "Unknown", "unknown", "warning-config-detail", "The health response could not be trusted.");
		setText("health-state", "Invalid response");
		setState("health-state", "error");
		setText("health-process", "Reachable · invalid response");
		setState("health-process", "error");
		setText("health-warning", "Unknown");
		setState("health-warning", "unknown");
		setText("health-reasons", "Unavailable");
		setState("health-reasons", "unknown");
		setSidebar("error", "Backend response invalid", "Warning readiness unknown");
		return;
	}

	setIntegrationStatus("integration-health", "Unreachable", "error");
	setIntegrationStatus("integration-state", "Backend unavailable", "error");
	setBanner("error", "Backend unreachable", health.message || "The SONIQ backend could not be reached.");
	setMetric("backend-status-value", "Unreachable", "error", "backend-status-detail", health.message || "The request did not complete.");
	setMetric("warning-config-value", "Unknown", "unknown", "warning-config-detail", "Warning readiness cannot be determined while the backend is unreachable.");
	setText("health-state", "Unreachable");
	setState("health-state", "error");
	setText("health-process", "Unreachable");
	setState("health-process", "error");
	setText("health-warning", "Unknown");
	setState("health-warning", "unknown");
	setText("health-reasons", "Unavailable");
	setState("health-reasons", "unknown");
	setSidebar("error", "Backend unreachable", "Start the backend and retry");
}

function classificationChip(record) {
	const chip = document.createElement("span");
	chip.className = "classification-chip";
	if (record.classificationLabel === "Teacher Discussion" || record.classificationLabel === "Student Conversation") {
		chip.textContent = record.classificationLabel;
		chip.dataset.label = record.classificationLabel;
	} else {
		chip.textContent = "Unavailable";
		chip.dataset.label = "unavailable";
	}
	return chip;
}

function warningChip(triggered) {
	const chip = document.createElement("span");
	chip.className = "warning-chip";
	chip.textContent = triggered ? "Triggered" : "Not triggered";
	chip.dataset.triggered = String(triggered);
	return chip;
}

export function soundLevelText(record) {
	if (Number.isFinite(record.soundLevelValue) && record.soundLevelUnit === "dB_SPL") {
		return `${record.soundLevelValue} dB SPL`;
	}
	if (Number.isFinite(record.soundLevelValue)) {
		return `${record.soundLevelValue} (unit unavailable)`;
	}
	return "Unavailable";
}

export function classificationState(record) {
	if (!record.classificationLabel) return "unavailable";
	if (record.classificationStatus === "fresh") return "ok";
	if (record.classificationStatus === "stale") return "warn";
	if (record.classificationStatus === "unavailable" || record.classificationStatus === "unknown") return "unavailable";
	return "warn";
}

export function soundLevelState(record) {
	if (!Number.isFinite(record.soundLevelValue)) return "unavailable";
	if (record.soundLevelUnit !== "dB_SPL") return "warn";
	if (record.soundLevelStatus === "fresh") return record.soundLevelCalibrated ? "ok" : "warn";
	if (record.soundLevelStatus === "stale") return "warn";
	if (record.soundLevelStatus === "unavailable" || record.soundLevelStatus === "unknown") return "unavailable";
	return "warn";
}

export function sensorState(status) {
	if (status === "online") return "ok";
	if (status === "offline") return "error";
	return "unknown";
}

function renderEventRows(events) {
	const body = byId("events-body");
	if (!body) return;
	body.replaceChildren();
	if (events.length === 0) {
		renderEventMessage("No events recorded yet. The backend returned an empty event list.", "empty");
		return;
	}
	for (const event of events) {
		const row = document.createElement("tr");

		const received = document.createElement("td");
		const time = document.createElement("time");
		time.dateTime = event.receivedAt;
		time.textContent = formatTimestamp(event.receivedAt);
		received.append(time);
		row.append(received);

		const classification = document.createElement("td");
		classification.append(classificationChip(event));
		row.append(classification);

		const sound = document.createElement("td");
		sound.textContent = soundLevelText(event);
		row.append(sound);

		const warning = document.createElement("td");
		warning.append(warningChip(event.warningTriggered));
		row.append(warning);

		const reason = document.createElement("td");
		reason.textContent = event.warningReason;
		row.append(reason);

		const device = document.createElement("td");
		device.textContent = event.deviceId;
		row.append(device);

		body.append(row);
	}
}

function renderEventMessage(message, stateValue) {
	const body = byId("events-body");
	if (!body) return;
	body.replaceChildren();
	const row = document.createElement("tr");
	row.className = "empty-row";
	row.dataset.state = stateValue;
	const cell = document.createElement("td");
	cell.colSpan = 6;
	cell.textContent = message;
	row.append(cell);
	body.append(row);
}

function updateEventsFooter() {
	const previous = byId("events-prev");
	const next = byId("events-next");
	const exportButton = byId("export-button");
	if (previous) previous.disabled = state.busy || state.eventsState !== "success" || state.offset <= 0;
	if (next) next.disabled = state.busy || state.eventsState !== "success" || !state.hasMore;
	if (exportButton) exportButton.disabled = state.busy || state.eventsState !== "success" || !state.events || state.events.length === 0;

	if (["success", "stale"].includes(state.eventsState) && state.events) {
		const parts = [`Showing ${state.events.length} event${state.events.length === 1 ? "" : "s"}`];
		if (state.total !== null) parts.push(`total ${state.total}`);
		if (state.invalidCount > 0) parts.push(`${state.invalidCount} skipped (invalid contract)`);
		if (state.eventsState === "stale") parts.push("refresh failed · showing last successful data");
		if (isStale(state.eventsAt, Date.now(), STALE_AFTER_MS)) {
			parts.push(`stale — last successful refresh ${formatTime(state.eventsAt)}`);
		}
		setText("events-summary", parts.join(" · "));
		return;
	}
	if (state.eventsState === "loading") {
		setText("events-summary", "Loading event history…");
		return;
	}
	if (state.eventsState === "unavailable") {
		setText("events-summary", "Event history unavailable — GET /api/v1/events is not available.");
		return;
	}
	if (state.eventsState === "error") {
		setText("events-summary", "Could not load event history. Check the backend connection and retry.");
		return;
	}
	setText("events-summary", "No event data loaded.");
}

function renderEvents(result, loadedAt) {
	if (result.ok) {
		state.eventsState = "success";
		state.events = result.events;
		state.eventsAt = loadedAt;
		state.offset = result.pagination.offset;
		state.limit = result.pagination.limit;
		state.total = result.pagination.total;
		state.hasMore = result.pagination.hasMore;
		state.invalidCount = result.invalidCount;
		if (result.pagination.offset === 0) {
			state.latestEvent = summarizeEvents(result.events).latestEvent;
		}
		setText("health-events", "Available (GET /api/v1/events)");
		setState("health-events", "ok");
		setIntegrationStatus("integration-events", `Loaded ${result.events.length} event${result.events.length === 1 ? "" : "s"} · PostgreSQL history`, "ok");
		renderEventRows(result.events);
		updateEventsFooter();
		return;
	}

	if (state.events && state.eventsAt) {
		state.eventsState = "stale";
		const reason = result.state === "unavailable" ? "Endpoint unavailable" : "Refresh failed";
		setText("health-events", `${reason} · showing last successful data`);
		setState("health-events", "warn");
		setIntegrationStatus("integration-events", `${reason} · showing last successful data`, "warn");
		updateEventsFooter();
		return;
	}

	state.eventsState = result.state === "unavailable" ? "unavailable" : "error";
	state.events = null;
	state.latestEvent = null;
	state.eventsAt = null;
	state.total = null;
	state.hasMore = false;
	state.invalidCount = 0;
	renderEventMessage(result.message, state.eventsState);
	updateEventsFooter();
	if (result.state === "unavailable") {
		setText("health-events", "Unavailable — GET /api/v1/events");
		setState("health-events", "unavailable");
		setIntegrationStatus("integration-events", "Unavailable · GET /api/v1/events", "warn");
	} else {
		setText("health-events", "Could not load event history");
		setState("health-events", "error");
		setIntegrationStatus("integration-events", result.message, "error");
	}
}

function renderLatest() {
	const event = state.latestEvent;
	const inference = state.lastInference;

	if (event) {
		const eventDataStale = state.eventsState === "stale" || isStale(state.eventsAt, Date.now(), STALE_AFTER_MS);
		setMetric(
			"classification-value",
			event.classificationLabel || "Unavailable",
			classificationState(event),
			"classification-detail",
			`Confident: ${event.classificationConfident ? "yes" : "no"} · status: ${event.classificationStatus}`,
		);
		setMetric(
			"sound-level-value",
			soundLevelText(event),
			soundLevelState(event),
			"sound-level-detail",
			`Calibrated: ${event.soundLevelCalibrated ? "yes" : "no"} · status: ${event.soundLevelStatus}`,
		);
		setMetric(
			"warning-status-value",
			event.warningTriggered ? "Triggered" : "Not triggered",
			event.warningTriggered ? "warn" : "ok",
			"warning-status-detail",
			`Backend decision. Reason: ${event.warningReason}. Physical buzzer delivery is not verified.`,
		);
		setMetric(
			"latest-event-value",
			formatTimestamp(event.receivedAt),
			eventDataStale ? "warn" : "ok",
			"latest-event-detail",
			`Device ${event.deviceId} · event ${event.eventId}${eventDataStale ? " · last successful refresh is stale" : ""}`,
		);

		setText("monitoring-source", eventDataStale ? "Event history · stale" : "Event history");
		setState("monitoring-source", eventDataStale ? "warn" : "ok");
		setMetric("monitor-classification", event.classificationLabel || "Unavailable", classificationState(event), "monitor-classification-meta", `Confident: ${event.classificationConfident ? "yes" : "no"} · status: ${event.classificationStatus}`);
		setMetric("monitor-sound", soundLevelText(event), soundLevelState(event), "monitor-sound-meta", `Calibrated: ${event.soundLevelCalibrated ? "yes" : "no"} · status: ${event.soundLevelStatus}`);
		setMetric("monitor-warning", event.warningTriggered ? "Triggered" : "Not triggered", event.warningTriggered ? "warn" : "ok", "monitor-warning-meta", "Decision returned by the backend warning policy.");
		setMetric("monitor-reason", event.warningReason, event.warningTriggered ? "warn" : "ok", "monitor-reason-meta", "Exact reason code returned by the backend.");
		setMetric("monitor-time", formatTimestamp(event.receivedAt), "ok", "monitor-time-meta", `Classification observed: ${formatTimestamp(event.classificationObservedAt)} · sound observed: ${formatTimestamp(event.soundLevelObservedAt)}`);
		setMetric("monitor-sensor", event.sensorStatus, sensorState(event.sensorStatus), "monitor-sensor-meta", `Device ${event.deviceId}. Reported sensor status is not physical verification.`);
		setText(
			"monitoring-note",
			eventDataStale
				? "Showing the last successful event-history response; the latest refresh failed or is older than 60 seconds. Warning decisions remain backend-provided; physical buzzer delivery is not verified."
				: "Actual event returned by GET /api/v1/events. Warning decisions come from the backend; physical buzzer delivery is not verified.",
		);
		return;
	}

	if (inference) {
		setMetric(
			"classification-value",
			inference.classification,
			"ok",
			"classification-detail",
			`Source: local WAV inference · model: ${inference.source === "experimental_model" ? "experimental (not evaluated)" : "held-out evaluated baseline"}`,
		);
		setMetric(
			"sound-level-value",
			"Unavailable",
			"unavailable",
			"sound-level-detail",
			"The classification endpoint does not return a sound-level measurement.",
		);
		setMetric(
			"warning-status-value",
			"Unknown",
			"unknown",
			"warning-status-detail",
			"The classification endpoint reports warning_evaluation: not_performed.",
		);
		setMetric(
			"latest-event-value",
			"Unavailable",
			"unavailable",
			"latest-event-detail",
			"No event history data is available.",
		);

		setText("monitoring-source", "Local inference");
		setState("monitoring-source", "ok");
		setMetric("monitor-classification", inference.classification, "ok", "monitor-classification-meta", `Source: local WAV inference · observed ${formatTimestamp(inference.observedAt)}`);
		setMetric("monitor-sound", "Unavailable", "unavailable", "monitor-sound-meta", "Not provided by POST /api/v1/classify.");
		setMetric("monitor-warning", "Unknown", "unknown", "monitor-warning-meta", "Warning policy was not evaluated by this endpoint.");
		setMetric("monitor-reason", "Unavailable", "unavailable", "monitor-reason-meta", "No warning decision was produced.");
		setMetric("monitor-time", formatTimestamp(inference.observedAt), "ok", "monitor-time-meta", "Model inference observation time.");
		setMetric("monitor-sensor", "Not tested", "unknown", "monitor-sensor-meta", "The classification endpoint does not test hardware.");
		setText("monitoring-note", "Actual model inference from POST /api/v1/classify. This is not live monitoring, and the endpoint does not evaluate warnings or sound levels.");
		return;
	}

	setMetric("classification-value", "Unavailable", "unavailable", "classification-detail", "No actual classification has been received.");
	setMetric("sound-level-value", "Unavailable", "unavailable", "sound-level-detail", "No sound-level reading is available from the backend.");
	setMetric("warning-status-value", "Unknown", "unknown", "warning-status-detail", "Warning status cannot be determined without an actual event.");
	setMetric("latest-event-value", "Unavailable", "unavailable", "latest-event-detail", "No event has been loaded.");
	setText("monitoring-source", "Unavailable");
	setState("monitoring-source", "unavailable");
	setMetric("monitor-classification", "Unavailable", "unavailable", "monitor-classification-meta", "No model result received.");
	setMetric("monitor-sound", "Unavailable", "unavailable", "monitor-sound-meta", "No microphone reading received.");
	setMetric("monitor-warning", "Unknown", "unknown", "monitor-warning-meta", "Warning policy was not evaluated.");
	setMetric("monitor-reason", "Unavailable", "unavailable", "monitor-reason-meta", "No backend warning reason received.");
	setMetric("monitor-time", "Unavailable", "unavailable", "monitor-time-meta", "No timestamp available.");
	setMetric("monitor-sensor", "Unavailable", "unavailable", "monitor-sensor-meta", "No device information available.");
	setText("monitoring-note", "The dashboard does not estimate readings or warning decisions. A warning decision does not prove that the physical buzzer fired.");
}

function renderHistorySummary() {
	if (!["success", "stale"].includes(state.eventsState) || !state.events) {
		const detail = state.eventsState === "unavailable"
			? "Event history is unavailable from the current backend."
			: state.eventsState === "error"
				? "Event history could not be loaded."
				: "Event history has not been loaded.";
		for (const id of ["history-total", "history-warnings", "history-teacher", "history-student", "history-readings"]) {
			setText(id, "Unavailable");
			setState(id, "unavailable");
		}
		setText("history-total-detail", detail);
		setText("history-warnings-detail", "Actual warning decisions only.");
		setText("history-teacher-detail", "Exact model label.");
		setText("history-student-detail", "Exact model label.");
		setText("history-readings-detail", "Calibrated dB SPL readings returned by events.");
		setText("history-latest", "Unavailable");
		setState("history-latest", "unavailable");
		setText("history-latest-detail", "No event timestamp available.");
		return;
	}

	const summary = summarizeEvents(state.events);
	const empty = state.events.length === 0;
	const latestIsStale = Boolean(state.latestEvent) && (
		state.eventsState === "stale" || isStale(state.eventsAt, Date.now(), STALE_AFTER_MS)
	);
	const freshnessDetail = state.eventsState === "stale"
		? "Last successful page; the latest refresh failed."
		: empty ? "No events recorded yet." : "From the current event-history page.";
	setMetric("history-total", String(summary.total), state.eventsState === "stale" ? "warn" : "ok", "history-total-detail", freshnessDetail);
	setMetric("history-warnings", String(summary.warningsTriggered), "ok", "history-warnings-detail", "Backend warning decisions in the loaded events.");
	setMetric("history-teacher", String(summary.teacherDiscussion), "ok", "history-teacher-detail", "Exact model label.");
	setMetric("history-student", String(summary.studentConversation), "ok", "history-student-detail", "Exact model label.");
	setMetric("history-readings", String(summary.soundReadings), "ok", "history-readings-detail", "Events with a dB_SPL sound reading.");
	setMetric(
		"history-latest",
		state.latestEvent ? formatTimestamp(state.latestEvent.receivedAt) : "None",
		state.latestEvent ? (latestIsStale ? "warn" : "ok") : "unavailable",
		"history-latest-detail",
		state.latestEvent
			? `Device ${state.latestEvent.deviceId}${latestIsStale ? " · last successful data" : ""}`
			: "No event timestamp available.",
	);
}

function beginLoading() {
	if (!state.health) {
		setBanner("loading", "Checking backend…", "Requesting GET /health and the event-history endpoint.");
		setMetric("backend-status-value", "Checking…", "loading", "backend-status-detail", "Waiting for GET /health.");
		setMetric("warning-config-value", "Checking…", "loading", "warning-config-detail", "Waiting for warning readiness.");
		setText("health-state", "Checking");
		setState("health-state", "loading");
	}
	if (!state.events) {
		state.eventsState = "loading";
		renderEventMessage("Loading event history…", "loading");
		updateEventsFooter();
	}
}

function setBusy(busy) {
	state.busy = busy;
	const main = document.querySelector(".main-content");
	if (main) main.setAttribute("aria-busy", String(busy));
	for (const id of ["refresh-data", "top-refresh", "events-refresh", "classify-submit"]) {
		const button = byId(id);
		if (button) button.disabled = busy;
	}
	updateEventsFooter();
}

async function loadDashboard({ quiet = false } = {}) {
	if (state.busy) return;
	setBusy(true);
	try {
		if (!quiet) beginLoading();
		const checkedAt = new Date().toISOString();
		const [health, events] = await Promise.all([
			checkBackend(fetch, state.baseUrl),
			fetchEvents({ fetchImpl: fetch, baseUrl: state.baseUrl, limit: state.limit, offset: state.offset }),
		]);
		renderHealth(health, checkedAt);
		renderEvents(events, checkedAt);
		renderLatest();
		renderHistorySummary();
		updateLastUpdated();
		if (!quiet) {
			showToast(
				health.ok
					? "Dashboard refreshed from the backend"
					: health.reachable
						? "Backend response was invalid"
						: "Backend unreachable",
			);
		}
	} catch (error) {
		setBanner("error", "Dashboard refresh failed", error?.message || "An unexpected error occurred while refreshing the dashboard.");
		showToast("Dashboard refresh failed");
	} finally {
		setBusy(false);
	}
}

async function loadEvents(offset = state.offset) {
	if (state.busy) return;
	setBusy(true);
	try {
		state.eventsState = "loading";
		if (!state.events) renderEventMessage("Loading event history…", "loading");
		updateEventsFooter();
		const loadedAt = new Date().toISOString();
		const result = await fetchEvents({ fetchImpl: fetch, baseUrl: state.baseUrl, limit: state.limit, offset });
		renderEvents(result, loadedAt);
		renderLatest();
		renderHistorySummary();
		updateLastUpdated();
		showToast(result.ok ? "Event history refreshed" : "Event history could not be refreshed");
	} catch (error) {
		if (state.events && state.eventsAt) {
			state.eventsState = "stale";
			setText("health-events", "Refresh failed · showing last successful data");
			setState("health-events", "warn");
			setIntegrationStatus("integration-events", "Refresh failed · showing last successful data", "warn");
		} else {
			state.eventsState = "error";
			state.events = null;
			state.latestEvent = null;
			renderEventMessage(error?.message || "Event history could not be loaded.", "error");
			setIntegrationStatus("integration-events", error?.message || "Could not load event history", "error");
		}
		updateEventsFooter();
		renderHistorySummary();
		updateLastUpdated();
		showToast("Event history could not be refreshed");
	} finally {
		setBusy(false);
	}
}

function exportEvents() {
	if (!state.events || state.events.length === 0) {
		showToast("No actual event data to export");
		return;
	}
	const csv = serializeEventReportCsv(state.events);
	const link = document.createElement("a");
	const objectUrl = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
	link.href = objectUrl;
	link.download = "soniq-event-report.csv";
	link.click();
	setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
	showToast("Actual event data exported");
}

function selectView(button) {
	const history = button.dataset.view === "history";
	document.querySelectorAll(".view-tab").forEach((tab) => {
		const active = tab === button;
		tab.classList.toggle("active", active);
		tab.setAttribute('aria-selected', active);
		tab.setAttribute('tabindex', active ? '0' : '-1');
	});
	document.querySelector('.live-summary').hidden = history;
	document.querySelector('.history-summary').hidden = !history;
	setText("view-description", history ? "Aggregated actual event history" : "Latest backend data");
	showToast(history ? "Event history summary selected" : "Live overview selected");
}

function initializeTabs() {
	const viewTabs = document.querySelectorAll(".view-tab");
	viewTabs.forEach((button, index) => {
		button.addEventListener('click', () => selectView(button));
		button.addEventListener("keydown", (event) => {
			let nextIndex;
			if (event.key === 'ArrowRight') nextIndex = (index + 1) % viewTabs.length;
			else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + viewTabs.length) % viewTabs.length;
			else if (event.key === 'Home') nextIndex = 0;
			else if (event.key === 'End') nextIndex = viewTabs.length - 1;
			else return;

			event.preventDefault();
			const nextTab = viewTabs[nextIndex];
			nextTab.focus();
			selectView(nextTab);
		});
	});
}

function initializeControls() {
	byId("refresh-data")?.addEventListener("click", () => loadDashboard());
	byId("top-refresh")?.addEventListener("click", () => loadDashboard());
	byId("events-refresh")?.addEventListener("click", () => loadEvents());
	byId("events-prev")?.addEventListener("click", () => {
		loadEvents(Math.max(0, state.offset - state.limit));
	});
	byId("events-next")?.addEventListener("click", () => {
		if (!state.hasMore) return;
		loadEvents(state.offset + state.limit);
	});
	byId("export-button")?.addEventListener("click", exportEvents);
	byId("profile-button")?.addEventListener("click", () => showToast("Teacher account controls are not part of this prototype"));

	document.querySelectorAll(".nav-link").forEach((link) => {
		link.addEventListener("click", () => document.querySelectorAll(".nav-link").forEach((item) => item.classList.toggle("active", item === link)));
	});

	const form = byId("classify-form");
	form?.addEventListener("submit", async (event) => {
		event.preventDefault();
		if (state.busy) return;
		setBusy(true);
		setText("inference-state", "Running");
		setState("inference-state", "loading");
		setIntegrationStatus("integration-classification", "Uploading WAV to backend", "loading");
		setText("inference-message", "Sending the selected WAV to POST /api/v1/classify…");
		byId("inference-result").hidden = true;
		try {
			const file = byId("classify-file")?.files?.[0];
			const result = await classifyAudioFile(file, fetch, state.baseUrl);
			if (result.ok) {
				state.lastInference = result;
				setText("inference-state", "Complete");
				setState("inference-state", "ok");
				setText(
					"inference-message",
					result.source === "experimental_model"
						? "Actual inference completed with an experimental model; it has no held-out evaluation."
						: "Actual inference completed using the loaded model artifact.",
				);
				setText("inference-class", result.classification);
				setText(
					"inference-probability",
					result.classProbability === null
						? "Not returned by this model"
						: `${(result.classProbability * 100).toFixed(1)}% (uncalibrated predict_proba)`,
				);
				setText(
					"inference-model",
					result.source === "experimental_model" ? "Experimental; not evaluated" : "Held-out evaluated baseline",
				);
				setText("inference-observed", formatTimestamp(result.observedAt));
				byId("inference-result").hidden = false;
				setIntegrationStatus("integration-classification", `Complete · ${result.classification}`, "ok");
				renderLatest();
				showToast("Actual model inference completed");
			} else {
				setText("inference-state", result.state === "model-unavailable" ? "Model unavailable" : "Failed");
				setState("inference-state", result.state === "model-unavailable" ? "warn" : "error");
				setIntegrationStatus("integration-classification", result.message, "error");
				setText("inference-message", result.message);
				byId("inference-result").hidden = true;
			}
		} catch (error) {
			setText("inference-state", "Failed");
			setState("inference-state", "error");
			setIntegrationStatus("integration-classification", "Classification request failed", "error");
			setText("inference-message", error?.message || "An unexpected error occurred while running inference.");
			byId("inference-result").hidden = true;
			showToast("Model inference failed");
		} finally {
			setBusy(false);
		}
	});
}

function initialize() {
	setText("current-date", new Intl.DateTimeFormat("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
		year: "numeric",
	}).format(new Date()).toUpperCase());
	setText("health-api-url", state.baseUrl);
	initializeTabs();
	initializeControls();
	updateEventsFooter();
	loadDashboard();
	startDashboardTimers();
	window.addEventListener("pagehide", () => {
		pageActive = false;
		stopDashboardTimers();
	});
	window.addEventListener("pageshow", () => {
		pageActive = true;
		startDashboardTimers();
	});
	document.addEventListener("visibilitychange", () => {
		if (document.hidden) {
			stopDashboardTimers();
			return;
		}
		startDashboardTimers();
		loadDashboard({ quiet: true });
	});
}

function stopDashboardTimers() {
	if (refreshTimer !== null) clearInterval(refreshTimer);
	if (freshnessTimer !== null) clearInterval(freshnessTimer);
	refreshTimer = null;
	freshnessTimer = null;
}

function startDashboardTimers() {
	if (!pageActive || document.hidden || refreshTimer !== null) return;
	refreshTimer = setInterval(() => loadDashboard({ quiet: true }), REFRESH_INTERVAL_MS);
	freshnessTimer = setInterval(() => {
		updateLastUpdated();
		updateEventsFooter();
	}, 15000);
}

if (typeof document !== "undefined") initialize();
