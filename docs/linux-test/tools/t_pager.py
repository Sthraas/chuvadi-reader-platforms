import sys; sys.path.insert(0, "/home/claude/chuvadi-reader-platforms/docs/linux-test/tools")
import helpers as h
from lt_base import *
a = App(APP, "/tmp/pager19", display=":95"); h.bind(a); a.start_display()
st = lambda: a.js("return [document.querySelector('.tb-pg-box').value, document.querySelector('.tb-pager').innerText.replace(/\\s+/g,' '), [...document.querySelectorAll('.xv-tab')].map(t=>t.innerText.trim().split(/\\s+/)[0]+':'+t.className.replace('xv-tab','').trim()), (document.querySelector('.xv-cell[data-a=\"A1\"]')||{innerText:''}).innerText.trim().slice(0,20), (document.querySelector('.xv-cell[data-a=\"B1\"]')||{innerText:''}).innerText.trim()]")
try:
    a.launch(sys.argv[1]) if len(sys.argv)>2 else (a.launch(), time.sleep(3), a.send("open "+sys.argv[1], timeout=20)); time.sleep(5)
    print("BTNS", a.js("return [...document.querySelectorAll('.tb-pager button, .tb-pager input')].map(b=>b.tagName+'|'+(b.getAttribute('aria-label')||'')+'|'+(b.title||'')+'|'+(b.disabled?'disabled':''))"))
    print("start", st())
    bs = a.js("return [...document.querySelectorAll('.tb-pager button')].map(b=>{var r=b.getBoundingClientRect(); return [(b.getAttribute('aria-label')||b.title), Math.round(r.left+r.width/2), Math.round(r.top+r.height/2), document.elementFromPoint(r.left+r.width/2, r.top+r.height/2)===b||b.contains(document.elementFromPoint(r.left+r.width/2, r.top+r.height/2))]})"); print("geom", bs)
    nx = [b for b in bs if 'ext' in (b[0] or '')][0]
    a.xdo("mousemove", str(nx[1]), str(nx[2])); a.xdo("click", "1"); time.sleep(2.5); print("mouse click Next ->", st())
    a.js("document.querySelector('.tb-pager button[aria-label^=Next]').click(); return 1"); time.sleep(2.5); print("js click Next ->", st())
    bx = a.rect(".tb-pg-box"); a.xdo("mousemove", str(int(bx[0]+bx[2]/2)), str(int(bx[1]+bx[3]/2))); a.xdo("click", "1"); a.xdo("key", "ctrl+a"); a.xdo("type", "2"); a.xdo("key", "Return"); time.sleep(2.5); print("type 2 Enter ->", st())
    a.js("document.querySelectorAll('.xv-tab')[1].click(); return 1"); time.sleep(1.5); print("sheet tab 2 clicked ->", st())
    a.js("document.querySelector('.tb-pager button[aria-label^=Prev]').click(); return 1"); time.sleep(2.5); print("js click Previous ->", st())
    print("LOG", [l[:200] for l in open(a.log_path).read().splitlines() if 'xception' in l or 'rror' in l][:4])
finally: a.stop()
