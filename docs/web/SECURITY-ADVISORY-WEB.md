# The portal and the library security advisory (17 Nov 2026)

**For:** the coordinator and the Foundation's shared assessment. **From:** Web. **Build looked at:** `platform/web` at patch 31 with the WT-26 and WT-27 fixes (the code named below has not changed since `35a7adda`).
**Asked:** until patched libraries land (Pdf 3.35.1, Sheets 2.2.1, Docs 2.4.1, Zip 1.0.2 and others), a crafted file can end the parsing process with a stack overflow that cannot be caught. Does the portal contain that? **Nothing in the product was changed for this note.** One test script was added (`tests/web-e2e/worker_crash.py`).

> **Status, 18 Nov (D-198):** the patched libraries gate Phase 2; a separate parse process on every host is to be built, with this worker as the model. Gap 3 is done: the portal refuses `Portal:Mode=Single` outside Development (BUILD-LOG step 43). Gaps 1, 2 and 4 now follow the parse-process design Arun approved (D-202): each person's worker gets its own engine. What Web builds for it, and what it needs from the Foundation's kit, is in `PARSE-PROCESS-NOTES-FOR-FOUNDATION.md` (updated 18 Nov). The note below is as written on 17 Nov.

## The short answer

In **gateway mode** (what the runbook deploys) a crafted file ends **one person's worker** and nothing else. The gateway stays up, other people go on working, the dead worker's files are removed, and the person can carry on in a fresh worker. That is proven below with a worker killed mid-open.

There are four gaps, in order of weight:

1. **No time limit on opening or drawing a PDF.** A file that makes the library spin (rather than crash) holds one CPU core in that person's worker until their session ends. Word, Excel and text have a 60-second limit; PDF has none.
2. **The memory cap is on the managed heap only (1,536 MB), not on the process.** And the caps add up to far more than the machine has: one service-wide limit sits above them, and if the kernel has to enforce it, systemd's default is to stop the **whole portal**.
3. **`Portal:Mode=Single` has no isolation at all** and is the value in the shipped `appsettings.json`. A crafted file there takes the whole portal down. The runbook sets Gateway; nothing refuses Single in production.
4. **A crashed worker is silent for the person** (they land on an empty Home with their documents gone and no message), and **nothing slows a person who uploads the same crashing file again and again** (each try costs a worker start).

## 1. Does each person's worker have a memory cap, and how much?

