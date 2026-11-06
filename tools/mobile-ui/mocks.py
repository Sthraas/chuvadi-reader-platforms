#!/usr/bin/env python3
# TESTING / DESIGN ONLY. Renders each mock phone frame in docs/mobile-ui/mocks/phone-screens.html to
# a PNG (392 × 816), plus one overview per screen: today | option A | option B.
#   mocks.py <today-dir with phone-home/library/settings-392x816.png> <out-dir>
import asyncio, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "docs", "mobile-ui", "mocks", "phone-screens.html")
today, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
IDS = ["home-a", "home-b", "library-a", "library-b", "settings-a", "settings-b"]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=1)
        await pg.goto("file://" + os.path.abspath(PAGE)); await pg.wait_for_timeout(2500)
        for i in IDS:
            await pg.locator(f"#{i}").screenshot(path=os.path.join(out, f"mock-{i}.png"))
        await b.close()

asyncio.run(main())
for screen in ["home", "library", "settings"]:
    ims = [("Today (no phone layout)", os.path.join(today, f"phone-{screen}-392x816.png")),
           ("Option A", os.path.join(out, f"mock-{screen}-a.png")),
           ("Option B", os.path.join(out, f"mock-{screen}-b.png"))]
    c = Image.new("RGB", (392 * 3 + 40, 816 + 34), "#9a948a"); d = ImageDraw.Draw(c)
    for k, (label, path) in enumerate(ims):
        x = k * 412
        c.paste(Image.open(path).convert("RGB"), (x, 34)); d.text((x + 4, 10), label, fill="white")
    c.save(os.path.join(out, f"{screen}-options.png"))
print("done")
