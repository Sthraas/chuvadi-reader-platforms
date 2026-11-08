# Linux Test — bugs

Build under test: `platform/linux` **eb65770** (725c1a9 differs only in `BUILD-LOG.md`).
Sandbox: Ubuntu 24.04 x64, 2 vCPU, no GPU, Xvfb + mutter; clean-install checks in Docker `ubuntu:24.04` / `ubuntu:26.04`.
Severity: **S1** crash/data loss/security · **S2** feature broken · **S3** wrong but usable · **S4** cosmetic.
Owner: **Linux** = Linux chat · **Shared** = existing Ui/Core/Hosting code (Reader chat / Foundation; affects every platform) · **Library** = Chuvadi library ask.
Every bug gets fixed; I re-verify on the fixing commit and mark it here.

| ID | Sev | Owner | Title | Status |
|---|---|---|---|---|
| B-01 | S3 | Linux | `.deb` fails lintian: 21 errors, 373 warnings | open |
| B-02 | S2 (legal) | Linux + Shared | Copyright file claims third-party OFL fonts for Sthraas; OFL texts not shipped | open |
| B-03 | S3 (security) | Shared | `nuget.config` has no package source mapping (dependency-confusion risk) | open |
| B-04 | S2 | Linux | Several files on the command line / `%F` open only the first | open |
| B-05 | S2 | Linux (+Foundation contract) | Single instance missing: a second launch opens a second window | open |
| B-06 | S2 | Linux | Window drop of several files opens only the first (code-confirmed; live drag pending) | open |
| B-07 | S2 | Shared | Password-protected PDF can't be opened: no password prompt | open |
| B-08 | S1 | Library + Shared | Zip-bomb `.docx` → 4.5 GB RAM, CPU-bound for 10+ min, "Opening…" forever, no cancel | open |
| B-09 | S1 | Library + Shared | `.xlsx` with a cell at XFD1048576 → 1.7 GB, "Opening…" forever | open |
| B-10 | S2 | Shared | One stuck open silently blocks every later open (no tab, no message) | open |
| B-11 | S3 | Library + Shared | Damaged PDF (bad `startxref` offset) not repaired; raw parser text shown to the user | open |
| B-12 | S3 (perf) | Linux | First launch per user on a GPU-less machine: ~1.7 s of blank window (WebKit GL compositing) | open — options |
| B-13 | S4 | Linux | Stray XML doc files shipped in `/usr/lib/chuvadi-reader` | open |
| B-14 | S3 | Linux | Landscape pages print shrunk onto portrait paper (orientation forced to portrait) | open |
| B-15 | S3 | Linux | No user namespaces → app aborts with a GLib ERROR, no message | open — options |
| B-16 | S2 | Linux + Shared | Read-only home → unhandled exception at startup, no window | open |
| B-17 | S3 | Linux | `UseSystemResourceKeys=true` → users see resource keys (`UnauthorizedAccess_IODenied_Path`, `EOCDNotFound`) instead of messages | open |
| B-18 | S3 (design) | Shared | Left bar at rest is the expanded 208 px labelled list; handout: 62 px icon rail, labels on hover | open |
| B-19 | S4 | Linux | Buttons on the left: top-bar brand cell widens past the left bar; divider no longer lines up (f7d0034) | open |
| B-20 | S4 | Linux | No printer / CUPS down: empty print dialog, no explanation | open |
| K-01 | — | Linux | GNOME close-only layout showed all three buttons (known, 7 Nov) | **fixed f7d0034 — verified** |

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
**Actual.** A second process and a second window (2 windows named Chuvadi); the first window still has one tab. Screenshot: `screenshots/B-05-second-launch.png`. The build log says this waits on Foundation's contract — `SINGLE-INSTANCE.md` is **not on `platform/foundation`** at the time of testing, so the dependency itself is outstanding. Coordinator: please confirm who is unblocking this.

