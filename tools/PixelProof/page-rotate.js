// TESTING ONLY (never shipped). Linux Test B-32: a page's /Rotate on screen.
// Usage: node page-rotate.js <port> <rotate>   with a desktop preview on <port> opened on turned-<rotate>.pdf
// (a 200 × 400 page, red square bottom-left, blue top-right; see tests/ChuvadiReader.Tests/PageRotateTests.cs).
// Prints the page's size on screen and where the two squares are, as fractions of the page from its top-left.
const { chromium } = require('playwright');
const [port, rotate] = process.argv.slice(2);
const want = { 0: { red: [0.125, 0.9375], blue: [0.875, 0.0625], wide: false }, 90: { red: [0.0625, 0.125], blue: [0.9375, 0.875], wide: true },
  180: { red: [0.875, 0.0625], blue: [0.125, 0.9375], wide: false }, 270: { red: [0.9375, 0.875], blue: [0.0625, 0.125], wide: true } }[rotate];
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => [...document.querySelectorAll('svg *')].some(e => getComputedStyle(e).fill === 'rgb(255, 0, 0)'), null, { timeout: 20000 });
  await p.waitForTimeout(800);
  const got = await p.evaluate(() => {
    const find = c => [...document.querySelectorAll('svg *')].filter(e => getComputedStyle(e).fill === c && !e.closest('.thumb-pg'))[0];
    const red = find('rgb(255, 0, 0)'), blue = find('rgb(0, 0, 255)');
    const page = red.closest('svg').getBoundingClientRect();
    const at = e => { const r = e.getBoundingClientRect(); return [(r.left + r.width / 2 - page.left) / page.width, (r.top + r.height / 2 - page.top) / page.height]; };
    return { w: page.width, h: page.height, red: at(red), blue: at(blue) };
  });
  const near = (a, e) => Math.abs(a[0] - e[0]) < 0.01 && Math.abs(a[1] - e[1]) < 0.01;
  const ok = (got.w > got.h) === want.wide && near(got.red, want.red) && near(got.blue, want.blue);
  const f = a => a.map(v => v.toFixed(3)).join(', ');
  console.log(`/Rotate ${rotate}: page ${Math.round(got.w)} × ${Math.round(got.h)} px, red at (${f(got.red)}), blue at (${f(got.blue)})  ${ok ? 'PASS' : 'FAIL'}`);
  await p.screenshot({ path: `page-rotate-${rotate}.png` });
  await b.close(); process.exit(ok ? 0 : 1);
})();
