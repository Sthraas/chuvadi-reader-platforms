# Web portal UI — existing-file hooks

## Still to apply — the encoding picker's rows are finger-sized on tablet and phone (found 16 Nov, checking patch 31 / D-191)
**`proposal/web-ui-encoding-rows-finger-size.patch`**, against foundation-pr **b895750** (applies cleanly). One file, `Ui/wwwroot/css/shell.css`, 2 lines added after the `.enc-*` rules:
`html[data-shell="tablet"] .enc-row, html[data-shell="phone"] .enc-row { min-height: 44px; }`, the same pattern as AT-25 and AT-26 in patch 31.

Why: the five rows of "Read this file as" are 34 px tall on every profile. On the tablet and the phone they are worked by a finger, where the app's other rows are 44 px (`.pop-item`, the phone's tools) to 48 px.

Measured (Chromium / Firefox / WebKit; the same in all three): rows 34 → **44 px** on portal tablet and portal phone; **34 px, unchanged**, on portal desktop and the Windows profile; the card stays inside the screen (phone: 410–764 of 844 px). Screenshot: `screenshots/webkit-encoding-rows-finger-phone.png`.

## Applied by the Foundation (patch 31, commit 6f7790e, with AT-26's finger-sized buttons; checked on b895750) — the ask-before-closing card keeps the keyboard inside it (D-190)
The two focus stops and `FocusCloseAskAsync` are in as sent. Checked on b895750: Tab goes Save › Save as… › Discard › Cancel › Save, Shift Tab the other way, and Esc cancels, in three browsers on the portal and Windows profiles.

**`proposal/web-ui-close-card-keeps-focus.patch`**, against foundation **7c0b4bc** (= foundation-pr 71754e1 for `src`; applies cleanly, alone and with the two diffs below). Two files, 14 lines added and 1 removed:
- `Ui/Layout/MainLayout.razor`: two focus stops (`<span class="closeq-edge" tabindex="0" aria-hidden="true">`), one before the first button and one after Cancel. The first sends focus to Cancel, the second to the first button (`FocusCloseAskAsync`); Cancel gets a `@ref`.
- `Ui/wwwroot/css/shell.css`: `.closeq-edge` has no size and no outline.

What it cures (patch 29 as merged; the same in Chromium and WebKit, on the portal and Windows profiles; in headless Firefox the focus leaves the page):
- Tab from Cancel goes to the page behind the scrim (first the body, then the brand button; on a phone the Back button). Shift Tab from Save goes to a rail button behind ("More view options").
- With the focus out there, **Esc no longer cancels** (the key handler is on the card), and **Enter works the control behind**: on the brand button the app goes to Home with the question still open on top.
- Nothing is lost (the card stays and still needs its answer), but a modal question should hold the keyboard.

With the patch (three browsers, portal and Windows profiles): Tab goes Save › Save as… › Discard › Cancel › Save › …; Shift Tab goes Save › Cancel › Discard › Save as… › Save; Esc cancels from anywhere in that cycle and the tab stays. Build `-warnaserror` 0 warnings; 593 tests pass with this and the two diffs below applied together.

## Applied by the Foundation (patch 30, commit 188d986; checked on 6d80aa3) — the rail word for "Sign with certificate" on the portal: "soon", not "off"
In exactly as sent (`git apply -R --check` succeeds). Checked on 6d80aa3: "soon" in the Reader's Protect rail and Redact's Tools rail in three browsers, inside the rail; all 12 certificate cases as D-187 says.

**`proposal/web-ui-portal-certificate-rail-word.patch`**, against foundation **754d1e2**; it still applies cleanly to **7c0b4bc** (patch 29), where I re-checked it: the word reads "soon" in three browsers. Four files, 3 lines added and 11 removed. Routed to the Foundation by the coordinator, 16 Nov 14:33.

Why it is needed: patch 28 (commit 7b3e1af, 15 Nov 19:00 UTC = 16 Nov 00:30 IST) applied the **first** version of my certificate diff, in which a greyed "Sign with certificate" shows the word "off". The coordinator's decision at 00:40 was to use the word every other unavailable rail item on the portal uses, which is "soon". My updated diff was pushed after the Foundation had applied the first one. This follow-up brings the code to the updated version:
- `Ui/Components/Rails/RailButton.razor`: the `DisabledTag` parameter goes; a greyed button shows "soon", as before patch 28.
- `Ui/Components/Platform/PlatformText.cs`: `CertificateSigningTag` goes.
- `Ui/Pages/Reader.razor`, `Ui/Pages/Redact.razor`: the two buttons no longer pass `DisabledTag`.

