#!/usr/bin/env python3
"""Provisioning Zabbix de la supervision du cluster PVE — trace exécutable
du chantier du 29/08/2026 (17-zabbix.md § Supervision du cluster).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API Zabbix (nommé « provisioning »,
rattaché à supportTIM, révocable dans l'UI) est lu dans /root/.zbx-api-token.
Le secret du token PVE n'est requis qu'à la création de l'hôte cluster-pve :
variable d'environnement PVE_TOKEN_SECRET.

Objets gérés :
  - groupe d'hôtes « Infrastructure PVE » ;
  - hôte cluster-pve : template officiel « Proxmox VE by HTTP » + macros
    (URL pve1, token zabbix@pve!monitoring, stockage Warning à 80) ;
  - template « TIM Cluster PVE » : Ceph via /cluster/ceph/status (santé,
    OSD) + déclencheurs, joignabilité :8006 des trois nœuds (simple checks) ;
  - retouches du template officiel : « Not running », disque LXC, mémoire
    (nœud/LXC/VM) relevés en High ; manual_close sur les mémoire ;
  - déclencheur High « vm-storage >= 85 % (nearfull Ceph) » ;
  - 9 hôtes certificats (template « Website certificate by Zabbix agent 2 »,
    macro expiry 14 j, trigger d'expiration en High) — l'IP de connexion
    force 10.40.0.10/.30 pour éviter le piège n° 32 ;
  - hôtes agents des invités (créés une fois, listés ici pour mémoire) ;
  - déclencheurs FS >= 90 % sur les VM pbs et odoo ;
  - tableau de bord « Cluster PVE » (créé une fois ; non recréé s'il existe).

Usage : zabbix-provision-pve.py {group-host|tim-template|certs|check}
"""
import json
import os
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
GROUP = "Infrastructure PVE"
TPL = "TIM Cluster PVE"
PVE_TPL = "Proxmox VE by HTTP"
CERT_TPL = "Website certificate by Zabbix agent 2"
NODES = ("pve1", "pve2", "pve3")


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


def group_host():
    gid = group_id()
    h = zbx("host.get", {"filter": {"host": ["cluster-pve"]}})
    if h:
        print("cluster-pve existe")
        return
    secret = os.environ.get("PVE_TOKEN_SECRET") or sys.exit("PVE_TOKEN_SECRET absent")
    zbx("host.create", {
        "host": "cluster-pve", "name": "Cluster PVE (tim-cluster)",
        "groups": [{"groupid": gid}],
        "templates": [{"templateid": template_id(PVE_TPL)}],
        "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": "127.0.0.1",
                        "dns": "", "port": "10050"}],  # ancre des simple checks
        "macros": [
            {"macro": "{$PVE.URL.HOST}", "value": "pve1.infra.teleimagerie.net"},
            {"macro": "{$PVE.TOKEN.ID}", "value": "zabbix@pve!monitoring"},
            {"macro": "{$PVE.TOKEN.SECRET}", "value": secret, "type": "1"},
            {"macro": "{$PVE.STORAGE.PUSE.MAX.WARN}", "value": "80"},
            {"macro": "{$PVE.LXC.MEMORY.PUSE.MAX.WARN}", "value": "95"},
            {"macro": "{$PVE.VM.MEMORY.PUSE.MAX.WARN}", "value": "95"},
        ]})
    print("cluster-pve cree")


def ensure_item(tid, params):
    ex = zbx("item.get", {"templateids": [tid], "filter": {"key_": [params["key_"]]}})
    return ex[0]["itemid"] if ex else zbx("item.create", {**params, "hostid": tid})["itemids"][0]


def ensure_trigger(tid, desc, expr, prio):
    if not zbx("trigger.get", {"templateids": [tid], "filter": {"description": [desc]}}):
        zbx("trigger.create", {"description": desc, "expression": expr, "priority": prio})


