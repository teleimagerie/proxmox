#!/bin/bash
# Compare les copies de configs/ aux fichiers reellement en production.
#
# LECTURE SEULE par defaut : le script ne modifie rien, ni ici ni sur le cluster.
# Il signale les ecarts, il ne les corrige pas -- une divergence n'est pas
# forcement une derive : le depot peut porter volontairement un etat non
# applique (sshd-10-hardening-ct.conf en est un exemple).
#
#   scripts/check-drift.sh              compare et affiche
#   scripts/check-drift.sh --diff       affiche aussi le detail des ecarts
#   scripts/check-drift.sh --update     recopie les fichiers divergents dans
#                                       configs/ pour relecture (git diff avant
#                                       de commiter -- jamais de commit auto)
#
# Sortie : 0 si tout concorde, 1 s'il existe au moins un ecart, 2 en cas
# d'erreur d'acces. Utilisable dans une verification avant commit.
#
# LISTE BLANCHE EXPLICITE, jamais de glob : /etc/pve/priv/ contient la CA du
# cluster, les keyrings Ceph et authkey.key. Une synchro en masse les
# aspirerait dans l'historique git, de facon irreversible. Chaque fichier est
# donc nomme un par un, avec sa source.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PVE1=root@pve1.infra.teleimagerie.net
SSHOPT=(-o BatchMode=yes -o ConnectTimeout=10)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

MODE=compare
case "${1:-}" in
    --diff)   MODE=diff ;;
    --update) MODE=update ;;
    "")       ;;
    *) echo "usage: $0 [--diff|--update]" >&2; exit 2 ;;
esac

# copie_locale <source>
# Fichiers repliques par pmxcfs ou locaux a pve1 : lisibles depuis pve1.
copie_locale() { ssh "${SSHOPT[@]}" "$PVE1" "cat '$1'" 2>/dev/null; }

# copie_noeud <noeud> <source>
# Fichiers LOCAUX a chaque noeud (/etc/network/interfaces) : pve1 ne voit pas
# ceux de pve2 et pve3, il faut rebondir.
copie_noeud() {
    ssh "${SSHOPT[@]}" "$PVE1" "ssh -o BatchMode=yes -o ConnectTimeout=10 $1 \"cat '$2'\"" 2>/dev/null
}

# copie_ct <ctid> <source>
# Fichiers vivant dans un conteneur. Le CT est une ressource HA : on demande
# a ha-manager sur quel noeud il tourne, on ne presume pas.
copie_ct() {
    # heredoc non quote cote local (pour interpoler $1 et $2), mais le script
    # distant est ecrit en une seule passe : pas de quoting a trois niveaux.
    ssh "${SSHOPT[@]}" "$PVE1" bash 2>/dev/null <<EOF
export LC_ALL=C
n=\$(ha-manager status | awk '/ct:$1 / {gsub(/[(),]/,""); print \$3}')
[ -n "\$n" ] || exit 1
ssh -o BatchMode=yes -o ConnectTimeout=10 "\$n" "pct exec $1 -- cat '$2'"
EOF
}

ecarts=0
absents=0
total=0

# verifie <fichier-configs> <description-source> <commande...>
verifie() {
    local nom="$1" source="$2"; shift 2
    local local_f="$REPO/configs/$nom" dist_f="$TMP/$nom"
    total=$((total + 1))

    if [ ! -f "$local_f" ]; then
        printf '  %-28s %s\n' "$nom" "ABSENT DU DEPOT"
        absents=$((absents + 1)); return
    fi

    "$@" > "$dist_f" 2>/dev/null
    if [ ! -s "$dist_f" ]; then
        printf '  %-28s %s\n' "$nom" "INJOIGNABLE ($source)"
        absents=$((absents + 1)); return
    fi

    # on ignore les lignes d'en-tete de provenance ajoutees dans le depot
    # (# source : ... / # releve le ...), absentes du fichier en production
    if diff -q <(grep -vE '^(#|//) (source|releve le|NOTE) ' "$local_f") "$dist_f" >/dev/null 2>&1; then
        printf '  %-28s %s\n' "$nom" "identique"
    else
        printf '  %-28s %s\n' "$nom" "DIFFERENT  <- $source"
        ecarts=$((ecarts + 1))
        if [ "$MODE" = diff ]; then
            diff -u <(grep -vE '^(#|//) (source|releve le|NOTE) ' "$local_f") "$dist_f" \
                | sed 's/^/      /' | head -40
        elif [ "$MODE" = update ]; then
            # on preserve l'en-tete de provenance du depot
            { grep -E '^(#|//) (source|releve le|NOTE) ' "$local_f"; cat "$dist_f"; } > "$local_f.new" \
                && mv "$local_f.new" "$local_f"
            echo "      -> configs/$nom mis a jour, relire avec git diff"
        fi
    fi
}

