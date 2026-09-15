#!/usr/bin/env python3
"""Provisioning Zabbix des deux pré-productions MyTIM / MyISOTEAM (VM 103 et
104 du cluster) — trace exécutable du chantier du 14/09/2026
(20-mytim-staging.md, 17-zabbix.md).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API (« provisioning ») est lu dans
/root/.zbx-api-token.

Objets gérés, sur le patron des autres invités du cluster :
  - hôtes mytim-staging (10.40.0.80) et myisoteam-staging (10.40.0.90),
    groupe « Infrastructure PVE », template « Linux by Zabbix agent »
    (agent 2 passif dans la VM, ufw ouvert sur 10050 depuis 10.40.0.60 par
    provisioning.yaml du dépôt gestion) ;
  - hôtes certificats cert-staging-tim / cert-staging-isoteam (template
    « Website certificate by Zabbix agent 2 », noms app.staging.*) avec
    l'IP de connexion forcée à 10.40.0.10 — piège n° 32 : depuis le CT 204,
    la VIP .122 mène à la GUI d'OPNsense. Un seul hôte par certificat
    wildcard suffit (gestion. et mailer. portent le même certificat).
  La vue hyperviseur (CPU, RAM, disque, état) vient de la découverte
  « Proxmox VE by HTTP » de l'hôte cluster-pve.
  - hyperviseur : les deux VM tournent sans balloon (balloon: 0) — l'API PVE
    remonte alors mem = memhost (RSS du processus QEMU), soit 101 % de maxmem
    en permanence, et le High « high memory usage » du gabarit ne se ferme
    jamais (82 mails en 24 h le 14/09, rappel horaire d'ALERTE HAUTE). Macro
    contextuelle {$PVE.VM.MEMORY.PUSE.MAX.WARN:"qemu/N"} = 200 sur
    cluster-pve : 100 (le choix fait pour PBS) est atteignable ici, 200 non.
    Les problèmes ouverts sont fermés s'ils ne se ferment pas seuls.
  - seuils : la mémoire réelle des VM (agent, vm.memory.utilization) porte un
    High propre « > 90 % pendant 1 h », retour sous 85 % sur 30 min ; les
    Average du gabarit Linux restent, sans mail.

Usage : zabbix-provision-staging.py {hotes|certs|hyperviseur|seuils|check}
"""
import json
import sys
import time
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()
GROUP = "Infrastructure PVE"
TPL_LINUX = "Linux by Zabbix agent"
CERT_TPL = "Website certificate by Zabbix agent 2"
PROXY_IP = "10.40.0.10"

HOTES = (
    ("mytim-staging", "mytim-staging (VM 103)", "10.40.0.80"),
    ("myisoteam-staging", "myisoteam-staging (VM 104)", "10.40.0.90"),
)
CERTS = (
    ("cert-staging-tim", "Certificat *.staging.teleimagerie.net", "app.staging.teleimagerie.net"),
    ("cert-staging-isoteam", "Certificat *.staging.isoteam.mn", "app.staging.isoteam.mn"),
)
# balloon 0 -> memhost >= maxmem : 100 est atteignable, 200 ne l'est pas
VM_SANS_BALLOON = ("qemu/103", "qemu/104")
MACRO_MEM = '{$PVE.VM.MEMORY.PUSE.MAX.WARN:"%s"}'
SEUIL_MEM = "Memoire reelle > 90 % depuis 1 h"


def zbx(method, params):
    req = urllib.request.Request(
        API,
        data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
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


def hotes():
    gid, tid = group_id(), template_id(TPL_LINUX)
    for host, name, ip in HOTES:
        if zbx("host.get", {"filter": {"host": [host]}}):
            print(f"{host} existe")
            continue
        zbx("host.create", {
            "host": host, "name": name,
            "groups": [{"groupid": gid}],
            "templates": [{"templateid": tid}],
            "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": ip, "dns": "", "port": "10050"}]})
        print(f"{host} cree ({ip})")


def certs():
    gid, tid = group_id(), template_id(CERT_TPL)
    for host, name, fqdn in CERTS:
        if zbx("host.get", {"filter": {"host": [host]}}):
            print(f"{host} existe")
            continue
        zbx("host.create", {
            "host": host, "name": name,
            "groups": [{"groupid": gid}],
            "templates": [{"templateid": tid}],
            # sonde executee par l'agent 2 du CT 204 lui-meme (comme cert-odoo)
            "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": "10.40.0.60", "dns": "", "port": "10050"}],
            "macros": [{"macro": "{$CERT.WEBSITE.HOSTNAME}", "value": fqdn},
                       {"macro": "{$CERT.WEBSITE.IP}", "value": PROXY_IP}]})
        print(f"{host} cree ({fqdn} via {PROXY_IP})")


