# Mobile app UI → Foundation: hooks and hand-off (updated 9 Nov)

## Outstanding for Foundation: H-17 (`proposal/mobile-ui-hooks-6.patch`)
Android Test **AT-04**: on touch the desk header still shows the desktop row (swatch 16 px, BM, All,
Inv, ← →, duplicate, Clear, delete; 16–20 px targets). 12f / 12i draw only the name, the page count
and ···. `mobile-ui-hooks-6.patch` = H-17 alone; it applies cleanly to Foundation 053e8e4.
Landed combined sets now live in `proposal/landed/`, so Android's `compose.sh` only ever sees the
outstanding one.

### H-17: the desk header's small buttons move into the ··· menu on touch (12f, 12i)
(`Ui/Pages/Bench.razor`, +31 / −2)
- On Tablet and Phone (`TouchDesks`, from H-16) the header renders: name · chips (№, A4/LTR) ·
  "N pg" · ···. The colour swatch, BM, All / Inv, ← →, duplicate, Clear and delete aren't rendered.
- They join the ··· menu, labelled, through `DeskMenuDo` (same methods, no logic duplicated):
  - top: Select all pages, Invert selection (when the desk has pages), Bookmarks on Bind: on/off,
    Desk colour (opens the existing palette), Move desk left / right, Duplicate desk;
  - foot, after Bind desk: Delete all pages (when it has pages), Delete desk.
- Desktop: the header is exactly as today (`@if (!TouchDesks)` around the removed buttons; Read,
  Mark, Arrange, Home and the open desk menu are clock-only at 1440×900).
- **For:** 12f / 12i as drawn; every removed control stays reachable with a label; one file, reusing
  H-16's flag and helper.
