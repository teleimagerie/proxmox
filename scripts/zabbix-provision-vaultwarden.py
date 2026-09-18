#!/usr/bin/env python3
"""Provisioning Zabbix du coffre Vaultwarden (VM 105) — chantier du 18/09/2026
(21-vaultwarden.md, 17-zabbix.md).

S'exécute SUR le CT 204. Idempotent : chaque objet est cherché avant d'être
créé ; relancer ne casse rien. Le jeton API (« provisioning ») est lu dans
/root/.zbx-api-token. Squelette : zabbix-provision-staging.py.

Objets gérés :
  - hôte vaultwarden (10.40.0.100), groupe « Infrastructure PVE », template
    « Linux by Zabbix agent » (agent 2 passif dans la VM, ufw ouvert sur
    10050 depuis 10.40.0.60) ;
  - hôte certificat cert-vault (template « Website certificate by Zabbix
    agent 2 », nom vault.teleimagerie.net) avec l'IP de connexion forcée à
    10.40.0.10 — piège n° 32 : depuis le CT 204, la VIP .122 mène à la GUI
    d'OPNsense ;
  - macro {$PVE.VM.MEMORY.PUSE.MAX.WARN:"qemu/105"} = 200 sur cluster-pve
    (VM sans balloon — piège n° 42) ;
  - High « mémoire réelle > 90 % pendant 1 h » sur l'hôte agent.

Usage : zabbix-provision-vaultwarden.py {hotes|certs|hyperviseur|seuils|check|tout}
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
    ("vaultwarden", "vaultwarden (VM 105)", "10.40.0.100"),
)
CERTS = (
    ("cert-vault", "Certificat vault.teleimagerie.net", "vault.teleimagerie.net"),
)
VM_SANS_BALLOON = ("qemu/105",)
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
    """Faux signal mémoire de l'hyperviseur neutralisé d'emblée (leçon du piège n° 42)."""
    hid = host_id("cluster-pve")
    for ctx in VM_SANS_BALLOON:
        macro = MACRO_MEM % ctx
        m = zbx("usermacro.get", {"hostids": [hid], "filter": {"macro": [macro]},
                                  "output": ["hostmacroid", "value"]})
        if not m:
            zbx("usermacro.create", {"hostid": hid, "macro": macro, "value": "200",
                                     "description": "18/09/2026 : VM sans balloon, l'API PVE remonte memhost (101 % de maxmem en permanence) ; memoire reelle suivie par l'agent"})
            print(f"  macro {macro} posee a 200")
        elif m[0]["value"] != "200":
            zbx("usermacro.update", {"hostmacroid": m[0]["hostmacroid"], "value": "200"})
            print(f"  macro {macro} mise a jour a 200")
        else:
            print(f"  macro {macro} deja a 200")


def seuils():
    """High propre sur la mémoire réelle vue par l'agent : > 90 % pendant 1 h, retour sous 85 %."""
    for host, _, _ in HOTES:
        hid = host_id(host)
        if zbx("trigger.get", {"hostids": [hid], "filter": {"description": [SEUIL_MEM]}}):
            print(f"  {host}: declencheur deja present")
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
    for host, _, _ in HOTES + CERTS:
        h = zbx("host.get", {"filter": {"host": [host]}, "selectInterfaces": ["ip", "available"]})
        if not h:
            print(f"{host}: ABSENT")
            continue
        items = zbx("item.get", {"hostids": [h[0]["hostid"]], "output": ["name", "lastvalue"],
                                 "filter": {"key_": ["agent.ping", "cert.not_after"]}})
        print(f"{host}: interfaces={[(i['ip'], i['available']) for i in h[0]['interfaces']]} "
              f"items={[(i['name'], i['lastvalue']) for i in items]}")


def tout():
    hotes(); certs(); hyperviseur(); seuils()
    print("--- pause cache de configuration (piege n° 41) ---")
    time.sleep(15)
    check()


if __name__ == "__main__":
    actions = {"hotes": hotes, "certs": certs, "hyperviseur": hyperviseur,
               "seuils": seuils, "check": check, "tout": tout}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    actions[sys.argv[1]]()