Nothing else changes: the sentence, the greyed state, the tap on touch and the card are as in patch 28.

Proofs: with the patch, "Sign with certificate" shows "soon" in the Reader's Protect rail and Redact's Tools rail in Chromium, Firefox and WebKit, ending at x 1204 inside the rail's 1218. Build `-warnaserror` 0 warnings; 539 tests pass (no guard test names the word). Screenshot: `screenshots/chromium-u18-rail-hover.png`.

## Applied by the Foundation (patch 30, commit b5ffad5, placed by hand; checked on 6d80aa3) — the hidden-matches line under the sheet instead of above it (U-20 a, D-192)
The same change as sent (the block just above the sheet tabs, the border on its top edge); not byte-identical because the Foundation placed it by hand around the resize code. Checked on 6d80aa3: 0% of the sentence covered at 1280, 1920, tablet and phone sizes in three browsers; the right words in 9 of 9 cases, shown only when a match is in a hidden row or column.

**`proposal/web-ui-xlsx-hidden-matches-under-sheet.patch`**, **regenerated 16 Nov against foundation 7c0b4bc (patch 29)**: the version written against 754d1e2 no longer applied, because patch 29 changed the lines around it for the resize. The change itself is the same. Two files, 9 lines added and 6 removed. Re-measured on patch 29: 0% of the sentence covered at 1280, 1920, tablet and phone sizes in three browsers.
- `Ui/Components/Viewers/XlsxView.razor`: the `xv-hiddenhits` block moves from above the value bar to just above the sheet tabs.
- `Ui/Components/Viewers/XlsxView.razor.css`: its border goes on the top edge instead of the bottom.

What it cures: the Find box (`.rfind`, `position: absolute; top: 12px`, centred) floats over the top of the viewer, where patch 28 puts the line. Share of the sentence's text covered by the Find box (`layout.xlsx`, Find "hidden"; measured from the text's own rectangles):

| Size | Patch 28 (line above the sheet) | With this patch (line under the sheet) |
|---|---|---|
| Desktop 1280×720 | 10% ("C6 (hid…" is cut) | 0% |
| Desktop 1920×1080 | 0% | 0% |
| Tablet 1024×768 | 18–20% | 0% |
| Phone 390×844 | 43–48% (only "2 mat" and "colu" can be read) | 0% |

The same in Chromium, Firefox and WebKit. Screenshots: `screenshots/webkit-u19-line-under-find-box.png` (patch 28), `screenshots/webkit-u19-line-under-sheet.png` (with this patch).

## Applied by the Foundation (patch 28, commit 7b3e1af; checked on 754d1e2) — "Sign with certificate" off on the portal, greyed with its reason (U-18 b, D-187)
**As the first version sent (rail word "off"); see the follow-up above.** Checked in the portal on 754d1e2: 12 of 12 cases behave as D-187 says (three browsers × portal desktop, tablet, phone and the Windows profile). The text below describes the updated version of the diff.

**`proposal/web-ui-portal-certificate-off.patch`**, against foundation **7fd806f** (patch 27; applies cleanly; independent of the Find-focus patch below, and the two apply together). Nine files, 39 lines added and 6 removed. **Updated 16 Nov 00:40**: the rail word is the existing "soon", so `RailButton` no longer gets a word parameter.

| File | Change |
|---|---|
| `Ui/Components/Platform/PlatformText.cs` | The sentence (`CertificateSigningOnPortal`), `CertificateSigningOff(platform)` (the sentence on Web, null elsewhere) and `ReasonOnTap(platform)` (true where `Input` has Touch) |
| `Ui/Components/Rails/RailButton.razor` | One optional parameter, `ReasonOnTap`: with a `DisabledReason`, the button is not `disabled` but gets class `off` and `aria-disabled="true"`, so it looks greyed and still runs `OnClick`. The default leaves every existing button as it is |
| `Ui/wwwroot/css/shell.css` | `.rb.off { opacity: 0.38; }`, the same grey as `.rb:disabled` |
| `Ui/Pages/Reader.razor` | Protect rail's button gets `DisabledReason` and `ReasonOnTap`. The "cert" card: where signing is off it shows the sentence in place of the certificate, password, reason, location and Save controls |
| `Ui/Pages/Redact.razor` | Tools rail's button gets the same two parameters |
| `Ui/Pages/Reader.Shell.cs` | Command `p.cert` (Ctrl K, phone Protect strip): greyed with the reason; on a touch screen it runs and is marked `Dimmed` |
| `Core/Reader/ShellService.cs` | `ShellCommand.Dimmed` (init-only, default false): shown greyed although it runs |
| `Ui/Components/Platform/Phone/PhoneToolStrip.razor`, `Ui/wwwroot/css/mobile.css` | A `Dimmed` command's tool gets class `dim`; `.ph-tool.dim { opacity: .38; }` |

