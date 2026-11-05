# Android — decisions for Arun

Each item: what is needed, the options with pros and cons, and the Android chat's lean. Nothing
here is built around a missing decision; where the app is blocked, the gap is stated.

Status key: **OPEN** (waiting on Arun) · **DECIDED** (with date).

---

## A-01 Play Store application id — OPEN
The id is permanent once the app is published. A placeholder `in.chuvadi.reader` is used now.

| Option | For | Against |
|---|---|---|
| `in.chuvadi.reader` | Matches the planned `reader.chuvadi.in` portal domain. | Needs the `chuvadi.in` domain to stay Arun's. |
| `com.sthraas.chuvadi.reader` | Ties the app to the publishing company (Sthraas Intelligence). | Long; the brand isn't Sthraas. |
| `com.imagiqa.chuvadi.reader` | Existing company. | Same. |

Also needed: which Play developer account publishes it (Sthraas or imagiQa) — it decides the
"developer name" shown on the store.

## A-02 How Android files reach the path-based Core — OPEN (shared with the Foundation chat)
Android never gives file paths. Documents come as `content://` URIs with a temporary grant.
`ChuvadiReader.Core` works on paths everywhere (`IFilePicker` returns paths, `OpenDocumentService`,
`RecentFilesService`, `IPrintService.PrintAsync(pdfPath)`, `SaveFolderService`, `LibraryService`'s
`FileSystemWatcher`, `SessionService`).

What works today with no Core change: **opening**. The host streams the document into a private
working copy and opens it under its real name (`OpenDocumentService.Request(path, name)`).

What does not work yet:
- **Saving back** to the original and **Save as** to a place the user picks: Core writes a path,
  and nothing tells the host "written — copy it back to this URI".
- **Recent files / Pinned** survive only while the working copy exists.
- **Library / Watched folders** use `FileSystemWatcher` on a folder path; Android folders are
  tree URIs. **Default save folder** (`MyDocuments/Chuvadi`) lands in app-private storage, which the
  user can't see.

| Option | For | Against |
|---|---|---|
| (a) Host-side working copies + a small new host hook ("file saved at path → host copies it to its URI"), and a per-file record of URI ↔ copy with persisted URI grants | Core keeps paths; smallest change; same model the Mac sandbox may need. | Needs a new member in a Core interface (existing file). Two copies of each open document on the phone. |
| (b) Core moves to a document-handle / stream abstraction (`IDocumentSource`) | Cleanest on Android, Web and a sandboxed Mac. | Large change to existing Core files; Windows behaviour must be re-verified. |

Lean: **(a)** now — it ships soonest and fits the "build the right thing" rule because Mac
(sandbox) and Web (server uploads) need the same "copy back" hook. Foundation chat to confirm in
`PLATFORM-INTERFACE.md`.

