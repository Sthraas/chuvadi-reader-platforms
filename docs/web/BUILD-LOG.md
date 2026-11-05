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
