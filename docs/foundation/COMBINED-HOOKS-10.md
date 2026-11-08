# Tenth combined patch — B-24: a stalled read never freezes the Reader (9 Nov, D-130)

**Bug (Linux Test, `docs/linux-test/BUGS.md` B-24, S2):** a PDF whose file never delivers data (a hung SMB/NFS/sshfs mount, an unplugged USB stick; reproduced with a FIFO) left the Reader blank: no "Opening…", no rails, no Cancel. Every later open was stuck behind it.

**Cause:** the PDF open ran on the Reader's own thread. The library's `OpenAsync(path…)` is synchronous until its first await, so `open(2)` on a source that never answers blocked that thread. Even `File.Exists` (a `stat`) blocks on a hung mount. Nothing could render, and the Reader's open loop waited on it.

## Fix (shared Core and Ui; every platform)
| Change | Where |
|---|---|
| "Opening…" is shown **before** anything touches the file; the existence check and the library open run on a pool thread | `TabsService.EnsureLoadedAsync` |
| Each loading tab has its own cancellation. Closing the tab ("Stop opening" / "Close this tab" in the slow-open note, or the tab's ×) cancels the wait **at once**, which frees the slot. The stuck read finishes or not on its own; anything it opens later is disposed, never shown. "Stopped" isn't reported as an error | `TabsService` (`OpenCancel`, `Release`, `DisposeWhenDone`) |
| The Reader adds every queued request's tab at once and lets them load side by side, so one stuck file never holds up the next. When opens overlap, only the active tab's finish drops other render caches | `Reader.razor` `OpenPendingAsync`; `TabsService.OpenAsync` |
| Word and Excel: their viewers already load on a pool thread, ignore a stale result, and show the slow-open note with "Stop opening" (which closes the tab). Docs 1.1.0 and Sheets 1.1.2 take no cancellation token, so the stuck read itself stops only with the Docs/Sheets move | unchanged |

## Tests
- `A_stalled_read_shows_opening_at_once_cancels_at_once_and_never_blocks_later_opens`: a reader that blocks its calling thread forever, as `open(2)` does. The caller gets "Opening…" at once, a later file opens meanwhile, and closing frees the slot while the read is still stuck. Runs on every OS.
- `A_fifo_that_never_delivers_data_doesnt_block_the_library_open_path`: the real chuvadi-pdf open on a real FIFO, on Linux and macOS (the Linux Test fixture's case). It then unblocks the FIFO, so no thread is left behind.
- Checked against the old open path: the test hangs there, exactly B-24 (aborted by the 30 s hang detector). It passes on the new one.

## Proof
- Build 0 warnings (`-warnaserror`, both solutions); tests 299/299 (Reader 191, Hosting 59, Mobile UI 16, Web UI 33).
- Windows-layout screens vs `f1e4126`: 26/27 identical. Home at 1× showed its relative-time artefact (it has fallen on a different scale every run).
- Cost: one thread-pool hop per PDF open, microseconds; nothing else at startup.

## Windows behaviour change
None visible when files answer. On a stalled source (a disconnected network drive), "Opening…" now shows at once, Stop/Close works, and other files keep opening.

# Part 2 (coordinator 03:20)
| Item | From | Where |
|---|---|---|
| **Chuvadi.Zip 1.0.0** in `ci/packages`: Arun's release asset of tag `zip-v1.0.0`, unchanged; SHA-256 `e019f9b6…0104` (`PACKAGES-ZIP-1.0.0.md`); notices regenerated (MIT) | Coordinator, for D-129 (Web chat) | `ci/packages`, `legal/THIRD-PARTY-NOTICES.txt`, `scripts/make-notices.py` |
| **Upload wording** (coordinator 01:42): choosing a file says "Upload…" on the portal in Arrange (empty desk, shelf +, desk image, rail, Ctrl K) and Protect; desktop and Android keep "Fetch…" character for character (`PlatformText.FetchOrUpload`) | Web portal UI (`web-ui-upload-wording.patch`, dd0b705) | `PlatformText.cs`, `Bench.razor`, `Bench.Shell.cs`, `Redact.razor` |
| **Q-3 (D-119 c)**: portal Home says "Files in this session" for the storage map and "Nothing shelved this session — open the Library" for empty shelves | Web portal UI (`web-ui-home-session-wording.patch`, dd0b705) | `PlatformText.cs`, `Dashboard.razor` |
| Tests for both wordings (other platforms unchanged; portal says upload; Home's session texts) | Foundation | `PortalWordingTests.cs` |

Proof:
- Build 0 warnings; tests 305/305 (Reader 191, Hosting 59, Mobile UI 16, Web UI 39).
- Windows-layout screens vs `d70590a`: 27/27 identical (Home and Reader at 1× differed on the first run only; identical on two re-runs).
- Preview: the portal shows "Files in this session", "Upload a file" and "Upload a document…"; the desktop shows "Storage map", "Fetch a file" and "Fetch a document…". No page errors.
