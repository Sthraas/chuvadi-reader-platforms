import sys, time, zipfile, subprocess, os
from playwright.sync_api import sync_playwright
B="http://127.0.0.1:5290"
with sync_playwright() as p:
    for e in sys.argv[1:]:
        b=getattr(p,e).launch(); c=b.new_context(viewport={"width":1440,"height":900}, extra_http_headers={"X-Dev-User":"zip-"+e}, accept_downloads=True); pg=c.new_page()
        got=[]; pg.on("download", lambda d: got.append(d))
        pg.goto(B+"/"); pg.wait_for_selector("text=Upload")
        with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
        fc.value.set_files("/tmp/corpus/text-13.pdf"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(600)
        pg.click("header button:has-text('Document')"); pg.wait_for_timeout(400); pg.click("text=Split"); pg.wait_for_timeout(1200)
        pg.click("text=Use current: text-13.pdf"); pg.wait_for_timeout(1200)
        t0=time.time(); pg.click("button.tbtn-go:not([disabled])")
        while time.time()-t0<30 and not got: pg.wait_for_timeout(300)
        pg.wait_for_timeout(3000)
        names=[d.suggested_filename for d in got]
        res=f"{e}: {len(got)} download(s) {names} in {round(time.time()-t0,1)} s"
        if got and names[0].endswith(".zip"):
            zp=f"/tmp/explore/split-{e}.zip"; got[0].save_as(zp); z=zipfile.ZipFile(zp)
            ok=[]; 
            for i,n in enumerate(sorted(z.namelist()),1):
                open("/tmp/explore/_p.pdf","wb").write(z.read(n))
                t=subprocess.run(["pdftotext","/tmp/explore/_p.pdf","-"],capture_output=True,text=True).stdout.splitlines()
                pages=subprocess.run(["pdfinfo","/tmp/explore/_p.pdf"],capture_output=True,text=True).stdout
                ok.append(t[:1]==[f"Page {i} of 13"] and "Pages:           1" in pages)
            res+=f" | zip test {z.testzip() is None}, {len(z.namelist())} entries {sorted(z.namelist())[:2]}..., each right page: {all(ok)}"
        print(res, flush=True)
        # one-file save stays a PDF
        got.clear(); pg.goto(B+"/"); pg.wait_for_selector("text=Upload")
        with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
        fc.value.set_files("/tmp/corpus/text-3.pdf"); pg.wait_for_selector(".rpage svg"); pg.wait_for_timeout(600)
        pg.locator("body").press("2"); pg.wait_for_timeout(400)
        bx=pg.locator('.rpage-wrap[data-page="0"] .rpage').bounding_box()
        pg.click("button[aria-label='Rectangle']"); pg.mouse.move(bx['x']+100,bx['y']+200); pg.mouse.down(); pg.mouse.move(bx['x']+250,bx['y']+260,steps=6); pg.mouse.up()
        pg.click("button[aria-label='Save as new PDF']"); t0=time.time()
        while time.time()-t0<20 and not got: pg.wait_for_timeout(300)
        print(f"   one-file save -> {[d.suggested_filename for d in got]} failure={[d.failure() for d in got]}", flush=True)
        b.close()
