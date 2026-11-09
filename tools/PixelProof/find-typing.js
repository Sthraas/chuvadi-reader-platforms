// TESTING ONLY (Android Test AT-10). Typed characters reach the text fields even when the Ui answers slowly.
// The fields used to be value="@x" + @oninput: each answer wrote the field back to what the app had seen so far,
// so keys typed in between were lost (Android's WebView + IME, "burstwordtest" -> "burtwordt"). Here the round trip
// is slowed on purpose (CPU throttling and a delayed socket) so the race shows on any machine.
// Usage: node find-typing.js [port]   (desktop preview, ASPNETCORE_ENVIRONMENT=Development CHVD_FF=desktop)
const { chromium } = require('playwright');
const port = process.argv[2] || 5102;
const word = 'burstwordtest';
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  // Delay every message the page sends to the app, as a slow device does.
  await p.addInitScript(() => {
    const send = WebSocket.prototype.send;
    WebSocket.prototype.send = function (d) { setTimeout(() => send.call(this, d), 60); };
  });
  const cdp = await p.context().newCDPSession(p);
  const fields = [
    { name: 'Reader Find', url: '/reader', open: async () => { await p.keyboard.press('Control+f'); }, sel: '.rfind-box' },
    { name: 'Library search', url: '/library', open: async () => {}, sel: '.libp-search input, input[placeholder*="Search"]' },
    { name: 'Ctrl K bar', url: '/', open: async () => { await p.keyboard.press('Control+k'); }, sel: '.cmd-in' },
  ];
  let fail = 0;
  for (const f of fields) {
    await p.goto(`http://127.0.0.1:${port}${f.url}`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(800);
    await f.open();
    const box = p.locator(f.sel).first();
    await box.waitFor({ timeout: 5000 });
    await box.click();
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    await p.keyboard.type(word, { delay: 15 });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
    await p.waitForTimeout(2000);
    const got = await box.inputValue();
    const ok = got === word;
    if (!ok) fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${f.name.padEnd(15)} typed "${word}", field has "${got}"`);
  }
  await b.close();
  process.exit(fail ? 1 : 0);
})();
