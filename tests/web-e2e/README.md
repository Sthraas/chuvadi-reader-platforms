# Web portal browser flows (test tool only)

Drives a running portal with Playwright and the machine's Chrome. Test tooling only — never shipped.

```
pip install playwright            # uses the installed Google Chrome (channel "chrome")
cd src/ChuvadiReader.Web
ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://127.0.0.1:5090 dotnet run > /tmp/portal.log 2>&1 &
python3 tests/web-e2e/flows.py http://127.0.0.1:5090 <some.pdf> <output folder> /tmp/portal.log
```

Covers: open a PDF through the browser's file chooser, print the current page (browser print of a PDF;
`print()` is recorded because headless Chrome has no print dialog), merge two PDFs and receive the
download, and no console errors. Exit code 0 when every check passes.
