# What Web would do for advisory gaps 1, 2 and 4 — notes for the Foundation's parse-process design

**For:** the Foundation (D-198: a separate parse process on every host; the portal's worker is the model it must fit) and the coordinator. **From:** Web, 18 Nov 2026. **Nothing here is built** (D-198: not until the Foundation's design says where the shared part sits). Gap 3 (Single mode refused in production) is built; see BUILD-LOG step 43. Background: `SECURITY-ADVISORY-WEB.md`.

## What the portal's worker already is, as the model

| Property | Today on the portal |
|---|---|
| One process holds every parsing library | The worker (`Portal:Mode=Worker`), one per signed-in person, started by the gateway. The gateway loads no Chuvadi library. |
| Talks to its supervisor over a private channel | A Unix socket, every call signed with a per-worker secret, the secret given on standard input. The worker ends when that input closes. |
| The supervisor can see whether it is alive | `/health` every 30 s (`tabs`, `circuits`, `connected`, `sessions`); three missed answers end it. Every supervisor call has a 10 s limit (WT-24). |
| A crash is contained | Proven (`worker_crash.py`, three engines): gateway and other people untouched, files removed, the person carries on in a fresh worker. |
| Memory | Managed-heap cap only (`DOTNET_GCHeapHardLimit`, 1,536 MB). No operating-system cap yet (gap 2). |
| Time | None from outside (gap 1). |

What a desktop host will not have that the portal has: a supervisor that already exists and outlives the parser. On the portal that is the gateway; on the desktop it would be the app itself.

## Gap 1 — a time limit on PDF open and draw, enforced from outside

**The problem.** A parse that spins without checking its cancellation cannot be stopped from inside the process. Today `/health` still answers while one thread spins, so the gateway sees a healthy worker.

**What the supervisor needs to know:** whether a parse operation is in progress, of what kind, and since when. Liveness alone is not enough.

**What I would do:**

1. **A shared hook around every library call (this is the shared part).** For example `IParseWatch.Begin(kind, fileName) → IDisposable`, with kinds such as open, draw page, search and save. The Core wraps each call into Chuvadi.Pdf, Sheets, Docs and so on. The parse process exposes the operations in progress.
2. **On the portal**, `/health` would add `busy: [{ kind, since }]`. A separate fast check in the gateway (every 2 s, its own call with the 10 s limit) ends the worker when an operation runs past its limit. Suggested limits: open 60 s (as Word and Excel already have inside), drawing one page 30 s. They must be measured against the Foundation's corpus of honest heavy files before they are fixed; the heaviest page I measured took about 1 GB and drew in seconds, not tens of seconds.
3. **A worker that doesn't answer the fast check** within its limit three times running is ended too (a worker stuck in native code may not answer at all).
4. **What the person sees** is gap 4's message, with the reason "took too long".

**An alternative without the shared hook:** the gateway reads each worker's CPU time from `/proc/<pid>/stat` and ends one that has used about one core for T seconds without delivering a page. It needs no shared code, but it is a guess. It cannot tell a spinning parse from an honest heavy one, and it is Linux only, so it is no model for other hosts. **I recommend the hook.**

**A cost to decide:** ending a worker closes **every** document that person has open, because there is one worker per person. A process per document would avoid that, but costs about 120 MB each when idle (measured: 118–122 MB for a new worker). For the portal I would keep one per person in Phase 2; the desktop may choose differently.

## Gap 2 — an operating-system memory cap per worker, and the service-wide limit

### Measured here

This machine runs cgroup v1 with no systemd as process 1. The scratch script is `/tmp/claude-0/-home-claude/7ffac0d2-b192-5ac5-a2f0-9f100b859181/scratchpad/memcap.py`; the heavy file is a PDF with one 5000 × 5000 image.

| Setup | What happened |
|---|---|
| **Per worker:** the heavy person's worker alone in a memory group with a 600 MB limit | It reached 681 MB peak resident memory. After 3 s the kernel ended it (logged as "Memory cgroup out of memory: Killed process …"), and the gateway logged exit code 137. The gateway stayed healthy, the other person's next pages drew, and the files were cleaned up. The heap cap (1,536 MB) never came into play. |
| **Service-wide:** gateway and all workers in one group, limit 650 MB (twice) | The kernel ended the **largest process, the heavy person's worker**, both times. The gateway and the other person were untouched. At 900 and 1,200 MB the limit was never reached (peak use of the whole group was 860 MB). |
| **Address-space limit** (`prlimit --as`) on a worker-sized process | At 2 GB it could not even start ("Out of memory"). At 4 GB it started but failed under use. At 8 GB it worked. The .NET runtime reserves large ranges of address space, so this limit is **unusable** as a memory cap. |

