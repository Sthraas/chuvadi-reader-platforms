"""Large/limit-edge XLSX files written as raw SpreadsheetML (Web Test chat; test tooling only).
python3 make_large_xlsx.py <out>
  big-100k.xlsx        100,000 rows x 6 columns (V-3 size; opens; used for timing and Cancel)
  rows-1048576.xlsx    exactly Excel's maximum rows (should open)
  rows-1048577.xlsx    one row over (MaxRowsPerSheet → refused)
  entries-20001.xlsx   20,001 zip entries (MaxPackageEntries → refused)
  ratio-600.xlsx       a 300 MB part of repeated text, ratio > 500:1 (MaxCompressionRatio / MaxPartBytes → refused)"""
import os, sys, zipfile
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
CT = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
WB = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>')
WBRELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
HEAD = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
TAIL = '</sheetData></worksheet>'

def book(name, rows_writer, extra=None):
    with zipfile.ZipFile(os.path.join(out, name), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT); z.writestr("_rels/.rels", RELS)
        z.writestr("xl/workbook.xml", WB); z.writestr("xl/_rels/workbook.xml.rels", WBRELS)
        with z.open("xl/worksheets/sheet1.xml", "w", force_zip64=True) as f:
            f.write(HEAD.encode()); rows_writer(f); f.write(TAIL.encode())
        if extra: extra(z)
    print(f"{os.path.getsize(os.path.join(out, name)):>12}  {name}")

def rows(n, cols):
    def w(f):
        buf = []
        for r in range(1, n + 1):
            cells = "".join(f'<c r="{chr(65 + c)}{r}" t="inlineStr"><is><t>r{r}c{c}</t></is></c>' if c % 2 else f'<c r="{chr(65 + c)}{r}"><v>{r * (c + 1)}</v></c>' for c in range(cols))
            buf.append(f'<row r="{r}">{cells}</row>')
            if len(buf) >= 5000: f.write("".join(buf).encode()); buf = []
        f.write("".join(buf).encode())
    return w

book("big-100k.xlsx", rows(100_000, 6))
book("rows-1048576.xlsx", rows(1_048_576, 1))
book("rows-1048577.xlsx", rows(1_048_577, 1))
book("entries-20001.xlsx", rows(3, 2), extra=lambda z: [z.writestr(f"customXml/item{i}.xml", "<x/>") for i in range(20_001)])
def ratio(f):
    f.write('<row r="1"><c r="A1" t="inlineStr"><is><t>'.encode())
    chunk = ("A" * (1 << 20)).encode()
    for _ in range(300): f.write(chunk)
    f.write('</t></is></c></row>'.encode())
book("ratio-600.xlsx", ratio)
