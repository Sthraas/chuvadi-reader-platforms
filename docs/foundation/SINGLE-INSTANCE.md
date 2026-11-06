# Single instance (tabbed) — design with options (approved in principle by Arun, 7 Nov)

**Goal:** opening a file while Chuvadi runs hands it to the running copy as a new tab, on every desktop platform. **Rule:** the hand-off must not slow the first launch.

## What happens today
- **Windows ignores the file it is opened with.** `App.OnStartup` never reads `e.Args`, so "Open with Chuvadi" or a double-click starts a new, empty copy. A drop of several files opens only the first (`MainWindow.OnFileDrop`: `supported[0]`).
- **Mac:** already single instance (LaunchServices hands the file to the running app; `MacIncomingFiles`, `platform/mac` bf9651c).
- **Android:** `LaunchMode.SingleTask`; a new file arrives as a new intent in the running activity.
- **Linux:** a second copy starts (plain `gtk_init`, no `GtkApplication`).
- **Web:** not applicable (each browser tab is its own session).

## Contract and shared pieces

```csharp
// ChuvadiReader.Platform — the running copy's side.
public interface IAppInstance
{
    /// Files another launch handed over. Raised on a background thread; the kit's router marshals.
    event Action<IReadOnlyList<string>>? FilesReceived;
}
```

In the kit (`ChuvadiReader.Hosting`, BCL only):
1. **`DesktopSingleInstance.Claim(args)`**, called first thing in `Main`/`OnStartup`, before DI and before any window. It returns `Primary`, or `HandedOver`, in which case the process exits at once without showing a window.
2. **`StartListening()`**, called after the first paint (`IAppReadySignal.Ready`), on a background thread. The listening part loads the sockets/pipes assembly (≈12 ms measured), so it stays off the critical path. A second copy that arrives earlier waits up to 3 s for it.
3. **`IncomingFiles`**: one router for every way a file arrives (command line, hand-off, drop, Mac open-URL, Android intent). It is a generalised `MacIncomingFiles`:
   - It holds files until the UI is ready.
   - It keeps only readable, openable files (`DocumentFormatExtensions.IsOpenable`).
   - It sends them to the Bench shelf when the Bench is open, otherwise one Reader tab each, in order (the F-3 queue makes this safe).
   - It brings the window forward.

## Options per host

### Windows (I build this side once you pick)
| Option | How | Pros | Cons |
|---|---|---|---|
| **W-A (recommended)** | Election by a **named mutex** (`Local\Chuvadi.Reader.<user SID hash>`, one per user per session). Hand-off over a **named pipe** with the same name, current user only (`PipeOptions.CurrentUserOnly`), created after the first paint | The mutex lives in the core library: microseconds, no extra assembly at startup. The OS frees it if Chuvadi crashes (abandoned mutex = taken over), so there are no stale locks. The pipe is per user, so other users can't send paths. Pure .NET | Two mechanisms (mutex + pipe), about 150 lines |
| W-B | Pipe only: creating the server with `FirstPipeInstance` is the election | One mechanism | Loads `System.IO.Pipes` before the window (a few ms on every launch) |
| W-C | `WM_COPYDATA` to the main window (`FindWindow`/`SendMessageTimeout`) | Frozen-window detection built in (the timeout) | Needs the window to exist (race at startup); window-title matching is fragile; P/Invoke; files during the splash need extra handling |
| W-D | VB's `WindowsFormsApplicationBase.IsSingleInstance` | Ready-made | Pulls in WinForms and VB assemblies at startup (slower), takes over the WPF startup model, no control over the frozen case |

### Linux (Linux chat builds; the kit supplies the shared part)
| Option | How | Pros | Cons |
|---|---|---|---|
| **L-A (recommended)** | The kit's Unix path: election by an exclusive **lock file** in `$XDG_RUNTIME_DIR` (the kernel releases it if the process dies). The winner deletes any stale socket and listens on a **Unix socket** there after the first paint | Same kit code and protocol as Windows. Measured here: crash recovery works; election 4.3 ms in a cold test process (less inside the app, where file I/O is already loaded); the 12 ms socket set-up happens after the paint | On Wayland, raising the running window needs the launcher's activation token (`XDG_ACTIVATION_TOKEN`): the second copy forwards it and the Linux host passes it to GTK. A small host addition |
| L-B | Switch the native host to `GtkApplication` with `G_APPLICATION_HANDLES_OPEN` (D-Bus) | Desktop-standard; the activation token and window raising are handled by GTK | Reworks the Linux host's startup; needs a D-Bus session bus (missing in some kiosk set-ups); a different code path from Windows |
| ✗ | .NET named pipes as on Windows | — | **Tested and rejected:** on Linux a pipe is a socket file left behind after a crash. Every later launch then believes a copy is running and loses 500 ms timing out |

### Mac and Android
Nothing new: both are single-instance natively. They can route through the kit's `IncomingFiles` so every platform behaves the same (optional for the Mac chat, which already does this).

## If the running copy is frozen
The listener runs on its own thread, so it answers even when the UI thread is stuck. It acknowledges a file only after the UI thread has taken it.

| Option | Behaviour | Pros | Cons |
|---|---|---|---|
| **F-1 (recommended)** | The new copy waits up to **1.5 s** for the acknowledgement, then opens the file in its own window, as today. The frozen copy gives up its own attempt at 1.0 s and drops the file, so it can never open it a second time if it recovers | No new UI (the design is final); the file always opens; no duplicate tab | A 1.5 s delay in that rare case; two windows until the frozen one is closed |
| F-2 | A message: "Chuvadi isn't responding — Open in a new window / Cancel" | Tells the person what happened | A new dialog that isn't in the design |
| F-3 | Keep waiting | — | The file may never open |

Tested on Linux with a deliberately frozen primary: the hand-off normally completes in 31 ms; when frozen, the new copy gave up at 1.5 s and could open its own window.

## Startup speed (the rule)
- First launch, critical path: one mutex (Windows) or one lock file (Linux) before the window. The pipe or socket starts after the first paint. Target: under 1 ms added; it will be measured in the app with the startup probe before and after, as before.
- A launch that hands over exits before building DI or any window, so it is faster than a launch is today.

## Safety
- Per user (Windows pipe ACL is current-user only; Linux `$XDG_RUNTIME_DIR` is 0700).
- Paths are resolved to full paths by the sender. The receiver accepts at most 64 files and 64 KB per message, and only existing, openable files.
- The protocol is a length-prefixed UTF-8 list of paths plus a one-byte acknowledgement, with a version byte first so the format can change later.

## Behaviour changes for Arun's list
1. Windows opens the file it was started with (today it ignores it). A bug fix.
2. A second launch hands its file to the running copy as a new tab (the approved feature).
3. Dropping several files opens each in its own tab (today only the first). Recommended for consistency; it can stay first-file-only if preferred.
