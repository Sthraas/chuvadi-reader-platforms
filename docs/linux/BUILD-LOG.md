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

### 12. CI — first runs
- Build, all 161 Reader tests and ReadyToRun publish pass on **x64 and ARM64** runners.
- Launch failed on both: `bwrap: setting up uid map: Permission denied`. Ubuntu 24.04+ sets
  `kernel.apparmor_restrict_unprivileged_userns = 1` (confirmed on the runner); WebKitGTK's bubblewrap
  sandbox needs a user namespace. **Real Ubuntu 24.04/26.04 desktops have the same restriction**, so
  this is a packaging requirement. My sandbox runs as root without AppArmor, which hid it.
  Fix (new file): `packaging/apparmor/chuvadi-reader` — adds only `userns` for our binary, as Ubuntu
  does for its own browsers; WebKit's sandbox stays on. The `.deb` will install it; CI loads it now.
- An x64 run hung 20 min inside `apt-get install` (mirror). Added apt retries/timeouts and job timeouts.
- With the profile: both architectures launch. x64 shows the dashboard. **ARM64 shows only the theme
  colour** — .NET reports first render, but no page pixels reach the screen. Under investigation.
- The launch test only checked the .NET first-render event, so it passed a blank window. Fixed: it
  now requires a real picture on screen (more than 200 colours) within 10 s of first render.

CI startup (ms since process start, 3 runs): x64 window 297–817, dashboard 1071–1961;
ARM64 window 528–996, first render 1533–2565. First launch on a fresh runner pays a one-time
font-cache cost (`gtk init` 2.1 s once, ~80 ms after).

## 2026-11-06 — Session 2: on the Foundation, printing, packages, full UI pass

