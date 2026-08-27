#!/usr/bin/env python3
"""Bascule DNS de auth.teleimagerie.net vers le proxy (57.130.34.122).

Contexte : auth pointait vers un ancien VPS resilie (146.59.233.102 + AAAA),
identifie le 27/08/2026 — anomalie de 14-noms-de-domaine.md soldee. Le nom
devient le point d'entree du serveur d'authentification Keycloak (CT 203),
servi derriere proxy-tim comme pacs-secours.

switch : A -> 57.130.34.122 (TTL 60), suppression du AAAA (le proxy n'a pas
d'IPv6 de service). revert : retour a l'etat du 27/08/2026.

Usage : bascule-auth.py {status|switch|revert}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"
SUB = "auth"
OLD_A = "146.59.233.102"
OLD_AAAA = "2001:41d0:305:2100::a89a"
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


def status():
    for ft in ("A", "AAAA"):
        rid, rec = find(ft)
        if rec:
            print(f"  {SUB}.{ZONE} {ft} -> {rec['target']} (ttl {rec['ttl']}, id {rid})")
        else:
            print(f"  {SUB}.{ZONE} {ft} : absent")


def switch():
    rid_a, rec_a = find("A")
    if not rec_a:
        sys.exit("Pas d'enregistrement A auth — inattendu, stop.")
    if rec_a["target"] == NEW_A:
        print(f"  A deja sur {NEW_A}")
    else:
        call("PUT", f"/domain/zone/{ZONE}/record/{rid_a}", {"target": NEW_A, "ttl": 60})
        print(f"  A : {rec_a['target']} -> {NEW_A} (ttl 60)")
    rid_4a, rec_4a = find("AAAA")
    if rec_4a:
        call("DELETE", f"/domain/zone/{ZONE}/record/{rid_4a}")
        print(f"  AAAA {rec_4a['target']} supprime (VPS resilie, pas d'IPv6 au proxy)")
    else:
        print("  AAAA deja absent")
    call("POST", f"/domain/zone/{ZONE}/refresh", {})
    print("=== zone rechargee ===")


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
    call("POST", f"/domain/zone/{ZONE}/refresh", {})
    print("=== zone rechargee ===")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "switch", "revert"):
        sys.exit(__doc__)
    {"status": status, "switch": switch, "revert": revert}[sys.argv[1]]()
