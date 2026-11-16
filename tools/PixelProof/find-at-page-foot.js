// TESTING ONLY (never shipped). Mobile UI H-26: with pages snapping (page at a time), Find lands on the page of the
// match even when the match is at the page's foot. Desktop preview opened on tools/PixelProof/fixtures/foot.pdf
// (a word 91 % down each of four pages). Usage: node find-at-page-foot.js <port> 1440 900 footmark
// Before the fix 4 of 6 steps left the match off screen; after, none.
const { chromium } = require('playwright');
const [port, vw, vh, word] = process.argv.slice(2);
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +vw, height: +vh }, hasTouch: +vw < 900 });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' }); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  console.log('snap:', await p.evaluate(() => getComputedStyle(document.querySelector('.rdesk')).scrollSnapType), 'desk', await p.evaluate(() => document.querySelector('.rdesk').clientHeight), 'page', await p.evaluate(() => Math.round(document.querySelector('.rpage-wrap').getBoundingClientRect().height)));
  for (let z = 0; z < +(process.env.ZOOMS || 0); z++) { await p.keyboard.press('Control+='); await p.waitForTimeout(500); }
  console.log('after zoom snap:', await p.evaluate(() => getComputedStyle(document.querySelector('.rdesk')).scrollSnapType), 'page', await p.evaluate(() => Math.round(document.querySelector('.rpage-wrap').getBoundingClientRect().height)));
  await p.keyboard.press('Control+f'); await p.waitForTimeout(600); await p.keyboard.type(word); await p.keyboard.press('Enter'); await p.waitForTimeout(3500);
  let seen = 0, off = 0; const where = [];
  for (let i = 0; i < 6; i++) {
    const r = await p.evaluate(() => { const h = document.querySelector('.rfind-hl.cur'); const d = document.querySelector('.rdesk'); if (!h) return null; const a = h.getBoundingClientRect(), c = d.getBoundingClientRect(); return { page: h.closest('[data-page]').getAttribute('data-page'), frac: Math.round(100 * (a.top - h.closest('.rpage-wrap').getBoundingClientRect().top) / h.closest('.rpage-wrap').getBoundingClientRect().height), vis: a.top >= c.top - 1 && a.bottom <= c.bottom + 1 }; });
    if (r) { seen++; if (!r.vis) off++; where.push(`p${r.page}@${r.frac}%${r.vis ? "" : "!"}`); }
    await p.keyboard.press('Enter'); await p.waitForTimeout(1300);
  }
  console.log(`matches stepped ${seen}, off screen ${off}:`, where.join(' ')); await b.close(); })();
