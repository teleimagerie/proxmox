# DC TELLIS — fiche de référence du site distant

Deuxième datacenter de l'architecture HDS, opéré par un prestataire. C'est le
site désigné « le site distant » dans les fichiers antérieurs à ce document —
celui que joint le tunnel WireGuard `wg2`
([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) et que dessert le
relais TLS `syngo-via.*` ([09-proxy-tim.md](09-proxy-tim.md)).

L'inventaire ci-dessous a été **déclaré le 25/08/2026** par le responsable
infrastructure. Contrairement aux fichiers 01 à 11, la plupart des informations
n'ont pas encore été contrôlées sur machine : une seule adresse a été jointe par
le tunnel à ce jour. Chaque information porte donc son statut :

> ✅ vérifié/mesuré · 📋 déclaré (source : responsable infra, non contrôlé sur
> machine) · ⚠️ à vérifier / inconnu

---

## Fiche d'identité

| | | |
|---|---|---|
| Prestataire opérateur | nom, contacts, périmètre contractuel | ⚠️ à documenter |
| Localisation physique | — | ⚠️ à documenter |
| Statut HDS | à confirmer contractuellement (certification du prestataire, périmètre couvert) | ⚠️ |
| IP publique (WAN pfSense) | `37.61.243.246` | ✅ endpoint `wg2` opérationnel, et cible DNS de `syngo-via.*` en production |
| Accès admin depuis le DC OVH | tunnel `wg2` ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) ; modalités d'accès web aux équipements | ⚠️ à documenter |
| Rôle | production imagerie : PACS Philips, Syngo Via, RIS VENUS, passerelles IA, téléradiologie IMADIS | 📋 |

## Plan d'adressage

| Sous-réseau | Hôtes | Logique | Passerelle par défaut |
|---|---|---|---|
| `192.168.101.48/28` | `.49` → `.62` | bloc imagerie et production (PACS, IA, passerelles, équipements réseau) | ⚠️ `.59` probable, à confirmer |
| `192.168.101.96/28` | `.97` → `.110` | bloc Syngo Via (serveurs, TSplus, ProxyVia) | ⚠️ `.110` probable, à confirmer |
| `192.168.111.0/24` | `.1` → `.254` | RIS VENUS | ⚠️ `.254` (patte pfSense) probable, à confirmer |

> Ces trois réseaux sont exactement ceux annoncés dans les `AllowedIPs` du
> tunnel `wg2`, et le contrôle de non-recouvrement avec nos plages a déjà été
> fait ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)). Attention
> aux `/28` : `.63` et `.111` sont des adresses de broadcast, pas des hôtes.

---

## Inventaire par bloc fonctionnel

### Réseau et sécurité

Le site compte **deux pfSense** et son propre reverse proxy nginx — trois
équipements dont la configuration précise reste à collecter.

| IP | Machine | Rôle | Mainteneur | Statut |
|---|---|---|---|---|
| `192.168.101.59` | pfSense principal | pare-feu du site, serveur du tunnel `wg2` et du VPN nomades `tun_wg0` ; pattes `192.168.101.59`, `192.168.101.110`, `192.168.111.254` | ⚠️ | pattes ✅ (mise en place du tunnel, 14/08/2026) ; règles, NAT et WireGuard ⚠️ à vérifier précisément |
| `192.168.101.62` | pfSense « FW-Passerelle » | **second pfSense** — rôle inconnu (segmentation interne ? passerelle dédiée ?) | ⚠️ | ⚠️ |
| `192.168.101.61` | Reverse proxy nginx | reverse proxy local du site — noms servis, certificats et backends inconnus | ⚠️ | 📋 existence, ⚠️ rôle |
| `192.168.101.60` | Routeur vers Philips | routage vers l'environnement Philips (lié au PACS et à la télémaintenance ?) | ⚠️ | 📋 existence, ⚠️ rôle |

### Imagerie Philips

Le cœur métier du site : le PACS (*Picture Archiving and Communication
System*), qui archive les examens d'imagerie et les distribue aux stations de
lecture.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.52` | Vue PACS | PACS de production — archivage et distribution des examens | Philips | ✅ seule adresse dont la joignabilité par `wg2` a été testée (14/08/2026) |
| `192.168.101.53` | Vue Motion | visualiseur web « zéro empreinte » de la gamme Vue : consultation des images depuis un simple navigateur, sans client lourd | Philips | 📋 |
| `192.168.101.57` | Passerelle firewall SRSA | boîtier pare-feu de la télémaintenance Philips : canal d'accès distant de l'éditeur vers ses équipements | Philips | 📋 ; signification exacte du sigle et flux ⚠️ |

Le routeur `192.168.101.60` (bloc réseau ci-dessus) fait partie de cet
environnement.

### Analyse IA des images

Deux passerelles locales envoient les examens aux services d'analyse de leur
éditeur et rapatrient les résultats dans le flux de lecture.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.55` | Gateway Gleamer | analyse IA des images (radiographies) | Gleamer | 📋 ; flux exacts (destinations Internet, réinjection PACS) ⚠️ |
| `192.168.101.56` | Gateway Avicenna | analyse IA des images (imagerie en coupe) | Avicenna.AI | 📋 ; idem ⚠️ |

