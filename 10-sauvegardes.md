# Sauvegardes et NAS-HA

Mis en place le **13 août 2026**. Jusqu'à cette date le cluster n'avait
**aucune sauvegarde** — c'était son principal risque résiduel, Ceph ne protégeant
que de la panne matérielle.

---

## Le NAS-HA

| | |
|---|---|
| Service | `zpool-130899` |
| Adresse | **`10.201.13.43`** |
| Capacité | 3000 Gio, disques **SSD** |
| Datacenter | **`rbx` (Roubaix)** — le cluster est à **GRA4 (Gravelines)** |
| Protocole | NFS (v4.2 côté client) |
| Option souscrite | snapshots distants vers un second datacenter |

**Le NAS est dans un autre datacenter que le cluster.** Ce n'est pas un choix —
la localisation d'un NAS-HA ne se sélectionne pas — et c'est une bonne nouvelle :
un incident Gravelines n'emporte pas les sauvegardes.

> ⚠️ **Le NAS-HA ne peut pas rejoindre le vRack.** C'est une limitation OVH
> assumée et documentée. Il se joint par le **chemin IP publique** : la route
> passe par `vmbr0` et la passerelle `100.64.0.1`, en MTU 1500 — pas de jumbo
> frames, pas de VLAN 300. L'ACL du NAS attend donc les **IP publiques** des
> nœuds. Voir [07-pieges.md](07-pieges.md#24-le-nas-ha-nest-pas-raccordable-au-vrack).

### Partitions

| Partition | Taille | Export NFS | Usage |
|---|---|---|---|
| `pbs` | 1800 Gio | `10.201.13.43:/zpool-130899/pbs` | disque du datastore PBS |
| `vmstore` | 700 Gio | `10.201.13.43:/zpool-130899/vmstore` | disques VM, ISO, templates, config OPNsense |
| — | 500 Gio | — | laissé libre pour les snapshots ZFS OVH |

ACL sur les deux partitions, en `readwrite` : `91.134.84.222` (pve1),
`51.68.240.48` (pve2), `51.68.240.191` (pve3).

Snapshots ZFS armés côté OVH — **en lecture seule et hors de portée du cluster,
donc opposables à un ransomware** :

```
pbs      hour-1, day-1, day-3, day-7
vmstore  hour-1, day-1, day-7
```

`hour-1` est ajouté d'office par OVH à la création de la partition.

### Piloter le NAS

[`scripts/ovh-nasha.py`](scripts/ovh-nasha.py) crée les partitions, l'ACL et les
snapshots. Idempotent : il ne fait que ce qui manque, on peut le relancer pour
afficher l'état.

```bash
ssh root@pve1.infra.teleimagerie.net 'python3 /root/ovh-nasha.py'
```

Il lit ses identifiants dans `/root/.secrets/ovh-nasha.ini` sur pve1
(application OVH `Proxmox Nas-HA`, distincte de celle qui porte l'ACME).

### Débit mesuré

Depuis pve1, en écriture directe sur `vmstore`, **chiffres réels** :

```
écriture séquentielle 4 Gio    171 Mo/s
lecture  séquentielle 4 Gio    477 Mo/s
latence aller-retour           1,68 ms
```

> La bande passante du NAS-HA n'est **pas garantie** par OVH — elle est mutualisée.
> Ces chiffres sont un ordre de grandeur, pas un contrat.

---

## Stockages Proxmox

```
nfs: nas-pbs       1800 Gio   content images          format raw    → disque du datastore
nfs: nas-vm         700 Gio   content images,rootdir,iso,vztmpl,backup  format qcow2
pbs: pbs            ~1000 Gio  content backup          → datastore PBS "tim"
```

Options de montage communes :
`vers=4.2,hard,timeo=600,rsize=1048576,wsize=1048576,noatime`

- **NFSv4.2 imposé.** La v3 réclame `rpcbind`/`statd` et des rappels du serveur
  vers le client, que le `policy_in: DROP` du firewall bloquerait. La v4.0 garde
  un canal de rappel ; la v4.1 et au-delà, non. Aucune règle de firewall n'a été
  ajoutée : le trafic est sortant et le filtrage Proxmox est à état.
- `rsize`/`wsize` sont négociés à **131072** par le serveur, quelle que soit la
  valeur demandée. Sans conséquence.
- `nas-vm` est en **qcow2** pour conserver les instantanés de VM ; `nas-pbs` est
  en **raw**, sans préallocation.

`nas-vm` répond au besoin de capacité VM supplémentaire **et** rend les ISO et
templates communs aux trois nœuds — ce que `local` (48 Gio par nœud) ne permettait
pas.

> `nas-vm` convient aux ISO, templates, disques de données et VM froides.
> **Pas à une base de données ni à un PACS** : 1,68 ms de latence et une bande
> passante mutualisée face au NVMe local de Ceph à 25 Gb/s. Ceph reste le
> stockage de production.

---

## Architecture de sauvegarde

```
VM/CT du cluster ──vzdump──> PBS (VM 102) ──> /mnt/datastore/tim
                                              = ext4 sur /dev/sdb
                                              = disque raw 1000 Gio
                                              sur nas-pbs (NFS)
                                              → NAS-HA Roubaix
```

**Le datastore vit dans un disque virtuel, pas sur un montage NFS direct.**
C'est le choix structurant :

- le chunk store de PBS crée des **millions de fichiers de 1 à 4 Mo** ; à 1,68 ms
  de latence, chacun coûterait un aller-retour NFS et le ramasse-miettes comme la
  vérification deviendraient interminables ;
- avec un disque raw, l'hôte Proxmox fait le NFS et PBS travaille sur un bloc
  local en ext4 ;
- **la VM PBS n'a donc pas besoin de figurer dans l'ACL du NAS**, ce qui évite d'y
  déclarer l'IP de sortie NAT d'OPNsense.

### La VM PBS

| | |
|---|---|
| VMID / nom | **102** / `pbs` |
| Version | Proxmox Backup Server **4.2.5**, Debian 13 Trixie |
| CPU / RAM | 4 vCPU / 8 Gio |
| `scsi0` | 32 Gio sur `vm-storage` (Ceph) — système |
| `scsi1` | 1000 Gio raw sur `nas-pbs`, **`backup=0`** — datastore |
| `net0` | VLAN **300**, `10.30.0.20/24` — flux de sauvegarde et administration |
| `net1` | VLAN **400**, `10.40.0.20/24`, passerelle `10.40.0.1` — mises à jour APT |
| HA | `ha-manager add vm:102` — les deux disques sont sur du stockage partagé |
| Firewall | `/etc/pve/firewall/102.fw`, `policy_in: DROP`, entrée limitée à l'ipset `cluster` |

> **`backup=0` sur `scsi1` est impératif.** Sans lui, vzdump tenterait de
> sauvegarder le datastore lui-même dans le datastore. Attention : cela exclut le
> **disque**, pas la **VM** — la 102 est en outre retirée du job quotidien, voir
> [pourquoi](#pourquoi-la-vm-102-est-exclue-de-la-tâche-quotidienne).

**Deux cartes réseau, et pourquoi** : seul pve1 porte une adresse sur le VLAN 400
(`10.40.0.2`, héritée du chantier proxy). Le VLAN 300 est le seul présent sur les
trois nœuds : c'est donc par lui que PBS doit être joignable, où qu'il tourne. Mais
le VLAN 300 n'a pas de routeur — d'où la seconde carte sur le VLAN 400 pour la
seule sortie Internet.

### Accès à l'interface PBS

Le VLAN 300 n'est routé nulle part : l'interface web passe par un tunnel SSH.

```bash
ssh -L 8007:10.30.0.20:8007 root@pve1.infra.teleimagerie.net
# puis https://localhost:8007  —  compte root@pam de la VM PBS
```

**Depuis le VPN nomades** (`wg0`, qui route `10.40.0.0/24`), la patte VLAN 400
de la VM répond directement, sans tunnel : `https://10.40.0.20:8007`.
Depuis le 27/08/2026, la connexion peut aussi se faire en OIDC (realm
`keycloak` dans la liste déroulante) — les deux URL sont déclarées comme URI
de redirection, [16-keycloak.md](16-keycloak.md#ce-qui-est-raccordé).

Le certificat de PBS est **auto-signé** : l'avertissement du navigateur est ici
normal, contrairement au cluster qui porte un Let's Encrypt valide.

### Compte de service

```
utilisateur   backup@pbs
jeton         backup@pbs!pve
rôle          DatastorePowerUser sur /datastore/tim
empreinte     15:22:32:be:ff:14:31:4d:f7:d5:46:42:d6:17:25:40:
              e1:dd:54:0a:3c:15:03:82:db:4d:82:8e:5b:44:e2:1a
```

> Le rôle est accordé **à l'utilisateur *et* au jeton**. Les droits effectifs d'un
> jeton PBS sont l'**intersection** des siens et de ceux de son compte : accorder
> le rôle au seul jeton ne donne rien.
> Voir [07-pieges.md](07-pieges.md#26-les-droits-dun-jeton-pbs-sont-une-intersection).

Le secret du jeton vit dans `/etc/pve/priv/storage/pbs.pw` (répliqué par pmxcfs).

---

## Planification

| Quand | Quoi | Où |
|---|---|---|
| tous les jours **02:00** | vzdump de toutes les VM/CT **sauf la 102**, mode snapshot | → `pbs` |
| tous les jours **03:00** | prune : `keep-daily=7 keep-weekly=4 keep-monthly=6` | PBS |
| samedi **03:30** | vzdump de la VM 102 seule (hors datastore), `keep-last=4` | → `nas-vm` |
| dimanche **04:00** | vérification des sauvegardes non vérifiées de plus de 30 j | PBS |
| samedi **04:30** | copie de `/conf/config.xml` d'OPNsense | → `nas-vm` |
| dimanche **05:30** | ramasse-miettes du datastore | PBS |

Les tâches de sauvegarde sont dans `/etc/pve/jobs.cfg` (répliqué), celles de PBS
dans la VM 102. Les échecs sont notifiés par mail à `mcapon@teleimagerie.net`.

**Rétention : environ 8 mois de profondeur.** 7 quotidiennes, 4 hebdomadaires,
6 mensuelles.

### Pourquoi la VM 102 est exclue de la tâche quotidienne

Le job quotidien porte `exclude 102`. Ce n'est pas un oubli : **PBS ne peut pas se
sauvegarder dans son propre datastore.**

Constaté à la première exécution, le 14/08/2026 à 02:00. En mode `snapshot`,
vzdump gèle l'invité (`guest-fsfreeze`) *avant* d'ouvrir la connexion vers PBS —
lequel tourne dans la VM qu'on vient de geler. La connexion n'aboutit jamais et
échoue au bout de deux minutes :

```
ERROR: Backup of VM 102 failed - backup connect failed:
       command error: http upgrade request timed out
```

Pendant ces deux minutes, PBS était gelé pour tout le monde : la sauvegarde de la
CT 201 lancée depuis pve1 a pris **2 min 05 au lieu de 6 s**. Analyse complète
dans [07-pieges.md](07-pieges.md#28-pbs-ne-peut-pas-se-sauvegarder-dans-son-propre-datastore).

**Corrigé le 14/08/2026 à 22:07** : la 102 est exclue du job quotidien, et
couverte par le job hebdomadaire vers `nas-vm` — un stockage NFS géré par l'hôte,
donc insensible au gel de l'invité. Vérifié dans la foulée : sauvegarde de la 102
en **8 s** (648 Mo d'archive, disque creux à 94 %), et la tâche quotidienne
simulée sur pve2 se termine proprement (`skip external VMs: 100, 201`).

> **Conséquence à connaître pour la restauration** : la VM PBS ne se restaure pas
> depuis PBS. Elle se restaure depuis `nas-vm` :
> ```bash
> qmrestore /mnt/pve/nas-vm/dump/vzdump-qemu-102-<date>.vma.zst 102 --storage vm-storage
> ```
> Le datastore, lui, survit à la perte de la VM : il vit sur `nas-pbs`. Après
> restauration, rattacher le disque `scsi1` existant plutôt qu'en créer un neuf.

### Sauvegarde de la configuration OPNsense

`/usr/local/sbin/backup-opnsense.sh` sur **pve1** (seul nœud à joindre
`10.40.0.1`), déclenché par `backup-opnsense.timer`. Il dépose une copie datée
dans `/mnt/pve/nas-vm/opnsense-config/` et garde les 12 dernières.

> Ce fichier contient les **clés privées WireGuard**. Répertoire en `700`,
> fichiers en `600`. À traiter comme un secret.

La VM 100 est de toute façon sauvegardée entièrement dans PBS ; cette copie sert
à reconstruire un OPNsense neuf sans restaurer toute la VM.

---

## Chiffres mesurés

Relevés les 13 et 14/08/2026, **mesurés et non estimés**.

| Opération | Volume | Durée |
|---|---|---|
| 1ʳᵉ sauvegarde VM 100 (OPNsense) | 32 Gio, 89 % de zéros | **14 s** |
| 1ʳᵉ sauvegarde CT 201 (proxy-tim) | 686 Mio | **6,4 s** |
| Sauvegarde incrémentale CT 201 | 1,2 Mio réels, **99,8 % réutilisés** | **5,4 s** |
| Sauvegarde VM 102 → `nas-vm` (zstd) | 32 Gio, 94 % de zéros → 648 Mo | **8 s** |
| Restauration CT 201 → 299 sur `nas-vm` | 686 Mio à 163 Mio/s | **9,2 s** |
| Démarrage du conteneur restauré | | **1,0 s** |
| Vérification complète du datastore | 2 groupes | **0 erreur** |

La déduplication fonctionne : une sauvegarde quotidienne coûte le delta, pas le
volume total. En production, la tâche du 14/08 à 02:00 a traité la VM 100 en
**1 seconde** — rien n'avait changé.

---

## Procédures

### Sauvegarder maintenant

```bash
vzdump 100 201 --storage pbs --mode snapshot              # ciblé
vzdump --all --exclude 102 --storage pbs --mode snapshot  # tout le cluster
vzdump 102 --storage nas-vm --mode snapshot --compress zstd   # la VM PBS
```

> Ne jamais lancer `vzdump --all` vers `pbs` **sans** `--exclude 102` : la
> commande gèle PBS deux minutes et fait échouer les autres sauvegardes en cours.

### Lister ce qui existe

```bash
pvesm list pbs                      # sauvegardes déduppliquées
pvesm list nas-vm                   # archives vzdump de la VM PBS
ssh root@10.30.0.20 'proxmox-backup-manager task list'
```

### Restaurer

```bash
# conteneur, sous un NOUVEL identifiant, pour ne rien écraser
pct restore 299 pbs:backup/ct/201/<horodatage> --storage nas-vm

# machine virtuelle
qmrestore pbs:backup/vm/100/<horodatage> 299 --storage vm-storage
```

> **Toujours restaurer sous un identifiant libre**, jamais par-dessus la machine
> en production. Et retirer la carte réseau (`pct set 299 --delete net0`) avant de
> démarrer : deux machines avec la même IP se marchent dessus.

Restauration d'un fichier isolé : interface PBS → *Content* → icône dossier, ou
`proxmox-backup-client` monté en `catalog`.

### Rejouer le test de restauration

À refaire après toute évolution majeure. Une sauvegarde jamais restaurée n'est
pas une sauvegarde.

```bash
pct restore 299 pbs:backup/ct/201/<horodatage> --storage nas-vm
pct set 299 --delete net0
pct start 299
pct exec 299 -- nginx -t          # attendu : syntax is ok / test is successful
pct stop 299 && pct destroy 299
```

### Vérifier l'intégrité

```bash
ssh root@10.30.0.20 'proxmox-backup-manager verify tim'
ssh root@10.30.0.20 'proxmox-backup-manager garbage-collection status tim'
```

---

## Diagnostic

```bash
pvesm status                                  # nas-pbs, nas-vm, pbs : active ?
mount | grep 10.201                           # montages NFS présents ?
ping -c3 10.201.13.43                         # ~1,7 ms attendu
ssh root@10.30.0.20 'df -h /mnt/datastore/tim'
python3 /root/ovh-nasha.py                    # état côté OVH (ACL, snapshots, occupation)
```

### Un stockage NFS passe `inactive`

Après un `pvesm add`, `pvestatd` met une dizaine de secondes à voir le montage :
un `inactive` immédiat n'est pas une panne. Attendre, puis relancer `pvesm status`.

### Le NAS est injoignable

Les montages sont en **`hard`** — choix délibéré, l'intégrité prime sur la
disponibilité. Conséquence : les accès au partage **attendent** au lieu d'échouer,
et `pvestatd` peut sembler figé.

1. `ping 10.201.13.43` — si ça répond, c'est NFS ou l'ACL, pas le réseau
2. Vérifier l'ACL : `python3 /root/ovh-nasha.py` (une IP publique modifiée côté
   OVH suffit à tout couper)
3. Les VM sur Ceph ne sont pas concernées : seules les sauvegardes s'arrêtent
4. Ne pas remonter en `soft` pour « débloquer » — c'est ainsi qu'on corrompt un
   datastore

### Le datastore se remplit

```bash
ssh root@10.30.0.20 'df -h /mnt/datastore/tim'   # occupation ext4
python3 /root/ovh-nasha.py                        # occupation NAS + snapshots
```

Deux plafonds distincts, à ne pas confondre :

- **1000 Gio** — la taille du disque virtuel, vue par PBS ;
- **1800 Gio** — la partition NAS, qui porte *aussi* les snapshots ZFS d'OVH.
  Un fichier supprimé continue d'occuper de la place tant qu'un snapshot le
  retient.

Agrandir le disque du datastore (dans la limite de la partition) :

```bash
qm resize 102 scsi1 +200G
ssh root@10.30.0.20 'resize2fs /dev/sdb'
```

---

## Ce qui n'est pas couvert

- **Le chiffrement client PBS n'est pas activé.** Les données sont au repos chez
  OVH dans le périmètre HDS, et une clé perdue rend *toutes* les sauvegardes
  irrécupérables. À réévaluer, avec séquestre de la clé hors du cluster.
- **Une seule copie.** Les snapshots ZFS d'OVH et l'option de réplication distante
  atténuent, mais il n'existe pas de second datastore PBS ailleurs.
- **`backup-opnsense.timer` ne tourne que sur pve1.** Si pve1 est durablement
  hors service, cette copie hebdomadaire s'arrête sans bruit. Le script sait en
  revanche rebondir par la VM PBS si pve1 perd son adresse sur le VLAN 400.
- **La VM PBS n'est sauvegardée qu'une fois par semaine**, vers `nas-vm`. C'est
  assumé — son système est reconstructible et le datastore vit ailleurs — mais
  une modification de configuration PBS faite un lundi n'est protégée que le
  samedi suivant.
