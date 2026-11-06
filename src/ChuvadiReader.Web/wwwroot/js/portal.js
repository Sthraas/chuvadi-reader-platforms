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
    function print(url) {
        if (isSafari()) {
            window.open(url, '_blank', 'noopener');
            return Promise.resolve(true);
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
                        finish(true);
                    } catch (e) {
                        // Cross-viewer restriction: fall back to a new tab.
                        window.open(url, '_blank', 'noopener');
                        finish(true);
                    }
                }, 300);
            });
            frame.addEventListener('error', function () { finish(false); });
            setTimeout(function () { finish(false); }, 60000);
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

    window.chvdPortal = { pick: pick, download: download, print: print, copyImage: copyImage, openLink: openLink };
})();
