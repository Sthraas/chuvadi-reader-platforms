# Web portal — independent test plan (Web Test chat)

Opened by D-100. Tests `platform/web` (head **31b063e**) as built by the Web chat, with the look from the Web portal UI chat. Starting point: the Web chat's own `docs/web/TEST-PLAN.md` (F-, S-, G-, L-, M-, V- IDs kept), run in full, then the extra cases below (IDs `X-…`). Nothing is assumed to work until seen working.

Test tooling (Playwright and its browsers, Python, reportlab/pypdf/qpdf/poppler for the corpus, the Sangam stub) is used for testing only and never shipped (rule 3). Scripts live in `tests/web-test/`.

## 0. Environment (this sandbox)
- Ubuntu 24.04, 2 vCPU, 8 GB RAM, `/dev/shm` tmpfs. .NET SDK 10.0.403 installed fresh; empty package cache (`NUGET_PACKAGES=/tmp/nuget-clean`).
- Engines: Google Chrome for Testing 153, Playwright Chromium (no PDF viewer), Firefox (PDF viewer on), WebKit 26.6.
- Widths: desktop 1440×900, handout frame 1280×720, tablet 820×1180 and 1180×820 (touch), phone 390×844 (touch, mobile).
- Portals run from the Release publish output (`dotnet publish`), gateway mode, data root on `/dev/shm`:
  - `:5090` Development sign-in (`X-Dev-User` picks the person), gateway.
  - `:5091` same with short expiry (40 s idle, 25 s warning, 2 s check).
  - `:5094` Sangam configured against `tests/web-test/sangam_stub.py` (shows 12a; Sangam down/slow/wrong cases).
- The staging VM (16 GB / 8 vCPU) is not available yet (Arun: E2E last); load numbers here are sandbox numbers and say so.

## 1. Build from clean (X-B)
| ID | Check |
|---|---|
| X-B1 | Empty package cache; restore with `ci/nuget.config`; `dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror` → 0 warnings |
| X-B2 | Web and Web.Tests built with `-warnaserror` (they are outside Platforms.slnx) |
| X-B3 | All tests: Reader, Hosting, Mobile UI, Web UI, Web |
| X-B4 | Publish audit: every assembly is .NET/ASP.NET Core or our own (Chuvadi*, LiPicons); no third-party code; static assets listed; nothing that calls out to the internet |
| X-B5 | `ci/packages` chuvadi-pdf 3.31.2 SHA-256 against `docs/foundation/PACKAGES-3.31.2.md` |

## 2. Web chat plan, run in full
§1 F-1…F-23, §2 S-1…S-18, §3 G-1…G-12, §4 L-1…L-8, §5 browser matrix — each with the Web chat's own coverage (U/E/M) re-run here where it can run here; manual and VM items listed in RESULTS §"Still needs a person or the VM".

## 3. Beyond the Web chat's plan
### Sign-in and sessions
| ID | Check |
|---|---|
| X-S1 | 12a in light and dark, three engines, three widths; no Sangam ID field (D-63); Terms opens `/terms` before sign-in |
| X-S2 | Authorize request: PKCE S256, `state`, `nonce`, scope incl. `org.current` (D-65), no secret in the URL |
| X-S3 | Sangam down with a **cold** portal (no discovery cached) and with a **warm** one |
| X-S4 | Sangam slow (200 s stub): how long the person waits; other pages unaffected meanwhile |
| X-S5 | Absolute 8 h limit with a short setting while staying active |

### Isolation and security
| ID | Check |
|---|---|
| X-I1 | Person B fetches person A's print ticket → 404; A gets it |
| X-I2 | Security headers on every class of response in **gateway** mode (gateway pages, relayed worker pages, relayed static files, 404, error) — compared with single mode |
| X-I3 | Cross-site: activity endpoint with no / foreign / own Origin; circuit negotiate with a foreign Origin |
| X-I4 | Browser-supplied `X-Chvd-*` identity headers |
| X-I5 | Hostile file names through the real chooser: `../`, `..\`, reserved names, 250/1000 chars, HTML in the name, bidi override, empty stem, tabs, CJK |
| X-I6 | Hostile and damaged documents: wrong extension both ways, empty, truncated, random after header, 200 k-deep nesting, page-tree loop, 1 GB Flate bomb, 2 GB zip bombs as DOCX and XLSX, user-password PDF, 210 MB over the limit — while another person keeps paging (latency recorded) |
| X-I7 | Worker folders 0700; nothing written outside the tmpfs data root; no Data Protection keys on disk |
| X-I8 | Everyone leaves → all workers stop and the data root empties |

### Function
| ID | Check |
|---|---|
| X-F1 | Print "Current" prints the page shown; print output is vector (text, no page images) |
| X-F2 | No-print PDF refused at the card (and the reason is visible) |
| X-F3 | DOCX and XLSX open (python-docx, openpyxl and LibreOffice files) |
| X-F4 | Mark → save as download; forms; redact; split; password protect/remove; Bench |

### Design fidelity
| ID | Check |
|---|---|
| X-D1 | 12a, 12b (account menu) side by side with the handout frames at 1280×720 |
| X-D2 | Home and Read/Mark/Arrange/Protect in all five themes (light, dark, palm, indigo, contrast), three engines, three widths |
| X-D3 | Phone width uses the phone shell (bottom bar, tool strip; D-32/D-40); tablet uses the 72/72/60 px rails |
| X-D4 | Status bar wording per D-98; account menu Terms · Privacy footer per D-97 |

### Load and speed (milliseconds)
`tests/web-test/perf.py`: per person, own browser context, gateway mode.
| Metric | Definition |
|---|---|
| ttfb_ms | navigation start → first byte of `/` |
| fcp_ms | navigation start → first contentful paint (first rendered frame) |
| ready_ms | navigation start → left bar interactive (circuit up, worker started) |
| first_page_ms | file handed to the chooser → page 1 drawn |
| jump_ms | type 10 + Enter → page 10 drawn and in view |
| next_ms | next-page button → page 11 drawn |
Runs: 1, 10, 20 people here (40 needs the VM's memory: 40 × ~165 MB workers plus 40 browser contexts exceed this sandbox's 8 GB); cold worker start single-person ×5; JIT vs ReadyToRun publish; large documents (500-page text, 91 MB 40-page scan).
