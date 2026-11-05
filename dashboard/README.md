# SONIQ Dashboard

The dashboard is a static HTML/CSS/ES-module application. It has no build step
and no package dependencies.

## Run locally

From the repository root, start the backend in one terminal:

```powershell
python -m backend.app
```

Serve the dashboard from a second terminal on a loopback origin:

```powershell
python -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8001/`.

The backend grants browser CORS access only to loopback origins. Opening
`index.html` as a `file:` URL is not supported for API access.

## API configuration

The dashboard resolves the backend base URL in this order:

1. `window.SONIQ_API_BASE_URL` (injected by a deployment).
2. `<meta name="soniq-api-base" content="...">` in `index.html`.
3. `?api=http://127.0.0.1:8000` on the dashboard URL (local development).
4. `http://127.0.0.1:8000`.

Only `http:` and `https:` URLs without embedded credentials are accepted.
No credentials are stored in the dashboard.

## Current API usage

| Endpoint | Method | Dashboard use |
|---|---|---|
| `/health` | `GET` | Backend reachability and warning-configuration readiness. |
| `/api/v1/classify` | `POST` | User-selected WAV classification. Warning and sound level are not evaluated by this endpoint. |
| `/api/v1/events` | `GET` | Event history. **Not implemented by the current backend.** The dashboard shows an explicit Unavailable state for a 404/405/501 response. |
| `/api/v1/events` | `POST` | Used only by the optional integration-check panel to send an empty contract sample. It is never used to create monitoring data for the overview. |

The overview never invents sound levels, classifications, warning decisions, or
event history. If the backend does not provide a value, the dashboard shows
`Unavailable` or `Unknown`.

## UI states

- **Loading** — requests are in progress.
- **Empty** — the backend returned an empty event list.
- **Error** — a request failed or the response was malformed.
- **Unavailable** — the backend does not provide the required endpoint/data.
- **Stale** — the last successful refresh is older than 60 seconds.
- **Success** — actual backend data is displayed.
- **Unknown** — a warning decision cannot be determined from the available data.

## Files

- `index.html` — dashboard markup and accessible structure.
- `dashboard.mjs` — presentation and UI state management.
- `backend-adapter.mjs` — API validation, request handling, and contract checks.
- `dashboard.css` — dashboard-specific layout and state styles.
- `colors.css` — existing SONIQ visual system.
- `backend-adapter.css` — integration-check panel styles.
- `backend-adapter.test.mjs` — API adapter and contract `node:test` suite.
- `dashboard.test.mjs` — presentation-state and exact-label `node:test` suite.

Run the dashboard tests with:

```powershell
node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

## Backend requirement for event history (owner: Romeo Gutang Jr.)

The dashboard is ready to read event history, but the backend currently has no
read/list route. To complete this integration, the backend needs a read-only
endpoint such as:

```http
GET /api/v1/events?limit=10&offset=0
```

A response shape compatible with the dashboard adapter is:

```json
{
  "schema_version": "1.0",
  "events": [
    {
      "schema_version": "1.0",
      "event_id": "event-unique-id",
      "device_id": "device-unique-id",
      "received_at": "2026-11-05T04:00:00Z",
      "connection_status": { "backend": "online", "sensor": "unknown" },
      "classification": {
        "label": "Teacher Discussion",
        "confident": true,
        "status": "fresh",
        "observed_at": "2026-11-05T04:00:00Z"
      },
      "sound_level": {
        "value": 64.2,
        "unit": "dB_SPL",
        "calibrated": true,
        "status": "fresh",
        "observed_at": "2026-11-05T04:00:00Z"
      },
      "warning": { "triggered": false, "reason": "teacher_discussion" }
    }
  ],
  "pagination": { "total": 42, "has_more": true }
}
```

Each event must use the existing event-response contract and the exact
classification labels `Teacher Discussion` and `Student Conversation`. The
dashboard also accepts a bare JSON array of events; pagination metadata is
optional but recommended.

This contract is a dashboard requirement, not a claim that the endpoint exists.
Romeo should confirm the final route, ordering (newest first), page-size limits,
and pagination field names before the dashboard treats the integration as final.
