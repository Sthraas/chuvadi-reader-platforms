# Chuvadi Reader: platform readiness and package list

Compiled by the coordinator on 6 Nov 2026 from each library chat's own answers: (A) platform readiness, (B) package list. Targets: Windows, macOS, Linux, Android, and Web (always server-side only, never browser WebAssembly, per Arun). Answers are as the chats gave them; nothing has been changed in any repo. Every "proposal" still needs Arun's decision.

Checked against: monorepo main 1613d51 (Print, Docs, Sheets, Zip, Fonts), Layout main 22d5a07, Pdf tag v3.31.1.

Contents: 1 Print · 2 Docs · 3 Sheets · 4 Zip and Fonts · 5 Pdf · 6 Shaper (OpenType, Text.Shaping) · 7 Markup · 8 Layout · 9 Coordinator summary

---

## 1. Print (Chuvadi.Print, .Ipp, .Remote, .Windows)

### 1A. Platform readiness (main 1613d51; saved in the Print project as claude/print-platform-readiness.md)

| # | Question | Core (Chuvadi.Print) | Ipp | Remote | Windows |
|---|---|---|---|---|---|
| 1 | Fully managed? Native code? | Yes. No P/Invoke, no native binaries. | Yes. Only .NET sockets, HttpClient and SslStream. | Yes. | All C#, with 26 classic [DllImport] declarations in one internal class. 14 call winspool.drv (StartDoc/Page, WritePrinter, EnumPrinters, OpenPrinter, GetPrinter, DocumentProperties, DeviceCapabilities and the default-printer calls). 12 call gdi32.dll (CreateDC/IC, StartDoc/Page, GetDeviceCaps, StretchDIBits and others). No native binaries shipped. Guarded by [SupportedOSPlatform("windows")] and a run-time OperatingSystem.IsWindows() check that throws PlatformNotSupportedException. XpsWriter is portable. |
| 2 | Windows-only APIs outside the spooler path? | None. | None. | None. | None: no registry, no WinRT, no COM. Phase 4 part 3 will add COM calls (the Print Document Package API) and the PrintTicket conversion, on the same spooler path with the same guards. |
| 3 | Target framework; graceful failure elsewhere? | net10.0, no runtime identifiers. Loads everywhere. | Same. | Same. | Plain net10.0, not -windows, so it loads on Mac, Linux, Android and servers. A Windows type there throws PlatformNotSupportedException with a message. |
| 4 | Trimming and AOT? | Not flagged. The analyzers warn (IL2026, IL3050) only about PrinterRegistry's JSON, which uses reflection-based System.Text.Json and the non-generic enum converter. | No warnings of its own. | Same kind of JSON warnings, from the hub and agent protocol and journal (6 call sites plus the enum converter). | No warnings. The P/Invokes are DllImport, not source-generated LibraryImport. NativeAOT accepts them, and nothing blocks ReadyToRun. |
| 5 | File system | Works from streams. File paths are optional conveniences (job from a file, image output folder, saving the printer registry). No fixed locations. | The PWG raster target spools to a temp file (TemporaryFolder or the system temp folder, deleted when closed). The PDF-as-is and port 9100 routes stream. | The agent's journal, downloads and credentials go in a folder the host gives it. The hub's job store is in memory or files, the host's choice. | GDI and RAW: none. XpsWriter writes to a stream; writing to a file path is a convenience. |
| 6 | Startup cost | Nothing eager: no static constructors, no Lazy. | Discovery and capability queries only run when called. | Nothing until the host starts the hub or agent. | Printer enumeration and driver queries only run when called. |
| 7 | Thread safety | No static mutable state anywhere in Print. PrinterRegistry is locked. Jobs and targets are one per job. | The capability cache is locked and shareable. Clients and targets aren't documented as safe to share. | The hub and job stores are locked, so one hub serves many agents. Each agent is one loop. | No shared queue objects; the Windows spooler handles concurrency between jobs. |
| 8 | Fonts | None shipped or loaded. | None. | None. | None shipped. XpsWriter embeds only the font bytes the caller passes in. The ManualTests sample reads a system font, but that's sample code and isn't shipped. |

What printing means on each platform:

- **Windows:** every route.
- **Linux and Mac:** IPP and IPPS to network printers, the local CUPS server over IPP, port 9100, and PDF sent as-is.
- **Android:** IPP, IPPS and port 9100 straight to network printers. Discovering printers on the network needs the app to hold Android's Wi-Fi multicast lock and network permissions. Android's own print dialog is a hand-off the app does itself; Print doesn't wrap it.
- **Web server:** either the server prints directly over IPP or port 9100, or a site agent connects out to the server's hub (Chuvadi.Print.Remote) and prints locally. Handing off to the browser's print dialog belongs to the app, per D-202 P-05.

The unreleased PDF raster package in staging/ inherits whatever the Chuvadi.Pdf packages bring, so that part is for the Pdf chat to answer.

Changes that would be needed (proposals for Arun):

1. Make the four packages trimming- and AOT-safe. Move the JSON in PrinterRegistry and in Remote to System.Text.Json source generation with the generic enum converter, then set IsTrimmable and IsAotCompatible to true so the analyzers keep them clean. The JSON output must stay byte-identical, which the existing tests and saved files prove. Small job, but needs approval: it changes the project-file flags and the JSON engine.
2. Convert the 26 DllImport calls to source-generated LibraryImport. No behaviour change, and only Arun's Windows run can prove that. Best done before Phase 4 part 3, so the new COM and PrintTicket calls start out in the same style.
3. Document which objects are thread-safe, type by type, in the GUIDE. This needs a short audit of the targets first.
4. Optionally spool PWG raster in memory, for servers or containers with no writable temp folder. This would be a new option, so new API.
5. Add an Android note to the GUIDE about the multicast lock and permissions discovery needs. Docs only.

### 1B. Package list (saved in the Print project as claude/print-reader-package-list.md; checked against main 1613d51 and the rc.2 release record, packages packed locally to confirm dependencies)

| Package | Take now | Release asset (all .nupkg, lib/net10.0) | Depends on | For |
|---|---|---|---|---|
| Chuvadi.Print | 1.0.0-rc.2 | Chuvadi.Print.1.0.0-rc.2.nupkg | nothing | PrintJob, PrintSettings, PrintRouter, IPageRasterizer, PNG preview, audit. Every platform. |
| Chuvadi.Print.Ipp | 1.0.0-rc.2 | Chuvadi.Print.Ipp.1.0.0-rc.2.nupkg | Chuvadi.Print ≥ 1.0.0-rc.2 | IPP/IPPS, CUPS over IPP, raw port 9100, network discovery. Every platform. |
| Chuvadi.Print.Windows | 1.0.0-rc.2 | Chuvadi.Print.Windows.1.0.0-rc.2.nupkg | Chuvadi.Print ≥ 1.0.0-rc.2 | Windows spooler (raster) and Windows RAW. Loads anywhere, works only on Windows. |
| Chuvadi.Print.Remote | 1.0.0-rc.2, only if printing goes through a server hub and site agents | Chuvadi.Print.Remote.1.0.0-rc.2.nupkg | Chuvadi.Print ≥ 1.0.0-rc.2 | Hub, agent, job journal. |
| Chuvadi.Print.Pdf.Raster | not released (in staging, pinned to Pdf 3.22.1) | — | Chuvadi.Pdf | The ready-made PDF rasteriser. |

- Release link: https://github.com/arunshivab/chuvadi/releases/tag/print-v1.0.0-rc.2. The asset names come from the release record, whose checksums were checked against GitHub on 4 Nov. The Print session can't call the releases API, so it couldn't recheck them live.
- Pdf and Layout: none of the four released packages depends on either.
- The XPS work ships in 1.0.0-rc.3, tagged once submission to Windows queues is in (D-201). The Reader should take rc.2 now and move to rc.3 when it wants vector printing on Windows.

Per platform:

| Platform | Works with rc.2 | Not yet |
|---|---|---|
| Windows | Any printer queue as raster through the spooler, with all driver settings (paper, tray, duplex, copies). RAW pass-through. IPP printers directly. | Vector printing to queues (XPS) comes in rc.3. Sending a PDF as-is to IPP printers needs a font inspector (gap 2 below). |
| macOS, Linux | Local CUPS queues over IPP. Network IPP/IPPS printers. Raw port 9100. Discovery. | Windows routes, as expected. |
| Android | Network IPP/IPPS printers and raw port 9100. Discovery works if the app holds Android's Wi-Fi multicast lock and has network permission. | No CUPS. Android's own print dialog is the app's hand-off; Print doesn't wrap it. |
| Web server | The server prints to network printers directly. Or a site agent connects out to the server's hub (Chuvadi.Print.Remote) and prints locally. | Printing on the user's own machine through the browser's print dialog belongs to the app (D-202). |

Entry points (the app picks the backend at run time; Print has no automatic platform switch):

- **Windows:** `WindowsPrinters.List()`, `WindowsPrinters.DefaultPrinterName`, `WindowsPrinters.GetCapabilities(name)`. To print: `new PrintJob(pdfBytes).WithRasterizer(r).PrintTo(new WindowsPrinterTarget(name))`. Router alternative: `new PrintRouter(new RasterRoute(new WindowsPrinterTarget(name))).Print(job)`.
- **macOS and Linux:** `CupsQueues.List()`, then `using var router = IppRoutes.CreateCupsRouter(queue.Uri!)` and `router.Print(job)`.
- **Every platform, network printers:** `NetworkPrinterDiscovery.Browse()`, then `IppRoutes.CreateRouter(uri)`; for saved printers, `IppRoutes.CreateRouter(savedPrinter)` with `PrinterRegistry`. Then `router.Print(job)`. `new RawSocketTarget(host).Send(bytes, title, ct)` sends to port 9100 printers.
- **Android:** the network-printer path above. Discovery also needs the app's multicast lock.
- **Web server:** the network-printer path above, or `PrintHub` on the server with `PrintAgent` at each site.
- **Save as PDF:** never a Print route, on any platform (D-48). The Reader already has the PDF, so it saves it, or selected pages, with the Chuvadi.Pdf writer. A document it generates is exported with Chuvadi.Layout's PDF output.

Breaking changes the Reader must handle:

- From 0.x: Print is now four packages. Add Print.Windows, .Ipp or .Remote as needed; namespaces and type names are unchanged.
- From 0.x: the PDF adapter is renamed Chuvadi.Print.Pdf.Raster (still unreleased). PdfFileTarget and the virtual printer are gone.
- rc.1 to rc.2: additive, except that the audit file gains a 13th column, Route, placed last.
- Coming in rc.3: if the Reader uses Remote, `PrintAgent.RunOnceAsync` now reports a cancellation as OperationCanceledException even when it lands during a failed hub exchange.

Gaps that need Arun's decision:

- **Rasteriser.** Every raster route needs an IPageRasterizer. (a) The Reader writes a small adapter over its own Chuvadi.Pdf renderer; the interface is small: Open, then PageCount, GetPageSize and Render. (b) Wait for Chuvadi.Print.Pdf.Raster to be released, which needs the staging move and the move to Pdf 3.31.0. Print recommends (b) if the Reader can wait, otherwise (a) now and switch to (b) later.
- **PDF as-is.** Sending the PDF straight to printers that accept it needs an IPdfFontInspector. Without one, the router prints raster instead, which is safe but slower. Print's own inspector, built on Pdf 3.31's FontEmbeddingReport, comes with Phase 4 part (d). The Reader could also write its own.

