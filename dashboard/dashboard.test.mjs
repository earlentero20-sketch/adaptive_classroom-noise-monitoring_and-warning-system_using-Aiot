import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
	classificationState,
	sensorState,
	soundLevelState,
	soundLevelText,
} from "./dashboard.mjs";

test("classification display preserves the exact backend labels and status", () => {
	assert.equal(classificationState({
		classificationLabel: "Teacher Discussion",
		classificationStatus: "fresh",
	}), "ok");
	assert.equal(classificationState({
		classificationLabel: "Student Conversation",
		classificationStatus: "fresh",
	}), "ok");
	assert.equal(classificationState({
		classificationLabel: "Student Conversation",
		classificationStatus: "stale",
	}), "warn");
	assert.equal(classificationState({
		classificationLabel: null,
		classificationStatus: "unavailable",
	}), "unavailable");
});

test("sound and sensor displays reflect actual measurement state", () => {
	assert.equal(soundLevelText({ soundLevelValue: 76, soundLevelUnit: "dB_SPL" }), "76 dB SPL");
	assert.equal(soundLevelText({ soundLevelValue: 76, soundLevelUnit: null }), "76 (unit unavailable)");
	assert.equal(soundLevelText({ soundLevelValue: null }), "Unavailable");

	assert.equal(soundLevelState({
		soundLevelValue: 76,
		soundLevelUnit: "dB_SPL",
		soundLevelStatus: "fresh",
		soundLevelCalibrated: true,
	}), "ok");
	assert.equal(soundLevelState({
		soundLevelValue: 76,
		soundLevelUnit: "dB_SPL",
		soundLevelStatus: "fresh",
		soundLevelCalibrated: false,
	}), "warn");
	assert.equal(soundLevelState({
		soundLevelValue: 76,
		soundLevelUnit: "dB_SPL",
		soundLevelStatus: "stale",
		soundLevelCalibrated: true,
	}), "warn");
	assert.equal(soundLevelState({
		soundLevelValue: null,
		soundLevelUnit: "dB_SPL",
		soundLevelStatus: "unavailable",
		soundLevelCalibrated: false,
	}), "unavailable");

	assert.equal(sensorState("online"), "ok");
	assert.equal(sensorState("offline"), "error");
	assert.equal(sensorState("unknown"), "unknown");
});

test("dashboard exposes explicit loading, empty, error, unavailable, and unknown states", async () => {
	const script = await readFile(new URL("./dashboard.mjs", import.meta.url), "utf8");
	assert.match(script, /renderEventMessage\("Loading event history…", "loading"\)/);
	assert.match(script, /No events recorded yet\. The backend returned an empty event list\./);
	assert.match(script, /Could not load event history\. Check the backend connection and retry\./);
	assert.match(script, /Event history unavailable — the backend must provide GET \/api\/v1\/events\./);
	assert.match(script, /Unavailable — GET \/api\/v1\/events is not implemented/);
	assert.match(script, /Warning status cannot be determined without an actual event\./);
	assert.match(script, /No actual classification has been received\./);
	assert.match(script, /No sound-level reading is available from the backend\./);
});
