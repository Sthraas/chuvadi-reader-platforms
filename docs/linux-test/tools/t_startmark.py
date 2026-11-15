# Start-up mark (Linux host, 9c94b81): from the window's first frame to the app, is the window ever blank, and in the
# dark theme is there a light flash? Grabs the screen as fast as it can during launch and classifies each frame.
# Usage: t_startmark.py   (runs light, then dark with the same profile, each cold-ish and warm)
import helpers as h, json, threading
from lt_base import *
a = App(APP, EV + "/startmark", display=":86"); h.bind(a); a.start_display()
def grab(stop, frames, tag):
    n = 0
    while not stop.is_set():
        p = os.path.join(a.out, f"{tag}-{n:03d}.png"); t = time.time()
        subprocess.run(["import", "-window", "root", "-resize", "25%", p], env=a.env, capture_output=True); frames.append((t, p)); n += 1
def classify(p):
    r = subprocess.run(["convert", p, "-format", "%k %[fx:mean] %[fx:standard_deviation]", "info:"], capture_output=True, text=True).stdout.split()
    return int(r[0]), float(r[1]), float(r[2])
def run(tag):
    stop, frames = threading.Event(), []; th = threading.Thread(target=grab, args=(stop, frames, tag)); th.start()
    time.sleep(0.5); t0 = time.time(); a.log = open(a.log_path, "a")
    a.proc = subprocess.Popen([os.path.join(a.app_dir, "chuvadi-reader")], env=a.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=a.log, text=True, bufsize=1)
    threading.Thread(target=a._read, daemon=True).start()
    a.wait(lambda: a.js("return document.querySelector('.shell') !== null"), 40, "shell"); t_shell = time.time() - t0
    time.sleep(1.5); stop.set(); th.join(); seq = []
    for t, p in frames:
        k, mean, sd = classify(p); os.remove(p)
        kind = "no window" if (k < 4 and sd < 0.01) and not seq_has_window(seq) else ("flat" if sd < 0.004 else ("mark" if k < 400 else "app"))
        seq.append((round(t - t0, 2), kind, k, round(mean, 2)))
    out, last = [], None
    for s in seq:
        if s[1] != last: out.append(f"{s[0]:+.2f}s {s[1]} (colours {s[2]}, brightness {s[3]})"); last = s[1]
    gone = a.send("start-mark")
    print(f"START {tag}: shell at {t_shell:.2f} s; frames {len(seq)}; sequence: " + " → ".join(out) + f"; mark still up afterwards: {gone}", flush=True)
    bright = [s for s in seq if s[1] in ("flat", "mark") and s[3] > 0.6]
    return bright
def seq_has_window(seq): return any(s[1] != "no window" for s in seq)
def quit_app():
    a.proc.terminate()
    try: a.proc.wait(10)
    except Exception: a.proc.kill()
    time.sleep(1)
try:
    run("light-first"); quit_app(); run("light-warm")
    a.click(".tb-icon"); time.sleep(1); print("THEME now", a.js("return document.documentElement.dataset.theme"), flush=True); time.sleep(1); quit_app()
    b = run("dark-first"); print("DARK theme kept:", a.js("return document.documentElement.dataset.theme"), "| light frames before the app:", len(b), flush=True); quit_app()
    b = run("dark-warm"); print("DARK warm | light frames before the app:", len(b), flush=True)
finally: a.stop()
