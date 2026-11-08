import helpers as h
from lt_base import *
a=App(APP, EV+"/exact2", display=":67"); h.bind(a); a.start_display()
q="""var out=[]; [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&e.textContent.includes('double')).forEach(e=>{var s=getComputedStyle(e); var r=document.createRange(); r.selectNodeContents(e); out.push([JSON.stringify(e.textContent), s.whiteSpace, Math.round(r.getBoundingClientRect().width), JSON.stringify(e.innerText)])}); return out"""
try:
    for f in ["exact.xlsx","exact.docx"]:
        a.launch("/home/claude/exact/"+f); time.sleep(6)
        print(f, "| textContent, white-space, width px, innerText (what's rendered):", a.js(q))
        if f=="exact.xlsx":
            print("   formatted cells:", a.js("var c=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>e.textContent.trim()).filter(t=>/[₹%\\/]|^0\\.1$|E\\+19|^-7$|3\\.14|1,234|45000|2023/.test(t)); return c"))
        else:
            print("   tab rendered as:", a.js("var p=[...document.querySelectorAll('p,div')].filter(e=>e.offsetParent&&/^tab\\s*here$/.test(e.innerText.replace(/\\u00a0/g,' ').trim())); return p.map(e=>JSON.stringify(e.innerText)+' w='+Math.round(e.getBoundingClientRect().width))"))
        a.shot("exact-"+f); a.stop(); time.sleep(1)
finally: a.stop()
