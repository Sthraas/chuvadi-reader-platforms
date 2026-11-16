# Web portal — bugs found by the Web Test chat

Tested: `platform/web` @ **31b063e** (Foundation 4819d66 underneath), 8 Nov 2026. Every bug is to be fixed, however small (rule 7); each fix comes back here for re-verification. "Existing file" means a chuvadi-reader file: the fix goes to Arun as a listed change through the coordinator (rules 4 and 5), not straight into the code.

Severity: **High** = wrong result, security weakness, or a screen that doesn't work; **Medium** = untrue or missing text the decisions require; **Low** = polish, hardening, tooling.

| # | Severity | Area | Title | Owner | Status |
|---|---|---|---|---|---|
| WT-01 | High | Security | In gateway mode the Reader page loses its Content-Security-Policy (only `frame-ancestors 'self'` reaches the browser) | Web | **Verified fixed** in 1b32ad8 and **d180f2e** (9 Nov 03:30) — full policy on the gateway Reader page |
| WT-02 | High | Function | Print "Current" prints the **next** page; Measure card shows the next page number | Existing file → Arun | **Verified fixed** in 1b32ad8 and **d180f2e** — Current prints p1/p5 correctly (Chromium, Firefox); Measure card "page 5" on p5 (3 engines) |
| WT-03 | High | Design | Phone width shows squeezed desktop rails, not the phone shell; per-page strip and Arrange shelf clipped | Web (rebase) + Web portal UI (re-check) | **Verified fixed** (last on **d183ea8**, 10 Nov) — phone shell, 3 engines |
| WT-04 | Medium | Wording | Status bar still says "encrypted at rest" (D-98) | Web portal UI → Foundation patch → Web | **Verified fixed** (last on **d183ea8**) — "kept in memory only", 3 engines |
| WT-05 | Medium | Wording | 12a pitch still says "encrypted at rest" | Coordinator decision, then Web portal UI | **Verified fixed** in 1b32ad8 (D-103); unchanged since |
| WT-06 | Medium | Design | Account menu has no "Terms of use · Privacy" footer (D-97) | Web portal UI → Foundation patch → Web | **Verified fixed** (last on **d183ea8**) — Terms · Privacy footer, 3 engines |
| WT-07 | Low | Security | The circuit (`/_blazor`) accepts a foreign `Origin` | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — foreign Origin → 403, own → 200 |
| WT-08 | Low | Security | File names keep Unicode bidi controls (U+202E), so a name can display reversed | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — U+202E removed, 3 engines |
| WT-09 | Low | UX | The no-print reason is only a hover tooltip on a disabled button (invisible on touch) | Existing file → Arun | **Verified fixed** in 1b32ad8 and **d180f2e** — reason in the card body, 3 engines |
| WT-10 | Low | UX | A file that can't be opened shows raw parser text, and a "Fetch…" button where the portal says "Upload" | Existing file → Arun (text) / Web portal UI (label) | **Verified fixed** in **c38bd80** — no "Fetch" on the failed-open screen or anywhere in Arrange; "This PDF is damaged" sentence; 3 engines |
| WT-11 | Low | Packaging | Publish output carries `web.config` (IIS), `appsettings.Development.json`, `.pdb` and `.xml` files | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — `check-package.sh` PASS, no third-party assemblies |
| WT-12 | Low | Docs/CI | The plan's build command fails from a clean clone; Web is built without `-warnaserror` in CI and isn't in Platforms.slnx | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — documented restore works from an empty cache; 0 warnings with `-warnaserror` |
| WT-13 | Low | Test tooling | `load.py`: no output folder created; "paging" is mostly fixed sleeps; one browser for everyone | Web | **Verified fixed** in **d180f2e** — `load.py` creates its output folder, reports ms, no errors (5 people) |
| WT-14 | Low | Test tooling | `sangam_signin.py` sign-out step races in WebKit (1 in 5 runs) | Web | **Verified fixed** in d180f2e and **c38bd80** — WebKit 13/13 × 8 runs in total; Chrome, Firefox 13/13 |
| WT-15 | Medium | Security | Production starts with an `http://` Sangam address | Web | **Verified fixed** in d180f2e and **c38bd80** — Production + `http://` Sangam refuses to start; https starts |
| WT-16 | Low | UX | "Split to folder" on the portal arrives as one download per page | Web (D-129: one .zip via Chuvadi.Zip) | **Verified fixed** in **c38bd80** — Split to folder → one `text-13.zip` (Chuvadi.Zip 1.0.0), zip intact, 13 entries, each the right page; Chromium, Firefox, WebKit; a one-file save stays a plain PDF |
| WT-17 | High | Fidelity | Excel grid ignores each cell's number format (shows 0.125 for 12.50%, 1234.5 for ₹1,234.50, 7 for 007, ISO dates) — Sheets 2.0.2's `NumberFormatter` is not called | Existing file (Core `XlsxViewService`) → Foundation combined patch → Arun | **Verified fixed** in **04cdd21** (Foundation patch 24, D-161/D-162) — 12.50%, 1,234.50, ₹1,234.50, 09-11-2026, 007, 1.00E-07 shown as Excel shows them; the held value is the cell's hover text; 3 engines. Follow-ups in `PHASE-1-SIGNOFF.md` §2 |
| WT-18 | Low | Wording | An Excel file over the per-part size limit (or a zip bomb) is called "damaged or isn't an Excel workbook" instead of "too large" | Existing file (Core `XlsxViewService` message mapping) → Foundation patch | **Verified fixed** on **3f80768** (patch 29): `ratio-600.xlsx` and `zip-bomb.xlsx` → "This Excel workbook is too large to open: it goes beyond what Chuvadi allows. It may be damaged." in 0.3 s |
| WT-19 | Medium | Capacity | Closing an Excel file, or cancelling its open, gives no memory back: the worker keeps 0.5–1.3 GB (memory relief covers PDFs only) | Existing file (Core) → Foundation patch | **Verified fixed** on **eab426b** (16 Nov, Chromium): 1,048,576-row workbook closed — 1,054 → 155 MB within 2 s; cancelled open (`cancel-4x1m.xlsx`, peak 1,556 MB) — 147 MB within 2 s; idle 119 MB |
| WT-20 | Medium | Security | Signed-out / expired requests for a page image get **302 to `/signin?returnUrl=/_chvd/pages/<token>.png`**, not 404 — the token is copied into a URL | Web | **Verified fixed** in 6be3c17 and **04cdd21** — no cookie, bogus cookie, expired session, signed out (back-channel): all **404**, no `Location`; other pages still redirect to sign-in |
| WT-21 | Low | Privacy / memory | When a session ends (expiry or sign-out), the person's page images stay in their worker's memory until the worker stops (still held 3 min later) | Web (+ shared Core if the document itself stays open) | **Verified fixed** on **21ac80d** — expiry and Sign out free the session's documents whichever connection opened them (after two reloads: images 404, 741 → 248 MB; real Sangam sign-out after a reload: token 404, 374 → 145 MB) |
| WT-22 | Medium | Function / memory | Reloading the page (F5, or opening the address again) drops every open tab, and the documents it held stay open in the person's worker — unreachable, not closed at session end, still held 4+ minutes later | Web (tabs per connection) — design question for the coordinator | **Verified fixed** on **21ac80d** (D-174) — a reload brings the tabs back, the document is drawn again, old image addresses are freed, closed tabs stay closed, another person sees none; 3 engines. Unsaved marks are not kept (stated) → D-181 prompt, WT-23 |
| M-27 | High (S1) | Shared Ui | A mark drawn with the mouse is placed and saved at pointer × zoom on **WebKit 18.4 and earlier** (Safari 17/18, and the Mac app on those systems); correct on Chromium, Firefox, WebKit 26 | Foundation (PR 18, Reader main 04d97d7) → Web patch 27 | **Verified fixed** on **eab426b** (patch 27) — Chromium 153, Firefox 155, WebKit 26.6 and **WebKit 17.4**; Rectangle, Text box, move, resize, Redact box at a zoom |
| WT-23 | Low | Function | The "Leave site?" question (D-181) only knows the document that is showing: unsaved marks on another tab are lost on reload with no question | Web (stated limit in build log §36) — coordinator to accept or fix | **Verified fixed** on **3f80768** (patch 29) — Chromium, Firefox, WebKit: marks stay with their tab; reload while another tab holds marks raises the Leave-site question; closing a marked tab asks (Save / Save as… / Discard / Cancel) |
| WT-24 | High | Security / capacity | The session-expiry pass can hang for good (a session ending as its worker stops); after that no session on the portal expires and no worker is freed until a restart | Web | **Verified fixed** on **21665a3** (patch 30): the race met 22 times in 80 session ends and 20 fresh-portal runs — every session ended; worker killed or frozen mid-call — the others still end, and it is logged |
| WT-25 | Low | Privacy / memory | A browser that leaves without a clean close: worker and files stay 60–80 s past the session's end; `comeback.py` fails in Firefox for that reason | Web | **Verified fixed** on **21665a3**: browser closed or killed with the tab open — worker and files gone at 42 s (limit 40 s), Chromium and Firefox |

