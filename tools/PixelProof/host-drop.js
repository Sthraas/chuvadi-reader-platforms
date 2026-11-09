// TESTING ONLY (W-02). host-drop.js hands files dropped on the page to the host. Run against the desktop
// preview with a stand-in for WebView2's chrome.webview:   BASE=http://localhost:5102 node host-drop.js
const { chromium } = require('playwright');
const BASE = process.env.BASE || 'http://localhost:5102';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.addInitScript(() => {
    window.__sent = [];
    window.chrome = { webview: { postMessage() {}, postMessageWithAdditionalObjects(msg, files) {
      window.__sent.push({ msg, names: Array.from(files).map(f => f.name) }); } } };
  });
  await p.goto(BASE + '/', { waitUntil: 'networkidle' }); await p.waitForTimeout(1000);
  await p.addScriptTag({ url: '/_content/ChuvadiReader.Ui/js/host-drop.js' });
  const fire = (type, withFiles, preHandled) => p.evaluate(([type, withFiles, preHandled]) => {
    const dt = new DataTransfer();
    if (withFiles) { dt.items.add(new File(['%PDF-1.4'], 'Ward round.pdf', { type: 'application/pdf' })); dt.items.add(new File(['x'], 'notes.docx')); }
    else dt.setData('text/plain', 'a tab being dragged');
    const target = document.querySelector('main') || document.body;
    const stop = (e) => e.preventDefault();
    if (preHandled) document.addEventListener(type, stop, true); // as Mark mode does for an image on a page
    const ev = new DragEvent(type, { dataTransfer: dt, bubbles: true, cancelable: true });
    target.dispatchEvent(ev);
    if (preHandled) document.removeEventListener(type, stop, true);
    const sent = window.__sent.slice(); window.__sent.length = 0;
    return { prevented: ev.defaultPrevented, sent };
  }, [type, withFiles, preHandled]);
  const checks = [];
  let r = await fire('dragover', true, false); checks.push(['a file drag is accepted (browser won\'t open it itself)', r.prevented && r.sent.length === 0]);
  r = await fire('drop', true, false); checks.push(['files dropped on the page go to the host', r.sent.length === 1 && r.sent[0].msg === 'chvd:files-dropped' && r.sent[0].names.join('|') === 'Ward round.pdf|notes.docx']);
  r = await fire('drop', true, true); checks.push(['a drop a component already took is left alone', r.sent.length === 0]);
  r = await fire('dragover', false, false); checks.push(['a drag without files is left alone', !r.prevented]);
  r = await fire('drop', false, false); checks.push(['a drop without files sends nothing', r.sent.length === 0 && !r.prevented]);
  let fail = 0; for (const [n, ok] of checks) { if (!ok) fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${n}`); }
  console.log('page errors:', errs.length, errs.join(' | ')); await b.close(); process.exit(fail || errs.length ? 1 : 0);
})();