### Téléradiologie IMADIS

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.51` | DLMBOX | boîtier d'échange d'examens avec la plateforme de téléradiologie IMADIS | Deeplink Medical | 📋 ; flux (PACS, RIS, Internet) ⚠️ |

### Syngo Via

Syngo Via est la plateforme de post-traitement et de visualisation avancée de
Siemens Healthineers. Les utilisateurs y accèdent au travers de **TSplus**
(publication d'applications Windows en RemoteApp) — c'est la cible du relais
TLS `syngo-via.*` décrit dans [09-proxy-tim.md](09-proxy-tim.md).

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.98` | Syngo Via serveur 1 | plateforme Syngo Via — répartition des rôles entre les deux serveurs ⚠️ | Siemens Healthineers | 📋 |
| `192.168.101.100` | Syngo Via serveur 2 | idem | Siemens Healthineers | 📋 |
| `192.168.101.102` | TSplus | publication des applications Syngo Via (portail web + RemoteApp, multiplexés sur le 443) ; joint depuis Internet par le NAT du pfSense, le WAN `37.61.243.246` étant « son » adresse publique | TSplus | 📋 ; le service répond bien en `37.61.243.246:443` ✅, le NAT 443 → `.102` reste à confirmer ⚠️ |
| `192.168.101.103` | ProxyVia | routage DICOM vers Syngo Via | — | 📋 |

> **ProxyVia est double-attaché** : `192.168.101.103` dans ce bloc **et**
> `192.168.101.58` dans le bloc imagerie — `.58` n'est donc pas une adresse
> libre. Vraisemblablement le pont DICOM entre les deux sous-réseaux
> (modalités/PACS → Syngo Via), ⚠️ à confirmer.

### RIS VENUS (Softway Medical)

