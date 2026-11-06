# Mac — build log

Chuvadi Reader on macOS: .NET MAUI Blazor Hybrid, Mac Catalyst, universal (arm64 + x64),
hosting the unchanged `ChuvadiReader.Ui` in WKWebView. Branch `platform/mac`.

---

## 2026-11-06 — Session 1: baseline and host project

### 1. Environment
- Sandbox: Linux x64, no Mac. `.NET SDK 10.0.403` installed with Microsoft's `dotnet-install.sh`.
- Mac Catalyst cannot be compiled on Linux (the `maccatalyst` workload is macOS-only). **All Mac
  host code is first compiled on the GitHub Actions macOS runner** (`.github/workflows/mac.yml`).
- Working repo `Sthraas/chuvadi-reader-platforms`: **not reachable yet** from this session
  (`git ls-remote` → auth prompt; `add_repo` → no access). Work is committed locally on
  `platform/mac` and will be pushed once access is granted.
- Base: `arunshivab/chuvadi-reader` main at `c7b9e44` (chuvadi-pdf 3.31.1 + Chuvadi.Fonts 1.0.0).

### 2. Baseline of what the Mac host inherits (Linux, no changes)
```
dotnet build src/ChuvadiReader.Ui/ChuvadiReader.Ui.csproj --configfile ci/nuget.config -c Release
  → Build succeeded, 0 warnings, 0 errors
dotnet restore tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj --configfile ci/nuget.config
dotnet test  tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj -c Release --no-restore
  → Passed: 161, Failed: 0
```
The existing `ci.yml` already builds Core/Ui and runs these tests on `macos-latest`, so Core and Ui
are known to build and pass on macOS. `ci.yml` is left untouched; the Mac host has its own workflow.

### 3. What the platform layer is
Core already defines the host interfaces. The Windows host implements them in
`src/ChuvadiReader.Windows/Platform`. The Mac host implements the same set:

| Interface (Core) | Windows | Mac (new) |
|---|---|---|
| `IAppStorage` | FileAppStorage (%AppData%\Chuvadi) | FileAppStorage — copied unchanged, at `~/Library/Application Support/Chuvadi` |
| `IFilePicker` | WPF OpenFileDialog/SaveFileDialog | MacFilePicker — native NSOpenPanel/NSSavePanel, same titles and file types |
| `IImageClipboard` | WPF Clipboard | MacImageClipboard — UIPasteboard, PNG bytes as `public.png` |
| `IExternalLinks` | Process.Start | MacExternalLinks — UIApplication.OpenUrl (http/https/mailto only) |
| `IUiScale` | WebView2 ZoomFactor | MacUiScale — WKWebView.PageZoom |
| `IWindowControls` | user32 drag/min/max | MacWindowControls — AppKit via the Objective-C runtime |
| `IPrintService` | WPF/XPS + Chuvadi rasteriser | **NoopPrintService until Arun decides** the print path |
| file drop | WPF Drop | FileDrop — UIDropInteraction on the WKWebView, in-place file URLs |

### 4. Decisions taken inside new host code (routine)
- **Mac idiom** (`UIDeviceFamily` = 6): Catalyst renders at 100 %, not the iPad idiom's 77 % —
  required for fonts and layout to match the Windows app.
- **Native NSOpenPanel / NSSavePanel** via the Objective-C runtime (libobjc, part of macOS) rather
  than UIKit's document picker: UIKit has no save panel with a name field, and the panels return real
  paths, which Core's path-based `IFilePicker` contract needs.
- **App state location** asked of the OS (NSFileManager), because .NET's
  `SpecialFolder.ApplicationData` maps to `~/.config` on macOS.
- **Not sandboxed** (`Entitlements.plist`) — documents opened and saved by path anywhere, as on
  Windows. App Store distribution would change this (open decision).
- **No trimming** (`MtouchLink=None`) until the libraries declare trim safety (package report,
  decision 4); Sheets' typed import/export loses data when trimmed.
