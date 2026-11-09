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
| Chuvadi.Fonts 1.0.0 | `c15a82d1caa3d70f3e2abe16dd94201ea1d3dae91764735a19ffa7398c37f5fe` | match |
| Chuvadi.Sheets 2.0.1 | `417f537f74826deeb8cd14492441800243b45df9e714cd9ce6daf9138571c253` | match |
| Chuvadi.Zip 1.0.0 | `e019f9b61d48d705e9b8e81e3ca8bcbb3114056b2127f4e9ea2af0aa51110104` | match |
| Chuvadi.Markup 1.0.0 | `3257478005d2a159e8cf9d88899876dd75a419b8d2cd7d7d6b6754f9213a4192` | match |
| Chuvadi.Docs 1.5.1 (stop-gap, not used) | `102b682a5820110cd547ea648db6d87dedbf57906ef33d2a1a26730c4df1c265` | not in report |
| Chuvadi.Print 1.0.0-rc.2 | `252b6d10204d37069a35040ea89d58e1662a452c4e05fd90a0d8b90cd1049cbf` | not in report (record lives in the Print project) |
| Chuvadi.Print.Ipp 1.0.0-rc.2 | `82304b782ce23ac5dcb3895e1fee31898abf3c22222f9f9c65c423fba68aa562` | not in report |
| Chuvadi.Print.Windows 1.0.0-rc.2 | `df1ab37a48786ca5f1822e033b2f0fd45ba7339d9850140365360defb527b375` | not in report |
| Chuvadi.Print.Remote 1.0.0-rc.2 | `973885310888f3ec683633e1e94db1950d30ab0a7c0c2a07df11678794e7ebbf` | not in report |

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

### 5. Existing-file edits — proposal only
- Made the proposed edits on a local scratch branch (never pushed); exported as `docs/foundation/proposal/foundation-edits-1.patch` (23 files, +290/−66), explained in `docs/foundation/EDITS-FOR-APPROVAL.md` (Group A diffs; Groups B/C wait for decision F-1).
- Verified with the patch applied: Platforms solution 0 warnings, 172/172 tests; WPF host **compiled** on Linux with `-p:EnableWindowsTargeting=true` (0 warnings) — running it needs Arun's Windows machine.
- `git apply --check` of the patch on `platform/foundation`: clean.
- Fixed in my own code while doing this: WPF has no `SetDataObject` retry overload (WinForms-only) → own retry loop in `WpfClipboard`; `DesktopAppPaths.WorkingFolder` now equals `Path.GetTempPath()` so moving Core onto it later changes nothing on desktop; drift test lists the two new host seams.

### 6. CI
- Existing `.github/workflows/ci.yml` (Ubuntu/macOS/Windows, `main` only) left unchanged.
- New `.github/workflows/platform-build.yml` (reusable job: runner, build, test, build-args, workloads, label, full-feed) and `.github/workflows/platforms.yml` (on `platform/**`): shared code on ubuntu x64, ubuntu arm64, macOS, Windows; the Windows app on Windows; the full feed reproduced from the tag. All builds `-warnaserror`.
- Local check of the CI restore path (`--configfile ci/nuget.config`, clean package cache) + `-warnaserror`: 0 warnings, 0 errors.

### 7. First CI run (ae24bcf) and fixes
- Passed: shared code on ubuntu-latest, ubuntu-24.04-arm, macos-latest, windows-latest; the unchanged Windows app on windows-latest (`ChuvadiReader.slnx`, `-warnaserror`, 161 tests).
- Failed: `feed` — chuvadi-pdf's nuget.config needs Chuvadi.Fonts in its git-ignored `.fonts-feed` (their `build/fetch-fonts.ps1`). It passed locally only because the package cache already had it. Fixed: `setup-feed.sh` now does the same fetch with the SHA-256 check. Re-verified with an empty package cache: 45 packages, build 0 warnings.

