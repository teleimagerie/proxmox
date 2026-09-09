#!/usr/bin/env python3
"""Provisioning Zabbix du serveur ProxyVia (Siemens syngo.via DicomProxy, DC
TELLIS) — trace exécutable du chantier du 09/09/2026
(17-zabbix.md § ProxyVia, 13-tellis.md § ProxyVia).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API Zabbix (« provisioning »,
rattaché à supportTIM) est lu dans /root/.zbx-api-token. Aucun secret : la
supervision est SANS agent et SANS SNMP — que des sondes TCP externes et
l'ICMP, donc ni communauté ni jeton propre à l'hôte.

Choix de conception, expliqués ici pour ne pas être défaits plus tard :
  - SANS agent : dicomproxy est une appliance Siemens, on n'y installe rien.
    On ne pose donc pas non plus de gabarit « Linux by Zabbix agent » ;
  - SANS SNMP, contrairement aux syngo : aucun démon SNMP n'est publié ici.
    On supervise donc par le seul chemin déjà ouvert (le CT 204 joint
    192.168.101.103 par wg2, vérifié le 09/09 : ICMP ~27 ms, ports 9104/8443/
    5432 ouverts) ;
  - gabarit « ICMP Ping » SEUL : il fournit icmpping et le déclencheur High
    « Unavailable by ICMP ping ». Aucun autre gabarit n'étant posé, il n'y a
    pas de clé icmpping en double (le piège des hôtes SNMP ne s'applique pas) ;
  - une interface agent est déclarée bien qu'inutile (aucun agent) : elle sert
    d'ancre {HOST.CONN} aux simple checks, même rôle que sur les syngo/VENUS ;
  - les sondes de service sont des simple checks à la minute avec un
    déclencheur max(...,3m)=0, repris du motif syngo/VENUS. High pour ce qui
    est vital (le mail ne part qu'en High ou Disaster), Average pour le reste.
    L'adresse (.103) est celle du bloc syngo — même /28 que .98/.100, déjà
    supervisés ; .58 est la patte imagerie, pas une cible de sonde.

Le port 5432 est volontairement classé High : le proxy dépend de la base
registry pour son mapping patient->serveur. Le fait que ce port réponde depuis
le réseau est par ailleurs le défaut n°1 signalé à Siemens — la sonde ne s'y
authentifie pas, elle ne fait qu'ouvrir la socket.

Usage : zabbix-provision-dicomproxy.py {hotes|check}
"""
import json
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
GROUP = "Linux servers"
TPL_ICMP = "ICMP Ping"

HOST = "DICOMPROXY"
IP = "192.168.101.103"
ROLE = "Siemens syngo.via - repartiteur DICOM"

# port, nom du service, sévérité (4 = High -> mail, 3 = Average)
SONDES = (
    (9104, "DicomProxy DP_EC (repartiteur DICOM)", 4),
    (5432, "PostgreSQL registry (mapping patient->serveur)", 4),
    (8443, "Portail admin Tomcat", 3),
)


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


def group_id():
    g = zbx("hostgroup.get", {"filter": {"name": [GROUP]}})
    return g[0]["groupid"] if g else zbx("hostgroup.create", {"name": GROUP})["groupids"][0]


def template_id(name):
    t = zbx("template.get", {"filter": {"host": [name]}})
    if not t:
        sys.exit(f"template introuvable: {name}")
    return t[0]["templateid"]


def host_id(name):
    h = zbx("host.get", {"filter": {"host": [name]}})
    if not h:
        sys.exit(f"hote introuvable: {name} (lancer d'abord « hotes »)")
    return h[0]["hostid"]


def interface_id(hid):
    """L'interface de l'hôte, indispensable aux simple checks (voir ci-dessous)."""
    i = zbx("hostinterface.get", {"hostids": [hid], "output": ["interfaceid"]})
    if not i:
        sys.exit(f"aucune interface sur l'hote {hid}")
    return i[0]["interfaceid"]


