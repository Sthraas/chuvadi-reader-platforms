# Web portal UI — Chuvadi Reader

Branch `platform/web-ui` in `Sthraas/chuvadi-reader-platforms`. The web portal look (design `docs/design-handoff/Portal & Android.dc.html` 12a–12c, with `Reader Side Rails.dc.html` and `tokens.css`), built as **new components** inside the shared `ChuvadiReader.Ui`. Arun's scope: no per-user storage (no quota, "My files", "autosaved to your storage", storage meter) and no sharing ("Shared with me", "Share a link").

## What is here

| Component (`src/ChuvadiReader.Ui/Components/Platform/Portal/`) | Design | Used by |
|---|---|---|
| `PortalSignIn` — sign-in page: pitch, promises (D-31), "Continue with Sangam", "Download the desktop app"; Sangam ID field (login hint, D-34; no password) off by default (U-9 a) | 12a | The Web host's sign-in route |
| `AccountMenu` — avatar chip + card (name, Sangam ID, Get the desktop app, Account settings, Sign out) | 12b | MainLayout hook H1 |
| `PortalStatusUser` — "Arun S. · Sangam" in the status bar | 12b | MainLayout hook H3 |
| `PortalPhoneAccount` — account block (name, Sangam ID · unit) and server line at the foot of the phone ⋮ sheet | 12b on a phone (D-32, U-10 a) | H5, via Mobile UI's `PhoneShell` `MenuFooter` slot (both proposed) |
| `SangamGate` + `SangamGatingRow` — "Signing needs a Sangam identity" and "What needs Sangam" | 12c | Not hooked yet (see OPTIONS U-3) |
| `PortalLinks` — desktop-app URL (config; placeholder `PortalLinks.PlaceholderDesktopAppUrl`) and Sangam account-page URL (D-35) | — | Registered by the Web host |
| `AccountText` | — | initials / first name helper |

The Upload button (12b left bar) is hook H2; the status text is the Foundation's (inline in MainLayout).

All colours are theme tokens (`--chvd-*`), so the five themes apply; Night paper also re-tints the sign-in fields.

## For the Web chat (integration contract)
Register in the Web host, after `AddChuvadiReader(AppStateLifetime.PerConnection)`:
```csharp
services.AddScoped<IAccount, YourSangamAccount>();   // ChuvadiReader.Platform.IAccount: DisplayName, Email (Sangam ID), SignOutAsync, Changed
services.AddSingleton(new PortalLinks(
    DesktopAppUrl: configuration["Portal:DesktopAppUrl"] ?? PortalLinks.PlaceholderDesktopAppUrl,   // two arguments: no ForgotPasswordUrl (D-34, OPTIONS U-12)
    AccountSettingsUrl: "<Sangam's account page, or null to hide the item>",
    TermsUrl: "<where you serve the Foundation's EULA, e.g. /terms — optional; null hides the line>"));
```
Sign-in page (your route, for signed-out visitors — the Ui router is never shown before sign-in):
```razor
<PortalSignIn OnContinueWithSangam="StartSangamRedirect"
              Busy="_busy" Error="_error" />
```
The Sangam ID field is off (U-9 a): Sangam rc.16 does not pre-fill `login_hint`. If Arun agrees the Sangam change (U-9 c), add `ShowSangamId="true" OnSubmitId="(string id) => StartSangamRedirect(loginHint: id)"` — `OnSubmitId` gets the ID exactly as typed. No password is ever entered on our page (D-34; Sangam has no password grant).

`IAccount.Unit` (organisation, from Sangam's `sangam_org`) shows as "· Records" after the Sangam ID in the account card and the phone block.

Host page: link, after the Ui's `tokens.css`, `app.css`, `shell.css`, `prefs.css` — `_content/ChuvadiReader.Ui/css/mobile.css` (Mobile UI, D-32), then your `<Assembly>.styles.css` bundle. (The blue server dot is in `shell.css`; there is no portal stylesheet.) The sign-in page needs the same sheets plus `fonts/google/fonts.css` and `lipi-sans/lipi-sans.css`.

Several files uploaded at once: one `OpenDocumentService.Request` per file is fine since the Foundation's F-3 fix (second combined patch, D-66).

## Build and test
Requires .NET SDK 10.0.403+. Based on `platform/foundation` (2fafb60 — second combined patch — at session 4).
```bash
dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config
dotnet build   ChuvadiReader.Platforms.slnx -c Release --no-restore -warnaserror
dotnet test    ChuvadiReader.Platforms.slnx -c Release --no-build
```
Expected: 0 warnings; all test projects pass (session 4: see BUILD-LOG).

## Preview host (dev only, never shipped)
`tools/ChuvadiReader.WebUi.Preview` — Blazor Server (Kestrel) running the real Ui with a fake signed-in Sangam account. `PREVIEW_PLATFORM=web|windows|macos|linux`, `PREVIEW_FORMFACTOR=desktop|tablet|phone` (web).
```bash
git apply docs/web-ui/proposal/mobile-ui-request-phoneshell-slot.patch docs/web-ui/proposal/web-ui-hooks-3-phone.patch   # phone account block; revert before committing
DOTNET_ROOT=<sdk dir> tools/ChuvadiReader.WebUi.Preview/test/serve.sh
#   portal desktop :5101 · Windows :5102 · portal tablet :5103 · portal phone :5104
```
Pages: `/_preview/sign-in` (`?error=…&busy=true&id=true` to show the U-9 ID field), `/_preview/gate`, `/_preview/open?path=/abs/file.pdf` (one file), plus every Ui route. Tablet and phone use Mobile UI's `mobile.css`/`PhoneShell` (on `platform/foundation` since the combined patch); the phone account block needs the two patches above.

## Screenshot tests (external tools, testing only)
Python 3 + Playwright (Chromium, Firefox, WebKit) + Pillow, in a throwaway venv; never part of the build.
```bash
python3 tools/ChuvadiReader.WebUi.Preview/test/mkpdf.py $WEBUI_TEST_DIR/docs/discharge-summary.pdf 13
python3 tools/ChuvadiReader.WebUi.Preview/test/mkpdf.py $WEBUI_TEST_DIR/docs/lab-report.pdf 2
python  tools/ChuvadiReader.WebUi.Preview/test/shots.py handout chromium firefox webkit   # handout frames + portal: desktop 1280×720, tablet 1280×800 (touch), phone 390×844 (touch)
python  tools/ChuvadiReader.WebUi.Preview/test/desk.py before|after                       # Windows-platform screenshots for the before/after check
```
Reference shots are in `docs/web-ui/screenshots/` (handout frames 12a–12c beside the built pages).

## Status and open items
See `BUILD-LOG.md` (latest entry) and `OPTIONS-FOR-COORDINATOR.md`.
