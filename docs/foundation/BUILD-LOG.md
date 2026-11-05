# Foundation — build log

## 2026-11-06 — session 1

### 1. Code and packages
- Cloned `arunshivab/chuvadi-reader` (read only). `main` = **c7b9e44** "chuvadi-pdf 3.31.1 (+ Chuvadi.Fonts 1.0.0) (#10)". The Reader chat's 3.31.1 upgrade **has landed**; Foundation builds on it.
- Cloned `arunshivab/chuvadi-pdf` at tag **v3.31.1** (38c82c2). Packed with the repo's own command (`build/pack.ps1`): `dotnet pack Chuvadi.slnx -c Release -p:Version=3.31.1` → 34 packages. Working tree clean before and after (library code not touched).
  - Note: a first pack without `-p:Version` produced 0.1.0 packages; discarded. The script uses the right command.
  - Sandbox-packed DLLs are not byte-identical to the 3.31.1 DLLs committed in chuvadi-reader `ci/packages` (embedded build paths); names and versions match.
- Downloaded release assets from `github.com/arunshivab/chuvadi/releases` and checked SHA-256:

| Package | SHA-256 | vs report |
|---|---|---|
| Chuvadi.Fonts 1.0.0 | c15a82d1…37f5fe | match |
| Chuvadi.Sheets 2.0.1 | 417f537f…71c253 | match |
| Chuvadi.Zip 1.0.0 | e019f9b6…110104 | match |
| Chuvadi.Markup 1.0.0 | 32574780…6a4192 | match |
| Chuvadi.Docs 1.5.1 (stop-gap, not used) | 102b682a…cd1049cbf | not in report |
| Chuvadi.Print 1.0.0-rc.2 | 252b6d10…1049cbf | not in report (record lives in the Print project) |
| Chuvadi.Print.Ipp 1.0.0-rc.2 | 82304b78…c4aa562 | not in report |
| Chuvadi.Print.Windows 1.0.0-rc.2 | df1ab37a…527b375 | not in report |
| Chuvadi.Print.Remote 1.0.0-rc.2 | 97388531…dbf7ebbf | not in report |

- `scripts/setup-feed.sh` (new) reproduces the feed into `./localpackages` (the path the repo's `nuget.config` already uses).

### 2. Working repo
- Access to `Sthraas/chuvadi-reader-platforms` arrived mid-session. Its `main` holds `README.md` + `docs/` (design handout, coordination).
- `platform/foundation` = chuvadi-reader `main` (c7b9e44) merged with the working repo's `main` (unrelated histories), keeping chuvadi-reader's `README.md`. `src/` and `tests/` are identical to chuvadi-reader `main`.

### 3. Baseline on Linux
- .NET SDK 10.0.403 (sandbox). `dotnet build` of Core, Ui, tests: **0 warnings, 0 errors**. `dotnet test`: **161/161 pass**. (The Windows host can't build here: WPF.)

### 4. Inventory and design
- `docs/foundation/INVENTORY.md`: every host-specific item in Core and Ui with file:line.
- `docs/foundation/PLATFORM-INTERFACE.md`: the draft contract and decisions F-1…F-6.
- New projects (new files only):
  - `src/ChuvadiReader.Platform` — contracts (`IPlatformInfo`, `IFileWriteBack`, `IAppPaths`, `IAccount`, `IClipboard`, `IFileManager`, `IShare`, `IAppLifecycle`, `IAppCommands`).
  - `src/ChuvadiReader.Hosting` — `AddChuvadiReader(AppStateLifetime)`, desktop defaults, key labels, command registry.
  - `tests/ChuvadiReader.Hosting.Tests` — 11 tests: every service resolves (process and per-connection), per-connection isolation, host override wins, drift guard against `Windows/App.xaml.cs`, macOS key labels, command routing.
  - `ChuvadiReader.Platforms.slnx` — programme solution; the existing `ChuvadiReader.slnx` is unchanged.
- Build of `ChuvadiReader.Platforms.slnx`: **0 warnings, 0 errors**; tests **172/172 pass** (161 + 11).
