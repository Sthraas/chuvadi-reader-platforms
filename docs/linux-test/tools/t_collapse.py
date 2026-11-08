import helpers as h
from lt_base import *
a=App(APP, EV+"/collapse", display=":64"); h.bind(a); a.start_display()
W="var e=document.querySelector('.leftbar, aside.lb, nav'); return e? Math.round(e.getBoundingClientRect().width):-1"
try:
    a.launch("/home/claude/lt/five-pages.pdf"); time.sleep(5)
    w0=a.js(W); ok=a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.innerText.trim()=='Collapse'); if(!b) return false; b.click(); return true"); time.sleep(1.5)
    w1=a.js(W); a.shot("collapsed")
    exp=a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/Expand|Collapse/i.test((b.getAttribute('aria-label')||b.title||b.innerText).trim())); return b?(b.getAttribute('aria-label')||b.title||b.innerText).trim():''")
    a.js("var b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&/Expand/i.test((b.getAttribute('aria-label')||b.title||b.innerText).trim())); if(b) b.click()"); time.sleep(1.5); w2=a.js(W)
    print(f"Collapse clicked: {ok} | left bar width {w0} -> {w1} px | control now: '{exp}' | after Expand: {w2} px")
    a.launch("/home/claude/lt/five-pages.pdf") if False else None
finally: a.stop()
