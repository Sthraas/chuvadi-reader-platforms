#!/usr/bin/env python3
"""TESTING ONLY — sudo on a GitHub macOS runner (SIP is off there). Lets the smoke run's key sender post real key
presses: adds Accessibility and Post Event grants for the given executables to the system and user TCC databases.
  sudo grant-post-event.py <executable> [...]"""
import os, sqlite3, sys, time
now = int(time.time())
dbs = ["/Library/Application Support/com.apple.TCC/TCC.db"]
if os.environ.get("SUDO_USER"):
    dbs.append(f"/Users/{os.environ['SUDO_USER']}/Library/Application Support/com.apple.TCC/TCC.db")
for db in dbs:
    if not os.path.exists(db):
        continue
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(access)")]
    for client in sys.argv[1:]:
        for service in ("kTCCServiceAccessibility", "kTCCServicePostEvent"):
            row = {k: None for k in cols}
            row.update(service=service, client=client, client_type=1, auth_value=2, auth_reason=4, auth_version=1,
                       flags=0, last_modified=now)
            for k, v in (("indirect_object_identifier_type", 0), ("indirect_object_identifier", "UNUSED"),
                         ("boot_uuid", "UNUSED"), ("last_reminded", now)):
                if k in cols:
                    row[k] = v
            try:
                con.execute(f"INSERT OR REPLACE INTO access ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
                            list(row.values()))
                print("granted", service, client, "in", db)
            except Exception as e:
                print("grant failed", db, client, service, e)
    con.commit()
    con.close()