def tim_template():
    tg = zbx("templategroup.get", {"filter": {"name": ["Templates"]}})
    tgid = tg[0]["groupid"] if tg else zbx("templategroup.create", {"name": "Templates"})["groupids"][0]
    t = zbx("template.get", {"filter": {"host": [TPL]}})
    tid = t[0]["templateid"] if t else zbx("template.create", {"host": TPL, "groups": [{"groupid": tgid}]})["templateids"][0]

    master = ensure_item(tid, {
        "name": "Ceph: statut brut (API PVE)", "key_": "pve.ceph.status", "type": 19,
        "value_type": 4, "delay": "1m", "history": "1d", "trends": "0",
        "url": "https://{$PVE.URL.HOST}:{$PVE.URL.PORT}/api2/json/cluster/ceph/status",
        "headers": [{"name": "Authorization",
                     "value": "PVEAPIToken={$PVE.TOKEN.ID}={$PVE.TOKEN.SECRET}"}]})
    for name, key, path, vtype in (
            ("Ceph: sante", "pve.ceph.health", "$.data.health.status", 1),
            ("Ceph: OSD total", "pve.ceph.osd.num", "$.data.osdmap.num_osds", 3),
            ("Ceph: OSD up", "pve.ceph.osd.up", "$.data.osdmap.num_up_osds", 3),
            ("Ceph: OSD in", "pve.ceph.osd.in", "$.data.osdmap.num_in_osds", 3)):
        ensure_item(tid, {"name": name, "key_": key, "type": 18, "master_itemid": master,
                          "value_type": vtype, "delay": "0", "history": "7d",
                          "preprocessing": [{"type": 12, "params": path,
                                             "error_handler": 0, "error_handler_params": ""}]})
    for n in NODES:
        ensure_item(tid, {"name": f"API {n}:8006 joignable",
                          "key_": f"net.tcp.service[https,{n}.infra.teleimagerie.net,8006]",
                          "type": 3, "value_type": 3, "delay": "1m", "history": "7d"})

    ensure_trigger(tid, "Ceph HEALTH_ERR", f'last(/{TPL}/pve.ceph.health)="HEALTH_ERR"', 5)
    ensure_trigger(tid, "Ceph HEALTH_WARN", f'last(/{TPL}/pve.ceph.health)="HEALTH_WARN"', 2)
    ensure_trigger(tid, "Ceph: OSD down", f'last(/{TPL}/pve.ceph.osd.up)<last(/{TPL}/pve.ceph.osd.num)', 4)
    ensure_trigger(tid, "Ceph: OSD out", f'last(/{TPL}/pve.ceph.osd.in)<last(/{TPL}/pve.ceph.osd.num)', 4)
    for n in NODES:
        ensure_trigger(tid, f"{n}: API 8006 injoignable",
                       f'max(/{TPL}/net.tcp.service[https,{n}.infra.teleimagerie.net,8006],#3)=0', 4)

    h = zbx("host.get", {"filter": {"host": ["cluster-pve"]}})
    if h:
        zbx("host.massadd", {"hosts": [{"hostid": h[0]["hostid"]}], "templates": [{"templateid": tid}]})

    # retouches du template officiel : severites en High + manual_close
    pve_tid = template_id(PVE_TPL)
    protos = zbx("triggerprototype.get", {"templateids": [pve_tid],
                 "output": ["triggerid", "description", "priority", "manual_close"]})
    for p in protos:
        d = p["description"]
        wanted_high = ("Not running" in d or "high disk space usage" in d or "high memory usage" in d)
        if wanted_high and p["priority"] != "4":
            zbx("triggerprototype.update", {"triggerid": p["triggerid"], "priority": 4})
        if "high memory usage" in d and p["manual_close"] != "1":
            zbx("triggerprototype.update", {"triggerid": p["triggerid"], "manual_close": 1})

    # nearfull : sur l item decouvert (a re-poser si l item est recree par la LLD)
    near = "vm-storage >= 85 % (nearfull Ceph)"
    if h and not zbx("trigger.get", {"hostids": [h[0]["hostid"]], "filter": {"description": [near]}}):
        zbx("trigger.create", {"description": near, "priority": 4, "expression":
            'last(/cluster-pve/proxmox.node.disk[pve1,vm-storage])/last(/cluster-pve/proxmox.node.maxdisk[pve1,vm-storage])>=0.85'})
    print("template TIM + retouches OK")


def certs():
    gid = group_id()
    tplid = template_id(CERT_TPL)
    for m in zbx("usermacro.get", {"hostids": [tplid]}):
        if m["macro"] == "{$CERT.EXPIRY.WARN}" and m["value"] != "14":
            zbx("usermacro.update", {"hostmacroid": m["hostmacroid"], "value": "14"})
    for t in zbx("trigger.get", {"templateids": [tplid], "output": ["triggerid", "description", "priority"]}):
        if "expires soon" in t["description"] and t["priority"] != "4":
            zbx("trigger.update", {"triggerid": t["triggerid"], "priority": 4})
    sites = [
        ("cert-zabbix", "zabbix.teleimagerie.net", None, "10.40.0.10"),
        ("cert-auth", "auth.teleimagerie.net", None, "10.40.0.10"),
        ("cert-pacs-secours", "pacs-secours.teleimagerie.net", None, "10.40.0.10"),
        ("cert-odoo", "odoo.teleimagerie.net", None, "10.40.0.10"),
        ("cert-syngo", "syngo.teleimagerie.net", None, "10.40.0.10"),
        ("cert-headscale", "headscale.teleimagerie.net", None, "10.40.0.30"),
        ("cert-pve1", "pve1.infra.teleimagerie.net", "8006", None),
        ("cert-pve2", "pve2.infra.teleimagerie.net", "8006", None),
        ("cert-pve3", "pve3.infra.teleimagerie.net", "8006", None),
    ]
    for host, fqdn, port, ip in sites:
        if zbx("host.get", {"filter": {"host": [host]}}):
            continue
        macros = [{"macro": "{$CERT.WEBSITE.HOSTNAME}", "value": fqdn}]
        if port:
            macros.append({"macro": "{$CERT.WEBSITE.PORT}", "value": port})
        if ip:  # piege 32 : ne jamais laisser un client interne viser la VIP .122
            macros.append({"macro": "{$CERT.WEBSITE.IP}", "value": ip})
        zbx("host.create", {"host": host,
            "name": f"Certificat {fqdn}" + (f":{port}" if port else ""),
            "groups": [{"groupid": gid}], "templates": [{"templateid": tplid}],
            "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": "10.40.0.60",
                            "dns": "", "port": "10050"}],
            "macros": macros})
        print(host, "cree")
    print("certs OK")


def check():
    probs = zbx("problem.get", {"groupids": [group_id()], "output": ["name", "severity"]})
    print("problemes:", [(p["name"], p["severity"]) for p in probs] or "aucun")
    n = zbx("host.get", {"groupids": [group_id()], "countOutput": True})
    print("hotes du groupe:", n)
    for k in ("proxmox.cluster.quorate[tim-cluster]", "pve.ceph.health"):
        i = zbx("item.get", {"host": "cluster-pve", "search": {"key_": k},
                             "output": ["key_", "lastvalue"]})
        if i:
            print(f"  {i[0]['key_']} = {i[0]['lastvalue']}")


if __name__ == "__main__":
    actions = {"group-host": group_host, "tim-template": tim_template,
               "certs": certs, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
