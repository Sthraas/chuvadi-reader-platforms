# Web portal — test results (Web Test chat)

**Session 1: 8 Nov 2026, 19:15–20:30 IST.** Tested `platform/web` @ **31b063e** (Foundation 4819d66), Release publish, gateway mode unless stated. Environment and IDs: `TEST-PLAN.md`. Bugs: `BUGS.md` (WT-xx). Screenshots: `screenshots/` (a curated set; the full 446-shot run is reproducible with `tests/web-test/shots.py`).

Summary: **build, tests, isolation, uploads, hostile files, expiry, drag-and-drop, print path and legal pages pass.** Found 13 bugs: 3 High (gateway CSP, print prints the next page, no phone shell), 3 Medium (wording and footer per D-97/D-98, two already fixed on the Web portal UI branch), 7 Low. Two library items for Arun. Not yet run: real-Sangam end-to-end, production rehearsal (TLS/HSTS/`__Host-` cookie), Mark/forms/redact/split/password flows by hand — next session.

Legend: ✅ pass · ❌ fail (bug linked) · ⚠️ pass with a note · ⏳ not run yet · 👤 needs a person / real device · 🖥 needs the staging VM.

## 1. Build from clean
| ID | Result | Evidence |
|---|---|---|
| X-B1 | ✅ | Empty `NUGET_PACKAGES`; `dotnet restore ChuvadiReader.Platforms.slnx --configfile ci/nuget.config` (5.1 s), then `dotnet build … -c Release -warnaserror --no-restore`: **0 warnings, 0 errors** (27.5 s). Without the restore step the plan's command fails with NU1301 → ⚠️ WT-12 |
| X-B2 | ✅ | `ChuvadiReader.Web` and `.Web.Tests` with `-warnaserror`: 0 warnings each (they aren't in Platforms.slnx → WT-12) |
| X-B3 | ✅ | Reader **171/171**, Hosting **48/48**, Mobile UI **15/15**, Web UI **31/31**, Web **142/142** (27 s) |
| X-B4 | ✅ | Publish (16 MB): 35 assemblies, all ours (`Chuvadi.*` 3.31.2, Docs 1.1.0, Sheets 1.1.2, Fonts 1.0.0, `ChuvadiReader.*`, `LiPicons.Blazor` 1.1.0); the rest is the shared ASP.NET Core framework. No third-party assembly. Static: Blazor's own `blazor.web.js`/`blazor.server.js`, our JS/CSS, LiPi Sans and the handout's OFL fonts (Fraunces, Instrument Serif, IBM Plex Mono) served locally — no remote URL in any CSS/JS except Microsoft doc links inside `blazor.*.js` comments/messages. Extra files that shouldn't ship → WT-11 |
| X-B5 | ✅ | 34/34 chuvadi-pdf 3.31.2 `.nupkg` SHA-256 match `PACKAGES-3.31.2.md` |

## 2. Flows (Web chat plan §1)
| ID | Result | Evidence |
|---|---|---|
| F-1 | ✅ | 12a at `/signin` (Sangam mode): "Continue with Sangam", "Download the desktop app", "Terms of use"; no ID/password field (D-63). Light/dark × 3 engines × 5 widths in `screenshots/` |
| F-2 | ⏳ | Needs the real local Sangam (next session). Authorize redirect checked: X-S2 |
| F-3 | ✅ | `flows.py` Chrome/Chromium/Firefox/WebKit: open via chooser |
| F-4 | ✅ | Paging and jump timed in `perf.py` (§6); find ⏳ by hand |
| F-5 | ⏳ | Mark → save download by hand, next session |
| F-6 | ✅ | `flows.py` 4 engines: chooser allows several files; `merged.pdf` 26,139 bytes |
| F-7, F-8 | ⏳ | Split/Bench/press, redact, password protect/remove: next session |
| F-9 | ⚠️ | Print reaches the browser in 4 engines (Chrome: dialog call; Firefox: "print dialog" message; Chromium/WebKit: link → own tab). Print PDF is **vector** (41 text operators, 0 images, `pdffonts` shows text fonts). **But "Current" prints the next page → ❌ WT-02** |
| F-10 | ⚠️ | No-print PDF (qpdf `--print=none`): Print button disabled, reason only as tooltip → WT-09. Server refusal: unit `WebPrintTests` ✅ |
| F-11, F-12, F-19 | 👤 | Clipboard per browser, external links, ⌘ on a real Mac |
| F-13, F-14, F-16 | ⏳ | Real-Sangam run, next session |
| F-15 | ✅ | `/terms`, `/privacy`, `/licence?part=cookies` 200 before sign-in, DRAFT line present; `?part=<script>…` → 200, nothing echoed |
| F-17 | ✅ | X-I1, X-I6 (separate workers; B can't fetch A's print) |
| F-18 | ❌ | Phone → WT-03. Tablet 820×1180 renders the rails (screens in `screenshots/`); to re-check against 72/72/60 px after the rebase |
| F-20 | ⏳ | Unit tests ✅ (`MaintenanceTests`, `GatewayMaintenanceTests`); browser run next session |
| F-21 | ✅ | `flows.py` 4 engines: stray drop cancelled (`dropEffect none`; Firefox reports `copy` but the drop is cancelled) |
| F-22 | ✅ | `flows.py` 4 engines: a fake PDF refused with "fake.pdf isn't a valid PDF file."; a real PDF opens. Real desktop drag 👤 |
| F-23 | ⏳ | Privacy link beside Terms exists on `platform/web-ui` ce057c9, not in this build |

## 3. Security (Web chat plan §2 and X-I)
| ID | Result | Evidence |
|---|---|---|
| S-1 | ✅ | Unit `EndpointAuthTests`; probes: `/_worker/health`, `/_worker/end` → 404 from the browser side |
| S-2 | ⏳ | `__Host-chvd` Secure needs https: production rehearsal next session |
| S-3…S-5 | ✅ unit | `SangamSignInTests` (refusals), open redirect, back-channel |
| S-6 | ✅ | `/portal/activity`: no Origin → 403; `https://evil.example` → 403; own origin → 204 |
| S-7 | ⚠️ | X-I5/X-I6 below; bidi controls kept → WT-08 |
| S-8 | ✅ | X-I1: B fetching A's `/portal/print/<ticket>` → **404**; A → 200 |
| S-9 | ✅ | Folders `workers/<key>/{home,tmp,data}` all **0700**; browser `X-Chvd-Sub`/`X-Chvd-Worker` sent to the gateway are stripped (unit); `/_worker/*` 404 |
| S-10 | ✅ | `expiry.py` (3 engines): files gone at expiry. X-I8: after everyone left, workers 0 and data root empty within ~6 min |
| S-11 | ✅ | `expiry.py` Chrome, Firefox, WebKit **8/8 each**: warning at 15–17 s (40 s idle − 25 s), "I'm still here" clears it, the warning hands over `text-13.pdf` (same size), session ends 42 s after the last activity on `/signed-out`, files gone, no page errors |
| S-12 | ✅ unit / ⏳ rehearsal | `StorageCheckTests`; refusal on a disk data root by hand next session |
| S-13 | ❌ | **Gateway mode: the Reader page carries only `frame-ancestors 'self'` → WT-01.** Every gateway page, relayed static file, 404 and error carry the full policy, `nosniff`, `SAMEORIGIN`, `no-referrer`, Permissions-Policy, COOP, CORP; no `Server` header. TLS/HSTS: rehearsal next session |
| S-15 | ✅ | `/error` anonymous (500 page, no stack trace in the body) |
| S-17 | ✅ | `/licence?part=<script>alert(1)</script>` → nothing echoed |
| S-18 | ✅ | X-I6 |
| X-I3 | ⚠️ | Circuit negotiate accepts a foreign Origin → WT-07 |
| X-I5 | ✅ (one ⚠️) | Through the real chooser: `../../../../etc/passwd.pdf` → `passwd.pdf`; `..\..\windows\win.pdf` → `win.pdf`; `CON.pdf` → `_CON.pdf`; 250/1000 chars → 120-char stem; `ok<img src=x onerror=alert(1)>.pdf` → `okimg src=x onerror=alert(1).pdf`, no script ran; tab → removed; CJK kept; `.pdf` → refused "pdf: this kind of file can't be opened here."; no file outside the person's folder; U+202E kept → WT-08 |
| X-I6 | ✅ | Each refused cleanly with one message, no worker crash, the other person's next-page stayed **69–99 ms** throughout: `fake.pdf` "isn't a valid PDF file."; `pdf-as-docx.docx` "isn't a valid DOCX file."; `docx-as-pdf.pdf` refused; `empty.pdf` "is empty."; truncated / random / 200k-nested / page-loop / 1 GB Flate bomb → "Could not open this document…" (raw text → WT-10); 2 GB zip bombs (DOCX, XLSX) → refused, worker survived; `over-limit.pdf` (210 MB) → "larger than the 200 MB limit" in **0.1 s** (size checked before upload), others unaffected (73–120 ms). User-password PDF → "needs a password" (known gap, BUGS library section) |
| X-I7 | ✅ | `find / -xdev -newer <portal start>`: nothing written by the portal outside `/dev/shm/chvd-*`; no Data Protection key files anywhere |

## 4. Sangam failure cases (§3 and X-S)
| ID | Result | Evidence |
|---|---|---|
| X-S2 | ✅ | `/signin/sangam` → 302 to authorize with `response_type=code`, `client_id`, `redirect_uri …/signin-sangam`, `scope=openid profile email org.current`, `state`, `nonce`, `code_challenge` + `S256`; flow cookie `chvd.oidc.<state>`; no secret in the URL |
| G-1 | ⚠️ | Cold portal, Sangam down: **503 in 167 ms** with "Sangam can't be reached right now." ✅. Warm portal (discovery cached): 302 straight to the dead Sangam, so the browser shows its own "can't connect" page → option O-2 |
| G-4 | ✅ unit | filter covers it; stub `--bad-json`/`--wrong-issuer` by hand next session |
| G-9 | ⚠️ | Slow Sangam (200 s): the person waits **60.05 s**, then the 503 message ✅; `/terms` (56 ms) and `/signin` (30 ms) unaffected meanwhile ✅. 60 s is long → option O-1 |
| G-2, G-3, G-5…G-8, G-10, G-11 | ✅ unit / ⏳ | Real-Sangam session next |
| G-12 | 👤 | Needs a Sangam test person in two organisations |

## 5. Design fidelity
| ID | Result | Evidence |
|---|---|---|
| X-D1 12a | ✅ | Side by side with the handout at 1280×720: same split layout, brand, headline, card; ID/password fields and "Forgot?" gone (D-63); promises 1 and 3 per D-31. Pitch still "encrypted at rest" → WT-05 |
| X-D1 12b | ⚠️ | Account menu: name, Sangam ID line, "Get the desktop app", "Sign out" ✅; Storage / My files / Shared gone (scope) ✅; "Account settings" hidden (URL not configured) ✅; Terms · Privacy footer missing → WT-06. The handout frame shows the left bar collapsed; the build opens expanded with "Collapse" (shared Ui default — noted, not a Web bug) |
| X-D2 | ✅ | Desktop: Home + Read/Mark/Arrange/Protect in light, dark, palm, indigo, contrast — themes switch every surface, no unthemed panels seen; 3 engines (446 shots) |
| X-D3 | ❌ | Phone: no phone shell → WT-03 (Chromium, WebKit, Firefox) |
| X-D4 | ❌ | Status bar "encrypted at rest" → WT-04 |
| — | ⚠️ | Home on the portal shows a "Storage map" (Finance, Legal… "0 docs · 0 B") and "Your shelves are empty — open the Library". With no server storage (D-31 scope) these read as storage features. Question for the coordinator (Q-3) |

## 6. Load and speed (sandbox: 2 vCPU, 8 GB; server **and** all browsers on the same 2 cores)
`perf.py`, Chromium, `text-13.pdf`, gateway mode, each person a fresh worker. Medians (p90 / max) in **ms**.

| People | ttfb | first frame (FCP) | ready | first page | jump to p10 | next page | workers | per worker |
|---|---|---|---|---|---|---|---|---|
| 1 (cold, ×5) | 16–48 (one 1,456) | 292–352 | 375–439 | — | — | — | 1 each | ~135 MB idle |
| 1 | 778 | 1,316 | 1,736 | **375** | 832 | **267** | — | 179 MB |
| 10 | 4,800 (5,598) | 7,866 (9,212) | 8,298 (9,333) | 4,602 (6,127) | 2,852 (3,833) | 498 (1,575) | 10 | 161 MB |
| 20 | 10,426 (12,694) | 16,236 (20,116) | 16,578 (20,496) | 11,532 (16,060) | 5,410 (7,285) | 368 (2,067) | 20 | 162 MB |
| 1, 500-page text | 700 | 1,252 | 1,632 | **664** | 919 | 353 | — | 207 MB |
| 1, 91 MB 40-page scan | 23 | — | 360 | **1,247** | 826 | 231 | — | **497 MB** peak |

- **All 10 and 20 succeeded**, no errors. Gateway 185–204 MB under load; returns to ~210 MB idle; 299 open handles after this session (baseline for V-1).
- The 10/20-person times are dominated by this sandbox: 20 workers starting **and** 20 headless browser contexts on 2 cores (load average > 10). One person alone: first page 375 ms, next page 267 ms. These are not production numbers.
- **40 people:** not run here — 40 × ~165 MB workers (6.6 GB) plus 40 browser contexts exceed 8 GB. On the 16 GB VM the workers fit (≈ 6.8 GB with the gateway, leaving ~9 GB for documents and the OS). → 🖥 V-1.
- ReadyToRun publish (test only): ready 356–458 ms vs 375–439 ms JIT — no measurable gain, so not proposed.
- Memory per person: **~135 MB idle worker, ~165–180 MB after a typical 13-page session, ~500 MB with a 91 MB scan** (cap 1,536 MB).

## Still needs a person or the VM
- 👤 **M-1** Edge on Windows 11 · **M-2** Safari on a Mac (⌘ keys, print tab, image copy, 12a light/dark) · **M-3** Safari on iPhone and iPad · **M-4** Chrome on Android — the 12-step sequence in `docs/web/TEST-PLAN.md` §5a, after WT-03 is fixed.
- 👤 A real desktop drag of one and several files (F-21/F-22), clipboard image permission (F-11), G-12 (two-organisation Sangam person).
- 🖥 **V-1** 2-hour soak at 40 people · **V-2** real Let's Encrypt and forced renewal · **V-3** large documents at the limits with 20 others running · **V-4** fuzz corpus (this session's hostile set is a start: `tests/web-test/make_corpus.py`) · **V-5** log review · **V-6** restart with banner under load · **V-7** no DRAFT lines before go-live.

