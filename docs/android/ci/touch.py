#!/usr/bin/env python3
"""Real touch input on an Android emulator (CI only).

`adb shell input` can't do multi-touch and is too slow for a double-tap, so this writes Linux
multi-touch (protocol B) events straight to the emulator's touchscreen device, with real timing:
each frame is a small binary file of input_event structs, and a device-side script `cat`s them to
/dev/input/eventN with sleeps in between. Android sees the same events a finger would make.

    touch.py tap X Y
    touch.py doubletap X Y
    touch.py swipe X1 Y1 X2 Y2 [ms]
    touch.py pinch CX CY D_FROM D_TO [ms]        (two fingers, horizontal; D = distance in px)
    touch.py longdrag X1 Y1 X2 Y2 [hold_ms] [ms]
Coordinates are screen pixels in the current (portrait) orientation.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT = 0
BTN_TOUCH = 330
ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR, ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x2F, 0x30, 0x35, 0x36
ABS_MT_TRACKING_ID, ABS_MT_PRESSURE = 0x39, 0x3A
EVENT = struct.Struct("<qqHHi")  # 64-bit struct input_event: timeval (2 × long), type, code, value


def adb(*args, check=True):
    return subprocess.run(["adb", *args], check=check, capture_output=True, text=True).stdout


def find_touchscreen():
    """The input device that reports ABS_MT_POSITION_X, its axis maxima, and the screen size."""
    out = adb("shell", "getevent", "-p")
    device = None
    found = {}
    for line in out.splitlines():
        m = re.match(r"add device \d+: (\S+)", line)
        if m:
            device = m.group(1)
            continue
        m = re.match(r"\s*(0035|0036)\s*:\s*value \d+, min (\d+), max (\d+)", line)
        if m and device:
            found.setdefault(device, {})[m.group(1)] = int(m.group(3))
    # The touchscreen's axes follow the display's natural (rotation 0) size; an override wins.
    wm = adb("shell", "wm", "size")
    sizes = dict(re.findall(r"(Physical|Override) size: (\d+x\d+)", wm))
    w, h = (int(v) for v in (sizes.get("Override") or sizes["Physical"]).split("x"))
    for dev, axes in found.items():
        if "0035" in axes and "0036" in axes:
            return dev, axes["0035"], axes["0036"], w, h
    raise SystemExit("no multi-touch device found:\n" + out)


DEV, MAX_X, MAX_Y, SCREEN_W, SCREEN_H = find_touchscreen()
_next_id = [100]


def raw(x, y):
    return (round(x * MAX_X / max(1, SCREEN_W - 1)), round(y * MAX_Y / max(1, SCREEN_H - 1)))


def ev(t, c, v):
    return EVENT.pack(0, 0, t, c, v)


class Gesture:
    def __init__(self):
        self.steps = []          # (bytes, sleep_after_seconds)
        self.down = {}           # slot → tracking id

    def press(self, slot, x, y):
        tid = _next_id[0]
        _next_id[0] += 1
        self.down[slot] = tid
        rx, ry = raw(x, y)
        data = (ev(EV_ABS, ABS_MT_SLOT, slot) + ev(EV_ABS, ABS_MT_TRACKING_ID, tid)
                + ev(EV_ABS, ABS_MT_TOUCH_MAJOR, 6) + ev(EV_ABS, ABS_MT_PRESSURE, 60)
                + ev(EV_ABS, ABS_MT_POSITION_X, rx) + ev(EV_ABS, ABS_MT_POSITION_Y, ry))
        if len(self.down) == 1:
            data += ev(EV_KEY, BTN_TOUCH, 1)
        return data

    def move(self, slot, x, y):
        rx, ry = raw(x, y)
        return ev(EV_ABS, ABS_MT_SLOT, slot) + ev(EV_ABS, ABS_MT_POSITION_X, rx) + ev(EV_ABS, ABS_MT_POSITION_Y, ry)

    def release(self, slot):
        self.down.pop(slot, None)
        data = ev(EV_ABS, ABS_MT_SLOT, slot) + ev(EV_ABS, ABS_MT_TRACKING_ID, -1)
        if not self.down:
            data += ev(EV_KEY, BTN_TOUCH, 0)
        return data

    def emit(self, data, sleep_s):
        self.steps.append((data + ev(EV_SYN, SYN_REPORT, 0), sleep_s))

    def run(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = ["#!/system/bin/sh", "D=/data/local/tmp/chvd-touch"]
            # Steps with no pause after them go out in ONE `cat` (one write per file, microseconds apart):
            # each process start costs ~170 ms on the CI emulator, too slow for a double-tap.
            batch = []
            for i, (data, sleep_s) in enumerate(self.steps):
                with open(os.path.join(tmp, f"{i:03d}"), "wb") as f:
                    f.write(data)
                batch.append(f"$D/{i:03d}")
                if sleep_s > 0 or i == len(self.steps) - 1:
                    script.append(f"cat {' '.join(batch)} > {DEV}")
                    batch = []
                if sleep_s > 0:
                    script.append(f"sleep {sleep_s:.3f}")
            with open(os.path.join(tmp, "run.sh"), "w") as f:
                f.write("\n".join(script) + "\n")
            # Push the folder itself to a destination that doesn't exist yet: adb then creates it
            # with exactly these files (no "dir/." semantics to depend on).
            adb("shell", "rm -rf /data/local/tmp/chvd-touch")
            adb("push", tmp, "/data/local/tmp/chvd-touch")
            r = subprocess.run(["adb", "shell", "sh /data/local/tmp/chvd-touch/run.sh 2>&1; echo rc=$?"],
                               capture_output=True, text=True)
            if not r.stdout.strip().endswith("rc=0"):
                raise SystemExit(f"writing to {DEV} failed:\n{r.stdout}{r.stderr}")


def steps_between(a, b, n):
    return [a + (b - a) * (i / n) for i in range(1, n + 1)]


def tap(g, x, y, sleep_after=0.0):
    """Down and up as two reports in ONE write: each write is a process start on the slow emulator,
    and a double-tap must land inside mobile.js's 300 ms window."""
    syn = ev(EV_SYN, SYN_REPORT, 0)
    g.steps.append((g.press(0, x, y) + syn + g.release(0) + syn, sleep_after))