Note from Print: the new tests/Chuvadi.Print.Xps.Tests project is untracked; apply and commit chuvadi-print-xps-tests.zip as delivered (its CHANGELOG line is in the zip).

---

## 2. Docs (Chuvadi.Docs, Chuvadi.Docs.Conversion)

### 2A. Platform readiness (main 1613d51 plus PR 2b; saved in the Docs project as claude/docs-platform-readiness.md)

Both libraries are pure managed net10.0 code with no Windows-only APIs, and they work under trimming and NativeAOT. Markup (which Conversion depends on) and the shared code compiled into Docs were checked too. A test app using every main feature was run four ways on Linux: normal (JIT), ReadyToRun, trimmed, and NativeAOT. All four gave identical results, and so did runs under invariant globalization and the Turkish, German, Arabic and Tamil cultures. macOS and Android were not tested anywhere.

| # | Question | Chuvadi.Docs | Chuvadi.Docs.Conversion |
|---|---|---|---|
| 1 | Managed only? | Yes. 100% C#: no unsafe, no P/Invoke, no native files. .NET itself uses each platform's native crypto and zlib underneath. | Yes (Markup too). |
| 2 | Windows-only APIs? | None. No System.Drawing, GDI, registry or WinRT. Three OperatingSystem.IsWindows() checks in shared code only set Unix file permissions. | None. |
| 3 | Target | Plain net10.0 | Plain net10.0 |
| 4 | Trimming / AOT | The trim, AOT and single-file analyzers pass with 0 warnings, but the csproj doesn't set the flags yet (P2). Trimmed and NativeAOT builds run every feature with identical results. One reflection use, for rejecting a tracked formatting change; it works under AOT. No Assembly.Load, Activator, serializers or dynamic code. | The analyzers pass (Markup included); same results. |
| 5 | File system | Every path method has a stream or bytes version. No fixed locations. Two exceptions: (a) all three encrypted saves write a temporary file to the system temp folder; it is encrypted, readable only by the owner and deleted on close, but the caller cannot choose the folder (P1). (b) Saving to a path writes a temporary file beside the target, so it needs write access to that folder. Loading an encrypted file decrypts in memory, with no temporary file. | Streams only; no file access at all. |
| 6 | Startup | Nothing runs when the assembly loads; small lookup tables are built on first use. First full pass of the test app (whole process in brackets): JIT about 360 ms (440); ReadyToRun about 130 ms (190); trimmed about 630 ms (750); AOT about 27 ms (50). Second pass: 23, 18, 52 and 10 ms. Working set (runtime included): 73, 70, 58 and 37 MB; managed heap 1.2 MB. The trimmed build is slowest because trimming throws away .NET's precompiled code. Encrypted save or load with the default password strength takes about 80–130 ms here, longer on phones. | Included above. On JIT, the first Markdown import takes about 67–120 ms and the first HTML import about 40–50 ms. |
| 7 | Thread safety | No static state that changes after setup; static tables are built thread-safely by .NET. A Document or DocxReader instance must not be shared across threads; use one per request. 2,000 jobs on 32 threads gave 0 differences (machine has only 2 cores, so code review is the main evidence). | The same. Markup builds two lookup tables on first use without a lock. A race can build one twice, but never exposes a half-built table. |
| 8 | Fonts | None shipped, none loaded. It only writes font names into documents (Calibri in default styles and watermarks, plus whatever the caller sets). Rendering is Layout's and Fonts' job. | None. Default code font name is "Consolas"; the HTML preview names Calibri, Arial and Consolas in its CSS. |

Proposals for Arun:

- **P1. Let the caller choose where encrypted saves put their temporary file.** Now they always use the system temp folder; on a locked-down server, serverless host or container that folder can be read-only or very small. Proposal: a folder option like Sheets' XlsxWriterOptions.TempDirectory, and possibly an in-memory option. Pros: parity with Sheets; works where the temp folder doesn't. Cons: new public API; the in-memory option needs a small shared change and holds one extra copy of the package in memory. Release: 2.0.0 (folder option only) or 2.1.0.
- **P2. Add IsTrimmable and IsAotCompatible to the Docs and Conversion csproj files** (Markup through its own chat). Pros: since warnings are errors, a change that breaks trimming or AOT fails the build; consumers' trimmed builds treat the DLLs as safe to trim. Cons: future reflection needs an annotation.
- **P3. Add a macOS CI job and an AOT test job.** CI currently runs only Ubuntu and Windows; workflow change, coordinator to sequence. Note: with the sandbox SDK (10.0.402), NuGet's security audit flags the AOT compiler package 10.0.13 (GHSA-p3jp-9v83-76w9) and warnings-as-errors stops the AOT publish. A newer SDK should pull a fixed version; check on Arun's machine.
- **P4. Re-run this check after markup-v1.1.0**, since the clean-room rewrite replaces Markup's code.

