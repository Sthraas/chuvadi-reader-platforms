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
