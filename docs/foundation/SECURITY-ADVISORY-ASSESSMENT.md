# Security advisory (library D-405, D-406): what it means for the Reader

Foundation, 17 Nov. **An assessment only: no code was changed.** Read against the work branch (Reader main 24b2bac plus patch 32) and the host branches as of 16 Nov (`platform/web` 35a7add, `platform/mac` 9631897, `platform/linux` b08b0e5, `platform/android` 582b3be).

## 1. Short answer

- **The Reader opens outside files on every host, in the app's own process on four of five.** Windows, Mac, Linux and Android parse in the app process. Only the portal has a separate process, one worker per signed-in person.
- **PDF is the open door.** Every PDF open in the shared code passes no limits: 51 call sites in 18 files (the coordinator's count of 39 is of the same sites, counted differently). Word and Excel already use the library's untrusted-input limits.
- **Limits alone do not close it on Pdf 3.32.0.** The library's limits are honoured by the rasteriser and the text extractor, and the Reader draws pages through the SVG renderer. Measured here: a 1 MB PDF that unpacks to 560 MB ran 27 seconds and ended in out-of-memory, the same with limits set as without.
- **The three features named in item 3 all ship today** on Pdf 3.32.0: Protect (redaction), the signature check with the system trust store, and Arrange's page operations.
- **Several advisory items do not touch the Reader** because it does not use those libraries or options: Layout, the Sheets import options, zip extraction, spool files and the hub.
- **I could not reproduce the stack overflow.** Twelve obvious crafted PDFs (deep nesting, cycles, self-drawing forms) were all refused or drawn safely by 3.32.0. The files that do overflow are the library chat's; we need them to measure what we are exposed to.

## 2. Item by item

Hosts: W Windows, M Mac, L Linux, A Android, P portal. "All" means all five, through the shared Core.

| # | Advisory item | Applies to the Reader? Where | What we do today | Possible now, on the versions we have | Needs the patched versions |
|---|---|---|---|---|---|
| 1 | Parse in a separate worker process with a memory cap and a time limit | Yes, all hosts. Every viewer and tool in Core | W, M, L, A: parsed inside the app process; no cap, no time limit. P: one worker process per person, managed-heap cap 1,536 MB, no time limit on a parse | P: add an operating-system memory cap and a per-operation time limit to the worker (Web chat). Desktop and Android: a parse helper process is new architecture, not a setting (see section 4) | The stack-overflow fixes themselves. Without them, only process isolation contains the crash |
| 2a | `XlsxReaderOptions.ForUntrustedInput()` | Yes, all. `XlsxViewService` | **Done.** Set on every Excel open, with cancellation | Nothing more | Sheets 2.2.1 for the fixes behind it |
| 2b | `DocxReaderOptions.ForUntrustedInput()` | Yes, all. `DocxViewService` | **Done** (B-08, D-168) | Nothing more | Docs 2.4.1 |
| 2c | `LayoutLimits.ForUntrustedInput()` | No. The Reader does not reference Chuvadi.Layout; Word pages are laid out by the Reader's own code | Not used | Nothing | Applies only if Phase 2 brings Layout in |
| 2d | Sheets: `ApplyConditionalFormats` false, no `AutoDetectLayout.Open` on uploaded xlsx | Those two options: no, they do not exist in Sheets 2.0.4 and the Reader does not call them. **But** `XlsxViewService` does evaluate conditional formats through the model (`EvaluateConditionalFormats`) so the sheet shows its colours | Conditional formats are evaluated on every sheet shown | If the library chat confirms the weakness is in the evaluation itself: show sheets without conditional colours until 2.2.1 (a visible change, Arun's call) | Sheets 2.2.1. **Question for the library chat:** is `EvaluateConditionalFormats` on 2.0.4 affected? |
| 2e | `UseEmbeddedFonts` false for SVG export | Yes, all. The page view (`ChuvadiPdfReader`) and Export to SVG both use the SVG renderer | The option does not exist in 3.32.0 or 3.33.0. The Reader uses the default, which embeds the file's own fonts | The nearest setting today is `FontStrategy = CssFallbackOnly`. It makes every page draw in substitute fonts: pages would no longer look like the file. Not recommended as a blanket change | Pdf 3.35.1 for the fix and the new option |
| 2f | `MaxCharactersPerBlock` about 5,000 | No. Not in Docs 2.1.0; it belongs to Layout | Not used | Nothing | Applies only with Layout |
| 2g | `ZipExtractionLimits.Untrusted` | No extraction anywhere. P uses Chuvadi.Zip 1.0.0 only to **write** the download bundle. Core reads an xlsx's zip table with .NET's own reader, only after the library has refused the file, and unpacks nothing | Nothing unpacked | Nothing | P should still move to Zip 1.0.2 with the rest |
| 2h | Size-check spool files, accept only from the hub | No. The Reader has no hub and reads no spool files | Not used | Nothing | Nothing |
| 2i | Print only to known printers over ipps with a pinned certificate | L only. `CupsPrintService` uses Chuvadi.Print.Ipp 1.0.0-rc.2. W prints through Windows' own spooler; M and A through the system print panel | L sends to the local CUPS, or to a CUPS server address the user's system names, as `ipp://` (not encrypted, no pinned certificate) | L could refuse any server that is not the local CUPS until the patch (Linux chat; a behaviour change) | The Print patch, and a decision on remote CUPS servers |
| 2j | Pdf: resource limits on every outside PDF | Yes, all. 51 open sites in 18 files, including the viewer, Library, folder search, properties, Arrange, Protect, sign, stamp, print (W) | **None set anywhere** | One shared open helper in Core that every site uses, with `PdfLimits` (input size, page count, decoded bytes, memory, operators, pixels). Worth doing once, in Phase 2. On 3.32.0 it protects text extraction, search and raster pages, **not** the SVG page view (measured, section 3) | Pdf 3.35.1 for limits that hold on the SVG path |
| 2k | Pdf: XFA scripts off | Not reachable today. The Reader does not reference Chuvadi.Pdf.Xfa (the script engines live there). It reads XFA values as data and shows "dynamic XFA, cannot display" | No script is run | Nothing | Check again when Phase 2 takes 3.35.1, in case Flatten starts to run calculations |
| 3a | Do not ship Pdf redaction until 3.35.1 | Yes, all. Protect: `RedactService` (11 open sites), Pdf.Redaction 3.32.0 | **Ships** on Windows; in the shared Ui for the other hosts | Hold it back or warn (section 5) | Pdf 3.35.1 |
| 3b | Do not ship signature verification with a trust store until 3.35.1 | Yes. `SignatureCheckService`, with `UseSystemTrustStore` true by default (reads the system root store) | **Ships**; the verdict "trusted" is shown to the user | Hold back, warn, or show the check without the trust verdict (section 5) | Pdf 3.35.1 |
| 3c | Do not ship page operations on files with hidden layers until 3.35.1 | Yes. Arrange (`BenchComposer`, `BenchService`), `PdfToolsService` (merge, split, rotate, delete), and the tools that rewrite a file (stamp, flatten, compress) | **Ships**. The Reader knows a file's layers (the Layers panel) but page operations do not check for them | Detect layers and warn or refuse (section 5) | Pdf 3.35.1 |

Other files the Reader opens (text, Markdown, HTML, CSV, images) do not go through the Chuvadi libraries and are outside this advisory. Text files already have a size limit.

## 3. What was measured here (test only, nothing shipped)

A small probe opened and drew twelve crafted PDFs with Pdf 3.32.0, once with no limits and once with `PdfLimits` set.

| Crafted file | Result on 3.32.0 |
|---|---|
| Arrays or dictionaries nested 200,000 deep in the catalog | Refused cleanly: "nested 200001 levels deep; the limit is 512" |
| Page tree 50,000 levels deep | Opens; drawing refused cleanly (depth limit 1,024) |
| Page tree that points back to itself; resources that point to the page; an object that is a reference to itself; outline that loops | Open and draw safely |
| A form that draws itself; a function that contains itself | Draw safely |
| Array nested 200,000 deep inside page content; 300,000 unbalanced saves | Draw safely |
| **1 MB file that unpacks to 560 MB of page content** | **27 seconds, then out-of-memory. Identical with limits set**: the SVG renderer does not apply them |

So: 3.32.0 already guards the obvious recursion cases, and I have no file that produces the uncatchable stack overflow. That is not evidence that we are safe; it means the dangerous files are specific. **Ask for the library chat:** the reproducer files (or their recipe), so each host can be measured.

## 4. What a crash means on each host

A .NET stack overflow cannot be caught: the process ends at once.

| Host | Where files are parsed | A stack overflow | Memory or time runaway |
|---|---|---|---|
| Windows | In the app process | The app closes without a word. Unsaved marks, bookmark edits, redaction areas and Arrange desks are lost (the ask-before-closing card cannot run; drafts are not built yet, D-190). Files on disk are untouched. A file in Recents would crash again when reopened | No cap. The app can take the machine's memory; the user ends it by hand |
| Mac | In the app process | Same as Windows | Same |
| Linux | In the app process | Same as Windows | Same |
| Android | In the app process | The app closes; the system may show "app keeps stopping" | The system kills the app when it runs out of memory |
| Portal | In that person's worker process | **Only that person's worker dies. The gateway survives**: it is a separate process, it logs "worker ended with code …", clears the worker's folder, and shows that person "Your session stopped, please reload". Their open documents and unsaved work in that session are gone. Other people are not touched (Web Test has killed and frozen workers on purpose: WT-24 evidence) | **Memory cap: yes, partly.** `DOTNET_GCHeapHardLimit` at 1,536 MB caps the managed heap only; there is no operating-system cap on the whole process. **Time limit: no.** A parse that spins keeps a core busy; the health check still answers, so the worker is not stopped until the person leaves. With 40 worker slots, a few such files could hold the server's processors |

## 5. Options for Arun

### A. The patched libraries and Phase 2

| Option | For | Against |
|---|---|---|
| **A1. Make the patched libraries a gate for Phase 2: the Reader takes Pdf 3.35.1, Sheets 2.2.1, Docs 2.4.1 (and Print, Zip on the hosts that use them) in the one library move (D-186). Recommended** | One move, one round of proof on every host. The fixes are real fixes, not app-side workarounds (D-161). The shared open helper with limits (2j) goes in at the same time, where the limits actually hold | Phase 2 waits for the library releases. Until then production stays exposed as described |
| A2. Add app-side settings now on today's versions, take the libraries later | Something lands sooner | Little to gain: limits do not hold on the SVG view in 3.32.0, and the overflow cannot be stopped by settings. Two rounds of proof on five hosts for a partial result |
| A3. Take only the Pdf patch early, the rest in Phase 2 | Closes the largest door first | Breaks "one move"; Pdf has moved three minor versions (3.32 to 3.35), so it is a full re-proof anyway |

### B. A separate parse process on desktop and Android (advisory item 1)

| Option | For | Against |
|---|---|---|
| **B1. Not now. Rely on the patched libraries for desktop and Android; harden the portal worker (operating-system memory cap, time limit per operation). Recommended** | The portal is where one person's file can affect others, and it already has the process boundary. Desktop apps open the user's own files; a crash costs that user their unsaved work, which drafts (D-190, later) will soften | Desktop and Android stay "app dies" for any future overflow bug |
| B2. Build a parse helper process for every host now | Full containment everywhere | Large new architecture: every page draw crosses a process boundary, which costs startup and page speed (a stated priority), and Android cannot start helper processes the same way. Would be redone if the design is rushed |
| B3. Run parsing on a thread with a larger stack | Cheap | Does not stop an unbounded overflow, only delays it. Not a fix |

### C. Protect (redaction), signature check, page operations on files with hidden layers, until Pdf 3.35.1

| Option | For | Against |
|---|---|---|
| C1. Hold all three back (hide them) until 3.35.1 | Nobody relies on a result we cannot stand behind | Removes shipped features from Windows users; three behaviour changes to prove and then undo |
| **C2. Warn, do not hide. Recommended, with one condition below** | Honest and small. Protect: a line before making the redacted copy that it must not be relied on for sensitive material until the next update. Signature check: show what the signature says but not the "trusted" verdict, or mark the verdict as unconfirmed. Page operations: when the file has layers, say so and ask before going on | Users may ignore a warning. Still three small Ui changes |
| C3. Leave as is until Phase 2 | No work now | A redacted copy that might still hold the text, or a "trusted" verdict that might be wrong, is the worst kind of failure: silent |

**The condition on C2:** the advisory does not say what goes wrong in each feature. If redaction can leave the hidden text in the output file, a warning is not enough for Protect and it should be held back (C1 for Protect only). **Question for the library chat:** for each of the three, what exactly fails, and on which files.

### D. Before production, whatever is chosen above

- No host goes to production on Pdf 3.32.0 with outside files. For the portal this is firm: it takes uploads from anyone signed in.
- The portal worker gets an operating-system memory cap and a per-operation time limit (Web chat).
- Linux printing to a remote CUPS server is decided with the Print patch (Linux chat).

## 6. Questions to carry to the library coordinator

1. The reproducer files for the stack overflow, per library.
2. For redaction, signature verification with a trust store, and page operations with hidden layers: what fails, on which files, and is the output wrong or does the process crash?
3. Is `EvaluateConditionalFormats` on Sheets 2.0.4 affected, or only the import options?
4. In Pdf 3.35.1, does the SVG renderer honour `PdfLimits`? (On 3.32.0 it does not.)
5. Is the embedded-font weakness in font parsing generally (then the raster path is affected too) or only in SVG font embedding?
