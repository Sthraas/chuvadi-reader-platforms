"""Recreates the small hand-made test files that lived only in /tmp: /tmp/enc (encodings, WT-26), /tmp/p29 (Excel pager,
resize, hidden-cell Find). The others come from ../make_corpus.py (/tmp/corpus), ../make_fidelity.py (/tmp/fid),
../make_large_xlsx.py (/tmp/bigx); /tmp/m27 (plain.pdf, rot90.pdf) from make_m27.py. Test tooling only."""
import os, struct
os.makedirs("/tmp/enc", exist_ok=True); d = "/tmp/enc/"
open(d + "cp1252.txt", "wb").write("Café – naïve £5 “quoted” Zoë\nline two: façade\n".encode("cp1252"))
open(d + "utf16.txt", "wb").write("Unicode sixteen: தமிழ் café\n".encode("utf-16"))
open(d + "utf16be.txt", "wb").write(b"\xfe\xff" + "BE sixteen: தமிழ் café\n".encode("utf-16-be"))
open(d + "utf16le-nobom.txt", "wb").write("No BOM sixteen: café\n".encode("utf-16-le"))
open(d + "utf16le.md", "wb").write(b"\xff\xfe" + "# Kopf ü\n\nதமிழ் LE markdown\n".encode("utf-16-le"))
open(d + "utf8.md", "wb").write("# Heading é\n\nBody – தமிழ் ✓\n".encode("utf-8"))
open(d + "latin.html", "wb").write("<html><head><meta charset='windows-1252'></head><body><p>Prix: 5 € – déjà</p><script>document.title='x'</script></body></html>".encode("cp1252"))
open(d + "utf32.txt", "wb").write(b"\xff\xfe\x00\x00" + "UTF-32 text".encode("utf-32-le"))
open(d + "zeros.txt", "wb").write(b"\xff\xfe" + b"\x00\x00" * 40 + "tail".encode("utf-16-le"))
open(d + "badsurr.txt", "wb").write(b"\xff\xfe" + "ok ".encode("utf-16-le") + struct.pack("<H", 0xD800) + "x".encode("utf-16-le"))
open(d + "exe-as.txt", "wb").write(b"\xff\xfeMZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + bytes(range(256)) * 3)
from openpyxl import Workbook
os.makedirs("/tmp/p29", exist_ok=True); wb = Workbook(); a = wb.active; a.title = "Alpha"
for r in range(1, 31):
    for c in range(1, 9): a.cell(r, c, f"A-r{r}c{c}")
a["B2"] = "needle visible"; a["A5"] = "needle in hidden row"; a["C6"] = "needle in hidden column"; a["D9"] = "A very long text that does not fit in its column at all"
a.row_dimensions[5].hidden = True; a.column_dimensions["C"].hidden = True
wb.create_sheet("Beta")["A1"] = "beta-first"; wb.create_sheet("Gamma")["A1"] = "gamma-first"; wb.save("/tmp/p29/sheets.xlsx")
print("made /tmp/enc and /tmp/p29")
