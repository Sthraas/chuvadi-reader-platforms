#!/usr/bin/env python3
"""Mac Test fixtures (testing only, never shipped). Pure Python 3, no packages.

Writes test documents into the folder given as argv[1]:
  five-pages.pdf      5 pages, text + vector shapes, page 4 landscape, outline, a link, a known phrase per page
  annotated.pdf       2 pages with Square, Highlight, Text (note) and FreeText annotations (Print flag set)
  noview-print.pdf    a "COPY" stamp with NoView+Print flags and an annotation without Print (library ask L-2 probe)
  form.pdf            AcroForm: text field "name", checkbox "agree"
  links.pdf           http, https, mailto, javascript: and file: link annotations
  heavy-vector.pdf    one A1 page, ~8 MB content stream of line work (stand-in for the 7.9 MB CAD PDF)
  many-pages.pdf      500 text pages
  tamil.pdf           Tamil text drawn with a non-embedded font name (substitution probe, L-1)
  damaged-*.pdf       truncated, bad startxref, garbage, empty
  sample.docx         heading, paragraphs, bold/italic runs, a table
  sample.xlsx         2 sheets: numbers, a date, currency format, merged cells
  bomb.docx           1 MB docx whose document.xml inflates to 1 GiB
  far-cell.xlsx       sample.xlsx + a cell at XFD1048576
  missing-part.docx   [Content_Types] points at a document part that is absent
  notes.md, notes.txt, page.html   text formats
  ஆவணம்-tamil-name.pdf  copy of five-pages.pdf under a Tamil file name
  unsupported.zip     a zip that is not a document
Encrypted variants are made by the workflow with qpdf (tool), from five-pages.pdf.
"""
import os
import sys
import zipfile
import zlib


