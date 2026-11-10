"""Small PDFs the browser tests build for themselves (test tooling only)."""


def large_format_pdf(path):
    """One 1300 x 1300 pt page of lines: larger than A2, so the Reader draws it as an image (D-158)."""
    content = b"".join(b"%d 0 m %d 1300 l " % (x, x) for x in range(0, 1300, 20)) + b"S"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1300 1300] /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"]
    data, offsets = b"%PDF-1.7\n", []
    for n, o in enumerate(objs, 1):
        offsets.append(len(data))
        data += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    data += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    open(path, "wb").write(data)
