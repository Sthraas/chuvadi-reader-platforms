# Chuvadi Reader for Linux

Ubuntu 24.04 and 26.04, x64 and ARM64. The same design as Windows (`ChuvadiReader.Ui`, unchanged) in our own host:

```
chuvadi-reader (apphost, .NET 10, ReadyToRun)
 ├─ ChuvadiReader.Linux     new — composition root, WebViewManager subclass, Linux platform seams
 │   └─ libchvdhost.so       new — C shim: GTK 4 window + WebKitGTK 6.0 view (native/chvdhost.c)
 ├─ ChuvadiReader.Hosting   Foundation — AddChuvadiReader(...) registers every Core service
 ├─ ChuvadiReader.Platform  Foundation — the platform contracts
 ├─ ChuvadiReader.Ui        unchanged — the whole UI
 └─ ChuvadiReader.Core      unchanged — all library use
```

| Part | How |
|---|---|
| Window | GTK 4, custom chrome (the Ui's top bar), 12 px rounded corners (square when maximised, tiled, full screen or without a compositor); window buttons on the side the desktop's GNOME/KDE button layout puts them |
| Web view | WebKitGTK 6.0, ephemeral session (nothing written to disk), pinch zoom off, Inspect Element in Debug builds only |
| Assets | `app://localhost/` URI scheme, answered in-process by Microsoft's `WebViewManager` (part of .NET's Blazor) |
| JS ↔ .NET | `window.external.sendMessage/receiveMessage` (what `blazor.webview.js` expects); one ordered queue to the page |
| Files | GTK file dialogs (`GtkFileDialog`) — real paths; window drop; `chuvadi-reader a.pdf b.docx …` and the desktop entry's `%F` — every file in its own tab (the kit's `IncomingFiles`) |
| One copy | The kit's single instance (a lock file and a Unix socket in `$XDG_RUNTIME_DIR`): a later launch hands its files to the running window, which comes forward with the launcher's activation token |
| Clipboard | GDK clipboard, text and PNG |
| Show in folder | the file manager over D-Bus (`org.freedesktop.FileManager1.ShowItems`); the folder with `xdg-open` only when there is no file manager |
| Printing | Print card → GTK print dialog → the PDF as-is to the CUPS queue over IPP (`Chuvadi.Print.Ipp`); no rendering to images, so there is no "Print to File" (it would re-render the PDF). Pages keep their own orientation unless the dialog chooses one. A file whose permissions forbid printing is refused; with no printer (or CUPS stopped) Print says so instead of opening an empty dialog |
| Folders | settings in `~/.config/Chuvadi` (XDG; kept in memory with one notice when the home folder can't be written), saves under `~/Documents/Chuvadi Documents` |
| Start-up | without a GPU: GTK's CPU renderer and WebKit's compositing off (no shader compiling on a first launch); without user namespaces (WebKit's sandbox can't start): a plain message and exit code 2 — the sandbox is never switched off |

No third-party code: only .NET, GTK, GLib, WebKitGTK and CUPS (OS components) and Arun's Chuvadi libraries.

## Prerequisites

```bash
sudo apt install dotnet-sdk-10.0 libgtk-4-dev libwebkitgtk-6.0-dev
bash scripts/setup-feed.sh        # Chuvadi packages from ci/packages into ./localpackages
```

## Build and run

```bash
dotnet build src/ChuvadiReader.Linux -c Release -warnaserror
src/ChuvadiReader.Linux/bin/Release/net10.0/chuvadi-reader [file.pdf]
```

`CHUVADI_TIMING=1` prints each startup stage to stderr. On Ubuntu 24.04+ a development build needs the
AppArmor profile loaded for its path (WebKit's sandbox needs it; the `.deb` installs it for
`/usr/lib/chuvadi-reader`):

```bash
sed "s#@CHUVADI_BINARY@#$PWD/src/ChuvadiReader.Linux/bin/Release/net10.0/chuvadi-reader#" \
  src/ChuvadiReader.Linux/packaging/apparmor/chuvadi-reader | sudo tee /etc/apparmor.d/chuvadi-reader-dev
sudo apparmor_parser -r /etc/apparmor.d/chuvadi-reader-dev
```

## Publish

```bash
dotnet publish src/ChuvadiReader.Linux -c Release              # ReadyToRun, this machine's architecture
dotnet publish src/ChuvadiReader.Linux -c Release -r linux-arm64
```

The native shim is compiled by the project (`native/build.sh`, warnings are errors), so an ARM64 build runs
on ARM64 (CI: `ubuntu-24.04-arm`) or with a cross compiler (`CC=aarch64-linux-gnu-gcc` and ARM64 `pkg-config`).

## Package and install

```bash
src/ChuvadiReader.Linux/packaging/deb/build-deb.sh out/                       # self-contained (default)
src/ChuvadiReader.Linux/packaging/deb/build-deb.sh out/ --framework-dependent # needs dotnet-runtime-10.0
sudo apt install ./out/chuvadi-reader_1.0.0~preview_amd64.deb
```

The package installs the app in `/usr/lib/chuvadi-reader`, `chuvadi-reader` on the PATH, the menu entry
with PDF / Word / Excel associations, the icons (taken byte for byte from the Windows app's `chuvadi.ico`),
AppStream metadata, the AppArmor profile, and in `/usr/share/doc/chuvadi-reader/` the copyright file
(Chuvadi Reader: proprietary, free for everyone, not open source — the repository's `LICENSE` text when it
exists, and its EULA) with Microsoft's MIT licence and third-party notices for the .NET parts the build
contains. Remove with `sudo apt remove chuvadi-reader`.

## Test

```bash
tools/linux/smoke.sh <publish dir> <out dir> 3          # launch test: first render + real pixels on screen

dotnet publish src/ChuvadiReader.Linux -c Release -p:UiTest=true -o uitest-build   # test build only
tools/linux/uitest.py uitest-build <out dir>            # full pass: every toolbar, dialogs, print to CUPS
tools/linux/compare-design.py uitest-build <out dir>    # Linux vs Chromium (WebView2's engine), same pages
```

The UI test build adds `UiTestDriver` (commands on stdin); the shipped build never contains it. The full
pass needs Xvfb, mutter, xdotool, xclip, ImageMagick, poppler-utils, qpdf (makes the no-printing fixture) and
a default CUPS queue that writes PDFs (cups-pdf). More checks, each for one fixed bug: `check-deb.py` (lintian
--pedantic clean, file modes, font copyright), `no-userns-test.sh`, `readonly-home-test.py` (as an ordinary
user), `no-printer-test.py` (CUPS stopped), `reveal-test.py`, `first-launch.py` (records the time); the comparison also needs Python Playwright with Chromium — all test tools. CI
(`.github/workflows/linux.yml`) runs, on x64 and ARM64: build, tests, publish, the launch test, both
`.deb` packages, install + launch of the installed app, and the full UI pass.

Results so far: `BUILD-LOG.md` §21–§24; screenshots in `screenshots/`; open options in
`OPTIONS-FOR-COORDINATOR.md`.
