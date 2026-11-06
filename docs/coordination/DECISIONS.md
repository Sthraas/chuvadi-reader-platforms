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

## Waiting for Arun's final check
- Mac bundle ID (provisional `in.sthraas.chuvadi.reader`) and Android application ID (placeholder `in.chuvadi.reader`): both permanent once released; depend on the domain and Play/Apple accounts Arun owns.
- Which Play developer account publishes (Sthraas or imagiQa).
- App icon master (draft to be reviewed).
- Six Windows checks after Foundation Group A (in `docs/foundation/HANDOFF.md`).
- Library decisions already taken by Arun: Pdf 3.31.2 (server fixes A and B) — the Web portal goes to production only after it.
