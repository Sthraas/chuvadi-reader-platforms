# Mobile app UI — Android tablet and phone look

Branch `platform/mobile-ui` (includes `platform/foundation` 63af90f: combined hooks D-26, ReadyToRun, chuvadi-pdf 3.31.2).
Design: `docs/design-handoff/Portal & Android.dc.html` 12d-12j, `Reader Side Rails.dc.html`, `tokens.css`.

## What is here (all new files)
| Path | What |
|---|---|
| `src/ChuvadiReader.Ui/Components/Platform/Phone/PhoneShell.razor` | Phone shell (12g-12j): app bar, content, FAB, tool strip, ⋮ menu, View and Tabs sheets. Bottom bar: Read · Mark · Arrange · Protect in a document, Home · Library · Tabs · Settings elsewhere (4a, D-45) |
| `…/Phone/PhoneAppBar.razor` | Back · title / mono sub-line · counter (tap to type a page) or **Bind all** in Arrange · ⋮ (avatar on Home) |
| `…/Phone/PhoneToolStrip.razor` | 62 px strip, Mark and Protect only |
| `…/Phone/PhoneSheet.razor` | Bottom sheet (handle, serif title, Done, 44 px rows) |
| `…/Phone/PhoneCommands.cs` | Which ShellService command ids the strip, View sheet and FAB run |
| `…/Phone/TouchSupport.razor` | Loads `mobile.js` on tablet and phone layouts only |
| `src/ChuvadiReader.Ui/wwwroot/css/mobile.css` | Tablet sizing (72/72/60, 48 px targets), phone folding, phone Home / Library / Settings; every rule keyed on `html[data-shell="tablet|phone"]` or `.ph-*` |
| `src/ChuvadiReader.Ui/wwwroot/js/mobile.js` | Swipe paging (touch events), tap shows the page strip, long-press drag in Arrange, Shelf peek. Pinch and double-tap zoom are reader.js's own |
| `tests/ChuvadiReader.MobileUi.Tests` | Contract tests: command ids exist; strip/sheet match the frames; every CSS rule is scoped |
| `tests/ChuvadiReader.MobileUi.Preview` | **Testing only.** Blazor Server page that renders the Ui at phone/tablet/desktop |
| `tools/mobile-ui/*.sh, *.py` | **Testing only.** Preview runner, headless-Chromium screenshots with touch emulation, pixel compare, `gestures.py` (CDP touch: swipe, double-tap, pinch, fit, long-press drag) |
| `docs/mobile-ui/proposal/H5-…, H6-…, mobile-ui-hooks-3.patch` | The only existing-file changes (MainLayout, Settings.razor), **not applied**; for Foundation: `FOR-FOUNDATION.md` |
| `docs/mobile-ui/MU-8-PHONE-SCREENS.md`, `mocks/` | Phone Home / Library / Settings: the options and mocks behind D-45 (now built) |
| `tools/mobile-ui/mocks.py` | **Design only.** Renders the mock frames |

## How it switches
The host page writes `<html data-shell …>` for the first paint and MainLayout keeps it in sync
(non-Windows only); `mobile.css` keys on it. Components read `IPlatformInfo` (`@inject`, `Shell()`,
`FormFactorChanged`) — there is no cascade. `MainLayout` renders `PhoneShell` instead of its top bar /
left bar / status bar when `FormFactor == Phone`, and `TouchSupport` on non-Windows tablet/phone
(H-1, applied by Foundation; Windows renders neither). The phone shell runs
MainLayout's own methods (passed in) and the commands the mode views already register for Ctrl K —
nothing is re-implemented.

## Hosts must link
`_content/ChuvadiReader.Ui/css/mobile.css` after `shell.css` in `index.html` (Android; Web if F-5
gives it small-screen layouts). Windows doesn't need it (harmless if linked).

## Build, test, preview
```bash
dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config
dotnet build   ChuvadiReader.Platforms.slnx -c Release --no-restore -warnaserror
dotnet test    tests/ChuvadiReader.MobileUi.Tests -c Release --no-restore

# preview + screenshots (needs Chromium + Python Playwright — testing only)
tools/mobile-ui/run.sh phone   5180 out "phone-read 392x816" "phone-mark 392x816" "phone-viewsheet 392x816"
tools/mobile-ui/run.sh tablet  5181 out "tablet-read 1280x800" "tablet-arrange 800x1280"
tools/mobile-ui/run.sh desktop      5183 after  "desktop-read 1440x900" "desktop-read 990x700"
tools/mobile-ui/run.sh desktop-base 5184 before "desktop-read 1440x900" "desktop-read 990x700"
tools/mobile-ui/compare.py before after      # IDENTICAL / CLOCK ONLY = pass

# touch gestures (CDP touch events); <layout>-base runs unchanged platform/foundation for "before"
tools/mobile-ui/run.sh phone      5185 out "gestures 412x915" "gestures 915x412" "gestures-jitter 412x915"
tools/mobile-ui/run.sh tablet-base 5186 before "gestures 1280x800"
```
Run desktop and desktop-base **at the same time** (two ports, `CHVD_SCRATCH` apart): Home and Library
show the clock and relative ages ("2m"), which differ if the runs are a minute apart. A difference of
1 colour level on a few anti-aliased pixels also shows between two runs of the same tree.
Screens from each session are kept in `docs/mobile-ui/screens/<date>/` next to crops of the design frames.
