# Staging VM — what the Web Test runs need (one ask for Arun)

For: the 40-person load and V-1 to V-7 (`docs/web/TEST-PLAN.md` §5b). Built from the deployment runbook (`docs/web/DEPLOYMENT-RUNBOOK.md`) so staging matches production; nothing here is test-only except where marked. Written 10 Nov 2026.

## The ask in one paragraph
One E2E Networks VM sized as production (**Ubuntu 24.04 LTS, 8 vCPU, 16 GB RAM, 50 GB encrypted disk**), set up by runbook §3–§7; a **staging domain** with DNS pointing at it and ports 80/443 open; a **staging Sangam** reachable over https with the portal registered as a client; **two Sangam test persons** (one in two organisations); and for the load runs a **second, short-lived VM (8 vCPU, 16 GB)** to drive the browsers from, plus SSH for the Web Test chat for about two days.

## 1. Portal VM (production size)
| Item | Value | Why |
|---|---|---|
| OS | Ubuntu 24.04 LTS, unattended security updates on | runbook §3.1 |
| Size | **8 vCPU, 16 GB RAM** ("recommended start") | runbook §2: 40 people → `MaxWorkers=40`, `MemoryLimitMB=1536`, tmpfs `size=4G` |
| Disk | 50 GB, **encrypted volume** for `/var/lib/chuvadi` (keys, ACME account, certificates); swap **off** (or encrypted) | the portal refuses to start with plain swap; working copies stay in RAM (D-28) |
| tmpfs | `/srv/chuvadi/data` `size=4G,mode=0700,uid=chuvadi,nosuid,nodev,noexec` | runbook §3 step 5 |
| Runtime | `aspnetcore-runtime-10.0` from Microsoft's Ubuntu feed | §3.7 |
| Firewall | nftables: 80→8080, 443→8443; 22 only from Arun's and the load VM's addresses | §3.8 |
| Logs | journald `Storage=volatile` (or on the encrypted volume) | §3.4 |
| Access | SSH key for the Web Test chat (sudo for `systemctl`, `journalctl`, editing `/etc/chuvadi-portal.env`), for the test window only | to run and read V-1…V-7 |

## 2. https
| Item | Value |
|---|---|
| Domain | a **staging** name, e.g. `staging.<portal domain>` (B5) — `A` record (and `AAAA` if IPv6) to the VM |
| Certificate | Let's Encrypt via the portal's own ACME: **staging directory first**, then production (V-2). Needs port 80 reachable from the internet for the HTTP-01 challenge |
| Contact | an email for `Portal__Tls__Acme__ContactEmails__0` |
| Arun's yes | `Portal__Tls__Acme__AgreeToTermsOfService=true` — Arun agrees to Let's Encrypt's subscriber agreement (runbook §10) |

## 3. Sangam (staging instance, over https)
| Item | Value |
|---|---|
| Sangam | a staging Sangam reachable at `https://<sangam staging issuer>/` with a **publicly trusted certificate** (Sangam rejects self-signed certificates on back-channel calls — found 9 Nov) |
| Client | `chuvadi-portal` (or a staging id), **private_key_jwt** with the portal's public key; scopes `openid profile email org.current` |
| Redirect | `https://<staging domain>/signin-sangam` |
| Post-logout redirect | `https://<staging domain>/signed-out` |
| Back-channel logout | `https://<staging domain>/backchannel-logout` (session-aware) |
| Self-service link | the Sangam account address for `Portal__AccountSettingsUrl` |
| Test persons | **P1**: one organisation. **P2**: two organisations (G-12). Passwords handed to the tester out of band |

## 4. Load runs (V-1, V-3, part of V-6)
40 simultaneous browsers can't come from this sandbox (2 vCPU, 8 GB: 20 people already saturate it, session 1 §6).
- **Load VM:** a second E2E VM, **8 vCPU, 16 GB, Ubuntu 24.04**, in the same region, for 1–2 days; Python 3 + Playwright (test tooling only, never on the portal VM).
- **How the 40 people sign in — options for Arun:**
  - (a) **Development sign-in for the load passes only** (`ASPNETCORE_ENVIRONMENT=Development`, no `Sangam__` settings, the `X-Dev-User` header per person), then switch back to Production + Sangam for V-2, V-5, V-6, V-7. Pros: no 40 Sangam accounts; matches how `load.py` was built. Cons: the load passes don't exercise Sangam sign-in; staging is briefly in Development (firewalled to the load VM's address during those hours).
  - (b) **40 Sangam test persons** and real sign-ins. Pros: the full production path under load. Cons: 40 accounts to create and clean up; Sangam staging also carries the load.
  - **Recommendation: (a)** for V-1/V-3/V-4, with one short Production + Sangam round of 10 people (P1 signed in ten times) to show sign-in holds under load.

## 5. What each run needs
| Run | Needs from above | Time |
|---|---|---|
| 40-person load + **V-1** 2-hour soak | §1, §4 | ~3 h |
| **V-2** Let's Encrypt + forced renewal | §1, §2 (port 80 open, Arun's yes) | ~1 h |
| **V-3** large documents with 20 others running | §1, §4; test files are generated (`make_corpus.py`, `make_fidelity.py`) | ~1 h |
| **V-4** hostile documents | §1 | ~30 min |
| **V-5** log review | after V-1…V-4 | ~30 min |
| **V-6** restart with banner under load | §1, §4 | ~30 min |
| **V-7** no DRAFT lines | the counsel-reviewed Terms and Privacy in the build | 5 min |
| Back-channel over https (left from 9 Nov) | §2, §3 | 15 min |

## 6. Afterwards
Load VM deleted; SSH keys for the tester removed; Development settings gone from `/etc/chuvadi-portal.env` (`systemctl show` checked); Sangam test persons kept or removed as Arun prefers.