## B-06 — Drop of several files opens only the first (S2, Linux)
**Evidence.** `Program.cs:174` drop handler: filters supported paths, then `Request(supported[0])` only. Same root cause as B-04. Live multi-file drag test is still pending (needs a real drag source; I'll re-verify on the fix with one).
**Expected.** Each dropped file in its own tab.

## B-07 — Password-protected PDF can't be opened (S2, Shared)
**Steps.** `qpdf --encrypt user1 own1 256 -- five-pages.pdf aes256.pdf` (also AES-128). Open it (CLI or Open).
**Expected.** A password prompt — the handout's first-run screen promises "PDF, Word, Excel or an image — even password-protected ones", and Protect › Password says "Opened a locked file? Remove its password".
**Actual.** "Could not open this document. This PDF is encrypted and needs a password to open." with only "Fetch…". No prompt. Word/Excel have `UnlockCard`; the PDF viewer path has none. Screenshot: `screenshots/B-07-aes256-no-prompt.png`. (Affects every platform — existing Ui.)

## B-08 — Zip-bomb `.docx` exhausts memory and never ends (S1, Library + Shared)
**Steps.** A 1 MB `.docx` whose `word/document.xml` inflates to 1 GiB (generator in `RESULTS.md`). Open it.
**Expected.** Refused within a second or two with a clear "too large / damaged" message; memory bounded (Layout requirements §2 "bounded memory", Anjal A4 limits).
**Actual.** "Opening…" forever; app RSS **4.5 GB** and one core at ~94% after **10 min**; no cancel. Other tabs stayed usable. Screenshot: `screenshots/B-08-bomb-docx-opening-forever.png`.
**Fix.** Library: Chuvadi.Docs input limits (max part size / ratio, as chuvadi-pdf A4). App: cancel on the "Opening…" card and a timeout.

## B-09 — Huge-dimension `.xlsx` never opens (S1, Library + Shared)
**Steps.** `sample.xlsx` plus one cell at `XFD1048576`. Open it.
**Expected.** Opens (used range is two corners) or is refused with a message.
**Actual.** RSS jumps 305 MB → **1.72 GB** within 10 s and stays; "Opening…" for **185 s+** (stopped watching); CPU decays to ~3% (waiting, not working). Screenshot: `screenshots/B-09-far-cell-opening.png`.
**Fix.** Library: Sheets must not materialise the full grid to the sheet's extent. App: cancel + timeout as B-08.

## B-10 — A stuck open blocks every later open, silently (S2, Shared)
**Steps.** Open `far-cell.xlsx` (B-09); 5 s later open `five-pages.pdf`.
**Expected.** `five-pages.pdf` opens in its own tab (or is queued with visible feedback).
**Actual.** Never opens in 185 s; no tab, no toast. In the batch run, 8 files opened after `far-cell.xlsx` were all dropped the same way. The open path is serial with no timeout, so one bad file takes the app's opening ability down until restart.

## B-11 — Damaged PDF not repaired; raw parser text shown (S3, Library + Shared)
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

## B-16 — Read-only home crashes at startup (S2, Linux + Shared)
**Steps.** Non-root user, `chmod -R a-w ~`, launch `chuvadi-reader five-pages.pdf` (Docker `ubuntu:24.04`, installed `.deb`).
**Expected.** App starts with defaults in memory, opens the file, warns once that settings can't be saved (kiosk / locked-down / full-disk profiles do this).
**Actual.** `Chuvadi error: System.UnauthorizedAccessException: UnauthorizedAccess_IODenied_Path, /home/tester/.config` — process exits, no window. Settings/recents/category-folder creation all need to tolerate failure.

## B-17 — Users see .NET resource keys instead of messages (S3, Linux)
**Steps.** Non-root user; `chmod 000 locked.pdf`; `chuvadi-reader locked.pdf`.
**Expected.** "Could not open this document. Access to the path '/home/tester/locked.pdf' is denied." (what Windows shows).
**Actual.** "Could not open this document. **UnauthorizedAccess_IODenied_Path**, /home/tester/locked.pdf". Cause: `ChuvadiReader.Linux.csproj:19 <UseSystemResourceKeys>true</UseSystemResourceKeys>` strips the BCL's message strings; the shared Ui shows `ex.Message` in 65 places (disk full, access denied on save, etc. are all affected). Screenshot: `screenshots/B-17-resource-key-message.png`.
Second instance: a non-zip `.xlsx` shows "Couldn't open this workbook: **EOCDNotFound**".
**Fix.** Remove `UseSystemResourceKeys` (cost: a few hundred KB) — or map exceptions to own messages before display (bigger change, shared).

## B-18 — Left bar at rest is expanded, not the icon rail (S3 design, Shared)
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
