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
  La vue hyperviseur (CPU, RAM, disque, état) vient déjà de la découverte
  « Proxmox VE by HTTP » de l'hôte cluster-pve, rien à faire.

Usage : zabbix-provision-staging.py {hotes|certs|check}
"""
import json
import sys
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


def check():
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
    actions = {"hotes": hotes, "certs": certs, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
