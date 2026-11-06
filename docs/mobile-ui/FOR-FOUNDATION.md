# Mobile app UI → Foundation: hooks, session 3 (7 Nov)

Branch `platform/mobile-ui` now includes `platform/foundation` **63af90f**, which already has the combined
hooks (D-26): H-1 in MainLayout, reader.js pen/finger split (D-42), Bench's desk counter (D-46) and the
TabsService de-dup (D-48). So session 2's `H1-…`, `H3-…` and `mobile-ui-hooks-2.patch` are deleted;
nothing from them is still waiting.

Two new hooks, for MU-8 (D-45) and the Tabs sheet (D-43). They are **not** applied on this branch;
`tools/mobile-ui/preview.sh` applies `proposal/mobile-ui-hooks-*.patch` in a scratch copy for testing.
Both apply cleanly to 63af90f with `git apply`.

| Patch | File | Decision | Lines |
|---|---|---|---|
| `proposal/H5-mainlayout-tabs-sheet.patch` | `Ui/Layout/MainLayout.razor` | D-43 | +2 / −1 |
| `proposal/H6-settings-phone-push.patch` | `Ui/Pages/Settings.razor` | D-45 Settings A | +15 / −2 |
| `proposal/mobile-ui-hooks-3.patch` | both, concatenated | — | — |

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

## Evidence (63af90f + this branch + hooks-3, in a scratch copy)
- Programme solution: **0 warnings, 0 errors**; tests **161 + 28 + 14 + 4 = 207 pass**.
- **Desktop pixel-identical:** before (63af90f) and after were run at the same time
  (`screens/2026-11-07/desktop-compare.txt`).
  - Read 1440×900 and 990×700, Arrange, Mark, Settings 1440×900 and 700×800: only the clock differs.
  - Home: 5 pixels off by 1 colour level out of 255, on anti-aliased edges. The same region shows the
    same 1-level noise in an A/A run (63af90f vs 63af90f).
  - Library: 6 pixels off by 1 level on the anti-aliased ends of a bar. Same kind; this one didn't
    recur in 3 A/A runs.
  - Nothing visible. Earlier Home/Library differences (156 / 403 px) were "18:50" vs "18:51" and
    "2m" vs "3m" ages from running before and after a minute apart.
- StartupProbe not re-run: H-5 is inside the phone-only branch and H-6 is not on the startup path
  (Dashboard is).

## D-46 desk counter: one owner
Foundation's Bench now publishes the desk counter (`PublishDeskCounter`, bench.js `scrollDeskTo`).
My TouchSupport also published one (session 2). Two publishers would fight over the counter, so **mine
is removed** and Bench's is the one. The coordinator's note said "the desk counter with no Bench edit is
fine; keep it". That was overtaken by 63af90f already shipping the Bench version. **Please confirm**
Bench's counter is the one to keep.

## For the Android chat (via the coordinator)
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
