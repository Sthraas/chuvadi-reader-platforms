import helpers as h
from lt_base import *
PDF="/home/claude/lt/five-pages.pdf"; h.PDF=PDF
a=App(APP, EV+"/redact", display=":63"); h.bind(a); a.start_display()
OUTF=os.path.join(a.home,"Documents","redacted.pdf")
def btn(t): return a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=={json.dumps(t)} && b.offsetParent); if(!b) return false; b.click(); return true")
try:
    a.launch(PDF); time.sleep(3); a.click(".lb-mode",3); time.sleep(2)
    h.click_label(".srail","Find & redact"); time.sleep(1.5)
    h.type_into("input[placeholder='Find text…']", "print test"); time.sleep(0.5)
    btn("Find"); time.sleep(3)
    print("redact all:", btn("Redact all matches")); time.sleep(2)
    print("status:", a.text(".statusbar").replace("\n"," ")); a.shot("boxes")
    print("save:", btn("Save redacted copy")); time.sleep(2); a.shot("after-save-click")
    print("dialogs:", h.native_windows())
    h.file_dialog("Save", OUTF)
    a.wait(lambda: os.path.exists(OUTF) and os.path.getsize(OUTF)>0, 30, "redacted written")
    time.sleep(2); a.shot("saved"); print("toasts:", toasts(a))
    t=subprocess.run(["pdftotext",OUTF,"-"],capture_output=True,text=True).stdout
    print("PAGES", h.pdfinfo(OUTF).get("Pages"), "| 'print test' remaining:", t.count("print test"), "| 'Chuvadi Linux' remaining:", t.count("Chuvadi Linux"), "| raw bytes contain 'print test':", open(OUTF,'rb').read().count(b"print test"))
    subprocess.run(["cp",OUTF,EV+"/redact/redacted.pdf"])
finally: a.stop()
