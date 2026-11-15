// The title bar arrows and number box on an Excel file change the sheet shown, not only the number (B-33).
// usage: node sheet-pager.js PORT, with the desktop preview open on a workbook of several sheets.
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); p.on('pageerror', e => errs.push(String(e)));
  await p.goto('http://127.0.0.1:' + process.argv[2] + '/reader', { waitUntil: 'networkidle' }); await p.waitForSelector('.xv-canvas'); await p.waitForTimeout(1200);
  const st = () => p.evaluate(() => ({
    pager: [...document.querySelectorAll('.tb-pager button')].map(x => x.getAttribute('aria-label') + (x.disabled ? ' [disabled]' : '')),
    box: document.querySelector('.tb-pg-box')?.value, total: document.querySelector('.tb-pg-total')?.textContent,
    tabs: [...document.querySelectorAll('.xv-tab')].map(t => t.textContent.trim() + (t.classList.contains('on') ? '*' : '')),
    a1: document.querySelector('.xv-cell[data-a="A1"]')?.textContent,
    other: [...document.querySelectorAll('button')].filter(x => /prev|next/i.test((x.getAttribute('aria-label') || '') + (x.title || ''))).map(x => (x.getAttribute('aria-label') || x.title) + ' @' + x.className) }));
  console.log('start', JSON.stringify(await st()));
  for (const step of ['Next', 'Next', 'Previous']) {
    const btn = p.locator('.tb-pager button[aria-label^="' + step + '"]');
    if (await btn.isDisabled()) { console.log(step, 'is disabled'); continue; }
    await btn.click(); await p.waitForTimeout(900); const s = await st(); console.log(step, s.box, s.total, JSON.stringify(s.tabs), s.a1);
  }
  // the number box
  await p.fill('.tb-pg-box', '1'); await p.keyboard.press('Enter'); await p.waitForTimeout(800); let s = await st(); console.log('box=1', s.box, JSON.stringify(s.tabs));
  // click a sheet tab then see the pager follow
  const tabs = p.locator('.xv-tab'); if (await tabs.count() > 1) { await tabs.nth(1).click(); await p.waitForTimeout(800); s = await st(); console.log('tab2 clicked', s.box, JSON.stringify(s.tabs)); }
  await p.screenshot({ path: 'pager.png', clip: { x: 0, y: 0, width: 1440, height: 160 } });
  console.log('errors', JSON.stringify(errs.slice(0, 5))); await b.close(); })();