- **Window chrome default = design untouched**: the HTML window dots (top right, already in the Ui)
  drive the real window; native buttons hidden. One switch (`MacChrome.UseHtmlWindowButtons`) — the
  alternative waits for Arun.
- **App icon**: the 256 px PNG frame extracted unchanged from the Windows `chuvadi.ico`
  (to be replaced by the handout's brand asset once readable).
- **Drop list** copied from the Windows host (`.pdf .docx .doc .xlsx .xls`) for parity — see
  finding F1.

### 5. CI (`.github/workflows/mac.yml`, new)
`macos-26` runner → newest Xcode → `dotnet workload install maui-maccatalyst` → restore with
`ci/nuget.config` → tests on macOS → universal build → `lipo` check for arm64 + x86_64 → ad-hoc sign
(`codesign -s -`; arm64 code will not launch without at least an ad-hoc signature) → smoke launch
with `CHUVADI_SMOKE_EXIT=1` (exits after the first Blazor render, prints `CHUVADI_STARTUP` timings to
the job summary) → `ditto` zip + SHA-256 → artifact `Chuvadi-mac-universal-unsigned`.
**Not yet run** — waiting for repo access.

### 6. Findings in existing code (for Arun; nothing changed — rule 4)
- **F1** Windows drop accepts `.doc` and `.xls` (no viewer for them) but not `.md .txt .html`, which
  the Open dialog accepts. Drop and Open disagree.
- **F2** `SessionService` stores under `SpecialFolder.ApplicationData`, which on macOS is
  `~/.config/Chuvadi` — app state would be split between two folders on Mac (and Linux).
- **F3** `FileAppStorage.SetAsync` writes `settings.json` in place; a crash mid-write leaves a broken
  file, which the next start reads as empty — all settings silently lost. A write-to-temp-and-replace
  would fix it.
- **F4** Core still references the umbrella `Chuvadi.Pdf`, `Chuvadi.Docs 1.1.0` and
  `Chuvadi.Sheets 1.1.2`. The package report recommends individual Pdf packages (the umbrella adds
  ~6.7 MB incl. deprecated Fonts.Bundled/Woff2 and PdfA to the Mac app) and Sheets 2.0.1.
- **F5** Shortcut labels in the Ui are fixed text "Ctrl …" (54 lines across Razor, C# and JS). Cmd already works (the JS
  treats `metaKey` as Ctrl), but a Mac user sees "Ctrl K" where macOS expects "⌘K".

---

## 2026-11-06 — Session 1 (continued): working repo, CI, handout

### 7. Working repo
- Access granted. `platform/mac` = `main` (handout + coordination docs) → one commit importing
  chuvadi-reader `c7b9e44` unchanged (tree identical to `platform/web`'s baseline) → Mac commits.
- The handout in `docs/design-handoff/` is byte-identical to chuvadi-reader's `docs/design/revamp-v3`.
- The design note settles the Mac chrome: **traffic lights on the left, app menu in the macOS menu
  bar (File, Edit, View, Document, Window, Help), ⌘ shortcuts.** The earlier "HTML dots drive the
  window" default is replaced accordingly.

### 8. CI runs
| Run | Result | Cause → fix |
|---|---|---|
| 42130951598 | Tests ✔ (161, macOS); build ✘ | Latest workload (Mac Catalyst 27.0) needs Xcode 27.1; runner newest is 26.6 → pin SDK band `10.0.4xx` and workload set `10.0.401` (Mac Catalyst 26.5.10318). Found by reading every 10.0.400-band workload set: 10.0.400–10.0.401 carry 26.5, 10.0.401.1 onward carry 27.0. |
| 42131146081 | build ✘ | `Xcode_26.6.0.app` on the image has no macOS SDK / actool → select the newest Xcode that has both. |

### 9. Mac chrome (handout › Platforms, Shell layout) — host files only
- `wwwroot/index.html` (host's own page) sets `<html data-platform="mac">` and loads
  `wwwroot/css/mac.css`, which hides the Ui's right-hand window dots and starts the top bar after
  the native lights (80 px).
- `MacWindowControls.ApplyChrome`: title text and toolbar hidden, content runs to the top edge;
  the native close/minimise/zoom buttons are placed inside the Ui's 40 px top bar (left 14, pitch
  20, vertically centred; re-applied on resize, key, full-screen exit and scale changes; follows the
  Interface size setting).
- Double-click on the bar still zooms (the Ui's own handler → `IWindowControls.ToggleMaximize`).

### 10. macOS menu bar — host files only
Built in `AppDelegate.BuildMenu` from the commands the Ui already publishes into Core's
`ShellService` (id, group, label, shortcut, action, disabled reason); rebuilt when the published set
changes, enabled state checked each time a menu opens. Actions run through
`BlazorWebView.TryDispatchAsync`, i.e. exactly like the click in the Ui.
- **File**: Open, Close, Save marks, Save as new PDF, Print, Show in folder, Copy file path, bench session.
- **Edit**: standard macOS (Undo, Redo, Cut, Copy, Paste, Select All); Edit › Find removed so ⌘F
  reaches Chuvadi's Find.
- **View**: modes (Read/Mark/Arrange/Protect), View group, reading panels, Go to, Find or do anything… ⌘K,
  plus the system's Enter Full Screen.
- **Document**: the Document ▾ items of the active page, then submenus for Mark, Protect, Arrange, Tools.
- **Window**: standard macOS. **Help**: macOS menu search only.
- Shortcuts: every "Ctrl …" becomes ⌘ (Shift → ⇧, Alt → ⌥). Single-key shortcuts (R, 1–4) stay
  with the page so typing is never captured. macOS-owned keys (⌘C/V/X/A/Z/Q/H/M/,) are never taken.
  A key used by two commands is bound once (the first in menu order).

---

## 2026-11-06 — Session 1 (continued): first green build, Foundation kit

### 11. More CI runs
| Run | Result | Cause → fix |
|---|---|---|
| 3–6 | build ✘ | C# errors (IFilePicker clash with MAUI's, menu-builder API names, a lambda named `_`) fixed; then Xcode: the pinned pack 26.5.10318 needs **Xcode 26.6**, and the image's `Xcode_26.6.0.app` fails the build's SDK lookup → select `/Applications/Xcode_26.6.app` by name. |
| 9 | build ✔, lipo ✘ | The bundle is `Chuvadi.app` (ApplicationTitle) → locate the shallowest `.app` and its CFBundleExecutable from the build output. |
| 10–11 | smoke ✘ | `_mainSceneIdentifier should have been set` — a Catalyst app launched by running its binary directly gets no scene. Smoke now launches through LaunchServices: `open -W -n --env CHUVADI_SMOKE_EXIT=1 --stdout … Chuvadi.app`. (The scene manifest removed in the same step was not the cause; MAUI manages scenes, so it stays out.) |
| **42135527900** | **✔ all steps** | universal (x86_64 + arm64), ad-hoc signed, launched to first render, artifact uploaded. Foundation's `platforms` workflow (shared code on 4 OSes, Windows app, pack check) ✔ on the same commit. |

### 12. Rebased on `platform/foundation`
- Skipped my own baseline import (Foundation's import of the same `c7b9e44` + Group A supersedes it).
- Host now uses the kit: `AddChuvadiReader(AppStateLifetime.Process)` (no duplicated service list),
  `IPlatformInfo` = `FixedPlatformInfo(MacOS, mouse+keyboard, buttons Left, NativeMenuBar, TitleBarDrag,
  desktop capabilities, MacKeyLabels)`, `IClipboard` + `IImageClipboard` (`MacClipboard`, NSPasteboard),
  `IFileManager` (`MacFileManager`, Finder reveal via NSWorkspace), `IAppPaths` (`MacAppPaths`).
- **Window chrome**: per HANDOFF the Ui draws the traffic lights on the left (Group A `WindowButtons`, handout
  15 px / gap 9). The host hides the native title bar completely (buttons and the invisible strip that would take
  clicks on the top of the page) and moves/minimises/zooms/closes the real window through AppKit. The earlier
  native-button repositioning and the host `mac.css` are removed.
- **Menu bar** now built from `IAppCommands` (Foundation's `ShellAppCommands`): Document menu keeps the Ui's order
  and separators; items run through `InvokeAsync(id)` on the Blazor dispatcher; Immersive takes ⌃⌘F and replaces
  the system Enter Full Screen item (decision 6 Nov).
- Host page: same shape as Windows; `theme.js` comes from the Ui (`_content/ChuvadiReader.Ui/js/theme.js`).
- Drop accepts the Open panel's types (HANDOFF; F1 for the Mac).

### 13. Printing (decision 6 Nov: native panel, vector)
- New Core file `Reader/PrintDocumentBuilder.cs`: chuvadi-pdf opens the file (password if any) and
  `PageOperations.Assemble` writes exactly the requested pages in order, unencrypted, still vector. Reusable by
  Android and Web. 5 new tests (`PrintDocumentBuilderTests`); suite 166/166.
- `MacPrintService` hands that PDF to `UIPrintInteractionController` (the macOS print panel). Copies, paper,
  scaling and printer are chosen in the panel.

### 14. Size — 519 MB → 166 MB
`MtouchLink=SdkOnly`: only .NET's own framework is trimmed; Chuvadi libraries and app code untouched.
Bundle 165.8 MB (native executable 109.5 MB for both architectures, MonoBundle 52.2 MB, web assets 4.1 MB);
download zip 47 MB.

### 15. Startup (CI Apple Silicon runner, cold first launch, ms since process start)
| main | MAUI built | window | WebView ready | first render |
|---|---|---|---|---|
| 148 | 403 | 421 | 556 | 2434 |
The 1.9 s from WebView ready to first render is Blazor starting inside WKWebView on a cold runner; to be
measured on a real Mac and optimised next.

### 16. Findings for Foundation / Core (no existing file changed)
- **F6 (bug, Mac Catalyst)**: `OperatingSystem.IsMacOS()` is **false** under Mac Catalyst (`IsMacCatalyst`/`IsIOS`
  are true). Effects: the kit's `DesktopAppPaths` would put Mac app data under `~/.config` (the Mac host registers
  `MacAppPaths` instead); Core `CertificateSignService.cs:117` picks `EphemeralKeySet`, which macOS doesn't support
  (signing with a .pfx would fail on Mac); `PasswordService.cs:185` uses case-sensitive path comparison on Mac.
  Fix: test `OperatingSystem.IsMacOS() || OperatingSystem.IsMacCatalyst()`.

---

## 2026-11-06 (afternoon) — Session 2: decisions D-01…D-54 applied

### 17. Rebased on `platform/foundation` (Groups B and C)
Picks up write-back at every save, host folders, account, individual chuvadi-pdf packages (F4), F1–F3,
MainLayout platform attributes, `FileAppStorage` moved into the kit (atomic write, F3). Still waiting on
Foundation for chuvadi-pdf 3.31.2 (D-54) and the Mac Catalyst `IsMacOS()` fixes (F6) — rebase again then.

### 18. Host changes for the newer HANDOFF
- Host page sets `<html data-shell="desktop" data-platform="macos" data-form-factor="desktop"
  data-input="mouse keyboard">` so the first paint is already the Mac layout.
- Mac copy of `FileAppStorage` removed; the kit's `ChuvadiReader.Hosting.Desktop.FileAppStorage` is used.
- `IShare` → `MacShare` (the macOS share sheet, anchored at the top bar).
- Incoming files in one place, `MacIncomingFiles`: Finder drop, Finder "Open With" (while running and at
  launch, via the scene lifecycle events) → Bench when open, else Reader (first file, as the Windows
  drop). Files that arrive before the first render wait for it.
- Info.plist `CFBundleDocumentTypes`: the Open panel's types (PDF as Editor, the rest as Viewer), rank
  **Alternate** — Chuvadi is offered in Open With but never takes over a type by itself.
  `LSSupportsOpeningDocumentsInPlace` so the original file arrives, not a copy.

### 19. Print fidelity (b) — approved
`PrintDocumentBuilder` now flattens the whole document with `AnnotationFlattener` (all kinds, chuvadi-pdf's
generated appearances where the file's are missing or stale, `DropRemainingAnnotations` so nothing stays
live for macOS to draw its own way), then assembles the chosen pages. Still vector. New test
`Annotations_are_baked_into_the_page_and_none_stay_live` (red square annotation → no annotations left,
red pixels in the page). Suite 167/167; Hosting 27/27.
Residual gaps → library asks (`LIBRARY-ASKS.md`): L-1 embed missing fonts; L-2 flatten with print rules.

### 20. Docs
`REAL-MAC-CHECKS.md` — the checklist for the real Mac at the end. `LIBRARY-ASKS.md` — L-1, L-2.

### 21. CI after session 2 changes
- 42201356763 ✘ — `SceneOpenUrl` handler must return bool → fixed.
- **42201712779 ✔** — tests 167/167 on macOS, universal (x86_64 + arm64), launched to first render.
  Foundation's `platforms` workflow ✔ on the same code (42201356891).
- Size with individual Pdf packages (F4): bundle **155.8 MB** (native 106.5, MonoBundle 45.3, web 4.1),
  download **42 MB** (was 165.8 / 47).
- Startup (CI, cold, ms since process start): main 131 · MAUI built 348 · window 364 · WebView ready 491 ·
  **first render 1672** (was 2434).

---

## 2026-11-06 (night) — Session 3: chuvadi-pdf 3.31.2, startup options

### 22. Rebased on `platform/foundation` at 63af90f
chuvadi-pdf 3.31.2 (D-54), combined hooks (D-26; COMBINED-HOOKS.md: "Mac: nothing to change"), Mac
Catalyst `IsMacOS()` fixes in CertificateSignService and PasswordService (F6). Clean rebase. Core 167/167,
Hosting 28/28 on Linux with warnings as errors.

### 23. Bundle size — breakdown and options (for the coordinator)
Bundle 155.8 MB / download 42 MB with `SdkOnly`; 519 MB with no trimming.

| Part | MB |
|---|---|
| `Contents/MacOS/ChuvadiReader.Mac` — native code for arm64 + x64 (incl. AOT-compiled managed code on arm64) | 106.5 |
| `Contents/MonoBundle` — managed assemblies (20.2 in per-architecture copies), AOT data | 45.3 |
| `Contents/Resources/wwwroot` — fonts, CSS, JS | 4.1 |

| # | Option | Pros | Cons |
|---|---|---|---|
| 1 | Framework-only trimming (`SdkOnly`, in place) | Standard .NET Release setting for Apple targets; Chuvadi libraries and app code untouched; 519 → 156 MB | Leaves ~156 MB |
| 2 | Drop unused Chuvadi packages (F4, done by Foundation) | Zero risk | Already taken (166 → 156) |
| 3 | Full trimming (`MtouchLink=Full`) | Largest further cut | Unsafe until the libraries declare trim safety (decision 4); Sheets' typed import/export loses data when trimmed |
| 4 | Separate Intel and Apple Silicon downloads | Each roughly half | Two downloads and a choice for the person; universal approved and the Mac norm |
| 5 | Interpreter instead of AOT | Bundle 155 → 44 MB (measured) | First render +17 % (1.80 → 2.10 s, §26) and slower document work |

Recommendation: 1 now (in place), 3 after the libraries are trim-annotated; not 4 or 5.

### 24. Startup — the Mac Catalyst equivalent of ReadyToRun (D-50)
ReadyToRun is a CoreCLR image format; .NET for Mac Catalyst runs on **Mono**, so it does not apply. The SDK's
own levers are how managed code is compiled: AOT (Release default on arm64), LLVM-optimised AOT, or the
interpreter. First attempt (`mac-startup.yml`, one runner per variant, six launches each):

| Run | default AOT, warm median | AOT + LLVM | interpreter |
|---|---|---|---|
| 42270911133 | 755 ms | 1892 ms | 2089 ms |
| 42271962808 | 1857 ms | 2048 ms | 1036 ms |

**The two runs contradict each other** — hosted runners differ machine to machine, so per-variant jobs are
not comparable. Bundle sizes from the second run are reliable: **AOT 155 MB · AOT+LLVM 188 MB ·
interpreter 43 MB**. The workflow now builds all three on one runner and launches them in 12 interleaved
rounds (A B C, A B C…) — results in §26.

### 25. CI warnings
Each job warned that `actions/checkout@v4`, `setup-dotnet@v4`, `upload-artifact@v4` target the deprecated
Node.js 20. Mac workflows moved to `checkout@v7`, `setup-dotnet@v6`, `upload-artifact@v7` (Node 24; same
inputs). Foundation's `ci.yml` / `platform-build.yml` still use v4 — reported, not changed (not my files).

### 26. Startup — fair comparison (run 42272891752: one runner, 12 interleaved rounds)
| Variant | bundle | first render, median of rounds 2–12 | min–max | WebView ready (median) |
|---|---|---|---|---|
| **AOT (default, in use)** | 155 MB | **1799 ms** | 1756–2297 | 243 ms |
| AOT + LLVM | 188 MB | 1812 ms | 1726–2069 | 257 ms |
| interpreter | 44 MB | 2103 ms (+17 %) | 1999–2425 | 374 ms |

- LLVM: no startup gain, +33 MB → not used.
- Interpreter: −111 MB bundle for ~0.3 s slower start (and slower document work, unmeasured) → a size/speed
  trade-off for the coordinator (startup is the stated priority, so AOT stays meanwhile).
- In every variant ~1.5 s of the time is between WebView ready and Blazor's first render — the next
  startup target (shared Ui/Blazor start, not Mac-specific).
- Round-1 numbers include first-launch system work (Gatekeeper/LaunchServices registration) and are not a
  fair compare.

---

## 2026-11-07 — Session 4: second combined patch, single instance, print permission

### 27. Rebased on `platform/foundation` at 2fafb60
Second combined patch (open queue F-3, print permission L-8, wording, save-folder fallback) and
Chuvadi.Print 1.0.0-rc.2 in the feed. Core 178/178, Hosting 33/33 on Linux with warnings as errors.

### 28. Decisions applied
- **Size (coordinator):** keep AOT (faster start) and framework-only trimming; full trimming later, when the
  libraries are trim-annotated. Interpreter not taken. No change needed — this is what ships.
- **Single instance, tabbed (programme-wide):** macOS LaunchServices hands a file opened while Chuvadi runs
  (Finder Open With, double-click, a drop on the Dock icon) to the running app through `SceneOpenUrl`; the
  app has one scene, so there is never a second window. `MacIncomingFiles` now requests **every** file, so
  each opens in its own tab (Bench open → all join the shelf).
- **Print permission (L-8):** `PrintDocumentBuilder` checks `PrintPermission.Allows` right after opening and
  throws `PrintRefusedException` before any work; `MacPrintService` returns the same Failed result and
  message as Windows, and the macOS panel never opens. Shared, so Android and Web get it. New test
  `A_file_whose_permissions_forbid_printing_is_refused_before_any_work`.
- **Licence (proprietary, free):** waiting for Foundation's LICENSE and EULA; then the bundle gets
  `NSHumanReadableCopyright` and both files in `Contents/Resources`.
