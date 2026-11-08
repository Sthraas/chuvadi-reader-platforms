import helpers as h
from lt_base import *
a=App(APP, EV+"/split2", display=":91"); h.bind(a); a.start_display()
def btn(t): return a.js(f"var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.innerText.trim().startsWith({json.dumps(t)})); if(!b) return false; b.click(); return true")
def pdfs(d): return sorted(glob.glob(d+"/*.pdf"))
def desc(p): 
    t=subprocess.run(["pdftotext",p,"-"],capture_output=True,text=True).stdout
    return f"{os.path.basename(p)}: {h.pdfinfo(p).get('Pages')}p, 'Page N' seen={[n for n in range(1,6) if f'Page {n}' in t]}"
OUT=os.path.join(a.home,"Documents","split-out"); os.makedirs(OUT,exist_ok=True)
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    a.send("invoke doc.split"); time.sleep(3); btn("Use current"); time.sleep(2)
    print("split to folder:", btn("Split to folder")); time.sleep(2)
    print("dialogs:", h.native_windows())
    w=h.native_windows()
    title=w[0][1] if w else "Select"
    h.file_dialog(title.split()[0], OUT); time.sleep(1)
    # folder chooser may need an extra confirm button: press Return again if still open
    if h.native_windows(): a.key("Return"); time.sleep(2)
    a.wait(lambda: len(pdfs(OUT))>=5, 30, "split output")
    time.sleep(2); a.shot("split-done"); print("toasts:", toasts(a))
    for p in pdfs(OUT): print("  ", desc(p))
    # extract range 2-4
    print("radio2:", a.js("var r=document.querySelectorAll('input[type=radio]'); if(r.length<2) return false; r[1].click(); return true")); time.sleep(1.5)
    print("inputs now:", a.js("return [...document.querySelectorAll('input')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||e.placeholder||e.name)+'|'+e.type+'|'+e.value)"))
    a.js("var n=[...document.querySelectorAll('input[type=number]')].filter(e=>e.offsetParent); var set=(e,v)=>{e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));}; set(n[0],'2'); set(n[1],'4');"); time.sleep(1)
    a.shot("extract-mode")
    OUTX=os.path.join(a.home,"Documents","extract-2-4.pdf")
    print("extract:", btn("Extract range")); time.sleep(2)
    w=h.native_windows(); print("dialogs:", w)
    h.file_dialog(w[0][1].split()[0], OUTX)
    a.wait(lambda: os.path.exists(OUTX) and os.path.getsize(OUTX)>0, 30, "extract output"); time.sleep(1)
    print("  ", desc(OUTX)); a.shot("extract-done")
finally: a.stop()