### 8. Signal for the UI chats
- Coordinator (6 Nov): Mobile app UI and Web portal UI chats join; they need a platform + form-factor signal.
- Added `ShellLayout` (Desktop / Tablet / Phone / Portal) + `ShellLayouts.From/Key/Shell()` to the contracts (7 new tests, 18 in the kit). Group A now also writes `<html data-shell>` and cascades `PlatformState.Shell`. Guide: `FOR-UI-CHATS.md`.
- Patch regenerated (23 files, +290/−66), re-verified: Platforms solution and WPF host compile with `-warnaserror`, 179/179 tests.

### 9. Decisions applied (coordinator, 6 Nov)
- Group A applied (aeeac43): 0 warnings incl. WPF host compile, 179/179 tests.
- Feed: `ci/packages` is the source (byte-identical to Windows); `setup-feed.sh --verify-pack` re-packs v3.31.1 only to check the package set (34/34 match). CI restores from `ci/packages`; the `pack-check` job replaces `feed`.
- Contract: F-5 (Web follows the browser: `ShellLayouts.From` gives Phone/Tablet for small browsers, `IsPortal()` for portal chrome); `SavesAsDownload`; `IAppCommands` reshaped and filled from `ShellService` by `ShellAppCommands` (kit default, 3 tests) — no Ui hook for the Mac menu bar; kit defaults for `IAppPaths`, `IAccount`, `IAppLifecycle`. `HANDOFF.md` written.

### 10. Groups B and C (proposal 2)
- `proposal/foundation-edits-2.patch` (27 files, +451/−86): write-back at every save, host folders, account name, individual Pdf packages (F4), Mac chat F1/F2/F3, About version bug fix, capability gating.
- Verified on scratch: Platforms solution + WPF host compile `-warnaserror`, 188/188 tests; save-site guard mutation-checked.
- Sheets 2.0.1 probe (throwaway): Core's only compile break is `using Chuvadi.Sheets.Excel` → `Chuvadi.Sheets.Model` in XlsxViewService.cs; then 0 errors.

### 11. chuvadi-pdf 3.31.2 (D-54)
- Tag `v3.31.2` present (commit aff17e6). Packed unchanged → 34 packages, 0 warnings; tree clean.
- `ci/packages`: 3.31.1 chuvadi-pdf set replaced by 3.31.2 (hashes in `PACKAGES-3.31.2.md`); `ChuvadiPdfVersion` 3.31.2; `tests/ChuvadiReader.Tests` umbrella 3.31.2; `setup-feed.sh` and the pack-check job point at v3.31.2.
- Empty package cache → only 3.31.2 restored. Platforms solution + WPF host: 0 warnings; 188/188 tests.
- Chuvadi.Fonts kept at 1.0.0 (the v3.31.2 tag pins it).

### 12. Combined hooks (D-26) and ReadyToRun (D-50)
- One patch for Web H0–H9, Web UI and Mobile UI hooks, D-35/37/39/42/46/48/52 and the Mac Catalyst checks (`3358b00`, `COMBINED-HOOKS.md`, `proposal/combined-hooks.patch`). H0 not added: every hook reads the existing contract.
- Pixel proof (Chromium, 6 routes × 1/1.25/1.5×): a first draft differed on Home — a conditional had merged the shelf caption's two text nodes, moving glyphs by sub-pixels. Desktop branches now keep the original markup verbatim: 18/18 identical. Library page folder path gated the same way (H9), re-proved.
- D-39 on WebKit 26.6: dividers painted at 5–9 of 10 sub-pixel positions before, 10/10 after (1–1.5×). Kept off Windows (Chromium differs at 1.25×/1.75×).
- Phone/tablet smoke: 5 routes each, no errors.
- Mobile UI, Web UI tests and the preview host added to the Platforms solution. D-48 regression test added (fails without the fix).
- Platforms solution + WPF host `-warnaserror`: 0 warnings; 206/206 tests.
- Startup re-check: ReadyToRun +1 method / +1.2 ms (noise); JIT +12 methods, time within noise.
- D-50 (`a1a4660`): Windows csproj publishes ReadyToRun (win-x64 default) only when publishing. Cross-compiled here from Linux: every ChuvadiReader DLL in the publish has native code; plain build stays IL. Publish 43 → 52 MB.

