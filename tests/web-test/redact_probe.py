from playwright.sync_api import sync_playwright
B="http://127.0.0.1:5093"
with sync_playwright() as p:
    b=p.firefox.launch(); c=b.new_context(viewport={"width":1440,"height":900}, extra_http_headers={"X-Dev-User":"edits2"}, accept_downloads=True); pg=c.new_page()
    pg.goto(B+"/"); pg.wait_for_selector("text=Upload")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files("/tmp/corpus/text-3.pdf"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(800)
    pg.locator("body").press("4"); pg.wait_for_timeout(400); pg.click("button[aria-label='Redact box']"); pg.wait_for_timeout(600)
    r=pg.evaluate("""()=>{const t=[...document.querySelectorAll('.rpage-wrap[data-page="0"] svg text, .rpage-wrap[data-page="0"] svg tspan')].find(e=>e.textContent.includes('Line 1:'));const b=t.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}}""")
    print("Line 1 at", r)
    pg.mouse.move(r['x']-4, r['y']-3); pg.mouse.down(); pg.mouse.move(r['x']+r['w']+4, r['y']+r['h']+3, steps=8); pg.mouse.up(); pg.wait_for_timeout(500)
    pg.screenshot(path="/tmp/explore/redact2-marked.png")
    with pg.expect_download(timeout=30000) as dl: pg.click("button[aria-label='Save redacted copy']")
    dl.value.save_as("/tmp/explore/out-redacted2.pdf"); print("saved", dl.value.suggested_filename)
    b.close()
