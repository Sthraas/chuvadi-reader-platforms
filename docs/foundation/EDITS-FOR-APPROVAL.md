# Foundation — existing-file edits for Arun's approval

**Nothing here is applied to `platform/foundation`.** Approver: the coordinator (delegated by Arun, 6 Nov); nothing reaches `arunshivab/chuvadi-reader` before Arun's final check. Group A is one patch with exact diffs: `docs/foundation/proposal/foundation-edits-1.patch` (apply with `git apply`). It assumes the recommended answers to decisions F-2 (a), F-3 (switch) and F-6 (keep both); if you choose differently I regenerate it.
Groups B and C depend on decision F-1 (file model) and are listed by site; their diffs are written after you decide, so nothing is built for an option you don't pick.

## How Group A was verified
Applied on a local scratch branch (never pushed), then on Linux (.NET SDK 10.0.403):
- `ChuvadiReader.Platforms.slnx` build: **0 warnings, 0 errors**; tests **172/172 pass**.
- `ChuvadiReader.Windows` **compiled** with `-p:EnableWindowsTargeting=true`: **0 warnings, 0 errors**. It cannot be *run* here (WPF) — see "What to check on Windows".
- Static web assets: `_content/ChuvadiReader.Ui/js/theme.js` and `js/platform.js` are in the Windows host's asset manifest.

## Group A — needed by every platform; Windows looks and behaves the same

Windows output is designed to be identical: `CtrlKeyLabels` returns "Ctrl …" text unchanged, `WindowButtons Side=Right` renders the exact markup it replaces, `StatusLocation` renders the exact text on non-server hosts, and `isPrimary(e)` is the same Ctrl test on Windows. The exceptions are marked **visible** or **behaviour**.

| # | File | Change | Why | For | Against | Windows risk |
|---|---|---|---|---|---|---|
| A1 | `Core/ChuvadiReader.Core.csproj` | + ProjectReference to `ChuvadiReader.Platform` | Core and Ui can use the new contracts | One-line, contracts-only project (F-2 a) | Core now builds a second small project | None |
| A2 | `Ui/_Imports.razor` | + `@using ChuvadiReader.Ui.Components.Platform` | New components usable by tag | — | — | None |
| A3 | `Ui/App.razor` | Wrap `<Router>` in `<PlatformRoot>` | Sets `data-shell / data-platform / data-form-factor / data-input` on `<html>` and cascades form-factor changes so layouts re-render (Android fold, browser resize) | One place, no per-page code | One extra JS module load at start (~15 lines) | Very low: attributes only; no CSS uses them yet |
| A4 | `Ui/Layout/MainLayout.razor` | (a) inject `IPlatformInfo`; (b) `<WindowButtons Side=Left/>` at the start of the top bar and `Side=Right` in place of the `traffic` div; (c) `<StatusLocation/>` in place of the status text; (d) `StartDrag` returns early when `Chrome.TitleBarDrag` is false; (e) 10 "Ctrl …" labels and the Document-menu key column go through `Keys.Format` | Mac buttons on the left, none on Android/Web, server wording on Web (12b), no drag logic where there's no window, ⌘ labels on Mac | Design-exact per platform without touching the desktop markup | MainLayout gains 2 component tags | Low: same markup on Windows. **Check:** buttons still at the right, maximise icon still flips, drag + double-click maximise still work |
| A5 | `Ui/Components/Rails/RailButton.razor` | Shows `Keys.Format(Keys)` in the label and tooltip | Every rail button's shortcut (≈30) is fixed in one place | Keys stay canonical in all pages | — | None |
| A6 | `Ui/Components/Shell/CommandBar.razor` | Shows `Keys.Format(cc.Keys)` | Same, for Ctrl K results | Command `Keys` stay canonical — they are also the dispatch keys from `shell.js` | — | None |
| A7 | `Ui/Components/Settings/ShortcutsSection.razor` | `<kbd>` shows `Keys.Format(...)` | Settings › Shortcuts lists ⌘ on Mac | — | — | None |
| A8 | `Ui/Pages/Reader.razor` | inject `IPlatformInfo` and `IClipboard`; 2 bookmark tooltips via `Keys.Format` | ⌘ labels; text copy (A10) | — | — | None |
| A9 | `Ui/Pages/Bench.razor`, `Ui/Pages/Dashboard.razor` | inject `IPlatformInfo`; "Select all" tooltip and the Home tip via `Keys.Format` | ⌘ labels | — | — | **Visible (tiny):** Bench tooltip "Ctrl+A" becomes "Ctrl A", matching every other label |
| A10 | `Ui/Pages/Reader.Shell.cs:517` | `navigator.clipboard.writeText` → `IClipboard.SetTextAsync` | WKWebView on Mac may not expose `navigator.clipboard` (custom-scheme page) → "Couldn't copy"; one host-implemented path works everywhere | Same result on every platform | Copy now goes through the host | **Behaviour (equivalent):** Windows copies via the WPF clipboard (new `WpfClipboard`, 5 retries if another app holds the clipboard) instead of WebView2's. **Check:** "Copy file path" and other text copies |
| A11 | `Ui/wwwroot/js/reader.js:10, 98, 106, 117` | Import `isPrimary` from `platform.js`; use it for the tab/undo/zoom/find shortcuts; bare-key navigation also ignores Ctrl combos | **Bug fix (Mac):** today ⌘W, ⌘Z, ⌘F, ⌘±0, ⌘1-9, ⌘Tab do nothing on Mac because the code requires `ctrlKey && !metaKey` | One rule for all keys | — | None by construction: on Windows `isPrimary` = `ctrlKey && !metaKey`, exactly today's test; the added `ctrlKey` check on line 117 is only reached when Alt or Win is also held, which already returned. **Check:** Ctrl W/Tab/1-9/+/−/0/F/Z in the Reader |
| A12 | `Ui/wwwroot/js/theme.js` (moved from `Windows/wwwroot/theme.js`, content unchanged) + `Windows/wwwroot/index.html` script path | Every host needs `window.chuvadiTheme` | One copy, no drift | Windows page loads it from `_content/ChuvadiReader.Ui/js/theme.js` | Low. **Check:** theme switch, interface size 125/150 %, reduce motion |
| A13 | `Windows/ChuvadiReader.Windows.csproj` | + ProjectReference `ChuvadiReader.Hosting` | Shared registration (F-3) | — | — | None |
| A14 | `Windows/App.xaml.cs` | Replace the 40-line service list with `services.AddChuvadiReader(AppStateLifetime.Process)`; register `IClipboard` (`WpfClipboard`) and `IPlatformInfo` (Windows, buttons right, drag on, desktop capabilities, Ctrl labels) | One registration list for all five hosts | No drift; Web gets per-user lifetime from the same list | Windows now depends on the kit | Low: the kit registers the same 37 services as singletons (a test proves the set); host registrations still win. **Check:** app starts, every page opens |
| A15 | new `Windows/Platform/WpfClipboard.cs` | `IClipboard` for Windows | needed by A10/A14 | — | — | — |
| A16 | new `Ui/Components/Platform/` (`PlatformRoot`, `PlatformState`, `WindowButtons` + `.css`, `StatusLocation`) and `Ui/wwwroot/js/platform.js` | The platform switch itself | New files, but they need A1 to compile, so they ship in this patch | — | — | — |

