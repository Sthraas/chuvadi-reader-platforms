# Linux Test — test plan

Chat: **Linux Test** (opened by D-92). Subject under test: `platform/linux` at **eb65770**
("Linux build log: whole workflow green locally; build complete"). Independent of the Linux chat's own
harness: I use its tools where they are the only driver into the app (`UiTestDriver`, `uitest_lib.py`), but
every pass/fail is judged on my own evidence (pixels, files, CUPS output, process state), not on its reports.
Rule: **nothing passes until I have seen it work.**

## Environment
| | Where | Notes |
|---|---|---|
| Ubuntu 24.04 x64 | this sandbox (2 vCPU, 7 GB, no GPU, root, no systemd) | build, timing, UI, print |
| Ubuntu 24.04 x64 clean | Docker `ubuntu:24.04` | install from `.deb` only, fresh user, no SDK |
| Ubuntu 26.04 x64 | Docker `ubuntu:26.04` | install + launch + UI subset (Xvfb inside) |
| ARM64 | **pending CI confirmation** (D-90: no Actions runs). Option: QEMU user-mode in Docker for install/launch only — never for timing | see Options |
| Wayland | Weston headless (`--backend=headless`) + `GDK_BACKEND=wayland`; mutter `--headless --wayland` if it starts | |
| X11 | Xvfb + mutter (GNOME WM), Xvfb + kwin_x11 if installable, Xvfb with no WM / no compositor | |
| Reference | `docs/design-handoff/*.dc.html` in headless Chromium (test tool); Windows look = Ui in Chromium via the Foundation's dev-only preview host (WebView2 is Chromium) | no Windows machine here |

Test tools (never shipped): Xvfb, Weston, mutter, xdotool, xclip/wl-clipboard, ImageMagick, poppler-utils,
qpdf, lintian, cups + cups-pdf, Playwright/Chromium, strace, python.

## T1 Build and package from clean
| ID | Case | Pass when |
|---|---|---|
| T1.1 | Empty NuGet cache (`~/.nuget` removed), fresh clone, `scripts/setup-feed.sh` | feed has every `ci/packages` file; restore uses no nuget.org package other than Microsoft's |
| T1.2 | `dotnet build src/ChuvadiReader.Linux -c Release -warnaserror`; native shim `-Werror` | 0 warnings, 0 errors |
| T1.3 | Both test projects | all pass |
| T1.4 | Restore sources audit (`project.assets.json`) | only Microsoft.* / System.* and Arun's Chuvadi.* / LiPicons.* |
| T1.5 | `setup-feed.sh --verify-pack` (check only) | same package set as tag v3.31.2 |
| T1.6 | `.deb` self-contained + framework-dependent, amd64 | builds; `lintian` — every error and warning listed |
| T1.7 | `.deb` arm64 | when CI confirmed (or QEMU, see Options) |
| T1.8 | Install / remove / purge / reinstall / upgrade (old version → new) in clean 24.04 and 26.04 containers | apt resolves deps on each release; no files left after purge; settings survive upgrade |
| T1.9 | Desktop entry, `%F`, icon sizes, MIME (`application/pdf`, docx, xlsx), `desktop-file-validate`, `appstreamcli validate` | clean; `xdg-mime` default is ours; `gtk-launch` with 2 files opens both |
| T1.10 | `/usr/share/doc/chuvadi-reader/copyright` | names Sthraas Intelligence Pvt Ltd; proprietary licence |
| T1.11 | Package contents audit: every file in `/usr/lib/chuvadi-reader` | only .NET (Microsoft), our assemblies, Chuvadi libs, `libchvdhost.so`; `ldd` of every `.so` resolves only to OS packages (GTK, GLib, WebKitGTK, libc, ICU, OpenSSL); no Windows-only assemblies (e.g. `Rendering.Wpf`) shipped |
| T1.12 | Release build contains no test code | no `UiTestDriver` type in the shipped `chuvadi-reader.dll` |

## T2 Startup speed (ms)
≥ 10 runs each, median and worst. Probe: `CHUVADI_TIMING=1` stage marks plus my own independent check — an
external screenshot loop (first frame with real content) so the app's self-report is cross-checked.
| ID | Case |
|---|---|
| T2.1 | Cold: page cache dropped (`echo 3 > /proc/sys/vm/drop_caches`) before each run — window on screen, first rendered frame (dashboard) |
| T2.2 | Warm: back-to-back launches |
| T2.3 | Time to first PDF page visible, `chuvadi-reader five-pages.pdf`, cold and warm |
| T2.4 | Installed `.deb` (self-contained) vs framework-dependent |
| T2.5 | Compare with BUILD-LOG §21/§26/§33 and Foundation `STARTUP.md` (Windows) |

