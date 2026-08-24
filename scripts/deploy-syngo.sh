#!/bin/bash
# Deploiement des certificats syngo.* vers le CT 201 (proxy-tim, 10.40.0.10).
# Appele par acme.sh (reloadcmd enregistre via --install-cert) apres chaque
# renouvellement. Les fichiers sont d'abord poses par acme.sh dans
# /opt/acme/deployed/<nom>/, puis copies ici vers le conteneur.
# La cible est l'IP du CT (VLAN 400), pas un noeud : insensible aux bascules HA.
set -euo pipefail

D=/opt/acme/deployed
CT=root@10.40.0.10
SSH_OPTS="-o ConnectTimeout=10 -o BatchMode=yes"

for name in syngo-teleimagerie syngo-isoteam; do
    # tolere une paire absente : au premier --install-cert, l'autre domaine
    # n'a pas encore ete pose dans deployed/
    [ -s "$D/$name/fullchain.pem" ] && [ -s "$D/$name/privkey.pem" ] || continue
    scp $SSH_OPTS "$D/$name/fullchain.pem" "$CT:/etc/nginx/certs/$name/fullchain.pem"
    scp $SSH_OPTS "$D/$name/privkey.pem"   "$CT:/etc/nginx/certs/$name/privkey.pem"
done

ssh $SSH_OPTS "$CT" 'nginx -t && systemctl reload nginx'
