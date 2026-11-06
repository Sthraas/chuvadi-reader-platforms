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

## Waiting for Arun's final check
- Mac bundle ID (provisional `in.sthraas.chuvadi.reader`) and Android application ID (placeholder `in.chuvadi.reader`): both permanent once released; depend on the domain and Play/Apple accounts Arun owns.
- Which Play developer account publishes (Sthraas or imagiQa).
- App icon master (draft to be reviewed).
- Six Windows checks after Foundation Group A (in `docs/foundation/HANDOFF.md`).
- Library decisions already taken by Arun: Pdf 3.31.2 (server fixes A and B) — the Web portal goes to production only after it.
