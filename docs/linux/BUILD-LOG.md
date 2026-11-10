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
Run 42225596444 (commit `a77674e`, both architectures green; x64 also green on `dbc989b`), GitHub-hosted Ubuntu 24.04:
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

## 2026-11-07 — Session 3: coordinator decisions, ReadyToRun check

### 26. ReadyToRun publish (HANDOFF §2a, D-50)
The host csproj carries §2a's block (only when publishing; `PublishReadyToRun`, `SelfContained` false unless
asked). One difference, kept on purpose: the default runtime is the SDK's own (`linux-x64` on x64,
`linux-arm64` on ARM64) rather than a fixed `linux-x64`, so a plain `dotnet publish` on an ARM64 machine
builds ARM64; `-r` still picks either.

Checked on a fresh publish: **all 40 of our assemblies are precompiled** (CLI header has a non-zero
ManagedNativeHeader): `chuvadi-reader.dll`, Ui, Core, Hosting, Platform, every Chuvadi library
(Pdf.*, Sheets, Docs, Fonts, Print, Print.Ipp) and Blazor's Components / WebView.

Measured on the real app (not only the shared part): `smoke.sh`, launches alternating between the two
builds, 2-CPU sandbox, no GPU, build servers stopped.

| Publish | Size | Window shown (median) | Blazor first render (median) |
|---|---|---|---|
| JIT (`-p:PublishReadyToRun=false`) | 17 MB | 252 ms | 1,267 ms |
| **ReadyToRun (shipped)** | 25 MB | 229 ms | **1,089 ms** (−14 %) |

The rest of first render is WebKit's page load and Blazor's first render in the page, not JIT.
(Absolute numbers are higher than §21's 785 ms: this session's sandbox has 2 CPUs.)

### 27. Window drag: ignore a move that arrives after the button is up
One local full pass (2-CPU sandbox, first step after launch) failed `04-window-restore-drag-maximise`: the
top bar's mouse-down reaches `chvd_begin_move` one page → .NET → GTK round trip later, and the test's
half-second drag had ended by then. Repeated drags moved the window 8/8 with no stuck move afterwards, so
the outcome was only "no move". To make a late move safe, `chvd_begin_move` now checks the pointer's button
state and skips the move when the button is already released (otherwise the window manager could start a
move with no release to end it). Checked: drags at two speeds 8/8 move; quick clicks on the top bar 5/5 leave
the window where it was, and it does not follow the pointer afterwards.

### 28. Green on both architectures with the fix
Run 42274653421 (commit `7634036`): x64 and ARM64 each 106/106 in the full UI pass, both `.deb` packages built,
installed and launched (self-contained 36.7 MB x64 / 33.0 MB ARM64; framework-dependent 10.7 / 10.2 MB);
shared `platforms` workflow green. Local full pass on the same build: 106/106.

## 2026-11-07 — Session 3 (cont.): Arun's decisions on licence, single instance, no-printing files

### 29. "No printing" files refused before the dialog (D-66, L-8)
`CupsPrintService` reads the file's permissions while loading it (chuvadi-pdf `PdfDocument.Encryption.AllowPrint`)
and, when printing isn't allowed, returns "This file's permissions don't allow printing." without opening the
GTK dialog, decrypting the file or contacting CUPS. A file without encryption always prints.
- The library doesn't say which password opened a file, so a file opened with its permissions (owner)
  password is refused too; question to the coordinator.
- New fixture `no-print.pdf` (five-pages.pdf, AES-256, permissions password only, printing not allowed) made
  with qpdf (test tool, CI installs it); new UI step `31-print-not-allowed`: message shown, no dialog, nothing
  in CUPS.
- The Ui's Print card shows every result message in the same toast (with a tick), failures included — on
  Windows too; noted for the coordinator, not a Linux change.