## T3 Design fidelity
| ID | Case |
|---|---|
| T3.1 | Screens: Home, Library, Reader (each rail: Left, Tools, View, page strip, each card), Mark, Arrange/Bench, Protect, Settings (every section), 5 themes |
| T3.2 | Scales 1×, 1.25×, 1.5×, 2× (`GDK_SCALE`/`GDK_DPI_SCALE`, Weston `--scale`, and the app's interface size) — side-by-side sheets vs handout frames and vs the Ui in Chromium |
| T3.3 | 12 px corners: restored (rounded), maximised / tiled / full screen / no compositor (square) — pixel crop at 8× |
| T3.4 | Window buttons follow `gtk-decoration-layout`: Ubuntu default, vanilla GNOME `appmenu:close`, KDE-like `:minimize,maximize,close`, left `close,minimize,maximize:` |
| T3.5 | Fonts loaded (Fraunces, Instrument Serif, LiPi Sans, Plex Mono) — `document.fonts` check, not only visual |
| T3.6 | LiPicons render; hover, focus-visible rings via keyboard Tab; no RTL leakage (`dir`) |
| T3.7 | Every pixel difference above noise is a bug or an explained engine difference |

## T4 Function (parity with Windows Reader)
| ID | Case |
|---|---|
| T4.1 | Open (dialog, CLI, `%F`), view, zoom, find, pager |
| T4.2 | Annotate (Mark tools), save, Save as; reopen and verify with qpdf/pdftotext |
| T4.3 | Sign (certificate signature as far as the build enables it), forms fill and save |
| T4.4 | Redact — text really removed (`pdftotext`), not just covered |
| T4.5 | Arrange: reorder, rotate, delete, merge, split — verify page count/order of output |
| T4.6 | Encrypt / password, open encrypted with right and wrong password |
| T4.7 | Print to CUPS PDF queue: output is **vector** (`pdffonts` shows fonts, `pdfimages -list` no full-page images, text extractable); pages/copies/collate |
| T4.8 | No-printing file refused, no CUPS job; owner-password case recorded (D-71) |
| T4.9 | Word and Excel viewing as far as the libraries allow (Layout not released — note, not a bug) |
| T4.10 | File dialogs (open/save via portal), window drop of 1 and of several files, clipboard text + PNG (both directions), Show in folder (D-Bus FileManager1 with a stub service, and fallback) |
| T4.11 | Single instance: second launch → files into the running window, one tab each; Wayland activation token. (D-83 approved; BUILD-LOG says waiting on the Foundation contract — tested and reported as found) |
| T4.12 | XDG: `XDG_CONFIG_HOME`, `XDG_DOCUMENTS_DIR` honoured; nothing written outside them |

## T5 Robustness
| ID | Case |
|---|---|
| T5.1 | Damaged PDFs (truncated, bad xref, garbage), damaged docx/xlsx (zip bombs, missing parts) — message, no crash, no hang |
| T5.2 | Encrypted (user password, owner-only, RC4/AES-128/AES-256) |
| T5.3 | Very large: the 7.9 MB vector CAD PDF (**needs Arun / the Reader chat's upload — not reachable from here**); stand-in: generated 500-page and heavy-vector PDFs |
| T5.4 | Many tabs (30+), memory over time |
| T5.5 | Low memory (cgroup / `systemd-run`-free: `ulimit -v` and a memory-capped container) |
| T5.6 | Read-only home; missing `~/Documents`; full disk on save |
| T5.7 | No printer / CUPS stopped; no network (`--network none` container) |
| T5.8 | Locale `en_IN.UTF-8`, `ta_IN`, `de_DE` (comma decimal) — numbers, dates, sizes |
| T5.9 | Fresh user; upgrade with existing settings (corrupt `settings.json` too) |

## T6 Wayland and X11
| ID | Case |
|---|---|
| T6.1 | Launch + full smoke under Weston (Wayland) and Xvfb/mutter (X11) |
| T6.2 | HiDPI 2× and fractional 1.25×/1.5× under Wayland (`wp_fractional_scale`) — crisp text, correct hit targets |
| T6.3 | Drag-move, resize edges, maximise/minimise under both |
| T6.4 | KDE: kwin if installable in the sandbox, else button layout via GTK settings only (noted as a limit) |

## Reporting
`RESULTS.md` (every case, pass/fail, evidence), `BUGS.md` (steps, expected, actual, evidence, severity
S1 crash/data loss · S2 feature broken · S3 wrong but usable · S4 cosmetic), `screenshots/`.
Bugs go to the Linux chat through the coordinator; I re-verify each fix on its commit.

## Options for the coordinator
**O-1 ARM64 before CI is back**
| Option | Pros | Cons |
|---|---|---|
| A. Wait for CI (`ubuntu-24.04-arm`) | real hardware; real timing | blocked until billing is confirmed |
| B. QEMU user-mode in Docker now | install/launch/UI checks on arm64 today, no cost | very slow; timing meaningless; WebKit under emulation may misbehave for reasons that aren't ours |
| **Recommendation:** B now for install + launch only, A for the real ARM64 sign-off. |