- **Against:** one more tap for those actions on touch; Delete desk sits in a menu rather than as a
  visible icon (it's still the last item, after a separator).
- Icons: the menu uses LiPicon keys that exist (`check`, `refresh`, `bookmark`, `circle`,
  `arrow-left`, `arrow-right`, `copy`, `trash`). **Heads-up, not in the patch:** `Icon.razor` maps
  `swatches` → `palette`, and LiPicons 1.1.0 has no `palette` key, so anything asking for `swatches`
  draws nothing. Worth a look by whoever owns Icon.razor.

### Small note, not a hook: "change…" folder buttons (Export, Press cards)
`Reader.razor` lines 200 and 267 draw "change…" as inline-styled 16 px buttons right above the next
control, so on touch their area is shared with it. If they took a class (Bench's Scatter uses
`class="link"`), mobile.css could space them for touch. Nothing needed now.

## Landed: H-14 and H-16 (eighth combined patch, 63f37b1, 839d39d), exactly as written
The record of both follows.

## Outstanding for Foundation: H-14 and H-16 (`proposal/mobile-ui-hooks-5.patch`)
Coordinator decisions D-111 to D-114 (8 Nov 20:22). `mobile-ui-hooks-5.patch` = H-14 + H-16, which
applies cleanly to 9fbed93.

### H-14: the phone opens a document fitted to the width, edge to edge (12g–12j)
(`Ui/Pages/Reader.razor` + `Ui/wwwroot/js/reader.js`, +7 / −3)
- Reader: a new document's first fit is `Width` on a phone (`Page` elsewhere, unchanged), so the View
  sheet's check sits on **Fit width**, as in 12j.
- reader.js `measureFit` reads its side padding from `--rfit-pad-x` on the desk (default **60 px**, as
  today); mobile.css sets 24 px on the phone, so the page is 12 px from each edge, as in 12g.
- **For:** matches 12g / 12h / 12j; the desktop default is untouched.
- **Against:** one more CSS hook in reader.js; phone landscape (no frame) also opens at Fit width.

### H-16: the desk's actions move into its ··· menu on touch (D-114; 12f, 12i)
(`Ui/Pages/Bench.razor`, +47 / −0)
- On Tablet and Phone the desk's ··· menu gains every footer action with its label: Image, Blank page,
  Reverse, Sort into source order, Impose, Number pages, Size (original / A4 / Letter), Watermark,
  Header / footer, Scatter, Export, Lift, Delete selected (when pages are selected), Bind desk.
- The footer isn't rendered there, so a desk is its header and pages, as in 12f.
- Each item closes the menu, then runs the same method the footer button runs (`DeskMenuDo`); no
  logic is duplicated.
- Desktop: the footer renders exactly as today (Arrange 1440×900: 2 pixels of 1-level noise, as in A/A
  runs).
- **Also fixes a gap of mine:** since session 1 the phone hid the footer with nothing in its place, so
  these actions were unreachable on a phone. They're now in the ··· menu.
- **For:** 12f as drawn; every action keeps its label; one file; desktop unchanged.
- **Against:** one more tap to reach an action on touch; Bench gains an `IPlatformInfo` inject and
  two small helpers.
- Touch styling (44 px rows, a full-width Size choice) is in mobile.css.

### D-112 Save on the tablet Mark rail: no Reader diff needed
The Reader's Mark rail already ends with **Save** and the primary **Save as new PDF**, on every platform.
On a tablet the rail is taller than the screen, so the foot was scrolled out of view, and that's why
12e looked different. Fixed in mobile.css: on the tablet, a tools rail's primary action stays pinned at
the foot of the visible rail (`position: sticky`), drawn solid when disabled so nothing shows through.
That's Mark's Save as new, Protect's Save redacted copy and Arrange's Bind, all at the foot as drawn.
On the phone the FAB is Mark's Save already (12h). Desktop unchanged; nothing for Foundation.

### Decisions recorded
- **D-111** rail heading: keep the mode name on all platforms (the Reader chat may switch Windows to
  "TOOLS"; touch then follows).
- **D-113** More view options on the tablet View rail: kept.

## Round 5/6 screenshots vs the handout (8 Nov) — what changed here, and what needs a decision
Compared frame by frame (`screens/2026-11-08/handout-compare/`).
- Round 6 device shots (API 36): 12g Read, 12i Arrange, 12d tablet Read, tablet Arrange (landscape).
- Frames round 6 doesn't cover were shot headless at the device sizes: 12e, 12f portrait, 12h, 12j.

Fixed in my files (no hook):

| Frame | Difference | Fix |
|---|---|---|
| 12g 12h 12j | Page not edge to edge; centred mid-screen | H-14, and pages top-aligned 12 px under the bar while paging (mobile.css) |
| 12d 12g | Desktop-styled scrollbar on the desk | No scrollbars on phone / tablet (none in any touch frame) |
| 12d 12e 12g | Page-curl corner (decorative, "lifts on hover") | Hidden on touch: hover-only, and not in the frames |
| 12d 12e | "58%" zoom readout in the View rail | Hidden on the tablet (not in 12d / 12e) |
| 12j | View sheet covered the strip and bar, and dimmed the page | `PhoneSheet Docked`: the sheet sits above the strip and bar with a clear scrim |
| 12i | Inline "Add desk" tile *and* the FAB | Tile hidden on the phone (the FAB is Add desk) |
| 12i | Desk "···" in a bordered box | Plain, as drawn |
| 12i | FAB floating over the open Shelf's page grid | FAB steps aside while the Shelf is open |
| 12f | Shelf as a 175 px column in tablet portrait | The phone's Shelf sheet (52 px peek; tap or swipe up), stopping at the tools rail |

Checked and **not** a difference: View-sheet rows are 44 px in the handout too (measured in the rendered
handout); the tablet rails already scroll, so long rails are reachable; "/ row" is the Bench's own
desks-per-row label; Mark's sub-line and greyed tools are state.

**Decided 8 Nov (D-111 to D-114)**: see the top of this file. Original options, kept for the record:
1. **Rail heading "TOOLS".** Both handouts (Side Rails and 12d / 12e / 12f) label the tools rail
   "TOOLS"; the Reader and Bench write the mode name ("READ", "MARK", "ARRANGE") on every platform.
   - (a) Keep the mode name: no change.
   - (b) "TOOLS" everywhere: follows the handouts, but changes the desktop (3 strings).
   - Recommend asking Arun; it changes Windows.
2. **Mark rail: "Save as new" at its foot** (12e). The Reader's Mark rail has more tools (shapes, arrow,
   undo / redo / delete) and no Save there; Save is in Document ⌄.
   - (a) Leave it.
   - (b) A Save button at the rail's foot (Reader hook, all platforms).
   - Recommend (b) if Arun wants 12e exactly.
3. **"More view options" (sliders) in the View rail** isn't in 12d. I kept it: it opens the View card
   (text size, colours…), which has no other entry point on the tablet.
