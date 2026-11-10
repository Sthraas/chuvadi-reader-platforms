// TESTING ONLY (never shipped). Linux fresh-open stall (bf60da9, step 36c's first run): a fresh app shows a small PDF at
// 115 %, then opens a heavy 5-sheet A1 drawing (POST /__preview/open). Passes when sheet 1 is drawn and fitted.
// Preview: ASPNETCORE_ENVIRONMENT=Development CHVD_FF=linux CHVD_OPEN=small.pdf. Usage: node fresh-open.js port drawing.pdf
const { chromium } = require('playwright');
(async () => {
  const port = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const log = [];
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('DBG')) log.push(m.text()); });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  await p.keyboard.press('Control+='); await p.waitForTimeout(300);
  const zoomBefore = await p.evaluate(() => document.querySelector('.rzoom-val, .tb-zoom, [class*=zoom]')?.textContent?.trim());
  const t0 = Date.now();
  await p.request.post(`http://127.0.0.1:${port}/__preview/open?path=${encodeURIComponent(process.argv[3])}`);
  let drawn = -1, fitted = null;
  for (let i = 0; i < 300; i++) {
    await p.waitForTimeout(100);
    const s = await p.evaluate(() => {
      const w = document.querySelector('.rpage-wrap[data-page="0"] .rpage');
      return { svg: !!(w && w.querySelector('svg')), w: w ? Math.round(w.getBoundingClientRect().width) : 0, h: w ? Math.round(w.getBoundingClientRect().height) : 0, pages: document.querySelectorAll('.rpage-wrap').length };
    });
    if (s.svg && s.pages === 5) { drawn = Date.now() - t0; await p.waitForTimeout(1500); fitted = await p.evaluate(() => { const r = document.querySelector('.rpage-wrap[data-page="0"] .rpage').getBoundingClientRect(); const d = document.querySelector('.rdesk'); return { w: Math.round(r.width), h: Math.round(r.height), deskW: d.clientWidth, deskH: d.clientHeight, fits: r.width <= d.clientWidth && r.height <= d.clientHeight }; }); break; }
    fitted = s;
  }
  console.log(JSON.stringify({ zoomBefore, drawnMs: drawn, page0: fitted, errors: log.slice(-12) }));
  await b.close();
})();
