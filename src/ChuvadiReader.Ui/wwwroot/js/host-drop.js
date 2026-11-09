// W-02: files dropped anywhere on the page go to the host, which opens them (Bench shelf or Reader tabs).
// WebView2 (Windows) never gives the page a file's path, and its native window covers the WPF window, so
// the host's own Drop event can't fire over the page. Instead the dropped File objects are handed over with
// chrome.webview.postMessageWithAdditionalObjects; the host reads each CoreWebView2File.Path.
// Drops a component already handled (e.g. an image onto a page in Mark mode) are left alone.
(function () {
    const wv = window.chrome && window.chrome.webview;
    if (!wv || typeof wv.postMessageWithAdditionalObjects !== 'function') return;
    const hasFiles = (e) => !!e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0;
    window.addEventListener('dragover', (e) => {
        if (!hasFiles(e) || e.defaultPrevented) return;
        e.preventDefault(); // allow the drop (and keep the browser from opening the file itself)
        e.dataTransfer.dropEffect = 'copy';
    });
    window.addEventListener('drop', (e) => {
        if (!hasFiles(e) || e.defaultPrevented) return;
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) wv.postMessageWithAdditionalObjects('chvd:files-dropped', e.dataTransfer.files);
    });
})();
