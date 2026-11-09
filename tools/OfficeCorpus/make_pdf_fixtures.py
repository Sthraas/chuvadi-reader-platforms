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
