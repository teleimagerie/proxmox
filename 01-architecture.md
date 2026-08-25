# Architecture

## Matériel

Trois serveurs dédiés OVHcloud **identiques**, tous au datacenter **GRA4**
(co-localisation indispensable à la latence Ceph).

| | |
|---|---|
| CPU | AMD EPYC 4344P — 8c/16t, 3,8 / 5,3 GHz, **1 socket** |
| RAM | 64 Go DDR5 5200 |
| Disques | 2 × 960 Go NVMe (894,3 Gio utiles), soft RAID — pas de carte RAID |
| Réseau | 1 NIC publique + 1 NIC vRack **25 Gb/s** (DAC) |

Modèles NVMe observés : Micron `MTFDKCC960TGP` (pve1, pve2) et
`Micron_7450_MTFDKCC960TFR` (pve3). Sans incidence, mais explique la différence
de nommage des interfaces réseau.

## Inventaire des nœuds — table de correspondance

**Le tableau de référence.** Trois nommages coexistent : celui d'OVH (`ns…`,
utilisé dans l'espace client et les tickets), le nôtre (`pve1/2/3`, utilisé par
le cluster) et le FQDN public (`*.infra.teleimagerie.net`, utilisé par les
certificats et l'interface web).

| | **pve1** | **pve2** | **pve3** |
|---|---|---|---|
| **Nom OVH** | `ns3245256.ip-91-134-84.eu` | `ns3245278.ip-51-68-240.eu` | `ns3258339.ip-51-68-240.eu` |
| **FQDN public** | `pve1.infra.teleimagerie.net` | `pve2.infra.teleimagerie.net` | `pve3.infra.teleimagerie.net` |
| **IP publique** | `91.134.84.222/32` | `51.68.240.48/32` | `51.68.240.191/32` |
| vRack 100 — Corosync | `10.100.0.11/24` | `10.100.0.12/24` | `10.100.0.13/24` |
| vRack 200 — Ceph | `10.200.0.11/24` | `10.200.0.12/24` | `10.200.0.13/24` |
| vRack 300 — VM (`vmbr1`) | `10.30.0.11/24` | `10.30.0.12/24` | `10.30.0.13/24` |
| NIC publique (`vmbr0`) | `enp8s0f0np0` | `enp8s0f0np0` | **`enp2s0f0np0`** |
| NIC vRack | `enp8s0f1np1` | `enp8s0f1np1` | **`enp2s0f1np1`** |
| OSD Ceph | `osd.0`, `osd.1` | `osd.2`, `osd.3` | `osd.4`, `osd.5` |
| ID Corosync | 1 | 2 | 3 |

Passerelle publique commune : **`100.64.0.1`** sur les trois nœuds.

### Repères pour ne pas se tromper de machine

- **Le dernier octet vRack donne le numéro du nœud** : `.11` = pve1, `.12` = pve2,
  `.13` = pve3. Vrai sur les trois VLAN.
- **pve1 est le seul en `91.134.84.x`.** pve2 et pve3 sont tous deux en
  `51.68.240.x` et ne se distinguent que par le dernier octet (`.48` contre
  `.191`) — c'est là que se produisent les confusions.
- Les noms OVH `ns3245256` et `ns3245278` ne diffèrent que par leurs deux
  derniers chiffres. **Vérifier avant toute action destructive** :
  ```bash
  ssh root@<hôte> hostname
  ```

### Deux pièges de configuration

> **pve3 ne nomme pas ses interfaces comme les deux autres** (`enp2s0…` contre
> `enp8s0…`), à cause d'un modèle de NVMe et d'une carte mère différents. Tout
> script touchant au réseau doit **détecter** le nom, jamais le supposer.

> Les IP publiques sont en **`/32`** avec une passerelle hors sous-réseau
> (`100.64.0.1`). C'est la configuration OVH standard : ne pas « corriger » en
> croyant à une erreur de masque, cela couperait le nœud.

## Réseau

vRack **`pn-1165892`**, 25 Gb/s. Depuis le 11/08/2026, la carte vRack porte un
**bridge VLAN-aware unique** (`vmbr1`) avec filtrage VLAN par port.

| Lien | VLAN | Sous-réseau | MTU | Usage |
|---|---|---|---|---|
| `vmbr1.100` | 100 | `10.100.0.0/24` | 1500 | Corosync ring0 + trafic inter-nœuds |
| `vmbr1.200` | 200 | `10.200.0.0/24` | **9000** | Ceph public + cluster, migration à chaud |
| `vmbr1.300` | 300 | `10.30.0.0/24` | 1500 | Infrastructure — VM PBS (`10.30.0.20`) |
| `vmbr1` + `tag=400` | 400 | `10.40.0.0/24` | 1500 | LAN des VM (derrière OPNsense) |
| `vmbr1` **sans tag** | — | bloc public OVH | 1500 | **WAN OPNsense uniquement** |
| `vmbr0` (`<nic publique>`) | — | IP publiques | 1500 | Management, Corosync ring1 |

```
auto vmbr1
iface vmbr1 inet manual
	bridge-ports <nic-vrack>
	bridge-vlan-aware yes
	bridge-vids 2-4094
	bridge-stp off
	bridge-fd 0
	mtu 9000
```

**Ajouter un VLAN ne demande plus aucune modification des hôtes** : il suffit de
poser `tag=N` sur la carte réseau de la VM. C'est le bénéfice principal de cette
structure, au-delà d'OPNsense.

Sur le VLAN 400, les machines sont allouées par dizaines : `.1` passerelle
(OPNsense), `.10` proxy-tim (CT 201), `.20` PBS (VM 102, sortie APT), `.30`
headscale (CT 202), `.40` pacs03 (PACS de secours, bare-metal Windows GRA3
raccordé au vRack — [15-pacs-secours.md](15-pacs-secours.md)). S'y ajoute une
plage **hors VLAN** : le tailnet headscale
`100.72.0.0/16` ([11-headscale.md](11-headscale.md)) — choisie dans le CGNAT
`100.64.0.0/10` mais **hors `100.64.0.0/24`**, car `100.64.0.1` est la
passerelle publique OVH des trois nœuds : ne jamais enrôler un hyperviseur
dans le tailnet.

> ⚠️ **Une carte sans `tag` sur `vmbr1` est raccordée au bloc public OVH.** Toute
> VM de production doit porter `tag=400`. Oublier le tag expose la machine
> directement sur Internet. La carte WAN d'OPNsense est la seule carte
> légitimement sans tag du cluster.

Le filtrage VLAN par port empêche une VM d'émettre ou de recevoir sur un VLAN qui
ne lui est pas assigné — une VM compromise ne peut pas injecter dans Corosync ni
dans Ceph. C'est ce qui a motivé le choix du bridge VLAN-aware plutôt qu'un bridge
classique, qui aurait laissé fuiter tous les VLAN vers toutes les VM.

Dernier octet : **`.11` = pve1, `.12` = pve2, `.13` = pve3** sur chaque VLAN.

**Jumbo frames validés** en conditions réelles sur le VLAN 200 :
`ping -M do -s 8972` passe entre les trois nœuds. Ne pas relever le MTU du
VLAN 100 : Corosync veut de la latence basse, pas du débit.

### Corosync : deux anneaux

```
ring0 : 10.100.0.11/12/13     (vRack, dédié, faible latence)
ring1 : IP publiques           (secours si le vRack tombe)
```

`link_mode: passive`. Les deux anneaux sont vérifiés `connected` par
`corosync-cfgtool -n`. Trois nœuds ⇒ quorum de 2, **aucun QDevice nécessaire**.

### Résolution de noms

`/etc/hosts` fait pointer les noms courts vers les **IP vRack VLAN 100**, pas
vers les IP publiques. Le trafic inter-nœuds (proxy API, pmxcfs) emprunte donc
le réseau privé à 25 Gb/s. `nsswitch.conf` place `files` avant `myhostname`,
ce qui garantit que `pve1` résout bien en `10.100.0.11`.

Entrées annexes disponibles : `pveN-ceph` (VLAN 200) et `pveN-pub` (IP publique).
Les FQDN du fichier sont en `tim.lan`, domaine interne qui n'existe que dans ce
`/etc/hosts` — aucun serveur DNS ne le sert
([14-noms-de-domaine.md](14-noms-de-domaine.md#résolution-interne)).

## Disques

Partitionnement **livré tel quel par le template OVH `proxmox9`** — aucune
réinstallation n'a été nécessaire, contrairement à ce que le plan initial prévoyait.

| Partition | Taille | Type | Usage |
|---|---|---|---|
| `p1` | 511 Mio | RAID1 `md1` | `/boot/efi` |
| `p2` | 1 Gio | RAID1 `md2` | `/boot` |
| `p3` | 97,7 Gio | RAID1 `md3` | `/` (ext4) |
| `p4` | 7,9 Gio | **hors RAID** | swap |
| `p5` | 48,8 Gio | miroir ZFS `data` | `/var/lib/vz` (zvol `data/zd0`) |
| `p6` | 2 Mio | — | marqueur iso9660 OVH — **ne pas toucher**, *un seul disque par nœud* |
| `p7` | **738,4 Gio** | aucun | **OSD Ceph** (créée par nous) |

`p7` a été créée avec `sgdisk -n 7:0:0`, qui sélectionne le plus grand bloc libre.
`pveceph osd create` accepte une partition ; c'est uniquement l'interface web qui
ne sait pas voir l'espace non alloué.

> **Les deux disques d'un nœud ne sont pas identiques.** Relevé le 14/08/2026 :
> le marqueur `p6` — image iso9660 `config-2` déposée par l'installeur OVH, en fin
> de disque — n'existe que sur **un disque sur deux**, et pas le même partout :
>
> | | disque portant `p6` | `p7` s'arrête |
> |---|---|---|
> | pve1, pve2 | `nvme1n1` | avant `p6` sur `nvme1n1`, en fin de disque sur `nvme0n1` |
> | **pve3** | **`nvme0n1`** | l'inverse |
>
> L'écart est de 4 064 secteurs (2 Mio) : sans conséquence sur Ceph, les six OSD
> pesant tous 738,4 Gio. Mais **ne pas supposer les deux tables identiques** lors
> d'un remplacement de disque — voir
> [03-exploitation.md](03-exploitation.md#un-disque-nvme-est-mort).

> **Le swap n'est pas redondé** : `p4` est une partition indépendante sur chaque
> disque, hors RAID. La perte d'un NVMe fait donc disparaître la moitié du swap
> et peut provoquer des OOM. C'est le défaut du template OVH. Avec 64 Go de RAM
> et Ceph, le risque est faible mais réel — voir [06-reste-a-faire.md](06-reste-a-faire.md).

## Stockage NAS-HA

Depuis le 13/08/2026, un **NAS-HA OVH `zpool-130899`** complète le stockage
local : 3000 Gio de SSD, à **Roubaix** — donc dans un autre datacenter que le
cluster, ce qui vaut séparation géographique pour les sauvegardes.

| Partition | Taille | Stockage Proxmox | Contenu |
|---|---|---|---|
| `pbs` | 1800 Gio | `nas-pbs` (NFS) | disque du datastore Proxmox Backup Server |
| `vmstore` | 700 Gio | `nas-vm` (NFS) | disques VM, ISO, templates, sauvegardes |

> ⚠️ **Le NAS-HA n'est pas raccordable au vRack** — limitation OVH. Il se joint
> par `10.201.13.43` via la **route par défaut**, donc par `vmbr0` et
> `100.64.0.1`, en MTU 1500. Son ACL attend les **IP publiques** des nœuds, pas
> leurs IP vRack. Ne pas chercher à le poser sur le VLAN 300 : c'est impossible.

Attention à la proximité des adresses : le NAS est en **`10.201`**`.13.43`, le
VLAN Ceph en **`10.200`**`.0.x`. Un chiffre d'écart.

Détail complet dans [10-sauvegardes.md](10-sauvegardes.md).

## Ceph

```
fsid            08c111f7-4af0-46dc-bc3b-9ca7f358a80f
version         Tentacle 20.2.2
public_network  10.200.0.0/24
cluster_network 10.200.0.0/24     (mutualisé : inutile de séparer à 25 Gb/s)
MON / MGR       3 / 3 (un par nœud)
OSD             6 (deux par nœud, 738 Gio chacun, classe ssd)
```

Pool applicatif **`vm-storage`** : `size=3`, `min_size=2`, `pg_autoscale_mode=on`
(l'autoscaler a ramené `pg_num` de 128 à 32, comportement normal à vide).

**Domaine de défaillance CRUSH = `host`** — vérifié explicitement. Avec deux OSD
par nœud, c'est ce qui garantit que les trois répliques atterrissent sur trois
machines distinctes. Point le plus critique de toute la configuration Ceph :

```bash
ceph osd crush rule dump replicated_rule | grep -A1 chooseleaf   # attendu : "type": "host"
```

## Dimensionnement

### Disque

```
6 OSD × 738,4 Gio            = 4,3 Tio bruts
÷ 3 répliques                = 1,44 Tio utilisables   (MAX AVAIL annoncé : 1,4 Tio)
× 0,85 (seuil nearfull)      ≈ 1,22 Tio à ne pas dépasser en pratique
```

Auquel s'ajoutent **700 Gio sur `nas-vm`** (NAS-HA). Capacité VM totale
≈ **1,9 Tio**, mais les deux stockages ne se valent pas :

| | Ceph `vm-storage` | NAS `nas-vm` |
|---|---|---|
| Capacité pratique | 1,22 Tio | 700 Gio |
| Support | NVMe local, 25 Gb/s | SSD distant, bande passante mutualisée |
| Latence | locale | 1,68 ms (Gravelines ↔ Roubaix) |
| Débit mesuré | — | 171 Mo/s écriture, 477 Mo/s lecture |
| Usage | **production** | ISO, templates, disques de données, VM froides |

Ne pas poser sur `nas-vm` une base de données ni un PACS.

### Mémoire

Par nœud, sur 64 Go :

| Poste | Réservé |
|---|---|
| 2 OSD × `osd_memory_target` 4 Go | 8 Go |
| MON + MGR | ~3 Go |
| Hôte, noyau, pmxcfs | ~3 Go |
| **Disponible pour les VM** | **~50 Go** |

**Plafond à respecter : ~100 Go de RAM VM cumulée sur les 3 nœuds.** Au-delà,
deux nœuds ne peuvent plus porter la charge des trois et la promesse HA devient
fausse le jour de la panne.

## Conséquence structurelle du choix à 3 nœuds

Avec `size=3` et un domaine de défaillance `host`, la perte d'un nœud laisse
Ceph **durablement dégradé** : il ne reste que deux hôtes, donc aucun
emplacement pour recréer la troisième réplique.

- Les VM continuent de fonctionner (`min_size=2` satisfait)
- `ceph -s` affiche `HEALTH_WARN`, les PG passent `active+undersized+degraded`
- Le mot **`active`** est ce qui compte : les I/O ne sont pas bloquées
- La resynchronisation se fait seule au retour du nœud (< 1 min mesurée à vide)

C'est le comportement attendu de cette topologie, pas une avarie. Un 4ᵉ nœud
permettrait l'auto-guérison.
