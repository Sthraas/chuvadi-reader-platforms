# Web — build log

Branch `platform/web` in `Sthraas/chuvadi-reader-platforms`. Newest entries at the bottom.

## 2026-11-06 — kickoff, baseline and feasibility spike

### 1. Read the inputs
- Kickoff (Web job + programme rulebook), package report `docs/coordination/chuvadi-reader-platform-and-packages.md`, `docs/coordination/DESIGN-NOTE.md`.
- Design spec for Web: `docs/design-handoff/Portal & Android.dc.html` frames 12a (Sangam sign-in), 12b (portal Reader), 12c (Sangam gating).
- `platform/foundation` does not exist yet, so `docs/foundation/PLATFORM-INTERFACE.md` is not available. Will re-check each session.

### 2. Toolchain
- Sandbox: Ubuntu 24.04, 2 cores, 7 GB RAM.
- Installed .NET SDK 10.0.403 (runtime 10.0.14, same as Arun's) with the official `dotnet-install.sh --channel 10.0` into `/home/claude/.dotnet` (sandbox only).

### 3. Baseline: the Reader builds and tests clean on Linux
Upstream `arunshivab/chuvadi-reader` at `c7b9e44` (chuvadi-pdf 3.31.1 + Chuvadi.Fonts 1.0.0).
```
dotnet restore <Core|Ui|Tests csproj> --configfile ci/nuget.config
dotnet build tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj -c Release --no-restore   # 0 warnings, 0 errors
dotnet build src/ChuvadiReader.Ui/ChuvadiReader.Ui.csproj -c Release --no-restore           # 0 warnings, 0 errors
dotnet test  tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj -c Release --no-build      # 161 passed, 0 failed
```
The committed feed `ci/packages` already holds every package Core uses, so no `dotnet pack` of chuvadi-pdf was needed for the baseline.

### 4. Branch and import
- Created `platform/web` from `main` (`1d5ff21`).
- Imported the upstream tree at `c7b9e44` byte-for-byte (`git archive c7b9e44 | tar -x`). Checked with `diff -r` against the upstream clone: identical apart from build output. The root `README.md` is now the upstream one (the working repo's two-line README was replaced) so the import stays exact.
- Every later Web commit adds new files only; `git diff <import commit>..HEAD --diff-filter=M` must stay empty unless Arun approves an existing-file change.

### 5. Feasibility spike (scratch only, not committed)
A throwaway Blazor Server project referencing the unchanged `ChuvadiReader.Ui` and `ChuvadiReader.Core`:
- `AddRazorComponents().AddInteractiveServerComponents()`, host page rendering `ChuvadiReader.Ui.App` with `InteractiveServer`, `blazor.web.js`, the Ui stylesheets, and the Windows host's `theme.js` copied.
- Every Core service registered **scoped** (per user circuit) instead of singleton; stub picker, clipboard, print, window controls.
- `dotnet publish -c Release`: 0 warnings, 0 errors. Run from the publish folder (running the build output directly fails on static assets — the development static-asset handler looks for files under the project's `wwwroot`; publish output is the production path anyway).
- Headless Chrome (testing tool only) on `/`, `/library`, `/settings`: the unchanged Ui renders and is styled correctly, prerender and interactive circuit both work, 0 server errors.
- Memory of the host process: 93.5 MB idle, 116.7 MB after the first page, 134.1 MB after five page loads (untuned).

Findings that need Arun (see `DECISIONS-PENDING.md`):
- The dashboard greets "Good evening, Root." — `UserProfileService` reads the server's OS account name.
- Window buttons, "offline · on this device" and "nothing leaves this device" all show on the web.
- Core writes to the system temp folder, `%AppData%` and `Documents`, which a shared server process would share between users.
- The kickoff (no file stays after the session) and the design (persistent, encrypted per-user storage with a quota) disagree.

### 6. Blockers recorded
See `README.md` § Blockers.

### 7. Sangam integration read (read-only)
Cloned `arunshivab/sangam` at `v1.0.0-rc.16` (`d43a5ff`), read the client README, ADR-0003/0007/0017, the pilot guide and the sample. Answers in `SANGAM-INTEGRATION.md`. Nothing in that repo was changed.

### 8. Existing-file hooks drafted (not applied)
Drafted `IHostChrome` and hooks H0–H8 in a scratch copy, saved as `proposals/H0-H6-host-chrome.diff` and `proposals/H7-H8-save-folder-and-samples.diff` with `proposals/HOST-CHROME-PROPOSAL.md`.
- Core, Ui, tests: 0 warnings, 0 errors; 161/161 tests pass; WPF host compiles (`EnableWindowsTargeting=true`).
- Desktop rendering unchanged: rendered HTML of `/`, `/settings`, `/library` identical apart from flex-container whitespace and one HTML entity; headless-Chrome screenshots differ only in the clock and a blinking caret — the same as two runs of the unchanged build.

### 9. Decisions received (6 Nov)
No server storage; Sangam via our own code; TLS source pluggable (Pezhai being asked); no sharing; packages from `ci/packages`; session-only encrypted working copies; browser printing of the PDF; portal look moves to the Web portal UI chat. Recorded in `DECISIONS-PENDING.md`.

### 10. Server host built (`src/ChuvadiReader.Web`, commit `869e569`)
- Blazor Server host page rendering the unchanged `ChuvadiReader.Ui.App` (Interactive Server, no prerender), the Ui's stylesheets and fonts as the Windows `index.html` loads them, `theme.js` copied from the Windows host.
- All Reader services registered **scoped** (one set per browser session).
- `SessionSpace`: `{DataRoot}/users/{hash of Sangam sub}/sessions/{random id}/` with `uploads`, `outbox`, `print`; folders 0700; deleted when the circuit closes (`SessionLifetime`) and swept at start-up.
- Open: `WebFilePicker` opens the browser's chooser (directly while the click's user activation lasts, else a one-click prompt), uploads in 4 MB chunks to `/portal/upload/...` (same-origin check, owner check, strict order, size limits, extension allow-list identical to the desktop dialogs, first-bytes content check). Returns server paths, so the Reader opens them unchanged.
- Save / Save as / choose a folder: a path in the session outbox; `OutboxDelivery` polls (no inotify), and when a file is finished (size stable, no writer holding it) hands it to the browser as a single-use download link. `SessionAppStorage` points the Reader's default save folder at the session's own "Chuvadi Documents" folder.
- Print: the browser prints the PDF; a page range or a protected file gets a chuvadi-pdf print copy (`PageOperations.Assemble`); Safari opens the PDF in a new tab.
- Clipboard (Clipboard API) and external links (new tab, no opener).
- TLS: `ICertificateSource` with `PemFileCertificateSource` (reloads a renewed PEM pair without restart; keeps the old one if the new one is broken). Kestrel: no Server header, 64 KB default body limit raised per upload chunk.
- Security headers: CSP (self only; inline styles for the Ui; `data:` fonts for chuvadi-pdf's SVG pages), nosniff, SAMEORIGIN framing, no referrer, permissions policy, COOP/CORP, HSTS outside Development.
- Sign-in: Development/Testing only (`X-Dev-User` header picks the test person); any other environment refuses to start until the Sangam client exists.
- CI: `.github/workflows/web.yml` builds with warnings as errors, runs both test suites, publishes.

Results:
```
dotnet build src/ChuvadiReader.Web -c Release            # 0 warnings, 0 errors (TreatWarningsAsErrors)
dotnet test tests/ChuvadiReader.Web.Tests -c Release      # 47 passed, 3 consecutive runs
```
Browser flows (Playwright driving the machine's Chrome, test tool only), `tests/web-e2e/flows.py`:
- open a PDF through the left-bar Open (chooser opened directly, upload, Reader shows the page) — pass, 3.3 s;
- print the current page (one-page print copy served as `application/pdf`, `print()` called once) — pass;
- Merge two PDFs → `merged.pdf` downloaded, starts with `%PDF-`, 1.39 MB — pass;
- no console errors — pass (after adding `favicon.ico` and allowing `data:` fonts).
- Session files deleted ~180 s after the browser left (the 3-minute reconnect window).

Measurements: cold start 0.66–0.72 s; idle 100 MB; 172 MB after one full session (`ISOLATION-DECISION.md`).

Findings for the Reader chat / coordinator (in the proposal): Phase 0 sample recents/pins/watched folder on every empty start (H8); "Reset to default" save folder points at the server account's Documents (H7); server paths and folder choosers visible on the portal (H9); desktop clipboard reports "Copied" even when the clipboard was locked (the portal reports the failure instead).

### 11. Rebased on the Foundation (6 Nov)
- `git rebase --onto origin/platform/foundation <import> platform/web`: the three Web commits (new files only) moved onto `platform/foundation` @ `bb0e17a` (Group A applied). My own import commit was dropped; the Foundation carries the Reader tree.
- Withdrew the `IHostChrome` proposal (H0–H9): Foundation Group A (window buttons, status text) and the proposed Groups B/C (write-back, `IAppPaths`, `IAccount`, folder gating) cover it. Remaining gaps G1–G4 in `WEB-GAPS-AFTER-FOUNDATION.md`.
- Web host now uses the kit: `AddChuvadiReader(AppStateLifetime.PerConnection)`, then `WebPlatformInfo` (form factor from the browser width via `portal.js`, ⌘ on Mac browsers, no window buttons, account menu, server-side, saves as downloads), `SessionAppPaths` (app data and scratch inside the session folder), `WebAccount` (signed-in person), `WebFileWriteBack` (download on commit, files or whole folders), `WebClipboard` (`IClipboard` + `IImageClipboard`). `theme.js` now comes from the Ui (Group A12); the host copy was removed.
- Delivery: `OutboxDelivery.DeliverAsync` (write-back) and the outbox watch share one record of delivered file versions (path, size, time), so a save is downloaded once whichever path reports it, and a later re-save of the same file is delivered again.
- Checks: build 0 warnings/0 errors; 47/47 tests; browser flows all pass (open, print → PDF + `print()`, merge → download, no console errors); with Group A the portal shows no window buttons and the server status text; a 390 px touch viewport switches `<html data-form-factor>` to `phone`, back to `desktop` at 1440 px.
- Decisions received: own ACME client for Let's Encrypt; domain likely chuvadi.in (config); Sangam tested locally until it goes to production; E2E deployment last.

### 12. Decisions D-24 to D-54 read; branch pushed (6 Nov, afternoon)
- Read `docs/coordination/DECISIONS.md` on main. For Web: per-person workers (D-24), own ACME client (D-25), hooks into the Foundation's combined patch (D-26), certificate signing off (D-27), tmpfs + LUKS (D-28), appearance settings in browser storage (D-29), 30 min idle / 8 h absolute with a 5-minute warning (D-30), portal UI items D-31 to D-39, chuvadi-pdf 3.31.2 everywhere (D-54).
- Pushed the Foundation-based branch with `--force-with-lease` (approved), rebased again onto `platform/foundation` @ `60dca85` (Groups B and C applied): build 0/0, 47/47 tests, browser flows pass, Merge downloaded once (write-back and outbox watch agree).
- chuvadi-pdf 3.31.2 is not yet in `ci/packages` on `platform/foundation`; rebase when it is.

### 13. ACME client for Let's Encrypt (`src/ChuvadiReader.Web/Hosting/Acme/`)
Our own RFC 8555 client, BCL only:
- `AcmeJws`: base64url, P-256 JWK, RFC 7638 thumbprint, flattened JWS with ES256 (`jwk` on newAccount, `kid` after), POST-as-GET.
- `AcmeClient`: directory, nonces (Replay-Nonce kept; `badNonce` retried 3 times), account (terms must be agreed), order, http-01 per authorization, polling with Retry-After, finalize with a CSR for a fresh P-256 key naming every domain, PEM chain download; challenge tokens removed afterwards whatever happens.
- `Http01ChallengeStore` + `UseHttp01Challenges()`: answers only published tokens, GET only, ahead of HTTPS redirection and sign-in.
- `AcmeCertificateManager` (the `ICertificateSource` when ACME is on): loads the stored certificate at start, else serves a 2-day self-signed one so HTTPS comes up; installs a new certificate at once (Kestrel's certificate selector reads it per handshake) and writes key and chain atomically, owner-only. Renewal window = `RenewBeforeDays`, capped at a third of the lifetime.
- `AcmeRenewalService`: checks every 12 h; on failure keeps the current certificate, logs, retries after 10 min doubling up to 12 h.
- Startup fails fast if ACME is on without certificate paths, domains or account folder. Default directory is Let's Encrypt staging.

Tests (`AcmeTests.cs`, 16 new): a strict fake ACME server in the test project (our code) checks every signature, single-use nonces, the `url` header, jwk/kid use, POST-as-GET, CSR names, and validates http-01 by fetching from the portal. Covered: real portal first start orders, installs and **serves the new certificate on the same listener without restart** (TLS handshake checked); restart reuses certificate and account; renewal inside the window; 6-day/90-day windows; bad-nonce retry and give-up; failed validation; terms not agreed; same key → same account; challenge endpoint answers only published tokens; incomplete settings stop startup.
```
dotnet test tests/ChuvadiReader.Web.Tests -c Release   # 63 passed, 3 consecutive runs
```
Not done here: a run against Let's Encrypt **staging** needs the real domain pointing at the server (deployment step). Pebble (Let's Encrypt's own test server) would be an extra conformance check, but building it from source here was refused by my sandbox's safety check (external code); it can be run on the test VM if the coordinator wants it, test-only.

### 14. Sangam sign-in (`src/ChuvadiReader.Web/Auth/`)
Our own OpenID Connect client, BCL and ASP.NET Core only:
- `Jwt`, `JsonWebKey`: compact JWS parsing (no JWE, no `none`, size limit), RSA ≥ 2048 and EC P-256/384/521 keys, RS/PS/ES signature checks.
- `SangamMetadata`: discovery and JWKS, cached; unknown `kid` refreshes the keys (rate-limited).
- `JwtVerifier`: ID tokens (signature, algorithm allow-list, `crit` refused, `iss`, `aud`, `azp`, `exp`/`nbf`/`iat` with 2 min skew, `nonce`) and logout tokens (`typ` `logout+jwt`, back-channel event, no `nonce`, `jti`, `sid` or `sub`).
- `SangamSignIn`: `/signin` (Auth Code + PKCE S256, state, nonce; flow kept in a Data Protection cookie for 10 min), `/signin-sangam` (state and RFC 9207 `iss` check, code exchange with `private_key_jwt` or `client_secret_basic`, cookie sign-in, safe local return address only), `/signout` → Sangam end-session with `id_token_hint` → `/signout-sangam` → `/signed-out`, `POST /backchannel-logout`.
- `PortalSessions`: revoked sign-ins (cookie refused on the next request) and the open tabs of each sign-in; ending a tab deletes its files and sends the browser to `/signed-out` through `chvdPortal.leave` (our one-way call; `NavigationManager` from a request thread faulted the circuit).
- Cookie: `__Host-chvd` on https (`chvd.session` on local http), HttpOnly, SameSite=Lax, 8 h absolute, no sliding. `/portal/*` and `/_blazor` answer 401 instead of redirecting.
- Fixes found on the way: a re-entrant lock in key refresh (deadlock), tabs ended mid-redirect at `/signout` (now ended on the way back), the e2e wait loops (the Playwright sync API only sees navigations while it is called, so `time.sleep` made the back-channel check look flaky).
```
dotnet test tests/ChuvadiReader.Web.Tests -c Release   # 93 passed, 0 warnings, 3 runs
python3 tests/web-e2e/sangam_signin.py …               # real local Sangam: all checks pass, 4 runs in a row
```
Findings for Sangam's team are in `SANGAM-INTEGRATION.md` (`login_hint` unsupported, back-channel address set only from the operator console, Development logout-token issuer).

### 15. Rebased onto chuvadi-pdf 3.31.2 and the combined hooks (6 Nov, evening)
- `platform/foundation` @ `63af90f` has chuvadi-pdf 3.31.2 in `ci/packages` (D-54) and the combined hook patch (D-26). Rebased the seven Web commits (new files only, no conflicts); Core resolves `Chuvadi.Pdf.*` 3.31.2. Pdf A/B are no longer blockers (D-55).
- The patch's `AccountMenu` (12b) injects `PortalLinks`, so the host now registers it from `Portal:DesktopAppUrl` (default `https://chuvadi.in/download`, D-35), `Portal:AccountSettingsUrl` and `Portal:ForgotPasswordUrl` (empty hides them).
- `IAccount.Unit` (D-35): the name in Sangam's `sangam_org` claim (sent with the `org.current` scope), kept in the portal cookie; malformed claims give no unit.
- Browser flows updated for the portal's "Upload" label; the Sangam e2e now signs out from the account menu and checks it shows the person's name and Sangam ID.
- Checks: build 0/0; 100/100 tests; browser flows all pass; real local Sangam e2e passes 3 runs in a row.

### 16. Coordinator decisions of 6 Nov night
- Sign-in page: (a) — visitors go straight to Sangam until the Web portal UI chat's "Continue with Sangam"-only 12a lands (its U-9 (a)); then the host renders it. `login_hint` goes to Arun as a Sangam ask.
- `org.current` is now in the default scope, so the unit shows after the Sangam ID; people in several organisations see Sangam's chooser (intended). Real local Sangam e2e passes with it.
- F-3 (one pending path in `OpenDocumentService`): nothing to change in the host. Opening on the web goes through `PickDocumentAsync` (one file, `multiple: false`); the host never calls `OpenDocumentService.Request`; `PickDocumentsAsync` (Merge, Bench) returns a list that those pages use themselves. Any future multi-file open in the host must open one file at a time until the Foundation's queue lands.

### 17. Per-person workers behind our own gateway (D-24) — 7 Nov
- `Portal:Mode`: `Single` (one process; development, tests), `Gateway` (production), `Worker` (started by the gateway only). Same program and publish for all three.
- Gateway: TLS and ACME, Sangam sign-in, the session clock, static files, `/healthz`. Every other signed-in request goes to the person's worker through `GatewayRelay` (our own code): HTTP streamed both ways (upload chunks get the chunk limit, everything else the 64 KB default), and the circuit's WebSocket frame by frame. Browser `X-Chvd-*` headers, `X-Dev-User` and the gateway's own cookies never reach a worker; `/_worker/*` answers 404 to browsers.
- `WorkerPool`: one worker per person (start races give exactly one). Each has `{DataRoot}/workers/<key>/{home,tmp,data}` (0700), HOME/TMPDIR/XDG there, `DOTNET_GCHeapHardLimit`, no crash dumps, and none of the gateway's `Sangam__`/`Portal__`/URL settings. The shared secret goes on standard input, never the environment. The socket lives in a 0700 folder. It is started the way the gateway was (`dotnet` or the app host), with `DOTNET_ROOT` passed on. A worker is stopped (folder deleted) when it has had no circuit and no request for `IdleStop`, or stops answering three checks; it is replaced if it crashes. Supervision runs in parallel. `MaxWorkers` reached → "The portal is busy" page.
- Worker: listens only on its Unix socket. `GatewayIdentityHandler` accepts a request only with the secret and only for its own person. Control endpoints `/_worker/{health,end,notice}`. `GatewayLifeline`: end of standard input (gateway gone) stops it.
- `ITabControl` splits "which sign-ins count" (`PortalSessions`, where the cookie lives) from "the open tabs" (`OpenTabs`, where the circuits live). Back-channel logout and sign-out now reach tabs in workers.
- Data Protection keys are kept in memory (`InMemoryKeyRepository`): nothing written to disk, and no start-up warning. A restart ends every session anyway.
- Fixes on the way: workers didn't start through the app host where .NET isn't in a standard place (now started like the gateway, with `DOTNET_ROOT`); `HasExited` after a stop.
- Tests: 10 gateway tests with real worker processes (one per person, private env and folders, a worker refuses anyone but its gateway and its person, header spoofing, end and idle stop with the files removed, crash and replace, busy page, start race, health check, static files without a worker). Browser flows, real-Sangam e2e and expiry e2e all pass through the gateway.

### 18. Session expiry (D-30) — 7 Nov
- `SessionClock` (gateway or single process): per sign-in, idle 30 min, at most 8 h (`chvd_signin` claim), warning 5 min before. When the time is up the sign-in is revoked and its tabs ended.
- Activity is page loads, file transfers, and `POST /portal/activity` from the page's input (pointer, key, wheel, touch). Reports go out at most once per 1/30 of the idle limit (a minute). The request needs the portal's Origin and `X-Chvd-Activity`. Not counted: the circuit's WebSocket (its keep-alive pings would keep an abandoned tab alive) and static files.
- `ExpiryWarning` in every open tab, including tabs opened during the warning:
  - "I'm still here" (idle only);
  - "Download the open document(s)": a copy, or a ZIP of every open document the session may hand out;
  - "Download with your marks", which runs the Reader's own `m.saveas` when marks aren't saved.
- Fix found by the e2e: the portal's own components had no `_Imports.razor`, so `@onclick` was written into the HTML as text and the buttons did nothing. Added; the e2e now checks each button's effect.
- Tests: 8 clock and activity tests (manual clock) and `tests/web-e2e/expiry.py`.

### 19. Working copies in RAM (D-28) — 7 Nov
- `StorageCheck` at start-up outside Development refuses to start in two cases, with a message naming the problem:
  - `DataRoot` is not on tmpfs/ramfs (read from `/proc/self/mountinfo`);
  - an active swap isn't on dm-crypt (`/sys/block/dm-N/dm/uuid` starts with `CRYPT-`) or zram. Swap files are refused.
- Both checks can be turned off one by one (`Portal:Storage`). LUKS for the rest of the disk, log storage, core dumps and the systemd hardening are in the runbook.
- 5 tests with fake `/proc` and `/sys`, plus a refused production start.

### 20. Load test, health check, runbook — 7 Nov
- `tests/web-e2e/load.py` (Playwright, async): N people at once through the gateway, each with their own worker.
  - All succeeded at 3, 10 and 15 people.
  - 15 people (2-core sandbox shared with 15 headless browsers): ready 4.8 s median, upload+render 8.6 s, print 4.1 s.
  - Peak 15 workers, ~173 MB each; gateway ~110 MB. After everyone left, every worker stopped and its files were removed (reconnect window + idle stop).
- ReadyToRun publish measured: no gain in worker start (0.55–0.7 s either way), so not used for the web.
- `/healthz` (anonymous, `ok` only, starts no worker).
- `DEPLOYMENT-RUNBOOK.md`, rehearsed locally in the production configuration:
  - set-up: Production environment, gateway mode, app host, tmpfs data root, TLS on 8443 with `ASPNETCORE_HTTPS_PORT`;
  - passed: the D-28 refusal on a disk data root; the 307 to HTTPS; HSTS and CSP headers; real Sangam sign-in; the `__Host-chvd` Secure cookie; sign-out of every tab; workers and socket folder removed on stop;
  - not run: back-channel, because the local Sangam can't trust a self-signed certificate.
```
dotnet test tests/ChuvadiReader.Web.Tests -c Release   # 123 passed, 0 warnings
```

### 21. Second and third combined patches, the 12a sign-in page, L-8, restart banner — 7 Nov
- Rebased the Web commits onto `platform/foundation` @ `2fafb60` (second combined patch, `COMBINED-HOOKS-2.md`) without conflicts.
- History of the 12a integration:
  - I first took the Web portal UI chat's portal files straight from `0c99e19`. That broke the shared CI: the Foundation's Mobile UI preview and Web UI test copies still used the old types. I held it back, and the coordinator decided (a): the Foundation carries the files.
  - It did, in `5aaa271` (third combined patch, part 1). `platform/web` is rebuilt on `a4acc56` with the Web commits only; my take-and-hold commits are gone.
  - From now on, every push builds the whole shared solution with `-warnaserror` and runs all its tests first.
- **PortalLinks:** already registered by the host. It now takes two arguments (`DesktopAppUrl`, `AccountSettingsUrl`) from the Web portal UI chat's `0c99e19`. `Portal:ForgotPasswordUrl` is removed (no password field, D-34), and the desktop-app default is the Ui's own `PlaceholderDesktopAppUrl`. `PortalLinks` is registered in every mode, because the gateway renders the sign-in page.
- **12a sign-in page** (U-9 a; the portal files as the Foundation carries them in `5aaa271`):
  - `GET /signin` renders `PortalSignIn` to plain HTML on the server with its own tiny service set. No circuit is needed, so there's no worker before sign-in.
  - `js/signin.js` sends "Continue with Sangam" to `GET /signin/sangam` (the old redirect), with a safe return address. Sign-in failures show their reason on the same page.
  - The Sangam ID field stays off until Sangam pre-fills `login_hint`.
- **Fix:** `UseExceptionHandler("/error")` had no `/error` endpoint. Outside Development, an unexpected failure was sent to sign-in and looped until the address was too long. `/error` is now an anonymous page (test added). Found when the first version of the sign-in page threw in single mode, because Blazor's circuit navigation manager can't run outside a circuit; fixed by the page's own service set.
- **L-8:** `WebPrintService` refuses a file whose permissions forbid printing, with `PrintPermission.Refused`, before anything reaches the browser. Without this check the whole file would be handed over, and a range or password print copy would carry no protection at all. Tests: refused for whole and range prints, with no copy made; a protected file that allows printing still prints.
- **Multi-file open (F-3 queue):** nothing for the host to do. The Ui's open paths call the one-file picker, and the Ui has no drop handler yet (see the report).
- **Restart banner** (updates at quiet hours, announced in advance):
  - `MaintenanceAnnouncer` reads `Portal:MaintenanceNoticeFile` every 15 s. A time without its zone is refused with a log line.
  - `ITabControl.AnnounceAsync`; the gateway passes the notice to every worker, and to workers started later.
  - `MaintenanceBanner` shows bottom-left in every tab until the time passes or the file is removed.
  - 6 tests, plus a browser check.
- Checks: the whole shared solution builds with `-warnaserror`; its tests pass (Reader 171, Hosting 33, Mobile UI 11, Web UI 16); Web 136/136; the real-Sangam e2e through the gateway, now starting at 12a, passes.
- **Sangam unreachable:** "Continue with Sangam" and the callback show "Sangam can't be reached right now…" on the sign-in page (503), instead of an error page. Signing out still ends on the signed-out page, since the portal session is already over. 2 tests. Found when the local Sangam stopped during the e2e.
- Still to come from the Foundation, and needing no Web code: the optional `PortalLinks.TermsUrl`, with a "Terms of use" line under the sign-in card, is on the Web portal UI branch. The EULA's About page is coming too (coordinator: terms via About, through the Foundation). The portal drop zone is now a Foundation item.

### 22. Licences page, four-browser runs, Safari printing, test plan — 7 Nov
- Rebased onto `platform/foundation` @ `615afde` (third combined patch, part 2).
- **Licences page:** `PortalLinks` gets `TermsUrl` = `Portal:TermsUrl` (default `/licence`, also passed to workers), and the sign-in page shows "Terms of use".
  - `/licence` is the Foundation's `LicencesSection`, rendered to plain HTML (`StaticPages`, shared with the sign-in page), so it is readable before sign-in with no worker. `js/legal.js` turns its three-way switch into links (`?part=eula|licence|notices`; anything else shows the agreement).
  - In single mode it takes precedence over the Ui's own `/licence` only on full page loads.
- **S-1, sign-in on every endpoint:** `EndpointAuthTests` lists every route in single and gateway mode and fails on any anonymous route outside a fixed list. It also checks that the known protected routes really are protected.
- **Browser matrix:** `flows.py`, `sangam_signin.py` and `expiry.py` take `--browser chrome|chromium|firefox|webkit` (Playwright's own engines, test only). Fixes found by it:
  - **Safari printing:** Safari blocks a tab that the page opens after a server round trip, and can't print a PDF in a frame. The portal now shows "Open the PDF to print", a link the person clicks (their click is the gesture Safari needs).
  - **No PDF viewer in the page** (the person set PDFs to download): the hidden frame never loads. After 20 s the same link is offered, instead of failing after 60 s.
  - The browser now says which happened (`dialog`, `tab`, `failed`), and the Reader's message is true for both: "Sent 1 page to the browser's print dialog" or "Ready: open the PDF (1 page) from the link, then print it from its tab".
  - Test witnesses: the print check counts only its own request in the server log (it used to read the last line, which an earlier run could satisfy). Firefox's own messages on leaving a page aren't counted as portal errors.
- **`TEST-PLAN.md`** for the Web Test chat: 20 flows, 18 security checks, 12 Sangam failure cases, 8 load checks, the browser matrix, deployment checks, a run log and known gaps.
- Checks: the whole shared solution `-warnaserror` (0/0) and its tests; Web 140/140; flows in 4 engines; real-Sangam e2e and expiry e2e in Chrome, Firefox and WebKit; `load.py` 10/10.

### 23. Fourth combined patch, legal pages (D-86), drop refused (D-89) — 7 Nov, morning
- Rebased onto `platform/foundation` @ `e5802e6`: the third patch's part 3 (legal drafts and legal pages), single instance, and the fourth patch. Nothing in them needs Web host code except the legal pages:
  - single instance is desktop;
  - host notices: the Web host has none (kit default);
  - the portal wording W-1 to W-4 is Ui text.
- **D-86 (a), legal pages:** `/terms`, `/privacy` and `/licence` render the Foundation's `LicencesSection` to plain HTML before sign-in.
  - The renderer gives the page the Web platform info, so it shows the portal's documents: terms of use, privacy, cookies, third-party notices.
  - `js/legal.js` turns the switch into the four addresses.
  - `Portal:TermsUrl` now defaults to `/terms`, so the sign-in page's "Terms of use" opens it.
  - The texts are shown as shipped, DRAFT line included.
  - Tests: every page answers before sign-in with no worker; DRAFT and copyright present; the apps' EULA isn't shown on the portal; unknown parts open the terms. `/terms` and `/privacy` added to the route list.
- **D-86 (b):** the sign-in page has been live since the third patch; `web-12a-ready` is no longer needed.
- **D-86 (c):** `TEST-PLAN.md` now has the manual runs (M-1 Edge, M-2 Safari on Mac, M-3 Safari on iPhone and iPad, M-4 Android Chrome) as one 12-step sequence plus per-browser checks. It also has the staging runs: V-1 two-hour soak, V-2 real Let's Encrypt with a forced renewal, V-3 large documents, V-4 hostile documents, V-5 logs, V-6 restart with the banner, V-7 no DRAFT before go-live.
- **D-89, now:**
  - `WebCapabilities.DropFiles = false`. Nothing in the Ui reads the flag yet (option B's wording hasn't landed), so the flag alone didn't stop the trap: a browser opens a file dropped on a page that doesn't take it.
  - `portal.js` now cancels any file drop nothing in the page handled, with the "not allowed" cursor while dragging. The Reader's own image drops run first and are left alone.
  - `flows.py` checks the drop is cancelled in all four engines, and a control check confirms a page without the script doesn't cancel it.
- **D-89, next:** the host side of `IDroppedFiles` when the Foundation publishes it.
- For counsel (not changed; the drafts are the Foundation's): the terms say documents are processed "in an encrypted working area". Under D-28 the working copies are in RAM (tmpfs), never on disk, with swap encrypted; RAM itself isn't encrypted.
- Checks (local only; no CI runs until Actions billing is confirmed):
  - shared solution `-warnaserror` 0/0, its tests (Reader 171, Hosting 48, Mobile UI 15, Web UI 31), Web 140/140;
  - flows in 4 engines, 7/7 each;
  - legal pages in Chrome;
  - real-Sangam e2e through the gateway.

### 24. Drag and drop on the portal (D-89 A) — 7 Nov, mid-morning
- Rebased onto `platform/foundation` @ `4819d66`: the `IDroppedFiles` seam and the Ui's `PortalDropCatcher` (a full-window file input switched on while documents are dragged), and the CI changes (D-90).
- **`WebDroppedFiles`** (scoped, per session), as COMBINED-HOOKS-5 asks:
  - each dropped file is read once, inside the call, and streamed into the session's uploads folder through the same `UploadTicket` the upload endpoint uses. So drops get exactly the upload's checks and messages: allowed document types, `MaxUploadBytes`, content matching the extension, unique names, owner-only files;
  - each refusal is one short message ("fake.pdf isn't a valid PDF", "short.pdf didn't arrive completely", "… couldn't be uploaded" for a broken stream); half-written files are removed;
  - accepted files go to `IncomingFiles.Receive`, so they open one tab each, or land on the Bench shelf when it's open;
  - `MaxFileBytes` is `MaxUploadBytes`, so the browser stream stops at the same limit.
- `WebCapabilities.DropFiles = true`.
- `portal.js`: the stray-drop guard from step 23 stays (a drop before the catcher loads, or one that misses it, is still cancelled), but now leaves drops onto a file input alone, since that is the browser delivering the file to the catcher.
- Tests: `DroppedFilesTests` (two PDFs with the same name stored apart, owner-only, opened; an .exe, a fake PDF, an oversize file, an empty file and a short stream each refused with nothing left behind; folders stripped from a name). `flows.py`: a stray drop is cancelled, a fake PDF given to the catcher is refused with its message, a real PDF opens in the Reader.
- Checks: shared solution `-warnaserror` 0/0 and its tests (Reader 171, Hosting 48, Mobile UI 15, Web UI 31); Web 142/142; flows in 4 engines through workers, 9/9 each.

### 25. Web Test chat's first bugs (Q-4) — 8 Nov, evening
- Rebased onto `platform/foundation` @ `63f37b1` (seventh and eighth patches). That brings the phone shell (WT-03), the D-98 status text (WT-04) and the account menu's "Terms of use · Privacy" footer (WT-06); the Web Test chat re-checks them. `PortalLinks` now takes `PrivacyUrl`: `Portal:PrivacyUrl`, default `/privacy`, also passed to workers.
- **WT-01 (High):** the relay copied a worker's headers by replacing, so Blazor's `frame-ancestors 'self'` replaced the gateway's full policy on the Reader page. `Content-Security-Policy` is now appended; the browser enforces both, which leaves the stricter one. Test: a relayed `/` carries the full policy.
- **WT-07:** `/_blazor` refuses a foreign `Origin` in both modes. Opening the circuit (the negotiate POST, the WebSocket upgrade) must carry the portal's own origin. The closing page's beacon (`/_blazor/disconnect`) may carry none, since Safari sends it without one, and it can only end a circuit whose secret id it holds. Found by running WebKit, not by the unit tests. Tests in both modes.
- **WT-08:** names lose bidi controls (U+061C, U+200E, U+200F, U+202A–U+202E, U+2066–U+2069). Joiners stay, because Malayalam and Tamil need them. Tests: the name cleaner and a drop.
- **WT-11:** the package has no `web.config`, `appsettings.Development.json`, `.pdb` or `.xml`. Builds keep symbols for tests. `tests/web-e2e/check-package.sh` checks it in CI.
- **WT-12:** `web.yml` builds and publishes with `-warnaserror`, a newer push cancels the older run, and the package is checked. TEST-PLAN §0 gives the clean-clone restore. Web stays out of `ChuvadiReader.Platforms.slnx` (its tests need Linux; that solution runs on every runner), and §0 says so.
- **WT-13:** `load.py` creates its output folder. Page turns are timed until the next page is drawn and in view (no fixed waits). Each person gets their own browser process (`--browsers N` to share). Times are in ms.
- **O-1:** every call to Sangam (discovery, keys, token) has `Sangam:CallTimeout`, 10 s; a hang gives the "can't be reached" message.
- **O-2:** "Continue with Sangam" first probes Sangam (`Sangam:ProbeTimeout` 2 s, answer reused `Sangam:ProbeCacheFor` 30 s), so a Sangam that went down after discovery was cached shows our message instead of a dead page.
- Not for Web: WT-02, WT-09, WT-10 (shared Ui, to the Foundation); WT-05 (decided D-103, in the Foundation's patch).

### 26. WT-14 to WT-16 (D-129) — 9 Nov, early
- Rebased onto `platform/foundation` @ `f1e4126` (ninth patch: opening password-protected PDFs through the library).
- **WT-14:** `sangam_signin.py` now waits for the portal's signed-out page after sign-out, instead of network idle (WebKit could be idle on Sangam's end-session page before the redirect). WebKit 5 runs, 13/13 each.
- **WT-15:** outside Development and the test suite, start-up is refused unless `Sangam:Authority` is https. It is checked when the options are built, so a misconfigured portal never serves a page. Tests: http refused, https starts (Production, data root on tmpfs).
- **WT-16 / O-3 (one .zip for multi-file saves):** not built yet; it needs Chuvadi.Zip in `ci/packages`, which isn't there. The host side is ready to build: the Ui already commits a whole folder through `IFileWriteBack` after "Split to folder" and the like, so the host can zip the folder at that moment (two or more files → one `.zip`, one file → that file) and stop the outbox watcher delivering folder files one by one.

### 27. One .zip for multi-file saves (WT-16, D-129) and the Word limits (D-137) — 9 Nov, morning
- Rebased onto `platform/foundation` @ `1016987`: Chuvadi.Zip 1.0.0 in `ci/packages` (Arun's `zip-v1.0.0` asset, unchanged, SHA-256 recorded), Chuvadi.Docs 2.0.0 and Chuvadi.Sheets 2.0.2 with their limits and cancellation, the portal's "Upload" and "this session" wording.
- The portal references **Chuvadi.Zip 1.0.0** (Arun's library; no .NET compression in shipped code).
- **WT-16 / O-3:**
  - a folder from the folder picker is no longer watched file by file; its files wait for the Reader's write-back of the whole folder (Split to folder, Scatter, Bench and Reader exports all make that call);
  - on that call, two or more new files go out as **one .zip** (`ZipBundle`: streamed from each file with Chuvadi.Zip, owner-only, folder paths kept, named after what the files share, e.g. "report.zip", else "Chuvadi files.zip"); a single new file goes as itself; committing again sends nothing new; a failed hand-over can be retried;
  - Save and Save as folders (one file each) and the session's save folder still download each finished file as before.
- **D-137:** the portal keeps the shared Core's Word limits (20 MB per part, 64 MB in total) and Excel's untrusted-input limits; nothing on the host loosens them. Checked through the portal: a normal .docx opens with its double spaces as in the file; a .docx showing a 25 MB picture and a 100 KB zip bomb unpacking to 100 MB both say "too large to open"; the portal keeps answering.
- Tests: `ZipSaveTests` (one zip holding every file exactly, read back with .NET's reader as a test-only interoperability check; one file as itself; picked folders not sent file by file; save folders unchanged; names). `flows.py` step 4 (split → one .zip of every page). New `office_limits.py`.
- A Blazor "navigation cancelled" log line and Firefox's "WebSocket is not in the OPEN state" appeared only when a test left a page mid-update; the scripts now let the page settle, and neither appears in normal use.

### 28. chuvadi-pdf 3.32.0 on the portal (LIB-1, WT-17) — 9 Nov, morning
- Rebased onto `platform/foundation` @ `022b7c0`: chuvadi-pdf 3.32.0 (`EncryptionInfo.OpenedWith` / `EffectiveFlags`, the unsigned /P fix), the twelfth combined patch and the AT-03 typed registrations (D-146; same services, order and lifetimes). No host change needed.
- The published portal carries `Chuvadi.Pdf/3.32.0` (checked in `deps.json`).
- D-137 kept: the portal reports `ServerSide`, so Word files get the strict 20 MB per part and 64 MB in total (the desktop gets 100/400). New test `PortalLimitsTests` pins it. Layout's `ForUntrustedInput` is for when Layout arrives.
- Checks: shared solution 0 warnings and its tests (Reader 212, Hosting 64, Mobile UI 16, Web UI 39); Web 165/165; package check; `flows.py` 10/10 and `office_limits.py` 6/6 in Chrome and WebKit.

### 29. Patches 13 to 19 and the Web portal UI's latest — 10 Nov, morning
- Rebased onto `platform/foundation` @ `f88f9ef` (PR #12): Linux B-24 and B-25, owner-password printing, pages drawn off the Ui thread with no render backlog, memory given back after a heavy close, Chuvadi.Sheets 2.0.4. Merged Web portal UI `ce805d1` (its docs and preview tool; no shared Ui source beyond what the Foundation carries). No host change needed.
- **D-155:** the host never reads Excel files itself; every workbook goes through the shared `XlsxViewService`, which uses `XlsxReaderOptions.ForUntrustedInput()` with the open's cancellation (a closed tab, "Stop opening"). New test pins it from the portal side. **D-137** stays: Word files on the portal get 20 MB per part and 64 MB in total.
- **Memory relief on a shared server (MinGap):** the relief is per process. On the portal each person has their own worker, so a heavy close collects only that person's worker; the gateway and other people are never paused, and each worker runs it at most once per 30 s (plus the 65 s follow-up). Measured through the gateway with a PDF showing a 5000×5000-pixel image:
  - 1 person: worker 1021 MB → 224 MB within 10 s of closing the tab; at most 0.54 core busy; gateway 0.07 core.
  - 4 people closing at the same moment: workers 3572 MB → 867 MB within 10 s; at most 0.71 core busy across all of them; gateway 0.1 core; nothing slowed for anyone else.
  - So MinGap still protects the server: closes by different people run in parallel processes at small cost, and one person can't trigger collections back to back.
- **Capacity note (not a relief issue):** one such page costs about 1 GB in its worker while it's open. Five open at once filled this 8 GB test machine before anyone closed. On the 16 GB launch VM that's roughly a dozen people with very heavy pages at the same moment. Recorded for the staging run (TEST-PLAN L-9).
- Checks: shared solution 0 warnings and its tests; Web 166/166; package check; `flows.py` 10/10 in all four engines; `office_limits.py` 6/6 in Chrome and WebKit.
