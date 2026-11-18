# Mobile app UI — build log

## 2026-11-06 — session 1

### 1. Reading
- Working repo `Sthraas/chuvadi-reader-platforms`: RULEBOOK, DESIGN-NOTE, packages report, design handout
  (README, DISCUSSION, `Portal & Android` 12a-12j rendered in headless Chrome and read in source, tokens.css).
- `platform/foundation`: PLATFORM-INTERFACE, FOR-UI-CHATS (ShellLayout signal, `data-shell`), Group A
  applied at **aeeac43** (PlatformRoot, PlatformState, WindowButtons). `platform/android`: host, DECISIONS,
  tablet CSS in `android.css` — **no phone components there**, so nothing to continue from.
- Ui code read for the hooks: MainLayout, shell.css, ShellService, rails, Reader/Bench/Redact command
  registrations, reader.js (wheel zoom), bench.js (pointer drag), shell.js.

### 2. Branch
`platform/mobile-ui` created from `origin/platform/foundation` (aeeac43, after the coordinator's update that
Group A landed). Commits authored as Arun, no attribution lines (rule 10).

### 3. Environment
.NET SDK 10.0.403 (dotnet-install, channel 10.0). Packages from the Reader's committed feed
(`--configfile ci/nuget.config`), as the coordinator directed. Headless Chrome + Python Playwright for
screenshots — **testing only**.

### 4. Built (new files only)
- Phone shell components (`Components/Platform/Phone/`), `css/mobile.css`, `js/mobile.js` — see README.
- Design mapping: every colour of the frames maps 1:1 to a token (`#8a3a1c` binding, `#fbf7ec` surface-hi,
  `#f2ead6` surface-mid, `#e8dcc4` surface-lo, `#c4b497` border, `#d9cdb4` border-soft, `#3a2f25` ink-soft,
  `#8a7c64` ink-muted), so all five themes work.
- Sizes from the frame source: phone app bar 56, strip 62 (52×50 items), bottom bar 80 (60×32 pill, 15 px
  italic verb), FAB 56 r16, sheet r22 with 44 px rows; tablet top bar 52, rails 72/72/60, 60 px mode
  buttons, 48 px targets.

### 5. Existing-file change — proposal only
`docs/mobile-ui/proposal/mobile-ui-hooks-1.patch` (MainLayout, +16 lines). Never applied on the branch;
`tools/mobile-ui/preview.sh` applies it in a scratch copy. Options and risks: `OPTIONS.md` MU-1.

### 6. Tests and checks
- `tests/ChuvadiReader.MobileUi.Tests` (3): command ids the phone uses are registered by the mode views;
  strip/sheet labels equal the frames; every selector in mobile.css is scoped to tablet/phone.
  Mutation check: renaming one id and adding one unscoped rule → both tests fail; restored → pass.
- Programme solution: **0 warnings, 0 errors**; tests **161 + 18 + 3 pass**.
- Preview (Blazor Server, testing only) at phone 392×816 / 816×392, tablet 1280×800 / 800×1280, touch
  emulation on: **0 console errors** in every scenario (Read, Mark, Protect, View sheet, ⋮ menu, Arrange).
- **Desktop pixel-identical:** unchanged foundation tree vs. this branch + hooks, 1440×900 Read, 990×700 Read,
  1440×900 Arrange → identical except the live clock seconds.

### 7. Fixed on the way (own code)
- `Open` name clash in PhoneShell (parameter vs. sheet opener) → `ShowSheet`.
- `Path` ambiguity (Chuvadi.Pdf.Graphics.Path) in the preview fixtures.
- Tablet brand was clipped by the 60 px brand box → `min-width: max-content`; `+`/⋯ tab buttons hidden (12d
  shows only the active tab and +N).
- The hover-only "To desk" chip covered the page on touch → hidden on tablet/phone (same action is in the
  tap-to-show page strip).
- Phone Arrange: Shelf opened over the desks → rests as a 52 px peek; FAB lifted above it.
- Preview: added favicon stub (only 404); restore before opening fixtures (see OPTIONS "Possible bug").
- Baseline script first deleted a Razor comment along with the link line → baseline now uses `git archive`
  of the unchanged foundation commit.

### 8. Found for others
- Android host: scoped CSS bundle not linked in `index.html` (all component CSS missing on Android).
- Core `TabsService.RestoreAsync` doesn't de-duplicate already-open paths (edge case).
Both in `OPTIONS.md`.

### Screens
`docs/mobile-ui/screens/2026-11-06/` — phone, tablet, desktop before/after, and crops of the design frames.

## 2026-11-06 — session 2 (after D-40 … D-54)

### Read
DECISIONS.md on main (D-01 … D-53; D-54 from the coordinator's message). Foundation moved to 60dca85:
**no `PlatformRoot` / `PlatformState` cascade any more** (startup rule) — components inject
`IPlatformInfo`; MainLayout sets `<html data-*>` on non-Windows hosts; host pages set them for the
first paint. chuvadi-pdf 3.31.2 not in Foundation's feed yet (3.31.1).

### Done
- Rebased on 60dca85 (clean). Ported TouchSupport / PhoneShell / preview host off the cascade
  (`IPlatformInfo`, injected `IAppLifecycle`); the preview page writes the `<html data-*>` attributes
  (none on Windows, as the WPF page).
- H-1 regenerated: Windows renders neither TouchSupport nor PhoneShell (my first version rendered
  TouchSupport everywhere — a cost under the startup rule). Gates on plain properties.
- D-43 Tabs sheet; D-44 landscape bars; D-46 Protect FAB = Save redacted copy; D-46 desk counter with
  no hook; D-42 pen/finger diff (corrected to Reader.razor) + CSS.
- D-48: wrote the fix and a test; the test failed **with** the fix → found my report was wrong;
  withdrew both (`FOR-FOUNDATION.md`).
- MU-8: two options each for phone Home / Library / Settings, rendered from the handout's tokens and
  icons with the app's real theme names, labels and section icons; the handout's own phone Home
  (Chuvadi Mobile 4a) is the base for Home. Not built.
- Harness: drops a browser session's components on disconnect (stale sessions kept the redaction view
  registered and leaked into the next screenshot); every phone scenario starts from Read; copy step
  skips deleted files.

### Evidence
0 warnings; 161 + 27 + 4 tests; desktop pixel-identical on Read ×2, Arrange, Mark; StartupProbe
+1 JIT method / +2.2 ms (noise floor 7 ms); 0 console errors in every phone/tablet scenario.
Screens: `screens/2026-11-06-pm/`, mocks: `mocks/`.

### Found
- Settings wording "computer" on Android (Appearance, Language) — for PlatformText (Foundation).
- The redaction view opens at its desktop zoom on a phone (page wider than the screen) — needs a
  fit-width default on phone; Redact is an existing file → hook, next session with options.
- Tablet desk label can't singularise ("1 / 1 desks").

### D-54 — chuvadi-pdf 3.31.2
Foundation landed it (be4498a) during the session. A rebase was clean locally, but publishing it
needs a force-push over this branch's pushed history, which was refused as destructive. So the
branch takes Foundation by a **merge** instead (no history rewritten; fast-forward push); the
resulting tree was checked byte-identical to the rebased one. Restore resolves Chuvadi.Pdf.* 3.31.2
from `ci/packages`. Re-verified on 3.31.2: 0 warnings; 161 + 27 + 4 tests; hook patches still
apply; desktop pixel-identical (Read, Arrange, Mark at 1440×900); 0 console errors on phone
Read / Tabs / Redact / Arrange and tablet Read / Arrange.

## Session 3 — 7 Nov: MU-8 built, Android touch bugs, F-4

Took `platform/foundation` 63af90f by merge (it carries the combined hooks D-26: H-1, reader.js
pen/finger, Bench desk counter, D-48). 12 add/add conflicts on the Phone files: kept mine, which already
used `IPlatformInfo`. Session 2's H1/H3 patches deleted (applied upstream).

### Done
- **F-4:** TouchSupport and PhoneShell inject `IPlatformInfo` and use `Info.Shell()`, with no
  cascade left.
- **Android bug 1, swipe never pages (step 32):** pointer events got `pointercancel` from the
  WebView's own pan. Swipe now reads touch events (never cancelled). A desk that fits sideways gets
  `.chvd-hfit` → `touch-action: pan-y`.
- **Android bug 2, fit page > fit width, sizes jump:** my double-tap fit flip ran together with
  reader.js's double-tap zoom on the same tap. Removed mine (and my Ctrl-wheel pinch: reader.js already
  pinches).
- **Android bug 3, long-press intermittent (step 34):** Chrome ignores a blocking touchmove listener
  added mid-gesture. Now registered while Arrange shows (`setArrange`); an armed press cancels the pan.
  A page lifted from the open Shelf drops the sheet to its peek (phone landscape: the sheet covered
  every desk).
