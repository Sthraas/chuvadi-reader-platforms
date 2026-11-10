# Web portal browser tests (test tool only)

These drive a running portal with Playwright and the machine's Chrome. They are test tooling only and never shipped. Install with `pip install playwright`; it uses the installed Google Chrome (channel "chrome").

Each script works against both modes:
- **single**: the default, one process;
- **gateway**: `Portal__Mode=Gateway`, with per-person worker processes (D-24), as in production.

Each exits 0 when every check passes. Every script takes `--browser chrome|chromium|firefox|webkit`. The default is the machine's Chrome. Firefox runs with its own PDF viewer on, as it ships. WebKit is Safari's engine. Playwright's Chromium has no PDF viewer, so it stands in for "PDFs set to download". Install the extra engines with `python3 -m playwright install firefox webkit`.

```
cd src/ChuvadiReader.Web
env ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://127.0.0.1:5090 Portal__Mode=Gateway \
    "Logging__LogLevel__Microsoft.AspNetCore=Information" dotnet run > /tmp/portal.log 2>&1 &   # request log = print witness
```

| Script | Needs | Covers |
|---|---|---|
| `flows.py <base> <some.pdf> <out> <server log>` | Development sign-in | Open a PDF through the browser's file chooser. Split every page to a folder and receive one .zip (D-129). Print the current page (browser print of a PDF; `print()` is recorded, because headless Chrome has no print dialog). Merge two PDFs and receive the download. No console errors. |
| `sangam_signin.py <base> <sangam> <out> [--insecure]` | A Sangam run locally (see `docs/web/README.md`) | Register and sign in. The person's name and the account menu show. Cookie flags (`__Host-chvd` and Secure on https). Sign-out ends every tab. Sign in again. Signing out on Sangam ends the tab (back-channel). `--insecure` accepts a self-signed certificate, for rehearsing the production setup. |
| `expiry.py <base> <some.pdf> <out> [--data-root <dir>]` | Short limits: `Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:25 Portal__ExpiryCheckInterval=00:00:02` | D-30. The idle warning shows. "I'm still here" takes it down. The warning hands over both open documents as one zip. The ended session's page image is freed at once (WT-21). The session ends on the signed-out page, and the person's files are gone. |
| `load.py <base> <some.pdf> <out> <people> [--browsers N] [--server-dir <publish folder>]` | Development sign-in, gateway mode; a PDF of 8 pages or more | That many people at once, each with their own worker and (by default) their own browser process: open, upload, render, page, print. Each step timed in ms until the page is drawn, no fixed waits (WT-13). Reports step times, failures and the peak memory of the gateway and workers. |
| `check-package.sh <publish folder>` | A `dotnet publish` output | The package holds only what runs on the Linux server: no `web.config`, development settings, symbols or API docs (WT-11). CI runs it. |
| `office_limits.py <base> <out> [--browser …]` | Development sign-in | D-137: the portal keeps the strict Word limits. A normal .docx opens with its double spaces; one showing a 25 MB picture and a zip bomb (100 MB unpacked from 100 KB) are refused as "too large to open"; the portal still answers. |
| `page_images.py <base> <out> [--browser …]` | Development sign-in, gateway mode | D-158: a large-format page is drawn from `/_chvd/pages/<token>.png` (200, image/png, private, no-store); another signed-in person gets 404; someone not signed in gets 404 with no redirect (WT-20); after the tab closes the owner gets 404. |
