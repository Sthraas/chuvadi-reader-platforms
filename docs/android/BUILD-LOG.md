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

### 7. First CI run failed — fixed
Run 42131193468: "Install Android SDK packages" failed with NU1301 — the implicit restore used
the Reader's root `nuget.config`, whose dev-only `./localpackages` does not exist in CI. (The
sandbox workspace had not copied that file, so it didn't show locally.) Fix: restore first with
`--configfile ci/nuget.config`, then `InstallAndroidDependencies --no-restore`; the Debug x86_64
build (which re-restores for its RID) gets `-p:RestoreConfigFile=ci/nuget.config`. Sandbox
workspace now includes the root `nuget.config`, so it matches CI; the CI steps were re-run
locally and pass.

### 8. Release package (sandbox)
`dotnet publish -c Release -f net10.0-android` → `in.chuvadi.reader-Signed.aab` 53.9 MB,
`.apk` 54.3 MB (debug-key signed), 0 warnings.

### 9. Tablet layout (Portal & Android 12d–12f) — host CSS only, pending A-03 (later removed, see 13)
- `wwwroot/android.js` sets `html[data-form-factor]` = tablet (shorter side ≥ 600 dp) / phone,
  updated on resize (split screen, foldables).
- `wwwroot/android.css`, tablet block: rails 72 / 72 / 60 (View folds below 1000 px, as the Ui
  already does), 48 px targets, mode verbs under icons, no hover-expand, top bar 52 px with the
  command field as a search icon, no theme toggle or status bar; Home via the wordmark.
- To be checked against the emulator tablet screenshots from CI.

### 10. Existing-file proposal started — `EXISTING-FILE-PROPOSAL.md`
P-01 (individual chuvadi-pdf packages in Core) tried in the sandbox workspace only (the Reader
repo is untouched): Core + Ui + tests build with 0 warnings, 161/161 Reader tests pass.

## 2026-11-06 — Session 2: Foundation kit, platform services, printing, icon, honest CI

### 11. Scope and decisions received (coordinator)
A-01…A-09 decided (DECISIONS.md). The phone/tablet look moved to the Mobile app UI chat
(`platform/mobile-ui`); this chat owns the host, platform services, packaging, CI and integration.

### 12. Built on Foundation's kit (`platform/foundation` @ 5505d5e)
- The build workspace and CI now use the pinned Foundation snapshot: chuvadi-reader c7b9e44
  unchanged + `ChuvadiReader.Platform` (contracts) + `ChuvadiReader.Hosting` (kit).
- `MauiProgram` calls `AddChuvadiReader(AppStateLifetime.Process)`; the host's own copy of the
  service list and its no-op services are gone (kit defaults: `IUiScale`, `IWindowControls`).
- New host implementations: `AndroidPlatformInfo` (Phone/Tablet from sw600dp, re-evaluated on every
  configuration change), `AndroidAppPaths`, `AndroidLifecycle` (Suspending on pause, Resumed,
  back gesture offered to the Ui first), `DocumentLinks` + `AndroidFileWriteBack` + SAF
  `AndroidFilePicker` (A-02), `AndroidClipboard` (text + image) and `AndroidShare` through an own
  read-only `SharedFileProvider`, `ActivityResults` for system pickers.
- `GlobalUsings.cs`: MAUI's `IFilePicker`/`IClipboard`/`IShare` names clash with Chuvadi's.

### 13. A-03 applied
Removed `android.js` and every host CSS rule keyed on Ui classes; `android.css` only pads for the
system bars.

### 14. Printing (A-04) — `AndroidPrintService`
Android `PrintManager` with the PDF as-is; page ranges / passwords via chuvadi-pdf
`PageOperations.Assemble` into a temporary PDF (deleted after hand-off). Outcome from the print job
state (printed / cancelled / failed).

### 15. App icon draft (A-09)
Rendered `Brand Assets.dc.html`, measured where Chrome places ச (Tiro Tamil 635 px on the 1024 tile:
ink box 307,271–717,611), converted the glyph to a path with fontTools (asset generation only;
nothing shipped) and wrote: `icon-master.svg`, `icon-store-square.svg` → `play-store-icon-512.png`,
adaptive `appicon.svg` (background) + `appicon_foreground.svg` + `appicon_monochrome.svg`,
`make-icons.py`, `compare-with-handout.png`. Scale check: 0.6337 px/unit = 635 px / 1000 UPM.

### 16. CI was a false green — fixed
Run 42131731200 passed all four emulators, but the evidence showed: **phone — blank screen at 30 s;
tablet — Ui rendered without its component styles**. Causes found:
1. `index.html` did not link `ChuvadiReader.Android.styles.css`, the host bundle that imports the
   Ui's scoped component styles (204 KB). Linked now.
2. WebView console: "Blazor.start() failed: Blazor has already started" — MAUI starts Blazor itself,
   so the script needs `autostart="false"` (the WPF host differs). Fixed.
   (The Mac host's `index.html` has the same tag without `autostart="false"`; reported to the coordinator.)
3. The smoke test only checked "no crash". It now waits up to 120 s for the Ui's own text in the
   accessibility tree, re-checks after rotation, keeps timed screenshots and UI dumps, and fails on
   any WebView console error.
The phone's blank screen has no error in logcat; whether fixes 1–2 cure it is what the next run
shows (no KVM in the sandbox, so emulators run only in CI).

### 17. First honest emulator run (42133970009) — what it showed
- **The Ui renders on phone and tablet with its full styling** (fix 16.1 + 16.2 worked). No crashes,
  no WebView console errors.
- All four jobs still failed, for test reasons: phone API 36 installed before Android finished
  booting (package manager "Broken pipe") — the script now waits for `sys.boot_completed` and retries
  the install; the other three looked for the text "Read", but the mode buttons read "Read 1",
  "Mark 2"… (label + key) — markers corrected and checked against the real UI dumps.
- **Real issue found: the system bars overlapped the app** (clock over the wordmark, gesture handle
  over the status line). Android 15 is always edge-to-edge and the WebView ignores CSS safe-area
  insets. Fixed natively in `SystemBars.cs`: the root view is padded by the system-bar, cut-out and
  keyboard insets, the margin takes the saved theme's page colour (Windows host's mapping), and the
  bar icons switch light/dark. The CSS padding and `viewport-fit=cover` were removed.
- Seen, not Android's to fix: window buttons still drawn (until the Ui reads
  `ShellChrome.Buttons = None`, A-03); the phone shows the desktop shell squeezed (Mobile app UI
  chat); "Good morning, U0_a209" (A-10); Home lists sample recent/pinned/watched entries
  (`patient_chart.pdf`, "8 documents found") on a fresh install — reported to the coordinator.