def ensure_item(hid, params):
    """Crée l'item, ou rattache l'interface à un item déjà créé sans elle.

    Piège : un simple check dont la clé laisse l'adresse vide
    (net.tcp.service[tcp,,9104]) part en « non supporté » avec
    « Check service item must have IP parameter or host interface specified »
    si l'item ne porte pas explicitement interfaceid. L'interface déclarée sur
    l'hôte ne suffit pas : l'interface web la rattache toute seule, l'API non.
    """
    ex = zbx("item.get", {"hostids": [hid], "output": ["itemid", "interfaceid"],
                          "filter": {"key_": [params["key_"]]}})
    if ex:
        if params.get("interfaceid") and ex[0].get("interfaceid") in ("0", 0, None):
            zbx("item.update", {"itemid": ex[0]["itemid"],
                                "interfaceid": params["interfaceid"]})
            print(f"  interface rattachee a {params['key_']}")
        return ex[0]["itemid"]
    return zbx("item.create", {**params, "hostid": hid})["itemids"][0]


def ensure_trigger(desc, expr, prio, recovery=None):
    if zbx("trigger.get", {"filter": {"description": [desc]}}):
        return False
    params = {"description": desc, "expression": expr, "priority": prio,
              "manual_close": 1}
    if recovery:  # recovery_mode 1 = expression de retour à la normale dédiée
        params.update({"recovery_mode": 1, "recovery_expression": recovery})
    zbx("trigger.create", params)
    return True


def hotes():
    """Crée l'hôte DICOMPROXY (ICMP seul), puis ses sondes de service TCP."""
    gid = group_id()
    if zbx("host.get", {"filter": {"host": [HOST]}}):
        print(f"{HOST} existe")
    else:
        zbx("host.create", {
            "host": HOST, "name": f"{HOST} ({ROLE})",
            "groups": [{"groupid": gid}],
            "templates": [{"templateid": template_id(TPL_ICMP)}],
            # interface inutile (aucun agent) : ancre {HOST.CONN} des simple checks
            "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": IP,
                            "dns": "", "port": "10050"}],
        })
        print(f"{HOST} cree ({IP})")

    hid = host_id(HOST)
    for port, service, prio in SONDES:
        cle = f"net.tcp.service[tcp,,{port}]"
        ensure_item(hid, {
            "name": f"{service} (tcp/{port}) joignable",
            "key_": cle, "type": 3, "value_type": 3, "delay": "1m",
            "interfaceid": interface_id(hid),
        })
        desc = f"{service} (tcp/{port}) INJOIGNABLE sur {HOST}"
        if ensure_trigger(desc, f"max(/{HOST}/{cle},3m)=0", prio):
            print(f"  sonde tcp/{port} ({service}) -> {'High' if prio == 4 else 'Average'}")


def check():
    hid = host_id(HOST)
    cles = ["icmpping"] + [f"net.tcp.service[tcp,,{p}]" for p, _, _ in SONDES]
    items = zbx("item.get", {"hostids": [hid],
                             "output": ["key_", "lastvalue", "lastclock", "state"],
                             "filter": {"key_": cles}})
    vus = {i["key_"]: i for i in items}
    frais = any(i.get("lastclock", "0") != "0" for i in items)
    print(f"{HOST:12} {'recoit des donnees' if frais else 'AUCUNE donnee'}")
    for cle in cles:
        i = vus.get(cle)
        if not i:
            print(f"             {cle} : ITEM ABSENT")
            continue
        etat = " NON SUPPORTE" if i.get("state") == "1" else ""
        print(f"             {cle} = {i.get('lastvalue', '?')}{etat}")
    pbs = zbx("problem.get", {"hostids": [hid], "output": ["name", "severity"]})
    print(f"\nproblemes ouverts sur {HOST} : {len(pbs)}")
    for p in pbs:
        print(f"  [{p['severity']}] {p['name']}")


if __name__ == "__main__":
    cmds = {"hotes": hotes, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
