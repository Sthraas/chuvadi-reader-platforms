// TESTING ONLY (never shipped). D-190: Excel columns and rows can be resized on screen (drag an edge, press it twice
// to fit), for viewing only. Usage: node excel-resize.js <port> <workbook path>   with a desktop preview on <port>
// opened on tools/OfficeCorpus's layout.xlsx as the last file (sheets: Layout, Settings (right to left, 150 %), ...).
const { chromium: chromiumEngine, webkit } = require(process.env.PW_MODULE || 'playwright'); const chromium = process.env.ENGINE === 'webkit' ? webkit : chromiumEngine; const fs = require('fs'); const crypto = require('crypto');
const [port, file] = process.argv.slice(2);
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
const sha = () => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
(async () => {
  const before = sha();
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, hasTouch: true }); const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' }); await p.waitForSelector('.xv-canvas'); await p.waitForTimeout(1200);
  const hdr = (kind, n) => p.evaluate(([kind, n]) => { const e = document.querySelector(`.xv-${kind}hdr[data-${kind === 'col' ? 'c' : 'r'}="${n}"]`); if (!e) return null; const r0 = e.getBoundingClientRect(); /* an older engine (WebKit 18, macOS 15) gives rectangles inside a CSS zoom in the zoomed element's own units: put them on screen */ const pr = document.createElement('div'); pr.style.cssText = 'position:fixed;width:10px;zoom:2;visibility:hidden'; document.body.appendChild(pr); const unz = Math.abs(pr.getBoundingClientRect().width - 10) < 0.5; pr.remove(); let z = 1; if (unz) for (let x = e; x && x.nodeType === 1; x = x.parentElement) { const v = parseFloat(getComputedStyle(x).zoom); if (v > 0) z *= v; } const r = { left: r0.left * z, right: r0.right * z, top: r0.top * z, bottom: r0.bottom * z, width: r0.width * z, height: r0.height * z }; return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height, own: e.classList.contains('own'), css: parseFloat(kind === 'col' ? e.style.width : e.style.height) }; }, [kind, n]);
  const drag = async (x0, y0, x1, y1) => { await p.mouse.move(x0, y0); await p.mouse.down(); await p.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, { steps: 4 }); await p.mouse.move(x1, y1, { steps: 4 }); await p.mouse.up(); await p.waitForTimeout(600); };
  const twice = async (x, y) => { await p.mouse.move(x, y); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(90); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(900); };
  const resetBtn = () => p.locator('.xv-resetsizes').count();
  const near = (a, b, tol = 1.5) => Math.abs(a - b) <= tol;

  // ── a column, by dragging ──
  let B = await hdr('col', 2), C = await hdr('col', 4);   // column C is hidden in this sheet: D follows B
  check(await resetBtn() === 0 && !B.own, 'as the file holds it: no column is marked and there is no "File\'s own sizes" button');
  await p.mouse.move(B.right - 1, B.top + 8); await p.waitForTimeout(150);
  check(await p.evaluate(() => document.querySelector('.xv-gridwrap').style.cursor) === 'col-resize', 'the pointer over a column\'s edge shows the resize cursor');
  await drag(B.right - 1, B.top + 8, B.right - 1 + 70, B.top + 8);
  let B2 = await hdr('col', 2), C2 = await hdr('col', 4);
  check(near(B2.w, B.w + 70) && near(C2.left, C.left + 70) && near(C2.w, C.w), 'dragging column B\'s edge 70 px widens B by 70 px and moves the columns after it', `(${B.w} → ${B2.w}; D at ${C.left} → ${C2.left})`);
  check(B2.own && !C2.own && await resetBtn() === 1, 'B is marked as changed, and "File\'s own sizes" appears');
  const cellFollows = await p.evaluate(() => { const c = document.querySelector('.xv-cell[data-a^="D"]'); const h = document.querySelector('.xv-colhdr[data-c="4"]'); return c && h ? Math.abs(c.getBoundingClientRect().left - h.getBoundingClientRect().left) < 2.5 : null; });
  check(cellFollows !== false, 'the cells of the next column sit under its letter', String(cellFollows));
  await drag(B2.right - 1, B2.top + 8, B2.left - 300, B2.top + 8);
  let B3 = await hdr('col', 2);
  check(near(B3.w, 8, 1), 'a column cannot be dragged out of sight: it stops at 8 px', `(${B3.w})`);

  // ── fit, by pressing the edge twice ──
  await twice(B3.right - 1, B3.top + 8);
  let B4 = await hdr('col', 2);
  const fits = await p.evaluate(() => [...document.querySelectorAll('.xv-cell[data-a^="B"]')].filter(c => /^B\d+$/.test(c.getAttribute('data-a')) && !c.classList.contains('merged')).map(c => { const s = c.querySelector('.xv-s'); return s ? { a: c.getAttribute('data-a'), text: s.getBoundingClientRect().width, cell: c.getBoundingClientRect().width } : null; }).filter(Boolean));
  const widest = fits.reduce((m, f) => Math.max(m, f.text), 0);
  check(B4.w > 8 && fits.length > 0 && B4.w >= widest && B4.w <= widest + 12, 'pressing the edge twice fits the column to its widest text', `(column ${B4.w.toFixed(1)} px, widest text ${widest.toFixed(1)} px, ${fits.length} cells on screen)`);

  // ── a row ──
  let R3 = await hdr('row', 3), R4 = await hdr('row', 4);
  await drag(R3.left + 10, R3.bottom - 1, R3.left + 10, R3.bottom - 1 + 30);
  let R3b = await hdr('row', 3), R4b = await hdr('row', 4);
  check(near(R3b.h, R3.h + 30) && near(R4b.top, R4.top + 30) && R3b.own, 'dragging row 3\'s edge 30 px makes it 30 px taller and moves the rows below', `(${R3.h} → ${R3b.h})`);
  await twice(R3b.left + 10, R3b.bottom - 1);
  let R3c = await hdr('row', 3);
  check(R3c.h > 8 && R3c.h < R3b.h, 'pressing a row\'s edge twice fits it to its text', `(${R3b.h} → ${R3c.h})`);

  // ── a hidden column stays hidden ──
  const hiddenCols = await p.evaluate(() => { const ns = [...document.querySelectorAll('.xv-top .xv-colhdr')].map(e => +e.getAttribute('data-c')).sort((a, b) => a - b); const miss = []; for (let i = ns[0]; i < ns[ns.length - 1]; i++) if (!ns.includes(i)) miss.push(i); return miss; });
  check(hiddenCols.length > 0, 'the sheet\'s hidden columns have no header to drag, before and after', JSON.stringify(hiddenCols));

  // ── kept with the tab ──
  const other = p.locator('.rtab').first(); await other.click(); await p.waitForTimeout(900);
  await p.locator('.rtab', { hasText: file.split('/').pop() }).click(); await p.waitForSelector('.xv-canvas'); await p.waitForTimeout(1500);
  let B5 = await hdr('col', 2), R3d = await hdr('row', 3);
  check(near(B5.w, B4.w) && near(R3d.h, R3c.h) && B5.own, 'after another tab and back, the sizes are as they were left', `(B ${B5.w.toFixed(1)}, row 3 ${R3d.h.toFixed(1)})`);

  // ── a zoomed, right-to-left sheet ──
  await p.locator('.xv-tab', { hasText: 'Settings' }).click(); await p.waitForTimeout(1000);
  const zoom = await p.evaluate(() => parseFloat(document.querySelector('.xv-canvas').style.zoom));
  let S2 = await hdr('col', 2);
  check(await resetBtn() === 0, 'another sheet is still as the file holds it');
  // right to left: a column's far edge is its left side; dragging it left widens the column
  await drag(S2.left + 1, S2.top + 8, S2.left + 1 - 60, S2.top + 8);
  let S2b = await hdr('col', 2);
  check(near(S2b.w, S2.w + 60, 2) && near(S2b.css, S2.css + 60 / zoom, 1.5), `on a right-to-left sheet at ${zoom * 100} %, dragging the edge 60 px on screen widens the column by 60 px on screen`, `(${S2.w.toFixed(1)} → ${S2b.w.toFixed(1)} on screen; ${S2.css} → ${S2b.css} at 100 %)`);

  // ── a finger ──
  let S3 = await hdr('col', 3);
  if (process.env.ENGINE === 'webkit') console.log('SKIP  the touch-pointer check needs Chromium\'s touch input (not WebKit)');
  else {
  const cdp = await ctx.newCDPSession(p);
  const touch = (type, x, y) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
  const scroll0 = await p.evaluate(() => { const g = document.querySelector('.xv-gridwrap'); return [g.scrollLeft, g.scrollTop]; });
  // M-29: this preview profile is a host with no touch screen, like the Mac, whose Mac Catalyst at times hands WebKit a
  // mouse drag as a touch pointer. There it is taken at once, as a mouse is: no rest, mouse reach (1 px inside).
  // (On touch hosts a finger rests 350 ms first, D-193: Mobile UI's own proofs cover that.)
  await touch('touchStart', S3.left + 1, S3.top + 8); for (let i = 1; i <= 6; i++) await touch('touchMove', S3.left + 1 - i * 8, S3.top + 8); await touch('touchEnd'); await p.waitForTimeout(700);
  let S3b = await hdr('col', 3);
  const scroll1 = await p.evaluate(() => { const g = document.querySelector('.xv-gridwrap'); return [g.scrollLeft, g.scrollTop]; });
  check(near(S3b.w, S3.w + 48, 3) && JSON.stringify(scroll0) === JSON.stringify(scroll1), 'M-29: on a host with no touch screen, a drag that arrives as a touch pointer takes the edge at once, like a mouse, and the sheet does not scroll instead', `(${S3.w.toFixed(1)} → ${S3b.w.toFixed(1)})`);
  }

  // ── back to the file's own sizes ──
  await p.locator('.xv-resetsizes').click(); await p.waitForTimeout(700);
  let S2c = await hdr('col', 2), S3c = await hdr('col', 3);
  check(near(S2c.w, S2.w) && near(S3c.w, S3.w) && !S2c.own && await resetBtn() === 0, '"File\'s own sizes" puts this sheet back and goes away');
  await p.locator('.xv-tab', { hasText: 'Layout' }).click(); await p.waitForTimeout(1000);
  check(await resetBtn() === 1, 'the other sheet keeps its own until it is reset too');
  await p.locator('.xv-resetsizes').click(); await p.waitForTimeout(700);
  let B6 = await hdr('col', 2), R3e = await hdr('row', 3);
  check(near(B6.w, B.w) && near(R3e.h, R3.h) && await resetBtn() === 0, 'and it too goes back to exactly the file\'s widths and heights', `(B ${B6.w}, row 3 ${R3e.h})`);

  check(sha() === before, 'the file on disk is byte for byte what it was');
  check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
  await b.close(); process.exit(fail ? 1 : 0);
})();
