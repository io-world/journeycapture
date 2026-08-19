# Manual smoke test (Windows only)

These checks require a real Windows desktop session and cannot be automated from macOS.

1. Copy `config.example.json` to `config.json` next to `journeycapture.exe`, set a real
   `api_key`, and add your controller machine's IP to `allowed_ips`.
2. Launch `journeycapture.exe`. Confirm it binds the configured port and writes to
   `journeycapture.log`.
3. `GET /health` with the `X-API-Key` header set correctly → `200 {"status": "ok", ...}`.
4. `GET /health` with a wrong/missing key → `401`.
5. `GET /health` from a machine/IP not in `allowed_ips` → `403`.
6. `GET /screenshot/monitors` → sane monitor layout for the machine.
7. `GET /screenshot` → capture bytes, open and visually confirm it matches the desktop.
8. `POST /mouse/move` to a known coordinate → confirm the cursor lands there
   (multi-monitor + DPI scaling: coordinates from a screenshot pixel should match where
   the cursor actually goes).
9. `POST /mouse/click` → confirm a click registers where expected.
10. Open Notepad, `POST /keyboard/type` some text → confirm it appears correctly.
11. `POST /keyboard/key` with `{"keys": ["ctrl", "alt", "delete"]}` behaves as an OS-level
    combo (careful — this may lock the session; test last).
12. Confirm UIPI behavior: input to an elevated window is blocked unless
    `journeycapture.exe` itself is run as Administrator.
13. Note any Windows Firewall prompt or antivirus flag on first launch.

Example request from PowerShell:

```powershell
Invoke-RestMethod -Uri "http://<host>:8443/health" -Headers @{ "X-API-Key" = "<key>" }
```
