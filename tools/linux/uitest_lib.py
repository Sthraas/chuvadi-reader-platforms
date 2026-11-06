"""Linux UI test harness (test-only, never shipped).

Starts Xvfb + mutter (test tools), launches the UI-test build of Chuvadi Reader
(dotnet publish -p:UiTest=true) with a fresh profile, and talks to its UiTestDriver over
stdin/stdout. Real input (clicks, keys, typing into GTK dialogs) goes through xdotool;
page state is read with JavaScript through the driver.
"""
import json, os, shutil, subprocess, tempfile, threading, time, queue


class App:
    def __init__(self, app_dir, out_dir, display=":95", env=None):
        self.app_dir, self.out, self.display = app_dir, out_dir, display
        os.makedirs(out_dir, exist_ok=True)
        self.home = tempfile.mkdtemp(prefix="chvd-home-")
        os.makedirs(os.path.join(self.home, "Documents"), exist_ok=True)
        self.env = dict(os.environ, HOME=self.home, DISPLAY=display, GTK_A11Y="none", CHUVADI_TIMING="1",
                        XDG_CONFIG_HOME=os.path.join(self.home, ".config"),
                        XDG_RUNTIME_DIR=tempfile.mkdtemp(prefix="chvd-xdg-"), NO_AT_BRIDGE="1")
        self.env.update(env or {})
        os.chmod(self.env["XDG_RUNTIME_DIR"], 0o700)
        self.log_path = os.path.join(out_dir, "app.log")
        self.replies = queue.Queue()
        self.procs = []

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start_display(self):
        """Xvfb, one session bus for the whole run (as a desktop session has), and mutter."""
        self.procs.append(subprocess.Popen(["Xvfb", self.display, "-screen", "0", "1920x1080x24"],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1)
        bus = subprocess.run(["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"],
                             env=self.env, capture_output=True, text=True, check=True).stdout.split()
        self.env["DBUS_SESSION_BUS_ADDRESS"], self.bus_pid = bus[0], int(bus[1])
        self.procs.append(subprocess.Popen(["mutter", "--x11", "--replace"], env=self.env,
                                           stdout=open(os.path.join(self.out, "mutter.log"), "w"),
                                           stderr=subprocess.STDOUT))
        time.sleep(3)

    def launch(self, *args, timeout=60):
        self.log = open(self.log_path, "w")
        self.proc = subprocess.Popen([os.path.join(self.app_dir, "chuvadi-reader"), *args],
                                     env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.log, text=True, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()
        self.wait_log("blazor first render", timeout)
        self.wait(lambda: self.js("return document.querySelector('.shell') !== null"), 30, "shell rendered")
        time.sleep(1.5)

    def _read(self):
        for line in self.proc.stdout:
            self.replies.put(line.rstrip("\n"))

    def restart(self):
        """A fresh app process with a fresh profile, on the same display and session bus."""
        try:
            self.proc.terminate()
            self.proc.wait(10)
        except Exception:
            pass
        self.home = tempfile.mkdtemp(prefix="chvd-home-")
        os.makedirs(os.path.join(self.home, "Documents"), exist_ok=True)
        self.env.update(HOME=self.home, XDG_CONFIG_HOME=os.path.join(self.home, ".config"))
        self.replies = queue.Queue()
        self.log_path = os.path.join(self.out, "app-2.log")
        self.launch()

    def stop(self):
        try:
            self.proc.terminate()
            self.proc.wait(10)
        except Exception:
            pass
        for p in reversed(self.procs):
            p.terminate()
        self.procs.clear()
        # The session bus last: services it started (portals) exit when it goes.
        if getattr(self, "bus_pid", None):
            try:
                os.kill(self.bus_pid, 15)
            except ProcessLookupError:
                pass
            self.bus_pid = None

    def alive(self):
        return self.proc.poll() is None

    # ── driver ─────────────────────────────────────────────────────────────
    def send(self, line, timeout=40):
        self._n = getattr(self, "_n", 0) + 1
        n = str(self._n)
        self.proc.stdin.write(n + " " + line.replace("\n", " ") + "\n")
        self.proc.stdin.flush()
        end = time.time() + timeout
        while True:
            reply = self.replies.get(timeout=max(0.1, end - time.time()))
            rid, _, rest = reply.partition(" ")
            if rid != n:
                continue  # a late answer to an earlier command that timed out here
            if rest.startswith("ERR "):
                raise RuntimeError(rest[4:])
            return json.loads(rest[3:])

    def js(self, body):
        return self.send("js " + body)

    def commands(self):
        return self.send("commands")

    def invoke(self, command_id):
        return self.send("invoke " + command_id)

    def open(self, path):
        return self.send("open " + path)

    # ── page helpers ───────────────────────────────────────────────────────
    def click(self, selector, index=0):
        """Clicks an element by CSS selector (a DOM click: Blazor's onclick handlers run)."""
        ok = self.js(f"var e=document.querySelectorAll({json.dumps(selector)})[{index}]; if(!e) return false; e.scrollIntoView({{block:'nearest'}}); e.click(); return true;")
        if not ok:
            raise RuntimeError("no element " + selector)
        time.sleep(0.4)

    def exists(self, selector):
        return self.js(f"return document.querySelector({json.dumps(selector)}) !== null")

    def text(self, selector):
        return self.js(f"var e=document.querySelector({json.dumps(selector)}); return e ? e.innerText : null")

    def rect(self, selector, index=0):
        """Screen rectangle of an element (the window is maximised at 0,0 on the test screen)."""
        return self.js(f"var e=document.querySelectorAll({json.dumps(selector)})[{index}]; if(!e) return null; var r=e.getBoundingClientRect(); return [r.left,r.top,r.width,r.height]")

    def error_ui_visible(self):
        return self.js("var e=document.getElementById('blazor-error-ui'); return !!e && getComputedStyle(e).display !== 'none'")

    def wait(self, predicate, timeout=20, what="condition"):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = predicate()
                if last:
                    return last
            except Exception as ex:  # page busy or navigating
                last = ex
            time.sleep(0.25)
        raise TimeoutError(f"timed out waiting for {what} (last: {last})")

    def wait_log(self, text, timeout=30):
        self.wait(lambda: text in open(self.log_path).read(), timeout, "log: " + text)

    # ── real input ─────────────────────────────────────────────────────────
    def xdo(self, *args):
        subprocess.run(["xdotool", *args], env=self.env, check=True)

    def key(self, *keys):
        for k in keys:
            self.xdo("key", "--clearmodifiers", k)
            time.sleep(0.15)

    def type(self, text):
        self.xdo("type", "--delay", "20", text)

    def mouse_click(self, x, y, button=1, double=False):
        self.xdo("mousemove", str(int(x)), str(int(y)))
        self.xdo("click", "--repeat", "2" if double else "1", "--delay", "80", str(button))
        time.sleep(0.4)

    def click_real(self, selector, index=0):
        """A real pointer click at the element's centre (for mousedown handlers and focus)."""
        r = self.rect(selector, index)
        if not r:
            raise RuntimeError("no element " + selector)
        self.mouse_click(r[0] + r[2] / 2, r[1] + r[3] / 2)

    def windows(self, name):
        r = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", name], env=self.env,
                           capture_output=True, text=True)
        return [w for w in r.stdout.split() if w]

    def wait_window(self, name, timeout=15):
        return self.wait(lambda: self.windows(name), timeout, "window " + name)[0]

    def shot(self, name):
        path = os.path.join(self.out, name + ".png")
        subprocess.run(["import", "-window", "root", path], env=self.env, check=True)
        return path
