// Touch for the tablet and phone shells (Portal & Android 12d-12j). Loaded by TouchSupport.razor and
// PhoneShell.razor only when <html data-shell> is "tablet" or "phone"; never on desktop or portal.
//
// reader.js already owns pinch-to-zoom and double-tap zoom on touchscreens ("Pinch, double-tap and
// swipe do zoom and paging" — handout 12g), so this file adds only what the desktop code lacks:
//   * horizontal swipe on pages that fit sideways → next / previous page (Read mode): a quick fling, or
//     a slower drag across a third of the desk (Android's own pager does both). Detected from touch
//     events, which keep arriving when the WebView takes the drag as a pan (pointer events get
//     pointercancel there — Android BUILD-LOG step 32). A desk whose pages fit sideways is marked
//     .chvd-hfit so it pans only vertically (mobile.css), leaving the sideways drag to the swipe.
//   * tap on the canvas → shows the per-page strip for a few seconds (desktop shows it on hover)
//   * Arrange: long-press a page (or a Shelf page) to drag it; a quick swipe scrolls instead. While
//     Arrange shows, a blocking touchmove listener is registered *before* any press, so the browser
//     waits for it and an armed press can stop the pan (Chrome ignores one added mid-gesture — step 34).
//   * phone Arrange: the Shelf rests as a peek; tap it or swipe up to open, swipe down to close; a page
//     long-pressed out of the open Shelf drops it back to the peek so the desks are reachable.

let net = null;          // DotNetObjectReference<TouchSupport>
let attached = false;
let tap = null;              // pointer tap candidate {x, y, t, id, moved, target}
let swipe = null;            // touch swipe candidate {x, y, t, target, multi, movedAt}
let stripTimer = null;
let press = null;            // Arrange long-press state
let arrange = false;
let fitTimer = 0;

const TAP_SLOP = 10;
const SWIPE_MIN = 60;
const SWIPE_MS = 600;
const LONG_PRESS_MS = 450;

export function initTouch(dotnetRef) {
    net = dotnetRef || net;
    if (attached) return;
    attached = true;
    document.addEventListener('pointerdown', onDown, true);
    document.addEventListener('pointermove', onMove, true);
    document.addEventListener('pointerup', onUp, true);
    document.addEventListener('pointercancel', onCancel, true);
    document.addEventListener('contextmenu', onContextMenu, true);
    document.addEventListener('touchstart', onTouchStart, { capture: true, passive: true });
    document.addEventListener('touchmove', onTouchMove, { capture: true, passive: true });
    document.addEventListener('touchend', onTouchEnd, { capture: true, passive: true });
    document.addEventListener('touchcancel', onTouchCancel, { capture: true, passive: true });
    fitTimer = setInterval(markFits, 300);
    markFits();
}

export function disposeTouch() {
    if (!attached) return;
    attached = false;
    document.removeEventListener('pointerdown', onDown, true);
    document.removeEventListener('pointermove', onMove, true);
    document.removeEventListener('pointerup', onUp, true);
    document.removeEventListener('pointercancel', onCancel, true);
    document.removeEventListener('contextmenu', onContextMenu, true);
    document.removeEventListener('touchstart', onTouchStart, true);
    document.removeEventListener('touchmove', onTouchMove, true);
    document.removeEventListener('touchend', onTouchEnd, true);
    document.removeEventListener('touchcancel', onTouchCancel, true);
    setArrange(false);
    clearInterval(fitTimer); fitTimer = 0;
    cancelPress();
    tap = null; swipe = null;
    clearTimeout(stripTimer);
}

/** TouchSupport tells us when Arrange is showing (long-press drag needs the blocking listener). */
export function setArrange(on) {
    on = !!on;
    if (on === arrange) return;
    arrange = on;
    if (on) document.addEventListener('touchmove', guardMove, { capture: true, passive: false });
    else document.removeEventListener('touchmove', guardMove, { capture: true });
}

function guardMove(e) {
    // Only an armed press stops the pan; every other drag scrolls as usual.
    if (press && press.armed && e.cancelable) e.preventDefault();
}

function isTouch(e) { return e.pointerType === 'touch'; }

function deskOf(el) { return el && el.closest ? el.closest('.rdesk') : null; }

function interactive(el) {
    return !!(el && el.closest && el.closest('button, input, select, textarea, a, [contenteditable], .mk-layer, .fcards, .pstrip, .mdrawer'));
}

function isPhone() { return document.documentElement.getAttribute('data-shell') === 'phone'; }

// A desk whose pages fit sideways pans only vertically, so a sideways drag is ours (swipe).
function markFits() {
    for (const d of document.querySelectorAll('.rdesk')) {
        d.classList.toggle('chvd-hfit', pagesFit(d));
    }
}

