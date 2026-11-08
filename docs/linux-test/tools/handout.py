from playwright.sync_api import sync_playwright
H="/home/claude/chuvadi-reader-platforms/docs/design-handoff/Reader Side Rails.dc.html"; EV="/home/claude/evidence/lt/snap"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files"])
    pg=b.new_page(viewport={"width":1600,"height":1000}); pg.goto("file://"+H); pg.wait_for_timeout(4000)
    frames=pg.evaluate("""[...document.querySelectorAll('[data-frame], .frame, [class*=frame]')].filter(e=>e.getBoundingClientRect().width>600).slice(0,40).map(e=>{const r=e.getBoundingClientRect();return {cls:e.className.toString().slice(0,40),t:(e.querySelector('h1,h2,h3,.title,[class*=title]')||{}).textContent,x:r.x,y:r.y+scrollY,w:r.width,h:r.height}})""")
    for f in frames[:40]: print(f)
    pg.screenshot(path=EV+"/handout-full.png", full_page=True)
    b.close()