- **D-46:** Bench publishes the desk counter (63af90f); mine removed, because two would fight.
- **MU-8 / D-45:**
  - Off-document bar Home · Library · Tabs · N · Settings; Home avatar, search pill and extended Open FAB.
  - Home 4a layout: resume cards sideways, drop zone and clock eyebrow hidden.
  - Library: one-row chips, two-line rows, Shelf as desktop.
  - Settings A: list → section pushed; Back returns to the list (H-6).
  - Landscape bar icon-only.
- Hooks for Foundation: H-5 (MainLayout passes SwitchTab/CloseTab) and H-6 (Settings phone push).
- Preview host seeds a 7-file library in category folders (Library was empty).
- Harness:
  - `gestures.py`: CDP touch, checks swipe, double-tap, pinch, fit, and long-press with or without jitter.
  - `<layout>-base` mode for any layout.
  - `shoot.py` start paths for Home, Library and Settings.

### Evidence (`screens/2026-11-07/`)
- 0 warnings; 161 + 28 + 14 + 4 tests pass (hooks applied); the branch alone builds with 0 warnings.
- Gestures: every check passes on phone 412×915, phone 915×412, tablet 1280×800 and jitter. On 63af90f
  ("before"), swipe FAILs on phone and tablet (`pointerdown, pointercancel`).
- 0 console errors in all 18 phone and tablet scenarios.
- Desktop: before and after run side by side:
  - Read ×2, Arrange, Mark, Settings ×2: only the clock differs.
  - Home and Library: ≤ 6 pixels off by 1 colour level out of 255 (anti-aliasing; the Home region
    recurs in base-vs-base runs).
  - A first sequential run had shown 156 / 403 px on Home / Library: the clock minute and "2m" / "3m"
    ages.

### Not reproducible headless (device re-run needed)
- The intermittent long-press: passes every time headless, including with jitter.
- 456 vs 342 fit sizes: A4 portrait fits equally in Chromium; the cause (double-tap duplication) is fixed.

### Open (OPTIONS.md › MU-8 open points)
- Home search pill placement.
- Settings row summaries.
- Library Default view placeholder.
- Redaction view zoom on a phone.
- Shelf drop-to-peek: my choice, please confirm.
- "1 / 1 desks".
- "Computer" wording in Settings (Appearance, Language, Kiosk), for PlatformText.

## Session 3b, 7 Nov: coordinator decisions, Android run 42276742988

- **Android run 42276742988** (four emulators) built the *pinned* `MOBILEUI_REF` f29b6a6 (session 2),
  so its swipe and double-tap failures are the bugs fixed in 26739e8. The Android chat needs to bump
  the pin and switch `compose.sh` to `mobile-ui-hooks-3.patch` (hooks-2 is gone).
- Checked its other phone failures headless on today's tip:
  - **Phone ⋮ › Print opens nothing.** Same on desktop Document › Print, Export and Press on
    unchanged 63af90f: the Reader commands don't re-render the Reader. **H-8** (bug fix).
  - **→ moves the page but the phone counter stays on 1** (desk scrolls 0 → 779 → 1558 px): NavPage
    is called from JS, which doesn't re-render; the scroll observer usually covers it on desktop. H-8.
  - **Find count empty**: the find box searches on Enter (design); the test needs Enter. The
    dropped letters ("ttet") are host input.
- **H-7 Redact fit width on a phone** (approved): 793 px page / 381 px overflow → zoom 0.47, no overflow.
- **Shelf drop-to-peek** kept as my choice (OPTIONS.md).
- **Web portal slot** in PhoneShell: `OpenLabel`, `OpenIcon`, `MenuFooter` (applied by hand: the
  request patch was cut against the session-2 file). The Home Open button follows `OpenLabel`.
- `tools/mobile-ui/checks.py` plus run.sh scenario `checks`.

Evidence:
- 0 warnings; 207 tests with H-5 to H-8 applied.
- checks.py: PASS on phone portrait and landscape, tablet and desktop. On 63af90f, Print fails
  (phone and desktop) and Redact overflows 381 px.
- Desktop before/after run side by side: Read 1440 and Mark identical, the rest clock only.

### H-8 revised (coordinator, 7 Nov: combined patch, reuse the Reader's helper)
- The Reader's `T(...)` re-render helper moves from a local function in `ReaderCommands` to a private
  method; Document › Export / Press / Print use it. `NavPage` keeps one `StateHasChanged()` after its
  await (`T` is synchronous).
- Results: 0 warnings, 207 tests, hooks-3 applies to 63af90f; checks.py passes on phone (portrait and
  landscape), tablet and desktop; desktop before/after shows only the clock on all eight screens.
- Lesson: run at most two preview servers at once for pixel comparisons. Four at once gave false
  differences, with pages still rendering.

### Android round 2 (run 42281134585): real-device results → swipe fix
- Long-press drag and pinch pass on all four emulators. Double-tap passes on API 36; on API 35 the
  test's page-width probe reads 100 % throughout (older WebView rect of a zoomed element), so the
  measure is suspect. → and Print fail on phones: H-8, not in that build.
- **Swipe failed everywhere.** Causes:
  - the injected swipe takes ~1.8 s (one process start per step), against my 600 ms limit;
  - phones show unexplained sideways overflow in the desk, against my whole-desk fit check.
- Fix (mobile.js):
  - pages on a quick fling **or** a drag across a third of the desk;
  - a long-press then drag, or a drag that leaves selected text, never pages;
  - "fits" now means the pages in view fit, measured on the unzoomed `.rpage-wrap`.
- gestures.py: slow swipe (1.8 s), swipe with 190 px of other overflow, and long-press then drag.
  - On 26739e8: the first two FAIL (`screens/2026-11-07/before-26739e8/`).
  - Now: every check passes on phone portrait and landscape, jitter, and tablet.
- Lesson: my fling limit was tuned to CDP's instant events. Injected touch on a slow emulator, and a
  slow real finger, need the distance rule too.

### 7 Nov (late): Foundation 615afde merged; MU-8 polish
- Merged `platform/foundation` 615afde (second and third combined patches: PlatformText wording —
  "Follow the phone's light / dark setting" now shows —, Licences page, Print packages). Clean merge.
  All four hooks (H-5 to H-8) still apply.
- Results: 0 warnings; tests 171 + 33 + 19 + 12 = 235 pass with hooks applied.
- MU-8 fidelity pass against 4a and the D-45 mocks (CSS only):
  - The Library row checkbox (20 px) and "+" tag (20 px) were under the 44 px target. The checkbox is
    now a 44 px theme-drawn box (tap selects; the Press bar appears). The tag "+", category chips,
    file name, view toggle and Search keep their look, with an invisible `::after` making each hit
    area 44 px. A script checks every visible control on the Library: none under 44 px.
  - Folder paths (Library header, Home storage map) are hidden on phone and tablet: no file manager
    there.
  - The Library search input fills its 44 px field, with an ellipsis on the long placeholder.
- Evidence:
  - Desktop vs 615afde: Home, Library and Read differ only in the clock.
  - Phone and tablet gestures and checks all pass; 0 console errors on the 5 MU-8 screens.
- Still open (decisions; OPTIONS.md): Home search placement (Dashboard hook), Settings row summaries
  (Settings hook), Library Default view (the Reader chat's setting).
- Android CI is stopped (GitHub billing), so this was tested locally only. The device check of the
  swipe fix and the over-wide phone element wait for the Android chat's run.

### 7 Nov (late): the phone "over-wide" page found → H-9
- The Android probe (5f5056e) is written but can't run (CI on billing hold). The Android build log
  gave the clue: Fit page 456 vs Fit width 342 = **1.333 = 96/72**.
- `.rpage-load` is 595 × 842 (points); a rendered A4 page is 793 px. The Reader fits a new document
  right after `init`, before the first render.
- Headless proof: reader.js `measureFit` on the same desk returns 0.444 on rendered pages and 0.592 on
  placeholders.
- Slow network and CPU didn't reproduce it end to end, because the preview's pages were already
  rendered and cached server-side.
- H-9: `measureFit` waits (≤ 2 s) for a rendered page. checks.py: 615afde 0.592 FAIL, with H-9 0.444
  PASS (the render arrives 300 ms after the fit is asked).
- Results: 0 warnings; 235 tests with H-5 to H-9; desktop vs 615afde clock-only, apart from ≤ 8 pixels
  of 1-colour-level anti-aliasing noise.
- Lesson: my preview hid a timing bug because its pages were cached. A fresh-render check now forces
  the slow order.

### 7 Nov, 05:05: D-88 (H-10, H-11), Foundation hand-off, e5802e6 merged
- Merged `platform/foundation` e5802e6 (fourth combined patch, single instance); clean; all hooks apply.
- **H-10** (Dashboard, D-88): PhoneShell cascades its search button as `PhoneHomeSearch`; Home places
  it under the count line as in 4a. Without the hook the shell's own copy shows (mobile.css `:has()`
  hides it once Home has placed it); checked on this branch alone.
  - StartupProbe caught the first draft adding one whitespace text node to the desktop HTML. Moved the
    expression onto the `</section>` line, and the desktop Home HTML is now byte-identical.
