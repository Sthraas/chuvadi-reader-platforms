# Web — existing-file hooks after the Foundation (replaces the earlier H0–H9 proposal)

6 Nov 2026. My earlier `IHostChrome` proposal (H0–H9) is **withdrawn**: the Foundation's `IPlatformInfo`, `IAppPaths`, `IAccount`, `IFileWriteBack` and its Groups A–C cover most of it, and two chats editing the same Reader files would conflict. `platform/web` is now rebased on `platform/foundation` (Group A applied) and uses the kit (`AddChuvadiReader(AppStateLifetime.PerConnection)`).

## Where each earlier hook went

| Earlier | Covered by | State |
|---|---|---|
| H1 window buttons → account menu | Group A4 (`WindowButtons`, `Chrome.Buttons = None` on Web) + later hook "AccountMenu slot" | Buttons gone on the portal (checked in the browser). Account menu: Web portal UI chat + Foundation's later hook |
| H2 status text | Group A4 (`StatusLocation`) | Portal shows "processed on the server · encrypted at rest · only you can see it" (checked) |
| H6 OS user name | Group C5 (`IAccount.DisplayName`) | Pending approval; portal still greets "Root" until then |
| H7 default save folder | Group C3 (`IAppPaths.DefaultSaveFolder`) | Pending approval; the portal host already points the save folder at the session through `IAppStorage` |
| Temp files and desk templates (isolation point 1) | Groups C2 and C4 (`IAppPaths.WorkingFolder` / `AppDataFolder`) | Pending approval |
| Folder choosers, "Show in folder", "Copy file path" | Group C9 (hidden when `PickFolders` / `WatchFolders` / `RevealInFolder` are false) | Pending approval |
| Saves → downloads | Group B (`IFileWriteBack.CommitAsync` at every save) | Pending approval; the portal implements `IFileWriteBack` and also watches its outbox until B lands |

## Gaps no Foundation group covers yet (for the coordinator / Foundation chat)

Seen on the running portal with Group A applied (headless Chrome, 1440 × 900):

| # | Where | Today on the portal | Needed | Suggested owner |
|---|---|---|---|---|
| G1 | `Pages/Dashboard.razor:31` blurb; `Pages/Settings.razor:37`; `Settings/AboutSection.razor:14`; `Settings/LibrarySection.razor:50` | "nothing leaves this device", "Stored on this device only", "Network: Offline", "Stays on this device" | Server wording when `Capabilities.ServerSide` | Foundation lists it as waiting for Arun's Web wording; wording itself from the Web portal UI chat |
| G2 | `Core/Documents/RecentFilesService.cs` (`SeedSample`), `PinnedAndWatchedServices.cs` (`PinnedService`, `WatchedFolderService`) | Phase 0 sample recents (`patient_chart.pdf`, `consent_form.pdf` marked encrypted…), a pinned `aerb_submission.pdf`, and "Watched folder ~/Documents/Chuvadi · 8 documents found · scanned 2m" on **every** portal visit (each session starts empty); clicking one opens a file that doesn't exist | (a) **bug fix:** remove the Phase 0 samples everywhere (also shown on a fresh desktop install), or (b) skip them when `Capabilities.ServerSide` | Reader chat / Foundation; I recommend (a) |
| G3 | `Pages/Dashboard.razor:112` "Storage map" and `:160` Library shelf caption; `:186–190` watched-folder card | Shows the server path of the session folder (`/…/users/<key>/sessions/<id>/…`); watched-folder card with "change" | No server paths on the portal ("Chuvadi Documents" only); card hidden when `WatchFolders` is false (C9 hides the Settings rows but not this card) | Foundation (extend C9) |
| G4 | `Layout/MainLayout.razor` left-bar "Open" (folder icon) | "Open" | 12b shows "upload" in the left-bar globals | Web portal UI chat decides; one label/icon switch on `Kind == Web` |

Nothing in this file is applied. No existing file is changed on `platform/web` (checked with `git diff --diff-filter=M` against `platform/foundation`).
