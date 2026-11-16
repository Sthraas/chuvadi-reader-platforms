# Web — what remains for a Phase 1 sign-off (Web Test chat)

> **Updated 16 Nov 2026, 17:30 IST** — sign-off pass on **3f80768** (patch 29). The section below supersedes §1–§3 of the 11 Nov text that follows.

## Verdict on 3f80768: not signed off — one High bug open (WT-24)
Everything else in the Phase 1 scope passes on this head in Chrome, Firefox and WebKit (and WebKit 17.4 for marks); table in `RESULTS.md`.

**Fixed and verified:** WT-01 to WT-23 (all of them), M-27, LIB-1, LIB-2; the close card (D-186, D-190), Excel resize, sheet pager, hidden-cell Find line.

**Blocks the sign-off**
| # | What | Owner |
|---|---|---|
| **WT-24** | **High.** The session-expiry pass can hang for good; after that no session on the portal expires and no worker is freed until a restart. 2 runs in 9 on a0a2f7c, 0 in 20 on 3f80768, code unchanged — a race | Web fixes (time limit on gateway → worker calls); Web Test re-tests, including a forced stop of the worker mid-call |
| WT-25 | Low. Browser closed or killed with a tab open: worker and files stay about 60 s past the session's end | Web: confirm the timer; fix or state it |
| Skipped tests | 6 skipped in the Reader tests — the written reasons | Foundation (in hand) |

**For the coordinator to decide (small):** Excel sizes set by dragging go on a page reload — accept and state, or keep with the session's tab (BUGS.md; I'd accept for Phase 1).

**Honest gaps in this pass:** no frame-by-frame comparison of the screenshots with the handout (layout looked through only; Firefox and WebKit desktop not re-shot); the close card not checked at phone width; lines, images and signature at a zoom on old WebKit left to the Phase 2 device script; speed at 20 people is not meaningful on this 2-core sandbox.

**Phase 2 unchanged:** 40-person load (sessions kept 30 min after a browser is closed count against `MaxWorkers = 40`), V-1 to V-7, https back-channel, M-1 to M-4 (add Safari 17/18 devices), G-12. One build note for the runbook: `dotnet workload update` once per machine.

---

# 11 Nov 2026 text

Tested head: `platform/web` **04cdd21**. Full evidence: `RESULTS.md`; bugs: `BUGS.md`.

## 1. Where Web stands
- Build from clean, 0 warnings; 610 tests pass (3 skipped); no third-party code in the package.
- 17 of 22 bugs verified fixed (WT-01 to WT-17, WT-20); WT-21 fixed for the open tab. LIB-1 and LIB-2 fixed in the libraries.
- Passing on 04cdd21 in Chrome, Firefox and WebKit: everyday flows, real-Sangam sign-in / sign-out / back-channel / expiry (idle and 8-hour), isolation, uploads and hostile files, page-image security, Word and Excel fidelity, phone and tablet layouts, restart banner, production start-up refusals.

## 2. Must close before sign-off
| # | What | Owner | Note |
|---|---|---|---|
| WT-22 | Reload loses open tabs; their documents stay open in the worker and are not closed at session end | Web, after the coordinator picks (a) or (b) | Medium. Completes WT-21 |
| WT-19 | Excel close / cancelled open gives no memory back (690 MB and 1,378 MB held) | Foundation / library | Medium; matters for the 40-person budget in Phase 2 |
| WT-18 | Oversized Excel part / zip bomb called "damaged" instead of "too large" | Foundation / library | Low |
| WT-17 follow-ups | Decisions, not defects — see below | Coordinator / Arun | |
| Skipped tests | 3 skipped in the Reader tests (2 CropBox, 1 time-only Excel) — say why, or un-skip | Foundation | rule: every bug fixed |

**WT-17 follow-ups (D-161/D-162):**
1. **Whose number grouping?** The grid uses the server's culture, so everyone gets the server's grouping (here `1,234.50`); Indian grouping (`12,34,567.89`) needs the server set to en-IN. Options: (a) server set to en-IN in the runbook — one line, same for all; (b) follow each person's browser language — right per person, more work and a portal-only path. Recommendation: (a) for Phase 1.
2. **Stored value on touch:** the held value is hover text only; phones and tablets can't see it. Needs the Ui choice the Web chat flagged (show it when a cell is selected).
3. **General cells:** 3.14159265358979 shows as `3.141592654` (as Excel does), full value on hover — confirm this is what D-161 intends, since the build log says General keeps the full value.

## 3. Still to do by the Web Test chat in Phase 1 (on the sign-off head)
- Re-test WT-22, WT-18, WT-19 and the WT-17 follow-ups as they land.
- One final full pass on the sign-off head: clean build, all suites × 3 engines, hostile corpus, fidelity, and the design screenshots (five themes × three engines × desktop / tablet / phone) against the handout frames — the last full screenshot comparison was on 31b063e, before the phone shell.
- Confirm the tablet portrait frame (View rail hidden at 820×1180).
- Sandbox speed re-run (1 / 10 / 20 people) on the sign-off head, for a before/after against session 1.

## 4. Not Phase 1
- **Phase 2 (production server):** 40-person load, V-1 to V-7, back-channel over https with a trusted certificate, M-1 to M-4, G-12, real desktop drag, clipboard — `TEST-PLAN.md` "Phases", `STAGING-VM-ASK.md`, `MANUAL-SCRIPT.md`.
- **Waiting on the libraries (same on Windows):** Fill form, Highlight, Note, certificate signing, OCR, "As printed" (Chuvadi.Layout); Sheets built-in date format 14.
- **Legal:** Terms and Privacy still carry DRAFT lines until counsel's review (V-7 checks they are gone).
