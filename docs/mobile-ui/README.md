# Mobile app UI — Android tablet and phone look

Branch `platform/mobile-ui` (based on `platform/foundation` aeeac43, Group A applied).
Design: `docs/design-handoff/Portal & Android.dc.html` 12d-12j, `Reader Side Rails.dc.html`, `tokens.css`.

## What is here (all new files)
| Path | What |
|---|---|
| `src/ChuvadiReader.Ui/Components/Platform/Phone/PhoneShell.razor` | Phone shell (12g-12j): app bar, content, FAB, tool strip, bottom bar, ⋮ menu, View sheet |
| `…/Phone/PhoneAppBar.razor` | Back · title / mono sub-line · counter (tap to type a page) or **Bind all** in Arrange · ⋮ |
| `…/Phone/PhoneToolStrip.razor` | 62 px strip, Mark and Protect only |
| `…/Phone/PhoneSheet.razor` | Bottom sheet (handle, serif title, Done, 44 px rows) |
| `…/Phone/PhoneCommands.cs` | Which ShellService command ids the strip, View sheet and FAB run |
| `…/Phone/TouchSupport.razor` | Loads `mobile.js` on tablet and phone layouts only |
| `src/ChuvadiReader.Ui/wwwroot/css/mobile.css` | Tablet sizing (72/72/60, 48 px targets) and phone folding; every rule keyed on `html[data-shell="tablet|phone"]` or `.ph-*` |
| `src/ChuvadiReader.Ui/wwwroot/js/mobile.js` | Pinch → the Reader's own zoom, double-tap fit, swipe paging, tap shows the page strip, long-press drag in Arrange, Shelf peek |
| `tests/ChuvadiReader.MobileUi.Tests` | Contract tests: command ids exist; strip/sheet match the frames; every CSS rule is scoped |
| `tests/ChuvadiReader.MobileUi.Preview` | **Testing only.** Blazor Server page that renders the Ui at phone/tablet/desktop |
| `tools/mobile-ui/*.sh, *.py` | **Testing only.** Preview runner, headless-Chromium screenshots with touch emulation, pixel compare |
| `docs/mobile-ui/proposal/mobile-ui-hooks-1.patch` | The only existing-file change (MainLayout), **not applied** — see `OPTIONS.md` |

## How it switches
`PlatformRoot` (Foundation) writes `<html data-shell>`; `mobile.css` keys on it. `MainLayout` renders
`PhoneShell` instead of its top bar / left bar / status bar when `PlatformState.Shell == Phone`
(hook H-1) and `TouchSupport` everywhere (H-2, a no-op on desktop/portal). The phone shell runs
MainLayout's own methods (passed in) and the commands the mode views already register for Ctrl K —
nothing is re-implemented.

## Hosts must link
`_content/ChuvadiReader.Ui/css/mobile.css` after `shell.css` in `index.html` (Android; Web if F-5
gives it small-screen layouts). Windows doesn't need it (harmless if linked).

## Build, test, preview
```bash
dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config
dotnet build   ChuvadiReader.Platforms.slnx -c Release --no-restore -warnaserror
dotnet test    tests/ChuvadiReader.MobileUi.Tests -c Release --configfile ci/nuget.config

# preview + screenshots (needs Chromium + Python Playwright — testing only)
tools/mobile-ui/run.sh phone   5180 out "phone-read 392x816" "phone-mark 392x816" "phone-viewsheet 392x816"
tools/mobile-ui/run.sh tablet  5181 out "tablet-read 1280x800" "tablet-arrange 800x1280"
tools/mobile-ui/run.sh desktop      5183 after  "desktop-read 1440x900" "desktop-read 990x700"
tools/mobile-ui/run.sh desktop-base 5184 before "desktop-read 1440x900" "desktop-read 990x700"
tools/mobile-ui/compare.py before after      # IDENTICAL / CLOCK ONLY = pass
```
Screens from each session are kept in `docs/mobile-ui/screens/<date>/` next to crops of the design frames.
