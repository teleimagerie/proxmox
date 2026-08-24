#!/bin/bash
# Copie hebdomadaire de /conf/config.xml d'OPNsense (VM 100) vers le NAS.
# Le fichier contient les cles privees WireGuard : mode 600, repertoire 700.
#
# Deux chemins d'acces, essayes dans l'ordre :
#   1. direct, si pve1 porte encore son adresse 10.40.0.2 sur le VLAN 400
#      (adresse NON persistante : elle disparait au redemarrage de pve1)
#   2. rebond par la VM PBS (10.30.0.20), qui est sur le VLAN 400 en permanence
# Dans les deux cas l'authentification finale se fait avec la cle de root@pve1,
# qui est la seule inscrite dans le config.xml d'OPNsense.
set -euo pipefail

DEST=/mnt/pve/nas-vm/opnsense-config
FICHIER="$DEST/config-$(date +%F).xml"
SSHOPT=(-q -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=15)

install -d -m 700 "$DEST"
umask 077

if ! scp "${SSHOPT[@]}" root@10.40.0.1:/conf/config.xml "$FICHIER" 2>/dev/null; then
    logger -t backup-opnsense "acces direct indisponible, rebond par la VM PBS"
    scp "${SSHOPT[@]}" -o ProxyJump=root@10.30.0.20 \
        root@10.40.0.1:/conf/config.xml "$FICHIER"
fi

# garde-fou : un config.xml valide fait plus de 10 Ko et commence par <?xml
[ "$(stat -c%s "$FICHIER")" -gt 10240 ] || { rm -f "$FICHIER"; echo "config.xml suspect" >&2; exit 1; }
head -c 5 "$FICHIER" | grep -q "<?xml" || { rm -f "$FICHIER"; echo "config.xml illisible" >&2; exit 1; }

# rotation : on garde les 12 copies les plus recentes
ls -1t "$DEST"/config-*.xml | tail -n +13 | xargs -r rm -f
logger -t backup-opnsense "sauvegarde OK : $FICHIER"
