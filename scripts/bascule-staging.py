#!/usr/bin/env python3
"""Bascule DNS des pre-productions MyTIM / MyISOTEAM vers le proxy (57.130.34.122).

Contexte : migration des deux dedies OVH tim-staging (ns3240118, 79.137.100.185)
et isoteam-staging (ns3240079, 79.137.100.184) vers les VM 103 et 104 du
cluster, servies derriere proxy-tim comme odoo, auth et zabbix
(voir 20-mytim-staging.md).

Deux zones, plusieurs enregistrements par zone (le wildcard *.staging porte
app., gestion. et mailer.staging ; les autres sont des alias historiques
redigires en 301 par le vhost nginx) :

  teleimagerie.net : *.staging  app-staging  gestion-staging
  isoteam.mn       : *.staging  app-staging  gestion-staging  preprod-app  preprod-gestion

status  : etat de chaque enregistrement (A et AAAA) dans les deux zones.
ttl60   : abaisse le TTL des A (et AAAA s'il en existe) a 60 sans changer les
          cibles (a lancer >= 1 h avant la bascule, TTL de zone 3600).
switch  : A -> 57.130.34.122 (TTL 60), suppression des AAAA eventuels
          (le proxy n'a pas d'IPv6 de service).
revert  : retour aux dedies OVH, tant qu'ils existent.
ttl3600 : remonte le TTL des A a 3600 (apres validation, dedies resilies).

Chaque zone a sa propre paire de serveurs autoritaires (piege n 10 de
07-pieges.md) : verifier avec dig @ns17.ovh.net (teleimagerie.net) et
dig @ns102.ovh.net (isoteam.mn).

Usage : bascule-staging.py {status|ttl60|switch|revert|ttl3600}
Lit la cle API dans /root/.secrets/ovh.ini (ne quitte pas pve1).
"""
import configparser
import hashlib
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
NEW_A = "57.130.34.122"
# zone -> (ancienne cible, sous-domaines)
PLAN = {
    "teleimagerie.net": ("79.137.100.185", ["*.staging", "app-staging", "gestion-staging"]),
    "isoteam.mn": ("79.137.100.184", ["*.staging", "app-staging", "gestion-staging",
                                      "preprod-app", "preprod-gestion"]),
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


def find(zone, sub, field_type):
    """Renvoie (rid, rec) ou (None, None). Refuse les doublons."""
    q = urllib.parse.quote(sub)
    ids = call("GET", f"/domain/zone/{zone}/record?fieldType={field_type}&subDomain={q}")
    if not ids:
        return None, None
    if len(ids) != 1:
        sys.exit(f"{sub}.{zone} : {len(ids)} enregistrements {field_type} — inattendu, stop.")
    return ids[0], call("GET", f"/domain/zone/{zone}/record/{ids[0]}")


def refresh(zone):
    call("POST", f"/domain/zone/{zone}/refresh", {})
    print(f"=== zone {zone} rechargee ===")


def each():
    for zone, (old_a, subs) in PLAN.items():
        for sub in subs:
            yield zone, old_a, sub


def status():
    for zone, old_a, sub in each():
        for ft in ("A", "AAAA"):
            rid, rec = find(zone, sub, ft)
            if rec:
                tag = "PROXY" if rec["target"] == NEW_A else ("OVH-dedie" if rec["target"] == old_a else "INATTENDU")
                print(f"  {sub}.{zone} {ft} -> {rec['target']} [{tag}] (ttl {rec['ttl']}, id {rid})")
            elif ft == "A":
                print(f"  {sub}.{zone} A : ABSENT")


def ttl60():
    for zone, (old_a, subs) in PLAN.items():
        changed = False
        for sub in subs:
            for ft in ("A", "AAAA"):
                rid, rec = find(zone, sub, ft)
                if not rec:
                    continue
                if rec["ttl"] == 60:
                    print(f"  {sub}.{zone} {ft} deja en ttl 60")
                else:
                    call("PUT", f"/domain/zone/{zone}/record/{rid}", {"target": rec["target"], "ttl": 60})
                    print(f"  {sub}.{zone} {ft} -> {rec['target']} : ttl {rec['ttl']} -> 60")
                    changed = True
        if changed:
            refresh(zone)


def switch():
    for zone, (old_a, subs) in PLAN.items():
        for sub in subs:
            rid_a, rec_a = find(zone, sub, "A")
            if not rec_a:
                sys.exit(f"Pas d'enregistrement A {sub}.{zone} — inattendu, stop.")
            if rec_a["target"] == NEW_A:
                print(f"  {sub}.{zone} A deja sur {NEW_A}")
            elif rec_a["target"] != old_a:
                sys.exit(f"  {sub}.{zone} A pointe sur {rec_a['target']} (ni {old_a} ni {NEW_A}) — inattendu, stop.")
            else:
                call("PUT", f"/domain/zone/{zone}/record/{rid_a}", {"target": NEW_A, "ttl": 60})
                print(f"  {sub}.{zone} A : {rec_a['target']} -> {NEW_A} (ttl 60)")
            rid_4a, rec_4a = find(zone, sub, "AAAA")
            if rec_4a:
                call("DELETE", f"/domain/zone/{zone}/record/{rid_4a}")
                print(f"  {sub}.{zone} AAAA {rec_4a['target']} supprime (pas d'IPv6 au proxy)")
        refresh(zone)


def revert():
    for zone, (old_a, subs) in PLAN.items():
        for sub in subs:
            rid_a, rec_a = find(zone, sub, "A")
            if rec_a and rec_a["target"] != old_a:
                call("PUT", f"/domain/zone/{zone}/record/{rid_a}", {"target": old_a, "ttl": 60})
                print(f"  {sub}.{zone} A : {rec_a['target']} -> {old_a}")
            else:
                print(f"  {sub}.{zone} A deja sur {old_a}")
        refresh(zone)


def ttl3600():
    for zone, (old_a, subs) in PLAN.items():
        changed = False
        for sub in subs:
            rid_a, rec_a = find(zone, sub, "A")
            if not rec_a:
                sys.exit(f"Pas d'enregistrement A {sub}.{zone} — inattendu, stop.")
            if rec_a["target"] != NEW_A:
                sys.exit(f"  {sub}.{zone} A pointe sur {rec_a['target']}, pas {NEW_A} — remonter le TTL n'a pas de sens, stop.")
            if rec_a["ttl"] == 3600:
                print(f"  {sub}.{zone} A deja en ttl 3600")
                continue
            call("PUT", f"/domain/zone/{zone}/record/{rid_a}", {"target": NEW_A, "ttl": 3600})
            print(f"  {sub}.{zone} A -> {NEW_A} : ttl {rec_a['ttl']} -> 3600")
            changed = True
        if changed:
            refresh(zone)


if __name__ == "__main__":
    actions = {"status": status, "ttl60": ttl60, "switch": switch,
               "revert": revert, "ttl3600": ttl3600}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
