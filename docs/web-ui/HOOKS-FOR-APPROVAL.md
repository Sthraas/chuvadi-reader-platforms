# Web portal UI — existing-file hooks

## Applied by the Foundation (combined patch, D-26, `3358b00`)
H1 account menu in the top bar · H2 "Upload" for Open · H3 signed-in user in the status bar · H4 blue server dot (CSS in `shell.css`, light `#2c3e8c`, dark `#8fa3e6`). The Foundation wrote them in its own form (a MainLayout `IsPortal` property; the user item wrapped in `sb-item` by MainLayout) and proved Windows pixel-identical. Also applied: `IAccount.Unit` and "· Unit" in `AccountMenu` (D-35).

Consequences on my side (this branch):
- `PortalStatusUser` renders only the text (its session-2 form), so MainLayout's `sb-item` wrapper is the only one. The session-1 copy in the combined patch renders its own `sb-item` too — nested spans until this branch lands.
- My `wwwroot/css/portal.css` is dropped: the rule lives in `shell.css`. (Its contrast-theme colour `#1d2b6e` is not carried over; the Foundation's rule leaves contrast on the default blue — fine.)
- The combined patch carries my **session-1** Portal files (password field, old promises, `PortalCredentials`, three-argument `PortalLinks`). This branch replaces them with the decided versions (D-31, D-34, D-35, U-9 a) — see BUILD-LOG session 3 and README "For the Web chat".

## Still to apply — the portal on a phone: H5 (D-32, U-10 a; approved D-75 for the Foundation's next combined patch)
- **Slot: done by Mobile UI** on `platform/mobile-ui` 1a27cd6 — `OpenLabel`, `OpenIcon`, `RenderFragment<EventCallback>? MenuFooter` invoked with `EventCallback.Factory.Create(this, Close)`, exactly as requested (they also use `OpenLabel` on the phone Home FAB). My request patch is removed.
- **H5: `proposal/web-ui-hooks-3-phone.patch`** (MainLayout, +12/−1), applies to `platform/foundation` a4acc56: the PhoneShell tag gets `OpenLabel`/`OpenIcon` from the existing `IsPortal`, and `MenuFooter="@(Platform.Chrome.AccountMenu ? PortalMenuFooter : null)"`; one static `RenderFragment<EventCallback>` renders `PortalPhoneAccount` with `OnDone = close`.

Verified (session 5) with foundation a4acc56 + Mobile UI's Phone files from 1a27cd6 + H5, all local: build `-warnaserror` 0 warnings; Chromium/Firefox/WebKit at phone 390×844 (touch): no console errors; the ⋮ sheet on a document view and on Library shows Upload and the account block; a row closes the sheet. Windows: PhoneShell is not rendered; the static field is one delegate per process.

Order: Mobile UI's slot must be on `platform/foundation` before H5 (H5 does not compile without it).

## Proposed, waiting for a decision
- U-14 (a): `PortalAccountCard` in Settings › Account on the portal (OPTIONS U-14). Not built until decided.

## Later hooks (not proposed yet)
- `SangamGate` on "Sign with certificate" (desktop) — D-33: deferred until a desktop Sangam client exists.
- Sign-in page: no Ui hook. The Web host renders `PortalSignIn` for signed-out visitors (its own route).
