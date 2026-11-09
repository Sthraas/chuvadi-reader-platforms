# Eleventh combined patch — Word and Excel libraries moved (D-136, 9 Nov)

Arun's decision D-136: the Foundation moves **Chuvadi.Docs 1.1.0 → 2.0.0** and **Chuvadi.Sheets 1.1.2 → 2.0.2** inside PR #11, wires in their protections, and finishes B-08b and Excel cancel.

## 1. Packages
Arun's release assets of `docs-v2.0.0` and `sheets-v2.0.2`, unchanged, SHA-256 recorded (`PACKAGES-DOCS-SHEETS-2.md`). The old 1.1.0 and 1.1.2 files are removed from `ci/packages`. Third-party notices are regenerated.

## 2. Code changes (the package report's breaking-changes lists, `docs/coordination/chuvadi-reader-platform-and-packages.md` §2–3)
| Change | Where |
|---|---|
| Namespaces: `Chuvadi.Docs.Word` → `Chuvadi.Docs.Model`, `Chuvadi.Sheets.Excel` → `Chuvadi.Sheets.Model` | `DocxViewService.cs`, `XlsxViewService.cs`, `AppInfo.cs` (About's version list) |
| Read failures: already `DocxFormatException` / `XlsxFormatException`; limit breaches (`DocxSecurityLimitException`, `XlsxLimitExceededException`) → "too large to open" | the two view services |
| Old zip API (`Chuvadi.Sheets.Zip`): **not used anywhere** in the shared code, so nothing to replace; Docs and Sheets don't reference Chuvadi.Zip | — |
| Word table cells: content is `TableCell.Blocks` (paragraphs and nested tables, in order); nested tables now render | `DocxViewService.MapTable` |
| Docs 2.0 keeps tabs and line breaks inside the text (`\t`, `\n`). Word and Excel keep runs of spaces. The views now show them instead of letting the browser collapse them: Word runs `pre-wrap` with Word's 0.5 in tab stops; Excel cells `pre` (`pre-wrap` when the cell wraps) | `DocRunsView.razor`, `DocxView.razor.css`, `XlsxView.razor(.css)` |
| Streams: Core opens by path only, so there are no streams to close | — |

## 3. Protections (B-08, B-08b) — all through the libraries
| | Word (Docs 2.0.0) | Excel (Sheets 2.0.2) |
|---|---|---|
| Zip-bomb limits | `DocxReaderOptions` (checked against declared and actually inflated sizes): **portal 20 MB per part / 64 MB total; desktop and mobile 100 MB / 400 MB** (D-137) | `XlsxReaderOptions.ForUntrustedInput()`: 256 MB per part, 1 GB total, 500:1, Excel's row maximum (the levels Core's own guard used) |
| Cancel and time-out | a token passed to `Document.Load(path, password, options, token)`, checked on every XML node | `XlsxReaderOptions.CancellationToken`, checked on every row |

- The token comes from the viewer (`ViewerBase.NewLoadToken`). It is cancelled when the tab closes or "Stop opening" is pressed, when another load starts, and after 60 s, when the slow-open note gives up. The viewer then shows "Chuvadi stopped waiting for this file…".
- The viewer also stops waiting at once (`WaitAsync`, as B-24 did for PDFs), even when a read is stuck where no token can reach it.
- **Core's own `OfficePackageGuard` is retired:** the libraries now do this job, including against packages that lie about their sizes, which the guard couldn't catch.
- **Word limits by where the file is opened (D-137, part 2):** desktop and mobile allow **100 MB per part and 400 MB in total**, because a person opens their own files and medical or scanned documents can carry one large picture. The Web portal keeps **20 MB and 64 MB**, because many people share one server. The choice is keyed on `IPlatformInfo.Capabilities.ServerSide`, and both sets are pinned in tests.

## 4. Data comes through as the file holds it
- **Corpus** (`tests/ChuvadiReader.Tests/Fixtures/Office`):
  - Excel: every value kind, both date systems, formula results, errors, styles, frozen panes and a hidden sheet; a 200-row census sheet (1,153 cells); the far-corner cell (B-09).
  - Word: headings, runs with formatting, tabs, line breaks, double spaces, Tamil, lists, a quote, a table, a header and footer, landscape and an image.
- **Truth:** `expected.json`, written by `tools/OfficeCorpus/make.py` from the files' own XML and from openpyxl, never from Chuvadi.
- **Test** `OfficeViewTests` (11 tests, every platform): every value matches. Both zip bombs are refused by the libraries. The Word limits are the agreed ones. A cancelled token stops both libraries.

**Old vs new, on the same files:**
| | Old (Docs 1.1.0, Sheets 1.1.2) | New |
|---|---|---|
| Values not as in the file | **18**: formula cells blank (5); dates shown as serial numbers (7, both date systems); tabs and line breaks dropped (2); header and footer missing (2); landscape not detected; image missing | **0** |
| `realistic.xlsx` (written by openpyxl) | could not open it ("Part '/xl/xl/worksheets/sheet1.xml' not found") | all 1,153 cells as in the file |
| Zip bomb (Linux Test's `bomb.docx`) | refused by Core's guard | refused by the library |

**On screen** (portal preview): Excel shows leading, trailing and double spaces, Tamil, formula results, dates and errors as in the file. Word shows the tab, the line break, double spaces, Tamil, the table, the header and the footer. No page errors.

## Part 2 (D-137, coordinator 05:00)
| Item | Change | Test |
|---|---|---|
| Word limits by device | `DocxViewService(IPlatformInfo)` picks 20 MB / 64 MB on the portal (`ServerSide`) and 100 MB / 400 MB elsewhere | Both sets pinned. The same document with a 30 MB picture is refused on the server and opens locally with the whole picture. A 120 MB bomb is refused locally too |
| **List markers** (fidelity bug) | Every list item's marker comes from the library's `Document.GetListLabels()`, which includes numbering through paragraph styles, tables, headers and footers ("1.", "2.3.", "iv)", "•"). Before, numbered lists showed "–" and style-based lists showed no marker. Word's Symbol and Wingdings bullets (private-use characters such as U+F0B7) get their standard Unicode shape, because only Windows' own fonts draw them; numbers and the document's text are never changed | The test file's items show "•", "•", "1.", "2." (as Word shows them). The glyph mapping and pass-through are tested on their own. Checked on screen |

## Proof
- Build 0 warnings (`-warnaserror`, both solutions); tests 313/313 (Reader 199, Hosting 59, Mobile UI 16, Web UI 39).
- Windows-layout screens vs `053e8e4`: 24/27 identical. The 3 Settings › About screens differ only in the versions shown (Chuvadi.Docs 2.0.0, Chuvadi.Sheets 2.0.2). Home and Library at 1× were the known artefacts (identical on re-run).

## Windows behaviour changes
Word and Excel files show their values as the file holds them: formula results, dates, tabs, line breaks, runs of spaces, headers and footers, landscape pages, pictures and table text. A zip bomb or an oversized Word file is refused with "too large to open". A slow Word or Excel open stops at "Stop opening" or after a minute. About lists the new versions.
