// TESTING ONLY (never shipped). Mac Test M-27: a mark drawn with the mouse must land under the pointer, at any zoom.
// Usage: node mark-pointer.js <port> [chromium|webkit] [old-webkit]   with a desktop preview on <port> opened on a PDF.
// old-webkit: makes the browser report rectangles under CSS zoom the way older WebKit does (in the element's own
// unzoomed pixels), which is what M-27 looks like: without the fix the rectangle lands at pointer times zoom.
// Draws a rectangle by dragging between two screen points at three zooms and asks the page what is under the
// middle of the drag and under each corner (elementFromPoint, which does not depend on how rectangles are reported).
const pw = require('playwright');
const [port, engine = 'chromium', mode = ''] = process.argv.slice(2);
(async () => {
  const b = await pw[engine].launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  if (mode === 'old-webkit') {
    await p.addInitScript(() => {
      const real = Element.prototype.getBoundingClientRect;
      Element.prototype.getBoundingClientRect = function () {
        const r = real.call(this); let zoom = 1;
        for (let e = this; e && e.nodeType === 1; e = e.parentElement) { const z = parseFloat(getComputedStyle(e).zoom); if (isFinite(z) && z > 0) zoom *= z; }
        return zoom === 1 ? r : new DOMRect(r.left / zoom, r.top / zoom, r.width / zoom, r.height / zoom);
      };
    });
  }
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  await p.keyboard.press('2'); await p.waitForTimeout(800);
  // Marks stay with their tab now (D-186 Q3 B), so a run before this one may have left some: start with none.
  const clear = p.locator('button[aria-label="Clear all marks"]'); if (await clear.isEnabled()) { await clear.click(); await p.waitForTimeout(300); }
  await p.click('button[aria-label="Rectangle"]'); await p.waitForTimeout(300);
  let fail = 0;
  const zoomNow = () => p.evaluate(() => { let e = document.querySelector('.rpage-wrap'); while (e && !(e.style && e.style.getPropertyValue('--rpage-zoom'))) e = e.parentElement; return e ? parseFloat(e.style.getPropertyValue('--rpage-zoom')) : NaN; });
  const setZoom = async (factor) => { await p.evaluate((f) => { const d = document.querySelector('.rdesk').getBoundingClientRect();   /* the desk is not zoomed: true on every engine */ window.chuvadiPinch && (window.chuvadiPinch('begin', 1, d.left + d.width / 2, d.top + 200), window.chuvadiPinch('change', f, d.left + d.width / 2, d.top + 200), window.chuvadiPinch('end')); }, factor); await p.waitForTimeout(700); };
  for (const step of [1, 1.6, 0.5]) {
    if (step !== 1) await setZoom(step);
    const zoom = await zoomNow();
    // Two points well inside the first page on screen, found by asking what is under them.
    const a = { x: 620, y: 300 }, c = { x: 760, y: 420 };
    const onPage = await p.evaluate(([a, c]) => [a, c].every(q => { const e = document.elementFromPoint(q.x, q.y); return e && !!e.closest('.rpage-wrap'); }), [a, c]);
    const before = await p.evaluate(() => document.querySelectorAll('.mk-shape').length);
    await p.mouse.move(a.x, a.y); await p.mouse.down(); await p.mouse.move((a.x + c.x) / 2, (a.y + c.y) / 2, { steps: 4 }); await p.mouse.move(c.x, c.y, { steps: 4 }); await p.mouse.up();
    await p.waitForTimeout(700);
    const got = await p.evaluate(([a, c]) => {
      const shapes = [...document.querySelectorAll('.mk-shape')]; const s = shapes[shapes.length - 1]; if (!s) return null;
      const under = (x, y) => { const e = document.elementFromPoint(x, y); return !!(e && (e === s || s.contains(e) || e.closest('.mk-shape') === s)); };
      const r = s.getBoundingClientRect();
      return { count: shapes.length, middle: under((a.x + c.x) / 2, (a.y + c.y) / 2), inA: under(a.x + 6, a.y + 6), inC: under(c.x - 6, c.y - 6), outside: under(a.x - 12, a.y - 12) || under(c.x + 12, c.y + 12),
        reported: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] };
    }, [a, c]);
    const ok = onPage && got && got.count === before + 1 && got.middle && got.inA && got.inC && !got.outside;
    if (!ok) fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  zoom ${zoom}: a rectangle dragged from (${a.x}, ${a.y}) to (${c.x}, ${c.y}) is under the pointer's path  ${JSON.stringify(got)}`);
    // Clear the selection so the next drag starts a new shape.
    await p.keyboard.press('Escape'); await p.waitForTimeout(200);
  }
  await b.close(); process.exit(fail ? 1 : 0);
})();
