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
| T4.8b | Print a file opened with its owner password | 🔒 can't open with a password (B-07) | |
| T4.9 | Word / Excel viewing | ✅ `sample.docx` renders in the Word view; `.xlsx` in the grid; ⚠️ known: shared-string index shown as value (Sheets 2.0.2, D-87) | |
| T4.10a | File dialogs (open/save) | ✅ GTK dialogs drive correctly | |
| T4.10b | Real drag from another app (GTK 4 file-list drag source, xdotool), 2 files (db28319) | ❌ **B-06 confirmed live**: drop accepted, only the first file opens. No drop overlay while dragging — expected until Foundation's D-104 overlay lands (not on `platform/linux` yet); retest then | `screenshots/B-06-*` | |
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
| T5.3 | 7.9 MB vector CAD PDF | 🔒 file not reachable from here — **needs Arun / the Reader chat's upload**. Stand-in: 1.6 MB, 120,000-stroke A3 drawing views and prints vector ✅ |
| T5.4 | 30 tabs | ✅ (T4.13) |
| T5.5 | Low memory (600 MB cgroup) | ✅ starts, opens PDF, ~260 MB RSS |
| T5.6 | Read-only home | ❌ **B-16** crash at startup |
| T5.6b | Unreadable file (non-root, mode 000) | ❌ **B-17** resource key shown |
| T5.7 | No network (`--network none`) | ✅ starts and opens PDF; nothing tries to connect |
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
