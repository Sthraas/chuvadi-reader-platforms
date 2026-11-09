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

## Applied by the Foundation (eleventh/twelfth patches; checked on eb74e52) — Q-3 Home wording on the portal (D-119 c)
`git apply -R --check` succeeds on eb74e52; it renders as below.

**`proposal/web-ui-home-session-wording.patch`**, against foundation **d70590a** (applies cleanly; builds with 0 warnings together with the Upload-wording diff):
- `Components/Platform/PlatformText.cs` (+8): `HomeStorageMapTitle = "Files in this session"` and `HomeShelvesEmpty = "Nothing shelved this session — open the Library"`.
- `Pages/Dashboard.razor` (+2/−2): on the portal (`IsPortal`), the Storage map heading and the empty Library shelf line use these. The desktop text stays in place, unchanged.

Why the shelf line isn't the example wording: "Your shelves for this session are empty — open the Library" wraps to two lines in all three browsers at every size, making the Library card 19 px taller, which is a layout change. The shorter line keeps "this session" and fits on one line, so (c) holds without hiding anything.

Measured (preview; Chromium / Firefox / WebKit; desktop 1280×720, tablet 1024×768 touch, phone 390×844 touch): both lines stay on one line, no block changes size in any of the 9 cases, and Windows shows the same text and is pixel-identical in all three browsers (clock masked). Screenshots: `screenshots/chromium-q3a-home.png`, `screenshots/webkit-q3a-phone-home.png`.

## Applied by the Foundation (eleventh/twelfth patches; checked on eb74e52) — "Upload" in Arrange and Redact on the portal (coordinator 9 Nov 01:42)
`git apply -R --check` succeeds on eb74e52; it renders as below.

**`proposal/web-ui-upload-wording.patch`**, against foundation **839d39d**, and still applies cleanly on **d70590a**. It touches four of the Foundation's files and adds no new injects, because both pages already inject `IPlatformInfo Platform`:
- `Components/Platform/PlatformText.cs` (+6): `FetchOrUpload(platform, desktop, portal)` returns the portal text when `Kind == Web` and the desktop text otherwise (Android included), character for character.
- `Pages/Bench.razor` (+5/−5), `Pages/Bench.Shell.cs` (+1/−1), `Pages/Redact.razor` (+2/−2): every "Fetch" label goes through it, with the desktop text left exactly as it was:

| Where | Desktop / Android (unchanged) | Portal |
|---|---|---|
| Arrange shelf, empty | Fetch a PDF to start. · Fetch a file | Upload a PDF to start. · Upload a file |
| Arrange shelf "Add a file" tooltip | Fetch another PDF onto the shelf | Upload another PDF onto the shelf |
| Arrange Tools rail | Fetch file | Upload file |
| Arrange desk "Image" tooltip | Fetch image | Upload image |
| Arrange command (Ctrl K) | Fetch a file onto the shelf | Upload a file onto the shelf |
| Redact, empty and error states | Fetch a document… | Upload a document… |

Icons are unchanged, since this is a wording change only. Redact's "Redact another file…" has no "Fetch" in it, so I left it.

Proofs (preview; Chromium / Firefox / WebKit; desktop 1280×720, tablet 1024×768 touch, phone 390×844 touch, Windows 1280×720). I scanned every text node, `title` and `aria-label` on `/bench` and `/redact`:
- Portal: no "Fetch" left at any size and nothing overflows. "Upload a PDF to start." stays one line (17 px), the button stays 32 px tall, and the rail label stays inside its 120 px slot.
- Windows: the same strings as without the patch, and pixel-identical screenshots of both pages in all three browsers (clock masked).
- The Ctrl K command label goes through the same helper; I checked it in the source, not on screen.
- Screenshots: `screenshots/chromium-upload-arrange.png`, `screenshots/webkit-upload-phone-redact.png`.

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