def main():
    cmd, args = sys.argv[1], [float(a) for a in sys.argv[2:]]
    g = Gesture()
    if cmd == "tap":
        tap(g, *args[:2])
    elif cmd == "doubletap":
        x, y = args[:2]
        tap(g, x, y)   # no pause: both taps leave in one process (see run())
        tap(g, x, y)
    elif cmd == "swipe":
        x1, y1, x2, y2 = args[:4]
        ms = args[4] if len(args) > 4 else 250
        n = 8
        g.emit(g.press(0, x1, y1), ms / 1000 / n)
        for x, y in zip(steps_between(x1, x2, n), steps_between(y1, y2, n)):
            g.emit(g.move(0, x, y), ms / 1000 / n)
        g.emit(g.release(0), 0)
    elif cmd == "pinch":
        cx, cy, d0, d1 = args[:4]
        ms = args[4] if len(args) > 4 else 500
        n = 12
        g.emit(g.press(0, cx - d0 / 2, cy) + g.press(1, cx + d0 / 2, cy), 0.05)
        for d in steps_between(d0, d1, n):
            g.emit(g.move(0, cx - d / 2, cy) + g.move(1, cx + d / 2, cy), ms / 1000 / n)
        g.emit(g.release(1), 0.02)
        g.emit(g.release(0), 0)
    elif cmd == "longdrag":
        x1, y1, x2, y2 = args[:4]
        hold = args[4] if len(args) > 4 else 800
        ms = args[5] if len(args) > 5 else 700
        n = 14
        g.emit(g.press(0, x1, y1), hold / 1000)
        for x, y in zip(steps_between(x1, x2, n), steps_between(y1, y2, n)):
            g.emit(g.move(0, x, y), ms / 1000 / n)
        g.emit(g.move(0, x2, y2), 0.3)
        g.emit(g.release(0), 0)
    else:
        raise SystemExit(__doc__)
    g.run()
    print(f"{cmd} {' '.join(sys.argv[2:])} on {DEV} (raw max {MAX_X}x{MAX_Y}, screen {SCREEN_W}x{SCREEN_H})")


if __name__ == "__main__":
    main()