4. **Tablet portrait Arrange: the desk toolbar** (Image, Blank, Reverse, Watermark, Bind…) isn't in 12f.
   Its actions exist nowhere else (the desk's ··· has only templates), so it stays.
   - (a) Keep it as is.
   - (b) Icons only in portrait (smaller; loses the labels).
   - (c) Move the actions into the desk's ··· menu on touch (Bench hook).
   - Recommend (c) for the handout look without losing anything; it needs Bench edits.

## CI on this branch (D-93, 7 Nov 05:20)
- The 23:36 UTC run failed on `shared (windows-latest)`: 4 tests in `SingleInstanceTests` (Foundation's
  e5802e6, merged here). The cause was in `DesktopSingleInstance` on Windows:
  - The named **Mutex** was acquired, and Windows mutexes are owned by a thread and re-entrant on it.
  - The tests claim twice inside one process on the same thread, so the second claim also became
    `Primary`.
  - In the real app it was worse: `ClaimAsync` took the mutex on a thread-pool thread. When the pool
    retires that idle thread, the mutex is abandoned, and the next launch takes it as "the previous
    copy died", giving two running copies and files that are no longer handed over.
- **Foundation had already fixed it in 839571e** (create the mutex, never acquire it). I reviewed it and
  it is correct; the only gap is the documented F-1 fallback in a microseconds-wide race. Merged
  Foundation 4819d66 here: run 42314377764 passes on all 6 jobs. No change of mine was needed.

## Ready for Foundation: what you asked for (coordinator, 7 Nov 04:55)
Branch `platform/mobile-ui` includes `platform/foundation` **e5802e6** (fourth combined patch). Two kinds
of change come from here:

**1. New files (mine): take them by merging `platform/mobile-ui`.** Foundation's tree still has my
*session-2* copies of the phone files (from 3358b00). The current ones are on this branch; merging it
brings all of them, as the Android chat's `compose.sh` already does:
`Components/Platform/Phone/*` (PhoneShell, PhoneAppBar, PhoneCommands, PhoneSheetKind, TouchSupport),
`wwwroot/css/mobile.css`, `wwwroot/js/mobile.js`, and `tests/ChuvadiReader.MobileUi.*`.
- **(a) The Web UI chat's PhoneShell slot is in PhoneShell on this branch** (`OpenLabel`, `OpenIcon`,
  `MenuFooter`, since 1a27cd6), so its H5 phone account block can land once PhoneShell is merged.
  The Home Open button follows `OpenLabel` too ("Upload" on the portal).
  - If Foundation needs the slot **before** merging this branch: the Web UI chat's own
    `docs/web-ui/proposal/mobile-ui-request-phoneshell-slot.patch` applies cleanly to Foundation's
    session-2 PhoneShell copy at e5802e6 (checked). Merging this branch afterwards then supersedes
    that copy.
- Also only in the new files: MU-8 (D-45), the touch fixes (swipe, long-press, D-46 counter left to
  Bench), and the phone half of H-7 (`fitWidthZoom` in mobile.js).

**2. Existing-file hooks: `proposal/mobile-ui-hooks-3.patch`** (H-5 to H-12, applies cleanly to **4819d66**).
- **(c) Redact fit width on a phone = H-7** below. It needs `mobile.js` from this branch (its
  `fitWidthZoom`), so apply it together with the merge in step 1.
- **D-88 = H-10 (Dashboard) and H-11 (Settings)** below.

Evidence for the set (hooks-3 on this branch, i.e. e5802e6 + mobile-ui + H-5 to H-11):
- 0 warnings; tests 171 + 48 + 31 + 16 = **266 pass**.
- **Desktop vs e5802e6, before and after run side by side** (`screens/2026-11-07/desktop-compare.txt`):
  - Settings 1440×900: identical.
  - Library, Read 1440×900 and 990×700, Mark, Settings 700×800: clock only.
  - Arrange and Home: clock plus 2 / 15 pixels off by 1 colour level (renderer anti-aliasing; the
    rendered desktop Home HTML is **byte-identical** to e5802e6, below).
