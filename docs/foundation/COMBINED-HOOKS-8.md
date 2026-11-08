# Eighth combined patch — on `platform/foundation` (8 Nov)

## Part 1 (applied)
| Item | From | Where |
|---|---|---|
| **H-14**: a phone opens a new document at Fit width, 12 px from each edge (12g–12j). Elsewhere it stays Fit page. `measureFit` reads its side padding from `--rfit-pad-x`, default 60 px, so the desktop is unchanged | Mobile UI (`mobile-ui-hooks-5.patch`, 9bb7f76) | `Reader.razor`, `reader.js` |
| Mobile UI's own files for rounds 5 and 6 (12d–12j): no touch scrollbars, no hover-only page curl, docked View sheet, phone Arrange, tablet-portrait Shelf sheet, `--rfit-pad-x: 24px` on the phone | Mobile UI (9bb7f76) | `PhoneSheet.razor`, `PhoneShell.razor`, `mobile.css`, `mobile.js` |
| **U-17 (b), D-109**: on the portal, while files are dragged over the window, Home's drop zone keeps its frame but hides its own icon and text, so only "Drop to open" shows | Web portal UI (`web-ui-home-drop-zone.patch`, 74b40c2) | `Dashboard.razor.css`, `portal-drop.js` |

Proof (tree with part 2b and this part):
- Windows 27/27 identical vs `9fbed93`.
- Phone 412×915: the first fit is 12 px | 12 px; the desktop still fits the page (60 px default); no page errors.
- Portal: drop checks 1–7 pass. While dragging, `<html>` has `chvd-dragging`, Home's zone frame is visible and its contents hidden; both restore on leave; no page errors.
- Build 0 warnings; tests 276/276.

## Part 2 (applied, 9 Nov)
### Linux chat's shared fixes (`docs/linux/PROPOSAL-shared-fixes-8nov.md`, exact diff against `ffb2823`, tested on Linux 114/114)
Taken as written, except: its D-101 hunks (identical to part 2b of the seventh patch, already here), its Linux host files and `tools/linux/uitest.py` (they land on `platform/linux` with its rebase).
| # | Bug | Change |
|---|---|---|
| S2 | B-07 | A password-protected PDF asks for its password in its tab (`UnlockCard`, as Word/Excel); the password stays in memory for that tab only |
| S3 | B-11 / WT-10 | Damaged PDF → "This PDF is damaged" (States & Feedback 8e), "Try to repair (new copy)", "Show in folder"; parser text under Details |
| S4 | B-08 | `OfficePackageGuard`: Word/Excel zip bombs refused before the library inflates them |
| S5 | B-09 / B-10 | Excel grid draws only the rows on screen (`<Virtualize>`), so a huge sheet no longer holds up later opens |
| S6 | B-03 | `nuget.config` package source mapping: `Chuvadi.*`, `LiPicons.*` only from the local feed |
| S7 | B-02 | Full OFL 1.1 texts next to the Ui's fonts |
| S8 | B-19 | Left-hand window buttons sit inside the brand cell |
| S9 | B-23 | The page's "send" hover button is out of the Tab order |

### D-120 fixes written here
| Bug | Change | Test |
|---|---|---|
| **WT-02** | `ReaderTab.CurrentPageIndex` (zero-based); the Reader passes it to Print, Measure, Layers, Signatures and Password cards (it passed the 1-based page, so "Current" printed the next page) | `TestChatFixesTests` (index; print "current" on pages 1 and 13) |
| **WT-09** | The Print card says why it can't print as text at its top, not only in a tooltip | Preview: card text visible (screenshot) |
| **WT-10 / B-11b** | Every other open failure: a plain sentence ("This file is damaged or isn't a PDF Chuvadi can read." / an access sentence) with the system's text under Details; "Upload…" instead of "Fetch…" on the portal (other platforms keep "Fetch…") | `TestChatFixesTests`; preview: the portal's broken PDF shows the parser text only under Details |
| **B-08b** | `SlowOpenNote` in every "Opening…" (PDF and the five viewers): after 10 s "This file is taking longer than usual to open." with "Stop opening"; at 60 s "Chuvadi stopped waiting…" with "Close this tab". Stopping closes the tab; a late PDF session is disposed. The library can't cancel a load yet (Linux's library ask 4), so the abandoned load finishes in the background; the zip-bomb guard bounds the worst case | `TestChatFixesTests` (closed while opening: late session disposed, the next open works) |
| **B-10** | Covered by S5 plus B-08b (a stuck open can be stopped; later opens run regardless) | as above |
| **B-16** | The kit's `FileAppStorage` never throws for a folder it can't create, read or write: values kept in memory for the session, settings on disk still read, `CanSave` / `CannotSaveReason` / `CannotSave` (once) for the host to tell the person. Covers Windows, Mac, Linux and Android; Linux can drop its `ResilientAppStorage` | `FileAppStorageTests` (3) |
| **B-22** (D-123) | One keyboard-only ring: `:focus-visible { outline: 2px solid var(--chvd-binding); outline-offset: 2px; }` in `tokens.css`; components with their own focus style keep it | Preview: Tab → 2 px accent ring; click → none |

### Mobile UI (95b9d79)
| Item | Where |
|---|---|
| **D-112**: the tablet rail's Save pinned at its foot | `mobile.css` (Mobile UI's own file) |
| **D-114 / H-16**: on tablet and phone the desk's ··· menu holds every footer action; the footer isn't rendered | `Bench.razor` (`H16-bench-desk-actions-in-menu-on-touch.patch`) |

### Proof
- Build 0 warnings (`-warnaserror`, both solutions); tests 295/295 (Reader 187, Hosting 59, Mobile UI 16, Web UI 33).
- Windows-layout screens vs `63f37b1`: 22 of 27 identical on the first run. The 3 Print-card screens differ as intended: the preview has no print service, so the card now says why (WT-09). On a real Windows, with its print service, the text shows only for a file whose permissions forbid printing. Home's 1× and 1.25× differences were the known artefacts (identical on re-run; then only the relative-time "1m/2m").
- Portal: a broken PDF shows the damaged state, the parser text only under Details. Desktop: the B-22 ring, keyboard only. No page errors.