- **H-11** (Settings, D-88): one-line summaries in the phone section list. The mock's "audit log" is
  "audit trail" here (the Account section's own title).
- Foundation's asks: (a) the Web UI slot is in my PhoneShell (merge this branch; their own patch also
  applies to Foundation's session-2 copy); (c) Redact = H-7. Both set out at the top of
  FOR-FOUNDATION.md.
- D-89 drop zone: nothing to build; check on phone and tablet when Foundation lands it.
- Results:
  - 0 warnings; 266 tests with H-5 to H-11.
  - Desktop vs e5802e6: clock only, plus 2 / 15 pixels of 1-level noise on Arrange / Home.
  - StartupProbe +0.4 ms total.
  - Gestures and checks: 30 PASS on phone (portrait and landscape) and tablet; 0 console errors.
- Gesture bugs (item 4): the fixes are in (swipe rule, H-9 fit, long-press). The device check waits for
  CI (billing hold; no runs triggered).

### 7 Nov, 05:20 (D-93): CI red on windows-latest → fixed upstream; H-12
- Run 42313017152: `shared (windows-latest)` failed, with 4 SingleInstanceTests on Foundation's new
  Windows single-instance code. Cause: an acquired named Mutex is thread-owned (re-entrant in tests;
  abandoned when the `ClaimAsync` pool thread retires, giving a second "primary" in real use).
  Foundation fixed it in 839571e (created, never acquired); reviewed, correct.
- Merged Foundation 4819d66 (fix, D-89 drop wording, CI rules). All hooks apply. Run 42314377764:
  **all 6 jobs green**.
- D-89 check (as asked): the first-run box could never show on Android, because Phase 0 sample recents
  and pins are seeded on every non-server host. **H-12** (Core, for decision) turns the samples off on
  Android only.
  - Proven with the preview's new `CHVD_EMPTY=1` (fresh install). Before: phantom recents, no first-run
    box. After: "Open your first document", D-89 C wording correct on phone and tablet.
  - Results: desktop unchanged; 266 tests with H-5 to H-12.
- For PlatformText: the tablet first-run tip says "Ctrl K".

## 8 Nov: Android round 3 → H-13; sixth combined patch merged
- Round 3 (run 42314548860): swipe, pinch, long-press drag pass on all four emulators; phone sideways
  overflow 0 px (H-9). Two new findings: double-tap lands on the wrong page; API 35 Fit page 147 px.
- Reproduced headless on Foundation 8098695 (sixth combined patch, with H-5 to H-12):
  - Double-tap on page 2: under 2 → **3**, counter 2 → **1**. Causes: `anchorZoom` scales the fixed
    page gaps; the visible-page spy keeps stale, height-relative ratios (logged `OnPageVisible(1)` at
    218 ms into the gesture).
  - Old-WebView fit: faked API 35's unzoomed boxes → fit 0.197 instead of 0.444.
- **H-13** (reader.js): page-anchored zoom; visible page by pixels, measured now (also on scroll);
  natural size from the SVG's width / height. Same natural-size fix in my `fitWidthZoom`.
- Tests: gestures.py "double-tap on page 2 stays on page 2"; checks.py "fit … unzoomed (API 35)".
  Before FAIL, after PASS (phone portrait and landscape, tablet).
- Results:
  - 273 tests; desktop clock-only, apart from 12 pixels of 1-level noise on Home.
- Merged Foundation 8098695: one conflict, in mobile.js (Foundation carried my earlier copy); kept
  mine. H-5 and H-12 landed in merged / generalised form, intent checked.

## 8 Nov, evening: round 5/6 screenshots vs the handout → fixes, H-14
- Round 6 artefacts (run 42488183117, API 36 phone and tablet; API 35 shows the D-105 WebView screen).
- Handout frames 12d–12j rendered from `Portal & Android.dc.html`; headless shots for the frames round 6
  doesn't cover.
- Fixed (mobile.css, PhoneSheet, PhoneShell, mobile.js):
  - no touch scrollbars; page curl and View-rail zoom readout hidden on touch;
  - View sheet docked above the strip and bar (no dimming);
  - phone Arrange: no inline Add desk, plain ···, FAB hides while the Shelf is open;
  - tablet portrait: the Shelf is a bottom sheet (no column);
  - phone pages top-aligned.
- **H-14** (Reader + reader.js): phone opens at Fit width; the fit's side padding comes from
  `--rfit-pad-x` (phone 24 px), so the page is edge to edge with 12 px margins.
- Checked rather than assumed:
  - Handout sheet rows are 44 px (measured), so mine match.
  - Tablet rails already scroll.
  - "/ row" is a Bench label.
- Merged Foundation 9fbed93 (seventh combined patch, H-13 as written).
- Results:
  - 274 tests with H-14; desktop clock-only apart from ≤ 8 pixels of 1-level noise.
  - 39 gesture and platform checks pass; 0 console errors.
- Four decisions for the coordinator (FOR-FOUNDATION.md): the TOOLS heading, Save at the Mark rail's
  foot, the More view options button, the tablet-portrait desk toolbar.

### 8 Nov, 20:30: D-111 to D-114
- D-112 (Save on the tablet Mark rail): the rail already ends with Save / Save as new; it scrolled out of
  view. mobile.css pins a tools rail's primary action at the foot on the tablet (solid when disabled).
  No Reader diff.
- D-114 → **H-16** (Bench): desk actions in the ··· menu on touch; footer not rendered there. Fixes my own
  session-1 gap (the phone hid the footer, so its actions were unreachable). shoot.py `-deskmenu`
  scenario.
- `mobile-ui-hooks-5.patch` = H-14 + H-16, which applies to 9fbed93.
- Results:
  - 274 tests; desktop Read / Mark identical, Read 990 clock only, Arrange / Home 1-level noise as A/A.
  - 39 touch checks pass; 0 console errors.
- D-111 (keep the mode-name heading) and D-113 (keep More view options) recorded.

## 9 Nov, 01:30: eighth combined patch merged; nothing outstanding for Foundation
- Foundation 839d39d (eighth combined patch) contains **H-14** (63f37b1) and **H-16** (839d39d), both
  exactly as written (reverse-apply check). The D-112 tablet Save needed no diff (mobile.css). No hooks
  are outstanding.
- preview.sh skips a hooks patch that is already in the tree.
- Results: 295 tests; 26 phone and tablet touch checks pass; 0 console errors.
- Android Test chat: no `platform/android-test` branch or `docs/android-test/BUGS.md` yet. Nothing to
  pick up.
- Other Test chats' lists, checked for Mobile UI items:
  - Web Test WT-03 (phone portal showed desktop rails) is fixed upstream by the sixth patch's
    PhoneShell, waiting for the Web rebase.
  - WT-09 (no-print reason only in a hover tooltip) is an existing file, routed to Arun.
  - Linux and Mac lists have no touch items.

## 9 Nov: Android Test AT-04, AT-05, AT-06; Foundation 053e8e4 merged
- Merged Foundation 053e8e4. The landed combined patches (hooks-3, 4, 5) no longer applied either way
  after the ninth and tenth patches, so preview.sh (and Android's `compose.sh`) would fail on them:
  moved to `proposal/landed/`; preview.sh applies only the outstanding `mobile-ui-hooks-N.patch`.
- **AT-04** → **H-17** (Bench): the touch desk header is name · chips · N pg · ···; the small buttons
  move into the ··· menu with labels. `mobile-ui-hooks-6.patch`.
- **AT-06** (targets under 44 dp), mobile.css only, no look change:
  - tablet top bar: brand, ‹ ›, Document, search get invisible `::after` areas; the page box gets a
    transparent border (44 × 44, same visible box); the pager gap is 10 px (was 4) so the box and the
    arrows don't overlap. Tablet desk ··· gets a 44 px area.
  - phone: avatar (the old `outline` gave no hit area, now `::after`), pager chip, sheet handle.
  - both: the desk name field is 44 px tall to tap, same layout.
  - The Library `.libp-go` / `.tagchip` already had `::after` areas; AT-06 measured the boxes.
  - Audit (elementFromPoint ±21 px from each control's centre): nothing under 42 px on tablet Read /
    Arrange (800×1280, 1280×800 Read), phone Read / Arrange / Home.
  - Not in AT-06 but seen: the tablet-landscape Shelf (docked, ≥1000 px) keeps its desktop-size
    controls (16–28 px). Left for a decision.
- **AT-05** is not a portrait or touch layout issue: the screenshot is Arrange, and Arrange registers
  no Document menu on any platform (desktop too); `Document ▾` shows in Read portrait. 12f draws it in
  Arrange. Needs a decision on what it holds there.
- gestures.py: the tablet-portrait drag test opens the Shelf peek first (it failed on a closed peek;
  the app was fine).
- Results:
  - 305 tests (191 + 16 + 59 + 39) on the patched tree.
  - Desktop before/after (Foundation vs this branch + H-17): clock only on Read, Mark, Arrange, Home
    and the open desk menu.
  - Touch gestures and checks pass at 800×1280, 1280×800, 412×915, 915×412; 0 console errors.

## 9 Nov, 04:42: D-37 for every touch control (coordinator)
- Coordinator: every touch control gets at least a 44 px tap area, the Shelf's too; visible size as drawn.
- mobile.css: Shelf (icon buttons 44 px boxes; file-row icons 44 px apart, on their own line when docked;
  tools, slider, add, filter fields and buttons), Library on the tablet (name, checkbox drawn at 15 px with a
  44 px target, tag rows, view buttons, search), phone Library fixes (the name and tag areas were clipped by
  their own overflow), Settings (segments, toggles, list), Home (mini buttons, links), dialog sliders and
  dialog spacing (Watermark, Header & footer, Interleave).
- mobile.js `nearTarget`: a tap on nothing clickable goes to the nearest control within its 44 px area
  (OPTIONS MU-11, pros and cons).
- `tools/mobile-ui/targets.py`: the audit; checks.py: a real tap 5 px outside Watermark's "B" toggles it.
- Results:
  - Audit at 1280×800, 800×1280, 412×915, 915×412 on Read, Mark, Protect, Arrange, Shelf, desk menu,
    Document menu, View sheet, Home, Library, Settings, and Print, Properties, Export, Watermark, Header &
    footer, Interleave, Press: nothing under 44 px apart from (a) the sheet handle, whose 44 px area sits
    mostly above it (a tap there closes the sheet anyway), (b) rows scrolled half under a bar, and (c) the
    "change…" folder buttons in the Export / Press cards (inline-styled, 16 px, close to the next button:
    note to Foundation).
  - 305 tests; desktop clock-only (Read, Mark, Arrange, Home, desk menu); 56 touch checks pass (52 gestures and checks, plus the new tap check at 4 sizes); 0 console
    errors.

## 9 Nov, 05:55: Android Test look bugs routed here (AT-04, AT-05, AT-06, AT-09)
- Merged Foundation 42461ba (eleventh combined patch). H-17 still applies.
- AT-04: H-17 (desk header on touch), already written. AT-06: done (D-37 work above).
- AT-05 → **H-18**: Arrange keeps Document ▾ on tablet and phone; each item runs in Read on the active tab.
- AT-09 → **H-19**: Find scrolls to the match, not its page's top. Reproduced first: at 3× zoom the match
  near page 3's foot stayed below the screen at 1280×800, 800×1280 and 412×915.
- Preview fixture: page 3 of every fixture PDF has one word, "zephyrine", near its foot (the AT-09 case).
- `mobile-ui-hooks-6.patch` = H-17 + H-18 + H-19; applies to 42461ba.
- checks.py: Arrange › Document › Properties opens the card in Read; Find shows the match on screen with
  the counter on its page.
- Results:
  - 324 tests (210 + 16 + 59 + 39) on the patched tree.
  - Desktop before/after: clock only on Read, Mark, Home and the desk menu; Arrange clock plus ≤ 8-level
    noise, as in A/A runs.
  - 64 touch checks pass at 800×1280, 1280×800, 412×915, 915×412; 0 console errors.

## 9 Nov, 06:40: decisions
- Document ▾ in Arrange (H-18): touch-only, as written. Windows' layout is the Reader chat's call.
- The three touch-only visible changes (Settings options ≥ 44 px wide, tablet pager 12 px wider, docked Shelf
  icons on their own line): approved.
- H-17 to H-19 go to Foundation as `mobile-ui-hooks-6.patch` (applies to 42461ba). Desktop static screens
  pixel-identical (last run: clock only, Arrange ≤ 8-level noise as A/A).
- Merged Foundation 6fbe24e (twelfth combined patch); `mobile-ui-hooks-6.patch` still applies.
  Re-run on the merge: 64 touch checks pass at 4 sizes, no Read control under 44 px; desktop Read, Mark and
  desk menu clock only, Arrange and Home clock plus ≤ 8-level noise (as in A/A runs).

## 9 Nov, 07:32: Foundation 022b7c0 merged; H-17 to H-19 landed; H-20
- Merged Foundation 022b7c0 (non-destructive merge, as on every update: force-pushes are refused here).
  H-17, H-18 and H-19 are in bfffab6 exactly as written; hooks-6 moved to `proposal/landed/`.
- D-134 check: only the view-only rail says TOOLS; Read, Mark, Protect and Arrange keep their mode names →
  **H-20** (`mobile-ui-hooks-7.patch`), five `Heading=` values.
- D-135 check: the Mark rail ends with Save and Save as new PDF on every platform.
- Tablet Save pin (D-112), measured with and without it (tools rail, Save buttons in view?):
  - Without: tablet landscape 1280×800 and 1024×768 Mark rail scrolls; Save and Save as new are both below
    the fold. Portrait 800×1280 fits. Protect and Arrange fit everywhere.
  - With (today): Save as new stays visible; plain Save scrolls away in landscape.
  - Desktop for comparison: fits at 1440×900 and 1366×768; at 1280×720 Save as new is below the fold.
  - Pin kept until the coordinator decides (options in the status).

## 10 Nov: D-150 and D-151 done; Foundation f88f9ef merged
- Merged Foundation c91a581 (9 Nov) and f88f9ef (nineteenth combined patch).
- **D-150** (mobile.css, tablet only): Mark's Save pins just above Save as new PDF at the foot of the tools
  rail (48 px button + 4 px gap; only the gap is covered between them). Protect and Arrange keep their single
  pinned action. Desktop untouched.
- **D-151 → H-20 updated**: SideRail `Label` parameter (aria-label), Heading TOOLS on every tools rail with
  the mode name as Label. Regenerated against f88f9ef as `mobile-ui-hooks-7.patch`.
- checks.py: tablet Mark rail shows TOOLS, announces MARK, and both Saves stay in view at the rail's top,
  middle and foot (1280×800 and 1024×768 scroll; 800×1280 fits).
- Test hygiene: the preview keeps a tab's mode and zoom between runs, so the new Mark-rail check left the
  next tablet run in Mark, where swipes don't page (3 false swipe failures). checks.py now returns to Read
  and Fit page after its checks, and gestures.py starts in Read. Two back-to-back full runs: 66 / 66 pass.
- Results:
  - 367 tests (233 + 16 + 77 + 41) on the patched tree (localpackages from `scripts/setup-feed.sh`).
  - Desktop before/after at 1440×900: Read, Mark, Arrange and the desk menu differ only in the rail heading
    (40 × 6 px, READ / MARK / ARRANGE → TOOLS) and the clock; Home clock only; aria-labels unchanged
    (READ, MARK, ARRANGE, PROTECT); 0 console errors.

## 10 Nov, 09:13: Android Test round 5 — AT-06 and AT-09 (tablet)
- Merged Foundation 846706e (H-20 landed as the twenty-second patch). preview.sh: with no outstanding hooks
  patch, `ls` failing under `pipefail` stopped the script silently; fixed.
- **AT-06**: Android Test measures each control's own box (as TalkBack and the Accessibility Scanner do);
  the earlier invisible `::after` areas don't show there. The listed controls now have 44 px boxes of their
  own, drawn exactly as before: transparent bands with the background clipped inside, outlines as inset
  lines, negative margins so nothing moves. Phone avatar, pager chip, sheet handle, Library search button,
  filter chips, view buttons, tag add; tablet brand, page arrows, Document, search, desk ··· .
  - Before/after screenshots of Home, Library, Read, the sheets and the tablet top bar: same layout
    (container positions identical); differences only in antialiasing of the outlines (a 1 px outline as an
    inset line, held at 1 px on 1× screens) and the "5m / 7m" times.
  - checks.py: the AT-06 list measures ≥ 44 px on every size (fails on the old CSS: tb-brand 83×22 …).
- **AT-09 (tablet)** → **H-21** (reader.js, `mobile-ui-hooks-8.patch`): a jump keeps its target through
  page-height changes and the page box keeps the match's page. checks.py's Find check now runs with a 6×
  slower CPU and page heights changing during the move; it fails on Foundation's reader.js (page box 4,
  view off the match) and passes with H-21 on every size.
- New finding (not changed, question to the coordinator): on touch the desk page tiles' action row
  (Peek, Duplicate, Rotate, Split here, Crop, Margins; 18 px) is invisible (shown on hover) but still takes
  taps: a tap at the foot of a tile duplicates the page (seen at 412×915 and 1280×800).
- Results: 386 tests (247 + 16 + 82 + 41); 70 touch checks pass at 4 sizes; desktop before/after
  identical apart from the clock; 0 console errors.

## 10 Nov, 16:40: Foundation 15033c8 merged; D-163; H-21 withdrawn
- Merged platform/foundation 741930b (patch 23), then platform/foundation-pr 15033c8. The PR branch has its
  own history (squashed) and the same tree as 741930b less 34 doc / workflow files, so it needed
  `--allow-unrelated-histories`; the only conflicts were in this branch's own files (the PR branch holds an
  older copy of mobile.css, mobile.js and the preview host), resolved to this branch's. 15033c8 is now an
  ancestor of the head, and every shared file equals 15033c8's.
- H-21: covered by patch 23 (see FOR-FOUNDATION); hooks-8 retired.
- **D-163**: stopgap in mobile.css — the page tiles' hover action row isn't rendered on touch (it took taps
  while invisible). **H-22** (`mobile-ui-hooks-9.patch`, Bench.razor +11): the actions in the touch desk
  menu for the selected pages.
- checks.py: a tap at a tile's foot only selects; the desk menu duplicates the selection. The → check no
  longer assumes the run starts on page 1 (the preview keeps a tab's page).
- Results: 390 tests (247 + 16 + 86 + 41) on the patched tree; 74 touch checks pass at 4 sizes, two runs back
  to back; desktop before/after identical apart from the clock (Read, Mark, Arrange, Home, desk menu); 0
  console errors.

## 10 Nov, 20:50: Foundation dd59362 (patch 24) merged; Excel on phone and tablet
- Merged platform/foundation-pr dd59362: no conflicts.
- Excel formats and the value bar, with `tests/…/Fixtures/Office/formats.xlsx` opened through the preview's
  `/__preview/open`:
  - Formatted cells show as on desktop at all four sizes (currency, separators, percentages, dates,
    accounting, ₹); the grid scrolls sideways inside its own area, no page overflow.
  - Tablet: a tap selects the cell and the value bar shows its address and stored value.
  - **Phone: the value bar never showed** — the tap listener wasn't added (an after-render ran before the
    grid was drawn; an empty element reference went to `gridValueBar`). → **H-23** (XlsxView.razor).
  - mobile.js: a spreadsheet cell takes its own tap (it isn't a control, so a tap on a cell within 22 px of
    a small control — the sheet tabs, Grid / As printed — would have gone to that control).
  - Not this chat's: `h:mm` cells show `########` (Foundation's SH-L1) and date 14 shows `03-15-23` (SH-L2),
    as Foundation's audit lists.
