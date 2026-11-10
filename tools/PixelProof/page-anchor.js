// TESTING ONLY (Linux finding 2, nineteenth patch). The page asked for stays in view when page heights change
// under it, as when the fit zoom lands after the first drawing. Desktop preview (ASPNETCORE_ENVIRONMENT=Development
// CHVD_FF=desktop), the 13-page sample active. Usage: node page-anchor.js [port]
const { chromium } = require('playwright');
const port = process.argv[2] || 5102;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  await p.waitForTimeout(800);
  // WebKit (Linux, macOS, iOS) has no CSS scroll anchoring; Chromium and WebView2 do, and would hide the bug.
  // Continuous scrolling (no page snapping), where a page's height follows the zoom.
  await p.evaluate(() => { const d = document.querySelector('.rdesk'); d.style.overflowAnchor = 'none'; d.classList.remove('snap'); });
  const topPage = () => p.evaluate(() => {
    const d = document.querySelector('.rdesk'), t = d.getBoundingClientRect().top + 2;
    for (const w of d.querySelectorAll('.rpage-wrap')) { const r = w.getBoundingClientRect(); if (r.bottom > t) return +w.dataset.page; }
    return -1;
  });
  const shown = () => p.evaluate(() => (document.querySelector('.rpg-in, input.rpage-in, .rnav input') || {}).value || '');
  const jump = (i) => p.evaluate(async (i) => {
    const m = await import('/_content/ChuvadiReader.Ui/js/reader.js');
    m.scrollToPage(document.querySelector('.rdesk'), i);
  }, i);
  const refit = (k) => p.evaluate((k) => {   // what a new fit does: every page's height changes at once
    const d = document.querySelector('.rdesk');
    const z = parseFloat(getComputedStyle(d).getPropertyValue('--rpage-zoom')) || 1;
    d.style.setProperty('--rpage-zoom', String(z * k));
  }, k);
  let fail = 0;
  const check = (name, got, want) => { const ok = got === want; if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}: page in view ${got + 1}, wanted ${want + 1}`); };

  // 1. Jump to page 7, settle, then the fit shrinks every page (A1 sheet landing: ~2,600 → ~1,000 px).
  await jump(6); await p.waitForTimeout(1600);
  await refit(0.43); await p.waitForTimeout(600);
  check('jump, then the fit shrinks the pages', await topPage(), 6);
  // 2. Jump to page 3 and the fit grows the pages while the jump is still scrolling.
  await jump(2); await p.waitForTimeout(120);
  await refit(1 / 0.43); await p.waitForTimeout(1800);
  check('fit changes during the jump', await topPage(), 2);
  // 3. Scroll by hand to page 10, then the heights change.
  await p.evaluate(() => { const d = document.querySelector('.rdesk'); const w = d.querySelector('.rpage-wrap[data-page="9"]'); d.scrollTop += w.getBoundingClientRect().top - d.getBoundingClientRect().top; });
  await p.waitForTimeout(500);
  await refit(0.6); await p.waitForTimeout(600);
  check('scrolled by hand, then the heights change', await topPage(), 9);
  // 4. Scroll with the wheel and a page changes size before the scrolling has settled (the anchor is taken 200 ms
  //    after scrolling stops): the view stays where the wheel took it, not back where it was.
  await p.mouse.move(700, 450);
  const before = await topPage();
  await p.mouse.wheel(0, 2400); await p.waitForTimeout(60);
  const wheeled = await topPage();
  await refit(1.02); await p.waitForTimeout(600);
  check('wheel, then a page changes size at once', await topPage(), wheeled);
  if (wheeled === before) { fail++; console.log('FAIL  the wheel did not move the view'); }
  await b.close();
  process.exit(fail ? 1 : 0);
})();