### 30. Licence in the package (Arun: proprietary, free for everyone, not open source)
- `copyright` (DEP-5): `Files: *` → `Copyright: 2026 Dr. Arun Shiva B` (year of the Reader's first commit),
  `License: Chuvadi-Proprietary`. Its text is the repository's `LICENSE` when the Foundation adds it
  (`build-deb.sh` embeds it); until then the decision's own words. An `EULA*` file at the repository root is
  installed next to it.
- Microsoft's parts corrected: Blazor and Microsoft.Extensions ship in **both** variants (the file said
  self-contained only); the .NET runtime only in self-contained. Full MIT text included; their
  `THIRD-PARTY-NOTICES` are installed from the exact packages in the build's `deps.json` (self-contained: 4
  files, framework-dependent: 3).
- AppStream `project_license`: `LicenseRef-proprietary` (`appstreamcli validate` passes). Lintian: no copyright
  warnings.

### Single instance (approved programme-wide)
Waits for the Foundation's kit contract; the Linux side will be D-Bus (the session bus the app already uses
for Show in folder) or a Unix socket — options with pros and cons when the contract lands.

### 31. Green
Run 42283536949 (commit `833cea3`): x64 and ARM64 each **107/107** in the full UI pass (with
`31-print-not-allowed`), both `.deb` packages built, installed and launched with the licence and notices in
`/usr/share/doc/chuvadi-reader/`; shared `platforms` workflow green. Local: 107/107. (One earlier local run
failed the print step only because the sandbox's CUPS scheduler had exited — no service manager here; CI's
runs under systemd.)

## 2026-11-07 — Session 3 (end): holder, Print card proposal, local run of the whole workflow