- checks.py: Excel — `($1,235)` shown, a tap shows `B9 = -1234.5` in the bar, on screen; then closes the tab.
- Results: 438 tests pass, 3 skipped by Foundation as library items (PDF-L1, PDF-L2, SH-L1): 292 + 16 + 89 + 41
  on the patched tree; 78 touch checks pass at 4 sizes; desktop before/after identical apart from the clock
  (Read, Mark, Arrange, Home, desk menu); 0 console errors.

## 11 Nov, 02:35: Foundation 742a5da merged; H-22 landed; AT-06 leftovers
- Merged platform/foundation-pr 742a5da (patch 25, parts 1-4): no conflicts. H-22 is in, exactly as written;
  hooks-9 now carries H-23 only, regenerated against 742a5da.
- **AT-06 leftovers** (Android Test R8): the controls that still had an invisible `::after` area instead of a
  box of their own now have 44 px boxes, drawn as before — desk name field (phone 43.7, tablet 41.5–43),
  Home `Open library` link, Home small buttons, Settings side list (tablet), size options, switches, Arrange
  `Add a file` / `Fetch another PDF`, Shelf search button. Tablet Home recent rows are 44 px high (were 34;
  the phone's are 50): a list row is its own control, so the row itself grows.
  - Before/after screenshots: Settings (tablet and phone), Home (phone) and phone Arrange identical; tablet
    Arrange differs by 59 px of antialiasing at the `Add a file` icon; tablet Home only in the clock.
- New `tools/mobile-ui/boxes.py`: every visible, enabled control's own box on Home, Library, Settings, Read,
  Mark, Arrange, Shelf, desk menu, Protect and the Document menu — as Android Test measures. 0 under 44 px at
  412×915, 915×412, 800×1280 and 1280×800 (it found 21 before this change).
- Results: 453 tests pass, 3 skipped by Foundation as library items: 305 + 16 + 91 + 41 on the patched tree; 78
  touch checks pass and the box audit is clean at 4 sizes; desktop before/after identical apart from the clock
  (the bar clock, and the time in Home's greeting line); 0 console errors.

## 11 Nov, 06:35: Foundation 07ed3ca (patch 26) merged; no hooks left; Excel grid and turned pages on touch
- Merged platform/foundation-pr 07ed3ca: no conflicts. H-23 is covered by Foundation's own fix; hooks-9 and
  the H-23 diff moved to `proposal/landed/`. **No outstanding hooks patch.**
- **Excel grid** (`Fixtures/Office/layout.xlsx`), Foundation's own proof run with touch at 412×915, 915×412,
  800×1280 and 1280×800: 19 of 19 at each size — merged cells, hidden row and column, text running over, rich
  text, data bars, borders, comment mark, hidden sheets shown dimmed, value bar with its link (on the phone
  too, with no hooks patch), a far cell, frozen panes, windowing, Find on shown and stored value, a
  right-to-left sheet, 150 %, no script errors. Find for a workbook opens from the rail (tablet) and ⋮ (phone).
  - The sheet tabs (27 px) and Grid / As printed (24 px) are now 44 px boxes on touch, drawn as before (3
    antialiasing pixels differ at the selected tab's corner); the bottom bar keeps its 37 px.
  - mobile.js and checks.py follow the new grid markup (`.xv-cell` is no longer a `td`).
  - boxes.py opens the workbook and measures the Excel view too.
- **Turned pages** (a 4-page PDF with /Rotate 0, 90, 180, 270) at the same four sizes: pages are shown
  turned; a ×2 pinch on the /Rotate 90 page gives exactly 2.00, the page stays turned and the page box stays
  on 2; no console errors. A double tap after a pinch zooms further (Foundation's design: a pinch ends the
  double-tap toggle).
  - For Foundation (FOR-FOUNDATION.md): F-1 Find's highlight on a turned page is drawn unturned and Find
    scrolls to the wrong spot; F-2 Fit page lets a turned page overflow sideways in portrait (137 px on the
    phone).
- Results: 522 tests pass, 6 skipped by Foundation: 374 + 91 + 41 + 16, with no hooks patch; 78 touch checks
  pass and the box audit is clean at 4 sizes; 0 console errors.
- Desktop before (07ed3ca) / after at 1440×900: Read, Mark, Arrange, the desk menu and the Excel view
  identical apart from the clock. Home: identical apart from the clocks in one run of three; in the other
  two, 4 pixels differ by 1 or 2 colour levels — and the same 4 pixels differ between two runs of the
  "after" build itself, so it is drawing noise, not a change. (The first pass showed the same kind of
  1-level pixels on Arrange and the Excel view; a repeat on fresh hosts was clean.)

## 15 Nov, 23:30: Android Test round 10 — AT-22 (mark card over Save) and AT-20 (Shelf drag on the tablet)
- Coordinator: 44 px for the tablet Home recent rows is confirmed (the touch rule holds everywhere). F-1 and
  F-2 are with Foundation.
- **AT-22** (phone: a drawn mark's card covers Save as new PDF and can't be closed). Reproduced at 412×915:
  the card covered the floating Save and the tool strip, ran 18 px under the bottom bar, and had no ×.
  - mobile.css (mine): in Mark and Protect the card now sits above the tool strip, so the tools stay usable;
    while any card is open the floating Save rides 12 px above the card's top edge (CSS anchor positioning;
    where a WebView doesn't have it, Save sits under the top bar instead); the card's height leaves room
    for Save in landscape too.
  - H-24 (Foundation's Reader.razor, as a diff): the Text box, shape and Image cards get a close control
    on tablet and phone. Closing drops the selection; the mark stays.
  - Tablet: the card never covered the rail's two Saves; its × (all cards) was 25×15 and is now a 45 px box
    drawn on the same pixels.
  - checks.py check 11: draw a rectangle; Save and the tools are the top element at their centres; × is
    ≥ 44 px; × closes the card and the mark is still there; then the mark is deleted again.
- **AT-20** (tablet portrait: long-press drag from the Shelf doesn't land). My side was part of it: the
  drag armed after 450 ms, and Android's own long-press time is 400 ms — `input draganddrop` starts moving
  at 400 ms, so the move came first and was taken as a scroll. Measured at 800×1280 with the sheet open,
  page 3 to the middle of the desk: holds of 380, 400 and 430 ms failed, 470 and 520 ms landed.
  - mobile.js: `LONG_PRESS_MS` 450 → 350. gestures.py's Shelf drag now holds 400 ms.
  - For: a drag at the platform's own timing lands, phone and tablet. Against: a finger that rests 350 ms
    on a page before scrolling now picks the page up instead of scrolling (was 450 ms).
  - The raw touch script not following the tablet's rotation is Android Test's side, as its note says.
- Results (with hooks-10 applied): 522 tests pass, 6 skipped by Foundation: 374 + 91 + 41 + 16; touch at
  800×1280, 1280×800, 412×915, 915×412: 82 checks pass (gestures 8/8/9/9, checks 12 each), box audit clean
  at all four; desktop before (07ed3ca) / after at 1440×900: Read, Mark, Mark with a rectangle selected,
  Arrange and the desk menu identical apart from the clock; Home shows the same 4 noise pixels as on 11 Nov
  (they also differ between two runs of one build).

## 16 Nov, 00:15: Foundation 57a63c5 (patch 27) merged; pinch and marks by finger and by mouse
- Merged platform/foundation-pr 57a63c5: no conflicts. (My clone's fetch list only had main and mobile-ui,
  so a plain fetch missed it; fetched `refs/heads/platform/*` explicitly.)
- The repo `global.json` pins SDK 10.0.403 and its workload set: `dotnet workload update` once in
  /home/claude/mui, as Foundation's note says; before it nothing built ("Workload version 10.0.403 … not found").
- New tool `tools/mobile-ui/pinchmarks.py` (18 checks), at 800×1280, 1280×800, 412×915 and 915×412:
  - PDF: two-finger pinch ×1.5 → ×1.50; Ctrl + wheel (mouse, trackpad) zooms; `window.chuvadiPinch` ×0.8 → ×0.8.
  - Excel and Word: two-finger pinch ×1.4 → text ×1.4; Ctrl + wheel; `window.chuvadiPinch` ×1.25; no
    sideways page overflow. (Finger pinch on these viewers is new in patch 27 and doesn't collide with
    mobile.js.)
  - Mark: a rectangle dragged by finger and by mouse lies under the drag (0 px off) at the fit zoom and at ×1.6.
- **Found:** in Mark, a finger pinch also placed a mark each time (a text box, or the picked shape). Not new
  in patch 27. Shared code, so it is a diff for Foundation: **H-25** (FOR-FOUNDATION.md). hooks-10 is replaced
  by `mobile-ui-hooks-11.patch` = H-24 + H-25. The first shape of H-25 broke Foundation's
  `Every_markup_press_is_tracked_so_pointerup_waits_for_it`; reshaped so `MkUp` still opens with the press wait.
- Results (hooks-11 applied): 528 tests pass, 6 skipped by Foundation: 374 + 97 + 41 + 16; touch at the four
  sizes: 154 checks pass (pinchmarks 18 each, gestures 8/8/9/9, checks 12 each), box audit clean; desktop
  before (57a63c5) / after at 1440×900: Mark, Mark with a rectangle selected, Arrange and the desk menu
  identical apart from the clock; Read and Home show the known 1 to 2 level noise pixels (same places as
  on 15 Nov, where a repeat run was clean).

## 16 Nov, 02:45: Foundation 87f95c0 (patch 28) merged; F-1, F-2, H-24 and the Find changes re-checked
- Merged platform/foundation-pr 87f95c0: no conflicts. H-24 is in as sent: its patch and hooks-11 moved to
  `proposal/landed/`. Foundation also touched two of my files (PhoneToolStrip.razor: a `dim` class;
  mobile.css: `.ph-tool.dim`, for D-187) — kept.
- New tool `tools/mobile-ui/turned.py` (13 checks; needs a four-turns PDF: /Rotate 0, 90, 180, 270 with
  `rotmark<turn>` on each page), at 800×1280, 1280×800, 412×915, 915×412:
  - F-1: Find's highlight is on the word, turned as the word is, on screen and not covered, on all four turns.
  - F-2: Fit page keeps every page inside the desk (phone portrait: 388×549 upright, 388×274 turned; no
    sideways overflow); Fit width no wider than the desk.
  - Excel: the Find box has the cursor; "2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)"
    shows above the sheet, whole and inside the screen (one 26 px line at 412 px); gone when no match is hidden.
  - Word: the Find box has the cursor.
  - H-24: checks.py check 11 passes with no hooks patch for it (× on the card closes it, the mark stays).
- **Found and fixed (mine, mobile.css):**
  - The Find bar's controls were 26 px (arrows, ×, word) and 30 px (box) on touch; the box audit never
    opened Find. Now 44 px boxes on phone and tablet, drawn as before (50 corner pixels of antialiasing
    differ on the tablet bar). turned.py checks them.
  - Phone: the Find bar was 428 px wide on a 412 px screen (8 px cut each side) and lay over the top 56 px
    of the page; `rotmark90` sat half under it. While Find is open it now takes the top bar's place.
    For: nothing of the page is covered, the bar fits any width. Against: the title, page chip and ⋮ are
    hidden while Find is open (the bar has its own count and ×).
- **Found, shared code:** H-26 (page at a time: Find settles on the next page when the match is low on its
  page) as a diff; F-3 (the Find bar covers a match at a page's top on tablet and desktop) as a note. Both
  in FOR-FOUNDATION.md. hooks-12 = H-25 + H-26.
- Results (hooks-12 applied): 539 tests pass, 6 skipped by Foundation: 382 + 100 + 41 + 16; touch at the
  four sizes: 206 checks pass (turned 13 each, pinchmarks 18 each, checks 12 each, gestures 8/8/9/9), box
  audit clean; desktop before (87f95c0) / after at 1440×900: Mark, Mark with a rectangle selected, Arrange,
  the desk menu and Read with Find open identical apart from the clock; Read and Home show the known
  1-level noise pixels in the same places as before.

## 16 Nov, 14:40: Foundation 71754e1 (patch 29) merged; the ask-before-closing card and Excel resize by finger
- Merged platform/foundation-pr 71754e1: no conflicts. H-25 and H-26 still apply and are still outstanding.
- **The ask-before-closing card** (new tool `tools/mobile-ui/closecard.py`, 6 checks; it opens a copy of a
  PDF under a 100-character name), at 412×915, 915×412, 800×1280, 1280×800:
  - Phone, both ways up: Save / Save as… / Discard / Cancel all there, each 44 px high, each the top element
    at its centre, inside the screen; the long name wraps. With the system bars' insets set (24 px top,
    48 px bottom, through Chrome's safe-area override) the card sits above the bottom bar. With the keyboard
    up (the window 320 px shorter in portrait, 200 px in landscape) all four are still on screen.
    Foundation's phone styling holds; I only added a height limit with scrolling, for safety.
  - Tablet: the four answers were 30 px high. Fixed with the cards below.
  - Cancel keeps the tab and its mark; Discard closes the tab.
  - Not seen here: a real keyboard and real system bars. Both are stood in for (a shorter window; inset
    override). Android Test should look once on the emulator.
- **Found and fixed (mine, mobile.css): the tablet's cards were never 44 px.** Card buttons, number and text
  boxes 30 px, segment buttons 28 px, colour dots 20 px, tick rows 19 px — on every float card; the box
  audit doesn't open cards. Now 44 px boxes drawn as before (a selected rectangle's card: 260 pixels of
  corner and dot-edge antialiasing differ, nothing moves). Colour dots and tick rows on the phone too.
  checks.py check 11 now measures every control on the rectangle's card. Still small: the tick box itself
  (13 px; its row is the 44 px target). Other cards (text box, image, sign, redact) get the same rules but
  are not measured by a check yet.
- **Excel resize by finger** (new tool `tools/mobile-ui/xlresize.py`, 13 checks), same four sizes:
  - Dragging column B's edge 60 px widens it 60 px and the sheet doesn't scroll; 10 px off the edge still
    takes it; two taps fit it and don't zoom; a row's edge the same; zoomed, the edge still follows the
    finger; a finger in the middle of a column letter scrolls; a pinch on the cells zooms.
  - "File's own sizes" was 24 px high: a 44 px box now (mine).
  - **Fights:** (1) a pinch that starts on an edge also resized → H-27 diff (shared viewers.js), fixed with
    it. (2) a finger on an ordinary (20 px) row number resizes instead of scrolling → F-4, three ways with
    for and against, for Foundation and the coordinator; xlresize.py prints it as OPEN, not FAIL.
- hooks-12 is replaced by `mobile-ui-hooks-13.patch` = H-25 + H-26 + H-27.
- Results (hooks-13 applied): 593 tests pass, 6 skipped by Foundation: 434 + 102 + 41 + 16; touch at the
  four sizes: 279 checks pass, 0 fail, 1 open (F-4, at three sizes); box audit clean; desktop before
  (71754e1) / after at 1440×900: Read, Mark, a selected rectangle's card, the ask-before-closing card,
  Arrange and the desk menu identical apart from the clock; Home has the known 1-level noise pixels.

## 16 Nov, 21:25: Foundation 4b704c8 (patch 30) merged; Android Test round 12 (AT-25 to AT-28); D-193
- Merged platform/foundation-pr 4b704c8: no conflicts. H-25 and H-26 are in: their patches and hooks-13
  moved to `proposal/landed/`.
- Round 12 was run on Mobile UI ca152c4, one commit before the card and Excel fixes of ae6ae6d.
- **AT-27** (pinch in Mark draws a rectangle): on patch 30 with no hooks patch for it, Rectangle armed, both
  fingers on the page, landing 5, 30 and 120 ms apart, one lifting first: phone 388 → 1164 → 388 px,
  tablet 596 → 1787 → 596 px; 0 marks each time, no card comes up, the pinch back works. Closed by H-25
  as landed. pinchmarks.py keeps checking it.
- **AT-26** (tablet close-card buttons 30 px): 44 px since ae6ae6d (the tablet card rule covers `.closeq`);
  now also 12 px between the answers (Save 51×44, Save as… 79×44, Discard 67×44, Cancel 63×44; Discard is
  12 px from Save as…). closecard.py checks it at both tablet sizes.
- **AT-25** ("File's own sizes" 24 px): a 44 px box since ae6ae6d (111×44), checked in xlresize.py.
- **AT-28** (Export card, Merge page 16 to 34 px). Reproduced, and wider than filed: the Press card (chips,
  slider 16, tick rows 19, number boxes 25 and 29), the Merge rows' move and remove buttons (26), the
  Split page ("change" 16, number boxes, ± steppers 30×34), "dashboard" back links (16).
  - Merge and Split are class-based: fixed in mobile.css (mine).
  - The Export and Press cards are inline-styled with no classes → **H-29** (class names only, shared
    Reader.razor), and mobile.css rules on those names. Without H-29 the two cards stay as they were.
  - All drawn as before: with and without my rules every control of the Press card keeps its centre and
    the card its height (422 px); tablet screenshots differ by 142 to 499 pixels of corner antialiasing.
  - New tool `tools/mobile-ui/cards.py`: opens the Export card, the Press card (Custom, target size on), the
    Merge page (two files added) and the Split page (page range), and fails on any control under 44 px,
    covered, or off screen. 13 + 13 + 10 + 11 controls.
- **D-193** (F-4 decided: B). **H-28**: by finger an Excel edge is taken by resting on it about 350 ms, the
  guide line showing when; a finger that moves at once scrolls; two taps fit; mouse and pen as before.
  xlresize.py is rewritten for it (15 checks, no OPEN line left): the row-number scroll that failed at
  three sizes now passes at all four.
- hooks-13 is replaced by `mobile-ui-hooks-14.patch` = H-27 + H-28 (viewers.js) + H-29 (Reader.razor).
- Not done: the real Android build. What I can run is the same shared UI in the phone and tablet shells in
  headless Chrome; the 44 px rules are plain CSS on `html[data-shell]`, so the same rules load in the
  WebView, but the measurement on the emulator is Android Test's.
- Results (hooks-14 applied): 597 tests pass, 6 skipped by Foundation: 438 + 102 + 41 + 16; touch at
  800×1280, 1280×800, 412×915, 915×412: 306 checks pass, 0 fail (gestures 8/8/9/9, checks 12, pinchmarks 18,
  xlresize 15, cards 4, turned 13, closecard 6 each), box audit clean at all four; desktop before (4b704c8) /
  after at 1440×900: Mark, a selected rectangle's card, the ask-before-closing card, the Export card, the
  Press card, the Merge page, the Split page, Arrange and the desk menu identical apart from the clock; Read
  and Home show the known 1 to 2 level noise pixels in the same places as before.
  (cards.py first failed at 915×412 on controls further down a scrolling card; the audit now scrolls each
  control into view before it tests it, and passes at all four.)

## 16 Nov, 22:50: Foundation b895750 (patch 31) merged; the encoding picker (D-191) on phone and tablet
- Merged platform/foundation-pr b895750: no conflicts. H-27, H-28 and H-29 still apply; hooks-14 stays.
- **The picker's three ways in, on touch:**
  - Status-bar button: not there. The phone and tablet have no status bar (the handout's frames), so neither
    the encoding nor the "bytes don't fit" note is on screen → F-5, a choice for the coordinator.
  - Menu entry "Text encoding…": there on the phone (⋮) and the tablet (Document ▾), a 44 px row, for
    text, Markdown and HTML.
  - The card "Read this file as": opens from that entry. Phone: a bottom sheet above the bottom bar (412 × 304).
    Tablet: in the card column (270 × 284).
- **Found and fixed (mine, mobile.css):** the card's rows were 34 px high. Now 44 px boxes drawn as before
  (card pixel-identical on the tablet; on the phone only the page behind differs).
- New tool `tools/mobile-ui/encpicker.py` (11 checks; it writes its own Windows-1252 .txt, .md and .html), at
  412×915, 915×412, 800×1280, 1280×800:
  - every row and the close control 44 px, on top, inside the screen; the same with the system bars'
    insets set (24 top, 48 bottom) and with the keyboard up (a shorter window);
  - by finger: Automatic names Windows-1252 and the accents read right; a tap on UTF-8 marks that row and
    the card says "6 bytes don't fit UTF-8"; a tap on Windows-1252 puts it right; × closes.
  - Stood in for, not seen: a real keyboard and real system bars (as for the close card).
- **Patch 31's own touch rules** ("File's own sizes" 44 px; the tablet close card 44 × 80) overlap mine:
  both hold, sizes pass. With Foundation's rule alone the Excel bar grows 37 → 53 px while a size is changed;
  mine keeps it at 37. Noted for Foundation as N-1.
- Results (hooks-14 applied): 597 tests pass, 6 skipped by Foundation: 438 + 102 + 41 + 16; touch at the
  four sizes: 350 checks pass, 0 fail (gestures 8/8/9/9, checks 12, pinchmarks 18, xlresize 15, cards 4,
  encpicker 11, turned 13, closecard 6 each), box audit clean; desktop before (b895750) / after at 1440×900:
  Mark, the mark card, the close card, the encoding card, Export, Press, Merge, Split, Arrange and the desk
  menu identical apart from the clock; Read and Home show the known 1-level noise pixels.

## 18 Nov, 00:00: Foundation 149f4fc (patch 32) merged; the three new close questions and the Find bar aside
- Merged platform/foundation-pr 149f4fc: no conflicts. H-27, H-28, H-29 still apply; hooks-14 stays.
- **The new questions** (new tool `tools/mobile-ui/closework.py`, 16 checks), at 412×915, 915×412, 800×1280,
  1280×800:
  - Bookmarks (a bookmark added with Ctrl+B, the tab closed): Save bookmarks / Discard / Cancel.
  - Protect (a redaction area drawn by finger, the tab closed): Discard / Cancel.
  - Arrange (pages on a desk, the app asked to close through the preview's close-app): Save session… /
    Discard / Cancel.
  - Each: every answer 44 px, on top, inside the screen, 8 px or more apart; the same with the system bars'
    insets set and with the keyboard up (both stood in for); Cancel keeps the work; Discard closes.
  - Foundation's styling holds; nothing changed for them.
- **Found and fixed (mine, PhoneShell.razor):** on the phone, Protect's Box opens the redaction page, and its
  Back arrow went Home, leaving the document behind (and its ⋮ has no Close). Back there now returns to the
  document (/reader). Settings sections and everything else as before. closework.py checks it.
- **The Find bar's bottom place (D-195)** (new tool `tools/mobile-ui/findaside.py`, Foundation's top.pdf, 16
  matches, as the size opens and in Fit width): no match off screen or under the bar, the bar inside, on top,
  44 px controls. Tablet: aside 0 / 3 times at 800×1280, 12 / 1 at 1280×800. Phone: never needed.
  - **Fixed (mine, mobile.css):** were the phone's bar ever given `aside` it would sit on the bottom bar
    (845 to 901 inside 835 to 915); it stays in the top bar's place there. Checked by forcing the class.
- Results (hooks-14 applied): 606 tests pass, 6 skipped by Foundation: 446 + 103 + 41 + 16; touch at the four
  sizes: 430 checks pass, 0 fail (gestures 8/8/9/9, checks 12, pinchmarks 18, xlresize 15, cards 4, encpicker 11, findaside 3/3/4/4, turned 13, closecard 6, closework 16/16/17/17); box audit clean; desktop before (149f4fc) / after at 1440×900: Read, Mark, the mark
  card, the close card, the encoding card, Export, Press, Merge, Split and the desk menu identical apart from
  the clock; Arrange and Home show 4 and 17 pixels one colour level off (the known noise).

## 18 Nov, 01:35: Foundation 9e00fdf (patch 33) merged; held redaction, the unchecked signature, the page-operation question
- Merged platform/foundation-pr 9e00fdf: no conflicts. H-27, H-28, H-29 landed exactly as sent (6257ecb): their
  patches and hooks-14 moved to `proposal/landed/`.
- Correction recorded (README, FOR-FOUNDATION): Android's `compose.sh` has not applied Mobile UI hooks since 9 Nov;
  hooks reach Android only through Foundation. Earlier rounds here said otherwise.
- **Held redaction (D-198):**
  - Phone (mine, PhoneToolStrip + PhoneShell): Box and Find in Protect's strip were plainly disabled and a tap
    said nothing. A greyed tool with a reason now answers a tap with that reason as a notice ("Redaction comes
    back with the next update."), on screen and on top. Applies to any strip tool that is off for a reason.
  - Tablet and desktop (Foundation's Reader.razor) → **H-30**: the held "Redaction" rail button passes
    `Disabled="true"`, which cancels its own `ReasonOnTap`, so no reason can be read on touch; and "Save redacted
    copy" stays as the bright primary button though it only says redaction comes back. Diff: soft button that
    notifies; Save redacted copy hidden while held.
- **The unchecked signature (D-198)** (new tool `tools/mobile-ui/signature.py`, 7 checks; a PDF signed with a
  self-signed certificate for testing):
  - The banner above the page ran off both edges on phone portrait and Details could not be reached; Details
    41×18 and its × 20×20 at every size. Fixed (mine, mobile.css): the banner stays inside the page area and
    wraps on the phone; Details, ×, the card's Close and Details / Hide details are 44 px boxes drawn as before.
  - The Signatures card's header line ("1 signature · not checked in this version") doesn't wrap and pushes Close
    out of the card, under the rail, on the tablet and on desktop → **H-31** (one CSS line). mobile.css holds the
    same rule on touch until it lands (marked for removal).
- **The page-operation question (D-198)** (new tool `tools/mobile-ui/pageop.py`, 16 checks): from Arrange (desk ···
  › Bind desk), Merge and Split, by finger. Continue / Cancel each 44 px, on top, inside the screen, 8 px apart,
  also with system-bar insets and the keyboard up; a plain file told it loses nothing; each Merge file named and
  the layer line there for a layered file; Cancel stops; after Continue the same file isn't asked again.
  Foundation's styling holds; nothing changed.
- closework.py: its Protect part now checks the held state (a tap says why; no Save redacted copy), since there
  are no redaction areas to ask about while redaction is held.
- README: lists every touch check script and the tooling traps.
- `mobile-ui-hooks-15.patch` = H-30 + H-31 (for Foundation only).
- **Found on the full run (mine):** phone landscape with the keyboard up (212 px window), the Merge question (two
  files and the layer line) scrolled inside its height limit and Continue / Cancel fell below the fold. The
  answers of every question card now stay pinned to its foot while the text scrolls; a card that fits looks
  exactly as before (Arrange question 380×226 before and after).
- checks.py: "Redact opens at fit width" (H-7) can't run while redaction is held; it now says so (NOTE) and goes
  on; it returns with redaction. The phone's checks are 11 for now.
- A container restart cut the first phone run short; the phone sizes were run again in full.
- Results (hooks-15 applied): 608 tests pass, 6 skipped by Foundation: 448 + 103 + 41 + 16; touch at the four
  sizes: 506 checks pass, 0 fail (tablet 126 each: gestures 8, checks 12, pinchmarks 18, xlresize 15, cards 4,
  encpicker 11, findaside 3, turned 13, closecard 6, closework 13, pageop 16, signature 7; phone 127 each:
  gestures 9, checks 11, findaside 4, the rest the same); box audit clean at all four. Desktop before (9e00fdf) /
  after at 1440×900, on fresh hosts: Read, Mark, the mark card, the close card, the encoding card, Export, Press,
  Merge, Split, Arrange, the desk menu and the signature banner identical apart from the clock; Protect and the
  Signatures card differ exactly as H-30 and H-31 intend (Save redacted copy gone from the rail; Close back in the
  card); Home shows its 12 known noise pixels. (A first pass compared hosts with different open tabs and differed
  everywhere; redone.)


## 18 Nov, 19:15: D-205 (F-5 option B) — the text encoding on the phone and tablet
- **Phone** (PhoneShell): the ⋮ sheet's "Text encoding…" row shows the encoding the file is read as as its value;
  while bytes don't fit it, the note in red (`--chvd-danger`, as the status bar) under the label, e.g. "6 bytes
  don't fit UTF-8". The row stays a 44 px box; it reads both aloud. No note → the row looks as before plus the value.
- **Tablet** (TouchSupport): a chip beside the page box only while there is a note; a tap opens "Read this file
  as". Drawn 26 px high, its box 44 px. The room between the page box (centred) and Document ▾ is half the width
  less 294 px, so: from 1100 px wide it shows the whole note; narrower it shows the encoding's name alone (the
  note is read aloud and is on the card it opens); below 760 px (small portrait tablets) it sits under the top
  bar, centred — the same place it takes where a WebView has no CSS anchor positioning. Found on the first check
  run: at 800×1280 the whole note covered Document ▾; hence the name-only form.
- Both read `StatusBarSlot` (D-191), which MainLayout cascades only around `@Body`; the touch shells are outside
  it → **H-32** (MainLayout, 2 lines, touch-only branches). Without it nothing new shows. `mobile-ui-hooks-16.patch`
  = H-30 + H-31 + H-32 (replaces hooks-15). Not on Android until Foundation lands it (agreed 18 Nov).
- New check `tools/mobile-ui/encnote.py` (phone 5, tablet 8 checks).
- Patch 34 (foundation-pr 5e63202, not merged here yet) does the phone tool strip's tap-for-reason (AT-30) as my
  a6e9016 does; at the next merge I take theirs.
- Leans accepted 18 Nov: phone Find bar over the top bar, 350 ms long-press, the redaction-page ⋮ as it is.
- Results (hooks-16 applied): 608 tests pass, 6 skipped by Foundation (448 + 103 + 41 + 16); touch at the four
  sizes: 532 checks pass, 0 fail (tablet 134 each: gestures 8, checks 12, pinchmarks 18, xlresize 15, cards 4,
  encpicker 11, encnote 8, findaside 3, turned 13, closecard 6, closework 13, pageop 16, signature 7; phone 132
  each: gestures 9, checks 11, findaside 4, encnote 5, the rest the same); box audit clean at all four. (pageop's
  plain-file check needs a file without bookmarks or labels — `tools/PixelProof/fixtures/foot.pdf`, not rich.pdf.)
  Desktop before (9e00fdf) / after at 1440×900 on fresh hosts: the status bar's encoding, the encoding card, the
  mark card and the close card identical apart from the clock; mobile.js not loaded.

## 18 Nov, 21:30: Foundation 5e63202 (patch 34) merged (af1b700b)
- One conflict, `PhoneToolStrip.razor`: took Foundation's (AT-30, a greyed tool answers a tap with its reason)
  and dropped my `OnReason` wiring in PhoneShell (a6e9016 did the same).
- **H-30 landed in Foundation's own form (B-36):** held Redaction answers a tap (`SayRedactionHeld`); Save
  redacted copy stays, greyed with the same reason, rather than left out. Moved to `proposal/landed/`.
  Outstanding: `mobile-ui-hooks-17.patch` = H-31 + H-32.
- Foundation's mouse proof `tools/PixelProof/excel-resize.js` on H-28 (desktop 1440×900, `hasTouch`): 19 / 19
  pass, M-29 included; the workbook on disk unchanged.
- closework.py brought up to patch 34: the Arrange close question's first answer is now "Save" (D-203, no file
  dialog), and Save redacted copy is checked as greyed, 44 px, on top, a tap says why and saves nothing (B-36).
- **Found and fixed (mine):** on a tablet the "Redaction comes back…" message sat bottom right, over the side
  rail's last button, so a tap on Save redacted copy hit the message's Dismiss. My tablet rule put messages
  there; they are now centred at the bottom over the page (the rails on the right are 72–132 px wide). Desktop
  and phone unchanged.
