# drive the UiTest build on mutter-headless Wayland via its stdin driver (test only)
import subprocess, os, sys, time, json, re
env=dict(os.environ, WAYLAND_DISPLAY="wl-mt", GDK_BACKEND="wayland", HOME="/tmp/wlhome", GTK_A11Y="none", WAYLAND_DEBUG="client")
env.pop("DISPLAY",None); os.makedirs("/tmp/wlhome",exist_ok=True)
p=subprocess.Popen(["/home/claude/uitest2/chuvadi-reader","/home/claude/lt/five-pages.pdf"],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open("/tmp/wl-debug.log","w"),text=True,bufsize=1)
def rd(tmo=30):
    t=time.time()
    while time.time()-t<tmo:
        l=p.stdout.readline()
        if l: return l.strip()
    return None
# wait for driver ready
t=time.time()
while time.time()-t<90 and "driver ready" not in open("/tmp/wl-debug.log").read(): time.sleep(1)
print("driver ready after", round(time.time()-t), "s"); time.sleep(6)
N=[0]
def js(code):
    N[0]+=1; p.stdin.write(f"{N[0]} js "+code.replace("\n"," ")+"\n"); p.stdin.flush()
    while True:
        l=rd(20)
        if l is None or l.startswith(f"{N[0]} "): return l
print("devicePixelRatio / innerWidth / page text px:", js("return [devicePixelRatio, innerWidth, innerHeight]"))
print("font size of page heading / body:", js("return [getComputedStyle(document.body).fontSize]"))
print("left bar & rails widths (CSS px):", js("return ['.leftbar', 'aside', '.srail-tools', '.srail-view'].map(s=>{var e=document.querySelector(s); return e? s+' '+Math.round(e.getBoundingClientRect().width):s+' -'})"))
p.terminate(); time.sleep(1)
log=open("/tmp/wl-debug.log").read()
print("fractional-scale bound:", "wp_fractional_scale_manager_v1" in log and "get_fractional_scale" in log)
print("preferred_scale events:", sorted(set(re.findall(r"preferred_scale\((\d+)\)",log))))
print("viewport set_destination used:", log.count("wp_viewport@") > 0 and "set_destination" in log)
print("buffer sizes attached (last 3):", re.findall(r"wl_buffer@\d+\.?[^\n]*?(\d{3,4}), (\d{3,4})",log)[-3:] if False else "")