// Do the pages in view fit sideways? Measured on each page's .rpage-wrap, which isn't zoomed itself:
// its scrollWidth includes the zoomed page in every WebView, whereas getBoundingClientRect of a
// CSS-zoomed element differs between WebView versions (Android API 35 reports it unzoomed). Other
// content that overflows the desk doesn't count — the emulator showed such overflow on phones.
function pagesFit(desk) {
    const top = desk.getBoundingClientRect().top, bottom = top + desk.clientHeight;
    let seen = 0;
    for (const w of desk.querySelectorAll('.rpage-wrap')) {
        const r = w.getBoundingClientRect();
        if (r.bottom <= top || r.top >= bottom) { if (seen) break; continue; }
        seen++;
        if (w.scrollWidth > w.clientWidth + 1) return false;
    }
    return seen > 0;
}

function hasSelection() {
    const sel = window.getSelection && window.getSelection();
    return !!(sel && !sel.isCollapsed && String(sel).length > 0);
}

// ── swipe (touch events: never cancelled by the WebView's own pan) ────────────
function onTouchStart(e) {
    if (e.touches.length !== 1) { if (swipe) swipe.multi = true; return; }
    const t = e.touches[0];
    swipe = { x: t.clientX, y: t.clientY, t: performance.now(), target: e.target, multi: false, movedAt: 0 };
}

function onTouchMove(e) {
    const s = swipe;
    if (!s || s.movedAt || e.touches.length !== 1) return;
    const t = e.touches[0];
    if (Math.hypot(t.clientX - s.x, t.clientY - s.y) > TAP_SLOP) s.movedAt = performance.now();
}

function onTouchEnd(e) {
    const s = swipe;
    if (!s || e.touches.length !== 0) return;
    swipe = null;
    if (s.multi || press) return;
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - s.x, dy = t.clientY - s.y;

    // Phone Arrange: swipe up on the Shelf peek opens it, swipe down on its header closes it.
    const sh = s.target.closest ? s.target.closest('.bench-shelf') : null;
    if (sh && isPhone() && Math.abs(dy) > SWIPE_MIN && Math.abs(dy) > 2 * Math.abs(dx)) {
        if (dy < 0) sh.classList.add('chvd-open');
        else if (s.target.closest('.shelf-head') || sh.scrollTop <= 0) sh.classList.remove('chvd-open');
        return;
    }

    // Paging: horizontal, on pages that fit sideways (otherwise the drag pans the page); a quick fling
    // or a drag across a third of the desk. A long-press then drag selects text instead.
    const desk = deskOf(s.target);
    if (!desk || interactive(s.target)) return;
    const adx = Math.abs(dx), ady = Math.abs(dy);
    const quick = adx > SWIPE_MIN && performance.now() - s.t < SWIPE_MS;
    const far = adx > Math.max(2 * SWIPE_MIN, desk.clientWidth * 0.33);
    const held = s.movedAt && s.movedAt - s.t > LONG_PRESS_MS;
    if (adx > 2 * ady && (quick || far) && !held && !hasSelection() && pagesFit(desk)) {
        call('OnSwipe', dx < 0 ? 1 : -1);
    }
}

function onTouchCancel() { swipe = null; }

// ── pointer routing: tap and long-press ──────────────────────────────────────
function onDown(e) {
    if (!isTouch(e) || e.__chvdSynthetic) return;
    if (!e.isPrimary) { tap = null; cancelPress(); return; }   // a second finger: pinch is reader.js's
    if (beginPress(e)) return;
    tap = { x: e.clientX, y: e.clientY, t: performance.now(), id: e.pointerId, moved: false, target: e.target };
}

function onMove(e) {
    if (!isTouch(e)) return;
    if (press && !press.armed && e.pointerId === press.id
        && Math.hypot(e.clientX - press.x, e.clientY - press.y) > TAP_SLOP) cancelPress();   // a scroll
    if (tap && tap.id === e.pointerId && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) > TAP_SLOP) tap.moved = true;
}

function onUp(e) {
    if (!isTouch(e) || e.__chvdSynthetic) return;
    if (press && e.pointerId === press.id) {
        if (!press.armed) {
            // A quick tap on a page: hand bench.js the press it never saw, so it selects the page
            // exactly as a click does (its pointerup listener runs after this one).
            replayDown(press);
        }
        cancelPress();
        return;
    }

    const t = tap;
    tap = null;
    if (!t || t.id !== e.pointerId || t.moved) return;

    // Phone Arrange: the Shelf rests as a peek; a tap on its header (or the peek) opens / closes it.
    const shelf = t.target.closest ? t.target.closest('.bench-shelf') : null;
    if (shelf && isPhone() && (!shelf.classList.contains('chvd-open') || t.target.closest('.shelf-head'))) {
        shelf.classList.toggle('chvd-open');
        return;
    }
    if (interactive(t.target)) return;
    showStrip(t.target);
}