**Yes, on the managed heap: 1,536 MB by default** (`Portal:Workers:MemoryLimitMB`; the runbook's table gives 1,024 for an 8 GB machine).

- Where: `WorkerPool.StartInfo` sets `DOTNET_GCHeapHardLimit` (seen on a running worker: `0x60000000` = 1,536 MB) and `DOTNET_gcServer=0`. Test: `A_worker_gets_a_private_home_a_memory_cap_and_none_of_the_gateways_secrets`.
- **What it is not:** an operating-system limit. On a running worker, `/proc/<pid>/limits` shows resident set, address space and CPU time all **unlimited**. Memory outside the managed heap (native buffers, thread stacks, the runtime itself) is not counted. Past the cap the runtime throws out-of-memory inside the worker; I have **not tested** what the worker then does (it may fail the one open, or end).
- **Stack:** 8 MB for the main thread (the system default), the runtime's default for others. No setting of ours. A stack overflow ends the process whatever the size.
- **The sum is over-committed.** The runbook's recommended machine is 16 GB with 40 workers at 1,536 MB: 61 GB of caps on a 16 GB machine. It works because people rarely come near the cap. Crafted files could bring several workers to their caps together.
- **Above the workers, one limit for the whole service:** the runbook's unit has `MemoryMax=<VM RAM minus 1.5G>` for gateway and workers together. If that is reached, the kernel kills a process in the group (usually the largest, so a worker, but it does not have to be). **systemd's default `OOMPolicy` is `stop`: when the kernel kills any process of a service for memory, the whole service is stopped** (and `Restart=always` starts it again 3 s later, with everyone signed out and every open document gone). This is from the runbook and systemd's documented default; **not tested here**.
- **Crash dumps:** the worker's environment turns the runtime's dump off (`DOTNET_DbgEnableMiniDump=0`, `DOTNET_EnableCrashReport=0`) and the unit has `LimitCORE=0`, so a crash should not write a person's document memory to disk. In the test below no dump file appeared (this machine also has core files off, so that part rests on the unit setting).

## 2. Is there a time limit on opening and rendering a document?

**For Word, Excel, text, Markdown and HTML: yes, 60 seconds. For PDF: no.** These limits are in the shared Ui and Core, not in Web.

| Kind | Opening | Drawing |
|---|---|---|
| Word, Excel | After 10 s a note with "Stop opening"; after 60 s the open is cancelled and "gave up" is shown (`ViewerBase`, `SlowOpenNote.GiveUpAfter`). The cancellation reaches the library, which checks it at every XML node. Excel is read with `XlsxReaderOptions.ForUntrustedInput()` (D-155); Word with the server limits, 20 MB a part and 64 MB in all (D-137). | Part of the open. |
| Text, Markdown, HTML | Same 60 s. | Same. |
| **PDF** | After 10 s the note with "Stop opening" (the person must press it). **No automatic limit that I can find.** | **No time limit.** A page's drawing is cancelled only when the tab closes, and the library call that draws a page takes no cancellation (`renderer.RenderPage(document, pageNumber)`). |

Two things follow, and they hold for every kind:

- **A cancellation only works if the library looks at it.** A parser stuck in a loop that never checks cannot be stopped from inside the process. Only ending the worker stops it.
- **Nothing outside the worker watches for that.** The gateway checks a worker's health every 30 s, but a worker with one thread spinning still answers, so it is not stopped. It runs until the person's session ends (30 minutes idle, 8 hours at most) and the worker is then stopped. With 40 workers on 8 cores, eight such files would take all the CPU.

Other limits that are in place (Web): upload size 200 MB a file (`Portal:MaxUploadBytes`), 50 files a pick, 64 a drop; the gateway's own calls to a worker 10 s (WT-24).

## 3. What happens to the gateway and to other people when one worker dies? (Proven)

**Nothing happens to them.** `tests/web-e2e/worker_crash.py`, gateway mode, run in Chrome, Firefox and WebKit on fresh portals, 11 of 11 checks each:

Two people. The second has a PDF open. The first has one PDF open and is uploading a second; while that upload and open are under way their worker is ended with `SIGKILL`.

| Checked | Result |
|---|---|
| Each person has their own worker process | Yes (two process ids) |
| The gateway | Alive, health check answers, before and after |
| The other person | Their next three pages draw; same worker process as before |
| The dead worker's files (the first person's uploaded PDF) | Removed, 3.1 s and 3.6 s after it died |
| Memory dump left behind | None |
| Gateway log | `Worker a855f28d (pid 4321) ended with code 137` (a warning) |
| The first person | Still signed in after a reload, on a **new** worker process, with **no** open documents; can upload and open again |

Also covered by a unit test: `A_crashed_worker_is_cleaned_up_and_replaced_on_the_next_request`.