def pdf_bytes(objects):
    """objects: list of bytes bodies, numbered 1..n. Object 1 must be the Catalog."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for o in offsets:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def stream(data, compress=True):
    if compress:
        z = zlib.compress(data, 6)
        return f"<< /Length {len(z)} /Filter /FlateDecode >>\nstream\n".encode() + z + b"\nendstream"
    return f"<< /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"


def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Doc:
    """Tiny PDF builder: pages with content, fonts Helvetica/Times (standard 14), optional annots."""

    def __init__(self):
        self.objs = [None, None]  # 1 catalog, 2 pages
        self.pages = []
        self.font_h = self.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        self.font_t = self.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>")
        self.catalog_extra = b""

    def add(self, body):
        self.objs.append(body)
        return len(self.objs)

    def page(self, content, w=595, h=842, annots=None):
        c = self.add(stream(content))
        a = b""
        if annots:
            a = b" /Annots [" + b" ".join(f"{x} 0 R".encode() for x in annots) + b"]"
        p = self.add(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Contents {c} 0 R "
            f"/Resources << /Font << /F1 {self.font_h} 0 R /F2 {self.font_t} 0 R >> >>".encode() + a + b" >>")
        self.pages.append(p)
        return p

    def bytes(self):
        kids = b" ".join(f"{p} 0 R".encode() for p in self.pages)
        self.objs[0] = b"<< /Type /Catalog /Pages 2 0 R" + self.catalog_extra + b" >>"
        self.objs[1] = b"<< /Type /Pages /Kids [" + kids + f"] /Count {len(self.pages)} >>".encode()
        return pdf_bytes(self.objs)


def text_page(title, lines, w=595, h=842, extra=b""):
    s = f"BT /F2 22 Tf 56 {h - 80} Td ({esc(title)}) Tj ET\n"
    y = h - 120
    for ln in lines:
        s += f"BT /F1 12 Tf 56 {y} Td ({esc(ln)}) Tj ET\n"
        y -= 18
    # vector work: a framed box, a circle-ish polygon and a diagonal, in colour
    s += f"0.62 0.25 0.16 RG 1.5 w 50 50 {w - 100} 60 re S\n"
    s += "0.2 0.4 0.7 rg 300 200 m 340 260 l 380 200 l h f\n"
    s += f"0 0 0 RG 0.5 w 50 140 m {w - 50} 180 l S\n"
    return s.encode() + extra


def five_pages(d):
    doc = Doc()
    for i in range(1, 6):
        land = i == 4
        w, h = (842, 595) if land else (595, 842)
        doc.page(text_page(
            f"Page {i} of five" + (" (landscape)" if land else ""),
            [f"Chuvadi Mac test phrase marker-{i}.", "The quick brown fox jumps over the lazy dog.",
             "Discharge summary - ward 4 - patient record 0042.", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
             f"Unique word for find: zebracrossing{i}"], w, h), w, h)
    return doc.bytes()


def annot(rect, subtype, extra, flags=4):
    r = " ".join(str(x) for x in rect)
    return f"<< /Type /Annot /Subtype /{subtype} /Rect [{r}] /F {flags} ".encode() + extra + b" >>"


def annotated(d):
    doc = Doc()
    a1 = doc.add(annot([100, 600, 260, 680], "Square", b"/C [1 0 0] /BS << /W 3 >> /Contents (red square)"))
    a2 = doc.add(annot([56, 718, 400, 736], "Highlight",
                       b"/C [1 1 0] /QuadPoints [56 736 400 736 56 718 400 718] /Contents (highlight)"))
    a3 = doc.add(annot([450, 700, 470, 720], "Text", b"/C [1 0.8 0] /Contents (A sticky note) /Name /Comment"))
    a4 = doc.add(annot([100, 400, 400, 440], "FreeText", b"/DA (/Helv 14 Tf 0 0 1 rg) /Contents (Free text comment)"))
    doc.page(text_page("Annotated page", ["Chuvadi Mac test phrase marker-1.", "Square, highlight, note and free text."]),
             annots=[a1, a2, a3, a4])
    doc.page(text_page("Second page", ["No annotations here."]))
    return doc.bytes()


def noview_print(d):
    doc = Doc()
    # Print-only stamp: NoView (32) + Print (4) = 36; screen-only square: flags 0 (no Print)
    ap = doc.add(stream(b"1 0 0 rg BT /F1 48 Tf 10 10 Td (COPY) Tj ET", compress=False).replace(
        b"<< /Length", b"<< /Type /XObject /Subtype /Form /BBox [0 0 200 70] /Resources << /Font << /F1 3 0 R >> >> /Length"))
    a1 = doc.add(annot([300, 500, 500, 570], "Stamp", f"/Name /Draft /AP << /N {ap} 0 R >>".encode(), flags=36))
    a2 = doc.add(annot([100, 300, 200, 400], "Square", b"/C [0 0 1] /BS << /W 4 >>", flags=0))
    doc.page(text_page("Print flags", ["A COPY stamp prints but is not shown on screen.",
                                       "The blue square is shown on screen but must not print."]), annots=[a1, a2])
    return doc.bytes()


def form(d):
    doc = Doc()
    tf = doc.add(b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (name) /Rect [150 650 450 675] /F 4 "
                 b"/DA (/Helv 12 Tf 0 g) /MK << /BC [0 0 0] >> /V () >>")
    on = doc.add(stream(b"0 0 0 rg 3 3 12 12 re f", compress=False).replace(
        b"<< /Length", b"<< /Type /XObject /Subtype /Form /BBox [0 0 18 18] /Length"))
    off = doc.add(stream(b"0 0 0 RG 1 w 1 1 16 16 re S", compress=False).replace(
        b"<< /Length", b"<< /Type /XObject /Subtype /Form /BBox [0 0 18 18] /Length"))
    cb = doc.add(f"<< /Type /Annot /Subtype /Widget /FT /Btn /T (agree) /Rect [150 600 168 618] /F 4 "
                 f"/V /Off /AS /Off /AP << /N << /Yes {on} 0 R /Off {off} 0 R >> >> /MK << /BC [0 0 0] >> >>".encode())
    helv = doc.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    doc.page(text_page("Form", ["Name:", "", "", "I agree:"]), annots=[tf, cb])
    doc.catalog_extra = f" /AcroForm << /Fields [{tf} 0 R {cb} 0 R] /DA (/Helv 12 Tf 0 g) /DR << /Font << /Helv {helv} 0 R >> >> >>".encode()
    return doc.bytes()


def links(d):
    doc = Doc()
    items = [("https", "https://example.com/chuvadi-mac-test"), ("http", "http://example.com/"),
             ("mailto", "mailto:test@example.com"), ("javascript", "javascript:alert(1)"), ("file", "file:///etc/hosts")]
    annots, lines = [], []
    y = 700
    for name, uri in items:
        annots.append(doc.add(annot([56, y - 4, 400, y + 14], "Link",
                                    f"/Border [0 0 1] /A << /S /URI /URI ({esc(uri)}) >>".encode())))
        lines.append(f"{name}: {uri}")
        y -= 18
    s = "BT /F2 22 Tf 56 762 Td (Links) Tj ET\n"
    y = 700
    for ln in lines:
        s += f"BT /F1 12 Tf 56 {y} Td ({esc(ln)}) Tj ET\n"
        y -= 18
    doc.page(s.encode(), annots=annots)
    return doc.bytes()


def heavy_vector(d):
    doc = Doc()
    w, h = 2384, 1684  # A1 landscape
    parts = [b"0 0 0 RG 0.3 w\n"]
    size = 0
    i = 0
    import random
    rnd = random.Random(7)
    while size < 8_000_000:
        x, y = rnd.uniform(20, w - 20), rnd.uniform(20, h - 20)
        seg = f"{x:.2f} {y:.2f} m {x + rnd.uniform(-40, 40):.2f} {y + rnd.uniform(-40, 40):.2f} l " \
              f"{x + rnd.uniform(-40, 40):.2f} {y + rnd.uniform(-40, 40):.2f} l S\n".encode()
        parts.append(seg)
        size += len(seg)
        i += 1
    parts.append(b"BT /F2 60 Tf 100 100 Td (Heavy vector drawing - CAD stand-in) Tj ET\n")
    data = b"".join(parts)
    c = doc.add(stream(data, compress=False))  # uncompressed: file is ~8 MB like the CAD sample
    p = doc.add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Contents {c} 0 R "
                f"/Resources << /Font << /F2 {doc.font_t} 0 R >> >> >>".encode())
    doc.pages.append(p)
    return doc.bytes()


def many_pages(d):
    doc = Doc()
    for i in range(1, 501):
        doc.page(text_page(f"Page {i}", [f"Line {k} of page {i}: the quick brown fox." for k in range(1, 30)]))
    return doc.bytes()


def tamil(d):
    doc = Doc()
    # A TrueType font referenced by name only (no font program) -> the viewer and the print path must substitute.
    f = doc.add(b"<< /Type /Font /Subtype /TrueType /BaseFont /Latha /FirstChar 32 /LastChar 126 "
                b"/Encoding /WinAnsiEncoding >>")
    s = b"BT /F3 24 Tf 56 760 Td (Latha, not embedded: ABC abc 123) Tj ET\n"
    c = doc.add(stream(s))
    p = doc.add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {c} 0 R "
                f"/Resources << /Font << /F3 {f} 0 R >> >> >>".encode())
    doc.pages.append(p)
    return doc.bytes()


W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def docx(path, body_xml, include_document=True):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        if include_document:
            z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document {W_NS}><w:body>{body_xml}</w:body></w:document>')


def p(text, bold=False, italic=False, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + "</w:rPr>"
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def sample_docx(path):
    rows = "".join(f"<w:tr>{''.join(f'<w:tc><w:p><w:r><w:t>R{r}C{c}</w:t></w:r></w:p></w:tc>' for c in range(1, 4))}</w:tr>"
                   for r in range(1, 4))
    body = (p("Chuvadi Mac test document", bold=True, style="Heading1") + p("A plain paragraph with marker-docx.")
            + p("Bold run", bold=True) + p("Italic run", italic=True)
            + f"<w:tbl><w:tblPr><w:tblBorders><w:top w:val=\"single\"/><w:bottom w:val=\"single\"/></w:tblBorders></w:tblPr>{rows}</w:tbl>"
            + p("After the table."))
    docx(path, body)


def bomb_docx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        head = f'<?xml version="1.0" encoding="UTF-8"?><w:document {W_NS}><w:body><w:p><w:r><w:t>'.encode()
        with z.open("word/document.xml", "w", force_zip64=True) as f:
            f.write(head)
            chunk = b"A" * (1 << 20)
            for _ in range(1024):
                f.write(chunk)
            f.write(b"</w:t></w:r></w:p></w:body></w:document>")


S_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
R_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def xlsx(path, far_cell=False, hidden=False):
    sheet1_rows = (
        '<row r="1"><c r="A1" t="inlineStr"><is><t>Item</t></is></c><c r="B1" t="inlineStr"><is><t>Amount</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t>Date</t></is></c></row>'
        '<row r="2"><c r="A2" t="inlineStr"><is><t>Scan</t></is></c><c r="B2" s="1"><v>1234.5</v></c><c r="C2" s="2"><v>46334</v></c></row>'
        '<row r="3"><c r="A3" t="inlineStr"><is><t>Merged title</t></is></c></row>'
        '<row r="4"><c r="A4"><v>3.14159</v></c><c r="B4"><f>A4*2</f><v>6.28318</v></c></row>')
    if far_cell:
        sheet1_rows += '<row r="1048576"><c r="XFD1048576"><v>1</v></c></row>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   + ('<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' if hidden else '') +
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><workbook {S_NS} {R_NS}><sheets>'
                   '<sheet name="Charges" sheetId="1" r:id="rId1"/><sheet name="Second sheet" sheetId="2" r:id="rId2"/>'
                   + ('<sheet name="Hidden notes" sheetId="3" state="hidden" r:id="rId4"/>' if hidden else '') + '</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
                   '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   + ('<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>' if hidden else '')
                   + '</Relationships>')
        z.writestr("xl/styles.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><styleSheet {S_NS}>'
                   '<numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;₹&quot;#,##0.00"/></numFmts>'
                   '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
                   '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
                   '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
                   '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="164" applyNumberFormat="1"/><xf numFmtId="14" applyNumberFormat="1"/></cellXfs>'
                   '</styleSheet>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><worksheet {S_NS}><sheetData>{sheet1_rows}</sheetData>'
                   '<mergeCells count="1"><mergeCell ref="A3:C3"/></mergeCells></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><worksheet {S_NS}><sheetData>'
                   '<row r="1"><c r="A1" t="inlineStr"><is><t>marker-xlsx sheet two</t></is></c></row></sheetData></worksheet>')
        if hidden:
            z.writestr("xl/worksheets/sheet3.xml",
                       f'<?xml version="1.0" encoding="UTF-8"?><worksheet {S_NS}><sheetData>'
                       '<row r="1"><c r="A1" t="inlineStr"><is><t>marker-hidden sheet</t></is></c></row></sheetData></worksheet>')


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)

    def w(name, data):
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)

    five = five_pages(out)
    w("five-pages.pdf", five)
    w("ஆவணம்-tamil-name.pdf", five)
    w("second.pdf", five_pages(out))
    w("third.pdf", five_pages(out))
    w("annotated.pdf", annotated(out))
    w("noview-print.pdf", noview_print(out))
    w("form.pdf", form(out))
    w("links.pdf", links(out))
    w("heavy-vector.pdf", heavy_vector(out))
    w("many-pages.pdf", many_pages(out))
    w("tamil.pdf", tamil(out))
    w("damaged-truncated.pdf", five[: len(five) // 2])
    i = five.rfind(b"startxref\n")
    w("damaged-badxref.pdf", five[: i] + b"startxref\n999999\n%%EOF\n")
    w("damaged-garbage.pdf", b"%PDF-1.7\n" + os.urandom(20000))
    w("damaged-empty.pdf", b"")
    sample_docx(os.path.join(out, "sample.docx"))
    docx(os.path.join(out, "missing-part.docx"), "", include_document=False)
    bomb_docx(os.path.join(out, "bomb.docx"))
    xlsx(os.path.join(out, "sample.xlsx"))
    xlsx(os.path.join(out, "far-cell.xlsx"), far_cell=True)
    xlsx(os.path.join(out, "formats.xlsx"), hidden=True)
    w("notes.md", "# Notes\n\nSome **bold** and *italic* text, marker-md.\n\n- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n".encode())
    w("notes.txt", "Plain text file, marker-txt.\nSecond line.\n".encode())
    w("page.html", b"<html><body><h1>HTML page</h1><p>marker-html</p><script>document.title='x'</script>"
                   b"<img src='https://example.com/x.png'></body></html>")
    with zipfile.ZipFile(os.path.join(out, "unsupported.zip"), "w") as z:
        z.writestr("readme.txt", "not a document")
    print("fixtures in", out)


if __name__ == "__main__":
    main()
