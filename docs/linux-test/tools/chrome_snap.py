import sys
from playwright.sync_api import sync_playwright
W="/home/claude/uitest-build/wwwroot"; EV="/home/claude/evidence/lt/snap"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files","--force-device-scale-factor=1","--font-render-hinting=none"])
    pg=b.new_page(viewport={"width":1920,"height":1080})
    for n in sys.argv[1:]:
        pg.goto(f"file://{W}/snap-{n}.html"); pg.wait_for_timeout(1500)
        pg.evaluate("document.fonts.ready")
        print(n,"fonts loaded:", pg.evaluate("[...document.fonts].filter(f=>f.status=='loaded').map(f=>f.family).filter((v,i,a)=>a.indexOf(v)==i).join(', ')"))
        pg.screenshot(path=f"{EV}/chrome-{n}.png")
    b.close()