- **Startup (Windows profile, `tools/StartupProbe`, published Release, 25 interleaved runs, medians):**

  | | services | first render | total | JIT methods | assemblies | Home HTML |
  |---|---|---|---|---|---|---|
  | e5802e6 | 19.8 ms | 147.3 ms | 191.8 ms | 1,423 | 43 | 20,392 chars |
  | + H-5 to H-11 | 19.9 ms | 148.8 ms | 192.2 ms | 1,438 | 43 | 20,392, byte-identical (clock masked) |

  +0.4 ms total, inside the 7 ms A/A noise floor. A first H-10 draft added one whitespace text node to
  the desktop HTML (invisible); `@PhoneHomeSearch` now sits on the `</section>` line, so the markup is
  byte-identical.

| Patch | File | Decision | Lines |
|---|---|---|---|
| `proposal/H5-mainlayout-tabs-sheet.patch` | `Ui/Layout/MainLayout.razor` | D-43 | +2 / −1 |
| `proposal/H6-settings-phone-push.patch` | `Ui/Pages/Settings.razor` | D-45 Settings A | +15 / −2 |
| `proposal/H7-redact-phone-fit-width.patch` | `Ui/Pages/Redact.razor` | Coordinator, 7 Nov | +16 / −0 |
| `proposal/H8-reader-rerender-bugfix.patch` | `Ui/Pages/Reader.Shell.cs`, `Reader.razor` | **Bug fix**, found from Android run 42276742988; coordinator: combined patch (D-26) | +14 / −6 |
| `proposal/H9-reader-fit-after-render-bugfix.patch` | `Ui/wwwroot/js/reader.js` | **Bug fix**: the phone "over-wide" page and Fit page 456 vs 342 | +10 / −2 |
| `proposal/H10-dashboard-phone-search.patch` | `Ui/Pages/Dashboard.razor` | D-88 | +5 / −1 |
| `proposal/H11-settings-phone-summaries.patch` | `Ui/Pages/Settings.razor` (on top of H-6) | D-88 | +27 / −11 |
| `proposal/H12-core-no-samples-on-android.patch` | `Core/Documents/RecentFilesService.cs`, `PinnedAndWatchedServices.cs` | **Bug fix** (Android fresh install), for decision | +16 / −6 |
| `proposal/mobile-ui-hooks-3.patch` | all eight, in order | — | — |

