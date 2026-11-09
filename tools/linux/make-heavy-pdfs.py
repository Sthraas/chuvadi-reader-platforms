#!/usr/bin/env python3
"""Heavy PDFs for the render tests (test-only, never shipped; standard library only).

  tools/linux/make-heavy-pdfs.py <folder>

  big.pdf — 400 A4 pages, each with a large page number and a light vector grid: for paging fast.
  cad.pdf — 5 A1 sheets, each with ~120,000 stroked line segments and labels: a stand-in for a vector CAD
            drawing (B-27's kind of file; no real drawing is used or committed).
"""
import os, random, sys, zlib


def write_pdf(path, pages, image=None):
    """pages: list of (width, height, content bytes). One Helvetica font; content streams Flate-compressed.
    image: optional (width, height, colour space, raw bytes), placed as /Im1 on every page."""
    objs = []  # body of objects 1..n

    def add(body):
        objs.append(body)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    xobj = b""
    if image:
        iw, ih, cs, raw = image
        data = zlib.compress(raw, 1)
        im = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /%s /BitsPerComponent 8 "
                 b"/Filter /FlateDecode /Length %d >>\nstream\n" % (iw, ih, cs, len(data)) + data + b"\nendstream")
        xobj = b" /XObject << /Im1 %d 0 R >>" % im
    pages_id = len(objs) + 1 + 2 * len(pages)  # after every content + page object
    kids = []
    for w, h, content in pages:
        data = zlib.compress(content, 6)
        c = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
        p = add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 %d 0 R >>%s >> /Contents %d 0 R >>"
                % (pages_id, w, h, font, xobj, c))
        kids.append(p)
    assert add(b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))) == pages_id
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
    with open(path, "wb") as f:
        f.write(out)


def big_page(n):
    w, h = 595, 842
    s = [b"0.85 G 0.5 w"]
    for x in range(40, w - 39, 30):
        s.append(b"%d 40 m %d %d l" % (x, x, h - 40))
    for y in range(40, h - 39, 30):
        s.append(b"40 %d m %d %d l" % (y, w - 40, y))
    s.append(b"S 0 g BT /F1 64 Tf 150 420 Td (Page %d) Tj ET" % n)
    return w, h, b"\n".join(s)


def cad_page(n, segments=120_000):
    w, h = 2384, 1684  # A1 landscape, points
    rnd = random.Random(n)
    s = [b"0.2 w 0 0 0.6 RG"]
    for i in range(segments):
        x, y = rnd.uniform(30, w - 30), rnd.uniform(30, h - 30)
        dx, dy = rnd.uniform(-40, 40), rnd.uniform(-40, 40)
        s.append(b"%.2f %.2f m %.2f %.2f l" % (x, y, x + dx, y + dy))
        if i % 500 == 499:
            s.append(b"S")
    s.append(b"S 0 g BT /F1 48 Tf 80 80 Td (Sheet %d of 5 - generated vector test drawing) Tj ET" % n)
    return w, h, b"\n".join(s)


if __name__ == "__main__":
    folder = sys.argv[1]
    os.makedirs(folder, exist_ok=True)
    write_pdf(os.path.join(folder, "big.pdf"), [big_page(n) for n in range(1, 401)])
    write_pdf(os.path.join(folder, "cad.pdf"), [cad_page(n) for n in range(1, 6)])
    for name in ("big.pdf", "cad.pdf"):
        print(name, os.path.getsize(os.path.join(folder, name)) // 1024, "KB")
