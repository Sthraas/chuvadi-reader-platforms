import helpers as h
from lt_base import *
f="/home/claude/rx/owner-only-noprint.pdf"
a=App(APP, EV+"/noprint", display=":75"); h.bind(a); a.start_display()
try:
    a.launch(f); time.sleep(4); t0=time.time(); jobs0=len(glob.glob("/var/spool/cups/d*"))
    print("opened:", tabs(a), "| body says:", a.js("return document.body.innerText.includes('Could not open')"))
    h.focus_main(); a.key("ctrl+p"); time.sleep(1.2); a.shot("card")
    a.click("section[aria-label=Print] button.primary"); time.sleep(4)
    print("refusal shown:", a.js("return document.body.innerText.includes(\"permissions don't allow printing\")"))
    print("print dialog opened:", bool([x for x in h.native_windows() if x[1].startswith("Print")]))
    print("new CUPS jobs:", len(glob.glob("/var/spool/cups/d*"))-jobs0, "| new cups-pdf files:", len(h.cups_pdfs(t0)))
    a.shot("after")
finally: a.stop()
