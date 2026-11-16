# Web — what remains for a Phase 1 sign-off (Web Test chat)

> **Updated 17 Nov 2026, 02:15 IST** — head **21665a3** (patch 30 with Web's WT-24 and WT-25 fixes). The section below supersedes everything after it.

> **17 Nov, 06:30 IST — patch 31 head 35a7add tested.** Regression clean; two new bugs: **WT-26** (Medium: UTF-16 text files refused at upload — also true of 21665a3, I had not tried one) and **WT-27** (Low: Firefox first-moment drop ignored). The sign-off below stays on 21665a3 and now carries these two as open; I move it to a later head when WT-26 is fixed or the coordinator rules on it.

## Phase 1 sign-off for Web — signed off on 21665a3, with the limits below
**Web Test's finding:** on `platform/web` 21665a3 the Web portal does what Phase 1 asks, in Chrome, Firefox and WebKit, with marks also checked on WebKit 17.4. Every bug I raised is fixed and re-verified: **WT-01 to WT-25, M-27, LIB-1, LIB-2 — fixed.** Open since: WT-26, WT-27 (found on patch 31). Results table: `RESULTS.md`, 17 Nov (and 16 Nov on 3f80768 for design and speed).

**What the sign-off rests on**
- Build from clean, 0 warnings, all tests pass, package holds only .NET / ASP.NET Core and the product's own assemblies.
- Sign-in against a real Sangam (rc.16), sessions, idle and 8-hour expiry, reload, come-back — including a worker killed or frozen while a session ends.
- One person can't reach another's files, page images or print tickets; hostile files are refused cleanly while others keep working.
- PDF, Word and Excel open and show the file's own content; marks land under the pointer at every zoom; save, print, redact, close card.

**Limits of this sign-off — what I did not prove**
1. **Design:** screenshots taken and looked through for layout on 3f80768; no frame-by-frame comparison with the handout; Firefox and WebKit desktop not re-shot; the close card not checked at phone width.
2. **Touch details from patches 28 and 30** (close control on a mark's card, pinch in Mark, Find on a turned page) — not checked by me; Mobile UI's tests cover them.
3. **Old Safari:** marks, move, resize, Redact verified on WebKit 17.4; lines, images, signature at a zoom are in the Phase 2 device script.
4. **Speed and load:** fine for 1 and 10 people on a 2-core sandbox; 20 people is not meaningful here.
5. **A frozen worker** delays other people's session end by up to 10 s (bounded, logged) — note in BUGS.md, not a bug.
6. **Library limits that stay** (six skipped tests, `docs/foundation/SKIPPED-TESTS.md`): header/footer and watermark on cropped or turned pages, a picture placed with a turn, Excel time-only values. These are visible to people and wait on library releases.

**Left to do**
| When | What |
|---|---|
| Patch 32 head | Close card with Save as only, also on Sign out (D-194) — re-test with regression; the sign-off moves to that head |
| Phase 2, production server | 40-person load (sessions kept 30 min after a browser closes count against `MaxWorkers = 40`), V-1 to V-7, https back-channel, M-1 to M-4 incl. Safari 17/18 devices, G-12, speed at 20–40 people |
| Runbook | `dotnet workload update` once per build machine; `Workers:ControlTimeout` (10 s) is a new setting |

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
