# File-fidelity audit (D-161, 10 Nov 2026)

Arun's rule: **show what the file holds.** This lists every place found where any of the five apps shows something
other than the file, or hides something it holds. They all share one Ui and Core, so every item applies to all five
unless it says otherwise. Each item has a fix in the app (**App**) or a library item (**Lib**), and a status.

How it was checked: the Reader's code read end to end for each format; probe files (`tools/OfficeCorpus/make_formats.py`,
`make_pdf_fixtures.py`, and the cropped pages authored in `CropBoxTests`) run through Chuvadi.Sheets 2.0.4 and
chuvadi-pdf 3.32.0; the Windows Reader chat's list of 10 Nov (items it found) folded in.

**Fixed in the twenty-fourth patch:** E-01, E-02 (part), E-03, E-04, P-01, P-02.

## Excel (.xlsx)

| # | What differs from the file | Fix | Status |
|---|---|---|---|
| E-01 | Cells showed the raw value: no currency, separators, decimals, percentages, date or time formats | App: Chuvadi.Sheets' display text in the system culture; the value stays underneath (copy, Find, the value bar) | **Fixed** (D-161) |
| E-02 | Colour sections (`[Red]`, `[Color10]`), conditional formats' number format, fill and font, and `*` fills were ignored | App: from the library (FormatDetailed, the conditional-format evaluator); accounting fills keep the symbol at the left | **Fixed**; colour for ids 6 and 8 waits for SH-L3 |
| E-03 | Dates were left-aligned and booleans left-aligned | App: numbers and dates right, TRUE/FALSE centred (Excel's General alignment) | **Fixed** |
| E-04 | Copy and Find used the shown text | App: on the stored value (D-161) | **Fixed** (see question Q-1) |
| E-05 | Rows past 5,000 and columns past 256 are not in the grid (copy all and Find still see them) | App: virtualise columns as rows are; drop the row cap | Next patch |
| E-06 | Hidden rows and columns are shown | App: hide them as Excel does (`Rows[r].Hidden`, `Columns[c].Hidden`), with the row and column numbers skipping | Next patch |
| E-07 | Merged cells show unmerged | App: span them (`Sheet.MergeRanges`) | Next patch |
| E-08 | Row heights ignored (every row 22 px); column widths approximated (width × 7 px) | App: the file's heights; Excel's width-to-pixel rule for the default font | Next patch |
| E-09 | Text doesn't run into empty neighbouring cells; long text is cut with "…" at 360 px | App: overflow into empty neighbours as Excel does; no ellipsis | Next patch |
| E-10 | Frozen header rows are drawn bold whatever the file says | App: drop the forced bold | Next patch (one line) |
| E-11 | Cell borders, pattern and gradient fills, strikethrough, super/subscript, underline kinds, indent, rotation, shrink-to-fit are not drawn | App: the library has them (`CellStyle`) | Next patch |
| E-12 | Rich text inside a cell shows as plain text | App: draw `Cell.RichText` runs | Next patch |
| E-13 | Conditional-format data bars and icon sets are not drawn | App: the library gives bar length, colours and icon index | Next patch |
| E-14 | Hidden and very hidden sheets show as tabs | App: leave them out of the tabs (or mark them; Arun's call, Q-2) | Next patch |
| E-15 | Comments, hyperlinks, pictures, shapes and charts are not shown | App: comments and hyperlinks; Lib/Layout: pictures and charts | Comments, links next patch; drawings wait for Layout |
| E-16 | Gridlines always shown; right-to-left sheets shown left-to-right; the sheet's zoom ignored | App: `ShowGridLines`, `RightToLeft`, `ZoomScale` | Next patch |
| E-17 | "As printed" (page setup, print areas, headers and footers) not shown | Lib: Layout.Sheets via Layout.Pdf | Blocked: no Layout.Pdf release, no checksums |

### Sheets library items (urgent, D-161)

What `GetDisplayText` covers today (2.0.4, probed with en-IN): General; 0, #, ? placeholders; decimals; grouping
(en-IN 12,34,567); scaling commas; percent; scientific; fractions; up to four sections and `[>100]` conditions; colours;
literals, escapes, `_x` and `*x`; `[$₹-4009]` currency tags; text sections; dates (d, m, y, names), times and elapsed
`[h]`; 1904 workbooks. What it gets wrong or can't do:

| # | Item | Seen with 2.0.4 | Excel |
|---|---|---|---|
| SH-L1 | A time with no date (stored 0 to 1, 1900 system) is read one day early: 0.75 comes back as 1899-12-30 18:00 (−0.25) | `########`, and the stored value can't be recovered | 6:00 PM (h:mm AM/PM), value 0.75 |
| SH-L2 | Built-in 14 (short date) and 22 (date and time) are fixed codes; Excel uses the system's short date | 03-15-23, 3/15/23 18:00 | en-IN: 15-03-2023, 15-03-2023 18:00 |
| SH-L3 | Locale-dependent ids 5–8 and 41–44 always render as en-US, ignoring `Culture`; `GetNumberFormatCode` gives null, so their `[Red]` colour can't be had either | $1,235, ($1,234.50) | en-IN: ₹ 1,235, -₹ 1,234.50 in red |
| SH-L4 | `[$-F800]` (system long date) and `[$-F400]` (system time) use en-US patterns, not `Culture`'s | Wednesday, March 15, 2023 | en-IN: Wednesday, 15 March, 2023 |
| SH-L5 | A format's own locale tag (`[$-407]`, `[$-449]`) doesn't change month and day names | Wednesday, 15. March 2023 | Mittwoch, 15. März 2023 |
| SH-L6 | `[DBNum1–4]`, the Buddhist (`,107`) and Hijri (`B2`) calendars | 123, 15/3/2023 | 一百二十三, 15/3/2566 |
| SH-L7 | General and `#` overflow depend on the column's width: Excel shows fewer digits, scientific or `#####` when a number doesn't fit | 3.141592654 in any width | 3.14159 in a narrow column; `#####` for a date that doesn't fit |
| SH-L8 | An error cell (`t="e"`) reads as a string, so it can't be told from text "#DIV/0!" (Excel centres errors) | string | error |
| SH-L9 | One call for what Excel shows in a cell: text, colour (which wins, number-format colour or a conditional format's font colour), fill and fill index, with conditional formats applied (SH-9, proposed for 2.1.0) | the app combines four calls | — |
| SH-L10 | The stored value as the file writes it (the `<v>` text): dates come back as `DateTime` and are turned back into the stored number with `ToSerial`, exact only to 100 ns | — | — |

## PDF

| # | What differs from the file | Fix | Status |
|---|---|---|---|
| P-01 | Pages showed the whole MediaBox instead of the CropBox | Library 3.32.0 draws the CropBox; nothing passes another box | **Fixed** (D-160) |
| P-02 | With the CropBox shown, everything the Reader puts on a page was placed on the MediaBox: redaction boxes, markups, page numbers, bench crop, margins, resize and N-up, measuring, search boxes, a large sheet drawn as one image (stretched), and Properties' page size | App: all of them are fractions of the shown box (`ShownBox`: CropBox within MediaBox, inherited ones too) | **Fixed** |
| P-03 | Headers and footers are placed on the MediaBox, so on a cropped page they can fall in the hidden part | Lib PDF-L1 | Library |
| P-04 | Watermarks are centred on the MediaBox, not on the page as shown | Lib PDF-L2 | Library |
| P-05 | Page labels (/PageLabels: i, ii, A-1) aren't shown; the page box always counts 1…n | Lib PDF-L3 (read page labels), then App | Library |
| P-06 | /UserUnit pages are drawn at the wrong size (only Measure corrects for it) | Lib PDF-L4 | Library (Windows Reader chat's item 3) |
| P-07 | Dynamic XFA forms: only the static template shows, not the filled-in data | Lib PDF-L5 | Library (Windows Reader chat's item 2) |
| P-08 | Outline and link jumps, layers, viewports | Windows Reader chat's 3.32.0 PR | In progress; its link rectangles must use the shown box (`ShownBox`) |
| P-09 | A page's `/Rotate` (90, 180, 270) was ignored: the page was shown unturned (Linux Test B-32). Redaction, shapes and measuring already allowed for the turn, so on such a page they landed in the wrong place | App: the renderers are asked to apply the page's turn (`ApplyPageRotation`, in the library since before 3.32.0 and off by default); page numbers, text and pictures added in Mark, Properties' page size, image and SVG export, and the bench's crop, mask, margins, resize and imposition all follow the page as shown | **Fixed** (patch 26) |
| P-10 | On a turned page, headers and footers run along a side and a level watermark reads sideways | Lib PDF-L7 (HeaderFooter), PDF-L8 (WatermarkStamper): honour `/Rotate` | Library |
| P-11 | A picture placed with a quarter or half turn (one added in Mark on a turned page, or turned by 90° on any page) is missing from print and image export; it is in the file and on screen | Lib PDF-L6: `PageRasterizer` draws nothing for an image whose matrix is a quarter or half turn (it draws 45°; `SvgRenderer` draws all) | Library |
| — | Annotations, form values and layers: drawn as a viewer shows them (AnnotationMode View; values drawn when appearances are missing; the file's default layers) | — | Matches the file |

## Word (.docx)

| # | What differs from the file | Fix | Status |
|---|---|---|---|
| W-01 | Not shown as pages (page size, margins, breaks, columns) | Lib: Layout.Docs via Layout.Pdf | Blocked: no Layout.Pdf release |
| W-02 | Formatting that comes from a style (bold, size, font, colour, spacing, indents) isn't applied; only Title and Heading 1–3 are recognised | Lib: the resolved formatting per run and paragraph (Docs ask) | Library |
| W-03 | Floating images, text boxes and shapes; footnotes and endnotes; comments; tracked changes; fields (page numbers, TOC) | Lib (read them), then App | Library |
| W-04 | A list bullet in a Symbol or Wingdings code is shown as the standard Unicode shape, and any other symbol-font bullet as "•" | Lib: the glyph through the bundled fonts, or the exact mapping table | Library; the app's mapping stays until then |
| W-05 | Section headers and footers other than the first and default | Lib | Library |

## Markdown, text and HTML

| # | What differs from the file | Fix | Status |
|---|---|---|---|
| M-01 | Raw HTML inside Markdown is shown as text, not rendered | Safety (nothing in a file runs); Arun's call, Q-3 | Open |
| M-02 | Footnotes, definition lists, maths and diagrams in Markdown aren't rendered | App (CommonMark/GFM extensions) | Later |
| T-01 | A text file that isn't UTF-8 or UTF-16 is read as Latin-1, so Windows-1252 quotes and dashes (0x80–0x9F) show as control characters, and other code pages (ISCII, Shift-JIS) are wrong | App: Windows-1252 instead of Latin-1 (the .NET code-page provider is part of .NET) | Next patch |
| H-01 | Scripts, forms, frames, media, SVG and maths are removed; stylesheets and styles with `url(` are dropped, so web fonts and background images don't show; remote images wait for "Load images" | Safety; Arun's call, Q-3 (the Windows Reader chat's item 5) | Open |

## Display-only changes that don't alter the file

Zoom, text size, Find highlights, page colour (shown over the page, never saved) and the dark themes' grey around
the page. The page itself is always drawn as the file says.

## Questions for Arun

- **Q-1 (Excel Find):** D-161 says search on the value. Someone searching for "12,34,567" or "March" won't find a cell
  that shows it. Options: (A) value only, as now — pros: exactly the rule; cons: what you see isn't findable;
  (B) value or shown text — pros: finds both; cons: a hit may match only the shown text. Recommendation: **B**.
- **Q-2 (hidden sheets):** (A) leave them out, as Excel does — pros: same as Excel; cons: their data isn't reachable
  in a view-only app; (B) show them dimmed with "hidden" — pros: nothing the file holds is hidden from you; cons:
  differs from Excel. Recommendation: **B**, since the rule is not to hide what the file holds.
- **Q-3 (HTML and Markdown safety):** keep removing scripts, forms and remote content (the file can't run anything
  or call out), or show more. Recommendation: keep it, and say on the banner exactly what was left out (it does now).
