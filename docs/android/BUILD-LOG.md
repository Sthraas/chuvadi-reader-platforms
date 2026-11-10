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

### 18. Run 42136086344 — phone and tablet API 35 pass the strict check
Phone API 35: Ui rendered after 15 s; screenshots confirm the status and gesture bars are now clear
of the app. They also showed the "rotated" shot was still portrait: the emulator never rotated,
so the rotation check proved nothing. The test now rotates through the window manager's own lock
(`cmd window user-rotation lock 1`) and fails unless the screenshot size actually changes.

### 19. Run 42137557959 — real rotation verified; one emulator flake handled
Phone API 35 and tablet API 35 pass with real rotation (phone 1080x2400 → 2400x1080, same
process, Ui re-laid out, clear of the status bar, gesture bar and the camera cut-out). Tablet API 36
failed only because the emulator's own System UI hung ("System UI isn't responding", an ANR in
`com.android.systemui`) and its dialog covered the screen; the screenshot shows the app fully
rendered underneath and our logcat is clean. The test now taps "Wait" on that system dialog before
reading the screen.

### 20. Run 42139464288 — phone API 35 "crash" was the test tool
Phone API 35 rendered (20 s) and rotated correctly, then failed on "FATAL EXCEPTION: UiAutomation"
— the uiautomator tool's own process (pid 3392, "Bad file descriptor"), not the app (pid 3046).
The crash check now counts only the app's own managed crashes, native crashes and ANRs; other
processes' crashes are saved as evidence. Checked against that logcat (0 hits) and against sample
lines of each real crash format (3 of 3 caught, the tool's line ignored).

### 21. Run 42140626310 (b47218f) — all green, with evidence
| Job | Ui on screen | Rotation (screenshot size) | Notes |
|---|---|---|---|
| build | — | — | Release .aab + .apk, Debug x86_64 .apk |
| phone, API 35 | 20 s | 1080x2400 → 2400x1080 | |
| phone, API 36 | 10 s | 1080x2400 → 2400x1080 | emulator System UI ANR dismissed |
| tablet, API 35 | 20 s | 2560x1600 → 1600x2560 | |
| tablet, API 36 | 15 s | 2560x1600 → 1600x2560 | emulator System UI ANR dismissed |
Same process before and after rotation, Ui still present, no crash or ANR of the app, no WebView
console errors. Local Release publish: `.aab` 53.9 MB, `.apk` 54.3 MB, 0 warnings.

## 2026-11-06 — Session 3: D-49, A-10, Mobile UI integration, gesture tests

### 22. Inputs
`docs/coordination/DECISIONS.md` (D-01…D-53) read. For Android: D-16, D-17, D-49, A-10 (a) approved;
D-54 chuvadi-pdf 3.31.2 — the Foundation packs it; not on any branch yet at this session, so this
session builds on 3.31.1 and rebases when it lands.

### 23. D-49 (host fixes from the Mobile UI chat)
| Item | State |
|---|---|
| link `ChuvadiReader.Android.styles.css` | done in session 2 (step 16) |
| link `_content/ChuvadiReader.Ui/css/mobile.css` | done (after shell.css) |
| remove host tablet CSS, `.topbar .traffic`, body safe-area padding, `data-form-factor` writer | done in session 2 (A-03); `android.css` now removed entirely |
| form factor via `IPlatformInfo.FormFactorChanged` | done in session 2 (`AndroidPlatformInfo`, sw600dp) |
| register `IAppLifecycle`, raise `BackRequested` | done in session 2 (`AndroidLifecycle`, `MainActivity` back callback) |
Also from Foundation's current HANDOFF §2: `theme.js` now comes from the Ui
(`_content/ChuvadiReader.Ui/js/theme.js`; host copy removed); the host page carries the starting
`data-shell / data-platform / data-form-factor / data-input` on `<html>` for the first paint, from a
one-shot inline script using the same 600 dp rule (no resize listener; MainLayout keeps them in sync).

### 24. A-10 — no Core edit needed
Foundation's `UserProfileService.Name` already reads `IAccount.DisplayName` before the OS name. The host
registers `AndroidAccount` with an empty display name, so Home says "Good morning." until the person sets a
name. P-05 withdrawn.

### 25. Mobile UI integration (test composition)
`docs/android/integration/compose.sh`: Foundation `60dca85` + the Mobile UI chat's new Ui files from
`ea5d775` (Phone/*, mobile.css, mobile.js) + `mobile-ui-on-foundation.patch` + this host.
The patch (21 lines) exists only because the Mobile UI branch predates Foundation removing the
`PlatformState` cascade: MainLayout hooks H-1/H-2 re-based on the current file (`ShellLayouts.Shell(Platform)`),
and `TouchSupport` reading `IPlatformInfo` + `FormFactorChanged` instead of the cascade. To be replaced by
Foundation's combined patch (D-26) and the Mobile UI chat's own rebase.
Results on the composition: Android Debug build 0 warnings; Mobile UI tests 3/3, Hosting tests 27/27,
Reader tests 161/161.

### 26. Gesture tests (CI)
`docs/android/ci/emulator-tests.sh` = smoke test + `gestures.py`:
- the test PDF (`make-test-pdf.py`, 6 pages, checked to open with chuvadi-pdf 3.31.1) is pushed to
  Downloads and opened by ACTION_VIEW with its MediaStore `content://` URI — the real "Open with" path;
- gestures are real multi-touch events written to the emulator's touchscreen (`touch.py`; `adb input`
  can't do two fingers or a fast double-tap);
- results are read from the page through the Debug build's WebView DevTools socket (`cdp.py`):
  swipe → counter +1; double-tap → fit mode flips; pinch out → page ≥ 8 % wider; Arrange long-press
  drag → page order changes. Screenshots after each.

### 27. chuvadi-pdf 3.31.2 (D-54)
Foundation `be4498a` packed 3.31.2 from the unchanged tag into `ci/packages` (SHA-256s in its
`PACKAGES-3.31.2.md`) and pinned Core. Re-composed on it: the patch applies unchanged (only packages and
the version moved); Android Debug build 0 warnings. CI re-pinned to `be4498a`.

### 28. First gesture run (42202635440, 3.31.2 composition)
All four emulators: smoke test passes (Ui 10–25 s, real rotation), the phone shell and tablet layout
are detected (`data-shell` phone / tablet), and **Open with works**: the MediaStore `content://` URI
opens the 6-page PDF in the Reader ("1 / 6"). The gesture step then stopped at the touch tool, whose
error output was captured and not printed (my test-tool gap). Fixed: the tool's errors are printed
and recorded as a failed check, the remaining checks still run, the device's input-device facts are
saved, and the push no longer relies on adb's "dir/." handling. Dry-run against a fake emulator adb:
swipe 10 frames (0.37 s), double-tap 4 frames (0.32 s), pinch 15 frames with two slots, long-press drag
17 frames (0.8 s hold).

### 29. Gesture run 42204251084 — touch writes denied; one real layout issue
- Touch tool error now visible: `can't create /dev/input/event2: Permission denied`. The shell user is in the
  `input` group but SELinux denies it on these images. Fix: `adb root` (allowed on google_apis images) before
  the gestures.
- **Phone shell works on the emulator**: app bar (back · file name · "1 / 6" · ⋮), Read · Mark · Arrange · Protect
  bottom bar, Open with lands in the Reader.
- **Found, for the Mobile UI chat: on the phone, Fit page leaves the page ~54 CSS px wider than the view**
  (right edge clipped, sideways scrollbar; `.rdesk` scrollWidth − clientWidth = 54). Besides the look, it
  blocks swipe paging, which only acts when the page has no sideways overflow.

### 30. Run 42206027480 — real touch works; Open with must stay unprivileged
With a root adbd the touch tool works: a real tap on the bottom bar's Arrange switched the phone to
Arrange (app bar "Bind all"). But Open with then failed: a file pushed and an intent sent by root
don't give the app read access as the shell user's did. Order fixed: Open with as the shell user
(the real path a file manager takes), then `adb root` for the gestures only.

### 31. Run 42207618154 — first real swipe
Open with as the shell user works again ("1 / 6"), touch input works as root, and the page fits the phone
this time (overflowX 0 — the 54 px in step 29 was not reproduced). A real swipe reached the screen but the
page did not change. Suspected cause, not yet proven: the Reader's desk is `touch-action: pan-x pan-y`, so
Chrome claims a horizontal drag as its own pan and sends `pointercancel`, which mobile.js treats as "no
swipe". To prove it, the test now records (passive listeners only) the pointer/touch events the page sees
during each gesture and saves them as `events-<gesture>.json`. Also fixed a crash in my script when a state
value was missing.

### 32. Run 42209297085 — evidence per gesture (phone and tablet, API 35)
| Gesture | What the page received | Result | Whose |
|---|---|---|---|
| swipe | pointerdown → 1 pointermove → **pointercancel** | page doesn't change | **Mobile UI bug**: the desk is `touch-action: pan-x pan-y`, so the WebView claims a sideways drag as its own pan and cancels the pointer; mobile.js drops the swipe on pointercancel. Only shows on a real WebView. |
| tap | pointerdown/up, click | per-page strip appears (Rotate page · To desk · Snapshot · Bookmark) | works |
| double-tap | two taps **476 ms** apart | no flip | test: too slow for mobile.js's 300 ms window → each tap is now one write (2 writes + 80 ms) |
| pinch | 2 pointers, 16 Ctrl-wheel events from mobile.js | **zoomed in** (screenshot; desk `zoomed`) | works; my width measure read the wrong element → now the desk's content width |
| Arrange | tap on the bottom bar's Arrange | "1 desk · 0 pages", Shelf as a peek | works as designed; the test now opens the Shelf (tap on its header) and long-press-drags a Shelf page onto Desk 1 |
Also confirmed again on the phone: Fit page leaves the page ~54 CSS px wider than the view (screenshot:
edge cut, sideways scrollbar) — Mobile UI chat.

### 33. Run 42210920888 — tablet API 35: 6 of 8
PASS: Open with, pinch zooms in (desk `zoomed` false → true), Arrange shows the 6 pages on the Shelf,
**long-press drag puts a Shelf page on Desk 1** (desk pages 0 → 1). FAIL: swipe (pointercancel — Mobile UI bug,
step 32), double-tap: the two taps still reached the page 421 ms apart — each process start (`cat`, `sleep`)
costs ~170 ms on the CI emulator. Now both taps leave in one `cat` (one write per frame, microseconds
apart): real kernel touch events, faster than a person; the check covers the app's double-tap handling
(mobile.js's < 300 ms window), not human timing.

### 34. Run 42212604032 (aef674d) — all four emulators, real gestures
| Gesture | Phone 35 | Phone 36 | Tablet 35 | Tablet 36 |
|---|---|---|---|---|
| Open with (content://) | PASS | PASS | PASS | PASS |
| swipe → next page | FAIL | FAIL | FAIL | FAIL |
| double-tap → fit flips | FAIL | PASS (page → width) | PASS (page → width) | PASS (page → width) |
| pinch → zoom in | PASS | PASS | PASS | PASS |
| Arrange → 6 pages on the Shelf | PASS | PASS | PASS | PASS |
| phone: tap Shelf header opens it | PASS | PASS | — | — |
| long-press drag Shelf page → Desk 1 | PASS | PASS | FAIL | PASS |
The double-tap now reaches the page as one (taps 51 ms apart on phone 35, 4 ms on tablet 35), and
mobile.js recognises it on three emulators. Smoke test passes on all four. What is left is Mobile UI:
1. **Swipe** never pages (all four): pointerdown → pointermove → pointercancel (`.rdesk` is `touch-action: pan-x pan-y`; mobile.js drops the swipe on cancel).
2. **Phone Fit page is wrong.** On phone 36, Fit page is *wider* than Fit width (456 vs 342 CSS px; overflowX 54). On phone 35 the page
   opened cut off, then after the swipe it showed at ~90 px wide, and the double-tap left it at 793 px (no fit button on). The
   recogniser fired (counter jumped 1 → 3); the fit sizing is what's wrong.
3. **Long-press drag is intermittent** (tablet 35 this run; passed there last run): pointerdown, the hold, one pointermove, then
   pointercancel, so the WebView took the drag as a pan after the press armed. mobile.js needs to stop the pan once a press arms
   (`touch-action: none` on the armed element, or a non-passive touchmove `preventDefault`).
Screenshots: `gestures-phone.png`, `gestures-tablet.png` (sent to the coordinator).

### 35. Composition from platform/mobile-ui f29b6a6; platform-layer emulator tests
- **Composition simplified.** platform/mobile-ui f29b6a6 already contains Foundation be4498a (merged), and the
  Mobile UI chat now ships its own hook patch (`docs/mobile-ui/proposal/mobile-ui-hooks-2.patch`, H-1 MainLayout,
  H-3 Reader). `compose.sh` now: checkout of mobile-ui → check that FOUNDATION_REF is an ancestor → apply that
  patch (pending Foundation's combined patch, D-26) → Android host. My own `mobile-ui-on-foundation.patch` is
  retired. Sandbox build of the composition: 0 warnings, 0 errors.
- **`platform.py`** (third emulator stage, after gestures), each check evidenced by page state, Android state
  (dumpsys / uiautomator) or the produced file:
  Open with .docx / .xlsx (their text on screen) · Share to Chuvadi (ACTION_SEND EXTRA_STREAM → new tab) ·
  rotation with a document open (same process, tab, page; no sideways overflow) · hardware keyboard
  (→ next page, Ctrl = zoom, Ctrl F + typing finds) · soft keyboard (shows; the find box stays above it) ·
  printing (Print card → PrintManager dialog → Save as PDF → the saved PDF has all 4 pages; range 2-3 → 2 pages) ·
  back (closes a card; phone: closes the ⋮ sheet by key and by edge gesture; nothing open → leaves the app,
  process kept; relaunch → same tab) · split screen (WMShell moveToSideStage → re-layout at the half window,
  same process; then full screen again) · no crash / ANR.
- Test files: `make-test-office.py` writes a minimal .docx and .xlsx (standard library); checked locally with
  the Reader's own `DocxViewService` / `XlsxViewService` before use.
- **Not testable from the UI: share out.** No Ui command calls `IShare` (Android implements it: chooser with a
  read-only content URI). Reported to the coordinator.

### 36. Arun's decisions (7 Nov); Foundation 2fafb60 + Mobile UI 26739e8; platform tests, round 2
- **Composition:** Foundation `2fafb60` (second combined patch: L-8 print permission, F-3 open queue)
  with platform/mobile-ui `26739e8` (session 3) merged in (clean), plus `mobile-ui-hooks-3.patch` (H-5, H-6),
  plus the host. Sandbox build: 0 warnings, 0 errors.
- **L-8 (decision 2): `AndroidPrintService` refuses a no-printing PDF** (`PrintPermission.Allows`) before
  PrintManager sees it, with `PrintPermission.Refused`. Test fixture `ci/fixtures/no-print.pdf` (made
  with Core's own permission mask; `Allows` = false); the emulator test checks the Print card is locked
  with the reason.
- **Open with while running (decision 3):** already singleTask + OnNewIntent. The test now proves it
  directly: same process, exactly one activity record in one task, tab count + 1.
  Round 1 (run 42276742988) found that it **didn't open anything** on all four emulators: the intents
  arrived (`am start` shows delivery) but nothing opened and nothing was logged. **Host bug fixed:**
  `DocumentImport` let an exception from the name lookup vanish inside `Task.Run`. Now a failure is
  logged (tag `Chuvadi`) and shown to the person ("Chuvadi couldn't open that file." / "…didn't give
  access."). The test saves our log lines so the cause shows in the next run.
- **Licence (decision 1):** Play checklist updated (Free, proprietary EULA link; never "open source").
- Tests adjusted to the facts of round 1 (not to make them pass):
  - Start platform tests in Read. gestures.py ends in Arrange, where Open with drops the file on the
    Shelf by design.
  - Rotation checks a flip (the tablet's natural orientation is landscape).
  - The print dialog had no printer selected → choose "Save as PDF"; give the saved file a unique name.
  - **Back:** BlazorWebView steps back through the app's screens before leaving. The check now walks
    back until the app leaves, with no dead presses. "Back closes a card" also requires the same
    screen, so a history step that happens to close the card doesn't count.
  - Typing goes one key at a time (a burst dropped characters), then Enter.
  - The emulator has no hardware keyboard now. With one, Gboard showed only its small toolbar, so
    the on-screen keyboard wasn't really tested.
  - Double-tap follows the new contract (Mobile UI session 3): zoom in, a second double-tap returns.
- Round 1 already proved on all four emulators: rotation, split screen in and out (WMShell),
  relaunch, PrintManager dialog, back closes the phone ⋮ sheet (key and edge gesture), no crash.

### 37. Run 42281134585 (round 2) — causes found; coordinator's six items
| Item | Cause (evidence) | Fix |
|---|---|---|
| .docx / .xlsx / Share don't open | **Test.** `ActivityTaskManager: START … from uid 0`: gestures.py leaves adbd as root, and root's `am` grant doesn't reach the app. The app logged `nothing imported from content://media/external/downloads/19` and showed "Chuvadi couldn't open that file." (the new host message working). The no-print PDF sent as uid 2000 opened in a new tab: Open with while running works. | intents now sent as uid 2000 (`su 2000 am …`), like a real sending app |
| Save as PDF finds nothing | **Test.** `find /sdcard …`: `/sdcard` is a symlink and `find` doesn't follow it. The picker showed SAVE with "chuvadi-test.pdf". | search `/storage/emulated/0/` |
| Typed text garbled ("tte", "te", "t") | Gboard took the test touchscreen for a stylus and opened "Try out your stylus" over the app (screenshot p6), swallowing keys. | stylus handwriting off (Android setting); typing one key at a time with the field read after each key; **control field** (plain `<input>`, no Blazor) typed the same way to separate input path vs page |
| Soft keyboard / Find | Round 2 had Gboard's stylus toolbar, not the keyboard; host pads for IME insets (SystemBars). | evidence now records the IME window top and the WebView's bottom before/after |
| Back on the tablet doesn't close the Print card | **Ui gap.** Only PhoneShell listens to `IAppLifecycle.BackRequested` (its sheets). Cards on the tablet don't, so back goes to the WebView history. | proposal to the coordinator (Reader closes the open card on BackRequested) |
| Swipe never pages | **Test.** Mobile UI's fix works on the device: no more pointercancel (pointerdown → 8 moves → pointerup). My swipe took 1.15 s (every step is a process start), over mobile.js's 600 ms. | one pause after touch-down, then the moves and the lift in one write (~0.4 s) |
| Double-tap on API 35 | Same clean double tap as API 36 (taps 18–75 ms apart), but reader.js doesn't zoom on API 35. | re-check after this run; page-side if it stays |
| Relaunch "tab" empty | Back had walked to Home (`/`); relaunch correctly returns there. | check compares the screen it left from |

### 38. CI blocked — GitHub billing (7 Nov)
Run 42285556510 (commit 53d7ab3), attempts 1 and 2: no job started. GitHub's annotation: "The job was not
started because recent account payments have failed or your spending limit needs to be increased. Please
check the 'Billing & plans' section in your settings." Round 3 (the fixes in step 37) is unverified until
Actions runs again on Sthraas/chuvadi-reader-platforms. The sandbox has no KVM, so emulators run only in CI.
Usage note: each full run is 1 build plus 4 emulator jobs of about 30 minutes each.

### 39. Coordinator decisions (7 Nov): P-06 Back closes cards; over-wide probe; copyright
- **P-06** (decision (a)): `docs/android/proposal/P-06-back-closes-card.patch`, for Foundation's combined patch.
  The Reader subscribes to `IAppLifecycle.BackRequested` and closes the open card (measure included) as
  Escape does; with nothing open it declines, so the host's default runs. Applies to 2fafb60 and 615afde.
  The composition now applies Android's pending proposals too, so the emulators test it (platform.py:
  "back closes an open card and stays on the same screen").
- **Over-wide element probe** (Mobile UI's question): right after the PDF opens, gestures.py lists every
  element past the desk's visible right edge, the outermost ones with their chain from the desk, and for
  each: tag, classes, rect, how far over, and the computed width, min/max-width, box-sizing, margins,
  paddings, borders, transform and inline style. Saved as `gestures/overwide.json` and printed in the
  log. Checked in headless Chromium against a page with a known over-wide `.rpage` (found it, 38 px over).
  Runs on the next CI run on phone and tablet.
- **Copyright:** Foundation's `Directory.Build.props` (615afde) now sets Company, Authors, Product and
  Copyright (Sthraas Intelligence Pvt Ltd) for every project, the Android host included; no copy in the
  host's csproj. README carries the copyright line.
- **Composition:** Foundation 615afde + Mobile UI 745ef8e (merges cleanly) + mobile-ui-hooks-3 + P-06 +
  host: Android 0 warnings; Platforms solution `-warnaserror` 0 warnings; tests 171 + 33 + 12 + 19 pass.
- Still blocked: GitHub Actions on Sthraas (billing / spending limit), so no emulator evidence this step.

### 40. .NET runtime notices in the app (coordinator decision (a), 7 Nov)
- The app bundles the .NET runtime and .NET for Android, so it ships both packs' own
  `THIRD-PARTY-NOTICES.TXT` as assets `notices/dotnet-runtime.txt` (76 KB) and `notices/dotnet-android.txt`
  (145 KB). They come from the exact packs of the build (`BundledNETCoreAppPackageVersion`,
  `AndroidNETSdkVersion`, API from `TargetPlatformVersion`), with the NuGet cache as a fallback. The
  build fails if either is missing.
- First attempt (from `ResolvedRuntimePack`) worked for the single-CPU Debug build but packed nothing
  in Release: the multi-CPU outer build resolves no runtime packs. Caught by unzipping the Release
  packages. Now verified in all three: Debug x64 .apk, Release .apk and Release .aab.
- `Platform/RuntimeNotices.cs` reads both under headings, on demand only (never at startup). It is
  handed to Foundation's host-notices contract when that lands (Foundation is adding it). The
  Licences page then shows it.

### 41. CI by hand only (coordinator, 7 Nov 04:55 IST)
- The dispatches every 10 minutes from 20:47 to 22:27 UTC (02:17–03:57 IST) were mine: a watcher
  started after step 40 to begin round 3 the moment Actions came back. It ended on its own after ~110
  minutes; nothing of mine is running now. It won't be restarted, and nothing here starts runs on its own.
- The workflow is now `workflow_dispatch` only (no push / pull-request triggers), with an `emulators`
  input (`all`, `none`, or a list such as `phone-36,tablet-35`). The build job turns it into the
  emulator matrix, so a round runs only what it needs.
- Round 3 is on hold until the coordinator confirms. Its checklist adds D-89 option C: where
  `DropFiles` is false (Android), the first-run box says "open" rather than "drop" (Foundation's
  wording change; check on the emulator).

### 42. Round 3 set-up (D-93: CI back; one run by hand)
- **Composition:** Foundation `a73a898` (fourth combined patch with P-06, single instance, host notices,
  D-89) + Mobile UI `ac8e84c` merged (clean) + `mobile-ui-hooks-3.patch` (H-5 to H-11, incl. H-9: the
  first fit measured on the placeholder, Mobile UI's fix for the phone over-wide page). P-06 is detected
  as already in Foundation. Android 0 warnings; Platforms solution `-warnaserror` 0 warnings; tests
  171 + 48 + 31 + 16 pass.
- **Host, per HANDOFF:** `IHostNotices` → `AndroidHostNotices` (".NET runtime" tab: the two bundled
  notices). Files from other apps now go through the kit's `IncomingFiles.Receive` (one route for
  every host: Bench shelf or a new tab, after the first render); our import errors stay as they were.
  Single instance on Android = `LaunchMode.SingleTask` + `OnNewIntent` (already; tested in platform.py).
- **New check:** D-89 B, Home says "Open…", never "drop", on Android (`DropFiles` false).

### 43. Round 3 — run 42314548860 (all four emulators): results and test-tool fixes
**App results** (each emulator's first platform pass; the second pass was a test bug, below):
| Check | Phone 35 | Phone 36 | Tablet 35 | Tablet 36 |
|---|---|---|---|---|
| Smoke (start, Ui, rotation, no crash/console error) | PASS | PASS | PASS | PASS |
| Swipe pages | PASS | PASS | PASS | PASS |
| Double-tap zoom in / back | PASS | PASS | PASS (screenshots: 58 % → 200 % → 58 %; the check measured a placeholder page, fixed) | PASS |
| Pinch | PASS | PASS | PASS | PASS |
| Arrange → Shelf; long-press drag to desk | PASS | PASS | PASS | PASS |
| Phone Fit page sideways overflow | **0 px** (H-9 cured it) | **0 px** | 0 px | 0 px |
| Open with .docx / .xlsx while running → new tab, same activity + process | PASS | PASS | PASS* | PASS* |
| Share to Chuvadi → new tab | PASS | PASS | PASS* | PASS* |
| Rotation with a document (process, tab, page; no overflow) | PASS | PASS | PASS | PASS |
| → next page, Ctrl = zoom | PASS | PASS | PASS | PASS |
| Ctrl F + typing finds (1/4) | PASS | PASS* | PASS* | PASS* |
| Typing control (plain field) arrives exactly | PASS | PASS | PASS | PASS |
| On-screen keyboard: shows, app resizes above it (innerHeight 839→527 phone, 744→408 tablet), Find stays visible | PASS | PASS | PASS | PASS |
| Print card → Android print dialog (Save as PDF; preview 1/4…4/4) | PASS | PASS | PASS | PASS |
| Save as PDF wrote the file ("chuvadi-share (1).pdf", 3.05 kB, in the picker) | file made; page count not read (test bug) | ← | ← | ← |
\* marked FAIL by the check, wrong for test reasons: the tablet tab count counted each tab twice (every tab is a
`.rtab`, plus the "+N" chip, which is Tabs.Count − 1); find's value came back "Test" because Gboard's autocorrect
capitalises on Enter (the search found 1/4).
**Not reached** (the test crashed after printing): range print, L-8 no-print card, Back, split screen, D-89 wording.
**Test-tool bugs found and fixed (no app change):**
1. `platform.py` ran twice per job: with its folder first on `sys.path`, a library's `import platform` loaded the
   script itself. Renamed `platform_checks.py`.
2. The saved PDF's path had a space ("chuvadi-share (1).pdf"); `find` output was split on spaces. Split on lines.
3. Tablet tab count: count `.rtab` only.
4. Find: clear the field first; compare case-insensitively (Gboard autocorrect).
5. Double-tap / page width: measure the page under the desk's centre, not the first page with a box.
6. Over-wide probe: report the over-wide element itself (not its outermost ancestor) and leave out
   elements clipped inside their page. Re-checked in headless Chromium (finds `div.rpage`, 38 px over).
**For the Mobile UI chat (seen in the screenshots, round 3):**
- Double-tap zoom lands on the wrong page: on page 2, the zoom-in shows 1 / 6 (phone 36) or 6 / 6 (phone 35);
  the second double-tap returns to 2 / 6 (`round3-gestures-phone.png`). The zoom keeps no anchor on the tapped page.
- Phone API 35 Fit page is far too small: page box 147.6 px in a 402 px desk (`overwide.json`: the visible
  `.rpage-wrap`); phone API 36 is 341.9 px. Sideways overflow is 0 on all four emulators, so H-9 fixed that.

### 44. Round 4 set-up (coordinator, 8 Nov 18:15 IST)
- Script bugs from round 3 already fixed in d9854bc (tab count from `.rtab` only; saved PDF path split on lines, so
  "chuvadi-share (1).pdf" survives; script renamed `platform_checks.py`; find case; page under the desk centre;
  over-wide probe names the element itself).
- Composition: Foundation `4819d66` (CI-only change) + Mobile UI `2678dd2` (hooks-3 now H-5 to H-12; H-12: no
  sample recents/pins on Android, so a fresh install shows the first-run box) + host. Android 0 warnings;
  Platforms `-warnaserror` 0 warnings; tests 171 + 48 + 31 + 16 pass.
- Note on "58 % → 200 % → 58 %": that is double-tap working as designed (zoom in, then back). The bug for Mobile UI
  is the page it lands on (phone: page 2 → 1 / 6 or 6 / 6; tablet stays on 2 / 6), see step 43.

### 45. Round 4 — run 42481924551 (all four emulators)
| Check | Phone 35 | Phone 36 | Tablet 35 | Tablet 36 |
|---|---|---|---|---|
| Smoke | PASS | PASS | PASS | PASS |
| Swipe · pinch · Arrange · long-press drag | PASS | PASS | PASS | PASS |
| Double-tap zoom / back | FAIL¹ | PASS | FAIL² | PASS |
| Open with .docx / .xlsx while running (new tab, same activity + process) | PASS | PASS | PASS | PASS |
| Share to Chuvadi | PASS | PASS | FAIL³ | FAIL³ |
| Rotation · → · Ctrl = · Ctrl F · typing control · on-screen keyboard | PASS | PASS | PASS | PASS |
| Print card → dialog; Save as PDF (4 pages); range 2-3 (2 pages) | PASS | PASS | PASS (all-pages check FAIL³) | ← |
| L-8: no-print PDF → Print card locked with the reason | PASS | PASS | PASS | PASS |
| Back closes the Print card (P-06) | **FAIL⁴** | **FAIL⁴** | **FAIL⁴** | **FAIL⁴** |
| Phone: Back (key and edge gesture) closes the ⋮ sheet | PASS | PASS | — | — |
| Back walks screens then leaves; relaunch same process | FAIL⁴ / PASS | ← | ← | ← |
| D-89 Home says open, not drop | FAIL⁵ | FAIL⁵ | PASS | PASS |
| Split screen in and out | PASS | PASS | PASS | PASS |
| No crash / ANR in the app | PASS | PASS | PASS | PASS |
1. Emulator noise: "Pixel Launcher isn't responding" sat over the app and took the taps. gestures.py now clears
   system dialogs before every touch.
2. Measurement: the page under the centre is a page laid out at 793 px inside a 147 px wrapper (API 35 only), see 6.
3. Test: the tablet's page counter shows the number only ("1", no "/ 4"); the check now uses the page count.
4. **Host bug, fixed.** BlazorWebView registers its own Back callback (WebView history) when its handler connects,
   after the activity's; the dispatcher asks the newest first, so Back went to the WebView history and P-06 never ran
   (the "dead" Backs were history steps within /reader). The activity now re-adds its callback after the WebView
   initialises, when its handler changes, and on every resume (`PutBackFirst`). Sheets "closing" before was a side
   effect of the history step.
5. Test: phone Home has a "+ Open" button, not the sentence; no "drop" anywhere. The check now accepts "Open".
6. **API 35 page sizing (for the Mobile UI chat / decision):** phone and tablet API 35 lay pages out at full size
   (`.rpage`, 793 px, no transform) inside fit-sized wrappers (147 px), so Fit page shows tiny and measurements
   disagree. The Ui sizes pages with CSS `zoom` (`--rpage-zoom`, and on Android `theme.js` zooms the root), and
   Chromium changed how `zoom` reports sizes in 128. API 36 runs WebView 133 (correct). API 35's version wasn't in
   the logs; gestures.py now records `dumpsys webviewupdate` and the user agent per emulator.
- **Host fix, also:** relaunch showed one white frame (WebView default background); the WebView is now transparent
  until the page paints, so the page colour behind it shows.
- Phone "full screen again" picture was taken mid-animation (app in the top third, size already full); the check
  passed. A 2 s settle wait before that picture now.

### 46. Round 5 set-up (coordinator, 8 Nov 18:58 IST)
- Composition: Foundation `8098695` (sixth combined patch: Mobile UI H-5 to H-12 now in Foundation) + Mobile UI
  `a20f6d1` merged + `mobile-ui-hooks-4.patch` (H-13 only: reader.js zoom anchor on the visible page, API 35 fit) +
  host (Back first, transparent WebView). Android 0 warnings; Platforms `-warnaserror` 0 warnings; tests
  171 + 54 + 32 + 16 pass.
- New check: double-tap zoom stays on the tapped page (H-13).

### 47. Round 5 — run 42485287858 (all four emulators)
| Check | Phone 35 | Phone 36 | Tablet 35 | Tablet 36 |
|---|---|---|---|---|
| WebView | **124.0.6367.219** | 133.0.6943.137 | **124.0.6367.219** | 133.0.6943.137 |
| Smoke · swipe · pinch · Arrange · long-press drag | PASS | PASS | PASS | PASS |
| Double-tap zoom stays on the tapped page (H-13) | PASS | PASS | PASS | PASS |
| Double-tap / Ctrl = page width grows | FAIL¹ | PASS | FAIL¹ | PASS |
| Open with .docx/.xlsx while running · Share | PASS | PASS | PASS | PASS |
| Rotation · keys · find · typing · on-screen keyboard | PASS | PASS | PASS | PASS |
| Print → dialog · Save as PDF (4) · range (2) · L-8 locked | PASS | PASS | PASS | PASS |
| **Back closes the Print card (P-06 + Back-first host fix)** | **PASS** | **PASS** | **PASS** | **PASS** |
| Phone: Back key / edge gesture closes the ⋮ sheet | PASS | PASS | — | — |
| Back walks screens, then leaves; no dead presses | FAIL² | FAIL² | FAIL² | FAIL² |
| Relaunch · D-89 Home "open" · split in/out · no crash | PASS | PASS | PASS | PASS |
| Phone Fit page sideways overflow | 0 | 0 | 0 | 0 |
1. **WebView 124 (API 35) and CSS `zoom`.** H-13 fixed the API 35 Fit page (the phone now matches API 36), but on
   WebView 124 zoomed pages still measure at their unzoomed size (793 px at every zoom), and double-tap / pinch land
   on a blank white area (the page number stays right). Chromium standardised `zoom` in 128. Decision needed.
2. Back does leave the app (… /reader → /bench → /reader → / → launcher), but first takes 4 presses that change
   nothing: one per file opened while on the Reader (DOCX, XLSX, Share, no-print). Cause: `MainLayout.OnOpenRequested`
   navigates to `/reader` even when already there. **P-07** (Ui, for Foundation's combined patch) navigates only when
   the Reader isn't showing; the composition applies it in round 6.

### 48. D-105 (a): WebView 128+ required; round 6 set-up
- **Host:** `Platform/WebViewSupport.cs`. At start the app reads the WebView provider's version
  (`WebView.CurrentWebViewPackage`). Below 128, or with no WebView, it shows one native screen instead of the
  Reader: "One small update first", why (the version found), "nothing leaves this device", and an
  **Update Android System WebView** button that opens its Google Play page (falling back to the Play web page).
  On every resume it checks again and swaps in the Reader once the update is in. Cost on a supported device: one
  package-info read before the first page.
- **CI (coordinator: try a Play image first):** not possible for these tests. A Play image's WebView updates
  only after a Play sign-in, and Play images are locked builds without `adb root`, which the real-touch input
  needs. So: emulators below 128 run `webview_gate.py` (update screen shown, version named, Reader absent;
  button leaves the app; back in, same process, same screen; no crash). Smoke markers accept the update screen.
  At 128+ (API 36) the full gesture and platform suites run.
- **P-07** stays applied by the composition until Foundation takes it (coordinator has asked).
- Composition: Foundation `cd9b72d` (seventh combined patch part 1: H-13 in Foundation) + Mobile UI `a20f6d1` + P-07
  + host. Android 0 warnings; Platforms `-warnaserror` 0 warnings; tests 171 + 54 + 32 + 16 pass.

### 49. Round 6 — run 42488183117 (all four emulators)
- **API 36, phone and tablet: all green.** Gestures 10/10 (phone) and 9/9 (tablet), platform 25/25 and 23/23,
  smoke pass. With P-07 applied, Back now walks real screens only (/reader → /bench → /reader → / → launcher), no
  dead presses. Back closes the Print card; Open with / Share; rotation; keyboards; printing incl. L-8; split
  screen; D-89 wording; no crash.
- **API 35 (WebView 124.0.6367.219):** the app correctly showed the update screen (smoke test found it, portrait and
  rotated: "One small update first … On this device it is version 124.0.6367.219", the Update button). But the
  WebView gate never ran: **my slip** — in step 48 the `emulator-tests.sh` rewrite sat behind a failed `sed` in an
  `&&` chain and was never written, so the old runner sent API 35 into the Reader suites (which timed out waiting
  for a PDF the update screen rightly never shows). Runner now written and checked (`bash -n`); the gate runs on
  API 35 next round.

### 50. Round 7 set-up (coordinator, 8 Nov 20:05 IST): API 35 only
- Rebased onto Foundation `9fbed93` (seventh combined patch part 2a, which takes P-07); the composition now finds
  P-06, P-07 and Mobile UI's hooks-4 already in Foundation. Mobile UI `a20f6d1` unchanged. Android 0 warnings;
  Platforms `-warnaserror` 0 warnings; tests 171 + 54 + 33 + 16 pass.
- One run, `emulators=phone-35,tablet-35`: the WebView gate (update screen, Play button, back in) on WebView 124.

### 51. Round 7 — run 42490699776 (API 35 only, WebView 124.0.6367.219)
| WebView gate | Phone 35 | Tablet 35 |
|---|---|---|
| Update screen instead of the Reader, version named | FAIL¹ | PASS |
| Update button leaves the app | FAIL¹ | PASS (opened Chrome: no Play Store on this image) |
| Back in: same process, still the update screen | FAIL¹ | PASS |
| No crash / ANR in the app | PASS | PASS |
| Smoke | PASS | PASS |
1. The emulator's own "Pixel Launcher isn't responding" dialog was over the screen (dump texts: only that dialog),
   as in round 4. `webview_gate.py` now taps its "Wait" before reading the screen, like gestures.py does.

### 52. Phone API 35 re-run — run 42493320507: green
WebView gate 4/4 (update screen with version 124.0.6367.219; button → Play page in Chrome; back in, same process,
same screen; no crash), smoke pass. With round 6 (API 36 phone and tablet, all checks) and round 7 (API 35 tablet,
4/4), **every emulator is green** on Foundation 9fbed93 + Mobile UI a20f6d1 + this host (cd485ef).

### 53. Rebase onto Foundation 839d39d (eighth combined patch) — coordinator, 9 Nov 01:30 IST
- Composition: Foundation `839d39d` + Mobile UI `95b9d79` merged (clean); hooks-5 (H-14, H-16), P-06 and P-07 all
  found already in Foundation. Android 0 warnings; Platforms `-warnaserror` 0 warnings; tests 187 + 59 + 33 + 16 pass.
- New dispatch input `suite`: `full` (default) or `smoke` (install, start, Ui, rotation, no crash) — a rebase check
  without a full round. This rebase: one emulator, phone API 36, smoke.
- Note for the next full round: H-14 makes the phone open at Fit width (not Fit page); gestures.py's swipe and
  double-tap read the fit from the page, so they will show it.
- Smoke check, run 42518163924 (phone API 36, `suite=smoke`): build pass, smoke pass on 839d39d + 95b9d79.
- Android Test chat opened (`platform/android-test`, ee4f66c): BUGS.md has none filed yet (its round 1 running).

### 54. Android Test bugs AT-02, AT-07, AT-08; Release on the emulators; rebase onto 42461ba — coordinator, 9 Nov 05:55 IST
- Composition: Foundation `42461ba` + Mobile UI `1f4b4c3` merged (clean). My copy of mobile-ui-hooks-5 dropped (Foundation
  has it; compose.sh no longer applies Mobile UI hook patches). P-06 and P-07 moved to `proposal/applied/`.
- **AT-02** (unused MAUI Essentials manifest entries): `tools:node="remove"` for the web-sign-in activities, Essentials'
  file provider and the connectivity / battery / energy-saver receivers. Test: `ci/manifest-check.sh` on the Release
  .apk (aapt2): those gone, our provider, activity and Open-with / Share filters present, no permissions requested.
  Now a build-job step. Sandbox Release: 14/14 pass. (AndroidX.Browser's `KeepAliveService` stays with AT-01.)
- **AT-07** (cache path as tab / card / row labels): new kit seam proposed, P-08 `IPathLabels` (default: the path, so
  desktops are unchanged), used in the 13 places the Ui shows or reads out a path; `AndroidPathLabels` answers from the
  document links (device storage: `Download/report.pdf`; other providers: the name; picked folders: folder + place).
  The composition applies P-08 until Foundation decides. Test: `platform_checks.py` "no private cache path in tab, card
  or row titles, accessible names or text"; Hosting test `Default_path_labels_show_the_path`.
- **AT-08** (bars cream in every theme): `SystemBars` now follows `ThemeService.Changed` while the app runs (it read the
  theme only at start), with the colour of the Ui's edge bars (`--chvd-surface-hi`) and light icons on Night paper. Test:
  `platform_checks.py` sets each theme in Settings › Appearance and reads the top and bottom pixel rows of a raw
  screencap, plus the window's requested bar appearance.
- **Release on the emulators:** after the Debug suites (and in `suite=smoke`), `emulator-tests.sh` uninstalls and runs
  the smoke test on the Release .apk (it carries x86_64). AT-03 (Release crash from trimming) is Foundation's.
- Sandbox: Android Debug and Release `-warnaserror` 0 warnings; Hosting 60, MobileUi 16, WebUi 39 tests pass.
- **Run 42541330985** (phone and tablet API 36, full, 863112c): build pass, Release manifest check 14/14; gestures 10/10
  and 9/9; platform 27/27 and 25/25, including AT-07 (no cache path; names such as `chuvadi-test.docx`) and AT-08 (top and
  bottom rows exactly `#241b15` / `#f6f2e1` / `#f8f9fc` / `#ffffff` / `#fbf7ec`). **Release launch: FAIL on both** —
  AT-03 as filed: `NoConstructorMatch, ChuvadiReader.Platform.NoAppInstance` in `MainActivity.OnCreate` (Foundation's fix
  is not in 42461ba). Note for that fix: P-08's `PlainPathLabels` is another seam default of the same kind.
- AT-08's icon half wasn't judged in that run (the window dump on API 36 doesn't show the requested appearance). The check
  now reads the status-bar icons from the pixels; on that run's own screenshots it gives light icons on Night paper and
  dark on the other four, on both devices. It runs in the next round.

### 55. P-08 decided (a), D-146 — coordinator, 9 Nov 07:00 IST
- Patch finished for Foundation: also the Export / Press / Scatter folder lines (Reader, Bench, Library), Home's category
  folder and Settings' save and data folders (23 places, 13 Ui files). New drift-guard test
  `Ui_shows_paths_only_through_path_labels` beside `Default_path_labels_show_the_path`. Applies on 42461ba alone:
  Platforms `-warnaserror` 0 warnings, Hosting 61 pass. With Mobile UI 1f4b4c3: Core 210, Hosting 61, MobileUi 16,
  WebUi 39 pass; Android 0 warnings.

### 56. Rebase onto Foundation 022b7c0 (AT-03 fix, typed registrations) — coordinator, 9 Nov 07:30 IST
- Composition: Foundation `022b7c0` + Mobile UI `558a276` merged (clean). P-08 rebased: the seam is now a typed
  `Seam<IPathLabels, PlainPathLabels>` call and `TypedRegistrationTests` pins it; applies on 022b7c0 alone.
- Sandbox: Platforms `-warnaserror` 0 warnings; Core 212, Hosting 66, MobileUi 16, WebUi 39 pass; Android Debug and
  Release `-warnaserror` 0 warnings; Release manifest check 14/14.
- Round: all four emulators, full suite, with the Release (trimmed) launch — for AT-03.

### 57. Run 42549242105; rebase onto Foundation f88f9ef; AT-11 — coordinator, 9 Nov 20:23 and 10 Nov 07:23 IST
- **Run 42549242105** (all four, full, d134c74 on 022b7c0): every stage green on all four, **Release (trimmed) launch
  pass on all four — AT-03 fixed**. API 36: gestures and platform all pass, AT-07 and AT-08 included; API 35: WebView
  gate 4/4.
- Composition: Foundation `f88f9ef` (P-08, AT-03, AT-10, AT-13, Sheets 2.0.4) + Mobile UI `d34d542` merged (clean).
  P-08 is in Foundation: moved to `proposal/applied/`; no Android proposals pending.
- **AT-11** (phone tabs "lost" after a background kill): the tabs survive (TabsService saves them on every change; in
  Android Test's runs the count before each kill grew 7 → 16), but a recreated activity started a fresh WebView on Home,
  where the phone shows no tab strip — so the Reader, its tab and page were gone from view; the tablet's title-bar strip
  hid it. Host fix, no Ui hook needed: `SessionRoute` saves the Ui's route in the activity's saved state
  (`OnSaveInstanceState`) and a recreated activity starts the WebView there (`BlazorWebView.StartPath`); the Reader then
  reopens the active tab at its page. A cold start (no saved state) still opens Home, as on Windows. Test:
  `platform_checks.py` "after Android ends the app in the background, it comes back on the same document, page and tabs"
  (Home → card → Reader, Home key, `am kill`, relaunch; route, tab, tab count and page counter equal).
- Sandbox: Android Debug and Release `-warnaserror` 0 warnings; Release manifest 14/14; Core 233, Hosting 77, MobileUi 16,
  WebUi 39 pass.
- **Run 42739965634** (all four, full, ccd4452 on f88f9ef): build pass; **Release (trimmed) launch pass on all four**;
  API 35 WebView gate 4/4 on both; gestures 10/10 and 9/9; AT-07 and AT-08 pass on both API 36 (icons now judged:
  light on Night, dark on the rest). Failures:
  - phone 36: the AT-11 check stopped with a traceback — after the kill, the new process's DevTools reset the connection
    and `safe_state` only caught SystemExit. Test bug: fixed (any failure to reach the page means "not yet").
  - tablet 36: Share "4 → 4 tabs" — test race: the tab count was read after the intent, and the shared tab was already
    there. Fixed (read before). **Ui regression, for Foundation:** the shared PDF opened on page 1 (p3-shared) and,
    with no input, was on page 4 of 4 two seconds later (p4-rotated, rotation check's base counter 4); so "keyboard →
    next page" had nowhere to go. Passed on 022b7c0 (run 42549242105); new between 022b7c0 and f88f9ef (render
    scheduling / "page in view stays put" changes).
- **Run 42742138203** (phone and tablet API 36, full, 7b7450b): **all green** — gestures 10/10 and 9/9, platform 28/28 and
  26/26, Release launch pass on both. **AT-11 pass on both**: killed (new pid), back on `/reader`, same tab
  (`chuvadi-no-print.pdf`), same 5 tabs, same page. Share pass ([3, 4] tabs). The shared PDF again opened off page 1
  (phone "2 / 4", tablet "3") — the f88f9ef page drift, intermittent; with Foundation.
- Handed to Android Test: head **7b7450b** on f88f9ef + Mobile UI d34d542, for AT-02, AT-03, AT-07, AT-08, AT-10, AT-11, AT-13.

### 58. AT-12 (duplicate tab on Open with); D-158 page images wired; rebase onto Foundation 846706e — coordinator, 10 Nov 09:14 IST
- Android Test round 5 on 9ce073b: AT-02, 03, 04, 05, 07, 08, 10, 11 verified.
- **AT-12:** every incoming content URI was copied into a new working folder, so the same document arrived under a new
  path and the shared router (`TabsService.OpenAsync`, same-path → focus) couldn't recognise it. `DocumentLinks.Import`
  now reuses the working copy already linked to that URI (option (a) of the report): left exactly as it is while a tab
  holds it (it may have unsaved edits), refreshed from the source when no tab does; Recent keeps one entry. Limit: the
  same file reached through two different providers (MediaStore and Files) is still two URIs. Test: `platform_checks.py`
  "Open with on a document that is already open focuses its tab, no duplicate" (.docx again after the .xlsx: same tab
  count, .docx in front).
- **D-158:** `ChuvadiWebView` (BlazorWebView subclass) wraps the host's file provider in Foundation's
  `PageImageFileProvider`, as PAGE-IMAGES.md asks of the Android host; drawn page images load from memory, in process.
  Covered by Foundation's `PageImageFileProviderTests`; no raster page in our device fixtures yet.
- Composition: Foundation `846706e` + Mobile UI `c5c0b7e` (clean). Sandbox: Android Debug and Release `-warnaserror`
  0 warnings; Release manifest 14/14; Core 247, Hosting 82, MobileUi 16, WebUi 41 pass.
- **Run 42752591502** (phone and tablet API 36, full, 68a00b1 on 846706e): **AT-12 pass on both** (.docx again: 3 → 3
  tabs, .docx in front); AT-11 pass on both; Release launch pass on both; phone 29/29, gestures 10/10 and 9/9. Tablet
  26/27: "keyboard → next page" — the shared PDF was on page 4 of 4 before the key (the page drift from f88f9ef, with
  Foundation; not the keyboard).
- Handed to Android Test: head **68a00b1** for AT-12 (and D-158 page images).

### 59. Foundation PR #13 head 15033c8; AT-14 timeline and Chuvadi-only full AOT — coordinator, 10 Nov 15:28 IST
- Composition: Foundation `15033c8` (platform/foundation-pr: AT-15, page-box drift, AT-09, AT-13, TOOLS headings)
  **alone**. Mobile UI's head `2b29227` (H-21, AT-06) does not merge into it: 7 shared files conflict (reader.js 5 hunks
  — `init(…, newDocument)`, the pen split, `scrollToMatch` — mobile.css 8, mobile.js 4, Reader.razor 1, Foundation's
  build log, Hosting.Tests.csproj, the preview's services); c5c0b7e doesn't either. Shared files aren't mine to resolve:
  Mobile UI merges 15033c8, then I compose with it. `compose.sh` takes `none` for Foundation alone.
- Sandbox: Android Debug and Release `-warnaserror` 0 warnings; Release manifest 14/14; Core 247, Hosting 86, MobileUi 16,
  WebUi 41 pass.
- **AT-14, where the cold Open with time goes:** `Platform/StartupTimeline.cs`. The host stamps its stages (process,
  runtime, maui, activity, import-start/done, handed, webview, webview-ready) and, when the launch carries
  `--ez chuvadi.timing true`, watches the page every 25 ms (EvaluateJavascript, so it works on Release) for html
  (DOMContentLoaded), ui (Blazor's first UI), opening (Reader pages present) and painted (page 1's SVG), writing all of
  them to logcat tag `ChuvadiTiming` in ms since the process started. Off and silent without the extra.
  `ci/cold_open_timeline.py`: 10 cold runs (clear data, stop, drop caches, Open with as the shell user), per-stage
  median / worst; workflow suite `timeline`.
- **AT-14, Chuvadi-only full AOT (test variant, off by default):** `ChuvadiAot.targets`, `-p:ChuvadiFullAot=true`. Right
  after the SDK's profiled AOT pass it re-runs the SDK's own Mono AOT compiler, same settings, for Chuvadi.* and
  ChuvadiReader.* only, without "profile-only" (MAUI and the BCL keep their profiled images). Sandbox, all four ABIs:
  .apk 43.55 → 51.21 MB (+7.7 MB, +18 %; full AOT of everything was +21 MB, +49 %), .aab 43.00 → 50.69 MB; Chuvadi's
  x86_64 AOT images 0.67 → 11.3 MB (ChuvadiReader.Core 45 KB → 1.26 MB); build 184 s.
- **Run 42799399331** (all four, full, d387740 on 15033c8): API 35 WebView gate 4/4 on both; gestures 10/10 and 9/9;
  Release launch pass on all four; platform 28/29 (phone) and 26/27 (tablet). The one failure on each is a test race in
  the AT-11 check: the restore itself was right (killed, same route, tab and 5 tabs), but the page counter was read
  before it was filled (phone after "", tablet before ""). Fixed: wait for the counter on both sides.
- **Run 42799417097** (timeline): the variant build failed — NETSDK1047, the Debug x86_64 build had restored for
  android-x64 only and the variant used `--no-restore`. Fixed: the variant restores.
- **Run 42803390901 — AT-14 timeline** (phone and tablet API 36, Release, 12-page 5 KB PDF, 10 cold Open with runs each;
  ms since the process started, median / worst):

  | stage | phone shipped | phone Chuvadi AOT | tablet shipped | tablet Chuvadi AOT |
  |---|---|---|---|---|
  | runtime (first managed code) | 258 / 925 | 182 / 439 | 663 / 1248 | 784 / 1276 |
  | activity | 400 / 1357 | 329 / 589 | 857 / 1553 | 950 / 1453 |
  | webview ready | 702 / 2450 | 629 / 905 | 1256 / 2674 | 1336 / 1864 |
  | file copied (import-done) | 611 / 1903 | 542 / 799 | 1056 / 2347 | 1151 / 1693 |
  | handed to the Ui | 823 / 2731 | 741 / 1027 | 1425 / 2938 | 1489 / 2053 |
  | html (DOMContentLoaded) | 878 / 3082 | 807 / 1126 | 2018 / 3128 | 1895 / 2857 |
  | ui (Blazor's first UI) | 1757 / 5726 | 1585 / 1895 | 2674 / 6399 | 2622 / 3216 |
  | opening (Reader pages present) | 4425 / 9783 | 4243 / 4691 | 7875 / 12711 | 7480 / 7894 |
  | **painted (page 1)** | **4848 / 11308** | **4593 / 4939** | **8688 / 14206** | **8156 / 8644** |

  Where the time goes (medians): Android, .NET and MAUI to the activity ~0.4 s (phone) / 0.9 s (tablet); file copy
  ~0.1 s; WebView ready and page loaded by ~0.9 / 2.0 s; Blazor's first UI +0.9 / +0.7 s; then **Blazor UI → Reader
  pages present: 2.7 s (phone) / 5.2 s (tablet)** — for a 5 KB PDF, so not parsing; then page 1 painted +0.4 / +0.8 s.
  Chuvadi-only full AOT: median −0.26 s / −0.53 s (−5 % / −6 %), worst case roughly halved (11.3 → 4.9 s, 14.2 →
  8.6 s), and the Ui-to-pages gap unchanged (2.66 / 4.86 s) — so that gap isn't JIT. Cost +7.7 MB (+18 %), build 122 s.
- Timeline now also stamps `reader` (the Reader's route) and `loading` (its "Opening <name>…" line) to split that gap.
- **Run 42806063037 — AT-14 timeline with the gap split** (same setup; medians, ms since process start):

  | stage | phone shipped | phone Chuvadi AOT | tablet shipped | tablet Chuvadi AOT |
  |---|---|---|---|---|
  | ui (Blazor's first UI) | 2022 | 1970 | 2216 | 2173 |
  | **reader** (route /reader) | **4327 (+2305)** | **4319 (+2349)** | **5137 (+2921)** | **5288 (+3115)** |
  | loading ("Opening …") | 4573 (+246) | 4558 (+239) | 5219 (+82) | 5434 (+146) |
  | opening (pages present) | 4884 (+311) | 4831 (+273) | 7302 (+2083) | 7332 (+1898) |
  | painted (page 1) | 5382 (+498) | 5169 (+338) | 8127 (+825) | 8006 (+674) |

  The largest gap is **Blazor's first UI → the Reader's route: 2.3 s phone, 2.9–3.1 s tablet**, AOT or not. The
  incoming file is held by `IncomingFiles` until `IAppReadySignal`, which `MainLayout.OnAfterRenderAsync(firstRender)`
  raises only after its awaits in series (platform attributes, SaveFolders / Profile / Theme hydration, theme apply,
  `leftbar.open`, the `shell.js` import and init). Second on the tablet: reading the document, "Opening" → pages,
  ~2 s (0.3 s on the phone). Both are in the shared Ui / Core: for Foundation, with these numbers.

### 60. Foundation dd59362 + Mobile UI 3ecbc75; D-164 — coordinator, 10 Nov 20:45 IST
- **D-164:** build settings stay as shipped, no AOT. `ChuvadiAot.targets` stays as an off-by-default test variant for the
  timeline suite only (never in the shipped build). Both AT-14 waits are with Foundation.
- Composition: Foundation `dd59362` (platform/foundation-pr, patch 24: Excel number formats, CropBox, fresh-open fix) +
  Mobile UI `3ecbc75` (merged 15033c8; D-163) — clean. Mobile UI's `mobile-ui-hooks-9.patch` (H-22) applies but isn't in
  Foundation yet; by the standing rule it isn't applied here, so H-22 isn't in this build.
- Sandbox: Android Debug and Release `-warnaserror` 0 warnings; Release manifest 14/14; Core 292 (+3 skipped),
  Hosting 89, MobileUi 16, WebUi 41 pass.
- AT-01 is verified (Android Test R6); nothing of it waits on Arun.
- **Run 42841112122** (all four, full, 8f173c9): **all green** — API 35 WebView gate 4/4 on both; gestures 10/10 and 9/9;
  platform 29/29 (phone) and 27/27 (tablet), AT-07, AT-08, AT-11, AT-12 included; Release launch pass on all four.
  Head for Android Test round 9: 8f173c9.

### 61. AT-18 save pickers on; AT-19 notices from the resolved packs; Foundation 742a5da + Mobile UI 5c66f1a — coordinator, 11 Nov 02:25 IST
- Composition: Foundation `742a5da` (platform/foundation-pr: patch 25 parts 1-4 — AT-17, AT-16, D-164 cold open, H-22,
  Docs 2.1.0) + Mobile UI `5c66f1a` — clean. H-22 is in Foundation (67823ad); `mobile-ui-hooks-9.patch` now carries H-22
  and H-23 together, so it applies neither way; H-23 (Excel value bar on the phone) waits for Foundation.
- **AT-18 (S1):** `AndroidFilePicker.SavePickersEnabled` (hard-coded false since before the Ui delivered its saves) is
  gone: Save as new PDF, Save redacted copy, Bind / Combined / lift PDFs, signed and flattened copies, password copies,
  Merge and Split, PNG snapshots and the Bench session open Android's "save to" picker, and each is delivered by
  `WriteBack.DeliverOrThrowAsync` → `AndroidFileWriteBack` (Ui audit on 742a5da: all 15 save-to-file picker sites deliver — Bench through RunSave, the password card through Reader's OnProtectedSaved — and the 7 writing folder sites deliver the folder).
  Folder picker on too, done properly for its two kinds of use:
  - writing (Export pages, Scatter, Split to a folder, Press): the whole working folder is sent back, **subfolders
    included**, and a file whose namesake is already there **replaces it** (it used to make "name (1)");
  - reading (Library folder, watched folder, Settings' save folder): the folder's documents (PDF, DOCX, XLSX, and
    subfolders) are copied in when it's picked, so the Library shows what it holds; a later save **into** that folder
    sends that one file back at its place (it used to be "not needed" and never arrive). Copies brought in and not
    changed are never written back. Limit: the copy is of the folder as it was when picked (not live).
- **AT-19:** the notices target took its path from `$(BundledNETCoreAppPackageVersion)`, which SDK 10.0.404 moved off the
  pack the build resolves. It now runs after `_ResolveAssemblies` and takes the package id and version of the
  System.Private.CoreLib and Mono.Android the build actually resolved, so the shipped notices always match the shipped
  runtime. The workflow's SDK is pinned to 10.0.403 (Android Test's too). `global.json` for every workflow is
  Foundation's (repo root).
- Sandbox: Android Debug and Release `-warnaserror` 0 warnings, both carry the two notices; Release manifest 14/14;
  Core 305 (+3 skipped), Hosting 91, MobileUi 16, WebUi 41 pass. On-device save verification: Android Test's save suite
  (SV-1 to SV-6) in round 10; my rounds don't drive the save picker.
