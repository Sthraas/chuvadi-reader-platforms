# Web portal UI — existing-file hooks

## Applied by the Foundation (combined patch, D-26, `3358b00`)
H1 account menu in the top bar · H2 "Upload" for Open · H3 signed-in user in the status bar · H4 blue server dot (CSS in `shell.css`, light `#2c3e8c`, dark `#8fa3e6`). The Foundation wrote them in its own form (a MainLayout `IsPortal` property; the user item wrapped in `sb-item` by MainLayout) and proved Windows pixel-identical. Also applied: `IAccount.Unit` and "· Unit" in `AccountMenu` (D-35).

Consequences on my side (this branch):
- `PortalStatusUser` renders only the text (its session-2 form), so MainLayout's `sb-item` wrapper is the only one. The session-1 copy in the combined patch renders its own `sb-item` too — nested spans until this branch lands.
- My `wwwroot/css/portal.css` is dropped: the rule lives in `shell.css`. (Its contrast-theme colour `#1d2b6e` is not carried over; the Foundation's rule leaves contrast on the default blue — fine.)
- The combined patch carries my **session-1** Portal files (password field, old promises, `PortalCredentials`, three-argument `PortalLinks`). This branch replaces them with the decided versions (D-31, D-34, D-35, U-9 a) — see BUILD-LOG session 3 and README "For the Web chat".

## Still to apply — the portal on a phone: H5 (D-32, U-10 a; approved D-75 for the Foundation's next combined patch)
> **Status 7 Nov 04:55:** COMBINED-HOOKS-3 lists H5 as waiting for Mobile UI's slot "not yet on `platform/mobile-ui`" — that is out of date: the slot is on `platform/mobile-ui` since **1a27cd6** ("… Web portal PhoneShell slot") and still on its head 74c3fd6 (`PhoneShell.razor:124` and `:178`). H5 applies cleanly to foundation **fa9d120** (`git apply --check`). The Foundation can take the slot from Mobile UI's branch and then H5.
- **Slot: done by Mobile UI** on `platform/mobile-ui` 1a27cd6 — `OpenLabel`, `OpenIcon`, `RenderFragment<EventCallback>? MenuFooter` invoked with `EventCallback.Factory.Create(this, Close)`, exactly as requested (they also use `OpenLabel` on the phone Home FAB). My request patch is removed.
- **H5: `proposal/web-ui-hooks-3-phone.patch`** (MainLayout, +12/−1), applies to `platform/foundation` a4acc56: the PhoneShell tag gets `OpenLabel`/`OpenIcon` from the existing `IsPortal`, and `MenuFooter="@(Platform.Chrome.AccountMenu ? PortalMenuFooter : null)"`; one static `RenderFragment<EventCallback>` renders `PortalPhoneAccount` with `OnDone = close`.

Verified (session 5) with foundation a4acc56 + Mobile UI's Phone files from 1a27cd6 + H5, all local: build `-warnaserror` 0 warnings; Chromium/Firefox/WebKit at phone 390×844 (touch): no console errors; the ⋮ sheet on a document view and on Library shows Upload and the account block; a row closes the sheet. Windows: PhoneShell is not rendered; the static field is one delegate per process.

Order: Mobile UI's slot must be on `platform/foundation` before H5 (H5 does not compile without it).

## Still to apply — Settings › Account on the portal: H6 (U-14 a, approved 7 Nov)
> **Status 7 Nov 04:55:** not in COMBINED-HOOKS-3 or -4 (foundation fa9d120 has no `PortalAccountRows` and `AccountSection` is unchanged). **Resent against fa9d120:** `PortalAccountRows.razor`(+css) on this branch, and the same patch, which applies cleanly to fa9d120 (`git apply --check`); re-verified there (see BUILD-LOG session 7).
**`proposal/web-ui-hooks-4-account.patch`** — `Components/Settings/AccountSection.razor`, +10/−0, against `platform/foundation` 615afde (still applies to fa9d120): `@inject IPlatformInfo Platform`; inside the "Signed in" card, `@if (Platform.Chrome.AccountMenu) { <PortalAccountRows /> } else { …the two existing rows… }`. Role, Sign-in method, Lock after idle, Roles and Audit trail are untouched.

`PortalAccountRows` (mine, new): name with "Sangam ID · Unit" as the hint and a "Sangam" chip; "Account settings" → Sangam's page in a **new tab** (a link styled like `RowButton`: leaving the portal tab would end the session and its working copies, and a script-opened tab after a server round trip is popup-blocked); "Sign out" (hint "Your working copies are removed from the server") → `IAccount.SignOutAsync`.

Verified (local, Web profile): Chromium / Firefox / WebKit × portal desktop 1280×800, tablet 1280×800 (touch), phone 390×844 (touch): no "Not signed in", shows "arun.s@smh.sangam · Records", Sign out present and signs out; no console errors. Windows profile, `/settings?section=account`: **pixel-identical** full-page screenshots in all three browsers at 1280×720 and 1024×768. (Rendered markup differs by one whitespace text node between two block-level rows — Razor trims it beside the `@if`; it does not render.) Windows cost: one `bool` read; `PortalAccountRows` is never created on desktop. Screenshots: `screenshots/chromium-desktop-settings-account.png`, `webkit-phone-settings-account.png`.

With H6, the phone Home avatar (Mobile UI, → `/settings?section=account`) lands on a page with the real account and Sign out — no Mobile UI change needed.

## Later hooks (not proposed yet)
- `SangamGate` on "Sign with certificate" (desktop) — D-33: deferred until a desktop Sangam client exists.
- Sign-in page: no Ui hook. The Web host renders `PortalSignIn` for signed-out visitors (its own route).
