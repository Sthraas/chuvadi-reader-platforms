// TESTING ONLY (never shipped). AT-24: on a phone in page-at-a-time with the keyboard up (a short screen, so a page
// fitted to the width is taller than the view), Find lands on the match's own page with the match on screen, five
// times in a row. Before: each page box was squeezed to the view's height, pages ran over the next one, and a match
// at a page's foot was drawn and shown on the next page. Fixture: fixtures/find-page3-foot.pdf (Android Test's
// drift document: "zephyrine" only at the foot of page 3).
// Usage: [H=520] node find-short-screen.js <port> phone|tablet   (preview opened on the fixture)
const { chromium } = require('playwright');
const [port, ff] = process.argv.slice(2);
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
(async () => {
  const b = await chromium.launch(); const mobile = ff === 'phone';
  const ctx = await b.newContext({ viewport: mobile ? { width: 412, height: +(process.env.H || 915) } : { width: 800, height: +(process.env.H || 1280) }, hasTouch: true, isMobile: mobile, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); const cdp = await ctx.newCDPSession(p);
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' }); await p.waitForSelector('.rdesk .rpage-wrap'); await p.waitForTimeout(2500);
  const state = () => p.evaluate(() => { const d = document.querySelector('.rdesk'), dt = d.getBoundingClientRect(); const cur = document.querySelector('.rfind-hl.cur'); const holder = cur && cur.closest('.rpage-wrap'); let on = null, best = 0; for (const w of d.querySelectorAll('.rpage-wrap')) { const r = w.getBoundingClientRect(); const vis = Math.min(r.bottom, dt.bottom) - Math.max(r.top, dt.top); if (vis > best) { best = vis; on = +w.getAttribute('data-page') + 1; } } const hr = cur && cur.getBoundingClientRect(), hw = holder && holder.getBoundingClientRect(); return { page: holder ? +holder.getAttribute('data-page') + 1 : null, onScreen: on, visible: !!hr && hr.top >= dt.top && hr.bottom <= dt.bottom, insideItsPage: !!hr && !!hw && hr.top >= hw.top - 1 && hr.bottom <= hw.bottom + 1 }; });
  const swipe = async () => { const y = 300; await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 300, y }] }); for (const x of [260, 200, 140, 90]) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] }); await p.waitForTimeout(16); } await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); };
  let good = 0; const seen = [];
  for (let t = 0; t < 5; t++) {
    await p.evaluate(() => fetch('/__preview/find?q=zephyrine', { method: 'POST' }));
    await p.waitForTimeout(2500);
    const s = await state(); seen.push(`${s.onScreen}${s.visible ? '' : '(hidden)'}${s.insideItsPage ? '' : '(outside its page)'}`);
    if (s.page === 3 && s.onScreen === 3 && s.visible && s.insideItsPage) good++;
    await swipe(); await p.waitForTimeout(800); await swipe(); await p.waitForTimeout(1200);
  }
  check(good === 5, `${ff} ${process.env.H || 'full'} px high: Find goes to page 3 with the match on screen and inside its own page, 5 of 5`, `${good} of 5; screen pages ${seen.join(', ')}`);
  console.log(fail === 0 ? 'ALL PASS' : `${fail} FAILED`); await b.close(); process.exit(fail ? 1 : 0);
})();
