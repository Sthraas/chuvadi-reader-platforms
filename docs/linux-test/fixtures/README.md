# Linux Test fixtures (test-only; never shipped)

- `far-cell.xlsx` (B-09a) — the Linux chat's `sample.xlsx` fixture with one extra cell `<c r="XFD1048576"><v>1</v></c>` (row 1048576) appended to `xl/worksheets/sheet1.xml`, re-zipped with Python `zipfile`.
- `bomb.docx` (B-08a) — the same `sample.docx` with `word/document.xml` replaced by one run of 1,024 × 1 MiB `<w:t>AAAA…</w:t>` blocks (1 GiB uncompressed), deflated with Python `zipfile` (zip64) to ~1 MB.

SHA-256:
```
2f460d49bc22af7e4076e47f18474bf4c53efa1012170be55c39dcc636d28943  bomb.docx
1a30357a780021e19005e914ea3995eff4320ae717138690f6f91d859343fb07  far-cell.xlsx
```