function onCancel(e) {
    if (!isTouch(e)) return;
    if (tap && tap.id === e.pointerId) tap = null;
    if (press && e.pointerId === press.id && !press.armed) cancelPress();
}

function onContextMenu(e) {
    // Android shows a context menu / text selection on long-press; not on a page being dragged.
    if (press) e.preventDefault();
}

function call(method, arg) {
    if (!net) return;
    try { arg === undefined ? net.invokeMethodAsync(method) : net.invokeMethodAsync(method, arg); } catch { /* circuit gone */ }
}

// ── per-page strip: tap shows it (hover on desktop) ─────────────────────────
function showStrip(target) {
    const canvas = target && target.closest ? target.closest('.mview-canvas') : null;
    if (!canvas) return;
    canvas.classList.add('chvd-strip-on');
    clearTimeout(stripTimer);
    stripTimer = setTimeout(() => canvas.classList.remove('chvd-strip-on'), 4000);
}

// ── Arrange: long-press to drag ─────────────────────────────────────────────
function beginPress(e) {
    if (!arrange) return false;
    const card = e.target.closest ? e.target.closest('[data-bench-id], [data-shelf], [data-shelf-all]') : null;
    if (!card || e.target.closest('button') || e.target.closest('input')) return false;
    // bench.js would start its press now; hold it back until we know this isn't a scroll.
    e.stopPropagation();
    press = { id: e.pointerId, x: e.clientX, y: e.clientY, target: e.target, armed: false, timer: 0 };
    press.timer = setTimeout(armPress, LONG_PRESS_MS);
    return true;
}

function armPress() {
    if (!press) return;
    press.armed = true;   // guardMove now stops the pan for the rest of this touch
    try { navigator.vibrate && navigator.vibrate(12); } catch { /* not allowed */ }
    replayDown(press);
    // Phone: a page lifted out of the open Shelf sheet drops the sheet back to its peek, so the
    // desks it covered (all of them in landscape) are there to drop on. bench.js already holds the
    // press, so the drag carries on.
    const sheet = press.target.closest ? press.target.closest('.bench-shelf.chvd-open') : null;
    if (sheet && isPhone()) requestAnimationFrame(() => sheet.classList.remove('chvd-open'));
}

function replayDown(p) {
    const ev = new PointerEvent('pointerdown', {
        bubbles: true, cancelable: true, composed: true,
        pointerId: p.id, pointerType: 'touch', isPrimary: true, button: 0, buttons: 1,
        clientX: p.x, clientY: p.y,
    });
    ev.__chvdSynthetic = true;
    p.target.dispatchEvent(ev);
}

function cancelPress() {
    if (!press) return;
    clearTimeout(press.timer);
    press = null;
}

// ── Redact on a phone opens at fit width (hook H-7 in Redact.razor calls this) ─
/** The --rpage-zoom at which the first page fills the desk's width less a 16 px gutter each side. */
export async function fitWidthZoom(desk) {
    if (!desk) return 0;
    // Prefer a rendered page (its real size) over the A4 placeholder; wait briefly for the first one.
    for (let i = 0; i < 20 && !desk.querySelector('.rpage svg'); i++) await new Promise(r => setTimeout(r, 75));
    const page = desk.querySelector('.rpage');
    if (!page) return 0;
    const z = parseFloat(getComputedStyle(desk).getPropertyValue('--rpage-zoom')) || 1;
    const natW = page.getBoundingClientRect().width / z;
    if (!natW) return 0;
    const fit = (desk.clientWidth - 32) / natW;
    return Math.max(0.3, Math.min(4, Math.floor(fit * 100) / 100));
}

// ── orientation (phone View sheet: "Two-page · landscape only") ──────────────
let orientRef = null;
let orientHandler = null;

export function watchOrientation(dotnetRef) {
    orientRef = dotnetRef;
    if (orientHandler) window.removeEventListener('resize', orientHandler);
    orientHandler = () => {
        if (!orientRef) return;
        try { orientRef.invokeMethodAsync('SetLandscape', window.innerWidth > window.innerHeight); } catch { /* gone */ }
    };
    window.addEventListener('resize', orientHandler);
    orientHandler();
}

export function unwatchOrientation() {
    if (orientHandler) window.removeEventListener('resize', orientHandler);
    orientHandler = null;
    orientRef = null;
}