## A-03 Host-only styling differences — OPEN
Applied by the host's own stylesheet (`wwwroot/android.css`, new file), no Ui file touched:
1. Hide the title-bar window controls (min / max / close). Android has none. *(Recommended — same
   kind of difference as the Mac's traffic lights.)*
2. Tablet (per `Portal & Android` 12d–12f): no Ctrl K text field (search icon only), no theme
   toggle in the top bar (still in Settings › Appearance), no status bar, rails 72 / 72 / 60 px
   with 48 px targets, left-bar labels under the icons, no hover-expand on touch.

For: zero Ui edits; matches the spec. Against: host CSS depends on Ui class names — if the Reader
chat renames a class, Android drifts silently. Mitigation: the emulator screenshots in CI.

## A-04 Printing on Android — OPEN
| Option | For | Against |
|---|---|---|
| (a) Android's print framework (system print dialog; the PDF handed to it as-is) | Every printer the phone already knows (Mopria, vendor plugins, Save as PDF), no network permission, OS component (allowed). No rasteriser needed. | Not Chuvadi.Print; print options are the system dialog's. |
| (b) Chuvadi.Print.Ipp to network printers | Same engine as other platforms. | Needs INTERNET + Wi-Fi multicast permissions (Play data-safety + "nothing leaves this device" wording); raster route needs the Print rasteriser decision (adapter vs Print.Pdf.Raster); only IPP printers. |
| (c) Both | Full coverage. | Two paths to test. |

Lean: **(a)** for the first release, (b) later if wanted. Rule 2 note: (a) is an OS component,
not a workaround — the PDF goes to the OS unchanged.

## A-05 One MAUI project shared with Mac, or two — OPEN (needs the Mac chat)
| Option | For | Against |
|---|---|---|
| One `ChuvadiReader.Maui` (net10.0-android; net10.0-maccatalyst) | One host, one DI list. | Mac Catalyst is iPad-style; the Mac chat may prefer a native AppKit/WKWebView host. Android and Mac release cadences get coupled. |
| Two (`ChuvadiReader.Android`, Mac's own) | Each platform ships on its own; matches `ChuvadiReader.Windows`. | Duplicate service registration (≈45 lines). |

Lean: **two**, plus one shared `AddChuvadiReaderCore()` registration in Core (see A-06 #4).
Asked through the coordinator; Mac's answer pending.

## A-06 Existing-file changes this platform needs — OPEN
Prepared as one proposal with exact diffs in `docs/android/EXISTING-FILE-PROPOSAL.md`
(built up as items are confirmed). Known so far:
1. `ChuvadiReader.Core.csproj`: umbrella `Chuvadi.Pdf` → individual packages (rulebook; saves
   ~6.7 MB on phones).
2. `Chuvadi.Sheets` 1.1.2 → 2.0.1 (namespace change in Core; rulebook version).
3. `Chuvadi.Docs` 1.1.0 → stays until docs-v2.0.0 (rulebook).
4. Optional: move the service list and `theme.js` into Core/Ui so hosts don't copy them.
5. Phone layout hooks (A-07).

## A-07 Android phone layout — OPEN
`Portal & Android` 12g–12j: bottom bar (Read · Mark · Arrange · Protect; Open/Find/Library/
Settings in ⋮), tool strip above it (Mark/Protect only), app bar (back · title · ‹ n / N › · ⋮),
View sheet, primary action as a floating button. Not in the Ui today.
- Who builds it: Arun's decision (coordinator, 6 Nov).
- Where: new files in `ChuvadiReader.Ui` (e.g. `Components/Phone/`) or a new
  `ChuvadiReader.Ui.Phone` library. Lean: new files in `ChuvadiReader.Ui`, so every host shares them.
- Hooks needed in existing files (exact diffs to follow): `MainLayout.razor` must render the phone
  shell instead of the top bar / left bar when the form factor is phone; `Reader.razor` (and the
  Bench/Redact pages until they become modes) must not render the side rails on phone. Mode,
  page counter, Document menu and tool commands already flow through `ShellService`, so the phone
  components need no other hooks.

## A-08 Where the Chuvadi packages come from — OPEN
The rulebook says to `dotnet pack` chuvadi-pdf from tag v3.31.1. chuvadi-reader already commits
the exact 3.31.1 set (plus Fonts 1.0.0, LiPicons.Blazor 1.1.0, Docs 1.1.0, Sheets 1.1.2) in
`ci/packages`, which its own CI uses. The Android build restores from that feed.
For: byte-identical to what Windows ships; no repacking. Against: differs from the rulebook's
wording. Lean: keep the Reader's feed. (Re-packing from the tag stays possible as a check.)

## A-09 App icon master — OPEN
Only the 256 px Windows icon exists in the repo. Play needs a 512 px store icon and an adaptive
icon (foreground layer, ~432 px). Needed: the vector master from `Brand Assets.dc.html`, produced
by Arun (the handout says to make the final SVG in a vector tool).
