import helpers as h
from lt_base import *
CAD="/home/claude/cad/cad.pdf"; h.PDF=CAD
def rss(): return int(open(f"/proc/{a.proc.pid}/status").read().split("VmRSS:")[1].split()[0])//1024
def wk(): return sum(int(x) for x in subprocess.run("ps -o rss= -C WebKitWebProcess",shell=True,capture_output=True,text=True).stdout.split())//1024
def shot(n): a.shot(n); return EV+"/cad/"+n+".png"
def same(p,q): return subprocess.run(["compare","-metric","AE","-fuzz","2%",p,q,"/dev/null"],capture_output=True,text=True).stderr.strip()
a=App(APP, EV+"/cad", display=":61"); h.bind(a); a.start_display()
try:
    t0=time.time(); a.launch(CAD); time.sleep(2-(time.time()-t0) if time.time()-t0<2 else 0)
    s2=shot("p1-at-2s"); time.sleep(6); s8=shot("p1-at-8s")
    print(f"CAD p1: pixels differing between 2 s and 8 s: {same(s2,s8)} | app {rss()} MB, webkit {wk()} MB | pager '{a.js('return (document.querySelector(\".tb-pg-box input, .ph-pager-in\")||{}).value||\"\"')}' | errors: {'Could not open' in a.js('return document.body.innerText')}")
    peak=0
    for p in range(2,6):
        t=time.time(); a.key("Next"); 
        time.sleep(4); peak=max(peak,rss()); shot(f"page{p}")
        print(f"CAD page {p}: pager='{a.js('return (document.querySelector(\".tb-pg-box input, .ph-pager-in\")||{}).value||\"\"')}' rss {rss()} MB")
    a.key("Home"); time.sleep(3)
    for i in range(6): a.key("ctrl+plus"); time.sleep(0.6)
    time.sleep(4); peak=max(peak,rss()); shot("zoomed")
    zoom=a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&/^\\d+%$/.test(e.innerText.trim())).map(e=>e.innerText.trim()).slice(0,2)")
    print(f"CAD zoomed to {zoom}: app {rss()} MB, webkit {wk()} MB, peak app {peak} MB | alive {a.alive()}")
    a.key("ctrl+0"); time.sleep(2)
    t0=time.time(); h.focus_main(); a.key("ctrl+p"); time.sleep(1.2); a.click("section[aria-label=Print] button.primary")
    w=a.wait(lambda: [x for x in h.native_windows() if x[1].startswith("Print")],20,"dialog")[0][0]
    subprocess.run(["xdotool","windowactivate","--sync",w],env=a.env,capture_output=True); time.sleep(3); a.key("Return")
    out=a.wait(lambda: h.cups_pdfs(t0),300,"cups output"); out=sorted(out,key=os.path.getmtime)[-1]; time.sleep(5)
    sp=sorted([f for f in glob.glob("/var/spool/cups/d*") if os.path.getmtime(f)>t0],key=os.path.getmtime)
    print("CAD print: submitted byte-identical to source:", bool(sp) and open(sp[0],'rb').read()==open(CAD,'rb').read(), f"| took {time.time()-t0:.0f}s to CUPS output")
    print("CAD print out: pages", h.pdfinfo(out).get("Pages"), "| fonts", len(subprocess.run(["pdffonts",out],capture_output=True,text=True).stdout.splitlines())-2, "| images", len(subprocess.run(["pdfimages","-list",out],capture_output=True,text=True).stdout.splitlines())-2, "(source 170)")
    subprocess.run(["cp",out,EV+"/cad/printed.pdf"])
finally: a.stop()
