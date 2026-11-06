// The sign-in page (12a) is plain HTML rendered on the server; this wires its one action. "Continue
// with Sangam" leaves for Sangam through the portal (the address carries where to come back to).
(function () {
    var target = document.body.getAttribute('data-chvd-signin') || '/signin/sangam';
    function go(e) {
        if (e) e.preventDefault();
        document.querySelectorAll('.psi-sangam, .psi-submit').forEach(function (b) { b.disabled = true; });
        location.assign(target);
    }
    var button = document.querySelector('.psi-sangam');
    if (button) button.addEventListener('click', go);
    var form = document.querySelector('form.psi-card');
    if (form) form.addEventListener('submit', go);
})();
