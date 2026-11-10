# Linux Test — bugs

Found on `platform/linux` **eb65770** (later items on db28319); **Linux fixes re-verified on f3d5978 (9 Nov)**. Original build: (725c1a9 differs only in `BUILD-LOG.md`).
Sandbox: Ubuntu 24.04 x64, 2 vCPU, no GPU, Xvfb + mutter; clean-install checks in Docker `ubuntu:24.04` / `ubuntu:26.04`.
Severity: **S1** crash/data loss/security · **S2** feature broken · **S3** wrong but usable · **S4** cosmetic.
Owner: **Linux** = Linux chat · **Shared** = existing Ui/Core/Hosting code (Reader chat / Foundation; affects every platform) · **Library** = Chuvadi library ask.
Every bug gets fixed; I re-verify on the fixing commit and mark it here.

| ID | Sev | Owner | Title | Status |
|---|---|---|---|---|
| B-01 | S3 | Linux | `.deb` fails lintian: 21 errors, 373 warnings | **verified fixed f3d5978** — lintian `--pedantic` 0 tags (SC + FD); modes 0644/0755; overrides only on Microsoft binaries (note: the `spelling-error-in-binary *` and `lib*.so` globs also cover our own files — narrow them) |
| B-02 | S2 (legal) | Linux + Shared | Copyright file claims third-party OFL fonts for Sthraas; OFL texts not shipped | **verified fixed** — Linux stanzas f3d5978; `OFL.txt` next to `fonts/google/` and `lipi-sans/` e468d1a |
| B-03 | S3 (security) | Shared | `nuget.config` has no package source mapping (dependency-confusion risk) | **verified fixed e468d1a** (Foundation 8th patch) — `packageSourceMapping`: Chuvadi.\*/LiPicons.\* → local only; restore from an empty cache OK |
| B-04 | S2 | Linux | Several files on the command line / `%F` open only the first | **verified fixed f3d5978** — 3 files on the CLI → 3 tabs |
| B-05 | S2 | Linux | Single instance missing: a second launch opens a second window (Foundation contract + router already on `platform/foundation`) | **verified fixed f3d5978** — X11: 2nd launch exits 0, files arrive as tabs, one window; Wayland (mutter): hand-over 0.1 s, launcher token used via `xdg_activation_v1.activate`, no 2nd window |
| B-06 | S2 | Linux | Window drop of several files opens only the first (**confirmed live** on db28319 with a real drag) | **verified fixed f3d5978** — real 2-file drag (GTK 4 file list) → 2 tabs |
| B-07 | S2 | **shared Ui/Core** | Password-protected PDF can't be opened: no password prompt | **verified fixed e468d1a** (Foundation 8th patch) — password card; wrong → "That password doesn't open this file."; right → page; password in memory only, nothing in `/tmp` |
| B-08a | S1 | **library** | Zip-bomb `.docx` → 4.5 GB RAM, 10 min+: Chuvadi.Docs has no input limits | open — library (Chuvadi.Docs limits); app-side guard now refuses at once: "too large to open: its contents unpack to more than 1,024 MB", RSS flat ~287 MB |
| B-08b | S2 | **shared Ui/Core** | "Opening…" has no cancel and no timeout (B-08a, B-09a) | **verified fixed 7595ef3** — stalled `.pdf`/`.xlsx`/`.docx`: Cancel at 10.0–10.1 s, closes the tab; next open works |
| B-09a | S1 | **library** | `.xlsx` with a cell at XFD1048576 → 1.7 GB, never opens: Chuvadi.Sheets materialises to the sheet's extent | open — library (layout of the full range); **app side fixed e468d1a**: far-cell opens as a grid in ~2 s, RSS ~370 MB |
| B-10 | S2 | **shared Ui/Core** | One stuck open silently blocks every later open (no tab, no message) | **verified fixed e468d1a** (Foundation 8th patch) — five-pages opens within ~10 s while far-cell loads |
| B-11a | S3 | **library** | Damaged PDF (bad `startxref` offset) not repaired — chuvadi-pdf needs xref rebuild | open — library (chuvadi-pdf) |
| B-11b | S3 | **shared Ui/Core** | Raw parser text shown to the user instead of the handout's damaged-file message | **verified fixed e468d1a** (Foundation 8th patch) — "This PDF is damaged · Chuvadi couldn't read this file…" |
| B-12 | S3 (perf) | Linux | First launch per user on a GPU-less machine: ~1.7 s of blank window (WebKit GL compositing) | **verified fixed f3d5978** — new user's first launch 2,934 → 1,089 ms median (worst 1,527); warm 1,255 → 1,016 ms |
| B-13 | S4 | Linux | Stray XML doc files shipped in `/usr/lib/chuvadi-reader` | **verified fixed f3d5978** — no XML doc files shipped |
| B-14 | S3 | Linux | Landscape pages print shrunk onto portrait paper (orientation forced to portrait) | **verified fixed f3d5978** — landscape page printed with `/Rotate 90`, ink 92 % × 89 % (was ~½ size); source still byte-identical to CUPS, 0 images |
| B-15 | S3 | Linux | No user namespaces → app aborts with a GLib ERROR, no message | **verified fixed f3d5978** — Docker without namespaces: "Chuvadi can't start on this computer" dialog with reason and fix; Close → exit code 2, no abort |
| B-16 | S2 | **shared Ui/Core** | Read-only home → unhandled exception at startup, no window | **verified fixed** — Linux wrapper f3d5978 + Core guards e468d1a: read-only home starts and opens the file |
| B-17 | S3 | Linux | **D-110: option A** — `UseSystemResourceKeys=true` → users see resource keys (`UnauthorizedAccess_IODenied_Path`, `EOCDNotFound`) instead of messages | **verified fixed f3d5978; WT-10 wording verified faffa10** — unreadable PDF: "Chuvadi couldn't read this file. It may be open in another app, or you may not have permission…" + collapsed Details (its .NET text is real since keys are gone; expanded by the Linux chat's test 34d) |
| B-18 | S3 (design) | **shared Ui/Core** | Left bar at rest is the expanded 208 px labelled list; handout: 62 px icon rail, labels on hover | **by design (D-133)** — wide labelled rail stays; collapse button coming from the Reader chat → check on Linux when it lands. (faffa10's existing "‹ Collapse" already works on Linux: 208 → 62 px, "Expand the side bar" → 208 px) |
| B-19 | S4 | Linux | **D-110: option A** — Buttons on the left: top-bar brand cell widens past the left bar; divider no longer lines up (f7d0034) | **verified fixed e468d1a** (Foundation 8th patch) — buttons left: top-left cell stays 210 px, in line with the left bar |
| B-20 | S4 | Linux | No printer / CUPS down: empty print dialog, no explanation | **verified fixed f3d5978** — CUPS stopped: no empty dialog; toast "Chuvadi can't reach this computer's printing service (CUPS)… Settings › Printers" |
| B-21 | S3 | Linux | Show in folder: 5 s D-Bus timeout → `xdg-open` fallback → two file-manager windows | **verified fixed f3d5978** — cold Nautilus: one window; `xdg-open` fallback never called (logging stub) |
| B-22 | S4 | shared Ui/Core | No designed keyboard-focus style: each engine draws its own (GTK blue on Linux) | **verified fixed e468d1a** (Foundation 8th patch) — focus ring 2 px solid in the theme accent (#8a3a1c in light) |
| B-23 | S4 | shared Ui/Core | Tab order starts with one "Send page N to a desk" button per page | **verified fixed e468d1a** (Foundation 8th patch) — Tab starts on the current page's strip (rotate, send, snapshot, bookmark), not one button per page |
| B-24 | S2 | **shared Ui/Core** | A stalled read (hung network share) shows a blank Reader with no "Opening…" or Cancel, and blocks every later open | **verified fixed 7595ef3** (13th patch) — stalled `.pdf`/`.xlsx`/`.docx`: "Opening…" at 0.3–0.9 s, Cancel at 10 s, Cancel closes the tab, later opens never blocked · re-verified 64c9c16 · 8dcf4d8 · d918161 · bf60da9 |
| B-25 | S4 | **shared Ui/Core** | Excel viewer errors still use the old one-line wording (no WT-10 sentence + Details) | **verified fixed 7595ef3** — Excel "This file couldn't be read as an Excel workbook.", Word "…as a Word document.", damaged PDF "This PDF is damaged…", each with Details · re-verified 64c9c16 · 8dcf4d8 · d918161 · bf60da9 |
| B-26 | S3 | **shared Ui/Core** | Excel number formats not applied: `"₹"#,##0.00` shows `1234.5`, `0.00%` shows `0.125` (values unaltered) — Sheets 2.0.2 now has `Cell.GetDisplayText` | **deferred by decision (D-147)** — raw stored value is the decided behaviour for now (Arun's data-integrity rule); option A (formatted display text, exact value on hover) is a later improvement, with Arun |
| B-27 | S3 (perf) | **library + shared Ui/Core** | Large vector CAD PDF (5 × A1, ~1.44 M path ops): ~3–4 s to open + ~1 s to draw page 1; app memory 1.6 GB after viewing 5 pages | open (library) — bf60da9: sheet 1 5.8–6.4 s, sheets 2–5 3.6–5.7 s; page answers ≤ 0.09 s. Poppler ~1 s a sheet (`PaintStrokeOp`) |
| B-28 | S2 | Linux (UI test) | UI tests 36a–36c count the 24×24 loading icon as a drawn page, so their sheet times (0.1–0.2 s) and 36c memory don't measure the real drawing | **verified fixed 8dcf4d8** (4de79ed) — `rendered()` counts only a page-sized svg; Linux's 36c sheet times (4.9–5.6 s) now match mine on the real file |
| B-29 | S3 | **shared Ui/Core** (render queue) | Closing the CAD tab mid-render: the next file sometimes waits 3.7–4.6 s for its first page (2 of 6 closes) | **verified fixed 8dcf4d8, re-verified d918161 and bf60da9** — 6 of 6 mid-render closes: next file drawn in 0.25–0.28 s |
| B-30 | S2 (perf) | **shared Ui/Core + Foundation** | Memory isn't given back after closing the CAD drawing: 1.43–1.77 GB stays for 60 s+, and 680 MB of managed heap is still live after a full collection | **verified fixed bf60da9** — app 247–250 MB before, 862–985 MB with 5 sheets (was ~1.9 GB), **267–270 MB 2 s after closing** and steady for 60 s. Remaining, recorded: WebKit's web process 220 → ~585 MB and stays |
| K-01 | — | Linux | GNOME close-only layout showed all three buttons (known, 7 Nov) | **verified fixed f7d0034, re-verified f3d5978** (6 layouts) |

Routing (coordinator, 8 Nov): **Linux** → the Linux chat. **shared Ui/Core** → Foundation's combined patch, as exact diffs from the Linux chat or Foundation. **library** → the coordinator compiles them for Arun (library coordinator).
| Route | Bugs |
|---|---|
| Linux chat | B-01, B-04, B-05, B-06, B-12, B-13, B-14, B-15, B-17, B-19, B-20, B-21, and the Linux stanzas of B-02 |
| shared Ui/Core | B-03, B-07, B-08b, B-10, B-11b, B-16, B-18, B-22, B-23, B-24, B-25, B-26, and the OFL texts next to the fonts in B-02 |
| library | B-27 (with shared: parse/render time and memory on the CAD drawing), B-08a (Chuvadi.Docs input limits), B-09a (Chuvadi.Sheets: don't materialise to the sheet's extent), B-11a (chuvadi-pdf: rebuild the xref on a bad `startxref`) |
B-09's "no cancel / no timeout" half is the same fix as B-08b.

Known and already tracked (not re-filed): sample recent files / watched folder on a fresh profile (D-94 H-12);
`.xlsx` shared-string index shown as a value — `bad-sst.xlsx` shows `99` (Sheets 2.0.2 move, D-87);
GNOME close-only button layout — now K-01, fixed and verified.

---

## B-01 — `.deb` fails lintian (S3, Linux)
**Steps.** `src/ChuvadiReader.Linux/packaging/deb/build-deb.sh out/` (and `--framework-dependent`); `lintian --pedantic --display-info out/*.deb`.
**Expected.** Clean (or each remaining tag overridden with a reason).
**Actual.** Self-contained: **21 E, 373 W**. Framework-dependent: 7 E, 13 W. Full output: `evidence/T1.6-lintian-sc.txt`, `-fd.txt`.
| Tag | Count | Cause / fix |
|---|---|---|
| E shared-library-is-executable | 14 | `.so` copied with NuGet's extracted mode `0744`; should be `0644` |
| W non-standard-executable-perm / executable-not-elf-or-script | 193 / 179 | every `.dll`, `.json`, wwwroot file is `0744` — `build-deb.sh` keeps NuGet-cache modes. Fix: `find … -type f -exec chmod 0644`, then `0755` only on the apphost (and `createdump`) |
| E executable-in-usr-share-doc | 4 | Microsoft `THIRD-PARTY-NOTICES*.txt` at `0744` |
| E unstripped-binary-or-object | 1 | `libchvdhost.so` not stripped (`strip --strip-unneeded` or `install -s`) |
| E embedded-library zlib | 1 | `libSystem.IO.Compression.Native.so` (Microsoft's) — add an override with a reason |
| E no-changelog | 1 | add `usr/share/doc/chuvadi-reader/changelog.Debian.gz` |
| W no-manual-page | 1 | add a short `chuvadi-reader.1.gz` |
The build log's "lintian: no copyright warnings" only checked copyright tags.
Functionally harmless (the apphost is `0755`; users can run it) — but rule: no warnings.

## B-02 — Copyright file misattributes fonts; OFL texts missing (S2 legal, Linux + Shared)
**Steps.** `dpkg-deb -x` the package; read `usr/share/doc/chuvadi-reader/copyright`; list `wwwroot/_content/ChuvadiReader.Ui/fonts/` and `lipi-sans/`.
**Expected.** Sthraas owns Sthraas code; third-party fonts listed with their own copyright holders and licence (SIL OFL 1.1), and the OFL text shipped with them (OFL condition).
**Actual.** `Files: *  Copyright: Sthraas Intelligence Pvt Ltd` covers everything, including `fonts/google/` (Instrument Serif, Fraunces, Tiro Tamil) and LiPi Sans (built from Inter + Noto per its own `LICENSE.txt`). No OFL text anywhere in the package. Sthraas is named correctly for its own work.
**Fix.** Linux: add `Files: usr/lib/chuvadi-reader/wwwroot/_content/ChuvadiReader.Ui/fonts/*` (etc.) stanzas with the real holders and `License: OFL-1.1` + full text. Shared: the Ui should ship the OFL texts next to the fonts (Windows/Mac/Android have the same gap — ties in with the font notices in D-82).

## B-03 — No package source mapping in `nuget.config` (S3 security, Shared)
**Actual.** `nuget.config` lists `localpackages` **and** nuget.org with no `<packageSourceMapping>`. If anyone publishes `Chuvadi.*` or `LiPicons.*` on nuget.org with a matching/higher version, restore can take theirs. Checked today: none of `chuvadi.pdf`, `chuvadi.print`, `chuvadi.sheets`, `chuvadi.fonts`, `lipicons.blazor` exists on nuget.org (404) — latent, not active.
**Fix.** Map `Chuvadi.*` and `LiPicons.*` to the local feed only; everything else to nuget.org. (Existing file → Foundation/Reader.)

## B-04 — Only the first of several files opens (S2, Linux)
**Steps.** `chuvadi-reader five-pages.pdf second.pdf sample.docx` (what the desktop entry's `%F` does for a multi-selection "Open with").
**Expected.** Three tabs (D-83: each file in its own tab).
**Actual.** One tab, `five-pages.pdf`; the other two silently ignored. `Program.cs:179` `OpenFromCommandLine` takes `args.FirstOrDefault(existing && supported)` — the first one only. Screenshot: `screenshots/B-04-cli-3-files-one-tab.png`.

## B-05 — No single instance (S2, Linux; needs the Foundation contract)
**Steps.** App running with `five-pages.pdf`; run `chuvadi-reader sample.xlsx` again.
**Expected.** The file opens as a new tab in the running window (D-83 approved); on Wayland the window is activated with the launcher's token.
**Actual.** A second process and a second window (2 windows named Chuvadi); the first window still has one tab. Screenshot: `screenshots/B-05-second-launch.png`. Foundation's contract and router (D-83) have been on `platform/foundation` since 6 Nov 19:41 (`docs/foundation/SINGLE-INSTANCE.md`, `Hosting/Desktop/DesktopSingleInstance.cs`, `InstanceChannel.cs`, `Platform/AppInstance.cs`); the Linux side builds against it. *(Correction: my first report said the doc was missing — my check listed the wrong ref.)*

## B-06 — Drop of several files opens only the first (S2, Linux)
**Evidence.** `Program.cs:174` drop handler: filters supported paths, then `Request(supported[0])` only. Same root cause as B-04. **Confirmed live on db28319:** a GTK 4 window offering two files as a `GdkFileList` (as a file manager does), dragged with xdotool onto the Reader — drop accepted, one tab (`five-pages.pdf`). Screenshot: `screenshots/B-06-drag-two-files-one-tab.png`. Tool: `tools/dragsrc.py`, `tools/t_drag.py`.
**Expected.** Each dropped file in its own tab.

## B-07 — Password-protected PDF can't be opened (S2, shared Ui/Core)
**Steps.** `qpdf --encrypt user1 own1 256 -- five-pages.pdf aes256.pdf` (also AES-128). Open it (CLI or Open).
**Expected.** A password prompt — the handout's first-run screen promises "PDF, Word, Excel or an image — even password-protected ones", and Protect › Password says "Opened a locked file? Remove its password".
**Actual.** "Could not open this document. This PDF is encrypted and needs a password to open." with only "Fetch…". No prompt. Word/Excel have `UnlockCard`; the PDF viewer path has none. Screenshot: `screenshots/B-07-aes256-no-prompt.png`. (Affects every platform — existing Ui.)

## B-08 — Zip-bomb `.docx` exhausts memory and never ends (B-08a S1 library · B-08b S2 shared Ui/Core)
**Steps.** A 1 MB `.docx` whose `word/document.xml` inflates to 1 GiB (generator in `RESULTS.md`). Open it.
**Expected.** Refused within a second or two with a clear "too large / damaged" message; memory bounded (Layout requirements §2 "bounded memory", Anjal A4 limits).
**Actual.** "Opening…" forever; app RSS **4.5 GB** and one core at ~94% after **10 min**; no cancel. Other tabs stayed usable. Screenshot: `screenshots/B-08-bomb-docx-opening-forever.png`.
**Fix.** Library: Chuvadi.Docs input limits (max part size / ratio, as chuvadi-pdf A4). App: cancel on the "Opening…" card and a timeout.

## B-09a — Huge-dimension `.xlsx` never opens (S1, library; cancel/timeout = B-08b)
**Steps.** `sample.xlsx` plus one cell at `XFD1048576`. Open it.
**Expected.** Opens (used range is two corners) or is refused with a message.
**Actual.** RSS jumps 305 MB → **1.72 GB** within 10 s and stays; "Opening…" for **185 s+** (stopped watching); CPU decays to ~3% (waiting, not working). Screenshot: `screenshots/B-09-far-cell-opening.png`.
**Fix.** Library: Sheets must not materialise the full grid to the sheet's extent. App: cancel + timeout as B-08.

## B-10 — A stuck open blocks every later open, silently (S2, shared Ui/Core)
**Steps.** Open `far-cell.xlsx` (B-09); 5 s later open `five-pages.pdf`.
**Expected.** `five-pages.pdf` opens in its own tab (or is queued with visible feedback).
**Actual.** Never opens in 185 s; no tab, no toast. In the batch run, 8 files opened after `far-cell.xlsx` were all dropped the same way. The open path is serial with no timeout, so one bad file takes the app's opening ability down until restart.

## B-11 — Damaged PDF not repaired; raw parser text shown (B-11a S3 library · B-11b S3 shared Ui/Core)
**Steps.** Copy of `five-pages.pdf` with only the `startxref` offset changed to `999999`. Also an empty `.pdf`.
**Expected.** Opens via xref reconstruction (poppler/qpdf do), or a plain-language "This file is damaged" state from the handout.
**Actual.** "Could not open this document. Expected object number integer, got EndOfStream at offset -1." Empty file: "Could not locate 'startxref' keyword in the last 1024 bytes of the file." Screenshot: `screenshots/B-11-badxref-raw-error.png`.
**Fix.** Library: xref rebuild on bad offset. App: map parser exceptions to the handout's damaged-file message (keep detail under "Details").

## B-12 — First launch per user: ~1.7 s blank window on GPU-less machines (S3 perf, Linux)
**Steps.** Fresh `HOME`, caches dropped, launch. 10 runs.
**Actual.** Blazor "first render" at ~1.25 s, but the window stays plain cream until **~2.9 s** (median). Cause, isolated: Mesa compiling shaders for WebKit's GL compositor in software (llvmpipe) into `~/.cache/mesa_shader_cache`. Fresh profile + warm shader cache → 1.47 s; fresh profile + `WEBKIT_DISABLE_COMPOSITING_MODE=1` → 1.1 s. Even warm, compositing costs ~250 ms here (1.26 s → 1.0 s). Hits VMs, remote desktops, thin clients — and again after every Mesa update. Timeline: `screenshots/B-12-fresh-profile-timeline.png`. Options in `RESULTS.md` › Options O-2.

## B-13 — Stray XML doc files shipped (S4, Linux)
`ChuvadiReader.Hosting.xml` and `ChuvadiReader.Platform.xml` (IntelliSense docs) in `/usr/lib/chuvadi-reader`. Fix: `-p:GenerateDocumentationFile=false` on publish, or exclude in `build-deb.sh`.

## B-14 — Landscape pages print shrunk onto portrait paper (S3, Linux)
**Steps.** Open `five-pages.pdf` (page 4 is landscape) or a 3-page A3-landscape vector drawing; Ctrl+P → Print → GTK dialog defaults (A4) → Print to the cups-pdf queue.
**Expected.** Each page fills the sheet in its own orientation, as Windows/Acrobat/browsers auto-rotate (or the job follows the document's orientation).
**Actual.** The app sends `orientation-requested=3` (portrait) with `print-scaling=fit` (CUPS debug log), which stops CUPS auto-rotating: page 4 and every A3-landscape sheet print at **about half size** in the middle of a portrait page. Portrait pages are fine.
Evidence: `screenshots/B-14-five-pages-page4-shrunk.png`, `screenshots/B-14-a3-landscape-printed-portrait.png`. (Vector itself passes — see RESULTS T4.7.)
**Fix.** Don't send `orientation-requested` unless the user changed it in the dialog (let CUPS auto-rotate per page), or derive it per page.

## B-15 — No user namespaces → hard abort, no message (S3, Linux)
**Steps.** Run where unprivileged user namespaces are unavailable (here: Docker default seccomp; in the field: hardened kernels with `user.max_user_namespaces=0`, some locked-down corporate images, or Ubuntu 24.04+ without the AppArmor profile — the README's dev-build note).
**Expected.** A plain message ("Chuvadi can't start its secure document view on this system — …") and a clean exit code, or a documented fallback.
**Actual.** `bwrap: No permissions to create new namespace…` then `** ERROR **: Connection: failed to receive credentials` → SIGABRT. No window, nothing for the user. Options in RESULTS › O-3.

## B-16 — Read-only home crashes at startup (S2, shared Ui/Core)
**Steps.** Non-root user, `chmod -R a-w ~`, launch `chuvadi-reader five-pages.pdf` (Docker `ubuntu:24.04`, installed `.deb`).
**Expected.** App starts with defaults in memory, opens the file, warns once that settings can't be saved (kiosk / locked-down / full-disk profiles do this).
**Actual.** `Chuvadi error: System.UnauthorizedAccessException: UnauthorizedAccess_IODenied_Path, /home/tester/.config` — process exits, no window. Settings/recents/category-folder creation all need to tolerate failure. Unguarded `Directory.CreateDirectory`: `Hosting/Desktop/FileAppStorage.cs:27` (the one that throws at startup), `Core/Documents/CategoryService.cs:42,45`, `Core/Documents/RecoveryService.cs:32`.

## B-17 — Users see .NET resource keys instead of messages (S3, Linux)
**Steps.** Non-root user; `chmod 000 locked.pdf`; `chuvadi-reader locked.pdf`.
**Expected.** "Could not open this document. Access to the path '/home/tester/locked.pdf' is denied." (what Windows shows).
**Actual.** "Could not open this document. **UnauthorizedAccess_IODenied_Path**, /home/tester/locked.pdf". Cause: `ChuvadiReader.Linux.csproj:19 <UseSystemResourceKeys>true</UseSystemResourceKeys>` strips the BCL's message strings; the shared Ui shows `ex.Message` in 65 places (disk full, access denied on save, etc. are all affected). Screenshot: `screenshots/B-17-resource-key-message.png`.
Second instance: a non-zip `.xlsx` shows "Couldn't open this workbook: **EOCDNotFound**".
**Fix.** Remove `UseSystemResourceKeys` (cost: a few hundred KB) — or map exceptions to own messages before display (bigger change, shared).

## B-18 — Left bar at rest is expanded, not the icon rail (S3 design, shared Ui/Core)
**Steps.** Fresh profile, open any PDF.
**Expected.** Handout README / `Reader Side Rails`: "Left bar (62 px, fixed): … icons … On hover it expands over the canvas to show labels and shortcuts."
**Actual.** 208 px labelled list at rest (`MainLayout.razor:648` — `leftbar.open` defaults to open); hover-expand over the canvas not used. DESIGN-NOTE already says the Ui implements D-10 partly — filing so it's tracked to done. Same on every desktop.

## B-19 — Left-side buttons push the brand cell out of line (S4, Linux) — on f7d0034
**Steps.** `~/.config/gtk-4.0/settings.ini`: `gtk-decoration-layout=close,minimize,maximize:` (or `close:`); launch.
**Expected.** Buttons on the left, and the top bar's left cell still lines up with the left bar's edge (the handout's column), or a stated alternative.
**Actual.** Buttons correct ✅, but the brand cell widens (≈ 210 → 245 px with one button, ≈ 292 px with three) while the left bar stays 210 px, so the top-bar divider sits 35–80 px right of the left-bar edge. Evidence: `screenshots/B-19-buttons-right.png` vs `screenshots/B-19-buttons-left.png`.
**Options.** A. buttons overlay the left bar's top cell and the wordmark shifts within it (cell keeps 210 px; wordmark may truncate with three buttons). B. Accept a wider cell but widen the left bar to match while buttons are left. C. Accept as is. Recommendation: **A** — keeps the handout's column, the only cost is the wordmark sliding right.

## B-20 — No printer: empty dialog with no explanation (S4, Linux)
**Steps.** Stop CUPS (or a machine with no queues); open a PDF; Ctrl+P → Print.
**Expected.** A plain message before or instead of the dialog ("No printers found — add one in Settings › Printers"), as the handout's "Blocked actions explain themselves".
**Actual.** GTK dialog opens with an empty printer list and a disabled Print button; the card shows "Cancel printing". No crash; Cancel works. ("Print to File" is absent too — fine if deliberate, since it would re-render rather than send the PDF as-is; worth a line in the README.) Screenshot: `screenshots/B-20-no-printer-empty-dialog.png`.

## B-21 — Show in folder opens two file-manager windows (S3, Linux) — db28319
**Steps.** Nautilus not yet showing a window (fresh session, or `nautilus --gapplication-service` only); open a PDF; Document ▾ › Show in folder.
**Expected.** One Nautilus window with the file selected.
**Actual.** Two windows on the folder. `chvd_reveal` (`native/chvdhost.c:924`) calls `FileManager1.ShowItems` with a **5000 ms** timeout; Nautilus here needs ~8 s for its first window, so the call is treated as failed and `LinuxDesktop.RevealAsync` runs `xdg-open <folder>` — then Nautilus's own reply arrives (successfully) and opens the selected-file window too. `dbus-monitor`: call at 0 s, fallback at 5.01 s, Nautilus reply at 7.99 s (`evidence/reveal/dbus-monitor.log`). A logging `xdg-open` stub confirmed the fallback fires. A single direct `ShowItems` never opens two windows (cold → 1 window; warm → reused in 6 ms).
**Fix.** Fall back only when there is no FileManager1 (`ServiceUnknown` / `NameHasNoOwner` / `UnknownMethod`); on a timeout, trust the call (or use an async call with no fallback). Screenshot: `screenshots/B-21-two-nautilus-windows.png`.

## B-22 — No designed keyboard-focus style (S4, shared Ui/Core) — suggestion
**Steps.** Open a PDF; press Tab.
**Expected.** A consistent, designed focus ring (the handout's only focus treatment is the 1 px `binding` ring on a focused desk).
**Actual.** Every stop shows WebKit's default ring, `outline: auto 5px rgba(53,132,228,.8)` (GTK blue); Windows shows Chromium's own default — so focus looks different per platform. Only `.tb-pg-box` and `.ph-pager-in` define focus styles. Suggest one rule: `:focus-visible { outline: 2px solid var(--chvd-binding); outline-offset: 2px; }`. Screenshot: `screenshots/B-22-focus-ring-gtk-blue.png`.

## B-23 — Tab order starts with a per-page button for every page (S4, shared Ui/Core)
**Steps.** Open `five-pages.pdf`; focus the window; Tab.
**Actual.** Tab 1–5 are `button.rpage-send` "Send page N to a desk" (hover-only controls), one per page, before the rails. A 300-page document = 300 Tab presses to reach anything else.
**Fix.** `tabindex="-1"` on the per-page hover buttons (reach them via the page strip / keyboard shortcut), or make only the current page's strip tabbable.

---

## Linux chat — fixes for re-verification (9 Nov: re-verify on `platform/linux` e242d92, CI green on x64 and ARM64)
Each fix has a test in `.github/workflows/linux.yml` / `tools/linux` (details: `docs/linux/BUILD-LOG.md` §37).
| Bug | Commit | Test |
|---|---|---|
| B-01, B-13 | 043e490 | `check-deb.py`: lintian --pedantic reports nothing un-overridden (both packages), file modes, no XML / unused precompressed files |
| B-02 (Linux) | 043e490 | `check-deb.py`: each font file in its own stanza naming the holder from the font's metadata; full OFL-1.1 text |
| B-04, B-06 | 606d01b | UI steps 34b (three files on the command line → three tabs, in order), 34c (two dropped → two tabs) |
| B-05 | 606d01b | UI step 34c2: a second launch hands over and exits 0 in ~0.1 s, one window, a new tab. Uses the kit's `DesktopSingleInstance` (L-A, F-1) |
| B-12 | e8ca522 | UI step 34b2 (no GPU → compositing off); `first-launch.py` records the time (here: 4.7 s → 1.0 s on a fresh profile) |
| B-14 | 4e9e244 | UI step 30: printed landscape page 4 has rotation 90 (fills the sheet) |
| B-15 | e8ca522 | `no-userns-test.sh` (seccomp rule refusing user namespaces): message window, exit 2 |
| B-16 | e8ca522; kit's `FileAppStorage` since 4144909 | `readonly-home-test.py` as an ordinary user: starts, opens the file, one notice |
| B-17 | 4e9e244; test faffa10 | `check-deb.py` (runtimeconfig); UI step 34d as a non-root user (chmod 000 file → the plain sentence, Details says "Access to the path … is denied") |
| B-20 | 606d01b (test in CI: ffb2823); separate CUPS server 1da278d | `no-printer-test.py` with CUPS stopped: plain message, no dialog ; `remote-cups-test.py`: a stand-in server named in CUPS_SERVER or client.conf gets the job |
| B-21 | c9f5500 (test: ffb2823) | `reveal-test.py`: a file manager answering after 8 s → one ShowItems, no xdg-open; none → one xdg-open |

| D-101 | 4144909 (+ Foundation 839d39d) | UI step 35: three live layout changes followed without a restart |
| B-02 (Ui), B-03, B-07, B-08b, B-09a, B-10, B-11b | Foundation 839d39d, merged in bad60d7 | Reader tests (`PdfPasswordTabTests`, `DamagedPdfTabTests`, `OfficeViewTests`); `aes256.pdf`, `badxref.pdf`, `bomb.docx`, `far-cell.xlsx` in the app. Since Foundation 1016987 (merged in 3297355) B-08/B-08b are the libraries' own limits (Word 20 MB part / 64 MB total, Excel `ForUntrustedInput`) with Cancel, and the app's package guard is retired |
| B-19 | Foundation 839d39d | UI step 35: divider within 1.5 px of the left bar in all 8 layouts |
| B-22 | Foundation 839d39d | UI step 34b4: Tab ring is the theme accent in all five themes; none on a mouse click |
| B-23 | Foundation 839d39d | UI step 34b3: no per-page buttons in the first Tab stops |

B-18 goes to the Reader chat's desktop revamp (it changes Windows too).

**9 Nov, Linux chat — `PROPOSAL-shared-fixes-9nov.md` (f84c9ed on `platform/linux`), exact diff for Foundation:**
| Bug | Fix (in the diff) | Test |
|---|---|---|
| B-24 (reopened) | The Reader no longer opens each new tab's file on the page's thread (`RefreshDocKind`, unused result) | UI step 34e: named-pipe `slow.pdf` and `slow.xlsx` → "Opening…" ≤ 1.2 s, "Stop opening" ~10 s, the next file opens meanwhile (fails on e242d92) |
| B-25 | Every viewer: plain sentence + system text under a collapsed Details (WT-10) | UI step 34f: `notzip.xlsx`, `notzip.docx` (fails on e242d92) |
| B-26 | D-147: B — raw values stay, as the file holds them (Arun's data-integrity rule, D-136's tests). Excel display text with the exact value on hover goes to Arun once Chuvadi.Sheets renders dates in the culture's order (format 14 shows en-IN `03-15-23`; library list) | D-136 corpus tests (unchanged) |
| B-27 | Library list (coordinator) | — |
Re-verify B-24/B-25 once Foundation's patch with this diff is merged into `platform/linux`.

**9 Nov evening, Linux chat — head for re-verification: `platform/linux` c373a3d** (Foundation's twelfth patch,
022b7c0 + c91a581: chuvadi-pdf 3.32.0, AT-03, W-01, W-02, P-08).
- **B-26 (D-147):** re-verify — raw values as the file holds them, unchanged.
- **B-08b Cancel:** re-verify (the library's Cancel, since 1016987).
- **B-24 is NOT fixed on c373a3d:** Foundation's patch doesn't yet carry the Linux chat's diff (the
  page-thread probe is still in `Reader.razor`), so `t_b24.py` will still reproduce it. Re-verify after
  Foundation applies `PROPOSAL-shared-fixes-9nov.md`.
- **Owner-password printing (D-139):** on c373a3d the Print card unlocks with the owner password, but printing
  fails ("This PDF is encrypted and needs a password to open"): the card doesn't get the tab's password. Fix S3 is
  in the same proposal; the Linux UI step 31b tests it (passes with the fix, 118/118).

**9 Nov night, Linux chat — re-verify everything on `platform/linux` 7595ef3** (CI green on x64 and ARM64).
Foundation's thirteenth patch, part 1 (7d1ac03) carries the Linux chat's B-24, B-25 and S3 fixes.
| Re-verify | What changed | Linux test |
|---|---|---|
| B-24 with B-08b Cancel | No file probe on the page's thread (`RefreshDocKind` removed) | UI 34e: pipe `slow.pdf` / `slow.xlsx` → "Opening…" 0.3 s, "Stop opening" 10 s, the next file opens meanwhile; `t_b24.py` should now pass |
| B-25 | Every viewer: plain sentence, the library's text under a collapsed Details | UI 34f: `notzip.xlsx`, `notzip.docx` |
| B-26 (D-147) | None: raw values as the file holds them | D-136 corpus tests |
| Print with the owner password (D-139) | The Print card gets the tab's password | UI 31b: user password → locked; owner password → CUPS writes 5 pages |

**10 Nov, Linux chat — quick re-verify on `platform/linux` ba94dfa** (Foundation's fourteenth patch, 21a222d +
b41f25c: pages render off the Ui thread, D-152/AT-13; CI green on x64 and ARM64; UI pass 121/121).
Please re-run your regression and these, since rendering changed:
- Paging fast through a big PDF (Linux UI 36a: 400 pages, 150 PageDowns — page answers ≤ 0.10 s).
  **Known, reported:** the page landed on draws 7.5–8.3 s after the last key (renders for pages paged past
  aren't cancelled, so it waits behind them). Expect that; note your own numbers.
- Closing a tab while it renders (36b): the next file draws at once; no errors.
- The CAD PDF (B-27): open, page through the 5 sheets, close; note time per sheet, memory before/after close,
  and any pause over 1 s. Linux's generated stand-in (36c): sheets 0.2–0.3 s, memory 600–700 MB that stays
  after closing, and a ~2.2 s pause once in four runs.
- B-24 / B-08b / B-25 / owner-password printing (31b, 34e, 34f) still pass on this head.

## B-24 — A stalled read gives a blank Reader, no Cancel, and blocks later opens (S2, shared Ui/Core) — e468d1a
**Steps.** `mkfifo /tmp/fifo/slow.pdf` (a source that never delivers data — the real-world case is a hung SMB/NFS/sshfs mount or an unplugged USB drive); `open /tmp/fifo/slow.pdf`; after 5 s open `five-pages.pdf`.
**Expected.** "Opening…" at once; after 10 s the `SlowOpenNote` with Cancel; Cancel closes the tab; the second file opens regardless (B-08b / B-10).
**Actual.** A `slow.pdf` tab and a **blank Reader** — no "Opening…", no rails, no Cancel — for 25 s+. The second open never happens (driver `open` doesn't return in 20 s; still one tab). Same stall as `.xlsx`: "Opening…" shows, no Cancel (the Excel view has no `SlowOpenNote` yet). The UI itself stays responsive (JS answers throughout).
**Likely cause.** The file is read before the viewer (and its `SlowOpenNote`) is mounted, inside the serial open path — so the 10 s timer never starts and the queue waits on the read. Fix: mount the viewer with "Opening…" + `SlowOpenNote` first, read the file off the open queue with the cancellation token, and let the next open proceed.
Screenshot: `screenshots/B-24-stalled-pdf-blank.png`. Tools: `tools/t_cancel_pdf.py`, `tools/t_cancel_fifo.py`.

## B-25 — Excel viewer errors don't follow WT-10 (S4, shared Ui/Core) — faffa10
**Steps.** Open `notzip.xlsx` (bytes that aren't a zip).
**Expected.** WT-10 wording as the PDF path now has: a plain sentence, with .NET's message under a collapsed **Details**.
**Actual.** "Couldn't open this workbook: End of Central Directory record could not be found." — the technical text inline, no Details. Readable (not a resource key), so cosmetic. Screenshot: `screenshots/B-25-xlsx-old-wording.png`.

## B-24 — reopened on 1016987: the Reader's tab-changed handler probes the file on the UI thread
**Build.** `platform/linux` faffa10 + `platform/foundation` 1016987 merged locally (test only, not pushed); d70590a (B-24's fix) included. Fixture: `fixtures/stalled-source.sh`.
**Actual.** Stalled `.pdf`: blank Reader (no "Opening…", no Cancel), later opens blocked — as before. Stalled `.xlsx`: "Opening…" at 0.4 s, then no Cancel in 16 s, later opens blocked.
**Root cause** (managed stacks, `dotnet-stack`, `evidence/b24/stacks-xlsx-stall.txt`):
```
Interop+Sys.Open ← FileStream..ctor ← Chuvadi.Pdf.Documents.PdfDocument.Open(string)
 ← ChuvadiReader.Core.Documents.FlattenService.Probe(string)
 ← ChuvadiReader.Ui.Pages.Reader.RefreshDocKind(string) ← Reader.SyncActive() ← Reader.OnTabsChanged()
 ← ChuvadiReader.Core.Reader.TabsService.OpenAsync(...)   [UI thread]
```
The tenth patch moved the load off-thread, but adding the tab raises `TabsChanged` synchronously and the Reader probes the file (as a PDF, even for `.xlsx`) on the UI thread. The library load itself (`XlsxViewService.Load` → `Workbook.Load`) correctly sits on a pool thread.
**Fix.** In `RefreshDocKind`, don't open the file on the UI thread: run `FlattenService.Probe` on a pool thread with the tab's cancellation token (or after the load completes), and only for PDFs. Add a Reader-level test (the page + `TabsService`), not only `TabsService`.

## B-26 — Excel number formats not applied (S3, shared Ui/Core) — 1016987
**Steps.** Open `fixtures/exact.xlsx`.
**Expected.** Displayed text as Excel shows it, value untouched: B23 `1234.5` with `"₹"#,##0.00` → `₹1,234.50`; B24 `0.125` with `0.00%` → `12.50%`; B22 `45000` with built-in 14 → the locale's short date (en-IN `15-03-2023`); B21 General → `1.23457E+19`.
**Actual.** `1234.5`, `0.125`, `2023-03-15`, `1.2345678901234567E+19`. `XlsxViewService.FormatValue` shows values as-is by design, waiting for "Chuvadi.Sheets [to expose] a formatted display string per cell" — Sheets 2.0.2 now has `Cell.GetDisplayText(NumberFormatOptions)` and `NumberFormatter.FormatDetailed(...)`. All text cells come through exactly (see RESULTS).

## B-27 — Large vector CAD PDF: slow to open, heavy on memory (S3 perf, library + shared Ui/Core) — e242d92
**File.** Arun's 7.9 MB KDMC LINAC site layout (5 × A1, ~1.44 M path operators, 170 images, 38 fonts; produced by Chuvadi). **Not committed (public repo)** — the library team should get it from Arun directly.
**Measured** (2 vCPU, no GPU; `tools/t_cadtime.py`, `tools/t_cad.py`): from process start, "Opening…" clears at 6.0 s warm / 6.6 s cold and page 1 is fully drawn at 6.9 s warm (worst 7.2) / 7.5 s cold (worst 11.9); the UI-test launch accounts for ~2.8 s, so **~3–4 s to open + ~1 s to draw**. Poppler draws page 1 in ~1 s on the same machine. App memory: 835 MB after page 1, **1,607 MB after paging through all 5** (not released while open), WebKit ~480 MB at 180 %.
**Expected.** Arun's bar is "loads in milliseconds"; at minimum a first page in ~1–2 s and memory that doesn't grow with every page viewed.
**Notes.** Rendering is correct (crisp vector at 180 %). Printing sends the file byte-identical (✅). Where the time and memory go (parse vs. render vs. page cache) needs a profile on the library side — I can run `dotnet-trace` here if wanted.


---
**10 Nov, Linux chat — the single head for re-verification and Arun's check: `platform/linux` 64c9c16**
(CI green on x64 and ARM64; full UI pass 121/121). It carries Foundation's patches 14 (pages render off the Ui
thread), 15 (render queue: pages that left the view are cancelled, the page in view goes first) and 16 (memory
after closing a heavy document). Please move the checklist for Arun from 7595ef3 to this head.

**Correction to my 9 Nov note:** the "render backlog" (landed page drawn 7.5–8.3 s after fast paging) was my
mistake. WebKitGTK plays each PageDown as a smooth-scroll step, so after 150 fast PageDowns the view keeps moving for
~12 s; the pages were already drawn. Measured from when the view settles, the landed page is drawn within 1 s
(UI 36a). Expect the long scroll after holding PageDown — a separate Linux finding, with the coordinator.

Re-verify on 64c9c16:
| What | Linux test | Linux result |
|---|---|---|
| Fast paging, big PDF | 36a | page answers ≤ 0.08 s; drawn within 1 s of the view settling |
| Closing a tab while it renders | 36b | next file drawn in 0.3 s, no errors |
| CAD PDF (B-27): time per sheet, memory before / open / after close | 36c | sheets 0.1–0.2 s; full pass 616 → 691 → 691 MB. On its own: 269 → 360 → ~520 MB after closing (rises at close; reported) |
| B-24 + B-08b Cancel, B-25, owner-password printing | 34e, 34f, 31b | pass |
| B-26 (D-147) | — | raw values, unchanged |

---
## Linux Test — 10 Nov, re-verification on `platform/linux` 64c9c16 (B-28 to B-30, and an update to B-27)
Built from source (`-p:UiTest=true`); 2 vCPU, no GPU, Xvfb + mutter. Tool: `tools/t_render.py`. Arun's CAD file is
run locally only. **Nothing from it is committed** (no file, screenshot or text); numbers and stack frames only.

## B-28 — UI tests 36a–36c count the loading icon as a drawn page (S2, Linux UI test)
**Found.** `rendered(i)` in `tools/linux/uitest.py` checks for any `svg` inside `.rpage-wrap`. While a page is
drawing, that wrapper already holds the loading icon: an `svg` with `viewBox="0 0 24 24"` and 4 elements. The real
drawing arrives later as a page-sized `svg` (for example `viewBox="0 0 2384 1684"` holding one image).
**Effect.** 36c's "sheets 0.1–0.2 s" is the time until the icon appears. On the same build, the stand-in's sheet 1
actually draws at 53–55 s, and sheet 2 hadn't drawn after 4 min. 36c's memory "after closing" is taken after a
drawing that never finished, so it isn't the B-27 number. 36a and 36b pass either way, because big.pdf pages are
simple; but their timings carry the same flaw.
**Fix.** Treat a page as drawn only when its page-sized `svg` is present (viewBox width > 100), or when the Reader
sets an attribute on the page as the drawing lands. Then raise 36c's limits to what the drawing really takes, or
mark it as reported until B-27 lands.

## B-29 — Closing the CAD tab mid-render sometimes delays the next file (S3, shared Ui/Core)
**Steps.** Open Arun's CAD PDF and close its tab after 0.3 s, while sheet 1 is still drawing. Then open `five-pages.pdf`.
**Result.** 6 closes, all mid-render, over two app runs. The next file's page 1 drew in 0.17, 0.53, 0.62 and 0.36 s
in four of them, and in **3.66 s and 4.62 s** in the other two. The page itself kept answering in ≤ 0.02 s
throughout. The stand-in: 3 of 3 closes drew the next file in 0.33–0.37 s.
**Likely cause.** The closed tab's raster pass isn't cancelled mid-sheet, so the next document waits behind it.
`platform/linux` 4f67a4c ("nothing keeps drawing for a closed tab", after 64c9c16) may fix this; I'll re-check it
on the next head.

## B-30 — Memory not given back after closing the CAD drawing (S2 perf, shared Ui/Core + Foundation)
**Steps.** Fresh app. Open Arun's CAD PDF, visit sheets 1–5 and back, close the tab, then wait 60 s.
**Result.** Three runs. Memory as app/WebKit, in MB:

| Point | Memory (app / WebKit, MB) |
|---|---|
| Before opening | 248–250 / 221–222 |
| Sheet 1 drawn | 875–880 / 287–300 |
| All 5 sheets | 1,433–1,773 / 568–677 |
| 60 s after closing | 1,425–1,773 / 536–712 |

The app's memory didn't move at all after closing. The test-only `gc` verb (an aggressive full collection) brought
the app to 456–472 MB. But **the managed heap is still 680–682 MB after that collection**, so something still
holds the closed document's memory (its page cache or rasters). Freeing memory won't help while that reference remains.
**Expected (16th patch).** Back to within ~100 MB of where it started.
Linux's 4f67a4c ("memory back after vector sheets too") and Foundation's 3759b6f (memory part 3) are after
64c9c16. I'll re-check this on the next head, with the corrected drawn-page check.

## B-27 — update on 64c9c16
- **UI.** The UI stays responsive while sheets draw: the page answers in ≤ 0.23 s, with one 1.22 s answer in three
  runs. This is the fourteenth patch working.
- **Draw times.** Each draw is no faster. From the `open` command:
  - Sheet 1 takes **6.0 / 7.1 / 8.4 s**. On e242d92 it was about 3–4 s to open plus ~1 s to draw.
  - Sheets 2–3 take **10.5–13.5 s each**.
  - Sheets 4–5 are already drawn by the time I reach them, because they draw in the background.
  - Poppler draws sheet 1 in 1.0 s.
- **The generated stand-in** (`make-heavy-pdfs.py` cad.pdf):
  - Sheet 1 takes **53–55 s**; sheet 2 hadn't drawn after **4 min**.
  - The app holds 1.0–2.7 GB the whole time, at 80–100 % CPU.
  - Poppler draws a sheet in 0.9 s.
- **Where the time goes.** The stacks taken during sheet 2 show the time is spent painting strokes:
  `ChuvadiPdfSession.DrainAsync → RenderInGate → RenderPageAsRasterSvg → PageRasterizer.Guard → RasterizeUpright →
  RasterizeInternal → PaintDisplayList → PaintStrokeOp`. This is a job for the library's rasteriser. It is not a hang.


---
**10 Nov, Linux chat — the single head: `platform/linux` 8dcf4d8** (Foundation's patches 17 and 18, fc6286a;
B-28 fixed). Please re-verify B-28, B-29, B-30, 36c's memory on the real CAD PDF, and a quick regression.
- **B-28:** a page counts as drawn only with its page-sized svg. 36c's stand-in is now 10,000 strokes a sheet, sized
  to the real file's memory (the 120,000-stroke one took ~49 s a sheet). Local and ARM64 CI: every sheet draws in
  3–6 s; memory 344–371 MB before → 2.1–2.5 GB with 5 sheets drawn → 394–817 MB after closing (ARM64 back near the
  start at ~65 s; locally not). 36c records memory; it isn't asserted yet.
- **Known on this head:** x64 CI failed 36c once — sheet 1 of a fresh open never drew in 30 s (screenshot in the
  `linux-x64` artifact). Likely the redraw race in `PROPOSAL-render-findings-10nov.md` (1); not yet proven.
- **For B-30, use the test-only `gc` verb** after closing: on the stand-in the .NET heap was still 678 MB 80 s after
  closing, and 5 MB after one aggressive collection — nothing holds the document, but the relief runs too early.
  Your real-CAD numbers will tell Foundation whether that's the same there.
- **Also found:** moving to a page while the view fits the first drawing can land two sheets on (finding 2).

---
## Linux Test — 10 Nov, re-verification on `platform/linux` 8dcf4d8 (B-28, B-29, B-30; B-27 update)
Built from source (`-p:UiTest=true`); 2 vCPU, no GPU. Arun's CAD file is run locally only; numbers are committed, nothing from the file.
`tools/t_render.py` now waits for the page heights to hold before moving to a page (Linux finding 2).

- **B-28 ✅.** `tools/linux/uitest.py` `rendered()` counts a page only when its svg's viewBox is wider than 100.
- **B-29 ✅.**
  - Closing the CAD tab mid-render, then opening `five-pages.pdf`: the next file drew in **0.26–0.27 s**, 6 of 6
    times (64c9c16: twice 3.7–4.6 s).
  - Closing mid-render, then reopening the same drawing: sheet 1 drew in 4.3–5.9 s on the real file and 6.3–6.9 s on the
    stand-in, 6 of 6 times.
- **B-30: the release is fixed, and a gap is recorded.** Four runs on the real file:

  | Point | Memory (app / WebKit, MB) |
  |---|---|
  | Before opening | 248–250 / 216–220 |
  | 5 sheets | 1,403–1,488 / 655–665 |
  | +2 to +60 s after closing | 651–692 / ~600 |
  | +90 s after closing | 357–580 / ~600 |

  A full collection afterwards leaves **3–5 MB** of managed heap (64c9c16: 680 MB), so nothing holds the closed
  document any more. What's left:
  - The app stays ~400 MB above its start for a minute, and ~100–330 MB above it at 90 s.
  - WebKit keeps ~380 MB.

  This is Linux's finding 3: the relief runs before the drawing is garbage. It's with Foundation; I'm not blocking on it.
- **B-27 (update).**
  - The real file: sheet 1 takes **5.6–6.9 s**, and sheets 2–5 take **3.4–5.6 s** each. The page answers in ≤ 0.39 s.
  - Linux's new stand-in (10,000 strokes a sheet) behaves like the real file: sheets in 5.0–7.0 s, and 2.0–2.5 GB with 5 sheets.
  - Note: the build log (§50) puts the real file at "~1 s a sheet". On this machine it's 3.4–6.9 s.
- **Linux findings 1 and 2** (`docs/linux/PROPOSAL-render-findings-10nov.md`, with Foundation). I hit these on
  my own before taking the wait from Linux's test.
  - I typed 2 in the page box as soon as sheet 1's drawing arrived. At that moment sheet 1's slot shrinks from 3,680 px
    to 1,014 px, so the jump lands two sheets on.
  - Sheet 2, which was skipped, then **never drew in 240 s**. This happened in 2 of 3 runs.
  - A person typing a page number at that moment would see the wrong sheet, and the skipped one would stay blank.
    It's worth fixing before release.
- **CI.** The Linux run on 8dcf4d8 ([42723205272](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42723205272))
  **failed on x64**.
  - The failing step is the full UI pass: `36c-cad-drawing` "timed out waiting for sheet 1 drawn". arm64 passed, and
    both packages were built.
  - I couldn't reproduce it here: 3 of 3 stand-in runs on their own were fine, and so were 6 of 6 close-then-reopen
    runs of the same file.
  - It may be finding 1 or the D-156 wait after 36b's close. It's for the Linux chat.


---
**10 Nov, Linux chat — the single head: `platform/linux` d918161** (Foundation's nineteenth patch, f88f9ef: a
cancelled page is asked for again, the page in view stays put when heights change, a closed document's pages are let
go; plus the Linux host now gives freed native memory back with glibc's `malloc_trim` after each memory relief).
Linux CI green on x64 and ARM64; local full pass 121/121. Please re-verify B-28, B-29, B-30, the real CAD PDF's
memory, and a quick regression.
- **x64 36c (sheet 1 of a fresh open never drawn):** didn't recur on this head's CI.
- **36c memory (stand-in):** 337 MB before → 2.0 GB with 5 sheets drawn → 519 MB 90 s after closing; 2–4 relief
  passes ran, yet 80 s after closing the .NET heap still held 681–807 MB that one more aggressive collection clears
  (to 3–5 MB, app within 100 MB of the start). With Foundation. Use the `gc` verb (it now also reports `reliefPasses`)
  on the real CAD file: before and after it, 60–90 s after closing.

---
## Linux Test — 10 Nov, last pass on `platform/linux` d918161 (Foundation's nineteenth patch + glibc trim)
These results are on my real CAD file. Nothing from the file is committed; `tools/t_render.py` modes are `jumps`, `solo` and `close`.

**Linux findings 1 and 2 ✅** (`jumps`, 3 runs).
- *Typing 2 as sheet 1 lands.* The page box reads 2 and sheet 2 is in view every time, drawn in 2.6–3.1 s.
  On 8dcf4d8 the jump went two sheets on, and the skipped sheet never drew.
- *2 then 5 at once, so sheet 2's render is cancelled.* Sheet 5 draws in 9.3–9.5 s. Then paging back to sheets 2, 3
  and 4: each draws, in 0.0–8.6 s. None stays blank.

**B-29 ✅.** 6 of 6 mid-render closes: the next file drew in 0.26–0.28 s.

**B-30: gap still open (recorded, not blocking).** Five runs, memory as app / WebKit, in MB:

| Point | Memory (app / WebKit, MB) |
|---|---|
| Before opening | 247–251 / 220 |
| 5 sheets | 1,828–1,963 / 647–666 |
| +2 to +60 s after closing | 564–679 / ~600 |
| +90 s after closing | 335–649 |
| +240 s after closing | 363 and 650 (two longer runs) |

The relief ran twice in every run (`reliefPasses: 2`). Even so, the managed heap still held **176–873 MB**
afterwards, and one aggressive collection clears it to 4–6 MB, leaving the app at 298–335 MB, within ~50–90 MB of
its start. So the closed drawing's garbage outlives both relief passes; the Linux build log (§51) found the same.
The trim works once the garbage is collected. WebKit keeps ~380 MB more than at the start.
**Target "back within 100 MB of the start": not met yet.**

**B-27.** Sheet 1 takes 4.7–4.9 s, and sheets 2–5 take 2.9–4.9 s each. The page answers in ≤ 0.22 s.


---
**10 Nov, Linux chat — head for a quick re-check: `platform/linux` bf60da9** (Foundation's twentieth and
twenty-first patches: each memory relief waits for the finalizer thread; drawn pages served by address). Linux CI
green on x64 and ARM64; local full pass 122/122. Please re-check 36c, page images and a quick regression.
- **36c (memory now asserted):** 259–333 MB before → 0.86–1.2 GB with 5 sheets drawn (was ~2 GB) → 247–293 MB at
  once after closing. Please measure the real CAD PDF the same way.
- **Page images (new UI step 36d):** a drawn A1 sheet comes from `_chvd/pages/<32 hex>.png`; its page markup is 964
  characters (was ~77 MB inline); the address serves a PNG with `Cache-Control: private, no-store`; an unknown
  token is 404. Worth a look on the real CAD PDF: zoom in and out and page through, and check that sheets stay
  sharp and nothing goes blank.
- **Known, intermittent:** once in two local full passes (and once on x64 CI earlier), a fresh open of the drawing
  kept the previous zoom, never fitted, and never drew sheet 1 in 30 s. Reported to Foundation. If you see a
  sheet stuck as a portrait "page 1" placeholder, note the steps before it.

---
## Linux Test — 10 Nov, quick re-check on `platform/linux` bf60da9 (Foundation's patches 20–21)
These results are on my real CAD file. Nothing from the file is committed: hashes, sizes and timings only.
Tools: `tools/t_render.py`, `t_pages.py`, `t_stall.py`.

**36c memory ✅ (B-30 fixed).** Three runs, app / WebKit, in MB:

| Point | Memory (app / WebKit, MB) |
|---|---|
| Before opening | 247–250 / 220 |
| Sheet 1 drawn | ~808 / 251–312 |
| 5 sheets | 862–985 / ~595 |
| +2 s after closing | 267–270 / ~586 |
| +60 s after closing | 267–270 / ~585 |

The app is back within ~20 MB of its start at once. One relief pass ran, and a full collection afterwards finds
nothing more (heap 6–8 MB). **Still recorded:** WebKit's web process keeps ~365 MB more than at the start.

**36d page images by address ✅, pixel-identical.** `t_pages.py` decodes each sheet's image in the page and hashes
every pixel (FNV-1a over RGBA). d918161 serves the image inline; bf60da9 serves it from `_chvd/pages/<token>.png`.

| Sheet | Image | Hash, d918161 = bf60da9 | Markup, d918161 → bf60da9 |
|---|---|---|---|
| 1 | 3508 × 4967 | `e8708796` | 2,749,014 → 964 characters |
| 2 | 3508 × 4967 | `10a11e78` | 3,812,450 → 964 |
| 3 | 3508 × 4967 | `2ecca41f` | 4,301,618 → 964 |
| 4 | 3508 × 4967 | `382e4cc0` | 2,784,042 → 964 |
| 5 | 3508 × 4967 | `7cd34c49` | 4,417,414 → 964 |

Zooming sheet 1 in three steps (30 → 55 → 80 → 106 %) and back keeps the same image (same hash) in both builds:
nothing goes blank or is redrawn smaller. The raster is 4,967 px on the long side; at 106 % the sheet is about
2,500 px wide on screen, so it stays sharp.

**Fast paging ✅.** After 150 PageDowns the page answers in ≤ 0.10 s, and the landed page is already drawn. 40
page-box jumps: the landed page draws in 0.05 s. Page 400 draws in 0.19 s.

**Close mid-render ✅.** 6 of 6: the next file draws in 0.25–0.28 s.

**Cancelled sheets ✅.** A jump to 2 as sheet 1 lands goes to sheet 2 (2 of 2). After 2 then 5 at once, sheets 2, 3
and 4 all draw when paged back to.

**Intermittent fresh-open stall: not reproduced, but its starting state was caught.**
`t_stall.py` starts a fresh app for every try and opens the real CAD file four ways:
1. Launched with the file on the command line.
2. `open` sent 0.5 s after the window appears.
3. After a zoomed-in tab was closed.
4. After the same drawing was closed mid-render.

- **Result.** 0 stalls in 32 tries: 20 unloaded (sheet 1 in 5.3–7.9 s) and 12 with three busy loops hogging both CPUs
  (11.8–15.8 s).
- **The clue.** A fresh open starts at zoom **115 %** (`--rpage-zoom: 1.152`), with sheet 1's slot a portrait
  **2587 × 3680** px. This is exactly the state in Linux's report. The view fits (30 %, slot 678 × 1014) when the
  page sizes arrive.
- **The race.** Usually the fit comes before sheet 1 is drawn. But in 4 of the 32 tries the 115 % state was still
  showing at the moment sheet 1 drew (label 115 %, and once the slot was still 2587 × 3680); it fitted just
  afterwards. Launch from the command line is the slowest to fit (2 of 8 tries).
- **For Foundation.** "Fit" and "first sheet drawn" arrive in either order. The stall looks like the case where the
  fit (page sizes) never arrives, so the sheet waits at 115 % as a portrait placeholder. I'd look at what happens
  when the first render request is made before the page sizes land, and whether the size notification can be dropped.
- **Harness note.** My first run showed 7 "failures". They were mine: the next try reused an X display before Xvfb
  had let go, and `app.log` says "no display was found". Each try now has its own display.

**Quick regression ✅.** B-24 + B-08b Cancel (`.pdf`, `.xlsx`, `.docx`); B-25; owner-password printing; single
instance (1 window, 4 tabs); drops; print byte-identical; B-26 raw values (D-147); no files left in `/tmp`.
