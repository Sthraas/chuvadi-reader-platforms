"""Design-fidelity screenshots (Web Test chat; test tooling only).
python3 shots.py <dev base> <sangam-mode base> <pdf> <out> [engines...]
Dev base: Development sign-in portal. Sangam-mode base: portal with Sangam configured (shows 12a)."""
import os, sys, json
from playwright.sync_api import sync_playwright

dev, sso, pdf, out = sys.argv[1:5]
engines = sys.argv[5:] or ["chromium", "firefox", "webkit"]
os.makedirs(out, exist_ok=True)
SIZES = {"desktop": (1440, 900, False), "frame": (1280, 720, False), "tablet": (820, 1180, True), "tablet-land": (1180, 820, True), "phone": (390, 844, True)}
THEMES = ["light", "dark", "palm", "indigo", "contrast"]
notes = []
ONLY = [x for x in os.environ.get("ONLY_SIZES", "").split(",") if x]

def shot(pg, name):
    pg.wait_for_timeout(400)
    pg.screenshot(path=os.path.join(out, name + ".png"))

with sync_playwright() as p:
    for eng in engines:
        bt = getattr(p, eng)
        b = bt.launch()
        for size, (w, h, touch) in [(k, v) for k, v in SIZES.items() if not ONLY or k in ONLY]:
            kw = {"viewport": {"width": w, "height": h}}
            if touch and eng != "firefox": kw.update(has_touch=True, is_mobile=(size == "phone"))
            # 12a in light and dark
            for scheme in ("light", "dark"):
                c = b.new_context(color_scheme=scheme, **kw); pg = c.new_page()
                reqs, fin = [], set(); pg.on("request", lambda r: reqs.append(r.url)); pg.on("requestfinished", lambda r: fin.add(r.url))
                try:
                    pg.goto(sso + "/signin"); pg.wait_for_selector("text=Continue with Sangam")
                except Exception as e:
                    notes.append((eng, size, "12a-" + scheme, str(e).splitlines()[0], "pending: " + str([u for u in reqs if u not in fin]))); c.close(); continue
                shot(pg, f"{eng}-{size}-12a-{scheme}"); c.close()
            c = b.new_context(extra_http_headers={"X-Dev-User": f"shots-{eng}-{size}"}, **kw); pg = c.new_page()
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(dev + "/"); pg.wait_for_selector("text=Upload", timeout=60000)
            for t in THEMES:
                pg.evaluate(f"window.chuvadiTheme.set('{t}')"); shot(pg, f"{eng}-{size}-home-{t}")
            pg.evaluate("window.chuvadiTheme.set('light')")
            try:
                with pg.expect_file_chooser(timeout=15000) as fc:
                    pg.locator("text=Upload").first.click()
                fc.value.set_files(pdf); pg.wait_for_selector(".rpage svg", timeout=60000)
            except Exception as e:
                notes.append((eng, size, "upload", str(e).splitlines()[0])); c.close(); continue
            for t in THEMES:
                pg.evaluate(f"window.chuvadiTheme.set('{t}')")
                for key, mode in (("1", "read"), ("2", "mark"), ("3", "arrange"), ("4", "protect")):
                    try:
                        pg.locator("body").press(key) if size != "phone" else pg.keyboard.press(key)
                    except Exception as e: notes.append((eng, size, mode, str(e).splitlines()[0]))
                    pg.wait_for_timeout(500)
                    shot(pg, f"{eng}-{size}-{mode}-{t}")
                    if mode == "arrange":  # Arrange may leave the Reader (Bench); come back
                        pg.go_back() if "/bench" in pg.url else None
                pg.keyboard.press("1"); pg.wait_for_timeout(300)
            pg.evaluate("window.chuvadiTheme.set('light')")
            # account menu
            try:
                pg.locator("button:has-text('Developer'), .acct-btn, [aria-label*='ccount' i]").first.click(timeout=5000)
                shot(pg, f"{eng}-{size}-account-light")
                pg.keyboard.press("Escape")
            except Exception as e: notes.append((eng, size, "account", str(e).splitlines()[0]))
            for name, path in (("settings", "/settings"), ("library", "/library")):
                try:
                    pg.goto(dev + path); pg.wait_for_timeout(1500); shot(pg, f"{eng}-{size}-{name}-light")
                except Exception as e: notes.append((eng, size, name, str(e).splitlines()[0]))
            if errs: notes.append((eng, size, "pageerror", errs[:3]))
            c.close()
        b.close()
json.dump(notes, open(os.path.join(out, "notes.json"), "w"), indent=1)
print("notes:", json.dumps(notes, indent=1)[:3000])
