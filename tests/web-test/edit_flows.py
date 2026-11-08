import subprocess, json
from playwright.sync_api import sync_playwright
B="http://127.0.0.1:5093"
def drag(pg,x0,y0,x1,y1): pg.mouse.move(x0,y0); pg.mouse.down(); pg.mouse.move(x1,y1,steps=8); pg.mouse.up()
def open_doc(pg,f):
    pg.goto(B+"/"); pg.wait_for_selector("text=Upload")
    with pg.expect_file_chooser() as fc: pg.click("nav.leftbar >> text=Upload")
    fc.value.set_files(f); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(800)
    return pg.locator('.rpage-wrap[data-page="0"] .rpage').bounding_box()
def body(pg): return pg.evaluate("document.body.innerText")
with sync_playwright() as p:
    b=p.firefox.launch(); c=b.new_context(viewport={"width":1440,"height":900}, extra_http_headers={"X-Dev-User":"edits"}, accept_downloads=True); pg=c.new_page()
    # 1. Mark -> save as new
    bx=open_doc(pg,"/tmp/corpus/text-3.pdf"); pg.locator("body").press("2"); pg.wait_for_timeout(400)
    pg.click("button[aria-label='Rectangle']"); drag(pg,bx['x']+100,bx['y']+200,bx['x']+300,bx['y']+300)
    pg.click("button[aria-label='Text']"); pg.mouse.click(bx['x']+120,bx['y']+420); pg.wait_for_timeout(300); pg.keyboard.type("WEBTEST NOTE"); pg.keyboard.press("Escape")
    with pg.expect_download(timeout=30000) as dl: pg.click("button[aria-label='Save as new PDF']")
    dl.value.save_as("/tmp/explore/out-marked.pdf"); print("MARK saved", dl.value.suggested_filename)
    # 2. Protect -> redact box -> save redacted copy
    bx=open_doc(pg,"/tmp/corpus/text-3.pdf"); pg.locator("body").press("4"); pg.wait_for_timeout(400)
    pg.click("button[aria-label='Redact box']"); pg.wait_for_timeout(400)
    drag(pg,bx['x']+60,bx['y']+100,bx['x']+420,bx['y']+125)   # over Line 1/2 area
    pg.wait_for_timeout(500); pg.screenshot(path="/tmp/explore/redact-marked.png")
    try:
        with pg.expect_download(timeout=30000) as dl:
            pg.click("button[aria-label='Save redacted copy']"); pg.wait_for_timeout(1200)
            for t in ["Apply","Redact","Save","Continue"]:
                bt=pg.query_selector(f".card button.primary:has-text('{t}'), [role=dialog] button.primary:has-text('{t}')")
                if bt: print("redact card button:",t); bt.click(); break
        dl.value.save_as("/tmp/explore/out-redacted.pdf"); print("REDACT saved", dl.value.suggested_filename)
    except Exception as e:
        pg.screenshot(path="/tmp/explore/redact-fail.png"); print("REDACT failed:", str(e).splitlines()[0]); print([l for l in body(pg).splitlines() if 'edact' in l][:6])
    # 3. Protect -> Password
    open_doc(pg,"/tmp/corpus/text-3.pdf"); pg.locator("body").press("4"); pg.wait_for_timeout(400)
    pg.click("button[aria-label='Password']"); pg.wait_for_timeout(800); pg.screenshot(path="/tmp/explore/password-card.png")
    ins=pg.query_selector_all(".card input[type=password], [class*=card] input[type=password]"); print("password inputs:", len(ins))
    try:
        for i in ins: i.fill("webtest-open")
        with pg.expect_download(timeout=30000) as dl:
            pg.click(".card button.primary, [class*=card] button.primary")
        dl.value.save_as("/tmp/explore/out-password.pdf"); print("PASSWORD saved", dl.value.suggested_filename)
    except Exception as e:
        print("PASSWORD failed:", str(e).splitlines()[0]); pg.screenshot(path="/tmp/explore/password-fail.png")
    b.close()
