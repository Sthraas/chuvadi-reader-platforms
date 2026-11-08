#!/usr/bin/env python3
"""First launch per person: time from start to real content on screen (test-only, never shipped).

  tools/linux/first-launch.py <publish dir> <runs>

Each run: a fresh HOME with empty config and cache folders (no Mesa shader cache: a person's first launch,
or the first after a Mesa update), its own Xvfb, mutter and session bus. "Content" = more than 200 colours
in the window area. Prints the median and every run. B-12. Needs Xvfb, mutter, ImageMagick (test tools).
"""
import os, subprocess, sys, tempfile, time, statistics
app_dir, runs = sys.argv[1], int(sys.argv[2])
disp = ":87"
x = subprocess.Popen(["Xvfb", disp, "-screen", "0", "1440x900x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env0 = dict(os.environ, DISPLAY=disp)
bus = subprocess.run(["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"], env=env0, capture_output=True, text=True).stdout.split()
env0["DBUS_SESSION_BUS_ADDRESS"] = bus[0]
wm = subprocess.Popen(["mutter", "--x11", "--replace"], env=env0, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)
def colours():
    r = subprocess.run(["import", "-display", disp, "-window", "root", "-crop", "1100x700+170+100", "-format", "%k", "info:"], capture_output=True, text=True)
    try: return int(r.stdout.strip() or 0)
    except ValueError: return 0
res = {"first launch": []}
try:
    for i in range(runs):
        for label in res:
            home = tempfile.mkdtemp(prefix="blank-home-")
            env = dict(env0, HOME=home, XDG_CONFIG_HOME=home + "/.config", XDG_CACHE_HOME=home + "/.cache")
            t0 = time.time()
            p = subprocess.Popen([app_dir + "/chuvadi-reader"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            seen = None
            while time.time() - t0 < 20:
                if colours() > 200: seen = time.time() - t0; break
            p.terminate(); p.wait(10)
            res[label].append(seen)
            subprocess.run(["rm", "-rf", home])
            time.sleep(1)
finally:
    wm.terminate(); x.terminate(); subprocess.run(["kill", bus[1]])
for k, v in res.items():
    ok = [t for t in v if t]
    print(f"{k}: median {statistics.median(ok):.2f} s  runs {[round(t,2) if t else None for t in v]}")
