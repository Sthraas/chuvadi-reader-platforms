# Third combined patch — in progress on `platform/foundation`

Approved 7 Nov 01:00. Each item lands when its input is ready; the same pixel proof runs each time.

| Item | State |
|---|---|
| (b) Web UI's Portal files (decided versions: D-31 promises, D-34 no password — `PortalCredentials` removed, two-argument `PortalLinks` + `PlaceholderDesktopAppUrl`, U-9 `ShowSangamId`, `PortalPhoneAccount` for H5) and their tests | **Applied.** The portal status bar has no nested `sb-item` (checked in the preview: 0; the user item reads "root · Sangam") |
| (1) Web UI's latest sign-in page and `PortalLinks` (`f4e20d9`: optional `TermsUrl`, two-argument construction still works) and its tests; the preview and tests updated | **Applied** (part 2) |
| (2) **Licences page:** About › Help › Licences › Open shows the licence agreement, the licence and the third-party notices (one segmented view, "‹ About" back). The same page lives at `/licence` (`?part=notices`) for links from outside the shell, e.g. the portal's "Terms of use" (`PortalLinks.TermsUrl = "/licence"`). Texts are embedded from `LICENSE` and `legal/` (one source; read only when the page opens); a test checks they match the shipped files | **Applied** (part 2). Every host gets it with no host code |
| (3) Home drop zone on the portal and mobile | Options in `DROP-ZONE-OPTIONS.md`; waiting for a decision |
| (d) `ci.yml` and `platform-build.yml`: `actions/checkout@v7`, `actions/setup-dotnet@v6`, `actions/upload-artifact@v7` (Node 24), as on `platform/mac` | **Applied** |
| (a) Web UI H5 phone account block (`docs/web-ui/proposal/web-ui-hooks-3-phone.patch`) | Waiting: needs Mobile UI's PhoneShell slot first (`docs/web-ui/proposal/mobile-ui-request-phoneshell-slot.patch`, not yet on `platform/mobile-ui`) |
| (c) Mobile UI Redact fit-width on phone | Waiting for the Mobile UI chat's diff |

## Proof so far
- Windows pixel-identical: 9 screens × 1/1.25/1.5×, before `2fafb60` vs after — 27/27 identical.
- Web portal preview renders with no errors.
- Build 0 warnings; tests 231/231 (Web UI tests 14 → 16).

## Proof, part 2
- Windows: 9 screens × 3 scales — 24/27 identical; the 3 differences are Settings › About, all in the Licences row (hint "Licence agreement and third-party notices", Open now enabled) — the approved change. One Reader 1× difference (17 px, top bar) was a timing flake: three reruns identical.
- Licences page checked on desktop, phone and the portal (`/licence`); no errors.
- My two drafts (`LICENSE`, `legal/EULA.txt`) are now stored one line per paragraph so they wrap to any width; the words are unchanged (checked). The third-party licence texts stay verbatim.
- Build 0 warnings; tests 234/234.

## For the Web host
`PortalLinks` takes `(desktopAppUrl, accountSettingsUrl, termsUrl = null)` (no "Forgot?" link — D-34). Set `termsUrl` to `"/licence"` and allow that route before sign-in.