### 13. Second combined patch (7 Nov)
- Coordinator round: U-11 Web wording, Android wording, F-2, F-3, L-8, kit save-folder fallback, Chuvadi.Print packages. `aadd992` + `7c67b89`; `COMBINED-HOOKS-2.md`, `proposal/combined-hooks-2.patch`.
- L-8 via the open document (`PdfDocumentVm.AllowsPrinting`, read from the encryption dictionary at open — no second file read) + the Print card + `WpfPrintService`. Test fixture: `TestSigning.ProtectRestricted` with a no-print mask; the test fails without the fix.
- F-2 moved into Core (`GreetingText`) so it is testable; the name is never changed.
- F-3: `PendingOpen` records in a locked queue; `TryTake` hands each out once. Reader loops over them.
- Kit fallback mirrors `LinuxAppPaths`; Windows result unchanged (Documents always exists).
- Print packages copied from `platform/linux`; SHA-256s match its §18; dependency closure complete.
- Pixel proof: 9 screens × 3 scales, 27/27 identical once `~/Documents` exists. The first run differed only in the save-folder path (`/tmp/…` before, `~/Documents/…` after) — item 6 doing its job in this Documents-less sandbox.
- Preview gained `CHVD_FF=web`; checking the portal found that the Web host must register `PortalLinks` (by design; noted in HANDOFF).
- 229/229 tests; 0 warnings. Startup (ReadyToRun) 196.0 → 196.3 ms, 358 → 358 methods.

### 14. Licence, single-instance design, third patch (7 Nov)
- Licence files (drafts for legal review), shared metadata, Windows ships them; notices generated from each package's licence field with verbatim licence texts (Debian's Apache-2.0, .NET's MIT, the font package's OFL).
- Single instance: design with options (`SINGLE-INSTANCE.md`). Tested here: .NET named pipes on Linux leave the socket file after a crash (every later launch waits 500 ms) — rejected; lock file + Unix socket recovers from a crash; a frozen primary is detected in 1.5 s. Election 4.3 ms in a cold test process; socket set-up 12 ms, so it runs after the first paint.
- Third patch: Web UI Portal files (both rounds), CI on Node 24, Licences page (About row + `/licence`). Drop zone options in `DROP-ZONE-OPTIONS.md`.
- PR push to arunshivab/chuvadi-reader: still 403 (app not installed); branch kept current.

