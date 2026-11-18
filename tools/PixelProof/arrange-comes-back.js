// TESTING ONLY (never shipped). D-203: the desks kept by Save at the last close come back the first time Arrange is
// opened in the next run, and Reset clears them for the run after. Run after close-guard-arrange.js desktop, on a
// fresh preview started with CHVD_KEEP_ARRANGE=1. Usage: node arrange-comes-back.js <port> first|after-reset
const { chromium } = require('playwright');
const [port, stage] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  const unsaved0 = await fetch(base + '/__preview/unsaved').then(r => r.json());
  check(unsaved0.hasUnsavedWork === false, 'at the start nothing is asked about (Arrange not opened yet)', JSON.stringify(unsaved0));
  await p.goto(base + '/bench', { waitUntil: 'networkidle' }); await p.waitForTimeout(2500);
  const desks = await p.evaluate(() => [...document.querySelectorAll('.bt-bind')].length);
  const pages = await p.evaluate(() => document.querySelectorAll('.bpage[data-bench-id]').length);
  if (stage === 'first') {
    check(desks >= 2 && pages >= 16, 'both kept desks are back (4 + 12 pages)', `desks with a Bind button ${desks}, page cards ${pages}`);
    const u = await fetch(base + '/__preview/unsaved').then(r => r.json());
    check(u.hasUnsavedWork === false, 'and, as kept, they are not asked about', JSON.stringify(u));
    await p.screenshot({ path: 'arrange-comes-back.png' });
    await p.locator('button[aria-label="Reset bench"]').click(); await p.waitForTimeout(500);
    const text = await p.evaluate(() => (document.querySelector('.modal-body') || {}).textContent || '');
    check(/here and the next time the app starts/.test(text), 'Reset says it clears the desks for the next start too', text);
    await p.locator('.modal-foot button', { hasText: 'Clear bench' }).click(); await p.waitForTimeout(800);
  } else {
    check(pages === 0, 'after Reset, the next start brings nothing back', `page cards ${pages}`);
  }
  check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
  await b.close(); process.exit(fail ? 1 : 0);
})();
