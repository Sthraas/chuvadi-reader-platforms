# Chuvadi.Sheets 2.0.4 in ci/packages (seventeenth combined patch, 10 Nov 2026)

Replaces 2.0.2 (2.0.3 skipped, as the coordinator asked). Downloaded unchanged from Arun's release asset:
`github.com/arunshivab/chuvadi/releases/download/sheets-v2.0.4/Chuvadi.Sheets.2.0.4.nupkg`.

| Package | Tag (object → commit) | Size | SHA-256 |
|---|---|---|---|
| Chuvadi.Sheets.2.0.4.nupkg | `sheets-v2.0.4` (77aad06 → 9b8110b) | 354,835 B | `9b777e9518494a0531e25742c1f3fb7f8633dd9dabf44fa083cc44d0dd345d90` |

- **Hash:** equals the one Arun published (9B777E95…5D90).
- **Ties to the tag:** the nuspec names the monorepo at commit `9b8110b89567084fad2be582657d238f694ea928`, the tag's commit.
- **Same terms:** no package dependencies, net10.0, MIT. Notices regenerated (the only change is the version line).

## What 2.0.4 changes for the Reader
- **We were already past the 1.1.2 → 2.x breaks:**
  - namespace `Chuvadi.Sheets.Model`;
  - `XlsxFormatException` for malformed files;
  - load options `XlsxReaderOptions.ForUntrustedInput()` plus the open's `CancellationToken`.
- **DataTable column names** (Qty, Qty2, Column1…): the Reader doesn't use `DataTable`.
- **Streams are no longer closed by the library:** the Reader loads by path, so this has no effect.
- **Pictures, charts, macros, pivots and some styles are lost on load and save:** the Reader only reads xlsx. It never writes one back (no save, export or write-back path for Excel files anywhere in Core or Ui), so there is nothing to warn about under D-155. If an Excel save is ever added, it needs that warning first.

## Checks
- All 22 `OfficeViewTests` pass unchanged: every value exactly as in the file, the 1904 workbook and the far cell included.
- Built from an empty package cache; 0 warnings.
- **en-IN date format 14 is unchanged in 2.0.4.** `Cell.GetDisplayText` with en-IN still gives month first: 5 Nov 2024 shows as `11-05-24`, 1 Jan 1904 as `01-01-04` (same as en-US). Excel on an en-IN computer shows day first.
  - The Reader isn't affected, because it shows raw values (D-147: dates as `yyyy-mm-dd`).
  - The library item from B-26 still stands.
