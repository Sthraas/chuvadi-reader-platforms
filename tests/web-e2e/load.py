"""Concurrency and load through the gateway (D-24), with real browsers. Test tool only (Playwright +
the machine's Chrome); run against a gateway with the Development sign-in, where each simulated
person is told apart by the X-Dev-User header.

Each person, all at once: opens the portal (their worker starts), uploads the PDF, waits for page 1 to
be drawn, pages through it (each step timed until the next page is drawn and in view, no fixed waits),
prints the current page (the server assembles a PDF), then goes on paging for a while. Measures each
step, counts failures, and samples the memory of the gateway and every worker process (from /proc).

Each person gets their own browser process by default (WT-13), so one person's page work doesn't slow
another's in the client and get counted as server time. `--browsers N` shares N processes between
everyone, for big runs on a small client machine. The PDF needs at least 8 pages. Times are in ms.

Usage: python3 load.py <portal base> <some.pdf> <out folder> <people> [--browsers N] [--server-dir <publish folder>]
"""
import asyncio, json, os, statistics, sys, time
from playwright.async_api import async_playwright

base, pdf, out, people = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], int(sys.argv[4])
server_dir = sys.argv[sys.argv.index("--server-dir") + 1] if "--server-dir" in sys.argv else None
browsers = int(sys.argv[sys.argv.index("--browsers") + 1]) if "--browsers" in sys.argv else people
os.makedirs(out, exist_ok=True)  # WT-13: the results file and failure screenshots go here

# Page i (0-based) is drawn (its SVG has content) and at least partly in view.
DRAWN = """(i) => { const w = document.querySelector('.rpage-wrap[data-page="' + i + '"]');
  if (!w) return false; const s = w.querySelector('.rpage svg'); if (!s || s.childElementCount === 0) return false;
  const r = w.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }"""
NEXT = "button.tb-pg-btn[aria-label='Next page']"


def rss_mb(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        return None


def portal_processes():
    """Gateway and workers: dotnet or app-host processes running from the publish folder."""
    found = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
            env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
        except OSError:
            continue
        if not any(b"ChuvadiReader.Web" in c for c in cmd):
            continue
        cwd = os.readlink(f"/proc/{pid}/cwd") if os.path.exists(f"/proc/{pid}/cwd") else ""
        if server_dir and not cwd.startswith(server_dir.rstrip('/')):
            continue
        role = "worker" if b"Portal__Mode=Worker" in env else "gateway"
        found[int(pid)] = role
    return found


samples = []


async def sampler(stop):
    while not stop.is_set():
        procs = portal_processes()
        mem = {pid: rss_mb(pid) for pid in procs}
        samples.append({
            "t": time.time(),
            "gateway_mb": sum(m or 0 for p, m in mem.items() if procs[p] == "gateway"),
            "workers": sum(1 for p in procs if procs[p] == "worker"),
            "workers_mb": sum(m or 0 for p, m in mem.items() if procs[p] == "worker"),
        })
        try:
            await asyncio.wait_for(stop.wait(), 1.0)
        except asyncio.TimeoutError:
            pass


async def person(browser, n, results):
    r = {"person": n, "steps": {}, "error": None}
    results.append(r)
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, extra_http_headers={"X-Dev-User": f"load-{n:03d}"})
    page = await ctx.new_page()
    page_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    async def step(name, coro):
        t0 = time.perf_counter()
        await coro
        r["steps"][name] = round((time.perf_counter() - t0) * 1000)

    async def next_page(i):
        """Next page, until page i (0-based) is drawn and in view."""
        await page.locator(NEXT).first.click()
        await page.wait_for_function(DRAWN, arg=i, timeout=60000, polling="raf")

    try:
        await step("open", page.goto(base + "/"))
        await step("ready", page.wait_for_selector("nav.leftbar >> text=Upload", timeout=90000))
        async with page.expect_file_chooser(timeout=30000) as fc:
            await page.click("nav.leftbar >> text=Upload")
        chooser = await fc.value
        t0 = time.perf_counter()
        await chooser.set_files(pdf)
        await page.wait_for_function(DRAWN, arg=0, timeout=120000, polling="raf")
        r["steps"]["upload+render"] = round((time.perf_counter() - t0) * 1000)

        turns = []  # one value per page turn
        for i in range(1, 7):
            t0 = time.perf_counter()
            await next_page(i)
            turns.append(round((time.perf_counter() - t0) * 1000))
        r["steps"]["page_turn"] = round(statistics.median(turns))
        r["page_turns"] = turns

        await page.add_init_script("window.print = function () {};")
        await page.evaluate("window.print = function () {}")
        t0 = time.perf_counter()
        async with page.expect_response(lambda resp: "/portal/print/" in resp.url, timeout=60000) as pr:
            await page.keyboard.press("Control+p")
            await page.wait_for_selector("button.primary:has-text('Print')", timeout=30000)
            await page.click("button:has-text('Current')")
            await page.click("button.primary:has-text('Print')")
        resp = await pr.value
        r["steps"]["print"] = round((time.perf_counter() - t0) * 1000)
        if resp.status != 200:
            raise RuntimeError(f"print answered {resp.status}")

        await page.keyboard.press("Escape")
        for i in range(7, 7 + 10):  # stay busy while the others work (not timed)
            try:
                await next_page(i)
            except Exception:  # noqa: BLE001 - past the last page: go back to the start
                await page.locator("input.tb-pg-box").first.fill("1")
                await page.locator("input.tb-pg-box").first.press("Enter")
        if page_errors:
            raise RuntimeError("page errors: " + "; ".join(page_errors[:2]))
    except Exception as e:  # noqa: BLE001 - a test tool reports every failure
        r["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        try:
            await page.screenshot(path=os.path.join(out, f"load-fail-{n:03d}.png"))
        except Exception:  # noqa: BLE001
            pass
    finally:
        await ctx.close()


async def main():
    results = []
    stop = asyncio.Event()
    async with async_playwright() as p:
        pool = [await p.chromium.launch(channel="chrome", args=["--no-sandbox", "--disable-gpu"]) for _ in range(max(1, min(browsers, people)))]
        sampling = asyncio.create_task(sampler(stop))
        t0 = time.perf_counter()
        await asyncio.gather(*(person(pool[n % len(pool)], n, results) for n in range(people)))
        wall = time.perf_counter() - t0
        stop.set()
        await sampling
        for b in pool:
            await b.close()

    ok = [r for r in results if not r["error"]]
    summary = {"people": people, "browsers": len(pool), "succeeded": len(ok), "failed": len(results) - len(ok), "wall_ms": round(wall * 1000)}
    for name in ["ready", "upload+render", "page_turn", "print"]:
        values = [r["steps"][name] for r in ok if name in r["steps"]]
        if values:
            summary[name] = {"median_ms": round(statistics.median(values)), "max_ms": max(values)}
    if samples:
        peak = max(samples, key=lambda s: s["gateway_mb"] + s["workers_mb"])
        summary["peak"] = {"workers": peak["workers"], "gateway_mb": round(peak["gateway_mb"]), "workers_mb": round(peak["workers_mb"]),
                           "per_worker_mb": round(peak["workers_mb"] / peak["workers"]) if peak["workers"] else None}
    summary["errors"] = [r["error"] for r in results if r["error"]][:5]
    with open(os.path.join(out, f"load-{people}.json"), "w") as f:
        json.dump({"summary": summary, "results": results, "samples": samples}, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0 if summary["failed"] == 0 else 1


sys.exit(asyncio.run(main()))
