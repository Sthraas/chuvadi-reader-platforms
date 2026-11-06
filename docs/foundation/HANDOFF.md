# Foundation hand-off

For every platform chat (Mac, Linux, Android, Web) and the UI chats (Mobile app UI, Web portal UI). Branch `platform/foundation` on `Sthraas/chuvadi-reader-platforms`; base your branch on it. Decisions F-1…F-7 are final (coordinator, 6 Nov 2026) — see `PLATFORM-INTERFACE.md` §8.

## 1. What is in place
- `src/ChuvadiReader.Platform` — the contract (no dependencies, trim/AOT clean).
- `src/ChuvadiReader.Hosting` — `services.AddChuvadiReader(lifetime)`: every Core service, plus defaults for every seam; `ShellAppCommands` (menu-bar commands from the shell registry); desktop defaults (`DesktopAppPaths`, `LocalAccount`, `CtrlKeyLabels` / `MacKeyLabels`, `FixedPlatformInfo`).
- Groups A, B and C applied: MainLayout publishes `<html data-shell data-platform data-form-factor data-input>` on non-Windows hosts and re-renders on form-factor changes; window buttons, status text and key labels follow the platform; every save delivers through `IFileWriteBack`; host folders, account, gating; Windows registers through the kit.
- Startup: `STARTUP.md` (measured before/after; the branch adds no ReadyToRun startup cost).
- Combined hooks (D-26) applied: phone shell, touch support, portal account menu, server wording and paths, D-35/37/39/42/46/48/52 — `COMBINED-HOOKS.md` (what each chat must update is at its end).
- Windows publishes ReadyToRun (D-50); see §2a for your host.

## 2. Writing a host
```csharp
services.AddChuvadiReader(AppStateLifetime.Process);          // Web: AppStateLifetime.PerConnection
services.AddSingleton<IPlatformInfo>(…);                       // kind, form factor, input, chrome, capabilities, key labels
services.AddSingleton<IAppStorage>(…);                         // required
services.AddSingleton<IFilePicker>(…);                         // required — returns readable LOCAL paths (F-1)
services.AddSingleton<IImageClipboard>(…);                     // required
services.AddSingleton<IClipboard>(…);                          // required (text + image)
// as the platform supports them (defaults are safe no-ops):
// IPrintService, IWindowControls, IUiScale, IExternalLinks, IFileWriteBack, IAppPaths, IAccount,
// IAppLifecycle, IFileManager, IShare
```
A registration after `AddChuvadiReader` wins.

### 2a. Publish for startup speed (D-50)
Startup speed is a priority: publish precompiled so the app doesn't JIT-compile at launch. Measured on the shared code: ReadyToRun cuts Core/Ui startup work by about a third (JIT-compiled methods 1,415 → 357); app DLLs grow about 2.5× (Windows publish 43 → 52 MB).

| Host | How | Status |
|---|---|---|
| Windows | `<PublishReadyToRun>` in `ChuvadiReader.Windows.csproj`, only when publishing; `dotnet publish` defaults to win-x64, `-r win-arm64` for Arm | done |
| Linux | the same block in your host csproj with `linux-x64` (and `-r linux-arm64`) | Linux chat |
| Web (server) | the same block with `linux-x64` for the server publish | Web chat |
| Mac | check what the .NET for macOS / Mac Catalyst SDK offers for Release (ReadyToRun or AOT) and measure launch with and without | Mac chat — report the numbers |
| Android | ReadyToRun does not apply; keep the Release default (profiled AOT) and measure launch | Android chat |

The block to copy:
```xml
<PropertyGroup Condition="'$(_IsPublishing)' == 'true'">
  <PublishReadyToRun>true</PublishReadyToRun>
  <RuntimeIdentifier Condition="'$(RuntimeIdentifier)' == ''">linux-x64</RuntimeIdentifier>
  <SelfContained Condition="'$(SelfContained)' == ''">false</SelfContained>
</PropertyGroup>
```
Check a published DLL is precompiled: its CLI header has a ManagedNativeHeader (non-zero). Measure with `tools/StartupProbe` (shared part) plus your own window-shown time.

### What each host must provide

| Seam | Mac | Linux | Android | Web |
|---|---|---|---|---|
| `IPlatformInfo` | `MacOS`, Desktop, buttons **Left**, `NativeMenuBar`, `MacKeyLabels` | `Linux`, Desktop, buttons from the desktop's layout, radius 12 | `Android`, Tablet/Phone (+ `FormFactorChanged`), Touch/Pen | `Web`, form factor from the browser width (+ changes), `AccountMenu`, `ServerSide`, `SavesAsDownload`; `MacKeyLabels` for Mac browsers |
| `IFilePicker` | NSOpen/SavePanel → real paths | GTK/portal dialogs → real paths | SAF → copy into app storage, return that path; remember the URI for write-back | upload → session-only encrypted working copy, return its path; `PickFolderAsync` → a fresh empty session folder, no dialog (its files are delivered as one download) |
| `IFileWriteBack` | default (none) | default (none) | write the working file back to its URI (folder picks: to the tree) | browser download (Save and Save as) |
| `IAppPaths` | default (`~/Library/Application Support/Chuvadi`) | default (XDG) | app files / cache dirs | per-session encrypted folder; `DefaultSaveFolder` null |
| `IPrintService` | OS print panel with the PDF (vector) | PDF as-is to CUPS, raster fallback, PrintCard dialog | `PrintManager` with the PDF | browser print of the PDF |
| `IWindowControls` | native window (traffic lights drawn by the Ui on the left) | native window | — | — |
| `IClipboard` / `IImageClipboard` | NSPasteboard | GTK clipboard | ClipboardManager | browser clipboard (HTTPS) |
| `IAccount` | default | default | default | Sangam identity |
| `IAppLifecycle` | — | — | suspend/resume/back | page close = suspend |
| `IFileManager` | Finder reveal | file manager (D-Bus `ShowItems`) | — | — |
| `IShare` | share sheet | — | share sheet | — |
| Menu bar | build from `IAppCommands` (below) | — | — | — |

