// TESTING ONLY (D-158). A raster page drawn from its in-app address looks exactly like the same page drawn inline.
// Two desktop previews with CHVD_OPEN=<a large-format PDF>: before (inline data address) and after (page address).
// Usage: node raster-identical.js <beforePort> <afterPort> [out-dir]
const { chromium } = require('playwright');
const { PNG } = (() => { try { return require('pngjs'); } catch { return {}; } })();
const fs = require('fs');
const [before, after] = [process.argv[2] || 5101, process.argv[3] || 5102];
const out = process.argv[4] || '.';
async function shot(port, scale) {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: scale });
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => {
    const img = document.querySelector('.rdesk .rpage svg image');
    return img && (img.getAttribute('href') || '').length > 0 && document.querySelector('.rdesk .rpage svg image').getBBox().width > 0;
  }, null, { timeout: 300000 });
  // the image must have loaded and decoded, wherever it comes from
  await p.evaluate(async () => {
    const href = document.querySelector('.rdesk .rpage svg image').getAttribute('href');
    const i = new Image(); i.src = href; await i.decode();
  });
  // Fit the drawn page (the first fit can run before a slow page is drawn and measure its placeholder instead,
  // which depends on timing, not on how the image is delivered).
  await p.locator('.rdesk').click({ position: { x: 3, y: 3 } }); await p.keyboard.press('p'); // Fit page
  await p.waitForTimeout(1500);
  // Same view in both: the desk at its top, the first page only (its neighbours draw on their own schedule).
  await p.evaluate(() => { document.querySelector('.rdesk').scrollTop = 0; });
  await p.mouse.move(1430, 5);   // away from the page, so its hover bar is gone
  await p.waitForTimeout(1200);
  const href = await p.evaluate(() => document.querySelector('.rdesk .rpage svg image').getAttribute('href'));
  const buf = await p.locator('.rpage-wrap[data-page="0"] .rpage svg').screenshot();
  await b.close();
  return { buf, href };
}
(async () => {
  let fail = 0;
  for (const scale of [1, 2]) {
    const a = await shot(before, scale), b = await shot(after, scale);
    fs.writeFileSync(`${out}/raster-before@${scale}x.png`, a.buf);
    fs.writeFileSync(`${out}/raster-after@${scale}x.png`, b.buf);
    const same = Buffer.compare(a.buf, b.buf) === 0;
    if (!same) fail++;
    console.log(`${same ? 'IDENTICAL' : 'DIFF     '} raster page @${scale}x  before href ${a.href.slice(0, 30)}… (${a.href.length} chars)  after href ${b.href}`);
  }
  process.exit(fail ? 1 : 0);
})();
