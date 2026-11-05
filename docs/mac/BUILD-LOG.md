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
