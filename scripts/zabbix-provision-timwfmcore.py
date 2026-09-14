#!/usr/bin/env python3
"""Provisioning Zabbix de la Vue PACS Philips TIMWFMCORE (192.168.101.52, DC
TELLIS) — supervision applicative posée le 11/09/2026 (17-zabbix.md § Vue PACS
TIMWFMCORE, 13-tellis.md § TIMWFMCORE).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API Zabbix (« provisioning »,
rattaché à supportTIM) est lu dans /root/.zbx-api-token. Aucun autre secret.

Point de départ : l'hôte TIMWFMCORE EXISTE déjà (agent 2 actif, gabarit
« Windows by Zabbix agent active », 206 items, seuils Database(F:) posés le
30/08/2026). Ce script ne le recrée pas : il le complète. Avant lui, seule la
couche Windows était surveillée ; rien ne regardait l'applicatif Vue PACS, la
chaîne de sauvegarde RMAN, la réception DICOM ni les plantages.

Choix de conception, expliqués ici pour ne pas être défaits plus tard :
  - l'hôte n'avait AUCUNE interface (agent actif pur). Les simple checks
    (sondes TCP, ICMP) en exigent une comme ancre {HOST.CONN} : on en déclare
    une (agent, 192.168.101.52:10050) sans qu'aucun sondage passif n'ait lieu.
    Même rôle que sur les VENUS ;
  - « ICMP Ping » est ajouté EN PLUS du gabarit agent actif : cumul sûr
    (vérifié le 05/09/2026, aucun item icmpping dans le gabarit agent actif),
    interdit en revanche avec « Windows by SNMP » (piège syngo) ;
  - les sondes TCP sont des simple checks à la minute, déclencheur
    max(...,3m)=0, repris du motif syngo/VENUS. High pour ce qui est vital
    (le mail ne part qu'en High ou Disaster), Average pour le reste. Elles
    partent du CT 204 par wg2 : la route retour 10.40.0.0/24 via .59 existe
    sur .52 mais est VOLATILE (ActiveStore) — si toutes les sondes tombent
    ensemble après un reboot du PACS, regarder d'abord cette route ;
  - services critiques : le gabarit découvre déjà chaque service Windows
    (service.discovery) et porte un déclencheur Average « is not running »,
    donc sans mail. On pose un déclencheur High dédié sur l'item DÉCOUVERT
    (on ne crée pas d'item doublon, la clé serait identique) et on désactive
    l'Average du gabarit pour ces services-là — motif pacs03 (30/08/2026) ;
  - sauvegarde RMAN : vfs.dir.count avec max_age, pas vfs.dir.get — le
    prétraitement JSONPath ne sait pas faire un max() sur des dates. Cycles
    constatés le 11/09/2026 : archivelogs toutes les 3 h (logs back_archive.ok_*),
    copie complète des datafiles le vendredi (COPY\\DF_*), DBInfo quotidien ;
  - plantages : eventlog[] limité à la source « Application Error » id 1000
    (10 à 60 événements/jour), Average si svstream.exe en rafale. Le dossier
    crashes/ donne la courbe de tendance. Le High « svdser.exe » posé le 11/09
    a été RETIRÉ le 14/09/2026 (5 mails le 11/09) : Philips indique que ces
    vidages sont normaux, le serveur DICOM se termine de lui-même après
    quelques minutes sans activité — RETIRES le supprime s'il existe encore ;
  - contrôles internes du PACS (Imaginet System Check, 15 scripts perl toutes
    les 15 min) : le PACS s'auto-surveille mais personne ne lisait le résultat.
    logrt[] sur system_checks\\, restreint aux quatre contrôles utiles — le
    reste (uptime, cpu) bavarde toutes les 15 min. C'est le SEUL accès à
    l'état Oracle : l'authentification OS « / as sysdba » est refusée en
    session SSH (ORA-01017, constaté le 11/09/2026) ;
  - sous-commande « disque » : BACKUP(G:) oscille de +200 Go chaque vendredi
    (copie complète) avant purge de la précédente : 74 % → ~94 % → 74 %. Un
    High à 85 % sonnerait chaque semaine pour rien. On laisse l'Average du
    gabarit à 90 % (visible, sans mail) et on pose un High à hystérésis
    95 %/90 % qui ne parle que si la purge n'a pas eu lieu.

Usage : zabbix-provision-timwfmcore.py {hotes|disque|check}
"""
import json
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
HOST = "TIMWFMCORE"
IP = "192.168.101.52"
TPL_ICMP = "ICMP Ping"
LOG = r"C:\Program Files\Carestream\System5\log"
RMAN = r"G:\Backup\oradata\mst1\backup"