### What to check on Windows after applying Group A
1. `scripts/setup-feed.sh` (or your local-nuget), then `dotnet build ChuvadiReader.slnx -c Release` → 0 warnings; `dotnet test` → 161 pass.
2. Start the app: window maximised as before, top bar unchanged, buttons at the right; minimise / maximise-restore (icon flips) / close; drag the top bar; double-click it to maximise.
3. Settings › Appearance: all 5 themes, interface size 100/125/150, reduce motion.
4. Reader: Ctrl W, Ctrl Shift W, Ctrl Alt W, Ctrl Tab, Ctrl 1-9, Ctrl + / − / 0, Ctrl F, Ctrl Z; Ctrl K command bar shows "Ctrl …" keys.
5. Document ▾ › Copy file path → paste somewhere.
6. Status bar still says "offline · on this device".

## Group B — file write-back (after decision F-1)

If F-1 = C (recommended): one line after each successful write to a path the person chose or opened — `await WriteBack.CommitAsync(path);` — plus an error toast when it fails. Desktop: `NoFileWriteBack` → no change on Windows. Sites (from INVENTORY F5/F6/F7):
- Save as: PasswordCard.razor:5 flow; Bench.razor:2048, 2055, 2078, 2664; Merge.razor:128; Reader.Shell.cs:770; Reader.razor:1768, 1881 (PNG), 3025, 3140; Redact.razor:563; Split.razor:229; Bench.razor:1497 (session).
- Save in place: Reader.razor:1802-1808, 2197-2203, 2988-2994.
- Output to folder: Bench.razor:2062, 2617, 2656, 2730; Reader.razor:1251, 1302; Split.razor:200; Dashboard.razor:439/448 and Library/Settings folder pickers (these are *source* folders: no write-back; hidden where `PickFolders` is false — Group C).
- Plus a test that fails if a new save site skips the call.

## Group C — paths, account, capability gating (after F-1; small)
- `IAppPaths`: SessionService.cs:46, AppInfo.cs:46, SaveFolderService.cs:31 (same values on Windows by construction), and the ~20 temp sites in INVENTORY P4 → `IAppPaths.WorkingFolder` (desktop = `Path.GetTempPath()`, unchanged).
- `IAccount`: UserProfileService.cs:39 and the status-bar user chip (MainLayout.razor:165).
- Capability gating (hide or lock, per your choice): folder pickers when `PickFolders` is false; Watched folder/Library roots when `WatchFolders` is false; "Show in folder" / "Copy file path" when `RevealInFolder` is false; device-only wording (AboutSection.razor:14, Settings.razor:37, LibrarySection.razor:50) when `ServerSide` — **the Web wording is yours to give.**
- "Show in folder" (Reader.Shell.cs:424) wired to `IFileManager` on desktop — a new working feature, so listed separately for you to accept or leave as "Coming soon".

## Later hooks (when the components exist; not in this proposal)
- MainLayout: `AccountMenu` slot when `Chrome.AccountMenu` (Web, 12b); Web sign-in route (12a); `SangamGate` on certificate signing (12c).
- MainLayout + Reader/Bench/Redact: phone bottom bar, tool strip and View sheet when `FormFactor.Phone` (12g-12j); tablet sizes via `data-form-factor="tablet"` CSS (12d-12f).
- reader.js: pen draws / finger pans on tablets (12e); WebKit `gesture*` pinch for Mac/Linux (INVENTORY K2, after a device test).
- MainLayout/Reader: Android back closes the open card, sheet or drawer first (`IAppLifecycle.BackRequested`).
- Ui publishes its command list to `IAppCommands` for the macOS menu bar.
