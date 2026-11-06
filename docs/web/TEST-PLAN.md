# Web portal — test plan

For the Web Test chat. It covers every flow, the security checks, Sangam failure cases, expiry, load and concurrency, and the browser matrix. Each check has an ID, what to do, what must happen, and where it is already automated. Run the automated parts first; the manual parts are what automation can't reach.

**Coverage key**
- **U**: `tests/ChuvadiReader.Web.Tests` (xUnit). Runs in CI (`web.yml`) and with `dotnet test`.
- **E**: `tests/web-e2e/*.py` (Playwright, real browsers, against a running portal). See `tests/web-e2e/README.md`.
- **M**: manual.
- **P**: pending something not yet available (named in the row).

Test tooling (Playwright, its browsers, PostgreSQL for the local Sangam) is used for testing only and never shipped (rule 3).

## 0. Environments

| Name | How | Used for |
|---|---|---|
| Unit | `dotnet test tests/ChuvadiReader.Web.Tests -c Release` | U (gateway tests start real worker processes) |
| Local single | `ASPNETCORE_ENVIRONMENT=Development dotnet run` in `src/ChuvadiReader.Web` | Quick checks with the Development sign-in (`X-Dev-User` picks the person) |
| Local gateway | as above with `Portal__Mode=Gateway` | As in production: a worker per person |
| Local Sangam | `docs/web/README.md` § "Testing against a real Sangam run locally" | Sign-in, sign-out, back-channel |
| Production rehearsal | `ASPNETCORE_ENVIRONMENT=Production`, gateway mode, data root on tmpfs (`/dev/shm/...`), TLS from a test PEM on 8443, `ASPNETCORE_HTTPS_PORT`, `--insecure` in the e2e | Start-up checks, redirects, headers, cookies as in production |
| Staging VM | Same size as production (runbook §2), before go-live | Load at real size, real Let's Encrypt staging, real Sangam |

The whole shared solution must pass before any push: `dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror` and `dotnet test ChuvadiReader.Platforms.slnx`, plus the Web tests.

## 1. Flows

| ID | Flow | Must happen | Coverage |
|---|---|---|---|
| F-1 | Visitor opens `/` | 12a sign-in page: "Continue with Sangam", "Download the desktop app", "Terms of use"; no password or Sangam ID field (D-34, U-9 a) | U `The_sign_in_page_is_12a…`, E `sangam_signin.py` |
| F-2 | Continue with Sangam → sign in → back | The Reader opens; the status bar and account menu show the name and Sangam ID (and the unit when Sangam sends `sangam_org`) | U full sign-in ×2 (secret, private_key_jwt); E `sangam_signin.py` |
| F-3 | Upload a document (left bar Upload, Home "Upload a file…") | Browser file chooser, one file; it opens in the Reader | E `flows.py` |
| F-4 | Read: page, zoom, find | As on the desktop | E `load.py` (paging); M |
| F-5 | Mark: add marks, Save marks into this file (Ctrl S) / Save as new PDF | A download of the marked PDF; on the web, saving is always a download | M |
| F-6 | Arrange: merge two PDFs | Chooser allows several files; `merged.pdf` downloads | E `flows.py` |
| F-7 | Arrange: split, Bench, press | Results download | M |
| F-8 | Protect: redact, password protect, remove password | Results download; refusals as on the desktop | M |
| F-9 | Print the current page / a range / everything / a password-protected file | Chrome/Edge/Firefox: the browser's print dialog with a PDF of just those pages. Safari, or a browser set to download PDFs: "Open the PDF to print" link, which opens the PDF in its own tab | E `flows.py` (4 engines); M on real Safari/Edge |
| F-10 | Print a file whose permissions forbid printing | Print card locked with "This file's permissions don't allow printing."; the server refuses as well, nothing reaches the browser (L-8) | U `WebPrintTests`; M (card) |
| F-11 | Copy text / copy an image | Clipboard; the browser may ask permission for images | M (per browser) |
| F-12 | External links (desktop app, account settings) | Open in a new tab with no handle back to the portal | M |
| F-13 | Account menu → Sign out | Sangam end-session → signed-out page; every other tab of that sign-in also goes to the signed-out page | E `sangam_signin.py` |
| F-14 | Sign out on Sangam itself | Back-channel: the open portal tab goes to the signed-out page within seconds | E `sangam_signin.py` |
| F-15 | Terms of use | `/licence` readable before sign-in; switch between agreement, licence and notices | U `GatewayTests`, `LicencePageTests`; M |
| F-16 | Two tabs, one person | Both work; signing out in one ends the other | E `sangam_signin.py` |
| F-17 | Two people at once | Separate workers; nothing of one visible to the other | U `GatewayTests`; E `load.py` |
| F-18 | Phone and tablet sizes | Form factor follows the browser (D-07); phone layout from the Mobile UI chat | M (Chrome device mode, real phone) |
| F-19 | Mac keyboard | ⌘ labels and shortcuts on macOS browsers (D-07) | M |
| F-20 | Planned restart banner | Operator file → banner in every tab, including later arrivals; gone when the time passes or the file is removed | U `MaintenanceTests`, `GatewayMaintenanceTests`; M (runbook §8.9) |
| P-1 | Portal Terms of Use and Privacy Notice at `/terms`, `/privacy`, readable before sign-in | Served like `/licence`; "Terms of use" points to `/terms` | **P**: the Foundation's legal drafts |
| P-2 | Drop a file on Home | Foundation item (drop-zone options) | **P** |

