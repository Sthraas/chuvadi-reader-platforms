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