### 13. Inputs
- `docs/coordination/DECISIONS.md` (D-01…D-54) on main. Applied to Linux: D-01 packages from
  `ci/packages`; D-02 working path + write-back (desktop: none needed); D-04/D-05 contracts + shared
  `AddChuvadiReader` kit; D-06 printing (PDF as-is to CUPS, raster only as fallback, the app's Print card);
  D-21 Show in folder; D-26 combined hooks (merged); D-39 WebKit dividers (applies to `data-platform="linux"`);
  D-50 ReadyToRun publish; D-54 chuvadi-pdf 3.31.2.
- Foundation's `PLATFORM-INTERFACE.md`, `HANDOFF.md`, `STARTUP.md`, `COMBINED-HOOKS.md`.
- The three Linux options from session 1 (Ubuntu releases, runtime bundling, chrome) are not decided yet.

### 14. ARM64 "blank window" — not an app bug
A probe on the ARM64 runner (eight renderer settings, 14 s wait) showed the full dashboard with the default
settings: the session-1 launch test took its screenshot 2 s after .NET's first render, and the ARM64 runner
paints later. The pixel-checking launch test (cfbd462) passes 3/3 on ARM64. The probe branch
`platform/linux-probe` could not be deleted from here (the proxy refuses branch deletion); it is harmless.

### 15. Moved onto platform/foundation
A force-push was refused (it rewrites published history), so the branch takes Foundation by **merge**:
`2c6307f` (tree identical to a rebase, checked with `git diff`), later `8856495` (3.31.2 + combined hooks).
- Registration through `services.AddChuvadiReader(AppStateLifetime.Process)`, then the Linux seams:
  `IPlatformInfo` (Linux, Desktop, Mouse+Keyboard, buttons from the desktop's layout, `CornerRadiusPx` 12,
  `CtrlKeyLabels`), `IAppStorage` (kit's `FileAppStorage`), `IClipboard` (new: text + PNG), `IFileManager`
  (new: D-Bus `org.freedesktop.FileManager1.ShowItems`, else `xdg-open` on the folder), `IAppPaths`
  (`LinuxAppPaths`, see 17), plus the session-1 seams. `prepare-tree.sh` removed (the tree is the full Reader).
- Host page: the Windows shape, `chuvadi-reader.styles.css`, and `<html data-shell="desktop"
  data-platform="linux" data-form-factor="desktop" data-input="mouse keyboard">` for the first paint.
- `ChuvadiReader.Platforms.slnx`: the Linux host was added, which **broke the shared `platforms` CI**
  (it builds that solution on macOS/Windows/Ubuntu runners without GTK headers). Taken out again; the Linux
  workflow builds the host.
- CI now builds from the tree with `scripts/setup-feed.sh`, runs both test projects.

### 16. Linux chrome (handout: same as Windows, 12 px corners, GNOME/KDE button layout)
- **Buttons:** `gtk-decoration-layout` (GTK reads GNOME's `button-layout` and KDE's GTK settings): close on
  the left of the ':' → `WindowButtons.Left` (the Ui's left-hand component), else Right. Checked: default →
  right; `close,minimize,maximize:` → left (screenshots).
- **Corners:** window CSS `border-radius: 12px` with `overflow: hidden` clipping the web view; square when
  maximised, tiled, full screen or `solid-csd` (no compositor). Checked at 8× zoom on a restored window.
- **Pinch zoom off** (a capture-phase `GtkGestureZoom` claims it), as the Windows host turns it off.
  WebKitGTK has no Ctrl+scroll / Ctrl± page zoom of its own.

### 17. Bug found and fixed (host side): saves could land in /tmp
.NET returns "" for the Documents folder when it doesn't exist yet; the kit's `DesktopAppPaths` then gives
no default save folder and Core falls back to the temp folder, so "Chuvadi Documents" would be created
under `/tmp` (wiped at reboot). Seen in the sandbox (no `~/Documents`). `LinuxAppPaths` always uses the
XDG documents folder, else `~/Documents` (created on first save). Reported to Foundation for the shared kit.

### 18. Printing (D-06)
Print card (pages, copies, fit) → **GTK's print dialog** (`GtkPrintUnixDialog`, an OS component; the card
already says "The printer dialog opens next", as on Windows) preset from the card → the **PDF as-is** to
the chosen CUPS queue over IPP with `Chuvadi.Print.Ipp` (`IppDocumentTarget`; queue URI from
`CupsQueues.List`). Settings sent: pages, copies, collate, two-sided, paper size (from the dialog — the
library always sends a paper size, so it must be the printer's), orientation, fit/actual size, page set,
reverse order, pages per sheet, the queue's own options (tray, media type, resolution… — PPD names) and
the Job tab (priority, cover pages, print-at time, billing), each typed as its IPP attribute. The dialog
lists CUPS printers only (GTK setting `gtk-print-backends` = `cups`; GTK 4 no longer reads the GTK 3
`GTK_PRINT_BACKENDS` variable — my first attempt used it and "Print to File" still showed; caught on the
dialog screenshot and fixed). Checked in CUPS's own job file: `sides`, `media iso_a4_210x297mm`,
`print-scaling fit`, `number-up-layout`, `job-priority`, `Resolution 300dpi`, `job-sheets none`,
`job-hold-until no-hold` all accepted, and the job printed. Files with an open password are sent decrypted from
memory (CUPS can't open them), made with the library calls Core uses. Messages as on Windows.
- **Not done (library):** the raster fallback needs `Chuvadi.Print.Pdf.Raster` (no release/tag exists) and
  the router's PDF route needs a font inspector to know every font is embedded. Until then every job goes
  as-is to CUPS, which converts it with its own filters (every local queue accepts PDF).
- Packages: `Chuvadi.Print` and `Chuvadi.Print.Ipp` **1.0.0-rc.2** from the `print-v1.0.0-rc.2` release
  (no checksum file is published), added to `ci/packages`:
  - `Chuvadi.Print.1.0.0-rc.2.nupkg` sha256 `252b6d10204d37069a35040ea89d58e1662a452c4e05fd90a0d8b90cd1049cbf`
  - `Chuvadi.Print.Ipp.1.0.0-rc.2.nupkg` sha256 `82304b782ce23ac5dcb3895e1fee31898abf3c22222f9f9c65c423fba68aa562`

### 19. Bugs found and fixed in my code
- **App kept running after its window closed.** After the GTK loop ends, disposing the WebView manager waits
  on components that clean up through JS interop — the page is gone, so it waited forever. Disposal now
  gets 1 s, then the process ends (as the Windows app ends with its window). Measured: exits ~1 s after Close.
- **Message order to the page.** Blazor's dispatcher can run inline on the GTK main thread; a message sent
  from there was delivered at once and could overtake messages still queued from worker threads. All
  messages now go through one FIFO drained on the main thread. (Prevention: reasoned from how the
  dispatcher works; not observed.)
- **Tests leaked processes** (not an app bug): one `dbus-run-session` per launch left its portal services
  running after the app was killed — 46 D-Bus daemons and 39 portal sets, load average 37 on 2 cores — which
  stalled launches by up to 85 s. Smoke and UI tests now use one session bus per run, as a desktop session
  has. With that: 0 of 40 launches stalled; first render 1.3–1.9 s each time.

### 20. UI test build and harness
- `-p:UiTest=true` adds `UiTestDriver` (stdin: `js`, `commands`, `invoke`, `open`; numbered replies, each
  command on its own task). The shipped build never contains it.
- `tools/linux/uitest.py` + `uitest_lib.py`: Xvfb, one session bus, mutter, the app with a fresh profile;
  DOM clicks for buttons, real pointer and keys (xdotool) for window chrome, typing, drawing and GTK dialogs;
  `make-fixtures.py` writes the PDF (5 pages, page 4 landscape), DOCX and XLSX by hand. Each step checks the
  app is alive, Blazor's error bar is hidden and no new "Chuvadi error" is logged, and keeps a screenshot.
- GTK file dialogs open through the desktop portal (`xdg-desktop-portal-gtk`, another process) — so KDE
  users get KDE's dialog; the harness finds dialogs by title.

### 21. Startup (D-50 ReadyToRun; Arun: "load in milliseconds")
Published Release, ReadyToRun, framework-dependent; this sandbox (2 cores, **no GPU**, software GL);
one warm-up launch, then medians of 12 (ms since process start; `tools/linux` stage marks):

| Stage | Before | After the renderer change |
|---|---|---|
| .NET `Main` | 34 | 30 |
| GTK ready | 110 | 103 |
| services built (`AddChuvadiReader`) | 136 | 129 |
| window + web view created | 156 | 147 |
| navigation started | 192 | 170 |
| **window on screen** (theme colour) | **656** | **177** |
| page loaded (WebKit) | 1116 | 379 |
| **Blazor first render** (dashboard) | **1504** | **785** |

- Showing the window cost ~460 ms: GTK set up its GL renderer, which without a GPU runs in software
  (llvmpipe). Measured alternatives: `GSK_RENDERER=gl` 1420, `vulkan` 1464, **`cairo` 813** (first render);
  WebKit's own switches on top of cairo (no DMA-BUF 781, Skia CPU 796) are within noise.
- Change (shim): **without a DRM render node** (`/dev/dri/renderD*` absent — VMs, remote sessions, CI)
  GTK's CPU renderer is used; **with a GPU, GTK's default stays** (it was not measured here: no GPU in the
  sandbox or on GitHub's runners). A `GSK_RENDERER` the person sets always wins.
- What is left: WebKit's web process + page load ~200 ms, Blazor building the dashboard ~400 ms (shared Ui;
  Foundation's S3 profiling, D-51). Cold first launch after install: ~2.5–3 s (font cache, first WebKit
  process), once.

### 22. Packages (.deb)
`src/ChuvadiReader.Linux/packaging/deb/build-deb.sh <out> [--framework-dependent]`, run on the target
architecture (CI builds amd64 on `ubuntu-24.04`, arm64 on `ubuntu-24.04-arm`).

| | self-contained (default, pending decision) | framework-dependent |
|---|---|---|
| download (amd64) | 36.7 MB | 10.7 MB |
| installed | 105 MB | 25 MB + `dotnet-runtime-10.0` (~70 MB, shared) |
| .NET | inside the package | Ubuntu's package |

- Dependencies from `dpkg-shlibdeps` on every native library (24.04 names, valid on 26.04: `libglib2.0-0t64`,
  `libgtk-4-1`, `libwebkitgtk-6.0-4`, `libjavascriptcoregtk-6.0-1`, `libsoup-3.0-0`…), plus what .NET loads
  at run time: `libicu74 | libicu78` (24.04 / 26.04) and `libssl3t64` (self-contained) or `dotnet-runtime-10.0`.
  Recommends `cups` and a portal backend.
- `libcoreclrtraceptprovider.so` (.NET's optional LTTng tracing hook) is left out: it links
  `liblttng-ust.so.0`, which 24.04 no longer ships, and .NET runs without it.
- Contents: `/usr/lib/chuvadi-reader` (app), `/usr/bin/chuvadi-reader` (symlink),
  `in.chuvadi.Reader.desktop` (PDF / DOCX / XLSX; `desktop-file-validate` clean),
  `in.chuvadi.Reader.metainfo.xml` (`appstreamcli validate` passes; one pedantic note: capital letter in the
  ID, which is a placeholder anyway), icons 16–256 px copied byte for byte from the PNG images inside the
  Windows app's `chuvadi.ico`, `/etc/apparmor.d/chuvadi-reader` (conffile; `postinst` loads it).
- Installed here: `xdg-mime query default application/pdf` → `in.chuvadi.Reader.desktop`; `xdg-open
  five-pages.pdf` started the installed app on that file (first render 1.48 s); the profile compiles
  (`apparmor_parser -Q`). `apt remove` leaves only the profile (standard for a conffile); `purge` removes it.
- Placeholders for Arun: app ID `in.chuvadi.Reader`, Maintainer `Sthraas Intelligence Pvt Ltd
  <maintainer@chuvadi.in>`, Homepage `https://chuvadi.in`, licence "to be confirmed" (no licence file).

### 23. UI test pass (sandbox, x64) — `tools/linux/uitest.py`
Final build: **106 / 106 steps pass** (report and screenshots: CI artifact `linux-<arch>/uitest`).
- Chrome: theme toggle; restore → real drag of the top bar moves the window → double-click maximises;
  Minimise (WM state Iconic + hidden; a compositing WM keeps the window mapped) and raise; Close ends the
  process (exit 0); rail collapse/expand; all 10 Settings sections; all 5 themes; interface size 125/150/100.
- Open through the GTK file dialog (via the desktop portal), pager, every Read rail tool (Print and
  Immersive tested separately), page strip, every Document ▾ item, tab menu, Ctrl K (60 items), and **every
  enabled command in the Ctrl K registry: 44 run, 0 errors** (2 open a dialog, closed by the test).
- Mark: rectangle drawn with a real pointer drag → **Save as new PDF through the GTK save dialog** → valid
  5-page PDF; every Mark rail tool. Protect: **Password-protect a copy** typed into the card → the copy won't
  open without the password, and with it `Encrypted: yes (AES-256)`; every Protect rail tool.
- Arrange: Fetch file through the GTK dialog → the file on the shelf with 5 thumbnails; every rail tool.
- Word and Excel viewers show the fixture content. Shortcuts Ctrl ±/0, Ctrl F, Ctrl Tab, Ctrl O, F11,
  Ctrl Shift W.
- **Print**: Print card (Custom 2-4, 2 copies) → GTK print dialog → the CUPS PDF queue wrote **6 pages:
  2, 3, 4, 2, 3, 4 (collated), 0 images, real font data — vector**; the card said "Sent 3 pages to the
  printer" (Windows wording). Cancel in the dialog sends nothing.
- Harness fixes on the way (all test-side): dialogs belong to the portal process, so they are found by
  title; dismissing never clicks the window's Close; stray keys (1–4 switch modes) avoided by focusing
  the main window and checking typed values; numbered driver replies; functional checks run on a fresh
  process after the toolbar sweep (which toggles every View tool); cups-pdf reuses file names, so output is
  found by time.
- Not covered by automation: dragging a file in from another app (needs a drag source in the test
  session); Show in folder with a real file manager (none in the test session; the fallback ran).

### 24. Compared with the Windows design — `tools/linux/compare-design.py`
Same pages, same documents, 1440 × 900 (the handout's reference), clock hidden: the Ui in **Chromium**
(WebView2's engine) through Foundation's dev-only preview host in its Windows-desktop mode, and in the
**Linux app**. Sheets in `docs/linux/screenshots/compare-*.png`.

| Page | Pixels differing (fuzz 6 %) |
|---|---|
| Home | 6.2 % |
| Reader | 1.8 % |
| Library | 2.3 % |
| Settings | 5.6 % |

Layout, chrome, colours, icons and type match element for element. What differs: text antialiasing
(every glyph edge), 2–3 px of line-height rounding in Settings (WebKit vs Chromium font metrics), data (the
Linux run's Recent list and storage path), and scrollbars (headless Chromium hides them; the Linux app
shows the Ui's styled scrollbar, as WebView2 does). Linux-only by design: window buttons follow the desktop's
layout, 12 px corners when not maximised (`screenshots/linux-buttons-left-gnome-kde-layout.png`,
`linux-12px-corner-8x.png`). The Ui itself implements the handout's D-10 rails partly (DESIGN-NOTE); that is
the Reader chat's work, not a platform difference.

### 25. CI: both architectures green — `.github/workflows/linux.yml`
Runs 42224638571 (x64, commit `dbc989b`) and 42225596444 (ARM64, commit `a77674e`), GitHub-hosted Ubuntu 24.04:
build (warnings are errors), both test projects, ReadyToRun publish, launch test, both `.deb` packages, install
of the `.deb` (postinst loads the AppArmor profile; `xdg-mime` default for PDF), launch of the installed app,
CUPS PDF queue, full UI pass.

| | x64 | ARM64 |
|---|---|---|
| `.deb` self-contained (download / installed) | 36.7 MB / 105 MB | 33.0 MB / 115 MB |
| `.deb` framework-dependent | 10.7 MB | 10.2 MB |
| Full UI pass | 106 / 106 | 106 / 106 |
| Blazor first render, launch test (runner, no GPU) | 1.2–1.5 s | 1.06–1.23 s (first launch 3.5 s, cold disk) |

Fixes on the way: `smoke.sh` read the session bus with `read` (stopped by `set -e`) → `sed`; the ARM64 image
has no `xdg-utils` → installed with the test tools. One x64 rerun after Ubuntu's mirror timed out (apt).

Known upstream warning, harmless: GTK 4.14's print dialog logs two `Gtk-CRITICAL` lines
(`gtk_column_view_get_model`, `gtk_single_selection_get_selected_item`) when it is closed with Escape — inside
GTK's own dispose (`g_list_store_remove_all` on its printer list after the list view is gone; backtrace taken).
No crash, no effect on the job. A two-dialog C reproducer without our code does not always trigger it; not
worked around (it would mean reaching into GTK's internals).
Also in the CI log: Microsoft Edge (preinstalled on the runner) aborts at teardown — the UI pass's external
link opened it through `xdg-open`; test environment only.
