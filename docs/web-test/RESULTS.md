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
