import helpers as h
from lt_base import *
W="/home/claude/uitest-build/wwwroot"
a=App(APP, EV+"/snap", display=":77"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(4)
    def snap(name):
        a.js("document.querySelectorAll('.clock,[class*=clock]').forEach(e=>e.textContent='13:00:00')")
        time.sleep(0.5)
        html=a.js("return '<!DOCTYPE html>'+document.documentElement.outerHTML")
        vw=a.js("return [innerWidth,innerHeight,devicePixelRatio]")
        html=html.replace('<head>','<head><base href=\"file://'+W+'/\">',1)
        html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
        open(f"{W}/snap-{name}.html","w").write(html)
        x,y=a.js("var r=document.documentElement.getBoundingClientRect(); return [window.screenX,window.screenY]")
        a.shot("linux-"+name); json.dump({"vw":vw}, open(f"{EV}/snap/{name}.json","w")); print(name, vw)
    import re
    snap("home")
    a.send("open /home/claude/lt/five-pages.pdf"); time.sleep(5); snap("reader")
finally: a.stop()
