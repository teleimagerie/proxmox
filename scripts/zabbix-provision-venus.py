#!/usr/bin/env python3
"""Provisioning Zabbix des trois serveurs RIS VENUS (Softway Medical, DC
TELLIS) — trace exécutable du chantier du 05/09/2026
(17-zabbix.md § Serveurs RIS VENUS, 13-tellis.md § RIS VENUS).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API Zabbix (« provisioning »,
rattaché à supportTIM) est lu dans /root/.zbx-api-token. Aucun autre secret :
les VENUS sont supervisés par agent actif, il n'y a pas de communauté SNMP
comme pour les syngo.

Choix de conception, expliqués ici pour ne pas être défaits plus tard :
  - « Windows by Zabbix agent ACTIF » : l'agent se connecte au serveur, donc
    aucun port entrant à ouvrir sur les VENUS — décisif sur le .63, le seul
    des trois dont le pare-feu Windows est allumé. Même choix que TIMWFMCORE
    et WIN-SRV-TSPLUS ;
  - le template « ICMP Ping » est ajouté EN PLUS : vérifié le 05/09/2026, le
    template agent actif ne contient aucun item icmpping, donc pas de clé en
    double. Attention : ce cumul est interdit avec « Windows by SNMP », qui
    embarque déjà l'ICMP (piège rencontré sur les syngo) ;
  - une interface agent est déclarée bien qu'inutile en mode actif : elle sert
    d'ancre {HOST.CONN} aux simple checks (même rôle que l'interface SNMP des
    syngo). Aucun sondage passif n'a lieu ;
  - les sondes de service sont des simple checks à la minute avec un
    déclencheur max(...,3m)=0, repris du motif syngo. High pour ce qui est
    vital (le mail ne part qu'en High ou Disaster), Average pour le reste ;
  - sous-commande « disque » : le déclencheur High sur le D: du .63 ne peut
    être créé qu'APRÈS la première découverte des volumes par l'agent, car il
    porte sur un item découvert. Le template classerait ce volume en Average,
    donc sans mail, alors qu'il tourne au-dessus de 90 % occupé. On éteint son
    seuil CRIT par macro contextuelle et on le remplace par un High à
    hystérésis (déclenche > 90 % pendant 5 min, ne retombe que sous 85 %
    pendant 30 min).

Usage : zabbix-provision-venus.py {hotes|disque|check}
"""
import json
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
GROUP = "Windows servers"
TPL_WIN = "Windows by Zabbix agent active"
TPL_ICMP = "ICMP Ping"

# hôte, IP, libellé du rôle
SERVEURS = (
    ("TIM-VENUS1-AP", "192.168.111.63", "RIS VENUS - application"),
    ("TIM-VENUS2-IF", "192.168.111.64", "RIS VENUS - interfaces et SFTP des sites"),
    ("TIM-VENUS3-DB", "192.168.111.65", "RIS VENUS - base de donnees"),
)

# hôte, port, nom du service, sévérité (4 = High -> mail, 3 = Average)
SONDES = (
    ("TIM-VENUS1-AP", 443,  "Web VENUS / IIS", 4),
    ("TIM-VENUS1-AP", 3306, "MariaDB locale (venus, mirthdb)", 4),
    ("TIM-VENUS1-AP", 3389, "RDP", 3),
    ("TIM-VENUS2-IF", 2222, "SFTP de depot des sites", 4),
    ("TIM-VENUS2-IF", 8081, "Tomcat JasperReports", 3),
    ("TIM-VENUS2-IF", 3389, "RDP", 3),
    ("TIM-VENUS3-DB", 3306, "MariaDB isotim (base de production du RIS)", 4),
    ("TIM-VENUS3-DB", 3389, "RDP", 3),
)

# Services critiques surveillés par l'agent, et non par une sonde TCP.
# Mirth Connect ÉCOUTE bien sur 8080, mais n'est PAS publié sur le réseau du
# .63 : son pare-feu est actif (le seul des trois) et aucune règle n'ouvre ce
# port — vérifié le 05/09/2026 depuis le serveur Zabbix ET depuis le poste,
# alors que le port répond en local. Une sonde TCP externe y alarmerait donc
# en permanence sur un service en parfait état. On interroge l'agent, qui voit
# l'état réel du service quel que soit le pare-feu, et on garde le même
# capteur sur le .64 pour que les deux serveurs se lisent pareil.
# hôte, nom du service Windows, libellé
SERVICES = (
    ("TIM-VENUS1-AP", "Mirth Connect Service", "Mirth Connect"),
    ("TIM-VENUS2-IF", "Mirth Connect Service", "Mirth Connect"),
)

# sondes remplacées après coup : l'item et ses déclencheurs sont supprimés
RETIREES = (
    ("TIM-VENUS1-AP", "net.tcp.service[tcp,,8080]"),
    ("TIM-VENUS2-IF", "net.tcp.service[tcp,,8080]"),
)

