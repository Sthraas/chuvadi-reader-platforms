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

    // Leave for another portal address. Only same-origin paths; returns at once, navigates after.
    function leave(path) {
        if (typeof path !== 'string' || path.charAt(0) !== '/' || path.charAt(1) === '/') return;
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

    window.chvdPortal = { pick: pick, download: download, print: print, copyImage: copyImage, copyText: copyText, openLink: openLink, watchViewport: watchViewport, leave: leave, trackActivity: trackActivity, stillHere: stillHere };
})();
