"""Load and speed in milliseconds (Web Test chat; test tooling only, never shipped).

python3 perf.py <base> <pdf> <out folder> <people> [--browser chromium|firefox|webkit] [--server-dir <publish>]

Per person (own browser context, Development sign-in X-Dev-User, gateway mode):
  ttfb_ms        navigation start -> first byte of /
  fcp_ms         navigation start -> first contentful paint (first rendered frame)
  ready_ms       navigation start -> left bar interactive (Blazor circuit up, worker started)
  first_page_ms  file handed to the chooser -> page 1 drawn (svg with content in .rpage-wrap[data-page=0])
  jump_ms        type 10 in the page box + Enter -> page 10 drawn and in view
  next_ms        next-page button -> page 11 drawn and in view
Memory: gateway RSS, worker count, total and per-worker RSS (peak), sampled every 250 ms.
"""
import asyncio, json, os, statistics, sys, time
from playwright.async_api import async_playwright

base, pdf, out, people = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], int(sys.argv[4])
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chromium"
server_dir = sys.argv[sys.argv.index("--server-dir") + 1] if "--server-dir" in sys.argv else None
os.makedirs(out, exist_ok=True)

def rss_mb(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"): return int(line.split()[1]) / 1024
    except OSError: return 0
    return 0

def procs():
    found = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read()
            if b"ChuvadiReader.Web" not in cmd: continue
            env = open(f"/proc/{pid}/environ", "rb").read()
        except OSError: continue
        found[int(pid)] = "worker" if b"Portal__Mode=Worker" in env else "gateway"
    return found

samples = []
async def sampler(stop):
    while not stop.is_set():
        p = procs(); m = {k: rss_mb(k) for k in p}
        w = [m[k] for k in p if p[k] == "worker"]
        samples.append({"gw": sum(m[k] for k in p if p[k] == "gateway"), "n": len(w), "wsum": sum(w), "wmax": max(w, default=0)})
        try: await asyncio.wait_for(stop.wait(), 0.25)
        except asyncio.TimeoutError: pass

DRAWN = """(i) => { const w = document.querySelector('.rpage-wrap[data-page="' + i + '"]');
  if (!w) return false; const s = w.querySelector('.rpage svg'); if (!s || s.childElementCount === 0) return false;
  const r = w.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }"""

async def person(browser, n, results):
    r = {"person": n, "error": None}; results.append(r)
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": f"perf-{n:03d}"})
    page = await ctx.new_page()
    try:
        await page.goto(base + "/", wait_until="commit")
        await page.wait_for_selector("nav.leftbar >> text=Upload", timeout=120000)
        nav = await page.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0];
            const f = performance.getEntriesByName('first-contentful-paint')[0];
            return { ttfb: n.responseStart, fcp: f ? f.startTime : null, ready: performance.now() }; }""")
        r["ttfb_ms"], r["fcp_ms"], r["ready_ms"] = round(nav["ttfb"]), round(nav["fcp"] or -1), round(nav["ready"])
        async with page.expect_file_chooser(timeout=30000) as fc:
            await page.click("nav.leftbar >> text=Upload")
        ch = await fc.value
        t0 = time.perf_counter()
        await ch.set_files(pdf)
        await page.wait_for_function(DRAWN, arg=0, timeout=120000, polling="raf")
        r["first_page_ms"] = round((time.perf_counter() - t0) * 1000)
        box = page.locator("input.tb-pg-box").first
        await box.fill("10"); t0 = time.perf_counter(); await box.press("Enter")
        await page.wait_for_function(DRAWN, arg=9, timeout=60000, polling="raf")
        r["jump_ms"] = round((time.perf_counter() - t0) * 1000)
        nxt = page.locator("button.tb-pg-btn[aria-label='Next page']").first
        t0 = time.perf_counter(); await nxt.click()
        await page.wait_for_function(DRAWN, arg=10, timeout=60000, polling="raf")
        r["next_ms"] = round((time.perf_counter() - t0) * 1000)
    except Exception as e:
        r["error"] = str(e).splitlines()[0][:200]
        try: await page.screenshot(path=os.path.join(out, f"fail-{n:03d}.png"))
        except Exception: pass
    finally:
        await ctx.close()

def stat(results, k):
    v = [r[k] for r in results if r.get(k) is not None and r.get(k, -1) >= 0]
    if not v: return None
    v.sort()
    return {"median": round(statistics.median(v)), "p90": v[min(len(v) - 1, int(len(v) * 0.9))], "max": v[-1], "min": v[0]}

async def main():
    stop = asyncio.Event(); s = asyncio.create_task(sampler(stop))
    async with async_playwright() as p:
        b = await getattr(p, engine).launch()
        results = []; t0 = time.perf_counter()
        await asyncio.gather(*(person(b, i, results) for i in range(people)))
        wall = time.perf_counter() - t0
        await b.close()
    stop.set(); await s
    peak = max(samples, key=lambda x: x["wsum"]) if samples else {}
    rep = {"people": people, "engine": engine, "pdf": os.path.basename(pdf),
           "succeeded": sum(1 for r in results if not r["error"]), "wall_ms": round(wall * 1000),
           **{k: stat(results, k) for k in ("ttfb_ms", "fcp_ms", "ready_ms", "first_page_ms", "jump_ms", "next_ms")},
           "peak_workers": max((x["n"] for x in samples), default=0),
           "peak_gateway_mb": round(max((x["gw"] for x in samples), default=0)),
           "peak_workers_total_mb": round(peak.get("wsum", 0)),
           "peak_largest_worker_mb": round(max((x["wmax"] for x in samples), default=0)),
           "per_worker_mb_at_peak": round(peak["wsum"] / peak["n"]) if peak.get("n") else None,
           "errors": [(r["person"], r["error"]) for r in results if r["error"]]}
    json.dump({"summary": rep, "people": results}, open(os.path.join(out, f"perf-{people}-{engine}.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
    return 0 if rep["succeeded"] == people else 1

sys.exit(asyncio.run(main()))
