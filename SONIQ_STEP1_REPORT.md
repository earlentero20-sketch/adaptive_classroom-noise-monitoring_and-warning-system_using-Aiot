# SONIQ Step 1 — Backend LAN Connectivity Repair

**Date:** 2026-11-09  
**Status:** Code and documentation updated; runtime and LAN behavior **NOT TESTED** because the available Python executable cannot run in this environment and no second LAN client is available.

## Binding configuration

- **Previous:** `BACKEND_HOST` defaulted to `127.0.0.1`; `main()` rejected every non-loopback address. `BACKEND_PORT` defaulted to `8000`.
- **New:** `BACKEND_HOST` still defaults to `127.0.0.1`. It now accepts loopback, `0.0.0.0`, or an RFC1918 private IPv4 address, and rejects public IPv4 addresses. `BACKEND_PORT` remains configurable from `1` to `65535`, default `8000`.
- **Routes/formats:** No route, request, response, or database format was changed. `/api/v1/classify` retains its loopback-client restriction; LAN connectivity is for the existing event endpoint and health route.

## LAN access

1. Run `ipconfig` on the Windows host and find the active Wi-Fi/Ethernet adapter's IPv4 Address, such as `[PRIVATE_LAN_IPV4]`.
2. Set `BACKEND_HOST=0.0.0.0` (or the specific private IPv4) and `BACKEND_PORT=8000` in the backend process environment, then start `python -m backend.app`.
3. Set the firmware `SERVER_URL` to `http://<Windows-LAN-IPv4>:8000/api/v1/events`. The SSID/password must connect the ESP32 to the same trusted LAN. The sketch was not modified.
4. If needed, add an inbound Windows Firewall rule for TCP 8000, Private profile, and `LocalSubnet`, as documented in [`docs/LAN_CONNECTIVITY.md`](docs/LAN_CONNECTIVITY.md). Remove the rule when no longer needed. Do not enable a Public profile rule or router port forwarding.

The detailed commands and constraints are in [`docs/LAN_CONNECTIVITY.md`](docs/LAN_CONNECTIVITY.md). The backend has no application authentication, so this is intended for a trusted private LAN only. LAN browser dashboard access remains restricted by the existing loopback-only CORS allowlist.

## Files modified

- `backend/app.py` — allow private IPv4 and wildcard listener configuration while preserving loopback default and port validation.
- `backend/tests/test_app.py` — replace the old test expecting wildcard rejection with tests for LAN bind acceptance and public address rejection.
- `.env.example` — document `BACKEND_HOST` and `BACKEND_PORT` defaults.
- `docs/INTERFACE_CONTRACT.md` — document the new configurable LAN listener limits.
- `docs/INTEGRATION_PLAN.md` — clarify the loopback default and opt-in private-LAN event listener.
- `docs/LAN_CONNECTIVITY.md` — Windows IP, startup, firewall, and firmware URL instructions.
- `SONIQ_STEP1_REPORT.md` — this report.

No firmware behavior, API route/response, model, database, or warning logic was changed.

## Tests performed

- **Code review:** startup host/port validation and firmware's existing `SERVER_URL` reviewed.
- **Unit tests:** **NOT TESTED.** Attempting Python execution earlier in this workspace failed: the Windows Store alias could not run, and `ml/.venv` references a missing Python installation under a different Windows user. The targeted tests were updated but not executed.
- **Backend startup/listening:** **NOT TESTED** for the same runtime limitation.
- **Localhost health:** **NOT TESTED**.
- **LAN access from another device:** **NOT TESTED**; no second device/network test was available.
- **Existing endpoint access over LAN:** **NOT TESTED**. Source inspection confirms the event route remains registered; `/api/v1/classify` deliberately denies non-loopback clients.
- **Windows Firewall:** no rule was created or changed. The report provides a scoped command for the operator to run if needed.

## Remaining blockers

- Install/use a valid Python environment and run `python -B -m unittest backend.tests.test_app -v` and the broader backend tests.
- Configure PostgreSQL and run the backend to verify local health.
- Confirm the actual Windows LAN IPv4, same-subnet reachability, Windows network profile/firewall, and ESP32 HTTP response on the target network.
- Keep router port forwarding disabled; public network exposure is not supported.