Library items (Arun's libraries; not app bugs, recorded so they aren't lost): **LIB-1**, **LIB-2** at the end — on the coordinator's list for Arun's library coordinator (20:40).

**Coordinator decisions 8 Nov 20:40 (D-117 to D-120):** O-1 (b) 10 s timeout for discovery and the token call; O-2 (b) probe Sangam before redirecting (2 s, cached 30 s); WT-05 already D-103; Q-3 (c) keep Storage map and shelves with "this session" wording if the Web portal UI confirms no layout change, else (b); order: Web rebases first, then WT-01, WT-07, WT-08, WT-11 to WT-13; WT-02, WT-09, WT-10 into Foundation's combined patch → PR #11. New checks to run when they land: O-1 (G-9 ≤ 10 s), O-2 (G-1 warm shows our message), Q-3 wording.

---

## WT-01 — Gateway mode drops the portal's CSP on the Reader page (High, security)
**Steps**
1. Start the portal in gateway mode (production layout): `Portal__Mode=Gateway`.
2. `curl -sD - -o /dev/null -H 'X-Dev-User: a' http://127.0.0.1:5090/` (in production: the signed-in Reader page).

**Expected:** the portal's policy, as on every gateway page: `default-src 'self'; script-src 'self'; … object-src 'none'; base-uri 'self'; form-action 'self'`.

**Actual:** `Content-Security-Policy: frame-ancestors 'self'` only. Relayed static files keep the full policy; gateway pages (`/terms`, `/signin`, 404) keep it. In single mode the same page carries **both** headers (the browser enforces both, so single mode is safe).

