# Journal de déploiement

Ce qui a réellement été fait le 11 août 2026, dans l'ordre, avec les décisions
et leurs justifications. Les commandes sont reproductibles.

## Point de départ

Les 3 serveurs étaient **déjà installés** en Proxmox VE 9.2.6 via le template
OVH `proxmox9`, avec la clé SSH injectée. Le plan initial prévoyait une
réinstallation pour maîtriser le partitionnement : **elle s'est révélée inutile**.

Vérification qui a permis de l'éviter :

```bash
sgdisk -p /dev/nvme0n1     # → "Total free space is 1548456590 sectors (738.4 GiB)"
```

Le template OVH laisse spontanément 738,4 Gio libres et contigus par disque, et
place déjà `/var/lib/vz` sur un miroir ZFS de 48,5 Go. Exactement la cible visée.

**Leçon** : toujours inspecter l'existant avant de planifier une réinstallation.

## Phase 1 — Préparation des nœuds

```bash
apt-get update && apt-get -y full-upgrade          # 9.2.6 → 9.2.10
apt-get -y install chrony gdisk parted ifupdown2
```

Le dépôt `pve-no-subscription` était **déjà configuré** par OVH et
`pve-enterprise.sources` entièrement commenté : rien à changer.

Chrony synchronise à la microseconde. Indispensable — Ceph et Corosync ne
tolèrent pas la dérive d'horloge (> 50 ms fait sortir les MON du quorum).

### Réseau vRack

La seconde NIC était `DOWN` mais physiquement raccordée (`ethtool` :
`Speed: 25000Mb/s`, `Link detected: yes`).

Configuration ajoutée dans `/etc/network/interfaces`, **sans toucher à `vmbr0`** —
c'est ce qui rend l'opération sûre à distance. Bloc délimité par des marqueurs
`# >>> VRACK` / `# <<< VRACK` pour être rejouable :

```
auto <nic>
iface <nic> inet manual
	mtu 9000

auto <nic>.100
iface <nic>.100 inet static
	address 10.100.0.<idx>/24
	mtu 1500

auto <nic>.200
iface <nic>.200 inet static
	address 10.200.0.<idx>/24
	mtu 9000

auto vmbr1
iface vmbr1 inet static
	address 10.30.0.<idx>/24
	bridge-ports <nic>.300
	bridge-stp off
	bridge-fd 0
	mtu 1500
```

**Méthode employée pour ne pas se verrouiller** — à réutiliser pour toute
modification réseau à distance :

1. Sauvegarde de `/etc/network/interfaces`
2. Validation syntaxique **à blanc** : `ifreload -a -n` (restauration si échec)
3. Minuterie de restauration automatique armée avant application :
   ```bash
   setsid nohup bash -c 'sleep 240; [ -f /tmp/net-ok ] || {
       cp /etc/network/interfaces.bak /etc/network/interfaces; ifreload -a; }' &
   ```
4. `ifreload -a`, puis test de connectivité depuis l'extérieur
5. `touch /tmp/net-ok` pour désarmer **seulement une fois le test concluant**

### Renommage des nœuds

`ns3245256` → `pve1`, etc. **Fait avant toute mise en cluster** : renommer un
nœud déjà membre est nettement plus délicat.

```bash
echo pve1 > /etc/hostname && hostnamectl set-hostname pve1
# /etc/hosts réécrit : noms courts → IP vRack VLAN 100
systemctl reboot
rm -rf /etc/pve/nodes/ns3245256          # répertoire orphelin, après reboot
```

## Phase 2 — Cluster

Prérequis : maillage SSH root entre les 3 nœuds (clés publiques croisées dans
`authorized_keys` + `known_hosts` pré-alimenté par `ssh-keyscan`).

```bash
# sur pve1
pvecm create tim-cluster --link0 10.100.0.11 --link1 91.134.84.222

# sur pve2 puis pve3, séquentiellement — jamais en parallèle
pvecm add 10.100.0.11 --link0 10.100.0.12 --link1 51.68.240.48  --use_ssh 1
pvecm add 10.100.0.11 --link0 10.100.0.13 --link1 51.68.240.191 --use_ssh 1
```

