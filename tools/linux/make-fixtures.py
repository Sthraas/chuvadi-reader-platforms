#!/usr/bin/env python3
"""Test fixtures for the Linux UI test (test-only, never shipped).

Writes into the given folder:
  five-pages.pdf  — 5 pages (page 4 landscape), "Page N" in Helvetica (a standard, non-embedded font)
  sample.docx     — a minimal Word document (one heading, one paragraph)
  sample.xlsx     — a minimal workbook (one sheet, a few cells)
Everything is written by hand with the standard library, so no tool or library is involved.
"""
import sys, os, zipfile

def pdf(path):
    objs = []
    def add(body):
        objs.append(body)
        return len(objs)
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_id = len(objs) + 1 + 10  # placeholder, fixed below
    kids = []
    page_objs = []
    for n in range(1, 6):
        w, h = (842, 595) if n == 4 else (595, 842)
        text = f"BT /F1 36 Tf 72 {h-120} Td (Page {n}) Tj ET\nBT /F1 14 Tf 72 {h-160} Td (Chuvadi Linux print test - {'landscape' if n == 4 else 'portrait'}) Tj ET\n0 0 1 RG 4 w 36 36 {w-72} {h-72} re S".encode()
        content = add(b"<< /Length %d >>\nstream\n" % len(text) + text + b"\nendstream")
        page_objs.append((content, w, h))
    pages = len(objs) + len(page_objs) + 1
    for content, w, h in page_objs:
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>" % (pages, w, h, content, font)))
    assert add(b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + b"] /Count %d >>" % len(kids)) == pages
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages)
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offsets:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
    open(path, "wb").write(out)

CT = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

def docx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", CT + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", CT + '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:rPr><w:b/><w:sz w:val="40"/></w:rPr><w:t>Chuvadi Linux test document</w:t></w:r></w:p><w:p><w:r><w:t>This paragraph checks the Word viewer on Linux.</w:t></w:r></w:p></w:body></w:document>')

def xlsx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", CT + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", CT + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", CT + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", CT + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Test</t></is></c><c r="B1" t="inlineStr"><is><t>Value</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Pages</t></is></c><c r="B2"><v>5</v></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>Copies</t></is></c><c r="B3"><v>2</v></c></row></sheetData></worksheet>')

if __name__ == "__main__":
    folder = sys.argv[1]
    os.makedirs(folder, exist_ok=True)
    pdf(os.path.join(folder, "five-pages.pdf"))
    docx(os.path.join(folder, "sample.docx"))
    xlsx(os.path.join(folder, "sample.xlsx"))
    print("fixtures in", folder)
