# W-02 — How users are kept apart on the server (final pros and cons, no server storage)

For the coordinator to finalise. Updated 6 Nov 2026 after Arun's decision that nothing is kept after the session. The session code already built (`SessionSpace`, tickets, uploads, downloads, print) works the same under both options; what differs is how many processes run it.

## Measurements (sandbox, 2 cores, .NET 10.0.14, Release publish)

| | Value |
|---|---|
| One portal process, cold start to serving | 0.66–0.72 s (3 runs) |
| Idle process | 100 MB |
| After one complete session (open a 690 KB PDF, print a page, merge two PDFs, download) | 172 MB |
| Light extra circuit (just browsing pages) | ~4 MB each (spike, 5 circuits) |

Documents dominate memory in both options: a 300-page scan costs the same wherever it is opened.

## What still breaks user isolation in one shared process, even with no storage

1. **Core and Ui write outside the session folder.** `BenchService` (4 methods), `PressService`, `Reader.razor` (3 places) and `Bench.razor` (1) write to `Path.GetTempPath()`; `SessionService` keeps desk templates in `%AppData%/ChuvadiReader/desk-templates.json`. In one process those are **shared by every user** (one person's saved desk templates would appear for everyone) and they **outlive the session**, which breaks "nothing kept after the session". The host cannot redirect them per user: the temp folder and AppData are per process. Only changes to the Reader chat's Core and Ui code fix this in a shared process.
2. **Pdf A (name table never shrinks):** the shared process grows with every document anyone opens until it is restarted.
3. **Pdf B (font renderer race):** concurrent users can make Indic text disappear for everyone until restart.
4. **Failure blast radius:** a hostile or broken file that hangs or exhausts memory affects every signed-in person.

## Options

### (a) One shared process, services per session

| Pros | Cons |
|---|---|
| Lowest memory: one ~100 MB base, then only what each session's documents need; several hundred light sessions per 8 GB | Points 1–4 above. Point 1 needs edits to ~10 places in Core/Ui owned by the Reader chat (rule 4), or the Foundation's file model to cover temp and app-data writes too |
| Simplest to run: one service, one log, no relay | Pdf A and Pdf B stay server-wide production blockers until the library fixes ship |
| No start delay after sign-in | No per-person memory cap; one bad document can take the service down for all |

### (b) One worker process per signed-in person, behind our own Kestrel gateway (recommended)

The gateway (Kestrel, our code) terminates TLS, runs the Sangam sign-in, and relays each person's HTTP and WebSocket traffic to their own worker over a Unix socket. Each worker is this same portal app, started with `HOME`, `TMPDIR` and the data root pointing inside that person's session folder, and a memory cap (`DOTNET_GCHeapHardLimit`, built into .NET). On sign-out, Sangam back-channel logout, idle expiry or crash, the gateway stops the worker and deletes the folder.

| Pros | Cons |
|---|---|
| Point 1 solved with **no change to Core or Ui**: the temp folder, AppData and Documents of a worker are inside that person's session folder, so they are private and deleted with it | ~100 MB base per active person (172 MB after a typical session): roughly 40–60 concurrent people per 8 GB VM, versus hundreds in (a) |
| Pdf A: memory returns to the OS when the person leaves. Pdf B: only that person's own parallel renders can hit it. Both become contained risks rather than server-wide blockers (still to be fixed in the library) | We write and test the relay (HTTP + WebSocket, ~400–600 lines of our own code, no YARP) and the worker supervisor |
| A hostile file can only hang or exhaust its own worker; the memory cap and a watchdog kill it without touching others | 0.7 s extra on first load after sign-in (cold start measured above); a small pre-started pool can hide it |
| Clear audit and limits per person (CPU, memory, session length) | More moving parts to monitor (worker count, starts, kills) |

### (c) Hybrid: shared process now, workers later

| Pros | Cons |
|---|---|
| Fastest to first deployment | Ships with points 1–4 open, so it can't meet "nothing kept after the session" or "only you can see it" without the Core edits; the move to workers later redoes the hosting layer (an interim design) |

## Recommendation

**(b) per-person workers.** With no server storage, the deciding factor is that a shared process cannot keep the Reader's own temp and app-data files private or delete them at session end without editing the Reader chat's code, and it carries Pdf A/B for everyone. Workers give real isolation with zero changes to Core or Ui, at the cost of memory (size the VM for the expected concurrent users) and our own relay code.

If concurrency targets are high (hundreds at once on one VM), (a) becomes attractive only after (1) the Reader chat routes those temp/app-data writes through a per-session root (or the Foundation's file model covers them) and (2) Pdf A and Pdf B are fixed.

## Questions that size the VM (for Arun / E2E)

- Expected concurrent signed-in people at launch and in a year?
- Largest document people will open (pages, MB)?
- Session idle expiry (proposed: 30 minutes idle, 8 hours absolute)?