### 15. Legal documents (Arun's answers, 7 Nov)
- DPDP checked against published summaries of the Rules (notified 13 Nov 2025; core obligations from 13 May 2027; 90-day grievance limit; 72-hour Board breach report; one-year log retention for specified purposes — flagged to counsel against the portal's "nothing kept").
- Found: the portal keeps no appearance settings in browser storage (settings are per session in server memory; the Ui uses no browser storage), so the cookie notice says so and leaves a section ready.
- Found: the four display fonts in `wwwroot/fonts/google` shipped without their OFL texts; now in the notices (verbatim from google/fonts). Android declares no INTERNET permission, so Play's answer is "no data collected".
- `scripts/make-notices.py` rebuilds the notices from `ci/packages` and `legal/licenses/`.

### 16. Single instance built; host notices; fourth patch (7 Nov)
- Kit: `IAppInstance`, `IncomingFiles`, `DesktopSingleInstance` + `InstanceChannel`; Windows host wired. 13 tests (real OS paths per runner); 48/48 kit tests here, stable over 5 runs. Windows path compiled only (CI stopped).
- First-launch claim on Linux was 7.7 ms cold: culture formatting/casing (ICU), `string.Create<uint>` (JIT) and `getpwuid` removed → 1–3.5 ms, the rest is the first native open + lock; `ClaimAsync` overlaps it with host start-up.
- Wayland: the hand-over carries `XDG_ACTIVATION_TOKEN`.
- `IHostNotices` + Licences tab (preview shows it on phone/tablet only).
- P-06 and the Linux toast patch applied as given; W-1–W-4 as the Web portal UI chat worded them. 265/265; pixel-identical (one known harness artefact).

### 17. PR opened; D-90 proposal; D-89 built; Windows mutex fix (7 Nov)
- PR #11 opened on arunshivab/chuvadi-reader (4 commits, Arun sole author, no attribution). Its CI (Windows, Ubuntu, macOS) started automatically; cancelled after ~35 s to keep to "no Mac/Windows runs until confirmed".
- My 04:55 push to platform/foundation ran the old full matrix (repo now public). The Windows job failed 4 single-instance tests: an owned mutex is re-entrant on one thread. Fixed by never acquiring it.
- D-90 workflow patch on local branch `proposal/d90-workflows` (not pushed): Linux x64 per push, the rest manual, docs-only pushes run nothing, pack check only when the feed changes, cancel-in-progress, job timeouts. actionlint clean.
- D-89: `IDroppedFiles`, `PortalDropCatcher`, `portal-drop.js`, B wording; 7 browser checks; 27/27 desktop identical.

### 18. CI rules (D-93)
- Kept only D-90 (a) docs-only pushes run nothing and (d) cancel-in-progress per branch, in `platforms.yml` and `ci.yml`; the Linux-only matrix, manual Mac/Windows jobs, the pack-check split and job timeouts were dropped (repo public, minutes free). Local branch `proposal/d90-workflows` deleted.

### 19. Sixth combined patch (8 Nov)
- Mobile UI H-5 to H-12 (+ their current Phone files, the PhoneShell slot), Web UI H5 (merged by hand with H-5) and H6, D-96 touch tip. H-12 widened to every non-Windows platform (one rule, `PhaseZeroSamples`). `COMBINED-HOOKS-6.md`.
- Proof: desktop identical (Library's "1m"/"2m" relative time and the one-pixel Reader artefact aside); phone, tablet and portal smoke clean; 273/273; 0 warnings.

### 20. D-98 legal wording (8 Nov)
- Terms of Use, Privacy Notice B6 and the App Store portal text: "encrypted working area" → "kept in memory only, never written to disk" (D-28: tmpfs). Still DRAFT. Kept as accurate: the encrypted sign-in cookie (ASP.NET Data Protection) and HTTPS.
- Not changed (approved wording, D-20): PlatformText.ServerPrivacy still says "encrypted" on the portal (Settings footer, Library index hint, About › Network) — raised with the coordinator.

### 21. Seventh combined patch, part 1 (8 Nov)
- H-13 (Mobile UI), Web H7 + Portal files (PortalLegalLinks), Linux window-button layout (shared diff unchanged). 27/27 desktop identical; portal/phone smoke clean; 273/273. Part 2 waits for D-101 (live chrome event) and D-104 (drop overlay). `COMBINED-HOOKS-7.md`.

### 22. Seventh combined patch, part 2a (8 Nov)
- Portal privacy line "kept in memory only" (D-106), Android P-07, Web UI D-104 drop overlay and D-103 pitch. 27/27 desktop identical; drop checks pass; 274/274. D-101 still awaited.

### 23. Seventh combined patch, part 2b (8 Nov)
- D-101 written here (coordinator 20:22): `IPlatformInfo.ChromeChanged` (default does nothing), MainLayout redraws the top bar on non-Windows platforms. Contract test, plus the preview's Linux mode with a live-layout endpoint and `tools/PixelProof/chrome-changed.js` (6/6). 27/27 desktop identical; 276/276.
- Lesson: start the preview with `ASPNETCORE_ENVIRONMENT=Development`. Otherwise static web assets are off, `blazor.web.js` is served empty and the page never becomes interactive. Only prerender runs, so a live event finds no listener.

### 24. Eighth combined patch, part 1 (8 Nov)
- H-14 (Mobile UI: the phone opens at Fit width; desktop margin 60 px), Mobile UI's own phone and tablet files (9bb7f76), Web UI U-17 (b) Home drop zone during a drag (D-109). 27/27 desktop identical; phone fit 12 | 12 px; portal drop 7/7 plus U-17 state check; 276/276. Part 2 waits for D-112 and D-114. `COMBINED-HOOKS-8.md`.

### 25. Eighth combined patch, part 2 (9 Nov)
- The Linux chat's shared diff (B-02, B-03, B-07, B-08, B-09/B-10, B-11, B-19, B-23) without its D-101 hunks (already here), Linux host files and uitest.py. D-120 fixes WT-02, WT-09, WT-10/B-11b, B-08b, B-16 in the kit, B-22 (D-123). Mobile UI D-112 and D-114 (H-16). 295/295; Windows-layout screens identical apart from the intended Print-card text. `COMBINED-HOOKS-8.md`.

### 26. Ninth combined patch (9 Nov)
- B-07 through the library's `PasswordSupplied`; unlock card in the Password card's language; B-11a repair already shared via `RecoveryService` → `PdfRepairer.Repair`; Sheets 1.1.2 has no `XlsxReaderOptions.CancellationToken` (waits for the Sheets move). 297/297; 27/27 identical. `COMBINED-HOOKS-9.md`.
- Open questions to the coordinator: (a) `RequiresPassword` measured at the cost of a plain open, so not on the open path; (b) `PdfOpenOptions.Password` would mean the stream overload, which buffers the file, while the path overload already takes the password.

### 27. Tenth combined patch (9 Nov, D-130)
- B-24: the PDF open (existence check included) moved off the Reader's thread with a per-tab cancel; closing frees the slot at once; late results disposed; queued opens load side by side. Tests with a thread-blocking reader and a real FIFO (the old path hangs on them). 299/299; 26/27 + Home artefact. `COMBINED-HOOKS-10.md`.

### 28. Tenth combined patch, part 2 (9 Nov)
- Chuvadi.Zip 1.0.0 (release asset of `zip-v1.0.0`, commit 170bc40) into `ci/packages`, SHA-256 recorded (`PACKAGES-ZIP-1.0.0.md`), notices regenerated. Web UI Upload wording and Q-3 "this session" wording, with tests. 305/305; 27/27.

### 29. Eleventh combined patch (9 Nov, D-136)
- Chuvadi.Docs 2.0.0 and Chuvadi.Sheets 2.0.2 (release assets of docs-v2.0.0 / sheets-v2.0.2, SHA-256 in `PACKAGES-DOCS-SHEETS-2.md`), namespaces to `.Model`, table cells from `TableCell.Blocks`, whitespace shown as in the file. Library limits (Docs 20 MB / 64 MB; Sheets ForUntrustedInput) and cancellation (token, 60 s) replace Core's guard; viewers stop waiting at once. Corpus with independent expected values: old 18 wrong, new 0. 313/313; 24/27 + About (versions). `COMBINED-HOOKS-11.md`.

### 30. Eleventh combined patch, part 2 (9 Nov, D-137)
- Word limits keyed on `ServerSide`: portal 20/64 MB, desktop and mobile 100/400 MB (a 30 MB picture opens locally, is refused on the server). List markers from `Document.GetListLabels()`; Symbol/Wingdings bullets drawn as Unicode shapes. 324/324; 26/27 + Home artefact.

### 31. Twelfth combined patch, part 1 (9 Nov, D-139 item 1 + AT-03)
- chuvadi-pdf 3.32.0 from the release, 34/34 against its SHA256SUMS.txt. Stale commit stamp (aff17e6) checked: packed the signed tag, so 33/33 DLLs are identical in metadata, IL sizes and resources (`PACKAGES-3.32.0.md`). Printing follows `EncryptionInfo.EffectiveFlags` (the owner password prints; D-102 ends). LIB-1 pypdf `/P 4294965243` fixture opens (3.31.2 failed).
- AT-03: typed registrations with `DynamicallyAccessedMembers`; trim and AOT analysers on Hosting; settings JSON source-generated (byte-identical). `tools/TrimProbe` reproduced 6/53 failures before, 0 after; `trim-check` CI job. `TRIMMING.md`.
