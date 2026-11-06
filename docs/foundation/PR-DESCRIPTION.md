# Platform layer (Foundation) — Mac, Linux, Android, Web groundwork

Lands the Foundation edits in chuvadi-reader first (Arun's merge plan (a)), so the Reader chat builds on them. **Do not merge before the Windows checks below.**

Three commits: code (`src`, `tests`, `ChuvadiReader.Platforms.slnx`), dev tools (never shipped), docs (`docs/foundation`).

## What changes
**New projects**
- `ChuvadiReader.Platform` — the contract every host implements: platform kind, form factor, input, window chrome, capabilities, key labels, `ShellLayout` (desktop / tablet / phone / portal), file write-back, app folders, account, clipboard, file manager, share, lifecycle, menu-bar commands.
- `ChuvadiReader.Hosting` — `AddChuvadiReader(lifetime)` registers every Core service once for all hosts (per-connection for Web); defaults for each seam; menu-bar commands from `ShellService`; desktop defaults (folders, account, Ctrl/⌘ labels, settings file storage).
- `tests/ChuvadiReader.Hosting.Tests` — 27 tests (service graph, per-connection isolation, Windows registration drift guard, key labels, command bridge, every save delivers, openable types vs the Open dialog, settings write, host folders).

**Ui / Core (Windows looks and behaves the same, except where marked)**
- Window buttons follow the platform: right on Windows (original markup), left on macOS, none on Android/Web; title-bar drag only where there is a native window.
- Shortcut labels per platform (⌘ on macOS); command keys stay canonical. **Visible:** Bench "Select all" tooltip "Ctrl+A" → "Ctrl A".
- **Bug fix (macOS):** Reader shortcuts required Ctrl; ⌘ now works on Mac. Windows test unchanged.
- Text copy through the host clipboard (Windows: WPF clipboard with retries) instead of WebView2's.
- `theme.js` moves from the Windows host into the Ui (content unchanged plus one setter Windows never calls).
- Every save delivers through `IFileWriteBack` (no-op on desktop); a test fails if a save site skips it.
- Temp files, default save folder, desk templates and user name come from the host. **Visible on disk:** desk templates now live in `%AppData%\Chuvadi`; existing ones are copied over from `%AppData%\ChuvadiReader` on first use.
- Controls a platform can never support are hidden (folder pickers, watched folders, Show in folder / Copy file path) — all stay on Windows.
- **New on Windows:** Document ▾ › Show in folder works (opens Explorer with the file selected).
- Core uses the 17 individual chuvadi-pdf 3.31.1 packages instead of the umbrella (drops PdfA, Color, Fonts.Woff2, Fonts.Bundled, Xfa, Reader — none used). All from `ci/packages`; nothing added.
- **Bug fix:** Settings › About showed chuvadi-pdf 3.30.2; versions now read from the loaded libraries (shows 3.31.1).
- **Bug fix:** window drop accepts exactly the Open dialog's types (it accepted .doc/.xls, which then failed, and refused .md/.markdown/.txt/.log/.html/.htm).
- **Bug fix:** settings are written to a temp file that then replaces `settings.json`.
- Web wording only on the Web portal (Windows text unchanged).

**Windows host:** registers through `AddChuvadiReader`; adds `WpfClipboard`, `WpfFileManager`; `FileAppStorage` moves to the shared kit.

## Startup (published Release; `docs/foundation/STARTUP.md`)
Core/Ui startup measured with `tools/StartupProbe` (services + first render of the real App), main c7b9e44 vs this branch, medians:

| Build | Services | First render | Total | Methods JIT-compiled |
|---|---|---|---|---|
| main, JIT | 26.0 ms | 198.4 ms | 256.3 ms | 1,372 |
| branch, JIT | 28.0 ms | 204.5 ms | 263.8 ms | 1,415 |
| main, ReadyToRun | 22.7 ms | 124.1 ms | 177.5 ms | 351 |
| branch, ReadyToRun | 23.1 ms | 126.3 ms | 177.3 ms | 357 |

- ReadyToRun: no added cost. JIT: +43 small methods (~7 ms, ~3 %), after removing a module fetch, a root cascading component and generic registrations from the first version.
- Rendered HTML identical to main on Windows (apart from the clock and whitespace).
- **Recommended win (not in this PR):** publish the Windows app ReadyToRun — −80 ms (−31 %) of Core/Ui startup. Time the WPF + WebView2 part on Windows with `pwsh scripts/measure-startup.ps1` and `-ReadyToRun`.
- Measured on Linux x64, 2-core sandbox (A/A noise ≈ 7 ms); the WPF host compiles here with `-p:EnableWindowsTargeting=true` but can only run on Windows.

## Verified
- `ChuvadiReader.Platforms.slnx` and `ChuvadiReader.Windows` build with `-warnaserror`: 0 warnings, 0 errors.
- Tests: 188/188 (161 existing + 27 new).
- Working-repo CI (Sthraas/chuvadi-reader-platforms, `platform/foundation`): shared code on Ubuntu x64/arm64, macOS, Windows; the Windows app on windows-latest; package check.

## Windows checks for Arun before merging
1. `dotnet build ChuvadiReader.slnx -c Release` → 0 warnings; `dotnet test` → all pass.
2. Start the app: maximised as before, top bar unchanged, window buttons at the right; minimise / maximise-restore (icon flips) / close; drag the top bar; double-click it to maximise.
3. Settings › Appearance: all 5 themes, interface size 100 / 125 / 150, reduce motion.
4. Reader: Ctrl W, Ctrl Shift W, Ctrl Alt W, Ctrl Tab, Ctrl 1-9, Ctrl + / − / 0, Ctrl F, Ctrl Z; Ctrl K command bar shows "Ctrl …" keys.
5. Document ▾ › Copy file path, then paste somewhere.
6. Status bar still says "offline · on this device".

Also for this PR's other changes:

7. Settings › About: chuvadi-pdf 3.31.1.
8. Drop a .md and a .docx on the window: both open; a .doc is refused.
9. Arrange: Apply template still lists your templates; Save template works.
10. Change a setting, restart: kept.
11. Bind a desk, Merge, Split, Stamp in place, Save marks in place: files written as before.
12. Document ▾ › Show in folder: Explorer opens with the file selected.

## Known gaps (not changed here)
- Windows printing is raster (`WpfPrintService`); move to Chuvadi.Print's vector XPS route when rc.3 is released.
- Layout not released (Word/Excel exact view, Save as PDF); Docs stays 1.1.0; Sheets 1.1.2 pending the Reader chat's plan.
