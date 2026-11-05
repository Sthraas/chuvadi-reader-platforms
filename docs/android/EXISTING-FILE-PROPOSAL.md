# Android — proposed changes to existing chuvadi-reader files

One proposal for Arun to approve in one go (rule 4). Each change: exact diff, why, pros and
cons, and how it was verified. **Nothing here has been applied to chuvadi-reader.** Diffs are
against `c7b9e44`. Items are added as they are confirmed; approval can be per item.

Status: **P-01 ready.** P-02 … P-04 listed, diffs to follow.

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
