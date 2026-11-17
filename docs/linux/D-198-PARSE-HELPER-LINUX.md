# D-198 on Linux: what a document-parsing helper process can use, and what Linux prefers

18 Nov, Linux chat, for Foundation's design. Nothing is built. Measured on this machine (kernel 6.18, glibc,
.NET 10.0.14 framework-dependent, as the `.deb` runs) with a stand-in helper; what was not measured is said.

## Recommended shape on Linux

| | Recommendation | Why |
|---|---|---|
| Which program | **The app's own binary, started again with a helper argument** (e.g. `chuvadi-reader --parse-helper`) | Nothing new in the package to install or check; same runtime and ReadyToRun code; the AppArmor profile the `.deb` already ships (`/etc/apparmor.d/chuvadi-reader`, which allows `userns` for our binary) attaches to it by path, so the namespaces below are allowed on Ubuntu |
| Started by | The app, as a **child process** (`posix_spawn` / .NET `Process`) | Dies with the app (`PR_SET_PDEATHSIG`, set in the child) |
| Talking | **Inherited pipes** (stdin/stdout), length-prefixed messages | No socket name, nothing on disk, nothing another local user can connect to |
| The file | **Opened by the app, handed over as a file descriptor**; large results (page images) back through a sealed `memfd` | The helper never needs to open a path, so it can be denied the file system |
| Lifetime | One helper per document being parsed, or a small pool reused and **replaced after a crash, a limit hit, or N documents** | A crash costs one document, not the app; start cost below |
| On a limit hit | The app shows the document as "could not be opened safely" and keeps running | — |

## Limits: what works for a .NET helper, measured

| Mechanism | Result | Use |
|---|---|---|
| **`DOTNET_GCHeapHardLimit`** (env var, set by the parent) | Clean `OutOfMemoryException` at the cap (512 MB set: stopped at 496 MB), the helper can report and exit | **The memory cap.** Covers the managed heap, which is nearly everything for pure-managed libraries |
| `RLIMIT_AS` (`setrlimit`, address space) | **Breaks .NET**: the GC reserves address space up front; at 256 MB, 512 MB and 1 GB the runtime does not start ("GC heap initialization failed", exit 137), even with a GC limit of 512 MB. Starts at 2 GB | Not usable as a cap |
| `RLIMIT_DATA` (private writable memory) | 256 MB: clean `OutOfMemoryException` at 160 MB. 512 MB: the runtime itself failed (`Win32Exception: Cannot allocate memory`, abort). 1 GB: fine | A backstop only, set well above the GC cap (e.g. GC cap + 512 MB); unpredictable when tight |
| **`RLIMIT_CPU`** | Kills a busy loop at the limit (CPU seconds, not wall time) | Backstop for a parser spinning |
| **Wall-clock watchdog in the app** | Always available | **The time limit**: the app kills the helper (`SIGKILL`) after N seconds without an answer |
| `RLIMIT_CORE = 0`, `PR_SET_DUMPABLE 0` | — | A crash must not write the document's contents to disk as a core dump (matters for patient records) |
| `RLIMIT_NOFILE` small (e.g. 32) | — | The helper needs a handful of descriptors |
| cgroup v2 `MemoryMax` / `CPUQuota` (through the systemd user manager: a transient scope over D-Bus, `org.freedesktop.systemd1.Manager.StartTransientUnit`, GLib's D-Bus, nothing external) | Not measurable here (no cgroup controllers in this container). On Ubuntu/Fedora desktops the user manager delegates them | **Optional extra**, kernel-enforced and counting native memory too. Must not be required: no systemd user session on some systems (some containers, WSL, non-systemd distributions) |

Start time of a small framework-dependent ReadyToRun .NET helper, warm: **34–41 ms** (first run 68 ms). A real
helper loading the document libraries will be more; not measured. So per-document start is affordable; per-page is not.

## Isolation beyond limits

| Mechanism | Linux view |
|---|---|
| **User + network namespace** (`unshare(CLONE_NEWUSER \| CLONE_NEWNET)` in the child, before the runtime starts) | **Preferred first step**: the helper has no network at all, with no rule list to maintain. On Ubuntu 24.04+ unprivileged user namespaces need an AppArmor `userns` rule, which our profile already gives our binary (B-15). Where namespaces are refused, the helper still runs, without this layer |
| seccomp filter | Possible, but: (1) the "no externals" rule rules out libseccomp, so the BPF filter is hand-written in the native shim; (2) an **allowlist** for the .NET runtime is fragile: a runtime update that uses a new syscall kills every helper. If used, a **short denylist** (`socket` for AF_INET/AF_INET6, `connect`, `execve`, `ptrace`, `process_vm_*`, `mount`) with `PR_SET_NO_NEW_PRIVS`, installed after start-up. Second step, after the namespace |
| Landlock (file system) | Kernel 5.13+; with the file handed over as a descriptor the helper can be denied all paths. Third step; needs a fallback where the kernel lacks it |

## What Linux would ask of the shared design
1. The helper is the app's own binary with an argument, so every host can decide how to start it.
2. The parent opens the file and hands over a descriptor (or the bytes), never a path.
3. Limits are set by the host (each platform differs); the shared code only needs "the helper died / timed out / ran out of memory" as answers it shows to the person.
4. A message format that does not need the helper to touch the network or the file system.

## Not measured here
A real helper with the document libraries loaded (start time, memory at rest); cgroups on a desktop; what the
namespaces cost at start-up; any of this on KDE/Fedora.
