"""WT-27: a document dropped in the first moment after the page appears is not lost.

Before any of the page's own script has run, the test arranges a drop of two files at the earliest moment a
person could make one (the page's content has just been parsed; the portal's connection and its drop
catcher are not there yet): a PDF that isn't one, and a real PDF. Checks: the drop is cancelled (the browser
doesn't open the file and leave Chuvadi); once the page is ready the first file is refused with the upload's
own message and the second opens in the Reader; and a first-moment drop of an image alone is cancelled and
not uploaded (the catcher doesn't take images). On a fresh portal each engine's first visit is the slow one
(the person's worker is starting), which is where this used to be silent in Firefox.
Development sign-in.

Usage: python3 early_drop.py <portal base> <some.pdf> [--browser chrome|chromium|firefox|webkit]
"""
import base64
import sys

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as, sign_out

base, pdf = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []
real = base64.b64encode(open(pdf, "rb").read()).decode()

EARLY = """
(() => {
  const bytes = (b64) => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const files = %s;
  document.addEventListener('DOMContentLoaded', () => {
    const dt = new DataTransfer();
    for (const f of files) dt.items.add(new File([f.b64 ? bytes(f.b64) : f.text], f.name, { type: f.type }));
    const over = new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt });
    document.body.dispatchEvent(over);
    const drop = new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt });
    const cancelled = !document.body.dispatchEvent(drop);
    window.__early = { cancelled, catcher: !!document.querySelector('.pdrop input'), effect: dt.dropEffect };
  });
})();
"""


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail).replace("\n", " ") if detail != "" else ""))


def js_files(items):
    import json
    return json.dumps(items)


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()

    # --- documents, dropped before the catcher exists -----------------------------------------------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx, base, "early-" + engine)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script(EARLY % js_files([
        {"name": "fake.pdf", "type": "application/pdf", "text": "just text"},
        {"name": "early.pdf", "type": "application/pdf", "b64": real},
    ]))
    page.goto(base + "/")
    page.wait_for_function("() => window.__early", timeout=30000)
    early = page.evaluate("() => window.__early")
    check("the drop came before the catcher was there, and was cancelled (the browser stays on Chuvadi)",
          early["cancelled"] and not early["catcher"], early)
    try:
        page.wait_for_selector("text=fake.pdf isn't a valid PDF", timeout=30000)
        check("once the page is ready, the file that isn't a PDF is refused with the upload's message", True)
    except Exception as ex:  # noqa: BLE001
        check("once the page is ready, the file that isn't a PDF is refused with the upload's message", False, str(ex)[:120])
    try:
        page.wait_for_url("**/reader**", timeout=30000)
        page.wait_for_selector(".rpage", timeout=60000)
        name = page.locator(".rtab .rtab-name").all_inner_texts()
        check("... and the real PDF opens in the Reader", name == ["early.pdf"], name)
    except Exception as ex:  # noqa: BLE001
        check("... and the real PDF opens in the Reader", False, str(ex)[:120])
    check("no page errors", not errors, "; ".join(errors[:3]))
    sign_out(ctx, base)

    # --- an image alone is not kept ------------------------------------------------------------------------
    ctx2 = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(ctx2, base, "early-img-" + engine)
    page2 = ctx2.new_page()
    page2.add_init_script(EARLY % js_files([{"name": "photo.png", "type": "image/png", "text": "not really a picture"}]))
    page2.goto(base + "/")
    page2.wait_for_function("() => window.__early", timeout=30000)
    page2.wait_for_function("() => window.chvdPortal && window.chvdPortal.dropCatcherLive()", timeout=30000)
    page2.wait_for_timeout(2500)
    body = page2.locator("body").inner_text()
    check("a first-moment drop of an image alone is cancelled and not uploaded",
          page2.evaluate("() => window.__early.cancelled") and "photo.png" not in body and "/reader" not in page2.url)
    sign_out(ctx2, base)
    b.close()

sys.exit(0 if all(results) else 1)
