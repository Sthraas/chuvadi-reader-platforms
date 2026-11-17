// TESTING ONLY (never shipped). D-194: Arrange asks at app close when desks changed since the last bind or session
// save; the host hears when "unsaved work" changes; and where the host does not save in place (the portal) the
// marks card offers only Save as.
// Usage: node close-guard-arrange.js <port> desktop|web <a.pdf> <b.pdf>   (preview in that profile on <port>)
const { chromium } = require('playwright');
const [port, profile, A, B] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
let fail = 0;
const check = (ok, what, extra = '') => { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}${extra ? '  ' + extra : ''}`); };
const post = (path) => fetch(base + path, { method: 'POST' }).then(r => r.json());
const get = (path) => fetch(base + path).then(r => r.json());
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await post('/__preview/open?path=' + encodeURIComponent(A));
  await p.goto(base + '/reader', { waitUntil: 'networkidle' });
  await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0, null, { timeout: 30000 }); await p.waitForTimeout(600);
  const card = () => p.evaluate(() => { const c = document.querySelector('.closeq'); return c ? { title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\s+/g, ' ').trim(), buttons: [...c.querySelectorAll('button')].map(x => x.textContent.trim()) } : null; });
  const answer = async label => { await p.locator('.closeq button', { hasText: new RegExp('^' + label) }).click(); await p.waitForTimeout(1200); };
  const shapes = () => p.evaluate(() => document.querySelectorAll('.mk-shape').length);
  const draw = async () => {
    if (!(await p.locator('button[aria-label="Rectangle"]').count())) { await p.keyboard.press('2'); await p.waitForTimeout(700); }
    await p.click('button[aria-label="Rectangle"]'); await p.waitForTimeout(250);
    await p.mouse.move(600, 300); await p.mouse.down(); await p.mouse.move(700, 380, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(500);
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
  };
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  if (profile === 'web') {
    await draw();
    await p.locator('.rtab.active .rtab-x').click(); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
    const c = await card();
    check(same(c.buttons, ['Save as…', 'Discard', 'Cancel']), 'portal: the marks card offers only Save as, with Discard and Cancel (no Save into the session copy)', JSON.stringify(c.buttons));
    await answer('Cancel');
    let closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
    check(same((await card()).buttons, ['Save as…', 'Discard', 'Cancel']), 'portal: the same card for the whole app (what Sign out calls)');
    await answer('Save as'); await p.waitForTimeout(1500);
    const r = await closing;
    check(r.closed === true && !(await card()), 'portal: Save as answers it and the close goes on', JSON.stringify(r));
  } else {
    let u = await get('/__preview/unsaved'); const told0 = u.told;
    check(u.hasUnsavedWork === false, 'at the start nothing is unsaved', JSON.stringify(u));
    let r = await post('/__preview/close-app');
    check(r.hadUnsavedWork === false && r.closed === true && !(await card()), 'so the app closes at once, no question');

    await post('/__preview/arrange?path=' + encodeURIComponent(A));
    u = await get('/__preview/unsaved');
    check(u.hasUnsavedWork === true && u.desksUnsaved === 1 && u.told === told0 + 1, 'pages put on a desk in Arrange are unsaved work, and the host is told once', JSON.stringify(u));

    let closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(500);
    let c = await card();
    check(c.title === 'Save what you arranged?' && /^1 desk in Arrange/.test(c.text) && same(c.buttons, ['Save session…', 'Discard', 'Cancel']), 'closing the app asks about Arrange: Save session / Discard / Cancel', JSON.stringify(c));
    check(new URL(p.url()).pathname === '/bench', 'and Arrange is the page on screen', p.url());
    await answer('Cancel'); r = await closing;
    u = await get('/__preview/unsaved');
    check(r.closed === false && u.hasUnsavedWork === true && !(await card()), 'Cancel: the app stays open and the desks are as they were', JSON.stringify(r));

    closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
    await answer('Save session'); await p.waitForTimeout(800); r = await closing;
    u = await get('/__preview/unsaved');
    check(r.closed === true && u.hasUnsavedWork === false && u.told === told0 + 2, 'Save session: saved, the app may close, and the host is told it is no longer unsaved', JSON.stringify({ r, u }));
    r = await post('/__preview/close-app');
    check(r.hadUnsavedWork === false && r.closed === true, 'asked again after the save: closes at once');

    await post('/__preview/arrange?path=' + encodeURIComponent(B));
    u = await get('/__preview/unsaved');
    check(u.hasUnsavedWork === true && u.desksUnsaved === 1, 'a new desk after the save is unsaved; the saved desk is not counted', JSON.stringify(u));

    // marks and Arrange together: Arrange is asked first, the files last, so a Discard of marks cannot be followed by a Cancel
    await p.evaluate(() => Blazor.navigateTo('/reader')); await p.waitForFunction(() => document.querySelectorAll('.rdesk .rpage svg').length > 0); await p.waitForTimeout(700);
    await draw(); check(await shapes() === 1, 'a mark is drawn as well');
    closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(500);
    c = await card();
    check(c.title === 'Save what you arranged?', 'with marks and desks both unsaved, Arrange is asked about first', c.title);
    await answer('Discard'); c = await card();
    check(!!c && /^Save the marks on/.test(c.title) && same(c.buttons, ['Save', 'Save as…', 'Discard', 'Cancel']), 'then the file with marks: Save / Save as / Discard / Cancel', JSON.stringify(c));
    await answer('Cancel'); r = await closing;
    u = await get('/__preview/unsaved');
    check(r.closed === false && u.hasUnsavedWork === true && u.desksUnsaved === 1, 'Cancel on the file: the app stays open; the desks answered Discard are still there (nothing is destroyed until the app closes)', JSON.stringify({ r, u }));
    await p.waitForTimeout(500);
    if (!(await p.locator('button[aria-label="Rectangle"]').count())) { await p.keyboard.press('2'); await p.waitForTimeout(700); }
    check(await shapes() === 1, 'and the mark is still there');
    closing = post('/__preview/close-app'); await p.waitForSelector('.closeq'); await p.waitForTimeout(400);
    await answer('Discard'); await answer('Discard'); r = await closing;
    check(r.closed === true, 'Discard for both: the app may close', JSON.stringify(r));
  }
  check(errs.length === 0, 'no script errors', JSON.stringify(errs.slice(0, 3)));
  await b.close(); process.exit(fail ? 1 : 0);
})();
