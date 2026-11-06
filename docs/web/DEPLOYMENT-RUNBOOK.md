# Web portal — deployment runbook (E2E Networks)

The **last** step of the Web plan (Arun, 6 Nov). Ready to run once B5 (domain) and B6 (E2E account, region, VM plan, DNS) are settled. Values in `<angle brackets>` are filled in on the day; nothing here is specific to a domain.

Everything that runs on the server is our own code on .NET 10 and Linux. Nothing else is installed except the .NET runtime and the operating system's own packages (D-24, rule 3).

## 1. What runs
```
browser ──https──▶ nftables 443→8443, 80→8080 ──▶ gateway (Portal:Mode=Gateway, user chuvadi)
                                                   │  TLS (own ACME client), Sangam sign-in, expiry (D-30),
                                                   │  static files, /healthz
                                                   └─ Unix socket per person ──▶ worker (same program, Portal:Mode=Worker)
                                                         HOME, TMPDIR, data under /srv/chuvadi/data/workers/<key> (tmpfs)
```
- One gateway process (systemd service `chuvadi-portal`). It starts one worker process per signed-in person, and stops it when they leave. A worker never listens on the network.
- **Working copies live only in RAM**: the tmpfs at `/srv/chuvadi/data` (D-28). The portal refuses to start if `Portal:DataRoot` isn't on tmpfs, or if swap is on and not encrypted.
- **Anything else that touches disk** sits on a LUKS volume at `/var/lib/chuvadi`: certificates, the ACME account key, the Sangam client key and logs (D-28).
- Restarting the service ends every session. The browser goes to Sangam, which signs the person straight back in if their Sangam session is still on. Their files are gone, which is the promise (D-20, D-31).

## 2. Sizing (measured 7 Nov, `tests/web-e2e/load.py`)
| Measured (2-core sandbox, browsers on the same machine) | Value |
|---|---|
| Gateway, idle | ~110 MB |
| One active person's worker (open a 690 KB PDF, read, print) | ~175 MB |
| Worker start (first page after sign-in) | 0.55–0.7 s; ReadyToRun made no difference, so a plain publish is used |
| 15 people at once: all succeeded | ready 4.8 s median, upload+render 8.6 s median (CPU shared with 15 browsers) |

RAM needed ≈ 1.5 GB (OS) + 0.2 GB (gateway) + people × (0.2 GB + the files they have open). Files count twice: the copy in tmpfs, plus the document the Reader holds in memory.

| VM | `Portal:Workers:MaxWorkers` | tmpfs `size=` | `Portal:Workers:MemoryLimitMB` |
|---|---|---|---|
| 8 GB, 4 vCPU | 20 | 2G | 1024 |
| 16 GB, 8 vCPU (recommended start) | 40 | 4G | 1536 |
| 32 GB, 16 vCPU | 80 | 8G | 1536 |

Beyond `MaxWorkers`, a newcomer sees "The portal is busy". Raise the VM before raising the number.

## 3. Server preparation (once)
1. **OS**: Ubuntu 24.04 LTS on the E2E VM. Enable unattended security updates.
2. **No unencrypted swap**: `swapoff -a` and remove swap lines from `/etc/fstab`. Or use an encrypted swap (`/etc/crypttab`: `cryptswap /dev/<part> /dev/urandom swap,cipher=aes-xts-plain64,size=256`) or zram.
3. **LUKS volume** (an attached E2E block volume):
   ```
   cryptsetup luksFormat /dev/<vdb>
   cryptsetup open /dev/<vdb> chuvadi-data
   mkfs.ext4 /dev/mapper/chuvadi-data
   echo 'chuvadi-data /dev/<vdb> none luks' >> /etc/crypttab
   echo '/dev/mapper/chuvadi-data /var/lib/chuvadi ext4 defaults,nodev,nosuid 0 2' >> /etc/fstab
   ```
   The passphrase is entered at boot from E2E's console, or held in Pezhai once that is wired. Never keep it on the VM's own disk.
4. **Logs on the encrypted volume**: in `/etc/systemd/journald.conf.d/chuvadi.conf` set `Storage=volatile`. Or bind-mount `/var/log/journal` onto `/var/lib/chuvadi/journal`. File names people upload may appear in logs.
5. **User and folders**:
   ```
   useradd --system --home-dir /var/lib/chuvadi --shell /usr/sbin/nologin chuvadi
   install -d -o chuvadi -g chuvadi -m 0700 /srv/chuvadi /var/lib/chuvadi/tls /var/lib/chuvadi/acme /var/lib/chuvadi/keys
   echo 'tmpfs /srv/chuvadi/data tmpfs size=<4G>,mode=0700,uid=chuvadi,gid=chuvadi,nosuid,nodev,noexec 0 0' >> /etc/fstab
   mkdir -p /srv/chuvadi/data && mount /srv/chuvadi/data
   ```
