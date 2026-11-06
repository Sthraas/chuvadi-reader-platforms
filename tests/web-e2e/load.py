"""Concurrency and load through the gateway (D-24), with real browsers. Test tool only (Playwright +
the machine's Chrome); run against a gateway with the Development sign-in, where each simulated
person is told apart by the X-Dev-User header.

Each person, all at once: opens the portal (their worker starts), uploads the PDF, waits for the page
to render, pages through it, prints the current page (the server assembles a PDF), then goes on paging
for a while. Measures each step, counts failures, and samples the memory of the gateway and every
worker process (from /proc) while everyone is active.

Usage: python3 load.py <portal base> <some.pdf> <out folder> <people> [--server-dir <publish folder>]
"""
import asyncio, json, os, statistics, sys, time
from playwright.async_api import async_playwright

base, pdf, out, people = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], int(sys.argv[4])
server_dir = sys.argv[sys.argv.index("--server-dir") + 1] if "--server-dir" in sys.argv else None


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
        t0 = time.time()
        await coro
        r["steps"][name] = round(time.time() - t0, 2)

    try:
        await step("open", page.goto(base + "/"))
        await step("ready", page.wait_for_selector("nav.leftbar >> text=Upload", timeout=90000))
        async with page.expect_file_chooser(timeout=30000) as fc:
            await page.click("nav.leftbar >> text=Upload")
        chooser = await fc.value
        t0 = time.time()
        await chooser.set_files(pdf)
        await page.wait_for_selector(".page svg, svg text", timeout=120000)
        r["steps"]["upload+render"] = round(time.time() - t0, 2)

        t0 = time.time()
        for _ in range(6):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(250)
        r["steps"]["paging"] = round(time.time() - t0, 2)

        await page.add_init_script("window.print = function () {};")
        await page.evaluate("window.print = function () {}")
        t0 = time.time()
        async with page.expect_response(lambda resp: "/portal/print/" in resp.url, timeout=60000) as pr:
            await page.keyboard.press("Control+p")
            await page.wait_for_selector("button.primary:has-text('Print')", timeout=30000)
            await page.click("button:has-text('Current')")
            await page.click("button.primary:has-text('Print')")
        resp = await pr.value
        r["steps"]["print"] = round(time.time() - t0, 2)
        if resp.status != 200:
            raise RuntimeError(f"print answered {resp.status}")

        for _ in range(10):  # stay busy while the others work
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(500)
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
        browser = await p.chromium.launch(channel="chrome", args=["--no-sandbox", "--disable-gpu"])
        sampling = asyncio.create_task(sampler(stop))
        t0 = time.time()
        await asyncio.gather(*(person(browser, n, results) for n in range(people)))
        wall = time.time() - t0
        stop.set()
        await sampling
        await browser.close()

    ok = [r for r in results if not r["error"]]
    summary = {"people": people, "succeeded": len(ok), "failed": len(results) - len(ok), "wall_s": round(wall, 1)}
    for name in ["ready", "upload+render", "paging", "print"]:
        values = [r["steps"][name] for r in ok if name in r["steps"]]
        if values:
            summary[name] = {"median_s": round(statistics.median(values), 2), "max_s": max(values)}
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
