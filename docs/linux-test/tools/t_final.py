import helpers as h, re
from lt_base import *
def txt(): return a.js("return document.body.innerText.replace(/\\s+/g,' ')") or ''
def cancel(): return a.js("return [...document.querySelectorAll('button')].some(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim()))")
def closeall(): a.js("[...document.querySelectorAll('.rtab')].forEach(t=>{var x=t.querySelector('button'); if(x) x.click()})"); time.sleep(1)
def card_title(): return a.js("var c=document.querySelector('section[aria-label=Print]'); return c?(c.title||'')+' | locked='+(!!c.querySelector('.locked,[aria-disabled=true]')):'no card'")
def unlock(path,pw):
    a.send("open "+path); time.sleep(3)
    h.type_into("input[type=password]",pw); a.key("Return"); time.sleep(5)
a=App(APP, EV+"/final", display=":61"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(3)
    for f in ["slow.pdf","slow.xlsx","slow.docx"]:
        t0=time.time(); a.send("open /tmp/chvd-stall/"+f, timeout=10); op=cn=None
        while time.time()-t0<16:
            if op is None and 'Opening' in txt(): op=round(time.time()-t0,1)
            if cancel(): cn=round(time.time()-t0,1); break
            time.sleep(0.3)
        a.shot("stall-"+f)
        a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim())); if(b) b.click()"); time.sleep(2)
        gone=f not in tabs(a)
        try: a.send("open /home/claude/lt/five-pages.pdf", timeout=15); time.sleep(3); nxt='five-pages.pdf' in tabs(a)
        except Exception: nxt="BLOCKED"
        print(f"B-24/B-08b {f}: Opening at {op}s | Cancel at {cn}s | tab closed by Cancel: {gone} | next open: {nxt}", flush=True); closeall()
    for f in ["/home/claude/rx/notzip.xlsx","/home/claude/rx/missing-part.docx","/home/claude/rx/badxref.pdf"]:
        a.send("open "+f); time.sleep(4)
        d=a.js("var s=[...document.querySelectorAll('details,summary,button')].find(e=>e.offsetParent&&/^Details/i.test(e.innerText.trim())); if(!s) return 'no Details'; s.click(); return 'Details ok'"); time.sleep(1)
        msg=[s for s in re.split(r'(?<=[.!?]) ',txt()) if re.search(r"couldn|damag|can't|cannot|read this",s,re.I)][:2]
        det=a.js("return [...document.querySelectorAll('details')].filter(e=>e.open).map(e=>e.innerText.replace(/\\s+/g,' ').slice(0,140))")
        print(f"B-25 {os.path.basename(f)}: {msg} | {d} | {det}", flush=True); a.shot("b25-"+os.path.basename(f)); closeall()
    jobs0=len(glob.glob("/var/spool/cups/d*"))
    unlock("/home/claude/rx/both-pw-noprint.pdf","u-pass"); print("OWNER user-pw tab:", tabs(a), "| print card:", card_title(), flush=True)
    h.focus_main(); a.key("ctrl+p"); time.sleep(1.2); a.click("section[aria-label=Print] button.primary"); time.sleep(4)
    print("OWNER user-pw: dialog opened:", bool([x for x in h.native_windows() if x[1].startswith("Print")]), "| new CUPS jobs:", len(glob.glob("/var/spool/cups/d*"))-jobs0, "| refusal shown:", "allow printing" in txt(), flush=True)
    a.key("Escape"); time.sleep(1); closeall()
    t0=time.time(); unlock("/home/claude/rx/both-pw-noprint-2.pdf","o-pass"); print("OWNER owner-pw tab:", tabs(a), "| print card:", card_title(), flush=True)
    h.focus_main(); a.key("ctrl+p"); time.sleep(1.2); a.click("section[aria-label=Print] button.primary")
    w=a.wait(lambda: [x for x in h.native_windows() if x[1].startswith("Print")],15,"dialog")[0][0]
    subprocess.run(["xdotool","windowactivate","--sync",w],env=a.env,capture_output=True); time.sleep(3); a.key("Return")
    out=a.wait(lambda: h.cups_pdfs(t0),90,"cups"); out=sorted(out,key=os.path.getmtime)[-1]; time.sleep(3)
    sp=sorted([f for f in glob.glob("/var/spool/cups/d*") if os.path.getmtime(f)>t0],key=os.path.getmtime)
    sub=sp[0] if sp else None
    enc=subprocess.run(["qpdf","--show-encryption",sub],capture_output=True,text=True).stdout.split("\n")[0] if sub else "-"
    same=open(sub,'rb').read()==open("/home/claude/rx/both-pw-noprint-2.pdf",'rb').read() if sub else None
    print(f"OWNER owner-pw printed: CUPS out pages {h.pdfinfo(out).get('Pages')}, fonts {len(subprocess.run(['pdffonts',out],capture_output=True,text=True).stdout.splitlines())-2}, images {len(subprocess.run(['pdfimages','-list',out],capture_output=True,text=True).stdout.splitlines())-2} | submitted byte-identical to source: {same} | submitted encryption: {enc}", flush=True)
    a.shot("owner-printed"); closeall()
    a.send("open /home/claude/exact/exact.xlsx"); time.sleep(5)
    print("REG B-26 formats:", a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>e.textContent).filter(t=>/1234|1,234|0\\.125|12\\.5|45000|2023|E\\+19|₹/.test(t))"), flush=True)
finally: a.stop()
print("PRIV new files in /tmp:", subprocess.run("find /tmp -maxdepth 3 -newer /tmp/lt9-mark -type f \\( -iname '*.pdf' -o -iname '*.tmp' \\) 2>/dev/null | grep -vE 'chvd-home|uitest|claude-0' | head",shell=True,capture_output=True,text=True).stdout.strip() or "none")
