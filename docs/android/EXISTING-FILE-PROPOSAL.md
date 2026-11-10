# Android — proposed changes to existing chuvadi-reader files

One proposal for Arun to approve in one go (rule 4). Each change: exact diff, why, pros and
cons, and how it was verified. **Nothing here has been applied to chuvadi-reader.** Diffs are
against `c7b9e44`. Items are added as they are confirmed; approval can be per item.

Status (7 Nov): P-01 applied centrally by Foundation. P-02 waits on the Reader chat. P-03 moved to the
Mobile app UI chat. P-04 covered by Foundation's host kit. P-05 withdrawn. **P-06 decided (a) by the
coordinator, for Foundation's combined patch.**

---

## P-01 `src/ChuvadiReader.Core/ChuvadiReader.Core.csproj` — individual chuvadi-pdf packages
Rulebook + library report decision 11: individual packages, not the `Chuvadi.Pdf` umbrella. The
umbrella also pulls `Pdf.PdfA` (4.3 MB), the deprecated `Fonts.Bundled` (2.3 MB) and `Fonts.Woff2`,
plus `Color` and `Xfa`, none of which the Reader uses. The list below is exactly the chuvadi-pdf
namespaces Core and Ui `using` today.

```diff
@@ -1,17 +1,35 @@
 <Project Sdk="Microsoft.NET.Sdk">
   <PropertyGroup>
     <TargetFramework>net10.0</TargetFramework>
+    <!-- One version for every chuvadi-pdf package (they are mono-versioned; never mix). -->
+    <ChuvadiPdfVersion>3.31.1</ChuvadiPdfVersion>
   </PropertyGroup>
 
   <ItemGroup>
     <!--
-      chuvadi-pdf consumed ONLY as its packaged distribution (the Chuvadi.Pdf
-      meta-package), restored from the local feed in ./localpackages via the
-      solution nuget.config. No project reference, no vendored source.
-      The meta-package pulls Chuvadi.Pdf.Documents + Chuvadi.Pdf.Svg (and the
-      rest of the cross-platform modules), which is what ChuvadiPdfReader uses.
+      chuvadi-pdf consumed ONLY as its packaged distribution, restored from the
+      local feed in ./localpackages via the solution nuget.config. No project
+      reference, no vendored source. Individual packages, not the Chuvadi.Pdf
+      umbrella: exactly the modules Core and Ui use (the umbrella would add PdfA,
+      Color, Xfa and the deprecated Fonts.Bundled / Fonts.Woff2, ~6.7 MB).
     -->
-    <PackageReference Include="Chuvadi.Pdf" Version="3.31.1" />
+    <PackageReference Include="Chuvadi.Cryptography" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Primitives" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Objects" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.IO" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Documents" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Graphics" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Images" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Forms" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Authoring" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Operations" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Rendering" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Rendering.DisplayList" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Svg" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Text" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Redaction" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Signatures" Version="$(ChuvadiPdfVersion)" />
+    <PackageReference Include="Chuvadi.Pdf.Watermark" Version="$(ChuvadiPdfVersion)" />
     <PackageReference Include="Chuvadi.Docs" Version="1.1.0" />
     <PackageReference Include="Chuvadi.Sheets" Version="1.1.2" />
   </ItemGroup>
```

- **For:** smaller app on every platform (most on phones); deprecated packages out; the version
  is one property.
- **Against:** 17 references instead of 1; a future Core feature that needs a new module (e.g.
  Xfa, PdfA) must add its reference.
- **Behaviour change:** none intended — same 3.31.1 code; only unused modules drop out. The test
  project keeps its own umbrella reference (fixtures), unchanged.
- **Verified (sandbox):** Core, Ui and the test project build with 0 warnings; **all 161 Reader
  tests pass**. Not yet verified: the Windows WPF host build (needs Windows CI), and the measured
  size saving on the Android package (next session).

