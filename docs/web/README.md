# Chuvadi Reader — Web portal

Blazor Server portal for Chuvadi Reader: the unchanged `ChuvadiReader.Ui` rendered on the server, Sangam sign-in, hosted on E2E Networks under a Chuvadi domain (a configuration value; not bought yet). Design spec: `docs/design-handoff/Portal & Android.dc.html` 12a–12c.

## Status (6 Nov 2026)
- Server host built: the unchanged Ui under Blazor Server; uploads, downloads, browser printing, session folders deleted at session end; pluggable TLS certificate; security headers; 47 tests; web CI.
- Sign-in is Development-only until the Sangam client (our own code) lands — next step.
- Based on `platform/foundation` (Group A applied); services through `AddChuvadiReader(AppStateLifetime.PerConnection)` with the portal's own `IPlatformInfo`, `IAppPaths`, `IAccount`, `IFileWriteBack`, `IClipboard`.
- Own ACME client (Let's Encrypt) built and tested against a strict fake ACME server (our test code). Next: Sangam client tested against a local Sangam.
- Open decisions: isolation (W-02, `ISOLATION-DECISION.md`), gaps G1–G4 (`WEB-GAPS-AFTER-FOUNDATION.md`), W-08 to W-11 in `DECISIONS-PENDING.md`.

## Build and test
Requires the .NET 10 SDK (10.0.403 or later). Packages come from the committed `ci/packages` feed.
```
dotnet restore src/ChuvadiReader.Web/ChuvadiReader.Web.csproj --configfile ci/nuget.config
dotnet restore tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj --configfile ci/nuget.config
dotnet build src/ChuvadiReader.Web/ChuvadiReader.Web.csproj -c Release --no-restore
dotnet test tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj -c Release
```

## Run locally (Development sign-in)
```
cd src/ChuvadiReader.Web
ASPNETCORE_ENVIRONMENT=Development dotnet run
```
Session files go to `src/ChuvadiReader.Web/.portal-data` (git-ignored) and are deleted when the browser session ends.

## Configuration (`Portal` section, or `Portal__…` environment variables)
| Key | Meaning |
|---|---|
| `PublicOrigin` | The portal's https address, e.g. `https://chuvadi.in` (config value; required outside Development) |
| `DataRoot` | Folder for session files (production: RAM-backed or encrypted volume, see W-09) |
| `MaxUploadBytes`, `MaxFilesPerPick`, `UploadChunkBytes` | Upload limits (200 MB, 50 files, 4 MB chunks) |
| `PickTimeout`, `DownloadLinkLifetime`, `SaveWaitLimit` | 30 min, 10 min, 30 min |
| `AllowCertificateUpload` | Off (W-08) |
| `Tls:CertificatePath`, `Tls:KeyPath`, `Tls:ReloadCheck` | PEM pair served by Kestrel (with ACME off: re-read every 5 min when changed; with ACME on: where issued certificates are stored) |
| `Tls:Acme:Enabled` | Our own ACME client orders and renews Let's Encrypt certificates and swaps them in without restart |
| `Tls:Acme:DirectoryUrl` | Default Let's Encrypt **staging**; set `https://acme-v02.api.letsencrypt.org/directory` for production |
| `Tls:Acme:Domains`, `Tls:Acme:ContactEmails` | e.g. `chuvadi.in`, `www.chuvadi.in`; expiry mail address |
| `Tls:Acme:AgreeToTermsOfService` | Must be set to `true` by Arun (Let's Encrypt subscriber agreement) |
| `Tls:Acme:AccountFolder` | Holds `account.key.pem` (owner-only) |
| `Tls:Acme:RenewBeforeDays`, `CheckInterval`, `RetryAfterFailure` | 30 days (capped at a third of the lifetime), 12 h, 10 min doubling |

The server must listen on port 80 as well as 443: Let's Encrypt checks `http://<domain>/.well-known/acme-challenge/…`. Those requests are answered before HTTPS redirection and sign-in; every other port-80 request is redirected to HTTPS.

Package, install and production deployment (E2E runbook) sections will follow.

## Blockers
| # | Blocker | Owner | Effect on Web |
|---|---|---|---|
| B1 | Pdf A and Pdf B fixed in chuvadi-pdf 3.31.2 (D-54) | Foundation packs 3.31.2 into `ci/packages` | Production waits for the rebase onto 3.31.2 |
| B3 | Layout family unreleased; `Layout.Pdf` pins chuvadi-pdf [3.30.2] vs 3.31.1 | Library chats | Word/Excel exact-layout view, their printing and Save as PDF unavailable on the web, as on desktop. |
| B4 | Docs 2.0.0 not released (Core still on Docs 1.1.0) | Reader chat / Arun | The web uses whatever Core uses. |
| B5 | Portal domain not bought | Arun | Sangam client registration (redirect addresses) and TLS certificate wait for it. |
| B6 | E2E Networks details (account, region, VM plans, DNS) | Arun | Deployment runbook can be drafted, not executed. |
