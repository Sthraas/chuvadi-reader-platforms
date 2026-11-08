# Web Test chat tooling (testing only, never shipped)

| Script | Use |
|---|---|
| `make_corpus.py <out>` | Ordinary, protected, large and hostile documents (needs reportlab, pypdf, python-docx, openpyxl, Pillow). Protected files are then re-made with qpdf: `qpdf --encrypt "" owner 256 --print=none -- text-3.pdf no-print.pdf` (pypdf writes `/P` unsigned — see BUGS LIB-1) |
| `perf.py <base> <pdf> <out> <people>` | Load and speed in milliseconds (ttfb, first frame, ready, first page, jump, next) and worker memory |
| `sec_browser.py <base> <corpus> <out> <server log> <data root>` | Isolation (print ticket), vector print, hostile names, hostile documents with a second person paging |
| `shots.py <dev base> <sangam base> <pdf> <out> [engines]` | Design screenshots: 12a light/dark, Home and the four modes in five themes, account menu, Settings, Library at five sizes (`ONLY_SIZES=phone,…` to limit) |
| `sangam_stub.py <port> [--delay s] [--bad-json] [--wrong-issuer]` | Stand-in for Sangam discovery/authorize, for 12a and the down/slow cases |

Portals for these runs: Release publish, `ASPNETCORE_ENVIRONMENT=Development`, `Portal__Mode=Gateway`, `Portal__DataRoot=/dev/shm/<folder>`; for 12a add `Sangam__Authority=http://127.0.0.1:<stub port>/ Sangam__ClientId=chuvadi-portal Sangam__ClientSecret=<test value>`.
