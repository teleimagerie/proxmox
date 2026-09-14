#!/usr/bin/env python3
"""Temporisation des alertes de disponibilité des deux serveurs syngo.via de
TELLIS (SYNGOVIA-135104 = 192.168.101.98, SYNGOVIA-135113 = .100), décidée le
14/09/2026 (17-zabbix.md § Syngo Via, 13-tellis.md § syngo.via).

Les hôtes eux-mêmes ont été posés À LA MAIN le 02/09/2026 (gabarit « Windows by
SNMP », communauté dédiée, sondes TCP 104/443/3389) : ce script ne les crée
pas. Il ne porte que la règle du 14/09 et le contrôle.

S'exécute SUR le CT 204. Idempotent : relancer ne change rien de plus. Le jeton
API Zabbix (« provisioning ») est lu dans /root/.zbx-api-token. Aucun autre
secret.

Pourquoi : les deux serveurs REDÉMARRENT chaque dimanche vers 02:27-02:31
(constaté les 07 et 14/09/2026, 1 à 2 minutes d'arrêt). Avec les seuils du
02/09 — sondes TCP max(...,3m)=0 et « Unavailable by ICMP ping » du gabarit
(max(icmpping,#3)=0) — chaque reboot envoyait quatre mails High pour rien.
Décision : n'alerter qu'après 15 minutes d'indisponibilité.

Mécanique :
  - les déclencheurs de sonde TCP sont propres aux hôtes : leur expression
    passe simplement de 3m à 15m (nom et sévérité inchangés) ;
  - « Unavailable by ICMP ping » est HÉRITÉ du gabarit : son expression ne se
    modifie pas au niveau de l'hôte. On le DÉSACTIVE sur chaque hôte et on pose
    un High propre à l'hôte sur le même item icmpping, à 15 min — même motif
    que les services critiques de pacs03/TIMWFMCORE (Average du gabarit éteint,
    High dédié à côté) ;
  - max(/H/clé,15m)=0 = quinze valeurs consécutives à 0 à la minute ; se
    referme dès le premier 1 ;
  - rien d'autre n'est touché : « No SNMP data collection », ICMP loss et
    response time restent en Warning (sans mail).

Usage : zabbix-provision-syngo.py {hotes|check}
"""
import json
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
HOSTS = ("SYNGOVIA-135104", "SYNGOVIA-135113")
DELAI = "15m"
# port, sévérité attendue (4 = High -> mail, 3 = Average) — telles que posées le 02/09
SONDES = ((104, 4), (443, 4), (3389, 3))
ICMP_TEMPLATE = "Unavailable by ICMP ping"


def zbx(method, params):
    req = urllib.request.Request(
        API,
        data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                         "id": 1}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    out = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in out:
        sys.exit(f"API {method}: {out['error']}")
    return out["result"]


def host_id(host):
    h = zbx("host.get", {"filter": {"host": [host]}})
    if not h:
        sys.exit(f"hote introuvable: {host} — il doit exister (pose a la main le 02/09/2026)")
    return h[0]["hostid"]


def ensure_trigger(desc, expr, prio):
    if zbx("trigger.get", {"filter": {"description": [desc]}}):
        return False
    zbx("trigger.create", {"description": desc, "expression": expr,
                           "priority": prio, "manual_close": 1})
    return True


def hotes():
    for host in HOSTS:
        hid = host_id(host)
        print(f"== {host}")

        # --- sondes TCP : 3m -> 15m ----------------------------------------
        for port, prio in SONDES:
            cle = f"net.tcp.service[tcp,,{port}]"
            voulu = f"max(/{host}/{cle},{DELAI})=0"
            t = zbx("trigger.get", {"hostids": [hid], "expandExpression": 1,
                                    "output": ["triggerid", "description", "expression", "priority"],
                                    "search": {"description": f"(tcp/{port}) INJOIGNABLE sur {host}"}})
            if not t:
                print(f"  ATTENTION sonde tcp/{port} sans declencheur (pose a la main le 02/09 ?)")
                continue
            t = t[0]
            if t["expression"] == voulu:
                continue
            zbx("trigger.update", {"triggerid": t["triggerid"], "expression": voulu})
            print(f"  sonde tcp/{port} : {t['expression']} -> {voulu}")
            if int(t["priority"]) != prio:
                print(f"    (severite {t['priority']} laissee telle quelle, attendue {prio})")

        # --- ICMP : herite du gabarit desactive, High propre a 15 min ----------
        for t in zbx("trigger.get", {"hostids": [hid], "output": ["triggerid", "status", "templateid"],
                                     "search": {"description": ICMP_TEMPLATE}}):
            if t["templateid"] not in ("0", 0) and t["status"] == "0":
                zbx("trigger.update", {"triggerid": t["triggerid"], "status": 1})
                print(f"  herite du gabarit desactive : « {ICMP_TEMPLATE} » (max(icmpping,#3)=0)")
        desc = f"INJOIGNABLE en ICMP depuis 15 min : {host} (reboot hebdo dimanche ~02:30 tolere)"
        if ensure_trigger(desc, f"max(/{host}/icmpping,{DELAI})=0", 4):
            print(f"  High pose : {desc}")


def check():
    for host in HOSTS:
        hid = host_id(host)
        print(f"== {host}")
        for t in zbx("trigger.get", {"hostids": [hid], "expandExpression": 1, "sortfield": "description",
                                     "output": ["description", "expression", "priority", "status", "templateid"]}):
            if "INJOIGNABLE" in t["description"] or "ICMP" in t["description"]:
                etat = "actif" if t["status"] == "0" else "DESACTIVE"
                orig = "gabarit" if t["templateid"] not in ("0", 0) else "hote"
                print(f"  [{t['priority']}] {etat:9} {orig:7} {t['description']}")
                print(f"        {t['expression']}")
        for i in zbx("item.get", {"hostids": [hid], "output": ["key_", "lastvalue", "state", "error"]}):
            if i["key_"] == "icmpping" or i["key_"].startswith("net.tcp.service"):
                print(f"  {i['key_']:32} = {i['lastvalue']}" + (f"  NON SUPPORTE {i['error']}" if i["state"] == "1" else ""))
        pbs = zbx("problem.get", {"hostids": [hid], "output": ["name", "severity"]})
        print(f"  problemes ouverts : {len(pbs)}")
        for p in pbs:
            print(f"    [{p['severity']}] {p['name']}")


if __name__ == "__main__":
    cmds = {"hotes": hotes, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
