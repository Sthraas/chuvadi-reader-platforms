# The older code pages: what "More encodings" would cost

**Question (D-191):** the first encoding picker lists Automatic, UTF-8, Windows-1252, UTF-16 LE and UTF-16 BE. None of
those needs anything beyond what .NET always has (Windows-1252 is the Reader's own table). "More encodings"
(Cyrillic, Greek, Japanese, Chinese, Korean, Tamil ISCII and so on; 38 in `TextEncodings.All`) needs .NET's
code-pages provider. This is what that costs.

## What it is
`System.Text.Encoding.CodePages` is part of .NET itself: no package, nothing external (the "no externals" rule holds).
It is switched on by one call, `Encoding.RegisterProvider(CodePagesEncodingProvider.Instance)`.

## Measured
| | Result |
|---|---|
| Size added to a trimmed build | about 0.7 MB: linux-x64 726 KB, osx-arm64 726 KB, android-arm64 715 KB |
| Trim warnings added | none |
| Encodings it brings | 109 |
| Switching it on | about 2 ms, once |
| First read in one of its encodings | about 15 ms, once per encoding |
| Cost at startup | none: the Core switches it on the first time one of those encodings is asked for (`TextEncodings`), never before |
| Kept in a trimmed build | yes: `tools/TrimProbe` reads a sample in all 38 listed encodings and fails if one is missing or if the provider is on after startup ("38 encodings, 0 missing, code pages on at startup: False") |

Sizes and times were measured on this build machine (Linux x64) on 15 Nov; the other two sizes are from trimmed
publishes for those targets made here, not from runs on those devices.

## What is not measured
Windows and Mac Catalyst trimmed sizes (expected the same file, about 0.7 MB), and times on a phone.

## Reading
The size is already paid if the Core refers to the provider at all, which it does since patch 29 (the long list is
built and tested). So "More encodings" costs no further size and no startup time; what remains is a Ui decision.
