// TESTING ONLY. Cold app: a small PDF open plus cad.pdf (active); page through N sheets, close cad, sample memory.
const { chromium } = require('playwright');
const fs = require('fs');
const pid = +process.argv[2], sheets = +(process.argv[3] || 2), port = process.argv[4] || 5102;
function mem() {
  const st = fs.readFileSync(`/proc/${pid}/status`, 'utf8');
  const g = k => +(st.match(new RegExp(k + ':\\s+(\\d+)'))[1]) / 1024 | 0;
  return `rss ${g('VmRSS')} anon ${g('RssAnon')}`;
}
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const t0 = Date.now(), log = s => console.log(`${((Date.now() - t0) / 1000).toFixed(1).padStart(6)} s  ${s}  | ${mem()}`);
  log('start');
  await p.goto(`http://127.0.0.1:${port}/reader`, { waitUntil: 'networkidle' });
  for (let i = 1; i <= sheets; i++) {
    await p.waitForFunction(n => document.querySelectorAll('.rpage svg').length >= n, i, { timeout: 600000 });
    log(`sheet ${i} drawn`);
    if (i < sheets) { await p.locator('.rdesk, .desk, [data-page]').first().click({ position: { x: 5, y: 5 } }).catch(() => {}); await p.keyboard.press('PageDown'); }
  }
  log('before close');
  await p.keyboard.press('Control+w');
  for (let k = 0; k < 16; k++) { await p.waitForTimeout(k < 4 ? 500 : 5000); log(`after close`); }
  await b.close();
})();
