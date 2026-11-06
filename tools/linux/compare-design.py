#!/usr/bin/env python3
"""Linux vs Windows-engine vs handout screenshots (test-only, never shipped).

  tools/linux/compare-design.py <ui-test publish dir> <out dir>

1. Runs Foundation's dev-only preview host (tests/ChuvadiReader.MobileUi.Preview, CHVD_FF=desktop: it
   reports Windows, so the chrome is exactly the WPF app's) and screenshots Home, Reader, Library and
   Settings in Chromium — the engine of WebView2, which the Windows app uses.
2. Shows the same pages in the Linux app (WebKitGTK), with the same two fixture documents open.
3. Same size (1440 × 900, the handout's reference), clock hidden, animations off. Writes per page:
   windows-*.png, linux-*.png, side-by-side *-compare.png, a diff image and the share of pixels that differ.
4. Renders the handout's Reader Side Rails canvas for the design itself (handout-reader-side-rails.png).
Needs: the .NET SDK, Python Playwright with Chromium, Xvfb, mutter, ImageMagick — all test tools.
"""
import glob, json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uitest_lib import App  # noqa: E402

APP_DIR, OUT = sys.argv[1], sys.argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
os.makedirs(OUT, exist_ok=True)
W, H = 1440, 900
MASK = ".sb-clock{visibility:hidden!important} *{caret-color:transparent!important;animation:none!important;transition:none!important}"
PAGES = ["home", "reader", "library", "settings"]

# ── 1. Windows engine: the preview host in Chromium ─────────────────────────
env = dict(os.environ, CHVD_FF="desktop", ASPNETCORE_URLS="http://127.0.0.1:5110", DOTNET_CLI_TELEMETRY_OPTOUT="1",
           ASPNETCORE_ENVIRONMENT="Development")  # Development: serves the Ui's _content static assets
host = subprocess.Popen(["dotnet", "run", "-c", "Release", "--project", os.path.join(ROOT, "tests/ChuvadiReader.MobileUi.Preview")],
                        env=env, stdout=open(os.path.join(OUT, "preview-host.log"), "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(240):
        try:
            urllib.request.urlopen("http://127.0.0.1:5110/", timeout=2)
            break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for name, route in zip(PAGES, ["/", "/reader", "/library", "/settings"]):
            page.goto("http://127.0.0.1:5110" + route, wait_until="networkidle")
            page.wait_for_selector(".statusbar", timeout=30000)
            page.add_style_tag(content=MASK)
            page.wait_for_timeout(2500)
            page.screenshot(path=os.path.join(OUT, f"windows-{name}.png"))
        # the handout's own canvas (design reference)
        hp = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        hp.goto("file://" + os.path.join(ROOT, "docs/design-handoff/Reader Side Rails.dc.html"))
        hp.wait_for_timeout(4000)
        hp.screenshot(path=os.path.join(OUT, "handout-reader-side-rails.png"), full_page=True)
        b.close()
    fixtures = sorted(glob.glob("/tmp/chvd-mobile-preview-*"), key=os.path.getmtime)[-1]
finally:
    host.terminate()

# ── 2. Linux: the same pages in the app ──────────────────────────────────────
app = App(APP_DIR, os.path.join(OUT, "linux-run"), display=":91")
app.procs.append(subprocess.Popen(["Xvfb", ":91", "-screen", "0", f"{W}x{H}x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
time.sleep(1)
bus = subprocess.run(["dbus-daemon", "--session", "--fork", "--print-address=1", "--print-pid=1"], env=app.env,
                     capture_output=True, text=True, check=True).stdout.split()
app.env["DBUS_SESSION_BUS_ADDRESS"], app.bus_pid = bus[0], int(bus[1])
app.procs.append(subprocess.Popen(["mutter", "--x11", "--replace"], env=app.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
time.sleep(3)
try:
    app.launch()
    for doc in ("lab-report.pdf", "discharge-summary.pdf"):  # the preview host's order
        app.open(os.path.join(fixtures, doc))
        app.wait(lambda doc=doc: app.js(f"return [...document.querySelectorAll('.rtab')].some(t=>t.innerText.includes({json.dumps(doc)}))"), 20, doc)
        time.sleep(1.5)
    app.js(f"var s=document.createElement('style'); s.textContent={json.dumps(MASK)}; document.head.appendChild(s); return true")

    def go(name):
        # The same navigation as the Chromium side (by address), so both show the same state.
        if name == "reader":
            app.js("var t=[...document.querySelectorAll('.rtab')].find(t=>t.innerText.includes('discharge-summary.pdf')); t.click(); return true")
            time.sleep(1)
        route = {"home": "/", "reader": "/reader", "library": "/library", "settings": "/settings"}[name]
        app.js(f"Blazor.navigateTo({json.dumps(route)}); return true")
        time.sleep(2.5)

    for name in PAGES:
        go(name)
        app.shot(f"../linux-{name}")
finally:
    app.stop()

# ── 3. Compare ───────────────────────────────────────────────────────────────
rows = []
for name in PAGES:
    win, lin = os.path.join(OUT, f"windows-{name}.png"), os.path.join(OUT, f"linux-{name}.png")
    r = subprocess.run(["compare", "-metric", "AE", "-fuzz", "6%", win, lin, os.path.join(OUT, f"{name}-diff.png")],
                       capture_output=True, text=True)
    differing = int(float(r.stderr.strip().split()[0] or 0))
    share = 100.0 * differing / (W * H)
    subprocess.run(["convert", "(", win, "-background", "#333", "-fill", "white", "-gravity", "north", "-splice", "0x28",
                    "-pointsize", "18", "-annotate", "+0+4", "Windows engine (Chromium / WebView2) — preview host", ")",
                    "(", lin, "-background", "#333", "-fill", "white", "-gravity", "north", "-splice", "0x28",
                    "-pointsize", "18", "-annotate", "+0+4", "Linux (WebKitGTK) — this host", ")",
                    "+append", os.path.join(OUT, f"{name}-compare.png")], check=True)
    rows.append((name, differing, share))
with open(os.path.join(OUT, "compare.md"), "w") as f:
    f.write("| Page | Pixels differing (fuzz 6%) | Share |\n|---|---|---|\n")
    for name, n, share in rows:
        f.write(f"| {name} | {n:,} | {share:.2f} % |\n")
print(open(os.path.join(OUT, "compare.md")).read())
