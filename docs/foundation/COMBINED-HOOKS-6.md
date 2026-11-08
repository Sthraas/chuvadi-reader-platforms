# Sixth combined patch — on `platform/foundation` (8 Nov)

| Item | From | Where |
|---|---|---|
| Mobile UI's current phone files: PhoneShell (with the **PhoneShell slot** `OpenLabel`/`OpenIcon`/`MenuFooter`, since 1a27cd6), PhoneAppBar, PhoneCommands, PhoneSheetKind, TouchSupport, `mobile.css`, `mobile.js` (incl. `fitWidthZoom` for H-7), preview and tests — taken from `platform/mobile-ui` 2678dd2 (their own files, on top of foundation 4819d66) | Mobile UI | `Components/Platform/Phone/*`, `wwwroot/css/mobile.css`, `wwwroot/js/mobile.js`, `tests/ChuvadiReader.MobileUi.*` |
| **H-5** tabs sheet (D-43) | Mobile UI | `MainLayout.razor` |
| **H-6** Settings on phone (D-45) | Mobile UI | `Settings.razor` |
| **H-7** Redact fit width on a phone | Mobile UI | `Redact.razor` |
| **H-8** bug fix: Reader re-render | Mobile UI | `Reader.Shell.cs`, `Reader.razor` |
| **H-9** bug fix: fit after render (phone "over-wide" page) | Mobile UI | `reader.js` |
| **H-10** Home search under the count line (D-88) | Mobile UI | `Dashboard.razor` |
| **H-11** Settings row summaries on phone (D-88) | Mobile UI | `Settings.razor` |
| **H-12** bug fix: no Phase 0 samples on a fresh install — **widened to every platform except Windows** (D-94: "fresh platform install"; Mac and Linux had the same missing-file samples). One rule, `PhaseZeroSamples.Shown`; Windows unchanged | Mobile UI, widened here | `Core/Documents/PhaseZeroSamples.cs`, `RecentFilesService`, `PinnedAndWatchedServices` |
| **Web UI H5** phone account block at the foot of the ⋮ sheet (through the slot); "Upload" on the portal phone | Web portal UI | `MainLayout.razor` (merged by hand with H-5 on the same PhoneShell line) |
| **Web UI H6** Settings › Account shows the Sangam account on the portal (`PortalAccountRows`) | Web portal UI | `AccountSection.razor`, Portal files from `platform/web-ui` a81a3ab (incl. optional `PortalLinks.PrivacyUrl`) |
| **D-96** first-run tip on Tablet and Phone, keyed on form factor (shell layout), not input: "Tip: tap “Find or do anything” to reach any file or action. Try typing “merge”." — both layouts show that control | Coordinator | `Dashboard.razor`, `PlatformText.TouchFindTip` (was `PhoneFindTip`) |

## Proof
- Windows pixel-identical: 9 screens × 3 scales, before `4819d66` vs after. Rerun results: all identical except the Library's relative-time column ("1m" before vs "2m" after: the before server started a minute earlier — data, not rendering) and the known one-pixel first-shot Reader artefact.
- Phone (412×915), tablet (1280×800) and portal phone: Home, Reader, Bench, Redact, Library, Settings — no page errors, no error bar. First run (`CHVD_EMPTY=1`): tablet and phone show the touch tip and "Open your first document"; the desktop-browser portal keeps "Ctrl K".
- Build: Platforms solution and WPF host with `-warnaserror`, 0 warnings. Tests **273/273** (Reader 171, Hosting 54 incl. 6 new for the sample rule, Mobile UI 16, Web UI 32).
- Startup: Mobile UI measured H-5 to H-11 at +0.4 ms (inside the 7 ms noise floor), desktop Home HTML byte-identical; this patch adds no desktop rendering beyond that.
