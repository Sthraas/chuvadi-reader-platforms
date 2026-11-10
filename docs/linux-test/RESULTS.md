# Linux Test — results

Build under test: `platform/linux` **eb65770** (all T1–T6 cases below) plus **f7d0034 / db28319** (button-layout fix re-verify, ARM64 artifact).
Sandbox: Ubuntu 24.04 x64, 2 vCPU, 7 GB, **no GPU**, root, no systemd. Clean installs: Docker `ubuntu:24.04`, `ubuntu:26.04` (non-root `tester`). ARM64: Docker `linux/arm64` under QEMU user-mode (install/launch only — no timing).
Legend: ✅ pass · ❌ fail (bug ID) · ⚠️ pass with note · ⏳ not yet run · 🔒 blocked (reason).
Evidence paths are relative to this folder unless absolute. My test tools (never shipped) are in `tools/`.

## Summary
| Area | ✅ | ❌ | ⏳/🔒 |
|---|---|---|---|
| T1 Build & package | 10 | 3 (B-01, B-02, B-13) | 1 |
| T2 Startup | 4 | 1 (B-12) | — |
| T3 Design | 9 | 4 (B-18, B-19, B-22, B-23) | 1 |
| T4 Function | 14 | 6 (B-04–B-07, B-14, B-21) | 3 |
| T5 Robustness | 11 | 7 (B-08–B-11, B-16, B-17, B-20) | 2 |
| T6 Wayland/X11 | 5 | 1 (B-15) | 2 |

The Linux chat's own UI pass (`tools/linux/uitest.py`) re-run here independently: **106/107**; the one fail (`05-window-minimise`) was my environment (`xprop` from `x11-utils` not installed), not the app.

---

## T1 Build and package from clean
| ID | Case | Result | Evidence |
|---|---|---|---|
| T1.1 | Empty `~/.nuget`, fresh worktree, `scripts/setup-feed.sh` | ✅ `localpackages/` byte-identical to `ci/packages` | `diff` clean |
| T1.2 | `dotnet build -c Release -warnaserror` | ✅ 0 warnings, 0 errors | `evidence/` build log |
| T1.3 | Test projects | ✅ `ChuvadiReader.Tests` 161/161, `Hosting.Tests` 28/28 | |
| T1.4 | Restored packages | ✅ only Microsoft.\*, System.\*, Chuvadi.\*, LiPicons.\* — ⚠️ but no source mapping → **B-03** | `T1.4-cache.txt` |
| T1.5 | `--verify-pack` vs tag | ⏳ | |
| T1.6 | `.deb` SC + FD, lintian | ❌ **B-01** (SC 21 E / 373 W; FD 7 E / 13 W) | `evidence/T1.6-lintian-*.txt` |
| T1.7 | `.deb` arm64 (CI artifact, run 42481652554 on f7d0034) | ✅ install/remove on arm64; launch 🔒 QEMU (see ARM64) | `evidence/T1.7-arm64*.log` |
| T1.8 | Install / remove / purge, 24.04 + 26.04, SC + FD | ✅ apt resolves deps on both; purge leaves nothing; FD pulls `dotnet-runtime-10.0` | `evidence/T1.8-install-*.log` |
| T1.8b | Upgrade 0.9.0~preview → 1.0.0~preview with existing settings | ✅ theme (Dark) + recents survive; app opens in Dark | `screenshots/` `upg-new` |
| T1.9 | Desktop entry, `%F`, icons, MIME | ✅ `desktop-file-validate` clean, `appstreamcli validate` clean, `xdg-mime` default = `in.chuvadi.Reader.desktop` for pdf/docx/xlsx; hicolor 16–256 | install logs |
| T1.10 | Copyright names Sthraas Intelligence Pvt Ltd | ✅ named — ❌ but claims third-party fonts too → **B-02** | |
| T1.11 | Package contents audit | ✅ only .NET (Microsoft), own assemblies, Chuvadi libs, LiPicons, `libchvdhost.so`; `ldd` of every `.so` resolves to OS libs only (GTK, GLib, WebKitGTK, libc, ICU, OpenSSL, zlib); no Windows-only assembly (`Rendering.Wpf` absent). ⚠️ shipped fonts are third-party OFL (B-02); stray XML docs → **B-13** | |
| T1.12 | No test code in release | ✅ `UiTestDriver` absent from shipped `chuvadi-reader.dll` | |

**ARM64** (CI artifact `chuvadi-reader_1.0.0~preview_arm64.deb`, QEMU): see the ARM64 section at the end.

