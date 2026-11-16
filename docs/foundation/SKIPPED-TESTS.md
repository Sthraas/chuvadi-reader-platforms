# The skipped tests in the Reader's tests, and why

Six tests in `tests/ChuvadiReader.Tests` are skipped. Each is a defect in a Chuvadi library that the Reader must not
paper over (D-161: no app-side workarounds for library gaps). The test is written and states what is right; it is
unskipped when the library release that fixes its item is taken. Nothing else is skipped.

| Item | Test (file) | What the library does | What is right |
|---|---|---|---|
| PDF-L1 | `CropBoxTests.cs`, header and footer on a cropped page | `HeaderFooter` (chuvadi-pdf 3.32.0) places the bands on the MediaBox, so on a cropped page they fall in the part the file hides | Bands inside the page as shown (the CropBox) |
| PDF-L2 | `CropBoxTests.cs`, watermark on a cropped page | `WatermarkStamper` centres on the MediaBox (on the test page it lands 62 % across, 60 % down) | Centred on the page as shown |
| PDF-L6 | `PageRotateTests.cs`, a picture placed with a turn | `PageRasterizer` draws nothing for a picture placed with a quarter or half turn | The picture drawn, turned |
| PDF-L7 | `PageRotateTests.cs`, header and footer on a turned page | `HeaderFooter` ignores the page's /Rotate: the footer runs along a side of the page as shown | The footer along the bottom of the page as shown |
| PDF-L8 | `PageRotateTests.cs`, watermark on a turned page | `WatermarkStamper` ignores /Rotate: a level watermark reads sideways on the page as shown | Level on the page as shown |
| SH-L1 | `XlsxDisplayTests.cs`, time-only values | Chuvadi.Sheets 2.0.4 reads a time-only value (stored 0 to 1) one day early. Not fixed in 2.0.5 | The time as the file holds it. Ask: `LIBRARY-ASK-SHEETS-SH-L1.md` |

PDF-L6, L7 and L8 are theories, so the test runner counts each once: six skipped in all.

A seventh library item has no skipped test because the Reader words it itself meanwhile: SH-L2 (a size refusal that
is not typed as one; `LIBRARY-ASK-SHEETS-SH-L2.md`, test `XlsxTooLargeTests`).
