#!/usr/bin/env python3
"""Bascule DNS de zabbix.teleimagerie.net vers le proxy (57.130.34.122).

Contexte : migration du serveur Zabbix depuis le VPS OVH 51.178.36.192
vers le CT 204 (10.40.0.60), servi derriere proxy-tim comme auth et
pacs-secours. Le nom n'a pas d'AAAA (verifie sur ns17 le 29/08/2026).

Methode maison (09-proxy-tim.md) : ttl60 une heure avant la bascule,
switch le jour J, ttl3600 apres stabilisation. revert = retour au VPS,
effectif en ~60 s tant que le TTL est bas.

Usage : bascule-zabbix.py {status|ttl60|switch|revert|ttl3600}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"
SUB = "zabbix"
OLD_A = "51.178.36.192"   # VPS OVH d'origine
NEW_A = "57.130.34.122"   # VIP proxy-tim

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


def get_a():
    """L'enregistrement A, obligatoire ; refuse un AAAA inattendu."""
    rid_4a, rec_4a = find("AAAA")
    if rec_4a:
        sys.exit(f"AAAA inattendu ({rec_4a['target']}) — le plan n'en prevoit pas, stop.")
    rid_a, rec_a = find("A")
    if not rec_a:
        sys.exit(f"Pas d'enregistrement A {SUB} — inattendu, stop.")
    return rid_a, rec_a


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


def set_record(target, ttl):
    rid, rec = get_a()
    if rec["target"] == target and rec["ttl"] == ttl:
        print(f"  A deja sur {target} ttl {ttl} — rien a faire")
        return
    call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": target, "ttl": ttl})
    print(f"  A : {rec['target']} (ttl {rec['ttl']}) -> {target} (ttl {ttl})")
    refresh()


def ttl60():
    """Abaisse le TTL sans changer la cible (H-1 avant bascule)."""
    _, rec = get_a()
    set_record(rec["target"], 60)


def switch():
    set_record(NEW_A, 60)


def revert():
    set_record(OLD_A, 60)


def ttl3600():
    """Remonte le TTL sur la cible courante (apres stabilisation)."""
    _, rec = get_a()
    set_record(rec["target"], 3600)


if __name__ == "__main__":
    actions = {"status": status, "ttl60": ttl60, "switch": switch,
               "revert": revert, "ttl3600": ttl3600}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
