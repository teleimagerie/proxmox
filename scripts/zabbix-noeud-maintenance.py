#!/usr/bin/env python3
"""Fait taire Zabbix pour une maintenance planifiée d'un ou plusieurs nœuds PVE,
sans aveugler le reste du cluster (Ceph, autres nœuds, invités).

Une maintenance Zabbix sur l'hôte cluster-pve couperait TOUT (les déclencheurs
n'ont qu'un tag « scope:availability ») : on désactive donc seulement, pour
chaque nœud nommé, « Proxmox VE: Node [pveN] offline » (gabarit officiel,
déclencheur découvert) et « pveN: API 8006 injoignable » (gabarit TIM).
Un nœud en maintenance HA n'a plus d'invité : rien d'autre ne sonnera.

S'exécute SUR le CT 204 (jeton API dans /root/.zbx-api-token). Idempotent.

Usage : zabbix-noeud-maintenance.py {off|on|status} pve1 [pve2 ...]
  off     désactive les déclencheurs des nœuds (à faire AVANT la coupure)
  on      les réactive (à faire APRÈS le retour, quand pvecm les voit online)
  status  affiche leur état

Écrit le 16/09/2026 pour la coupure OVH du 06/10/2026 (baie de pve1 et pve2,
06-reste-a-faire.md § 14)."""
import json
import sys
import urllib.request

API = "http://127.0.0.1:8080/api_jsonrpc.php"
TOKEN = open("/root/.zbx-api-token").read().strip()


def zbx(method, params):
    req = urllib.request.Request(
        API, data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                              "id": 1}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    out = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in out:
        sys.exit(f"API {method}: {out['error']}")
    return out["result"]


def triggers(node):
    found = []
    for pattern in (f"Node [{node}] offline", f"{node}: API 8006 injoignable"):
        t = zbx("trigger.get", {"host": "cluster-pve", "search": {"description": pattern},
                                "output": ["triggerid", "description", "status", "value"]})
        found += [x for x in t if pattern in x["description"]]
    return found


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("off", "on", "status"):
        sys.exit(__doc__)
    action, nodes = sys.argv[1], sys.argv[2:]
    for node in nodes:
        for t in triggers(node):
            etat = "DESACTIVE" if t["status"] == "1" else "actif"
            if action == "status" or (action == "off" and t["status"] == "1") \
                    or (action == "on" and t["status"] == "0"):
                print(f"  {t['description']:<45} {etat}  (probleme: {'oui' if t['value']=='1' else 'non'})")
                continue
            zbx("trigger.update", {"triggerid": t["triggerid"], "status": "1" if action == "off" else "0"})
            print(f"  {t['description']:<45} {etat} -> {'DESACTIVE' if action=='off' else 'actif'}")
    if action == "off":
        print("Rappel : relancer avec « on » au retour des nœuds.")


if __name__ == "__main__":
    main()
