"""Test corpus for the Web Test chat (test tooling only, never shipped).
Usage: python3 make_corpus.py <out folder>
Writes ordinary, protected, large and hostile documents used by the probes and browser runs."""
import io, os, sys, zipfile, random
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions as P
import docx, openpyxl
from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
J = lambda n: os.path.join(out, n)

def text_pdf(path, pages, word="chuvadi"):
    c = canvas.Canvas(path, pagesize=A4)
    for i in range(pages):
        c.setFont("Helvetica-Bold", 28); c.drawString(72, 760, f"Page {i+1} of {pages}")
        c.setFont("Helvetica", 12)
        for l in range(40):
            c.drawString(72, 720 - l * 16, f"Line {l+1}: the quick brown fox {word} jumps over the lazy dog {i+1}.{l+1}")
        c.showPage()
    c.save()

text_pdf(J("text-13.pdf"), 13)
text_pdf(J("text-3.pdf"), 3, "merge")
text_pdf(J("text-500.pdf"), 500)

def protect(src, dst, user="", owner="owner-secret", perms=None):
    w = PdfWriter(clone_from=src)
    kw = {}
    if perms is not None: kw["permissions_flag"] = perms
    w.encrypt(user_password=user, owner_password=owner, algorithm="AES-256", **kw)
    w.write(dst)

all_but_print = P.all() & ~P.PRINT & ~P.PRINT_TO_REPRESENTATION
protect(J("text-3.pdf"), J("no-print.pdf"), perms=all_but_print)
protect(J("text-3.pdf"), J("user-password.pdf"), user="open-me")

# A form PDF
c = canvas.Canvas(J("form.pdf"), pagesize=A4)
c.drawString(72, 760, "Name:"); c.acroForm.textfield(name="name", x=140, y=745, width=250, height=22)
c.drawString(72, 700, "Agree:"); c.acroForm.checkbox(name="agree", x=140, y=690, size=18)
c.save()

# Scanned-like heavy PDF: 40 pages of noisy full-page images (~ tens of MB)
rnd = random.Random(1)
c = canvas.Canvas(J("scan-40.pdf"), pagesize=A4)
for i in range(40):
    img = Image.effect_noise((1240, 1754), 60 + i).convert("RGB")
    b = io.BytesIO(); img.save(b, "JPEG", quality=92); b.seek(0)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(b), 0, 0, *A4); c.drawString(40, 40, f"scan {i+1}"); c.showPage()
c.save()

# Office files
d = docx.Document(); d.add_heading("Chuvadi docx test", 0)
for i in range(30): d.add_paragraph(f"Paragraph {i+1}: chuvadi word document line.")
d.save(J("doc.docx"))
wb = openpyxl.Workbook(); ws = wb.active
for r in range(1, 201): ws.append([r, f"row {r}", r * 1.5])
wb.save(J("sheet.xlsx"))

# ---- hostile / damaged ----
open(J("fake.pdf"), "wb").write(b"this is not a pdf at all")
open(J("pdf-as-docx.docx"), "wb").write(open(J("text-3.pdf"), "rb").read())
open(J("docx-as-pdf.pdf"), "wb").write(open(J("doc.docx"), "rb").read())
open(J("empty.pdf"), "wb").write(b"")
data = open(J("text-3.pdf"), "rb").read()
open(J("truncated.pdf"), "wb").write(data[: len(data) // 2])
open(J("garbage-after-header.pdf"), "wb").write(b"%PDF-1.7\n" + bytes(rnd.getrandbits(8) for _ in range(200000)))
# deeply nested arrays
nest = b"[" * 200000 + b"]" * 200000
open(J("deep-nest.pdf"), "wb").write(b"%PDF-1.4\n1 0 obj\n" + nest + b"\nendobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
# reference loop pages tree
loop = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Pages/Kids[2 0 R]/Count 1/Parent 2 0 R>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
open(J("pages-loop.pdf"), "wb").write(loop)
# Flate bomb: 1 GB of zeros in a content stream (compresses to ~1 MB)
import zlib
co = zlib.compressobj(9)
chunk = b"\0" * (16 * 1024 * 1024)
bomb = b"".join(co.compress(chunk) for _ in range(64)) + co.flush()
body = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length " + str(len(bomb)).encode() + b"/Filter/FlateDecode>>stream\n" + bomb + b"\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
open(J("flate-bomb.pdf"), "wb").write(body)
# zip bomb docx: document.xml of 2 GB declared via repeated zeros
with zipfile.ZipFile(J("zip-bomb.docx"), "w", zipfile.ZIP_DEFLATED) as z:
    src = zipfile.ZipFile(J("doc.docx"))
    for n in src.namelist():
        if n != "word/document.xml": z.writestr(n, src.read(n))
    with z.open("word/document.xml", "w", force_zip64=True) as f:
        for _ in range(128): f.write(b" " * (16 * 1024 * 1024))
with zipfile.ZipFile(J("zip-bomb.xlsx"), "w", zipfile.ZIP_DEFLATED) as z:
    src = zipfile.ZipFile(J("sheet.xlsx"))
    for n in src.namelist():
        if n != "xl/worksheets/sheet1.xml": z.writestr(n, src.read(n))
    with z.open("xl/worksheets/sheet1.xml", "w", force_zip64=True) as f:
        for _ in range(128): f.write(b" " * (16 * 1024 * 1024))
# 210 MB file just over the 200 MB limit (valid header)
with open(J("over-limit.pdf"), "wb") as f:
    f.write(data); f.write(b"%" * (210 * 1024 * 1024))
print("corpus in", out)
for n in sorted(os.listdir(out)): print(f"{os.path.getsize(J(n)):>12}  {n}")