# volume à surveiller en High : hôte, lettre, libellé, seuil et seuil de
# retour à la normale (en % utilisé). L'hystérésis n'est pas décorative : ce
# volume oscille (4,8 Go libres le 04/09 au soir, 16,4 Go le 05/09 à 11 h
# après passage de Venus_Clean_Daemon), un seuil sec produirait des rafales
# de mails à chaque purge.
DISQUE = ("TIM-VENUS1-AP", "D:", "VENUS", 90, 85)


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
    (net.tcp.service[tcp,,443]) part en « non supporté » avec
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
    """Crée les trois hôtes, puis leurs sondes de service."""
    gid = group_id()
    tids = [{"templateid": template_id(TPL_WIN)},
            {"templateid": template_id(TPL_ICMP)}]
    for nom, ip, role in SERVEURS:
        if zbx("host.get", {"filter": {"host": [nom]}}):
            print(f"{nom} existe")
            continue
        zbx("host.create", {
            "host": nom, "name": f"{nom} ({role})",
            "groups": [{"groupid": gid}],
            "templates": tids,
            # interface inutile en mode actif : ancre {HOST.CONN} des simple checks
            "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": ip,
                            "dns": "", "port": "10050"}],
        })
        print(f"{nom} cree ({ip})")

    for nom, port, service, prio in SONDES:
        hid = host_id(nom)
        cle = f"net.tcp.service[tcp,,{port}]"
        ensure_item(hid, {
            "name": f"{service} (tcp/{port}) joignable",
            "key_": cle, "type": 3, "value_type": 3, "delay": "1m",
            "interfaceid": interface_id(hid),
        })
        desc = f"{service} (tcp/{port}) INJOIGNABLE sur {nom}"
        if ensure_trigger(desc, f"max(/{nom}/{cle},3m)=0", prio):
            print(f"  sonde {nom} tcp/{port} ({service}) -> {'High' if prio == 4 else 'Average'}")

    for nom, svc, libelle in SERVICES:
        hid = host_id(nom)
        cle = f'service.info["{svc}",state]'
        # type 7 = agent actif : aucune interface, aucun port entrant
        ensure_item(hid, {
            "name": f"{libelle} : etat du service",
            "key_": cle, "type": 7, "value_type": 3, "delay": "1m",
        })
        desc = f"SERVICE CRITIQUE {libelle} arrete sur {nom}"
        # service.info[...,state] : 0 = running, tout le reste est une anomalie
        if ensure_trigger(desc, f"last(/{nom}/{cle})<>0", 4):
            print(f"  service {nom} « {svc} » -> High")

    for nom, cle in RETIREES:
        hid = host_id(nom)
        ex = zbx("item.get", {"hostids": [hid], "filter": {"key_": [cle]}})
        if ex:
            zbx("item.delete", [ex[0]["itemid"]])
            print(f"  sonde retiree : {nom} {cle}")


def disque():
    """Déclencheur High sur le volume saturé du .63, après découverte."""
    nom, lettre, label, seuil, retour = DISQUE
    hid = host_id(nom)
    cle = f"vfs.fs.dependent.size[{lettre},pused]"
    if not zbx("item.get", {"hostids": [hid], "filter": {"key_": [cle]}}):
        sys.exit(f"item {cle} pas encore decouvert sur {nom} : attendre la "
                 f"decouverte des volumes par l'agent, puis relancer")
    # le template classerait ce volume en Average (donc sans mail) : on eteint
    # son seuil CRIT par macro contextuelle {#FSLABEL}({#FSNAME}) et on le
    # remplace par un declencheur High. Le seuil WARN reste actif.
    macro = f'{{$VFS.FS.PUSED.MAX.CRIT:"{label}({lettre})"}}'
    ex = zbx("usermacro.get", {"hostids": [hid], "filter": {"macro": [macro]}})
    if not ex:
        zbx("usermacro.create", {"hostid": hid, "macro": macro, "value": "100"})
        print(f"macro posee : {macro} = 100 (eteint l'Average du gabarit)")
    desc = f"VOLUME CRITIQUE {lettre} ({label}) sur {nom}"
    expr = f"min(/{nom}/{cle},5m)>{seuil}"
    recov = f"max(/{nom}/{cle},30m)<{retour}"
    if ensure_trigger(desc, expr, 4, recov):
        print(f"declencheur High pose : {desc}")
        print(f"  probleme  : {expr}")
        print(f"  retour    : {recov}")
    else:
        print(f"declencheur deja present : {desc}")


def check():
    noms = [s[0] for s in SERVEURS]
    for nom in noms:
        hid = host_id(nom)
        items = zbx("item.get", {"hostids": [hid], "output": ["key_", "lastvalue", "lastclock"],
                                 "filter": {"key_": ["system.uptime", "icmpping",
                                                     "vfs.fs.dependent.size[D:,pused]"]}})
        vus = {i["key_"]: i for i in items}
        up = vus.get("system.uptime", {}).get("lastclock", "0")
        etat = "recoit des donnees" if up != "0" else "AUCUNE donnee d'agent"
        print(f"{nom:16} {etat}")
        for cle in ("icmpping", "vfs.fs.dependent.size[D:,pused]"):
            if cle in vus:
                print(f"                 {cle} = {vus[cle]['lastvalue']}")
        vol = zbx("item.get", {"hostids": [hid], "search": {"key_": "vfs.fs.dependent.size["},
                               "output": ["key_"]})
        lettres = sorted({i["key_"].split("[")[1].split(",")[0] for i in vol})
        if lettres:
            print(f"                 volumes decouverts : {', '.join(lettres)}")
    gid = group_id()
    pbs = zbx("problem.get", {"groupids": [gid], "output": ["name", "severity"]})
    print(f"\nproblemes ouverts dans « {GROUP} » : {len(pbs)}")
    for p in pbs:
        if p["name"].count("VENUS") or p["severity"] in ("4", "5"):
            print(f"  [{p['severity']}] {p['name']}")


if __name__ == "__main__":
    cmds = {"hotes": hotes, "disque": disque, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
