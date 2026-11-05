# Linux build log

## 2026-11-06 — Session 1: host proven end to end

### 1. Inputs read
- Kickoff + rulebook (`docs/coordination/RULEBOOK.md`), package report, `DESIGN-NOTE.md`, handout README
  ("Linux: same as Windows, 12 px window corners, honour GNOME/KDE button layout").
- chuvadi-reader `main` at `c7b9e44` (chuvadi-pdf 3.31.1 + Chuvadi.Fonts 1.0.0).
- Windows host (`ChuvadiReader.Windows`): ~1,500 lines over eight Core interfaces — `IFilePicker`,
  `IImageClipboard`, `IPrintService`, `IAppStorage`, `IUiScale`, `IExternalLinks`, `IWindowControls`,
  `IAppReadySignal`. The Linux host implements the same set.
- Foundation's `PLATFORM-INTERFACE.md`: not published yet. Building the host directly, as instructed.

### 2. Sandbox
Ubuntu 24.04.5, x64, 2 cores, 7 GB, no GPU.
```bash
apt-get install dotnet-sdk-10.0 libgtk-4-dev libwebkitgtk-6.0-dev libwebkit2gtk-4.1-dev xvfb mutter imagemagick dbus-x11
```
.NET SDK 10.0.114 (Ubuntu package). WebKitGTK 2.52.6. Xvfb, mutter, imagemagick: test only.

### 3. Existing projects on Linux
`ChuvadiReader.Core` and `ChuvadiReader.Ui` build unchanged on Linux: 0 warnings, 0 errors.
All 161 tests in `ChuvadiReader.Tests` pass on Linux.

### 4. GTK / WebKitGTK availability (packages.ubuntu.com, checked today)
| Ubuntu | WebKitGTK 4.1 (GTK 3) | WebKitGTK 6.0 (GTK 4) | GTK 4 |
|---|---|---|---|
| 22.04 jammy | 2.50.4 | 2.50.4 | 4.6.9 |
| 24.04 noble | 2.52.6 | 2.52.6 | 4.14 |
| 26.04 resolute | 2.52.6 | 2.52.6 | 4.22 |

Decision pending with Arun (see status). The host is written against GTK 4 + WebKitGTK 6.0.

### 5. WebViewManager API (Microsoft.AspNetCore.Components.WebView 10.0.0)
Abstract `NavigateCore(Uri)`, `SendMessage(string)`; protected `MessageReceived(Uri, string)`,
`TryGetResponseContent(...)`. It serves `_framework/blazor.webview.js` itself and resolves
`_content/...` through the static-web-assets manifest internally (`StaticWebAssetsLoader`), so a host
supplies only a window, a URI scheme and a message pipe.

### 6. Native shim — `src/ChuvadiReader.Linux/native/chvdhost.c` (new)
GTK 4 window (custom chrome: empty hidden titlebar keeps CSD frame and resize edges), WebKitGTK 6.0
view, `app://` scheme (registered secure + CORS-enabled), bridge user script defining
`window.external`, script-message handler, navigation policy (only `app://localhost` loads; user
links go to .NET → `IExternalLinks`), window-level file drop (capture phase), begin-move from the last
press, clipboard image, `GtkFileDialog` (portal), coalesced thread-safe wake.
Ephemeral network session: nothing on disk, so an update can never be served stale assets (the
problem `WebViewCache` solves on Windows).
Built with `-Wall -Wextra -Werror`. 17+ exports, ~40 KB.

### 7. .NET host — `src/ChuvadiReader.Linux` (new)
- `Program.cs`: same service registrations as `App.xaml.cs`; pre-paint colour per theme; opens a
  file passed on the command line after first render; drop rules as Windows (Bench vs Reader).
- `LinuxWebViewManager`: `app://localhost/`, `Dispatcher.CreateDefault()`.
- `GtkHost`: unmanaged callbacks, main-thread queue.
- Platform: `FileAppStorage` (copy of the Windows one, `~/.config/Chuvadi`), `LinuxWindowControls`,
  `LinuxUiScale` (WebKit zoom = whole-window zoom), `LinuxExternalLinks` (`xdg-open`),
  `LinuxImageClipboard`, `GtkFilePicker` (same titles and filters as WpfFilePicker).
- `IPrintService` = `NoopPrintService` until the print design is agreed (card greyed out, not broken).

### 8. Bugs found and fixed in my own code
- Dev build has no `wwwroot` folder → `DirectoryNotFoundException`. Fixed: `NullFileProvider` when
  absent (the manifest supplies the assets).
- I had dropped the host stylesheet link, believing `ChuvadiReader.Windows.styles.css` was a dead link.
  Wrong: the host bundle `@import`s the Ui's scoped CSS. Restored as `chuvadi-reader.styles.css`.
  (Retracted my note about a 404 on Windows — there is none.)

### 9. Result
Home renders identically to the Windows design, maximised, under mutter (screenshot in CI artifacts).

### 10. Startup (published, ReadyToRun, framework-dependent; this VM, software rendering)
| Stage | ms since process start |
|---|---|
| .NET main | 35–88 |
| GTK ready | 124–197 |
| window + web view created | 184–315 |
| window on screen (theme colour) | 337–591 |
| page loaded | 755–1253 |
| Blazor first render | 1277–1815 |

Next: profile page load (WebKit web-process start, CSS/fonts) and Blazor boot.

### 11. Repo
New files only on `platform/linux`. `tools/linux/prepare-tree.sh` overlays them on chuvadi-reader at
`c7b9e44` and fails if any existing file differs. CI: `.github/workflows/linux.yml` (x64 + arm64).