def host_id(host):
    h = zbx("host.get", {"filter": {"host": [host]}})
    if not h:
        sys.exit(f"hote introuvable: {host}")
    return h[0]["hostid"]


def hyperviseur():
    """Faux signal mémoire de l'hyperviseur neutralisé sur cluster-pve (macro contextuelle)."""
    hid = host_id("cluster-pve")
    changee = False
    for ctx in VM_SANS_BALLOON:
        macro = MACRO_MEM % ctx
        m = zbx("usermacro.get", {"hostids": [hid], "filter": {"macro": [macro]},
                                  "output": ["hostmacroid", "value"]})
        if not m:
            zbx("usermacro.create", {"hostid": hid, "macro": macro, "value": "200",
                                     "description": "15/09/2026 : VM sans balloon, l'API PVE remonte memhost (101 % de maxmem en permanence) ; memoire reelle suivie par l'agent"})
            print(f"  macro {macro} posee a 200")
            changee = True
        elif m[0]["value"] != "200":
            zbx("usermacro.update", {"hostmacroid": m[0]["hostmacroid"], "value": "200"})
            print(f"  macro {macro} mise a jour a 200")
            changee = True
    if changee:
        time.sleep(15)  # cache de configuration (piege n. 41)
    # les problemes doivent se fermer seuls a l'evaluation suivante (item a 1 min) ;
    # sinon fermeture manuelle (manual_close autorise par le gabarit depuis le 29/08)
    for essai in range(3):
        ouverts = [p for p in zbx("problem.get", {"hostids": [hid], "output": ["eventid", "name"]})
                   if "high memory usage" in p["name"] and any(f"({c})" in p["name"] for c in VM_SANS_BALLOON)]
        if not ouverts:
            break
        if essai < 2:
            time.sleep(60)
            continue
        for p in ouverts:
            zbx("event.acknowledge", {"eventids": [p["eventid"]], "action": 1,
                                      "message": "VM sans balloon : faux signal hyperviseur, macro a 200 le 15/09/2026"})
            print(f"  probleme ferme : {p['name']}")


def seuils():
    """High propre sur la mémoire réelle vue par l'agent : > 90 % pendant 1 h, retour sous 85 %."""
    for host, _, _ in HOTES:
        hid = host_id(host)
        if zbx("trigger.get", {"hostids": [hid], "filter": {"description": [SEUIL_MEM]}}):
            continue
        zbx("trigger.create", {
            "description": SEUIL_MEM, "priority": 4, "manual_close": 1,
            "expression": f"min(/{host}/vm.memory.utilization,1h)>90",
            "recovery_mode": 1,
            "recovery_expression": f"max(/{host}/vm.memory.utilization,30m)<85"})
        print(f"  {host}: declencheur « {SEUIL_MEM} » cree")


def check():
    hid = host_id("cluster-pve")
    for ctx in VM_SANS_BALLOON:
        m = zbx("usermacro.get", {"hostids": [hid], "filter": {"macro": [MACRO_MEM % ctx]}, "output": ["value"]})
        print(f"cluster-pve: {MACRO_MEM % ctx} = {m[0]['value'] if m else 'ABSENTE'}")
    mem = [p["name"] for p in zbx("problem.get", {"hostids": [hid], "output": ["name"]}) if "memory" in p["name"]]
    print("cluster-pve: problemes memoire ouverts:", mem or "aucun")
    for host, _, _ in HOTES:
        for t in zbx("trigger.get", {"hostids": [host_id(host)], "filter": {"description": [SEUIL_MEM]},
                                     "output": ["value", "status"]}):
            print(f"{host}: « {SEUIL_MEM} » status={t['status']} value={t['value']}")
        it = zbx("item.get", {"host": host, "filter": {"key_": ["vm.memory.utilization"]}, "output": ["lastvalue"]})
        print(f"{host}: vm.memory.utilization = {it[0]['lastvalue'][:5] if it else '?'} %")
    for host, _, _ in HOTES + CERTS:
        h = zbx("host.get", {"filter": {"host": [host]}, "selectInterfaces": ["ip", "available"]})
        if not h:
            print(f"{host}: ABSENT")
            continue
        items = zbx("item.get", {"hostids": [h[0]["hostid"]], "output": ["name", "lastvalue", "lastclock"],
                                 "filter": {"key_": ["agent.ping", "cert.not_after"]}})
        print(f"{host}: interfaces={[ (i['ip'], i['available']) for i in h[0]['interfaces']]} "
              f"items={[ (i['name'], i['lastvalue']) for i in items]}")


if __name__ == "__main__":
    actions = {"hotes": hotes, "certs": certs, "hyperviseur": hyperviseur,
               "seuils": seuils, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
