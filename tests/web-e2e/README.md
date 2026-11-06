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
| `flows.py <base> <some.pdf> <out> <server log>` | Development sign-in | Open a PDF through the browser's file chooser. Print the current page (browser print of a PDF; `print()` is recorded, because headless Chrome has no print dialog). Merge two PDFs and receive the download. No console errors. |
| `sangam_signin.py <base> <sangam> <out> [--insecure]` | A Sangam run locally (see `docs/web/README.md`) | Register and sign in. The person's name and the account menu show. Cookie flags (`__Host-chvd` and Secure on https). Sign-out ends every tab. Sign in again. Signing out on Sangam ends the tab (back-channel). `--insecure` accepts a self-signed certificate, for rehearsing the production setup. |
| `expiry.py <base> <some.pdf> <out> [--data-root <dir>]` | Short limits: `Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:25 Portal__ExpiryCheckInterval=00:00:02` | D-30. The idle warning shows. "I'm still here" takes it down. The warning hands over the open document. The session ends on the signed-out page, and the person's files are gone. |
| `load.py <base> <some.pdf> <out> <people> [--server-dir <publish folder>]` | Development sign-in, gateway mode | That many people at once, each with their own worker: open, upload, render, page, print. Reports step times, failures and the peak memory of the gateway and workers. |
