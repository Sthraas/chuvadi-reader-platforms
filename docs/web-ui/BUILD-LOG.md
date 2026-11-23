# Web portal UI — build log

Branch `platform/web-ui` in `Sthraas/chuvadi-reader-platforms`. Newest entries at the bottom.

## 2026-11-06 — session 1

### 1. Inputs read
- `docs/coordination/RULEBOOK.md`, `DESIGN-NOTE.md`, `chuvadi-reader-platform-and-packages.md` (main 0f7ebbb).
- Handout: `Portal & Android.dc.html` 12a–12c (markup and data), `Reader Side Rails.dc.html`, `tokens.css`, README.
- `platform/foundation` (ab7c570): `PLATFORM-INTERFACE.md`, `FOR-UI-CHATS.md`, `EDITS-FOR-APPROVAL.md`, the contracts in `src/ChuvadiReader.Platform`, the Group A patch (it already drafts `PlatformRoot`, `WindowButtons`, `StatusLocation`).
- `platform/web` (4460dd4): build log, `DECISIONS-PENDING.md` (W-01…W-07), README.
- Coordinator update (6 Nov, 05:23): signal = `ShellLayout` cascaded as `PlatformState.Shell` + `<html data-shell>`; Web is always Portal and follows the browser for phone/tablet layouts and ⌘ labels; Foundation drafts `StatusLocation`/`WindowButtons`; `AccountMenu`, `PortalSignIn`, `SangamGate` are mine; AccountMenu drops "My files" and "Shared with me"; Web files are session-only working copies, Save = browser download; packages from the committed `ci/packages` feed.

### 2. Toolchain
- .NET SDK 10.0.403 via the official `dotnet-install.sh --channel 10.0` into `~/.dotnet` (sandbox).
- `dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config`, build: 0 warnings, 0 errors (Foundation baseline).

### 3. Branch
- `platform/web-ui` from `origin/platform/foundation` (ab7c570).
- First commit: Foundation's **Group A patch applied verbatim** (`docs/foundation/proposal/foundation-edits-1.patch`, `git apply`, no edits of mine). Reason: my components use `ChuvadiReader.Platform` types, which the Ui can only see through Group A's A1. The coordinator decided Group A centrally (Foundation applies it); this commit is replaced by Foundation's own when I rebase. CI on this branch stays green meanwhile.

### 4. Components (new files only)
`src/ChuvadiReader.Ui/Components/Platform/Portal/`: `PortalSignIn` (12a), `AccountMenu` (12b), `PortalStatusUser` (12b), `SangamGate` + `SangamGatingRow` (12c), `PortalLinks`, `PortalCredentials`, `AccountText`; scoped CSS for each, theme tokens only.
Decisions inside my own code (routine):
- Components hold no sign-in logic. `PortalSignIn` raises callbacks; `AccountMenu`/`PortalStatusUser` read `IAccount`; URLs come from `PortalLinks` (registered by the Web host). So the Web chat owns all Sangam code, as agreed.
- `PortalCredentials.ToString()` hides the password; the form clears the password on submit; the Sangam ID is passed exactly as typed (no trimming).
- Account card positioned as 12b (below the top bar, beside the Tools rail: right = 64 + 54 + 12 px); on browsers ≤ 720 px it anchors 12 px from the right and the chip shows only the avatar.
- Sign-in page stacks card-first under 900 px.
- Scope: storage meter, "My files", "Shared with me" and the "Share a link" gating row left out. Handout texts that the no-storage scope may make untrue are **kept as designed** and raised as U-1.

### 5. Hooks (proposal only, not committed as edits)
`docs/web-ui/proposal/web-ui-hooks-1.patch` + `HOOKS-FOR-APPROVAL.md`: H1 account menu, H2 Upload, H3 status user, H4 `IsPortal`. One file (MainLayout), +11/−2.
- First version wrapped the user item in `@if/else`, which dropped a whitespace text node between two status items on desktop (invisible in a flex row, but not byte-identical). Fixed by switching **inside** the existing `<span class="sb-item">`; desktop markup is now byte-identical.

