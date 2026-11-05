// Android host: tells the page which form factor it is showing, as html[data-form-factor].
//   tablet — the window's shorter side is at least 600 dp (Android's own tablet line, sw600dp)
//   phone  — anything smaller
// CSS px in the Android WebView are dp, so the window size here is the size Android uses.
// Re-evaluated on every resize: split screen, freeform windows and foldables can move a running
// app between the two.
(function () {
    var root = document.documentElement;
    function apply() {
        var shorter = Math.min(window.innerWidth, window.innerHeight);
        var ff = shorter >= 600 ? 'tablet' : 'phone';
        if (root.getAttribute('data-form-factor') !== ff) root.setAttribute('data-form-factor', ff);
        root.setAttribute('data-platform', 'android');
    }
    apply();
    window.addEventListener('resize', apply);
})();
