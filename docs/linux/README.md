# Chuvadi Reader for Linux

Ubuntu, x64 and ARM64. Same design as Windows (`ChuvadiReader.Ui`, unchanged), in our own host:

```
chuvadi-reader (apphost, .NET 10)
 ├─ ChuvadiReader.Linux     new — composition root, WebViewManager subclass, platform services
 │   └─ libchvdhost.so       new — C shim: GTK 4 window + WebKitGTK 6.0 view (native/chvdhost.c)
 ├─ ChuvadiReader.Ui        unchanged — the whole UI
 └─ ChuvadiReader.Core      unchanged — all library use
```

- **Window:** GTK 4, custom chrome (the HTML title bar), client-side frame with resize edges.
- **Web view:** WebKitGTK 6.0 with an ephemeral session (nothing written to disk).
- **Assets:** an `app://localhost/` URI scheme answered in-process by Microsoft's `WebViewManager`
  (from `Microsoft.AspNetCore.Components.WebView`, part of .NET's Blazor).
- **JS ↔ .NET:** `window.external.sendMessage/receiveMessage` (what `blazor.webview.js` expects),
  carried by a WebKit script-message handler one way and `evaluate_javascript` the other.
- **Threading:** Blazor runs on its own synchronization context; anything that touches GTK is
  posted to the GTK main thread (`GtkHost.Post`).
- **Dev tools:** Inspect Element only in Debug builds.

No third-party code: only .NET, GTK, GLib and WebKitGTK (OS components).

## Prerequisites (Ubuntu 24.04 / 26.04)

```bash
sudo apt install dotnet-sdk-10.0 libgtk-4-dev libwebkitgtk-6.0-dev
```

## Build and run

The working repo holds only the new Linux files. `prepare-tree.sh` checks out chuvadi-reader at the
pinned commit, adds them, fills the local package feed, and fails if any existing file differs.

```bash
tools/linux/prepare-tree.sh ./reader
dotnet build reader/src/ChuvadiReader.Linux -c Release
reader/src/ChuvadiReader.Linux/bin/Release/net10.0/chuvadi-reader [file.pdf]
```

`CHUVADI_TIMING=1` prints every startup stage to stderr.

## Publish

```bash
dotnet publish reader/src/ChuvadiReader.Linux -c Release -r linux-x64   --self-contained false -o publish-x64
dotnet publish reader/src/ChuvadiReader.Linux -c Release -r linux-arm64 --self-contained false -o publish-arm64
```

ReadyToRun is on. The native shim is built by the project (`native/build.sh`, warnings are errors).
An ARM64 publish must run on ARM64 (CI uses `ubuntu-24.04-arm`) or with a cross compiler
(`CC=aarch64-linux-gnu-gcc` and ARM64 `pkg-config` files).

## Test

```bash
tools/linux/smoke.sh publish-x64 smoke-out 3   # Xvfb + mutter (test-only tools)
```

Passes when Blazor's first render arrives within 30 s with no logged error; writes timings and a
screenshot. CI (`.github/workflows/linux.yml`) runs build, the Reader's tests, publish and this test
on x64 and ARM64.

## Package and install

`.deb` packaging, desktop entry, icon and file associations: in progress (see BUILD-LOG).
