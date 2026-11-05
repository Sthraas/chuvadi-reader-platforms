# Chuvadi Reader — Web portal

Blazor Server portal for Chuvadi Reader: the unchanged `ChuvadiReader.Ui` rendered on the server, Sangam sign-in, hosted on E2E Networks under a Chuvadi domain (a configuration value; not bought yet). Design spec: `docs/design-handoff/Portal & Android.dc.html` 12a–12c.

## Status (6 Nov 2026)
- Baseline import of chuvadi-reader `c7b9e44` done; Core, Ui and tests build and pass on Linux.
- Feasibility proven: the unchanged Ui runs under Blazor Server Interactive Server rendering.
- The server host project is **not committed yet**: its shape depends on decisions W-01 (storage) and W-02 (isolation) in `DECISIONS-PENDING.md`.

## Build (current state)
Requires the .NET 10 SDK (10.0.403 or later).
```
dotnet restore src/ChuvadiReader.Core/ChuvadiReader.Core.csproj --configfile ci/nuget.config
dotnet restore src/ChuvadiReader.Ui/ChuvadiReader.Ui.csproj --configfile ci/nuget.config
dotnet restore tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj --configfile ci/nuget.config
dotnet build tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj -c Release --no-restore
dotnet test tests/ChuvadiReader.Tests/ChuvadiReader.Tests.csproj -c Release --no-build
```
Run, package and install sections will be added with the host project.

## Blockers
| # | Blocker | Owner | Effect on Web |
|---|---|---|---|
| B1 | Pdf A — PDF name table never shrinks (report §5A) | Arun (library) | Not to production until decided. Option W-02(b) limits the growth to one user's worker. |
| B2 | Pdf B — shared LiPi FontRenderer race can drop Indic text (report §5A) | Arun (library) | Not to production until decided. W-02(b) limits it to one user's session. |
| B3 | Layout family unreleased; `Layout.Pdf` pins chuvadi-pdf [3.30.2] vs 3.31.1 | Library chats | Word/Excel exact-layout view, their printing and Save as PDF unavailable on the web, as on desktop. |
| B4 | Docs 2.0.0 not released (Core still on Docs 1.1.0) | Reader chat / Arun | The web uses whatever Core uses. |
| B5 | Sangam integration method unknown | Arun (W-04) | Sign-in page (12a) and gating can't be wired. |
| B6 | E2E Networks details (account, region, VM plans, DNS) | Arun | Deployment runbook can be drafted, not executed. |
