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

Interfaces réseau (14/09/2026, second temps) : la découverte SNMP du gabarit
remontait 35 à 37 « interfaces » par serveur — commutateurs virtuels Hyper-V
(vSwitch/vEthernet nat et WSL), pseudo-interfaces des pilotes de filtrage
(WFP, QoS Packet Scheduler), tunnels Teredo/ISATAP et miniports « Local Area
Connection* N » — et une dizaine d'Average « Link down » restaient ouverts en
permanence, ou se rouvraient à chaque reboot. Le filtre du gabarit porte sur
ifDescr, que Windows remplit avec le nom du pilote ; le libellé utile est
ifAlias ({#IFALIAS}, entre parenthèses dans le nom des items). On surcharge
donc {$NET.IF.IFALIAS.NOT_MATCHES} (« CHANGE_IF_NEEDED » dans le gabarit) par
une macro d'hôte : il ne reste que « HPE Network Port 10G 1 » (câblé) et
« 10G 2 » (non câblé, en 2 stable : « Link down » ne sonne que sur un
changement). Les items exclus deviennent « ressources perdues » et sont
supprimés par Zabbix 7 jours plus tard (lifetime du gabarit) ; entre-temps
leurs déclencheurs « Link down » sont désactivés et les problèmes ouverts
fermés à la main (manual_close autorisé par le gabarit).

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
# ifAlias des interfaces exclues de la découverte (PCRE, sensible à la casse)
IFALIAS_EXCLUS = r"vSwitch|vEthernet|Local Area Connection\*|LightWeight Filter|QoS Packet Scheduler|Loopback|Hyper-V"
MACRO_IFALIAS = "{$NET.IF.IFALIAS.NOT_MATCHES}"


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

        interfaces(host, hid)


def interfaces(host, hid):
    """Filtre de découverte sur ifAlias, découverte relancée, bruit résiduel éteint."""
    import re
    import time
    m = zbx("usermacro.get", {"hostids": [hid], "filter": {"macro": [MACRO_IFALIAS]},
                              "output": ["hostmacroid", "value"]})
    changee = False
    if not m:
        zbx("usermacro.create", {"hostid": hid, "macro": MACRO_IFALIAS, "value": IFALIAS_EXCLUS,
                                 "description": "14/09/2026 : commutateurs virtuels Hyper-V, pilotes de filtrage, tunnels et miniports exclus (ne reste que les ports HPE 10G)"})
        print(f"  macro {MACRO_IFALIAS} posee")
        changee = True
    elif m[0]["value"] != IFALIAS_EXCLUS:
        zbx("usermacro.update", {"hostmacroid": m[0]["hostmacroid"], "value": IFALIAS_EXCLUS})
        print(f"  macro {MACRO_IFALIAS} mise a jour")
        changee = True
    # découverte relancée tout de suite (task « execute now » sur la règle de l'hôte).
    # Piège (14/09/2026) : lancée dans la foulée de la macro, la découverte
    # tourne avec l'ancien cache de configuration (CacheUpdateFrequency 10 s)
    # et ne filtre rien — constaté sur .98 ; on attend le rafraîchissement.
    lld = zbx("discoveryrule.get", {"hostids": [hid], "filter": {"key_": ["net.if.discovery"]},
                                    "output": ["itemid"]})
    if lld:
        if changee:
            time.sleep(15)
        zbx("task.create", [{"type": 6, "request": {"itemid": lld[0]["itemid"]}}])
    # déclencheurs « Link down » des interfaces exclues : désactivés, problèmes fermés
    exclu = re.compile(IFALIAS_EXCLUS)
    for t in zbx("trigger.get", {"hostids": [hid], "search": {"description": "Link down"},
                                 "output": ["triggerid", "description", "status", "value"]}):
        alias = t["description"].split("(", 1)[1].rsplit(")", 1)[0] if "(" in t["description"] else ""
        if not exclu.search(alias):
            continue
        if t["status"] == "0":
            zbx("trigger.update", {"triggerid": t["triggerid"], "status": 1})
            print(f"  Link down desactive : {alias}")
        if t["value"] == "1":
            for e in zbx("problem.get", {"objectids": [t["triggerid"]], "output": ["eventid"]}):
                zbx("event.acknowledge", {"eventids": [e["eventid"]], "action": 1,
                                          "message": "interface virtuelle exclue de la decouverte le 14/09/2026"})
                print(f"  probleme ferme : {t['description']}")


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
        ifs = zbx("item.get", {"hostids": [hid], "output": ["name", "lastvalue"], "search": {"key_": "net.if.status"}})
        print(f"  interfaces decouvertes : {len(ifs)}")
        for i in ifs:
            print(f"    {i['lastvalue']:>2}  {i['name'].split(': ')[0]}")
        pbs = zbx("problem.get", {"hostids": [hid], "output": ["name", "severity"]})
        print(f"  problemes ouverts : {len(pbs)}")
        for p in pbs:
            print(f"    [{p['severity']}] {p['name']}")


if __name__ == "__main__":
    cmds = {"hotes": hotes, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