## T2 Startup (ms) — 2 vCPU, no GPU, Xvfb 1440×900 + mutter
Independent probe: `framewatch` (test tool) forks the app, polls the X root window every ~10 ms; **content** = first frame where the changed pixels hold > 200 colours (the smoke test's rule), **settled** = last change before 1.5 s of stillness (status-bar clock masked). App's own `CHUVADI_TIMING` marks recorded alongside. Median / worst / best of n.

| Case | n | window shown (app) | Blazor first render (app) | **real content on screen** | settled |
|---|---|---|---|---|---|
| Warm, Home | 12 | 234 / 264 / 217 | 1,039 / 1,175 / 973 | **1,255 / 1,397 / 1,179** | 1,334 / 1,397 |
| Cold (page cache dropped), Home | 12 | 324 / 348 / 288 | 1,255 / 1,363 / 1,184 | **1,538 / 1,655 / 1,418** | 1,600 / 1,708 |
| Warm, PDF first page (CUPS test page) | 12 | 249 / 301 | 1,073 / 1,190 | **1,577 / 1,932 / 1,234** | 1,992 / 2,969 |
| Cold, PDF first page | 12 | 342 / 392 | 1,247 / 1,443 | **1,760 / 1,950 / 1,592** | 2,182 / 2,446 |
| Installed `.deb` (self-contained), warm | 12 | 244 / 287 | 1,047 / 1,134 | **1,262 / 1,403** | 1,320 / 1,462 |
| Installed `.deb` (self-contained), cold | 12 | 405 / 469 | 1,323 / 1,441 | **1,630 / 1,782** | 1,724 / 1,844 |
| **First launch for a new user** (fresh HOME + cold) | 10 | 328 / 354 | 1,253 / 1,372 | **2,934 / 3,129 / 2,854** ❌ B-12 | 3,008 / 3,218 |
| Wayland (Weston, pixman), warm | 3 | 222–233 | 820–952 | not probed (no X root) | |
| **f3d5978** — first launch, new user | 10 | 332 / 729 | 1,107 / 1,538 | **1,089 / 1,527 / 1,014** ✅ B-12 fixed | 1,116 / 1,568 |
| **f3d5978** — warm, Home | 10 | 259 / 545 | 1,042 / 1,255 | **1,016 / 1,259 / 848** | 1,062 / 1,288 |
| **f3d5978** — warm, PDF first page | 10 | 238 / 324 | 936 / 1,211 | **875 / 1,215 / 828** | 1,588 / 1,870 |

Findings
- ✅ Matches the Linux chat's numbers for what it measures (its "first render 0.97–1.07 s" ≈ my warm 1,039 median). But **"first render" is not pixels**: real content arrives **~220 ms later warm** and **~1.7 s later on a user's first launch**. Recommend the build log reports time-to-pixels too.
- Self-contained `.deb` ≈ framework-dependent publish (+8 ms warm, +90 ms cold — larger files from disk).
- ❌ **B-12**: first launch per user on a GPU-less machine — Mesa compiling WebKit's compositor shaders in software. Isolated: warm shader cache → 1.47 s; `WEBKIT_DISABLE_COMPOSITING_MODE=1` → 1.1 s (and 1.0 s vs 1.26 s even warm). Options O-2.
- ✅ Exits cleanly on SIGTERM (≤ 1 s), no orphan WebKit processes.
- **Windows comparison: not possible** — Foundation `STARTUP.md` documents in-process stage costs only; end-to-end Windows numbers wait on D-51 (Arun's machine).

## T3 Design fidelity
| ID | Case | Result | Evidence |
|---|---|---|---|
| T3.1 | Every screen captured (Home, Library, Reader + each rail/card, Mark, Arrange/Bench, Protect, Settings × 10 sections, 5 themes, docmenu, command bar) | ✅ captured by the re-run UI pass; review against the handout continues (T3.7) | `/home/claude/evidence/uitest/*.png` (not committed — 107 files; will attach a contact sheet) |
| T3.2a | **Engine vs Windows engine**: identical DOM snapshot from the running Linux app rendered in Chrome (= WebView2's engine) at 1920×1080 | ✅ explained differences only: Home 3.9 % / Reader 1.8 % of pixels differ > 8 %; WebKitGTK sets body text ~0.5 % wider (3 px over 480 px) and blocks ~2 px higher (glyph hinting / line-height rounding); Reader page 5 px left (overlay vs classic scrollbar gutter); page size identical (686 px). All fonts loaded in both (Fraunces, Instrument Serif, IBM Plex Mono, Tiro Tamil, LiPi Sans). | `evidence/snap/` |
| T3.2b | vs handout `Reader Side Rails` | ❌ **B-18**: left bar at rest is the expanded 208 px labelled list; handout: 62 px icon rail that expands on hover (shared Ui default `leftbar.open`). Tools/View rails: same sets and order (+ "More view options"). Pager centred ✅ (README: "centred, always visible"). | |
| T3.2c | Scales 1×, 1.25×, 1.5× (interface size) | ✅ reviewed side by side: proportional, no clipping/overlap; at 150 % the top-bar search collapses to its Ctrl K chip and theme names wrap to two lines (reasonable) | |
| T3.2d | 2× HiDPI (Weston `--scale=2`) | ✅ crisp text, wordmark, LiPicons — no blur | `T6-wayland-scale2.png` |
| T3.3 | 12 px corners | ✅ restored under mutter: all 4 corners rounded, measured inset consistent with r = 12 px; maximised: square; no WM / no compositor: square with a thin resize border | `evidence/corners/` |
| T3.4 | Button layout follows `gtk-decoration-layout` | eb65770: ✅ right, ✅ left, ❌ close-only (known). **f7d0034: ✅ all** — `:minimize,maximize,close`, `close,minimize,maximize:`, `appmenu:close`, `close:`, `close:maximize`, `minimize:`. ❌ new **B-19** (S4): with buttons on the left the top-bar brand cell widens past the left bar, so the top-bar divider no longer lines up with the left bar's edge | `evidence/buttons/` |
| T3.5 | Fonts actually loaded (`document.fonts`) | ✅ | T3.2a |
| T3.6a | Rails hover-expand (db28319) | ✅ Tools rail 64 → 228 px on hover with labels (Pages & outline, Add bookmark, Snapshot, Layers…) | `screenshots/T3-hover-tools-rail.png` |
| T3.6b | Keyboard focus | ⚠️ visible ring on every stop, but it is WebKit's default GTK blue (`auto 5px rgba(53,132,228,.8)`) — no designed `:focus-visible` style, so focus looks different per engine → **B-22**; Tab order starts with one "Send page N to a desk" button per page → **B-23** | `screenshots/B-22-*` |
| T3.6c | RTL | ✅ no `dir=rtl` anywhere; layout LTR throughout | |
| T3.7 | Five themes vs handout | ✅ **token-for-token identical** to the handout's `tokens.css`: light 21, dark 18, palm 18, indigo 18, contrast 19 tokens, 0 differences, 0 extras; all five apply at runtime (UI pass 09-theme-0…4) | |
| T3.8 | KDE (kwin) | 🔒 kwin not installable headless here; layout covered by GTK setting (T3.4) | |

## T4 Function
| ID | Case | Result | Evidence |
|---|---|---|---|
| T4.1 | Open (dialog, CLI), view, zoom, find, pager | ✅ (UI pass 10–13) | |
| T4.1b | Several files on CLI / `%F` | ❌ **B-04** | `screenshots/B-04-*` |
| T4.2 | Annotate + Save as new PDF, reopen | ✅ (UI pass re-run here; output is a valid 5-page PDF) | |
| T4.3 | Sign with certificate | 🔒 disabled in the build ("soon") — library/Sangam-gated, not a Linux defect | |
| T4.3b | Forms fill + save | 🔒 "Fill form" is a *Coming soon* placeholder in the shared Ui (`Reader.Shell.cs:483`) — same on Windows. Form PDFs render the same as poppler (own AcroForm fixture `evidence/form.pdf`) | |
| T4.4 | **Redaction really removes text** | ✅ Find & redact "print test" → Redact all (5) → Save redacted copy (GTK dialog): `pdftotext` 0 hits, **raw bytes 0 hits**, rest of text intact, 5 pages | `/home/claude/evidence/lt/redact/redacted.pdf` |
| T4.5a | Split → every page to a folder (db28319) | ✅ 5 files, 1 page each, each with its own "Page N" text |
| T4.5b | Split → extract range 2–4 | ✅ 3 pages, exactly pages 2, 3, 4 |
| T4.5c | Merge (Add open documents → Merge & Save) | ✅ 6 pages in order (five-pages 1–5, then the test page); both sources' fonts carried (Helvetica, embedded Ubuntu-Medium) | |
| T4.6 | Password: protect a copy | ✅ AES-256 copy (UI pass); limiting print/copy is library-gated (card says so) | |
| T4.6b | **Open a password-protected PDF** | ❌ **B-07** no prompt | `screenshots/B-07-*` |
| T4.7 | **Print is vector** | ✅ The app submits the **source PDF byte-identical** to CUPS (preserved spool file `cmp`-equal) — CUPS test page, `five-pages.pdf`, and a 3-page A3 drawing with 40,000 strokes/page. cups-pdf output: fonts present, text extractable, **0 images**. | `/home/claude/evidence/lt/print/` |
| T4.7b | Landscape pages | ❌ **B-14** printed at ~½ size on portrait paper | `screenshots/B-14-*` |
| T4.8 | No-printing permission (qpdf `--print=none`, owner pw only) | ✅ refusal message; no GTK dialog; **0 CUPS jobs** | |
| T4.8b | Print a file opened with its owner password (D-139, 7595ef3) | ✅ own qpdf fixture (user `u-pass`, owner `o-pass`, `--print=none`): user password → refused, 0 CUPS jobs; owner password → printed, 5 pages, fonts, 0 images (vector). CUPS receives an unencrypted copy (needed — a printer can't decrypt); no copy left in `/tmp` | |
| T4.9 | Word / Excel viewing | ✅ `sample.docx` renders in the Word view; `.xlsx` in the grid; ⚠️ known: shared-string index shown as value (Sheets 2.0.2, D-87) | |
| T4.10a | File dialogs (open/save) | ✅ GTK dialogs drive correctly | |
| T4.10b | Real drag from another app (GTK 4 file-list drag source, xdotool), 2 files (db28319) | ❌ **B-06 confirmed live**: drop accepted, only the first file opens. **Fixed f3d5978: 2 tabs ✅.** No overlay while dragging is correct: D-104 is the portal's overlay; a desktop overlay is option (c), noted for Arun | `screenshots/B-06-*` | |
| T4.10c | Clipboard text | ✅ selected page text → Ctrl+C → `xclip` returns it exactly | |
| T4.10d | Clipboard PNG (Snapshot → Copy to clipboard) | ✅ `image/png` (+ tiff/jpeg/bmp) offered; 543×362 PNG of real page pixels | `/home/claude/evidence/lt/clip/clip.png` |
| T4.10e | Show in folder with real Nautilus 46 (db28319) | ⚠️ opens the right folder — ❌ **B-21**: when the file manager needs > 5 s for its first window the app times out, falls back to `xdg-open` and the user gets two windows (the fallback one without the file selected). Proven with `dbus-monitor` (call 0 s, fallback at 5.01 s, Nautilus's successful reply at 7.99 s) | `screenshots/B-21-*`, `evidence/reveal/dbus-monitor.log` | |
| T4.11 | Single instance | ❌ **B-05** | `screenshots/B-05-*` |
| T4.12 | XDG folders | ✅ settings in `$XDG_CONFIG_HOME/Chuvadi/settings.json`; Documents via XDG; ⚠️ creates `~/Documents/Chuvadi Documents/{Finance,Legal,…}` category folders on first run — designed (Core `CategoryService`), not a bug | |
| T4.13 | Many tabs (30) | ✅ app ~500 MB + WebKit ~500 MB, plateaus; tab switch 33 ms; ⚠️ memory not returned after closing all (GC/WebKit cache behaviour, noted) | |
| T4.14 | Fresh profile shows sample recents | known (D-94 H-12) | |

## T5 Robustness
| ID | Case | Result |
|---|---|---|
| T5.1a | Truncated / garbage / no-EOF PDFs (isolated re-run, without the far-cell file) | ✅ no crash; truncated + garbage refused with a message (⚠️ raw parser wording, B-11); no-EOF opens normally |
| T5.1b | Bad `startxref` offset | ❌ **B-11** not repaired |
| T5.1c | Deep-nesting PDF | ✅ refused, no hang |
| T5.1d | Zip-bomb docx | ❌ **B-08** (S1) 4.5 GB, 10 min+ |
| T5.1e | xlsx cell at XFD1048576 | ❌ **B-09** (S1) 1.7 GB, never opens |
| T5.1f | Stuck open blocks later opens | ❌ **B-10** |
| T5.1g | Missing `document.xml` docx, not-a-zip xlsx | ✅ no crash; docx: clear message naming the missing part; ❌ xlsx: "Couldn't open this workbook: **EOCDNotFound**" — resource key (B-17) |
| T5.2 | Encrypted RC4-40 / RC4-128 / AES-128 / AES-256 | ❌ **B-07** (can't enter a password); no crash |
| T5.3 | **7.9 MB vector CAD PDF** (Arun's KDMC LINAC site layout, attached 9 Nov 05:46; 8,294,223 bytes, 5 × A1, ~1.44 M path operators, 170 images, 38 fonts, produced by Chuvadi). **Not committed — the repo is public; no screenshots of it either.** Build e242d92 | ✅ opens and renders correctly (lines, hatching, labels crisp at 180 %); all 5 pages; zoom; no errors. Time from process start (UI-test build, incl. ~2.8 s driver launch): "Opening…" gone **6.0 s** warm / 6.6 s cold, page drawn **6.9 s** warm (worst 7.2) / **7.5 s** cold (worst 11.9) — i.e. ~3–4 s to open + ~1 s to draw (poppler draws page 1 in ~1 s). Memory: app 835 MB after page 1, **1.6 GB** after all 5 pages (+ WebKit ~480 MB) → **B-27**. Print: the app sends the file **byte-identical** to CUPS ✅; the cups-pdf output is 5 page rasters (0 fonts) — but so is `lp cad.pdf` with no app at all: cups-pdf's Ghostscript pass rasterises this file itself; a real PDF-capable printer gets the vector file. ⚠️ frame-watcher "settled" (1.3 s) was the steady "Opening…" card, not the page — CAD timings above come from `tools/t_cadtime.py` |
| T5.4 | 30 tabs | ✅ (T4.13) |
| T5.5 | Low memory (600 MB cgroup) | ✅ starts, opens PDF, ~260 MB RSS |
| T5.6 | Read-only home | ❌ **B-16** crash at startup |
| T5.6b | Unreadable file (non-root, mode 000) | ❌ **B-17** resource key shown |
| T5.7 | No network (`--network none`) | ✅ starts and opens PDF; nothing tries to connect |
| T4.7c | **Remote CUPS** (faffa10) — a real second CUPS server in Docker (`tools/remote-cups/Dockerfile`, queue `RemotePDF` on port 6631), **local CUPS stopped** | ✅ via `CUPS_SERVER=localhost:6631` and, separately, via `~/.cups/client.conf` `ServerName` alone: GTK dialog on the remote server, jobs RemotePDF-1/-2 complete there; output 5 pages, fonts, 0 images (vector) |
| T5.7b | No printer / CUPS stopped | ✅ no crash, Cancel works — ❌ **B-20** (S4) empty dialog, no explanation |
| T5.8 | Locales en_IN, de_DE | ✅ start + open; ⏳ number/date formatting inside the UI not yet compared |
| T5.9a | Fresh non-root user, 24.04 and 26.04 | ✅ |
| T5.9b | Upgrade with existing settings | ✅ (T1.8b) |
| T5.9c | Corrupt `settings.json` | ✅ starts with defaults; ⚠️ silently overwrites the bad file (no `.bak`) |
| T5.10 | No working copies of documents in `/tmp` | ✅ (re-check for decrypted copies once B-07 is fixed) — ⚠️ unit tests leave `/tmp/chuvadi-test-*.pdf` behind (test hygiene) |

## T6 Wayland and X11
| ID | Case | Result |
|---|---|---|
| T6.1a | X11: Xvfb + mutter | ✅ (all of the above) |
| T6.1b | Wayland: Weston 13 headless (pixman), `GDK_BACKEND=wayland` | ✅ starts, renders Reader + PDF, restores tabs; first render 0.82–0.95 s |
| T6.1c | No WM at all | ✅ renders; square corners |
| T6.2a | 2× HiDPI (Weston) | ✅ crisp |
| T6.2b | Fractional 1.25× / 1.5× under Wayland (mutter 46 headless, `scale-monitor-framebuffer`) | ✅ app binds `wp_fractional_scale_manager_v1`, receives `preferred_scale(150)` / `(180)`, uses viewporter; layout correct (1800×1125 → 1440×900 CSS px at 1.25, 1200×750 at 1.5; rails keep 64/54 px). ⚠️ engine note: WebKitGTK renders at DPR 2 and the compositor scales down; WebView2 renders at the exact fraction — sizes identical, Linux text may be marginally softer (no pixels from headless mutter to judge) | `tools/wlrun.py`, `tools/setscale.py` |
| T6.3 | Drag-move / resize / max / min | ✅ drag/restore/maximise (UI pass 04); ⏳ minimise — the pass's step 05 failed on my environment (`xprop` missing), to re-run |
| T6.4 | Containers / no user namespaces | ❌ **B-15** hard abort |

## ARM64
CI artifact `linux-arm64/deb/chuvadi-reader_1.0.0~preview_arm64.deb` from run 42481652554 (f7d0034), in Docker `ubuntu:24.04` `linux/arm64` under QEMU user-mode:
| Case | Result |
|---|---|
| `apt install` of the arm64 `.deb` (deps resolve on arm64 24.04) | ✅ rc 0; `Architecture: arm64`, `Version: 1.0.0~preview` |
| `apt remove` | ✅ rc 0 |
| Launch | 🔒 **environment**: the app reaches "window + web view" (8.8 s emulated), then the .NET runtime throws `NullReferenceException` **inside `System.Array.Empty<T>()`** during DI resolution — impossible on a sound runtime; .NET under QEMU user-mode is unsupported (W^X/JIT). Not an app defect. Logs: `evidence/arm64-startup-error.log`, `evidence/arm64-app.log` |
**Sign-off for ARM64 launch/UI = the real arm64 CI runner** (green on f7d0034 per the Linux chat). Next session: download that run's UI-pass screenshots and judge them myself; optionally retry QEMU with `DOTNET_EnableWriteXorExecute=0`.

---

## Options for the coordinator

**O-1 ARM64 sign-off** — CI is allowed again (D-93). Recommendation: use the CI arm64 runner for the real sign-off (the Linux chat's run on f7d0034 is green); I add QEMU install/launch as an independent second check (done this session) and verify the CI artifact, not a local re-pack.

**O-2 B-12 — GPU-less first launch (WebKit GL compositing)**
| Option | Pros | Cons |
|---|---|---|
| A. When no DRM render node exists (shim already detects this for GTK), set WebKit's hardware-acceleration policy to *never* | first launch 2.9 s → ~1.1 s and every launch ~250 ms faster on VMs / remote desktops / thin clients; no effect on GPU machines | CSS transforms/animations composited in software → heavier scroll/zoom on very large pages; needs a measure on a real GPU-less laptop |
| B. Leave as is, document | no code | 1.7 s blank window on every new user and after every Mesa update on those machines |
| C. Splash/skeleton while the compositor warms | perceived speed | still 2.9 s to usable; adds UI |
**Recommendation: A**, gated on the render-node check, plus a scroll/zoom smoke on a big PDF to confirm no regression.

**O-3 B-15 — no user namespaces**
| Option | Pros | Cons |
|---|---|---|
| A. Detect before creating the web view (try `unshare(CLONE_NEWUSER)` in the shim); show a GTK message dialog with the fix (AppArmor profile / sysctl) and exit 1 | clear for users and admins; keeps the sandbox mandatory | small native code |
| B. Fall back to `WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1` | always starts | drops the web-process sandbox — against "nothing leaves this device" for untrusted documents. Not recommended |
| C. Leave as is | — | silent abort |
**Recommendation: A.**

**O-4 B-17 — resource keys** — A. remove `UseSystemResourceKeys` (Linux-only, a few hundred KB, immediate); B. own messages for every exception shown (shared, larger). **Recommendation: A now; B later with the Reader chat for friendlier wording on every platform.**

## Questions for the coordinator / Arun
1. The **7.9 MB vector CAD PDF** from the Reader chat's uploads — can Arun attach it here (or commit it to a test-fixtures path)? T5.3 is blocked without it.
2. ~~B-05 contract~~ — answered: on `platform/foundation` since 6 Nov; Linux builds against it. (My error.)
3. Routing done in BUGS.md (Linux / shared Ui/Core / library).

---

## Sign-off — Linux, f3d5978 + Foundation's 8th patch (e468d1a), 9 Nov 2026

**Ready (Linux side, verified by me on f3d5978).** Clean build (`-warnaserror`, 0 warnings) and tests (171 + 54 + 25); `.deb` self-contained and framework-dependent lintian-clean (`--pedantic`, 0 tags), installs/upgrades/purges on Ubuntu 24.04 and 26.04, desktop entry/MIME/icons valid, copyright correct for Sthraas and every font. Printing is vector (the source PDF goes to CUPS byte-identical; landscape pages rotate), no-print files refused, no-printer explained. Single instance on X11 and Wayland (token activation), several files from the command line, drops and hand-overs each in their own tab. Redaction removes the text. Split, extract, merge outputs correct. Clipboard text and PNG. Show in folder: one window. Read-only home, unreadable files, no namespaces, no network, 600 MB cap, en_IN/de_DE: all handled with plain messages. Five themes token-for-token with the handout; corners, button layouts (6), HiDPI 2× and fractional 1.25/1.5× correct. Startup: warm Home **1.0 s**, first PDF page **0.9 s**, a new user's first launch **1.1 s** (2-CPU, no-GPU sandbox). All 16 Linux-routed bugs (B-01, B-04–B-06, B-12–B-17, B-20, B-21, K-01, B-02 Linux part) **verified fixed**.

**Foundation's 8th patch — verified on e468d1a (9 Nov 01:50 IST):** B-02 (OFL text), B-03, B-07, B-10, B-11b, B-16, B-19, B-22, B-23 ✅; B-08/B-09 symptoms gone (bomb refused at once, far-cell opens in ~2 s); B-08b accepted on code (D-130): far-cell now opens in ~1 s so the 10 s Cancel note can't appear; a forced stall (named pipe) shows no Cancel — **B-24** (S2, shared, D-130 → Foundation's next patch): a stalled read gives a blank Reader and blocks later opens. Cancel is re-verified with B-24. Build 0 warnings, tests 187 + 59 + 25, lintian 0. **faffa10 (9 Nov 03:30 IST):** remote CUPS ✅ (env and client.conf, real remote server); B-17 WT-10 wording ✅ (PDF path); B-25 (S4, shared) Excel errors not yet on WT-10; build 0 warnings, lintian 0, Linux tests 44. Orientation kept (D-131). **Foundation 1016987 (local merge onto faffa10, 9 Nov 05:30 IST):** build 0 warnings, tests 199 + 59 + 44; Docs 2.0.0 / Sheets 2.0.2 in. ❌ **B-24 reopened** — stack dump shows `Reader.RefreshDocKind` → `FlattenService.Probe` → `PdfDocument.Open` on the UI thread (blocks on a stalled source, PDF and xlsx); B-08b's Cancel can't render for the same reason. ✅ B-25. Word/Excel cases: bomb refused ("too large… more than Chuvadi allows"), broken files plain messages, far-cell 1 s, 400k rows 1 s, bad shared-string index → "couldn't be read" (no wrong value shown). **Exact data ✅**: every text value in `fixtures/exact.xlsx`/`.docx` (double/leading/trailing spaces, case, misspelling, Tamil, tab, `00123`, line break) matches the file character for character and renders with whitespace kept (`pre` / `pre-wrap`); ❌ **B-26** Excel number formats not applied (values unaltered). B-18 **by design (D-133)**; the new collapse button gets a Linux check when it reaches the shared Ui. **Still open:** **B-24** (stalled reads, Foundation's next patch; B-08b re-verified with it).

**Waiting on the library (via Arun):** B-08a Chuvadi.Docs input limits · B-09a Sheets range layout (app side fixed) — fixtures in `fixtures/` · B-11a chuvadi-pdf xref rebuild · Sheets 2.0.2 shared-string fix (D-87) · form filling and certificate signing (*Coming soon* in the Ui).

**Waiting on Arun:** Windows end-to-end timings (D-51) for a side-by-side. (CAD PDF received and tested 9 Nov — T5.3.)

**Manual items for a real machine** (not possible in this sandbox):
1. Ubuntu 24.04 desktop with AppArmor on and a GPU: install the `.deb`, launch from the app grid, check the AppArmor profile loads and timings with a real GPU.
2. GNOME (Wayland) and KDE Plasma: window buttons, drag-move, snap/tiling corners, minimise (my run of the UI pass's step 05 failed only for a missing tool; CI's pass covers it).
3. Drag from Files/Dolphin onto the window; Show in folder with Files and Dolphin (selection highlighted).
4. A real printer: landscape/portrait mix, copies, a file opened with its owner password.
5. Fractional 125 %/150 % on a real HiDPI panel — judge text crispness (sizes already verified).
6. ARM64 hardware (or the CI runner's screenshots, judged by me): launch and UI pass.

### Re-verification on 7595ef3 (9 Nov 2026, 22:00 IST)
Build 0 warnings; tests 212 + 75 + 44; lintian 0. **B-24 ✅ and B-08b ✅** (stalled PDF/Excel/Word: "Opening…" < 1 s, Cancel at 10 s, Cancel closes the tab, later opens never blocked) · **B-25 ✅** (WT-10 wording + Details for Excel, Word, PDF) · **owner-password printing ✅** (D-139). Regression ✅: several files on the CLI, single instance (2nd/3rd launch), 2-file drop, Show in folder (one window, no fallback), vector print byte-identical. B-26 deferred by decision (D-147).

### Linux readiness (7595ef3)
**Ready for Arun's check.** Every Linux-routed and shared bug is verified fixed; **B-26 is deferred by decision (D-147)** — Excel shows the stored value, never a reformatted one (Arun's data-integrity rule); formatted display with the exact value on hover is a later option.
Waiting elsewhere, not Linux defects: **library** — B-08a (Docs limits; the app already refuses the bomb), B-09a library side (app side fixed), B-27 (CAD render time/memory, profile in `evidence/b27/`); **Reader chat** — the new left-bar collapse button (D-133; existing Collapse works on Linux); **Arun** — Windows timings (D-51).
**Real-machine checks** (unchanged, listed above in the sign-off): AppArmor + GPU desktop install; GNOME Wayland and KDE window behaviour; drag from Files/Dolphin and Show in folder there; a real printer (mixed orientation, copies, owner password); fractional scaling on a HiDPI panel; ARM64 hardware.

---

## Re-verification on 64c9c16 (10 Nov) — Foundation's patches 14–16: rendering off the Ui thread

This build was made from source with `-p:UiTest=true` and run on 2 vCPU, with no GPU. The tools are
`tools/t_final.py`, `t_multi.py`, `t_drag.py`, `t_print.py` and `t_render.py`. Arun's CAD file was run here only;
I've committed numbers only.

**Regression ✅**

| Case | Result |
|---|---|
| B-24 + B-08b Cancel | Stalled `.pdf`, `.xlsx` and `.docx`: "Opening…" shows in 0.3–0.4 s, Cancel appears at 10.1–10.3 s, Cancel closes the tab, and the next file opens. |
| B-25 | Excel, Word and PDF errors each show a WT-10 sentence with Details. |
| Owner-password printing (D-139) | Opened with the user password: printing refused, 0 CUPS jobs. Opened with the owner password: prints 5 vector pages. |
| Single instance | 3 files on the command line give 3 tabs. A second launch hands its file to the first window and exits: one window, 4 tabs. |
| Drops | The overlay shows; dropping 2 files gives 2 tabs. |
| Print | `five-pages.pdf` is submitted byte-identical, and the output is vector with fonts. |
| B-26 | Raw values, as decided (D-147). |

No new files appear in `/tmp`.

**Render steps**

| Step | Result |
|---|---|
| 36a fast paging (400 pages) | ✅ The page answers in ≤ 0.18 s while paging. After 150 PageDowns, the view settles 13–19 s after the last key (WebKitGTK's smooth scroll, a separate Linux finding), and the landed page is already drawn. 40 jumps through the page box, 50 ms apart: the landed page draws in 0.03 s. Page 400 draws in 0.04–0.52 s. |
| 36b closing a tab mid-render | Stand-in ✅: 3 of 3 closes, the next file draws in 0.33–0.37 s. Real CAD ⚠️: in 4 of 6 closes the next file draws in 0.17–0.62 s, but in the other 2 it takes **3.7 s and 4.6 s** (**B-29**). The page answers in ≤ 0.08 s throughout. |
| 36c Arun's CAD, on its own, 3 runs | **Sheet 1 draws in 6.0 / 7.1 / 8.4 s.** Sheets 2–3 take **10.5–13.5 s each**; sheets 4–5 are drawn in the background by the time I reach them; paging back is instant. The page answers in ≤ 0.23 s (once 1.22 s). See the memory table below. |
| 36c Linux's stand-in | **Sheet 1: 53–55 s. Sheet 2: not drawn after 4 min** (busy in `PageRasterizer.PaintStrokeOp`). Poppler draws a sheet in 0.9 s. |

Memory during 36c with Arun's CAD, app / WebKit, in MB:

| Point | Memory |
|---|---|
| Before opening | 248 / 221 |
| Sheet 1 drawn | ~880 / 290 |
| All 5 sheets | 1,430–1,770 / 570–680 |
| 60 s after closing | **unchanged** (**B-30**) |

The test-only full collection brings the app to ~460 MB, but 680 MB of managed heap is still live after closing.

**My own test had a measurement bug.** My first numbers were 0.3 s for sheet 1 and memory rising *after* closing.
Both were artefacts: the check counted the 24×24 loading icon as a drawn page. Linux's UI tests 36a–36c use the same
check, so their "sheets 0.1–0.2 s" figure doesn't measure the drawing either (**B-28**). With a check that waits for
the page-sized drawing, the numbers above are the real ones.

**Where this leaves Linux.**
- The regression set is clean.
- The UI stays responsive while heavy pages draw.
- Fast paging works.
- Heavy drawings are still slow to draw. **B-27** is the library's job: the stroke rasteriser.
- Memory isn't given back after closing (**B-30**).
- Closing mid-render can occasionally delay the next file (**B-29**).

`platform/linux` already has 4f67a4c after 64c9c16 ("nothing keeps drawing for a closed tab; memory back after vector
sheets"), and 3759b6f is on its way. On the next head I'll re-check 36c with the corrected check, 36b, and a quick
regression pass. **Linux is ready for Arun's check, with these known**, and the checklist below has moved to 64c9c16.

## Re-verification on 8dcf4d8 (10 Nov) — Foundation's patches 17–18

| Item | Result |
|---|---|
| B-28 | ✅ fixed |
| B-29 | ✅ fixed: the next file draws in 0.26–0.27 s, 6 of 6 |
| B-30 | ✅ the closed document is released (3–5 MB of heap left after a full collection). The memory gap after closing is recorded, not blocking |
| B-27 | Real CAD sheet 1 takes 5.6–6.9 s, sheets 2–5 take 3.4–5.6 s each (64c9c16: 10.5–13.5 s). The page answers in ≤ 0.39 s |

Memory with the real CAD file, app / WebKit, in MB:

| Point | Memory |
|---|---|
| Before opening | ~250 / 220 |
| 5 sheets | 1,400–1,490 / ~660 |
| +2 to +60 s after closing | 650–690 / ~600 |
| +90 s after closing | 360–580 / ~600 |

**Quick regression ✅**

| Case | Result |
|---|---|
| B-24 + B-08b Cancel | `.pdf`, `.xlsx` and `.docx`: "Opening…" in 0.3–0.4 s, Cancel at 10.0–10.3 s, Cancel closes the tab, and the next file opens |
| B-25 | Excel, Word and PDF errors follow WT-10 |
| Owner-password printing | User password: refused, 0 jobs. Owner password: 5 vector pages |
| Single instance | One window, 4 tabs |
| Drops | 2 tabs |
| Print | Byte-identical, vector |
| B-26 | Raw values, as decided (D-147; Sheets 2.0.4) |

No files are left in `/tmp`.

**Also seen:**
- Linux's render findings 1 and 2. A page-box jump made as sheet 1's drawing lands goes two sheets on, and the
  skipped sheet never draws (2 of 3 runs). This is with Foundation.
- CI x64 failed on UI step 36c (run 42723205272). arm64 passed and the packages were built. I couldn't reproduce
  the failure here; details are in BUGS.md.

**Where Linux stands.** The regression is clean, B-28, B-29 and B-30 are fixed, and drawing is about twice as fast
as on 64c9c16. Ready for Arun's check, with these known:
- B-27: sheets take seconds, not milliseconds.
- The memory gap after closing.
- Findings 1 and 2.
- A red x64 CI run.

## Sign-off — Linux d918161 (10 Nov) — superseded by bf60da9 below

**Build and CI.** Built from source. [CI run 42731544977](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42731544977)
is green on x64 and arm64; the red x64 36c from 8dcf4d8 is gone.

**Rendering, with Arun's real CAD file** (2 vCPU, no GPU):

| Item | Result |
|---|---|
| Sheet times (B-27) | Sheet 1 takes 4.7–4.9 s; each new sheet takes 2.9–4.9 s. The window answers in ≤ 0.22 s while sheets draw |
| Closing mid-render (B-29) ✅ | The next file draws in 0.26–0.28 s, 6 of 6 |
| Jumping to a page as sheet 1 lands (finding 2) ✅ | Lands on the right sheet, 3 of 3 |
| Paging back to a cancelled sheet (finding 1) ✅ | Every cancelled sheet draws when paged back to |
| Memory after closing (B-30) ⚠️ | Not back near the start (table below) |

Memory, app / WebKit, in MB:

| Point | Memory |
|---|---|
| Before opening | ~250 / 220 |
| 5 sheets | 1,830–1,960 / ~660 |
| First minute after closing | 565–680 / ~600 |
| 90–240 s after closing | 335–650 / ~600 |

So memory after closing is still not back near the start. The closed drawing's garbage outlives the relief passes,
and one more collection brings the app to ~300–335 MB. It's recorded and with Foundation, and it doesn't block (per
the coordinator).

**Quick regression ✅**

| Case | Result |
|---|---|
| B-24 + B-08b Cancel | `.pdf`, `.xlsx`, `.docx`: Cancel at 10.2–10.3 s, the tab closes, and the next file opens |
| B-25 | WT-10 wording with Details for Excel, Word and PDF |
| Owner-password printing | User password: refused, 0 jobs. Owner password: 5 vector pages |
| Single instance | One window, 4 tabs |
| Drops | 2 tabs |
| Print | Byte-identical |
| B-26 | Raw values (D-147) |

No files are left in `/tmp`.

**Ready.** Linux at d918161 is ready for Arun's check.
- Everything Linux-routed and shared is verified fixed: B-01 to B-25, B-28, B-29, and Linux's render findings 1 and 2.
- Deferred or by design: B-18 (D-133) and B-26 (D-147).
- Open, not blocking:
  - B-27: sheets take seconds; the fix is in the library's rasteriser.
  - B-30's memory gap after closing.
  - The library items B-08a, B-09a (library side) and B-11a.
- The real-machine checks above still need a real desktop: GPU, GNOME Wayland/KDE, a real printer, Files/Dolphin, and fractional scaling.

## Sign-off — Linux bf60da9 (10 Nov): ready for Arun

**Build and CI.** Built from source. [CI run 42756482625](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42756482625)
is green on x64 and arm64. This replaces the d918161 sign-off above.

**With Arun's real CAD file** (2 vCPU, no GPU):

| Item | Result |
|---|---|
| Memory after closing (B-30) ✅ | App back to 267–270 MB 2 s after closing, against 247–250 MB before opening. See the table below |
| Page images by address (36d) ✅ | All 5 sheets are pixel-identical to d918161 (same hash for every pixel). Each page's markup drops from 2.7–4.4 MB to 964 characters. Zooming in and out keeps the image; nothing goes blank |
| Fast paging ✅ | The page answers in ≤ 0.10 s, and the landed page is drawn |
| Close mid-render (B-29) ✅ | The next file draws in 0.25–0.28 s, 6 of 6 |
| Cancelled sheets ✅ | A page-box jump lands on the right sheet, and cancelled sheets draw when paged back to |
| Sheet times (B-27, open, library) | Sheet 1 takes 5.8–6.4 s; each new sheet takes 3.6–5.7 s. The window answers in ≤ 0.09 s |

Memory, app / WebKit, in MB:

| Point | Memory |
|---|---|
| Before opening | ~250 / 220 |
| 5 sheets | 862–985 / ~595 (was ~1.9 GB) |
| 2–60 s after closing | 267–270 / ~585 |

WebKit's web process keeps ~365 MB more than at the start; that is recorded.

**Intermittent fresh-open stall (reported by Linux): not reproduced** in 32 fresh starts, opened four ways, 12 of
them under CPU load. I did catch its starting state: 115 % zoom, with sheet 1 as a portrait placeholder. It
sometimes outlasts the first draw before the view fits. The steps and numbers are in BUGS.md. It's with Foundation,
and it doesn't block.

**Quick regression ✅**

| Case | Result |
|---|---|
| B-24 + B-08b Cancel | `.pdf`, `.xlsx`, `.docx`: Cancel at 10.1–10.3 s, the tab closes, and the next file opens |
| B-25 | WT-10 wording with Details for Excel, Word and PDF |
| Owner-password printing | User password: refused, 0 jobs. Owner password: 5 vector pages |
| Single instance | One window, 4 tabs |
| Drops | 2 tabs |
| Print | Byte-identical |
| B-26 | Raw values (D-147) |

No files are left in `/tmp`.

**Ready.** Linux at bf60da9 is ready for Arun's check.
- Everything Linux-routed and shared is verified fixed: B-01 to B-25, B-28, B-29, B-30, and Linux's render findings.
- Deferred or by design: B-18 (D-133) and B-26 (D-147).
- Open, not blocking:
  - B-27: sheets take seconds; the fix is in the library's rasteriser.
  - The intermittent fresh-open stall.
  - WebKit's memory after closing.
  - The library items B-08a, B-09a (library side) and B-11a.
- The real-machine checks still need a real desktop.

## Arun's check — Linux bf60da9

**Get the package.** GitHub → `Sthraas/chuvadi-reader-platforms` → Actions → run **Linux** on `bf60da9` ([run 42756482625](https://github.com/Sthraas/chuvadi-reader-platforms/actions/runs/42756482625), green) → Artifacts → **linux-x64** (ARM machine: `linux-arm64`). Unzip it and use **`deb/chuvadi-reader_1.0.0~preview_amd64.deb`** — the self-contained one (37.8 MB, needs no .NET; artifacts kept until 8 Feb 2027). SHA-256 `4bb65be7870e2f164257ae9db76a2f40aa5af42ed021a0e19916e83404e2c0b3`. (`deb-framework-dependent/` is the smaller variant that pulls in Microsoft's .NET runtime package.) Or with the CLI: `gh run download 42756482625 -R Sthraas/chuvadi-reader-platforms -n linux-x64`.

**Install** (Ubuntu 24.04 or 26.04, desktop):
```
cd ~/Downloads/linux-x64/deb
sha256sum chuvadi-reader_1.0.0~preview_amd64.deb      # compare with the value above
sudo apt install ./chuvadi-reader_1.0.0~preview_amd64.deb
```
It appears in the app grid as **Chuvadi Reader**; it also installs and loads its AppArmor profile. If the window ever opens blank, run `sudo apparmor_parser -r /etc/apparmor.d/chuvadi-reader` and start it again. To remove: `sudo apt remove chuvadi-reader` (`purge` also removes settings).

**Ten things worth trying first**
1. **Start from the app grid**, cold and again warm — note how long until Home shows (here: ~1.0 s warm on 2 CPUs without a GPU).
2. **Open a PDF by double-clicking it in Files**, then select **three files** → right-click → Open With → Chuvadi: each becomes its own tab in the one window.
3. **Drag two files from Files onto the window** — two tabs.
4. **The KDMC CAD drawing**: open it, page through all 5 sheets (try typing a sheet number, and jumping ahead then back), zoom in and out, close it. Note the time each sheet takes to draw, and the memory in System Monitor before opening, with 5 sheets, and just after closing. Here, on 2 CPUs with no GPU: sheet 1 takes ~6 s and each new sheet 4–6 s (B-27, known); the app goes from ~250 MB to ~0.9–1 GB with 5 sheets and back to ~270 MB on closing. Your real-hardware numbers are the useful ones. The window should stay responsive while it draws, and every sheet should draw and stay sharp. **One thing to watch for:** if a freshly opened drawing ever sits at 115 % with sheet 1 as a tall blank page and never draws, note exactly what you did just before. It's a rare stall we haven't been able to reproduce.
5. **Print to your real printer**: a mixed portrait/landscape file, 2 copies; check it's crisp (vector), and that a file whose permissions forbid printing is refused — then works when opened with its owner password.
6. **A password-protected PDF**: wrong password, then the right one.
7. **Mark → annotate → Save as**, and **Protect → Find & redact** a word → Save redacted copy — then search the saved copy for the word (it must be gone).
8. **Word and Excel files** of your own — the data should read exactly as in the file (spaces, spelling, case untouched); Excel numbers show their stored value (D-147).
9. **Document ▾ → Show in folder** opens Files with the file selected; **Snapshot → Copy** then paste into another app.
10. **Settings**: switch the five themes and the interface size; change GNOME's window-button layout (Tweaks → Window Titlebars) and see the buttons follow; maximise and restore (corners square when maximised, rounded otherwise).

Anything odd: note the step and what you saw; I reproduce it here and file it in `BUGS.md`.
