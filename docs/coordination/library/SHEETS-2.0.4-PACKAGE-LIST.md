Chuvadi.Sheets for the Chuvadi Reader: package list (updated 2026-11-10 for 2.0.4, main 9b8110b)

Rows 1, 2 and items 12 and 13 were updated for 2.0.2 to 2.0.4. Row 5 (Layout) is the Layout chat's status as of 2026-11-06; confirm it with that chat.

#	Question	Answer
1	Package and version	Chuvadi.Sheets 2.0.4 now (bug fixes on 2.0.1, same API). Neither 2.1.0 gap blocks viewing and light editing. The AOT gap is only in ToXlsx<T>/ReadXlsx<T> (object mapping), which a viewer does not need; avoid them in an AOT build. Saving to a stream works since 2.0.1 (left open, any stream), but it uses the temp folder. 2.1.0 is additive (D3, the header check, the AOT fix and an in-memory spool if approved), so moving to it later is a recompile.
2	Release and asset	https://github.com/arunshivab/chuvadi/releases/tag/sheets-v2.0.4. Asset Chuvadi.Sheets.2.0.4.nupkg, a .nupkg holding lib/net10.0/Chuvadi.Sheets.dll and its XML docs. SHA-256 9B777E9518494A0531E25742C1F3FB7F8633DD9DABF44FA083CC44D0DD345D90. Not on nuget.org (D-46); use it from a local feed. The tag is signed; the package is not.
3	Dependencies	None. Pure BCL, net10.0, no package dependencies, and independent of the Reader's chuvadi-pdf 3.31.1. Viewing or printing through Layout adds packages (row 5).
4	Platforms	Beyond sheets-platform-readiness.md:
• Windows, Linux: CI, Arun's gates and the measurements.
• macOS: nothing OS-specific (the Unix paths as on Linux); not run.
• Android: reading is fully in memory from a stream, so it suits content URIs. Saving needs a writable temp folder (Path.GetTempPath() is the app cache) and a writable target folder for path saves; with content URIs, save to a stream. Not run.
• Server, many users: safe concurrently with one Workbook/reader per request (256 parallel runs, identical results). Size memory for the files: an encrypted file is decrypted whole in memory. Use XlsxReaderOptions.ForUntrustedInput() for uploads (size, ratio, entry, row and spin-count limits) and pass a CancellationToken. Saves write temp files to disk.
• All: formatting is invariant unless you pass NumberFormatOptions.Culture (for Indian grouping, en-IN). Invariant-globalization builds work.
5	Viewing, printing, Save as PDF	Chuvadi.Layout.Sheets 0.1.0:
• SheetsLayout.Open(Stream or byte[], SheetsImportOptions?, LayoutOptions?, ct), or SheetsLayout.Open(Workbook, …) for a workbook loaded with IncludeStyledEmptyCells = true;
• it returns a LaidOutDocument (pages, SVG and PNG);
• PDF: doc.ToPdf(stream, LayoutPdfOptions) from Chuvadi.Layout.Pdf;
• fonts: options.FontSources.Add(FontPackSource.For(SubstituteFontPack.Instance)) from Chuvadi.Layout.Fonts;
• LayoutOptions.Password for encrypted files.
The Layout chat owns these, so treat the following as status to confirm with it:
• no Layout package is released yet (D-202: the tags wait for fonts-v1.1.0);
• Layout.Pdf is in staging/ and pins chuvadi-pdf exactly to 3.30.2, which conflicts with the Reader's 3.31.1;
• the chain is Layout.Sheets 0.1.0 → Chuvadi.Sheets 2.x and Chuvadi.Layout 0.1.0 → Chuvadi.Fonts 1.1.0 (only fonts-v1.0.0 is tagged).
6	Breaking changes	Below.
Breaking changes from 1.1.2 to 2.0.4, and what the Reader must change

Source-breaking (the code must change):

Namespace Chuvadi.Sheets.Excel → Chuvadi.Sheets.Model (2.0.0). Change the using lines and fully qualified names, then recompile; 1.x binaries do not bind.
One exception type for malformed files (2.0.0): XlsxFormatException, with the original as InnerException, from every read API.
catch (InvalidDataException) or catch (XmlException) around reads becomes catch (XlsxFormatException).
InvalidDataException remains only for MaxPartBytes, marked Data["Chuvadi.Sheets.ReadLimit"] = true.
A damaged encrypted file with a password given is now XlsxFormatException, not a password error. Show "damaged", not "wrong password".
Missing or wrong password: XlsxPasswordRequiredException, unchanged.
Chuvadi.Sheets.Zip obsolete (CS0618; ZipFormatException since 2.0.1). With warnings as errors the build breaks; move to Chuvadi.Zip or suppress.
ConditionalFormatRule cannot be subclassed outside the library (1.6.0).

