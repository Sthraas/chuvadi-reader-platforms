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

## Foundation's prototype bench on Linux (18 Nov; D-202 approved the design)
`tools/ParseProcessPrototype` from Foundation's design commit 82fe982f, unchanged, `bench` with its defaults
(engine heap cap 512 MB, 10 s per request). Foundation's own files are not in the repo, so the files are made by
`tools/linux/make-parse-bench-files.py` (test only, fixed seeds, the same on every machine): a 12-page text PDF,
a 400-page vector grid, a 20-page scan, a 5-sheet A1 CAD drawing (B-27's kind), a flate bomb (560 MB unpacked),
a 2,000-paragraph Word file, the repo's `discharge.docx` and `layout.xlsx`, a 20,000-row workbook, and two probes
(a page tree 2,000 deep, an array nested 200,001 deep). CI: the `parse-bench` job in `linux.yml`, run on
ecd0ee5d (it runs only for a commit whose message holds `[parse-bench]`); reports are the run's artifacts.

| | this machine | CI x64 runner | CI ARM64 runner |
|---|---|---|---|
| machine | Ubuntu 24.04.5, x64, 2 cores, .NET 10.0.14 | Ubuntu 24.04.5, AMD EPYC 9V74, 4 cores, 16 GB, .NET 10.0.15 | Ubuntu 24.04.5, Arm64, 4 cores, 16 GB, .NET 10.0.15 |
| engine start, first / median | 28 / 27 ms | 51 / 44 ms | 48 / 41 ms |
| engine idle memory | 27 MB | 33 MB | 32 MB |
| first document, open and page 1: in the app / new engine (start included) | 97 / 124 ms | 125 / 165 ms | 117 / 150 ms |
| wire, 6,000 KB there and back | 19 ms | 19 ms | 17 ms |
| page, text PDF, in-process / engine (median) | 3.0 / 2.9 ms | 4.1 / 6.1 ms | 5.7 / 7.7 ms |
| page, scan PDF | 75 / 79 ms | 58 / 56 ms | 57 / 57 ms |
| page, CAD sheet (6.9 MB of SVG a page) | 5.1 / 5.2 s | 4.0 / 4.1 s | 2.9 / 2.9 s |
| engine memory after drawing | 119 MB | 150 MB | 126 MB |
| Word: discharge.docx / long-2000p.docx, in-process / engine | 24/27, 29/30 ms | 20/20, 21/24 ms | 30/32, 26/32 ms |
| Excel: rows-20000.xlsx | **fails in the engine: OutOfMemory at 512 MB** | same | same |
| stack overflow: noticed after / file back | 14 ms / 123 ms | 404 ms / 118 ms | 598 ms / 133 ms |
| endless loop: ended at the limit / file back | 10.0 s / 121 ms | 10.0 s / 109 ms | 10.0 s / 135 ms |
| allocating without end: refused after / file back | 226 ms / 118 ms | 202 ms / 112 ms | 169 ms / 134 ms |
| deep page tree, nested array, flate bomb | all refused, app up | all refused, app up | all refused, app up |

What this says for Linux:
- **The design holds on Linux, x64 and ARM64.** The engine adds about 25–40 ms to the first open (its start) and
  0–2 ms a page; every failure (uncatchable stack overflow, endless loop, runaway memory, the three crafted files)
  ends or refuses in the engine while the app carries on, and the file is back in 110–135 ms.
- **The 20,000-row workbook needs more than the 512 MB cap**, on every machine. With the cap raised it loads
  (1 GB: 620 ms in the engine against 300 ms in-process) and the model sent back is **79 MB of JSON**: the memory
  goes into sending the whole grid, not into reading the file (1 MB). For Foundation's contract: send a workbook a
  window of rows at a time (or in a compact binary form), or the cap stops ordinary large spreadsheets.
- **Stack size differs by machine:** 8 MB here and on a typical desktop, 16 MB on the CI runners (their default
  `ulimit -s`). A deeper stack takes longer to overflow (14 ms here, 400–600 ms on the runners) but the engine still
  dies alone. The engine should not depend on the inherited stack size for its depth limits.
- **The CAD drawing is the only slow page** (3–5 s a sheet, B-27), and it is as slow in-process; the engine costs
  1–2 % on it.

## Not measured here
A real helper with the document libraries loaded (start time, memory at rest); cgroups on a desktop; what the
namespaces cost at start-up; any of this on KDE/Fedora.