Files arriving from outside (drop, Open with, share intent, macOS open-file, upload): `BenchDropService.Drop(paths)` when `IsBenchActive`, else `OpenDocumentService.Request(path)` — working paths per F-1. Accept the same types as the Open dialog (Group C fixes the Windows list to match).

Host page: copy the Windows `wwwroot/index.html` shape; load `_content/ChuvadiReader.Ui/js/theme.js` before the Blazor script; disable page zoom/pinch in the web view (the Reader zooms the canvas itself). **Put your initial `data-shell`, `data-platform`, `data-form-factor` and `data-input` on `<html>` in the host page** (Web: computed from the request / a tiny inline script; Android: from the device) so the first paint already has the right layout; MainLayout keeps them in sync afterwards with one `chuvadiTheme.setPlatform` call. Windows sets none (absent = Windows desktop) and makes no call — zero startup cost. **Tablet and phone hosts (Android; Web when it serves small screens) also link `_content/ChuvadiReader.Ui/css/mobile.css`**; desktop hosts must not (every rule in it is keyed on `data-shell`, but it is one more file to load).

## 3. macOS menu bar — `IAppCommands` (decided: filled host-side from `ShellService`, no Ui hook)
- `Commands`: everything the Ctrl K bar can run now (global + the mounted page's) — `Id`, `Label`, `Group` (File, Tabs, Document, Read, Mark, Arrange, Protect, View…), canonical `Keys`, `IsEnabled`, `DisabledReason`.
- `DocumentMenu`: the Document ▾ items in order, `IsSeparator` for dividers.
- `Changed`: rebuild the menu (or just its enabled states) on every raise.
- `InvokeAsync(id)`: runs it; returns false for unknown/disabled. Call it on the Blazor dispatcher (`BlazorWebView.Dispatcher.InvokeAsync`).
- Show shortcuts with `IPlatformInfo.Keys.Format(keys)` → ⌘ glyphs.
Tests: `tests/ChuvadiReader.Hosting.Tests` (`App_commands_come_from_the_shell_registry`, `Document_menu_keeps_order_and_marks_separators`, `Invoke_runs_enabled_commands_only`).

## 4. Package feed
Packages come from chuvadi-reader's committed `ci/packages` (byte-identical to the Windows app).
`scripts/setup-feed.sh` copies them to `./localpackages`; `--verify-pack` additionally checks that chuvadi-pdf v3.31.1 re-packs to the same 34 package names and versions (a check only). Missing packages your host needs (e.g. Chuvadi.Print rc.2 for Linux) are added to `ci/packages` from their GitHub release with the checksum recorded — ask the coordinator; that folder is an existing part of the repo.

## 5. CI
- `.github/workflows/platforms.yml` runs on `platform/**`: shared code on ubuntu x64, ubuntu arm64, macOS, Windows; the Windows app; the pack check. All `-warnaserror`.
- Add your host job with the template:
```yaml
  mac:
    uses: ./.github/workflows/platform-build.yml
    with:
      runner: macos-latest
      label: mac
      build: src/ChuvadiReader.Mac/ChuvadiReader.Mac.csproj
      workloads: maui-maccatalyst      # android: maui-android
```
- `ci.yml` (main only) is unchanged.

## 6. For Arun's final check on Windows (after the platform pushes)
1. `dotnet build ChuvadiReader.slnx -c Release` → 0 warnings; `dotnet test` → all pass.
2. Start the app: maximised as before, top bar unchanged, window buttons at the right; minimise / maximise-restore (icon flips) / close; drag the top bar; double-click it to maximise.
3. Settings › Appearance: all 5 themes, interface size 100 / 125 / 150, reduce motion.
4. Reader: Ctrl W, Ctrl Shift W, Ctrl Alt W, Ctrl Tab, Ctrl 1-9, Ctrl + / − / 0, Ctrl F, Ctrl Z; Ctrl K command bar shows "Ctrl …" keys.
5. Document ▾ › Copy file path, then paste somewhere.
6. Status bar still says "offline · on this device".
7. Combined hooks (D-26): the status-bar clock ticks every second; Home, Library and Settings › About still show the folder paths and the Watched folder card; reopen the app with two tabs open — each file appears once.
8. ReadyToRun (D-50): `dotnet publish src/ChuvadiReader.Windows -c Release` → output in `bin/Release/net10.0-windows10.0.19041.0/win-x64/publish`; the published app starts and works; `pwsh scripts/measure-startup.ps1` vs `-ReadyToRun` to see the gain.

## 7. Blockers (library — Arun's decisions)
- Layout not released; `Layout.Pdf` pins chuvadi-pdf [3.30.2] — Word/Excel exact view, Save as PDF and their printing.
- Pdf A (name table never shrinks), Pdf B (LiPi FontRenderer race) — before Web multi-user load.
- Docs 2.0.0 pending (Docs stays 1.1.0).
- **Known gap — Windows printing is raster** (`WpfPrintService` renders pages to images), against Arun's vector rule. Existing Reader behaviour, out of platform scope (coordinator, 6 Nov). Move it to Chuvadi.Print's vector XPS route when `Chuvadi.Print` 1.0.0-rc.3 is released. No change now.