### 6. Preview host and tests
- `tools/ChuvadiReader.WebUi.Preview` (dev only, `IsPackable/IsPublishable=false`): Blazor Server running the real Ui with fakes (in-memory settings, no pickers, signed-in fake Sangam account). Bug found and fixed in my own preview: `MapRazorComponents` needs `AddAdditionalAssemblies(Ui)` or server routes 404 on a cold load.
- `tests/ChuvadiReader.WebUi.Tests` (xunit, test-only): initials/first name, password never in `ToString`, ID passed as typed, gating list without sharing — 14 tests.
- Added both projects to `ChuvadiReader.Platforms.slnx` (Foundation's programme solution; "platform chats add their projects here").
- `dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror`: 0 warnings, 0 errors. `dotnet test`: 18 + 14 + 161 = **193 pass**. Same with the hooks patch applied.

### 7. Visual checks (Playwright 1.x with Chromium, Firefox 1555, WebKit 27.2 — testing only)
- Handout frames 12a/12b/12c captured from the `.dc.html`; built pages captured at 1280×720 (desktop), 1024×768 (tablet), 390×844 (phone) in all three browsers. No console errors or page errors in any browser.
- 12a, 12b (account card) and 12c match the frames in layout, sizes, type and colour (Cream paper), apart from the scope removals and the empty form fields (the frame shows sample values).
- Phone width: my components reflow correctly; the desktop shell around them does not (U-2).
- Desktop unchanged: see `HOOKS-FOR-APPROVAL.md` (markup identical; 48 screenshot pairs, differences only clock digits and antialias jitter that also occurs between two runs of one build).
- Finding for the Reader chat: WebKit at 1× drops the 0.5 px status-bar dividers (F-1).

### 8. Raised to the coordinator
`OPTIONS-FOR-COORDINATOR.md`: U-1 storage wording, U-2 portal at phone/tablet widths, U-3 where SangamGate goes, U-4 password vs login hint, U-5 account menu details (settings URL, download URL, organisation line), U-6 theme toggle and version text on the portal, U-7 server status dot colour, U-8 card position without rails, F-1 WebKit hairlines.

## 2026-11-06 — session 2 (coordinator update 15:41: D-31 to D-39, D-54)

### 1. Inputs
- `docs/coordination/DECISIONS.md` on main (D-01 to D-53 + Arun's 05:39 answers). Mine: D-31 to D-39; also relevant D-07, D-20, D-26 (one combined patch), D-28, D-32, D-54.
- `platform/foundation` 60dca85: Groups A–C applied; startup changes removed `PlatformRoot`/the cascade (read `IPlatformInfo` directly, `Info.Shell()`, `Info.IsPortal()`), window buttons and status text inline in MainLayout; `FOR-UI-CHATS.md`, `STARTUP.md`. No `IAccount.Unit` and no chuvadi-pdf 3.31.2 there yet.
- `platform/mobile-ui` ea5d775 (PhoneShell, mobile.css/js, hook H-1) and `platform/web` 24bf615 (`WebPlatform` thresholds: phone ≤ 599 px, touch tablet ≤ 1366 px; `SANGAM-INTEGRATION.md` S-02).
- `arunshivab/sangam` d43a5ff (rc.16), read only, for D-34.

### 2. Rebase
`git rebase --onto origin/platform/foundation 183f511` — my temporary Group A commit dropped (Foundation's own commits replace it); my session-1 commit replayed cleanly.

### 3. Changes (my files only)
- `PortalSignIn`: D-31 promise texts; D-34 — password field and "Forgot?" removed, `OnSubmitId(string)` gives the Sangam ID as typed (login hint), `ShowSangamId` parameter (default true = 12a) for the U-9 outcome. `PortalCredentials` deleted (no password anywhere in the portal Ui).
- `PortalLinks(DesktopAppUrl, AccountSettingsUrl)` + `PlaceholderDesktopAppUrl` = https://chuvadi.in/download (D-35).
- `AccountMenu.razor.css`: tablet sizes (40 px chip, 48 px rows) under `html[data-shell="tablet"]` (D-32). The card's position already follows `--sh-tools`/`--sh-view`, which mobile.css sets for tablet.
- New `PortalPhoneAccount` (D-32): account block + server line + Get the desktop app / Account settings / Sign out for the foot of the phone ⋮ sheet, in the sheet's own `.ph-row` style.
- New `wwwroot/css/portal.css` (D-37): blue `.status-dot.server`, per theme. Linked by the Web host only.
- Hooks regenerated: `proposal/web-ui-hooks-2.patch` (H1–H4, +7/−3, no new `@code` members → no extra Windows JIT); `hooks-1` removed. H5 and the Mobile UI slot request (`proposal/mobile-ui-request-phoneshell-slot.patch`) documented in `HOOKS-FOR-APPROVAL.md` §2.
- Preview host: no `PlatformRoot`; `PreviewPlatformInfo` with `PREVIEW_FORMFACTOR`; Web values match the Web chat's `WebChrome`/capabilities (`SavesAsDownload`); links `mobile.css` and `portal.css`; `/_preview/open` opens one file (F-3). `serve.sh` runs four servers; `shots.py` shoots portal desktop/tablet/phone with touch on tablet/phone.
- Tests: 15 in WebUi.Tests (D-31 lines pinned, no storage/delete promise, D-35 placeholder, gating list without sharing, name helpers).

### 4. D-34 check (Sangam)
`login_hint` is accepted by OpenIddict and listed in Sangam's parameter review, but no Sangam code reads it: `/login` pre-fills only from its own sign-in cookie. No password grant is enabled either. Reported as U-9 with options; the ID field stays as designed until the coordinator decides.

### 5. Verification
- Build `-warnaserror` 0 warnings; tests 27 + 15 + 161 = **203 pass** (with and without the hooks patch).
- Portal screenshots, Chromium + Firefox + WebKit at desktop 1280×720, tablet 1280×800 (touch), phone 390×844 (touch): no console or page errors.
- Phone and tablet were checked with Mobile UI's files copied in **locally only** (their `PlatformState` use adapted to `IPlatformInfo`), plus H5 and the slot: Upload in the ⋮ sheet, account block at its foot, and using a row closes the sheet (first draft passed a plain `Action` → sheet state closed without re-rendering; fixed by having PhoneShell pass an `EventCallback` on itself). All local copies removed before committing.
- Desktop unchanged with hooks-2 (Windows profile): markup of `/`, `/library`, `/settings` identical; 48 screenshot pairs → 34 identical, 12 clock digits, 2 sub-pixel icon antialiasing (visually identical; same run-to-run jitter as session 1).

### 6. Raised
`OPTIONS-FOR-COORDINATOR.md`: U-9 login_hint, U-10 position of the phone account block, U-11 two Home lines untrue on the portal; F-2 doubled full stop in the greeting, F-3 one pending path in `OpenDocumentService`, F-4 Mobile UI still on the removed cascade.

### 7. D-54 rebase (chuvadi-pdf 3.31.2)
The Foundation landed 3.31.2 during this session (`be4498a`). Rebased onto it: clean; `web-ui-hooks-2.patch` still applies; build 0 warnings; tests 27 + 15 + 161 pass; Windows-profile markup of `/`, `/library`, `/settings` identical with and without the hooks; portal desktop and tablet screenshots unchanged in Chromium. (Phone on the committed branch shows the desktop shell and a 404 for `mobile.css` — expected until Mobile UI's files land with the combined patch.)

## 2026-11-07 — session 3 (coordinator 6 Nov 23:54: U-9 a, U-10 a, U-11 a; F-2/F-3 → Foundation; F-4 → Mobile UI)

### 1. What changed underneath
- `platform/foundation` 63af90f: combined hooks (D-26) applied — H1–H4 in MainLayout (Foundation's own form: `IsPortal` property; user item wrapped in `sb-item`), the blue-dot rule in `shell.css`, `IAccount.Unit` (default null) shown in `AccountMenu`, Mobile UI's phone/tablet files and `mobile.css`. **It carried my session-1 Portal files** (password field, old promises, `PortalCredentials`, three-argument `PortalLinks`).
- `platform/web` 4761662: fills `Unit` from Sangam's `sangam_org` and registers `PortalLinks` with three arguments (session-1 shape).
- `platform/mobile-ui` f29b6a6: no `PhoneShell` slot yet.

### 2. Branch rebuilt on foundation
`git reset --hard origin/platform/foundation`, then my current versions of the files I own checked out from 475f7af: Portal `PortalSignIn`(+css), `PortalLinks`, `PortalStatusUser`, `AccountMenu.razor.css`, `PortalPhoneAccount`(+css); `PortalCredentials.cs` deleted; `tests/ChuvadiReader.WebUi.Tests`, `tools/ChuvadiReader.WebUi.Preview`, `docs/web-ui`. Kept the Foundation's `AccountMenu.razor` (its Unit line). `portal.css` dropped (rule now in `shell.css`). Preview project added to the slnx beside the Mobile UI preview.

### 3. Decisions applied
- U-9 (a): `PortalSignIn.ShowSangamIdDefault = false` — the card shows only "Continue with Sangam" and the desktop-app line. Field and `OnSubmitId` kept for U-9 (c). Test added. Preview: `?id=true` shows the field.
- U-10 (a): unchanged (foot). Slot request and H5 regenerated against 63af90f (`mobile-ui-request-phoneshell-slot.patch`, `web-ui-hooks-3-phone.patch`; `web-ui-hooks-2.patch` removed — applied by the Foundation).
- D-35: "· Unit" added to `PortalPhoneAccount`; preview fake account has Unit "Records".
- Phone block dot: same colours as `shell.css` (`#2c3e8c`, dark `#8fa3e6`).
- Web chat: one-line `PortalLinks` change needed (OPTIONS U-12).

### 4. Verification
- Build `-warnaserror` 0 warnings; tests MobileUi 3 + Hosting 28 + WebUi 16 + Reader 161 = **208 pass** (also with both phone patches applied).
- Chromium, Firefox, WebKit × portal desktop 1280×720 / tablet 1280×800 (touch) / phone 390×844 (touch), with the phone patches applied: no console or page errors; ⋮ sheet shows Upload and the account block with "· Records"; "Account settings" opens a new tab and closes the sheet. Sign-in shows only "Continue with Sangam" + the desktop-app line at every width.
- Windows profile server-rendered markup of `/`, `/library`, `/settings`: identical with and without the phone patches.
- Committed state: phone patches reverted (MainLayout and PhoneShell are not my files).

## 2026-11-07 — session 4 (coordinator 7 Nov 01:00: phone route approved; licence proprietary, free for everyone)

### 1. Checked
`platform/foundation` 2fafb60 (second combined patch: F-2, F-3 queue, Home Web wording; does not yet take my Portal files or H5 — coordinator says both are coming), `platform/mobile-ui` 26739e8 (no `PhoneShell` slot yet), `platform/web` 9cf2a3b, `main` 577cd0c (D-61 to D-68; D-63 = U-9, D-64 = U-10/U-11, D-66 = F-2/F-3). No LICENSE/EULA on any branch yet.

### 2. Terms of use (U-13)
- `PortalLinks` gains optional `TermsUrl` (default null). `PortalSignIn` shows "Terms of use" under the desktop-app line only when it is set. Two-argument construction unchanged.
- Test: terms optional, two-argument call still valid. Preview passes "/terms".
- Wording options (link only / "by continuing you accept" / checkbox) raised as U-13; built the link only.

### 3. Rebase
Onto 2fafb60: clean (the second patch touches none of my files). Both phone patches still apply (`git apply --check`). README: F-3 note updated (one `Request` per uploaded file is fine now), `TermsUrl` in the integration example; preview comment updated.

### 4. Verification
Build `-warnaserror` 0 warnings; tests Hosting 33 + MobileUi 11 + WebUi 17 + Reader 171 = **232 pass**. Chromium, Firefox, WebKit at desktop, tablet and phone: no console errors; the terms line fits the card at every width. (On this branch the phone ⋮ sheet has no account block — expected until the slot and H5 land.)

## 2026-11-07 — session 5 (coordinator 7 Nov 01:34: U-13 a)

### 1. Checked all branches
`platform/foundation` a4acc56 (carries my session-3 Portal files — status-bar spans fixed; `LICENSE`, `legal/EULA.txt` draft, `THIRD-PARTY-NOTICES.txt`; H5 not yet), `platform/mobile-ui` 1a27cd6 (**PhoneShell slot added**, identical to my request), `platform/web` 0e204dc ("hold the 12a integration until the Foundation carries it"), `main` 7801fca (D-69 to D-75; D-75 approves H5, spans, two-argument `PortalLinks`).

### 2. Branch rebuilt on a4acc56
Reset to foundation; my files checked out from f4e20d9 (Portal folder, WebUi tests, preview, docs). Net difference to foundation's Portal files: only the session-4 terms link. Preview project re-added to the slnx (foundation's copy dropped it). Removed `proposal/mobile-ui-request-phoneshell-slot.patch` (done by Mobile UI).

### 3. U-13
Decided (a) — already built. The EULA draft's "using the software you agree to it" fits a plain link.

### 4. H5 against the real slot (local only)
foundation a4acc56 + Mobile UI's Phone folder, mobile.css and mobile.js from 1a27cd6 + H5: 0 warnings; three browsers, phone width, no console errors; account block in the ⋮ sheet on a document view and on Library. All local files reverted.

### 5. Found while testing — raised
- **U-14:** Settings › Account says "Not signed in" / "Sign in with Sangam" on the portal, and the new phone Home avatar leads there (no Sign out on that path). Options in OPTIONS; recommendation (a) a `PortalAccountCard` hook.
- **O-1 to O-3:** Library empty text mentions folders; `PlatformText` says "computer" on Web (theme toggle, name hint); "Ctrl K" tip on touch phones.

### 6. Verification (committed state)
Build `-warnaserror` 0 warnings; tests Hosting 33 + MobileUi 11 + WebUi 17 + Reader 171 = **232 pass**.

### 7. CI did not run (account billing)
Run 42286178538 on de5da8a: every job "was not started because recent account payments have failed or your spending limit needs to be increased" (GitHub billing for the `Sthraas` account) — no code ran. Local: build `-warnaserror` 0 warnings, 232 tests pass. The last green run on `platform/foundation` was 19:42 UTC (a4acc56). Needs Arun (Billing & plans); re-run CI once cleared.

## 2026-11-07 — session 6 (coordinator 7 Nov 01:58: U-14 a; W wording for PlatformText; copyright; CI stopped — build locally)

### 1. Checked all branches
`platform/foundation` 615afde (third combined patch: Licences page and EULA in the app, D-77; my sign-in with the Terms link; `LicenceTextTests` in my test project), `platform/web` d30dbbe, `platform/mobile-ui` 745ef8e, `main` cab9981 (D-76 to D-81). Rebased onto 615afde: clean; my Portal files now equal the Foundation's copies.

### 2. Copyright
The Foundation sets it once for every assembly in `Directory.Build.props` (`Company`/`Authors` "Sthraas Intelligence Pvt Ltd", `Copyright` "© 2026 Sthraas Intelligence Pvt Ltd. All rights reserved.") and in `LICENSE`. My code compiles into `ChuvadiReader.Ui` and the dev-only preview/tests, all under that props file; the repo has no per-file headers, so none added. No visible copyright line in the 12a design; the in-app Licences page (D-77) carries it.

### 3. U-14 (a)
New `PortalAccountRows`(+css) and `proposal/web-ui-hooks-4-account.patch` (H6). "Account settings" hint made neutral after checking Sangam: its `/account` now forwards to a separate account portal whose contents this repo can't confirm. Verified as in HOOKS (portal three browsers × three sizes; Windows pixel-identical).

### 4. W-1 to W-4
Exact wording and suggested `PlatformText` code in OPTIONS. Checked: portal settings are session memory (`SessionAppStorage`), D-29 browser storage covers appearance only; Android reports a keyboard always; "Find or do anything…" is the phone Home search box.

### 5. Build (CI stopped — local only)
Committed state (hooks reverted), .NET SDK 10.0.403: build `-warnaserror` 0 warnings; tests Hosting 33 + MobileUi 11 + WebUi 19 + Reader 171 = **234 pass**. `web-ui-hooks-3-phone.patch` and `web-ui-hooks-4-account.patch` both `git apply --check` clean on 615afde. GitHub Actions not used (billing).

## 2026-11-07 — session 7 (coordinator 7 Nov 04:55: H6 status, legal links, drop overlay; no CI runs)

### 1. Checked all branches
`platform/foundation` fa9d120 (fourth combined patch: W-1 to W-4 applied; `Licence` page serves `/licence`, `/terms`, `/privacy`), `platform/web` 9425984, `platform/mobile-ui` 74c3fd6 (**PhoneShell slot present since 1a27cd6**), `main` 3dcb84c (D-82 to D-92). H5 and H6 are not on foundation.

### 2. Rebase
Onto fa9d120: clean. My Portal files equal the Foundation's copies except `PortalAccountRows` (H6), which only this branch has.

### 3. Legal links
- 12a: "Terms of use · Privacy" under the desktop-app line; new optional `PortalLinks.PrivacyUrl` (fourth argument, default null — the Web chat's earlier calls still compile). Link text "Privacy" matches the `/privacy` page heading. Test added.
- Account menu (12b has no place): options as U-15; not built.

### 4. H6 resent and re-verified on fa9d120
`web-ui-hooks-4-account.patch` applies cleanly; with it applied: build 0 warnings; portal Settings › Account in Chromium/Firefox/WebKit × desktop/tablet/phone shows the real account, no "Not signed in", no console errors; Windows `/settings?section=account` full-page screenshots pixel-identical (3 browsers × 1280×720, 1024×768). H5 also applies cleanly to fa9d120.

### 5. D-89 check list
Written in OPTIONS (handout Walkthrough "Drop to open" + States 8b), including the browser limit: file names are not available during drag.

### 6. Build (no CI: commit carries [skip ci])
Build `-warnaserror` 0 warnings; tests Mobile UI 15 + Hosting 48 + Web UI 32 + Reader 171 = **266 pass**.

## 2026-11-07 — session 8 (D-93: CI back, repo public)
Rebased onto `platform/foundation` 4819d66 (new CI rules: docs-only pushes run nothing, newer push cancels older). Local: 0 warnings, 266 tests pass. CI `platforms` run 42314281411 (dispatched, head 5c37e62): **success** — shared on ubuntu x64, ubuntu ARM64, macOS, Windows; windows-app; pack-check.

## 2026-11-08 — session 9 (coordinator 8 Nov 18:40: finish U-15; D-98 status wording)

### 1. Checked all branches
`platform/foundation` 8098695 (sixth combined patch: **PhoneShell slot, H5 and H6 applied**), `platform/web` 31b063e (drop: Web half of D-89 A), `platform/mobile-ui` 2678dd2, `main` c92e758 (D-94 to D-100; D-97 = U-15 a, D-98 = wording, D-100 Web Test chat). Rebased onto 8098695: clean; my committed Portal files equal the Foundation's copies.

### 2. U-15 (a) built
New `PortalLegalLinks` ("Terms of use · Privacy", each hidden when its URL is null; opens a new tab; reports clicks so menus close). Used under the sign-in card (replaces the inline markup), as a footer under Sign out in `AccountMenu`, and at the foot of `PortalPhoneAccount`. Wrapper divs owned by each host, hidden when empty.

### 3. D-98
`PortalPhoneAccount` server line → "processed on the server · kept in memory only · only you can see it". Status bar is MainLayout's → `proposal/web-ui-hooks-7-status-text.patch` (H7, text only). The 12a pitch's "encrypted at rest" raised as U-16 (not changed).

### 4. D-89 overlay check
Foundation's `PortalDropCatcher` behaviour matches the check list; it is invisible by design while the handout draws a "Drop to open" state → options in OPTIONS (recommend b).

### 5. Verification
Build `-warnaserror` 0 warnings; tests 16 + 54 + 32 + 171 = **273 pass**. With H7 applied locally: Chromium / Firefox / WebKit — desktop status bar shows the D-98 text; account card footer shows "Terms of use · Privacy" and using a link closes the card; phone (390×844, on the Foundation's real slot + H5) shows the memory line and the footer under Sign out; no console errors.

## 2026-11-08 — session 10 (coordinator 19:15: U-16 a / D-103; drop overlay b / D-104)

### 1. Checked all branches
`platform/foundation` f6607a3 (legal drafts reworded for D-98; H7 not yet), `platform/mobile-ui` a20f6d1, `platform/web` 31b063e, `main` d034fb8. Test branch present: `platform/linux-test` (no web-test branch yet). Rebased onto f6607a3: clean.

### 2. U-16 (a)
12a pitch: "…processed on our server, kept in memory only, and visible only to you." Test pins it (no "encrypted at rest"). No other "encrypted at rest" left in my files; the status bar's is MainLayout's (H7, sent).

### 3. D-104 (b) — "Drop to open"
Diff for the Foundation: `proposal/web-ui-drop-overlay.patch` (catcher markup + CSS only). Preview gains `PreviewDroppedFiles` (Web profile) so the catcher renders. Proofs in HOOKS. Found U-17 (overlap with Home's own drop zone) — options raised.

### 4. Build and tests
Build `-warnaserror` 0 warnings; tests 16 + 54 + 33 + 171 = **274 pass**.

## 2026-11-08 — session 11 (coordinator 19:50: U-17 b / D-109)

### 1. Checked all branches
`platform/foundation` 9fbed93 (part 2a: **H7, the D-103 pitch and the drop overlay applied** — `git apply -R --check` of both patches succeeds), `main` 19116b6 (D-108, D-109), `platform/mobile-ui` a20f6d1, `platform/web` 31b063e. No `platform/web-test` yet. Rebased onto 9fbed93: clean; my `src` equals the Foundation's.

### 2. U-17 (b)
Diff for the Foundation: `proposal/web-ui-home-drop-zone.patch` — `portal-drop.js` toggles `chvd-dragging` on `<html>` with the catcher's `on`; one rule in `Dashboard.razor.css` hides Home's zone contents (`visibility`, frame kept). Proved in three browsers, Cream and Night paper; Windows unaffected (HOOKS). Foundation files reverted on this branch.

### 3. Build and tests
Build `-warnaserror` 0 warnings; tests below.

### 4. Push (coordinator 20:22: no force)
The rebased branch no longer followed GitHub's cd03fac, and the force push was refused. I merged cd03fac in with no change to the files (`-s ours`). The ten files that differed were all the Foundation's 9fbed93 work, which this branch already has. Merge commit e27a52a was pushed normally, and CI run 42491908079 is green. Authorship stays Arun's; commits are not re-signed (signing is Arun's choice later).

## 2026-11-09 — session 12 (coordinator 01:30: check against 839d39d; Web Test look bugs; Q-3 / D-119)

### 1. Checked all branches
`platform/foundation` 839d39d (eighth combined patch: 63f37b1 has **U-17**, 839d39d has the Test chats' shared fixes), `platform/web-test` e6014d7 (BUGS.md WT-01 to WT-13), `main` 0f48211, `platform/mobile-ui` 95b9d79, `platform/web` 31b063e (not rebased yet). Merged 839d39d into this branch (a merge, not a rebase, so no force push). My `src` equals the Foundation's.

### 2. My changes on 839d39d (Chromium / Firefox / WebKit)
- `git apply -R --check` succeeds for H7, the drop overlay and U-17.
- 12a: the pitch says "kept in memory only" (Fraunces 15 px). The three D-31 promises are as decided. "Terms of use · Privacy" sits under the card.
- Status bar: "processed on the server · kept in memory only · only you can see it" (H7).
- Account card: "Terms of use · Privacy" footer (12.5 px), linking `/terms` and `/privacy` in a new tab (U-15).
- Phone: in the Reader, the ⋮ sheet shows the account block, the memory line, Get the desktop app, Account settings, Sign out, and "Terms of use · Privacy" at the foot. Phone Home now has the avatar (Mobile UI, handout 4a), which leads to Settings › Account with my rows (H6).

### 3. Web Test look bugs
WT-04 (status-bar wording), WT-05 (12a pitch) and WT-06 (account footer) are fixed in the Foundation and render correctly in the preview. They're still open on `platform/web` until the Web chat rebases. WT-03 (phone shell): the PhoneShell renders at 390×844 in the preview; re-test after the rebase. WT-10 label: Reader's couldn't-open button says "Upload…" on the Web (839d39d). Nothing else in WT-01 to WT-13 is mine.

### 4. Q-3 (D-119 c)
No layout change is needed → `proposal/web-ui-home-session-note.patch` ("0 pdfs · this session" on the two counts). Measured in 3 browsers × 3 sizes; Windows pixel-identical (HOOKS).

### 5. Build and tests
Build `-warnaserror` 0 warnings (with and without the patch); tests 16 + 59 + 33 + 187 = **295 pass**.

### 6. "Upload" in Arrange and Redact (coordinator 01:42)
Branches re-checked first: `platform/web` has moved to 1b32ad8, `platform/android-test` is new, and the Foundation is still at 839d39d. Diff: `proposal/web-ui-upload-wording.patch`. It uses a `PlatformText.FetchOrUpload` helper with the desktop text kept character for character, and covers 7 labels in Arrange and Redact. Proofs are in HOOKS: no "Fetch" left on the portal at any size in any of the three browsers, no overflow, and Windows text and pixels unchanged. Build `-warnaserror` 0 warnings; tests 295 pass.

## 2026-11-09 — session 13 (coordinator 02:30: Q-3 wording; Web rebased)

### 1. Checked all branches
`platform/foundation` f1e4126 (ninth combined patch: open-password prompt), merged in. `platform/web` 1b32ad8 (rebased), `platform/web-test` 86b9587, `main` 6b7051b (D-125 to D-128). My Upload-wording diff hasn't been applied yet and still applies to f1e4126.

### 2. Q-3 with the coordinator's wording
"Files in this session" fits, but "Your shelves for this session are empty — open the Library" wraps to two lines (the Library card grows 19 px) in all three browsers at all three sizes. So I built both (a) a shorter line that fits, "Nothing shelved this session — open the Library", with no size change in any of the 9 cases and Windows pixel-identical, and (b) hide on the Web. Waiting for the choice (OPTIONS). The first Q-3 diff is withdrawn.

### 3. Build and tests
Build `-warnaserror` 0 warnings with each diff applied and with neither; tests **297 pass**.

## 2026-11-09 — session 14 (coordinator 03:07: go ahead with Q-3 (c); Upload diff to the Foundation)
Branches checked: `platform/foundation` d70590a (tenth combined patch, B-24), merged in; `platform/web` 35229c3, `platform/web-test` 2cc43db, `main` ee2b877 (D-129, D-130). Q-3 (c) is sent as `proposal/web-ui-home-session-wording.patch`, with "Files in this session" and "Nothing shelved this session — open the Library". The example line wraps, so I used the line that fits; the hide version is dropped. Both of my open diffs apply to d70590a and build together with 0 warnings.

## 2026-11-09 — session 15 (coordinator 06:05: bring the branch up to date with the Foundation and re-check everything)

### 1. Branches
Checked all: `platform/foundation` eb74e52 (eleventh patch: Docs 2.0.0 / Sheets 2.0.2; twelfth part 1: chuvadi-pdf 3.32.0), `main` 9e3707a (D-139, D-140), `platform/web` c38bd80, `platform/web-test` 45f303e, `platform/mobile-ui` 1f4b4c3. Merged eb74e52 in (a merge, not a rebase, so no force push, per the 20:22 decision). My `src` equals the Foundation's.

### 2. My diffs in the Foundation
`git apply -R --check` succeeds for `web-ui-home-session-wording.patch` and `web-ui-upload-wording.patch`, so both are in exactly as sent. None of my hooks are waiting now.

### 3. Render check: baseline vs merged
I screenshotted every portal surface in Chromium, Firefox and WebKit at desktop 1280×720, tablet 1024×768 touch and phone 390×844 touch: 12a sign-in, 12c Sangam gate, Home, the 12b account menu with its footer (desktop and tablet), Arrange, Redact, and the phone Reader's ⋮ sheet. That's 54 screenshots, compared against a worktree of my previous head (dd0b705) with the two diffs applied, which is the state already proven against the handout.
- Text: identical in all 54 once the clock times are masked.
- Pixels: identical in all 54 with the two clocks masked (Home's date line and the status bar). One 3×12 px sliver on the Chromium 12b chip edge didn't come back on two fresh baseline shots, so it was a one-off render glitch.
- Wording on the portal: "FILES IN THIS SESSION" (capitalised by CSS, the same as "STORAGE MAP") and "Nothing shelved this session — open the Library"; "Upload a PDF to start. / Upload a file" and "Upload a document…"; no "Fetch" on any portal screen; account footer "Terms of use · Privacy"; status bar "processed on the server · kept in memory only · only you can see it".
Nothing needed fixing.

### 4. Build and tests
After a restore for the new library versions: build `-warnaserror` 0 warnings; tests 16 + 39 + 212 + 60 = **327 pass**, 0 fail.

## 2026-11-09 — session 16 (coordinator 07:31: bring the branch up to foundation 022b7c0)
- Branches checked: `platform/foundation` 022b7c0 (twelfth patch parts 2–3 and D-146), `main` a5f7cf0, `platform/web` c38bd80, `platform/web-test` 277e9a7, `platform/mobile-ui` 558a276. Merged 022b7c0 in (a merge rather than a rebase, so no force push; same result). My `src` equals the Foundation's.
- W-02 `host-drop.js` loads only in the Windows WebView2 page (`index.html`) and returns at once without `chrome.webview`, so the portal's drop catcher isn't affected. Re-proved U-17 in three browsers: during a drag the zone's contents are hidden, its frame stays and the overlay shows; afterwards everything is restored.
- Re-shot the 54 portal screenshots against session 15's (eb74e52). The text is identical. Pixels are identical apart from (1) Arrange's desk header on tablet and phone, where Mobile UI's H-17 to H-19 moved the BM, arrow, copy and delete buttons behind ⋯ on touch screens (their intended change; desktop Arrange is unchanged), and (2) the known flaky 3 px sliver on the Chromium 12b chip edge.
- Build `-warnaserror` 0 warnings; tests 16 + 39 + 212 + 64 = **331 pass**.

## 2026-11-10 — session 17 (coordinator 07:26: Web track restarted; merge foundation f88f9ef, patches 13–19)
- Branches checked: `platform/foundation` f88f9ef, `main` 081d7a5, `platform/web` 002bf02, `platform/web-test` 277e9a7 (no new look bugs), `platform/mobile-ui` d34d542. Merged f88f9ef in with a merge commit; no conflicts, and my `src` is identical to the Foundation's.
- What changed that touches the portal: Home, the tabs and the Reader now show tooltips through `IPathLabels.Describe(path)`, and MainLayout fills the native menu bar only on macOS. My wording and layout are untouched. The preview gets `IPathLabels` from `AddChuvadiReader` (the `Seam` default), so the preview needed no change.
- Build `-warnaserror` 0 warnings; tests 233 + 16 + 41 + 77 = **367 pass** (up from 331 with the Foundation's new tests).
- Re-check against ce805d1 in a worktree: 63 screenshots in Chromium, Firefox and WebKit at desktop, tablet and phone sizes, covering 12a, the 12c Sangam gate, Home, the 12b account menu with its footer, Settings › Account (new in the sweep), Arrange, Redact, and the phone ⋮ sheet. The text is identical in all 63. Pixels are identical apart from the known flaky Chromium chip sliver and a 34×1 px anti-aliasing change on a toolbar button group's top edge in Chromium tablet Arrange. That one is consistent and comes from the Foundation's render patches; it's not a portal surface and you can't see it at normal size.
- Drop overlay (U-17 / D-104): in all three browsers on both zones, a PDF drag hides the contents, keeps the frame and shows the overlay, and everything is restored afterwards. An image drag, window blur and the Windows profile never set it.

## 2026-11-10 — session 18 (coordinator 20:50 and 22:45: merge foundation-pr dd59362, patches 20–24; Excel value bar in the portal)

### 1. Branches, and which branch I merged
Checked all: `platform/foundation-pr` dd59362, `platform/foundation` ec09f4f, `main` 9196b3a, `platform/web` 04cdd21, `platform/web-test` 6a6e981, `platform/mobile-ui` 5c66f1a.
`foundation-pr` has a different history (patches 12–21 squashed in #12), so merging it conflicts in 10 files. Its tree is `platform/foundation` ec09f4f **minus 34 files**: `docs/design-handoff/` (26, the handout I build from), three coordination docs, and `.github/workflows/platforms.yml` and `platform-build.yml` (this branch's CI). `src`, `tests`, `tools` and `ci` are byte-identical. So I merged **`platform/foundation` ec09f4f**: the same patches 20–24, a clean merge, and it keeps CI and the handout. After the merge, `git diff HEAD origin/platform/foundation-pr -- src` is empty. Raised with the coordinator.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 292 + 16 + 41 + 89 = **438 pass**, 0 fail, 3 skipped (the Foundation's own skips, SH-L1 among them).

### 3. Portal surfaces against d3a7139
63 screenshots (Chromium / Firefox / WebKit × desktop / tablet / phone; 12a, 12c, Home, 12b, Settings › Account, Arrange, Redact, phone ⋮ sheet). The text is identical in all of them. The only pixel change is the Tools rail heading in Arrange and Redact at desktop and tablet sizes, now "TOOLS" (H-20, patch 22, intended). Drop overlay: 6 of 6.

### 4. Excel in the portal (patch 24, D-161)
- Formatted cells show as the file's number formats say (1,234,567 · ($1,235) · 25.60% · 1 1/4 · 15-Mar-23), right-aligned, at all sizes.
- **Bug found**: the value bar's click listener was on in only 4 of 10 opens, the same in all three browsers. It is a render-order race in `XlsxView`. The fix is sent to the Foundation as `proposal/web-ui-xlsx-value-bar-race.patch` and measures 10 of 10 (HOOKS). The Foundation's files are reverted on this branch, so the bug is still here until the Foundation applies the diff.
- Known library item SH-L1 is visible: time-only cells show "########", and the value bar shows -0.25 for a stored 0.75.

### 5. CI on dfbca11: one Windows-only failure, not from this branch
Run 42863954875: 7 of 8 jobs pass (Linux, macOS, the trimmed launches, pack-check, the Windows app). `shared (windows-latest)` fails one test, the Foundation's `MemoryAfterCloseTests.Closing_a_heavy_document_brings_memory_back_near_where_it_was`: "live memory after close: 4 → 72 MB". It gives the same numbers on a re-run of the job. The other 437 pass there (16 + 89 + 41 + 291).
- `platform/mobile-ui`'s merge of the same patch (run 42862735037) fails on the same test with the same numbers, also Windows only.
- The Foundation's own run of ec09f4f (42805261634) passed on Windows.
- This branch differs from ec09f4f only in `docs/web-ui`, the preview tool and the `_Imports.razor` it needs; nothing the test exercises. Locally (Linux) the test passes: 438 of 438.
Raised with the coordinator for the Foundation.

## 2026-11-10 — session 19 (coordinator 23:35: read Web Test's report on WT-03 to WT-06)
- Coordinator's answers: merging `platform/foundation` rather than `foundation-pr` was right, and the branch stays as it is. The value-bar diff goes to the Foundation together with Mobile UI's H-23 (same area), and the Foundation reconciles the two. The Windows memory test is a known intermittent on 4-core Windows runners, also on main; the Foundation is fixing the cause.
- Branches checked: `platform/web-test` 6a6e981 (10 Nov), `platform/web` 04cdd21, `platform/foundation` 9c1bf87, `platform/foundation-pr` 67823ad, `platform/mobile-ui` 5c66f1a, `main` 9196b3a.
- Web Test `BUGS.md` / `RESULTS.md` at 6a6e981: **WT-03, WT-04 and WT-06 are verified fixed in three engines on `platform/web` d183ea8** (10 Nov 07:30–08:40). WT-05 was verified in 1b32ad8 and is unchanged. The WT-10 label and its Arrange addendum were verified in c38bd80 (no "Fetch" on the portal). Q-3 ("this session") is green in the regression run and in `verify_fixes.py`.
- Nothing in Web Test's documents is open against the Web portal UI. The open items, WT-17 to WT-21, are Core, Foundation or Web items.
- One note for Web Test's WT-17 re-test on patch 24: until `proposal/web-ui-xlsx-value-bar-race.patch` is applied, the Excel value bar turns on in only about 4 of 10 opens in the portal.

## 2026-11-11 — session 20 (coordinator 02:35: merge the latest Foundation, patch 25 parts 1–4; Word "left out" note)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 742a5da, `platform/foundation` 382aada, `main` 159d04b, `platform/web` 04cdd21, `platform/web-test` aa25188, `platform/mobile-ui` 5c66f1a. As on 10 Nov (confirmed by the coordinator at 23:35), I merged **`platform/foundation` 382aada**: `src`, `tests`, `tools` and `ci` are identical to foundation-pr 742a5da, and the merge is clean. After the merge `src` equals foundation-pr's.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 305 + 16 + 41 + 91 = **453 pass**, 0 fail, 3 skipped (the Foundation's).

### 3. Portal surfaces against df9c399
63 screenshots (three browsers × desktop / tablet / phone; 12a, 12c, Home, 12b, Settings › Account, Arrange, Redact, phone ⋮ sheet): **text and pixels identical in all 63**. Drop overlay 6 of 6.

### 4. Word files: parts left out (D-168)
I made damaged copies as the tests do: a broken `word/header1.xml` in `discharge.docx`, and `landscape.docx` without its picture.
- The note shows above the page in all three browsers at all three sizes: "Part of this document is damaged and is left out: a header." / "… a picture." A sound file shows no note. There are no page errors and no sideways scroll.
- Look: LiPi Sans 13 px on a pale yellow box (fixed colours, the same in Night paper, where the Word page also stays white). On desktop it is exactly as wide as the page.
- **Found**: on tablet and phone the note is wider than the page (edge to edge on a phone). A one-rule diff is sent to the Foundation: `proposal/web-ui-docx-leftout-margins.patch` (HOOKS). The Foundation's file is reverted here.

### 5. Excel value bar
Not in yet (it goes into the Foundation's part 5); `proposal/web-ui-xlsx-value-bar-race.patch` still applies to 382aada. Measured again on this build: the bar came up in 6 of 18 opens.

## 2026-11-11 — session 21 (coordinator 06:35: merge the latest Foundation, patch 26; Excel grid with hidden sheets and Find)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 07ed3ca, `platform/foundation` 37bd4a0, `main` a06697d, `platform/web` d6b86ac, `platform/web-test` aa25188, `platform/mobile-ui` 8699719. Merged **`platform/foundation` 37bd4a0** (its `src`, `tests`, `tools` and `ci` are identical to foundation-pr 07ed3ca; the merge is clean). After the merge `src` equals foundation-pr's.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 374 + 16 + 41 + 91 = **522 pass**, 0 fail, 6 skipped (the Foundation's).

### 3. My two diffs
- Word note margins: in exactly as sent. The note and the page share the same edges at all sizes in three browsers.
- Excel value bar: in, reconciled with H-23. First click shows the bar in 36 of 36 opens (12 per browser); Windows profile 9 of 9.

### 4. Excel grid in the portal (`layout.xlsx`; Chromium / Firefox / WebKit × desktop / tablet / phone)
- The grid is as the file holds it: hidden column C and hidden row 5 take no room (headers A B D E…, rows 1–4, 6…), column A and rows 1–2 are frozen, and merged title, tall and wrapped rows, borders, rich text, data bars, icons and the comment mark all show. The page never scrolls sideways.
- Hidden sheets: four tabs, with "Secret" and "Deep" dimmed and carrying a "hidden" pill and the title "This sheet is hidden in the workbook". Clicking or tapping one shows it ("in a hidden sheet"). On the phone the tab strip scrolls.
- Find (desktop and tablet: the left bar's Find; phone: ⋮ › Find): "hidden" → "4 found", tab badges 2 / – / 1 / 1. "7654321" (stored) and "7,654,321" (shown) each give "1 found" (D-171). "pattern" → A14 is outlined. "zzzq" → "0 found". The same in all nine cases.
- Value bar: A17 → "A17 1234567" on the first click or tap in all nine cases.
- Screenshots: `screenshots/chromium-xlsx-grid-find-hidden.png`, `screenshots/webkit-xlsx-phone-grid-hidden-find.png`.

### 5. Portal surfaces against c3e3f1c
63 screenshots: the text is identical in all of them. Pixels are identical apart from the known flaky Chromium chip sliver, and **Redact's Tools rail at desktop and tablet sizes: "Sign with certificate" is no longer greyed out** (Windows PR 15). That is live on the portal against D-27 → OPTIONS **U-18**. Drop overlay 6 of 6.

### 6. Observations passed to the Foundation (OPTIONS)
The Office Find box doesn't take the cursor (old, all platforms); Find hits in hidden rows and columns can't be seen; on the phone "4 found" wraps and far tab badges are off-screen; merged range cut at the frozen line (already declared, E-07).

## 2026-11-15/16 — session 22 (coordinator 15 Nov 23:55: D-187, U-18 (b); Find-focus diff; hidden Find matches as an option)

### 1. Branches and merge
Checked all: `platform/foundation` 20030cb (15 Nov; pinch-to-zoom, M-27 mark-under-pointer fix), `platform/foundation-pr` 89ac6b2 (11 Nov, older), `platform/foundation-lib33` 52b867c (work in progress, not for merge, D-186), `main` e578a80 (D-186, D-187), `platform/web` 21ac80d, `platform/web-test` aa25188 (unchanged), `platform/mobile-ui` a1dfb40. Merged **`platform/foundation` 20030cb** (clean); `src` equals the Foundation's. Both diffs below are written against it.

### 2. U-18 (b): `proposal/web-ui-portal-certificate-off.patch`
Nine files, +48 / −7 (HOOKS has the table). On the portal "Sign with certificate" is greyed with the D-187 sentence in the Reader's Protect rail, Redact's Tools rail, Ctrl K and the phone's Protect strip. With a mouse it is disabled and the sentence is its tooltip. On a touch screen it stays greyed but answers a tap, and the card shows the sentence in place of its fields. Proved in Chromium, Firefox and WebKit at desktop, tablet and phone sizes: 9 of 9 as decided.
- Rail word: "off". "desktop app" and "desktop" run past the rail's edge (measured: "desktop" by 4 px in all three browsers); "off" ends where the shortcut letters end.
- Windows profile, with and without the patch (Protect rail, Sign card, Redact rail × 3 browsers): 8 of 9 pixel-identical. The ninth (Chromium, rail shot) differs in an 82 × 5 px strip on the Ctrl K pill's bottom edge, which the patch doesn't touch and which is identical in the other two Chromium shots of the same top bar. On Windows the button is enabled and the full card shows, as before.
- Portal sweep (63 screenshots against the merged tree without the patches): text identical in all 63; the only pixel change is the Redact rail's button at desktop and tablet sizes, greyed again (intended).

### 3. Find focus: `proposal/web-ui-office-find-focus.patch`
Two files, +12. The Find box of the Word, Excel, Markdown and text viewers takes the cursor when it opens. Proved by typing without clicking the box: "4 found" in `layout.xlsx` and "1 found" in `discharge.docx`, from the left bar's Find (desktop, tablet), from ⋮ › Find (phone) and on the Windows profile, in all three browsers. Not provable here: a real iPhone raising its keyboard (HOOKS says why and what to check).

### 4. Found on the way
**Ctrl F does nothing on Office files** (old, every platform): the key handler is set up only with a PDF's desk. I tried routing `OpenFind` to the viewers' Find; no effect, so it is left out of the patch and written up in OPTIONS for the Foundation.

### 5. U-19 (option, not a diff)
How a person sees Find matches that sit in hidden rows and columns: three options in OPTIONS, recommending a line under the Find box that names them with their cell addresses.

### 6. Build and tests
- Merged tree as pushed (the Foundation's files untouched): build `-warnaserror` 0 warnings.
- With both patches applied: build `-warnaserror` 0 warnings; tests 374 + 16 + 41 + 97 = **528 pass**, 0 fail, 6 skipped (the Foundation's). Each patch applies alone and in either order.

## 2026-11-16 — session 23 (coordinator 00:15 and 00:40: merge patch 27; rail word; U-19 and Ctrl F answers)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 57a63c5, `platform/foundation` 7fd806f, `main` e578a80, `platform/web` 4803bfa, `platform/web-test` aa25188 (unchanged), `platform/mobile-ui` 5a49864. Merged **`platform/foundation` 7fd806f** (`src`, `tests`, `tools`, `ci` and `global.json` identical to foundation-pr 57a63c5; foundation-pr itself conflicts, as before). Session 22 already had patch 27's code (pinch, M-27 mark placement); new here are `global.json`, the workflows that read it, and one line in the solution file. No app code changed.

### 2. Strict `global.json` (D-178, D-186)
The SDK here is 10.0.403. The first build failed on every project with `MSB4242` ("Workload version 10.0.403 … was not found"): the file pins the workload set as well. Cure, as the Foundation's log says: `dotnet workload update` once in the repo folder (4 s). After that, `dotnet workload --info` reports 10.0.403.

### 3. Build, tests, portal
Build `-warnaserror` 0 warnings. Tests 374 + 16 + 41 + 97 = **528 pass**, 0 fail, 6 skipped. Portal sweep against session 22's clean screenshots: text identical in all 63; pixels identical apart from the known flaky Chromium chip sliver. Drop overlay 6 of 6.

### 4. Rail word for U-18: "soon"
Coordinator: use what other unavailable rail items on the portal use. I listed every greyed rail button with a reason on the portal (Reader Read / Mark / Protect, Arrange, Redact, an Excel file): all are `disabled` with the word "soon" (Highlight, Note, Fill form, Print, Convert to PDF), the same as on Windows. `proposal/web-ui-portal-certificate-off.patch` is regenerated without the word parameter (now +39 / −6, nine files). Re-proved: 12 of 12 cases as decided; "soon" ends at 1204 of 1218 in three browsers. With both patches applied over 7fd806f: build 0 warnings, 528 tests pass; each applies alone and together.

### 5. Answers recorded
D-188: U-19 (a) now, (b) later. Ctrl F on Office files: a Foundation task. Both marked in OPTIONS.

## 2026-11-16 — session 24 (coordinator 02:45: merge patch 28 and confirm its four changes in the portal)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 87f95c0 (patch 28), `platform/foundation` 7354215 (**two commits past patch 28**: the encoding picker's Core side, and the Excel title bar's sheet arrows), `main` f361e03, `platform/web` eab426b, `platform/web-test` 7f0b5c1, `platform/mobile-ui` cbdef77. The coordinator asked for 87f95c0, so I merged **754d1e2**, the commit on `platform/foundation` with the same `src`, `tests`, `tools`, `ci` and `global.json` as foundation-pr 87f95c0, and left the two later commits for their own patch. Clean merge; `src` equals foundation-pr's.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 382 + 16 + 41 + 100 = **539 pass**, 0 fail, 6 skipped (the Foundation's).

### 3. The four changes, in the portal, Chromium / Firefox / WebKit
1. **Sign with certificate greyed with its reason (D-187)**: 12 of 12 cases as decided (portal desktop: disabled, tooltip with the sentence; tablet and phone: greyed, answers a tap, card shows the sentence with no fields; Windows profile: enabled, full card). **One thing off: the rail word is "off".** Patch 28 took the first version of my diff, twenty minutes before the updated one. Follow-up diff: `proposal/web-ui-portal-certificate-rail-word.patch` (HOOKS).
2. **Find box takes the cursor in Excel and Word**: in exactly as sent. 54 of 54 cases.
3. **Hidden Find matches named above the sheet (D-188, U-19 a)**: the line appears in 9 of 9 cases with the right words ("2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)"), and not before a search, for a visible-only match, on the hidden sheet, or after clearing. **But the Find box covers it**: 10% of the sentence at 1280 px, about 20% on a tablet, 43–48% on a phone. Options in OPTIONS U-20, with a measured diff ready for the one I recommend (the line under the sheet: 0% covered at every size).
4. **Ctrl F opens the viewers' Find**: on Excel and Word, portal and Windows profiles, three browsers: the box opens and has the cursor (part of the 54).

### 4. Portal surfaces against session 22's clean screenshots
63 screenshots: text identical in all. Pixels: the Redact rail's "Sign with certificate" at desktop and tablet sizes (greyed, intended) and the known flaky Chromium chip sliver. Drop overlay 6 of 6.

### 5. The two follow-up diffs
Each applies to 754d1e2 alone and together. With the rail-word one applied: build 0 warnings, 539 tests pass.

## 2026-11-16 — session 25 (coordinator 14:40: merge patch 29; the ask-before-closing card and the Excel resize in the portal)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 71754e1, `platform/foundation` 7c0b4bc, `main` 33ca3b8 (D-190 to D-192), `platform/web` a0a2f7c, `platform/web-test` 4ac4521, `platform/mobile-ui` ca152c4. `platform/foundation` 7c0b4bc has the same `src`, `tests`, `tools`, `ci` and `global.json` as foundation-pr 71754e1; merged it (clean). `src` equals foundation-pr's.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 434 + 16 + 41 + 102 = **593 pass**, 0 fail, 6 skipped (the Foundation's).

### 3. The ask-before-closing card (D-190)
Three browsers × portal desktop, tablet, phone and the Windows profile, each case on its own copy of a PDF with one rectangle mark placed: wording, button order, focus, Enter, Esc, Tab, Discard, Cancel, a read-only file, and the scrim. Closing the tab: the × on desktop and Windows, Document ▾ › Close on the tablet (12d), the tab list's Close on the phone. Results in OPTIONS. Everything is as D-190 says except: Tab leaves the card (diff sent), the title's words differ from the ones D-190 quotes (for the coordinator), and "Save as…" wraps on the phone.

### 4. Excel resize (D-190)
The same 12 cases on copies of `layout.xlsx`: all pass (OPTIONS has the numbers).

### 5. Diffs for the Foundation, all against 7c0b4bc
- New: `proposal/web-ui-close-card-keeps-focus.patch`.
- Regenerated: `proposal/web-ui-xlsx-hidden-matches-under-sheet.patch` (D-192); the 754d1e2 version no longer applied.
- Unchanged, still applies: `proposal/web-ui-portal-certificate-rail-word.patch`.
With all three applied together: build 0 warnings, 593 tests pass; the hidden-matches line is 0% covered at every size and the rail word is "soon" in three browsers. Each applies alone.

### 6. Portal surfaces against patch 28's screenshots
63 screenshots: text identical in all. Pixels differ only in Home's greeting ("Good evening" at 21:34, "Good morning" at 09:38 on the container's clock). Drop overlay 6 of 6.

## 2026-11-16 — session 26 (coordinator 21:35: merge patch 30 and confirm it in the portal)

### 1. Branches and merge
Checked all: `platform/foundation-pr` 4b704c8, `platform/foundation` 6d80aa3, `main` 1c482d4, `platform/web` 3f80768, `platform/web-test` 9e4cc6a, `platform/mobile-ui` ae6ae6d. `platform/foundation` 6d80aa3 has the same `src`, `tests`, `tools`, `ci` and `global.json` as foundation-pr 4b704c8; merged it (clean). `src` equals foundation-pr's.

### 2. Build and tests
Build `-warnaserror` 0 warnings. Tests 438 + 16 + 41 + 102 = **597 pass**, 0 fail, 6 skipped (the Foundation's).

### 3. Patch 30 in the portal, Chromium / Firefox / WebKit
1. **Hidden-matches line under the sheet (D-192)**: in, placed by hand by the Foundation. 0% covered by the Find box at four sizes; right words in 9 of 9 cases; not shown before a search, for a visible-only match, on the hidden sheet, or after clearing.
2. **Rail word "soon"**: in exactly as sent. 12 of 12 certificate cases as D-187 says; the word fits the rail.
3. **Find stays on the match's page (Mobile UI H-26)**: the Foundation's `foot.pdf` (the word 91% down each of four pages), Find "footmark", six steps, on portal desktop, tablet, phone and the Windows profile: 72 steps, the match on screen and on its own page every time (pages snap, `y mandatory`, on all four).
4. **A pinch in Mark leaves no mark (Mobile UI H-25)**: tablet and phone profiles. Two touch pointers sent by script in all three browsers, and real two-finger touches (CDP) in Chromium: no shape and no text with Rectangle or with Text. Control: one finger still drags a rectangle (0 → 1).

### 4. Portal surfaces against patch 29's screenshots
63 screenshots: text identical in all; pixels identical with Home's date line and greeting masked (they follow the clock). Drop overlay 6 of 6.

### 5. Still with the Foundation
`proposal/web-ui-close-card-keeps-focus.patch` is not in patch 30 and still applies cleanly to 6d80aa3.

### 6. View on the card's Save on the portal
Three lines in OPTIONS: Save should download as Ctrl S does (D-03), not stay as it is.

## 2026-11-16 — session 27 (coordinator 22:50: merge patch 31 and the encoding picker Ui; check the picker in the portal)

### 1. Last time's CI
Run on f685f8c: all nine jobs green (the two macOS jobs ran after I reported).

### 2. Branches and merge
Checked all: `platform/foundation-pr` b895750, `platform/foundation` 9bef505, `main` f88a6f6 (D-194 to D-196), `platform/web` 21665a3, `platform/web-test` 9e4cc6a, `platform/mobile-ui` 1720924.
This time no commit on `platform/foundation` has foundation-pr's code: the encoding picker Ui (f222811, PR 23) went into Reader main and was merged from there into foundation-pr. foundation-pr itself conflicts with this branch in 39 paths (its squashed history). So: merged `platform/foundation` 9bef505 (clean), then cherry-picked f222811. That stopped on one conflict (`Reader.razor`, patch 31 and the picker next to each other), which the Foundation had already resolved in b895750, so I took the Foundation's resolved files (`src`, `tests`, `ci`, `global.json`, `tools/PixelProof`) from b895750 as they are. Result: those are **byte-identical to foundation-pr b895750**; this branch still differs only by the design handoff, the coordination docs and the CI workflows it keeps.

### 3. Build and tests
Build `-warnaserror` 0 warnings. Tests 438 + 16 + 41 + 102 = **597 pass**, 0 fail, 6 skipped (the Foundation's).

### 4. The encoding picker in the portal
Three browsers × four profiles on copies of a Windows-1252 text file, plus the five-file detection check. Results and four points in OPTIONS. One diff: `proposal/web-ui-encoding-rows-finger-size.patch`.

### 5. My keep-focus diff
In patch 31 (6f7790e). Re-checked: Tab and Shift Tab cycle inside the card and Esc cancels, three browsers, portal and Windows profiles.

### 6. Portal surfaces against patch 30's screenshots
63 screenshots: text identical; pixels identical apart from the known flaky Chromium chip sliver (Home's date and greeting masked). Drop overlay 6 of 6.

## 2026-11-18 — session 28 (coordinator 17 Nov 23:58: merge patch 32; check the close questions and Find in the portal)

### 1. Last time's CI
Run on b5cd853: all nine jobs green.

### 2. Branches and merge
Checked all: `platform/foundation-pr` 149f4fc, `platform/foundation` c80f76a, `main` 73d3573, `platform/web` 95c44b0, `platform/web-test` f16176b, `platform/mobile-ui` 9e3f987.
`platform/foundation` c80f76a has foundation-pr's code exactly (`src`, `tests`, `tools`, `ci`, `global.json`), so I merged it. The merge was clean and the code is **byte-identical to foundation-pr 149f4fc**.

### 3. Build and tests
Build `-warnaserror` 0 warnings. Tests 446 + 16 + 41 + 103 = **606 pass**, 0 fail, 6 skipped (the Foundation's).

### 4. My preview, so the close questions can be tested
In `tools/ChuvadiReader.WebUi.Preview` (mine, not shared code): Sign out asks `IUnsavedWork` first, as the portal will. `PREVIEW_SAVE_DIR` lets Save as… and Save session… write a file. Two new pages: `/_preview/arrange` (fills a desk) and `/_preview/close-app` (stands in for a window close on the Windows profile). My first version of `close-app` navigated again after the answer, which asked a second time; I fixed it to leave the answer in a page variable, and re-ran that case in three browsers.

### 5. Patch 32 in the portal
`p32.py`: marks, bookmarks, redaction areas, Arrange, Arrange and marks together, and Find over `tools/PixelProof/fixtures/top.pdf`. Three browsers × four profiles, every case passing; details and two wording points in OPTIONS. One look problem on the phone (two long labels on two lines) → `proposal/web-ui-close-card-phone-labels.patch`, measured before and after at 360 and 390 px.

### 6. Portal surfaces against patch 31's screenshots
63 screenshots. Text identical apart from the status bar's clock; pixels the same apart from that clock and the known flaky Chromium chip sliver. Drop overlay 6 of 6, no console errors.

### 7. Web Test (f16176b)
Nothing against the Web portal UI. My patch 31 point 4 (encoding choice after reload) is proved on the real portal.

## 2026-11-18 — session 29 (coordinator 01:35: merge patch 33; check its wording in the portal)

### 1. Last time's CI
Run on 5fa28ec: all nine jobs green. The two diffs from sessions 27 and 28 were routed to the Foundation by the coordinator (HOOKS updated).

### 2. Branches and merge
Checked all: `platform/foundation-pr` 9e00fdf, `platform/foundation` e7ba750, `main` eed82d8 (the coordinator says b193ab0; not fetched yet here), `platform/web` 95c44b0, `platform/web-test` f16176b, `platform/mobile-ui` df420b5.
`platform/foundation` e7ba750 has foundation-pr's code exactly, so I merged it. Clean; **byte-identical to foundation-pr 9e00fdf**.

### 3. Build and tests
Build `-warnaserror` 0 warnings. Tests 448 + 16 + 41 + 103 = **608 pass**, 0 fail, 6 skipped (the Foundation's).

### 4. Patch 33 in the portal
`p33.py` (test files in the scratchpad):
- the page-operation question with a plain, a bookmarked and a layered file, and two files at once;
- Redaction held in Protect, the R key, Ctrl K, the redact page and Arrange;
- the signature banner and card, with a signed copy made by the app's own signing service;
- the Excel line, with a sheet that has one conditional-colour rule.

Three browsers × four profiles, all as designed; four points in OPTIONS. One gap on touch (a tap on held Redaction says nothing) → `proposal/web-ui-held-redaction-reason-on-tap.patch`, measured before and after.

### 5. Portal surfaces against patch 32's screenshots
63 screenshots. Text identical apart from the clock and, on purpose, the redact page ("Upload…" → "Back to the document"; status "Redaction comes back with the next update."). Pixels the same elsewhere apart from the known Chromium chip sliver. Drop overlay 6 of 6, no console errors.

## 2026-11-18 — session 30 (coordinator 21:30: merge patch 34; check my two diffs and "Keep what you arranged?" in the portal)

### 1. Last time's CI
Run on f177358: all nine jobs green.

### 2. Branches and merge
Checked all: `platform/foundation-pr` 5e63202, `platform/foundation` e2fb8c1 (parse-process bench work after patch 34), `main` e8cf326, `platform/web` b8f004c, `platform/web-test` 5c64d20, `platform/mobile-ui` fd5206c.
`platform/foundation` badecc0 ("Build log 63: patch 34") has foundation-pr's code exactly, so I merged it. Clean; **byte-identical to foundation-pr 5e63202**. Both my diffs are in as sent (`git apply -R --check` succeeds). My held-Redaction diff no longer applies: the Foundation fixed that more widely (AT-30).

### 3. Build and tests
Build `-warnaserror` 0 warnings. Tests 449 + 16 + 41 + 103 = **609 pass**, 0 fail, 6 skipped (the Foundation's).

### 4. Checks
- `p34.py`: the Arrange card on Sign out (portal) and on window close (Windows) — wording, keyboard, Esc, Save (kept file written), the next start (desks back, not asked again), two desks, Discard (kept file gone). The preview's data folder was pointed at a scratch folder (`XDG_CONFIG_HOME`) so the kept file could be watched.
- `enc44.py`: encoding rows 44 px on touch, 34 px with a mouse.
- `wrap.py`: phone close-card labels.
- `p33tap2.py`, `p34d.py`: held tools by tap and click.

Three browsers × four profiles, all as designed. One finding: on the portal, Save in this card keeps the desks in the session's data folder, which Sign out deletes → OPTIONS, with options; recommendation (b).

### 5. Portal surfaces against patch 33's screenshots
63 screenshots: pixel-identical (clock masked). Drop overlay 6 of 6, no console errors.

## 2026-11-24 — session 31 (coordinator 01:45: D-206, write the exact diff for the portal Arrange card)

### 1. Branches
Checked all: `platform/foundation-pr` 5e63202 (unchanged), `platform/foundation` e2fb8c1, `main` 4ab431e (D-206 to D-209), `platform/web` 744be4f, `platform/web-test` 36bf031, `platform/mobile-ui` 135eb21. Last CI on 13d94e9: all nine jobs green.

### 2. The diff
`proposal/web-ui-portal-arrange-signout-download.patch` against 5e63202. Details and measurements in HOOKS. Web's Sign out already waits for the connection's downloads, so I expect no new host code.

### 3. Proof
- `d206.py` (in `/home/claude/wk`): three browsers × four profiles, run with the diff and again without it.
- The portal changes as intended. The Windows profile gives identical results, and its card screenshots are pixel-identical apart from the clock.
- `so.py`: Cancel keeps you signed in; Save session… signs out.
- Tests: 614 pass with the diff (5 new). One Reader test failed once in the first full run; it passed in three reruns.
- `src` is back to 5e63202 on this branch.

## 2026-11-24 — session 32 (coordinator 02:05: D-215 wording)
Branches checked: `platform/foundation-pr` 5e63202, `platform/foundation` e2fb8c1, `main` 2320437, `platform/web` 744be4f, `platform/web-test` e186d3a, `platform/mobile-ui` 135eb21.
- Wrote `proposal/web-ui-d215-wording.patch`: "language" in the page-operation question, and "Read this file as…" for the encoding command and the card's radio group, plus the tests and proofs that name them.
- Checked with `d215.py` (in `/home/claude/wk`): three browsers × four profiles, 12 of 12. Tests: 609 pass.
- It applies together with the D-206 diff. `src` is back to 5e63202.
