# Proposal: host chrome hooks (H0–H9) for the web portal

Status: **proposal only, not applied.** For the coordinator to review and finalise (Arun delegated decisions for this repo, 6 Nov). Prepared 6 Nov 2026 by the Web chat. Rule 4: every line below edits a file the Reader chat owns.

- Exact patches (beside this file), against the chuvadi-reader `c7b9e44` import; both pass `git apply --check`, the second on top of the first:
  - `H0-H6-host-chrome.diff` — 8 files, +98 / −15 (one new file, `IHostChrome.cs`).
  - `H7-H8-save-folder-and-samples.diff` — 5 files, +49 / −6.
- H9 is described below; its diff follows once the Web portal UI chat says how those spots should look.
- After Arun's 6 Nov decisions (no server storage, no sharing), the account menu holds only Get the desktop app, Account settings and Sign out; its look belongs to the Web portal UI chat. H1 only provides the slot.

## The idea

One new Core interface, `IHostChrome`, says where the chrome and wording differ between the desktop app and the web portal. **Every member defaults to today's desktop value**, and `DesktopHostChrome` is an empty class that keeps those defaults. So on Windows (and later Mac, Linux, Android) nothing changes; the web portal registers its own implementation with the 12b values and supplies its account menu as a component.

```csharp
public interface IHostChrome
{
    bool ShowsWindowControls => true;                       // H1
    Type? TopBarEnd => null;                                // H1: portal account button + menu
    string WhereProcessed => "offline · on this device";    // H2
    string? Identity => null;                               // H2: "Arun S. · Sangam"
    string OpenLabel => "Open";  string OpenIcon => "folder"; // H3: "Upload" / "upload"
    string PrivacyLine => "nothing leaves this device";     // H4
    string StorageNote => "Stored on this device only";     // H5
    string NetworkHint => "offline · nothing leaves this device"; string NetworkValue => "Offline"; // H5
    bool ShowsDataFolder => true;                           // H5
    string IndexHint => "Stays on this device";             // H5
    string? DefaultName => null;                            // H6: Sangam display name
}
public sealed class DesktopHostChrome : IHostChrome { }
```

## Each change

| # | File | Change | Why on the web |
|---|---|---|---|
| H0 | `Core/Window/IHostChrome.cs` (new) | The interface and `DesktopHostChrome` | One seam instead of scattered `if (web)` checks |
| H0 | `Windows/App.xaml.cs` | +1 line: `services.AddSingleton<IHostChrome, DesktopHostChrome>();` | Every host must register it, because the Ui injects it |
| H1 | `Ui/Layout/MainLayout.razor` | Render `Host.TopBarEnd` (if any) via `DynamicComponent`; wrap the three window buttons in `@if (Host.ShowsWindowControls)` | 12b: no window controls, account menu instead (My files, Shared with me, Get the desktop app, Account settings, Sign out, storage meter) |
| H2 | `Ui/Layout/MainLayout.razor` | Status bar: `@Host.WhereProcessed`; identity `Host.Identity ?? Profile.Name ?? "This computer"` | 12b: "processed on the server · encrypted at rest · only you can see it", "Arun S. · Sangam" |
| H3 | `Ui/Layout/MainLayout.razor` | Left-bar "Open" label and icon from `Host.OpenLabel` / `Host.OpenIcon` (same `AddTab` action) | 12b's left bar globals: upload, find, library, home |
| H4 | `Ui/Pages/Dashboard.razor` | Blurb ends with `@Host.PrivacyLine` | "nothing leaves this device" is false on the server |
| H5 | `Ui/Pages/Settings.razor`, `Settings/AboutSection.razor`, `Settings/LibrarySection.razor` | Settings footer, About › Network hint/value, hide the Data folder row, Library index hint — all from `Host` | Same wording problem; the Data folder row would show a server path |
| H6 | `Core/Documents/UserProfileService.cs` | Second constructor taking `IHostChrome`; name order becomes: name set in Settings → `Host.DefaultName` → OS user name | The spike greeted "Good evening, Root." (the server account) |

## H7 — default save folder from the host (safety)

| File | Change |
|---|---|
| `Core/Window/IHostChrome.cs` | `string? DefaultSaveFolder => null;` |
| `Core/Documents/SaveFolderService.cs` | Second constructor taking `IHostChrome`; new instance method `DefaultFolder()` = host's folder, else today's `DefaultBaseFolder()`; `HydrateAsync` and `SetBaseFolderAsync(null)` use it |
| `Ui/Components/Settings/SavingSection.razor` | "Reset to default" tooltip shows `SaveFolders.DefaultFolder()` |

Why: today `SaveFolderService` defaults to `Documents/Chuvadi Documents` of the account running the process, and **Settings › Saving › Reset to default** sets it back there. On the server that is the service account's home: one person's exports would land in a folder shared by everyone and kept after the session. The portal host already seeds its session folder through `IAppStorage` (new code, no edit), but "Reset to default" bypasses storage and can't be caught by the host. H7 closes that.

