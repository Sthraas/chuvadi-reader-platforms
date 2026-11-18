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
| `src/ChuvadiReader.Ui/wwwroot/js/mobile.js` | Swipe paging (touch events; a fling or a drag across a third of the desk, on pages that fit), tap shows the page strip, long-press drag in Arrange, Shelf peek, Redact fit width. Pinch and double-tap zoom are reader.js's own |
| `tests/ChuvadiReader.MobileUi.Tests` | Contract tests: command ids exist; strip/sheet match the frames; every CSS rule is scoped |
| `tests/ChuvadiReader.MobileUi.Preview` | **Testing only.** Blazor Server page that renders the Ui at phone/tablet/desktop |
| `tools/mobile-ui/*.sh, *.py` | **Testing only.** Preview runner, headless-Chromium screenshots with touch emulation, pixel compare, `gestures.py` (CDP touch: swipe, double-tap, pinch, fit, long-press drag), `checks.py` (→ paging, Document › Print, phone Redact fit width) |
| `docs/mobile-ui/proposal/H5-…, H6-…, H7-…, H8-…, mobile-ui-hooks-3.patch` | The only existing-file changes (MainLayout, Settings, Redact, Reader), **not applied**; for Foundation: `FOR-FOUNDATION.md` |
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
tools/mobile-ui/run.sh phone      5187 out "checks 412x915"
```
`CHVD_EMPTY=1` before `run.sh` starts the preview like a fresh install (no tabs: Home's first-run box).
Run desktop and desktop-base **at the same time** (two ports, `CHVD_SCRATCH` apart): Home and Library
show the clock and relative ages ("2m"), which differ if the runs are a minute apart. A difference of
1 colour level on a few anti-aliased pixels also shows between two runs of the same tree.
Screens from each session are kept in `docs/mobile-ui/screens/<date>/` next to crops of the design frames.

### Every touch check (run against a running preview: `preview.sh <phone|tablet> <port>`)
Each prints PASS / FAIL lines and exits 1 on any FAIL. Run at 412×915, 915×412 (phone) and 800×1280, 1280×800 (tablet).
| Script | What it covers | Extra argument |
|---|---|---|
| `gestures.py` | swipe, pinch, double-tap, long-press drag from the Shelf | |
| `checks.py` | arrow keys, near-tap, Arrange menu, Find under load, Mark rail, AT-06 boxes, tiles, Excel, AT-22 | |
| `boxes.py` | every control class on the main screens ≥ 44 px (and the Excel view) | |
| `pinchmarks.py` | pinch three ways on PDF, Excel, Word; marks under finger and mouse; no stray mark | |
| `turned.py` | Find and Fit on /Rotate pages; Find in Excel and Word; Find bar boxes | a four-turns PDF |
| `closecard.py` | the ask-before-closing card (marks) | any PDF |
| `closework.py` | Bookmarks, Arrange questions; Protect's held redaction; phone Back from /redact | any PDF |
| `pageop.py` | the page-operation question from Arrange, Merge, Split | any PDF |
| `xlresize.py` | Excel resize by finger (hold), scroll and pinch stay theirs | |
| `cards.py` | Export and Press cards, Merge and Split pages | |
| `encpicker.py` | "Read this file as" for text, Markdown, HTML | |
| `encnote.py` | D-205: the encoding on the phone's ⋮ row (value + red note) and the tablet's chip beside the page box; needs H-32 (hooks-17) | |
| `findaside.py` | the Find bar's bottom place with `tools/PixelProof/fixtures/top.pdf` | |
| `signature.py` | the unchecked-signature banner and the Signatures card | a signed PDF |

Traps: run `dotnet workload update` in the repo after `global.json` changes; fetch `+refs/heads/platform/*`;
move a landed hooks patch to `proposal/landed/` before `preview.sh`; the preview keeps tabs, zoom and mode
between runs, so give "before" and "after" hosts the same history.
**Mobile UI hooks are Foundation's to take; Android's `compose.sh` does not apply them (since 9 Nov).**
