// TESTING ONLY (W-01). Where does a press on the top bar move the window? Run against the desktop preview
// (CHVD_FF=desktop, Development); it records window calls at /__preview/window-log.
//   BASE=http://localhost:5102 node titlebar-drag.js
const { chromium } = require('playwright');
const BASE = process.env.BASE || 'http://localhost:5102';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(BASE + '/reader', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
  const log = async () => (await p.request.get(BASE + '/__preview/window-log')).json();
  // An empty point inside a container: a spot whose topmost element is the container itself.
  const empty = (sel) => p.evaluate((sel) => {
    const el = document.querySelector(sel); const r = el.getBoundingClientRect(); const y = r.top + r.height / 2;
    for (let x = r.left + 2; x < r.right - 2; x += 4) if (document.elementFromPoint(x, y) === el) return { x, y };
    return null;
  }, sel);
  const centre = (sel) => p.evaluate((sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, sel);
  const press = async (pt) => { await p.mouse.move(pt.x, pt.y); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(400); };
  // The bar's empty middle is the right group's leading space (it stretches to the centre column).
  const middle = await empty('.tb-right');
  const cases = [
    ['empty middle of the bar', middle, 1, 0],
    ['empty space around the brand', await empty('.tb-brandbox'), 1, 0],
    ['the search box', await centre('.tb-cmd'), 0, 0],
    ['the page number', await centre('.tb-pg-box'), 0, 0],
    ['the brand', await centre('.tb-brand'), 0, 0],
  ];
  let fail = 0;
  for (const [name, pt, wantDrag, wantMax] of cases) {
    if (!pt) { console.log(`FAIL  ${name}: no empty point found`); fail++; continue; }
    const before = await log(); await press(pt); const after = await log();
    const d = after.drags - before.drags, m = after.maximizes - before.maximizes; const ok = d === wantDrag && m === wantMax;
    if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}: drags +${d}, maximise +${m} (want +${wantDrag}, +${wantMax})`);
    await p.keyboard.press('Escape');
  }
  const pt = middle; const before = await log();
  if (pt) { await p.mouse.move(pt.x, pt.y); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(80); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(400); }
  const after = await log(); const m = after.maximizes - before.maximizes; if (m !== 1) fail++;
  console.log(`${m === 1 ? 'PASS' : 'FAIL'}  double press on the empty middle: maximise +${m} (want +1)`);
  console.log('page errors:', errs.length); await b.close(); process.exit(fail || errs.length ? 1 : 0);
})();