Le RIS (*Radiology Information System*) gère le versant administratif et
organisationnel de l'imagerie : demandes d'examens, planning, comptes rendus,
facturation. Déploiement classique en trois tiers.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.111.63` | `TIM-VENUS1-AP` | serveur application | Softway Medical | 📋 |
| `192.168.111.64` | `TIM-VENUS2-IF` | serveur interfaces — interopérabilité (HL7) avec les autres systèmes | Softway Medical | 📋 ; correspondants et flux ⚠️ |
| `192.168.111.65` | `TIM-VENUS3-DB` | base de données | Softway Medical | 📋 ; sauvegarde ⚠️ |

> L'autre RIS utilisé, **Xplore (EDL)**, est hébergé directement chez EDL :
> **hors périmètre** de cette documentation.

### À identifier

| IP | Machine | Rôle | Statut |
|---|---|---|---|
| `192.168.101.54` | VM Ubuntu `prod01` | **contenu inconnu** — première cible de la [checklist de collecte](#checklist-de-collecte) | ⚠️ |
| `.49`, `.50`, `.97`, `.99`, `.101`, `.104` → `.109`, et l'essentiel de `192.168.111.0/24` | — | jamais déclarées : libres ou occupées ? | ⚠️ demander la liste au prestataire |

---

## Les deux pfSense et le routage interne

Ce qui est établi :

- le pfSense principal a une patte dans chacun des trois sous-réseaux
  (`192.168.101.59`, `192.168.101.110`, `192.168.111.254`) — constaté lors de la
  mise en place du tunnel ;
- il porte des **routes statiques** vers `10.40.0.0/24` et `10.90.0.0/24` via le
  tunnel `wg2` ;
- mais **les routes retour n'ont été posées que sur `192.168.101.52`** : les
  autres serveurs répondent à leur passerelle par défaut et sont injoignables
  depuis chez nous tant qu'ils n'ont pas reçu le même traitement — point ouvert
  documenté dans
  [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts).

Ce qui est inconnu ⚠️ : le rôle du second pfSense `.62` « FW-Passerelle », qui
route réellement entre les trois sous-réseaux (le pfSense seul ? le routeur
`.60` ?), les règles de filtrage internes, et le NAT.

---

## Tunnels WireGuard du site

### `wg2` — site-à-site vers le DC OVH

Vue côté TELLIS uniquement — tout le reste (adressage, pair, MTU, validation)
est dans [08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822) :

| | |
|---|---|
| Tunnel | `tun_wg2` « VPN-Wireguard-SiteTIM », assigné à l'interface `OPT3` |
| Adresse | `172.33.0.1/24` — **le pfSense est serveur**, c'est lui qui détient l'adressage |
| Écoute | UDP `51822` sur le WAN `37.61.243.246` |
| Routes statiques | vers `10.40.0.0/24` et `10.90.0.0/24`, passerelle `172.33.0.7` |

### `tun_wg0` — VPN nomades du site

Le pfSense porte aussi `tun_wg0`, le **VPN nomades du prestataire, en
production**. Il ne fait pas partie de notre périmètre, mais nous concerne
doublement : c'est en assignant par erreur notre premier pair sur ce tunnel que
ses utilisateurs ont été coupés le 14/08/2026 (piège n° 23), et surtout :

> ⚠️ **La clé privée de `tun_wg0` a été exposée** en clair dans un historique de
> terminal les 13-14/08/2026, lors de l'extraction des configurations. Sa
> rotation est à la main du prestataire, **qui doit en être informé** — suivi
> dans [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts).
> Aucune clé ne figure ni ne doit figurer dans ce dépôt.

---

## Reverse proxy nginx local

`192.168.101.61`. Tout est à documenter ⚠️ : noms servis, certificats,
backends, exposition (interne seulement, ou publié sur Internet ?). À ne pas
confondre avec notre `proxy-tim` ([09-proxy-tim.md](09-proxy-tim.md)) ni avec
le NAT 443 → TSplus du pfSense : trois chemins distincts peuvent mener à un
service du site.

---

## Flux internes

Gabarit à remplir lors de la collecte — les lignes actuelles sont des
présomptions d'architecture, pas des flux constatés :

| Source | Destination | Port/proto | Rôle | Statut |
|---|---|---|---|---|
| modalités / sites d'acquisition | `.52` Vue PACS | DICOM | envoi des examens | ⚠️ chemin d'arrivée à documenter |
| `.52` Vue PACS | `.55` Gleamer, `.56` Avicenna | DICOM | envoi à l'analyse IA, retour des résultats | 📋 présumé |
| `.51` DLMBOX | PACS / RIS / Internet | DICOM, HL7 | échanges téléradiologie IMADIS | 📋 présumé |
| `.58`/`.103` ProxyVia | `.98`, `.100` Syngo Via | DICOM | routage des examens vers Syngo Via | 📋 présumé |
| `.53` Vue Motion | `.52` Vue PACS | — | lecture des images pour le visualiseur web | 📋 présumé |
| `.102` TSplus | `.98`, `.100` Syngo Via | — | publication des applications aux utilisateurs | 📋 présumé |
| `192.168.111.64` VENUS-IF | ? | HL7 | interopérabilité RIS (demandes, comptes rendus) | ⚠️ correspondants à documenter |
| `.57` SRSA | Internet (Philips) | — | télémaintenance Philips | 📋 présumé |

---

## Checklist de collecte

Ce qu'il faut extraire pour transformer les 📋/⚠️ ci-dessus en ✅. Les exports
de pfSense contiennent les **clés privées WireGuard** : ils transitent par le
canal des secrets et ne rejoignent jamais ce dépôt.

**pfSense principal `192.168.101.59`** :

- [ ] export `config.xml` (*Diagnostics → Backup & Restore*) — à conserver hors dépôt
- [ ] version de pfSense, matériel ou VM
- [ ] liste des interfaces et de leurs adresses (confirmer les trois pattes)
- [ ] règles de filtrage, interface par interface
- [ ] port forwards NAT — confirmer `443` et `80` → `192.168.101.102` (TSplus)
- [ ] table de routage (qui route entre les trois sous-réseaux ?)
- [ ] baux DHCP statiques, s'il est serveur DHCP
- [ ] pairs des tunnels `tun_wg0` et `tun_wg2` (noms et `AllowedIPs`, pas les clés)

**pfSense « FW-Passerelle » `192.168.101.62`** :

- [ ] son rôle — que filtre-t-il, entre quoi et quoi ?
- [ ] interfaces, règles, export `config.xml`

**VM `prod01` `192.168.101.54`** :

- [ ] `ss -tlnp` — quels services écoutent ?
- [ ] `docker ps` le cas échéant, services systemd actifs
- [ ] version d'OS, qui l'administre et pour quoi faire

**Reverse proxy nginx `192.168.101.61`** :

- [ ] `nginx -T` — noms servis, backends, certificats et leurs échéances — à
  rapprocher de l'inventaire des noms ([14-noms-de-domaine.md](14-noms-de-domaine.md))

**RIS VENUS** :

- [ ] flux HL7 de `TIM-VENUS2-IF` : correspondants, sens, ports
- [ ] sauvegarde de la base `TIM-VENUS3-DB` : qui, comment, testée ?
- [ ] contact support Softway Medical

**Prestataire** :

- [ ] identité, contacts, périmètre contractuel, statut HDS
- [ ] procédure d'accès admin (la nôtre et la sienne)
- [ ] **l'informer de l'exposition de la clé `tun_wg0`** et suivre la rotation
      ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts))

**Divers** :

- [ ] confirmer la double patte ProxyVia `.58`/`.103` et son rôle de pont DICOM
- [ ] liste des adresses réellement occupées (la demander, ne pas scanner un
      site de production)
- [ ] poser les routes retour `10.40.0.0/24`/`10.90.0.0/24` sur chaque serveur
      que nous devons joindre, ou trancher pour un NAT côté pfSense
