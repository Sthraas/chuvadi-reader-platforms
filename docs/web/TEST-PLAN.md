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

From a clean clone, restore from the committed feed first (WT-12; the root `nuget.config` points at a local folder that isn't in git):

```
dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config
dotnet restore tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj --configfile ci/nuget.config
```

Before any push, both must pass:
- the whole shared solution: `dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror` and `dotnet test ChuvadiReader.Platforms.slnx -c Release`;
- the Web portal: `dotnet build tests/ChuvadiReader.Web.Tests -c Release -warnaserror` (builds the portal too) and `dotnet test tests/ChuvadiReader.Web.Tests -c Release`.

The Web projects aren't in `ChuvadiReader.Platforms.slnx` on purpose: that solution runs on every runner the hosts use (Linux x64 and Arm, macOS, Windows), and the Web tests need Linux (Unix sockets, `/proc`, per-person worker processes). CI builds Web in `web.yml` with `-warnaserror`, and checks the published package (`tests/web-e2e/check-package.sh`, WT-11).

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
| F-15 | Legal pages (D-86) | `/terms`, `/privacy`, `/licence?part=cookies|notices` readable before sign-in, with no worker started. The portal's four documents (terms of use, privacy, cookies, third-party notices), not the apps' EULA. Each shows its DRAFT line and the copyright line. The switch moves between the four addresses. The 12a "Terms of use" opens `/terms` | U `GatewayTests` (legal pages), `LicencePageTests`, `EndpointAuthTests`; E browser check (switch, 4 addresses); M on each browser in §5 |
| F-16 | Two tabs, one person | Both work; signing out in one ends the other | E `sangam_signin.py` |
| F-17 | Two people at once | Separate workers; nothing of one visible to the other | U `GatewayTests`; E `load.py` |
| F-18 | Phone and tablet sizes | Form factor follows the browser (D-07); phone layout from the Mobile UI chat | M (Chrome device mode, real phone) |
| F-19 | Mac keyboard | ⌘ labels and shortcuts on macOS browsers (D-07) | M |
| F-20 | Planned restart banner | Operator file → banner in every tab, including later arrivals; gone when the time passes or the file is removed | U `MaintenanceTests`, `GatewayMaintenanceTests`; M (runbook §8.9) |
| F-21 | Drop a file anywhere on the portal (D-89) | The browser never opens the file or leaves Chuvadi: documents go to the drop catcher (F-22); a drop that misses it is cancelled. An image dropped onto a page in the Reader still adds it (the Reader's own drop) | E `flows.py` (a stray drop is cancelled); M with a real file from the desktop on each browser in §5 |
| F-22 | Drop documents on the portal (D-89 A) | Each dropped file streams to the session's working copy (tmpfs, D-28) through the upload's own checks (S-7: types, content matches the extension, size, owner-only folder) and opens in its own tab (or on the Bench shelf when it's open). A refused file gives one short message and leaves nothing behind. Several files at once, up to 64 | U `DroppedFilesTests`; E `flows.py` (a fake PDF refused with its message; a real PDF opens in the Reader, through a worker); M: drag one and several real files from the desktop, an image onto a Reader page, and a 300 MB file (refused) on each browser in §5 |
| F-23 | Privacy link on the sign-in page and account menu (D-86, D-97) | "Terms of use · Privacy" on 12a and in the account menu footer; `/privacy` opens before sign-in | U `SangamSignInTests`; E (Web Test) |
| F-24 | Save that writes several files (D-129, WT-16): "Split to folder", Scatter, export pages | One `.zip` download, named after what the files share ("report.zip"), holding every file byte for byte with its folder path; one file goes as itself; committing again sends nothing new; no multi-download prompt, nothing for Safari to block | U `ZipSaveTests`; E `flows.py` (split: one .zip of every page, 4 engines); M Safari on Mac and iPhone (§5a) |
| F-25 | Word and Excel limits (D-136, D-137: the portal keeps the strict Word limits) | A normal .docx opens as in the file; a .docx showing a picture over 20 MB, or unpacking to more than 64 MB (a zip bomb), says "too large to open"; the worker stays up | E `office_limits.py` (4 engines); Foundation `OfficeViewTests` pin the figures |
| F-26 | Open tabs belong to the signed-in session (D-174, WT-22) | A reload, the portal's address opened again, a dropped connection or a second browser tab of the same sign-in shows the same tabs (order, active tab, page); the active document is drawn again from the same working copy; settings and recents survive too. A tab closed before a reload stays closed. Closing the browser tab without signing out and coming back within the session shows the documents again. Another person, or the same person's other sign-in, sees none of it. Not kept across a reload: marks not yet saved into the file, and a typed password (asked again) | U `SessionKeepsTabsTests`; E `reload.py` (4 engines), `comeback.py`, `sangam_signin.py` (real cookie and sid, 3 engines); M on a phone: lock the screen for a minute, unlock |
| F-27 | What a connection and a session let go of (WT-22, WT-21) | A connection that ends (reload, tab closed) closes the documents it had open at once: their page images answer 404 within seconds and their memory is freed; the saved tab list is untouched. When the session ends (sign-out, expiry, a Sangam sign-out), with any number of connections or none: every page image of that sign-in is freed (`PageImages.RemoveOwner`), its folder is deleted, its settings dropped, and its worker stops | U `SessionKeepsTabsTests`; E `reload.py`, `expiry.py` (a reload, then expiry: both images 404, files gone), `comeback.py` (expiry with no tab open: worker and files gone) |

## 2. Security checks

| ID | Check | Must happen | Coverage |
|---|---|---|---|
| S-1 | Sign-in on every endpoint | Only these are anonymous: `/signin`, `/signin/sangam`, `/signin-sangam`, `/signout`, `/signout-sangam`, `/signed-out`, `/backchannel-logout`, `/terms`, `/privacy`, `/licence`, `/healthz`, `/error`, static files. Every other route (Reader pages, circuit, uploads, downloads, print, activity, the gateway relay) needs a signed-in person. Pages without sign-in redirect to `/signin`; `/portal/*` and `/_blazor` answer 401 | U `EndpointAuthTests` (lists every route in single and gateway mode), `Anonymous_pages_go_to_sign_in…` |
| S-2 | Cookie | `__Host-chvd` on https (Secure, HttpOnly, SameSite=Lax, path /), `chvd.session` on local http; 8 h absolute, not sliding; no sign-in flow cookie left behind | U; E (`--insecure` on the rehearsal) |
| S-3 | Sign-in protocol | PKCE S256, state, nonce, RFC 9207 `iss`; ID token signature, `alg` allow-list (no `none`, no HS*), `iss`, `aud`, `azp`, expiry, nonce, unknown `kid`; flow cookie bound to the browser, 10 min | U `SangamSignInTests` (refusal cases) |
| S-4 | Open redirect | `returnUrl` only local (`//evil`, `/\\evil`, absolute URLs, CR/LF refused) — on `/signin`, the page's link and the callback | U |
| S-5 | Back-channel logout | Only a valid `logout+jwt` (signature, `aud`, events, no nonce, `jti`, `sid` or `sub`) ends anything; replay does nothing; a copied cookie stops working at once | U |
| S-6 | Cross-site requests | Uploads, activity reports, sign-out and the circuit (`/_blazor` negotiate and WebSocket, WT-07) refuse other origins (`Origin` / `Sec-Fetch-Site`); custom header on activity | U `EndpointTests`, `GatewayTests.The_circuit_opens_only_from_the_portals_own_pages`, `ActivityEndpointTests` |
| S-7 | Upload validation | Allowed types per chooser (desktop dialog list), content must match the extension (magic bytes), size and count limits, chunk limit, chunks in order and within the announced size, names cleaned (no folders, control characters, reserved names), same names don't overwrite, incomplete files discarded, tickets owner-only and expiring | U `UploadTests`, `TicketTests`, `EndpointTests` |
| S-8 | Downloads and print links | Unguessable, single-use (downloads), owner-only, expiring; print serves the PDF inline only to its owner | U `TicketTests`, `EndpointTests` |
| S-9 | Isolation between people (D-24) | One worker process per person; a worker answers only its gateway (secret on stdin) and only its person; browser `X-Chvd-*` headers stripped; `/_worker/*` 404 to browsers; gateway cookies never reach a worker; socket and worker folders 0700; no `Sangam__`/TLS settings or secrets in a worker's environment; memory cap; no crash dumps | U `GatewayTests` |
| S-10 | File wiping | A person's files go when: the tab closes (after the 3-min reconnect window), they sign out, Sangam signs them out, the session expires, the worker is idle-stopped, the worker crashes, the gateway stops, or the portal starts after a crash (sweep) | U `GatewayTests` (end, crash, stop), `SpaceLayoutTests` (sweep); E `expiry.py --data-root`; E `load.py` + listing (all workers gone after everyone left) |
| S-11 | Expiry (D-30) | 30 min idle, 8 h absolute; warning 5 min before in every open tab; "I'm still here", any input or a page load takes the idle warning down; only real activity counts (not the circuit's keep-alive, not static files); at the end the cookie stops working and files go | U `SessionClockTests`; E `expiry.py` (short limits) |
| S-12 | Working copies at rest (D-28) | Outside Development, start-up refused unless `DataRoot` is on tmpfs and swap is off, dm-crypt or zram; Data Protection keys never on disk | U `StorageCheckTests`; M (rehearsal: refusal on a disk data root) |
| S-13 | Transport and headers | HTTPS redirect (307 to the public port), HSTS, CSP (in gateway mode too: a relayed Reader page carries the full policy, WT-01) (`script-src 'self'`, `frame-ancestors 'self'`), `nosniff`, frame and referrer policy, no `Server` header; TLS 1.2/1.3 only | U `Every_response_carries_the_security_headers`; M (rehearsal, `curl -vk`) |
| S-13a | Sangam address (WT-15) | Outside Development, start-up is refused unless `Sangam:Authority` is https (discovery, keys and the token call with the client secret never go over plain http) | U `StorageCheckTests.Production_refuses_a_sangam_address_that_isnt_https` |
| S-19 | Page images by address (D-158; **Web Test security pass before it ships**) | `/_chvd/pages/<32 hex>.png`: 200 only to the person **and** sign-in (Sangam `sid`) that drew it, computed from the server's own sign-in; another person, the same person's other sign-in, unknown, freed (page or tab closed), malformed or path-like addresses: the same 404; not signed in, signed out or expired: a plain 404 with nothing redirected, so the token never lands in a returnUrl, an address or history (WT-20); `Sec-Fetch-Site` cross-site or same-site, or a foreign `Origin`: 404; `Cache-Control: private, no-store`, `Cross-Origin-Resource-Policy: same-origin`, `nosniff`, no CORS; fetches don't count as activity; when a session ends (sign-out, expiry) its open documents are closed and their images freed at once (WT-21) | U `PageImageEndpointTests`; E `page_images.py` (gateway, 4 engines), `expiry.py` (image 404 right after expiry, 3 engines); Web Test: token guessing and timing, another user's and another session's cookie, after sign-out and expiry |
| S-14 | Certificates | Let's Encrypt via our ACME client: order, renew in window, keep working certificate on failure, hot swap without restart | U `Acme*Tests`, `CertificateSourceTests`; **V-2** on staging |
| S-15 | Error handling | Unexpected failures show `/error` (anonymous; never loops through sign-in); no stack traces outside Development | U `The_error_page_needs_no_sign_in…`; M |
| S-16 | Logs | No document content, tokens, passwords or cookies in logs; worker log lines carry a key hash, not the person's id | M (`journalctl` review during staging) |
| S-17 | Untrusted input on public pages | `/licence?part=` anything → the agreement, nothing echoed; sign-in error text encoded | U `GatewayTests` licences page |
| S-18 | Hostile documents | Malformed, huge, deeply nested or decompression-bomb PDFs/DOCX/XLSX only hang or exhaust their own worker (memory cap); others unaffected | M (fuzz corpus) during staging; U covers the cap's presence |

## 3. Sangam failure cases

| ID | Case | Must happen | Coverage |
|---|---|---|---|
| G-1 | Sangam down at "Continue with Sangam" | Sign-in page with "Sangam can't be reached right now…" (503) | U `SangamUnreachableTests` |
| G-2 | Sangam down at sign-out | Portal session ended anyway; signed-out page | U |
| G-3 | Sangam down at the callback (token endpoint) | Same message on the sign-in page | U `SangamTimeoutTests` (a token call that hangs gives up at 10 s, O-1); M (stop Sangam between authorize and callback) |
| G-3a | Sangam stops after discovery is cached (O-2) | "Continue with Sangam" probes Sangam (2 s limit, answer reused 30 s) and shows the same message instead of sending the browser to a dead Sangam | U `SangamTimeoutTests`; M (stop the local Sangam, wait 30 s, press "Continue with Sangam") |
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
| L-6 | Soak: 40 people for 2 hours | No memory growth in the gateway; worker memory returns when people leave; no file left behind | **V-1** on staging |
| L-7 | Large documents | Upload in chunks completes; rendering stays within the worker's cap; others unaffected | **V-3** on staging |
| L-8 | Restart under load (planned, with the banner) | Banner shown in advance; restart ends sessions cleanly; people sign in again | M (runbook §9) |
| L-9 | Memory back after heavy closes, many people (sixteenth to eighteenth patches, MinGap) | Each worker gives its memory back within about 10 s of a heavy close; the relief runs in that person's worker only, so the gateway and other people aren't paused; at most once per 30 s per worker | E (Web chat, 9-10 Nov: 4 people, a 5000x5000-pixel PDF, 3.5 GB → 0.87 GB in 10 s, at most 0.7 core busy, gateway 0.1 core); V (staging: 10 people on the 16 GB VM) |

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

### 5a. Manual browser runs (the Web Test chat, on real devices)

Every run uses the same sequence, against the local gateway with real Sangam (or staging once it exists). Note the browser and OS versions, and put a ✓, or a description of what went wrong, against each step.

| # | Step | Expect |
|---|---|---|
| 1 | Open the portal | 12a sign-in page; "Terms of use" opens `/terms` in a new tab and the switch reaches Privacy, Cookies, Third-party notices |
| 2 | Continue with Sangam, sign in | Back in the Reader; name and Sangam ID in the account menu |
| 3 | Drag a PDF from the desktop onto Home, then onto the Reader | "Not allowed" cursor; nothing opens; the browser stays on Chuvadi |
| 4 | Upload (left bar) one PDF, one DOCX, one XLSX | Each opens; a file renamed to the wrong extension is refused |
| 5 | Page, zoom, find a word | As on the desktop |
| 6 | Add a highlight and a note; Save as new PDF | A download; it opens in the OS viewer with the marks |
| 7 | Print the current page, then pages 2–3 | Chrome, Edge, Firefox: the browser's print dialog shows only those pages. Safari: "Open the PDF to print" → PDF tab → print from there |
| 8 | Print a no-print PDF | The print card refuses |
| 9 | Merge two PDFs | `merged.pdf` downloads |
| 10 | Copy text; copy a page image | The clipboard has them (image: the browser may ask permission) |
| 11 | Open a second tab of the portal; sign out from the first | Both tabs end on the signed-out page |
| 12 | Sign in, leave the tab untouched (with a short idle limit on the test server) | Warning, "I'm still here" works; later the session ends on the signed-out page |

Per browser, on top of the sequence:

| Run | Device | Also check |
|---|---|---|
| M-1 Edge | Windows 11, current Edge | Edge's own PDF viewer prints the right pages; Ctrl labels; the downloads bar |
| M-2 Safari on Mac | macOS 15 or later, current Safari | ⌘ labels and shortcuts (⌘P, ⌘F); the print link opens a PDF tab and ⌘P prints it; image copy asks permission; the 12a page in light and dark |
| M-3 Safari on iPhone and iPad | iOS/iPadOS 18 or later | Upload from Files and from Photos; phone layout on iPhone, tablet layout on iPad (both orientations); print via the PDF tab's share sheet; downloads land in Files; touch selection and marks; no page zoom on double-tap |
| M-4 Chrome on Android | Android 14 or later, current Chrome | Upload from the device and from Drive; phone layout; print via the PDF tab; downloads; the back button doesn't lose the session |

### 5b. Staging-VM runs (before go-live; the VM sized as production, runbook §2)

| ID | Run | How | Pass when |
|---|---|---|---|
| V-1 | **Two-hour soak** | From a separate machine with the Development sign-in **on the staging VM only**: `load.py` with 40 people, repeated back to back for 2 hours (`for i in $(seq 1 30); do python3 load.py … 40; done`). Every 5 min, sample: gateway RSS, number of workers, total worker RSS, `du -s /srv/chuvadi/data`, open file handles of the gateway (`ls /proc/<pid>/fd | wc -l`) | No failures; gateway RSS and handles flat (±10 %) after the first round; workers return to 0 and `data/workers` empties within ~6 min of each round; no errors in `journalctl` |
| V-2 | **Real Let's Encrypt** | Runbook §8.3: staging directory first, then production. Then force a renewal by setting `Portal__Tls__Acme__RenewBeforeDays=89` and restarting; watch `journalctl` | Staging certificate issued and served; production certificate trusted by the browsers in §5a; the forced renewal installs a new certificate with no restart and no dropped connections; a failed renewal (DNS pointed away briefly) keeps the old certificate and retries |
| V-3 | **Large documents** | Upload, read, mark, save, print and merge: a 300-page scanned PDF (~150 MB), a PDF at the 200 MB upload limit, one just over it, a 500-page text PDF, a 50 MB DOCX, an XLSX with 100,000 rows. Run two people at once doing this, and one person doing it while 20 others run `load.py` | Within-limit files work; over-limit refused with the size message; no worker exceeds its `MemoryLimitMB` without a clean refusal; the other people's timings stay within 2× of the V-1 medians |
| V-4 | Hostile documents (S-18) | A fuzz corpus of malformed PDFs, zip bombs as DOCX/XLSX, deeply nested objects | Only that person's worker is affected (refusal, or a worker restart); the gateway and others continue |
| V-5 | Logs (S-16) | After V-1 to V-4, read `journalctl -u chuvadi-portal` | No document text, tokens, passwords, cookies or Sangam ids in the logs |
| V-6 | Restart with the banner (L-8, F-20) | Runbook §9 during a V-1 round | Banner in every tab ahead of time; the restart ends sessions cleanly; people sign in again |
| V-7 | Drafts before go-live | `curl -s https://<domain>/terms /privacy` | **No "DRAFT" line**: the legal texts are the counsel-reviewed versions (the drafts say not to publish) |

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

**7 Nov, morning (on `platform/foundation` @ `e5802e6`, fourth combined patch):**
- Shared solution `-warnaserror`, 0 warnings; tests Reader 171, Hosting 48, Mobile UI 15, Web UI 31.
- Web 140/140.
- `flows.py` including the D-89 drop check: Chrome, Firefox, WebKit and Chromium 7/7. The control check confirms a page without the portal script doesn't cancel the drop.
- Legal pages in Chrome: `/terms`, `/privacy`, cookies and notices; the switch moves between the four addresses; DRAFT shown; no page errors.
- Real-Sangam e2e through the gateway: pass (back-channel 1.3 s).

**7 Nov, mid-morning (on `platform/foundation` @ `4819d66`, IDroppedFiles seam):**
- Shared solution `-warnaserror`, 0 warnings; tests Reader 171, Hosting 48, Mobile UI 15, Web UI 31.
- Web 142/142 (new: `DroppedFilesTests`).
- `flows.py` with the D-89 A drop checks, gateway mode: Chrome, Firefox, WebKit and Chromium 9/9.

**8 Nov, evening (on `platform/foundation` @ `63f37b1`; fixes for WT-01, 07, 08, 11, 12, 13 and O-1, O-2):**
- Shared solution `-warnaserror`, 0 warnings, and its tests; Web tests (new: relayed CSP, circuit origin, bidi names, Sangam timeouts and probe).
- `flows.py` in gateway mode: Chrome, Firefox, WebKit and Chromium 9/9, no 403s in the server log.
- `load.py` (3 people, own browser each): 3/3, times in ms from draws.
- `check-package.sh` on a fresh publish: pass (and fails on the old package).

**9 Nov, early (on `platform/foundation` @ `f1e4126`; WT-14, WT-15):**
- Web 156/156 (new: http Sangam refused in Production, https starts).
- `sangam_signin.py` in WebKit against a local Sangam: 5 runs, 13/13 each (WT-14 fix: waits for the signed-out page, not network idle).

**9 Nov, morning (on `platform/foundation` @ `1016987`; WT-16, D-137):**
- Shared solution `-warnaserror`, 0 warnings, and its tests; Web tests (new: `ZipSaveTests`).
- `flows.py` 10/10 in Chrome, Firefox, WebKit and Chromium: split to folder gives one `sample.zip` of all 33 pages.
- `office_limits.py` 6/6 in all four engines (Firefox 4 runs clean).
- `check-package.sh`: pass.

**10 Nov, morning (on `platform/foundation` @ `f88f9ef` plus Web portal UI `ce805d1`):**
- Shared solution 0 warnings and its tests (Reader 233, Hosting 77, Mobile UI 16, Web UI 41); Web 166/166.
- `flows.py` 10/10 in Chrome, Firefox, WebKit and Chromium; `office_limits.py` 6/6 in Chrome and WebKit.
- L-9 heavy closes: 1 person 1021 → 224 MB; 4 people 3572 → 867 MB within 10 s.

**10 Nov, mid-morning (Foundation `c7712d0` merged; D-158 endpoint):**
- Shared solution 0 warnings and its tests (Reader 247, Hosting 81, Mobile UI 16, Web UI 41); Web 171/171.
- `page_images.py` 6/6 and `flows.py` 10/10 in Chrome, Firefox, WebKit and Chromium, gateway mode.

**10 Nov, evening (WT-20, WT-21):**
- Web 172/172; shared solution 0 warnings and its tests.
- `page_images.py` 7/7 and `flows.py` 10/10 in Chrome, Firefox, WebKit and Chromium; `expiry.py` 10/10 in Chrome, Firefox and WebKit (short limits).

**11 Nov, early (Foundation `742a5da` merged; D-174, RemoveOwner):**
- Shared solution 0 warnings and its tests (Reader 305 with 3 skipped by the Foundation, Hosting 91, Mobile UI 16, Web UI 41); Web 178/178; package check.
- `reload.py` 11/11 in Chrome, Firefox, WebKit and Chromium; `expiry.py` 12/12 in Chrome, Firefox and WebKit; `comeback.py` 5/5 in Chrome and WebKit; `sangam_signin.py` 18/18 in Chrome, Firefox and WebKit.
- `flows.py` 10/10, `page_images.py` 7/7 and `office_limits.py` 6/6 in all four engines; `load.py` 3/3.

## 8. Known gaps
- **Browser tests and the Development sign-in:** name the person with the `chvd-dev-user` cookie, not only the `X-Dev-User` header. A closing page's "disconnect" call is a beacon: it carries cookies (as the real sign-in does) but not a test tool's extra headers, so with the header alone it reaches the default person's worker and the old connection lingers for 3 minutes. That made WT-22's leak look larger in Development than it is with the real cookie.
- The legal texts are drafts and say not to publish until counsel has reviewed them: V-7 blocks go-live until the DRAFT lines are gone.
- F-23 (a Privacy link on 12a) waits for a decision. A real drag from the desktop (F-21, F-22) can only be run by hand: browser automation can't carry an OS file drag.
- Manual runs M-1 to M-4 (§5a) need real devices; staging runs V-1 to V-7 (§5b) need the VM, which comes last by Arun's decision. G-12 needs a Sangam test person in two organisations.
