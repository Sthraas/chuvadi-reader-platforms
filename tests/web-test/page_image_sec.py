"""Security pass for the page-image endpoint /_chvd/pages/<token>.png (D-158). Web Test chat; test tooling only.
python3 page_image_sec.py <dev base> <out> <engine>     (gateway mode, Development sign-in)"""
import os, re, sys, time, json, collections, urllib.request
from playwright.sync_api import sync_playwright

base, out, engine = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
res = []
def check(name, ok, detail=""):
    res.append((name, bool(ok))); print(("PASS " if ok else "FAIL ") + f"[{engine}] {name}" + (f" — {str(detail)[:200]}" if detail != "" else ""), flush=True)

def large_pdf(path, pages=6):
    """Large-format pages (1300 x 1300 pt) with colour content, so they are drawn as images."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None]
    kids = []
    for i in range(pages):
        content = f"q {0.2 + 0.1 * i:.2f} 0.4 0.7 rg 50 50 1200 1200 re f Q q 1 0.8 0 rg {100 + 50 * i} 300 400 400 re f Q BT /F1 120 Tf 120 1100 Td (Page {i + 1}) Tj ET".encode()
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1300 1300] /Resources << /Font << /F1 {3 + 2 * pages} 0 R >> >> /Contents {len(objs) + 2} 0 R >>")
        kids.append(len(objs))
        objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {pages} >>"
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    body = b"%PDF-1.7\n"; offs = []
    for n, o in enumerate(objs, 1):
        offs.append(len(body)); body += f"{n} 0 obj\n".encode() + (o if isinstance(o, bytes) else o.encode()) + b"\nendobj\n"
    x = len(body)
    body += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    body += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    open(path, "wb").write(body)

def raw(path, headers=None, method="GET"):
    req = urllib.request.Request(base + path, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e: return e.code, dict(e.headers), e.read()

pdf = os.path.join(out, "large-6.pdf"); large_pdf(pdf)
HREFS = "() => [...document.querySelectorAll('.rpage svg image')].map(i => i.getAttribute('href') || i.getAttribute('xlink:href') || '')"
with sync_playwright() as p:
    b = getattr(p, engine).launch()
    A = b.new_context(extra_http_headers={"X-Dev-User": "pis-a-" + engine}, viewport={"width": 1400, "height": 900})
    a = A.new_page(); seen = []
    a.on("request", lambda r: seen.append((r.url, r.headers.get("referer"))) if "/_chvd/pages/" in r.url else None)
    a.goto(base + "/"); a.wait_for_selector("text=Upload")
    with a.expect_file_chooser() as fc: a.locator("text=Upload").first.click()
    fc.value.set_files(pdf)
    a.wait_for_function("() => [...document.querySelectorAll('.rpage svg image')].some(i => (i.getAttribute('href') || '').startsWith('_chvd/pages/'))", timeout=60000)
    a.wait_for_timeout(1500)
    hrefs = [h for h in a.evaluate(HREFS) if h.startswith("_chvd/pages/")]
    check("pages drawn as images come from /_chvd/pages/<token>.png", hrefs and all(re.fullmatch(r"_chvd/pages/[0-9a-f]{32}\.png", h) for h in hrefs), hrefs[:2])
    check("no data: URL images left in the page", not any(h.startswith("data:") for h in a.evaluate(HREFS)))
    path = "/" + hrefs[0]
    # owner, through the browser (cookies/headers as the page uses them)
    r = A.request.get(base + path)
    h = {k.lower(): v for k, v in r.headers.items()}
    check("owner gets 200 image/png", r.status == 200 and h.get("content-type", "").startswith("image/png"), (r.status, h.get("content-type")))
    check("Cache-Control private, no-store", set(x.strip() for x in h.get("cache-control", "").split(",")) == {"private", "no-store"}, h.get("cache-control"))
    check("nosniff + CORP same-origin", h.get("x-content-type-options") == "nosniff" and h.get("cross-origin-resource-policy") == "same-origin", (h.get("x-content-type-options"), h.get("cross-origin-resource-policy")))
    check("no CORS header on the owner's response", not any(k.startswith("access-control-") for k in h), [k for k in h if k.startswith("access-control-")])
    png_a = r.body()
    # referrer: the page's own fetches carry no Referer (Referrer-Policy no-referrer)
    check("image requests carry no Referer", seen and all(not ref for _, ref in seen), seen[:2])
    pol = raw("/", {"X-Dev-User": "pis-a-" + engine})[1]
    check("Reader page sends Referrer-Policy: no-referrer", {k.lower(): v for k, v in pol.items()}.get("referrer-policy") == "no-referrer")
    # other person, signed out, cross-site, foreign origin
    s, hh, body = raw(path, {"X-Dev-User": "pis-b-" + engine}); check("another signed-in person: 404", s == 404, s)
    s, hh, body = raw(path); check("signed-out request: 404", s == 404, (s, hh.get("Location")))
    for name, hdr in [("Sec-Fetch-Site: cross-site", {"Sec-Fetch-Site": "cross-site"}), ("Sec-Fetch-Site: same-site", {"Sec-Fetch-Site": "same-site"}),
                      ("foreign Origin", {"Origin": "https://evil.example"}), ("Origin null", {"Origin": "null"})]:
        s, hh, _ = raw(path, {"X-Dev-User": "pis-a-" + engine, **hdr})
        check(f"owner's token with {name}: 404", s == 404, s)
    s, hh, _ = raw(path, {"X-Dev-User": "pis-a-" + engine, "Sec-Fetch-Site": "same-origin", "Origin": base})
    check("owner, same-origin marks: 200", s == 200, s)
    s, hh, _ = raw(path, {"X-Dev-User": "pis-a-" + engine, "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}, method="OPTIONS")
    check("CORS preflight: no Access-Control-Allow-*", not any(k.lower().startswith("access-control-allow") for k in hh), (s, [k for k in hh if k.lower().startswith("access-control")]))
    # malformed addresses: all 404, never 500
    tok = path.split("/")[-1][:32]
    bad = [tok.upper() + ".png", tok[:31] + ".png", tok + "0.png", tok + ".PNG", tok + ".png.png", tok, tok + ".png%00", "..%2f..%2fappsettings.json",
           "%2e%2e/%2e%2e/etc/passwd", tok + ".png?x=1", tok + ".png/", "0" * 32 + ".png", tok + ".jpg", "../" + tok + ".png"]
    codes = {}
    for x in bad:
        s, _, _ = raw("/_chvd/pages/" + x, {"X-Dev-User": "pis-a-" + engine}); codes[x[:40]] = s
    ok_codes = {k: v for k, v in codes.items() if not (k.startswith(tok) and (k.endswith("?x=1") or k.endswith(".png/")))}
    check("malformed / traversal / near-miss addresses: 404 (400 for a NUL), never 5xx", all(v in (404, 400) for v in ok_codes.values()) and not any(v >= 500 for v in codes.values()), codes)
    # token quality: collect tokens over several opens
    toks = set(h.split("/")[-1][:32] for h in hrefs)
    for i in range(6):
        a.evaluate(f"document.querySelector('.rpage-wrap[data-page=\"{i}\"]').scrollIntoView()"); a.wait_for_timeout(900)
        toks |= set(h.split("/")[-1][:32] for h in a.evaluate(HREFS) if h.startswith("_chvd/pages/"))
    bits = "".join(bin(int(t, 16))[2:].zfill(128) for t in toks)
    ones = bits.count("1") / len(bits)
    pref = collections.Counter(t[:4] for t in toks).most_common(1)[0][1]
    check(f"tokens: 128-bit hex, all distinct, no shared prefix ({len(toks)} seen)", len(toks) >= 5 and all(len(t) == 32 for t in toks) and pref == 1 and 0.4 < ones < 0.6, f"ones={ones:.3f}")
    # freed when pages are dropped (scroll far away), and at close
    first_tokens = [h.split("/")[-1][:32] for h in hrefs]
    a.evaluate("document.querySelector('.rpage-wrap[data-page=\"5\"]').scrollIntoView()"); a.wait_for_timeout(2500)
    still = {t: raw(f"/_chvd/pages/{t}.png", {"X-Dev-User": "pis-a-" + engine})[0] for t in first_tokens}
    print(f"   after scrolling to the last page, page-1 tokens answer: {still}")
    try:
        a.locator("header button[aria-label^='Close'], header [title^='Close']").first.click(timeout=5000)
    except Exception as e: print("   close click:", str(e).splitlines()[0])
    a.wait_for_timeout(1500)
    after = {t[:8]: raw(f"/_chvd/pages/{t}.png", {"X-Dev-User": "pis-a-" + engine})[0] for t in list(toks)}
    check("after the tab closes every token is 404", all(v == 404 for v in after.values()), after)
    json.dump({"tokens": sorted(toks), "first": first_tokens}, open(os.path.join(out, f"tokens-{engine}.json"), "w"))
    open(os.path.join(out, f"page1-{engine}.png"), "wb").write(png_a)
    b.close()
print(f"{sum(ok for _, ok in res)}/{len(res)} pass")
