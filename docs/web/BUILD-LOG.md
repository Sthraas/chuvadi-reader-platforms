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
