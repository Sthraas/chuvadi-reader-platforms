"""D-158: drawn pages by address on the portal, through the gateway and the person's worker.

Builds a large-format PDF (1300 x 1300 pt, drawn as an image), opens it as one person and checks: the page's
image comes from /_chvd/pages/<token>.png, 200, image/png, private and no-store; another signed-in person
asking for the same address gets 404; once the tab is closed the owner gets 404 too. Development sign-in.

Usage: python3 page_images.py <portal base> <out folder> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys

from playwright.sync_api import sync_playwright

base, out = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
os.makedirs(out, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + detail if detail else ""))


def large_format_pdf(path):
    content = b"".join(b"%d 0 m %d 1300 l " % (x, x) for x in range(0, 1300, 20)) + b"S"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1300 1300] /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"]
    data, offsets = b"%PDF-1.7\n", []
    for n, o in enumerate(objs, 1):
        offsets.append(len(data))
        data += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    data += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    open(path, "wb").write(data)


pdf = os.path.join(out, "large-format.pdf")
large_format_pdf(pdf)

with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()
    owner = b.new_context(extra_http_headers={"X-Dev-User": "img-owner-" + engine}, viewport={"width": 1400, "height": 900})
    other = b.new_context(extra_http_headers={"X-Dev-User": "img-other-" + engine})
    page = owner.new_page()
    seen = []
    page.on("response", lambda r: seen.append(r) if "/_chvd/pages/" in r.url else None)
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("text=Upload a file")
    fc.value.set_files(pdf)
    page.wait_for_url("**/reader**", timeout=30000)
    try:
        page.wait_for_function("() => [...document.querySelectorAll('.rpage svg image')].some(i => (i.getAttribute('href') || '').startsWith('_chvd/pages/'))", timeout=60000)
        page.wait_for_timeout(1500)
        href = page.evaluate("() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href')).find(h => h.startsWith('_chvd/pages/'))")
    except Exception as ex:  # noqa: BLE001
        href = None
        check("the large-format page is drawn from an address", False, str(ex)[:120])
    if href:
        url = base + "/" + href
        check("the page's image is drawn from /_chvd/pages/<32 hex>.png", len(href) == len("_chvd/pages/") + 32 + 4, href)
        r = next((x for x in seen if x.url == url), None)
        check("the browser got it: 200, image/png, private and no-store",
              r is not None and r.status == 200 and r.headers.get("content-type") == "image/png"
              and "no-store" in r.headers.get("cache-control", "") and "private" in r.headers.get("cache-control", ""),
              "" if r is None else "%d %s %s" % (r.status, r.headers.get("content-type"), r.headers.get("cache-control")))
        drawn = page.evaluate("() => { const i = [...document.querySelectorAll('.rpage svg image')].find(i => (i.getAttribute('href') || '').startsWith('_chvd/pages/')); return i ? i.getBBox().width > 100 : false; }")
        check("the image shows on the page", drawn)
        check("another signed-in person asking for that address gets 404", other.request.get(url).status == 404)
        check("the owner asking again directly gets it", owner.request.get(url).status == 200)
        page.click("button.rtab-x")
        page.wait_for_timeout(2000)
        check("after the tab is closed the owner gets 404 too", owner.request.get(url).status == 404)
    b.close()

sys.exit(0 if all(results) else 1)
