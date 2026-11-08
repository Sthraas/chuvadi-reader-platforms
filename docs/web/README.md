# Chuvadi Reader — Web portal

Blazor Server portal for Chuvadi Reader: the unchanged `ChuvadiReader.Ui` rendered on the server, Sangam sign-in, hosted on E2E Networks under a Chuvadi domain (a configuration value; not bought yet). Design spec: `docs/design-handoff/Portal & Android.dc.html` 12a–12c.

## Status (7 Nov 2026)
- Server host built: the unchanged Ui under Blazor Server; uploads, downloads, browser printing, session folders deleted at session end; pluggable TLS certificate; security headers; 123 tests; web CI.
- **Per-person workers behind our own gateway (D-24)** built: `Portal:Mode=Gateway` relays each person's HTTP and circuit WebSocket over a Unix socket to their own worker process (private HOME/TMPDIR, memory cap, secret on standard input, ends with the gateway).
- **Session expiry (D-30)**: 30 minutes idle, 8 hours at most, a warning in every open tab 5 minutes before that offers the open documents (and the document with unsaved marks) as downloads.
- **Working copies in RAM (D-28)**: outside Development the portal refuses to start unless `DataRoot` is on tmpfs and swap is off, dm-crypt or zram.
- Load-tested with real browsers through the gateway: 15 people at once, all succeeded; ~175 MB per active person. Deployment runbook ready: `DEPLOYMENT-RUNBOOK.md` (rehearsed locally in the production configuration).
- Sangam sign-in built (our own OpenID Connect client, `src/ChuvadiReader.Web/Auth/`): tested in CI against a fake Sangam (our test code) and end to end against a real Sangam run locally (read-only, test only), including sign-out and back-channel logout ending open tabs.
- Based on `platform/foundation` (Group A applied); services through `AddChuvadiReader(AppStateLifetime.PerConnection)` with the portal's own `IPlatformInfo`, `IAppPaths`, `IAccount`, `IFileWriteBack`, `IClipboard`.
- Own ACME client (Let's Encrypt) built and tested against a strict fake ACME server (our test code).
- Based on `platform/foundation` @ `63af90f`: chuvadi-pdf 3.31.2 (D-54; Pdf A/B cleared, D-55) and the combined hooks (D-26), so the portal shows the 12b account menu, the server status dot and the signed-in person; the host supplies `PortalLinks` and `IAccount.Unit`.
- Rebased on `platform/foundation` @ `a4acc56` (third combined patch, part 1: the Web portal UI's decided portal files; licence and EULA). The 12a sign-in page ("Continue with Sangam" only, U-9 a) is served at `/signin`; `PortalLinks` takes two arguments. Browser printing refuses files whose permissions forbid it (L-8). Planned restarts are announced with a banner in every open tab.
- On `platform/foundation` @ `e5802e6` (fourth combined patch). D-86: `/terms`, `/privacy` and `/licence?part=cookies|notices` serve the Foundation's portal documents before sign-in, kept marked DRAFT; "Terms of use" on the sign-in page opens `/terms`. D-89: `DropFiles = false`, and a dropped file is refused instead of the browser opening it and leaving Chuvadi.
- Printing works in Safari and in browsers without a PDF viewer (an "Open the PDF to print" link the person clicks). The browser flows, sign-in and expiry e2e run in Chrome, Firefox and WebKit.
- Test plan for the Web Test chat: `TEST-PLAN.md`.
- On `platform/foundation` @ `4819d66`. D-89 A: documents dropped on the portal stream into the session's working copy through the upload's own checks and open in the Reader (`WebDroppedFiles`, `DropFiles = true`).
- On `platform/foundation` @ `63f37b1` (seventh and eighth patches: phone shell, D-98 wording, legal links in the account menu). Fixes for the Web Test chat's WT-01, 07, 08, 11, 12, 13 and O-1, O-2 (BUILD-LOG step 25).
- On `platform/foundation` @ `1016987`. Several files from one save download as one .zip, written with Chuvadi.Zip (D-129); the strict Word limits hold on the portal (D-137). BUILD-LOG step 27.
- Next: the Web Test chat's re-checks. Domain and E2E stay last (Arun).

## Build and test
Requires the .NET 10 SDK (10.0.403 or later). Packages come from the committed `ci/packages` feed.
```
dotnet restore src/ChuvadiReader.Web/ChuvadiReader.Web.csproj --configfile ci/nuget.config
dotnet restore tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj --configfile ci/nuget.config
dotnet build tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj -c Release --no-restore -warnaserror
dotnet test tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj -c Release
```

## Run locally (Development sign-in)
```
cd src/ChuvadiReader.Web
ASPNETCORE_ENVIRONMENT=Development dotnet run                         # one process
ASPNETCORE_ENVIRONMENT=Development Portal__Mode=Gateway dotnet run    # as in production: gateway + a worker per person
```
Session files go to `src/ChuvadiReader.Web/.portal-data` (git-ignored) and are deleted when the browser session ends. Browser tests: `tests/web-e2e/README.md`.

## Configuration (`Portal` section, or `Portal__…` environment variables)
| Key | Meaning |
|---|---|
| `Mode` | `Single` (default; development, tests) or `Gateway` (production, D-24). `Worker` is set by the gateway only |
| `PublicOrigin` | The portal's https address, e.g. `https://chuvadi.in` (config value; required outside Development) |
| `DataRoot` | Folder for session files; production: a tmpfs (D-28) |
| `Storage:RequireMemoryFileSystem`, `Storage:RequireEncryptedSwap` | D-28 start-up checks, on outside Development |
| `MaintenanceNoticeFile` | Planned-restart banner in every open tab: line 1 the time with its zone, optional line 2 the text (runbook §9) |
| `IdleTimeout`, `ExpiryWarning`, `ExpiryCheckInterval` | 30 min, 5 min, 15 s (D-30); the 8-hour limit is `Sangam:AbsoluteSessionLifetime` |
| `Workers:MaxWorkers`, `Workers:MemoryLimitMB` | 40 people at once, 1536 MB heap cap per worker (size them with the runbook's table) |
| `Workers:IdleStop`, `Workers:CheckInterval`, `Workers:StartTimeout` | 2 min with no open tab, 30 s, 30 s |
| `Workers:SocketFolder`, `Workers:Command` | Socket folder (production `/run/chuvadi-portal`); the program to start (default: this one, started the same way) |
| `MaxUploadBytes`, `MaxFilesPerPick`, `UploadChunkBytes` | Upload limits (200 MB, 50 files, 4 MB chunks) |
| `PickTimeout`, `DownloadLinkLifetime`, `SaveWaitLimit` | 30 min, 10 min, 30 min |
| `AllowCertificateUpload` | Off (D-27) |
| `TermsUrl` | "Terms of use" on the sign-in page and in the account menu; default `/terms` (served before sign-in, D-86). Empty hides it |
| `PrivacyUrl` | "Privacy" beside it (D-97); default `/privacy`. Empty hides it |
| `Sangam:CallTimeout` | Longest any call to Sangam may take (discovery, keys, token); default 10 s (O-1) |
| `Sangam:ProbeTimeout`, `Sangam:ProbeCacheFor` | "Continue with Sangam" first checks Sangam answers within 2 s; the answer is reused for 30 s (O-2) |
| `DesktopAppUrl` | "Get the desktop app" in the account menu (D-35); placeholder `https://chuvadi.in/download` |
| `AccountSettingsUrl` | "Account settings" → Sangam's self-service site (D-35); empty hides the item until its address is known |
| `Tls:CertificatePath`, `Tls:KeyPath`, `Tls:ReloadCheck` | PEM pair served by Kestrel (with ACME off: re-read every 5 min when changed; with ACME on: where issued certificates are stored) |
| `Tls:Acme:Enabled` | Our own ACME client orders and renews Let's Encrypt certificates and swaps them in without restart |
| `Tls:Acme:DirectoryUrl` | Default Let's Encrypt **staging**; set `https://acme-v02.api.letsencrypt.org/directory` for production |
| `Tls:Acme:Domains`, `Tls:Acme:ContactEmails` | e.g. `chuvadi.in`, `www.chuvadi.in`; expiry mail address |
| `Tls:Acme:AgreeToTermsOfService` | Must be set to `true` by Arun (Let's Encrypt subscriber agreement) |
| `Tls:Acme:AccountFolder` | Holds `account.key.pem` (owner-only) |
| `Tls:Acme:RenewBeforeDays`, `CheckInterval`, `RetryAfterFailure` | 30 days (capped at a third of the lifetime), 12 h, 10 min doubling |

The server must listen on port 80 as well as 443: Let's Encrypt checks `http://<domain>/.well-known/acme-challenge/…`. Those requests are answered before HTTPS redirection and sign-in; every other port-80 request is redirected to HTTPS.

## Sign-in (`Sangam` section, or `Sangam__…` environment variables)
Without `Sangam:Authority` and `Sangam:ClientId` the portal uses the Development sign-in in Development and Testing, and refuses to start anywhere else.

| Key | Meaning |
|---|---|
| `Authority` | Sangam's issuer, e.g. `https://sangamid.in/` (discovery is read from `.well-known/openid-configuration`) |
| `ClientId` | The portal's client id registered with Sangam |
| `PrivateKeyPath`, `PrivateKeyId` | ES256 key (PEM) and its registered key id for `private_key_jwt` (preferred) |
| `ClientSecret` | Otherwise a client secret (`client_secret_basic`); set it as an environment variable, never in a file in the repo |
| `Scope`, `UiLocales` | `openid profile email org.current` (`org.current` gives the unit after the Sangam ID, 12b; people in several organisations see Sangam's chooser, which is intended); optional `en`, `hi` or `ml` |
| `CallbackPath`, `SignedOutCallbackPath`, `BackChannelLogoutPath` | `/signin-sangam`, `/signout-sangam`, `/backchannel-logout` — register these three addresses with Sangam |
| `ClockSkew`, `SignInTimeLimit`, `AbsoluteSessionLifetime` | 2 min, 10 min to finish signing in, 8 h per sign-in (D-30) |

### Testing against a real Sangam run locally
Sangam stays read-only; a copy is exported with `git archive` and run in Development (PostgreSQL 16 with Sangam's `deploy/postgres/init.sql`):
```
Sangam__Issuer=http://localhost:5100/ \
Sangam__Clients__chuvadi__ClientId=chuvadi-portal Sangam__Clients__chuvadi__Kind=application \
Sangam__Clients__chuvadi__BaseUrl=http://localhost:5600/ Sangam__Clients__chuvadi__Secret=<local test secret> \
ASPNETCORE_URLS=http://localhost:5100 dotnet Sangam.Identity.Server.dll
# back-channel address (Sangam sets it only from its operator console; locally by SQL):
psql -c "update apps set back_channel_logout_uri='http://localhost:5600/backchannel-logout' where client_id='chuvadi-portal'"
# portal:
ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://localhost:5600 Portal__DataRoot=<folder> \
Sangam__Authority=http://localhost:5100/ Sangam__ClientId=chuvadi-portal Sangam__ClientSecret=<local test secret> dotnet ChuvadiReader.Web.dll
python3 tests/web-e2e/sangam_signin.py http://localhost:5600 http://localhost:5100 <out folder>
```

Package, install and production deployment: `DEPLOYMENT-RUNBOOK.md`.

## Blockers
| # | Blocker | Owner | Effect on Web |
|---|---|---|---|
| B3 | Layout family unreleased; `Layout.Pdf` pins chuvadi-pdf [3.30.2] vs 3.31.1 | Library chats | Word/Excel exact-layout view, their printing and Save as PDF unavailable on the web, as on desktop. |
| B4 | Docs 2.0.0 not released (Core still on Docs 1.1.0) | Reader chat / Arun | The web uses whatever Core uses. |
| B5 | Portal domain not bought | Arun | Sangam client registration (redirect addresses) and TLS certificate wait for it. |
| B6 | E2E Networks details (account, region, VM plans, DNS) | Arun | Deployment runbook can be drafted, not executed. |
