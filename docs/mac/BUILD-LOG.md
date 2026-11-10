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

---

## 2026-11-07 (morning) — Session 5: legal texts, kit file router; CI on hold

**CI on hold (coordinator, 04:55 IST):** no Mac runs and no pushes until confirmed — macOS minutes cost 10× Linux.
Everything below is built and checked locally; one manual run of the Mac workflow verifies it.

### 29. Rebased on `platform/foundation` at fa9d120
Third and fourth combined patches: legal documents (LICENSE, `legal/`), Licences page, host notices (D-84),
single instance in the kit (`IncomingFiles`, `IAppInstance`, D-83), Back closes card, portal wording.
Core 178/178, Hosting 48/48 on Linux with warnings as errors.

### 30. Legal texts in the bundle (D-82, D-84; HANDOFF "Mac" row)
- `Info.plist` `NSHumanReadableCopyright` = the shared Copyright value.
- `BundleResource` items put `LICENSE`, `legal/EULA.txt`, `legal/THIRD-PARTY-NOTICES.txt` unchanged in
  `Contents/Resources/legal/` (still DRAFT).
- Target `ChuvadiDotnetNotices`, hooked through `CollectBundleResourcesDependsOn` (the extension point the
  .NET for Mac Catalyst SDK documents in Xamarin.Shared.targets; checked in the pinned 26.5.10318 pack),
  copies the Mono runtime pack's `THIRD-PARTY-NOTICES.TXT` and the Mac Catalyst runtime pack's `LICENSE` from
  `@(ResolvedRuntimePack)` — the exact packs the build uses — and fails the build if either is missing.
  The item lookup and first-pack selection were run against a real self-contained build here (linux-x64
  runtime pack 10.0.14) — first-entry selection fixed after a probe showed property batching picks the last.
- `MacHostNotices` (`IHostNotices`, title ".NET runtime") reads both texts on demand, each under its own
  heading, files untouched.
- Mac workflow step **Verify bundle layout**: all five files present, the three repo texts byte-identical
  (`cmp`), DRAFT lines kept, the copyright value exact.

### 31. Kit file router
`MacIncomingFiles` removed; the Mac host now routes Finder drop, Open With, Dock drop and launch files to
the kit's `IncomingFiles` (same behaviour on every platform; it also handles "already ready", so no eager
construction). `MacFileArrivals` only hops onto the Blazor dispatcher once the WebView exists.

### 32. Workflows
`mac.yml` and `mac-startup.yml` are now **manual only** (`workflow_dispatch`), as D-90 proposes for Mac jobs.
Foundation's `platforms` workflow still runs on push (including a macOS job), so pushes stay on hold.

### 33. CI back (D-93) — legal texts verified on the Mac runner
Pushed and ran the Mac workflow by hand. Four runs to get the .NET notices lookup right — each failure was the
build's own guard stopping it, never a silent miss:

| Run | Result | What it showed → fix |
|---|---|---|
| 42314097811 | ✘ | No `Microsoft.NETCore.App` runtime pack in `@(ResolvedRuntimePack)` on Mac Catalyst → use `@(ResolvedFrameworkReference)`'s `RuntimePackPath`, as macios does |
| 42314551631 | ✘ | Universal build's outer step has no RID: framework references carry no runtime pack path → also try `_PackageToDownload` |
| 42314833601 | ✘ | Outer step has no download list either → last resort: the SDK's `KnownRuntimePack` table (Mono pack pattern + exact version), valid in every step |
| 42315095775 | ✘ | Runtime notices found; Mac Catalyst licence then hit the same outer-step gap → `KnownFrameworkReference` "Microsoft.MacCatalyst.Runtimes" (pattern + exact version), packs folder or NuGet cache |
| **42315335992** | **✔** | tests 178/178 on macOS; **bundle layout verified**; universal x86_64 + arm64; launched to first render; artifact 43 MB |

