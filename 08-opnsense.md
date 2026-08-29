# OPNsense — passerelle, firewall et VPN

VM pare-feu du cluster, déployée le 11/08/2026. Point de passage réseau unique des
machines virtuelles : accès Internet, filtrage, et accès VPN.

> **Pourquoi OPNsense et non pfSense**, qui était la demande initiale : Netgate ne
> publie plus d'ISO autonome pour pfSense CE depuis la 2.8 — le miroir public
> s'arrête à la 2.7.2 (2023) et la version courante n'est accessible que via un
> installeur en ligne réservé aux comptes de leur boutique. À cela s'ajoutent un
> rythme de correctifs plus lent et des nouveautés réservées à pfSense **Plus**,
> payant hors matériel Netgate. OPNsense se télécharge directement, publie deux
> versions majeures par an, et intègre WireGuard au noyau depuis la 24.1.

---

## Fiche d'identité

| | |
|---|---|
| VM | `opnsense`, **VMID 100**, sur `vm-storage` (Ceph) |
| Version | OPNsense 26.1.6_2 (amd64), FreeBSD 14.3 |
| Ressources | 4 vCPU (`host`), 8 Go sans ballooning, disque 32 Go |
| Haute dispo | ressource HA, `max_restart 3`, `max_relocate 3` |
| Interface web | `https://10.40.0.1` — **accessible par WireGuard uniquement** |
| Console de secours | série, via `qm terminal 100` ou le socket `/var/run/qemu-server/100.serial0` |

### Réseau

| Rôle | Interface | Carte Proxmox | Adresse |
|---|---|---|---|
| **WAN** | `vtnet0` | `net0` → `vmbr1` **sans tag** | `57.130.34.121/29`, passerelle `57.130.34.126` |
| **LAN** | `vtnet1` | `net1` → `vmbr1` **`tag=400`** | `10.40.0.1/24` |
| **WGVPN** | `wg0` (`opt1`) | — | `10.90.0.1/24` |
| **WGSITE2** | `wg2` (`opt3`) | — | `172.33.0.7/32` |

### Bloc public OVH `57.130.34.120/29`

| Adresse | Rôle |
|---|---|
| `.120` | réseau — réservée |
| **`.121`** | **WAN OPNsense** |
| `.122` | IP virtuelle **proxy-tim** (CT 201) — depuis le 12/08/2026 |
| `.123` | IP virtuelle **headscale** (CT 202) — depuis le 15/08/2026 |
| `.124` → `.125` | libres (2 IP disponibles) |
| `.126` | passerelle OVH |
| `.127` | broadcast |

Le bloc est rattaché **au vRack**, pas à un serveur. C'est ce qui rend la haute
disponibilité réelle : **validé en conditions réelles** — après migration de la VM
sur pve2, un client du VLAN 400 sortait toujours en `57.130.34.121`, sans aucune
action côté OVH. Avec une IP rattachée à un serveur et sa MAC virtuelle, ce test
aurait échoué.

---

## Filtrage

Règles dans l'ordre d'évaluation (la première qui correspond gagne) :

| Interface | Action | Objet |
|---|---|---|
| `lan` | **block** | LAN → `10.100.0.0/24` (Corosync) |
| `lan` | **block** | LAN → `10.200.0.0/24` (Ceph) |
| `lan` | **block** | LAN → `10.30.0.0/24` (Infrastructure, **serveur de sauvegarde**) |
| `lan` | pass | LAN → tout (IPv4 puis IPv6) |
| `wan` | pass | UDP **51820** vers l'IP WAN (WireGuard nomades) |
| `wan` | pass | UDP **51822** vers l'IP WAN (WireGuard site-à-site) |
| `wan` | rdr+pass | TCP **80/443** vers `.122` → `10.40.0.10` (proxy-tim) |
| `wan` | rdr+pass | TCP **10051** vers `.122` → `10.40.0.60` (trapper Zabbix, agents actifs — [17-zabbix.md](17-zabbix.md), 29/08/2026) |
| `wan` | rdr+pass | TCP **443** et UDP **3478** vers `.123` → `10.40.0.30` (headscale) |
| `opt1` | **block** ×3 | Nomades → les trois réseaux d'infrastructure |
| `opt1` | pass | Nomades → tout |
| `opt3` | **block** ×3 | TELLIS (site distant) → les trois réseaux d'infrastructure |
| `opt3` | pass | TELLIS (site distant) → tout |

