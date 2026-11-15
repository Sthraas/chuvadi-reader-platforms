// TESTING ONLY (never shipped). Patch 28 on screen: Mobile UI F-1 and F-2, D-188 (U-19 a), Ctrl F on a Word file.
// Usage: node patch28.js <port> <phone port>   with a phone preview on <phone port> opened on four-turns.pdf, and a desktop preview on <port> opened on four-turns.pdf (pages with /Rotate 0, 90,
// 180, 270, a word "rotmark<turn>" on each), layout.xlsx and a .docx (CHVD_OPEN="four-turns.pdf;layout.xlsx;x.docx").
const { chromium } = require('playwright');
const port = process.argv[2];
(async () => {
  const b = await chromium.launch();
  const out = []; const check = (name, ok, detail) => out.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`);
  const open = async (viewport) => { const p = await b.newPage({ viewport }); await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' }); await p.waitForTimeout(800); return p; };
  const tab = async (p, ext) => { await p.locator(`[title$="${ext}"], .tab:has-text("${ext}")`).first().click(); await p.waitForTimeout(900); };

  // ── F-1: Find's highlight is on the word, on every turn ──
  let p = await open({ width: 1440, height: 900 });
  await p.waitForSelector('.rpage svg', { timeout: 20000 });   // the PDF is the last one opened, so it is the tab on screen
  for (const turn of [0, 90, 180, 270]) {
    await p.keyboard.press('Control+f'); await p.waitForSelector('.rfind-box'); await p.waitForTimeout(300); await p.keyboard.press('Control+a'); await p.keyboard.type(`rotmark${turn}`, { delay: 40 }); await p.keyboard.press('Enter'); await p.waitForTimeout(3000);
    const got = await p.evaluate((word) => {
      const hl = document.querySelector('.rfind-hl.cur'); if (!hl) return { noHighlight: true, box: (document.querySelector('.rfind-box') || {}).value, bars: document.querySelectorAll('.rfind-box').length, count: document.querySelectorAll('.rfind-hl').length };
      const wrap = hl.closest('.rpage-wrap'); const texts = [...wrap.querySelectorAll('svg text, svg tspan')].filter(t => t.textContent.includes(word));
      if (!texts.length) return { noText: true };
      const t = texts[texts.length - 1].getBoundingClientRect(), h = hl.getBoundingClientRect(), d = document.querySelector('.rdesk').getBoundingClientRect();
      const cx = h.left + h.width / 2, cy = h.top + h.height / 2;
      return { onWord: cx > t.left - 3 && cx < t.right + 3 && cy > t.top - 3 && cy < t.bottom + 3, sideways: h.height > h.width, wordSideways: t.height > t.width, onScreen: cy > d.top && cy < d.bottom && cx > d.left && cx < d.right };
    }, `rotmark${turn}`);
    check(`F-1 /Rotate ${turn}: the highlight is on the word, turned as the word is, and on screen`, got && got.onWord && got.sideways === got.wordSideways && got.onScreen, JSON.stringify(got));
    await p.keyboard.press('Escape'); await p.waitForTimeout(300);
  }
  await p.close();

  // ── F-2: Fit page fits the page on screen (phone portrait, the /Rotate 90 page) ──
  p = await b.newPage({ viewport: { width: 412, height: 915 }, hasTouch: true, isMobile: true }); await p.goto(`http://127.0.0.1:${process.argv[3] || port}/reader`, { waitUntil: 'networkidle' }); await p.waitForTimeout(800); await p.waitForSelector('.rpage svg', { timeout: 20000 });
  await p.waitForSelector('.rpage svg', { timeout: 20000 }); await p.waitForTimeout(1500);
  const click = (label) => p.evaluate((l) => { const b = [...document.querySelectorAll('button')].find(b => (b.title || b.getAttribute('aria-label') || b.textContent).trim().startsWith(l)); b.click(); }, label);
  const sizes = () => p.evaluate(() => { const d = document.querySelector('.rdesk'); return { desk: [d.clientWidth, d.clientHeight], pages: [...document.querySelectorAll('.rpage-wrap')].map(w => { const s = w.querySelector('.rpage svg'); if (!s) return null; const r = s.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }).filter(Boolean) }; });
  await click('Fit page'); await p.waitForTimeout(1500);
  const fp = await sizes();
  check('F-2 phone portrait, Fit page: every page, upright or turned, is inside the screen', fp.pages.length >= 3 && fp.pages.every(([w, h]) => w <= fp.desk[0] && h <= fp.desk[1]), JSON.stringify(fp));
  check('F-2 the upright pages are as large as before (388 px wide), the turned ones fitted to the width', fp.pages.some(([w]) => w === 388) && fp.pages.some(([w, h]) => w > h && w <= fp.desk[0] && w >= fp.desk[0] - 30), '');
  await click('Fit width'); await p.waitForTimeout(1500);
  const fw = await sizes();
  check('F-2 Fit width: every page is as wide as the screen allows', fw.pages.every(([w]) => w <= fw.desk[0] && w >= fw.desk[0] - 30), JSON.stringify(fw));
  await click('Zoom in'); await p.waitForTimeout(1500);
  const zi = await sizes();
  check('a zoom of the person\'s own applies to every page alike again', zi.pages.every(([w, h]) => Math.abs(Math.max(w, h) - Math.max(...zi.pages[0])) <= 2), JSON.stringify(zi));
  await p.close();

  // ── D-188: matches in hidden rows and columns are named ──
  p = await open({ width: 1440, height: 900 });
  await tab(p, '.xlsx'); await p.waitForSelector('.xv-canvas', { timeout: 20000 });
  await p.keyboard.press('Control+f'); await p.waitForTimeout(600);
  const viaKey = !!(await p.$('.rfind-box'));
  check('Ctrl F opens Find on an Excel file (it did nothing before)', viaKey);
  if (!viaKey) await p.getByText('Find', { exact: true }).first().click();
  await p.waitForSelector('.rfind-box');
  check('the Find box has the cursor', await p.evaluate(() => document.activeElement && document.activeElement.classList.contains('rfind-box')));
  await p.keyboard.type('hidden'); await p.keyboard.press('Enter'); await p.waitForTimeout(1100);
  const line = await p.evaluate(() => { const e = document.querySelector('.xv-hiddenhits'); return e ? e.textContent.trim() : null; });
  check('D-188 the matches in a hidden row and a hidden column are named', line === '2 matches are in hidden cells: A5 (hidden row), C6 (hidden column)', line);
  await p.fill('.rfind-box', 'Title'); await p.press('.rfind-box', 'Enter'); await p.waitForTimeout(900);
  check('no line when no match is hidden', !(await p.$('.xv-hiddenhits')));
  await tab(p, '.docx'); await p.waitForSelector('.dv-sheet', { timeout: 20000 });
  await p.mouse.click(700, 500); await p.keyboard.press('Control+f'); await p.waitForTimeout(600);
  check('Ctrl F opens Find on a Word file, with the cursor in the box', await p.evaluate(() => document.activeElement && document.activeElement.classList.contains('rfind-box')));
  console.log(out.join('\n')); await b.close(); process.exit(out.some(l => l.startsWith('FAIL')) ? 1 : 0);
})();