### 32. Copyright holder and the Print card fix
- `copyright`: `Copyright: 2026 Sthraas Intelligence Pvt Ltd` (Arun's decision for all products). AppStream
  already names Sthraas Intelligence Pvt Ltd as developer.
- Print card errors in the error style: approved; diff in `PROPOSAL-print-card-errors.md` for the Foundation's
  combined patch (one existing file, `PrintCard.razor`; not committed here). Checked with the diff applied:
  the refusal shows the error toast, a successful print keeps the success toast.

### 33. The whole Linux workflow, run locally — green
GitHub Actions on Sthraas is stopped (billing), so every step of `.github/workflows/linux.yml` was run locally on
commit `5d742dd` (x64, Ubuntu 24.04 sandbox, 2 CPUs, no GPU), in order:

| Step | Result |
|---|---|
| Package feed, build (warnings are errors) | pass |
| Reader tests / host-kit tests | 161 / 161, 28 / 28 |
| ReadyToRun publish, UI-test publish | pass |
| Launch test (3 launches, real pixels) | pass; first render 0.97–1.07 s |
| `.deb` self-contained / framework-dependent | 36.7 MB / 10.7 MB |
| Install the `.deb` (status, AppArmor profile, `desktop-file-validate`, Sthraas in the copyright file) | pass |
| Launch the installed app (2 launches) | pass; first render 0.95–1.12 s |
| CUPS PDF queue | pass |
| Full UI pass | **107 / 107** |

ARM64 can't run in this sandbox: its last run is CI 42283536949 (commit `833cea3`, 107 / 107); since then only
the copyright holder line and documents changed.

### Linux build: complete
Everything asked of the Linux build is done and green locally. Open only because they wait on others:
1. Delete `LinuxAppPaths`' save-folder fallback and the Linux copies of the Print packages in `ci/packages`
   — when the Foundation's second patch lands (rebase).
2. Single instance — when the Foundation's kit contract lands (D-Bus or Unix socket; options then).
3. The Print card fix — arrives with the Foundation's combined patch.
4. ARM64 re-run in CI when Actions is back.

### 34. ARM64 rerun on the current head (D-93)
CI is back. Run 42314276500 (workflow_dispatch on `eb65770`, the head that was green locally on x64):

| | x64 | ARM64 |
|---|---|---|
| Full UI pass | 107 / 107 | **107 / 107** |
| `.deb` self-contained / framework-dependent | 36.7 / 10.7 MB | 33.1 / 10.2 MB |
| Blazor first render, launch test | 0.85–1.09 s | 0.89–1.01 s (first launch 4.2 s, cold disk) |

Build, all tests, ReadyToRun publish, launch test, both `.deb` packages, install + launch of the installed
app, CUPS queue: green on both.

## 2026-11-08 — Session 4: window buttons follow the desktop's layout exactly

### 35. Bug (D-93): close-only and every other layout
The design note says to honour the GNOME/KDE button layout. Linux took only the *side*; the Ui then drew
all three buttons, so vanilla GNOME (`appmenu:close`) showed minimise and maximise, and layouts such as
`close:maximize` couldn't be shown. Fixed — details and the shared-file diff in
`PROPOSAL-window-button-layout.md`:
- Contract: `ShellChrome.ButtonLayout` (ordered buttons at each end; null = today's behaviour elsewhere).
- Ui: `WindowButtons` draws a given list in order; `MainLayout` uses it at both ends when set.
- Linux: the shim returns GTK's whole `gtk-decoration-layout`; `GtkButtonLayout.Parse` reads it exactly as
  GTK 4.14's header bar does — checked against Ubuntu's GTK 4.14.5 source (`gtkwindowcontrols.c`): split
  at the first ':', exact names (strcmp), non-button names skipped, duplicates drawn twice, no ':' = left.
- Tests: new `tests/ChuvadiReader.Linux.Tests` (25 parser cases, in the workflow); new UI step
  `35-button-layouts` — the real app under 8 layouts set through GTK's own settings file, buttons and order
  at both ends checked, minimise / maximise checked against the window manager's state; the window-close
  step now runs under vanilla GNOME's close-only layout.
- Test-harness fix on the way: a fresh profile can open maximised, so the step reads the state first.
- Local (x64): all tests incl. Web and Mobile Ui (shared Ui changed); full UI pass **108 / 108**.
- Not built: following a layout *change* while the app runs (read at start-up) — option B in the proposal.

### 36. Green in CI on both architectures with the fix
Run 42481652554 (commit `f7d0034`): x64 and ARM64 each **108 / 108** in the full UI pass, including
`35-button-layouts` (8 layouts exact, window close under vanilla GNOME's close-only layout); Linux parser
tests 25 / 25 on both; both `.deb` packages built, installed and launched (36.7 / 10.8 MB x64,
33.1 / 10.2 MB ARM64). The shared `platforms` workflow (run 42481652486) is green too — the Windows app,
and the shared build on Windows, macOS, Ubuntu x64 and ARM64 — so the contract and Ui change is safe for
every other host.

The Linux Test chat (`platform/linux-test`, 9ef12c4) has a test plan and no `BUGS.md` yet; its T3.4 covers
this layout bug.

## 2026-11-08 — Session 4 (cont.): the Linux Test chat's bugs (B-01 to B-23), Foundation's patches merged

### 37. Every Linux bug fixed with a test
| Bug | Fix | Test | Commit |
|---|---|---|---|
| B-01 lintian | file modes (0644, apphost/createdump 0755), stripped shim, `changelog.gz`, man page, md5sums, unused precompressed copies dropped; overrides with reasons for Microsoft's binaries, the app's web fonts, LiPi's licence and `index.html` | `tools/linux/check-deb.py`: `lintian --pedantic` must report nothing un-overridden; file modes | 043e490 |
| B-02 (Linux) | copyright: one stanza per font family with the holder from the font's own metadata, `License: OFL-1.1` and the full OFL text | check-deb.py: every font file has its own stanza naming its holder; OFL text present | 043e490 |
| B-04, B-06 | every file from the command line, the desktop entry's `%F` or a drop opens in its own tab, in order (now through the kit's `IncomingFiles`) | UI steps 34b, 34c | 4e9e244 → 606d01b |
| B-05 | single instance: the kit's `DesktopSingleInstance` (L-A: lock file + Unix socket, F-1), claimed on a thread during start-up; a later launch hands over and exits; the window comes forward with the launcher's activation token | UI step 34c2 (hand-over in 0.11 s, one window) | 606d01b (replaces my D-Bus version, 29db68a) |
| B-12 | no GPU → WebKit compositing off (D-110 A); first launch on a fresh profile: 4.7 s → 1.0 s to real content (6 runs each) | UI step 34b2 (the choice); `first-launch.py` records the time in CI | e8ca522 |
| B-13 | no IntelliSense XML (project setting + package script) | check-deb.py | 043e490 |
| B-14 | landscape pages: the ticket's `orientation-requested` is removed unless the dialog chose one, so CUPS turns each page to fit (measured: rot 90, full size) | UI step 30: printed page 4 is turned | 4e9e244 |
| B-15 | bubblewrap probed once (in parallel with services, 0.6 ms on the critical path) before any web view; if it can't start: a plain message window and exit 2 (D-110 A: never switch the sandbox off) | `no-userns-test.sh` under a seccomp rule refusing user namespaces (as Docker's default) | e8ca522 |
| B-16 | `ResilientAppStorage`: settings in memory when the folder can't be written, one error notice | `readonly-home-test.py` as an ordinary user | e8ca522 |
| B-17 | `UseSystemResourceKeys` removed | check-deb.py (runtimeconfig); UI step 34d on non-root runners | 4e9e244 |
| B-20 | no printer / CUPS down: a plain message, no empty dialog | `no-printer-test.py` with CUPS stopped | 606d01b |
| B-21 | Show in folder falls back to `xdg-open` only when there's no file manager on the bus, never on a slow one (30 s) | `reveal-test.py`: an 8-second stand-in file manager → 1 call, no fallback; none → 1 fallback | c9f5500 |

Shared ones (B-02 OFL texts in the Ui, B-03, B-07, B-08b, B-10, B-11b, B-19, B-23, and D-101) are exact diffs in
`PROPOSAL-shared-fixes-8nov.md` for Foundation's next combined patch; library asks are listed there too.
B-18 (left bar resting state) belongs to the Reader chat's desktop revamp (it changes Windows too); B-22 (focus
style) is a design option for the coordinator.

