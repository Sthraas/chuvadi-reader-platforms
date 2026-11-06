# Mobile app UI → Foundation: hooks, session 3 (7 Nov)

Branch `platform/mobile-ui` now includes `platform/foundation` **63af90f**, which already has the combined
hooks (D-26): H-1 in MainLayout, reader.js pen/finger split (D-42), Bench's desk counter (D-46) and the
TabsService de-dup (D-48). So session 2's `H1-…`, `H3-…` and `mobile-ui-hooks-2.patch` are deleted;
nothing from them is still waiting.

Four new hooks. They are **not** applied on this branch; `tools/mobile-ui/preview.sh` applies
`proposal/mobile-ui-hooks-3.patch` (all four) in a scratch copy for testing. It applies cleanly to
63af90f with `git apply`.

| Patch | File | Decision | Lines |
|---|---|---|---|
| `proposal/H5-mainlayout-tabs-sheet.patch` | `Ui/Layout/MainLayout.razor` | D-43 | +2 / −1 |
| `proposal/H6-settings-phone-push.patch` | `Ui/Pages/Settings.razor` | D-45 Settings A | +15 / −2 |
| `proposal/H7-redact-phone-fit-width.patch` | `Ui/Pages/Redact.razor` | Coordinator, 7 Nov | +16 / −0 |
| `proposal/H8-reader-rerender-bugfix.patch` | `Ui/Pages/Reader.Shell.cs`, `Reader.razor` | **Bug fix**, found from Android run 42276742988; coordinator: combined patch (D-26) | +14 / −6 |
| `proposal/mobile-ui-hooks-3.patch` | all four, concatenated | — | — |

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

## Evidence (63af90f + this branch + hooks-3, in a scratch copy)
- Programme solution: **0 warnings, 0 errors**; tests **161 + 28 + 14 + 4 = 207 pass** (H-5 to H-8 applied).
- **Desktop pixel-identical:** before (63af90f) and after (H-5 to H-8) were run at the same time
  (`screens/2026-11-07/desktop-compare.txt`).
  - Read 1440×900 and 990×700, Arrange, Mark, Home, Library, Settings 1440×900 and 700×800: only the
    clock differs.
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
