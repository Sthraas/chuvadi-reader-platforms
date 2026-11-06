// The licences page is plain HTML rendered on the server (readable before sign-in); this turns its
// three-way switch into links: Licence agreement, Licence, Third-party notices.
(function () {
    var base = document.body.getAttribute('data-chvd-licence') || '/licence';
    var parts = ['eula', 'licence', 'notices'];
    document.querySelectorAll('.seg .seg-opt').forEach(function (button, i) {
        if (!parts[i]) return;
        button.addEventListener('click', function () { location.assign(base + '?part=' + parts[i]); });
    });
})();
