import helpers as h
from lt_base import *
def spool_after(t0): return sorted([f for f in glob.glob("/var/spool/cups/d*") if os.path.getmtime(f)>t0], key=os.path.getmtime)
def info(p):
    fonts=subprocess.run(["pdffonts",p],capture_output=True,text=True).stdout.strip().splitlines()[2:]
    imgs=subprocess.run(["pdfimages","-list",p],capture_output=True,text=True).stdout.strip().splitlines()[2:]
    pi=h.pdfinfo(p); txt=subprocess.run(["pdftotext",p,"-"],capture_output=True,text=True).stdout
    return f"pages={pi.get('Pages')} size={pi.get('Page size')} producer={pi.get('Producer','-')!r} fonts={[f.split()[0] for f in fonts]} images={len(imgs)} text={txt.strip()[:60]!r}"
import sys as _s
files=_s.argv[1:]
for n,f in enumerate(files):
  a=App(APP, EV+"/print", display=":%d"%(70+n)); h.bind(a); a.start_display()
  try:
        a.launch(f); time.sleep(4); h.PDF=f
        t0=time.time(); h.focus_main(); a.key("ctrl+p"); time.sleep(1.2)
        a.click("section[aria-label=Print] button.primary")
        w=a.wait(lambda: [x for x in h.native_windows() if x[1].startswith("Print")],15,"dialog")[0][0]
        subprocess.run(["xdotool","windowactivate","--sync",w],env=a.env,capture_output=True); time.sleep(3); a.key("Return")
        out=a.wait(lambda: h.cups_pdfs(t0),120,"cups output"); out=sorted(out,key=os.path.getmtime)[-1]; time.sleep(2)
        sp=spool_after(t0)
        print("SOURCE  ", os.path.basename(f), info(f))
        for s in sp:
            kind=subprocess.run(["file","-b",s],capture_output=True,text=True).stdout.strip()
            same=open(s,'rb').read()==open(f,'rb').read()
            print("SUBMITTED", s, kind[:40], "byte-identical to source:", same, info(s) if kind.startswith("PDF") else "")
        print("CUPS OUT", os.path.basename(out), info(out))
        subprocess.run(["cp",out,EV+"/print/out-"+os.path.basename(f)])
        if sp: subprocess.run(["cp",sp[0],EV+"/print/submitted-"+os.path.basename(f)])
        a.shot("printed-"+os.path.basename(f))
  finally: a.stop()
