# D-198 — a parsing helper process on the Mac: what the platform allows

For Foundation's design. Written from Apple's documented rules and from how this app is built today; **nothing here
has been tried on a Mac yet** — the points marked "to prove" need a run.

## Where the Mac app stands today
- **Not sandboxed.** `Platforms/MacCatalyst/Entitlements.plist` sets `com.apple.security.app-sandbox` to false, the
  app is ad-hoc signed and handed out as a zip. The Mac App Store is an open decision (it requires the sandbox).
- So today nothing in macOS stops the app starting and supervising a second process.

## Can the app start and supervise a helper? Yes — two ways

| | A. Bundled helper executable (child process) | B. XPC service |
|---|---|---|
| What it is | An executable inside the .app that the app starts itself and talks to over pipes | A small bundle in `Contents/XPCServices`; macOS (launchd) starts it on first use |
| Starting it from .NET | `System.Diagnostics.Process` is supported on Mac Catalyst; stdin/stdout pipes, exit code, `Kill` | `NSXPCConnection` from the app; the service itself needs an XPC listener — no .NET template for that |
| Same code on every host | Yes: start, pipe, time out, kill is the same shape as Windows and Linux | No: Mac-only plumbing |
| Restart after a crash | The app notices the exit and starts another | macOS restarts it on the next message |
| Its own tighter sandbox | Possible (see below) | Yes, by its own entitlements |
| Effort on the Mac | Small | Large; to prove that a .NET process can be an XPC service at all |

I would recommend **A** to Foundation: it is the one shape all hosts can share.

**What the helper executable can be** (A):
1. **The app's own executable, started again with a "parse" argument.** `Program.Main` is ours and can branch before
   UIKit starts, so no window, no Dock icon. No second runtime in the bundle. To prove: that a Catalyst binary runs
   headless this way, and what it costs to start (the app's cold start is the upper bound).
2. **A separate console program** (osx-arm64 + osx-x64, joined into one universal file) in the bundle. Clean, but it
   carries its own .NET runtime — tens of MB — unless it can be built Native AOT, which depends on the libraries.

## Supervising it: time limit yes, memory cap only by watching
- **Time limit:** the app's own timer, then kill. Reliable. (`RLIMIT_CPU` also works, but counts processor time, not
  clock time.)
- **Memory cap:** macOS gives ordinary apps **no kernel-enforced memory cap** for a child. `RLIMIT_RSS` is not
  enforced, and `RLIMIT_AS` limits address space, which a .NET runtime reserves far more of than it uses. The cap has
  to be the app polling the helper's memory (`proc_pid_rusage`, the "physical footprint" figure Activity Monitor shows)
  and killing it over the limit. That means a short overshoot between polls is possible — the design should say what
  poll interval is acceptable. This differs from Windows (job objects) and Linux (cgroups / rlimits).
- **A crash** in the helper leaves the app running; macOS writes a crash report under the helper's name.

## Entitlements
- **Today (no sandbox, ad-hoc signed):** none needed. The helper must be signed like everything else in the bundle
  (the build's ad-hoc signing covers nested executables; to prove for a second executable).
- **Signed with a Developer ID and notarised (outside the store):** the helper is signed with the same team and the
  hardened runtime; no extra entitlement for starting a child.
- **Sandboxed (App Store):** a helper the app starts must be signed with exactly two entitlements —
  `com.apple.security.app-sandbox` and `com.apple.security.inherit` — and then runs inside the app's sandbox, with the
  app's access to the files the person opened. An XPC service instead carries its own sandbox entitlements and gets
  no file access unless the app passes it the data or an open file.
- **Making the helper tighter than the app:** an XPC service can simply have no file or network entitlements. A plain
  child cannot be given a narrower App Sandbox than its parent by entitlement; passing it only the bytes of the
  document over a pipe (never a path) is the practical way to keep it away from the disk.

## What breaks for the App Store
- **Nothing in the helper idea itself.** A bundled helper or XPC service is allowed; code downloaded later is not.
- Every executable in the bundle must be sandboxed and signed by the same team; the two-entitlement rule above is
  strict (extra entitlements on an inheriting helper make it fail to start).
- The helper may run only from inside the bundle.
- To prove under the sandbox: that the app may read a child's memory figure and kill it (expected yes for its own
  child).
- The real App Store cost is unchanged and is not about the helper: the sandbox itself (opening and saving by path,
  session restore of files) — the open decision in `docs/mac/README.md`.

## What the design should settle for the Mac
1. Child process over pipes (A) for all hosts, or a Mac-only XPC service?
2. Helper = the app's own executable in a parse mode, or a separate program (size against start-up time)?
3. Document passed as bytes or as a path? Bytes keep a sandboxed helper simple and work for both A and B.
4. One helper kept warm, or one per document? Start-up cost on the Mac is to be measured.
5. The memory cap as "watched and killed within N ms", since macOS cannot enforce it in the kernel.
6. Where today's in-process parsing on the Mac host goes: the print PDF builder and the page-image hook also read
   documents in the app's process.