echo "=== /etc/pve : replique par pmxcfs, lu depuis pve1 ==="
verifie ceph.conf            "pve1:/etc/pve/ceph.conf"            copie_locale /etc/pve/ceph.conf
verifie corosync.conf        "pve1:/etc/pve/corosync.conf"        copie_locale /etc/pve/corosync.conf
verifie storage.cfg          "pve1:/etc/pve/storage.cfg"          copie_locale /etc/pve/storage.cfg
verifie jobs.cfg             "pve1:/etc/pve/jobs.cfg"             copie_locale /etc/pve/jobs.cfg
verifie datacenter.cfg       "pve1:/etc/pve/datacenter.cfg"       copie_locale /etc/pve/datacenter.cfg
verifie ha-resources.cfg     "pve1:/etc/pve/ha/resources.cfg"     copie_locale /etc/pve/ha/resources.cfg
verifie cluster.fw           "pve1:/etc/pve/firewall/cluster.fw"  copie_locale /etc/pve/firewall/cluster.fw
verifie firewall-102-pbs.fw  "pve1:/etc/pve/firewall/102.fw"      copie_locale /etc/pve/firewall/102.fw

echo "=== local a pve1 ==="
verifie hosts                     "pve1:/etc/hosts"    copie_locale /etc/hosts
verifie sshd-10-hardening.conf    "pve1:/etc/ssh/sshd_config.d/10-hardening.conf" \
                                  copie_locale /etc/ssh/sshd_config.d/10-hardening.conf
verifie fail2ban-proxmox.local    "pve1:/etc/fail2ban/jail.d/proxmox.local" \
                                  copie_locale /etc/fail2ban/jail.d/proxmox.local

echo "=== local a chaque noeud (rebond depuis pve1) ==="
verifie interfaces-pve1 "pve1:/etc/network/interfaces" copie_locale /etc/network/interfaces
verifie interfaces-pve2 "pve2:/etc/network/interfaces" copie_noeud pve2 /etc/network/interfaces
verifie interfaces-pve3 "pve3:/etc/network/interfaces" copie_noeud pve3 /etc/network/interfaces

echo "=== dans le CT 202 (headscale, ressource HA) ==="
verifie headscale-config.yaml "CT202:/etc/headscale/config.yaml" copie_ct 202 /etc/headscale/config.yaml
verifie headscale-acl.hujson  "CT202:/etc/headscale/acl.hujson"  copie_ct 202 /etc/headscale/acl.hujson

echo
# sshd-10-hardening-ct.conf n'est volontairement PAS verifie : il decrit un
# etat non applique (voir 04-securite.md, "Durcir le SSH des conteneurs").
echo "Non compare : sshd-10-hardening-ct.conf (etat non applique, volontaire)."

if [ "$absents" -gt 0 ]; then
    echo "$ecarts ecart(s) et $absents fichier(s) injoignable(s) sur $total."
    exit 2
elif [ "$ecarts" -gt 0 ]; then
    echo "$ecarts ecart(s) sur $total. Relancer avec --diff pour le detail."
    exit 1
else
    echo "Aucun ecart : les $total fichiers de configs/ sont conformes."
    exit 0
fi
