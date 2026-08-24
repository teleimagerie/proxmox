#!/usr/bin/env python3
"""Cree les enregistrements A pve{1,2,3}.infra.teleimagerie.net via l'API OVH."""
import hashlib
import os
import json
import sys
import urllib.request

AK = os.environ["OVH_AK"]
AS = os.environ["OVH_AS"]
CK = os.environ["OVH_CK"]
BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"

RECORDS = {
    "pve1.infra": "91.134.84.222",
    "pve2.infra": "51.68.240.48",
    "pve3.infra": "51.68.240.191",
}


def server_time():
    with urllib.request.urlopen(f"{BASE}/auth/time", timeout=15) as r:
        return int(r.read())


def call(method, path, body=None):
    url = BASE + path
    payload = json.dumps(body) if body is not None else ""
    ts = str(server_time())
    raw = f"{AS}+{CK}+{method}+{url}+{payload}+{ts}"
    sig = "$1$" + hashlib.sha1(raw.encode()).hexdigest()
    req = urllib.request.Request(
        url,
        data=payload.encode() if payload else None,
        method=method,
        headers={
            "X-Ovh-Application": AK,
            "X-Ovh-Consumer": CK,
            "X-Ovh-Timestamp": ts,
            "X-Ovh-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        print(f"  ERREUR HTTP {e.code} sur {method} {path} : {e.read().decode()[:300]}")
        return "ERROR"


print("=== verification des droits sur la zone ===")
ids = call("GET", f"/domain/zone/{ZONE}/record?fieldType=A")
if ids == "ERROR":
    sys.exit("Identifiants ou droits invalides.")
print(f"  OK : {len(ids)} enregistrements A existants dans {ZONE}")

print("=== enregistrements existants sous .infra ===")
existing = {}
for rid in ids:
    rec = call("GET", f"/domain/zone/{ZONE}/record/{rid}")
    if rec != "ERROR" and rec and rec.get("subDomain", "").endswith(".infra"):
        existing[rec["subDomain"]] = (rid, rec["target"])
        print(f"  {rec['subDomain']} -> {rec['target']}")
if not existing:
    print("  (aucun)")

print("=== creation / mise a jour ===")
changed = False
for sub, ip in RECORDS.items():
    if sub in existing:
        rid, cur = existing[sub]
        if cur == ip:
            print(f"  {sub} deja correct ({ip})")
            continue
        call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": ip, "ttl": 300})
        print(f"  {sub} mis a jour : {cur} -> {ip}")
        changed = True
    else:
        r = call("POST", f"/domain/zone/{ZONE}/record",
                 {"fieldType": "A", "subDomain": sub, "target": ip, "ttl": 300})
        if r != "ERROR":
            print(f"  {sub} cree -> {ip}")
            changed = True

if changed:
    call("POST", f"/domain/zone/{ZONE}/refresh", {})
    print("=== zone rechargee ===")
else:
    print("=== rien a modifier ===")
