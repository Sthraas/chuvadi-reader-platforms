// TESTING ONLY (never shipped). F-3 (D-195): the current Find match never comes to rest under the Find bar.
// Preview opened on tools/PixelProof/fixtures/top.pdf (the word three times across the top line of each of four
// pages, and once mid-page). Usage: [ZOOMS=n] node find-under-bar.js <port> <w> <h> topmark
// Passes when no step leaves the match off screen or overlapping the bar.
const { chromium } = require('playwright');
const [port, vw, vh, word] = process.argv.slice(2);
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: +vw, height: +vh }, hasTouch: +vw < 900 });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' }); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  for (let z = 0; z < +(process.env.ZOOMS || 0); z++) { await p.keyboard.press('Control+='); await p.waitForTimeout(500); }
  console.log('snap:', await p.evaluate(() => getComputedStyle(document.querySelector('.rdesk')).scrollSnapType));
  await p.keyboard.press('Control+f'); await p.waitForTimeout(600); await p.keyboard.type(word); await p.keyboard.press('Enter'); await p.waitForTimeout(3500);
  let seen = 0, bad = 0, aside = 0, moved = 0; const where = [];
  for (let i = 0; i < 16; i++) {
    const r = await p.evaluate(() => { const h = document.querySelector('.rfind-hl.cur'), d = document.querySelector('.rdesk'), f = document.querySelector('.rfind'); if (!h || !f) return null;
      const a = h.getBoundingClientRect(), c = d.getBoundingClientRect(), q = f.getBoundingClientRect(), w = h.closest('.rpage-wrap').getBoundingClientRect();
      return { page: h.closest('[data-page]').getAttribute('data-page'), vis: a.top >= c.top - 1 && a.bottom <= c.bottom + 1,
        under: a.left < q.right && a.right > q.left && a.top < q.bottom && a.bottom > q.top, aside: f.classList.contains('aside'),
        pageTop: Math.round(w.top - c.top), inDesk: q.top >= c.top - 1 && q.bottom <= c.bottom + 1 }; });
    if (r) { seen++; if (!r.vis || r.under || !r.inDesk) bad++; if (r.aside) aside++; else if (r.pageTop > 20) moved++;
      where.push(`p${r.page}${r.aside ? 'A' : ''}${r.under ? '!under' : ''}${r.vis ? '' : '!off'}`); }
    await p.keyboard.press('Enter'); await p.waitForTimeout(1300);
  }
  console.log(`${bad === 0 && seen === 16 ? 'PASS' : 'FAIL'}: steps ${seen}, covered or off screen ${bad}, bar aside ${aside}:`, where.join(' ')); await b.close(); })();
