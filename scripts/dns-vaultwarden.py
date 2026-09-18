#!/usr/bin/env python3
"""Cree vault.teleimagerie.net -> proxy-tim (57.130.34.122) via l'API OVH.

Contexte : publication du coffre de mots de passe Vaultwarden (VM 105),
servi derriere proxy-tim comme auth, odoo et zabbix (voir 21-vaultwarden.md).
Creation simple — pas de bascule depuis un ancien hebergement, donc pas de
ttl60/switch/revert : le nom n'existe pas encore.

status  : montre l'etat des enregistrements A et AAAA de vault.
create  : cree l'A -> 57.130.34.122 (TTL 60 le temps de la mise en service).
          Refuse si un A existe deja vers une autre cible, et ne cree JAMAIS
          d'AAAA (le proxy n'a pas d'IPv6 de service — piege recurrent).
ttl3600 : remonte le TTL a 3600 une fois le service valide.

Usage : dns-vaultwarden.py {status|create|ttl3600}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"
SUB = "vault"
TARGET = "57.130.34.122"

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


def create():
    rid_a, rec_a = find("A")
    if rec_a:
        if rec_a["target"] == TARGET:
            print(f"  A deja sur {TARGET} (ttl {rec_a['ttl']})")
        else:
            sys.exit(f"  A pointe deja sur {rec_a['target']} — inattendu, stop.")
    else:
        call("POST", f"/domain/zone/{ZONE}/record",
             {"fieldType": "A", "subDomain": SUB, "target": TARGET, "ttl": 60})
        print(f"  A cree -> {TARGET} (ttl 60)")
        refresh()
    rid_4a, rec_4a = find("AAAA")
    if rec_4a:
        sys.exit(f"  AAAA inattendu vers {rec_4a['target']} — le proxy n'a pas d'IPv6, a supprimer a la main.")


def ttl3600():
    rid_a, rec_a = find("A")
    if not rec_a:
        sys.exit("Pas d'enregistrement A vault — inattendu, stop.")
    if rec_a["target"] != TARGET:
        sys.exit(f"  A pointe sur {rec_a['target']}, pas {TARGET} — remonter le TTL n'a pas de sens, stop.")
    if rec_a["ttl"] == 3600:
        print("  A deja en ttl 3600")
        return
    call("PUT", f"/domain/zone/{ZONE}/record/{rid_a}", {"target": TARGET, "ttl": 3600})
    print(f"  A -> {TARGET} : ttl {rec_a['ttl']} -> 3600")
    refresh()


if __name__ == "__main__":
    actions = {"status": status, "create": create, "ttl3600": ttl3600}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
