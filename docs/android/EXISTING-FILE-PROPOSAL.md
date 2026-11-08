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

## P-06 Back closes the open card — for Foundation's combined patch (coordinator decision (a), 7 Nov)
Patch: [`proposal/P-06-back-closes-card.patch`](proposal/P-06-back-closes-card.patch), against
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
Patch: [`proposal/P-07-no-duplicate-reader-history.patch`](proposal/P-07-no-duplicate-reader-history.patch), against
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
