# Third combined patch — in progress on `platform/foundation`

Approved 7 Nov 01:00. Each item lands when its input is ready; the same pixel proof runs each time.

| Item | State |
|---|---|
| (b) Web UI's Portal files (decided versions: D-31 promises, D-34 no password — `PortalCredentials` removed, two-argument `PortalLinks` + `PlaceholderDesktopAppUrl`, U-9 `ShowSangamId`, `PortalPhoneAccount` for H5) and their tests | **Applied.** The portal status bar has no nested `sb-item` (checked in the preview: 0; the user item reads "root · Sangam") |
| (d) `ci.yml` and `platform-build.yml`: `actions/checkout@v7`, `actions/setup-dotnet@v6`, `actions/upload-artifact@v7` (Node 24), as on `platform/mac` | **Applied** |
| (a) Web UI H5 phone account block (`docs/web-ui/proposal/web-ui-hooks-3-phone.patch`) | Waiting: needs Mobile UI's PhoneShell slot first (`docs/web-ui/proposal/mobile-ui-request-phoneshell-slot.patch`, not yet on `platform/mobile-ui`) |
| (c) Mobile UI Redact fit-width on phone | Waiting for the Mobile UI chat's diff |

## Proof so far
- Windows pixel-identical: 9 screens × 1/1.25/1.5×, before `2fafb60` vs after — 27/27 identical.
- Web portal preview renders with no errors.
- Build 0 warnings; tests 231/231 (Web UI tests 14 → 16).

## For the Web host
`PortalLinks` now takes two arguments: `new PortalLinks(desktopAppUrl, accountSettingsUrl)` (no "Forgot?" link — D-34).
