# The portal under the parse-process design (D-202): what Web builds, and what it needs from the kit

**For:** the Foundation and the coordinator. **From:** Web. **Updated 18 Nov 2026** to follow `PARSE-PROCESS-DESIGN.md` as Arun approved it (D-202). The portal is step 5 of the design's build order. **Nothing here is built yet**, apart from Single mode being refused in production (BUILD-LOG step 43). The first version of these notes (17–18 Nov, before D-202) proposed a gateway watchdog and a gateway-only fix; this replaces it.

## 1. The portal under D-202, in one paragraph

Each signed-in person keeps their own worker process; nothing changes for the gateway's relay, sign-in or sessions. Parsing leaves the worker: the worker starts an **engine** of its own (as the Linux host does), and every Chuvadi library call goes there. A file that kills the engine kills only the engine. The person's session, tabs and unsaved work stay, and they see the shared bar on the tab. Each engine has a **1 GB cgroup cap** plus a heap cap, and the worker's own cap comes down once parsing has left it. A file that stops an engine **twice** is refused at upload for that person for the rest of the session. **Three deaths in a minute** (of engines or of workers) and starts are held back. The Foundation builds the worker-engine contract in the kit; Web builds the gateway's parts.

## 2. Who builds what

| Part | Foundation (kit, shared) | Web (portal) |
|---|---|---|
| The engine, its protocol, the app halves of the services | ✔ | |
| `IParseEngineHost` for the portal: start the worker's engine, hand back its streams, end it | The contract | The portal's implementation, in the worker. It starts the engine as the Linux host does, with `PR_SET_PDEATHSIG` so the engine dies with its worker, and puts the engine in its own cgroup (W-1). |
| Time limits per request (open 30 s, draw 30 s, Word/Excel 60 s, cells 10 s, jobs 60 s without progress) | ✔ The kit keeps the clock in the worker and ends the engine | Nothing extra. The gateway keeps supervising the worker as today (health every 30 s, three missed answers end it; every call has a 10 s limit, WT-24). |
| The bar on the tab, "Try again" / "Close the file", the reasons | ✔ (shared Ui) | |
| A file that stopped an engine twice: not reopened automatically | ✔ within one worker's life | Across the worker's death, and at upload (W-4) |
| 3 deaths a minute → wait 5, 20, 60 s | ✔ for engines within one worker's life | The same rule per person across workers, and for workers themselves (W-3) |
| Memory caps from the operating system | | Per engine 1 GB and per worker lowered: W-1. Unit changes and the real-host test: W-5 |
| When a worker itself dies: a page that says what happened, and "Start again" | | W-2 (with WT-28) |

## 3. What Web will build (W-1 to W-6), in order

**W-1. Memory groups per worker and per engine**

- **Unit:** `Delegate=memory pids`, so the service user owns its part of the cgroup tree. `OOMPolicy=continue`, so one process ended for memory never stops the service. `MemoryMax=` stays as the last line for the whole service.
- **The tree:** the gateway lives in a leaf `…/chuvadi-portal.service/gateway`, because cgroup v2 allows no process in an inner node. Each person gets `…/workers/<key8>/worker`, and each engine `…/workers/<key8>/engine-<n>`.
- **Engine group:** `memory.max=1G`, `memory.swap.max=0`, `memory.oom.group=1`. The engine's heap cap stays below it (suggested 768 MB), so most over-large files fail politely inside the engine first. The design measured exactly that at 512 MB.
- **Worker group:** a lowered cap, to be measured once parsing has left (W-6). My guess is 512 MB, with its heap cap at 384 MB; today the heap cap is 1,536 MB.
- **Placing processes:** the gateway places each worker, and the worker places its engine. Both are the same user under delegation. The process is moved in right after it starts, before it reads anything.
- **Fallback:** without delegation (for example a non-systemd host in development), log once and run with heap caps only.

**W-2. When a worker itself dies: say so, and "Start again"**

- The gateway knows the exit code and whether it ended the worker itself.
- The next page that person reaches shows, in plain words: "Your documents had to be reopened: the portal's reader for you stopped." Then a **Start again** button, instead of today's "Your session stopped. Please reload the page to start again."
- **WT-28 is fixed in the same piece:** a reload within about a second of a worker's death lands on that message and needs a second reload. The gateway logs an antiforgery key the new worker doesn't have: each worker has its own data-protection keys, so a page from the dead worker can't post to its replacement.
- A worker death should now be rare; what remains are worker bugs and the worker's own memory cap.

**W-3. A per-person crash ledger in the gateway**

