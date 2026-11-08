# Linux Test fixtures (test-only; never shipped)

- `far-cell.xlsx` (B-09a) — the Linux chat's `sample.xlsx` fixture with one extra cell `<c r="XFD1048576"><v>1</v></c>` (row 1048576) appended to `xl/worksheets/sheet1.xml`, re-zipped with Python `zipfile`.
- `bomb.docx` (B-08a) — the same `sample.docx` with `word/document.xml` replaced by one run of 1,024 × 1 MiB `<w:t>AAAA…</w:t>` blocks (1 GiB uncompressed), deflated with Python `zipfile` (zip64) to ~1 MB.

SHA-256:
```
2f460d49bc22af7e4076e47f18474bf4c53efa1012170be55c39dcc636d28943  bomb.docx
1a30357a780021e19005e914ea3995eff4320ae717138690f6f91d859343fb07  far-cell.xlsx
```

- **Stalled source** (B-24, B-08b) — not a file: a named pipe (FIFO) that never delivers data, standing in for a hung network share or an unplugged USB drive. `stalled-source.sh make [dir]` creates `slow.pdf` and `slow.xlsx` pipes (default `/tmp/chvd-stall`); open one in Chuvadi, wait 10 s+ (Cancel should appear), then open any other file (it must open). `stalled-source.sh clean [dir]` unblocks the reader and removes them without hanging. Linux/macOS only (`mkfifo`); on Windows an equivalent is a file on an SMB share whose server is paused. Pass = "Opening…" visible at once, Cancel visible after 10 s, Cancel closes the tab, later opens never blocked (D-130).
- `exact.xlsx`, `exact.docx` (+ `expected.json`) — data that must come through exactly as stored: double/leading/trailing spaces, mixed case, a misspelling, Tamil, a tab, `00123` as text, a line break; xlsx also numbers with General, short-date (14), `"₹"#,##0.00` and `0.00%` (10) formats. Written by hand with Python `zipfile` (minimal valid OOXML; docx reuses `sample.docx`'s other parts).
