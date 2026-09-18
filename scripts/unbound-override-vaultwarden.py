# Ajoute l'override Unbound split-horizon de vault.teleimagerie.net (VM 105)
# vers proxy-tim (10.40.0.10). Idempotent. A executer SUR OPNsense.
# Sans lui, les machines du VLAN 400 et du VPN joignant la VIP 57.130.34.122
# tombent sur la GUI d'OPNsense (piege n° 32).
import re, shutil, subprocess, uuid
CONF = "/conf/config.xml"
NAMES = [("vault", "teleimagerie.net")]
s = open(CONF).read()
assert s.count("<hosts>") == 1, "bloc <hosts> unique attendu"
shutil.copy2(CONF, CONF + ".bak-vaultwarden-20260918")
added = []
for host, dom in NAMES:
    if re.search(rf"<hostname>{re.escape(host)}</hostname>\s*<domain>{re.escape(dom)}</domain>", s):
        continue
    block = f"""        <host uuid="{uuid.uuid4()}">
          <enabled>1</enabled>
          <hostname>{host}</hostname>
          <domain>{dom}</domain>
          <rr>A</rr>
          <mxprio/>
          <mx/>
          <server>10.40.0.10</server>
          <description>Vaultwarden (VM 105) via proxy-tim - split-horizon interne, fiche 21</description>
        </host>
"""
    s = s.replace("<hosts>\n", "<hosts>\n" + block, 1)
    added.append(f"{host}.{dom}")
open(CONF, "w").write(s)
print("ajoutes :", added or "aucun (deja presents)")
subprocess.run(["configctl", "unbound", "restart"], check=True)
subprocess.run(["configctl", "filter", "reload"], check=True)
he = open("/var/unbound/host_entries.conf").read()
for host, dom in NAMES:
    n = f"{host}.{dom}"
    print(n, "OK" if f'"{n}  IN A 10.40.0.10"' in he else "ABSENT de host_entries.conf !")