# port, nom du service, sévérité (4 = High -> mail, 3 = Average)
SONDES = (
    (2104, "MVSMAIN - serveur DICOM Vue PACS (AET TODAY, URGENCE...)", 4),
    (2001, "Loader DICOM", 4),
    (2105, "Loader DICOM (second port)", 4),
    (1521, "Oracle listener mst1", 4),
    (443, "IIS / portail Vue", 4),
    (22104, "MVSMAIN securise (TLS)", 3),
    (8080, "Tomcat 7", 3),
    (7789, "FLEXlm (licences)", 3),
    (3389, "RDP", 3),
    (22, "SSH (acces admin TIM)", 3),
)

# nom Windows du service (tel que découvert par le gabarit), libellé
SERVICES = (
    ("Imaginet MVSMain Server", "MVSMain (serveur DICOM)"),
    ("Imaginet MVSMain Secured Server", "MVSMain securise"),
    ("Imaginet Loader Server", "Loader DICOM"),
    ("Imaginet Auto-Router Execution Module", "AutoRouter execution"),
    ("Imaginet Auto-Router Scheduling Module", "AutoRouter planification"),
    ("Imaginet Medilink Listener", "Medilink HL7"),
    ("Imaginet RisSync Server", "RisSync"),
    ("Imaginet Task Dispatcher", "Task Dispatcher"),
    ("Imaginet PACS Restarter Service", "PACS Restarter (relance les processus plantes)"),
    ("Imaginet DataGrid Controller", "DataGrid Controller"),
    ("Mirth3.5.2", "Mirth Connect 3.5.2"),
    ("OracleServicemst1", "Oracle instance mst1"),
    ("OracleOraDB19Home1TNSListener", "Oracle listener"),
    ("Tomcat7", "Apache Tomcat 7"),
    ("W3SVC", "IIS"),
    ("FLEXlm Service", "FLEXlm licences"),
    ("Kafka", "Kafka"),
    ("Zookeeper", "Zookeeper"),
    ("Ignite", "Ignite Server Node"),
)

# clé, nom, déclencheur (description, expression, sévérité)
# vfs.dir.count[dir,regex_incl,regex_excl,types_incl,types_excl,max_depth,
#               min_size,max_size,min_age,max_age] — =0 signifie « rien de
# plus récent que max_age »
SAUVEGARDES = (
    (f'vfs.dir.count["{RMAN}","^back_archive\\.ok_",,file,,0,,,,8h]',
     "RMAN : sauvegardes d'archivelogs de moins de 8 h",
     "SAUVEGARDE RMAN archivelogs absente depuis 8 h sur TIMWFMCORE (cycle normal 3 h)", 4),
    (f'vfs.dir.count["{RMAN}\\COPY","^DF_",,file,,0,,,,9d]',
     "RMAN : copie complete des datafiles de moins de 9 j",
     "SAUVEGARDE RMAN copie complete absente depuis 9 j sur TIMWFMCORE (cycle normal hebdo, vendredi)", 4),
    (r'vfs.dir.count["G:\Backup\DBInfo","^DBInfo_",,file,,0,,,,2d]',
     "RMAN : export DBInfo de moins de 2 j",
     "Export DBInfo absent depuis 2 j sur TIMWFMCORE", 3),
)

CRASH_DIR = f'vfs.dir.count["{LOG}\\crashes",,,file,,0,,,,24h]'
EVENTLOG = 'eventlog[Application,,"Error","Application Error",1000,,skip]'
SYSCHECK = (f'logrt["{LOG}\\system_checks\\log_system_check_.*\\.log",'
            '"(check_oracle_free_space|check_mirth|check_patient_data|check_storage)\\.pl ended with errors",,,skip]')

# volume, libellé, seuil High, seuil de retour (en % utilisé)
DISQUE = ("G:", "BACKUP", 95, 90)