> **`--use_ssh 1` est indispensable.** Par défaut `pvecm add` s'authentifie sur
> l'API du nœud existant et réclame interactivement le mot de passe `root@pam`
> (« EOF while reading password » en non-interactif). `--use_ssh` bascule sur la
> jonction historique par SSH, qui accepte l'authentification par clé.

## Phase 3 — Ceph

```bash
yes | pveceph install --repository no-subscription      # sur les 3 nœuds
```

> Le `yes |` est nécessaire : `pveceph install` appelle `apt` sans `-y` et
> `DEBIAN_FRONTEND=noninteractive` ne suffit pas.

```bash
# sur pve1
pveceph init --network 10.200.0.0/24 --cluster-network 10.200.0.0/24
pveceph mon create                       # puis sur pve2 et pve3
pveceph mgr create                       # idem

# sur chaque nœud : partition puis OSD
sgdisk -n 7:0:0 -t 7:8300 -c 7:ceph-osd /dev/nvme0n1
sgdisk -n 7:0:0 -t 7:8300 -c 7:ceph-osd /dev/nvme1n1
partprobe /dev/nvme0n1 /dev/nvme1n1
pveceph osd create /dev/nvme0n1p7
pveceph osd create /dev/nvme1n1p7

# pool applicatif
pveceph pool create vm-storage --size 3 --min_size 2 \
    --application rbd --pg_autoscale_mode on --add_storages 1
```

`sgdisk -n 7:0:0` sélectionne automatiquement le plus grand bloc libre : il
remplit l'espace entre `p5` et `p6` sans toucher au marqueur OVH.

## Phase 4 — Haute disponibilité

`/etc/pve/datacenter.cfg` :

```
migration: secure,network=10.200.0.0/24
ha: shutdown_policy=migrate
```

Migration sur le VLAN 200 (25 Gb/s, jumbo). `shutdown_policy=migrate` fait
migrer à chaud les VM HA lors d'un arrêt planifié au lieu de les couper.

Watchdog : `softdog`, chargé par défaut. Aucun groupe HA créé — inutile sur
3 nœuds où toute VM peut tourner partout. En PVE 9 les groupes sont d'ailleurs
supplantés par `ha-manager rules` (affinités).

Tests de bascule : voir [05-tests-ha.md](05-tests-ha.md).

## Phase 5 — Durcissement

Détail complet dans [04-securite.md](04-securite.md). Résumé chronologique :

1. `sshd_config.d/10-hardening.conf` : mot de passe désactivé, root par clé seule
2. Postfix restreint en `loopback-only` + `smtp_address_preference = ipv4`
3. fail2ban : prisons `sshd` et `proxmox` (**un `reload` est requis après install**)
4. Firewall datacenter `policy_in: DROP`, activé avec minuterie de restauration
5. Notifications : `pveum user modify root@pam --email mcapon@teleimagerie.net`
6. Compte nominatif `matt@pve` + rôle `Administrator` sur `/`
7. TLS Let's Encrypt via DNS-01 OVH

### TLS

```bash
pvenode acme account register default mcapon@teleimagerie.net \
    --directory https://acme-v02.api.letsencrypt.org/directory     # accepter les CGU

pvenode acme plugin add dns ovh --api ovh --data <fichier> --validation-delay 120

# sur chaque nœud
pvenode config set --acme account=default
pvenode config set --acmedomain0 domain=pveN.infra.teleimagerie.net,plugin=ovh
pvenode acme cert order
```

Les enregistrements A `pve{1,2,3}.infra.teleimagerie.net` ont été créés via
l'API OVH. Le `--validation-delay 120` laisse le temps à la propagation du TXT.

Renouvellement automatique par `pve-daily-update.timer` (quotidien, ~03:03 UTC).

## Ce qui a été supprimé après validation

- VM de test `9000` (`ha-test`, Debian 13 cloud) et son disque RBD
- Image `debian13.qcow2` dans `/var/lib/vz/template/iso`
- Scripts temporaires, comptes jetables (`tfatest@pve`, `probe@pve`, `rtest@pve`)
- Service `corosync-restore.service` (filet de sécurité du test HA)
- Minuteries `fw-rollback`

