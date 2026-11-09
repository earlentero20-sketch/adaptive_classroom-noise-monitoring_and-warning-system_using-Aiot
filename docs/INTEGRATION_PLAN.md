# Proposed SONIQ event integration plan

**Status:** proposal only; no new transport, endpoint, firmware behavior, or
event schema has been implemented. Approval from Jann, Earl, Romeo, Audey, and
the project lead is required before architectural work begins.

## Current gap

The ESP32 currently posts an event with no classification and no sound-level
measurement. Its local RMS value is not calibrated dB SPL. The host-side
`POST /api/v1/classify` route accepts one complete PCM WAV and returns an ML
label, but it does not create or persist an event and is restricted to
loopback clients. The `/api/v1/events` route independently validates the event,
applies warning policy, and persists it. The dashboard reads persisted events
and can submit a WAV for separate classification. These paths are not currently
joined into one lifecycle.

## Candidate local demonstration lifecycle

1. The ESP32 captures a bounded audio window and transfers its PCM samples,
   device ID, and capture time to a host companion over USB serial. This is a
   proposed transport; Jann must confirm memory, throughput, framing, and
   timestamp behavior before implementation.
2. The host companion wraps the samples in a complete PCM WAV and submits them
   to the existing loopback-only `/api/v1/classify` route. The format and window
   must match the artifact's preprocessing metadata. Experimental model
   artifacts are present in this checkout, but their metadata marks them as
   full-fit runs without held-out evaluation and the data review as incomplete.
   They have not been loaded or validated in this environment and are not
   evidence of an approved or evaluated classifier.
3. The companion pairs the class result with an independent calibrated dB SPL
   measurement and its observation timestamp. Raw I2S/RMS amplitude must never
   be represented as dB SPL. A missing, uncalibrated, invalid, or older than
   30-second measurement fails closed.
4. Until Earl and the project lead approve a confidence rule, the companion
   must not convert an uncalibrated `model_confidence` probability into the
   event contract's `classification.confident=true`. With that gate false,
   warning decisions remain off.
5. The companion submits one `/api/v1/events` request with a unique event ID,
   the exact model label, classification timestamp, independent calibrated
   sound reading, and sensor status. The backend applies the existing
   class-specific rule: only a confident `Student Conversation` with a valid
   calibrated dB SPL reading strictly greater than 75 dB and no more than
   30 seconds old can trigger a warning. `Teacher Discussion` never triggers.
6. The backend commits the event before returning success. It returns the
   stored event and warning decision; duplicate IDs remain conflicts. The
   dashboard displays the persisted event through its existing event-history
   route.
7. Any physical buzzer response would require a separately approved
   authorization path back to the ESP32, loss-of-connection behavior, and
   hardware safety tests. The current firmware keeps physical buzzer operation
   disabled; this proposal does not change that behavior.

The backend defaults to loopback. Step 1 adds an opt-in private IPv4 listener
for the existing firmware event endpoint; see `LAN_CONNECTIVITY.md` for the
host firewall and ESP32 address setup. This enables LAN event posts only. The
host audio companion should continue using loopback, `/api/v1/classify` remains
loopback-client-only, and this change does not implement the proposed audio
transport or authorize broader network deployment. Any network access beyond
a trusted private LAN requires a separately approved authenticated design.

## Decisions required before implementation

- **Jann:** confirm USB serial audio framing, supported sample format/window,
  buffer limits, device timestamps, and whether returning an authorization
  over serial is feasible.
- **Earl:** provide a trusted compatible model artifact and its preprocessing
  metadata; define the classification-to-event mapping and obtain approval for
  any confidence rule. Identify a calibrated independent dB SPL source.
- **Romeo:** confirm the event remains the persistence boundary, transaction
  behavior, duplicate handling, and the local companion's API interaction.
- **Audey:** confirm the current persisted-event fields are sufficient for
  history and error display; do not add inferred fields.
- **Project lead:** approve the transport and end-to-end lifecycle, privacy
  handling for audio, retention, and any hardware warning behavior.

Until these decisions are approved, the current interfaces remain separate and
no complete hardware-to-model-to-event-to-warning path should be claimed.
