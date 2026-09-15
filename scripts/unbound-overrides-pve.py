#!/usr/bin/env python3
# Overrides Unbound split-horizon des hyperviseurs : pveN.infra.teleimagerie.net
# -> patte d'administration VLAN 400 (10.40.0.2/.3/.4/.5/.6). Idempotent.
# A executer SUR OPNsense (python3 natif) : ne cree que les entrees absentes,
# ne touche pas aux trois overrides poses a la main le 31/08/2026.
# Meme mecanique que unbound-overrides-staging.py (bloc <host> dans
# unboundplus/hosts, restart d'Unbound — un reload ne regenere pas
# host_entries.conf, piege du 31/08 — puis controle du fichier genere).
import re, shutil, subprocess, sys, uuid
from datetime import date

CONF = "/conf/config.xml"
DOM = "teleimagerie.net"
NODES = {"pve1.infra": "10.40.0.2", "pve2.infra": "10.40.0.3", "pve3.infra": "10.40.0.4",
         "pve4.infra": "10.40.0.5", "pve5.infra": "10.40.0.6"}   # pve4/pve5 : 15/09/2026

s = open(CONF).read()
assert s.count("<hosts>") == 1, "bloc <hosts> unique attendu"
bak = f"{CONF}.bak-pve-overrides-{date.today():%Y%m%d}"
shutil.copy2(CONF, bak)
added = []
for hn, ip in NODES.items():
    if re.search(rf"<hostname>{re.escape(hn)}</hostname>\s*<domain>{re.escape(DOM)}</domain>", s):
        continue
    block = f"""        <host uuid="{uuid.uuid4()}">
          <enabled>1</enabled>
          <hostname>{hn}</hostname>
          <domain>{DOM}</domain>
          <rr>A</rr>
          <mxprio/>
          <mx/>
          <server>{ip}</server>
          <description>Hyperviseur {hn.split('.')[0]} - administration par le chemin prive VLAN 400, {date.today():%d/%m/%Y}</description>
        </host>
"""
    s = s.replace("<hosts>\n", "<hosts>\n" + block, 1)
    added.append(f"{hn}.{DOM} -> {ip}")
if not added:
    print("rien a ajouter (overrides deja presents)")
    sys.exit(0)
open(CONF, "w").write(s)
print("sauvegarde :", bak)
print("ajoutes :", added)
subprocess.run(["configctl", "unbound", "restart"], check=True)
subprocess.run(["configctl", "filter", "reload"], check=True)
he = open("/var/unbound/host_entries.conf").read()
rc = 0
for hn, ip in NODES.items():
    n = f"{hn}.{DOM}"
    ok = f'"{n}  IN A {ip}"' in he
    print(n, "OK" if ok else "ABSENT de host_entries.conf !")
    rc |= not ok
sys.exit(rc)
