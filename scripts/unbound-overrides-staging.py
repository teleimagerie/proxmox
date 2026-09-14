# Ajoute les overrides Unbound split-horizon des pre-productions (VM 103/104)
# vers proxy-tim (10.40.0.10). Idempotent. A executer SUR OPNsense.
import re, shutil, subprocess, uuid
CONF = "/conf/config.xml"
NAMES = [("app","teleimagerie.net"),("gestion","teleimagerie.net"),("mailer","teleimagerie.net"),
         ("app","isoteam.mn"),("gestion","isoteam.mn"),("mailer","isoteam.mn")]
s = open(CONF).read()
assert s.count("<hosts>") == 1, "bloc <hosts> unique attendu"
shutil.copy2(CONF, CONF + ".bak-staging-20260914")
added = []
for host, dom in NAMES:
    hn = f"{host}.staging"
    if re.search(rf"<hostname>{re.escape(hn)}</hostname>\s*<domain>{re.escape(dom)}</domain>", s):
        continue
    block = f"""        <host uuid="{uuid.uuid4()}">
          <enabled>1</enabled>
          <hostname>{hn}</hostname>
          <domain>{dom}</domain>
          <rr>A</rr>
          <mxprio/>
          <mx/>
          <server>10.40.0.10</server>
          <description>Pre-production MyTIM/MyISOTEAM (VM 103/104) via proxy-tim - split-horizon interne, 14/09/2026</description>
        </host>
"""
    s = s.replace("<hosts>\n", "<hosts>\n" + block, 1)
    added.append(f"{hn}.{dom}")
open(CONF, "w").write(s)
print("ajoutes :", added or "aucun (deja presents)")
subprocess.run(["configctl", "unbound", "restart"], check=True)
subprocess.run(["configctl", "filter", "reload"], check=True)
he = open("/var/unbound/host_entries.conf").read()
for host, dom in NAMES:
    n = f"{host}.staging.{dom}"
    print(n, "OK" if f'"{n}  IN A 10.40.0.10"' in he else "ABSENT de host_entries.conf !")
