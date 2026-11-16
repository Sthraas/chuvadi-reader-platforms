// TESTING ONLY (never shipped). D-186 Q3 B and D-190: marks stay with their tab, and closing with unsaved marks asks.
// Usage: node close-guard.js <port> <a.pdf> <b.pdf> <c.pdf> <readonly.pdf>   with a desktop preview on <port>.
// The four files are opened through the preview's /__preview/open, as a host's Open does; /__preview/close-app
// stands in for a host's window close (it calls IUnsavedWork exactly as a host must).
const { chromium } = require('playwright');
const [port, A, B, C, RO] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
const post = (path) => fetch(base + path, { method: 'POST' }).then(r => r.json());
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  for (const f of [A, B, C, RO]) await post('/__preview/open?path=' + encodeURIComponent(f));
  await p.goto(base + '/reader', { waitUntil: 'networkidle' });
  const name = f => f.split('/').pop();
  const tabNames = () => p.evaluate(() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim()));
  const active = () => p.evaluate(() => document.querySelector('.rtab.active .rtab-name')?.textContent.trim());
  const shapes = () => p.evaluate(() => document.querySelectorAll('.mk-shape').length);
  const card = () => p.evaluate(() => { const c = document.querySelector('.closeq'); return c ? { title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\s+/g, ' ').trim(), buttons: [...c.querySelectorAll('button')].map(x => x.textContent.trim()), err: c.querySelector('.closeq-err')?.textContent.trim() || null } : null; });
  const sw = async f => { await p.locator('.rtab', { hasText: name(f) }).first().click(); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 }); await p.waitForTimeout(700); };
  const draw = async (dx = 0) => {
    if (!(await p.locator('button[aria-label="Rectangle"]').count())) { await p.keyboard.press('2'); await p.waitForTimeout(700); }
    await p.click('button[aria-label="Rectangle"]'); await p.waitForTimeout(250);
    const a = { x: 600 + dx, y: 300 }, c = { x: 700 + dx, y: 380 };
    await p.mouse.move(a.x, a.y); await p.mouse.down(); await p.mouse.move(c.x, c.y, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(500);
    await p.keyboard.press('Escape'); await p.waitForTimeout(250);
  };
  const closeX = async f => { await p.locator('.rtab', { hasText: name(f) }).first().locator('.rtab-x').click(); await p.waitForTimeout(700); };
  const answer = async label => { await p.locator('.closeq button', { hasText: new RegExp('^' + label) }).click(); await p.waitForTimeout(1200); };

  // ── Q3 B: marks stay with their tab ──
  await sw(A); await draw(); check(await shapes() === 1, 'a rectangle is drawn on the first file');
  await sw(B); check(await shapes() === 0, 'another tab shows none of it');
  await draw(); await draw(140); check(await shapes() === 2, 'two rectangles are drawn on the second file');
  await sw(A); check(await shapes() === 1, 'back on the first file its rectangle is still there (it was lost before)');
  await sw(B); check(await shapes() === 2, 'and the second file still has its two');
  await p.evaluate(() => Blazor.navigateTo('/')); await p.waitForTimeout(900);
  await p.evaluate(() => Blazor.navigateTo('/reader')); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0); await p.waitForTimeout(900);
  if (!(await p.locator('button[aria-label="Rectangle"]').count())) { await p.keyboard.press('2'); await p.waitForTimeout(700); }
  check(await shapes() === 2, 'after Home and back, the marks are still there');
  await p.keyboard.press('Control+z'); await p.waitForTimeout(400);
  check(await shapes() === 1, 'undo still works after coming back (the history stays with the tab)');
  await p.keyboard.press('Control+y'); await p.waitForTimeout(400);

  // ── D-190: closing a tab ──
  await closeX(C); check(!(await card()) && !(await tabNames()).includes(name(C)), 'a tab with no marks closes at once, no question');
  await closeX(A);
  let c = await card();
  check(!!c && c.title.includes(name(A)) && JSON.stringify(c.buttons) === JSON.stringify(['Save', 'Save as…', 'Discard', 'Cancel']), 'closing a tab with marks asks: Save / Save as / Discard / Cancel', JSON.stringify(c));
  check(await active() === name(A), 'the file asked about is the one on screen');
  // The keyboard stays in the card (Web portal UI): Tab and Shift Tab go round its buttons, never to the page behind.
  const focused = () => p.evaluate(() => { const a = document.activeElement; return a && a.closest('.closeq') ? a.textContent.trim() : 'OUTSIDE:' + (a ? a.tagName + '.' + a.className : 'none'); });
  const round = [await focused()];
  for (let i = 0; i < 5; i++) { await p.keyboard.press('Tab'); await p.waitForTimeout(120); round.push(await focused()); }
  const back = [];
  for (let i = 0; i < 5; i++) { await p.keyboard.press('Shift+Tab'); await p.waitForTimeout(120); back.push(await focused()); }
  check(![...round, ...back].some(f => f.startsWith('OUTSIDE')) && round[4] === round[0] && new Set(round).size === 4, 'Tab and Shift Tab go round the card\'s four buttons and never leave it', JSON.stringify(round) + ' ' + JSON.stringify(back));
  await p.keyboard.press('Escape'); await p.waitForTimeout(500);
  check(!(await card()) && (await tabNames()).includes(name(A)) && await shapes() === 1, 'Escape is Cancel: the tab stays, the mark stays');
  await closeX(A); await answer('Cancel');
  check((await tabNames()).includes(name(A)) && await shapes() === 1, 'Cancel: the tab stays, the mark stays');
  await closeX(A); await answer('Discard');
  check(!(await card()) && !(await tabNames()).includes(name(A)), 'Discard: the tab closes');

  // ── the whole app ──
  await sw(RO); await draw();
  let closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
  c = await card();
  check(!!c && /File 1 of 2/.test(c.text), 'closing the app with two files with marks asks about them one at a time', JSON.stringify(c));
  const firstAsked = await active();
  await answer('Discard'); c = await card();
  check(!!c && /File 2 of 2/.test(c.text) && await active() !== firstAsked, 'after an answer, the next file is shown and asked about', JSON.stringify(c && c.title));
  check(c && c.title.includes(name(RO)) && JSON.stringify(c.buttons) === JSON.stringify(['Save as…', 'Discard', 'Cancel']), 'a file that cannot be written offers only Save as', JSON.stringify(c && c.buttons));
  await answer('Cancel');
  let r = await closing;
  check(r.hadUnsavedWork === true && r.closed === false, 'Cancel on any file: the app stays open', JSON.stringify(r));
  await sw(B); const keptB = await shapes(); await sw(RO); const keptRO = await shapes();
  check(keptB === 2 && keptRO === 1, 'and nothing was discarded, not even on the file answered Discard before the Cancel', `(${keptB}, ${keptRO})`);

  // Save as on the read-only file, Save on the other; then the app may close.
  closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
  c = await card(); const order = [c.title];
  await answer(c.buttons.includes('Save') ? 'Save$' : 'Save as'); await p.waitForTimeout(1500);
  c = await card(); if (c) { order.push(c.title); await answer(c.buttons.includes('Save') ? 'Save$' : 'Save as'); await p.waitForTimeout(1500); }
  r = await closing;
  check(r.closed === true && !(await card()), 'Save on one file and Save as on the other: the app may close', JSON.stringify(r) + ' ' + JSON.stringify(order));
  r = await post('/__preview/close-app');
  check(r.hadUnsavedWork === false && r.closed === true && !(await card()), 'asked again, nothing is unsaved: it closes at once with no question', JSON.stringify(r));
  await sw(B); check(await shapes() === 0, 'the marks saved into the file are in the file now, no longer loose marks');
  check((await tabNames()).length === 4, 'closing the app closed no tab (they are there for the next start)', JSON.stringify(await tabNames()));
  check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
  await p.screenshot({ path: 'close-guard.png' });
  await b.close(); process.exit(fail ? 1 : 0);
})();
