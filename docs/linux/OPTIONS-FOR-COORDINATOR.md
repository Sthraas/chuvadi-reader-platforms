# Linux — open options for the coordinator

6 Nov 2026. Each with pros, cons and a recommendation. L-1 to L-3 are carried over from session 1.

## L-1 Which Ubuntu releases (and GTK)
| Option | Pros | Cons |
|---|---|---|
| **A. 24.04 + 26.04, GTK 4 + WebKitGTK 6.0** (built and tested) | current toolkit; portal file dialogs (GNOME and KDE each show their own); fractional scaling; nothing to redo | 22.04 not supported (standard support ends April 2027) |
| B. A + 22.04 | 22.04 users until April 2027 | 22.04 has GTK 4.6: no `GtkFileDialog` (4.10+) — a second dialog path kept 5 months; another CI image |
| C. GTK 3 + WebKitGTK 4.1 everywhere | widest reach | legacy toolkit, weaker on high-DPI; the move to GTK 4 would be redone later |

**Recommendation: A.**

## L-2 .NET runtime in the .deb
| Option | Download / installed (amd64) | Pros | Cons |
|---|---|---|---|
| **A. Self-contained** (built, default today) | 36.7 MB / 105 MB | no dependency on Ubuntu's .NET; one known runtime; the same folder works for any later format | bigger; we ship .NET security fixes ourselves (rebuild + release) |
| B. Framework-dependent (built, `--framework-dependent`) | 10.7 MB / 25 MB + `dotnet-runtime-10.0` (~70 MB, shared) | small; Ubuntu patches the runtime | runtime version varies per machine; Ubuntu's .NET build, not Microsoft's |

**Recommendation: A** (predictable behaviour; startup measured on that build). B stays one flag away.

## L-3 Window buttons: the desktop's layout
Built: the side comes from the desktop (`gtk-decoration-layout`: GNOME's `button-layout`, KDE's GTK
settings). The Ui's `WindowButtons` draws the full set on either side.

| Option | Pros | Cons |
|---|---|---|
| **A. Side only** (built) | no Ui change; matches Ubuntu's default (`:minimize,maximize,close`) and KDE's | vanilla GNOME's default is close only (`appmenu:close`): we still show minimise and maximise |
| B. Exact set and order | true to every desktop's setting | Ui change: `WindowButtons` takes a list (existing-file hook in MainLayout for the right-hand side, which is inline today) |

**Recommendation: A now**; B if Arun wants vanilla-GNOME exactness (small Ui hook, Foundation's combined patch).

## L-4 AppImage (kickoff asked)
| Option | Pros | Cons |
|---|---|---|
| **A. No AppImage; .deb only** | one format, tested; installs the AppArmor profile WebKit's sandbox needs on 24.04+ | no "download and run" file |
| B. AppImage as well | runs without installing; other distributions | **can't install the AppArmor profile**: on Ubuntu 24.04+ WebKit's sandbox can't start, so it would need the sandbox switched off — not acceptable; FUSE 2 is no longer installed by default either |

**Recommendation: A.** If other distributions matter later: Flatpak or Snap, which carry their own confinement.

## L-5 Printing route while the library is pending
Built: every job goes as the PDF itself to CUPS (`IppDocumentTarget`), which converts it with its own
filters. The library's router (`IppRoutes.CreateCupsRouter`) only sends a PDF as-is when the job says
every font is embedded, and its raster fallback needs `Chuvadi.Print.Pdf.Raster`, which isn't released.

| Option | Pros | Cons |
|---|---|---|
| **A. As-is to CUPS now; the router when the adapter ships** (built) | prints every PDF, vector, D-06 as written | a PDF with non-embedded unusual fonts prints with CUPS's substitutes (standard 14 fonts are metric-compatible) |
| B. Router only | the library decides PDF vs raster | today a PDF with any non-embedded font can't print at all |

**Recommendation: A.** Library asks for Arun: (1) release `Chuvadi.Print.Pdf.Raster` (the raster
fallback); (2) a font inspector for the router (`PrintRouter.FontInspector`) from chuvadi-pdf; (3)
`IppJobTicket` always sends paper size, colour and orientation — a "printer default" (null) would help
queues whose default differs (the host avoids it today by passing the dialog's paper size).

## L-6 Printer dialog
| Option | Pros | Cons |
|---|---|---|
| **A. GTK's print dialog after the Print card; Chuvadi.Print.Ipp sends** (built) | the card's own text says "The printer dialog opens next" (as on Windows); printer choice and every queue option; our library in the path | the dialog repeats pages/copies (preset from the card) |
| B. GTK prints the file itself (`GtkPrintJob`) | GTK honours every dialog choice by itself | Chuvadi.Print not used; no audit trail, no future raster route |
| C. No dialog: default printer | simplest | no printer choice; the card's text becomes untrue |

**Recommendation: A.**

## L-7 Opening a file while Chuvadi is running
"Open with" starts a second copy — the same as Windows today (no single-instance handling there).

| Option | Pros | Cons |
|---|---|---|
| **A. Same as Windows** (built) | parity; no change | two windows, two sets of tabs |
| B. Single instance (D-Bus on Linux, a named pipe on Windows): the file opens as a new tab in the running app | what users expect from a tabbed reader | a behaviour change for Windows too (Arun's call); new code on both hosts |

**Recommendation: A now, B as a programme-wide item for Arun.**

## L-8 Print permission in protected PDFs
Windows prints a protected file even when its permissions forbid printing (it renders with the password);
Linux does the same for parity.

| Option | Pros | Cons |
|---|---|---|
| **A. Keep parity** (built) | no behaviour change | a file that says "no printing" prints |
| B. Respect "no printing" on every platform | honours the author's setting | behaviour change on Windows (a bug fix to list for Arun) |

**Recommendation: B, as a listed bug fix for Arun** (Core/Windows change; Linux follows).

## L-9 Small items
1. **Foundation `DesktopAppPaths`**: returns no save folder when `~/Documents` doesn't exist, so Core
   saves under `/tmp`. Linux works around it in `LinuxAppPaths`; propose the same fallback in the kit.
2. **`ci/packages`**: `Chuvadi.Print` and `Chuvadi.Print.Ipp` 1.0.0-rc.2 added on `platform/linux` (SHA-256s
   in BUILD-LOG §18) — please adopt centrally or tell me to move them.
3. **Placeholders for Arun** in the package: app ID `in.chuvadi.Reader`, Maintainer
   `Sthraas Intelligence Pvt Ltd <maintainer@chuvadi.in>`, Homepage `https://chuvadi.in`, licence
   (the repository has no licence file).
4. **`platform/linux-probe`**: a finished temporary branch; I can't delete it from here.
