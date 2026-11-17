// TESTING ONLY (never shipped). Protect: ten redaction areas drawn one after another with the mouse are all kept.
// Before, the first area selected the page text under it and later presses became the browser's drag of that
// selection (main: 1 or 9 of 10 kept). Preview on any PDF at port 5117. Usage: node protect-draw.js
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(`http://127.0.0.1:5117/reader`, { waitUntil: 'networkidle' }); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0);
  await p.locator('.rdesk').click({ position: { x: 20, y: 20 } }).catch(() => { }); await p.keyboard.press('4'); await p.waitForTimeout(700); await p.keyboard.press('r'); await p.waitForSelector('.mk-layer.drawmode', { timeout: 20000 }); await p.waitForTimeout(1200);
  await p.evaluate(() => { window.__ev = []; for (const t of ['dragstart', 'selectstart']) document.addEventListener(t, e => window.__ev.push(t + '@' + (e.target.className || e.target.nodeName) + ' sel=' + getSelection().type), true); });
  const layer = await p.evaluate(() => { const r = document.querySelector('.mk-layer.drawmode').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width }; });
  for (let i = 0; i < 10; i++) { const x = layer.x + layer.w * 0.3, y = Math.max(layer.y, 140) + 30 + i * 60; await p.mouse.move(x, y); await p.mouse.down(); await p.mouse.move(x + 140, y + 40, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(+(process.env.GAP || 500)); }
  console.log('boxes', await p.evaluate(() => document.querySelectorAll('.mk-box-x').length), 'of 10;', (await p.evaluate(() => window.__ev)).join(' | ') || 'no drag or selection events'); await b.close(); })();