**Bug found and fixed during this measurement (WorkerPool, Web).** When a worker was killed, the page reconnected at once and its replacement started in the same folder. The dead worker's exit handler, arriving late, could then delete the **live** worker's files and socket, or make the new start fail with an error the person saw. Both clean-ups now take a per-person lock, and a late one leaves a newer worker's files alone. Test: `A_dead_workers_late_clean_up_leaves_its_replacements_files_and_socket_alone`.

### Not measured: what systemd does

**I could not test OOMPolicy here,** because this container has no systemd running. systemd's documented default is `OOMPolicy=stop`: when the kernel ends any process of the service for memory, systemd stops **the whole service**. With `Restart=always` it starts again 3 s later, with everyone signed out and every open document gone. So the kernel's sensible choice above (end the heavy worker) would be turned into a portal-wide outage. **This has to be tested on the real host before Phase 2** (steps below). We should not rely on the default.

### What I would do (portal only; no shared code)

1. **In the unit:**
   - `OOMPolicy=continue`, so one worker ended for memory never stops the service.
   - `Delegate=memory pids`, so the gateway may manage memory groups under its own part of the tree.
   - Keep `MemoryMax=` for the whole service as the last line.
2. **The gateway gives each worker its own group:**
   - Paths `…/chuvadi-portal.service/workers/<key8>` and the gateway itself in `…/gateway`, because cgroup v2 allows no process in an inner node.
   - Settings per group: `memory.max` (suggested 1.5 GB), `memory.swap.max=0`, and `memory.oom.group=1` so the whole worker goes together.
   - The worker is moved in right after it starts. The window before the move is a few milliseconds, before it reads anything, since a worker opens nothing until its first request.
   - This uses only operating-system interfaces (files under `/sys/fs/cgroup`), so it is inside the no-externals rule.
3. **Keep the heap cap below the group's limit**, so an over-large open usually fails politely inside the worker ("not enough memory to open this file") before the kernel has to end it. One caveat: what the worker does on reaching its heap cap is untested; it is part of the test below.
4. **`OOMScoreAdjust=-500` for the gateway** (set by the unit on the service, then raised back to 0 for each worker as it starts), so that under the service-wide limit the kernel always prefers a worker.

### Test on the real host (Ubuntu with systemd, before Phase 2)

1. Install the service with the runbook's unit and `MemoryMax=1500M` for the test. Sign in as two people. One opens the heavy PDF until the kernel ends their worker.
2. **With the default policy:** expect, per the documentation, the whole service to stop and restart. Record it with `journalctl -u chuvadi-portal`.
3. **With `OOMPolicy=continue`:** expect only that worker to go, the other person to be unaffected, and the person to be put on a fresh worker.
4. **With per-worker groups** (once built), the same at 1.5 GB per worker, with the service-wide limit not reached.

## Gap 4 — a message when a person's worker died, and slowing down repeated crashes

**What the gateway knows** when a worker ends: its exit code and signal (137 for killed, 134 for the runtime's own abort, which is what a stack overflow gives); whether the gateway itself ended it (gap 1's time limit, or no health answers); and, once gap 1's hook exists, which operation and file name were in progress at the last check.

**The message (needs a shared Ui seam):**
- The replacement worker is started with the reason, and the Ui shows a message on Home once, for example: "The portal had to stop while opening **report.pdf**, and your open documents were closed. If it happens again, the file may be damaged."
- Variants for "took too long" and "used too much memory".
- The shared part is a way for a host to hand the Ui a message to show at start (an existing message seam may do).
- The file name stays in the gateway's memory only, for that person's session.

**Slowing repeats (Web only):**
- **Refuse the same file again:** the worker computes a SHA-256 of each upload as it is stored. The gateway keeps, in memory and for that person only, the hashes of files that were being opened when their worker ended. An upload with the same hash within the session is refused with "This file stopped the portal before, so it isn't opened again."
- **Back off after repeated crashes:** 3 worker deaths in 10 minutes and the gateway holds new worker starts for that person for 1 minute, then 5 minutes on the next, with a page saying why and until when. It resets after 30 minutes without a crash. Sign-in and sign-out keep working; only opening is held.
- Other people are never affected by this; it is per person.

## Where the shared part would sit (my reading; the Foundation decides)

| | Shared (Foundation) | Portal (Web) |
|---|---|---|
| 1 | The hook around library calls, and how a parse process reports operations in progress | The fast check in the gateway, the limits, ending the worker |
| 2 | Nothing for the portal (a desktop parse process needs its own cap: Job objects on Windows, cgroups on Linux) | Unit settings, per-worker memory groups, the real-host test |
| 4 | A way to hand the Ui a message at start; the file name from 1's hook | Counting deaths, refusing the same file, the back-off |
