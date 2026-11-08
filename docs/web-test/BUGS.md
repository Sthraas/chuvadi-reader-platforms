# Web portal — bugs found by the Web Test chat

Tested: `platform/web` @ **31b063e** (Foundation 4819d66 underneath), 8 Nov 2026. Every bug is to be fixed, however small (rule 7); each fix comes back here for re-verification. "Existing file" means a chuvadi-reader file: the fix goes to Arun as a listed change through the coordinator (rules 4 and 5), not straight into the code.

Severity: **High** = wrong result, security weakness, or a screen that doesn't work; **Medium** = untrue or missing text the decisions require; **Low** = polish, hardening, tooling.

| # | Severity | Area | Title | Owner | Status |
|---|---|---|---|---|---|
| WT-01 | High | Security | In gateway mode the Reader page loses its Content-Security-Policy (only `frame-ancestors 'self'` reaches the browser) | Web | **Verified fixed** in 1b32ad8 and **d180f2e** (9 Nov 03:30) — full policy on the gateway Reader page |
| WT-02 | High | Function | Print "Current" prints the **next** page; Measure card shows the next page number | Existing file → Arun | **Verified fixed** in 1b32ad8 and **d180f2e** — Current prints p1/p5 correctly (Chromium, Firefox); Measure card "page 5" on p5 (3 engines) |
| WT-03 | High | Design | Phone width shows squeezed desktop rails, not the phone shell; per-page strip and Arrange shelf clipped | Web (rebase) + Web portal UI (re-check) | **Verified fixed** in 1b32ad8 and **d180f2e** — phone shell (bottom bar Read/Mark/Arrange/Protect, full-width page, no sideways scroll), 3 engines |
| WT-04 | Medium | Wording | Status bar still says "encrypted at rest" (D-98) | Web portal UI → Foundation patch → Web | **Verified fixed** in 1b32ad8 and **d180f2e** — "kept in memory only", 3 engines |
| WT-05 | Medium | Wording | 12a pitch still says "encrypted at rest" | Coordinator decision, then Web portal UI | **Verified fixed** in 1b32ad8 — 12a "kept in memory only", 3 engines (D-103); unchanged in d180f2e |
| WT-06 | Medium | Design | Account menu has no "Terms of use · Privacy" footer (D-97) | Web portal UI → Foundation patch → Web | **Verified fixed** in 1b32ad8 and **d180f2e** — "Terms of use · Privacy" footer, 3 engines |
| WT-07 | Low | Security | The circuit (`/_blazor`) accepts a foreign `Origin` | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — foreign Origin → 403, own → 200 |
| WT-08 | Low | Security | File names keep Unicode bidi controls (U+202E), so a name can display reversed | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — U+202E removed, 3 engines |
| WT-09 | Low | UX | The no-print reason is only a hover tooltip on a disabled button (invisible on touch) | Existing file → Arun | **Verified fixed** in 1b32ad8 and **d180f2e** — reason in the card body, 3 engines |
| WT-10 | Low | UX | A file that can't be opened shows raw parser text, and a "Fetch…" button where the portal says "Upload" | Existing file → Arun (text) / Web portal UI (label) | **Partly fixed** (d180f2e) — damaged-file sentence and "Upload" ✅; Arrange still "Fetch…" (diff on `platform/web-ui` 99ba339, waiting for Foundation → Web) |
| WT-11 | Low | Packaging | Publish output carries `web.config` (IIS), `appsettings.Development.json`, `.pdb` and `.xml` files | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — `check-package.sh` PASS, no third-party assemblies |
| WT-12 | Low | Docs/CI | The plan's build command fails from a clean clone; Web is built without `-warnaserror` in CI and isn't in Platforms.slnx | Web | **Verified fixed** in 1b32ad8 and **d180f2e** — documented restore works from an empty cache; 0 warnings with `-warnaserror` |
| WT-13 | Low | Test tooling | `load.py`: no output folder created; "paging" is mostly fixed sleeps; one browser for everyone | Web | **Verified fixed** in **d180f2e** — `load.py` creates its output folder, reports ms, no errors (5 people) |
| WT-14 | Low | Test tooling | `sangam_signin.py` sign-out step races in WebKit (1 in 5 runs) | Web | **Verified fixed** in **d180f2e** — WebKit sign-in suite 13/13 in 5 of 5 runs; Chrome 13/13, Firefox 13/13 |
| WT-15 | Medium | Security | Production starts with an `http://` Sangam address | Web | **Verified fixed** in **d180f2e** — Production with `http://` Sangam refuses to start ("Sangam:Authority must be an https address outside Development."); https starts |
| WT-16 | Low | UX | "Split to folder" on the portal arrives as one download per page | Web (D-129: one .zip via Chuvadi.Zip) | Open — D-129: one .zip via Chuvadi.Zip, waiting for Chuvadi.Zip in `ci/packages` |

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

## Library items (Arun's libraries)
- **LIB-1 chuvadi-pdf refuses `/P` written as an unsigned 32-bit number.** PDFs whose encryption dictionary has e.g. `/P 4294965240` (pypdf writes this) fail with "Invalid integer … must be a valid 32-bit signed integer". qpdf, poppler and pdf.js open them (reading the bits). Ask: accept 0…4294967295 and reinterpret as signed. Not worked around in the app (rule 2).
- **LIB-2 Chuvadi.Sheets 1.1.2 can't open XLSX with absolute relationship targets.** openpyxl (and so pandas) writes `Target="/xl/worksheets/sheet1.xml"`; Core reports "Couldn't open this workbook: Part '/xl/xl/worksheets/sheet1.xml' not found in package." LibreOffice/Excel (relative targets) open fine. Sheets 2.0.2 fixed `./` and `..` targets; to confirm whether absolute targets are covered when the Reader moves to 2.0.2 (D-87).
- **Known gap, not new:** a PDF with an open (user) password can't be opened on the portal — "This PDF is encrypted and needs a password to open." with no way to type it. Listed as library-gated in DESIGN-NOTE ("password API"); recorded so the test is re-run when that lands. **9 Nov: works in 1b32ad8** (prompt, wrong-password message, opens; 3 engines).