**Cause:** `GatewayRelay.RelayAsync` copies the worker's response headers with `http.Response.Headers[name] = values`, which replaces the policy the gateway already set with the one Blazor adds to interactive pages.

**Effect:** the page that shows people's documents runs without the script/object/base restrictions — the main defence if anything ever injects markup.

**Suggested fix (Web's choice):** append `Content-Security-Policy` instead of replacing it in the relay (or have the worker send the full policy), and add a gateway-mode test to `Every_response_carries_the_security_headers` for a relayed Razor page.

**Evidence:** `RESULTS.md` X-I2 (header dumps, gateway vs single).

## WT-02 — "Current page" prints the next page (High, function; existing code, Windows too)
**Steps**
1. Open `text-13.pdf` (each page headed "Page N of 13"). Page box shows 1, status bar "page 1 of 13".
2. Ctrl P → Current → Print.
3. Fetch the served print PDF; `pdftotext`.

**Expected:** "Page 1 of 13".

**Actual:** "Page 2 of 13" (one page, vector). On the last page it happens to be right, because the index is clamped.

**Cause (source of record, `arunshivab/chuvadi-reader` main c7b9e44):** `Reader.razor` passes `CurPage` (1-based: `pi + 1 == CurPage`) to `PrintCard CurrentPage`; `PrintCard` puts it into `PrintRequest.CurrentPage`, documented "Zero-based page the reader shows"; `PageRangeParser` uses it as an index. The same 1-based value goes to `MeasureCard`, which shows `page {CurrentPage + 1}` — so its label is one too high as well. LayersCard, SignaturesCard and PasswordCard receive the same value (no visible use found).

**Effect:** wrong page printed on every platform, Windows included.

**Fix route:** existing files → listed change for Arun (rules 4, 5): pass `CurPage - 1` where a zero-based page is expected (or make the cards' contract 1-based). Risk to Windows: the fix *changes* Windows output (correctly). A test: "current" on page 1 of 13 → index 0.

**Evidence:** `RESULTS.md` X-F1; `screenshots/print-card-page1.png`.

## WT-03 — Phone width has no phone shell (High, design)
**Steps:** open the portal at 390×844 (touch) in Chromium or WebKit.

**Expected (D-32, D-40, Portal & Android):** phone layout from the Mobile UI chat — bottom bar, tool strip in Mark/Protect, View sheet.

**Actual:** `<html data-shell="phone" data-form-factor="phone">` is set correctly, but the desktop rails render squeezed: Read/Tools/View rails take a third of the width; the per-page strip is clipped ("otate page"); in Arrange the Bench shelf and panels overlap the page; the brand is cut ("C⁠ச⁠huvadi" with a "⋮" over it).

**Cause:** `platform/web` sits on Foundation **4819d66**; the PhoneShell slot and Mobile UI hooks H-5…H-12 arrived in Foundation's sixth combined patch **584bbf2** (D-94).

**Fix:** Web rebases on Foundation ≥ 584bbf2 (with the Web portal UI's latest files); then I re-run the phone and tablet screenshots in three engines.

**Evidence:** `screenshots/chromium-phone-*.png`, `webkit-phone-*.png`.

## WT-04 — Status bar still "encrypted at rest" (Medium, wording, D-98)
**Actual (all engines, all widths):** "processed on the server · encrypted at rest · only you can see it". **Expected (D-98):** "processed on the server · kept in memory only · only you can see it". Fix exists on `platform/web-ui` 5bec046 (H7 patch) but isn't in the Web build. Re-verify after the rebase.

## WT-05 — 12a pitch still "encrypted at rest" (Medium, wording — question)
12a: "On the portal, files are processed on our server, encrypted at rest, and visible only to you." D-31 kept this text; D-98 later found that memory itself isn't encrypted and changed the status bar and the legal drafts — but not this sentence (also still in `platform/web-ui` `PortalSignIn.razor`). Options for the coordinator:
- (a) Change to "…processed on our server, kept in memory only, and visible only to you." Pros: true, matches D-98 and the Terms; DPDP-safer. Cons: differs from the handout text (as D-98 already does).
- (b) Keep. Pros: handout text. Cons: a claim on the public sign-in page that D-98 judged untrue.
**Recommendation: (a).**

## WT-06 — Account menu without Terms · Privacy footer (Medium, D-97)
Desktop account menu shows the name, "Get the desktop app", "Sign out" — no footer line. D-97 (a) decided a small "Terms of use · Privacy" footer. Fix exists on `platform/web-ui` 5bec046; not in the Web build. ("Account settings" is hidden because `AccountSettingsUrl` is empty — correct by configuration.)

## WT-07 — Circuit accepts a foreign Origin (Low, hardening)
`POST /_blazor/negotiate?negotiateVersion=1` with `Origin: https://evil.example` (signed in) → 200 with a connection token; the WebSocket relay passes `Origin` on and nothing checks it. The `SameSite=Lax` cookie stops most cross-site use, but a sibling sub-domain counts as same-site. The upload and activity endpoints already check Origin (`SameOrigin`); the circuit should too. **Fix:** in the gateway, refuse `/_blazor` requests (negotiate and upgrade) whose `Origin` isn't `PublicOrigin`.

## WT-08 — Bidi controls kept in file names (Low)
Uploading `rtl‮fdp.exe.pdf` keeps U+202E in the tab title, the working copy name and later download names, so the name displays reversed ("…exe…"). S-7 says control characters are cleaned; U+202A–U+202E, U+2066–U+2069 (format characters) aren't. **Fix:** drop Unicode `Cf` bidi controls in the name cleaner; add the case to `UploadTests`.

## WT-09 — No-print reason only in a tooltip (Low, existing file)
For a no-print PDF the Print button is disabled, with "This file's permissions don't allow printing." only as its `title`. On touch (phones, tablets) there is no hover, so the person sees a dead button. Arun dislikes hover-only information. **Fix (listed change):** show the sentence in the card body when printing is refused.

## WT-10 — Raw parser text on the "couldn't open" screen; "Fetch…" label (Low)
Examples: "Could not open this document. Invalid integer '4294965240' at offset 3927: must be a valid 32-bit signed integer."; "Could not locate 'startxref' keyword in the last 1024 bytes of the file." The button under it says "Fetch…" and opens the chooser, while the portal calls that action "Upload". **Fix:** a plain sentence ("This file is damaged or isn't a PDF Chuvadi can read") with the detail behind a "Details" toggle (existing file → Arun); label "Upload…" when `Kind == Web` (Web portal UI wording).

## WT-11 — Publish output carries files the Linux server doesn't need (Low)
`web.config` (IIS), `appsettings.Development.json` (development settings in the production package), `*.pdb`, `*.xml` (API docs). None are harmful today (`Development` is refused outside Development without Sangam), but the package should hold only what runs. **Fix:** `IsTransformWebConfigDisabled`/exclude `web.config`; exclude `appsettings.Development.json` from publish; `DebugType=none` (or ship symbols separately) and no doc XML for Release publish.

## WT-12 — Build command from a clean clone; CI strictness (Low)
`docs/web/TEST-PLAN.md` §0: `dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror` fails from a clean clone with NU1301 (root `nuget.config` points at the git-ignored `./localpackages`); it works after `dotnet restore … --configfile ci/nuget.config`. `web.yml` builds Web without `-warnaserror`, and Web/Web.Tests aren't in `ChuvadiReader.Platforms.slnx` (the plan's "whole shared solution" doesn't include them). Today all three build with 0 warnings. **Fix:** document the restore step; add `-warnaserror` in `web.yml`; add Web + Web.Tests to Platforms.slnx (new-file edit by the programme's rules) or say why not.

## WT-13 — load.py measurement issues (Low, test tooling)
`load.py` fails at the end if `<out>` doesn't exist; its "paging" step includes 6 × 250 ms fixed waits (1.5 s of the reported ~2 s); all people share one browser process, so client CPU is counted as server time. `tests/web-test/perf.py` measures in ms from browser timings and draws (`.rpage svg` with content) and can replace it.

---

## WT-10 addendum (9 Nov) — "Fetch" wording in Arrange
In Arrange (Bench) on the portal: "Fetch a PDF to start.", "Fetch a file", "Fetch file" (twice), "Fetch image", and the title "Fetch another PDF onto the shelf". The portal's word is "Upload". Same route as WT-10 (shared Ui → Foundation patch, `Kind == Web` wording). Found tonight; not in the 8 Nov report, so not a regression.

## WT-14 — `sangam_signin.py` sign-out race in WebKit (Low, test tooling)
After "Sign out", the script waits for `networkidle`, which WebKit sometimes reaches while still on Sangam's `/connect/endsession` before the redirect back; it then reports "sign-out ends on the portal's signed-out page" as failed. 1 failure in 5 WebKit runs, 0 in Chrome/Firefox; the portal behaves correctly. **Fix:** `page.wait_for_url(portal + "/signed-out*", timeout=30000)` instead of `networkidle`.

## WT-15 — Production accepts an `http://` Sangam address (Medium, security)
**Steps:** `ASPNETCORE_ENVIRONMENT=Production`, `Sangam__Authority=http://localhost:5100/` (plus TLS, PublicOrigin, tmpfs). **Expected:** refuse to start outside Development/Testing unless the Sangam address is https (as the portal already refuses Development sign-in and a disk data root). **Actual:** starts; discovery, token call (with the client secret) and back-channel would go over plain http if misconfigured. No https check exists for `Sangam:Authority` (`Auth/SangamMetadata.cs`). **Fix:** startup check — https required outside Development/Testing.

## WT-16 — Split to folder = one download per page (Low, UX — option)
On the portal "Split to folder" of a 13-page PDF hands the browser 13 separate downloads in 0.6 s (all 13 arrive in headless runs). Real Chrome asks "This site is trying to download multiple files" and Safari may block them. Option O-3 in `OPTIONS-FOR-COORDINATOR.md`.

## WT-17 — Excel grid shows stored values, not the cell's number format (High, fidelity; existing code, Windows too)
**Build:** `platform/web` c38bd80 (Sheets 2.0.2). **File:** `tests/web-test/make_fidelity.py` → `fid.xlsx` (openpyxl) and the same saved by LibreOffice — both behave the same.

| Cell value | Number format in the file | Excel / LibreOffice show | Chuvadi grid shows |
|---|---|---|---|
| 0.125 | `0.00%` | 12.50% | 0.125 |
| 1234.5 | `#,##0.00` | 1,234.50 | 1234.5 |
| 1234.5 | `"₹"#,##0.00` | ₹1,234.50 | 1234.5 |
| 2026-11-09 | `dd-mm-yyyy` | 09-11-2026 | 2026-11-09 |
| 7 | `000` | 007 | 7 |
| 1E-07 | `0.00E+00` | 1.00E-07 | 1E-07 |

Text cells, General numbers and cached formula results are exact (below). **Cause:** `ChuvadiReader.Core/Documents/XlsxViewService.cs` builds each cell's text with its own `FormatValue` (ISO dates, `CurrentCulture` numbers — so it also depends on the server's culture) and never reads the cell's number format; Sheets 2.0.2 ships `NumberFormatter.GetDisplayText` (SHEETS-FMT) for exactly this, unused (`grep` finds no caller). The layout requirements put "displayed cell text via the NumberFormatter" first for xlsx: a grid showing 0.125 for 12.50% can be misread. Underlying data is not changed — this is display. **Fix route:** existing Core file → listed change in Foundation's combined patch → Arun (PR #11); changes Windows output (correctly). Evidence: `screenshots/v3-xlsx-grid-formats.png`.

## WT-18 — Excel part-size refusal says "damaged" (Low, wording)
**Build:** d183ea8 (Sheets 2.0.4). `ratio-600.xlsx` (a 300 MB sheet part) and `zip-bomb.xlsx` (2 GB part) → "This file is damaged or isn't an Excel workbook Chuvadi can read." The other limits (rows, zip entries) → "This Excel workbook is too large to open: it goes beyond what Chuvadi allows. It may be damaged." On 002bf02 (Sheets 2.0.2) the same two files showed the raw library text ("Decompressed size limit of 268435456 bytes exceeded…"); on c38bd80 the zip bomb said "…its contents unpack to more than 2,048 MB". **Expected:** the "too large to open" sentence for every size limit — the person should learn the file is too big, not that it is broken. **Fix:** map the part-size limit (`MaxPartBytes` / `MaxTotalUncompressedBytes` / `MaxCompressionRatio`) to the "too large" message in the shared Core; a test per limit.

## WT-19 — Excel close / cancelled open keeps the memory (Medium, capacity)
**Build:** d183ea8 (Foundation f88f9ef, "memory given back after a heavy close"). Per-person worker RSS (`tests/web-test/memory_relief.py`, Firefox, tab close confirmed):

| Case | Idle | While open | 2–30 s after close |
|---|---|---|---|
| PDF with a 5000×5000 image (the Web chat's case) | 119 MB | 1,468 MB | **359 MB** ✅ |
| rows-1048576.xlsx | 120 MB | 609 MB | 611 MB ✗ |
| big-100k.xlsx | 119 MB | 366 MB | 368–370 MB ✗ |
| cancel-4x1m.xlsx — **Stop opening** | 121 MB | 1,304 MB | 1,304–1,307 MB ✗ (cap is 1,536 MB) |

**Cause:** `MemoryRelief.Request()` is called only from `ChuvadiPdfReader`'s close; Excel/Word closes and cancelled opens never ask. **Effect:** not a failure for the person — the next large open reuses the held memory (opened 1,048,576 rows after a cancel: peak 1,111 MB, same worker) — but the server can't use that memory for anyone else until the worker happens to collect or stops; with 40 people on 16 GB (runbook §2) a few cancelled big sheets eat the headroom. **Fix:** request relief on Excel/Word close and after a cancelled open (shared Core), with the same 30 s MinGap; re-measure here.

## WT-20 — page-image endpoint redirects signed-out requests, with the token in the URL (Medium, security)
**Build:** `platform/web` 78f7628 (D-158). **Steps** (Sangam configured, as in production): `curl -sD - https://<portal>/_chvd/pages/<any 32-hex>.png` with no cookie, a bogus cookie, or the cookie of an expired / signed-out session.
**Expected (D-158, S-19):** 404 — the same answer as for an unknown, freed or someone else's address.
**Actual:** `302 Found`, `Location: /signin?returnUrl=%2F_chvd%2Fpages%2F<token>.png`. Real-Sangam runs: expired session with its old cookie → 302; after Sign out (back-channel) → 302 with the token in `returnUrl`. In Development sign-in (no Sangam) the same request is 404, so dev-mode tests miss it.
**Effect:** the contract "every miss looks the same" breaks (a signed-out probe learns the route exists and needs sign-in), and the token lands in a redirect URL — browser history, any proxy or access log in front of the portal, and the `returnUrl` the sign-in page carries. The token alone isn't usable (owner = person + sign-in id), so this is hygiene, not a hole.
**Cause:** the route uses `.RequireAuthorization()`, so the cookie scheme's challenge (redirect to sign-in) runs before the handler's own 404.
**Fix:** for this route, answer 404 when the request isn't signed in (no challenge) — e.g. drop `RequireAuthorization()` and keep the handler's owner check (it already returns 404 without an owner), or a policy whose challenge is 404; add a Sangam-mode test (no cookie / expired cookie → 404, no `Location`).

## WT-21 — page images (and possibly the document) outlive the session in memory (Low; please confirm)
**Steps** (Development, `IdleTimeout` 40 s): open `large-6.pdf` (drawn as images), let the session expire, close the browser; one request 180 s later with the same person → **200**, the image is still served; the person's worker was still running at 180 s. In production that request can't succeed (the old cookie is dead → WT-20's 302; a new sign-in has a new sign-in id → **404**, verified with real Sangam), so it is not reachable — but the pixels stay in the worker's memory until it stops.
**Expected:** a session's end frees what it held, as closing the tab does (verified: every token 404 right after a tab close). **Ask:** confirm whether the session's documents are also still open in the worker after expiry/sign-out (files on disk are gone — S-10 ✅); if so, close them (and their images) at session end.

## WT-22 — a page reload loses the open tabs and orphans their documents (Medium)
**Build:** `platform/web` 04cdd21. **Steps:** open a PDF → press F5 (or load the portal address again in the same tab).
**Actual:** (1) the Reader comes back empty — the tab is gone and the person must upload the file again (any unsaved marks with it); (2) the first document is still open inside the person's worker: its page images still answer the owner (200), the memory is not given back, and **session end does not close it** — WT-21's fix closes only the current connection's tabs. Measured (Development, 40 s idle, `tests/web-test/session_end_free.py`): without a reload, expiry frees at once in 6 of 6 runs (e.g. 396 → 245 MB, tokens 404); with a reload between two opens, 0 of 5 runs freed (590 → 593 MB, tokens still 200, still held 260 s after the session ended).
**Expected:** either the tabs survive a reload (they are the person's session, and the working copies are still there), or the reload closes what it drops; and session end closes everything the person had open, whichever connection opened it.
**Options for the coordinator:**
- (a) Tabs belong to the person's session, not the connection: a reload shows the same tabs again. Pros: nothing lost on F5 or a dropped connection (phones do this often); one place to close at session end. Cons: the larger change (tab state moves out of the per-connection scope); must stay per-person.
- (b) Keep tabs per connection, but close a connection's documents as soon as it is replaced/ended, and at session end close every document the worker holds. Pros: small; fixes the leak. Cons: F5 still loses the open file and unsaved marks.
- **Recommendation: (a)** — it is what a person expects of a web page, and it removes the leak by construction; if it is too big for Phase 1, (b) now and (a) listed for Phase 3.

## M-27 on Web — marks land at pointer × zoom on WebKit 18.4 and earlier (found by Mac Test; measured here 15–16 Nov)
**Build:** `platform/web` 21ac80d (patch 26). Tools: `tests/web-test/mark_position.py` (DOM + saved PDF), `mark_position_pixels.py` (screenshots + saved PDF, no DOM geometry).
- **Chromium 153, Firefox 155, WebKit 26.6:** Rectangle and Text box by mouse at Fit (70 %; 93–94 % on the rotated page), 54 %, 100 %, 150 %, unrotated and /Rotate 90 — drawn shape within **0.9 px** of the pointer, saved position within **0.4 % of the page**, size within 0.5 %. No zoom dependence. (46 of 48 cases run; Firefox's two 150 %-rotated cases were cut by the run's time limit.)
- **WebKit 17.4** (Playwright 1.44's WebKit, same portal): a drag from (20 %, 20 %) to (55 %, 50 %) of the page is saved at — Fit 70 % unrotated: **(0 %, 11.6 %)**; 54 % unrotated: **(0 %, 5.9 %)**; 54 % rotated: **(0 %, 3.9 %)**; Fit 93 % rotated: **(16.9 %, 17.5 %)**. Text boxes the same. Evidence: `screenshots/m27-webkit17-54pct-*.png`.
- **Cause:** the page is zoomed with CSS `zoom` (`Reader.razor.css`, `--rpage-zoom`); `chuvadiReaderMkRect` (`reader.js`) returns the layer's `getBoundingClientRect`, and `MkDownPress` maps `(clientX − left) / width`. Probe — a 100×50 box at (10,10) inside `zoom: 2`: WebKit **17.4, 18.2, 18.4 → [10, 10, 100, 50]** (unzoomed); WebKit 26.6, Chromium, Firefox → [20, 20, 200, 100]. With the unzoomed rectangle the formula gives pointer × zoom.
- **Reach:** every tool that takes a position from the zoomed page (move/resize handles, lines, images, signature placement, Redact — `Redact.razor.css` uses the same `zoom`) — to check on the fix head with the old WebKit.

**16 Nov, `platform/web` eab426b (Foundation patch 27, the `chvdUnzoomedRects` probe in `reader.js` / `redact.js`) — verified fixed.**
| Engine | `mark_position.py` (Rectangle + Text box; Fit, 54, 100, 150 %; unrotated and /Rotate 90) | On screen, worst | Saved PDF, worst |
|---|---|---|---|
| Chromium 153 | 16/16 | 0.0 px | 0.4 % of the page |
| WebKit 26.6 | 16/16 | 0.9 px | 0.4 % |
| Firefox 155 | 14/16 — the two missing cases (100 %, rotated) are `Page.goto` time-outs (OBS-1), not position failures | 0.9 px | 0.4 % |
| **WebKit 17.4** | **16/16** (stroke under the pointer 8/8) | 0.9 px | 0.3 % |

Reach (`tests/web-test/zoom_tools.py`, 5/5 on WebKit 17.4, WebKit 26.6, Chromium, Firefox): a rectangle moved by (+70, +90) px and resized by (+40, +30) px at a zoom other than 100 % lands where the pointer went, saved position within 0.6 % of the page; **Redact box** drawn over line 10 at zoom 0.80 removes line 10 from the saved file (at most the touching lines 9 / 11 with it) and nothing else. The Web chat's `mark_zoom.py` 4/4 × Chrome, Firefox, WebKit. Not covered by script: lines, images and signature placement at a zoom on the old WebKit (same code path; in the manual script for Safari 17/18 devices, Phase 2).

## WT-23 — unsaved marks on a tab that isn't showing are lost on reload without a question (Low)
**Build:** 4803bfa (D-181). Draw a mark on document A, switch to document B's tab, reload: no "Leave site?" question, and A's mark is gone (Chromium, WebKit). With the marked document showing, the question comes (3 engines) and staying keeps the mark. Stated as a limit in the Web build log §36 ("only the document that is showing counts"). **Options:** (a) accept for Phase 1 and list it; (b) the Ui reports "any open tab has unsaved marks" (a shared-Ui signal → Foundation) and the guard uses that. **Recommendation: (b)** when the next combined patch goes anyway — losing work silently is the thing D-181 exists to stop.

**16 Nov — decided: fix** (coordinator, D-186 / D-190): marks are kept with the tab in memory, and an ask-before-closing card (Save / Save as / Discard / Cancel) covers tab and window close. Foundation is building both; re-test on the head that carries them.

**16 Nov, 3f80768 (patch 29) — WT-23 verified fixed** (`tests/web-test/close_card_probe.py`, 10/10 in Chromium, Firefox, WebKit; the Web chat's `close_card.py` 14/14 × 3): the second tab shows none of the first tab's marks and the first still has its mark on return; a reload from the other tab raises the browser's question and staying keeps the mark; the close card reads "Save the marks on **text-13.pdf**? It has 1 mark that is not saved. It is lost if you close without saving." with Save, Save as…, Discard, Cancel; Esc cancels; **Save** downloads the 13-page file with the mark drawn on page 1 and closes the tab; afterwards a reload asks nothing; a session that expires with unsaved marks goes to "Signed out" at 39–42 s with no question in the way. After **Save as new PDF** the reload question no longer comes (the limit noted on 4803bfa is gone). Screenshot `screenshots/p29-close-card-webkit.png`. Not checked: the card at phone width.

## WT-24 — the session-expiry pass can hang for good; after that no session on the portal ever expires (High, security / capacity)
**Build:** a0a2f7c (patch 28); first seen on eab426b as "OBS-2". **Reproduced 2 times in 9 fresh-portal runs** with `tests/web-test/expiry_stall.py` (Chromium; short limits: idle 40 s, expiry check 2 s, worker idle stop 5 s, worker check 2 s).
**Steps:** sign in (Development sign-in), open the portal page with no document, close the tab (the browser stays running), wait. **Expected:** "Session ended (Idle)" about 40 s later — 7 runs of 9. **Actual, 2 runs of 9:** the gateway never logs "Session ended"; from then on **nobody's** session ends on that portal: a new person who signs in afterwards is still signed in 90 s after leaving, no expiry warning is shown, workers and files of people who left are not freed (one stayed 8.5 minutes until I restarted), and nothing is logged — no "Session expiry pass failed". Only a restart clears it.
**Evidence:** `evidence/wt24/gateway-stalled-a0a2f7c.log` — the worker logs "Session … ended; 0 page image(s) freed", then "Gateway is gone; stopping", then finishes `POST /_worker/end` with 200 and stops; the gateway's "Session ended" line never comes.
**Where it hangs (from reading the code, for the Web chat to confirm):** `SessionClock.TickAsync` awaits `PortalSessions.RevokeAsync` → `WorkerPool.EndInAsync`, which awaits `worker.Client.SendAsync` / `ReadFromJsonAsync` with no time limit. When the worker is being stopped at the same moment (its idle stop racing the end call), the answer never arrives and the await never returns; the one expiry loop is then stuck for every session. `NoticeAsync` and `AnnounceToAsync` use the same unbounded call.
**Why High:** idle and 8-hour expiry are a security promise; one ordinary event (a session ending just as its worker stops) switches them off for everyone until a restart, silently, and workers pile up towards `MaxWorkers = 40`. With production's longer intervals each session end is less likely to hit the race, but every one is a roll of the dice and the damage is permanent.
**Asks:** a time limit on every gateway → worker control call (end, notice, maintenance) with the time-out treated as "couldn't reach the worker"; one session's failure must not stop the pass for the others; a log line when a pass takes longer than a few seconds; the safety net (`EndAbandoned`) on its own timer so it can't be stuck behind the same await. A test that stops the worker while `/end` is in flight would pin it.
**Not checked:** whether back-channel sign-out still works on a stalled portal (it takes a different path; to check with the fix).

**17 Nov, 21665a3 (patch 30) — WT-24 verified fixed.** The cause Web found is one step on from my reading: the cancelled call ended the expiry loop quietly instead of hanging it; same effect.
- **Many runs:** `expiry_many.py` — 10 rounds × 8 people on one short-limit portal (half with a PDF, half with nothing open so their workers idle-stop before the session ends): **80 of 80 sessions ended**, last one at 36–38 s each round, no worker folder left. The gateway logged "Worker … wasn't reached for /end (TaskCanceledException); it is stopping or has stopped" **22 times** — the race that used to end the loop — and carried on. `expiry_stall.py` on 20 fresh portals: 20 of 20 ended at 38 s (was 2 stalls in 9 on a0a2f7c).
- **Worker killed (SIGKILL) 8, 5 and 4 s before the limit** (`expiry_forced.py`, three people): the other two people's documents deleted at 37.5–41 s, all workers gone, the log line above, a person who comes afterwards expires at 39–40 s. 5/5 each.
- **Worker frozen (SIGSTOP) 8 s before the limit:** "Worker … didn't answer /end within 10 s; given up", "Session expiry pass took 10.0 s"; the frozen worker is stopped by the supervisor and its files are gone by 73 s; a later person expires at 39 s. **One thing short of the claim:** the other two people's documents went at **45 s**, not 37–40 s — sessions that fall due while a pass is waiting on a frozen worker wait for that pass (up to the 10 s limit). Bounded and logged; against a 30-minute limit I count it as a note, not a bug (4 runs, same each time).
- Web's 8 new tests pass (Web tests 190/190). Evidence: `evidence/p30/`.

## WT-25 — when the browser leaves without a clean close, the worker and files stay 60–80 s past the session's end (Low; please confirm what sets the time)
**Build:** a0a2f7c; the same on eab426b and 21ac80d. `tests/web-test/linger.py` (a PDF open; idle 40 s, worker idle 5 s): tab closed cleanly in Chromium → worker and files gone **40 s** after leaving. Browser closed or killed with the tab open (Chromium, Firefox), and Firefox's tab close on a0a2f7c and eab426b → gone after **102–122 s**; the gateway logs "Session ended (Idle); 1 open tab(s) closed" on time, but the worker and the person's files go a minute or more later. **Expected (WT-21):** files freed when the session ends. **Question for Web:** which timer is this (the circuit's wait for a lost browser?), and is it the same length with production's limits or longer? **Side effect:** the Web chat's `comeback.py` allows 90 s and so fails in Firefox on most runs (5 of 7 here on a0a2f7c) — test tooling, same cause.

**17 Nov, 21665a3 — WT-25 verified fixed.** `linger.py`: tab closed cleanly 40 s; browser closed with the tab open 42 s; browser killed 42 s — Chromium and Firefox (was 100–122 s). Web's `gone_browser.py` 4/4 closed and 4/4 killed × Chrome, Firefox, WebKit; `comeback.py` (now 65 s allowed) 5/5 Chrome, WebKit; Firefox 5/5 when it runs through — 2 of 3 Firefox runs stop at a `Page.goto` time-out (OBS-1 below).

## OBS-1, better understood (17 Nov) — Firefox under Playwright sometimes never reports "load" for a second page in the same browser context
When it happens the page is in fact there and working: `document.readyState` is "complete", the restored tab is shown, no request is pending (`/tmp/explore/ffback.py`, 1 run in 4; 3 of 16 cases in `mark_position.py`). So it is the test harness and the portal's own move to /reader during load, not something a person in Firefox meets. Recorded so nobody chases it again; M-2 in the manual script covers real Firefox.

## Note on patch 29 — Excel sizes set by dragging go on a page reload (question, not a bug entry)
Column and row sizes set by dragging are kept while the tab is open and across sheet changes, but a browser reload brings the tab back at the file's own sizes (all three engines). The commit says "kept with the tab in memory"; on the portal a reload keeps the tab (D-174) but not this. View-only, nothing is lost from the file. **Decided 16 Nov: accepted for Phase 1 (D-193, display only).** Options were: (a) accept and say so in the build log — no work; (b) keep the sizes with the session's tab as the open documents are — consistent with D-174, small Web/Core change. I'd take (a) for Phase 1.

## Library items (Arun's libraries)
- **LIB-1 chuvadi-pdf refuses `/P` written as an unsigned 32-bit number.** PDFs whose encryption dictionary has e.g. `/P 4294965240` (pypdf writes this) fail with "Invalid integer … must be a valid 32-bit signed integer". qpdf, poppler and pdf.js open them (reading the bits). Ask: accept 0…4294967295 and reinterpret as signed. Not worked around in the app (rule 2). **10 Nov: fixed in chuvadi-pdf 3.32.0** (`platform/web` 002bf02) — pypdf files with `/P 4294965240` and `/P 4294967292` open (the latter after its password), and the no-print bits are honoured (print card refuses).
- **LIB-2 Chuvadi.Sheets 1.1.2 can't open XLSX with absolute relationship targets.** openpyxl (and so pandas) writes `Target="/xl/worksheets/sheet1.xml"`; Core reports "Couldn't open this workbook: Part '/xl/xl/worksheets/sheet1.xml' not found in package." LibreOffice/Excel (relative targets) open fine. Sheets 2.0.2 fixed `./` and `..` targets; to confirm whether absolute targets are covered when the Reader moves to 2.0.2 (D-87). **9 Nov: fixed in Sheets 2.0.2** — openpyxl files (`Target="/xl/worksheets/sheet1.xml"`) open in c38bd80.
- **Known gap, not new:** a PDF with an open (user) password can't be opened on the portal — "This PDF is encrypted and needs a password to open." with no way to type it. Listed as library-gated in DESIGN-NOTE ("password API"); recorded so the test is re-run when that lands. **9 Nov: works in 1b32ad8** (prompt, wrong-password message, opens; 3 engines).
- **Sheets 2.0.4, built-in date format 14** (found by the Web chat, recorded here so it isn't lost): renders as `mm-dd-yy`; Excel shows the system short date ("11/5/2024" en-US, "05-11-2024" en-IN).