## Observations (not bugs yet)
- **OBS-1 Firefox automation:** in 2 of 15 Firefox page loads during the long screenshot run, Playwright's `load` event didn't fire within 30 s with **no pending request**; 9/9 isolated retries loaded in 151–1,181 ms. Looks like an automation quirk; check on real Firefox in a manual run.
- `/error` answers 500 when opened directly (by design: it is the error page).

## Re-verification log
| When | What | Result |
|---|---|---|
| 8 Nov 20:45 | Branch heads after the coordinator's 20:40 decisions | `platform/web` still 31b063e (not rebased; lacks Foundation 584bbf2) → nothing to re-test in a running build yet. Source check of Foundation **63f37b1**, which the rebase will bring: status bar "processed on the server · kept in memory only · only you can see it" (WT-04); 12a pitch "…kept in memory only…" (WT-05, D-103 in 9fbed93); `PortalLegalLinks` in `AccountMenu.razor` (WT-06); `PhoneShell` wired in `MainLayout.razor` (WT-03). WT-02 not yet changed (`Reader.razor` still passes 1-based `CurPage` to `PrintCard`) — expected, it goes into the combined patch. All four to be re-run in browsers (3 engines, phone/tablet/desktop) once the Web chat rebases |

## Session 2 — 9 Nov 2026, 01:30–02:20 IST
### Remaining cases from session 1 (build 31b063e, then regression on 1b32ad8)
| ID | Result | Evidence |
|---|---|---|
| F-2, F-13, F-14, F-16, S-5, G-2…G-8 (real Sangam) | ✅ | Local Sangam **v1.0.0-rc.16 (d43a5ff)**, exported with `git archive`, read-only, PostgreSQL 16, Development; portal gateway mode. `sangam_signin.py` **13/13 in Chrome, Firefox, WebKit** on 31b063e and again on **1b32ad8**: 12a → Continue with Sangam → Sangam sign-in → back signed in; Reader shows the Sangam name; account menu name + Sangam ID; cookie HttpOnly + SameSite=Lax; no flow cookie left; sign-out → `/signed-out`; the other open tab ended too; asked to sign in again; second sign-in; **back-channel logout from Sangam ends the open tab**. One WebKit run in five raced on sign-out (test script → WT-14) |
| X-S5 (8 h absolute) | ✅ | 1b32ad8, real Sangam, `Sangam__AbsoluteSessionLifetime=00:01:30`, warning 30 s, check 2 s; person kept active (12 page turns, one every ~5 s): warning "Your session is about to end — A session lasts at most 8 hours, so this one ends in less than a minute…" ~30 s before the end; ended on `/signed-out` ~95 s after sign-in (90 s + 5 s polling) despite activity (`screenshots/v2-absolute-warning.png`) |
| S-2, S-13 TLS (production rehearsal) | ✅ | `ASPNETCORE_ENVIRONMENT=Production`, gateway, tmpfs data root, self-signed PEM, real Sangam (second client `https://localhost:8443/`): starts; `sangam_signin.py --insecure` 13/14 — cookie **`__Host-chvd` + Secure** ✅; HSTS `max-age=31536000; includeSubDomains` ✅; full CSP ✅; `http://…:8080` → **307** to https ✅; **TLS 1.0/1.1 refused, 1.2/1.3 accepted** ✅; `X-Dev-User` ignored (302 to sign-in) ✅. Back-channel over https ✗ only because Sangam's own certificate check rejects a self-signed portal certificate (its callback, not the system store) → 🖥 V-2 with Let's Encrypt. Production accepted an `http://` Sangam address → **WT-15** |
| F-5 Mark | ✅ | Firefox: Rectangle drawn, "Save as new PDF" → `text-3-edited.pdf`; the shape is in the file (form XObject `/CvStamp0`, rendered and seen). Highlight, Note, Fill form are "Coming soon" — same as the desktop app (library-gated), not portal bugs. In Chromium with the Development header the download got 404: Playwright doesn't send the injected header on Chromium's download request; **with a real Sangam cookie Chromium downloads it (200)** — harness only |
| F-7 Split | ✅ | Document ▾ Split → "Use current" → "Split to folder": **13 files `text-13_p01…p13.pdf` in 0.6 s** as 13 separate downloads → option O-3 / WT-16 |
| F-8 Redact | ✅ | Protect → Redact box over "Line 1:" → "Save redacted copy" → `text-3-redacted.pdf`: "Line 1:" gone from `pdftotext` **and from the raw content stream** (true removal, not a cover-up); a line the box touched went too |
| F-8 Password | ✅ | Protect → Password → set → `text-3-protected.pdf`; `qpdf --requires-password` → needs a password |
| Forms | ⏳ | "Fill form" is "Coming soon" in the shared Ui (library-gated); nothing for the portal to test yet |
| — | ℹ️ | Protect shows "Sign with certificate — Waiting on the PDF library — certificate signing fails in chuvadi-pdf 3.30.1" (disabled; D-27 keeps it off on the portal anyway) |

