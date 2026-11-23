// Chuvadi web portal: the browser half of the host services (file chooser + chunked upload,
// downloads, print hand-off, clipboard, external links). Called from .NET through BrowserBridge.
// No network beyond the portal's own origin; no third-party code.
(function () {
    'use strict';

    // ── small DOM helpers (host overlays; the Web portal UI chat owns their final look) ─────────

    function overlay(title) {
        var root = document.createElement('div');
        root.className = 'chvd-portal-overlay';
        root.setAttribute('role', 'dialog');
        root.setAttribute('aria-modal', 'true');
        var card = document.createElement('div');
        card.className = 'chvd-portal-card';
        var h = document.createElement('div');
        h.className = 'chvd-portal-title';
        h.textContent = title;
        var body = document.createElement('div');
        body.className = 'chvd-portal-body';
        var actions = document.createElement('div');
        actions.className = 'chvd-portal-actions';
        card.appendChild(h);
        card.appendChild(body);
        card.appendChild(actions);
        root.appendChild(card);
        document.body.appendChild(root);
        return {
            root: root, body: body, actions: actions,
            button: function (label, primary, onClick) {
                var b = document.createElement('button');
                b.type = 'button';
                b.className = primary ? 'chvd-portal-btn primary' : 'chvd-portal-btn';
                b.textContent = label;
                b.addEventListener('click', onClick);
                actions.appendChild(b);
                return b;
            },
            close: function () { if (root.parentNode) root.parentNode.removeChild(root); }
        };
    }

    function hasActivation() {
        // Opening a file chooser needs a recent user gesture. The click reached the server and came
        // back; if the browser still counts it as active we open directly, else we ask for one click.
        var ua = navigator.userActivation;
        return !!(ua && ua.isActive);
    }

    // ── file chooser ──────────────────────────────────────────────────────────────────────────

    function choose(req) {
        return new Promise(function (resolve) {
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = req.accept;
            input.multiple = !!req.multiple;
            input.style.display = 'none';
            document.body.appendChild(input);
            var settled = false;
            var prompt = null;
            function done(files) {
                if (settled) return;
                settled = true;
                if (prompt) prompt.close();
                if (input.parentNode) input.parentNode.removeChild(input);
                resolve(files);
            }
            input.addEventListener('change', function () { done(Array.prototype.slice.call(input.files || [])); });
            input.addEventListener('cancel', function () { done([]); });

            if (hasActivation()) {
                input.click();
                return;
            }

            prompt = overlay(req.title || 'Choose a file');
            var p = document.createElement('p');
            p.textContent = req.multiple ? 'Choose the files to upload.' : 'Choose the file to upload.';
            prompt.body.appendChild(p);
            prompt.button('Cancel', false, function () { done([]); });
            prompt.button('Choose…', true, function () { input.click(); }).focus();
        });
    }

    async function postJson(url, data) {
        var r = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        var body = null;
        try { body = await r.json(); } catch (e) { body = null; }
        return { ok: r.ok, status: r.status, body: body };
    }

    async function uploadOne(req, file, progress) {
        var base = req.base + '/upload/' + encodeURIComponent(req.ticket) + '/files';
        var begin = await postJson(base, { name: file.name, size: file.size });
        if (!begin.ok) {
            throw new Error((begin.body && begin.body.error) || ('Upload refused (' + begin.status + ').'));
        }

        var id = begin.body.id;
        var offset = 0;
        while (offset < file.size) {
            var end = Math.min(offset + req.chunkBytes, file.size);
            var attempt = 0;
            for (;;) {
                var r = await fetch(base + '/' + encodeURIComponent(id) + '?offset=' + offset, {
                    method: 'PUT',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/octet-stream' },
                    body: file.slice(offset, end)
                });
                if (r.ok) break;
                var err = null;
                try { err = (await r.json()).error; } catch (e) { err = null; }
                // Network hiccups and 5xx are retried a few times; refusals are not.
                if (r.status >= 500 && attempt < 3) { attempt++; await new Promise(function (s) { setTimeout(s, 500 * attempt); }); continue; }
                throw new Error(err || ('Upload failed (' + r.status + ').'));
            }
            offset = end;
            progress(offset);
        }
        return id;
    }

    async function pick(req) {
        var files = await choose(req);
        if (!files.length) return [];

        var total = files.reduce(function (s, f) { return s + f.size; }, 0) || 1;
        var sent = 0;
        var box = overlay('Uploading');
        var line = document.createElement('div');
        var bar = document.createElement('div');
        bar.className = 'chvd-portal-progress';
        var fill = document.createElement('span');
        bar.appendChild(fill);
        box.body.appendChild(line);
        box.body.appendChild(bar);

        var ids = [];
        try {
            for (var i = 0; i < files.length; i++) {
                var f = files[i];
                line.textContent = f.name;
                var before = sent;
                ids.push(await uploadOne(req, f, function (done) {
                    fill.style.width = Math.round(100 * (before + done) / total) + '%';
                }));
                sent += f.size;
            }
            box.close();
            return ids;
        } catch (e) {
            box.body.textContent = e && e.message ? e.message : 'The upload failed.';
            await new Promise(function (resolve) {
                box.button('OK', true, resolve).focus();
            });
            box.close();
            return ids;
        }
    }

    // ── download, print, clipboard, links ─────────────────────────────────────────────────────

    function download(url, name) {
        var a = document.createElement('a');
        a.href = url;
        a.download = name || '';
        a.rel = 'noopener';
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { if (a.parentNode) a.parentNode.removeChild(a); }, 1000);
    }

    function isSafari() {
        var ua = navigator.userAgent;
        return /Safari\//.test(ua) && !/(Chrome|Chromium|Edg|OPR|Firefox|FxiOS|CriOS)\//.test(ua);
    }

    // Print the PDF with the browser's own viewer: load it in a hidden frame and call print() on it
    // (Chrome, Edge, Firefox). Safari can't print a PDF inside a frame, so there the PDF opens in a
    // new tab with its own print button.
    // A tab the person opens themselves. Browsers block a window that a page opens on its own after a
    // round trip to the server (it isn't the person's click any more), so the portal offers a link and
    // the person's click on it opens the PDF in its own tab, with the browser's print button.
    function offerTab(url) {
        var old = document.querySelector('.chvd-print-offer');
        if (old) old.parentNode.removeChild(old);
        var box = document.createElement('div');
        box.className = 'chvd-print-offer';
        box.setAttribute('role', 'status');
        var text = document.createElement('span');
        text.textContent = 'This browser prints a PDF from its own tab.';
        var link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.className = 'btn primary';
        link.textContent = 'Open the PDF to print';
        var close = document.createElement('button');
        close.type = 'button';
        close.className = 'btn';
        close.setAttribute('aria-label', 'Close');
        close.textContent = 'Close';
        function remove() { if (box.parentNode) box.parentNode.removeChild(box); }
        link.addEventListener('click', function () { setTimeout(remove, 0); });
        close.addEventListener('click', remove);
        box.appendChild(text);
        box.appendChild(link);
        box.appendChild(close);
        document.body.appendChild(box);
        setTimeout(remove, 120000); // the print link expires after 30 minutes; the offer goes sooner
        link.focus();
    }

    function print(url) {
        if (isSafari()) {
            // Safari can't print a PDF from inside a frame.
            offerTab(url);
            return Promise.resolve('tab');
        }

        return new Promise(function (resolve) {
            var frame = document.createElement('iframe');
            frame.className = 'chvd-portal-print';
            frame.setAttribute('aria-hidden', 'true');
            frame.tabIndex = -1;
            var finished = false;
            function finish(ok) {
                if (finished) return;
                finished = true;
                resolve(ok);
                // Keep the frame while the dialog is open (some browsers print asynchronously).
                setTimeout(function () { if (frame.parentNode) frame.parentNode.removeChild(frame); }, 120000);
            }
            frame.addEventListener('load', function () {
                // The PDF viewer needs a moment after load before print() picks up the document.
                setTimeout(function () {
                    try {
                        frame.contentWindow.focus();
                        frame.contentWindow.print();
                        finish('dialog');
                    } catch (e) {
                        // The PDF viewer refused print() from the page: let the person open it in a tab.
                        offerTab(url);
                        finish('tab');
                    }
                }, 300);
            });
            frame.addEventListener('error', function () { finish('failed'); });
            // No PDF viewer in the page (the person set PDFs to download or to open elsewhere): the frame
            // never loads, so offer the PDF in its own tab instead of failing.
            setTimeout(function () {
                if (!finished) {
                    offerTab(url);
                    finish('tab');
                }
            }, 20000);
            frame.src = url;
            document.body.appendChild(frame);
        });
    }

    async function copyImage(streamRef) {
        try {
            var buffer = await streamRef.arrayBuffer();
            var blob = new Blob([buffer], { type: 'image/png' });
            if (!navigator.clipboard || typeof ClipboardItem === 'undefined') return false;
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
            return true;
        } catch (e) {
            return false;
        }
    }

    async function copyText(text) {
        try {
            if (!navigator.clipboard) return false;
            await navigator.clipboard.writeText(text);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Reports the viewport to .NET (WebPlatformInfo) at start and after resizes settle, so the Ui
    // can follow the browser between desktop, tablet and phone layouts (Foundation F-5).
    function watchViewport(dotnet) {
        var coarse = window.matchMedia ? window.matchMedia('(pointer: coarse)') : null;
        var isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || '') || /Mac OS X/.test(navigator.userAgent);
        var last = '';
        var timer = null;
        function report() {
            var w = Math.round(window.innerWidth || document.documentElement.clientWidth || 0);
            var c = !!(coarse && coarse.matches);
            var key = w + '|' + c;
            if (key === last) return;
            last = key;
            dotnet.invokeMethodAsync('Report', w, c, isMac).catch(function () { });
        }
        window.addEventListener('resize', function () {
            if (timer) clearTimeout(timer);
            timer = setTimeout(report, 150);
        });
        if (coarse && coarse.addEventListener) coarse.addEventListener('change', report);
        report();
    }

    // D-181: while the open document has unsaved marks, the browser asks before a reload, a close or a move to
    // another site ("Leave site? Changes you made may not be saved"). The wording and look are the browser's.
    // A reload brings the tabs back (D-174) but not marks that were never saved.
    var unsavedMarks = false;
    function guardLeave(on) { unsavedMarks = on === true; }
    window.addEventListener('beforeunload', function (e) {
        if (!unsavedMarks) return undefined;
        e.preventDefault();
        e.returnValue = ''; // older browsers need a value set
        return '';
    });

    // Leave for another portal address. Only same-origin paths; returns at once, navigates after.
    // WT-31: Sign out in a fixed order. The page's own moves (the Ui going Home after the close card,
    // Blazor's history changes, a download link just clicked) must be over before the full page load to the
    // sign-out address starts, and nothing may start a move after it: in WebKit a later move cancelled that
    // load ("Frame load interrupted", "Navigation canceled by policy check"). So: wait until the page has
    // been quiet for a moment (capped), then stop all in-page moves and go.
    var lastMove = 0, departing = false;
    function noteMove() { lastMove = Date.now(); }
    ['pushState', 'replaceState'].forEach(function (name) {
        var original = history[name];
        if (typeof original !== 'function') return;
        history[name] = function () {
            if (departing) return undefined; // the page is leaving for good: no in-page move may cancel that
            noteMove();
            return original.apply(this, arguments);
        };
    });
    window.addEventListener('popstate', noteMove);
    var plainDownload = download;
    download = function (url, name) { noteMove(); return plainDownload(url, name); };
    function leaveWhenSettled(path, quietMs, maxMs) {
        if (typeof path !== 'string' || path.charAt(0) !== '/' || path.charAt(1) === '/') return Promise.resolve(false);
        var quiet = Math.max(50, quietMs | 0), until = Date.now() + Math.max(quiet, maxMs | 0);
        return new Promise(function (resolve) {
            (function check() {
                var now = Date.now();
                if (now - lastMove < quiet && now < until) { setTimeout(check, 50); return; }
                departing = true;
                unsavedMarks = false; // the person has answered the card
                window.location.assign(path);
                resolve(true);
            })();
        });
    }

    function leave(path) {
        if (typeof path !== 'string' || path.charAt(0) !== '/' || path.charAt(1) === '/') return;
        unsavedMarks = false; // the portal itself is leaving (the session ended): no question
        setTimeout(function () { window.location.replace(path); }, 0);
    }

    function openLink(url) {
        try {
            if (!/^(https?:|mailto:)/i.test(url)) return false;
            window.open(url, '_blank', 'noopener,noreferrer');
            // With "noopener" the browser returns null even when the tab opened.
            return true;
        } catch (e) {
            return false;
        }
    }

    // Session expiry (D-30): the server counts a person as active from their input in the page, reported
    // at most once a minute (the circuit's own keep-alive must not keep an abandoned tab alive).
    var lastReport = 0, pending = false, reportTimer = null, tracking = false;
    var REPORT_EVERY = 60000;

    function report() {
        reportTimer = null;
        pending = false;
        lastReport = Date.now();
        try {
            fetch('/portal/activity', { method: 'POST', credentials: 'same-origin', keepalive: true, headers: { 'X-Chvd-Activity': '1' } })
                .catch(function () { });
        } catch (e) { }
    }

    function onInput() {
        var since = Date.now() - lastReport;
        if (since >= REPORT_EVERY) {
            report();
        } else if (!pending) {
            pending = true;
            reportTimer = setTimeout(report, REPORT_EVERY - since);
        }
    }

    function trackActivity(everyMs) {
        if (tracking) return;
        tracking = true;
        if (everyMs >= 1000) REPORT_EVERY = everyMs;
        ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach(function (name) {
            document.addEventListener(name, onInput, { capture: true, passive: true });
        });
    }

    // "I'm still here": report now, whatever the last report was.
    function stillHere() {
        if (reportTimer) clearTimeout(reportTimer);
        report();
    }

    // D-89: a browser opens a file dropped on a page that doesn't take it, which would leave Chuvadi with
    // the file in the tab. The Ui's drop catcher (D-89 A) takes document drops; the Reader takes an image
    // dropped on a page. Anything neither handled (e.g. before the catcher has loaded) is cancelled here,
    // with the "not allowed" cursor while dragging. A drop onto a file input is the browser delivering
    // it to that input (the catcher's), so it is left alone.
    function hasFiles(e) {
        var types = e.dataTransfer && e.dataTransfer.types;
        return !!types && Array.prototype.indexOf.call(types, 'Files') >= 0;
    }
    function isFileInput(t) {
        return !!t && t.tagName === 'INPUT' && t.type === 'file';
    }
    document.addEventListener('dragover', function (e) {
        if (hasFiles(e) && !e.defaultPrevented && !isFileInput(e.target)) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'none';
        }
    });
    document.addEventListener('drop', function (e) {
        if (hasFiles(e) && !e.defaultPrevented && !isFileInput(e.target)) {
            e.preventDefault();
            holdForCatcher(e.dataTransfer);
        }
    });

    // WT-27: a document dropped in the first moment after the page appears, before the drop catcher can
    // take it, used to be cancelled without a word. It is kept and handed to the catcher's own file input
    // as soon as that is live, so it goes through exactly the checks and messages of any other drop.
    // (Once the catcher is live, a document drop that reaches this handler is one the Ui did not want, and is not kept.)
    // Image-only drops are not kept: the catcher doesn't take those (the Reader places them on a page).
    var held = null, heldSince = 0;
    function isImageOnly(files) {
        for (var i = 0; i < files.length; i++) {
            if (!(files[i].type && files[i].type.indexOf('image/') === 0)) return false;
        }
        return files.length > 0;
    }
    function holdForCatcher(dt) {
        // Only a drop made before the catcher is live is kept. Once it is live, a document drop that still
        // ends up here is one the Ui chose not to take (it hides the catcher when a drop isn't wanted): that
        // stays a cancelled drop, as before.
        if (catcherInput()) return;
        var files = dt && dt.files ? Array.prototype.slice.call(dt.files, 0, 64) : [];
        if (files.length === 0 || isImageOnly(files)) return;
        held = files;
        heldSince = Date.now();
        deliverHeld();
    }
    // The catcher's input is live once Blazor's InputFile has set itself up on it (it marks the element);
    // should that mark ever go away, an input that has been there for a second is taken as live.
    var inputSeen = 0;
    function catcherInput() {
        var input = document.querySelector('.pdrop input[type=file]');
        if (!input) { inputSeen = 0; return null; }
        if (!inputSeen) inputSeen = Date.now();
        return (input._blazorInputFileNextFileId !== undefined || Date.now() - inputSeen > 1000) ? input : null;
    }
    function deliverHeld() {
        if (!held) return;
        var input = catcherInput();
        if (!input) {
            if (Date.now() - heldSince < 20000) setTimeout(deliverHeld, 150); else held = null;
            return;
        }
        var files = held;
        held = null;
        try {
            var dt = new DataTransfer();
            files.forEach(function (f) { dt.items.add(f); });
            input.files = dt.files;
            input.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (err) {
            // A browser that can't put files into an input: the drop is lost, as before.
        }
    }

    window.chvdPortal = { guardLeave: guardLeave, pick: pick, download: function (u, n) { return download(u, n); }, leaveWhenSettled: leaveWhenSettled, print: print, copyImage: copyImage, copyText: copyText, openLink: openLink, watchViewport: watchViewport, leave: leave, trackActivity: trackActivity, stillHere: stillHere, dropCatcherLive: function () { return !!catcherInput(); } };
})();
