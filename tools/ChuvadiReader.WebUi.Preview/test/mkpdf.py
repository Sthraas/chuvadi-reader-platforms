import sys
def pdf(path, pages):
    objs=[]
    def add(s): objs.append(s); return len(objs)
    font=add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids=[]; pages_id_placeholder=None
    contents=[]
    for i in range(pages):
        lines=["BT /F1 18 Tf 60 780 Td (Discharge summary - page %d) Tj ET"%(i+1)]
        y=740
        for k in range(30):
            lines.append("BT /F1 10 Tf 60 %d Td (Line %d of the sample text for the preview document.) Tj ET"%(y,k+1)); y-=20
        s="\n".join(lines)
        contents.append(add("<< /Length %d >>\nstream\n%s\nendstream"%(len(s),s)))
    pages_id=len(objs)+pages+1
    for c in contents:
        kids.append(add("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"%(pages_id,font,c)))
    p=add("<< /Type /Pages /Kids [%s] /Count %d >>"%(" ".join("%d 0 R"%k for k in kids),pages)); assert p==pages_id
    cat=add("<< /Type /Catalog /Pages %d 0 R >>"%p)
    out=b"%PDF-1.4\n"; offs=[]
    for i,o in enumerate(objs):
        offs.append(len(out)); out+=("%d 0 obj\n%s\nendobj\n"%(i+1,o)).encode()
    x=len(out)
    out+=("xref\n0 %d\n0000000000 65535 f \n"%(len(objs)+1)).encode()
    for o in offs: out+=("%010d 00000 n \n"%o).encode()
    out+=("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"%(len(objs)+1,cat,x)).encode()
    open(path,"wb").write(out)
pdf(sys.argv[1], int(sys.argv[2]))
