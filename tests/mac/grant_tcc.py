#!/usr/bin/env python3
"""TESTING ONLY — run with sudo on a GitHub macOS runner (SIP is off there; the runner image grants its own
agent the same way). Gives the test tools Accessibility, Screen Recording, Post Event and Apple Events (Finder)
so the driver can read the AX tree, capture windows and send keys. Prints what it did.

  sudo grant_tcc.py <client path> [<client path> ...]
"""
import os
import sqlite3
import sys
import time

clients = sys.argv[1:]
dbs = ["/Library/Application Support/com.apple.TCC/TCC.db"]
user = os.environ.get("SUDO_USER")
if user:
    dbs.append(f"/Users/{user}/Library/Application Support/com.apple.TCC/TCC.db")
services = ["kTCCServiceAccessibility", "kTCCServiceScreenCapture", "kTCCServicePostEvent",
            "kTCCServiceListenEvent", "kTCCServiceSystemPolicyAllFiles"]
now = int(time.time())
for db in dbs:
    if not os.path.exists(db):
        print("no db", db)
        continue
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(access)")]
    for c in clients:
        for s in services + ["kTCCServiceAppleEvents"]:
            row = {k: None for k in cols}
            row.update(service=s, client=c, client_type=1, auth_value=2, auth_reason=4, auth_version=1, flags=0,
                       last_modified=now)
            if "indirect_object_identifier_type" in cols:
                row["indirect_object_identifier_type"] = 0
            if "indirect_object_identifier" in cols:
                row["indirect_object_identifier"] = "com.apple.finder" if s == "kTCCServiceAppleEvents" else "UNUSED"
            if "boot_uuid" in cols:
                row["boot_uuid"] = "UNUSED"
            if "policy_id" in cols:
                row["policy_id"] = None
            if "last_reminded" in cols:
                row["last_reminded"] = now
            if "pid" in cols:
                row["pid"] = None
            if "pid_version" in cols:
                row["pid_version"] = None
            q = f"INSERT OR REPLACE INTO access ({','.join(row)}) VALUES ({','.join('?' * len(row))})"
            try:
                con.execute(q, list(row.values()))
            except Exception as e:
                print("insert failed", db, c, s, e)
    con.commit()
    con.close()
    print("granted in", db, "for", clients)