## Extension à cinq nœuds — 15 septembre 2026

Les deux ex-dédiés de staging (`ns3240079` → **pve4**, `ns3240118` → **pve5**,
GRA3, [20-mytim-staging.md](20-mytim-staging.md)) ont été réinstallés depuis
l'espace client OVH avec le template `proxmox9_64` (nom d'hôte et clé SSH
posés à l'installation), partitionnement identique à celui de pve1-3 —
738,4 Gio libres par disque, marqueur `p6` sur `nvme0n1`. Ordre réellement
suivi, en une après-midi :

1. **Côté cluster, avant toute jonction** : IP publiques ajoutées à l'ipset
   `cluster` (minuterie `fw-rollback` armée puis désarmée), ACL du NAS-HA
   étendue (`ovh-nasha.py`), enregistrements A `pve4/pve5.infra` créés
   (`ovh-dns.py`), overrides Unbound `pveN.infra → 10.40.0.5/.6`
   ([scripts/unbound-overrides-pve.py](scripts/unbound-overrides-pve.py)),
   `/etc/hosts` des trois nœuds complété, clés root croisées.
2. **Côté nouveaux nœuds** : `full-upgrade` (9.2.18 → 9.2.20), `chrony gdisk
   parted ifupdown2`, `pveceph install`, `/etc/hosts` du dépôt, bloc `VRACK`
   de `/etc/network/interfaces` posé avec la méthode de la phase 1 (jumbo
   GRA3→GRA4 vérifié : `ping -M do -s 8972` passe, 0,15-0,3 ms), durcissement
   SSH/Postfix/fail2ban, tailnet en `userspace` (`100.72.0.8` pve4, `.9`
   pve5), redémarrage sur le noyau 7.0.14-17, chemin VPN `10.40.0.5/.6`
   vérifié **avant** la jonction (c'est lui qui reste quand `cluster.fw`
   ferme l'IP publique).
3. **Jonction** : `pvecm add 10.100.0.11 --link0 10.100.0.14 --link1
   79.137.100.184 --use_ssh 1`, puis pve5 ; 5 nœuds, 8 liens Corosync,
   5 stockages actifs, certificats Let's Encrypt émis dans la foulée.
4. **Ceph** : premier `pveceph mon create` **raté** — piège n° 43 (mon 20.2.4
   contre quorum 20.2.2, OOM des trois anciens mons, ~12 min sans quorum
   MON, aucune perte). Mise à niveau de pve1-3 (Ceph 20.2.4, PVE 9.2.20, sans
   redémarrage), rotation cephx (piège n° 44), puis MON/MGR sur pve4 et
   pve5 (quorum en 8 s), OSD 6-9, `size 4` — deux vagues de rééquilibrage
   (15 min puis 4 min, 90 à 580 Mio/s), `MAX AVAIL` final 1,5 Tio, occupation
   à ±5 % par hôte.
5. **Contrôles** : diagnostic express vert sur les cinq nœuds (5 / 8 liens /
   5 stockages, firewall, fail2ban, certificats), migration à chaud
   VM 103 → pve4 (12 s, coupure 121 ms) et VM 104 → pve5 (39 s, 20 ms) —
   les deux pré-productions **restent à GRA3** ; `make controle` sans écart,
   carte régénérée. Zabbix : aucun problème High ouvert, `HEALTH_WARN`
   volontaire (piège n° 44). Non fait : test KVM OVH des deux nœuds, SSO
   Keycloak (redirect URIs), redémarrage noyau de pve1-3 — [06 §13](06-reste-a-faire.md#13-extension-du-cluster-à-gra3-pve4pve5---faite-le-15092026-suites).
6. **Le soir même** : redémarrage de pve1, pve2, pve3 sur le noyau 7.0.14-17
   (maintenance HA un nœud à la fois, 33-75 s d'évacuation, 167-223 s de
   retour), puis fin de la migration cephx — clé admin en attente,
   consommateurs rafraîchis, confirmation et restriction à `aes256k`.
   KVM OVH de pve4/pve5 et redirect URIs Keycloak faits par l'admin dans la
   foulée. Non fait : porte tailnet de pve4/pve5 depuis un appareil admin, test HA GRA3.