No change needed: the one reflection use; the temp file beside the target in path saves (makes the replace atomic; stream saves don't use it); the default password strength (callers can change it). The Reader should do encrypted saves and loads off the UI thread.

### 2B. Package list (saved in the Docs project as claude/docs-reader-package-list.md)

**Verdict: the Reader should wait for docs-v2.0.0.** Layout.Docs, which turns a Docs document into PDF, is built against 2.0's renamed namespace (Chuvadi.Docs.Model), and none of the Layout packages are released yet.

**Version clash:** Chuvadi.Layout.Pdf pins chuvadi-pdf to exactly [3.30.2], and the Reader uses 3.31.1. NuGet can't resolve both, so the Layout chat must re-pin or loosen that pin.

Checked against main 1613d51, the tags, the published release pages, and the 1.1.0, 1.5.1 and Markup 1.0.0 nupkgs (downloaded and opened); public APIs of 1.1.0 vs 1.5.1, and 1.5.1 vs PR 2b, compared. Layout rows come from Layout's files on main; the Layout chat should confirm.

| Package | Take | Release / asset | Kind | Depends on |
|---|---|---|---|---|
| Chuvadi.Docs | Wait for 2.0.0. 1.5.1 is the latest release and only a stop-gap. | Now: https://github.com/arunshivab/chuvadi/releases/tag/docs-v1.5.1, Chuvadi.Docs.1.5.1.nupkg (267 KB). Then docs-v2.0.0, Chuvadi.Docs.2.0.0.nupkg | .nupkg (lib/net10.0) | Nothing. Shared code is compiled in; the nuspec lists no dependencies. |
| Chuvadi.Docs.Conversion | Only for Markdown, HTML or text conversion, or a quick HTML preview. Not needed to view or print. | First release in docs-v2.0.0: Chuvadi.Docs.Conversion.2.0.0.nupkg | .nupkg | Docs 2.0.0, Markup 1.1.0 |
| Chuvadi.Markup | Only with Conversion | Released: markup-v1.0.0, Chuvadi.Markup.1.0.0.nupkg. Conversion needs 1.1.0 (the clean-room rewrite), not tagged yet. | .nupkg | nothing |
| shared/Chuvadi.Internal, Chuvadi.Zip | Not packages the Reader takes | — | — | Docs uses .NET's own zip support |
| Chuvadi.Layout.Docs (DocsLayout.Open) | For viewing and printing | Not released (0.1.0) | .nupkg | Layout, Docs 2.0 |
| Chuvadi.Layout and Chuvadi.Layout.Fonts | With Layout.Docs (Layout.Fonts: recommended substitute fonts) | Not released (0.1.0) | .nupkg | Chuvadi.Fonts (released 1.0.0; main is at 1.1.0) |
| Chuvadi.Layout.Pdf (ToPdf, ToPng, PdfShaper) | For Save as PDF and page images | Not released; in staging/ only | .nupkg | Layout, plus six Chuvadi.Pdf packages pinned to [3.30.2] — clashes with 3.31.1 |

Release order the Reader depends on: markup-v1.1.0 → docs-v2.0.0 → the layout-* tags → Layout.Pdf moved out of staging. Packages are attached to GitHub releases only, nothing on nuget.org (D-46), so the Reader needs a local package feed.

Save as PDF:

```csharp
var options = new LayoutOptions { Shaper = new PdfShaper() };
options.FontSources.Add(FontPackSource.For(SubstituteFontPack.Instance));
using var laid = DocsLayout.Open(document, null, options, ct);
laid.ToPdf(outputStream, null, ct);
```

DocsLayout.Open also takes a stream or byte[], and options.Password opens encrypted files. `laid.GetPage(i).ToPng(dpi)` gives page images for the viewer or for Chuvadi.Print.

Per-platform notes (beyond the readiness answer):

- **All platforms, light editing:** load and save rebuilds the file from Docs' model, and anything the model can't hold is dropped on save: charts, shapes other than text boxes (only their text is kept), old-style VML pictures and content controls. The Reader should warn before saving such files. For value-filling edits, DocxTemplate.Fill keeps everything else intact.
- **Windows:** a save to a path keeps the file's attributes and security settings. A read-only file is refused with UnauthorizedAccessException.
- **macOS and Linux:** a save keeps the file's permissions and follows symbolic links.
- **Android:** content URIs are not file paths, so use the stream overloads. Encrypted saves still write a temporary file to the app's cache folder. Run encrypted open and save off the UI thread. For text search in large files, DocxReader streams instead of loading everything.
- **Server with many users:** one Document or DocxReader per request; keep the default reader limits. MaxPartBytes is off by default, so set it for uploads, and never use CreateUnrestricted() for untrusted files. Check HasMacros / GetActiveContent() before offering a download.

Breaking changes. Nothing between 1.1.0 and 1.5.1 breaks compilation (no public member removed or changed). The changes are in behaviour, plus 2.0.0's namespace rename.

- **1.2.0**
  - SaveTo(Stream) now leaves the stream open. Reader: dispose it yourself.
  - DocxReader.Open(stream) now owns the stream. Reader: don't use or dispose it afterwards.
  - Tabs and line breaks now sit inside the run text as \t and \n, not as separate runs. Reader: handle them in Run.Text.
  - "Distribute" alignment now loads as Distribute (was Justify).
  - Paragraph.Alignment = Left now means "inherit". Reader: use GetEffectiveParagraphFormat for what to display.
  - A part over the size limit now throws DocxSecurityLimitException (was InvalidDataException). A missing password is now reported as DocxPasswordRequiredException first.
  - Text extraction changed: no phantom tabs, no deleted text, no duplicated text-box text.
- **1.3.0**
  - Tables load fully structured; a table's borders are only what the file states, in Format.Borders.
  - Styles load: unknown style ids are kept, and Document.Defaults replaces the fixed Calibri 11.
- **1.4.0**
  - Loaded files come with their headers, so Header.Add appends to them. Reader: use SetText or Clear to replace.
  - Lists load as real numbering. Reader: get labels from GetListLabels().
  - A part that isn't well-formed throws instead of loading partly.
- **1.5.0**
  - Only Word packages load.
  - SaveTo(path) writes a temporary file beside the target, so it needs write access to the folder.
  - Identical pictures are stored once, and picture names are renumbered on save.
  - Template syntax changed (placeholder names are trimmed; {{#…}}-style markers are now blocks).
  - PageSetup.SizeStated is new; check it before trusting Size.
- **1.5.1:** only a compile fix.
- **2.0.0 (planned, includes the never-tagged 1.6.0)**
  - Namespace Chuvadi.Docs.Word → Chuvadi.Docs.Model. Reader: change one using line and recompile; nothing else is renamed.
  - Tracked deletions are now kept on save. Text-box text is no longer part of its paragraph's text; notes, fields, comments and properties now survive a save.
  - Every read failure is now DocxFormatException, with the original error inside. Reader: replace catches of XmlException and InvalidDataException.
  - The template methods now reject a broken package and write nothing.
  - Encrypted save gains a stream version, and encrypted files over about 7 MB now open.
  - A missing or corrupt main document part is reported at DocxReader.Open, not at the first read.
  - A broken header or footer now reads as blank and is listed in SkippedParts.
  - Saving onto a folder path now gives UnauthorizedAccessException.
  - Conversion: its import limits throw DocxLimitExceededException.
  - PR 3, still to come, changes only text, versions and CHANGELOGs.

Docs also found the README still says comments, tracked changes and most fields are lost on load and save; out of date since 1.6.0. It will correct that in PR 3 as a documentation fix.

---

## 3. Sheets (Chuvadi.Sheets)

### 3A. Platform readiness (main 1613d51, Sheets 2.0.1 plus the shared code it compiles in; Linux x64; Mac and Android not run; saved as claude/sheets-platform-readiness.md)

Chuvadi.Sheets is fully managed, has no Windows-only APIs and runs under NativeAOT. **One real problem: under NativeAOT, typed import and export silently lose every value.**

| # | Question | Sheets 2.0.1 |
|---|---|---|
| 1 | 100% managed? | Yes. No P/Invoke, DllImport/LibraryImport, unsafe code or native binaries, and zero NuGet dependencies. The only "InteropServices" use is a managed dictionary helper (CollectionsMarshal). |
| 2 | Windows-only APIs? | None: no System.Drawing, GDI, registry or WinRT. Three runtime OperatingSystem.IsWindows() checks only set Unix file permissions on temporary and replaced files. |
| 3 | Target | Plain net10.0. |
| 4 | Trimming / AOT | Not clean. The trim and AOT analyzers report 3 IL2090 warnings, all in typed import and export. A NativeAOT build works for models, the streaming reader and writer, encryption, number formats and auto-fit. But ToXlsx&lt;T&gt; writes empty cells and ReadXlsx&lt;T&gt; returns empty objects, with no error, because trimming removes the properties. Under the normal runtime both are correct. Nothing else is a concern: no Assembly.Load, no serializers, and ReadyToRun needs nothing special. |
| 5 | File system | Reading works fully from streams, with no disk use; encrypted files are decrypted in memory. Every save writes temporary files, even a save to a MemoryStream: one per sheet, plus one for the package when encrypting. They go in the system temp folder, and only XlsxWriter lets you choose another folder. Path saves also write a temporary file beside the target. Still path-only: the encrypted Workbook.SaveTo (the stream version is D3, in 2.1.0) and the ReadXlsx DataSet, DataTable and List&lt;T&gt; readers. No fixed locations. |
| 6 | Startup / first use | Nothing runs when the library loads; small built-in tables are built on first use. Normal runtime, first calls in a fresh process: save 73–81 ms, load 37–40 ms, first formatted value 25–48 ms, encrypted save and load 34–44 ms; peak memory 56–60 MB including the runtime. NativeAOT: about 1 ms per first call (6 ms for encryption), peak memory 24 MB, 10.7 MB app binary. |
| 7 | Thread safety | Shared state is safe: fixed tables, one concurrent cache of parsed number formats with a size cap, per-thread formatting buffers, no mutable global settings. 256 runs, 32 at a time (build, auto-fit, save, load, format, encrypt) all matched the single-threaded result. Workbook, readers and writers are not thread-safe; use one per request. |
| 8 | Fonts | None shipped or loaded. Auto-fit uses built-in width tables for Calibri, Cambria, Arial, Times New Roman and Courier New, scaled for other fonts, so it behaves the same on every platform. |

Formatting also gave identical results with .NET's invariant-globalization mode on, as many containers run.

Changes needed, as proposals for Arun (nothing built):

- **PR-1, typed import and export under trimming/AOT, for 2.1.0. The real gap.** (a) Mark the type parameter of ToXlsx&lt;T&gt;, XlsxExportConfig&lt;T&gt;, XlsxExport.AddSheet&lt;T&gt; and ReadXlsx&lt;T&gt; so the trimmer keeps its properties and constructor, then switch the trim/AOT checks on permanently. (b) Only flag these methods as not AOT-safe, so apps get a build warning instead of silent data loss. Sheets recommends (a). Nothing changes under the normal runtime. Rule 5 point: apps passing their own unmarked generic types would get a new warning in trim-checked builds only.
- **PR-2, saving without disk access.** A read-only container or sandboxed app cannot save at all today, and the stream overloads (Workbook.SaveTo(Stream), ToXlsx(stream), XlsxExport) cannot choose the folder. (a) Let the stream overloads take the temp folder. (b) An option to keep the temporary data in memory (or in memory up to a size); encrypted saves stay encrypted, as on disk. Sheets recommends (b) in 2.1.0, new API only. It touches the temp-file helper Docs is moving into shared/ (D-206), so it follows that PR.
- **PR-3, stream versions of the ReadXlsx DataSet, DataTable and List&lt;T&gt; readers**, for uploads on the server and Android. New API only, 2.1.0.
- **PR-4, memory for large encrypted reads.** The whole decrypted file is held in memory, once per concurrent user, bounded by the existing size limits. Recommend documenting now and deciding with the planned 2.1.0 change to stream the encrypted container.
- **PR-5, docs only:** a short platform and thread-safety section in the README and guide.
- **PR-6, test runs on Android and macOS** before the Reader depends on them: temp folder, Unix file permissions and safe file replacement.

### 3B. Package list (saved as claude/sheets-reader-package-list.md; SH-9 added to claude/sheets-2.1.0-scope.md)

**Verdict: take Chuvadi.Sheets 2.0.1 now; nothing about 2.1.0 needs to be waited for.** Viewing and printing through Layout is not ready yet: no Layout package is released, and Layout.Pdf pins an older chuvadi-pdf than the Reader's 3.31.1.

| # | Question | Answer |
|---|---|---|
| 1 | Package and version | Chuvadi.Sheets 2.0.1. Neither gap blocks viewing or light editing. The AOT problem is only in object mapping (ToXlsx&lt;T&gt; / ReadXlsx&lt;T&gt;), which a viewer doesn't use; avoid those two in an AOT build. Saving to a stream already works in 2.0.1 and leaves the stream open, but it writes temporary files to the temp folder. 2.1.0 only adds things, so moving to it later is just a rebuild. |
| 2 | Release and asset | https://github.com/arunshivab/chuvadi/releases/tag/sheets-v2.0.1. Asset Chuvadi.Sheets.2.0.1.nupkg, SHA-256 417F537F74826DEEB8CD14492441800243B45DF9E714CD9CE6DAF9138571C253. A .nupkg containing the DLL and its XML docs. Not on nuget.org (D-46), so use a local feed. The tag is signed; the package is not. |
| 3 | Dependencies | None: pure BCL on net10.0, no package dependencies, no link to chuvadi-pdf. Layout's packages (row 5) are only needed for viewing, printing and PDF. |
| 4 | Platform notes | Windows and Linux: tested (CI, Arun's gates, Sheets' measurements). macOS: nothing OS-specific; not run. Android: reading works fully in memory from a stream, so content URIs work; saving needs the app's temp folder (its cache folder); for content URIs, save to a stream rather than a path; not run. Server, many users: safe with one workbook or reader per request; 256 parallel runs gave identical results; allow memory for whole decrypted files; use XlsxReaderOptions.ForUntrustedInput() for uploads and pass a cancellation token; saves write temporary files to disk. All platforms: display formatting is culture-neutral unless the Reader passes a culture (en-IN for Indian grouping). |
| 5 | Viewing, printing, Save as PDF | `SheetsLayout.Open(stream or bytes, SheetsImportOptions, LayoutOptions)` in Chuvadi.Layout.Sheets 0.1.0 returns a LaidOutDocument with pages, SVG and PNG. PDF comes from `doc.ToPdf(stream, LayoutPdfOptions)` in Chuvadi.Layout.Pdf. Fonts come from `FontPackSource.For(SubstituteFontPack.Instance)` in Chuvadi.Layout.Fonts. LayoutOptions.Password opens encrypted files. To confirm with Layout: no Layout package is released yet (the tags wait for fonts-v1.1.0, D-202); Layout.Pdf is still in staging and pins chuvadi-pdf to exactly 3.30.2, which clashes with 3.31.1; the chain is Layout.Sheets → Sheets 2.x and Layout → Fonts 1.1.0, and only fonts-v1.0.0 is tagged. |
| 6 | Breaking changes | Below. |

Breaking changes from 1.1.2 to 2.0.1, and what the Reader must change.

Need code changes:

1. **Namespace (2.0.0).** Chuvadi.Sheets.Excel becomes Chuvadi.Sheets.Model. Change the using lines and recompile; code built against 1.x won't run against 2.x.
2. **Error type for damaged files (2.0.0).** Every damaged or malformed file now throws XlsxFormatException, with the original error inside. Replace catch (InvalidDataException) and catch (XmlException) around reads with catch (XlsxFormatException). A damaged encrypted file opened with a password is now XlsxFormatException, not a password error, so show "file is damaged", not "wrong password". Missing or wrong passwords still throw XlsxPasswordRequiredException.
3. **Old zip API obsolete.** Chuvadi.Sheets.Zip gives warning CS0618, which breaks a build that treats warnings as errors. Move to Chuvadi.Zip.
4. **Conditional-format rules** (ConditionalFormatRule) can no longer be subclassed outside the library (1.6.0).

Compile unchanged but behave differently:

5. Streams are no longer closed by the library: reading since 1.4.0, saving since 2.0.1. The Reader must close its own streams.
6. Very high encryption spin counts are refused. An encrypted file declaring more than 500,000 iterations now fails with XlsxLimitExceededException (1.7.0). Set MaxSpinCount = null to open such files when trusted.
7. Corrected values (1.4.0, 1.5.0); anything shown or cached under 1.1.2 will change: formula cells now return their stored result (they read as empty before); formula cells with no stored result now load; dates in 1904-based workbooks are no longer 1,462 days early; date serials 1 to 59 are now exact.
8. Load and save keeps much more: formulas, defined names, page setup, headers and footers, row and column settings, panes, hidden sheets, conditional formats, data validation, rich text, hyperlinks and comments. Files the Reader saves will differ from what 1.1.2 wrote, for the better.
9. Style details: locale-dependent built-in number formats read with an empty format code and the format id kept; a style built with .VAlign(x) no longer compares equal to the plain CellStyle; conditional cell styles are saved in a different form.
10. Streaming writer: column widths and frozen panes may now be set after the first row.
11. Saving to a path (2.0.1): written to a temporary file next to it and replaced only when the save succeeds. A failed save keeps the old file.

Still lost on load and save, unchanged since 1.1.2 (the Reader should warn before overwriting a file containing these): pictures, shapes, charts and chart sheets; header and footer pictures; macros; pivot tables; extended formatting (underline kind, strikethrough, superscript and subscript, pattern and gradient fills, diagonal borders, indent, rotation, shrink-to-fit, protection and the quote prefix).

Planned 2.1.0, nothing breaking. Adds: encrypted save to a stream (D3); a way to check whether a header exists; package description and tags without "zip"; if Arun approves, the AOT fix, an in-memory spool and stream versions of the ReadXlsx readers.

**New item needing Arun's decision (SH-9).** Layout's open items list A7 findings 8 and 9 for Sheets; both are display-text gaps that matter for a viewer:

- Excel shows the "/" in a date format as the computer's date separator (for example "18-05-1903"), and shows the built-in "d-mmm-yy" format as "02-Oct-24". Sheets keeps "/" and gives "2-Oct-24".
- Serial 0 and times below one day, such as 0.375, display as "########" under date and time formats. Excel shows "00-01-1900", "00:00:00" or "09:00:00".

Fixing these changes displayed text, so it needs a Rule 5 list before any code. Sheets suggests 2.1.0.

Separately: the D-195 font change has merged (PR #72); the guide re-rendered on the new main is byte-identical to the committed PDF.

---

## 4. Zip and Fonts (Chuvadi.Zip, Chuvadi.Fonts, shared/)

### 4A. Platform readiness (main 1613d51; analyzers plus a real trimmed publish on Linux x64; NativeAOT, ReadyToRun, Windows, macOS, Android not tested here — those answers are from code reading)

| # | Question | Chuvadi.Zip | Chuvadi.Fonts | shared/ (compiled into Sheets and Docs) |
|---|---|---|---|---|
| 1 | 100% managed? | Yes. No DllImport, LibraryImport, Marshal or unsafe. | Yes. Same checks. | Yes. Same checks; stackalloc Span only. |
| 1b | Native code behind the BCL | WinZip AES uses .NET's Aes, HMACSHA1 and Rfc2898DeriveBytes, which .NET backs with each OS's own crypto library. ZipCrypto and CRC-32 are our own code. | None. | Aes and the SHA hashes, with the same OS backing. |
| 2 | Windows-only APIs? | None. OperatingSystem.IsWindows() only picks Unix-mode handling and name-case rules. | None. | None. |
| 3 | Target | Plain net10.0. | Plain net10.0. | Same as the libraries that include it. |
| 4 | Trim/AOT safe? | Analyzers (IsTrimmable plus IsAotCompatible): 0 warnings. No reflection, Assembly.Load or dynamic code. | Analyzers: 0 warnings. One typeof(FontPack).Assembly resource lookup. | Via Docs: 0 warnings. Via Sheets: 3 IL2090 (see below). |
| 4b | Real trimmed publish | A trimmed (TrimMode=full) self-contained linux-x64 app using both libraries built with no warnings and ran correctly. | Same app read a font from the embedded resources. | Not part of that app. |
| 4c | NativeAOT, ReadyToRun | Not tested; analyzer cleanliness is the predictor. | Not tested. | Not tested. |
| 5 | File system | Works fully from Stream and byte[]. Non-seekable input is buffered in memory only, never on disk. Real paths only for the directory and file helpers (AddFile, ExtractTo, ZipDirectory). No temp files, no fixed locations. | None. No disk or network. | EncryptedSpool uses a temp file (Path.GetTempPath(), owner-only) for encrypted saves in Sheets and Docs. Neither Zip nor Fonts uses it. |
| 6 | Startup and memory | See below. | See below. | n/a |
| 7 | Thread safety | No mutable static state. CRC table read-only. The Untrusted and None limits presets are immutable (init-only). ZipReader has a per-archive lock plus Interlocked counters, so concurrent entry reads are safe. A writer instance is single-threaded like a stream (not separately verified). | Documented thread-safe. The license text is read lazily; a race at most reads it twice, with the same result. | Only static readonly tables. No caches, Lazy or ConcurrentDictionary found. |
| 8 | How Fonts ships | n/a | 22 .ttf files plus the OFL license as EmbeddedResource (Chuvadi.Fonts.&lt;file&gt;) inside the DLL. | n/a |

Startup and memory (trimmed self-contained, in the Zip sandbox):

- A hello-world baseline ran in 50–60 ms wall time with 19 MB peak memory.
- A smoke test that wrote a zip, read it back and read one font ran in 131–144 ms with 26–27 MB peak memory. The extra ~80 ms and 8 MB is mostly first-call JIT of our code, Deflate and SHA-256, not font loading.
- Nothing eager happens on load. The Fonts static init builds the 22-entry catalog (metadata only) and a name index. A font's bytes are read only on Open (a stream over the embedded data) or ReadAllBytes (copies one font, about 82 KB for Tamil).
- The Fonts DLL is 4.1 MB on disk (1.9 MB compressed in the nupkg).
- Lookup by name and the trimmer: FontPack builds each resource name at runtime and looks it up with GetManifestResourceStream. In the real trimmed run the Tamil font loaded at its full 82,452 bytes, so the trimmer keeps the resources. Works in single-file apps too (no Assembly.Location).

CI and release: neither has a trim or AOT check today.

Other finding: Sheets' 3 IL2090 warnings are in TypeAccessor.cs lines 66 and 106 and XlsxReadExtensions.cs line 177 (object export reflects over T's public properties). Docs has none.

Proposals for Arun (each needs approval; shared ones need sequencing):

1. Add IsTrimmable and IsAotCompatible to Zip and Fonts (Rule 5 list first). Already pass; this records the guarantee and runs the analyzers on every build.
2. CI check for trimming (shared change): a job publishing a small smoke app trimmed on Ubuntu with warnings as errors, using Zip and Fonts and later more packages; plus a NativeAOT publish if the runner can fetch the AOT compiler pack.
3. Sheets reflection warnings: annotate T with DynamicallyAccessedMembers(PublicProperties) at those three places, or accept that object export isn't trim-safe.
4. More platforms in CI: add macos-latest to the matrix (shared change). Android and browser WebAssembly can't be covered by CI easily.
5. Browser WebAssembly: AES entries may not work there. A server-side web app is unaffected. (Arun has now decided Web is server-side only, so this item is closed.)
6. Docs note: a platform-readiness section in the Zip and Fonts docs once results are final.

Zip would approve 1 and 2 first.

### 4B. Package list

**Verdict: Zip and Fonts are in good shape; one decision — wait for fonts-v1.1.0.** The Zip session couldn't query GitHub releases, so the matrix is from tags in the repo and release records; verified and unverified rows are marked.

Versions the Reader should take:

| Package | Take | Why | State |
|---|---|---|---|
| Chuvadi.Zip | 1.0.0 | The only version; the ZipCrypto fix is in it. | Released and verified. |
| Chuvadi.Fonts | Wait for 1.1.0 | 1.1.0 only adds IFontFilePack; the 22 font files are identical to 1.0.0. Main's Chuvadi.Layout.Fonts implements IFontFilePack (needs Fonts ≥ 1.1.0), and Layout takes its Fonts version from main. D-197 requires fonts-v1.1.0 before any Layout tag. | 1.0.0 released. 1.1.0 not tagged yet; the dating PR and tag steps are waiting on Arun. |

If the Reader uses only the fonts and not Layout, 1.0.0 works today.

Release links and assets:

| Package | Tag | Release link | Asset | Size | SHA-256 |
|---|---|---|---|---|---|
| Zip 1.0.0 | zip-v1.0.0 | https://github.com/arunshivab/chuvadi/releases/tag/zip-v1.0.0 | Chuvadi.Zip.1.0.0.nupkg | 51,674 B | e019f9b61d48d705e9b8e81e3ca8bcbb3114056b2127f4e9ea2af0aa51110104 |
| Fonts 1.0.0 | fonts-v1.0.0 | https://github.com/arunshivab/chuvadi/releases/tag/fonts-v1.0.0 | Chuvadi.Fonts.1.0.0.nupkg | 1,908,123 B | c15a82d1caa3d70f3e2abe16dd94201ea1d3dae91764735a19ffa7398c37f5fe |

Asset format: every release carries a .nupkg named &lt;PackageId&gt;.&lt;version&gt;.nupkg, never a loose DLL. GitHub-only, no nuget.org push. Link pattern: https://github.com/arunshivab/chuvadi/releases/tag/&lt;tag&gt;.

Who pulls them in (project references on main 1613d51):

| Package | References | Minimum that works |
|---|---|---|
| Chuvadi.Zip | Nothing references it. Docs, Sheets, Layout and Print have no reference to it. | n/a |
| Chuvadi.Fonts | Layout and Layout.Fonts | Fonts 1.1.0 |
| Chuvadi.Layout.Docs | Layout, Docs | Fonts 1.1.0 and Docs, both unreleased |
| Chuvadi.Layout.Sheets | Layout, Sheets | Fonts 1.1.0 |
| Chuvadi.Layout.Markup | Layout, Markup | Fonts 1.1.0, and Markup 1.1.0 once the swap ships |
| Chuvadi.Layout.Documents | Layout.Docs, Layout.Sheets | Fonts 1.1.0 |

- Zip: Sheets has its own zip code (obsolete since 2.0.0 in favour of Zip), so the Reader takes Zip directly.
- Pdf: separate repo; the Pdf chat must say whether it references Fonts or Zip.
- Version pins: a package's dependency version is the referenced project's &lt;Version&gt; at pack time.
- Unreleased versions on main: Docs and Docs.Conversion 1.6.0 (never tagged) and Markup 1.1.0 (the swap release). Don't pin to those until tagged.

Font pack:

| Item | Value |
|---|---|
| Files | 22 TrueType files: Latin ×4 (Regular, Bold, Italic, Bold Italic), plus Bengali, Devanagari, Gujarati, Gurmukhi, Kannada, Malayalam, Odia, Tamil and Telugu in Regular and Bold. Names, styles, lengths and SHA-256 are in the catalog. |
| Size on disk | 4,083,976 bytes of fonts; the DLL is about 4.1 MB. |
| Size in nupkg | 1,908,123 B (1.0.0, released); about 1.91 MB for 1.1.0 (local pack 1,910,509 B). |
| Loading | On demand, confirmed. Embedded resources; loading the assembly reads nothing; the static init builds only the 22-entry catalog (metadata). Bytes are read on Open or ReadAllBytes. |
| Not checked | Whether Chuvadi.Layout parses all faces at startup — for the Layout chat to confirm. |

Compatibility matrix — tags in the repo (GitHub releases/assets not verifiable from the Zip session; "verified" rows come from release records or Arun's pasted output):

| Package | Version | Tag | Asset | Status |
|---|---|---|---|---|
| Sheets | 2.0.1 | sheets-v2.0.1 | Chuvadi.Sheets.2.0.1.nupkg (344.25 KiB, 417F537F…C253) | verified |
| Sheets | 2.0.0 | sheets-v2.0.0 | Chuvadi.Sheets.2.0.0.nupkg (346,714 B, 17d0d0be…137a) | verified |
| Sheets | 1.8.0 | sheets-v1.8.0 | Chuvadi.Sheets.1.8.0.nupkg | release record exists; hash in claude/sheets-1.8.0-release-record.md |
| Sheets | 1.7.0, 1.2.0, 1.1.2, 1.1.1 | sheets-v1.7.0, -v1.2.0, -v1.1.2, -v1.1.1 | name by the pattern | tag only, unverified |
| Zip | 1.0.0 | zip-v1.0.0 | as above | verified |
| Fonts | 1.0.0 | fonts-v1.0.0 | as above | verified |
| Markup | 1.0.0 | markup-v1.0.0 | Chuvadi.Markup.1.0.0.nupkg (193.02 KiB, 32574780…4192) | verified |
| Print | 1.0.0-rc.2 | print-v1.0.0-rc.2 | Chuvadi.Print, .Ipp, .Remote and .Windows .1.0.0-rc.2.nupkg (hashes in the release record) | verified, pre-release |
| Print | 1.0.0-rc.1 | print-v1.0.0-rc.1 | the same four, .1.0.0-rc.1.nupkg | verified, pre-release |
| Docs | 1.5.1, 1.4.0, 1.3.0, 1.2.0, 1.0.0 | docs-v1.5.1, -v1.4.0, -v1.3.0, -v1.2.0, -v1.0.0 | name by the pattern | tag only, unverified |
| Docs | 1.1.0 | docs-v1.1.0 | n/a | a lightweight tag on a commit, not a signed tag; Zip would not pin to it |

Not released: Docs 1.6.0 (skipped), Docs.Conversion, OpenType, Text.Shaping, and all six Layout packages.

**Pinnable set today:** Sheets 2.0.1, Zip 1.0.0, Fonts 1.0.0, Markup 1.0.0, Print rc.2 with its three adapters, and Docs 1.5.1. None of the verified packages depends on another, so there is no version conflict among them. The real constraints start with Layout and Docs.Conversion.

Gaps and next steps (proposals; nothing changed):

- Verify the unverified rows: Arun runs `gh release list --limit 50`, then `gh release view <tag> --json assets` for each unverified tag, and pastes the output; Zip fills sizes and hashes.
- Release fonts-v1.1.0 first: unblocks the Layout group and gives the Reader one Fonts version to pin.
- Matrix file: a docs/COMPATIBILITY.md in the repo, updated at every release, so the Reader reads one place. Shared-file change; Arun sequences it.
- Release links: once verified, add links to the pinned set in that file.

---

## 5. Pdf (chuvadi-pdf, 34 packages, plus Chuvadi.Fonts as used by Pdf)

### 5A. Platform readiness (clean checkout of tag v3.31.1, 38c82c2)

The libraries are ready for all five targets as far as the code itself goes. Two server problems need fixing before the Reader runs as a web server (A and B below).

Baseline for every package unless its row says otherwise:

1. **Managed:** 100% managed C#. No DllImport, LibraryImport, extern or Marshal anywhere, no native files, no real unsafe code. Four projects allow unsafe code but never use it.
2. **Windows-only APIs:** none. The "Registry" matches are the PDF term /Registry (Adobe) and FilterRegistry.
3. **Target:** plain net10.0, no runtime identifiers.
4. **Trimming and AOT:** all 34 packages built with the trim, AOT and single-file analyzers on: 0 warnings each (a canary project confirmed the analyzers fire). Real NativeAOT build of a smoke program (Authoring with shaped Tamil, raster, SVG, text, PDF/A, shaping from Chuvadi.Fonts, a scripted XFA form): 0 warnings, byte-identical output to the JIT run. The 19 MB binary finished in 124 ms with a 66 MB working set; the JIT run took 729 ms and 108 MB. Only reflection use is GetManifestResourceStream (safe). Not declared: no package sets IsTrimmable or IsAotCompatible (C).
5. **Files:** works fully from streams and byte arrays. No temp folders, fixed locations, AppContext.BaseDirectory or environment variables.
6. **Startup:** nothing runs when an assembly loads; everything is lazy on first use.
7. **Threads:** all shared Default option objects are init-only, so immutable. Static lookup tables are built once and only read.
8. **Fonts:** none unless the row says so.

("base" = the baseline above)

| Package | (5) Files | (6) First-use cost | (7) Thread safety | (8) Fonts |
|---|---|---|---|---|
| Cryptography | base | base | base | — |
| Pdf.Primitives | base | base | ⚠ process-wide PDF name table that never shrinks (A) | — |
| Pdf.Objects | base | base | One document's object store is not thread-safe (PdfObjectStore.cs line 29) | — |
| Pdf.IO | base | base | Per document; its log is locked | — |
| Pdf.Documents | Open(path) and Save(path) are conveniences; stream overloads exist | base | One PdfDocument per thread (D) | — |
| Pdf.Filters | base | CCITT code tables built on first use | base | — |
| Pdf.Fonts | base | Adobe Glyph List table (~4,300 entries) built on first use, a few ms | base | — |
| Pdf.Fonts.Rendering | base | Embedded standard-14 outline data (362 KB), loaded once on first use of a non-embedded font. Thread-safe. | One FontRenderer must not be shared without care: its glyph caches are unlocked (B) | Standard-14 outlines, embedded |
| Pdf.Fonts.Bundled (deprecated) | base | Each WOFF2 face decoded on first use, then cached | Locked | 10 LiPi WOFF2 faces, embedded (2.4 MB DLL) |
| Pdf.Fonts.Woff2 (deprecated) | base | base | base | — |
| Pdf.Graphics, Color, Content, Images, Encryption | base | base | base | — |
| Pdf.Text | base | base | Tagged-order cache: weak table under a lock | — |
| Pdf.Text.Shaping | base | First call per face and script builds the shaping plan: ~76 ms under JIT (mostly JIT warm-up), then ~0.2 ms | Safe to share: 120,000 concurrent calls on 8 threads, 0 wrong results | Uses fonts the caller passes in |
| Pdf.Rendering.Walking, DisplayList | base | base | Display-list fonts are locked | — |
| Pdf.Rendering.Raster | base | First raster ~68 ms (includes the standard-14 load) | ⚠ shared LiPi FontRenderer race (B) | LiPi from Chuvadi.Fonts, loaded on first use per script and weight, kept for the process |
| Pdf.Rendering | base | base | base | — |
| Pdf.Rendering.Wpf | base | base | WPF's own rules | — |
| Pdf.Svg | base | base | base | Embeds the PDF's own fonts into the SVG |
| Pdf.Authoring | ReportBuilder.Save(path) and ImagePdfConverter path overloads are conveniences; byte and stream overloads exist | ~25 ms first document under JIT | LiPi program cache bounded by script | LiPi from Chuvadi.Fonts, on first use |
| Pdf.Forms | base | base | Face cache bounded (fixed LiPi file names) | LiPi fallback from Chuvadi.Fonts |
| Pdf.Annotations, Operations, Redaction, Watermark, Reader, Xfa | base | base | base | — |
| Pdf.PdfA | base | ICC profile and Liberation fonts read on use, ~28 ms first write | base | 12 Liberation TTFs and an sRGB profile, embedded (4.4 MB DLL) |
| Pdf.Signatures | base | base | The HttpClient is the caller's own; no network unless the caller asks for long-term validation data | — |
| Pdf (umbrella) | — | — | — | Leaves out the WPF package on purpose |
| Chuvadi.Fonts 1.0.0 | Embedded only | Nothing on load. ReadAllBytes copies one face per call (~0.2 ms for an 80 KB face) and returns a new array every time (E) | Read-only | 22 static TTFs plus the licence, uncompressed embedded resources (4.1 MB DLL) |

Row exceptions:

- Pdf.Rendering.Wpf is the only platform-specific package: net10.0-windows with UseWPF, so Windows-only by design.
- Chuvadi.Fonts was checked as the shipped DLL (separate package): managed, passed the NativeAOT smoke test; analyzers not run on its source by Pdf (Zip ran them: 0 warnings).
- Platform crypto: Cryptography, Signatures and Encryption use .NET's built-in RSA, ECDsa, AES and MD5. Works on Windows, Mac, Linux, Android and any server. In a browser (Blazor WebAssembly) they throw PlatformNotSupportedException (F) — not relevant now that Web is server-side only.

Items that need a change, as proposals for Arun:

- **A. The PDF name table never shrinks (server, high).** Every name read from any file is interned for the life of the process (PdfName.cs line 73); name equality is by reference. Measured: each 2.8 MB PDF with 200,000 unique names keeps ~25 MB after disposal; five such files kept 141 MB. Real files add up too (font subset names like /ABCDEF+Calibri carry a random prefix in every document). A long-running server grows without limit, and a crafted file can pin memory at will. Options: (a) compare names by value, intern only the well-known names — fixes it, slightly slower comparison, changes name equality internally (Rule 5); (b) a weak intern table — keeps reference equality, more complex; (c) a size cap — simple, but past the cap equality still needs (a). Recommendation: (a), proven on the 417-PDF corpus. About 1 session.
- **B. The shared LiPi FontRenderer races (server, high).** LipiFace keeps one renderer per script and weight for the process (LipiFace.cs line 22); its glyph caches are written without a lock (FontRenderer.cs lines 50 and 202). Measured: same lookups on one renderer from 8 threads — 5 of 6 runs threw (IndexOutOfRange, NullReference, .NET's "concurrent update … corrupted its state"); twice the cache stayed broken. Effect: the raster builder treats the throw as "glyph damaged" and draws nothing, so Indic text in non-embedded fonts can silently vanish, possibly for every user until a restart. Options: (a) make FontRenderer's caches concurrent — small, fixes every shared use; (b) per-document renderer — more memory and time; (c) a lock inside LipiFace — narrow, some contention. Recommendation: (a). Output unchanged; bug fix. About ¼ session.
- **C. Declare trim and AOT safety (all packages except WPF, medium).** Set IsAotCompatible=true in Directory.Build.props so analyzers run in every build; optionally a CI NativeAOT job running the smoke program. For: locks in today's 0-warning state. Against: package metadata (Rule 5), no output change. Recommendation: yes. About ¼ session.
- **D. State the thread-safety contract in the docs (medium, docs only).** One PdfDocument per thread, or lock it yourself; FontFace and TextShaper are safe to share. The Reader can't render pages of one document in parallel today (e.g. thumbnails). A thread-safe read mode would be a later feature.
- **E. FontPack.ReadAllBytes returns a new array every time (low).** TextShaper.Shape(byte[], …) caches by array identity, so fetching bytes on every call rebuilds face and plan each time. Options: (a) document it — keep the bytes or the FontFace; (b) change Chuvadi.Fonts to return a cached array (separate package; callers could modify a shared array). Recommendation: (a).
- **F. Browser-side WebAssembly** (Signatures and Encryption won't work; CI's WASM Smoke job only builds 4 packages). Closed: Web is server-side only.
- **G. Android has no CI coverage (low).** Nothing Android-specific in the code, but nothing tests it. Option: a net10.0-android build check.
- **H. Unused AllowUnsafeBlocks (low).** Remove from Filters, Fonts, IO and Primitives. No output change.

Note: the sandbox's older NativeAOT compiler (10.0.7) trips NuGet's vulnerability audit; Arun is on .NET 10.0.14, so not affected.

Pdf recommends A and B together in one release (3.31.2 or the next feature release, Arun's call), with C, D and H alongside.

### 5B. Package list (checked against tags v3.31.1 and v3.17.1; API comparison of all 519 old and 587 new public types; changelog for every release 3.18.0 to 3.31.1)

The Reader can move from 3.17.1 to 3.31.1 with no compile errors: no public API was removed or changed in signature. It does need Chuvadi.Fonts in its feed, and a list of behaviour changes to check. Pdf can't see the Reader's code, so for each change it says what to look for.

**1. Packages the Reader needs.** All versions must be the same: 3.31.1 for every Pdf package, plus Chuvadi.Fonts 1.0.0.

| Reader feature | Reference directly | Main types |
|---|---|---|
| Open, encrypted files, passwords | Chuvadi.Pdf.Documents | PdfDocument.Open(stream[, password]), RequiresPassword, PdfPasswordRequiredException |
| View as SVG (web view, cross-platform) | Chuvadi.Pdf.Svg | SvgRenderer |
| View as pixels (PNG, any UI) | Chuvadi.Pdf.Rendering | PageRasterizer, RenderRegion |
| View in WPF (Windows only, optional) | Chuvadi.Pdf.Rendering.Wpf | WpfRenderer |
| Facade (async open, SVG, thumbnails, outline, search, text runs) | Chuvadi.Pdf.Reader (optional) | ChuvadiPdfReader, PdfRenderExtensions |
| Text extraction | Chuvadi.Pdf.Text | TextExtractor |
| Search and text runs | Comes with Svg (in Rendering.DisplayList) | DocumentSearch |
| Edit pages: merge, split, reorder, crop, stamps, header and footer, outline writing, sanitise | Chuvadi.Pdf.Operations | PageOperations, PageCropper, OutlineWriter, PdfSanitizer |
| Compress or optimise | Chuvadi.Pdf.Operations | PdfCompressor |
| Encrypt on save | Operations or Authoring (EncryptionOptions lives in IO) | PageComposer.Write(stream, EncryptionOptions), PdfDocumentBuilder.Save(stream, EncryptionOptions) |
| New content | Chuvadi.Pdf.Authoring | PdfDocumentBuilder, PageBuilder |
| Comments | Chuvadi.Pdf.Annotations | AnnotationWriter |
| Forms (AcroForm) | Chuvadi.Pdf.Forms | FormFiller, OutlineReader |
| Forms (XFA) | Chuvadi.Pdf.Xfa | XfaRenderer.OpenComposed |
| Redaction | Chuvadi.Pdf.Redaction | Redactor, RedactionVerifier |
| Signatures | Chuvadi.Pdf.Signatures (brings Chuvadi.Cryptography) | PdfSigner, PdfSignatureVerifier |
| Watermarks (if used) | Chuvadi.Pdf.Watermark | WatermarkStamper |

What the Reader can leave out: Chuvadi.Pdf.PdfA (4.3 MB) unless it saves PDF/A; Chuvadi.Pdf.Fonts.Bundled (2.3 MB, deprecated; only the umbrella references it); Chuvadi.Pdf.Fonts.Woff2 (deprecated) and Chuvadi.Pdf.Color (only PdfA and the umbrella need them); Chuvadi.Pdf.Rendering.Wpf except in a Windows WPF build.

Umbrella or individual packages:

| Option | For | Against |
|---|---|---|
| Umbrella (Chuvadi.Pdf) | One reference, so versions can't drift. | Pulls everything except WPF: PdfA plus the deprecated Fonts.Bundled and Woff2, ~6.7 MB extra. Its dependency list is still the older set (DISTRIBUTION.md item 6). |
| Individual (rows above) | ~6.7 MB smaller, which matters on Android. Deprecated packages stay out. | ~14 references to keep at one version; a single version property in the csproj handles that. |

Pdf recommends individual references. **Decision for Arun.**

**2. Where each package comes from**

| Package | Where | File | Format |
|---|---|---|---|
| All 34 Pdf packages | Arun's local feed C:\Users\aruns\Documents\local-nuget, packed from the v3.31.1 tag (done in the 3.31.1 release) | Chuvadi.Pdf.&lt;Name&gt;.3.31.1.nupkg (e.g. Chuvadi.Pdf.Svg.3.31.1.nupkg); also Chuvadi.Cryptography.3.31.1.nupkg and Chuvadi.Pdf.3.31.1.nupkg | .nupkg (DLL, XML docs, embedded symbols) |
| Chuvadi.Fonts 1.0.0 | GitHub release asset https://github.com/arunshivab/chuvadi/releases/download/fonts-v1.0.0/Chuvadi.Fonts.1.0.0.nupkg (also already in local-nuget) | Chuvadi.Fonts.1.0.0.nupkg, SHA-256 C15A82D1CAA3D70F3E2ABE16DD94201EA1D3DAE91764735A19FFA7398C37F5FE | .nupkg |

**No GitHub release assets exist for chuvadi-pdf itself.** Its workflows never create a release; the documented flow is pack, copy to the local feed, then tag. (Pdf couldn't open the releases page to rule out a manual release.) If the Reader should download from GitHub, someone must first attach the 34 .nupkg to a v3.31.1 release.

Feed rule: the Reader's feed needs all 34 packages and Chuvadi.Fonts side by side. Chuvadi sessions don't touch the Reader's folders, so the Reader fetches from local-nuget itself.

**3. Dependency graph (3.31.1).** Leaves with no Chuvadi dependency: Primitives, Graphics, Color, Cryptography, Fonts.Woff2.

| Layer | Package: direct dependencies |
|---|---|
| Core | Filters: Primitives. Encryption: Primitives. Objects: Primitives, Filters. IO: Primitives, Filters, Encryption, Objects. Documents: Primitives, Objects, Encryption, IO. Images: Graphics, Filters. |
| Fonts | Fonts: Primitives, Objects, Filters. Fonts.Rendering: Fonts, Graphics, Objects, Primitives. Text.Shaping: Fonts.Rendering. |
| Content | Content: core, Fonts. Rendering.Walking: Primitives, Objects, Filters. |
| Font pack users | Authoring: core, Images, Fonts.Rendering, Text.Shaping, Chuvadi.Fonts. Forms: core, Fonts, Fonts.Rendering, Text.Shaping, Chuvadi.Fonts. Annotations: core, Forms, Fonts.Rendering. |
| Display lists | Rendering.DisplayList: core, Content, Fonts, Images, Fonts.Rendering, Walking, Annotations. Rendering.Raster: core, Content, Images, Fonts.Rendering, Text.Shaping, Walking, Annotations, Chuvadi.Fonts. |
| Output | Rendering: DisplayList, Raster, Images, Fonts.Rendering, Content, core. Svg: DisplayList, Rendering, Fonts, Fonts.Rendering, core. Text: core, Content, Fonts, Annotations. Rendering.Wpf: Documents, DisplayList. |
| Features | Operations: Authoring, Rendering, Content, Fonts, Forms, Text, Annotations, Images, core. Redaction: Operations, DisplayList, Text, Content, Fonts.Rendering, core. Xfa: Documents, Authoring, Text.Shaping. Watermark: Authoring, Images, Fonts.Rendering, core. Signatures: Cryptography, core. PdfA: Authoring, Color, Fonts.Rendering, Fonts.Woff2, core. Reader: Documents, Forms, DisplayList, Rendering, Images, Svg. |

Versions that work together: all Pdf packages are mono-versioned (each depends on siblings at exactly the same version) — use 3.31.1 everywhere, never mix. Chuvadi.Fonts 1.0.0 is the only version; 3.31.0 or later needs it. Text.Shaping (Pdf's, Chuvadi.Pdf.Text.Shaping) is part of the same version set. Anything that renders, does forms or authors pulls in both Chuvadi.Fonts and Text.Shaping.

**4. Platform support**

| Platform | Works | Does not work, or differs |
|---|---|---|
| Windows | Everything, including Rendering.Wpf for a WPF host. | — |
| macOS, Linux | Everything except WPF. View with Chuvadi.Pdf.Rendering (managed rasterizer to pixels or PNG, any UI toolkit) or Chuvadi.Pdf.Svg (SVG for a web view). | No WPF. NativeAOT checked on linux-x64 with identical output. macOS never run in CI beyond the build. |
| Android | All managed, no platform APIs. Use Rendering (bitmap) or Svg (WebView). Built-in crypto (RSA, ECDsa, AES, MD5) supported. | No WPF. Never built or run for Android (G). Individual packages save ~6.7 MB. |
| Server, many users | Fully managed, stream-only, no files or temp folders, NativeAOT-ready. | Before heavy use: fix A (name table) and B (LiPi renderer race, can drop Indic text). One PdfDocument per request or thread (D). |

**5. The font pack**

| Question | Answer |
|---|---|
| Which package | Chuvadi.Fonts 1.0.0 (FontPack). Comes through Authoring, Forms and Rendering.Raster, and so through Svg, Rendering, Operations, Redaction, Xfa and Reader. |
| Contents and size | 22 LiPi Sans static TTFs (Latin and 9 Indic scripts, Regular and Bold, plus Latin italics) and the OFL licence. DLL 4.1 MB, uncompressed embedded resources. |
| When it loads | On demand only. Nothing on assembly load. A face is read when first needed: ~2 ms for the first file, 0.2 ms after. The raster renderer loads each script's face once and keeps it. |
| Other fonts | Standard-14 outlines (362 KB, inside Fonts.Rendering) load once, the first time a non-embedded font is drawn. PdfA carries 12 Liberation TTFs, read only when writing PDF/A. |
| Trap | FontPack.ReadAllBytes returns a new array every call. Keep the bytes or the FontFace; don't fetch per shaping call (E). |

**6. Breaking changes, 3.17.1 to 3.31.1**

Compile level:

- Nothing removed or changed in signature. 68 types added; every 3.17.1 member is still there.
- Newly [Obsolete] (3.31.0, warning CS0618 — an error if the Reader builds with warnings as errors): Woff2Unpacker, Woff2Packer, BrotliEncoder, BrotliStoredEncoder (all in Fonts.Woff2) and BundledFonts (added in 3.30, deprecated in 3.31). If the Reader decodes LiPi WOFF2 itself: switch to FontPack.ReadAllBytes("LiPi-Sans-&lt;Script&gt;-Regular.ttf").
- PdfParseException is no longer sealed (3.24.0). Nothing to change.

Build and restore:

- The Reader's feed needs Chuvadi.Fonts.1.0.0.nupkg (3.31.0), or restore fails.
- Move every Chuvadi reference to 3.31.1 at once. There are now 34 packages; Fonts.Bundled was added in 3.30.
- DisplayList now pulls Annotations, Forms, Text.Shaping and Chuvadi.Fonts (~4.6 MB more, 3.31.0). Raster also pulls Chuvadi.Fonts and Text.Shaping (3.30.0).

Behaviour the Reader will see:

| Version | Change | What the Reader should check or do |
|---|---|---|
| 3.18.0 | Redaction default VectorRedactionMode.SubtractPrecise: paths are cut at the box instead of dropped whole. | DropIntersecting gives the old behaviour. Redaction previews will differ. |
| 3.18.1 | A Flate stream with a bad checksum now opens instead of throwing. | More files open; nothing to do. |
| 3.19.0, 3.20.0 | Security: Scrub crop and redaction now remove content they used to leave in the file. | Files cropped with Scrub or redacted by earlier versions should be redone. The Reader may want to tell users. |
| 3.19.0 | Imposition rejects invalid geometry with ArgumentException. | Catch it if the Reader imposes pages. |
| 3.21.0 | Layers hidden by default are no longer drawn, extracted or searched. | Set IgnoreOptionalContent or OptionalContentVisibility.AllVisible for the old view, or add a layers panel. |
| 3.21.0 | Warnings can appear after open (objects load and repair lazily). A damaged reference now gives "missing" instead of the wrong object. | Read PdfDocument.Warnings and IsRecovered after rendering, not only after opening. |
| 3.21.0 | Large tiling patterns are painted; new raster op TilingFillOp. | If the Reader walks the op stream itself, ignore unknown op types. |
| 3.22.0 | Redacted pages drop /Thumb and /PieceInfo. | Nothing to do. |
| 3.24.0 | Password-protected files throw PdfPasswordRequiredException (subclass of PdfParseException). New cancellation overloads and PdfSanitizer. | Catch the new exception before PdfParseException to prompt for a password, or call RequiresPassword first. |
| 3.26.0 | Shaper is now the HarfBuzz port. ShapedGlyph.Cluster is a UTF-16 index for every script (Indic runs gave a code point before). Advances exact, not rounded. | Only matters if the Reader shapes text itself or uses Cluster. |
| 3.27.0 | ShapingFeatures.Cpsp on by default, so LiPi Latin capitals are slightly wider. Dot leaders are spaced in extracted text. | Cpsp = false gives the old output. |
| 3.28.0 | TextFragment X, Y, Width and FontSize are in user space (before: text space, without CTM or form matrices). Rotated text is read as its own lines. | Check code that places highlights or selection from fragments. Remove any CTM correction the Reader added. |
| 3.29.0 | Superscripts and subscripts use Unicode forms ("H₂O"). Layout mode follows the structure tree and reads columns. Search matches compatibility forms ("H2O" finds "H₂O"). | Opt out with SuperscriptMode.Separate (3.28 output) or Join, UseTaggedOrder = false, SearchOptions.MatchCompatibilityForms = false. Match offsets stay in page text. |
| 3.30.0 | PageBuilder.DrawText throws ArgumentException for an unknown font name (before: blank text). | Use the standard 14, a font added with AddTrueTypeFont, or "Lipi" after UseLipiFonts. |
| 3.30.0 | Non-embedded fonts drawn with a standard-14 substitute (Indic through LiPi), with a FontSubstituted warning (before: nothing drawn). | More text appears, and more warnings; show them as information. |
| 3.30.0, 3.30.2 | SVG: embedded fonts load in browsers, and text sits at the PDF's positions. | SVG output differs; nothing to do. |
| 3.31.0 | Default View mode: form values show when /NeedAppearances is set, widgets and comments without appearances are drawn, text extraction returns those values. New AnnotationMode (View is default and matches 3.30). | Pages with forms or comments look fuller. Pass AnnotationMode.Print when printing. |
| 3.31.0 | Bold Indic text in non-embedded fonts uses LiPi Bold. | Nothing to do. |
| 3.31.0 | ShadingOp appears in the op stream with IsExpressible = false. | Ignore unknown ops (SVG and WPF already do). |
| 3.31.0 | Encoding and character-map fixes. | Text and raster change on some TeX PDFs (closer to MuPDF); characters above U+FFFF now draw. |
| 3.31.1 | Speed only. | — |

Details for every row are in the CHANGELOG [3.18.0] to [3.31.1].

What the Reader chat should search its own code for: `Woff2Unpacker`, `BundledFonts`; `TextFragment`, `ExtractFragments`, `.X`, `.Y`; `ShapedGlyph`, `Cluster`; `DrawText(` with a font name; `PdfParseException`; `OptionalContent`; any switch over RenderOp types.

---

## 6. Shaper (Chuvadi.OpenType, Chuvadi.Text.Shaping — clean-room, in development, not released)

### 6A. Platform readiness

Both libraries are pure managed C# on plain net10.0. Both build with 0 warnings with the trimming and AOT checks on, and a NativeAOT test app published and shaped text correctly on Linux.

| # | Question | Answer |
|---|---|---|
| 1 | 100% managed C#, no native code? | Yes, all C#, no DllImport or interop. Caveat: WOFF2 uses .NET's own BrotliDecoder and WOFF 1.0 uses ZLibStream. Both are part of .NET, but the runtime implements them with its own bundled native compression library. That works wherever .NET runs, including Android. |
| 2 | Windows-only APIs? | None. No file system, Environment or OS-specific calls. |
| 3 | Plain net10.0? | Yes, no platform suffix. |
| 4 | Trimming-safe and NativeAOT-compatible? | Yes: no reflection, no dynamic code, no emitted code; the Unicode tables are compiled into the DLL as constant data. Both build with IsTrimmable and IsAotCompatible on: 0 warnings; a NativeAOT app (linux-x64, 1.9 MB) loads a font and shapes text correctly. The two properties aren't switched on in the csproj files yet (design point 1). |
| 5 | Streams and bytes, no paths? | Yes, everything loads from byte[] or ReadOnlyMemory&lt;byte&gt;; no API takes a path. No Stream overload: a font needs random access, so the caller reads the stream into bytes first. |
| 6 | Startup cost of the ~100 KB tables | Essentially none. Constant data inside the DLL, read in place, not copied or built at start-up. Only a small array of script codes (a few KB) is created at first use. |
| 7 | Thread safety | Safe for concurrent use. OpenTypeFont is immutable; tables read on first use are published once, safely, and can be shared across threads. ShapingFont.Get keeps one shaping font per font in a thread-safe cache that holds no strong references, so it never keeps a font in memory. No other static state changes at run time. A GlyphBuffer belongs to one caller at a time (the reusable output buffer, documented as such). |

Design points to fix now:

1. Switch on IsTrimmable and IsAotCompatible in both library csproj files (shaper recommends). Repo warnings are errors, so any later reflection or dynamic code fails the build straight away. Build setting only; no behaviour or API change. The shaper will add it in the next phase-1 commit unless Arun objects.
2. WOFF2 in a browser (Blazor WebAssembly): .NET's Brotli decoder likely isn't available in the browser runtime. **Closed: Arun decided Web is always server-side only.**
3. A Stream overload would be a pure addition; not recommended now, since the caller still has to read the whole font.

None of this changes phase 1.

### 6B. Package list

Not asked: OpenType and Text.Shaping are unreleased (tags held until the layout views land, per the tag chain). The Reader uses Pdf's own Chuvadi.Pdf.Text.Shaping 3.31.1 today (see section 5).

---

## 7. Markup (Chuvadi.Markup)

### 7A. Platform readiness (main 1613d51, where Markup differs from 1.0.0 only by PR #51 — MaxOutputChars is now exact; saved as claude/markup-platform-readiness.md)

Chuvadi.Markup 1.0.x is ready for every target: all managed code, no Windows-only APIs, plain net10.0, and it passes the trim and NativeAOT checks with 0 warnings. For 1.1.0, the answers hold for the parts of the library that stay; the author's new parser and renderer haven't reached the Markup chat, so they get checked in the swap PR.

Method: code scan; .NET trim, AOT and single-file checks; a test app built three ways on Linux x64 (JIT, trimmed self-contained, NativeAOT) calling every entry point, including HTML bytes in windows-1252 and shift_jis, with 2,000 mixed calls on 32 threads. Mac and Android not run; CI covers Windows and Ubuntu.

| # | Question | 1.0.x (checked) | 1.1.0 |
|---|---|---|---|
| 1 | 100% managed | Yes. No P/Invoke, extern or unsafe code. | Rest of the library: yes. Author's code: checked in the swap PR. |
| 2 | Windows-only APIs | None. Legacy code pages come from the code-page provider built into .NET; works trimmed and under NativeAOT. | Same; author's code checked. |
| 3 | Plain net10.0 | Yes, net10.0 only. Android app projects can reference it. | Same. |
| 4 | Trim / NativeAOT | No reflection, no Regex at all, no dynamic code. Trim, AOT and single-file checks: 0 warnings. Trimmed and NativeAOT output byte-identical to JIT. The csproj doesn't yet declare IsTrimmable or IsAotCompatible. | Same checks run on the author's code in the swap PR. |
| 5 | Strings and streams only | Yes. No files, paths, temp folders or environment variables. Takes string, TextReader, byte[], spans or Stream; returns a string or writes to a TextWriter. | Same. |
| 6 | Startup cost | No large tables at startup. Built on first use: entity map (0.3 ms NativeAOT, 205 KB kept), entity prefix set on the first & in HTML (1.2 ms, 625 KB kept), case folding on the first link label (0.1 ms, 88 KB kept). First call ~25 ms under JIT (mostly compiling); under 0.1 ms under NativeAOT. NativeAOT starts at 5.6 MB of memory. A 199 KB document converts in ~11 ms. | The parser's own tables are measured in the speed run. |
| 7 | Many users at once | Every public call is static and keeps no state; option and policy presets are new objects each time. Only shared state is the three tables in row 6. Two simultaneous first requests may each build a table, but no reader sees a half-built one. 32 threads: 0 mismatches in 4,000 calls. | Rest of the library: same. Author's code checked for shared state. |
| 8 | Fonts | None. | Same. |

Proposals for Arun:

1. Declare `<IsAotCompatible>true</IsAotCompatible>` in the Markup csproj, in the swap PR. Turns the checks on for good (warnings are errors), marks the package trimmable, and checks the author's code from the first build. No behaviour change, but package metadata, so listed under Rule 5. No downside found; recommended.
2. Use the NativeAOT/trimmed test app in the swap proof (output vs JIT, 32 threads). A CI job could come later with the M-06 CI work (needs clang on Ubuntu, a shared ci.yml change through the integrator, ~1–2 extra minutes per run). Recommend the app now, CI later.
3. Optional: build each of the three tables only once, even under a race. Today's code is already safe; this only avoids building a table twice on a busy server's first requests (~200–600 KB once). No output change. Not needed for 1.1.0.
4. Mac and Android runs: Arun or the Reader chat would need to run the test app on a Mac and on an Android device or emulator. Markup has nothing platform-specific except the code-page encodings, which already passed trimmed and NativeAOT.

### 7B. Package list

- Released: markup-v1.0.0, 03 Nov 2026, https://github.com/arunshivab/chuvadi/releases/tag/markup-v1.0.0
- Asset: Chuvadi.Markup.1.0.0.nupkg (193 KB), https://github.com/arunshivab/chuvadi/releases/download/markup-v1.0.0/Chuvadi.Markup.1.0.0.nupkg. No separate DLL.
- Dependencies: none. Needs .NET 10.
- Used by: Chuvadi.Docs.Conversion and Chuvadi.Layout.Markup.
- 1.0.x to 1.1.0: no API break (public API listing identical). Behaviour changes, all approved, are the swap plan's Rule 5 items. A caller could notice exact MaxOutputChars, the new MaxNodes count, the new work-limit counting, the U+000B/U+000C/U+00A0/U+2028 rules (D-141, D-143, D-157) and link-label matching (D-174). The package no longer contains THIRD-PARTY-NOTICES.txt.

---

## 8. Layout (export, viewing and Save as PDF for Docs and Sheets)

### 8A. Platform readiness (main 22d5a07; saved as claude/layout-platform-readiness.md)

Method: source check; every package built with the trim and AOT analyzers on; every shipped assembly scanned for native imports; three real NativeAOT apps published on linux-x64 and their output compared with the normal (JIT) build. Answers are the same for all seven packages (Layout, Layout.Fonts, Layout.Docs, Layout.Sheets, Layout.Markup, Layout.Documents, staged Layout.Pdf) unless a row says otherwise.

| # | Question | Answer |
|---|---|---|
| 1 | 100% managed? | Yes. No DllImport/LibraryImport, no extern or unsafe code, no native files. All 31 Chuvadi assemblies a Layout app ships (including the 20 Chuvadi.Pdf 3.30.2 ones) contain 0 native imports and are IL-only. |
| 2 | Windows-only APIs? | None. No System.Drawing, GDI, registry or WinRT. The only OS-specific code is the list of system font folders, used only when the app turns on AllowSystemFonts (off by default). |
| 3 | Target | Plain net10.0, no platform-specific targets. |
| 4 | Trim / AOT | Analyzers report 0 trim or AOT warnings. Real NativeAOT apps work, output byte-identical to the normal build: 21.6 MB for docx, 24.2 MB with xlsx and Markdown, 27.0 MB with PDF and PNG. Only issue is in a dependency: Chuvadi.Sheets' 3 reflection warnings in its object-mapping APIs; Layout never calls those, and xlsx still works under AOT. The packages don't yet declare IsTrimmable or IsAotCompatible. ReadyToRun not tested (AOT is stricter, so expected to work). |
| 5 | File system | Everything from streams or byte arrays; fonts from embedded resources. No temp folders or fixed paths. The disk is read only when the app opts in: AllowSystemFonts, or a font folder it names itself. |
| 6 | Startup | Nothing loads up front. Options and font setup ~10 ms (under 1 ms with AOT). First document to SVG 220 ms, mostly .NET warming up; 13 ms with AOT. Later documents 5–7 ms. Working set: 18 MB after the first document, 33–36 MB with 16 at once (AOT). One PDF page 12 ms, one PNG page 177 ms. |
| 7 | Many users in one server process | Safe. 16 concurrent layouts of the same file gave identical output. The shared caches (parsed fonts per pack, glyph outlines per face, licence text) are all locked. Each font is parsed once and kept; at most about 12 MB of font data. Everything else is per document, or read-only lookup tables. |
| 8 | Font loading | The 29 substitute fonts (8.3 MB) are embedded in Layout.Fonts and load lazily: each is parsed the first time a document uses it. The LiPi fonts work the same way and are on by default. System fonts (only with AllowSystemFonts) come from the standard Windows, macOS and Linux font folders. Android has none of its own, so no system font is found there. |

Proposals for Arun (each through Rule 5 before any code):

1. **Share the system font scan across the process.** Today every document opened with AllowSystemFonts re-reads every system font file (23–48 ms here with 304 files; Windows has many more), and keeps its own copy of each font. One shared, rescannable scan fixes both, with no change to output.
2. **Android font folders.** Add /system/fonts and /product/fonts on Android.
3. **Declare IsTrimmable and IsAotCompatible** in Layout's seven project files, so CI catches future trim or AOT problems. No behaviour change.
4. **For the Sheets chat:** annotate the two generic methods behind its 3 reflection warnings, so AOT builds that reference Chuvadi.Sheets as a project stop failing.

For the Reader, no change proposed:

- Tamil and other complex scripts need LayoutOptions.Shaper set to PdfShaper, which lives in the staged Layout.Pdf. Without it, Layout uses unshaped glyphs and reports a warning.
- On Linux, fonts known only to fontconfig (Flatpak, Snap, NixOS) can be added with DirectoryFontSource.

Not tested: Windows, macOS and Android runs (only linux-x64; Windows is covered by Arun's normal test runs), ReadyToRun, and culture-specific number formats with invariant globalization on.

### 8B. Package list — PENDING

Sent to the Layout chat on 6 Nov; its answer will be added in the next revision of this file. What is already known from the other chats:

- **No Layout package is released yet.** All are 0.1.0 on main; the layout-* tags wait for fonts-v1.1.0 (D-197/D-202).
- **Version clash:** the staged Chuvadi.Layout.Pdf pins chuvadi-pdf to exactly [3.30.2]; the Reader uses 3.31.1. NuGet can't resolve both, so Layout must re-pin or loosen the pin before the Reader can use it.
- Dependency chain: Layout → Fonts 1.1.0; Layout.Docs → Docs 2.0; Layout.Sheets → Sheets 2.x; Layout.Markup → Markup (1.1.0 once the swap ships); Layout.Documents → Layout.Docs + Layout.Sheets.
- Entry points (from the Docs and Sheets chats, to be confirmed by Layout): Docs `DocsLayout.Open(document|stream|bytes, null, options, ct)` then `laid.ToPdf(stream, null, ct)` and `laid.GetPage(i).ToPng(dpi)`; Sheets `SheetsLayout.Open(stream|bytes, SheetsImportOptions, LayoutOptions)` then `doc.ToPdf(stream, LayoutPdfOptions)`; fonts via `FontPackSource.For(SubstituteFontPack.Instance)`; shaping via `new PdfShaper()`; `LayoutOptions.Password` for encrypted files.

---

## 9. Coordinator summary

### What the Reader can pin today

| Need | Package(s) and version | Source | Status |
|---|---|---|---|
| PDF view, edit, forms, redaction, compression, text, signatures, encryption | Chuvadi.Pdf.* 3.31.1 (individual packages recommended; all one version) | Arun's local-nuget (no GitHub release assets for chuvadi-pdf) | Ready on desktop and Android; server needs Pdf A and B fixed first |
| PDF font pack | Chuvadi.Fonts 1.0.0 | fonts-v1.0.0 release / local-nuget | Ready (on demand) |
| Excel / sheets | Chuvadi.Sheets 2.0.1 | sheets-v2.0.1 release | Ready; avoid ToXlsx&lt;T&gt;/ReadXlsx&lt;T&gt; in AOT builds until 2.1.0 |
| Zip | Chuvadi.Zip 1.0.0 | zip-v1.0.0 release | Ready |
| Printing | Chuvadi.Print, .Ipp, .Windows (+ .Remote if hub/agent) 1.0.0-rc.2 | print-v1.0.0-rc.2 release | Ready (raster); XPS vector in rc.3; needs a rasteriser (adapter or Print.Pdf.Raster) |
| Word / docs | Chuvadi.Docs 1.5.1 as a stop-gap only | docs-v1.5.1 release | **Wait for docs-v2.0.0** |
| Docs and Sheets view / print / Save as PDF | Layout family 0.1.0 | not released | **Blocked:** fonts-v1.1.0 → layout tags, plus the Layout.Pdf [3.30.2] pin clash with 3.31.1 |

All Chuvadi packages are .nupkg (lib/net10.0), GitHub releases only, never nuget.org (D-46): the Reader needs a local feed. Save as PDF of an existing PDF is the Chuvadi.Pdf writer, never a Print route (D-48).

### Platform picture

- Every library is 100% managed C# on plain net10.0, with no Windows-only APIs, except by design: Print.Windows (26 DllImport calls, guarded, loads everywhere) and Pdf.Rendering.Wpf (net10.0-windows).
- Analyzers: 0 trim/AOT warnings everywhere except Sheets (3 IL2090, typed import/export) and Print (JSON reflection in PrinterRegistry and Remote). Real NativeAOT runs succeeded for Pdf, Docs, Sheets, Markup, Layout and the shaper with output identical to JIT.
- Fonts everywhere load on demand; nothing eager at startup.
- macOS and Android have not been run by any chat; Windows and Linux are covered.
- Web is server-side only (Arun's decision, 6 Nov), so all browser-WebAssembly items (Pdf F, Zip 5, shaper WOFF2) are closed.

### Blocking issues for the Reader

1. **Server memory leak in Pdf** (Pdf A): the PDF name table never shrinks.
2. **Server race in Pdf** (Pdf B): shared LiPi FontRenderer can drop Indic text for every user.
3. **Sheets AOT data loss** (Sheets PR-1): typed import/export empty under NativeAOT.
4. **Layout.Pdf pin clash**: [3.30.2] vs the Reader's 3.31.1.
5. **Release chain** for Docs/Sheets viewing: fonts-v1.1.0 → markup-v1.1.0 → docs-v2.0.0 → layout-* tags → Layout.Pdf out of staging.
6. **No-disk saving** (Sheets PR-2, Docs P1, Print PWG spool): saves need a writable temp folder today.

### Decisions needed from Arun (proposed as D-207 onwards)

| # | Item | Coordinator lean |
|---|---|---|
| 1 | Pdf A: compare names by value, intern only well-known names (~1 session, Rule 5) | Yes |
| 2 | Pdf B: concurrent FontRenderer caches (~¼ session) | Yes — ship A and B together as 3.31.2 |
| 3 | Sheets PR-1 (a): annotate generic types, trim/AOT checks on, in 2.1.0 | Yes (a) |
| 4 | IsTrimmable/IsAotCompatible in every library (Pdf C, Docs P2, Zip 1, Markup 1 in the swap PR, Layout 3, shaper 1, Print after its JSON move) | Yes, everywhere |
| 5 | CI: trimmed + NativeAOT smoke publish on Ubuntu, macos-latest in the matrix, net10.0-android build check (Zip 2/4, Docs P3, Pdf G) | Yes (Zip owns, shared change) |
| 6 | No-disk saving: Docs temp-folder option in 2.0.0; in-memory spool for Docs and Sheets in 2.1.0 (after the D-206 shared move); Sheets stream readers (PR-3); Print in-memory PWG spool (optional) | Yes |
| 7 | Print: JSON to System.Text.Json source generation; DllImport → LibraryImport before Phase 4 part 3 | Yes to both |
| 8 | Docs-only items: thread-safety and platform sections (Pdf D, Print, Sheets PR-5, Zip/Fonts, Android multicast note); FontPack.ReadAllBytes note (Pdf E (a)); Sheets encrypted-read memory note (PR-4) | Yes |
| 9 | Small: remove unused AllowUnsafeBlocks (Pdf H); Docs re-check after markup-v1.1.0 (P4); Markup NativeAOT test app in swap proof | Yes |
| 10 | Layout: shared system font scan; Android font folders | Yes |
| 11 | Pdf: umbrella vs individual package references for the Reader | Individual |
| 12 | Print rasteriser: Reader adapter now vs wait for Print.Pdf.Raster | Adapter now, switch later (Reader shouldn't wait on the staging move) |
| 13 | Sheets SH-9: Excel-matching date separator and "########" display fixes in 2.1.0 (Rule 5 list first) | Yes |
| 14 | Compatibility matrix: docs/COMPATIBILITY.md updated at every release (shared change); Arun runs `gh release list` to verify unverified tags | Yes |
| 15 | Attach chuvadi-pdf 3.31.1 nupkgs to a GitHub release, or keep local-nuget only | Keep local-nuget for now |
| 16 | Release fonts-v1.1.0 next (already approved under D-197) | Do it next |

Still to test on real devices: macOS and Android runs (requested by Sheets PR-6, Markup 4, Docs P3).

Still pending: Layout's package-list answer (section 8B).