# déclencheurs posés par une version antérieure du script et retirés depuis
# (description exacte, motif) — supprimés s'ils existent encore
RETIRES = (
    (f"PLANTAGE du serveur DICOM svdser.exe sur {HOST} (coupe les receptions en cours)",
     "Philips, 14/09/2026 : svdser.exe se termine seul apres quelques minutes sans activite"),
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


def host_id():
    h = zbx("host.get", {"filter": {"host": [HOST]}})
    if not h:
        sys.exit(f"hote introuvable: {HOST} — il doit exister (agent actif raccorde le 30/08/2026)")
    return h[0]["hostid"]


def template_id(name):
    t = zbx("template.get", {"filter": {"host": [name]}})
    if not t:
        sys.exit(f"template introuvable: {name}")
    return t[0]["templateid"]


def interface_id(hid):
    """L'interface agent de l'hôte, créée si absente (ancre des simple checks)."""
    i = zbx("hostinterface.get", {"hostids": [hid], "output": ["interfaceid"]})
    if i:
        return i[0]["interfaceid"]
    iid = zbx("hostinterface.create", {"hostid": hid, "type": 1, "main": 1,
                                       "useip": 1, "ip": IP, "dns": "",
                                       "port": "10050"})["interfaceids"][0]
    print(f"interface agent creee ({IP}) : ancre des simple checks, aucun sondage passif")
    return iid


def ensure_item(hid, params):
    """Crée l'item, ou rattache l'interface à un item déjà créé sans elle.

    Piège (05/09/2026) : un simple check dont la clé laisse l'adresse vide
    part en « non supporté » tant que l'item ne porte pas explicitement
    interfaceid — l'interface web la rattache toute seule, l'API non.
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


def retirer_trigger(desc, motif):
    t = zbx("trigger.get", {"filter": {"description": [desc]}, "output": ["triggerid"]})
    if t:
        zbx("trigger.delete", [x["triggerid"] for x in t])
        print(f"  declencheur retire ({motif}) : {desc}")
        return True
    return False


def hotes():
    hid = host_id()
    iid = interface_id(hid)

    # --- ICMP Ping en plus du gabarit agent actif -------------------------
    tpl = zbx("host.get", {"hostids": [hid], "selectParentTemplates": ["host"]})[0]["parentTemplates"]
    if not any(t["host"] == TPL_ICMP for t in tpl):
        zbx("host.update", {"hostid": hid,
                            "templates": [{"templateid": t["templateid"]} for t in
                                          zbx("template.get", {"filter": {"host": [x["host"] for x in tpl]}})]
                            + [{"templateid": template_id(TPL_ICMP)}]})
        print(f"gabarit « {TPL_ICMP} » lie")

    # --- sondes TCP ---------------------------------------------------------
    for port, service, prio in SONDES:
        cle = f"net.tcp.service[tcp,,{port}]"
        ensure_item(hid, {
            "name": f"{service} (tcp/{port}) joignable",
            "key_": cle, "type": 3, "value_type": 3, "delay": "1m",
            "interfaceid": iid,
        })
        desc = f"{service} (tcp/{port}) INJOIGNABLE sur {HOST}"
        if ensure_trigger(desc, f"max(/{HOST}/{cle},3m)=0", prio):
            print(f"  sonde tcp/{port} ({service}) -> {'High' if prio == 4 else 'Average'}")

    # --- services critiques : High sur l'item decouvert, Average du gabarit eteint
    for svc, libelle in SERVICES:
        cle = f'service.info["{svc}",state]'
        if not zbx("item.get", {"hostids": [hid], "filter": {"key_": [cle]}}):
            print(f"  ATTENTION service non decouvert par le gabarit : {svc} (pas de declencheur)")
            continue
        desc = f"SERVICE CRITIQUE {libelle} en anomalie sur {HOST}"
        # service.info[...,state] : 0 = running, tout le reste est une anomalie
        if ensure_trigger(desc, f"last(/{HOST}/{cle})<>0", 4):
            print(f"  service « {svc} » -> High")
        for t in zbx("trigger.get", {"hostids": [hid], "output": ["triggerid", "status", "description"],
                                     "search": {"description": f'"{svc}"'}}):
            if "is not running" in t["description"] and t["status"] == "0":
                zbx("trigger.update", {"triggerid": t["triggerid"], "status": 1})
                print(f"    doublon Average du gabarit desactive : {t['description']}")

    # --- sauvegarde RMAN ----------------------------------------------------
    for cle, nom, desc, prio in SAUVEGARDES:
        # type 7 = agent actif : aucune interface, aucun port entrant
        ensure_item(hid, {"name": nom, "key_": cle, "type": 7, "value_type": 3,
                          "delay": "10m"})
        if ensure_trigger(desc, f"last(/{HOST}/{cle})=0", prio):
            print(f"  sauvegarde : {nom} -> {'High' if prio == 4 else 'Average'}")

    # --- plantages applicatifs ---------------------------------------------
    ensure_item(hid, {"name": "Plantages applicatifs (fichiers crashes/ de moins de 24 h)",
                      "key_": CRASH_DIR, "type": 7, "value_type": 3, "delay": "10m"})
    if ensure_trigger(f"Tempete de plantages Vue PACS sur {HOST} (>= 20 en 24 h)",
                      f"last(/{HOST}/{CRASH_DIR})>=20", 3):
        print("  plantages : courbe crashes/ -> Average si >= 20 en 24 h")
    ensure_item(hid, {"name": "Journal Application : plantages (Application Error 1000)",
                      "key_": EVENTLOG, "type": 7, "value_type": 2, "delay": "1m",
                      "history": "30d"})
    if ensure_trigger(f"Plantages svstream.exe en rafale sur {HOST} (>= 10 en 24 h)",
                      f'count(/{HOST}/{EVENTLOG},24h,"regexp","svstream.exe")>=10', 3):
        print("  rafale svstream.exe -> Average")

    # --- controles internes du PACS (Imaginet System Check) -----------------
    ensure_item(hid, {"name": "Controles internes du PACS (system_checks : oracle, mirth, patient data, storage)",
                      "key_": SYSCHECK, "type": 7, "value_type": 2, "delay": "5m",
                      "history": "30d"})
    if ensure_trigger(f"ORACLE mst1 : espace tablespace CRITICAL (controle interne du PACS) sur {HOST}",
                      f'find(/{HOST}/{SYSCHECK},1h,"regexp","check_oracle_free_space.pl ended with errors: .CRITICAL.")=1', 4):
        print("  oracle CRITICAL -> High")
    if ensure_trigger(f"ORACLE mst1 : espace tablespace WARNING (controle interne du PACS) sur {HOST}",
                      f'find(/{HOST}/{SYSCHECK},1h,"regexp","check_oracle_free_space.pl ended with errors: .WARNING.")=1', 3):
        print("  oracle WARNING -> Average")
    if ensure_trigger(f"Controle interne du PACS en CRITICAL (mirth, patient data ou storage) sur {HOST}",
                      f'find(/{HOST}/{SYSCHECK},1h,"regexp","(check_mirth|check_patient_data|check_storage).pl ended with errors: .CRITICAL.")=1', 3):
        print("  mirth/patient data/storage CRITICAL -> Average")

    # --- declencheurs retires depuis (idempotent) ---------------------------
    for desc, motif in RETIRES:
        retirer_trigger(desc, motif)


def disque():
    """Déclencheur High à hystérésis sur BACKUP(G:), après découverte."""
    lettre, label, seuil, retour = DISQUE
    hid = host_id()
    cle = f"vfs.fs.dependent.size[{lettre},pused]"
    if not zbx("item.get", {"hostids": [hid], "filter": {"key_": [cle]}}):
        sys.exit(f"item {cle} pas encore decouvert : attendre la decouverte des volumes, puis relancer")
    desc = f"{HOST}: FS {label}({lettre}) >= {seuil} % (purge RMAN en retard ?)"
    expr = f"min(/{HOST}/{cle},5m)>{seuil}"
    recov = f"max(/{HOST}/{cle},30m)<{retour}"
    if ensure_trigger(desc, expr, 4, recov):
        print(f"declencheur High pose : {desc}")
        print(f"  probleme  : {expr}")
        print(f"  retour    : {recov}")
    else:
        print(f"declencheur deja present : {desc}")
    print("(l'Average du gabarit a 90 % est conserve : visible, sans mail)")


def check():
    hid = host_id()
    items = zbx("item.get", {"hostids": [hid], "output": ["key_", "name", "lastvalue", "lastclock", "state", "error"]})
    ko = [i for i in items if i["state"] == "1"]
    print(f"{HOST}: {len(items)} items, {len(ko)} non supportes")
    for i in ko:
        print(f"  NON SUPPORTE {i['key_']} : {i['error']}")
    for i in items:
        k = i["key_"]
        if k in ("system.uptime", "icmpping", "icmppingloss") or k.startswith(("net.tcp.service", "vfs.dir.count")) \
           or k.startswith("service.info") and any(f'"{s}"' in k for s, _ in SERVICES):
            print(f"  {k:90.90} = {i['lastvalue']}")
    pbs = zbx("problem.get", {"hostids": [hid], "output": ["name", "severity"]})
    print(f"\nproblemes ouverts sur {HOST} : {len(pbs)}")
    for p in pbs:
        print(f"  [{p['severity']}] {p['name']}")


if __name__ == "__main__":
    cmds = {"hotes": hotes, "disque": disque, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