Rail word (coordinator 16 Nov 00:40: use what other unavailable rail items on the portal already use): every greyed rail item on the portal has the same state and word. It is `disabled`, with the reason in the tooltip and "soon" where the shortcut would be: Highlight, Note and Fill form ("Coming soon"), and on Office files Print ("Convert to PDF first") and Convert to PDF ("Coming with the Layout library"). The same on the Windows profile. So "Sign with certificate" shows **"soon"** too. It fits: it ends at x 1204 of the rail's 1218 in all three browsers.

Proofs (preview; Chromium / Firefox / WebKit; the same in all three):

| Profile | Button | On click or tap |
|---|---|---|
| Portal, desktop 1280×720, mouse | Reader Protect rail and Redact Tools rail: `disabled`, opacity 0.38, tooltip "Sign with certificate — Certificate signing is in the desktop app. Your private key never leaves your computer.", word "soon" | Nothing (disabled) |
| Portal, tablet 1024×768, touch | Both rails: not disabled, class `off`, `aria-disabled="true"`, opacity 0.38 | The card opens with the sentence; no "Choose certificate", no password box, no "Save signed copy" |
| Portal, phone 390×844, touch | Protect strip "Sign": not disabled, class `dim`, opacity 0.38 | The card opens with the sentence; no fields |
| Windows 1280×720 | Enabled, opacity 1, no word | The full card, as before |

Re-run on the final patch over foundation 7fd806f: 12 of 12 cases as decided (three browsers × the four profiles above). Windows profile pixel check and the portal sweep: see the build log, sessions 22 and 23. Screenshots: `screenshots/chromium-u18-rail-hover.png`, `screenshots/webkit-u18-tablet-card.png`, `screenshots/webkit-u18-phone-card.png`.

Not changed: the placed-signature card's note "For a certificate signature use Protect › Sign with certificate" still reads true (the button is there, with its reason). The Web host's `AllowCertificateUpload` stays as it is (off).

## Applied by the Foundation (patch 28; checked on 754d1e2) — the Find box in Word, Excel, Markdown and text files takes the cursor (coordinator 15 Nov, D-187)
In exactly as sent (`git apply -R --check` succeeds). With the Foundation's own Ctrl F change (63828b8) the key now opens the viewers' Find too. Checked on 754d1e2: 54 of 54 cases focus the box, and for Excel and Word typing without a click finds "4 found" / "1 found" (three browsers; left bar Find, Ctrl F, phone ⋮ › Find; portal desktop, tablet, phone and the Windows profile).

**`proposal/web-ui-office-find-focus.patch`**, against foundation **7fd806f** (applies cleanly; unchanged since 15 Nov). Two files, 12 lines added:
- `Ui/Pages/Reader.razor`: the viewers' Find box gets `@ref="_viewerFindBoxRef"`; `OnAfterRenderAsync` focuses it once after the render that draws it (`_focusViewerFind`), the same call the PDF Find box gets in `OpenFind`.
- `Ui/Pages/Reader.Shell.cs`: `OpenViewerFind` sets `_focusViewerFind`.

Proofs (preview; Chromium / Firefox / WebKit; the same in all three). "Focus" is `document.activeElement` 0.9 s after opening Find; then the query is typed **without clicking the box**:

| Profile | How Find is opened | Excel (`layout.xlsx`) | Word (`discharge.docx`) | PDF |
|---|---|---|---|---|
| Portal desktop | Left bar Find | box focused; "hidden" + Enter → "4 found" | box focused; "discharge" → "1 found" | box focused (as before) |
| Portal tablet (touch) | Left bar Find, tapped | focused; "4 found" | focused; "1 found" | focused |
| Portal phone (touch) | ⋮ › Find, tapped | focused; "4 found" | focused; "1 found" | focused |
| Windows | Left bar Find | focused; "4 found" | focused; "1 found" | focused |

Before the patch the focus stayed on the Find button (or the page) in every Office case.

