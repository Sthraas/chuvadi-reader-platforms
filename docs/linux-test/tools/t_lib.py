import helpers as h, json
import re
from lt_base import *
def txt(): return a.js("return document.body.innerText.replace(/\\s+/g,' ')")
def cancel_btn(): return a.js("return [...document.querySelectorAll('button')].some(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim()))")
def rss(): return int(open(f"/proc/{a.proc.pid}/status").read().split("VmRSS:")[1].split()[0])//1024
a=App(APP, EV+"/lib", display=":66"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(3)
    for f in []:
        t0=time.time(); a.send("open /tmp/chvd-stall/"+f, timeout=10)
        first_open=None; first_cancel=None
        while time.time()-t0<16:
            if first_open is None and 'Opening' in txt(): first_open=round(time.time()-t0,1)
            if cancel_btn(): first_cancel=round(time.time()-t0,1); break
            time.sleep(0.3)
        a.shot("stall-"+f)
        btxt=a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim())); return b?b.innerText.trim():''")
        a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/^(Cancel|Stop)/.test(b.innerText.trim())); if(b) b.click()"); time.sleep(2)
        gone=f not in tabs(a)
        try: a.send("open /home/claude/lt/five-pages.pdf", timeout=15); time.sleep(3); nxt='five-pages.pdf' in tabs(a)
        except Exception as e: nxt=f"driver open blocked ({str(e)[:40]})"
        print(f"B-24 {f}: 'Opening…' at {first_open}s | '{btxt}' at {first_cancel}s | tab closed after click: {gone} | next open works: {nxt}")
        a.js("[...document.querySelectorAll('.rtab')].forEach(t=>{var x=t.querySelector('button'); if(x) x.click()})"); time.sleep(1)
    for f in ["sample.docx","sample.xlsx","bad-sst.xlsx","far-cell.xlsx","bomb.docx","missing-part.docx","notzip.xlsx","big-400k.xlsx"]:
        p=("/home/claude/fx/" if f.startswith("sample") else "/home/claude/rx/")+f
        r0=rss(); t0=time.time(); a.send("open "+p, timeout=30)
        while time.time()-t0<30 and 'Opening' in txt(): time.sleep(0.5)
        time.sleep(1); el=round(time.time()-t0,1)
        msg=a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>e.innerText.trim()).filter(t=>t.length>20&&/open|large|damag|limit|couldn|read|Details/i.test(t)).slice(0,2)")
        print(f"LIB {f:18} {el:5}s rss {r0}->{rss()} MB | tab: {f in tabs(a)} | {msg}"); a.shot("lib-"+f)
    exp=json.load(open('/home/claude/exact/expected.json'))
    for f,key in [("exact.xlsx","S"),("exact.docx","P")]:
        a.send("open /home/claude/exact/"+f, timeout=30); time.sleep(5); a.shot("exact-"+f)
        texts=a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>e.textContent)")
        for s in exp[key]:
            hit=[t for t in texts if t==s]; near=[t for t in texts if t.strip().replace('\\t',' ').replace('\\n',' ')==s.strip().replace('\t',' ').replace('\n',' ') or s.strip() in t][:1]
            print(f"EXACT {f}: {s!r:24} exact={'YES' if hit else 'NO '} shown={near[0] if near and not hit else ''!r}")
        if f=="exact.xlsx":
            print("EXACT numbers shown (B20..B26):", [t for t in texts if re.match(r'^[-₹0-9.,%/ E+]+$',t.strip()) and t.strip()][:30])
        if f=="exact.docx":
            print("EXACT docx tab line:", [t for t in texts if 'tab' in t and 'here' in t][:2] or [t for t in texts if t in ('tab','here')][:3])
finally: a.stop()
