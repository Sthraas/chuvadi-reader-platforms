// TESTING ONLY. B-33, second cause: with two Excel files open, the title bar pager works on each after switching
// between them (it went dead: the viewer component was reused and the reference to it stayed empty).
// usage: node sheet-pager-two.js PORT, desktop preview opened on two workbooks of several sheets each.
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:' + process.argv[2] + '/reader', { waitUntil: 'networkidle' }); await p.waitForSelector('.xv-canvas'); await p.waitForTimeout(1200);
  const st = () => p.evaluate(() => ({ active: document.querySelector('.rtab.active .rtab-name')?.textContent.trim(), box: document.querySelector('.tb-pg-box')?.value, total: document.querySelector('.tb-pg-total')?.textContent.trim(), tab: document.querySelector('.xv-tab.on')?.textContent.trim() }));
  const next = async () => { const n = p.locator('.tb-pager button[aria-label^="Next"]'); if (await n.isDisabled()) return 'disabled'; await n.click(); await p.waitForTimeout(900); return JSON.stringify(await st()); };
  console.log('start      ', JSON.stringify(await st()));
  console.log('next       ', await next());
  const names = await p.evaluate(() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim()));
  const other = names.filter(n => n.endsWith('.xlsx') && n !== names[names.length - 1])[0];
  await p.locator('.rtab', { hasText: other }).first().click(); await p.waitForTimeout(1500);
  console.log('other xlsx ', JSON.stringify(await st()));
  console.log('next       ', await next());
  console.log('next       ', await next());
  await p.locator('.rtab', { hasText: names[names.length - 1] }).first().click(); await p.waitForTimeout(1500);
  console.log('back       ', JSON.stringify(await st()));
  console.log('next       ', await next());
  await b.close(); })();