### 38. Foundation's second to seventh combined patches merged (ec9de75)
No conflicts; the shared code on `platform/linux` is now identical to `platform/foundation` (9fbed93). Applied to
the Linux host: `LinuxAppPaths` deleted (the kit's `DesktopAppPaths` has the fallback); the Print packages are
the centrally adopted copies (same SHA-256s); print refusal uses Core's `PrintPermission` text; single instance
and the open router are the kit's. The Print card now locks itself for a no-printing file (Foundation), so UI step
31 checks the locked card; the Linux print service refuses too.

### 39. CI on ffb2823; the shared diff tested on Linux (8 Nov)
- CI on `ffb2823`: green on x64 and ARM64, including the new steps (B-15 no user namespaces, first launch,
  `check-deb.py`, B-16 read-only home, B-21 Show in folder, B-20 no printing service); the shared workflow green
  on Ubuntu x64/ARM64, macOS and Windows; the Windows app and pack-check green.
- Shared fixes (D-101 live layout, B-02 Ui OFL, B-03, B-07 to B-11, B-19, B-23) rebased on `ffb2823` as one
  exact diff in `PROPOSAL-shared-fixes-8nov.md` (applies cleanly with `git apply`). With it applied: Reader
  179/179, host kit 54/54, Linux 25/25, Web Ui 33/33, Mobile Ui 16/16; full UI pass 114/114 (step 35: 8 layouts
  exact, B-19 divider within 1.5 px, three live changes; step 34b3: B-23 Tab order).
- BUGS.md on `platform/linux-test` (14b1c43) lists each fix's commit and test for the Test chat to re-verify.

### 40. Foundation's eighth combined patch merged (839d39d, 9 Nov)
No conflicts. Foundation now carries the shared fixes (D-101 contract and top bar, B-02 Ui OFL, B-03, B-07 to
B-11, B-19, B-22, B-23), so the Linux chat's local shared branch is retired; its Linux-only part lands here:
GTK's `gtk-decoration-layout` changes raise `ChromeChanged` (D-101, live), with the `set-layout` test verb.
B-16 now uses the kit's `FileAppStorage` (keeps settings in memory, `CannotSave`); `ResilientAppStorage` is
deleted. Results: Reader 187/187, host kit 59/59, Linux 25/25, Web Ui 33/33, Mobile Ui 16/16; full UI pass
115/115 (step 35: 8 layouts + live changes, B-19 divider; 34b3 B-23; 34b4 B-22 accent ring in all five themes);
B-16 read-only home as an ordinary user: PASS.

### 41. Printing through a separate CUPS server (9 Nov)
Print asks the CUPS server this computer prints through, read as lpstat and GTK's print dialog read it:
`CUPS_SERVER`, then `ServerName` in `~/.cups/client.conf`, then in `/etc/cups/client.conf`
(`Platform/CupsServer.cs`; `CupsQueues.List(server)`). Nothing set, or a socket path, keeps the local CUPS with
the network printers it browses (`CupsQueues.List()`, as before). Tests: 19 parser tests (Linux 44/44);
`tools/linux/remote-cups-test.py` with a stand-in server (a second cupsd on localhost:8631 with a cups-pdf
queue) and the local CUPS stopped: nothing configured → the "can't reach" message; `CUPS_SERVER` → job completed
there; `client.conf` → the same. The previous build fails both remote cases (no dialog), so the test catches it.

Orientation (B-14) is unchanged. In Chuvadi.Print 1.0.0-rc.2, `PrintSettings.AutoRotate` only changes raster mode;
in document mode (CUPS lays out the PDF, as Linux prints) `IppJobTicket.Build` still sends `orientation-requested`
(3 for portrait) with it on, which is what shrinks landscape pages. Checked with a small program against the
package; options in the report.

### 42. Foundation's ninth to eleventh combined patches merged (1016987, 9 Nov)
B-07 through the library, B-24 (a stalled read never freezes the Reader), Chuvadi.Zip 1.0.0, Chuvadi.Docs 2.0.0 and
Chuvadi.Sheets 2.0.2 with their limits and cancellation (D-136). No conflicts; no Linux change needed. Results:
Reader 199/199, host kit 59/59, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16; both packages pass `check-deb.py`;
full UI pass 115/115.

Found on the way: a local build put a stale ReadyToRun image of Sheets 1.1.2 in the app under a deps.json that
said 2.0.2 (ReadyToRun recompiles only when an input is newer, and the release asset is dated earlier), so
Settings › About threw. Clean CI runners can't hit it, but a package built on a developer's machine could ship
it. `build-deb.sh` now clears ReadyToRun's cache before publishing, and `check-deb.py` checks that every Chuvadi
and LiPicons DLL is the version deps.json names (it fails on the stale package and passes with a stale image
planted in the cache).

### 43. Foundation's twelfth combined patch merged (022b7c0, c91a581; 9 Nov)
chuvadi-pdf 3.32.0 (owner password lifts a file's permissions, D-139), AT-03 typed registrations (D-146), W-01,
W-02, path labels (P-08). No conflicts; no Linux change needed (Linux isn't trimmed; it already uses
`PrintPermission.Allows`). Built with warnings as errors; Reader 212/212, host kit 66/66, Linux 44/44, Web Ui
39/39, Mobile Ui 16/16; `tools/TrimProbe` published trimmed for linux-x64 and launched: 53/53 services.

Found by a new UI step (31b, owner password → print): the Print card is unlocked, but printing fails with "This
PDF is encrypted and needs a password to open". `Reader.razor` opens `PrintCard` without the tab's password, so
the print service gets none (Windows too). One-line shared fix (`Password="@tab.Password"`) sent to Foundation
with B-24 and B-25 in `PROPOSAL-shared-fixes-9nov.md`; step 31b lands here with it.

### 44. Foundation's thirteenth combined patch, part 1 (7d1ac03, 9 Nov)
Carries the Linux chat's B-24 (no file probe on the page's thread), B-25 (viewer errors as WT-10) and S3 (the Print
card gets the tab's password, so an owner-password open prints, D-139). The tests that prove them land here:
- 31b: no-printing file with both passwords — user password: card locked; owner password: CUPS writes 5 pages.
- 34e: named-pipe `slow.pdf` / `slow.xlsx` — "Opening…" 0.3 s, "Stop opening" 10 s, the next file opens meanwhile.
- 34f: `notzip.xlsx` / `notzip.docx` — plain sentence, the library's text under a collapsed Details. (It now
  waits for the message naming the opened file's kind: both viewers can stay in the page; 3/3 runs.)

Built with warnings as errors; Reader 212/212, host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16; full
UI pass 118/118.

### 45. Foundation's fourteenth combined patch: pages render off the Ui thread (21a222d, b41f25c; 9 Nov)
No conflicts; no Linux change. Built with warnings as errors; Reader 220/220 (incl. `RenderOffUiThreadTests`),
host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16. Full UI pass 121/121 with three new steps on
generated PDFs (`tools/linux/make-heavy-pdfs.py`, test-only; no real drawing used):
- 36a, 400 pages, 6 bursts of 25 PageDowns: the page answers within 0.10 s throughout; page 400 draws after a jump.
  **Finding:** the page landed on (103) draws 7.5–8.3 s after the last key: every page that scrolled past queued
  a render (`EnsureRendered` from the page observer) and nothing cancels it when the page leaves the view, so the
  visible page waits behind the backlog (one render at a time per document). Shared Ui/Core; reported.
- 36b, a CAD tab closed as it opens: next file drawn in 0.1 s, page answers ≤ 0.06 s, no errors. (Sheet 1 draws in
  ~0.3 s, so the close usually lands just after it; Core's `RenderOffUiThreadTests` hold a render open with a hook
  for the deterministic case. A generated page couldn't be made reliably slow: a 6000 x 6000 CMYK image draws
  in 0.3 s.)
- 36c, 5 A1 sheets of ~120,000 strokes: sheets draw in 0.2–0.3 s (4.7 s for sheet 1 in the full flow, behind
  earlier work); the page answers ≤ 0.14 s. Memory after 5 sheets: app 600–700 MB, web 246 MB, and it stays high
  after the tab closes (B-27's growth, smaller). Once in four runs a ~2.2 s pause held either a sheet or the
  page's answer — consistent with a full garbage collection on that heap; not yet proven.

### 46. Foundation's fifteenth combined patch (bcd1ab1, 10 Nov) — and a correction to §45
Merged without conflicts; Reader 223/223, host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16; full UI pass
121/121.

**Correction:** §45's "render backlog" finding was wrong. Step 36a timed the landed page from the last key, but
WebKitGTK plays each PageDown as a smooth-scroll step, one after another: after 150 fast PageDowns the view keeps
moving for 12–14 s and only then reaches page ~150. Traced on both the fourteenth- and fifteenth-patch builds: all
400 pages of `big.pdf` were already drawn; the page counter climbed ~10 pages a second after the keys stopped. The
pages weren't late, the scroll was. (Foundation's queue change — pages that left the view are cancelled, the
nearest waiting page goes next — is still right for genuinely heavy pages.) 36a now waits for the view to settle
and fails if the landed page isn't drawn within 2 s of that: on both builds it is drawn within the 1 s it takes to
count as settled.

The real Linux finding is the scroll itself: held PageDown keeps scrolling for ~12 s after release. Reported with
options (it's WebKit's smooth scrolling, a host setting).

### 47. Foundation's sixteenth combined patch: memory after closing a heavy document (add7b05, 10 Nov)
Merged without conflicts; Reader 226/226, host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16; full UI pass
121/121. 36c now records the app's memory before opening the 5-sheet drawing, with it open, and after closing
(target: back within 100 MB of before). A test-only `gc` driver verb reports what an aggressive collection gives back.

- In the full pass (a warm app): 616 MB before, 691 MB with 5 sheets, 691 MB after closing — within the target.
- On its own (cold app, a small PDF kept open so closing returns to it, not Home): 269 → 360 MB with 5 sheets →
  **506–525 MB after closing**, i.e. memory *rises* ~150 MB at the close and stays (33 s). It is private memory
  (not shared/pixel buffers); the .NET heap is ~100–120 MB throughout. The patch's collection doesn't run here:
  it needs the closed document's rendered pages to hold ≥ 64 MB, and these vector sheets hold far less. An
  aggressive collection right after closing gives back ~150 MB (→ 362–368 MB), but within 2 s it is back to
  466–479 MB: something keeps allocating after the close. The close path itself (TabsService.CloseAsync: Release,
  then load the remaining tab) makes no thumbnails. Reported to Foundation; 36c becomes an assertion once fixed.

### 48. Foundation's sixteenth combined patch, part 2 (4f67a4c, 10 Nov)
Merged without conflicts; Reader 229/229, host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16. Closing the
5-sheet drawing now gives memory back when its drawing allocated ≥ 256 MB: cold 36c runs 5 of 7 back to 272–275 MB
from 257–259 MB. The 2 that weren't peaked lower (424–486 MB, i.e. the drawing allocated just under 256 MB) and kept
446–523 MB. With the heavy-drawing line at 64 MB (`PROPOSAL-memory-relief-10nov.md`, one line in Core): cold 6 of 6
(→ 270–277 MB), warm full pass 121/121 (548 → 726 → 351 MB). 36c stays a measurement on `platform/linux` until that
lands, then becomes the assertion (written and tested on the local branch).

### 49. Foundation's sixteenth combined patch, part 3 (3759b6f, 10 Nov)
Merged without conflicts; Reader 230/230, host kit 75/75, Linux 44/44, Web Ui 39/39, Mobile Ui 16/16. Closing one
drawing now gives its memory back every time: 36c cold, 4 of 4 (257–260 MB before, 442–545 MB with 5 sheets,
273–276 MB after closing). But the full pass (warm) failed 36c as an assertion — 341 → 671 → 680 MB — because 36b
closes a CAD tab just before, and `MemoryRelief.Request` drops a heavy close within 30 s of the last relief (or
while its 65 s follow-up runs). 36b then 36c without a fix: still 589 MB 40 s after closing. With the deferral in
`PROPOSAL-memory-relief-defer-10nov.md` (a close inside the gap waits for it; test added): 36b then 36c 3 of 3
(→ 290–292 MB, 18 s after closing), full pass 121/121 (542 → 755 → 330 MB). 36c becomes the assertion (waiting up
to 40 s) on `platform/linux` when Foundation takes it; until then it stays a measurement here.

### 50. Foundation's seventeenth and eighteenth combined patches (fc6286a, 10 Nov); B-28 fixed in the UI tests
Merged without conflicts (Chuvadi.Sheets 2.0.4; D-156 deferral; B-29/B-30 tests). Reader 233/233, host kit 75/75,
Linux 44/44, Web Ui 39/39, Mobile Ui 16/16; full UI pass 121/121.

**B-28 (Linux Test):** `rendered(i)` counted the 24 x 24 loading icon as a drawn page, so 36a–36c's draw times and
36c's memory were wrong (my mistake). A page now counts as drawn only when its page-sized svg is there. Re-measured:
- 36a: page answers ≤ 0.10 s; the landed page is drawn within 1 s of the view settling (13 s of smooth scrolling).
- 36b: now really closes mid-render; the next file draws in 0.3 s.
- 36c: the 120,000-stroke stand-in really took ~49 s a sheet and up to 2.4 GB (with sheets that never drew), far
  heavier than the real CAD file (~1 s a sheet), so it is now 10,000 strokes a sheet, sized to the real file's
  memory. Every sheet must draw within 30 s: 4.9–5.6 s each; the page answers ≤ 0.37 s. Memory is recorded: 371 MB
  before, 2.5 GB with 5 sheets drawn, 817 MB 90 s after closing.

Three findings, in `PROPOSAL-render-findings-10nov.md`: (1) a page back in view after its render was cancelled is
never drawn (one-line diff; seen with 49 s sheets); (2) moving to a page while the view fits the first drawing lands
two sheets on (36c waits for the page heights to hold); (3) after closing, the .NET heap still holds ~680 MB of
garbage that one aggressive collection clears (678 → 5 MB): the relief runs before the drawing is garbage, and ~150
MB stays outside the heap even then. 36c's memory becomes an assertion when (3) is settled.

### 51. Foundation's nineteenth combined patch (f88f9ef, 10 Nov); glibc trim after each memory relief
Merged without conflicts (the three render findings). Reader 233/233, host kit 77/77, Linux 46/46, Web Ui 41/41,
Mobile Ui 16/16. The Linux host hooks `MemoryReliefNotice.Relieved` to glibc's `malloc_trim(0)` (`GlibcTrim`;
`libc.so.6` only, turns itself off on another C library), so native memory freed by WebKitGTK and GLib goes back
too. Tests: 64 MB of small freed blocks given back to the system; hooking twice is harmless.

36c (memory still recorded, not asserted): every sheet draws (4.4–6.8 s), the page answers ≤ 0.41 s; 259 MB
before, 2.1 GB with 5 sheets, 616 MB 90 s after closing. The relief runs (2 passes, trim called each time), but
80 s after closing the .NET heap still holds 681–807 MB that one more aggressive collection clears to 3–5 MB (app
then 330–363 MB, within 100 MB of the start). So the closed drawing's memory is still held, or made, after both
passes. Reported to Foundation; 36c's memory becomes the assertion once that's found.

### 52. Foundation's twentieth and twenty-first combined patches (c7712d0, 10 Nov); page images by address on Linux
Merged without conflicts. Reader 247/247, host kit 81/81, Linux 46/46, Web Ui 41/41, Mobile Ui 16/16.
- **Page images (D-158):** the Linux host wraps its asset provider in `PageImageFileProvider` (in process, through
  the app:// scheme; no server). Two Linux fixes found by the new UI step 36d: page images are never cached
  (`private, no-store`; everything else may be), and an unknown, freed or other owner's token is "not found" (the
  scheme's fallback to the host page had answered 200). 36d: a drawn A1 sheet comes from `_chvd/pages/<token>.png`,
  its page markup is 964 characters (was ~77 MB inline), the address serves a PNG that decodes (4967 px wide), and
  an unknown token gives 404. (WebKitGTK's `fetch` reports no content type for any app:// asset, scripts and
  styles included, so 36d checks the PNG bytes and decodes it in an image element.)
- **36c memory is an assertion again:** 259–333 MB before, 860 MB–1.2 GB with 5 sheets drawn (was ~2 GB), and back
  to 247–293 MB at once after closing (within 100 MB of the start), with the glibc trim after each relief pass.
- Full UI pass 122/122 on the second run. **The first run failed 36c (and 36d after it):** a fresh open of the
  drawing kept the previous zoom (115 %), never fitted the view, showed sheet 1 as a portrait placeholder and never
  drew it in 30 s — as if the document's page sizes never arrived. Not reproduced by steps 01–19 + 36 or 20–34 + 36,
  nor by the second full run; the same symptom as x64 CI on 8dcf4d8. Reported to Foundation with the screenshot.

### 53. Foundation's patches 22 to 24 merged from platform/foundation-pr (dd59362, 10 Nov)
Excel number formats as the file holds them (D-161), the CropBox everywhere (D-160), Mark with a finger, and the fix
for the intermittent fresh-open stall. `platform/foundation-pr` carries PR #12 as one squashed commit, so the merge
conflicted in 13 shared files (none Linux-owned); resolved by taking Foundation's version of each, and checked:
every shared source and test file is identical to dd59362 (only the working repo's own CI workflows, coordination
docs and design handoff differ). No Linux change needed.

Built with warnings as errors; Reader 292/292 (3 skipped), host kit 89/89, Linux 46/46, Web Ui 41/41, Mobile Ui
16/16. Fresh-open stall: 10 of 10 opens of the drawing in one app (after a small PDF at a fixed 111 % zoom) drew
sheet 1 in 5.8–7.6 s and fitted the view (43 %); 36c as the first step in three fresh apps, 3 of 3. Full UI pass
122/122 on the first run (36c: 338 MB before, 954 MB with 5 sheets drawn, 273 MB after closing).
