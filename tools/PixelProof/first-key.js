// TESTING ONLY. AT-10 (reopened): keys typed the instant a tap with Text ends all reach the new text box.
// Usage: node first-key.js <port> <width> <height> <ms between tap and keys> <rounds>, tablet or phone preview.
// Before the fix 4 of 30 boxes were whole (gaps 0, 15, 40 ms; tablet and phone); after, 30 of 30.
// first key into a new Mark text box: tap, then 11 keys with almost no wait, several rounds
const { chromium } = require('playwright');
const [port, w, h, gap, rounds] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +w, height: +h }, hasTouch: true });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  await p.keyboard.press('2'); await p.waitForTimeout(900);
  const cdp = await p.context().newCDPSession(p);
  const box = await p.evaluate(() => { const r = document.querySelector('.mk-layer').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; });
  const out = [];
  for (let i = 0; i < +rounds; i++) {
    const x = box.x + box.w * (0.15 + 0.1 * (i % 6)), y = box.y + Math.min(box.h, 600) * (0.15 + 0.12 * i);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    if (+gap > 0) await p.waitForTimeout(+gap);   // no wait for the box: the keys follow the tap at once, as Android Test's do
    for (const ch of 'chuvadimark') await cdp.send('Input.dispatchKeyEvent', { type: 'char', text: ch });
    await p.waitForTimeout(900);
    out.push(await p.evaluate(() => { const t = document.querySelector('.mk-text.sel .mk-ta'); return t ? t.value : '(no box)'; }));
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
  }
  console.log(`${w}x${h} gap ${gap} ms:`, out.map(v => v === 'chuvadimark' ? 'whole' : JSON.stringify(v)).join('  '));
  await b.close();
})();
