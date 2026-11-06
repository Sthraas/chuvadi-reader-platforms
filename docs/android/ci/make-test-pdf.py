#!/usr/bin/env python3
"""Writes a small multi-page PDF for the emulator gesture tests (CI only, standard library only).

Each A4 page carries a large page number and a coloured band, so screenshots show which page is on
screen and Arrange shows six distinct cards.

    make-test-pdf.py <out.pdf> [pages=6]
"""
import sys

out = sys.argv[1]
count = int(sys.argv[2]) if len(sys.argv) > 2 else 6
colours = [(0.80, 0.30, 0.20), (0.20, 0.55, 0.35), (0.20, 0.35, 0.70),
           (0.75, 0.60, 0.15), (0.50, 0.25, 0.60), (0.15, 0.55, 0.60)]

objects = []  # index i holds object i+1


def add(body: bytes) -> int:
    objects.append(body)
    return len(objects)


font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
pages_id = len(objects) + 1 + 2 * count  # reserved after the page/content pairs
kids = []
for n in range(1, count + 1):
    r, g, b = colours[(n - 1) % len(colours)]
    stream = (
        f"{r:.2f} {g:.2f} {b:.2f} rg 0 742 595 100 re f\n"
        f"BT /F1 220 Tf 0.15 0.12 0.10 rg {200 if n < 10 else 110} 360 Td ({n}) Tj ET\n"
        f"BT /F1 28 Tf 0.15 0.12 0.10 rg 60 120 Td (Chuvadi test page {n} of {count}) Tj ET\n"
    ).encode()
    content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    page = add(
        b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Contents %d 0 R "
        b"/Resources << /Font << /F1 %d 0 R >> >> >>" % (pages_id, content, font))
    kids.append(page)

assert len(objects) + 1 == pages_id
add(b"<< /Type /Pages /Count %d /Kids [%s] >>" % (count, b" ".join(b"%d 0 R" % k for k in kids)))
catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

data = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
offsets = []
for i, body in enumerate(objects, start=1):
    offsets.append(len(data))
    data += b"%d 0 obj\n" % i + body + b"\nendobj\n"
xref = len(data)
data += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
for off in offsets:
    data += b"%010d 00000 n \n" % off
data += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, catalog, xref)

with open(out, "wb") as f:
    f.write(data)
print(f"wrote {out}: {count} pages, {len(data)} bytes")
