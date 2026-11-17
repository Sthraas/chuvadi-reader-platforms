// TESTING ONLY (never shipped). D-195: bookmark edits and Protect's redaction areas are kept with the tab and asked
// about on close (bookmarks: Save bookmarks / Discard / Cancel; redaction areas: Discard / Cancel).
// Usage: node close-guard-work.js <port> <a.pdf> <b.pdf>   with a desktop preview on <port>.
const { chromium } = require('playwright'); const fs = require('fs'); const crypto = require('crypto');
const [port, A, B] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
const post = (path) => fetch(base + path, { method: 'POST' }).then(r => r.json());
const get = (path) => fetch(base + path).then(r => r.json());
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  for (const f of [A, B]) await post('/__preview/open?path=' + encodeURIComponent(f));
  await p.goto(base + '/reader', { waitUntil: 'networkidle' });
  const name = f => f.split('/').pop();
  const ready = () => p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 });
  const sw = async f => { await p.locator('.rtab', { hasText: name(f) }).first().click(); await ready(); await p.waitForTimeout(700); };
  const tabNames = () => p.evaluate(() => [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim()));
  const card = () => p.evaluate(() => { const c = document.querySelector('.closeq'); return c ? { title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\s+/g, ' ').trim(), buttons: [...c.querySelectorAll('button')].map(x => x.textContent.trim()), focus: document.activeElement?.textContent.trim() } : null; });
  const closeX = async f => { await p.locator('.rtab', { hasText: name(f) }).first().locator('.rtab-x').click(); await p.waitForTimeout(800); };
  const answer = async label => { await p.locator('.closeq button', { hasText: new RegExp('^' + label) }).click(); await p.waitForTimeout(1500); };
  const rows = () => p.evaluate(() => document.querySelectorAll('.bm-row').length);
  const same = (a, c) => JSON.stringify(a) === JSON.stringify(c);
  await ready();

  // ── bookmarks ──
  await sw(A);
  const before = sha(A);
  await p.keyboard.press('Control+b'); await p.waitForTimeout(700); await p.keyboard.press('Enter'); await p.waitForTimeout(400);
  const n0 = await rows();
  check(n0 >= 1, 'a bookmark is added on the first file (not saved)', `(${n0} in the panel)`);
  let u = await get('/__preview/unsaved');
  check(u.hasUnsavedWork === true, 'that is unsaved work: a host is told', JSON.stringify(u));
  await sw(B); await sw(A);
  if (!(await rows())) { await p.keyboard.press('Control+Shift+o').catch(() => { }); await p.waitForTimeout(300); }
  check(await rows() === n0, 'after another tab and back, the bookmark is still in the panel (it was dropped before)', `(${await rows()})`);
  await closeX(A);
  let c = await card();
  check(!!c && c.title === `Save the bookmarks of ${name(A)}?` && same(c.buttons, ['Save bookmarks', 'Discard', 'Cancel']), 'closing the tab asks: Save bookmarks / Discard / Cancel', JSON.stringify(c));
  await answer('Cancel');
  check((await tabNames()).includes(name(A)) && sha(A) === before, 'Cancel: the tab stays and the file is untouched');
  await closeX(A); await answer('Save bookmarks');
  check(!(await card()) && !(await tabNames()).includes(name(A)) && sha(A) !== before, 'Save bookmarks: written into the file, and the tab closes');

  // ── Protect's redaction areas ──
  await sw(B);
  // D-198: redaction is hidden until Pdf 3.35.1 (Protect's rail shows one greyed "Redaction"). Then there are no
  // areas to keep, and this half has nothing to prove; it runs again when redaction comes back.
  await p.locator('.rdesk').click({ position: { x: 20, y: 20 } }).catch(() => { }); await p.keyboard.press('4'); await p.waitForTimeout(900);
  if (await p.locator('button[aria-label="Redaction"][disabled], button[aria-label="Redaction"][aria-disabled="true"]').count()) {
    console.log('SKIP  redaction areas: redaction is hidden until the next update (D-198)');
    check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
    await b.close(); process.exit(fail ? 1 : 0);
  }
  const toProtect = async () => { await p.locator('.rdesk').click({ position: { x: 20, y: 20 } }).catch(() => { }); await p.keyboard.press('4'); await p.waitForTimeout(700); await p.keyboard.press('r'); await p.waitForSelector('.mk-layer.drawmode', { timeout: 20000 }); await p.waitForTimeout(1200); };   // Protect, then its Redact box tool
  await toProtect();
  const boxes = () => p.evaluate(() => document.querySelectorAll('.mk-box-x').length);
  const layer = await p.evaluate(() => { const r = document.querySelector('.mk-layer.drawmode').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width }; });
  const drawBox = async (dy) => { const x = layer.x + layer.w * 0.3, y = Math.max(layer.y, 140) + dy; await p.mouse.move(x, y); await p.mouse.down(); await p.mouse.move(x + 140, y + 40, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(500); };
  await p.evaluate(() => { window.__ev = []; for (const t of ['dragstart', 'pointercancel']) document.addEventListener(t, () => window.__ev.push(t), true); });
  await drawBox(60); await drawBox(160);
  const stray = await p.evaluate(() => window.__ev);
  check(stray.length === 0, 'drawing started no browser drag (before, the second area was often lost to one)', JSON.stringify(stray));
  check(await boxes() === 2, 'two redaction areas are drawn in Protect', `(${await boxes()})`);
  u = await get('/__preview/unsaved');
  check(u.hasUnsavedWork === true, 'they are unsaved work');
  await p.keyboard.press('1'); await ready(); await p.waitForTimeout(700);
  await toProtect();
  check(await boxes() === 2, 'after leaving Protect for Read and coming back, both areas are still there (they were lost before)', `(${await boxes()})`);
  await p.evaluate(() => Blazor.navigateTo('/')); await p.waitForTimeout(800);
  await p.evaluate(() => Blazor.navigateTo('/redact')); await p.waitForSelector('.mk-layer.drawmode', { timeout: 20000 }).catch(() => { }); await p.waitForTimeout(1200);
  check(await boxes() === 2, 'and after Home and back to Protect with nothing handed over, the file opens again with its areas', `(${await boxes()})`);
  await p.keyboard.press('1'); await p.waitForTimeout(400); await p.evaluate(() => Blazor.navigateTo('/reader')); await ready(); await p.waitForTimeout(700);
  const bBefore = sha(B);
  await closeX(B);
  c = await card();
  check(!!c && c.title === `Discard the redaction areas on ${name(B)}?` && /2 redaction areas/.test(c.text) && same(c.buttons, ['Discard', 'Cancel']), 'closing the tab asks: Discard / Cancel only (no Save: the redacted copy is made in Protect)', JSON.stringify(c));
  check(c && c.focus === 'Cancel', 'the keyboard starts on Cancel, not on Discard', c && c.focus);
  await answer('Cancel');
  check((await tabNames()).includes(name(B)), 'Cancel: the tab stays');
  let closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
  c = await card();
  check(same(c.buttons, ['Discard', 'Cancel']), 'closing the app asks the same');
  await answer('Cancel'); let r = await closing;
  check(r.closed === false, 'Cancel: the app stays open', JSON.stringify(r));
  await closeX(B); await answer('Discard');
  u = await get('/__preview/unsaved');
  check(!(await tabNames()).includes(name(B)) && u.hasUnsavedWork === false && sha(B) === bBefore, 'Discard: the tab closes, nothing is unsaved any more, and the file was never touched', JSON.stringify(u));
  check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
  await b.close(); process.exit(fail ? 1 : 0);
})();
