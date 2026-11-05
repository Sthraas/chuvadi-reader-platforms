# Android — build log

Dated, step-by-step record of what was done, why, the commands, and the results.

## 2026-11-06 — Session 1: host project, first builds, CI

### 1. Read the inputs
- Kickoff + rulebook, the library coordinator's package report (6 Nov), `docs/coordination/
  DESIGN-NOTE.md`, `docs/design-handoff/README.md`, and `Portal & Android.dc.html` (rendered in
  headless Chrome — test tooling only) for the tablet (12d–12f) and phone (12g–12j) frames.
- Read `chuvadi-reader` at `c7b9e44` (chuvadi-pdf 3.31.1 + Chuvadi.Fonts 1.0.0): solution,
  `Directory.Build.*`, `ci/nuget.config` + `ci/packages`, the Windows host and every platform
  interface in Core (`IFilePicker`, `IPrintService`, `IImageClipboard`, `IWindowControls`,
  `IUiScale`, `IExternalLinks`, `IAppStorage`, `IAppReadySignal`).
- Findings that shape Android (all in DECISIONS.md): Core is path-based throughout (A-02); the
  title bar always renders window controls (A-03); Core references the umbrella `Chuvadi.Pdf` and
  Docs 1.1.0 / Sheets 1.1.2 (A-06); `theme.js` and the ~45-line service list are per host (A-06 #4).
  Pinch-zoom on the canvas already exists in the Ui (`reader.js`, touch handlers), so the host only
  has to stop the WebView zooming itself.

### 2. Branch
`platform/android` from `main` (`1d5ff21`, design handout). Commits authored as Arun.

### 3. Toolchain in the sandbox
```bash
curl -sSfL -o dotnet-install.sh https://dot.net/v1/dotnet-install.sh
bash dotnet-install.sh --channel 10.0 --install-dir /opt/dotnet     # → SDK 10.0.403
dotnet workload install maui-android                                 # Android packs 36.1.118, MAUI 10.0.110
USER=root dotnet build -t:InstallAndroidDependencies -f net10.0-android \
  src/ChuvadiReader.Android/ChuvadiReader.Android.csproj \
  -p:AndroidSdkDirectory=/home/claude/androidsdk -p:AcceptAndroidSDKLicenses=True
```
Note: the SDK installer fails with "UserName must have a valid value" when `USER` is unset.

### 4. Host project `src/ChuvadiReader.Android` (all new files)
- `ChuvadiReader.Android.csproj` — `net10.0-android`, MAUI, min API 35, `TreatWarningsAsErrors`,
  Release packages `aab;apk`. Only Microsoft's MAUI + BlazorWebView packages. Application id
  placeholder (A-01).
- `MauiProgram.cs` — the same Core services, same order, as the Windows host + Android services.
- `App.cs` — one window, one `BlazorWebView` with `ChuvadiReader.Ui.App`; WebView zoom off (the
  Ui's canvas pinch stays), no file/content access from the page, `TextZoom = 100`.
- `Platforms/Android/MainActivity.cs` — SingleTask; handles every configuration change so
  rotation, split screen, resize and keyboard never recreate the activity; Open-with (VIEW) and
  Share (SEND) for PDF / DOCX / XLSX.
- `Platforms/Android/AndroidManifest.xml` — no permissions; no backup / device transfer
  (`data_extraction_rules.xml`); predictive back enabled; private `ClipProvider`.
- `Platform/DocumentImport.cs` — streams a `content://` document into a private working copy and
  opens it under its real name (or drops it on the Bench when that is open, like a desktop drop).
- `Platform/AndroidFilePicker.cs` — open pickers via MAUI's `FilePicker` (SAF). Save / folder
  pickers return null until A-02.
- `Platform/AndroidImageClipboard.cs` + `Platforms/Android/ClipProvider.cs` — snapshot to
  clipboard through a read-only, non-exported provider of our own (no AndroidX FileProvider).
- `Platform/AndroidAppStorage.cs` — settings JSON, same format as Windows, atomic replace,
  source-generated JSON (trim-safe).
- `Platform/AndroidHostServices.cs` — `IUiScale` (Ui's CSS zoom path), `IExternalLinks`
  (Launcher), `IWindowControls` (no-op), `IPrintService` (unavailable until A-04).
- `wwwroot/index.html` (same as Windows + `viewport-fit=cover`), `wwwroot/theme.js` (copy of the
  Windows host's), `wwwroot/android.css` (window controls hidden — A-03; safe-area padding).
- Icon / splash: the Windows `chuvadi.ico` 256 px frame as PNG (A-09 for the real master).

### 5. Build
```bash
# workspace = chuvadi-reader @ c7b9e44 with src/ChuvadiReader.Android copied in
dotnet restore src/ChuvadiReader.Android/ChuvadiReader.Android.csproj --configfile ci/nuget.config
dotnet build   src/ChuvadiReader.Android/ChuvadiReader.Android.csproj -c Debug
```
Fixed on the way (own code): `IFilePicker` name clash with MAUI's `Microsoft.Maui.Storage.IFilePicker`
(alias); missing `Microsoft.AspNetCore.Components.WebView` using; `Logging.AddDebug` dropped (needs
an extra package); `new Java.Lang.Long(...)` obsolete on API 33+ → `Long.ValueOf`.
**Result: Debug build succeeded, 0 warnings, 0 errors; `in.chuvadi.reader-Signed.apk` produced.**

### 6. CI
`.github/workflows/android.yml`: pinned read-only checkout of chuvadi-reader, build Release
`.aab` + `.apk` and Debug x86_64 `.apk`; emulator smoke test (`docs/android/ci/smoke-test.sh`)
on phone + tablet × API 35 + 36: install, cold start, rotate (activity must not restart), fail on
any crash, upload screenshots + logcat.
