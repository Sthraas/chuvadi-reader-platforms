# B-33: the title bar's sheet pager on Excel files (Next, Previous, a typed number), with real mouse clicks and
# typing, in the situations that lost the viewer: from Home, with a PDF open first, on a second workbook, and back.
# Usage: t_pager.py <three-sheets.xlsx> <second.xlsx> <a.pdf>
import helpers as h
from lt_base import *
A, B, PDF = sys.argv[1], sys.argv[2], sys.argv[3]
a = App(APP, EV + "/pager", display=":95"); h.bind(a); a.start_display()
st = lambda: a.js("return [document.querySelector('.tb-pg-box').value, [...document.querySelectorAll('.xv-tab')].filter(t=>t.classList.contains('on')).map(t=>t.innerText.trim().split(/\\s+/)[0]).join(), (document.querySelector('.xv-cell[data-a=\"A1\"]')||{innerText:''}).innerText.trim().slice(0,18)]")
def click(lab):
    r = a.js(f"var b=document.querySelector('.tb-pager button[aria-label^=\"{lab}\"]'); var r=b.getBoundingClientRect(); return [Math.round(r.left+r.width/2), Math.round(r.top+r.height/2), b.disabled]")
    a.xdo("mousemove", str(r[0]), str(r[1])); a.xdo("click", "1"); time.sleep(1.3)
def typed(n):
    bx = a.rect(".tb-pg-box"); a.xdo("mousemove", str(int(bx[0] + bx[2] / 2)), str(int(bx[1] + bx[3] / 2))); a.xdo("click", "1"); a.xdo("key", "ctrl+a"); a.xdo("type", str(n)); a.xdo("key", "Return"); time.sleep(1.3)
def show(name): a.js(f"var t=[...document.querySelectorAll('.rtab')].find(t => t.textContent.includes('{name}')); t.click(); return 1"); time.sleep(2)
def run(tag):
    out = [("start", st())]
    click("Next"); out.append(("Next", st())); click("Next"); out.append(("Next", st())); click("Previous"); out.append(("Previous", st()))
    typed(1); out.append(("type 1", st())); typed(3); out.append(("type 3", st()))
    a.js("document.querySelectorAll('.xv-tab')[1].click(); return 1"); time.sleep(1.2); out.append(("tab 2", st())); click("Next"); out.append(("Next", st())); typed(1); out.append(("type 1", st()))
    ok = all(int(s[0]) >= 1 and s[1] != "" for _, s in out) and [s[0] for _, s in out] == ["1", "2", "3", "2", "1", "3", "2", "3", "1"] and len({(s[0], s[1], s[2]) for _, s in out}) == 3
    print(f"PAGER {tag}: {'OK' if ok else 'FAIL'} | " + " ; ".join(f"{k} -> {s[0]} {s[1]} '{s[2]}'" for k, s in out), flush=True)
try:
    a.launch(); time.sleep(3)
    a.send("open " + A, timeout=20); time.sleep(4); run("from Home")
    a.send("open " + PDF, timeout=20); time.sleep(3); show(os.path.basename(A)); run("after a PDF tab")
    a.send("open " + B, timeout=20); time.sleep(4); run("second workbook")
    show(os.path.basename(A)); run("back on the first")
finally: a.stop()