- Worker deaths (seen by the gateway), plus engine deaths, which the worker reports to the gateway as they happen.
- Three in a minute: the next worker start for that person waits 5, then 20, then 60 s. The page says so and until when.
- The ledger is handed to each new worker at start, so the kit's engine back-off carries on where it was rather than starting at zero.
- It is per person, in memory only, and dropped when the session ends. Other people are never affected.

**W-4. Refusing at upload a file that stopped an engine twice**

- The kit tells the worker which file a dead engine was reading. The worker sends the gateway that file's fingerprint (SHA-256 of the whole file, computed in the worker) with the death.
- After the second death, the fingerprint goes on that person's refused list. The gateway hands the list to the worker at start and on every change, so it survives a worker's death.
- The upload check (`TransferRegistry`, already Web's) refuses a matching upload with: "This file stopped the portal's reader twice, so it isn't opened again in this sign-in."
- In memory only, per person, dropped at session end. No file name or content is kept, only the fingerprint.

**W-5. On the real host**

1. **Test OOMPolicy before anything else.** Under the default `stop`, one process ended for memory should, per systemd's documentation, stop and restart the whole service. Under `continue`, only that process should go. Expected; not yet seen.
2. Then the groups from W-1.
3. Then the design's prototype bench on the portal's server (design section 9: `dotnet run -c Release --project tools/ParseProcessPrototype -- bench <folder>`).
4. Update the runbook's sizing table. Per person the worst case becomes a worker (lowered) plus a viewing engine (1 GB cap) plus a tool engine during a job (1 GB cap).

**W-6. Lowering the worker's cap**

Measure the worker's memory with the engine in place (10 people, the usual files), then set the worker's heap and cgroup caps from that. Measure before deciding; my guess is in W-1.

## 4. What Web needs from the kit (for the Foundation's contract)

1. **An event on the engine client when an engine dies**, with the reason (crash, time limit, memory), the request that was running, and the path of the file it was reading. The worker turns that into the report to the gateway (W-3, W-4).
2. **A way to seed the kit at worker start:** its back-off state (recent deaths and when) and the refused fingerprints. Then a worker that replaces a dead one carries on, rather than giving a hostile file three fresh tries.
3. **When the engine starts, on the portal:** I recommend option E2, on the first document, as the design recommends for Android. With up to 40 people on a server, 27 MB for every signed-in person who has opened nothing adds up, and 25 ms on a first open is not noticed on the web. A per-host switch in the kit would do.
4. **Tool engines (option A2) on the portal:** one at a time per person. A second writing job waits for the first, so one person can't hold several 1 GB engines. If the kit queues jobs per app instance, that is already so; please say.
5. **Session end:** the kit ends the engines when the worker's last session ends, and their memory goes with them, so WT-21 (page images held until the worker stops) disappears for engine-held data. Please confirm that the page images stay in the worker, or move to the engine.
6. **The fingerprint:** if the kit wants to keep "stopped twice" itself, use SHA-256 of the whole file, so the worker and gateway can share the same value.

## 5. Measured on this machine (still valid; the method under W-1 is the same)

This container runs cgroup v1, with no systemd as process 1. The scratch script is `/tmp/claude-0/-home-claude/7ffac0d2-b192-5ac5-a2f0-9f100b859181/scratchpad/memcap.py`; the heavy file is a PDF with one 5000 × 5000 image.

| Setup | What happened |
|---|---|
| Per worker: one worker in a 600 MB memory group | It peaked at 681 MB resident. The kernel ended it after 3 s and the gateway logged exit code 137. The gateway stayed healthy, the other person's next pages drew, and the files were cleaned up. The heap cap (1,536 MB) never came into play. |
| Service-wide: gateway and every worker in one 650 MB group (twice) | The kernel ended the **largest process, the heavy person's worker**, both times; never the gateway. At 900 and 1,200 MB the limit was not reached (the whole group peaked at 860 MB). |
| Address-space limit (`prlimit --as`) | At 2 GB the process could not start; at 4 GB it started but failed under use; at 8 GB it worked. Unusable, as the design also found. |

**Found and fixed while measuring:** a dead worker's clean-up, arriving after its replacement had started in the same folder, could delete the live worker's files and socket. Fixed in step 43, with a test.

**Not testable here:** systemd's `OOMPolicy` (W-5).

## 6. What D-202 replaced in these notes

- **A gateway watchdog for spinning parses** (CPU time, or a "busy since" in the worker's health): replaced by the kit's own per-request clock in the worker. The worker no longer parses, so a stuck parse can't make it miss its health answers.
- **Refusing a file after one crash:** D-202 says twice.
- **A message from the Ui on Home after a worker death:** most deaths are now engine deaths and get the shared bar on the tab. Only a worker death gets the gateway's page (W-2).
