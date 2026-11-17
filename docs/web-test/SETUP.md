# Web Test — setting up the test environment again

Everything the Web Test chat runs lives in `/tmp` and `/dev/shm`, which are lost when the container resets. This note and `tests/web-test/env/` let a fresh container be brought back in about an hour. All of it is **test tooling only**; none of it goes into the product.

## 1. What has to be there

| Thing | Where | How it is made |
|---|---|---|
| .NET SDK 10.0.403 | `/opt/dotnet` | Install the SDK; then **once per machine** `dotnet workload update` (the repo's `global.json` pins SDK and workload set 10.0.403 with roll-forward off; without it the build fails with MSB4242). Never change `global.json`. |
| Tested head | `/home/claude/wt-verify` | A detached checkout of `origin/platform/web` (`git clone` of `Sthraas/chuvadi-reader-platforms`, then `git checkout --detach origin/platform/web`). |
| My branch | `/home/claude/chuvadi-reader-platforms` | Clone on `platform/web-test`. Commit as `git -c user.name=Arun -c user.email=arunshiva@gmail.com commit …`, no attribution lines. Never push to `main`, `platform/web` or `arunshivab/chuvadi-reader`. |
| Python + Playwright | system `python3` | `pip install --break-system-packages playwright pypdf openpyxl pillow`, then `python3 -m playwright install chromium firefox webkit chrome`. |
| Old WebKit 17.4 (Safari 17 engine) | `/tmp/oldpw`, `/tmp/oldpw-browsers` | `tests/web-test/env/setup-old-webkit.sh` (Playwright 1.44 in its own venv, plus ICU 70 and libvpx 7 from Ubuntu 22.04 copied into the bundle; if the shell can't download the two .debs, attach them). |
| WebKit 18.2 / 18.4 (only for the M-27 probe) | `/tmp/pw1.49.0`, `/tmp/pw1.52.0` | Same as above with `playwright==1.49.0` / `1.52.0`. Rarely needed. |
| PostgreSQL 16 | `/tmp/pgdata`, socket in `/tmp`, port 5432 | `apt-get install postgresql-16` if missing; `env/start-sangam.sh` runs `initdb` and creates role/database `sangam_identity` / password `sangam_dev`. |
| Local Sangam v1.0.0-rc.16 (d43a5ff) | source `/home/claude/sangam`, published `/tmp/sangam-pub`, `http://localhost:5100` | `git archive` the Sangam repo at tag `v1.0.0-rc.16` into `/home/claude/sangam`, then `dotnet publish src/Sangam.Identity.Server -c Release -o /tmp/sangam-pub`. Start with `env/start-sangam.sh` (registers client `chuvadi-portal`, base URL `http://localhost:5600/`, secret in `/tmp/sangam-secret`, made on first run). Read-only use; it migrates its own database in Development. |
| Corpora | `/tmp/corpus`, `/tmp/fid`, `/tmp/bigx`, `/tmp/enc`, `/tmp/p29`, `/tmp/m27`, `/tmp/p33` | `python3 tests/web-test/make_corpus.py /tmp/corpus`; `make_fidelity.py /tmp/fid` (then copy `tests/web-test/fixtures/fid/fid-lo.*`, the LibreOffice re-saves, into `/tmp/fid`); `make_large_xlsx.py /tmp/bigx`; `env/make-small-corpora.py` (enc, p29); copy `tests/web-test/fixtures/m27/*.pdf` to `/tmp/m27` and `tests/web-test/fixtures/p33/*` to `/tmp/p33` (rich.pdf and layered.pdf are the Foundation's PixelProof fixtures; signed.pdf is text-3.pdf signed with a throw-away self-made certificate via pyHanko, `TZ=Asia/Kolkata` needed; cond.xlsx has two conditional rules and one own fill). Check each script's header line for its exact arguments. |

## 2. Building a head

```
cd /home/claude/wt-verify
git fetch origin
git checkout --detach origin/platform/web
git clean -xdfq
export PATH=/opt/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1
bash /home/claude/chuvadi-reader-platforms/tests/web-test/env/restore.sh
dotnet build ChuvadiReader.Platforms.slnx -c Release -warnaserror
dotnet test ChuvadiReader.Platforms.slnx -c Release --no-build
dotnet build tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj -c Release -warnaserror
dotnet test tests/ChuvadiReader.Web.Tests/ChuvadiReader.Web.Tests.csproj -c Release --no-build
dotnet publish src/ChuvadiReader.Web/ChuvadiReader.Web.csproj -c Release -o /tmp/pubNN
bash tests/web-e2e/check-package.sh /tmp/pubNN
```
Use a new `/tmp/pubNN` per head (pub17 = 95c44b01).

## 3. Running portals

Copy the helpers first: `cp tests/web-test/env/*.sh /tmp/ && chmod +x /tmp/*.sh`.

| Port | What | Start |
|---|---|---|
| 6090 / 6091 | Development sign-in, default limits | `PUB=/tmp/pubNN /tmp/start-portal.sh 6090 Gateway` |
| 5691–5694 | Development sign-in, **short limits** (idle 40 s, warning 10 s, checks 2 s, worker idle stop 5 s) | `PUB=/tmp/pubNN /tmp/start-portal.sh 5691 Gateway Portal__IdleTimeout=00:00:40 Portal__ExpiryWarning=00:00:10 Portal__ExpiryCheckInterval=00:00:02 Portal__Workers__IdleStop=00:00:05 Portal__Workers__CheckInterval=00:00:02` |
| 5600 | Real Sangam sign-in | `/tmp/start-sangam.sh`, then `PUB=/tmp/pubNN /tmp/start-sangam-portal.sh` |

Logs: `/tmp/portal-<port>.log`; data root `/dev/shm/chvd-<port>`; pid in `/tmp/portal-<port>.pid`.
Development sign-in in scripts: `pdfs.sign_in_as(context, base, name)` sets the `chvd-dev-user` cookie (the `X-Dev-User` header is not sent on downloads). Each person is one worker; **`MaxWorkers = 40`** and a closed browser keeps its worker until its session ends — restart portals between batches or the 41st person is turned away.

## 4. The runs

- `env/run-a.sh` — fresh-portal checks (first visit in Firefox, `early_drop.py`, `worker_crash.py`). Edit the list at the top for each head.
- `env/run-b.sh` — the Web chat's suites × Chrome, Firefox, WebKit (`flows`, `page_images`, `reload`, `leave_guard`, `close_card`, `mark_zoom`, `office_limits`, `sangam_signin`, `expiry`, `comeback`, `gone_browser`), then my `linger.py`. Starts PostgreSQL, Sangam and the three portals itself.
- `env/run-c.sh` — my scripts × 3 engines (`mark_position`, `zoom_tools`, `close_card_probe`, `excel_p29`, `holds_probe`, `encoding_probe`, `leave_prompt`, `reload_tabs`, `page_image_sec`, `verify_fixes`, `fidelity_check`), M-27 on WebKit 17.4, large Excel, `sec_browser.py`, `cleanup_race.py`. Waits for run-b to finish.
- Run them with `PUB=/tmp/pubNN OUT=/tmp/outNN RUNLOG_B=/tmp/run-b.log`, in the background (`setsid nohup … &`); together they take about 2½ hours on the 2-core sandbox.
- WT-24 checks (when expiry code changes): `expiry_stall.py` on 20 fresh short-limit portals, `expiry_many.py <base> <root> <log> 8 10`, `expiry_forced.py … kill 4` and `… stop 7`.
- Design: `ONLY_SIZES=desktop,tablet,phone python3 shots.py <dev base> http://localhost:5600 /tmp/corpus/text-13.pdf <out> chromium webkit firefox`.
- Speed: `perf.py <base> /tmp/corpus/text-13.pdf <out> <people>` for 1, 10, 20 (restart the portal between).

## 5. Known harness quirks (not product faults)

- **OBS-1:** Firefox under Playwright sometimes never reports "load" for a later page in the same context; the page is fine. Shows as `Page.goto` time-outs (1–3 of 16 M-27 cases, some `comeback.py` runs).
- Headless WebKit can't run the two print checks in `verify_fixes.py` (WT-02); covered by manual M-2.
- The View rail expands on hover and can cover the Tools rail: move the mouse away before clicking tools.
- Old WebKit (≤ 18.4) returns unzoomed rectangles inside CSS `zoom`; `mark_position.py` corrects for it — don't measure by hand with `getBoundingClientRect` there.

## 6. The watch

One scheduled check of `platform/web` must stay live (coordinator's standing instruction, 16 Nov): each run checks the head, tests what moved, writes `BUGS.md` / `RESULTS.md` / `PHASE-1-SIGNOFF.md`, and schedules itself again.
