# Ask for the Sheets list: SH-L1, time-only cells (Linux Test B-31)

**For:** Chuvadi.Sheets (seen in 2.0.4). **Severity:** S2: a wrong value is shown and handed on.
**It is purely the library.** The Reader passes the loaded cell to `Cell.GetDisplayText` and shows what comes back
(D-161: no app-side formatting). The fault is in **loading**, not in formatting.

## What happens
A cell that stores a time with no date (a number from 0 up to 1 in the 1900 date system) is loaded one day early.

| In the file (`formats.xlsx`) | `Cell.Value` after `Workbook.Load` | `NumberFormatter.ToSerial(value)` | `GetDisplayText` | Excel shows |
|---|---|---|---|---|
| `<v>0.75</v>`, numFmtId 18 (`h:mm AM/PM`) | `DateTime 1899-12-30 18:00:00` | **-0.25** | `########` | 6:00 PM |
| `<v>0.5104166</v>`, numFmtId 21 (`h:mm:ss`) | `DateTime 1899-12-30 12:14:59.994` | **-0.4895834…** | `########` | 12:15:00 |
| `<v>1.5</v>`, numFmtId 46 (`[h]:mm:ss`) | `DateTime 1900-01-01 12:00:00` | 1.5 (right) | 36:00:00 (right) | 36:00:00 |
| `<v>45000.75</v>`, numFmtId 22 | `DateTime 2023-03-15 18:00:00` | 45000.75 (right) | right | right |

So the loader turns a serial below 1 into a `DateTime` counted from 1899-12-30, while `ToSerial` (and the loader
itself for serials from 1 to 59) counts from 1899-12-31. The two disagree by one day for exactly the range 0 ≤ serial < 1.

The formatter is right when given the right input:
`NumberFormatter.Format(0.75, "h:mm AM/PM")` gives `6:00 PM`, and so does
`NumberFormatter.Format(new DateTime(1899, 12, 31, 18, 0, 0), "h:mm AM/PM")`.

## The ask
1. **Load:** a serial `s` with `0 ≤ s < 1` in the 1900 system loads as `1899-12-31` plus `s` days (the same epoch the
   loader uses for serials 1 to 59), so that `ToSerial(cell.Value)` returns `s` and `GetDisplayText` shows the time.
   Please check the 1904 system's `0 ≤ s < 1` range too.
2. **Round trip:** a test that for every stored serial in `[0, 61]` (both date systems), `ToSerial(Load(s)) == s`.
3. **Better still (already on the list as SH-L10):** give the stored number itself (`Cell.StoredNumber`, the `<v>` as
   written), so no reader has to go back from a `DateTime` to the number.

## How to reproduce
`tests/ChuvadiReader.Tests/Fixtures/Office/formats.xlsx` (made by `tools/OfficeCorpus/make_formats.py`), rows 18, 19
and the "system time F400" and "ss.000" rows:
`Workbook.Load(path).Sheets[0]`, cell B18: `Value`, `GetDisplayText(...)`, `NumberFormatter.ToSerial((DateTime)Value, false)`.

## In the Reader until then
The cells show `########` and their value bar, hover and copy give the wrong number (-0.25 for 0.75). One skipped test
names this item: `XlsxDisplayTests.Time_only_values_keep_their_stored_value_and_show_as_times`. It is unskipped when a
fixed Sheets lands.