Behaviour changes (code compiles; results differ): 5. The library no longer closes the caller's streams. Reads since 1.4.0, saves since 2.0.1. The Reader must dispose its own streams. 6. Encrypted files with a spin count above 500,000 are refused by default (1.7.0, XlsxReaderOptions.MaxSpinCount): XlsxLimitExceededException. Set it to null to lift the cap for trusted files. 7. Corrected values (1.4.0, 1.5.0):

formula cells now return their cached result (they read as null before);
formula cells without a cached value now load;
1904 workbooks' dates are no longer 1,462 days early;
serials 1 to 59 are exact; serial 60 (29-Feb-1900) is returned as a number.
Anything the Reader showed or cached from 1.1.2 for such files changes.
Load → save keeps much more. For light editing this means saved files differ from 1.1.2's, in the right direction:
formulas, defined names, page setup and header/footer (1.4.0, 1.5.0);
row and column settings, panes, visibility (hidden sheets stay hidden), conditional formats and data validation (1.6.0);
rich text, hyperlinks and comments (1.7.0).
Styles:
locale-dependent built-in formats (ids 5–8, 41–44) read as NumberFormat == null with the id kept (1.2.0);
a builder style with .VAlign(x) no longer equals the positional CellStyle (1.4.0);
CellIs conditional styles are written as a dxf (1.6.0).
Streaming writer: SetColumnWidth and FreezeRows/FreezeColumns are allowed after the first row; column spans are written sorted (1.6.0).
Path saves (2.0.1): written to .<name>.<8 hex>.tmp beside the target and replaced on success. The target appears only at Save; a failed save keeps the old file.
Damaged-file errors (2.0.2):
a workbook or sheet part that is missing (and undeclared) is now XlsxFormatException (with FileNotFoundException inside), not a bare FileNotFoundException. A path that does not exist is still FileNotFoundException, so keep "file not found" for that case only;
a text cell whose shared-string index cannot be resolved is now XlsxFormatException; 2.0.1 showed the index ("99") as the cell's text. With SheetReader.Rows it is thrown at that row, after the rows before it;
relationship targets with ./ or ../ segments now open (as in Excel).
DataTable column names (2.0.3, 2.0.4): ReadXlsx (DataSet) and ReadXlsxSheet (DataTable) no longer throw on a header row with a repeated, empty or non-text header, and since 2.0.4 name the columns exactly as Excel names a table's columns:
typed names are kept;
one shared counter numbers repeats (Qty2, Qty3) and empty headers (Column1, Column2, by count, not position);
for example, Qty, Qty, Qty2 gives Qty, Qty3, Qty2. A header-only sheet has its columns. By-name access is unchanged. Use 2.0.4, not 2.0.3: the empty-header names differ.

Still lost on load → save in 2.0.4 (unchanged since 1.1.2, so the Reader should warn before overwriting):

pictures, shapes, charts and chart sheets (read, not written);
header/footer pictures;
macros (load → save writes a macro-free .xlsx);
pivots;
the extended style properties: underline kind, strikethrough, super/subscript, pattern and gradient fills, diagonals, indent, rotation, shrink, reading order, protection, quote prefix;
locale-dependent number formats.

Planned 2.1.0: no breaking change; everything is additive.

D3: Workbook.SaveTo(Stream, EncryptionOptions).
SH-6: a header check.
SH-4: the description and tags drop "zip".
Proposed: PR-1 to PR-3 from the readiness note (the AOT annotations warn only callers that forward an unannotated generic T) and SH-9 (display text).
SH-9 would change displayed text for some date formats, so it gets its own rule 5 entry.

---
Coordinator note (10 Nov 15:24 IST, from Arun): row 5 is stale — Layout 0.1.0 and companions are tagged, but Layout.Pdf has no release and no checksums (see Foundation LAYOUT-RELEASE-CHECK.md). Sheets 2.0.5 is coming with a 1900-dates fix; a refreshed list follows after Sheets 2.0.5 and Layout 0.2.0.
