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
| B-24 | S2 | **shared Ui/Core** | A stalled read (hung network share) shows a blank Reader with no "Opening…" or Cancel, and blocks every later open | **verified fixed 7595ef3** (13th patch) — stalled `.pdf`/`.xlsx`/`.docx`: "Opening…" at 0.3–0.9 s, Cancel at 10 s, Cancel closes the tab, later opens never blocked |
| B-25 | S4 | **shared Ui/Core** | Excel viewer errors still use the old one-line wording (no WT-10 sentence + Details) | **verified fixed 7595ef3** — Excel "This file couldn't be read as an Excel workbook.", Word "…as a Word document.", damaged PDF "This PDF is damaged…", each with Details |
| B-26 | S3 | **shared Ui/Core** | Excel number formats not applied: `"₹"#,##0.00` shows `1234.5`, `0.00%` shows `0.125` (values unaltered) — Sheets 2.0.2 now has `Cell.GetDisplayText` | **deferred by decision (D-147)** — raw stored value is the decided behaviour for now (Arun's data-integrity rule); option A (formatted display text, exact value on hover) is a later improvement, with Arun |
| B-27 | S3 (perf) | **library + shared Ui/Core** | Large vector CAD PDF (5 × A1, ~1.44 M path ops): ~3–4 s to open + ~1 s to draw page 1; app memory 1.6 GB after viewing 5 pages | open — e242d92, measurements only |
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