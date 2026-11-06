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
