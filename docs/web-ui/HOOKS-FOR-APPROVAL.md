# Web portal UI — existing-file hooks

## Applied by the Foundation (combined patch, D-26, `3358b00`)
H1 account menu in the top bar · H2 "Upload" for Open · H3 signed-in user in the status bar · H4 blue server dot (CSS in `shell.css`, light `#2c3e8c`, dark `#8fa3e6`). The Foundation wrote them in its own form (a MainLayout `IsPortal` property; the user item wrapped in `sb-item` by MainLayout) and proved Windows pixel-identical. Also applied: `IAccount.Unit` and "· Unit" in `AccountMenu` (D-35).

Consequences on my side (this branch):
- `PortalStatusUser` renders only the text (its session-2 form), so MainLayout's `sb-item` wrapper is the only one. The session-1 copy in the combined patch renders its own `sb-item` too — nested spans until this branch lands.
- My `wwwroot/css/portal.css` is dropped: the rule lives in `shell.css`. (Its contrast-theme colour `#1d2b6e` is not carried over; the Foundation's rule leaves contrast on the default blue — fine.)
- The combined patch carries my **session-1** Portal files (password field, old promises, `PortalCredentials`, three-argument `PortalLinks`). This branch replaces them with the decided versions (D-31, D-34, D-35, U-9 a) — see BUILD-LOG session 3 and README "For the Web chat".

## Applied by the Foundation (sixth combined patch, foundation 8098695)
- Mobile UI's PhoneShell slot (1a27cd6), **H5** (phone account block) and **H6** (Settings › Account `PortalAccountRows`). Patches kept in `proposal/` for the record.

## Applied by the Foundation (part 2a, foundation 9fbed93)
- **H7** status-bar wording (D-98) and the **"Drop to open" overlay** (D-104 b) — checked: `git apply -R --check` of both patches succeeds on 9fbed93, and the 12a pitch (D-103) is as sent. Patches kept in `proposal/` for the record.

## Still to apply — "this session" on Home's counts (Q-3, D-119 c)
**`proposal/web-ui-home-session-note.patch`** — against foundation **839d39d** (applies cleanly):
- `Components/Platform/PlatformText.cs` (+3): `HomeSessionNote = " · this session"`.
- `Pages/Dashboard.razor` (+6/−2): on the portal (`Kind == Web`) the Storage map count and the Library shelf count read **"0 pdfs · this session"**. Text only, in the existing spans, so no new line or style. Desktop and Android render nothing extra (the Library shelf's desktop branch, with the folder name, isn't touched).

No layout change, measured (preview; Chromium / Firefox / WebKit; desktop 1280×720, tablet 1024×768 touch, phone 390×844 touch):
- Both headings stay one line (16 px), with no overflow. The longest count is 147 px in Chromium, in a 333–524 px heading.
- The Storage map and Library shelf blocks are the same width and height as without the patch in all 9 cases.
- Windows profile: same text, and the Home screenshot is pixel-identical with and without the patch in all three browsers (clock masked).
- Screenshots: `screenshots/chromium-q3-home-session.png`, `screenshots/webkit-q3-phone-home-session.png`.

## Applied by the Foundation (eighth combined patch part 1, foundation 63f37b1) — Home's drop zone during a drag (U-17 b, D-109)
Checked on 839d39d: `git apply -R --check` succeeds; behaviour as below.

**`proposal/web-ui-home-drop-zone.patch`** — against foundation **9fbed93** (applies cleanly), two of the Foundation's files:
- `wwwroot/js/portal-drop.js` (+4/−2): when the catcher turns `on`, also add `chvd-dragging` to `<html>`; remove it in `off` and in `dispose`.
- `Pages/Dashboard.razor.css` (+3): `html.chvd-dragging .drop > * { visibility: hidden; }` — Home's zone (first-run `.drop.first` and the regular `button.drop`) keeps its frame and size; only its contents hide, so one clean "Drop to open" shows. `visibility`, not `display`, so nothing moves.

The handout's panel is unchanged. Only the portal script sets the class, so desktop and Android are untouched.

Proofs (preview, Web profile; Chromium / Firefox / WebKit, 1280×720; patch applied locally, then reverted):
- PDF drag-enter, both zones (first-run and regular): `<html>` gets the class, zone children `visibility: hidden`, zone frame still `1px dashed`, overlay `display: flex`. Identical in all three browsers.
- Restored (class off, children visible): at rest, after drag-leave, after window blur. Image-only drag: never set.
- Windows profile (5102): a PDF drag never sets the class; Home screenshots with and without the patch are pixel-identical in Firefox and WebKit outside the clock; Chromium differs by a 3×4 px speck that also differs between two runs of the same build (noise).
- No console errors. Screenshots: `screenshots/chromium-u17-home-drag.png`, `screenshots/webkit-u17-home-drag-dark.png` (Night paper).

## Later hooks (not proposed yet)
- `SangamGate` on "Sign with certificate" (desktop) — D-33: deferred until a desktop Sangam client exists.
- Sign-in page: no Ui hook. The Web host renders `PortalSignIn` for signed-out visitors (its own route).