> Depuis le 13/08/2026, le blocage `LAN → 10.30.0.0/24` protège aussi le serveur
> de sauvegarde PBS (`10.30.0.20`) : une VM compromise sur le LAN ne peut pas
> l'atteindre. C'est voulu — l'interface PBS s'ouvre par tunnel SSH, voir
> [10-sauvegardes.md](10-sauvegardes.md#accès-à-linterface-pbs).

> Les règles `opt1` prennent `opt1 net` comme source ; celles d'`opt3` prennent
> **`any`**. Ce n'est pas une inattention : `wg2` porte un `/32`, donc `opt3 net`
> ne vaut que `172.33.0.7` et ne correspondrait à aucun paquet venu de
> `192.168.x`. La source `any` est sans danger ici — WireGuard n'admet sur
> l'interface que les adresses déclarées dans les `AllowedIPs` du pair.

> Les redirections des `.122` et `.123` portent leur autorisation **dans la
> règle NAT elle-même** (`<pass>pass</pass>`) : elles n'apparaissent pas dans la
> liste des règles WAN. Celles de headscale sont en réflexion **`purenat`**, et
> le correcteur global `enablenatreflectionhelper` est actif depuis le
> 15/08/2026 — nécessaire pour que les machines du VLAN 400 joignent leurs
> propres services publiés par la VIP publique
> ([07-pieges.md, piège 29](07-pieges.md#29-la-réflexion-nat-seule-ne-suffit-pas--il-faut-aussi-le-nat-sortant-du-retour)).

**NAT sortant** en mode hybride : `10.40.0.0/24` est masqué derrière
`57.130.34.121`, `10.40.0.10` (proxy-tim) derrière `57.130.34.122`, et
`10.40.0.30` (headscale) derrière `57.130.34.123`. Les règles
automatiques sont toutes attachées à `vtnet0` : le trafic à destination du site
distant sort par `wg2` et **n'est donc pas masqué**, ce qu'il faut pour un
site-à-site. Vérifiable par `pfctl -sn`.

La segmentation a été **vérifiée depuis un vrai client**, pas déduite : un conteneur
sur le VLAN 400 atteignait Internet et sortait bien en `57.130.34.121`, tandis que
Corosync, Ceph, l'infrastructure et l'interface Proxmox (8006) étaient tous
injoignables. Même résultat depuis un client WireGuard.

---

## WireGuard

### Nomades — `wg0`, UDP 51820, `10.90.0.0/24`

Pair existant : `nomade-01` → `10.90.0.2/32`. Dernier handshake relevé le
**13/08/2026 à 13:58** (mesure du 14/08 22:12) : le tunnel est configuré et
fonctionnel, mais aucun client ne s'y est connecté depuis. `configctl wireguard
show` donne l'horodatage réel — un pair déclaré n'est pas un pair actif.

La configuration client `/root/wg-nomade-01.conf` a bien été **retirée de pve1** :
elle contenait une clé privée et n'existe plus que dans le gestionnaire de secrets.
Pour en refabriquer une, recréer un pair — la clé privée d'un pair existant n'est
pas relisible.

Le tunnel scindé par défaut ne route que `10.40.0.0/24` et `10.90.0.0/24`.
Pour tout faire passer par le VPN : `AllowedIPs = 0.0.0.0/0`.

### Ajouter un nomade

1. Générer une paire de clés : `configctl wireguard gen_keypair`
2. Interface web → *VPN → WireGuard → Peers* → nouvelle entrée, IP libre dans
   `10.90.0.0/24`
3. Rattacher le pair à l'instance `wg-nomades`
4. Appliquer : `configctl wireguard configure`

Si le pair a été ajouté **en modifiant `config.xml` directement** plutôt que par
l'interface web, faire précéder cette commande d'un
`configctl template reload OPNsense/Wireguard` — voir le piège n° 22.

### Site-à-site — `wg2`, UDP 51822

Déployé le 14/08/2026. **L'OPNsense est client**, le pfSense du **DC TELLIS**
([13-tellis.md](13-tellis.md)) est serveur : c'est lui qui détient l'adressage
du tunnel et qui a alloué `172.33.0.7/32`.
L'adressage `10.91.0.0/30` un temps envisagé n'a jamais été utilisé.

| | |
|---|---|
| Instance | `wg-site2site-v2`, instance 2 → `wg2` → `opt3` (**WGSITE2**) |
| Adresse locale | `172.33.0.7/32` |
| Écoute locale | UDP **51822** sur `57.130.34.121` |
| Pair | `site-pfsense-v2`, endpoint `37.61.243.246:51822`, keepalive 25 s |
| Réseaux distants | `192.168.101.48/28`, `192.168.101.96/28`, `192.168.111.0/24` |
| Annoncé au distant | `172.33.0.7/32`, `10.40.0.0/24`, `10.90.0.0/24` |
| Site distant | **DC TELLIS** — inventaire complet dans [13-tellis.md](13-tellis.md) |

Côté pfSense TELLIS (`192.168.101.59`), le tunnel s'appelle `tun_wg2` « VPN-Wireguard-SiteTIM », porte
`172.33.0.1/24`, et est **assigné** à l'interface `OPT3` — condition nécessaire
pour lui attacher une passerelle `172.33.0.7` et les routes statiques vers
`10.40.0.0/24` et `10.90.0.0/24`.

**Un tunnel dédié, et non un pair ajouté au tunnel des nomades.** Le premier
essai plaçait notre pair sur `tun_wg0`, qui porte les nomades de TELLIS.
Assigner ce tunnel — indispensable au routage — l'a sorti du groupe d'interfaces
`WireGuard` et a coupé tous ses utilisateurs, dont l'administrateur connecté.
Un tunnel dédié ne portant que ce lien, son assignation n'expose personne.
La clé privée de `tun_wg0` a par ailleurs été exposée lors de ces manipulations —
voir [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts).

**Les serveurs distants ont besoin de routes explicites.** Le pfSense route nos
préfixes, mais ses serveurs répondent à leur passerelle par défaut. Chaque
machine à joindre doit connaître `10.40.0.0/24` et `10.90.0.0/24` via l'adresse
du pfSense sur son propre réseau — `192.168.101.59`, `192.168.101.110` ou
`192.168.111.254` selon le sous-réseau — et autoriser ces sources dans son
pare-feu local. Les équipements réseau dont la route par défaut pointe déjà sur
le pfSense fonctionnent sans rien ajouter. La liste des machines concernées est
l'inventaire de [13-tellis.md](13-tellis.md#inventaire-par-bloc-fonctionnel) —
seule `192.168.101.52` a reçu ce traitement à ce jour.

Ajouter `172.33.0.0/24` à ces routes n'est pas nécessaire au service, mais
conserve un point de mesure : si `172.33.0.7` joint un serveur alors que
`10.40.0.1` ne le joint pas, le tunnel est hors de cause et le défaut est dans
les routes.

### Validation du 14/08/2026

Mesuré, pas déduit : handshake établi, routes présentes des deux côtés, pfSense
joignant `10.40.0.1` et `10.90.0.1`, serveur `192.168.101.52` (le Vue PACS
Philips, [13-tellis.md](13-tellis.md#imagerie-philips)) joint depuis le LAN
et depuis les nomades, et **paquet de 1392 octets transmis sans fragmentation** —
ce dernier point valide le MTU 1420 de bout en bout, qu'un `ping` court n'aurait
pas révélé.

Les nomades atteignent TELLIS sans règle supplémentaire : leur trafic
entre par `opt1`, ne correspond à aucun des trois blocages, et sort par la règle
`pass` existante.

Une adresse en `/32` sur l'interface tunnel ne crée aucun réseau *on-link* — tout
le routage vient des `AllowedIPs`. C'est le fonctionnement normal d'un client
WireGuard, pas une anomalie.

**Le contrôle de recouvrement est la première chose à faire** avant d'ajouter un
site : aucune plage distante ne doit croiser `10.40.0.0/24`, `10.90.0.0/24`,
`10.30.0.0/24`, `10.100.0.0/24`, `10.200.0.0/24`, **`100.72.0.0/16`** (plage
du tailnet headscale, [11-headscale.md](11-headscale.md)) ni `172.32.0.0/24`
(tunnel WireGuard direct « DC-TELLIS-PARTENAIRES » entre pacs03 et le pfSense
TELLIS, découvert le 25/08/2026 — [15-pacs-secours.md](15-pacs-secours.md)).
Un chevauchement ne se voit qu'une fois le tunnel monté.

> Le pfSense TELLIS maîtrisant le tunnel, tout changement de son côté — port, IP
> publique, révocation de clé — coupe le lien sans préavis ici.

---

## Résolution interne — override Unbound

Unbound (sur `10.40.0.1`) est le résolveur des machines du VLAN 400. Il porte
des **host overrides** :

| Nom | Réponse interne | Raison |
|---|---|---|
| `auth.teleimagerie.net` (27/08/2026) | `10.40.0.10` (proxy-tim) | joindre la VIP `.122` depuis l'intérieur aboutit sur la GUI d'OPNsense — [piège n° 32](07-pieges.md#32-joindre-la-vip-122-depuis-lintérieur-aboutit-sur-la-gui-dopnsense) |
| `zabbix.teleimagerie.net` (29/08/2026) | `10.40.0.10` (proxy-tim) | même raison — ne couvre que le web : un client interne du trapper 10051 viserait `10.40.0.60` en direct ([17-zabbix.md](17-zabbix.md)) |

Les overrides sont inscrits dans `config.xml` (`unboundplus/hosts`) : ils
survivent à une reconstruction depuis l'export hebdomadaire, et la GUI les
montre dans *Services → Unbound DNS → Overrides*. Sauvegardes préalables aux
éditions : `/conf/config.xml.bak-keycloak-20260827` et
`/conf/config.xml.bak-zabbix-20260829` (celle-ci posée en éditant
`config.xml` en direct puis `configctl unbound restart` + `configctl filter
reload` — même effet que la GUI).

```bash
# vérifier la réponse interne (sur OPNsense)
drill @127.0.0.1 auth.teleimagerie.net A
```

> ⚠️ Cet override est une **dépendance de démarrage de headscale** (sa section
> `oidc` valide l'issuer au boot) et les CT doivent utiliser `10.40.0.1` comme
> résolveur pour le voir — [piège n° 33](07-pieges.md#33-un-ct-sans-nameserver-hérite-du-résolveur-public-du-nœud).

---

## Accès d'administration

**Interface web** : WireGuard, puis `https://10.40.0.1`.

**SSH depuis le poste d'administration**, en rebondissant par un hyperviseur —
fonctionne sans VPN :

```bash
ssh -J root@pve1.infra.teleimagerie.net root@10.40.0.1
```

Clés autorisées sur le compte root d'OPNsense : celle du poste d'administration
(`matt@LENOVO-MCA2`) et celle de root sur pve1 (nécessaire aux scripts).
Elles sont inscrites dans `config.xml` — voir le piège n° 20, une clé posée
directement dans `authorized_keys` ne survit pas à un redémarrage.

> Le shell root d'OPNsense est **tcsh** : `$(...)` et `2>/dev/null` y échouent.
> Encapsuler dans `sh -c "..."`.

**Voie de secours** : console série depuis n'importe quel nœud portant la VM.
Elle ne dépend d'aucune configuration réseau et fonctionne même firewall cassé :

```bash
qm terminal 100          # Ctrl+O pour quitter
```

> **Patte d'administration pérenne depuis le 27/08/2026** : pve1 porte
> `10.40.0.2` sur le VLAN 400 via une stanza `vmbr1.400` dans
> `/etc/network/interfaces` ([configs/interfaces-pve1](configs/interfaces-pve1)).
> Elle était posée à la main et mourait à chaque redémarrage — trois fois le
> 27/08/2026, cassant silencieusement le hook des certificats syngo
> ([09-proxy-tim.md](09-proxy-tim.md#renouvellement-automatisé-depuis-pve1--mis-en-place-le-24082026)).
> L'entorse à la segmentation est **assumée et neutralisée** : une règle
> prioritaire de `cluster.fw` jette tout ce qui vient de `10.40.0.0/24` vers
> les hyperviseurs — la patte est **sortante uniquement** (vérifié : port 22
> de `10.40.0.2` injoignable depuis un CT du VLAN 400, hook rejoué de bout en
> bout — [04-securite.md](04-securite.md#firewall)). `backup-opnsense.sh`
> garde en plus son repli par rebond PBS si la patte manquait.

Le mot de passe root d'OPNsense et la configuration du premier pair WireGuard ont
été transmis puis **détruits des serveurs** le 11/08/2026. Ils n'existent plus que
dans votre gestionnaire de secrets. Pour régénérer une configuration cliente,
passer par l'interface web ou recréer un pair.

En cas de perte du mot de passe root, l'accès SSH par clé reste opérationnel, et
l'option 3 du menu de la console série permet de le réinitialiser.

---

## Sauvegarde de la configuration

**Traité depuis le 13/08/2026**, à deux niveaux :

1. **La VM 100 entière** est sauvegardée chaque nuit dans PBS, sur le NAS-HA à
   Roubaix — donc hors du cluster et hors du datacenter.
2. **Une copie du seul `config.xml`**, chaque samedi à 04:30, dans
   `/mnt/pve/nas-vm/opnsense-config/` (12 copies conservées). Elle sert à
   reconstruire un OPNsense neuf sans restaurer toute la VM.

Le script est [`scripts/backup-opnsense.sh`](scripts/backup-opnsense.sh), déployé
dans `/usr/local/sbin/` sur pve1 et déclenché par `backup-opnsense.timer`.

> Il essaie d'abord l'accès direct par `10.40.0.2`, puis **rebondit par la VM PBS**
> (`10.30.0.20`), qui est sur le VLAN 400 en permanence. C'est ce qui le rend
> insensible à la disparition de l'adresse non persistante de pve1. Dans les deux
> cas, l'authentification finale utilise la clé de `root@pve1`, la seule inscrite
> dans `config.xml`.

Export manuel, si besoin : *System → Configuration → Backups*, ou

```bash
scp -J root@pve1.infra.teleimagerie.net root@10.40.0.1:/conf/config.xml \
    opnsense-config-$(date +%F).xml
```

> Le fichier contient les **clés privées WireGuard** : répertoire en `700`,
> fichiers en `600`, à traiter comme un secret.

Des sauvegardes automatiques existent aussi côté OPNsense dans `/conf/backup/`,
mais elles vivent sur la VM — inutiles si la VM est perdue.

---

## Points d'attention

**OPNsense est un point de défaillance unique pour l'accès Internet des VM.**
Sur panne du nœud porteur, la HA la relance ailleurs en ~2 min. Les VM continuent
de tourner, elles perdent seulement le réseau ; Ceph n'est pas affecté.

La paire CARP reste possible : le WAN étant dans le vRack, on échappe à la
limitation d'OVH qui interdit CARP sur le réseau public de ses serveurs dédiés.

**Une carte réseau sans `tag` sur `vmbr1` est raccordée au bloc public.** Toute VM
de production doit porter `tag=400`. La carte WAN d'OPNsense est la seule carte
légitimement sans tag du cluster.
