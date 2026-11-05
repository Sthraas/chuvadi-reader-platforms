# Foundation — build and run

## Prerequisites
- .NET SDK 10.0 (10.0.4xx), git, curl, sha256sum (Linux/macOS; on Windows use Git Bash or WSL for the feed script).

## Package feed
```bash
scripts/setup-feed.sh
```
Creates `./localpackages` (git-ignored), which the repo's `nuget.config` already points to: chuvadi-pdf 3.31.1 packed from the unchanged tag, released Chuvadi packages with checksums, and LiPicons.Blazor / Docs 1.1.0 / Sheets 1.1.2 from `ci/packages` (what Core pins today).

## Build and test (any OS)
```bash
dotnet build ChuvadiReader.Platforms.slnx -c Release
dotnet test  ChuvadiReader.Platforms.slnx -c Release --no-build
```
Expected: 0 warnings, 0 errors, all tests pass.

## Windows app (Windows only)
```powershell
dotnet build ChuvadiReader.slnx -c Release
dotnet run --project src/ChuvadiReader.Windows -c Release
```

## Writing a host
See `PLATFORM-INTERFACE.md` §1-§2 and `HANDOFF.md` (written once Arun has decided F-1…F-6).
