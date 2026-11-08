# Ninth combined patch — library features in the shared Core and Ui (9 Nov)

The library coordinator confirmed which library features are usable today (coordinator 01:55 IST). Everything goes through the library; no workarounds.

## 1. B-07 open password (chuvadi-pdf 3.31.2) — applied
| Change | Where |
|---|---|
| The prompt follows the library: `PdfPasswordRequiredException.PasswordSupplied` (3.24+) tells "none given" (just the prompt) from "wrong" ("That password doesn't open this file.", `TabsService.WrongPassword`) | `TabsService.cs` |
| The unlock card speaks the Protect › Password card's language: a **"Password to open"** label, **show / hide** inside the field, then **Open**. Lock icon in a 44 px circle (README §187). One card for PDF, Word and Excel, on every platform | `UnlockCard.razor(+.css)` |
| Test: the message follows `PasswordSupplied` both ways (`TestChatFixesTests`). The Linux chat's tests already cover missing, wrong and right with a real AES-256 file (`PdfPasswordTabTests`) | tests |

**Measured, so not wired into the open path:**
- `PdfDocument.RequiresPassword(path)` costs as much as a whole open of a plain PDF: 0.50 ms against 0.44 ms on a 38 KB file, warm. On a locked file it is slower (6.4 ms) than the failed open it would avoid (3.7 ms warm).
- Checking first would therefore double every PDF open and save nothing, so the open path catches the exception and reads `PasswordSupplied`.
- `PdfOpenOptions.Password` comes with the library's options-based `Open`. Its async form takes a stream that it buffers into memory. The path overload `OpenAsync(path, password, ct)` already carries the password and keeps today's file reading.
- Both are open questions to the coordinator (see BUILD-LOG §26).

Until `EncryptionInfo.OpenedWith` (chuvadi-pdf 3.32.0), a file opened with its owner password still refuses printing when its permissions say so.

## 2. B-11a repair (chuvadi-pdf `PdfRepairer.Repair`, 3.10+) — already shared
"Try to repair (new copy)" calls the shared Core's `RecoveryService.RecoverAsync`, which calls `PdfRepairer.Repair(input, output)` into a new file next to the others in "Recovered". Nothing is host-specific. The Linux chat's test damages a PDF, repairs it and opens the copy (`PdfPasswordTabTests`).

## 3. Sheets open cancel — waits for the Sheets move
Core carries Chuvadi.Sheets **1.1.2**. Its `XlsxReaderOptions` has `TreatFirstRowAsHeaders`, `AutoDetectDates`, `StrictXml` and `MaxPartBytes`, but no `CancellationToken`. `Workbook.Load` takes no options and there is no `XlsxReader.Open`. So B-08b's Stop and timeout for Excel are wired when Sheets moves (item 4's decision). Until then the slow-open note's "Stop opening" closes the tab and the load finishes in the background.

## Proof
- Build 0 warnings (`-warnaserror`, both solutions); tests 297/297 (Reader 189, Hosting 59, Mobile UI 16, Web UI 33).
- Preview (portal): a locked PDF shows "Password to open" with show/hide. A wrong password says so; the right one opens all 13 pages. No page errors.
- Windows-layout screens vs `839d39d`: 27/27 identical (the unlock card isn't on those screens; Home's few-pixel relative-time artefact moved between scales across runs).

## Windows behaviour change
The unlock card (locked PDF, Word, Excel) gains the "Password to open" label and show/hide. PR #11 lists it when it moves.
