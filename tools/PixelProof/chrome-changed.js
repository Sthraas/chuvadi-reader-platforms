// TESTING ONLY (D-101). Checks that the top bar redraws when the host raises IPlatformInfo.ChromeChanged.
// Run against the preview in Linux mode (Development, so the Blazor script is served):
//   ASPNETCORE_ENVIRONMENT=Development CHVD_FF=linux dotnet ChuvadiReader.MobileUi.Preview.dll --urls http://localhost:5107
//   BASE=http://localhost:5107 node chrome-changed.js
// For each GTK layout it posts to /__preview/button-layout (the preview's stand-in for the Linux host's
// settings watcher) and reads the buttons at each end of the top bar, without reloading the page.
const { chromium } = require('playwright');
const BASE = process.env.BASE || 'http://localhost:5107';
const cases = [
  ['appmenu:minimize,maximize,close', [], ['Minimize', 'Maximize', 'Close']],
  ['close:', ['Close'], []],
  ['close,minimize:maximize', ['Close', 'Minimize'], ['Maximize']],
  ['appmenu:close', [], ['Close']],
  [':', [], []],
  ['appmenu:minimize,maximize,close', [], ['Minimize', 'Maximize', 'Close']],
];
const read = (page) => page.evaluate(() => {
  const side = (sel) => Array.from(document.querySelectorAll(`header.topbar ${sel} .traffic .tl`))
    .map((b) => b.classList.contains('tl-min') ? 'Minimize' : b.classList.contains('tl-close') ? 'Close' : 'Maximize');
  return { left: side('.tb-left'), right: side('.tb-right') };
});
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(BASE + '/');
  await page.waitForSelector('header.topbar');
  await page.waitForTimeout(800);
  let fail = 0;
  for (const [gtk, left, right] of cases) {
    const r = await page.request.post(`${BASE}/__preview/button-layout?gtk=${encodeURIComponent(gtk)}`);
    const want = JSON.stringify({ left, right });
    let got = '';
    for (let i = 0; i < 20 && got !== want; i++) { await page.waitForTimeout(100); got = JSON.stringify(await read(page)); }
    const ok = r.ok() && got === want;
    if (!ok) fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  "${gtk}"  ${got}${ok ? '' : '  want ' + want}`);
  }
  console.log(`page errors: ${errors.length}${errors.length ? ' ' + errors.join(' | ') : ''}`);
  await browser.close();
  process.exit(fail || errors.length ? 1 : 0);
})();