**How faithful is `SIGKILL` to a stack overflow?** For the gateway they are the same event: the process is gone at once, cleans nothing up, and exits non-zero (137 here; the runtime's own abort on a stack overflow gives 134). I tried `SIGABRT` and `SIGSEGV` from outside first: the .NET runtime takes those two signals for its own use and the worker simply carried on, so they prove nothing and the script says so. **I did not produce a real stack overflow inside a worker**, because I have no crafted file; if the library coordinator can share one, the same script will take it in place of the kill.

**What I saw that is not good:**

- **The person is told nothing.** Five seconds after the kill their page was back on an empty Home: the page reconnected by itself to a fresh worker, and the document they had open was gone without a word. Not a security hole, but a person will not know why.
- **No brake on repeats.** The person can upload the same file again; each time a worker starts (about a second of CPU) and dies. Nothing counts crashes per person or holds them off. The gateway and others are affected only through CPU.
- A harmless warning appeared once in the gateway log (`Couldn't remove a worker's files yet: Could not find a part of the path …`): the clean-up of the dead worker and the start of the new one both remove the same folder. The folder was gone as it should be.
- **A crash loses every document that person has open**, not just the crafted one: their open tabs live in the worker's memory (D-174).

## 4. Is every upload parsed only inside the worker, never in the gateway?

**In gateway mode: yes.**

- The gateway passes an upload through as a stream without reading it: `GatewayRelay` wraps the request body in `StreamContent` and sends it to the person's worker. It raises the body-size limit for `/portal/upload` and looks at nothing in the body. Dropped files travel inside the browser's live connection, which the gateway relays as opaque WebSocket frames.
- The gateway does not even have the parsing libraries loaded. On a running portal, the gateway process had mapped only `ChuvadiReader.Web.dll` and `ChuvadiReader.Ui.dll` (the Ui for its static pages); **no `Chuvadi.*` library and not the Reader's Core**. The Reader's services are registered only for a worker or Single mode (`ConfigureWorker` / `AddReaderHost`).
- What the gateway does parse is not the person's file: HTTP, its cookies, and Sangam's sign-in answers (tokens and metadata, from Sangam over HTTPS).

**In Single mode: no.** `Portal:Mode=Single` runs sign-in, uploads and every library in one process for everyone. A stack overflow there ends the portal for everybody. Single is the value in `appsettings.json`; the runbook's environment file sets `Portal__Mode=Gateway`. Nothing stops a production start in Single mode.

## 5. Does anything in the gateway unzip or read the uploaded bytes?

**No.** Both places asked about run in the worker (in gateway mode), and neither is a parser:

- **The upload check** (`FileKinds.ContentMatches`, called from `TransferRegistry` when a file is complete, in the worker): reads the **first 1,024 bytes** of the stored file and compares them with fixed patterns (`%PDF-`, the zip signature for Word and Excel, image signatures; for text, "no zero byte", and since WT-26 a plain loop over 16-bit units when the file starts with a UTF-16 byte-order mark). No recursion, no library call, nothing sized by the file's content. It cannot overflow a stack.
- **The zip of several downloads** (`ZipBundle`, D-129): **writes** a zip with Chuvadi.Zip's writer from files the Reader has just produced, in the worker. It never opens or unzips anything a person uploaded. The portal does not accept `.zip` uploads at all.
- Where uploaded zips **are** read: a Word or Excel file is a zip, and Chuvadi.Docs and Chuvadi.Sheets open it, in the worker. If Zip 1.0.2 is one of the fixes, this is where the portal meets it. (Which zip reader those two libraries use is the library coordinator's to say; I did not look inside them.)

## What I would do, for the coordinator to decide (nothing built)

| | Change | Why | Cost and risk |
|---|---|---|---|
| A | **Refuse `Portal:Mode=Single` outside Development** (as the portal already refuses plain-http Sangam and a data folder that isn't in memory). | Closes gap 3 with a few lines in Web. | Small. Anyone running Single on purpose must switch; the runbook already says Gateway. |
| B | **A real per-worker memory limit** from the operating system, not only the heap cap: start each worker in its own cgroup scope with `MemoryMax`, or set an address-space limit on the worker process. And set `OOMPolicy=continue` in the unit so one worker's death by memory cannot stop the service. | Closes gap 2: the kernel then kills the one worker, which section 3 shows is contained. | Medium. Per-worker cgroups need systemd delegation or `systemd-run`; that is an operating-system component, so inside the "no externals" rule, but it needs a decision and a test on the real host. `OOMPolicy=continue` alone is one line in the runbook and removes the worst case today. |
| C | **A watchdog in the gateway**: a worker whose CPU has been pinned for longer than a set time with no page delivered is ended, and the person is told. Plus a time limit on PDF open in the shared code. | Closes gap 1 for files that spin. | The watchdog is Web's (medium; needs care not to kill honest heavy files; the heaviest page measured so far took about 1 GB in its worker). The PDF open limit is Foundation's. |
| D | **Tell the person** when their worker has stopped ("This document made the portal stop. Your other open documents were closed too."), and **hold off a person whose worker has died several times in a few minutes**. | Closes gap 4. | Small to medium, Web only. |

**My recommendation:** A and the `OOMPolicy=continue` line now (small, and they remove the two ways one file could take everyone down). D next. B's per-worker limit and C when the patched libraries' behaviour is known, because the right limits depend on what honest large files need.

## What was and was not checked

- **Checked by running:** section 3 (Chrome, Firefox and WebKit); the worker's environment and limits; which libraries the gateway process has loaded.
- **From the code:** sections 1 (where the cap is set), 2, 4 and 5.
- **Not checked:** a real stack overflow (no crafted file); what a worker does on reaching its heap cap; the `OOMPolicy` behaviour on a real host; Single mode under a crash (the conclusion there follows from there being one process).
