from playwright.sync_api import sync_playwright
B="http://127.0.0.1:5093"
with sync_playwright() as p:
    b=p.firefox.launch(); c=b.new_context(viewport={"width":1440,"height":900}, extra_http_headers={"X-Dev-User":"split2"}, accept_downloads=True); pg=c.new_page()
    pg.goto(B+"/"); pg.wait_for_selector("text=Upload")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(600)
    pg.click("header button:has-text('Document')"); pg.wait_for_timeout(500)
    print("menu:", [x.strip() for x in pg.evaluate("[...document.querySelectorAll('[role=menu] *, .dmenu *, .menu-pop *')].filter(e=>e.children.length==0&&e.offsetParent).map(e=>e.textContent)") if x.strip()][:25])
    pg.click("text=Split"); pg.wait_for_timeout(1500); pg.screenshot(path="/tmp/explore/split-card.png")
    print("url", pg.url, "| buttons:", pg.evaluate("[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&!b.disabled).map(b=>b.innerText.trim()).filter(x=>x&&x.length<40).slice(-15)"))
    pg.click("text=Use current: text-13.pdf"); pg.wait_for_timeout(1500); pg.screenshot(path="/tmp/explore/split-2.png")
    print("after use current:", pg.evaluate("[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&!b.disabled).map(b=>b.innerText.trim()).filter(x=>x&&x.length<40).slice(-12)"))
    go=pg.query_selector("button.tbtn-go:not([disabled])")
    if go:
        got=[]; pg.on("download", lambda d: got.append(d.suggested_filename))
        import time; t0=time.time(); go.click()
        while time.time()-t0 < 60 and len(got) < 13: pg.wait_for_timeout(500)
        print("SPLIT downloads:", len(got), "in", round(time.time()-t0,1), "s", sorted(got)[:3], "...")
    b.close()