## 2. Security checks

| ID | Check | Must happen | Coverage |
|---|---|---|---|
| S-1 | Sign-in on every endpoint | Only these are anonymous: `/signin`, `/signin/sangam`, `/signin-sangam`, `/signout`, `/signout-sangam`, `/signed-out`, `/backchannel-logout`, `/licence`, `/healthz`, `/error`, static files. Every other route (Reader pages, circuit, uploads, downloads, print, activity, the gateway relay) needs a signed-in person. Pages without sign-in redirect to `/signin`; `/portal/*` and `/_blazor` answer 401 | U `EndpointAuthTests` (lists every route in single and gateway mode), `Anonymous_pages_go_to_sign_in…` |
| S-2 | Cookie | `__Host-chvd` on https (Secure, HttpOnly, SameSite=Lax, path /), `chvd.session` on local http; 8 h absolute, not sliding; no sign-in flow cookie left behind | U; E (`--insecure` on the rehearsal) |
| S-3 | Sign-in protocol | PKCE S256, state, nonce, RFC 9207 `iss`; ID token signature, `alg` allow-list (no `none`, no HS*), `iss`, `aud`, `azp`, expiry, nonce, unknown `kid`; flow cookie bound to the browser, 10 min | U `SangamSignInTests` (refusal cases) |
| S-4 | Open redirect | `returnUrl` only local (`//evil`, `/\\evil`, absolute URLs, CR/LF refused) — on `/signin`, the page's link and the callback | U |
| S-5 | Back-channel logout | Only a valid `logout+jwt` (signature, `aud`, events, no nonce, `jti`, `sid` or `sub`) ends anything; replay does nothing; a copied cookie stops working at once | U |
| S-6 | Cross-site requests | Uploads, activity reports and sign-out refuse other origins (`Origin` / `Sec-Fetch-Site`); custom header on activity | U `EndpointTests`, `ActivityEndpointTests` |
| S-7 | Upload validation | Allowed types per chooser (desktop dialog list), content must match the extension (magic bytes), size and count limits, chunk limit, chunks in order and within the announced size, names cleaned (no folders, control characters, reserved names), same names don't overwrite, incomplete files discarded, tickets owner-only and expiring | U `UploadTests`, `TicketTests`, `EndpointTests` |
| S-8 | Downloads and print links | Unguessable, single-use (downloads), owner-only, expiring; print serves the PDF inline only to its owner | U `TicketTests`, `EndpointTests` |
| S-9 | Isolation between people (D-24) | One worker process per person; a worker answers only its gateway (secret on stdin) and only its person; browser `X-Chvd-*` headers stripped; `/_worker/*` 404 to browsers; gateway cookies never reach a worker; socket and worker folders 0700; no `Sangam__`/TLS settings or secrets in a worker's environment; memory cap; no crash dumps | U `GatewayTests` |
| S-10 | File wiping | A person's files go when: the tab closes (after the 3-min reconnect window), they sign out, Sangam signs them out, the session expires, the worker is idle-stopped, the worker crashes, the gateway stops, or the portal starts after a crash (sweep) | U `GatewayTests` (end, crash, stop), `SpaceLayoutTests` (sweep); E `expiry.py --data-root`; E `load.py` + listing (all workers gone after everyone left) |
| S-11 | Expiry (D-30) | 30 min idle, 8 h absolute; warning 5 min before in every open tab; "I'm still here", any input or a page load takes the idle warning down; only real activity counts (not the circuit's keep-alive, not static files); at the end the cookie stops working and files go | U `SessionClockTests`; E `expiry.py` (short limits) |
| S-12 | Working copies at rest (D-28) | Outside Development, start-up refused unless `DataRoot` is on tmpfs and swap is off, dm-crypt or zram; Data Protection keys never on disk | U `StorageCheckTests`; M (rehearsal: refusal on a disk data root) |
| S-13 | Transport and headers | HTTPS redirect (307 to the public port), HSTS, CSP (`script-src 'self'`, `frame-ancestors 'self'`), `nosniff`, frame and referrer policy, no `Server` header; TLS 1.2/1.3 only | U `Every_response_carries_the_security_headers`; M (rehearsal, `curl -vk`) |
| S-14 | Certificates | Let's Encrypt via our ACME client: order, renew in window, keep working certificate on failure, hot swap without restart | U `Acme*Tests`, `CertificateSourceTests`; **P** staging run on the real domain |
| S-15 | Error handling | Unexpected failures show `/error` (anonymous; never loops through sign-in); no stack traces outside Development | U `The_error_page_needs_no_sign_in…`; M |
| S-16 | Logs | No document content, tokens, passwords or cookies in logs; worker log lines carry a key hash, not the person's id | M (`journalctl` review during staging) |
| S-17 | Untrusted input on public pages | `/licence?part=` anything → the agreement, nothing echoed; sign-in error text encoded | U `GatewayTests` licences page |
| S-18 | Hostile documents | Malformed, huge, deeply nested or decompression-bomb PDFs/DOCX/XLSX only hang or exhaust their own worker (memory cap); others unaffected | M (fuzz corpus) during staging; U covers the cap's presence |

## 3. Sangam failure cases

| ID | Case | Must happen | Coverage |
|---|---|---|---|
| G-1 | Sangam down at "Continue with Sangam" | Sign-in page with "Sangam can't be reached right now…" (503) | U `SangamUnreachableTests` |
| G-2 | Sangam down at sign-out | Portal session ended anyway; signed-out page | U |
| G-3 | Sangam down at the callback (token endpoint) | Same message on the sign-in page | U (same filter); M (stop Sangam between authorize and callback) |
| G-4 | Discovery document wrong (bad JSON, wrong issuer, missing endpoint) | Same message; reason in the log | U (filter covers it); M |
| G-5 | Key rotation (new `kid`) | Keys refreshed once (rate-limited), sign-in works | U (`kid` refusal when truly unknown); M (rotate keys on the local Sangam) |
| G-6 | Person denies consent (`access_denied`) | Signed-out page | U (callback path); M |
| G-7 | Answer without `iss` while Sangam promises it; wrong `iss` (mix-up) | Refused | U |
| G-8 | Clock skew | ±2 min accepted; beyond refused | U (`exp`); M (skew the VM clock on staging) |
| G-9 | Slow Sangam | Sign-in waits up to the HTTP timeout, then G-1's message; other people unaffected | M |
| G-10 | Back-channel token with `sid` only / `sub` only / neither | `sid`: that sign-in; `sub`: every sign-in of the person; neither: refused | U |
| G-11 | Sangam's development issuer unset (finding 3) | Logout tokens refused (by design) | Noted in SANGAM-INTEGRATION; M on local runs |
| G-12 | Person in several organisations | Sangam's chooser appears (intended); unit shows the chosen one | **P** a Sangam test person in two organisations |

## 4. Load and concurrency

| ID | Check | Must happen | Coverage |
|---|---|---|---|
| L-1 | N people at once (3, 10, 15 here; up to `MaxWorkers` on staging) | All succeed; step times recorded; memory per worker ≈ 175 MB + documents | E `load.py` |
| L-2 | Same person, many requests at once | Exactly one worker starts | U `Many_requests_at_once…` |
| L-3 | `MaxWorkers` reached | Newcomers see "The portal is busy"; people already in are unaffected | U |
| L-4 | Worker crash under load | Only that person is affected; their next request gets a fresh worker; files cleaned | U (crash); M (kill a worker during `load.py`) |
| L-5 | Everyone leaves | All workers stop within reconnect window + `IdleStop` + check interval (~6 min); data root empty | E (`load.py` then watch `workers/`) |
| L-6 | Soak: 40 people for 2 hours on staging | No memory growth in the gateway; worker memory returns when people leave; no file left behind | **P** staging VM |
| L-7 | Large documents (300-page scan, 200 MB upload limit) | Upload in chunks completes; rendering within the worker cap | M on staging |
| L-8 | Restart under load (planned, with the banner) | Banner shown in advance; restart ends sessions cleanly; people sign in again | M (runbook §9) |

## 5. Browser matrix

| Browser | Engine run here | Status | Browser-specific behaviour to check |
|---|---|---|---|
| Chrome (desktop) | Chrome stable | F-3, F-6, F-9, F-13, F-14, F-16, S-11 pass | Print dialog over a hidden frame |
| Edge (desktop) | Same engine as Chrome | **M** | As Chrome; check Edge's own PDF viewer prints |
| Firefox (desktop) | Playwright Firefox with its PDF viewer on (as shipped) | F-3, F-6, F-9, F-13, F-14, S-11 pass | Print through pdf.js; a person who set PDFs to "save" gets the link after 20 s |
| Safari (macOS) | Playwright WebKit | F-3, F-6, F-9 (link to own tab), F-13, F-14, S-11 pass | Popup rules (the link is the person's click); clipboard image permission; ⌘ labels; **M on a real Mac** |
| Safari (iPhone/iPad) | — | **M** | Upload from Files/Photos; print via the share sheet in the PDF tab; phone/tablet layout; touch |
| Chrome (Android) | — | **M** | Upload from device; print; phone layout |
| A browser with no PDF viewer | Playwright Chromium | F-9 passes (link after 20 s) | — |

Run the engines here: `python3 tests/web-e2e/flows.py <base> <pdf> <out> <log> --browser chrome|firefox|webkit|chromium` (same flag on `sangam_signin.py` and `expiry.py`).

## 6. Deployment checks

Runbook §8 on the VM, in order. They cover the start-up refusal, `/healthz`, Let's Encrypt staging and then production, the redirects and headers, a real sign-in and print, sign-out with the folder wiped, back-channel, expiry and the restart banner.

## 7. Run log

**7 Nov 2026, this sandbox: 2 cores, 8 GB, Ubuntu 24.04, .NET 10.0.14.**

| Run | Result |
|---|---|
| Shared solution build (`-warnaserror`) and tests | 0 warnings; Reader 171, Hosting 33, Mobile UI 11, Web UI 19 passed |
| Web tests | 140/140 |
| `flows.py` through the gateway | Chrome 6/6, Firefox 6/6, WebKit 6/6, Chromium (no PDF viewer) 6/6 |
| `sangam_signin.py` through the gateway, real local Sangam | Chrome, Firefox, WebKit: all checks pass (back-channel 0–4 s) |
| `expiry.py` (40 s idle, 25 s warning) | Chrome, Firefox, WebKit: 8/8 each, files gone |
| `load.py` 10 people | 10/10; ready 3.7 s, upload+render 6.1 s, print 4.0 s (medians); ~176 MB per worker |
| Production rehearsal (6–7 Nov) | D-28 refusal, 307 redirect, headers, `__Host-chvd` Secure, sign-in and sign-out pass; back-channel not testable (self-signed certificate) |

Found and fixed while running this plan:
- Print in Safari: a tab opened by the page was blocked, so the portal now offers a link.
- A browser that downloads PDFs waited 60 s and then failed; it now gets the link after 20 s.
- The print message now says which of the two happened.

## 8. Known gaps
- **P-1:** `/terms` and `/privacy` wait for the Foundation's portal Terms of Use and Privacy Notice. Until then, "Terms of use" opens the desktop EULA, which itself refers to portal terms that don't exist yet.
- Real Edge, real Safari (macOS and iOS) and Android Chrome need manual runs.
- Staging-only items: L-6, L-7, S-14, S-16, S-18, G-12.
