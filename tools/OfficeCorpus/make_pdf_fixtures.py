# TESTING ONLY (never shipped; D-139). LIB-1: a PDF as pypdf writes it, with the encryption /P written as an
# unsigned 32-bit number (e.g. 4294965240), which chuvadi-pdf 3.31.x refused. Printing forbidden, copying
# allowed; user password "user", owner password "owner".
import sys, os, pypdf
from pypdf.constants import UserAccessPermissions as P
out = sys.argv[1]
w = pypdf.PdfWriter()
w.add_blank_page(width=595, height=842)
w.add_metadata({'/Title': 'pypdf unsigned P'})
# Every bit set (as the spec asks for the reserved high bits) except print (bit 3) and high-quality print (bit 12):
# 0xFFFFF7FB = 4294965243, written by pypdf as an unsigned number.
perms = 0xFFFFFFFF & ~(1 << 2) & ~(1 << 11)
w.encrypt(user_password='user', owner_password='owner', permissions_flag=perms, algorithm='AES-256')
with open(os.path.join(out, 'pypdf-unsigned-p.pdf'), 'wb') as f: w.write(f)

# D-160: a 600 x 800 page whose CropBox [50 200 450 700] is inherited from the page tree (/Pages), not on the page.
# "INSIDE" is in the shown box, "OUTSIDE" in the part it hides.
import io
from reportlab.pdfgen import canvas
from pypdf.generic import NameObject, ArrayObject, FloatObject
buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(600, 800)); c.setFont('Helvetica-Bold', 24)
c.drawString(120, 590, 'INSIDE'); c.drawString(10, 770, 'OUTSIDE'); c.showPage(); c.save()
w = pypdf.PdfWriter(); w.append(pypdf.PdfReader(io.BytesIO(buf.getvalue())))
pages = w._root_object['/Pages'].get_object()
pages[NameObject('/CropBox')] = ArrayObject([FloatObject(50), FloatObject(200), FloatObject(450), FloatObject(700)])
for kid in pages['/Kids']:
    if '/CropBox' in kid.get_object(): del kid.get_object()['/CropBox']
with open(os.path.join(out, 'inherited-cropbox.pdf'), 'wb') as f: w.write(f)