### Re-verification on `platform/web` @ **1b32ad8** (Foundation 839d39d)
Clean cache, documented restore, `-warnaserror`: shared solution 0 warnings — Reader **187**, Hosting **59**, Mobile UI **16**, Web UI **33**; Web and Web.Tests 0 warnings, Web **154/154**; publish 0 non-own assemblies; `check-package.sh` PASS. Browser checks: `tests/web-test/verify_fixes.py` (Chromium, Firefox, WebKit).

| Bug | Result |
|---|---|
| WT-01 CSP | ✅ Reader page in gateway mode: full policy + Blazor's `frame-ancestors` |
| WT-02 print page | ✅ Current on p1 → "Page 1 of 13" (1 page); on p5 → "Page 5 of 13" (Chromium, Firefox; WebKit hands print over as a link, so the server-side check is the same code); Measure card "page 5" on p5 |
| WT-03 phone shell | ✅ top bar with tab + page count, full-width page (366/390 px), bottom bar Read/Mark/Arrange/Protect, Home bottom bar Home/Library/Tabs/Settings — 3 engines (`screenshots/v2-phone-*.png`) |
| WT-04 status bar | ✅ "processed on the server · kept in memory only · only you can see it", 3 engines |
| WT-05 12a pitch | ✅ "kept in memory only", no "encrypted at rest"; Privacy link present (F-23 ✅), 3 engines |
| WT-06 account footer | ✅ "Terms of use · Privacy", 3 engines |
| WT-07 circuit Origin | ✅ foreign Origin → 403, own → 200 |
| WT-08 bidi names | ✅ U+202E removed, 3 engines |
| WT-09 no-print reason | ✅ "This file's permissions don't allow printing." in the card body, 3 engines |
| WT-10 wording | ⚠️ damaged file → "This PDF is damaged" ✅, "Upload" ✅; **Arrange still says "Fetch…"** (addendum) |
| WT-11 package | ✅ |
| WT-12 build/CI | ✅ |
| O-1 Sangam slow | ✅ 503 + message in **2.1 s** (the 2 s probe answers first; 10 s call limit behind it) |
| O-2 Sangam down, warm | ✅ 503 + message in 5 ms once the 30 s cached "up" result expires; back to 302 when Sangam returns. Within those 30 s a person can still be sent to a dead Sangam (as decided) |
| Q-3 Home wording | ⏳ unchanged (pending the Web portal UI's confirmation) |
| Regression | ✅ `flows.py` 9/9 × Chrome, Firefox, WebKit; `sangam_signin.py` 13/13 × 3; hostile-file suite: see below |

**Hostile-file regression on 1b32ad8** (`sec_browser.py`, Chrome): 19/21. All hostile names contained as before (`passwd.pdf`, `win.pdf`, `_CON.pdf`, 120-char stems, HTML stripped, U+202E removed, CJK kept); no script ran; every damaged/hostile document refused with one message, worker survived, the other person paged at 67–99 ms. Messages are now plain: damaged PDF → "…Chuvadi can try to rebuild it as a new copy." with "Try to repair (new copy)" and "Details"; zip bombs → "This Word document / Excel workbook is too large to open: its contents unpack to more than 2,048 MB. It may be damaged." The 2 fails are the known harness artefact (Playwright pushing 210 MB through the one shared browser); re-checked with separate browsers: refusal in 0.1 s, the other person 83–167 ms ✅.

**New in 1b32ad8 — password-protected PDFs open** (was a known gap): "This PDF is password-protected · Enter its password to view it here. The password stays in memory for this tab only." Wrong password → "That password doesn't open this file."; right password → page 1 drawn; the password never appears in the page HTML — ✅ Chromium, Firefox, WebKit.

## Re-verification on `platform/web` @ **d180f2e** (9 Nov 03:20–03:50 IST)
Rebased head: 3548bdd (= the 1b32ad8 fixes, rebased) + d180f2e (WT-14, WT-15).

- **Build from clean** (empty cache, documented restore, `-warnaserror`): shared solution 0 warnings — Reader **191**, Hosting **59**, Mobile UI **16**, Web UI **33**; Web + Web.Tests 0 warnings, Web **156/156**; publish: 0 third-party assemblies, `check-package.sh` PASS.
- **Browser checks** (`verify_fixes.py`, Chromium/Firefox/WebKit): WT-02 (print p1/p5 in Chromium and Firefox; Measure card "page 5" in all three), WT-03 (phone shell, all three), WT-04, WT-06, WT-08, WT-09, WT-10 failed-open screen — ✅. Arrange "Fetch…" (WT-10 addendum) and Q-3 still open, as expected (not in Web yet).
- **Curl checks:** WT-01 full CSP on the gateway Reader page ✅; WT-07 foreign Origin 403 / own 200 ✅.
- **WT-15:** Production + `http://` Sangam → refuses to start with "Sangam:Authority must be an https address outside Development." (the process exits on an unhandled options-validation exception, exit 134 — the message is clear; a tidier one-line refusal like the other start-up checks would be nicer, not a bug); Production + https → starts ✅.
- **WT-14:** `sangam_signin.py` (real Sangam rc.16) WebKit **13/13 × 5 runs**, Chrome 13/13, Firefox 13/13 (one Firefox run printed 12 lines; re-run 13/13).
- **WT-13:** `load.py` 5 people: output folder created, results in ms, no errors (print median 834 ms on this 2-vCPU sandbox), peak 179 MB per worker.
- **Regression:** `flows.py` 9/9 × Chrome, Firefox, WebKit.

## Re-verification on `platform/web` @ **c38bd80** (9 Nov 06:05–07:00 IST)
Rebased on Foundation's latest: WT-10 Arrange wording, Q-3 wording, Chuvadi.Docs **2.0.0**, Chuvadi.Sheets **2.0.2**, Chuvadi.Zip **1.0.0** (WT-16).

- **Build from clean:** shared solution 0 warnings — Reader **199**, Hosting **59**, Mobile UI **16**, Web UI **39**; Web + Web.Tests 0 warnings, Web **164/164**; `check-package.sh` PASS; no third-party assemblies. New packages' SHA-256 match `PACKAGES-DOCS-SHEETS-2.md` / `PACKAGES-ZIP-1.0.0.md`.
- **WT-10** ✅ no "Fetch" on the failed-open screen or in Arrange (3 engines). **Q-3** ✅ Home: "FILES IN THIS SESSION", "Nothing shelved this session — open the Library" (3 engines).
- **WT-14** ✅ WebKit 13/13 × 3, Chrome 13/13, Firefox 13/13 (real Sangam rc.16). **WT-15** ✅ refuses `http://` Sangam in Production.
- **WT-16** ✅ Split to folder (13 pages) → one `text-13.zip` in Chromium, Firefox and WebKit (Chromium/WebKit with a real Sangam cookie — see note), zip intact, 13 entries `text-13_p01…p13.pdf`, each the right single page; a one-file Mark save stays `text-3-edited.pdf`.
- **Regression:** `verify_fixes.py` — WT-02 (Chromium, Firefox), WT-03, WT-04, WT-06, WT-08, WT-09 ✅ in 3 engines.

### Word and Excel data fidelity (Docs 2.0.0, Sheets 2.0.2)
Corpus `tests/web-test/make_fidelity.py`: 14 text tokens built to catch normalisation (double/leading/trailing spaces, mIxEd case, misspellings kept as written, Tamil, Hindi, `<>&"'`, `00123`, a 20-digit string, accents, a tab) + 9 formatted numbers + a formula. Each file made by python-docx/openpyxl **and** re-saved by LibreOffice. Checked from the page DOM (`textContent`, which keeps every space) — Word runs render with `white-space: pre-wrap`, grid cells with `pre`.

| File | Result |
|---|---|
| fid.docx (python-docx) | ✅ **14/14 exact**, every space, case, misspelling and script as in the file |
| fid-lo.docx (LibreOffice) | ✅ 14/14 — LibreOffice stores the two leading spaces as their own run (`<w:t xml:space="preserve">  </w:t>`); the portal draws that run, nothing lost |
| fid.xlsx (openpyxl, absolute part paths) | ✅ opens (LIB-2 fixed in 2.0.2); text cells **14/14 exact**; General number 3.14159265358979 exact; formatted numbers ❌ **WT-17**; uncached formula blank (never recalculated — as designed) |
| fid-lo.xlsx (LibreOffice) | Same as above; the formula's cached result **2** shown |
| doc.docx, sheet.xlsx, sheet-libreoffice.xlsx (session-1 files) | ✅ open; sheet.xlsx no longer refused |
| zip-bomb.docx / .xlsx | ✅ refused: "…its contents unpack to more than 2,048 MB" |

"As printed" (xlsx) is disabled — waits on Chuvadi.Layout (D-08), as expected.

**Harness note:** with the Development header (`X-Dev-User`, injected by Playwright) Chromium and WebKit don't send the header on a download request, so the person's worker refuses the link (404). With a real Sangam cookie every engine downloads. Firefox carries the header. Not a portal bug; recorded so nobody re-reports it.

## 10 Nov 2026
- **LIB-1** ✅ on `platform/web` **002bf02** (chuvadi-pdf **3.32.0**, Firefox): AES-256 PDFs written by pypdf with an unsigned `/P` (4294965240, 4294967292) open; the user-password one after "open-me"; the no-print permission is read correctly from the unsigned value (Print card: "This file's permissions don't allow printing.").
- Wrote `STAGING-VM-ASK.md` (V-1…V-7, 40-person load) and `MANUAL-SCRIPT.md` (M-1…M-4, G-12).
- Waiting for the Web head with Web portal UI ce805d1 + Foundation f88f9ef for WT-17, WT-03…WT-06 and the regression (incl. large Excel uploads, limits, cancel).

### Large Excel uploads — baseline on 002bf02 (Sheets 2.0.2, `ForUntrustedInput`: 256 MB/part, 1 GB total, 500:1, 20,000 entries, 1,048,576 rows), Firefox
Files from `tests/web-test/make_large_xlsx.py`.

| File | Result |
|---|---|
| big-100k.xlsx (100,000 rows × 6) | grid in **2,576 ms** |
| rows-1048576.xlsx (Excel's maximum rows) | grid in **3,245 ms**, worker ~586 MB |
| rows-1048577.xlsx (one row over) | refused in 1.9 s: "This Excel workbook is too large to open: it goes beyond what Chuvadi allows. It may be damaged." ✅ |
| entries-20001.xlsx | refused in 0.6 s, same plain sentence ✅ |
| ratio-600.xlsx (300 MB part) | refused in 0.3 s — but with **raw library text**: "Couldn't open this workbook: Decompressed size limit of 268435456 bytes exceeded for package part 'xl/worksheets/sheet1.xml' (declared 314573011)." ⚠️ |
| zip-bomb.xlsx (2 GB part) | refused in 0.6 s, the same raw text ⚠️ (on c38bd80 the same file got the plain "unpacks to more than 2,048 MB" sentence) |
| cancel-1m-x12.xlsx (565 MB part) | refused, raw text ⚠️ (`screenshots/v4-xlsx-part-limit-raw-text.png`) |
| **Cancel**: cancel-4x1m.xlsx (89 MB, 4 × 139 MB parts, within limits) | "Stop" shown at 12.3 s; opening ended **187 ms** after the click; no grid; the person carries on ✅ |

To re-run on the f88f9ef head (Sheets 2.0.4); the raw part-limit text becomes a bug if it is still there.

## Re-verification on `platform/web` @ **d183ea8** (10 Nov, 07:30–08:40 IST)
Foundation **f88f9ef** + Web portal UI **ce805d1**: chuvadi-pdf 3.32.0, Sheets **2.0.4**, pages off the Ui thread, memory relief.

- **Build from clean:** shared solution 0 warnings — Reader **233**, Hosting **77**, Mobile UI **16**, Web UI **41**; Web + Web.Tests 0 warnings, Web **166/166**; `check-package.sh` PASS; no third-party assemblies; Sheets 2.0.4 SHA-256 matches `PACKAGES-SHEETS-2.0.4.md`.
- **WT-03, WT-04, WT-06** ✅ 3 engines (WT-05 unchanged since its verification). Regression in the same run ✅: WT-02 (Chromium, Firefox), WT-08, WT-09, WT-10, Q-3, 3 engines.
- **LIB-1** ✅ still (unsigned `/P` files open; no-print honoured).
- **WT-17** ❌ still open — formats not applied (`fid.xlsx`, `fid-lo.xlsx`: 17/23, the six formatted numbers wrong as before). Word fidelity unchanged ✅ (`fid.docx` 14/14 exact).
- **Regression:** `flows.py` **10/10** × Chrome, Firefox, WebKit; the Web chat's `office_limits.py` **6/6** × Chrome, WebKit.

### Large Excel uploads, limits and Cancel (Sheets 2.0.4, Firefox and Chromium)
| File | Firefox | Chromium |
|---|---|---|
| big-100k.xlsx | grid 2,798 ms | grid 2,913 ms |
| rows-1048576.xlsx (max rows) | grid 4,305 ms | grid 3,498 ms |
| rows-1048577.xlsx | refused 2.0 s "too large to open…" ✅ | refused 2.1 s ✅ |
| entries-20001.xlsx | refused 0.4 s "too large…" ✅ | refused 0.3 s ✅ |
| ratio-600.xlsx (300 MB part) | refused 0.3 s — "damaged or isn't an Excel workbook" → **WT-18** | same |
| zip-bomb.xlsx (2 GB part) | refused 0.3 s — same wording → WT-18 | same |
| **Cancel** cancel-4x1m.xlsx (89 MB, within limits) | Stop at 12.8 s (upload time on this sandbox), opening ended **181 ms** after the click ✅ | Stop at 0.9 s, ended **40 ms** after ✅ |
After Cancel the person carries on; the next large sheet opens in the same worker. Raw library text from 002bf02 is gone ✅.

### Memory given back after close → WT-19
PDF heavy close ✅ (1,468 → 359 MB within 2 s). Excel close and cancelled Excel open ✗ (memory kept; details in BUGS WT-19).

## Security pass — page images by address (D-158), `platform/web` @ **78f7628** (10 Nov, 15:30–17:30 IST)
Build from clean: shared solution 0 warnings — Reader **247**, Hosting **82**, Mobile UI **16**, Web UI **41**; Web + Web.Tests 0 warnings, Web **171/171**; `check-package.sh` PASS.

`tests/web-test/page_image_sec.py` (gateway, Development sign-in) — **19/19 in Chromium, Firefox and WebKit**:
| Check | Result |
|---|---|
| Pages drawn as images are `/_chvd/pages/<32 hex>.png`; no `data:` images left | ✅ |
| Owner: 200 `image/png`; `Cache-Control` = `no-store, private` (both directives; order differs from the code, same meaning); `nosniff`; `Cross-Origin-Resource-Policy: same-origin`; no `Access-Control-*` | ✅ |
| Referrer: image requests carry no `Referer`; the page sends `Referrer-Policy: no-referrer` | ✅ |
| Another signed-in person → 404; signed-out (Development) → 404 | ✅ (Sangam mode: ❌ 302 → **WT-20**) |
| Owner's token with `Sec-Fetch-Site: cross-site` / `same-site`, a foreign `Origin`, `Origin: null` → 404; same-origin marks → 200 | ✅ |
| CORS preflight (`OPTIONS`, foreign Origin) → 405, no `Access-Control-Allow-*` | ✅ |
| Malformed: upper-case hex, 31/33 chars, `.PNG`, `.png.png`, no extension, `.jpg`, `../`, `%2e%2e`, `%2f`, `%5c`, all-zero, non-hex → 404; `%00` → 400 (Kestrel); never 5xx. Note: `<token>.png/` and `<token>.png?x=1` reach the owner's own image (harmless — owner check still applies) | ✅ |
| Tokens: 16 sampled, 128-bit lower-case hex, all distinct, one-bits 50.4 %, no shared 3-character prefix | ✅ |
| Closed document → every token 404 right after the tab closes | ✅ |

With **real Sangam rc.16** (gateway, short idle): owner with cookie 200; **the first sign-in's token under the same person's second sign-in → 404** ✅; the second sign-in's token 200; fetching the image every 2 s **does not** keep the session alive (ended at 40 s) ✅; expired session with its old cookie → **302** (WT-20); after back-channel sign-out → 302 with the token in `returnUrl` (WT-20). After session end the image is still held in the worker's memory (WT-21).
**Logs:** at the shipped levels (`Microsoft.AspNetCore: Warning`) no token appears in the gateway or worker logs ✅. (At `Information`, which my test portals use, ASP.NET's request lines include the path — an operator choice; keep production at Warning.)
**Pixel identity** (`page_image_pixels.py`, old build d183ea8 inline `data:` images vs new endpoint): `large-6.pdf` (6 large-format pages, 2708×2708 px) — **PNG bytes identical** on every page, Chromium and Firefox ✅. (The 5000×5000-image PDF is drawn as a vector page in both builds, so it doesn't use the endpoint.)
**Regression:** the Web chat's `page_images.py` 6/6 × Chrome, Firefox, WebKit; `flows.py` 10/10 × 3; `office_limits.py` 6/6 × Chrome, WebKit; `sangam_signin.py` 13/13 × 3; `verify_fixes.py` all green (WT-02 … WT-10, Q-3).

## Re-verification on `platform/web` @ **6be3c17** and **04cdd21** (10 Nov, 20:40 – 11 Nov 00:10 IST)
04cdd21 = WT-20/WT-21 fixes + Foundation patch 24 (Excel number formats D-161/D-162, CropBox D-160).

- **Build from clean (04cdd21):** shared solution 0 warnings — Reader **292** (+3 skipped: two `CropBoxTests`, one `XlsxDisplayTests` time-only — reason to be confirmed), Hosting **89**, Mobile UI **16**, Web UI **41**; Web + Web.Tests 0 warnings, Web **172/172**; `check-package.sh` PASS; no third-party assemblies.
- **WT-20** ✅ (Sangam mode, real Sangam rc.16): no cookie → 404; bogus cookie → 404; expired session's old cookie → 404 (and again 5 s later); after back-channel sign-out → 404, no `Location`. `/` still redirects to sign-in. Fetching an image every 2 s still doesn't keep a session alive (ended at 38 s of a 40 s limit).
- **WT-21** ✅ for the open tab: expiry (Development) — tokens 200 → 404 at once, worker 396 → 245 MB (3 of 3 Firefox runs; Chromium and WebKit too); Sign out (real Sangam, Chromium and Firefox) — token 404, worker 387 → 140 MB within 3 s. ❌ after a page reload → **WT-22**.
- **WT-17** ✅: `fid.xlsx` / `fid-lo.xlsx` 22/23 as Excel shows them — `12.50%`, `1,234.50`, `₹1,234.50`, `09-11-2026`, `007`, `1.00E-07`; hover text holds the stored value (`0.125`, `1234.5`, `46335`, `7`, `1E-07`); Chromium, Firefox, WebKit (`screenshots/v5-xlsx-formats-applied.png`). The 23rd: a **General** cell holding 3.14159265358979 shows `3.141592654` (what Excel's General shows) with the full value in the hover — data intact, but the Web build log says General cells keep the full value; to confirm against D-161. Text cells still 14/14 exact; Word 14/14 (LibreOffice's leading-space run still drawn).
- **WT-18, WT-19** unchanged (with Foundation / the library).
- **Finished from session 1:** **F-20** restart banner ✅ 3 engines — shown 11–13 s after the notice file is written ("The portal restarts for an update at 00:26 (in about 44 minutes). Download anything you want to keep…"), a later arrival sees it, gone 11–12 s after the file is removed. **S-12** ✅ Production with a disk data root refuses: "The portal won't start: Portal:DataRoot (/tmp/diskroot) is on ext4 mounted at /; working copies must be in RAM (tmpfs) — D-28." **F-4 Find** ✅ 3 engines (a phrase on page 7 → page 7). **F-18 tablet** ✅ rails 72 / 72 / 60 px at 1180×820 (Chromium, WebKit), no sideways scroll; at 820×1180 the View rail is not shown (left 72, Tools 72) — to confirm against the tablet frame.
- **Regression (04cdd21):** `flows.py` 10/10, `page_images.py` 7/7, `sangam_signin.py` 13/13, `expiry.py` 10/10 — each in Chrome, Firefox, WebKit; `office_limits.py` 6/6 Chrome, WebKit; my `page_image_sec.py` 19/19 × 3; `verify_fixes.py` all green × 3.
- **Note (Development only):** with Development sign-in, the account menu's "Sign out" goes to `/signout`, which answers 404 (the route exists only with Sangam). Not a production path; sign-out tests need Sangam.
