#!/usr/bin/env python3
"""Bascule DNS de MyTIM (app/gestion) vers le proxy (57.130.34.122).

Contexte : migration de l'application de gestion depuis les VPS OVH vers les
VM 103 (tim-staging) et 104 (tim-prod) du cluster, servies derriere proxy-tim
comme odoo, auth et zabbix (voir 20-mytim.md).

Deux environnements, deux situations DNS differentes (releve du 31/08/2026) :
  prod    : A explicites app / gestion / d69eeb3e -> 51.210.24.59 (pas d'AAAA)
  staging : AUCUN A explicite — app.staging, gestion.staging et mailer.staging
            ne resolvent que par le wildcard *.staging -> 79.137.100.185.
            switch CREE donc les trois A ; revert les SUPPRIME (le wildcard
            reprend la main, sans toucher au wildcard lui-meme).

ttl60   : abaisse le TTL des A existants a 60 (a lancer >= 1 h avant).
          Sans effet en staging (rien d'explicite a abaisser : le wildcard
          garde son TTL de zone, les clients decouvriront le nouveau A a
          l'expiration de leur cache — 3600 s au pire).
switch  : A -> 57.130.34.122 (TTL 60), creation si absent, AAAA supprime.
revert  : retour a l'etat d'avant (prod : A -> ancien VPS ; staging :
          suppression des A crees), tant que le VPS existe.
ttl3600 : remonte le TTL a 3600 apres validation (VPS resilie).

Usage : bascule-mytim.py {prod|staging} {status|ttl60|switch|revert|ttl3600}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
ZONE = "teleimagerie.net"
NEW_A = "57.130.34.122"

ENVS = {
    "prod": {
        "noms": ["app", "gestion"],
        "old_a": "51.210.24.59",
        "explicite": True,       # les A existent : on les modifie
    },
    "staging": {
        "noms": ["app.staging", "gestion.staging", "mailer.staging"],
        "old_a": "79.137.100.185",   # cible du wildcard *.staging
        "explicite": False,      # rien d'explicite : on cree / on supprime
    },
}

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


def find(sub, field_type):
    """Renvoie (rid, rec) ou (None, None). Refuse les doublons."""
    q = urllib.parse.quote(sub)
    ids = call("GET", f"/domain/zone/{ZONE}/record?fieldType={field_type}&subDomain={q}")
    if not ids:
        return None, None
    if len(ids) != 1:
        sys.exit(f"{sub}.{ZONE} : {len(ids)} enregistrements {field_type} — inattendu, stop.")
    return ids[0], call("GET", f"/domain/zone/{ZONE}/record/{ids[0]}")


def refresh():
    call("POST", f"/domain/zone/{ZONE}/refresh", {})
    print("=== zone rechargee ===")


def status(env):
    for sub in env["noms"]:
        for ft in ("A", "AAAA"):
            rid, rec = find(sub, ft)
            if rec:
                print(f"  {sub}.{ZONE} {ft} -> {rec['target']} (ttl {rec['ttl']}, id {rid})")
            else:
                print(f"  {sub}.{ZONE} {ft} : absent" + (" (wildcard)" if ft == "A" and not env["explicite"] else ""))


def ttl60(env):
    changed = False
    for sub in env["noms"]:
        for ft in ("A", "AAAA"):
            rid, rec = find(sub, ft)
            if not rec:
                continue
            if rec["ttl"] == 60:
                print(f"  {sub} {ft} deja en ttl 60")
            else:
                call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": rec["target"], "ttl": 60})
                print(f"  {sub} {ft} -> {rec['target']} : ttl {rec['ttl']} -> 60")
                changed = True
    if changed:
        refresh()
    elif not env["explicite"]:
        print("  rien d'explicite a abaisser (wildcard) — normal en staging")


def switch(env):
    for sub in env["noms"]:
        rid, rec = find(sub, "A")
        if rec is None:
            call("POST", f"/domain/zone/{ZONE}/record",
                 {"fieldType": "A", "subDomain": sub, "target": NEW_A, "ttl": 60})
            print(f"  A {sub} cree -> {NEW_A} (ttl 60)")
        elif rec["target"] == NEW_A:
            print(f"  A {sub} deja sur {NEW_A}")
        elif rec["target"] != env["old_a"]:
            sys.exit(f"  A {sub} pointe sur {rec['target']} (ni {env['old_a']} ni {NEW_A}) — inattendu, stop.")
        else:
            call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": NEW_A, "ttl": 60})
            print(f"  A {sub} : {rec['target']} -> {NEW_A} (ttl 60)")
        rid4, rec4 = find(sub, "AAAA")
        if rec4:
            call("DELETE", f"/domain/zone/{ZONE}/record/{rid4}")
            print(f"  AAAA {sub} {rec4['target']} supprime (pas d'IPv6 au proxy)")
    refresh()


def revert(env):
    for sub in env["noms"]:
        rid, rec = find(sub, "A")
        if rec is None:
            print(f"  A {sub} absent — rien a faire")
        elif env["explicite"]:
            if rec["target"] != env["old_a"]:
                call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": env["old_a"], "ttl": 60})
                print(f"  A {sub} : {rec['target']} -> {env['old_a']}")
        else:
            call("DELETE", f"/domain/zone/{ZONE}/record/{rid}")
            print(f"  A {sub} supprime (le wildcard *.staging -> {env['old_a']} reprend)")
    refresh()


def ttl3600(env):
    changed = False
    for sub in env["noms"]:
        rid, rec = find(sub, "A")
        if not rec or rec["target"] != NEW_A:
            sys.exit(f"  A {sub} n'est pas sur {NEW_A} — remonter le TTL n'a pas de sens, stop.")
        if rec["ttl"] == 3600:
            print(f"  A {sub} deja en ttl 3600")
            continue
        call("PUT", f"/domain/zone/{ZONE}/record/{rid}", {"target": NEW_A, "ttl": 3600})
        print(f"  A {sub} -> {NEW_A} : ttl {rec['ttl']} -> 3600")
        changed = True
    if changed:
        refresh()


if __name__ == "__main__":
    actions = {"status": status, "ttl60": ttl60, "switch": switch,
               "revert": revert, "ttl3600": ttl3600}
    if len(sys.argv) != 3 or sys.argv[1] not in ENVS or sys.argv[2] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[2]](ENVS[sys.argv[1]])
