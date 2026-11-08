# Web portal UI — existing-file hooks

## Applied by the Foundation (combined patch, D-26, `3358b00`)
H1 account menu in the top bar · H2 "Upload" for Open · H3 signed-in user in the status bar · H4 blue server dot (CSS in `shell.css`, light `#2c3e8c`, dark `#8fa3e6`). The Foundation wrote them in its own form (a MainLayout `IsPortal` property; the user item wrapped in `sb-item` by MainLayout) and proved Windows pixel-identical. Also applied: `IAccount.Unit` and "· Unit" in `AccountMenu` (D-35).

Consequences on my side (this branch):
- `PortalStatusUser` renders only the text (its session-2 form), so MainLayout's `sb-item` wrapper is the only one. The session-1 copy in the combined patch renders its own `sb-item` too — nested spans until this branch lands.
- My `wwwroot/css/portal.css` is dropped: the rule lives in `shell.css`. (Its contrast-theme colour `#1d2b6e` is not carried over; the Foundation's rule leaves contrast on the default blue — fine.)
- The combined patch carries my **session-1** Portal files (password field, old promises, `PortalCredentials`, three-argument `PortalLinks`). This branch replaces them with the decided versions (D-31, D-34, D-35, U-9 a) — see BUILD-LOG session 3 and README "For the Web chat".

## Applied by the Foundation (sixth combined patch, foundation 8098695)
- Mobile UI's PhoneShell slot (1a27cd6), **H5** (phone account block) and **H6** (Settings › Account `PortalAccountRows`). Patches kept in `proposal/` for the record.

## Still to apply — H7: status-bar wording (D-98)
**`proposal/web-ui-hooks-7-status-text.patch`** — `Layout/MainLayout.razor`, one line, text only: "processed on the server · **encrypted at rest** · only you can see it" → "processed on the server · **kept in memory only** · only you can see it". Styling untouched (same span, dot and classes). Desktop branch ("offline · on this device") unchanged, so Windows is unaffected. Applies cleanly to foundation 8098695.
The same line in the phone account block (`PortalPhoneAccount`, my file) is already changed on this branch.

## Still to apply — "Drop to open" on the portal (D-104 b)
**`proposal/web-ui-drop-overlay.patch`** — the Foundation's `Components/Platform/Portal/PortalDropCatcher.razor` (+6/−3) and `.razor.css` (+16/−1), against foundation **f6607a3** (applies cleanly). Adds the handout's Walkthrough "Drop to open" panel inside the catcher, shown only while the catcher is `on` (documents dragged over the window); no file-name line (browsers don't expose names during a drag). No script or logic change.

Proofs (preview host, Web profile with a fake `IDroppedFiles`; Chromium / Firefox / WebKit, 1280×720):
- Computed style while dragging a PDF, identical in all three: `border: 2px dashed rgb(138, 58, 28)`, radius 14 px, background rgb(251, 247, 236) at 0.55, inset 24 px (left/top 24), title "Instrument Serif" 28 px — the handout's values. Night paper: border `#e08a52` (theme tokens).
- Shown: on a PDF drag-enter. Hidden: at rest, for an image-only drag (left to the Reader), after drag-leave, after window blur.
- The element under the panel's centre while dragging is the catcher's `INPUT type=file` in all three browsers — the panel (`pointer-events: none`) never takes the drop.
- No console errors. Windows profile: server-rendered markup of `/`, `/library`, `/settings` identical with and without the patch (the catcher is never rendered on desktop or Android).
- Screenshots: `screenshots/handout-drop.png` (the handout frame), `chromium-drop-over.png`, `webkit-drop-over-dark.png`.
- Open point: U-17 (Home's own drop zone shows through the panel).

## Later hooks (not proposed yet)
- `SangamGate` on "Sign with certificate" (desktop) — D-33: deferred until a desktop Sangam client exists.
- Sign-in page: no Ui hook. The Web host renders `PortalSignIn` for signed-out visitors (its own route).