6. **Kernel settings** (`/etc/sysctl.d/60-chuvadi.conf`): `fs.inotify.max_user_instances = 1024` (each session watches folders; every worker runs as `chuvadi`), `kernel.core_pattern = |/bin/false`, `fs.suid_dumpable = 0`.
7. **.NET runtime** (ASP.NET Core 10, Microsoft's package feed for Ubuntu): `apt install aspnetcore-runtime-10.0`. Check with `dotnet --list-runtimes`.
8. **Ports without root**: Kestrel listens on 8080 and 8443. nftables forwards 80 and 443 to them and allows only 22 from Arun's addresses (`/etc/nftables.conf`):
   ```
   table inet chuvadi {
     chain prerouting { type nat hook prerouting priority dstnat; tcp dport 80 redirect to :8080; tcp dport 443 redirect to :8443; }
     chain input { type filter hook input priority 0; policy drop;
       ct state established,related accept; iif lo accept;
       tcp dport { 80, 443, 8080, 8443 } accept; tcp dport 22 ip saddr { <admin addresses> } accept; icmp type echo-request accept; }
   }
   ```
   No `CAP_NET_BIND_SERVICE` is used: worker processes would inherit it.
9. **DNS**: `A` (and `AAAA` if IPv6) records for `<domain>` (and `www.<domain>` if wanted) point at the VM.

## 4. Install a version
```
# on the build machine (CI artefact or a clean checkout of platform/web)
dotnet restore src/ChuvadiReader.Web --configfile ci/nuget.config
dotnet publish src/ChuvadiReader.Web -c Release -o out/chuvadi-portal-<version> --no-restore
tar -C out -czf chuvadi-portal-<version>.tar.gz chuvadi-portal-<version>
sha256sum chuvadi-portal-<version>.tar.gz
# on the server
tar -C /opt -xzf chuvadi-portal-<version>.tar.gz && chown -R root:root /opt/chuvadi-portal-<version>
ln -sfn /opt/chuvadi-portal-<version> /opt/chuvadi-portal
```
The program folder is owned by root and read-only to the service.

## 5. Sangam client registration (with Sangam's operator)
| Item | Value |
|---|---|
| Client id | `<chuvadi-portal>` |
| Redirect URI | `https://<domain>/signin-sangam` |
| Post-logout redirect URI | `https://<domain>/signout-sangam` |
| Back-channel logout URI | `https://<domain>/backchannel-logout` (set in Sangam's **operator console**; finding 2) |
| Scopes | `openid profile email org.current` |
| Client authentication | `private_key_jwt`, ES256. Key made on the server: `openssl ecparam -name prime256v1 -genkey -noout -out /var/lib/chuvadi/keys/sangam-client.pem` (0600, owner `chuvadi`); give Sangam the public key and a key id |

## 6. Settings (`/etc/chuvadi-portal.env`, 0600 root)
```
ASPNETCORE_ENVIRONMENT=Production
ASPNETCORE_URLS=http://+:8080;https://+:8443
ASPNETCORE_HTTPS_PORT=443
Portal__Mode=Gateway
Portal__PublicOrigin=https://<domain>
Portal__DataRoot=/srv/chuvadi/data
Portal__Workers__SocketFolder=/run/chuvadi-portal
Portal__Workers__MaxWorkers=<40>
Portal__Workers__MemoryLimitMB=<1536>
Portal__AccountSettingsUrl=<Sangam self-service address>
Portal__MaintenanceNoticeFile=/var/lib/chuvadi/maintenance
Portal__DesktopAppUrl=<download page>
Portal__Tls__CertificatePath=/var/lib/chuvadi/tls/cert.pem
Portal__Tls__KeyPath=/var/lib/chuvadi/tls/key.pem
Portal__Tls__Acme__Enabled=true
Portal__Tls__Acme__Domains__0=<domain>
Portal__Tls__Acme__ContactEmails__0=<address>
Portal__Tls__Acme__AgreeToTermsOfService=<true, once Arun agrees>
Portal__Tls__Acme__AccountFolder=/var/lib/chuvadi/acme
# Staging first; production after step 8 passes:
# Portal__Tls__Acme__DirectoryUrl=https://acme-v02.api.letsencrypt.org/directory
Sangam__Authority=<https://sangam issuer/>
Sangam__ClientId=<chuvadi-portal>
Sangam__PrivateKeyPath=/var/lib/chuvadi/keys/sangam-client.pem
Sangam__PrivateKeyId=<key id>
```
The gateway passes none of the `Sangam__` settings to workers (tested).

## 7. systemd service (`/etc/systemd/system/chuvadi-portal.service`)
```
[Unit]
Description=Chuvadi Reader web portal (gateway and per-person workers)
After=network-online.target srv-chuvadi-data.mount var-lib-chuvadi.mount
Requires=srv-chuvadi-data.mount var-lib-chuvadi.mount
Wants=network-online.target

[Service]
User=chuvadi
Group=chuvadi
EnvironmentFile=/etc/chuvadi-portal.env
WorkingDirectory=/opt/chuvadi-portal
ExecStart=/opt/chuvadi-portal/ChuvadiReader.Web
RuntimeDirectory=chuvadi-portal
RuntimeDirectoryMode=0700
Restart=always
RestartSec=3
TimeoutStopSec=30
KillMode=control-group
LimitCORE=0
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/srv/chuvadi/data /var/lib/chuvadi
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
LockPersonality=yes
MemoryMax=<VM RAM minus 1.5G>
TasksMax=4096

[Install]
WantedBy=multi-user.target
```
`systemctl daemon-reload && systemctl enable --now chuvadi-portal`. When the service stops, each worker sees its standard input close and stops. `KillMode=control-group` catches any worker that doesn't.

## 8. Checks after install (in this order)
1. `systemctl status chuvadi-portal`: running, with no start-up refusal. A D-28 refusal names the problem.
2. `curl -sk https://127.0.0.1:8443/healthz` → `ok` (plain HTTP is redirected to HTTPS, like everything but the ACME challenge).
3. **Let's Encrypt staging**: `journalctl -u chuvadi-portal | grep -i acme` shows the order and the install. `curl -vk https://<domain>/healthz` shows the staging issuer. Then set the production directory URL, restart, and check that the browser shows a trusted certificate.
4. `curl -sI http://<domain>/` → 307 to `https://<domain>/` (port 443, not 8443). `curl -sI https://<domain>/healthz` shows HSTS, CSP, `X-Content-Type-Options`, no `Server` header.
5. In a browser: `https://<domain>/` → the portal's sign-in page (12a) → "Continue with Sangam" → Sangam → back signed in. The status bar shows the person. Open, print and merge a PDF, and download the result.
6. Sign out from the account menu → the signed-out page; `ls /srv/chuvadi/data/workers` is empty within about 3 minutes.
7. Sign in, sign out on Sangam itself → the portal tab goes to the signed-out page (back-channel).
8. Leave a tab idle: the warning comes at 25 minutes and the session ends at 30 (D-30).
9. Write a notice time an hour ahead into `/var/lib/chuvadi/maintenance`: the banner shows in an open tab; delete the file and it goes.
10. Load (optional, from a separate machine with the Development sign-in **off**): not possible against production, which only takes Sangam sign-ins. Run `tests/web-e2e/load.py` against a staging VM of the same size instead.

## 9. Operating
- **Logs**: `journalctl -u chuvadi-portal -f`. Worker lines are prefixed `ChuvadiReader.Web.Worker.<key>` (a hash, never the person's id).
- **Health**: E2E monitoring polls `https://<domain>/healthz` (anonymous, says only `ok`).
- **Certificates** renew by themselves 30 days before expiry, with no restart. Let's Encrypt mails the contact address if renewal keeps failing.
- **Updates** happen at a quiet hour, announced in advance (coordinator, 7 Nov):
  1. At least an hour before, write the restart time with its zone into the notice file:
     `echo '2026-11-08T22:00+05:30' | sudo -u chuvadi tee /var/lib/chuvadi/maintenance`.
     A second line can replace the standard text.
  2. Within 15 seconds, every open tab shows: "The portal restarts for an update at 22:00 (in about N minutes). Download anything you want to keep before then…". People who arrive later see it too.
  3. Install the new version (section 4). At the announced time run `systemctl restart chuvadi-portal`, then `rm /var/lib/chuvadi/maintenance`. The banner goes by itself once the time passes.
  - A restart ends all sessions: files are removed, and people sign in again (Sangam usually does that without asking).
- **Rollback**: point `/opt/chuvadi-portal` back to the previous folder and restart.
- **Backups**: no personal data to back up. Keep the env file, the Sangam client key and the ACME account key (all on the LUKS volume) in Pezhai.

## 10. Still open before go-live
| Item | Owner |
|---|---|
| Domain (B5) and E2E account, region, VM plan, DNS (B6) | Arun |
| Agreeing to Let's Encrypt's subscriber agreement (`AgreeToTermsOfService`) | Arun |
| Sangam production client registration (section 5) and the Sangam self-service address | Arun / Sangam |
| Where the LUKS passphrase lives (E2E console at boot, or Pezhai) | Arun |
