#!/usr/bin/env python3
"""Configure le NAS-HA zpool-130899 via l'API OVH : partitions, ACL, snapshots.

Idempotent : relancable sans effet de bord, il ne cree que ce qui manque.

Identifiants lus dans /root/.secrets/ovh-nasha.ini (ou $OVH_NASHA_INI),
au format cle = valeur :

    application_key    = ...
    application_secret = ...
    consumer_key       = ...

Le jeton doit porter les droits GET/POST/PUT/DELETE sur /dedicated/nasha/*.
La route de listing GET /dedicated/nasha n'est pas requise : le service est
adresse directement.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://eu.api.ovh.com/1.0"
SERVICE = "zpool-130899"
INI = os.environ.get("OVH_NASHA_INI", "/root/.secrets/ovh-nasha.ini")

# nom, taille en Go, description, snapshots automatiques
# 1800 + 700 = 2500 Go sur 3000 : le reste sert de reserve aux snapshots ZFS.
# La description n'accepte que de l'alphanumerique et des espaces : ni virgule,
# ni tiret, ni accent, sous peine de HTTP 400.
PARTITIONS = [
    ("pbs", 1800, "Datastore Proxmox Backup Server", ["day-1", "day-3", "day-7"]),
    ("vmstore", 700, "Disques VM ISO et templates", ["day-1", "day-7"]),
]

# ACL : IP PUBLIQUES des noeuds. Le NAS-HA n'est pas raccordable au vRack,
# les IP 10.100/10.200/10.30 y seraient refusees. Voir 07-pieges.md.
ACL = {
    "91.134.84.222": "pve1",
    "51.68.240.48": "pve2",
    "51.68.240.191": "pve3",
}


def credentials():
    if not os.path.exists(INI):
        sys.exit(f"Fichier d'identifiants absent : {INI}")
    kv = {}
    for line in open(INI):
        line = line.strip()
        if not line or line.startswith(("#", "[")) or "=" not in line:
            continue
        k, v = line.split("=", 1)
        kv[k.strip()] = v.strip()
    try:
        return kv["application_key"], kv["application_secret"], kv["consumer_key"]
    except KeyError as e:
        sys.exit(f"Cle {e} absente de {INI}")


AK, AS, CK = credentials()


def call(method, path, body=None):
    url = BASE + path
    payload = json.dumps(body) if body is not None else ""
    with urllib.request.urlopen(f"{BASE}/auth/time", timeout=15) as r:
        ts = str(int(r.read()))
    sig = "$1$" + hashlib.sha1(f"{AS}+{CK}+{method}+{url}+{payload}+{ts}".encode()).hexdigest()
    req = urllib.request.Request(
        url,
        data=payload.encode() if payload else None,
        method=method,
        headers={
            "X-Ovh-Application": AK,
            "X-Ovh-Consumer": CK,
            "X-Ovh-Timestamp": ts,
            "X-Ovh-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        sys.exit(f"ERREUR HTTP {e.code} sur {method} {path} : {e.read().decode()[:300]}")


def wait_task(task, label):
    """Attend la fin d'une tache NAS. Les creations de partition sont asynchrones."""
    tid = (task or {}).get("taskId")
    if tid is None:
        return
    for _ in range(120):                      # 120 x 5 s = 10 minutes
        t = call("GET", f"/dedicated/nasha/{SERVICE}/task/{tid}")
        status = t.get("status")
        if status == "done":
            print(f"  {label} : termine")
            return
        if status in ("cancelled", "customerError", "ovhError"):
            sys.exit(f"  {label} : ECHEC ({status}) {t.get('details') or ''}")
        time.sleep(5)
    sys.exit(f"  {label} : toujours en cours apres 10 minutes, arret")


def norm(ip):
    """91.134.84.222/32 et 91.134.84.222 designent la meme chose."""
    return ip.split("/")[0]


print("=== service ===")
info = call("GET", f"/dedicated/nasha/{SERVICE}")
print(f"  {SERVICE} · {info['zpoolSize']} Go · disques {info['diskType']} · "
      f"datacenter {info['datacenter']} · IP {info['ip']}")
print(f"  utilise : {info['zpoolCapacity']} Go")

print("=== partitions ===")
existantes = call("GET", f"/dedicated/nasha/{SERVICE}/partition") or []
for nom, taille, desc, _ in PARTITIONS:
    if nom in existantes:
        p = call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}")
        print(f"  {nom} deja presente ({p['size']} Go, {p['protocol']})")
        continue
    print(f"  creation de {nom} ({taille} Go, NFS)...")
    t = call("POST", f"/dedicated/nasha/{SERVICE}/partition", {
        "partitionName": nom,
        "protocol": "NFS",
        "size": taille,
        "partitionDescription": desc,
    })
    wait_task(t, f"creation {nom}")

print("=== ACL ===")
for nom, _, _, _ in PARTITIONS:
    actuelles = {norm(i) for i in (call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}/access") or [])}
    for ip, hote in ACL.items():
        if ip in actuelles:
            print(f"  {nom} : {ip} ({hote}) deja autorise")
            continue
        print(f"  {nom} : ajout de {ip} ({hote})...")
        t = call("POST", f"/dedicated/nasha/{SERVICE}/partition/{nom}/access", {
            "ip": ip,
            "type": "readwrite",
            "aclDescription": hote,
        })
        wait_task(t, f"acl {nom} {ip}")

print("=== snapshots automatiques ===")
for nom, _, _, snaps in PARTITIONS:
    actuels = set(call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}/snapshot") or [])
    for s in snaps:
        if s in actuels:
            print(f"  {nom} : {s} deja arme")
            continue
        print(f"  {nom} : activation de {s}...")
        t = call("POST", f"/dedicated/nasha/{SERVICE}/partition/{nom}/snapshot",
                 {"snapshotType": s})
        wait_task(t, f"snapshot {nom} {s}")

print("=== etat final ===")
info = call("GET", f"/dedicated/nasha/{SERVICE}")
print(f"  pool : {info['zpoolCapacity']} / {info['zpoolSize']} Go utilises")
for nom in call("GET", f"/dedicated/nasha/{SERVICE}/partition") or []:
    p = call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}")
    acl = call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}/access") or []
    snaps = call("GET", f"/dedicated/nasha/{SERVICE}/partition/{nom}/snapshot") or []
    print(f"  {nom} : {p['size']} Go {p['protocol']} · utilise {p['partitionCapacity']} Go "
          f"(dont {p['usedBySnapshots']} Go de snapshots)")
    print(f"      export   {info['ip']}:/{SERVICE}/{nom}")
    print(f"      acl      {', '.join(sorted(acl)) or '(aucune)'}")
    print(f"      snapshot {', '.join(sorted(snaps)) or '(aucun)'}")
