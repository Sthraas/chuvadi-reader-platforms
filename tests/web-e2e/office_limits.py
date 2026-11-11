"""D-137: the portal keeps the strict Word limits (Chuvadi.Docs: 20 MB per part, 64 MB in total).

Builds three .docx files (test tooling only): a normal one, one carrying a 25 MB picture, and a zip bomb
(a small file whose document part unpacks to 100 MB). Uploads each through the portal's file chooser
(Development sign-in) and checks: the normal one shows its text; the other two show "too large to open";
the portal still answers afterwards.

Usage: python3 office_limits.py <portal base> <out folder> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys
import urllib.request
import zipfile

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as

base, out = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
os.makedirs(out, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + detail if detail else ""))


TYPES = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
         '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')


DOC_RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdImg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/></Relationships>')
# An inline picture that the document really shows (so the library has to unpack it).
PICTURE = ('<w:p><w:r><w:drawing><wp:inline><wp:extent cx="914400" cy="914400"/><wp:docPr id="1" name="Picture 1"/>'
           '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr>'
           '<pic:cNvPr id="1" name="image1.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImg"/>'
           '<a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/></a:xfrm>'
           '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def doc(text, padding=0, picture=False):
    body = '<w:p><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % text + (PICTURE if picture else "")
    pad = "<!--" + " " * padding + "-->" if padding else ""
    return ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
            ' xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
            ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
            ' xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<w:body>%s%s</w:body></w:document>' % (body, pad))


def build(path, document, extra=None):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", document)
        for name, data in (extra or {}).items():
            z.writestr(name, data, compress_type=zipfile.ZIP_STORED)


normal = os.path.join(out, "limits-normal.docx")
picture = os.path.join(out, "limits-picture.docx")
bomb = os.path.join(out, "limits-bomb.docx")
build(normal, doc("Chuvadi  limits  check"))
build(picture, doc("big picture", picture=True), {"word/_rels/document.xml.rels": DOC_RELS,
                                                 "word/media/image1.png": b"\x89PNG\r\n\x1a\n" + os.urandom(25 * 1024 * 1024)})
build(bomb, doc("bomb", padding=100 * 1024 * 1024))
check("the zip bomb is small on disk", os.path.getsize(bomb) < 1024 * 1024, "%d bytes" % os.path.getsize(bomb))

with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "limits-" + engine)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def open_file(path):
        if page.url.startswith(base):
            page.wait_for_timeout(2000)  # let the page settle: Firefox reports a send on a closing socket if left mid-update
        page.goto(base + "/")
        page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
        with page.expect_file_chooser(timeout=15000) as fc:
            page.click("nav.leftbar >> text=Upload")  # Home shows "Upload a file" only while nothing is open (D-174)
        fc.value.set_files(path)

    open_file(normal)
    try:
        page.wait_for_function("() => document.body.innerText.includes('Chuvadi  limits  check')", timeout=30000)
        check("a normal Word file opens, double spaces as in the file", True)
    except Exception as ex:  # noqa: BLE001
        check("a normal Word file opens, double spaces as in the file", False, str(ex)[:120])

    for name, path in (("a Word file with a 25 MB picture", picture), ("a Word zip bomb", bomb)):
        open_file(path)
        try:
            page.wait_for_selector("text=too large to open", timeout=60000)
            check(name + " is refused as too large to open", True)
        except Exception as ex:  # noqa: BLE001
            check(name + " is refused as too large to open", False, str(ex)[:120])

    with urllib.request.urlopen(base + "/healthz", timeout=10) as r:
        check("the portal still answers", r.status == 200)
    check("no page errors", not errors, "; ".join(errors[:3]))
    b.close()

sys.exit(0 if all(ok for _, ok, _ in results) else 1)