**What I could not prove here:** that a real phone raises its keyboard. The box does take focus under touch emulation, and Android Chrome shows the keyboard on a focus like this. iOS Safari only does so when the focus happens inside the tap itself; on the portal (Blazor Server) the focus arrives one round trip later, exactly as it does for the PDF Find box today. This needs a look on a real iPhone (Web Test or Mobile Test). If iOS doesn't raise it, the PDF box has the same gap and the cure is the same for both: focus from a small script in the tap handler.

## Applied by the Foundation (patch 26; checked on 37bd4a0) — the Word "left out" note is wider than the page on tablet and phone (D-168)
In exactly as sent (`git apply -R --check` succeeds). Re-measured on 37bd4a0: the note and the page share the same edges at desktop, tablet and phone sizes in all three browsers.

**`proposal/web-ui-docx-leftout-margins.patch`**, against foundation **382aada** (= foundation-pr 742a5da for `src`; applies cleanly). One of the Foundation's files, `Components/Viewers/DocxView.razor.css`, one rule:
`.dv-leftout { max-width: 794px; … }` → `max-width: min(794px, calc(100% - 48px));`. The sheet is `width: 794px; max-width: calc(100% - 48px)`, so on a narrow stage the note was wider than the page. The colours and text are untouched.

Measured (preview, `leftout-header.docx` = the tests' damaged-header copy of `discharge.docx`; left–right edges in px, the same in Chromium, Firefox and WebKit unless noted):

| Size | Page | Note without the patch | Note with the patch |
|---|---|---|---|
| Desktop 1280 (Web and Windows profiles) | 288–1082 (WebKit 283–1077) | same as the page | same as the page (unchanged) |
| Tablet 1024 touch | 96–868 | 85–879 (11 px wider each side) | 96–868 |
| Phone 390 touch | 24–366 | 0–390 (edge to edge) | 24–366 |

Screenshots: `screenshots/chromium-docx-leftout-phone-before-after.png`, `screenshots/chromium-docx-leftout-desktop.png`. Not a portal-only matter: Android phones and tablets get the same rule.

## Applied by the Foundation (patch 26, reconciled with Mobile UI H-23; checked on 37bd4a0) — the Excel value bar often never turned on in the portal (D-161)
The retry is in `XlsxView.OnAfterRenderAsync` (`JsAsync<bool>("gridValueBar")`, guarded by `_version`). Re-measured on 37bd4a0: the bar shows on the first click in 12 of 12 opens in each of Chromium, Firefox and WebKit (Web profile) and 3 of 3 in each on the Windows profile. It was 4 of 10, then 6 of 18.

**`proposal/web-ui-xlsx-value-bar-race.patch`**, against foundation **ec09f4f** (= foundation-pr dd59362 for `src`; applies cleanly). Two of the Foundation's files, 12 lines added and 4 removed:
- `Components/Viewers/XlsxView.razor`: `OnAfterRenderAsync` set `_valueBarOn = true` before calling the script. That call can belong to a render from before the grid was drawn: the workbook finishes loading while the "busy" render is on its way to the browser, which is the normal case on Blazor Server. The script then finds no grid and does nothing, and it is never asked again. Now the flag is set only when the script says the listener is on (`JsAsync<bool>`), and only if no reload happened meanwhile (`_version`).
- `wwwroot/js/viewers.js` `gridValueBar`: returns `true` when the listener is on (already or newly) and `false` when the grid isn't connected or the bar isn't there. The behaviour is otherwise unchanged.

Measured in the preview (Web profile, 1280×720; open `formats.xlsx` / `realistic.xlsx`, wait 2.5 s, click the first cell):
- Without the patch: the listener is on, and the bar shows on click, in **4 of 10** opens in each of Chromium, Firefox and WebKit.
- With the patch: **10 of 10** in each. Windows profile with the patch: 4 of 4 in each.
- With the patch, at desktop, tablet and phone sizes in all three browsers: a 26 px bar in LiPi Sans 12 px, showing the address and the stored value (B2: shown 3.141592654, stored 3.14159265358979). The page never scrolls sideways, the selected cell is outlined in the binding colour, and there are no console errors.
- Screenshots: `screenshots/webkit-xlsx-value-bar.png`, `screenshots/webkit-xlsx-value-bar-phone.png`.

Not part of this diff, already recorded by the Foundation as library item **SH-L1** (Sheets 2.0.4): time-only cells show "########" and the value bar shows -0.25 where the file holds 0.75. It is visible in the portal on `formats.xlsx` B18, B19, B38 and B44.

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