## H-12: no Phase 0 samples on Android (bug fix; needs a decision)
On a fresh Android install, Home lists five sample recents (`patient_chart.pdf`, `consent_form.pdf`
"encrypted", …) and sample pins, and Settings shows the sample watched folder ("~/Documents/Chuvadi ·
8 documents found"). None of these files exist on the device, so tapping one fails. Worse:
- Home's **first-run box never appears** on Android (it needs no recents and no tabs).
- So D-89 option C's "Open your first document" can't show there, and the Android chat's round-3 D-89
  check can't pass as set up.

Already known: the Android chat reported the samples (BUILD-LOG step 17, A-10 area), and Foundation's
COMBINED-HOOKS records "samples off on the server only (Web H8 b); recommend (a) remove everywhere
when the Reader chat removes Phase 0 data".

| Option | For | Against |
|---|---|---|
| **(a) Samples off on Android only (H-12)** | Fixes the fresh install and unblocks D-89 on the device; Windows, Mac and Linux unchanged (pixel proof holds by construction: `Kind != Android`); 3 small edits in Core | Phase 0 placeholders stay on the desktops until the Reader chat removes them |
| (b) Samples on Windows only | Mac and Linux fresh installs are honest too | Changes the Mac and Linux chats' first-run screens; their call |
| (c) Remove the samples everywhere | The right end state | Changes Windows' first run; Arun / the Reader chat's decision |

**Recommend (a) now, (c) later.** The patch:
- Recents and Pinned: `_samples` also requires `Kind != Android`.
- Watched folder: takes `IPlatformInfo?` (optional, so DI and existing callers are unaffected) and
  keeps the sample folder off Android.
- On Android, Settings › Library then reads "0 documents found · scanned never" with "—".

Evidence (preview reports Android for phone and tablet; `CHVD_EMPTY=1` starts like a fresh install):
- `screens/2026-11-07/{before,after}/firstrun-*`. Before (4819d66): phantom recents, no first-run box.
  After: "Open your first document", Open a file… / Choose a library folder, empty Recents and Pinned.
- Desktop vs 4819d66: Home and Settings identical; Library 6 pixels of 1-level noise (scrollbar ends).
- With H-5 to H-12: 0 warnings; 266 tests pass.
- Also seen there, for PlatformText: the **tablet** first-run tip says "Ctrl K finds any file", which
  needs a keyboard. The phone already has its own tip.

## H-10: Home search under the count line on a phone (D-88)
PhoneShell (my file) cascades its search button, the one running MainLayout's Find, as a named slot
`PhoneHomeSearch`. Dashboard renders it right after the greeting block, i.e. under the count line as in
4a:
```razor
        </section>@* Phone: 4a's search under the count line (H-10); null elsewhere, renders nothing. *@@PhoneHomeSearch
…
    [CascadingParameter(Name = "PhoneHomeSearch")] public RenderFragment? PhoneHomeSearch { get; set; }
```
- **For:**
  - One search button and one code path (MainLayout's Find).
  - Dashboard doesn't know about the phone.
  - Off the phone nothing cascades the slot, so it is null and renders nothing: desktop Home is
    pixel-identical (clock only).
  - Without the hook, PhoneShell's own copy still shows (above the greeting), so nothing breaks
    before it lands. mobile.css hides that copy with `:has()` once Home has placed it.
- **Against:**
  - A cascading parameter is an invisible link between two files (named and commented on both sides).
  - On Windows, Dashboard looks up one more cascading value at first render. Measured with
    StartupProbe: +0.4 ms total, desktop Home HTML byte-identical (evidence above).
- **Alternative:** Dashboard renders its own phone search component. It would need its own route to
  MainLayout's Find, a second code path. Not recommended.

## H-11: one-line summaries in the phone Settings list (D-88)
`Section` gets a `Summary`; the row shows it only when `PhoneList` (H-6) is true, i.e. the phone's
section list. The texts come from the mock, checked against the current section labels. The mock's
"audit log" is "audit trail" here, the Account section's own card title:

| Section | Summary |
|---|---|
| Appearance | Theme · interface size · reduce motion |
| Reading | Default zoom · layout |
| Saving & files | Save folder · name new files · autosave drafts |
| Library & folders | Folder · default view · check every |
| Account & roles | Roles · lock after idle · audit trail |
| Kiosk | Allowed folder · exit PIN |
| Language | Language · dates · numbers · preferred name |
| Accessibility | Interface size · focus rings · larger touch targets |
| Shortcuts | With a keyboard attached |
| About | Versions · licences · data folder |

- **For:**
  - The summaries sit next to the section list they describe, in one table.
  - Desktop markup is unchanged: the span renders only on the phone list. Settings 1440×900 is
    identical, 700×800 clock only.
- **Against:**
  - Summaries are hand-written and can go stale when a section changes. Whoever edits a section
    should update its line.
  - It must apply after H-6 (it uses `PhoneList`); the combined patch keeps that order.
- **Alternative:** each section component publishes its own summary. Never stale, but it edits all
  ten section files. Not worth it for one line each.

## H-5: pass SwitchTab and CloseTab to the phone shell (MainLayout)
Foundation's H-1 renders `PhoneShell` without `SwitchTab` / `CloseTab`, so the phone Tabs sheet (D-43)
lists tabs but can't switch or close them. H-5 adds the two parameters to the existing PhoneShell tag.
- **For:** the sheet runs MainLayout's own methods (close still asks about unsaved changes); nothing is
  re-implemented; it only touches the phone branch, so the Windows render path is unchanged.
- **Against:** one more edit to MainLayout.
- **Alternative:** PhoneShell calls `TabsService` itself. No hook, but it would skip MainLayout's
  unsaved-changes prompt and navigation, so I don't recommend it.

## H-6: Settings A on a phone (section list → section pushed as its own screen)
- With no `?section=`, a phone shows only the section list (`settings phone-list`; mobile.css hides the body).
- Tapping a section navigates to `settings?section=<id>`, so the app-bar ← and Android Back return to
  the list. PhoneShell's Back already does this.
- Desktop and tablet keep `_active = id` exactly as today.
- **For:** the standard Android settings pattern; uses the existing deep link (`?section=`); keyed on
  `FormFactor == Phone`, so Windows never takes the new branch.
- **Against:**
  - Settings.razor is an existing page the Reader chat may still change.
  - On Windows, `PhoneList` is checked once per Settings render: one enum compare, not on the startup path.
- **Alternative:** CSS only. The section list would show, but a tap couldn't open a new screen, so
  Back couldn't step out of a section (Settings B behaviour). That isn't what D-45 chose.

## H-7: Redact on a phone opens at fit width (approved by the coordinator)
At 100 % the page is 793 px wide on a 412 px phone (381 px of sideways overflow). When the document is
first shown and `FormFactor == Phone`, Redact asks `mobile.js` `fitWidthZoom(desk)` for the zoom
that fits the first page's width less a 16 px gutter each side, then uses it. Zoom in / out work as before.
- **For:**
  - ~16 lines in Redact.razor; the measuring lives in the phone's own script.
  - Tablet and desktop never take the branch, and mobile.js is imported only on a phone.
  - Headless: zoom 0.47, page 373 px in a 412 px desk, no overflow (`screens/2026-11-07/after/phone-redact-412x915.png`).
- **Against:**
  - Redact now imports a phone script, a small coupling.
  - It waits up to 1.5 s for the first rendered page before measuring, using the A4 placeholder if
    none has rendered.
- **Alternatives:**
  - Put the measuring in `redact.js`: everything stays in Redact's own files, but it edits two
    existing files instead of one.
  - CSS `!important` on `--rpage-zoom`: no hook, but it breaks zoom in / out. Not recommended.

## H-8: bug fix: commands that don't re-render the Reader (all platforms, Windows included)
Coordinator, 7 Nov: goes into the combined patch (D-26), using the Reader's own re-render helper.
Found while checking the Android run's phone failures, then confirmed on unchanged 63af90f on desktop:
1. **Document › Print, Export pages as images and Reduce file size do nothing.**
   - Why: these commands set Reader state from MainLayout's menu click (or the phone ⋮ sheet), which
     re-renders only the layout, so the card never appears. Ctrl P works, because `r.print` goes
     through the Reader's `T(...)` helper, which re-renders.
   - Fix: `T(...)` moves from a local function inside `ReaderCommands` to a private method of Reader
     (same body), and the three Document commands use it: `T(DocExport)`, `T(DocPress)`,
     `T(() => OpenCard("print"))`. One helper, no second code path; the Read commands are unchanged.
2. **← / → page, but the counter can lag.**
   - Why: reader.js calls `NavPage` over JS interop, which doesn't re-render. The desktop usually hides
     this, because the page-visibility observer fires again afterwards. On a phone (one snapped page)
     it often doesn't, so the counter stays on 1 until the next tap.
   - Fix: `NavPage` re-renders after `GoTo`. `T(...)` takes a synchronous action and `GoTo` is async,
     so this is one `StateHasChanged()` after the await.
- **For:** fixes visible bugs on every platform; small diff (+14 / −6); nothing else changes on screen.
- **Against:** Reader is the Reader chat's file; it sees the change in the combined-patch PR.
- Possibly the same bug, **not changed and not checked**: view-only files (.docx, .xlsx) have `v.view`
  and `v.find`, which also change Reader state without re-rendering. For the Reader chat to check.
- Desktop at rest: only the clock differs (below). Headless: Document › Print fails on 63af90f and
  opens the card with H-8, on desktop, tablet and phone; → moves the counter on all three.

## H-9: bug fix: a new document's first fit is measured on the placeholder (all platforms)
The cause of the Android chat's "Phone Fit page is wrong" (456 vs 342 px) and, very likely, of the
phone desk's sideways overflow (the page itself is too wide):
- The Reader fits a newly opened document right after `init`, before any page has rendered.
- `measureFit` then measures the `.rpage-load` placeholder. It is sized in **points** (595 × 842), 3/4
  of a rendered page (793 px: 96/72 px per pt).
- So the fit comes out **4/3 too large**: 0.592 instead of 0.444 on a 412 px phone, i.e. a 469 px
  page on a 411 px screen, the emulator's figures.
- It only shows when the fit runs before the first page renders, as on a slow device. My preview had
  the pages cached, which is why it never showed headless.
- Proof (checks.py, "fit measured before the pages render"): pages swapped for placeholders, fit
  asked, render arriving 300 ms later. 615afde → **0.592** (FAIL); with H-9 → **0.444** (PASS).

Fix: `measureFit` waits up to 2 s for a rendered page and measures that one; with none, it falls back
to the placeholder as today. It becomes `async`. Both callers already use `InvokeAsync<double>`, which
awaits a returned promise, so nothing else changes.

| Option | For | Against |
|---|---|---|
| **(a) measureFit waits for a rendered page (H-9)** | Exact for any page size; one function in reader.js | The first fit lands up to one render later on a slow device (the placeholder shows at 100 % meanwhile) |
| (b) Size `.rpage-load` in px (793 × 1123) | One CSS line; no wait | Exact for A4 only: Letter is ~3 % off, landscape pages more |
| (c) Page sizes in `PdfDocumentVm`, placeholders sized per page | The most complete: no wrong measure and no layout jump for mixed page sizes | Core + ChuvadiPdfReader + Reader markup; much larger |

**Recommend (a)** now; (c) is worth doing when the Reader chat next touches lazy rendering.
- Desktop: at rest, Read and every other route are clock-only or 1-level anti-aliasing noise vs 615afde.
  Desktop fits a rendered page today, so nothing changes there.
- The Android probe (gestures.py `overwide.json`) should now show the over-wide element to be the
  `.rpage` itself. With H-9 in the composition, the next run should show no overflow and Fit page ≤
  Fit width on both phones.

## Evidence (63af90f + this branch + hooks-3, in a scratch copy)
- Programme solution: **0 warnings, 0 errors**; tests **161 + 28 + 14 + 4 = 207 pass** (H-5 to H-8 applied).
- **Desktop pixel-identical:** before (63af90f) and after (H-5 to H-8) were run at the same time
  (`screens/2026-11-07/desktop-compare.txt`).
  - Read 1440×900 and 990×700, Arrange, Mark, Home, Library, Settings 1440×900 and 700×800: only the
    clock differs, plus ≤ 8 pixels of 1-colour-level anti-aliasing noise on Home and Read (H-5 to H-9 vs 615afde).
  - A run with four preview servers at once showed differences on Read, Arrange and Home from pages
    still rendering under the load. Re-run with the two servers alone: clean.
  - An earlier run showed 1-colour-level anti-aliasing noise on 5–6 Home / Library pixels; the same
    noise appears in A/A runs of 63af90f against itself.
- Headless checks (`tools/mobile-ui/checks.py`, `screens/2026-11-07/*/checks-*.txt`): → paging,
  Document › Print and phone Redact fit width pass on phone (portrait and landscape), tablet and desktop.
- StartupProbe not re-run: H-5 is inside the phone-only branch; H-6, H-7 and H-8 are in Settings,
  Redact and Reader, none of which is on the startup path (Dashboard is).

## D-46 desk counter: one owner
Foundation's Bench now publishes the desk counter (`PublishDeskCounter`, bench.js `scrollDeskTo`).
My TouchSupport also published one (session 2). Two publishers would fight over the counter, so **mine
is removed** and Bench's is the one. The coordinator's note said "the desk counter with no Bench edit is
fine; keep it". That was overtaken by 63af90f already shipping the Bench version. **Please confirm**
Bench's counter is the one to keep.

## For the Android chat (via the coordinator)
**Round 2 (run 42281134585, `15bf9fb`, mobile-ui 26739e8 + Foundation 2fafb60) — real-device results:**

| | phone API 36 | phone API 35 | tablet API 36 | tablet API 35 |
|---|---|---|---|---|
| long-press drag (step 34) | PASS | PASS | PASS | PASS |
| pinch | PASS | PASS | PASS | PASS |
| double-tap zoom and back | PASS | FAIL* | PASS | FAIL* |
| swipe | FAIL | FAIL | FAIL | FAIL |
| → / Print (phone) | FAIL | FAIL | PASS | PASS |

- **Swipe, fixed in mobile.js** (`platform/mobile-ui` after c531f04). Two causes, both reproduced
  headless on 26739e8 and passing now:
  1. The injector writes each of the swipe's 9 steps with its own process start (~170 ms each,
     `touch.py`'s own comment), so a "250 ms" swipe takes ~1.8 s. My 600 ms fling limit rejected it.
     Swipe now also pages on a slower drag across a third of the desk (as Android's own pager does);
     a long-press then drag (text selection) still doesn't page.
  2. On the phones, something in the desk overflows sideways (`overflowX` 54 / 193 while
     `overflowPage` is 0), and I only allowed swipe when the whole desk fit. It now checks only that
     the pages in view fit, measured on `.rpage-wrap`.
  - Still unknown: **what** overflows the phone desk. Not reproducible headless at 411×867 or
    411×839 at 2.625×. Please log it once on the emulator:
    `[...document.querySelector('.rdesk').querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > document.querySelector('.rdesk').getBoundingClientRect().right + 1).slice(0, 5).map(e => e.className)`
- **\* Double-tap on API 35:** the page width reads 793 px (100 %) before and after every gesture,
  and the phone desk overflows only 54 px. That fits the older WebView reporting a CSS-`zoom`ed
  element's rect **unzoomed**, so the test's `pageW` can't see zoom changes there. Pinch passes on
  API 35 because it measures `contentW`. Suggest measuring double-tap the same way (desk `scrollWidth`
  or the desk's `--rpage-zoom`), then re-check. If it still fails, it's reader.js's double-tap
  (Foundation), and I'll look.
- **→ and Print on the phones** are the Reader bug fixed by **H-8**, which wasn't in this build
  (hooks-3 at 26739e8 had H-5 and H-6 only). compose.sh now picks the highest-numbered hooks patch,
  and the current hooks-3 (H-5 to H-8) applies cleanly to 2fafb60 + this branch (checked).
- Please re-run with `MOBILEUI_REF` at the current tip.

**Run 42276742988 tested the pinned snapshot `MOBILEUI_REF` f29b6a6 (session 2), not session 3**, so its
gesture failures are the bugs already fixed in 26739e8. To test the fixes:
1. In `android.yml`, set `MOBILEUI_REF` to the current `platform/mobile-ui` tip. Optionally set
   `FOUNDATION_REF` to 63af90f; be4498a is still contained, so the check passes either way.
2. In `compose.sh`, change `mobile-ui-hooks-2.patch` to `mobile-ui-hooks-3.patch`, in the `PATCH=`
   line and its error message. hooks-2 is gone: Foundation applied it in 63af90f, and the reverse
   check would fail on the new tip. hooks-3 holds H-5 to H-8.
3. Test expectations to change:
   - **double-tap**: expect zoom in and back (reader.js), not "flips the fit mode".
   - **Find**: the box searches on **Enter** (Reader design); type, then press Enter, before
     reading `.rfind-count`.
4. Not mine, for the Android host: the typed find text arrives with letters dropped or doubled ("ttet",
   "tet" for "test"). That's an IME / input issue on the host; the Reader's input is the same as on
   desktop.
5. The other failures in that run (Open with .docx / .xlsx, Share, Save as PDF from the print dialog,
   custom range, back with nothing open on tablet API 35, soft keyboard over find) are host or Foundation
   items, as far as I can tell: they involve intents, the print spooler and the host's back handling, not
   files on this branch. I didn't reproduce them; please send any that point at the phone or tablet UI.

Earlier notes, still valid:
- **Double-tap now zooms** (reader.js: to at least 200 %, and back). My double-tap "Fit width ⇄ Fit page"
  flip is gone; both ran together on the same tap, which caused the size jumps (456 / 90 / 793 px). The
  emulator test should expect zoom in and back, not a fit flip.
- **Swipe (step 32):** Android's own pan cancelled the pointer events. Swipe now reads touch events, and
  a desk whose pages fit sideways pans only vertically (`touch-action: pan-y`). Headless: FAIL on
  63af90f, PASS now, on phone portrait, phone landscape and tablet.
- **Long-press drag (step 34):** while Arrange shows, a blocking `touchmove` listener is in place before
  any press; once a press arms (450 ms), it stops the pan. Passes headless, with and without finger
  jitter, but the intermittent failure never reproduced headless. **Please re-run on the emulator.**
- **Fit page vs fit width (step 33):** fit page is ≤ fit width with no overflow and stays put after
  swipe and double-tap (headless). A4 portrait pages fit equally headless, so please re-check the
  456 vs 342 case on the device.
- Host rule: open files (share / open intents) through `OpenDocumentService`, never `TabsService.OpenAsync`.

## For Foundation's PlatformText
Settings says "computer" where Android needs "phone" / "device":
- Appearance › *Follow the computer's light / dark setting*
- Language › *Preferred name* hint ("your computer's name")
- Kiosk › "Turn this computer into a self-service station." (if Kiosk shows on Android at all)

Not changed here (Settings is an existing file; the coordinator routed it to PlatformText).