| Pros | Cons |
|---|---|
| Nothing the Reader saves can leave the session folder on the portal; desktop unchanged (null → today's folder) | One more member and constructor in Core; the static `DefaultBaseFolder()` stays for compatibility |

## H8 — Phase 0 sample data (bug fix candidate)

| File | Change |
|---|---|
| `Core/Window/IHostChrome.cs` | `bool ShowsSampleData => true;` |
| `Core/Documents/RecentFilesService.cs`, `PinnedAndWatchedServices.cs` (`PinnedService`, `WatchedFolderService`) | Second constructor taking `IHostChrome`; seed the samples only when `ShowsSampleData` |

Why: when nothing is stored, the Reader shows made-up recents (`patient_chart.pdf`, `consent_form.pdf` marked encrypted…), a pinned `aerb_submission.pdf` and a watched folder "~/Documents/Chuvadi · 8 documents found · scanned 2m". On the portal every session starts empty, so **every user would see them on every visit**, and clicking one opens a file that doesn't exist. The same samples show on a fresh desktop install.

| Option | Pros | Cons |
|---|---|---|
| (a) **Bug fix:** remove the Phase 0 samples everywhere | Honest dashboard on every platform; no flag | Changes the desktop's first run (empty-state screens show instead); the Reader chat's call |
| (b) The flag in the diff: off on the portal, on elsewhere | Desktop unchanged | Keeps placeholder data in a product build |

Recommendation: (a) for the product; the diff implements (b) so the portal is safe either way.

## H9 — server paths and folder choosers shown on the portal (diff to follow)

Seen in the running portal: Dashboard "Storage map" shows the session folder path (`/…/users/<key>/sessions/<id>/outbox/Chuvadi Documents`), and the Library shelf, Watched folder card, Settings › Library and Settings › Saving show folder paths with "Choose…/change/Reset" buttons. On the portal those paths mean nothing to the person and reveal server layout; choosing a folder gives a fresh empty download folder. Places: `Pages/Dashboard.razor` lines 42, 112, 160, 186–190; `Pages/Library.razor` line 376; `Settings/LibrarySection.razor` lines 11, 75, 86; `Settings/SavingSection.razor` lines 8–10, 48.

Proposed shape: `IHostChrome.HasLocalFolders` (false on the portal) to hide the folder choosers and the watched-folder card, and `IHostChrome.DisplayFolder(path)` to show "Chuvadi Documents (this session)" instead of a path. Also the Print card's Copies and Fit-to-page controls, which the browser's dialog decides on the portal. Waiting for the Web portal UI chat to say how each spot should look before writing the diff.

## Proof that the desktop is unchanged

Run in the sandbox on the patched copy (6 Nov), H0–H6 first and then again with H7–H8:
- `ChuvadiReader.Core`, `ChuvadiReader.Ui`, `ChuvadiReader.Tests`: 0 warnings, 0 errors; **161/161 tests pass** (every existing one-argument constructor is kept, so tests are untouched).
- `ChuvadiReader.Windows` compiled on Linux with `EnableWindowsTargeting=true`: 0 warnings, 0 errors (compile check only; Arun's Windows run is the real proof).
- Rendered HTML of `/`, `/settings`, `/library` with `DesktopHostChrome`, before vs after: same text and elements. The only differences are markup whitespace inside the flex top bar (not rendered) and the middle dot `·` written as an HTML entity (renders the same).
- Headless Chrome screenshots before vs after at 1440×900: the only pixel differences are the status-bar clock and a blinking caret, the same differences two runs of the unchanged build show against each other.

## Pros and cons

| | |
|---|---|
| Pros | Desktop output unchanged; one place for every host difference (Mac/Linux/Android can use it too, e.g. Mac traffic lights on the left); the portal's account menu is a component in the Web project, so the Ui stays free of web code and Sangam |
| Cons | Touches 7 files the Reader chat owns, so it should land in coordination with that chat to avoid merge conflicts; every host must register `IHostChrome` (one line each); wording lives in two places (Ui defaults, web implementation) |

## Alternatives considered

1. **Resolve `IHostChrome` optionally in the Ui** (inject `IServiceProvider`, fall back to `DesktopHostChrome`), so `App.xaml.cs` is not touched. Saves one line in each host but hides a missing registration; not recommended.
2. **A `HostKind` enum with web strings inside the Ui.** Fewer members, but puts web wording and the Sangam account menu into the shared Ui; not recommended.
3. **H6 without touching Core:** the web host's `IAppStorage` answers the `name` key with the Sangam name. Works today, but a person who clears their name falls back to the server's account name again, and it bends `IAppStorage`'s meaning; not recommended.

## Not covered here

- **Folder pickers as such** need no Ui change: on the portal "Save as" and "choose a folder" return a session download folder, and every file written there is downloaded by the browser (host code, already built).
- **"autosaved to your storage"**, storage meter, "My files", "Shared with me": dropped for this release (Arun, 6 Nov).
- **Sign-in page (12a)** and the account menu's look: the Web portal UI chat; no existing-file change.