Verified in `Chuvadi.app/Contents/Resources/legal/` (sizes = sources): `LICENSE.txt` 2959, `EULA.txt` 4282,
`THIRD-PARTY-NOTICES.txt` 41491 (all three byte-identical to the repo, DRAFT line kept),
`DOTNET-RUNTIME-THIRD-PARTY-NOTICES.txt` 76623 (Mono runtime pack), `DOTNET-MACCATALYST-LICENSE.txt` 6434
(Mac Catalyst runtime pack, "Xamarin SDK" MIT + third parties). `NSHumanReadableCopyright` exact.
Each lookup step was first run locally against real SDK builds (single-RID and multi-RID) or a packs layout
copied from the pinned SDK before it went to CI.
Foundation's `platforms` workflow green on the same code after rebasing onto a73a898 (its 839571e fixed the
Windows single-instance tests that failed on fa9d120).

## 2026-11-09 — Session 6: Mac Test M-01…M-16 fixed, each with a smoke check on a real macOS runner
Rebased onto Foundation 839d39d. `.github/scripts/mac-smoke.sh` (step "Smoke run (files, menu bar, window, quit)")
launches the built app with `CHUVADI_SMOKE=1`; `Platform/MacSmoke.cs` prints what the app sees and the script asserts it.

| Bug | Fix | Commit | Smoke check |
|---|---|---|---|
| M-01 | Menu bar from IAppCommands: File, View (⌘K, Immersive ⌃⌘F), Document with Mark/Protect/Arrange/Tools; AppKit Format/Find/Enter Full Screen removed | ca3fd1d | View, Document, Print ⌘P ✔ · **Open… ⌘O waits on the shared global-commands patch** |
| M-02 | Scene manifest + `SceneDelegate`; SceneWillConnect/OpenUrl → kit `IncomingFiles`; a launch file is received before Blazor starts instead of being dropped; Platform kept untrimmed (DI-only types had lost their constructors) | ca3fd1d, 69640cb, 09bab61 | launch file → tab; two more while running → tabs 3, one process ✔ |
| M-03 | `MacQuit`: on terminate/scene disconnect, windows let go of MAUI pages before the provider is disposed; a managed exception after quit began ends the process quietly | ca3fd1d | quit leaves no crash report ✔ |
| M-04 | Full-size content view, transparent hidden title bar; `SafeAreaEdges.None` and no scroll-view inset (MAUI kept a 32 pt safe area) | ca3fd1d, 09bab61 | web view top 0, full height ✔ |
| M-05 | `XSAppIconAssets` → Assets.car + CFBundleIconName | ca3fd1d | bundle step: Assets.car, CFBundleIconName ✔ |
| M-06 | WebKit prewarm at launch; marks for WebKit page loads | 09bab61, 44404d5 | prints the breakdown (below) |
| M-07 | 1100×720 centred, clamped to the screen's visible frame | ca3fd1d, 09bab61, e11011b | size (clamped on the 1024×768 runner) and centre ✔ |
| M-11 | Settings… ⌘, in the Chuvadi menu (`go.settings`) | ca3fd1d | **waits on the shared patch** (the command reaches IAppCommands only with it) |
| M-12 | Runtime legal files copied and chmod 0644 before bundling | ca3fd1d | bundle step: every `legal/*.txt` mode 644 ✔ |
| M-14 | `UseSystemResourceKeys=false` — .NET messages stay text | 4cc889d | ObjectDisposedException message is a sentence ✔ |
| M-15 | ⌘O — the File menu gets Open… ⌘O from the shared patch | (shared) | with M-01 |
| M-16 | Same root cause as M-02's crash: trimmed Platform DI types (fixed 69640cb, after the tested 7a65178) | 69640cb | after opening: route /reader, `.reader` rendered, error bar hidden, no Error logs ✔ |

**M-06 breakdown** (run 42522567159, warm launch, ms since process start): main 190 · prewarm load asked 332 ·
MAUI built 365 · window 540 · WebView ready 597 · Ui load asked 618 · **prewarm's empty page loaded 1722** · Ui
navigation starts 1761 · Blazor script 1958 · #app content 2238 · first paint 2443 · ready 2482.
The 1.1–1.4 s hole is WebKit launching its web-content/GPU/network processes: an *empty* page takes 1.4 s from the
request. Our side (main → load asked) is 430 ms. The prewarm cut ~260 ms (WebView ready → navigation 1.42 s → 1.16 s);
it cannot start earlier — CreateMauiApp is the first point UIKit is up. These runners are GPU-less VMs; on a real Mac
WebKit's process launch is expected to be far shorter — added to REAL-MAC-CHECKS.

