import helpers as h
from lt_base import *
a=App(APP, EV+"/merge", display=":92"); h.bind(a); a.start_display()
def btn(t): return a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.innerText.trim().startsWith({json.dumps(t)})); if(!b) return false; b.click(); return true")
def vis(): return [b for b in a.js("return [...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>b.innerText.trim().replace(/\\s+/g,' '))") if b][12:]
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5); a.send("open /usr/share/cups/data/default-testpage.pdf"); time.sleep(4)
    a.send("invoke doc.merge"); time.sleep(3); a.shot("merge-card")
    print("add open:", btn("Add open documents")); time.sleep(2); a.shot("merge-list")
    print("list:", a.js("return document.body.innerText.replace(/\\s+/g,' ').slice(160,600)"))
    OUTM=os.path.join(a.home,"Documents","merged.pdf")
    print("merge:", btn("Merge & Save")); time.sleep(2)
    w=h.native_windows(); print("dialogs:", w); h.file_dialog(w[0][1].split()[0], OUTM)
    a.wait(lambda: os.path.exists(OUTM) and os.path.getsize(OUTM)>0, 30, "merged"); time.sleep(1)
    t=subprocess.run(["pdftotext",OUTM,"-"],capture_output=True,text=True).stdout.split("\f")
    print("merged pages:", h.pdfinfo(OUTM).get("Pages"), [p.strip().split("\n")[0][:22] for p in t if p.strip()])
    print("source fonts kept:", subprocess.run(["pdffonts",OUTM],capture_output=True,text=True).stdout.split("\n")[2:5])
finally: a.stop()
