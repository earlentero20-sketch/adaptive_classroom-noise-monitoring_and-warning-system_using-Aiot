# SONIQ Backend on a Private LAN

The backend defaults to `127.0.0.1:8000`, which is reachable only from the
Windows computer running it. For the ESP32 event endpoint, configure a private
LAN listener. This prototype has no application authentication, so keep access
on a trusted private network. Do not create router port forwarding or expose
port 8000 to the public internet.

## Find the Windows computer's LAN IPv4 address

On the Windows computer, run:

```powershell
ipconfig
```

Find the active Wi-Fi or Ethernet adapter and note its **IPv4 Address**, for
example `[PRIVATE_LAN_IPV4]`. Do not use `127.0.0.1`; that address refers to the
ESP32 itself when used from the ESP32. Avoid VPN, virtual adapter, and
`169.254.*` addresses. Ensure the ESP32 joins the same trusted LAN/subnet and
that Wi-Fi client isolation or a guest network is not blocking device-to-PC
traffic.

## Configure and start the backend

Set these variables in the PowerShell process that starts the server:

```powershell
$env:BACKEND_HOST = "0.0.0.0"
$env:BACKEND_PORT = "8000"
python -m backend.app
```

`0.0.0.0` listens on all local IPv4 interfaces. For a narrower bind, set
`BACKEND_HOST` to the computer's private LAN IPv4 address (for example
`[PRIVATE_LAN_IPV4]`). The backend rejects public IPv4 bind addresses. The port is
configurable from 1 through 65535 and defaults to `8000`.

Check from the same computer:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://[PRIVATE_LAN_IPV4]:8000/health
```

Replace `[PRIVATE_LAN_IPV4]` with the active adapter address. For a custom backend
port, use that port in both URLs. A successful health response verifies the
HTTP listener only; it does not prove PostgreSQL, warning readiness, or sensor
connectivity.

## Windows Firewall

If Windows Firewall blocks inbound connections, open the backend TCP port only
for the **Private** profile and the local subnet. Run PowerShell as
Administrator:

```powershell
New-NetFirewallRule `
  -DisplayName "SONIQ backend private LAN" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8000 `
  -RemoteAddress LocalSubnet `
  -Profile Private
```

Change `8000` if `BACKEND_PORT` differs. Confirm the active Windows network is
classified as **Private** only when appropriate for that trusted network. Do
not enable this rule for the Public profile or configure router port forwarding.
Remove the rule when LAN access is no longer needed:

```powershell
Remove-NetFirewallRule -DisplayName "SONIQ backend private LAN"
```

## Configure the ESP32 target address

In `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino`, set
`SERVER_URL` to the Windows computer's private IPv4 address and backend port,
keeping the existing event route. For example:

```cpp
const char* SERVER_URL = "http://[PRIVATE_LAN_IPV4]:8000/api/v1/events";
```

Replace the example address with the active Windows adapter IPv4 address.
Keep `WIFI_SSID` and `WIFI_PASSWORD` set for the same trusted LAN and keep
credentials private. The sketch's current `[PRIVATE_LAN_IPV4]` is only a sample
address; it must match the actual computer. Recompile and upload the sketch,
then check its Serial Monitor for a successful HTTP response.

The existing `/api/v1/events` endpoint can accept the firmware's event POST
when the listener and firewall permit it. `/api/v1/classify` intentionally
remains loopback-client-only. Browser CORS also remains restricted to loopback
origins, so opening the dashboard from another LAN device is not enabled by
this change. Network exposure, authentication, audio transport, and hardware
behavior are outside this connectivity step.
