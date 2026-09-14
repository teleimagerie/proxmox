#!/bin/bash
# Deploiement du certificat wildcard *.staging.teleimagerie.net vers le CT 201
# (proxy-tim). Appele par acme.sh (reloadcmd) apres chaque renouvellement —
# meme patron que deploy-zabbix.sh. Cible = IP du CT (VLAN 400), insensible
# aux bascules HA.
set -euo pipefail
D=/opt/acme/deployed/staging-teleimagerie
CT=root@10.40.0.10
SSH_OPTS="-o ConnectTimeout=10 -o BatchMode=yes"
[ -s "$D/fullchain.pem" ] && [ -s "$D/privkey.pem" ] || exit 0
ssh $SSH_OPTS "$CT" "mkdir -p /etc/nginx/certs/staging-teleimagerie"
scp $SSH_OPTS "$D/fullchain.pem" "$CT:/etc/nginx/certs/staging-teleimagerie/fullchain.pem"
scp $SSH_OPTS "$D/privkey.pem"   "$CT:/etc/nginx/certs/staging-teleimagerie/privkey.pem"
ssh $SSH_OPTS "$CT" 'nginx -t && systemctl reload nginx'
