#!/usr/bin/env python3
"""Bascule DNS vers le proxy (57.130.34.122) — checklist 09-proxy-tim.md.

Perimetre : pacs-secours.teleimagerie.net, syngo.teleimagerie.net (mise a jour),
syngo.isoteam.mn (creation — anomalie n°2 de 14-noms-de-domaine.md).
Les syngo-via.* ne sont PAS touches (restent en direct sur TSplus).

Usage : bascule-3noms.py {status|switch|revert}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
OLD_IP = "51.75.203.20"
NEW_IP = "57.130.34.122"

# (zone, sous-domaine, action a la bascule)
TARGETS = [
    ("teleimagerie.net", "pacs-secours", "update"),
    ("teleimagerie.net", "syngo", "update"),
    ("isoteam.mn", "syngo", "create"),
]

ini = configparser.ConfigParser()
with open("/root/.secrets/ovh.ini") as f:
    ini.read_string("[dns]\n" + f.read())
AK = ini["dns"]["dns_ovh_application_key"]
AS = ini["dns"]["dns_ovh_application_secret"]
CK = ini["dns"]["dns_ovh_consumer_key"]


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
        sys.exit(f"ERREUR HTTP {e.code} sur {method} {path} : {e.read().decode()[:300]}")


def find_record(zone, sub):
    """Renvoie (rid, rec) ou (None, None) si absent. Refuse les doublons."""
    ids = call("GET", f"/domain/zone/{zone}/record?fieldType=A&subDomain={sub}")
    if not ids:
        return None, None
    if len(ids) != 1:
        sys.exit(f"{sub}.{zone} : {len(ids)} enregistrements A — situation inattendue, stop.")
    rec = call("GET", f"/domain/zone/{zone}/record/{ids[0]}")
    return ids[0], rec


action = sys.argv[1] if len(sys.argv) > 1 else "status"
if action not in ("status", "switch", "revert"):
    sys.exit(f"Action inconnue : {action}")

print(f"=== etat actuel ===")
state = {}
for zone, sub, mode in TARGETS:
    rid, rec = find_record(zone, sub)
    state[(zone, sub)] = (rid, rec)
    if rec:
        print(f"  {sub}.{zone} A {rec['target']} TTL {rec['ttl']}")
    else:
        print(f"  {sub}.{zone} : absent")

if action == "status":
    sys.exit(0)

# garde-fous avant toute ecriture
if action == "switch":
    for zone, sub, mode in TARGETS:
        rid, rec = state[(zone, sub)]
        if mode == "update" and (rec is None or rec["target"] not in (OLD_IP, NEW_IP)):
            sys.exit(f"{sub}.{zone} : cible inattendue — stop, rien n'a ete modifie.")
        if mode == "create" and rec is not None and rec["target"] != NEW_IP:
            sys.exit(f"{sub}.{zone} : existe deja avec {rec['target']} — stop.")

print(f"=== {action} ===")
touched_zones = set()
for zone, sub, mode in TARGETS:
    rid, rec = state[(zone, sub)]
    if action == "switch":
        if rec and rec["target"] == NEW_IP:
            print(f"  {sub}.{zone} deja sur {NEW_IP}")
            continue
        if mode == "update":
            call("PUT", f"/domain/zone/{zone}/record/{rid}", {"target": NEW_IP, "ttl": 60})
            print(f"  {sub}.{zone} : {rec['target']} -> {NEW_IP}")
        else:
            call("POST", f"/domain/zone/{zone}/record",
                 {"fieldType": "A", "subDomain": sub, "target": NEW_IP, "ttl": 60})
            print(f"  {sub}.{zone} : cree -> {NEW_IP}")
        touched_zones.add(zone)
    elif action == "revert":
        if mode == "update":
            if rec and rec["target"] != OLD_IP:
                call("PUT", f"/domain/zone/{zone}/record/{rid}", {"target": OLD_IP, "ttl": 60})
                print(f"  {sub}.{zone} : retour -> {OLD_IP}")
        else:
            if rid is not None:
                call("DELETE", f"/domain/zone/{zone}/record/{rid}")
                print(f"  {sub}.{zone} : supprime (etat d'avant creation)")
        touched_zones.add(zone)

for zone in sorted(touched_zones):
    call("POST", f"/domain/zone/{zone}/refresh", {})
    print(f"  zone {zone} rechargee")

print("=== etat final ===")
for zone, sub, mode in TARGETS:
    rid, rec = find_record(zone, sub)
    if rec:
        print(f"  {sub}.{zone} A {rec['target']} TTL {rec['ttl']}")
    else:
        print(f"  {sub}.{zone} : absent")
