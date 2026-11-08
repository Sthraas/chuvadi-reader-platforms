import helpers as h
from lt_base import *
a=App(APP, EV+"/clip", display=":79"); h.bind(a); a.start_display()
def targets(): return subprocess.run(["xclip","-selection","clipboard","-o","-t","TARGETS"],env=a.env,capture_output=True,text=True,timeout=10).stdout.split()
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(6)
    h.click_label(".srail","Snapshot"); time.sleep(2); a.shot("snapshot-tool")
    print("after Snapshot click, status:", a.text(".statusbar").replace("\n"," ")[:160])
    # drag a region on the page
    r=a.js("var p=document.querySelector('.page, .pdf-page, [class*=page] img, [class*=page] svg'); var b=p.getBoundingClientRect(); return [b.x,b.y,b.width,b.height]")
    print("page rect:", r)
    x,y=int(r[0]+60),int(r[1]+60)
    subprocess.run(["xdotool","mousemove",str(x),str(y),"mousedown","1","mousemove",str(x+200),str(y+120),"sleep","0.3","mousemove",str(x+300),str(y+200),"mouseup","1"],env=a.env)
    time.sleep(2); a.shot("snapshot-drawn")
    print("toasts:", toasts(a)); print("buttons visible:", [b for b in a.js("return [...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>b.innerText.trim())") if 'opy' in b or 'lip' in b or 'Save' in b])
    print("click copy:", a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.innerText.trim()=='Copy to clipboard'); if(!b) return false; b.click(); return true")); time.sleep(3); print("toasts:", toasts(a)); a.shot("after-copy")
    tg=targets(); print("clipboard TARGETS:", tg)
    if "image/png" in tg:
        png=subprocess.run(["xclip","-selection","clipboard","-o","-t","image/png"],env=a.env,capture_output=True,timeout=10).stdout
        open(EV+"/clip/clip.png","wb").write(png); print("PNG bytes:", len(png), subprocess.run(["identify",EV+"/clip/clip.png"],capture_output=True,text=True).stdout.strip())
    # text: Ctrl+A in page? use Find text copy: select text via JS selection on text layer then ctrl+c
    sel=a.js("var t=[...document.querySelectorAll('span,text,tspan')].find(e=>e.textContent.includes('Chuvadi Linux')); if(!t) return null; var r=document.createRange(); r.selectNodeContents(t); var s=getSelection(); s.removeAllRanges(); s.addRange(r); return s.toString()")
    print("selected in page text layer:", repr(sel)); h.focus_main(); a.key("ctrl+c"); time.sleep(1.5)
    print("clipboard text:", repr(subprocess.run(["xclip","-selection","clipboard","-o"],env=a.env,capture_output=True,text=True,timeout=10).stdout[:80]))
finally: a.stop()
