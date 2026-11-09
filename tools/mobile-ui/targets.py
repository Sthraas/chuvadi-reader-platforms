#!/usr/bin/env python3
# TESTING ONLY. Touch-target audit (D-37 / AT-06): every visible, enabled control on a screen should take
# a tap 21 px from its centre in each direction, directly or through mobile.js nearTarget (44 px areas).
#   targets.py <url> <W> <H> <path> <mode> [step "selector::text" ...] [shot.png]
#   mode: read | mark | protect | arrange | shelf | deskmenu | docmenu | viewsheet | home | lib | settings
import asyncio, sys
from playwright.async_api import async_playwright
url, W, H, path, mode = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
HIT = '''async () => { const m = await import('/_content/ChuvadiReader.Ui/js/mobile.js'); const out = [], R = 21;
  for (const e of document.querySelectorAll('button, a[href], input, select, [role=button]')) {
    if (e.disabled || e.closest('fieldset:disabled')) continue; const b = e.getBoundingClientRect(); if (!b.width || !b.height) continue;
    const st = getComputedStyle(e); if (st.visibility === 'hidden' || st.display === 'none') continue;
    const cx = b.left + b.width/2, cy = b.top + b.height/2;
    if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) continue;
    const top = document.elementFromPoint(cx, cy); if (!top || !(e === top || e.contains(top))) continue;   // covered
    const bad = [[R,0,'R'],[-R,0,'L'],[0,R,'D'],[0,-R,'U']].filter(([dx,dy]) => { const x=cx+dx, y=cy+dy;
      if (x<0||y<0||x>innerWidth||y>innerHeight) return false; const t=document.elementFromPoint(x,y); if (t && (t===e || e.contains(t))) return false; return m.nearTarget(x,y) !== e && !(t && t.tagName==='LABEL' && t.control===e); })
      .map(([dx,dy,n]) => { const t=document.elementFromPoint(cx+dx,cy+dy); return n+':'+(t?(String(t.className&&t.className.baseVal===undefined?t.className:t.tagName).split(' ')[0]||t.tagName):'-'); });
    const ok = !bad.length;
    if (!ok) out.push(bad.join(',') + ' ' + (e.className && e.className.baseVal === undefined ? '.'+String(e.className).split(' ')[0] : e.tagName) + ' ' + Math.round(b.width)+'x'+Math.round(b.height) + ' "' + (e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,18) + '"');
  } return out; }'''
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    pg=await (await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=True)).new_page()
    await pg.goto(url+path); await pg.wait_for_timeout(3500)
    if mode == "read" and await pg.evaluate("document.documentElement.dataset.shell")=="phone":
        await pg.locator(".ph-nav-b:nth-child(1)").click(); await pg.wait_for_timeout(900)
    phone = await pg.evaluate("document.documentElement.dataset.shell")=="phone"
    nav = {"read":1,"mark":2,"arrange":3,"shelf":3,"deskmenu":3,"protect":4,"docmenu":1,"viewsheet":1}
    if mode in nav and not (mode=="read"):
        n=nav[mode]
        await pg.locator(f".ph-nav-b:nth-child({n}), .lb-mode:nth-of-type({n})").first.click(); await pg.wait_for_timeout(1500)
    if mode == "shelf" and (phone or W < 1000):
        await pg.locator(".bench-shelf .shelf-head").first.tap(); await pg.wait_for_timeout(800)
    if mode == "deskmenu":
        await pg.locator(".desk-more").first.click(); await pg.wait_for_timeout(600)
    if mode == "docmenu":
        if phone: await pg.locator('.ph-bar button[aria-label="More"]').click()
        else: await pg.locator(".tb-doc").click()
        await pg.wait_for_timeout(600)
    if mode == "viewsheet" and phone:
        await pg.locator('.ph-bar button[aria-label="More"]').click(); await pg.wait_for_timeout(300)
        await pg.locator(".ph-row:has-text('View')").click(); await pg.wait_for_timeout(600)
    for step in [a for a in sys.argv[6:] if not a.endswith('.png')]:
        sel, _, txt = step.partition('::')
        loc = pg.locator(sel, has_text=txt) if txt else pg.locator(sel)
        try:
            await loc.first.click(timeout=4000)
        except Exception as ex:
            print("   step failed:", step); break
        await pg.wait_for_timeout(900)
    doc = await pg.evaluate("(()=>{const d=document.querySelector('.tb-doc'); if(!d) return 'absent'; const r=d.getBoundingClientRect(); return Math.round(r.width)+'x'+Math.round(r.height)+' at x'+Math.round(r.left)+' vis='+getComputedStyle(d).display})()")
    print(f"{W}x{H} {path} {mode}: Document button: {doc}")
    for x in sorted(set(await pg.evaluate(HIT))): print("   under 42:", x)
    if False: pass
    for a in sys.argv[6:]:
        if a.endswith('.png'): await pg.screenshot(path=a)
    await b.close()
asyncio.run(main())
