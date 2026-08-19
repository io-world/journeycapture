# Building the Windows executable

PyInstaller bundles the host platform's Python interpreter and native DLLs — it does not
cross-compile. This build must run on a real Windows machine (or a `windows-latest`
GitHub Actions runner). All commands below are PowerShell, run on Windows.

## 0. Get the code onto the Windows machine

This repo has no git remote configured yet, so copy the project folder over by
whatever means is convenient (USB drive, network share, zip + transfer, etc.) — the
whole `JourneyCapture` directory except `.venv/` if it exists. Then open PowerShell
and `cd` into it:

```powershell
cd C:\path\to\JourneyCapture
```

## 1. Install prerequisites

- **Python 3.11+**: not strictly required up front — `uv` can download and manage it
  for you — but having it doesn't hurt.
- **uv**: install if not already present:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Then restart the PowerShell window so `uv` is on `PATH`.

## 2. Install dependencies

```powershell
uv sync
```

This creates `.venv` and installs everything from `pyproject.toml`/`uv.lock`, including
the `pyinstaller` dev dependency.

## 3. (Optional but recommended) Run the test suite first

```powershell
uv run pytest -q
```

All 24 tests should pass — they run cross-platform with `mss`/`pynput` mocked, so this
is a good sanity check that the checkout is intact before spending time on a build.

## 4. Build the executable

```powershell
uv run pyinstaller --onefile --console --name journeycapture packaging/run.py
```

- `--console` (not `--windowed`) is intentional for the first build, so stdout/stderr
  are visible if something goes wrong at startup. Switch to `--windowed` later once
  file logging (`journeycapture.log`) has been proven sufficient on its own.
- This produces `dist\journeycapture.exe`, plus a `build\` scratch directory and a
  generated `journeycapture.spec` in the repo root — both are gitignored/disposable.

## 5. Verify the build picked up native dependencies correctly

Run the exe once (see step 6 for config setup first) and exercise `/screenshot`,
`/mouse/*`, and `/keyboard/*`. `pynput` ships a PyInstaller hook in recent versions and
should Just Work; `mss` needs no special hook (pure `ctypes` against `user32`/`gdi32`).
If either mouse/keyboard control or screenshots fail with an import error at runtime,
add the missing module explicitly:

```powershell
uv run pyinstaller --onefile --console --name journeycapture --hidden-import <module> packaging/run.py
```

## 6. Set up config.json next to the exe

```powershell
Copy-Item config.example.json dist\config.json
notepad dist\config.json
```

Edit it: set a real, long random `api_key`, and put your controller machine's IP(s) in
`allowed_ips`. The server will refuse to start with the placeholder key or an empty
allowlist — this is deliberate.

## 7. Run it

```powershell
cd dist
.\journeycapture.exe
```

Check for a Windows Firewall prompt on first launch (allow it if you want remote
machines to reach it), and confirm `journeycapture.log` is being written next to the
exe.

## 8. Save the spec for reproducible future builds

Once the `--hidden-import` flags (if any) are dialed in, save the final PyInstaller
command into `packaging/journeycapture.spec` so future builds are one command:

```powershell
Move-Item journeycapture.spec packaging\journeycapture.spec -Force
uv run pyinstaller packaging\journeycapture.spec
```

## Next: functional testing

The build succeeding doesn't mean mouse/keyboard/screenshot behavior is correct —
walk through [WINDOWS_SMOKE_TEST.md](WINDOWS_SMOKE_TEST.md) next.

## Known friction

A onefile exe that opens a listening port and drives mouse/keyboard matches the
heuristic signature of a RAT. Expect Windows Defender/AV flags and a first-run Firewall
prompt. Code-signing and/or AV exclusions may be needed for real deployment — this is
not something the Python code can fix.

## Optional: CI builds instead of a personal Windows box

A `windows-latest` GitHub Actions workflow running the same `uv sync` +
`pyinstaller` steps and uploading the exe as a build artifact removes the need to do
this manually on every release. Not set up yet (this repo has no git remote) — ask if
you want one added later.
