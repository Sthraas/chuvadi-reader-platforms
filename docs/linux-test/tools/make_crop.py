# TESTING ONLY (D-160): crop.pdf, four A4 pages. A red square sits inside the crop's bottom-left corner, a blue one inside
# its top-right corner, and a green block lies wholly OUTSIDE the crop.
#  1: CropBox [50 200 450 700] (400 x 500)   2: the same + /Rotate 90   3: no CropBox (control)   4: CropBox larger than MediaBox
import sys, io, pikepdf
from reportlab.pdfgen import canvas
buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(595, 842))
for n in range(4):
    c.setFillColorRGB(0, 0.6, 0); c.rect(470, 20, 100, 150, stroke=0, fill=1)        # outside the crop
    c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 14); c.drawString(475, 180, "OUTSIDE")
    c.setFillColorRGB(1, 0, 0); c.rect(50, 200, 40, 40, stroke=0, fill=1)            # crop bottom-left
    c.setFillColorRGB(0, 0, 1); c.rect(410, 660, 40, 40, stroke=0, fill=1)           # crop top-right
    c.setFillColorRGB(0, 0, 0); c.drawString(200, 450, f"INSIDE page {n+1}")
    c.showPage()
c.save(); buf.seek(0); pdf = pikepdf.open(buf)
pdf.pages[0].CropBox = [50, 200, 450, 700]
pdf.pages[1].CropBox = [50, 200, 450, 700]; pdf.pages[1].Rotate = 90
pdf.pages[3].CropBox = [-100, -100, 700, 900]
pdf.save(sys.argv[1])
