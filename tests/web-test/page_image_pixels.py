"""Pixel identity: old inline page images (data: URLs) vs new /_chvd/pages/<token>.png (D-158). Test tooling only.
python3 page_image_pixels.py <old base> <new base> <engine> <pdf>..."""
import base64, io, sys, hashlib
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
old, new, engine, pdfs = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4:]
H = "[...document.querySelectorAll('.rpage-wrap')].map(w => [w.dataset.page, (w.querySelector('.rpage svg image') || {getAttribute: () => ''}).getAttribute('href') || ''])"
def images(base, pdf, user):
    with sync_playwright() as p:
        b = getattr(p, engine).launch(); c = b.new_context(extra_http_headers={"X-Dev-User": user}, viewport={"width": 1400, "height": 900}); pg = c.new_page()
        pg.goto(base + "/"); pg.wait_for_selector("text=Upload")
        with pg.expect_file_chooser() as fc: pg.locator("text=Upload").first.click()
        fc.value.set_files(pdf)
        try: pg.wait_for_function("() => [...document.querySelectorAll('.rpage svg image')].length > 0", timeout=90000)
        except Exception: print("   no <image> page in", base, pdf.split('/')[-1]); b.close(); return {}
        n = pg.evaluate("document.querySelectorAll('.rpage-wrap').length"); out = {}
        for i in range(n):
            pg.evaluate(f"document.querySelector('.rpage-wrap[data-page=\"{i}\"]').scrollIntoView()")
            try: pg.wait_for_function(f"() => !!document.querySelector('.rpage-wrap[data-page=\"{i}\"] .rpage svg image')", timeout=30000)
            except Exception: continue
            pg.wait_for_timeout(400)
            href = dict(pg.evaluate(H)).get(str(i), "")
            if href.startswith("data:"): out[i] = base64.b64decode(href.split(",", 1)[1])
            elif href.startswith("_chvd/pages/"): out[i] = c.request.get(base + "/" + href).body()
        b.close(); return out
for pdf in pdfs:
    a = images(old, pdf, "px-old-" + engine); b_ = images(new, pdf, "px-new-" + engine)
    for i in sorted(set(a) | set(b_)):
        if i not in a or i not in b_: print(f"{pdf.split('/')[-1]} p{i + 1}: only in {'old' if i in a else 'new'}"); continue
        ia, ib = Image.open(io.BytesIO(a[i])).convert("RGBA"), Image.open(io.BytesIO(b_[i])).convert("RGBA")
        same = ia.size == ib.size and ImageChops.difference(ia, ib).getbbox() is None
        print(f"{pdf.split('/')[-1]} p{i + 1}: {ia.size} vs {ib.size} — pixels {'IDENTICAL' if same else 'DIFFER'}; png bytes {'identical' if a[i] == b_[i] else 'differ'} (sha {hashlib.sha256(a[i]).hexdigest()[:10]} / {hashlib.sha256(b_[i]).hexdigest()[:10]})")