## P-02 Chuvadi.Sheets 1.1.2 → 2.0.1 — diff to follow
Rulebook version. Breaking: namespace `Chuvadi.Sheets.Excel` → `Chuvadi.Sheets.Model` (one using
in Core), `XlsxFormatException` catches, streams no longer closed by the library. Affects every
platform — probably better owned by the Reader chat; listed here because the rulebook pins 2.0.1.

## P-03 Phone layout hooks — diffs to follow (DECISIONS A-07)
`Layout/MainLayout.razor` and `Pages/Reader.razor` (+ Bench/Redact pages) — render the phone shell
on `data-form-factor="phone"` instead of the top bar, left bar and side rails.

## P-04 Shared host pieces (optional) — diffs to follow (DECISIONS A-06 #4)
Move `theme.js` into `ChuvadiReader.Ui/wwwroot/js/` and the host service registrations into one
`AddChuvadiReaderCore()` in Core, so each host stops copying them.

## P-05 — withdrawn (6 Nov)
A-10 is solved host-side through `IAccount` (Foundation's `UserProfileService` reads it first); no Core edit.

## P-06 Back closes the open card — for Foundation's combined patch (coordinator decision (a), 7 Nov) — **taken by Foundation**
Patch: [`proposal/applied/P-06-back-closes-card.patch`](proposal/applied/P-06-back-closes-card.patch) (in Foundation), against
platform/foundation **2fafb60**; applies cleanly to 2fafb60 and to **615afde** (third combined patch). Files: `Ui/Pages/Reader.razor` (+3 lines:
inject `IAppLifecycle`, subscribe, unsubscribe) and `Ui/Pages/Reader.Shell.cs` (+28: `OnBackRequested`).

What it does: on the system Back gesture, if a card is open (measure included), the Reader closes it
exactly as Escape does and consumes the gesture; otherwise it returns false and the host does its
default (previous screen, then leave the app). Sheets come first on the phone: PhoneShell subscribes
before the page does (the layout initialises before its body), and the host stops at the first handler
that consumes.

- **Why:** on the tablet the Print card stayed open on Back (emulator run 42281134585, both tablets);
  only PhoneShell's sheets listened.
- **Windows unchanged:** the kit's `NoAppLifecycle` never raises `BackRequested`; the subscription is one
  delegate added at page start (no JIT of the handler unless raised).
- **Verified (sandbox):** on 615afde + Mobile UI 745ef8e + this patch: Platforms solution with `-warnaserror`
  0 warnings, 0 errors; tests 171 + 33 + 12 + 19 pass; Android host 0 warnings. On device: `platform.py` "back closes an open card (Print) and stays on the same screen" (same
  route, same tab) — will run when GitHub Actions runs again.
- **Not included (say if wanted):** Back closing the pages drawer or the find bar (Escape closes both on
  the desktop). Same pattern, a few lines each.

## P-07 Open from another app: no duplicate "/reader" history entry — **taken by Foundation (seventh combined patch part 2a, 9fbed93)**
Patch: [`proposal/applied/P-07-no-duplicate-reader-history.patch`](proposal/applied/P-07-no-duplicate-reader-history.patch), against
platform/foundation **8098695**; one file, `Ui/Layout/MainLayout.razor` (+9 −1).

`OnOpenRequested` navigates to `/reader` on every open request, even when the Reader is already showing (it takes the
request live through `OnOpenRequestedLive`). Each extra navigation adds another `/reader` entry to the WebView
history. On Android, Back walks that history after the Ui declines, so each one is a Back press that does nothing
visible: round 5 counted 4 such presses after 4 opens (DOCX, XLSX, Share, no-print), on all four emulators. The change
navigates only when the Reader isn't the current page.
- **For:** Back on Android goes straight through real screens; no behaviour change on any desktop (no history Back
  there, and the Reader already consumed the request without the navigation).
- **Against:** one more condition in MainLayout.
- **Verified (sandbox):** Platforms `-warnaserror` 0 warnings; tests 171 + 54 + 32 + 16 pass. On device: round 6
  (the composition applies Android's pending proposals), check "back steps back … with no dead presses".

## P-08 Paths shown to the person go through a host seam, `IPathLabels` (AT-07) — **decided (a), D-146 — taken by Foundation (twelfth combined patch part 4, c91a581)**
Patch: [`proposal/P-08-path-labels.patch`](proposal/applied/P-08-path-labels.patch), against platform/foundation **022b7c0** (applies
on it alone, and on 022b7c0 + Mobile UI 558a276); 16 files, +89 −23. Rebased 9 Nov 07:30 onto the typed registrations:
the seam is `Seam<IPathLabels, PlainPathLabels>(services, life)`, and `TypedRegistrationTests` pins it.

AT-07: on Android every document and picked folder is a working copy in the app's private cache, and the Ui put the
path in front of the person as a `title` (tooltip, and the accessible name TalkBack reads) or as text: tablet and phone
tabs, Home's cards, rows, pinned rows, category folder and watched folder, Library's folder and rows, Merge and Split
sources, the Export / Press / Scatter folder lines in the Reader, Bench and Library, and Settings' save, watched and data
folders. So TalkBack read `/data/user/0/in.chuvadi.reader/cache/work/open/1429e6d5…/report.pdf`.

**What the patch does**
- `ChuvadiReader.Platform/Services.cs` — the contract and its default:
  ```csharp
  public interface IPathLabels { string Describe(string? path); }               // the person-facing label; "" for null
  public sealed class PlainPathLabels : IPathLabels { … => path ?? string.Empty; } // kit default: the path itself
  ```
- `ChuvadiReader.Hosting/ChuvadiReaderServices.cs` — `Seam<IPathLabels, PlainPathLabels>(services, life)` after
  `IFileManager` (typed, so the trimmer keeps its constructor — AT-03); `TypedRegistrationTests`' pinned list gains
  `"IPathLabels = PlainPathLabels"`.
- Ui (13 files) — `@inject ChuvadiReader.Platform.IPathLabels PathLabels` and `PathLabels.Describe(…)` in the 23 places
  above. Nothing else changes in the markup.
- Tests (Hosting.Tests):
  - `Default_path_labels_show_the_path` — the kit's default is `PlainPathLabels` and returns the path exactly (desktops
    unchanged), `""` for null.
  - `Ui_shows_paths_only_through_path_labels` — a drift guard: reads every `.razor` in the Ui (copied as text, like the
    Windows drift test) and fails on any `title`, `aria-label` or `Text` parameter, or any text node, that shows a
    `…Path` / `…Folder` value directly. Checked to catch all 23 old lines and none of the new ones.

**Behaviour:** Windows, macOS, Linux and Web: identical (the default returns the path, so the tooltip and the visible
paths are character for character what they were). Android: `AndroidPathLabels` (host, on `platform/android`) answers
from the document links — device storage shows its place there (`Download/report.pdf`), another app or a cloud provider
shows the name, a picked folder shows its own place and the file's place in it; the app's data folder (Settings › About)
shows as it is.

**Decision (D-146):** (a). For: each platform gets the truthful label; Windows doesn't change. Against: one more contract
member. Rejected: (b) the file name everywhere (takes the full path from Windows, leaves Android's folders wrong); (c)
readable working-copy paths (TalkBack still reads a meaningless location).

**Verified (sandbox), on 022b7c0 + Mobile UI 558a276 + this patch:** Platforms `-warnaserror` 0 warnings; Core 212,
Hosting 66, MobileUi 16, WebUi 39 pass; Android Debug and Release `-warnaserror` 0 warnings. Earlier, on 42461ba alone + this patch: Platforms solution `-warnaserror` 0 warnings, 0 errors; Hosting
tests 61 pass. On 42461ba + Mobile UI 1f4b4c3 + this patch: Core tests 210, Hosting 61, MobileUi 16, WebUi 39 pass;
Android host Debug and Release `-warnaserror` 0 warnings. On device, run 42541330985 (phone and tablet API 36, first
version of the patch): `platform_checks.py` "no private cache path in tab, card or row titles, accessible names or text"
pass on both.
