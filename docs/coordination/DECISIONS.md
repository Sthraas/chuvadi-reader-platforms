# Programme decision log

Arun handed the calls to the coordinator on 6 Nov 2026 (05:21 IST). Every decision below was taken only after the chat laid out the options with pros and cons. Items marked **Arun** need his own answer (ownership facts, money, accounts).

## 6 Nov 2026 — Arun
- Web: no per-user server storage this release; users managed by Sangam; never change Sangam (it handles auth); sharing not in this release; TLS — ask the Vault chat whether Pezhai can issue certificates.
- Everything else follows the design handout.
- Separate chats for the mobile app UI and the web portal UI.
- Coordinator takes the calls, always after pros and cons.

## 6 Nov 2026 — coordinator
| # | Decision | Chosen | Reason (short) |
|---|---|---|---|
| D-01 | Package source | Reader's committed `ci/packages` feed; re-packing only as a check | Byte-identical to what Windows ships |
| D-02 | File model (F-1 / A-02) | Working path + write-back (option C) | Core untouched; zero Windows change; one hook for Android, Web, sandboxed Mac |
| D-03 | Web files | Session-only encrypted working copies, deleted on sign-out/session end/expiry; Save = browser download | Follows "no storage" |
| D-04 | Contracts project (F-2) | New `ChuvadiReader.Platform` | Clean, one csproj line |
| D-05 | Service registration (F-3, A-05) | Shared `AddChuvadiReader` kit; Windows switches; set-equality test kept | One list for five hosts |
| D-06 | Printing (F-4, A-04, Mac) | **Vector only** (Arun's rule). Windows: keep WpfPrintService for now. Mac: OS print panel fed the PDF itself. Linux: PDF as-is to CUPS, raster only as fallback. Android: PrintManager with the PDF. Web: browser print | OS components allowed; no rasterised printing |
| D-07 | Web form factor & keys (F-5) | Follow the browser | Same design on small screens; ⌘ on Mac browsers |
| D-08 | `IClipboard` vs `IImageClipboard` (F-6) | Keep both | No extra Windows edit |
| D-09 | Preview host for UI chats (F-7) | Yes, dev-only, never shipped | UI chats can test before hosts exist |
| D-10 | Foundation Group A existing-file edits | Approved (incl. A9 label, A10/A11 bug fixes) | Windows output identical except listed items; Arun's six Windows checks kept for final review |
| D-11 | Bug fixes from Mac chat (F1 drop types, F2 state folder, F3 atomic settings write) | Approved, applied centrally by Foundation | Bug fixes benefiting every platform |
| D-12 | Pdf packages in Core (F4 / P-01) | Individual 3.31.1 packages instead of the umbrella | ~6.7 MB smaller; deprecated packages out |
| D-13 | Sheets 2.0.1 | Pending — ask the Reader chat first | Avoid diverging from the Reader's Core |
| D-14 | Docs | Stay 1.1.0 until docs-v2.0.0 | Package report |
| D-15 | Mac host | Separate `ChuvadiReader.Mac`; direct download, signed + notarised, not sandboxed; App Store later; Immersive = ⌃⌘F host-side; Xcode workload pin kept | Path model works; native conventions |
| D-16 | Android host | Separate `ChuvadiReader.Android`; no host CSS on Ui class names (look built in Ui by Mobile UI chat) | No silent drift |
| D-17 | Android icon | Android chat builds a draft SVG master from Brand Assets, flagged for Arun | Unblocks Play assets |


## 6 Nov 2026 05:39 — Arun's answers
- Domain: probably chuvadi.in. Bundle ID / app ID decided before release, on the final domain; placeholders until then.
- Publisher: Sthraas Intelligence Pvt Ltd. Google Play and Apple Developer accounts are created after the company is registered; until then unsigned/test builds only.
- E2E server: at the very end. Sangam client registration: when Sangam goes to production (test against a local Sangam meanwhile).
- App icon: coordinator approves the draft if it matches Brand Assets; Arun may change it before the final release.
- Mac test on a friend's Mac: once everything is ready.
- TLS: our own C# ACME client for Let's Encrypt (Pezhai has a private CA only, not production-proven yet).
- Merge plan (a): Foundation edits land in arunshivab/chuvadi-reader first (PR, Arun merges after Windows checks). **Concentrate on speed** — move fast, and startup performance is a priority in every code change.
- Sheets 2.0.1: the Reader chat does the move.
- Library: release order fonts 1.1.0 → markup 1.1.0 → docs 2.0.0 → layout tags; re-pin Layout.Pdf off 3.30.2; the package report's leans on items 3–16 accepted; log PDF-09 as open.

## 6 Nov 2026 — coordinator (cont.)
| # | Decision | Chosen |
|---|---|---|
| D-18 | Foundation Group B (write-back) | Approved |
| D-19 | Foundation Group C; gating | Approved; HIDE what a platform can never do; LOCK only library-gated items |
| D-20 | Web wording for device-only lines | "Processed on the Chuvadi server · encrypted · only you can see it. Your files are removed when you sign out." Status bar as the handout |
| D-21 | "Show in folder" on desktop | Wire it (it's in the handout's Document menu) |
| D-22 | Windows raster printing | Known existing gap; move to Chuvadi.Print vector XPS (rc.3) when released |
| D-23 | Mac menu bar command source | Foundation kit fills IAppCommands from ShellService |


## 6 Nov 2026 06:00 check-in — coordinator (from the options files on each branch)
Each decided on the chat's own pros and cons. Delivered to the chats at the next check-in.

### Web (`docs/web/DECISIONS-PENDING.md`)
| # | Item | Decision |
|---|---|---|
| D-24 | W-02 isolation | Per-person worker process behind our own Kestrel gateway (contains Pdf A/B to one person, no Core edits) |
| D-25 | W-03 TLS (doc outdated) | Our own C# ACME client for Let's Encrypt, auto-renew, hot reload — Arun agreed 05:39 |
| D-26 | W-05 hooks H0–H9 | Not applied separately: Foundation merges every MainLayout/existing-file hook (Web H0–H9, Web-UI, Mobile-UI) into ONE combined patch, checks desktop pixel-identical, then applies |
| D-27 | W-08 certificate signing on the portal | (a) off now; (c) Sangam's e-signature ceremony later |
| D-28 | W-09 working copies at rest | (b) tmpfs (RAM, size-limited) for working copies + (a) LUKS volume for anything that touches disk; (c) per-session app encryption later |
| D-29 | W-10 settings across sessions | (b) appearance settings only in the person's browser storage |
| D-30 | W-11 session expiry | 30 min idle, 8 h absolute; a warning 5 min before idle expiry offering to download open work |

### Web portal UI (`docs/web-ui/OPTIONS-FOR-COORDINATOR.md`)
| # | Item | Decision |
|---|---|---|
| D-31 | U-1 texts made untrue by no storage | Keep pitch and status "encrypted at rest" (true with D-28); change only promise 1 → "Files live only for your session, then are wiped" and promise 3 → "Sign out and your files are gone from the server" |
| D-32 | U-2 portal on narrow browsers | (a) reuse the Mobile UI phone/tablet components; chrome = form factor + portal additions when Kind == Web |
| D-33 | U-3 Sangam gate | (a) desktop component; hook deferred until a desktop Sangam client exists; keep the gating list as the handout |
| D-34 | U-4 sign-in form | (a) the Sangam ID is a login hint, no password field on our page (if Sangam supports login_hint; else report) |
| D-35 | U-5 account menu | Account settings → Sangam's own page; desktop-app URL is config (placeholder https://chuvadi.in/download); add `Unit` to IAccount (Foundation) for "· Records" |
| D-36 | U-6 theme toggle and version on the portal | (a) keep both |
| D-37 | U-7 server status dot | Yes, blue `server` class on the dot when ServerSide |
| D-38 | U-8 account card position | (a) one position |
| D-39 | F-1 WebKit 0.5 px dividers vanish | Bug fix approved in direction; Foundation proposes the exact CSS with a Windows pixel check, in the combined patch |

### Mobile app UI (`docs/mobile-ui/OPTIONS.md`)
| # | Item | Decision |
|---|---|---|
| D-40 | MU-1 phone shell hook | (a) `@if (Shell == Phone)` in MainLayout — via the combined patch (D-26) |
| D-41 | MU-2 / MU-3 / MU-4 | (a) CSS on data-shell; actions by Ctrl K command id; touch via mobile.js — real-device check on the Android emulator |
| D-42 | MU-5 pen draws, finger pans | (a) reader.js hook on pointerType — in the combined patch |
| D-43 | MU-6 tabs on phone | (a) tap the title → Tabs sheet |
| D-44 | MU-7 phone landscape | (b) icon-only 56 px bottom bar, 48 px app bar |
| D-45 | MU-8 phone Home/Library/Settings | Not designed: Mobile UI chat brings two layout options per screen with mock screenshots and pros/cons before building |
| D-46 | MU-9 | Protect FAB = Save redacted copy; add the small Bench desk-counter hook (combined patch) so the tablet counter shows desks |
| D-47 | MU-10 phone title | File name |
| D-48 | TabsService.RestoreAsync duplicate tabs | Bug fix approved — skip a saved path already open (combined patch) |
| D-49 | Android host fixes from Mobile UI | Android chat: link the scoped styles CSS, link mobile.css, remove host tablet CSS/traffic rule/safe-area padding/data-form-factor writer, register IAppLifecycle with BackRequested |

### Foundation (`docs/foundation/STARTUP.md`)
| # | Item | Decision |
|---|---|---|
| D-50 | S1 ReadyToRun publish for Windows | Yes (−80 ms, no code change). Same for every desktop host where supported |
| D-51 | S3 profile first render | Yes, on Arun's machine via measure-startup.ps1 -ReadyToRun at his Windows check |
| D-52 | S4 clock re-renders whole shell every second | Fix: render only the clock span (combined patch) |
| D-53 | S2 composite R2R / PGO | Measure after S1; decide on numbers |

## Blocked on Arun
- **PR to arunshivab/chuvadi-reader:** the Foundation branch `platform/foundation-pr` (PR text in `docs/foundation/PR-DESCRIPTION.md`) is ready in the private repo, but neither the chat nor the coordinator can push to your public repo (access blocked). You push it and open the PR, then merge after the six Windows checks.


## 6 Nov 2026 15:40 — coordinator (delivered to all seven chats)
| # | Item | Decision |
|---|---|---|
| D-54 | chuvadi-pdf 3.31.2 released (fixes Pdf A and Pdf B, signing, named-destination links, non-zero MediaBox rendering) | Every platform moves to 3.31.2. Foundation packs it from the unchanged tag v3.31.2 into ci/packages with SHA-256s, until Arun's own copies are in chuvadi-reader. Fonts stays 1.0.0 unless pros/cons say otherwise |
| D-55 | Pdf A / Pdf B web blockers | Cleared once Web runs on 3.31.2 |
| D-56 | Combined hook patch (D-26) scope | Also includes Mac Catalyst fixes (CertificateSignService.cs:117, PasswordService.cs:185 check IsMacCatalyst) and adding the Mobile UI / Web UI test projects to Platforms.slnx |
| D-57 | Mac print fidelity | Flatten forms/annotations before handing the PDF to the OS print panel (still vector); font-embedding library ask via coordinator |
| D-58 | Mac bundle size (519 MB) | Size breakdown + options with pros and cons first |
| D-59 | Android A-10 home greeting showing the Android user id | Show no name until the person sets one (prefer IAccount on Android, no Core edit) |
| D-60 | Web branch rebase push | --force-with-lease on platform/web approved (own branch) |

## Waiting for Arun's final check
- Mac bundle ID (provisional `in.sthraas.chuvadi.reader`) and Android application ID (placeholder `in.chuvadi.reader`): both permanent once released; depend on the domain and Play/Apple accounts Arun owns.
- Which Play developer account publishes (Sthraas or imagiQa).
- App icon master (draft to be reviewed).
- Six Windows checks after Foundation Group A (in `docs/foundation/HANDOFF.md`).
- Pdf 3.31.2 released 6 Nov: the server fixes A and B are in; Web clears that blocker once on 3.31.2.
- Library coordinator asks (Arun's files): the 8 MB CAD PDF for PDF-09; any file still showing corrupted uncropped pages after Scrub on 3.31.2.

## 6 Nov 2026 23:55 — coordinator (delivered to all chats)
| # | Item | Decision |
|---|---|---|
| D-61 | MU-8 phone screens | Off-document bar = 4a (Home · Library · Tabs · Settings); Home B; Library both views, opens per Default view; Settings A (section list) |
| D-62 | Android-found Mobile UI bugs | Fix swipe pointercancel, phone Fit page width, long-press pan; switch H-1/TouchSupport to IPlatformInfo (F-4) |
| D-63 | U-9 sign-in page | Only "Continue with Sangam" + desktop-app line (Sangam ignores login_hint); Sangam pre-fill = ask for Arun |
| D-64 | U-10 / U-11 | Account block at the foot; Web wording for Home lines in Foundation's second patch |
| D-65 | Web account unit | Request org.current scope |
| D-66 | Bug fixes F-2 (greeting full stop), F-3 (OpenDocumentService queue), L-8 (respect "no printing" everywhere) | Approved; Foundation second patch |
| D-67 | Linux L-5/L-6/L-7 | PDF as-is to CUPS; GTK dialog then Chuvadi.Print.Ipp; no single instance now (programme item for Arun) |
| D-68 | Kit fallback save folder; Chuvadi.Print/.Ipp rc.2 in ci/packages | Foundation adopts centrally |

## For Arun (new)
- Library asks to pass on: Mac L-1 (embed missing fonts, subset, ToUnicode) and L-2 (flatten using each annotation's Print flag) in `docs/mac/LIBRARY-ASKS.md`; Linux: release Chuvadi.Print.Pdf.Raster, a font inspector for the print router, IppJobTicket "printer default".
- Sangam ask (your call, Sangam rule): pre-fill the sign-in Identifier from login_hint.
- Single-instance app (open file as a new tab in the running app) — programme-wide behaviour change incl. Windows.
- Licence for the Linux package metadata (repo has no licence file).
- Delete branch `platform/linux-probe` (finished temporary branch; deletion blocked for the coordinator).

## 7 Nov 2026 00:55 — Arun
- GitHub access option A: Claude GitHub app on Arun's personal account for chuvadi-reader; chats push branches and open PRs, Arun merges.
- Sangam login_hint pre-fill: Arun takes a write-up to the Sangam chat himself.
- Single instance (tabbed) approved programme-wide.
- Licence: proprietary, final. Free for everyone, never open source.
- Check-ins every 30 minutes.

## 7 Nov 2026 01:00 — coordinator
| # | Item | Decision |
|---|---|---|
| D-69 | Single-instance design | Foundation designs an IAppInstance kit contract with per-host options (Windows pipe, Linux D-Bus/socket, Mac native, Android singleTask/OnNewIntent); must not slow first launch |
| D-70 | LICENSE + EULA | Foundation adds proprietary LICENSE and EULA draft (marked for Arun's legal review); all package metadata uses it |
| D-71 | Owner-password printing gap | Wait for chuvadi-pdf 3.32.0 PDF-16 |
| D-72 | Web worker isolation / VM size | (a) same service account for launch; 16 GB / 8 vCPU for ~40 concurrent; restarts at quiet hours with a banner |
| D-73 | Mac size option 2 (−111 MB, +0.3 s startup) | Rejected — startup priority; do option 1 now, option 3 when libraries are trim-annotated |
| D-74 | Phone Redact fit-width hook; Shelf landscape peek | Approved; keep |
| D-75 | Web UI phone account block; Portal status-bar spans; PortalLinks 2 args; CI Node 24 actions | Approved; Foundation's next combined patch / Web host |

## 7 Nov 2026 01:35 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-76 | Web sign-in page + 2-arg PortalLinks route | (a) Foundation carries them in its next combined patch (updating its preview/test copies); Web applies web-12a-ready after |
| D-77 | EULA in the app | Foundation adds the EULA as a Ui page; About › Licences row links it |
| D-78 | Home drop zone does nothing on portal/mobile | Foundation brings options (Ui drop → upload via platform layer vs hide/reword) |
| D-79 | U-13 portal terms wording | (a) plain "Terms of use" link; click-through/tick-box are Arun's legal call; /terms readable before sign-in |
| D-80 | Mobile UI H-8 (Reader re-render) | Into Foundation's combined patch, reusing the Reader's re-render helper |
| D-81 | Android host failures seen by Mobile UI | Android chat checks/fixes: .docx/.xlsx open (library-blocked if Layout), Share, Save as PDF, back on API 35 tablet, keyboard over Find, garbled typing |

## For Arun — legal (from the Foundation's LICENSE/EULA draft)
1. Copyright holder: packaging lists Dr. Arun Shiva B; for Sthraas to license Chuvadi it should own the code (an assignment from you to Sthraas).
2. LiPicons icons are © imagiQa with no licence: Sthraas needs written permission from imagiQa to ship them.
3. Governing-law city and legal contact for the EULA.
4. Keep the "not a medical device" clause in the EULA?
5. Web portal needs its own Terms of Use and a privacy notice (DPDP Act) — and whether sign-in implies acceptance (click-through/tick-box) or just a link.

## 7 Nov 2026 02:05 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-82 | Arun's legal answers relayed | Copyright Sthraas Intelligence Pvt Ltd everywhere (incl. LiPicons, via Arun's later assignment); Ahmedabad jurisdiction; keep medical-device clause; Foundation drafts EULA, portal Terms, DPDP Privacy Notice, cookie/storage notice, third-party/font notices, Play data-safety — all "DRAFT, counsel review" |
| D-83 | Single instance | W-A + L-A + F-1 (Foundation's recommendation); multi-file drop opens each in a tab |
| D-84 | .NET runtime notices | (a) host supplies one extra notices text shown on the Licences page |
| D-85 | Android Back closes card (P-06) | Into Foundation's combined patch |
| D-86 | Web next steps | /terms and /privacy before sign-in; apply web-12a-ready after Foundation; write TEST-PLAN.md |

## 7 Nov 2026 04:30 — Sheets 2.0.2 (relayed by Arun from the library coordinator)
Released: tag sheets-v2.0.2. Fixes: relationship targets with ./ or .. now open (as Excel does); a missing workbook or sheet part throws XlsxFormatException (was FileNotFoundException); a text cell with a missing or out-of-range shared-string index marks the file damaged (XlsxFormatException) instead of showing the index as text. Supersedes 2.0.1 as the Reader's target (package report section 3B); the 1.1.2 → 2.0.x breaking changes in that report still apply. Package list and SHA-256 are in the Sheets chat's project.

Options considered:
- (a) Platforms stay on what chuvadi-reader main pins (1.1.2 today) and pick up 2.0.2 when the Reader chat moves main and the Foundation rebases. Pros: no edit to an existing file (Core.csproj is Reader-owned); no second copy of the namespace and API migration; no merge clash with the Reader chat. Cons: platform Excel viewing keeps the 1.1.2 behaviour until then.
- (b) Foundation bumps Chuvadi.Sheets in Core.csproj inside its combined patch. Pros: platforms get the fixes now. Cons: edits a Reader-owned existing file; the 2.0 namespace change (Chuvadi.Sheets.Excel → Model) and Zip obsoletion need code changes in Core the Reader chat is also making; certain merge conflict.

| # | Item | Decision |
|---|---|---|
| D-87 | Sheets 2.0.2 | (a). The Reader chat should target **2.0.2, not 2.0.1** (Arun relays). Platforms follow chuvadi-reader main; the Foundation adds the 2.0.2 .nupkg and its SHA-256 to ci/packages when it rebases on that change. Linux, Mac and Web carry Core's pin today; Android has no separate pin. |

## 7 Nov 2026 04:55 check-in — coordinator (browser back; all seven chats read)
| # | Item | Decision |
|---|---|---|
| D-88 | Mobile UI: Home search box position; Settings one-line summaries | Yes to both (handout 4a / Settings mock is final). Pros: screens follow the handout. Cons: two small phone-only hooks into existing files (Dashboard, Settings). Exact diffs to Foundation's combined patch with desktop pixel-identical proof |
| D-89 | Home drop zone on portal and mobile (DROP-ZONE-OPTIONS.md) | **C**: A (InputFile overlay + IDroppedFiles seam) on the portal only, B wording where DropFiles is false (Android). Web host sets DropFiles=false until A lands. Pros: the portal gets the designed drag-and-drop and loses the "browser opens the PDF and leaves the app" trap; Android stops promising a drop. Cons: most work of the four (still small). A and D rejected: A alone leaves Android promising a drop; D leaves the trap |
| D-90 | Actions cost (Arun: about $18 in a day; repo made public 04:46 IST) | Recommended to Arun: make the repo private again, because ci/packages publishes the Chuvadi library DLLs (Chuvadi is proprietary). Awaiting his A/B. Either way: Foundation proposes a workflow patch — docs-only pushes run nothing, per-push matrix Linux only, Mac/Windows/Android-emulator jobs manual only, cancel-in-progress per branch. No Mac/Windows/Android runs until the coordinator confirms |
| D-91 | Foundation PR | Coordinator add_repo for arunshivab/chuvadi-reader with push now succeeds; Foundation retries the push of platform/foundation-pr and opens the PR (never merges) |
| D-92 | Linux | Build accepted as complete (107/107 UI steps x64 locally; ARM64 last green on 833cea3). Linux Test chat opened; platform/linux takes only fixes the Test chat reports. ARM64 rerun when CI is confirmed |

## 7 Nov 2026 05:15 — Arun on the public repo
| # | Item | Decision |
|---|---|---|
| D-93 | Repo visibility and CI (replaces the hold in D-90) | Arun: the Chuvadi library and Reader repos are already public; the working repo stays public until the work is complete, then goes private; ci/packages stays as is. CI runs on public-repo minutes again (confirmed: 23:36 UTC runs started on all runners). Hold lifted: Android round 3, Mac verification run, Linux ARM64 rerun may go. Foundation's workflow patch keeps only (a) docs-only pushes run nothing and (d) cancel-in-progress per branch, because they save time; (b) and (c) dropped. Pros: free minutes, no history rewrite. Cons: costs return when it goes private — revisit D-90 (b)/(c) then |

## 7 Nov 2026 05:50 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-94 | Mobile UI hooks H-5 to H-12 and the PhoneShell slot (1a27cd6) | All into Foundation's next combined patch. Pros: phone/tablet follow the handout; H8/H9/H-12 are bug fixes (H-12: no sample recent files or watched folder on a fresh platform install, so the first-run box shows). Cons: several existing-file edits in one patch, covered by desktop pixel-identical proof, 0 warnings and all tests. Full removal of the sample data stays with the Reader chat (Arun to relay) |
| D-95 | PR #11 | Green on a12b14e; Foundation updates it after the next patch is green; coordinator tells Arun when it's ready for his checks |
| D-96 | Tablet/phone first-run tip "Ctrl K finds any file" | Touch wording on Tablet and Phone, keyed on form factor (the Android host always reports a keyboard); Foundation proposes the exact text |
| D-97 | Web UI U-15: Terms and Privacy in the account menu | (a) a small footer line, kept in About › Licences too. Pros: least change to the designed menu. Cons: small text. (b) two menu rows add rows the handout doesn't have; (c) is hard to find |
| — | Linux | Bug: on GNOME's close-only button layout, minimise and maximise still show; Linux chat fixing (the button layout must be followed exactly) |
| — | Web | The 04:55 message didn't arrive; resent at 05:50 with D-86, D-89 and D-93 |

## 8 Nov 2026 18:40 check-in — coordinator (restart after the 7–8 Nov stoppage)
| # | Item | Decision |
|---|---|---|
| D-98 | Wording "encrypted at rest" (portal status bar) and "encrypted working area" (draft terms) | Change both to accurate wording. Under D-28 documents live in memory only (tmpfs), are never written to disk, and swap is encrypted, but memory itself isn't encrypted. Status bar: "processed on the server · kept in memory only · only you can see it" (Web portal UI). Draft Terms and Privacy: "kept in memory only, never written to disk" (Foundation's legal drafts; still DRAFT for counsel). Pros: truthful, safer under DPDP, matches what the build does. Cons: differs from the handout's text, which predates D-28 (the kickoff allowed a wording change with pros and cons) |
| D-99 | Mac Test chat | Opened. Tests on GitHub macOS runners (public repo, free); real-Mac items stay in REAL-MAC-CHECKS.md for the friend's Mac |
| D-100 | Web Test chat | Opened. The Web plan is built (D-86, D-89 done; 142/142, CI green on 31b063e); starts from docs/web/TEST-PLAN.md. B5/B6 (domain, E2E) stay last |
| — | Stoppage | 7 Nov ~06:00 to 8 Nov 18:12 IST: usage limit, then subscription paused; Arun paid. Restart staggered to avoid hitting the limit again; check-ins now every 15 minutes (Arun) |

## 8 Nov 2026 19:00 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-101 | Linux: live change of the desktop's button layout | B: a "chrome changed" contract event so the top bar redraws immediately; diff to Foundation's next combined patch. Pros: the layout is followed exactly the whole time the app is open. Cons: one more contract member. A (applied only at start) leaves wrong buttons until restart |
| D-102 | Printing a file opened with its owner password | Still refused on every platform; the Linux chat's library ask (allow owners to print) goes to Arun, because the library is his |
| — | Linux Test | BUGS.md pushed (bd3a3a6): B-01 to B-13 sent to the Linux chat to fix, each with a test |
| — | Android | Round 4 done (e34d237); round 5 started (Back closes cards, double-tap on API 35, WebView version) |
| — | PR #11 | Green at 03406f0 on Windows, Ubuntu and macOS; waiting for Arun's Windows checks |

## 8 Nov 2026 19:15 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-103 | Web UI U-16: 12a sign-in pitch says "encrypted at rest" | (a) "…processed on our server, kept in memory only, and visible only to you." Same untrue claim D-98 fixed. (b) drop the clause loses the privacy promise; (c) keep it is false |
| D-104 | Portal drop overlay | (b) show the handout's "Drop to open" state on the portal during a file drag, without the file-name line (browsers don't expose it during the drag). The handout is final. (a) invisible leaves the designed state out; (c) desktop belongs to the Reader chat's Windows host — noted for Arun |
| — | Seventh combined patch | Foundation takes Mobile UI H-13 (fit/zoom jump, API 35 sizing), Web UI H7 (D-98 status text), the D-104 overlay diff and the Linux D-101 event |
| — | Web Test chat | Opened 19:13 IST (db2f7f00) |

## 8 Nov 2026 19:30 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-105 | Android API 35 ships WebView 124; CSS zoom measured differently before 128 (blank area when zoomed) | (a) require WebView 128+: startup check plus a message to update Android System WebView. Pros: host-only, about 20 lines; real Android 15 devices update WebView through Play; no Windows pixel risk. Cons: an API 35 emulator stuck at 124 only shows the message. Try a Play system image first; otherwise API 36 covers phone and tablet. (b) explicit sizing: big shared-UI change with Windows risk. (c) two code paths kept for old WebViews |
| D-106 | Android P-07: Back steps through duplicate history entries | Bug fix: MainLayout navigates to the Reader only when it isn't already showing; into Foundation's combined patch |
| D-107 | Portal privacy line in PlatformText ("encrypted", D-20) | Changed to "kept in memory only" — D-98 supersedes D-20 because D-28 made it inaccurate |
| — | PR #11 | Foundation moves it once, when part 2 of the seventh patch lands, so Arun checks one head |
| — | Mac Test | Two likely Mac bugs under confirmation: next/previous tab bound to ⌘Tab (macOS app switcher), and Immersive labelled F11 while the Mac binding is ⌃⌘F |

## 8 Nov 2026 19:50 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-108 | PR #11 timing | Move PR #11 now to 9fbed93 (seventh patch part 2a, green on all 6) so Arun can start his Windows checks; D-101 (Linux live button layout) follows as part 2b in a later small update. Pros: Arun isn't kept waiting on a Linux-only change. Cons: one more small PR update. Windows stays pixel-identical, so his checks remain valid |
| D-109 | Web UI U-17: Home drop zone shows through the "Drop to open" wash | (b) while a drag is on, Home's zone hides its contents and keeps its frame. Handout panel unchanged, desktop untouched. (a) doubled text where most drops happen; (c) no overlay on Home is inconsistent with where the drop is caught |

## 8 Nov 2026 20:05 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-110 | Linux Test recommendations | Approved: B-12 GPU compositing off only when no GPU (first launch 2.9 s → 1.1 s); B-15 clear message and clean exit when WebKit's sandbox namespaces are blocked (never disable the sandbox); B-17 remove UseSystemResourceKeys; B-19 top-bar left cell aligned with the left bar, wordmark slides when buttons are on the left. Also bugs for Linux: B-14 (landscape printed at half size on portrait paper) and lintian 21 errors / 373 warnings |
| — | Linux Test results | Printing is vector (original PDF byte-for-byte to CUPS, zero images, even a 120,000-stroke A3); no-print files refused before CUPS; redaction removes text from extracted text and raw bytes; startup warm 1,255 ms / cold 1,538 ms median to real content |
| — | Routing | Shared Ui/Core bugs (among B-07..B-11, B-16, B-18) → Foundation combined patch; library bugs → compiled for Arun to send to the library coordinator |
| — | PR #11 | Moved to b1caddc (D-108), green on Windows, Ubuntu and macOS |
| — | Android | Round 6: API 36 phone and tablet fully green; D-105 update screen works on API 35; round 7 (API 35 only) started |

## 8 Nov 2026 20:22 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-111 | Rail heading: handout "TOOLS" vs the app's mode name (READ/MARK/ARRANGE) on every platform incl. Windows | Keep the mode name on all platforms for now (Windows is the reference; one shared design). Flagged to Arun so the Reader chat can switch Windows to "TOOLS"; every platform then follows automatically |
| D-112 | Save at the foot of the tablet Mark rail (12e) | Add on Tablet and Phone form factors only, as drawn; touch users need a visible Save (no Ctrl S). Desktop unchanged; desktop alignment flagged to Arun |
| D-113 | "More view options" on the tablet View rail (not in 12d) | Keep — the only route to text size and colour on a tablet |
| D-114 | Desk toolbar in tablet portrait (not in 12f) | Move the actions into each desk's ··· menu on touch devices: 12f as drawn, labels kept. Keeping the toolbar breaks 12f; icons only lose the labels |
| D-115 | Web UI branch push after a remote change | (b) merge and push normally, no force (nothing rewritten). No re-authoring or signing — commits are Arun's alone |
| D-116 | D-101 contract member | Foundation writes it itself (Linux is busy with bugs); Linux wires its GTK settings watcher to it |
| — | PR #11 description | A "Generated by Claude Code" footer was added by the tooling; every edit from a session puts it back. Arun deletes the last two lines by hand on GitHub |

## 8 Nov 2026 20:40 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-117 | Web Test O-1: Sangam slow (60 s wait) | (b) 10 s timeout for discovery and the token call; a clear answer within 10 s. Cons: a Sangam that is slow but working (10–60 s) fails sign-in |
| D-118 | Web Test O-2: Sangam down with discovery cached | (b) probe Sangam before redirecting (2 s, cached 30 s) so people see our message instead of the browser's error |
| D-119 | Web Test Q-3: Home "Storage map" / "Your shelves" on the portal (no storage) | (c) keep them with the "this session" wording if no layout change is needed, else (b) hide on Web. Keeps one Home design and stays honest |
| D-120 | Routing of shared Ui/Core bugs | WT-02 (Current page prints the next page — changes Windows output, correctly), WT-09, WT-10/B-11b, B-07, B-08b, B-10, B-16 → Foundation's combined patch with tests; Windows behaviour changes stated in PR #11 for Arun |
| D-121 | B-18 left bar at rest (208 px list vs the handout's 62 px icon rail) | A Windows design difference, like D-111: flagged to Arun for the Reader chat; platforms keep matching Windows meanwhile |
| — | Library list for Arun | B-08a Docs has no input limits (zip-bomb .docx → 4.5 GB, 10 min+); B-09a Sheets materialises to the sheet's extent (cell at XFD1048576 → 1.7 GB, never opens); B-11a chuvadi-pdf doesn't rebuild a broken xref (bad startxref); LIB-1 chuvadi-pdf rejects /P written as unsigned 32-bit (pypdf writes it); LIB-2 Sheets 1.1.2 can't open absolute relationship targets (openpyxl) — check 2.0.2; D-102 owner-password printing; the password API (open-password prompt) |

## 8 Nov 2026 20:58 check-in — coordinator
| # | Item | Decision |
|---|---|---|
| D-122 | Android Test chat | Opened (b4b95b1d). All four emulators green (API 36 phone 10/10 + 25/25, tablet 9/9 + 23/23; API 35 phone and tablet: the WebView update screen 4/4) |
| — | PR #11 | Eighth patch part 1 (H-14, U-17) joins part 2 (Mobile UI D-112/D-114 diffs plus D-120 shared bugs) before the PR moves — one head for Arun |
| — | Android open items for release | Final app ID on chuvadi.in; Play upload key; Docs 2.0 / Sheets 2.0.x / Layout updates; save-in-place (waits on shared write-back) |

## 9 Nov 2026 00:50 — coordinator (second usage-limit stop, ~20:45 IST 8 Nov)
| # | Item | Decision |
|---|---|---|
| D-123 | Linux B-22 keyboard focus style | A: one keyboard-only :focus-visible outline using the theme's accent token from tokens.css (no new colour; follows all five themes). Accessibility need the handout doesn't forbid. Changes Windows, so it goes through Foundation and PR #11 for Arun. B (engine defaults) looks different per platform and clashes with Palm and Indigo |
| D-124 | Running eleven chats at once hit the account's usage limit twice | Finish one platform at a time. Now: Foundation + Linux Test only (Linux is closest: build complete, most bugs fixed). Then Android + Android Test, then Web + Web Test (+ Web portal UI), then Mac + Mac Test. Pros: steady progress without stops; earliest first release (Linux). Cons: the other platforms wait |
| — | Library list addition | Chuvadi.Print's printer list ignores a remote CUPS server (prints through one show "No printers"); also print orientation automatic, cancel a long open |

## 9 Nov 2026 01:30 — Arun
| # | Item | Decision |
|---|---|---|
| D-125 | Run all chats in parallel (Arun, 01:26 IST) | Replaces D-124. All eleven chats resumed at 01:30 IST; the Mac chat was given Mac Test's M-01..M-12 (S1 M-03 crash on quit; S2 M-01 empty menu bar, M-02 files from macOS never open). If the usage limit stops chats again, the coordinator tells Arun at once and resumes as soon as it clears |

## 9 Nov 2026 01:55 — library coordinator's answers (relayed by Arun)
| # | Item | Decision |
|---|---|---|
| D-126 | Use the library features that already exist | Foundation (ninth patch): B-07 open-password prompt via PdfDocument.RequiresPassword / PdfOpenOptions.Password / PdfPasswordRequiredException.PasswordSupplied; "Try to repair" via PdfRepairer.Repair; Sheets open cancel via XlsxReaderOptions.CancellationToken (if Core's Sheets version has it). Linux: print orientation via PrintSettings.AutoRotate (unless the person chose one); remote CUPS via CupsQueues.List(serverUri) from client.conf ServerName / CUPS_SERVER, plus local browsing as now |
| — | Answers back to the library | Print: the app calls CupsQueues.List(cancellationToken) (localhost only). Desktops use local CUPS with network browsing, and offices may point at a separate server via client.conf / CUPS_SERVER; ask: List() honours client.conf and CUPS_SERVER by default, as lpstat does. Sheets extent: Core uses Workbook.Load with its own grid (not SheetsLayout); test files committed by Linux Test under docs/linux-test/fixtures/ |
| — | Pending Arun | Who moves Docs (1.1.0 → 1.2.0/2.0.0, for zip-bomb limits and cancel) and Sheets (1.1.2 → 2.0.2): Foundation inside PR #11, or the Reader chat (D-87). Layout.Pdf pin PR [3.31.2, 4.0) is in Arun's queue to merge |

| D-127 | Mac Test: how to time first render for the Windows comparison | A: measure on the test side (no app change, no existing file touched); the method is noted next to the numbers. B (a first-render mark in the Windows startup log) would change a Reader-owned file |

| D-128 | Foundation: RequiresPassword and PdfOpenOptions.Password | Keep RequiresPassword off the open path (measured: it doubles every PDF open; use it later for a Library lock badge). Keep OpenAsync(path, password, ct): it passes the password through the library without reading the whole file into memory. PR #11 moves to the ninth patch once it is green; the Docs/Sheets move comes as a later update |
| — | Linux Test re-verify | Shared fixes verified on e468d1a: password prompt (wrong vs right), zip-bomb .docx refused at once (287 MB steady, was 4.5 GB), a stuck open no longer blocks others, damaged-PDF message, read-only home, top bar with buttons on the left, accent focus ring, Tab order. B-08b Cancel to be tested with far-cell.xlsx. Remaining: B-18 (Arun), library B-08a/B-09a, CAD PDF and Windows timings (Arun), six real-machine checks |

| D-129 | Web Test O-3: a save that produces several files ("Split to folder") | A single .zip built with Chuvadi.Zip (Arun's library; processing goes through Chuvadi), not .NET's compression. Pros: one download; no browser multi-download prompt or Safari block. Cons: the person unzips |
| — | Mac | M-16 first (it blocks most Mac Test function and robustness cases), then M-02 (files from Finder) |
| — | Web portal UI | Q-3 (D-119 (c)) "this session" wording on Home's Storage map and shelves, now |

| D-130 | Linux Test B-24 (S2): a PDF that never delivers data blanks the Reader and blocks every later open | Shared open path, so into Foundation's next combined patch (a Linux-only patch would split the code). The fix keeps "Opening…" and Cancel visible during a stall, Cancel frees the slot, and later opens are never blocked; the test uses a stalled stream. B-08b accepted on the code for now; Cancel is re-verified together with B-24 |

| D-131 | Linux print orientation (AutoRotate) | A: keep the Linux step that fixed B-14. Chuvadi.Print's AutoRotate affects raster mode only; in document mode the ticket still says portrait, which caused B-14. B (raster mode) is rejected: it prints images, and Arun's rule is vector everywhere. Library ask: in document mode, honour AutoRotate by leaving orientation-requested out of the ticket |
| — | Foundation next patch | B-24 stall fix; Chuvadi.Zip into ci/packages from its latest released tag (for D-129); Web portal UI's Upload wording and Q-3 "this session" diffs |

| D-132 | Mac: keep a warnings-and-errors log in ~/Library/Logs/Chuvadi | Yes: about 1 MB, rotated, local only, never sent anywhere; no document contents or passwords; file names as extension plus a short hash. Pros: a failure on Arun's or a user's Mac can be diagnosed. Cons: a small local file. Mentioned in the privacy notice draft |

## 9 Nov 2026 03:40 — Arun
| # | Item | Decision |
|---|---|---|
| D-133 | B-18 / D-121 left bar | Arun: documents are mostly portrait, so there is always room; keep the Reader's wide labelled left rail with a collapse button (Arun has asked the Reader chat for it). Platforms follow the Reader's version through the shared Ui; B-18 closed as "by design" |
| D-134 | D-111 rail heading | Arun (confirmed 03:40): the tool rail heading says "TOOLS" as in the handout, on every platform. The Reader chat changes Windows (Arun relays); platforms inherit through the shared Ui |
| D-135 | D-112 Save on the Mark rail, desktop | Arun: yes. Save at the foot of the Mark rail on desktop too, as in the handout. The Reader chat adds it on Windows; Mobile UI's touch-only version merges into the shared one |

| D-136 | Who moves Docs and Sheets (item 2) | Arun: (a). Foundation moves Chuvadi.Docs 1.1.0 → 2.0.0 and Chuvadi.Sheets 1.1.2 → 2.0.2 inside PR #11, including the Core code changes (namespace rename, old zip API retired), packs both from their release tags into ci/packages with SHA-256s, and wires Docs limits (MaxPartBytes ~20 MB, MaxTotalUncompressedBytes ~64 MB, timed token also passed to Paragraphs etc.) and the Sheets XlsxReaderOptions.CancellationToken into open/Cancel. The Reader chat must not make the same change (Arun relays); it picks this up when PR #11 merges. Replaces D-87 |

| — | Mobile UI: touch tap areas on the shelf | Yes: every touch control gets at least a 44 px hit area (D-37), visible size unchanged; desktop unchanged |
| — | Mac | M fixes done (c6d7705); Mac Test told to re-verify and run the blocked cases |

| — | D-136 landed | Foundation 1016987 (green on 6): Docs 2.0.0 + Sheets 2.0.2 + Chuvadi.Zip 1.0.0 from release tags; library limits and Cancel (60 s, Stop, close tab); Core's own zip-bomb check retired; independent data check (XML/openpyxl ground truth): old libraries 18 values wrong, new 0 wrong (all 1,153 cells of a 200-row sheet); whitespace preserved on screen. PR #11 at 063659e (patches 1–11), green; footer re-added by the tooling |
| D-137 | Word part limits | Desktop and mobile: 100 MB per part, 400 MB total (people open their own files; a scanned/medical Word file with one big picture is realistic). Web portal: keep 20 MB / 64 MB (shared server). Keyed on IPlatformInfo.ServerSide; both pinned in tests |
| D-138 | Word list markers from paragraph styles | Fix now with Docs 2.0's GetListLabels() — missing bullets are a fidelity bug |

## 9 Nov 2026 05:45 — library releases (relayed by Arun)
| # | Item | Decision |
|---|---|---|
| D-139 | Libraries released and verified: chuvadi-pdf 3.32.0 (signed tag v3.32.0, 34 packages + SHA256SUMS), Markup 1.1.0, Docs 2.0.0 + Docs.Conversion 2.0.0 (docs-v2.0.0), Layout 0.1.0 + Layout.Fonts/.Docs/.Sheets/.Markup/.Documents/.Pdf (Layout.Pdf → Pdf [3.31.2, 4.0)), Sheets 2.0.2 | Foundation takes them all from the GitHub releases, verified against SHA256SUMS; wires Word/Excel page view, print and Save as PDF through Layout; owner-password printing via EncryptionInfo.OpenedWith/EffectiveFlags (closes D-102); LIB-1 (unsigned /P) test. Layout limits: portal LayoutLimits.ForUntrustedInput() (50 MB source, 256 MB layout); desktop/mobile untrusted preset with 100 MB source and 512 MB layout (keyed on ServerSide). Item 3 (Layout.Pdf pin) closed — released |
| — | Known gaps / coming | 18 KB .docx with 2 million empty paragraphs (1.1 GB) passes byte limits → Docs 2.1.0 element cap; Pdf 3.32.1 RepairIfDamaged; Layout builds sheet pages only when asked (huge extents); Print rc.4 auto-rotate in document mode (D-131 ask); Sheets 2.0.3 DataTable header fix |

| D-140 | Android Test AT-03 (S1): Release build crashes at every launch (trimming strips seam-default constructors registered via untyped tables) | (a) annotate the tables in Hosting and turn on the trim analyser for Hosting/Platform; CI builds and launches trimmed Release (Android, Linux; Mac to check). (b) drop IsTrimmable bloats the app; (c) rooting in the Android host only hides it per platform |
| — | Android Test routing | AT-02, AT-07, AT-08 → Android; AT-04, AT-05, AT-06, AT-09 → Mobile UI; AT-01 (MAUI ships AndroidX, Material, Kotlin, Tink, Glide, Gson — not in the notices; Play data-safety draft says Chuvadi + Microsoft only) → Arun (no-externals rule) |

## 9 Nov 2026 06:10 — Arun
| # | Item | Decision |
|---|---|---|
| D-141 | PR #11 | Arun checked Windows and said "merge this". Merged by the coordinator into arunshivab/chuvadi-reader main at 2b8899d (merge commit, no attribution lines). The tooling re-adds the "Generated by Claude Code" footer to the PR description on every edit, so it remains on the closed PR's description only (not in any commit) |
| D-142 | Windows bugs from Arun's checks (logged for later, retest with Foundation) | W-01: title-bar drag and double-click (maximise) work only on the Chuvadi logo area, not the empty centre of the top bar. W-02: dragging a file into the app window does nothing. Both go to Foundation's list; the next update to main comes as a new PR |
| D-143 | Android AT-01: libraries MAUI bundles (AndroidX, Material, Kotlin, Tink, Glide, Gson) | Arun: accept what MAUI must bundle. List each with its licence and holder in the third-party notices, and correct the Play data-safety draft |

| D-144 | PR authorship / "with Claude" badge on PRs opened via the Claude app | Arun (06:23 IST): continue as now for the time being; revisit later. The badge on PR #11 is GitHub metadata and can't be removed; the merge commit is authored by Arun with no attribution |

| D-145 | Next PR and Layout | Open the next PR now without Layout (chuvadi-pdf 3.32.0, AT-03 Android Release crash fix + trimmed-launch CI, W-01 title-bar drag fix, W-02 WebView2 file-drop fix, D-143 notices, Mobile UI H-17..H-19). Layout: A — wait for a published Layout.Pdf release and SHA256SUMS for the docs/markup/layout releases (Foundation found Layout.Pdf has no release and the monorepo releases publish no checksums), rather than checking against tags ourselves |
| — | Mobile UI | Document ▾ in Arrange stays touch-only (Windows layout is the Reader chat's call); three touch-only size changes approved (Settings On/Off ≥44 px, tablet pager +12 px, docked Shelf icons on their own line) |

| D-146 | Android AT-07 / P-08: tabs and recents labelled with the app's private cache path | (a) a shared IPathLabels seam: desktops keep the real path and tooltip, Android shows the file name and its source. (b) file name only everywhere loses Windows' tooltip and leaves Android's Library paths wrong; (c) readable private paths still mean nothing to TalkBack. The AT-03 trimming fix must cover this default too |

| D-147 | Linux B-26: Excel cells show raw values (D-136) vs Excel's display text | B now: raw value as the file holds it (Arun's data-integrity rule; D-136 tests). A (display text, exact value on hover) proposed to Arun once Sheets formats dates in the culture's order (format 14 shows 03-15-23 in en-IN; Excel shows 15-03-2023) |
| — | Library list additions | Sheets: built-in date format 14 and other locale-dependent dates use month-first in en-IN; B-27: the 7.9 MB CAD PDF takes 3–4 s to open and memory grows to 1.6 GB over 5 pages (profile in docs/linux-test, numbers only) |
| — | Android Test | API 35 = update-screen test only, API 36 = Reader checks (c); "same file opened twice" to be compared with Windows' shared router |

## D-148 — Mac Test priorities and M-20 to M-22 (9 Nov 2026, coordinator)
M-17 and M-18 (S1) are fixed first, then M-19. M-22: add a printer-only local-network usage description plus a line in the privacy notice (Mac Test's recommendation; asking with generic wording, or hiding network printers, are both worse). M-21: Esc leaves Immersive on every platform; if Windows doesn't do it either, it's a shared Foundation bug. M-20 (heavy vector page) needs a Windows comparison and joins B-27 on Arun's list.

## D-149 — Android Test routing (9 Nov 2026, coordinator)
AT-10 (Find box loses typed characters) and AT-13 (heavy image page sometimes never paints) go to Foundation as shared Ui; AT-13 moves to the library list if the cause is the renderer. AT-11 (tabs lost on the phone after a background kill) goes to Android first, as host process-death restore, and to Foundation only if a Ui session-restore hook is needed.

## D-150 — Tablet Save pin: option C (9 Nov 2026, coordinator)
Both Save buttons are pinned together at the foot of the Mark rail, on touch only; desktop is untouched. A (remove the pin) hides both buttons on a landscape tablet, where there is no Ctrl+S. B (current pin) still hides plain Save. C costs a band of about two buttons' height and is easy to remove later.

## D-151 — H-20: TOOLS heading on every rail, with an accessible mode label (9 Nov 2026, coordinator)
Every tools rail shows the heading TOOLS, as D-134 says. The rail component takes a separate accessible label, so screen readers still announce READ, MARK, PROTECT and so on; otherwise the change would make accessibility worse.

## D-152 — AT-13 heavy image page: render off the UI thread (9 Nov 2026, coordinator)
The fix for pages left blank after a reopen is in the thirteenth patch. The remaining 4 s UI freeze on a 6000×6000 image is fixed properly with A: render off the UI thread, one render at a time per document, with a proof and a guard test (as B-24 did for opens), in the fourteenth patch. B (wait for the Release retest) leaves the freeze in place. C (the library decodes big images at display resolution) goes on Arun's library list as well.

## D-153 — M-21 is Mac-only (9 Nov 2026, coordinator)
On the Reader's main branch, `Reader.razor` `OnEscape` closes Measure, the card, the pages drawer, Find and the drawer, then leaves Immersive (`_reading = false; SetImmersive(false)`); `reader.js` sends Escape to it. So Esc leaves Immersive on Windows, and M-21 goes to the Mac chat (Esc probably not reaching the WebView on Catalyst). Linux re-verifies on the fourteenth patch before Arun's push, since rendering moved off the Ui thread (D-152).

## D-154 — M-18 re-scoped: recover from a WebContent crash (10 Nov 2026, coordinator)
Mac Test found that a real mouse click on Settings › Appearance works on macOS 26. The crash comes from a press through Accessibility, as VoiceOver and Voice Control users would make it, which kills Apple's WebContent process. M-18 drops from S1 to S2 and stays a bug. The Mac app handles WebContent termination by reloading back to the same screen, with a plain message and a chuvadi.log entry; it avoids the trigger if it can; and Apple gets a Feedback report.

## D-155 — Chuvadi.Sheets 2.0.4 and Layout (10 Nov 2026, coordinator; library news via Arun)
Foundation takes Sheets 2.0.4 directly, skipping 2.0.3: tag sheets-v2.0.4 on 9b8110b, asset Chuvadi.Sheets.2.0.4.nupkg, SHA-256 9B777E9518494A0531E25742C1F3FB7F8633DD9DABF44FA083CC44D0DD345D90. It names DataTable columns as Excel does and keeps the 2.0.1 API. The portal uses XlsxReaderOptions.ForUntrustedInput() plus a CancellationToken. Breaking changes from 1.1.2 are in the library's package list (namespace Chuvadi.Sheets.Model, XlsxFormatException, streams left open, spin-count cap, formula and 1904 fixes). Pictures, charts, macros, pivots and some extended styles are lost on load and save, so wherever the app writes an xlsx back it warns before overwriting. Exact-data tests stay. Layout: the library says Layout 0.1.0 and its companions (incl. Layout.Sheets, Layout.Pdf → Pdf [3.31.2, 4.0)) are released. Foundation checks each for a release asset with a checksum (D-145) before starting page view, print and Save as PDF through Layout (D-139 limits); any missing checksum goes to Arun.

## D-156 — Memory relief: a second heavy close waits instead of being dropped (10 Nov 2026, coordinator)
Linux's proposal (docs/linux/PROPOSAL-memory-relief-defer-10nov.md), option A: a heavy close inside the 30 s gap waits for the relief, so every heavy close gives memory back, at most 30 s late, and the spacing that protects a shared server stays. B (drop, as now) keeps the second drawing's memory until the app closes; C (no gap on desktop) adds a host-specific rule. With it: Foundation's eighteenth patch also takes Linux Test B-30 (real CAD: managed heap still 680 MB after a forced collection, so a reference is kept after close) and B-29 (cancel a closed tab's raster pass mid-sheet). Linux fixes its UI test B-28 (the loading icon counted as a drawn page). B-27 draw time stays a library item (PaintStrokeOp: 6–13 s per CAD sheet against ~1 s in Poppler). Linux is not final-ready until these are re-verified.

## D-157 — All chats restarted (10 Nov 2026, Arun, 07:23 IST)
Arun: "Please restart all of them... We need to finish all of them." The partial hold from 9 Nov 21:00 IST ends. Android, Android Test, Web and Mobile UI were restarted with fresh messages (their last turns had been stopped by the usage limit), and Web Test and Web portal UI were given their next steps. Foundation, Linux, Linux Test, Mac and Mac Test kept going. Check-ins: Arun now works from the Claude in Chrome side panel, so the browser can be used only in turns he starts. Scheduled check-ins follow the repos and CI; a full round of every chat happens on each message from Arun.

## D-158 — Page images: serve them from memory (B), after the finalizer-wait fix (10 Nov 2026, coordinator)
Foundation's table (10 Nov). A, keeping the page images as strings, is low risk, but every heavy page stays a huge string, and on the portal each one is a 39 MB SignalR message per user. B serves each page image from memory under an unguessable token that is freed at close. On WPF, Mac, Linux and Android this is one shared in-process file provider using each host's file-provider hook, with no localhost server and no new dependency. On the portal it is a same-origin endpoint tied to the signed-in user's session (private, no-store, 404 for anyone else or an expired token). B gives smaller memory, faster heavy raster pages and no huge strings; vector pages don't change. Decision: the three-line finalizer-wait fix first (twentieth patch, so Linux can turn on the 36c memory assertion), then B (twenty-first patch), with PixelProof showing raster pages pixel-identical and a Web Test security pass on the portal endpoint before it ships.

## D-159 — PR #12 merged; Windows retests later; the Windows Reader chat joins the programme (10 Nov 2026, Arun, 08:33 IST)
Arun: "W-01 and 02 can be tested later... Merge PR 12... Startup timings also be tested later... Keep them open." PR #12 was merged at 255aee2 (merge commit, clean message), bringing Foundation patches 12 to 21 to the Reader's main. W-01, W-02 and the Windows startup timings stay open for Arun to test later. Arun also asked that the coordinator coordinate the Windows Reader chat (7f7ff1ed…), because every app must look the same and have the same features. So Windows is now a programme platform: its design and features changes are kept in step with the shared Ui and the other hosts, and Windows bugs from the platform Test chats go to it. The programme has 5 apps: Windows, Mac, Linux, Android (mobile; there is no iOS app) and Web, with 12 chats.

## D-160 — CropBox default from chuvadi-pdf 3.32.0 (10 Nov 2026, coordinator)
The Windows Reader chat raised it: 3.32.0 shows the CropBox by default, where the Reader showed the MediaBox, so pages with bleed or scans look trimmed. That matches Acrobat and is more correct. Decision: accept the new default on every platform with one shared setting, but first send Arun before-and-after screenshots of a few files where the boxes differ. The Reader chat's 3.32.0 un-grey work (certificate signing, password permissions, owner remove-password, outline and link jumps, layers, viewports) is one PR on main, and Arun sees the visible-signature design before it is built.

## D-161 — Show what the file holds: Excel number formats 100% (10 Nov 2026, Arun, 09:26 IST; replaces D-147)
Arun: "data integrity rule is simple... show what the file holds... the format is also in the file... All cells should follow the format... 100%... definitely." D-147 read the data-integrity rule as "raw value only". That was wrong, because the number format is part of the file. Every Excel cell is now shown as its format says (currency, separators, decimals, percentages, dates, times, custom and conditional sections) through Chuvadi.Sheets' Cell.GetDisplayText, on all five apps. The stored value is never changed: copy, export and search work on it, and it shows on hover or selection. Locale-dependent built-ins (format 14) use the system culture, as Excel does. If the library gets them wrong, that is a library bug pushed as urgent, with no app-side workaround. The same rule revises D-160: the CropBox is in the file, so the apps follow it straight away, with no screenshots step. Foundation audits every other place where an app shows something other than what the file holds.

## D-162 — Excel General cells keep every digit; formatted cells follow their format (10 Nov 2026, Arun, 15:38 IST)
Web found that Excel's text for cells with no number format (General) shortens numbers (0.333333333333333 → 0.333333333, 1234567890123 → 1.23457E+12). Arun chose the coordinator's lean (b): every cell that has a number format is shown exactly as its format says (D-161: currency, separators, decimals, percentages, dates, times, custom sections), and General cells show the full value they hold, so nothing the file holds is hidden. The stored value is always on hover or selection. 1904-system dates showing 01-01-04 are a Sheets library bug (Sheets 2.0.5 brings a 1900-dates fix; the 1904 case goes on the library list). WT-17 is closed with this; WT-18 goes to the library list and WT-19 (Excel/Word memory relief) to Foundation.

## Blocker for Arun
- GitHub Actions on Sthraas stopped ~20:10 UTC 6 Nov: "recent account payments have failed or your spending limit needs to be increased". Options: pay/raise limit, make the working repo public (free minutes), or move. **Update 04:46 IST:** Arun made it public; coordinator asked him to revert to private (library DLLs in ci/packages) and cut minutes (D-90).
