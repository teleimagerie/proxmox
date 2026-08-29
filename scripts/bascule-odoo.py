#!/usr/bin/env python3
"""Bascule DNS de odoo.teleimagerie.net vers le proxy (57.130.34.122).

Contexte : migration de l'ERP Odoo depuis le VPS OVH vps-f18bcfe7
(91.134.75.199 + AAAA) vers la VM 101 du cluster, servie derriere
proxy-tim comme auth et pacs-secours (voir 17-odoo.md).

ttl60   : abaisse le TTL de l'A ET de l'AAAA a 60 sans changer les cibles
          (a lancer au moins 1 h avant la bascule — piege : ne baisser que
          l'A laisse les clients IPv6 sur l'ancien AAAA en cache 1 h).
switch  : A -> 57.130.34.122 (TTL 60), suppression du AAAA (le proxy n'a
          pas d'IPv6 de service).
revert  : retour a l'etat d'avant bascule (VPS), tant que le VPS existe.
ttl3600 : remonte le TTL de l'A a 3600 (apres validation, VPS resilie).

Usage : bascule-odoo.py {status|ttl60|switch|revert|ttl3600}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"
SUB = "odoo"
OLD_A = "91.134.75.199"
OLD_AAAA = "2001:41d0:304:200::675a"
NEW_A = "57.130.34.122"

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


def find(field_type):
    """Renvoie (rid, rec) ou (None, None). Refuse les doublons."""
    ids = call("GET", f"/domain/zone/{ZONE}/record?fieldType={field_type}&subDomain={SUB}")
    if not ids:
        return None, None
    if len(ids) != 1:
        sys.exit(f"{SUB}.{ZONE} : {len(ids)} enregistrements {field_type} — inattendu, stop.")
    return ids[0], call("GET", f"/domain/zone/{ZONE}/record/{ids[0]}")


def refresh():
    call("POST", f"/domain/zone/{ZONE}/refresh", {})
    print("=== zone rechargee ===")


def status():
    for ft in ("A", "AAAA"):
        rid, rec = find(ft)
        if rec:
            print(f"  {SUB}.{ZONE} {ft} -> {rec['target']} (ttl {rec['ttl']}, id {rid})")
        else:
            print(f"  {SUB}.{ZONE} {ft} : absent")


def ttl60():
    changed = False
    for ft in ("A", "AAAA"):
        rid, rec = find(ft)
        if not rec:
            print(f"  {ft} absent")
            continue
        if rec["ttl"] == 60:
            print(f"  {ft} deja en ttl 60")
        else:
            call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": rec["target"], "ttl": 60})
            print(f"  {ft} -> {rec['target']} : ttl {rec['ttl']} -> 60")
            changed = True
    if changed:
        refresh()


def switch():
    rid_a, rec_a = find("A")
    if not rec_a:
        sys.exit("Pas d'enregistrement A odoo — inattendu, stop.")
    if rec_a["target"] == NEW_A:
        print(f"  A deja sur {NEW_A}")
    elif rec_a["target"] != OLD_A:
        sys.exit(f"  A pointe sur {rec_a['target']} (ni {OLD_A} ni {NEW_A}) — inattendu, stop.")
    else:
        call("PUT", f"/domain/zone/{ZONE}/record/{rid_a}", {"target": NEW_A, "ttl": 60})
        print(f"  A : {rec_a['target']} -> {NEW_A} (ttl 60)")
    rid_4a, rec_4a = find("AAAA")
    if rec_4a:
        call("DELETE", f"/domain/zone/{ZONE}/record/{rid_4a}")
        print(f"  AAAA {rec_4a['target']} supprime (pas d'IPv6 au proxy)")
    else:
        print("  AAAA deja absent")
    refresh()


def revert():
    rid_a, rec_a = find("A")
    if rec_a and rec_a["target"] != OLD_A:
        call("PUT", f"/domain/zone/{ZONE}/record/{rid_a}", {"target": OLD_A, "ttl": 60})
        print(f"  A : {rec_a['target']} -> {OLD_A}")
    rid_4a, _ = find("AAAA")
    if not rid_4a:
        call("POST", f"/domain/zone/{ZONE}/record",
             {"fieldType": "AAAA", "subDomain": SUB, "target": OLD_AAAA, "ttl": 60})
        print(f"  AAAA recree -> {OLD_AAAA}")
    refresh()


def ttl3600():
    rid_a, rec_a = find("A")
    if not rec_a:
        sys.exit("Pas d'enregistrement A odoo — inattendu, stop.")
    if rec_a["target"] != NEW_A:
        sys.exit(f"  A pointe sur {rec_a['target']}, pas {NEW_A} — remonter le TTL n'a pas de sens, stop.")
    if rec_a["ttl"] == 3600:
        print("  A deja en ttl 3600")
        return
    call("PUT", f"/domain/zone/{ZONE}/record/{rid_a}", {"target": NEW_A, "ttl": 3600})
    print(f"  A -> {NEW_A} : ttl {rec_a['ttl']} -> 3600")
    refresh()


if __name__ == "__main__":
    actions = {"status": status, "ttl60": ttl60, "switch": switch,
               "revert": revert, "ttl3600": ttl3600}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
