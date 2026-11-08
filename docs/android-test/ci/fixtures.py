#!/usr/bin/env python3
"""Test documents for the Android Test suites (test tooling only; reportlab + pypdf, never shipped).

    fixtures.py <out-dir>
"""
import io
import os
import random
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions as P
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
WORDS = ("patient admitted with chest pain observed overnight troponin negative echo normal discharged "
         "on aspirin follow up in clinic after two weeks review medication and blood pressure").split()


def text_doc(path, pages, title="Discharge summary", size=A4, seed=1):
    rnd = random.Random(seed)
    c = canvas.Canvas(path, pagesize=size)
    c.setAuthor("Chuvadi Android Test")
    c.setTitle(title)
    w, h = size
    for n in range(1, pages + 1):
        c.setFillColorRGB(0.55, 0.23, 0.11)
        c.rect(0, h - 40, w, 40, fill=1, stroke=0)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(56, h - 90, f"{title} - page {n}")
        c.setFont("Helvetica", 11)
        y = h - 120
        while y > 80:
            c.drawString(56, y, " ".join(rnd.choice(WORDS) for _ in range(12)))
            y -= 16
        if n == 3:
            c.drawString(56, 60, "Unique marker: zephyrine")  # Find target, page 3 only
        c.setFont("Helvetica-Bold", 120)
        c.setFillColorRGB(0.8, 0.8, 0.8)
        c.drawCentredString(w / 2, h / 2 - 40, str(n))
        c.showPage()
    c.save()


def form_doc(path):
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(56, 780, "Patient name:")
    c.acroForm.textfield(name="patient", x=160, y=770, width=250, height=22, borderStyle="inset")
    c.drawString(56, 740, "Consent given:")
    c.acroForm.checkbox(name="consent", x=160, y=735, size=18)
    c.drawString(56, 700, "Ward:")
    c.acroForm.choice(name="ward", x=160, y=690, width=150, height=22, options=["Cardiac", "Oncology", "ICU"],
                      value="Cardiac")
    c.showPage()
    c.save()


def encrypt(src, dst, user="", owner="owner-secret", perms=None):
    r = PdfReader(src)
    w = PdfWriter(clone_from=r)
    kw = {"user_password": user, "owner_password": owner, "algorithm": "AES-256"}
    if perms is not None:
        kw["permissions_flag"] = perms
    w.encrypt(**kw)
    with open(dst, "wb") as f:
        w.write(f)


def image_doc(path, px=6000):
    from PIL import Image
    im = Image.effect_noise((px, px), 60).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    buf.seek(0)
    from reportlab.lib.utils import ImageReader
    c = canvas.Canvas(path, pagesize=A4)
    c.drawImage(ImageReader(buf), 0, 0, A4[0], A4[1])
    c.showPage()
    c.save()


p = lambda n: os.path.join(OUT, n)
text_doc(p("doc-12p.pdf"), 12)
text_doc(p("mixed-landscape.pdf"), 4, title="Wide report", size=landscape(A4), seed=2)
text_doc(p("big-600p.pdf"), 600, title="Large register", seed=3)
form_doc(p("form.pdf"))
encrypt(p("doc-12p.pdf"), p("enc-user.pdf"), user="chuvadi")
no_print = P.all() & ~P.PRINT & ~P.PRINT_TO_REPRESENTATION
encrypt(p("doc-12p.pdf"), p("enc-noprint-owner.pdf"), user="", perms=no_print)
image_doc(p("heavy-image.pdf"))
data = open(p("doc-12p.pdf"), "rb").read()
open(p("damaged-truncated.pdf"), "wb").write(data[: len(data) // 2])
i = data.rfind(b"startxref")
open(p("damaged-xref.pdf"), "wb").write(data[:i] + b"startxref\n999999\n%%EOF\n")
open(p("not-a-pdf.pdf"), "wb").write(os.urandom(40_000))
open(p("empty.pdf"), "wb").write(b"")
for f in sorted(os.listdir(OUT)):
    print(f"{f}\t{os.path.getsize(p(f))}")
