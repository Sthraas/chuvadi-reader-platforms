import helpers as h
from lt_base import *
a=App(APP, EV+"/hover", display=":94"); h.bind(a); a.start_display()
X=lambda *c: subprocess.run(["xdotool",*c],env=a.env,capture_output=True,text=True).stdout.strip()
def rect(sel): return a.js(f"var e=document.querySelector({json.dumps(sel)}); if(!e) return null; var r=e.getBoundingClientRect(); return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]")
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    rails=a.js("return [...document.querySelectorAll('.srail, [class*=rail]')].filter(e=>e.offsetParent).map(e=>e.className.toString().slice(0,40)+' '+JSON.stringify(e.getBoundingClientRect().toJSON()))")
    print("rails:", rails[:6])
    r=rect(".srail"); print("tools rail at rest:", r); a.shot("rest")
    X("mousemove",str(r[0]+r[2]//2),str(r[1]+120)); time.sleep(1.5)
    r2=rect(".srail"); print("tools rail on hover:", r2, "| labels visible:", a.js("return [...document.querySelectorAll('.srail button')].filter(b=>b.offsetParent).slice(0,4).map(b=>{var s=[...b.querySelectorAll('span')].find(x=>x.innerText.trim()); return s? (s.innerText.trim()+':'+getComputedStyle(s).opacity+':'+getComputedStyle(s).display):'-'})"))
    a.shot("hover-tools")
    X("mousemove","900","500"); time.sleep(0.8)
    # keyboard focus: Tab a few times and record focused element + its outline
    h.focus_main()
    for i in range(6):
        a.key("Tab"); time.sleep(0.4)
        print("Tab", i+1, a.js("var e=document.activeElement; var s=getComputedStyle(e); return e.tagName+' '+(e.getAttribute('aria-label')||e.innerText||'').trim().slice(0,24).replace(/\\s+/g,' ')+' | outline '+s.outlineStyle+' '+s.outlineWidth+' '+s.outlineColor+' | box-shadow '+s.boxShadow.slice(0,40)"))
    a.shot("focus-tab6")
finally: a.stop()