Shared patches for Foundation (tested on 839d39d): `docs/mac/foundation/M-08-M-09-M-10-mac-conventions.patch`,
`docs/mac/foundation/M-01-M-11-global-commands.patch`.

### 2026-11-09 (03:00) — M-16 and M-02 first (coordinator), checked through the tester's own path
- **M-16 through the Open panel**: the smoke run now starts on Home, presses the left bar's Open button, lets the real
  NSOpenPanel run modally (a modal-mode timer closes it and a fixture stands in for the choice) and checks the Reader for
  PDF (five pages), Markdown, text, HTML, Word and Excel. All six reach /reader with no error bar — on eb26aae, *before*
  any picker change — so M-16's cause was the trimmed Platform DI types (69640cb, after the tested 7a65178), not the
  panel. 6adeb7a still posts every panel to the next run-loop turn (never inside Blazor's click dispatch): defensive,
  not the fix.
- **Found and fixed: HTML documents showed blank on Mac.** MAUI's handler sent the viewer's `<iframe srcdoc>` navigation
  (`about:srcdoc`) to the browser and cancelled it. 31dfe67 keeps `about:srcdoc`/`about:blank` in the WebView, as
  WebView2 does. Proof: run 42527083558 (probe only) `frame=empty` + "error trying to open URL: about:srcdoc";
  run 42527099579 (fix) `frame="Page\nAn HTML file."`, no errors.
- **M-02**: a restored session (tabs saved by the previous launch) comes back first and the handed-over files are added
  after it; checks no longer assume an empty session. Run 42527099579: launch file and running hand-over ✔, one process ✔.
- Run 42527099579 (31dfe67): everything passes except File › Open… ⌘O (M-01/M-15) and Settings… (M-11), which wait on
  the shared global-commands patch.

### 2026-11-09 (04:00) — D-132: error log on the Mac
`Platform/MacErrorLog.cs` + `Platform/LogScrubber.cs` (6b7eeb2): warnings, errors and unhandled exceptions go to
`~/Library/Logs/Chuvadi/chuvadi.log`; at 512 KB it rolls to `chuvadi.1.log` (the older one is replaced) — about 1 MB in
all. Never sent anywhere. Every message is scrubbed: paths and file names → extension + 8-hex HMAC (per-Mac random salt in
the app's data folder, `log-salt`), quoted values (where an exception would quote document text or a password) → `<text
#hash>`, links → scheme and host, messages capped at 400 characters; stack traces keep code names and lose file paths.
Shared code logs nothing itself, so what lands here is framework errors and unhandled exceptions.
Tests: `tests/ChuvadiReader.Mac.Tests` (12, any OS, in the Mac workflow) and the smoke run reads the real file on macOS 26:
written, rolled over after 1.3 MB of warnings, 995 352 bytes total, none of the six opened fixtures' names, no `/Users/`,
no planted secret (run 42528878885). Privacy-notice wording for Foundation:
`docs/mac/foundation/D-132-privacy-notice-mac-log.patch` (new A2a under Part A; A1's "no crash reporting" stays true).

### 2026-11-09 (08:00) — rebased onto Foundation 022b7c0; trimmed Catalyst Release checked (AT-03)
- Rebased cleanly onto 022b7c0 (Docs 2.0.0, Sheets 2.0.2, Word limits D-137, chuvadi-pdf 3.32.0, typed registrations
  D-146). W-02's `host-drop.js` is WebView2-only and not needed: the Mac host takes drops natively (`FileDrop`).
- **The `TrimmerRootAssembly` workaround for ChuvadiReader.Platform is gone** (1d9a026): the bundle now relies on
  Foundation's typed registrations alone, so the launch checks test that fix, not mine. New workflow step "Prove the
  bundle is trimmed" fails if ILLink did not trim Platform or the workaround comes back.
- Run 42548722140 (1d9a026), Release, `MtouchLink=SdkOnly`, universal: Platform trimmed 25 600 → 20 480 bytes on both
  x64 and arm64; the trimmed bundle launches, opens a five-page PDF, Markdown, text, HTML, **Word and Excel** through
  the left bar's Open button and the real Open panel, hand-over at launch and while running, no Blazor error bar and
  no Error logs; quits without a crash report. Core 219/219, Mac 12/12.
  Still failing, as before: File › Open… ⌘O (M-01/M-15) and Settings… (M-11) — the global-commands patch.
- The three Mac patches for Foundation still apply on 022b7c0; with all three applied: Hosting 72/72, WebUi 39/39,
  Core 212/212.

### 2026-11-09 (23:30) — rebased onto Foundation b41f25c; M-17, M-18, M-19, M-21, M-22, M-03 (second form)
Rebased onto `platform/foundation` b41f25c (thirteenth patch with the three Mac patches, fourteenth: pages render off
the Ui thread, D-152). The smoke run now also walks the tester's sequences with **real keys**: `keys.swift` posts
HID key events (Post Event granted on the runner by `grant-post-event.py`, testing only), locked fixtures come from
qpdf (testing only), and the app reports the page after each step (route, Reader, error bar, unlock card, Immersive,
the keys the page received).
- **M-19 (fixed, 55bf376):** MAUI Blazor's renderer reports a component exception only to the page (the error bar,
  and message + .NET stack on `console.error`) and rethrows it into an unawaited dispatcher task — no logger sees it.
  The host page forwards `console.error`, window errors and unhandled rejections to `PageErrorBridge`, which writes
  them to the D-132 log, scrubbed. Smoke: a planted page error lands in `chuvadi.log` with the file name hashed.
- **Found through M-19 and fixed (863d442): Blazor was started twice** ("Blazor has already started" on every
  launch) — MAUI's Mac handler starts it from a WebKit user script, and the page also autostarted it.
  `autostart="false"` on the Mac host page, as MAUI's own templates do.
- **M-22 / D-148 (fixed, 55bf376):** `NSLocalNetworkUsageDescription` = "Chuvadi looks for printers on your network
  only when you open the Print panel. Your documents go only to the printer you choose." Workflow step checks it.
  Privacy-notice line for Foundation: `docs/mac/foundation/D-148-privacy-notice-mac-printers.patch` (A2b).
- **M-03 second form (fixed, 2d2ecd3):** `MacQuit.Detach` replaced the root of *every* window in a scene, including
  UIKit's keyboard window (`UITextEffectsWindow`, root `UIInputWindowController`); its dealloc during AppKit's quit is
  the tester's backtrace (`-[UIKeyboardSceneDelegate inputViews]`). Only windows whose root is MAUI's are detached
  now (after `EndEditing`). The smoke log shows `UITextEffectsWindow … detach=False` and counts crash reports over all
  three quits, two of them after typing in a field: none. The crash was intermittent for the tester; re-verify there.
- **M-17, M-18, M-21: not reproduced on b41f25c.** AES-256 wrong → prompt stays; right → opens; RC4 right → opens
  (real Return each time); real ⌃⌘F → Immersive, real Esc → the page gets `Escape` and leaves Immersive; mode switch,
  Document ▾, ⌘K, Library, then Settings → Settings shows. No error bar, no page errors. A probe with the old quit
  detach (f2575dc, reverted in 6bdc932) passed the same way, so my keyboard-window theory for M-17/M-18 was wrong;
  the tester saw them on c6d7705, before Foundation's thirteenth/fourteenth patches. Mac Test to re-verify.
- **M-11:** `go.settings` reaches the menu code and "Settings… ⌘," is inserted after About, but AppKit's app menu
  does not show it; diagnosis in progress (the builder's app menu is now logged).

### 2026-11-10 (01:00) — rebased onto Foundation bcd1ab1; M-11 fixed; M-18 hunted; M-19 first error
Commit hashes after this rebase: M-19 page errors 5f34138 · M-22 5f34138 · M-03 second form d390abc · Blazor once
a0c478d · reload logged 4a4b419 · M-11 a7c46be.
- **M-11 (fixed, a7c46be):** Settings… ⌘, never showed because `go.settings` was also under View › Go to, and UIKit
  silently drops a menu change that repeats a command already in the bar (same action and id). Settings now lives
  only in the Chuvadi menu, in its own section after About Chuvadi (through the Application menu's children; edits
  aimed at About itself were ignored). Run 42679963336: 38/38 checks, Settings… ⌘, present.
- **M-18 (not reproduced here):** Mac Test narrowed it to Settings › Appearance on macOS 26 and saw the page load again
  with a new WebContent process — WebKit's content process ends, the Blazor session dies with it. My smoke run (same
  image, macos-26-arm64 26.7.2) opens Settings → Appearance → Reading → Appearance, with and without an
  accessibility client reading the app throughout: the page lives, loads once, no WebContent crash report (runs
  42678975900, 42681067751). The AX walk did not reach the web area, so an AX-driven crash is not ruled out — the
  WebContent crash report from Mac Test's run 42676250705 is the next evidence.
- **M-19 (4a4b419):** when WebKit's content process ends, nothing throws first — so a second load of the Ui page is now
  logged as the error ("the page was loaded again … WebKit's content process ended or the page was reset"), ahead
  of the follow-on `MainLayout.DisposeAsync` JS-object error. Page errors (`console.error`, window errors, unhandled
  rejections) were already logged (5f34138).
- Smoke summary fixed for a run with nothing failing (bash 3.2 `set -u` and an empty array), 884b529.

### 2026-11-10 (03:00) — rebased onto Foundation 4f67a4c; D-154 recovery from a WebKit content-process end
- **Cause of M-18 (Mac Test, a5617b4):** on macOS 26 an Accessibility press (VoiceOver, Voice Control, any AX client)
  on Settings › Appearance makes Apple's `-[AXPMacPlatformElement _synthesizeMouseClick:]` index an empty Swift array
  inside the WebContent process → `EXC_BREAKPOINT`, the page is gone. A mouse click works. Apple's bug: report drafted
  in `docs/mac/APPLE-FEEDBACK.md` (FB-1).
- **D-154 (1), done (ac4e1a2):** `Platform/WebContentRecovery.cs`. A proxy in front of MAUI's navigation delegate
  (MAUI sets it after `BlazorWebViewInitialized`, so it is wrapped again 2 s later) answers
  `webViewWebContentProcessDidTerminate:` and forwards everything else to MAUI's delegate by Objective-C message
  forwarding. On termination: chuvadi.log gets "WebKit's content process ended; the page was reopened at <route>", a
  fresh BlazorWebView opens at the same route (`StartPath`, tracked from the WebView's URL; tabs and settings are
  process-wide, so they come back as they were), and the shell shows "Part of Chuvadi stopped unexpectedly and was
  reopened. Your open documents are as you left them." At most 3 times a minute.
  Smoke (run 42694841963, b790370, all 41 checks): Settings › Appearance, then WebKit's content process is killed →
  the end is noticed, the Ui is back on /settings with no error bar, the message shows, chuvadi.log has the line.
- **D-154 (2), not yet:** to try a change that avoids the trigger I need to reproduce it. My Accessibility press
  (`keys.swift ax-press`) does not reach the web content yet (6–167 elements; the Mac Test driver reaches it), so no
  control or role change has been tried. Next: reach the web area the way Mac Test's `macdrive.swift` does, then try
  the press on candidates.
- **D-154 (3), done:** `docs/mac/APPLE-FEEDBACK.md` FB-1 — steps, expected/actual, backtrace, system.
- First-launch hang seen twice on fresh runners (no `main` mark within 120 s, before any Chuvadi code runs; a re-run
  passes) — macOS's first-launch check of an ad-hoc-signed app, not the app. Watching it.

### 2026-11-10 (05:00) — M-21 fixed on the tester's path; M-15 works here
- **M-21 (3daf1ab):** after the Open panel closes the WebView often no longer has the keyboard: ⌃⌘F (a menu
  shortcut) still enters Immersive, Esc reaches nothing. The host page now reports Immersive (a MutationObserver on
  `body.chvd-immersive` → `chvdState`), and `AppDelegate.KeyCommands` carries an Esc command that UIKit offers only
  while Immersive is on (`CanPerform`); it hands Esc to the page, where reader.js calls `Reader.OnEscape` as on
  Windows. While Immersive is off the command is unavailable and Esc goes where it always went. Smoke (run 42712210203,
  re-run): two files through the Open panel, real ⌃⌘F → Immersive on, real Esc → "immersive escape → page" → off.
- **M-15:** on the same run a real ⌘O after the Open panel reaches the File menu's command
  (`menu-command file.open ran=True`), the panel runs and the file opens as a tab. Not reproduced here; the smoke
  run keeps checking it. If Mac Test still sees nothing, the next evidence is whether its ⌘O reaches the app at all.
- First-launch hang (now 3 times, every launch in that run silent): the startup step now prints processes and
  launch logs when it happens (83c2ac8).

### 2026-11-10 (06:30) — rebased onto Foundation fc6286a; M-09, M-14, M-15 checked; M-06 attributed
Run 42727139667 (c3ff2da): 47/47.
- **M-08/09/10:** the thirteenth patch is in this branch (`MacKeyLabels`: F11 → ⌃⌘F, ⌃Tab; WindowButtons "Zoom").
  The Mac host registers `MacKeyLabels` after `AddChuvadiReader`, and every Ui place that shows a shortcut formats it
  (RailButton, CommandBar, Settings › Shortcuts). On the runner the page's View rail button reads
  `title="Immersive (⌃⌘F)"`. Nothing shared is missing; no diff for Foundation.
- **M-15:** real ⌘O works first thing after launch and in the Reader — both reach File › Open a file…
  (`menu-command file.open ran=True`), the panel runs, the file opens. Not reproduced.
- **M-14 recipe for Mac Test:** make a PDF unreadable (`chmod 000 x.pdf`), open it, and open "Details" under "Can't
  read this file": .NET's own message shows ("Access to the path '…' is denied."), not a resource key. Smoke checks it.
- **M-06 — where the ~2.3 s goes** (warm, ms since process start, run 42717566474):
  | Stage | Owner | ms |
  |---|---|---|
  | process start → `main` | host (runtime, dyld) | 0 → 201 |
  | MAUI built, window, WebView ready, page load asked | host | → 796 |
  | **WebKit starts the page's content process; navigation begins** | **Apple (WebKit)** | **→ 2158 (1.36 s)** |
  | blazor.webview.js running | shared | → 2316 |
  | .NET Blazor started, #app rendered | shared | → 2751 |
  | first paint, ready | shared | → 3031 |
  Library: nothing runs before the first render. The biggest block is WebKit launching its process — slow on these
  GPU-less VMs; the prewarm cannot share it (each WKWebView gets its own content process). Host-side room is small
  (~0.6 s of MAUI/runtime start, already AOT). Shared: ~0.7 s of Blazor start and first render. A real Mac
  (REAL-MAC-CHECKS §11) is needed before more work on the WebKit part.

### 2026-11-10 (08:30) — rebased onto Foundation f88f9ef; M-08 and M-23 fixed
- **Cause:** keys that only the page handles did not arrive on Mac. After a panel closes the WebView is often no
  longer first responder (as in M-21), and UIKit uses ⌃Tab for its own keyboard focus moves. The shared side is
  right: reader.js takes ⌃Tab / ⌃⇧Tab before its ⌘ block and ⌘1–⌘9 under `isPrimary`; nothing for Foundation.
- **Fix (48f2f8c), Mac only:** `MacPageKeys` — app-level key commands for ⌃Tab, ⌃⇧Tab and ⌘1–⌘9 hand the key to the
  page's focused element as a keydown, so reader.js decides as on Windows (it ignores keys while typing in a field);
  and the WebView gets the keyboard back after every Open/Save panel and whenever the window becomes key.
- Smoke (run 42741171454): after the Open panel, real ⌃Tab → another tab, real ⌃⇧Tab → back, real ⌘1 → the first tab.
