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

## Part 2 (waiting)
- Mobile UI diffs from D-112 and D-114.
