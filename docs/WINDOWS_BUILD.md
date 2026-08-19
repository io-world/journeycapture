# Building the Windows executable

PyInstaller bundles the host platform's Python interpreter and native DLLs — it does not
cross-compile. This build must run on a real Windows machine (or a `windows-latest`
GitHub Actions runner). All commands below are PowerShell, run on Windows.

## 0. Get the code onto the Windows machine

```powershell
git clone https://github.com/io-world/journeycapture.git
cd journeycapture
```

(Or `git pull` if you already have a checkout there.)

## 1. One-shot build

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

This does everything through step 6 below in one command: installs `uv` if it's
missing, runs `uv sync`, runs the test suite (`uv run pytest -q`, aborting the build on
failure — pass `-SkipTests` to bypass), builds `dist\journeycapture-<version>.exe` with
PyInstaller (version read from `pyproject.toml` via
`importlib.metadata.version("journeycapture")`, so the exe name always matches the
installed package version), and copies `config.example.json` → `dist\config.json` if
one isn't already there. Pass `-OpenDist` to have it open `dist\` in Explorer when
done.

Skip to [step 6](#6-set-up-configjson-next-to-the-exe) to configure and run it. The
manual steps below are what the script automates — use them if you need to customize
the PyInstaller invocation (e.g. adding a `--hidden-import`).

## 2. Install prerequisites (manual)

- **Python 3.11+**: not strictly required up front — `uv` can download and manage it
  for you — but having it doesn't hurt.
- **uv**: install if not already present:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Then restart the PowerShell window so `uv` is on `PATH`.

## 3. Install dependencies (manual)

```powershell
uv sync
```

This creates `.venv` and installs everything from `pyproject.toml`/`uv.lock`, including
the `pyinstaller` dev dependency.

## 4. Run the test suite first (manual)

```powershell
uv run pytest -q
```

All 24 tests should pass — they run cross-platform with `mss`/`pynput` mocked, so this
is a good sanity check that the checkout is intact before spending time on a build.

## 5. Build the executable (manual)

```powershell
uv run pyinstaller --onefile --console --name journeycapture packaging/run.py
```

- `--console` (not `--windowed`) is intentional for the first build, so stdout/stderr
  are visible if something goes wrong at startup. Switch to `--windowed` later once
  file logging (`journeycapture.log`) has been proven sufficient on its own.
- This produces `dist\journeycapture.exe`, plus a `build\` scratch directory and a
  generated `journeycapture.spec` in the repo root — both are gitignored/disposable.
- If mouse/keyboard control or screenshots fail with an import error at runtime,
  `pynput` ships its own PyInstaller hook and should Just Work; `mss` needs no special
  hook (pure `ctypes` against `user32`/`gdi32`). Otherwise add the missing module
  explicitly with `--hidden-import <module>`.

## 6. Set up config.json next to the exe

`build_windows.ps1` does this for you if `dist\config.json` doesn't already exist. To
do it by hand:

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
.\journeycapture-<version>.exe
```

Check for a Windows Firewall prompt on first launch (allow it if you want remote
machines to reach it), and confirm `journeycapture.log` is being written next to the
exe.

## 8. Publish a release (optional)

```powershell
gh release create v<version> "dist\journeycapture-<version>.exe" --title v<version> --notes "..."
```

**Remember to rebuild and publish a new release after any change to
`input_control.py`, `capture.py`, or other runtime code** — a published release is a
frozen artifact; pulling the latest source on the Windows box doesn't update an
already-built/running `.exe`, and re-running `build_windows.ps1` doesn't re-publish the
release on its own.

## Next: functional testing

The build succeeding doesn't mean mouse/keyboard/screenshot behavior is correct —
walk through [WINDOWS_SMOKE_TEST.md](WINDOWS_SMOKE_TEST.md) next, or use the
`scripts/*.py` live-testing scripts from a controller machine (see `CLAUDE.md`).

## Known friction

A onefile exe that opens a listening port and drives mouse/keyboard matches the
heuristic signature of a RAT. Expect Windows Defender/AV flags and a first-run Firewall
prompt. Code-signing and/or AV exclusions may be needed for real deployment — this is
not something the Python code can fix.

## Optional: CI builds instead of a personal Windows box

A `windows-latest` GitHub Actions workflow running the same `uv sync` +
`build_windows.ps1` steps and uploading the exe as a build artifact (or publishing a
release directly) removes the need to do this manually on every release. Not set up
yet — ask if you want one added.
