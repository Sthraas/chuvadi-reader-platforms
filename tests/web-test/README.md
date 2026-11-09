# Web Test chat tooling (testing only, never shipped)

| Script | Use |
|---|---|
| `make_corpus.py <out>` | Ordinary, protected, large and hostile documents (needs reportlab, pypdf, python-docx, openpyxl, Pillow). Protected files are then re-made with qpdf: `qpdf --encrypt "" owner 256 --print=none -- text-3.pdf no-print.pdf` (pypdf writes `/P` unsigned — see BUGS LIB-1) |
| `perf.py <base> <pdf> <out> <people>` | Load and speed in milliseconds (ttfb, first frame, ready, first page, jump, next) and worker memory |
| `sec_browser.py <base> <corpus> <out> <server log> <data root>` | Isolation (print ticket), vector print, hostile names, hostile documents with a second person paging |
| `shots.py <dev base> <sangam base> <pdf> <out> [engines]` | Design screenshots: 12a light/dark, Home and the four modes in five themes, account menu, Settings, Library at five sizes (`ONLY_SIZES=phone,…` to limit) |
| `verify_fixes.py <dev base> <log> <corpus> <out> <engine>` | Re-verification of the WT bugs in a running build (3 engines) |
| `edit_flows.py`, `redact_probe.py`, `split_probe.py` | Mark save, redact, password and split, output files checked with pypdf/poppler/qpdf (Firefox) |
| `make_fidelity.py <out>`, `fidelity_check.py` | Word/Excel data-fidelity corpus (spaces, case, scripts, number formats) and its check |
| `zip_check.py <engines>` | Split → one .zip; one-file save stays PDF (use Firefox with the Development header; Chromium/WebKit need a real Sangam cookie for downloads) |
| `sangam_stub.py <port> [--delay s] [--bad-json] [--wrong-issuer]` | Stand-in for Sangam discovery/authorize, for 12a and the down/slow cases |

Portals for these runs: Release publish, `ASPNETCORE_ENVIRONMENT=Development`, `Portal__Mode=Gateway`, `Portal__DataRoot=/dev/shm/<folder>`; for 12a add `Sangam__Authority=http://127.0.0.1:<stub port>/ Sangam__ClientId=chuvadi-portal Sangam__ClientSecret=<test value>`.
