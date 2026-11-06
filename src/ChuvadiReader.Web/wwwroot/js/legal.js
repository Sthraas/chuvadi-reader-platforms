// The legal pages are plain HTML rendered on the server (readable before sign-in); this turns the
// document switch (Terms of use, Privacy, Cookies, Third-party notices) into links to their addresses.
(function () {
    var links = (document.body.getAttribute('data-chvd-docs') || '').split(' ');
    document.querySelectorAll('.seg .seg-opt').forEach(function (button, i) {
        if (!links[i]) return;
        button.addEventListener('click', function () { location.assign(links[i]); });
    });
})();
