#!/usr/bin/env python3
"""Files for Foundation's parse-process bench (tools/ParseProcessPrototype), test-only, never shipped; standard library only.

  tools/linux/make-parse-bench-files.py <folder>

Foundation's own run used files that are not in the repo, so this makes a set of the same kinds, the same on every
machine (fixed seeds), so the Linux numbers can be compared run to run (here, the x64 and ARM64 CI runners):

  a-text-12p.pdf    12 A4 pages of running text (Helvetica): an ordinary letter or report; named to come first,
                    as the bench takes the first PDF for its start-up and recovery timings
  grid-400p.pdf     400 A4 pages, a light vector grid and a page number: a long scanned-style file without images
  image-20p.pdf     20 pages, each with a 1200 x 1600 RGB image: a scan
  cad-5s.pdf        5 A1 sheets of 10,000 strokes (make-heavy-pdfs.py's cad.pdf): B-27's kind of drawing
  bomb-flate-560MB.pdf  one page whose content stream inflates to 560 MB of zeros (the bench keeps bomb* apart)
  long-2000p.docx   2,000 paragraphs of text
  discharge.docx, layout.xlsx   copied from the repo's test fixtures
  rows-20000.xlsx   20,000 rows x 8 columns of numbers and text (shared strings)
  probes/deep-page-tree.pdf          a page tree 2,000 levels deep (one page at the bottom)
  probes/nested-array-in-catalog.pdf a catalog entry holding an array nested 200,001 levels deep
"""
import importlib.util, os, random, shutil, sys, zipfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
spec = importlib.util.spec_from_file_location("heavy", os.path.join(HERE, "make-heavy-pdfs.py"))
heavy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(heavy)
WORDS = ("patient report clinical oncology dose plan review signed history imaging scan result follow normal "
         "within limits advised treatment course weekly fraction target volume organ risk margin").split()


def text_page(n, rnd):
    lines = [b"BT /F1 11 Tf 56 790 Td 14 TL"]
    for _ in range(52):
        words = " ".join(rnd.choice(WORDS) for _ in range(rnd.randint(9, 13)))
        lines.append(b"(%s) '" % words.encode())
    lines.append(b"ET BT /F1 9 Tf 290 30 Td (Page %d) Tj ET" % n)
    return 595, 842, b"\n".join(lines)


def raw_pdf(path, objects):
    """objects: bodies of objects 1..n; object 1 is the catalog."""
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    with open(path, "wb") as f:
        f.write(out)


def bomb(path, megabytes=560):
    comp = zlib.compressobj(9)
    chunk = b"\0" * (1 << 20)
    data = b"".join(comp.compress(chunk) for _ in range(megabytes)) + comp.flush()
    raw_pdf(path, [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream",
    ])


def deep_page_tree(path, depth=2000):
    # 1 catalog, 2..depth+1 Pages nodes each holding the next, then the page.
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    for i in range(depth):
        me, kid = 2 + i, 3 + i
        parent = b"" if i == 0 else b" /Parent %d 0 R" % (me - 1)
        objs.append(b"<< /Type /Pages /Kids [%d 0 R] /Count 1%s >>" % (kid, parent))
    page = 2 + depth
    objs.append(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] >>" % (page - 1))
    raw_pdf(path, objs)


def nested_array(path, depth=200_001):
    raw_pdf(path, [
        b"<< /Type /Catalog /Pages 2 0 R /Deep " + b"[" * depth + b"]" * depth + b" >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>",
    ])


def docx(path, paragraphs, rnd):
    body = "".join("<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % " ".join(rnd.choice(WORDS) for _ in range(40))
                   for _ in range(paragraphs))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>%s</w:body></w:document>' % body)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", doc)


def xlsx(path, rows, rnd):
    strings = WORDS
    def col(c):
        return "ABCDEFGH"[c]
    out = []
    for r in range(1, rows + 1):
        cells = []
        for c in range(8):
            ref = "%s%d" % (col(c), r)
            if c % 3 == 2:
                cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, rnd.randrange(len(strings))))
            else:
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, round(rnd.uniform(0, 10000), 2)))
        out.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook %s %s><sheets><sheet name="Data" sheetId="1" r:id="r1"/></sheets></workbook>' % (ns, rel))
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '<Relationship Id="r2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", '<?xml version="1.0" encoding="UTF-8"?><sst %s count="%d" uniqueCount="%d">%s</sst>'
                   % (ns, len(strings), len(strings), "".join("<si><t>%s</t></si>" % s for s in strings)))
        z.writestr("xl/worksheets/sheet1.xml", '<?xml version="1.0" encoding="UTF-8"?><worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, "".join(out)))


if __name__ == "__main__":
    folder = sys.argv[1]
    os.makedirs(os.path.join(folder, "probes"), exist_ok=True)
    rnd = random.Random(198)
    heavy.write_pdf(os.path.join(folder, "a-text-12p.pdf"), [text_page(n, rnd) for n in range(1, 13)])
    heavy.write_pdf(os.path.join(folder, "grid-400p.pdf"), [heavy.big_page(n) for n in range(1, 401)])
    w, h = 1200, 1600
    pixels = bytes((x * 7 + y * 3) % 256 for y in range(h) for x in range(0, w * 3))
    img_page = lambda n: (595, 842, b"q 595 0 0 842 0 0 cm /Im1 Do Q BT /F1 12 Tf 40 40 Td (Scan %d) Tj ET" % n)
    heavy.write_pdf(os.path.join(folder, "image-20p.pdf"), [img_page(n) for n in range(1, 21)], image=(w, h, b"DeviceRGB", pixels))
    heavy.write_pdf(os.path.join(folder, "cad-5s.pdf"), [heavy.cad_page(n) for n in range(1, 6)])
    bomb(os.path.join(folder, "bomb-flate-560MB.pdf"))
    docx(os.path.join(folder, "long-2000p.docx"), 2000, rnd)
    xlsx(os.path.join(folder, "rows-20000.xlsx"), 20000, rnd)
    for name in ("discharge.docx", "layout.xlsx"):
        shutil.copyfile(os.path.join(REPO, "tests", "ChuvadiReader.Tests", "Fixtures", "Office", name), os.path.join(folder, name))
    deep_page_tree(os.path.join(folder, "probes", "deep-page-tree.pdf"))
    nested_array(os.path.join(folder, "probes", "nested-array-in-catalog.pdf"))
    for root, _, files in os.walk(folder):
        for name in sorted(files):
            print(os.path.relpath(os.path.join(root, name), folder), os.path.getsize(os.path.join(root, name)) // 1024, "KB")
