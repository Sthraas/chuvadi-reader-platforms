import helpers as h, sys
from lt_base import *
f=sys.argv[1]
a=App(APP, EV+"/exact3-"+f, display=":6"+("8" if f.endswith("xlsx") else "9")); h.bind(a); a.start_display()
try:
    a.launch("/home/claude/exact/"+f); time.sleep(6)
    if f.endswith("xlsx"):
        print("xlsx cells with 1234/0.125/12.5/45000/₹:", a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>e.textContent).filter(t=>/1234|1,234|0\\.125|12\\.5|45000|₹|%/.test(t))"))
    else:
        print("docx double-space para:", a.js("var e=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&e.textContent.includes('double'))[0]; if(!e) return 'not found'; var s=getComputedStyle(e); return [JSON.stringify(e.textContent), s.whiteSpace, JSON.stringify(e.innerText)]"))
        print("docx leading/trailing:", a.js("return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&/leading|trailing/.test(e.textContent)).map(e=>[JSON.stringify(e.textContent),getComputedStyle(e).whiteSpace,JSON.stringify(e.innerText)])"))
        print("docx tab line:", a.js("var p=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&/tab/.test(e.textContent)&&/here/.test(e.textContent)&&e.textContent.length<30); var e=p[p.length-1]; return e?[JSON.stringify(e.textContent),JSON.stringify(e.innerText),Math.round(e.getBoundingClientRect().width)]:'none'"))
    a.shot("view")
finally: a.stop()
