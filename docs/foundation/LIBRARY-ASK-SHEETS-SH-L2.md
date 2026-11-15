# Library ask: Chuvadi.Sheets SH-L2, a size refusal that is not typed as one

**Found by:** Web Test (WT-18). **Seen in:** Chuvadi.Sheets 2.0.4 and 2.0.5.

## What happens
`Workbook.Load(path, password, XlsxReaderOptions.ForUntrustedInput())` on a workbook with a part over `MaxPartBytes`
(a 300 MB sheet part, or a 2 GB one) throws

    System.IO.InvalidDataException: Decompressed size limit of 268435456 bytes exceeded for package part
    'xl/worksheets/sheet1.xml' (declared 314573011).
    at Chuvadi.Sheets.Internal.PackageGuard.Check(Stream input, XlsxReaderOptions o, ReadBudget budget)

The documentation of `MaxPartBytes`, `MaxTotalUncompressedBytes`, `MaxCompressionRatio` and `MaxPackageEntries` says
these limits throw `XlsxLimitExceededException`. The row and entry limits do; the package guard does not.

## Why it matters
`InvalidDataException` is what a damaged file gives, so an app cannot tell "too big" from "broken" without reading
the message text. The Reader told people such a file was damaged.

## The ask
`PackageGuard` throws `XlsxLimitExceededException` (naming the limit, as the others do) for every package limit:
declared size, size actually inflated, total, ratio, entry count.

## What the Reader does meanwhile
After the library has refused a file with `InvalidDataException`, the Core reads the file's zip table of contents with
.NET's own zip reader and, if a declared size is beyond the same limits, words the refusal as "too large"
(`XlsxViewService.BeyondPackageLimits`). It never refuses a file itself. One case stays "damaged" until the library
changes: a part that declares a small size and inflates past the limit.

## Test files
A workbook whose one sheet is a single text cell of 300 MB (`tests/ChuvadiReader.Tests/XlsxTooLargeTests.cs` builds it).
