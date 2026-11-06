# Chuvadi Reader — Web portal

Blazor Server portal for Chuvadi Reader: the unchanged `ChuvadiReader.Ui` rendered on the server, Sangam sign-in, hosted on E2E Networks under a Chuvadi domain (a configuration value; not bought yet). Design spec: `docs/design-handoff/Portal & Android.dc.html` 12a–12c.

## Status (6 Nov 2026)
- Server host built: the unchanged Ui under Blazor Server; uploads, downloads, browser printing, session folders deleted at session end; pluggable TLS certificate; security headers; 47 tests; web CI.
- Sign-in is Development-only until the Sangam client (our own code) lands — next step.
- Open decisions: isolation (W-02, `ISOLATION-DECISION.md`), existing-file hooks (W-05, `proposals/`), W-08 to W-11 in `DECISIONS-PENDING.md`.

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
| `PublicOrigin` | The portal's https address (the domain is a config value; required outside Development) |
| `DataRoot` | Folder for session files (production: RAM-backed or encrypted volume, see W-09) |
| `MaxUploadBytes`, `MaxFilesPerPick`, `UploadChunkBytes` | Upload limits (200 MB, 50 files, 4 MB chunks) |
| `PickTimeout`, `DownloadLinkLifetime`, `SaveWaitLimit` | 30 min, 10 min, 30 min |
| `AllowCertificateUpload` | Off (W-08) |
| `Tls:CertificatePath`, `Tls:KeyPath`, `Tls:ReloadCheck` | PEM pair served by Kestrel, re-read every 5 min when changed |

Package, install and production deployment (E2E runbook) sections will follow.

## Blockers
| # | Blocker | Owner | Effect on Web |
|---|---|---|---|
| B1 | Pdf A — PDF name table never shrinks (report §5A) | Arun (library) | Not to production until decided. Option W-02(b) limits the growth to one user's worker. |
| B2 | Pdf B — shared LiPi FontRenderer race can drop Indic text (report §5A) | Arun (library) | Not to production until decided. W-02(b) limits it to one user's session. |
| B3 | Layout family unreleased; `Layout.Pdf` pins chuvadi-pdf [3.30.2] vs 3.31.1 | Library chats | Word/Excel exact-layout view, their printing and Save as PDF unavailable on the web, as on desktop. |
| B4 | Docs 2.0.0 not released (Core still on Docs 1.1.0) | Reader chat / Arun | The web uses whatever Core uses. |
| B5 | Portal domain not bought | Arun | Sangam client registration (redirect addresses) and TLS certificate wait for it. |
| B6 | E2E Networks details (account, region, VM plans, DNS) | Arun | Deployment runbook can be drafted, not executed. |
