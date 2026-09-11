# Architecture HDS — vue d'ensemble des deux datacenters

L'infrastructure de téléimagerie repose sur **deux datacenters** : le DC OVH
(le cluster Proxmox documenté dans les fichiers 01 à 11) et le DC TELLIS,
opéré par un prestataire ([13-tellis.md](13-tellis.md)). Ce fichier est la
couche « vue d'ensemble » : il assemble et renvoie, il n'introduit aucun fait
nouveau hors des interconnexions entre les deux sites.

> ✅ vérifié/mesuré · 📋 déclaré (non contrôlé sur machine) · ⚠️ à vérifier /
> inconnu

---

## Les deux sites

| | **DC OVH** | **DC TELLIS** |
|---|---|---|
| Lieu | Gravelines, GRA4 | ⚠️ à documenter |
| Opérateur | nous (serveurs dédiés OVHcloud) | prestataire — ⚠️ identité et contrat à documenter |
| Rôle | infrastructure transverse : pare-feu, reverse proxy, VPN, sauvegardes, authentification, supervision, ERP | production imagerie : PACS Philips, Syngo Via, RIS VENUS, passerelles IA, téléradiologie IMADIS |
| IP publiques | bloc `57.130.34.120/29` + les 3 nœuds | `37.61.243.246` (WAN pfSense) |
| Documentation | fichiers [01](01-architecture.md) à [11](11-headscale.md) + [15](15-pacs-secours.md), [16](16-keycloak.md) | [13-tellis.md](13-tellis.md) |

> **Périmètre HDS** : l'hébergement de données de santé impose des hébergeurs
> certifiés. OVHcloud est certifié HDS ; le statut du prestataire TELLIS et le
> périmètre exact couvert par chaque contrat restent **⚠️ à formaliser** — ne
> rien affirmer avant vérification contractuelle. Depuis le 27/08/2026, le
> serveur d'authentification ([16-keycloak.md](16-keycloak.md)) porte
> l'authentification d'accès.
> 📋 **Déclaré le 29/08/2026** : l'ensemble des serveurs (cluster Proxmox
> compris, donc Keycloak/CT 203) est hébergé en offre **HDS**. La question
> « l'IdP est-il dans le périmètre ? » ne bloque donc plus le raccordement
> SSO de MyTIM (y compris son extension future aux médecins) ; reste à
> consigner cette couverture dans la revue contractuelle ci-dessus.

Un troisième lieu intervient, sans être un datacenter opéré : le **NAS-HA
OVH de Roubaix**, qui reçoit les sauvegardes du cluster
([10-sauvegardes.md](10-sauvegardes.md)) — hors site par rapport à Gravelines.

---

## Schéma d'ensemble

```
                         utilisateurs (radiologues, sites)
                            │                    │
              https://syngo-via.*   (b) tailnet headscale 100.72.0.0/16
                            │            gw-qum (site), postes admin,
   aujourd'hui : DNS → ─────┤            hyperviseurs pve1/2/3 (tag:pve)
   37.61.243.246 direct     │                    ┆
   cible : DNS → ───────┐   │                    ┆
   57.130.34.122        │   │   ┌┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘
┌─── DC OVH (GRA4) ─────▼───┼───┼┐   ┌─── DC TELLIS ─────────────────────┐
│                           │   ┆│   │                                   │
│  proxy-tim (CT 201)       │   ┆│   │  pfSense ═══════ WAN 37.61.243.246
│    .122 · relais TLS ─────┼───┼┼───┼──► NAT 443 → TSplus .102          │
│  OPNsense (VM 100)        │   ┆│   │       │                           │
│    .121 · wg2 ════════════╪═══╪╪═══╪══ tun_wg2 (UDP 51822)             │
│  headscale (CT 202) ·.123 ┆┄┄┄┘│   │                                   │
│  pve1/2/3 · tag:pve ······┆    │   │  192.168.101.48/28  imagerie      │
│  PBS (VM 102) → NAS Roubaix    │   │  192.168.101.96/28  Syngo Via     │
│                                │   │  192.168.111.0/24   RIS VENUS     │
└────────────────────────────────┘   └───────────────────────────────────┘
        (a) chemin public : TLS relayé ou direct, selon l'état du DNS
        ═══  tunnel WireGuard wg2 (site-à-site)
        ┆┆┆  tailnet headscale — en service depuis le 15/08/2026
```

Trois liens distincts entre les deux mondes :

- **(a) le chemin public** — `syngo-via.*` en TLS sur le 443. Le DNS pointe
  **directement** sur `37.61.243.246` ; le relais TLS de `proxy-tim`
  (`57.130.34.122`) est prêt et vérifié, la bascule est une décision non prise
  ([09-proxy-tim.md](09-proxy-tim.md)) ;
- **le tunnel `wg2`** — site-à-site WireGuard entre OPNsense et le pfSense
  TELLIS, pour l'administration et les flux privés
  ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) ;
- **(b) le tailnet headscale** — plan de contrôle VPN des passerelles DICOM des
  sites d'acquisition ([11-headscale.md](11-headscale.md)), en service depuis
  le 15/08/2026. Enrôlés : le téléphone et le poste admin (user `admin`), la
  passerelle `gw-qum` (25/08/2026, direct vérifié, 32 ms) et les trois
  hyperviseurs (`tag:pve`, seconde porte d'administration, 31/08/2026). Aucun
  serveur hébergé sur le cluster n'y est enrôlé : `tag:pacs` est déclaré dans
  l'ACL sans qu'aucun nœud le porte.

---

## Flux inter-datacenters

| Flux | Source | Destination | Port/proto | Chemin | Statut |
|---|---|---|---|---|---|
| Utilisateurs → TSplus (`syngo-via.*`) | Internet | `37.61.243.246` | TCP `443` | public, direct (DNS actuel) | ✅ en production — seuls flux restés hors proxy après la bascule du 26/08/2026 |
| Idem, si bascule de `syngo-via.*` un jour | Internet | `57.130.34.122` → relais TLS → `37.61.243.246` | TCP `443` | public, via `proxy-tim` | ✅ prêt et vérifié ; décision non prise ([09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026)) |
| Défis ACME du certificat TSplus | Internet | `57.130.34.122` → relais → `37.61.243.246` | TCP `80` | public, via `proxy-tim` | ✅ testé le 24/08/2026 |
| Transport du tunnel site-à-site | `57.130.34.121` | `37.61.243.246` | UDP `51822` | public (WireGuard) | ✅ monté le 14/08/2026 |
| Admin / nomades → Vue PACS | `10.40.0.0/24`, `10.90.0.0/24` | `192.168.101.52` | — | dans `wg2` | ✅ testé le 14/08/2026 |
| Admin → autres machines TELLIS | idem | `192.168.101.x`, `192.168.111.x` | — | dans `wg2` | ✅ tranché le 05/09/2026 : `10.40.0.0/24` ↔ `192.168.111.x` fonctionne dans les deux sens ; seuls les serveurs derrière le second pfSense `.62` (bloc production) ont besoin d'une route retour explicite, posée sur `.52` et `.53` ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)) ; le poste d'admin, lui, arrive par le VPN nomades du pfSense (`172.31.0.3`, hors `wg2`) et a eu besoin de la même route retour — RDP et SSH directs vers `.52`/`.53` depuis le 11/09/2026 ([13-tellis.md](13-tellis.md#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)) |
| TELLIS → nos VM | `192.168.101.x`, `192.168.111.x` | `10.40.0.0/24` | — | dans `wg2` | ✅ testé le 25/08/2026 (prod01 → pacs03, 17–23 ms, après ajout d'une règle `pass` sur `OPT1_TIM` — [13-tellis.md](13-tellis.md#règles-posées-sur-opt1_tim-le-25082026-sens-tellis--dc-ovh)) ; agents VENUS → CT 204 le 05/09/2026 |
| **Sites → SFTP du RIS VENUS** | 6+ IP publiques (les sites) | `192.168.111.64:2222` | TCP `2222` | ⚠️ **entrée Internet, chemin de publication inconnu** | ✅ **actif et mesuré le 04/09/2026** (7 sites déposent quotidiennement) ; ⚠️ pas de réponse depuis un VPS externe sur les 3 IP publiques connues → NAT filtré par source ou autre adresse, à faire préciser ([13-tellis.md](13-tellis.md#tim-venus2-if-64--interfaces-sftp-des-sites-inventorié-le-04092026)) |
| VENUS app/interfaces → base RIS | `192.168.111.63`, `.64` | `192.168.111.65:3306` | TCP `3306` | LAN VENUS | ✅ constaté le 04/09/2026 (base `isotim`) |
| Sites + PACS Xplore → **ProxyVia** | `172.18.162.40:11112`, `10.0.241.54:104` | `192.168.101.103` (`DP_EC:9104`) | DICOM | bloc imagerie / syngo | ✅ inventorié le 09/09/2026 ([13-tellis.md#dicomproxy-103--proxyvia-le-répartiteur-dicom-inventorié-le-09092026](13-tellis.md#dicomproxy-103--proxyvia-le-répartiteur-dicom-inventorié-le-09092026)) |
| **ProxyVia → Syngo Via** | `192.168.101.103` | `.98`, `.100` (`:104`) | DICOM | répartition **round-robin**, repli croisé, mapping par PatientID | ✅ tranché le 09/09/2026 |
| **ProxyVia → PACS amont** | `192.168.101.103` | `192.168.101.52:2104` (TIMWFMCORE) | DICOM (store, Q/R) | `MoveDestination` réécrites | ✅ constaté le 09/09/2026 |
| `proxy-tim` → backend PACS de secours | `10.40.0.10` | `10.40.0.40` (pacs03, GRA3) | TCP `80` | vRack VLAN 400, inter-DC GRA4↔GRA3 | ✅ basculé le 25/08/2026, 0,25 ms ([15-pacs-secours.md](15-pacs-secours.md)) — avant : HTTP clair vers `188.165.77.137` par Internet |
| Réplication TELLIS → pacs03 | site TELLIS | `172.32.0.2` (pacs03) | WireGuard | tunnel direct `tun_wg1`, hors `wg2` | ✅ en production — doit perdurer, décision du 25/08/2026 ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)) |

---

## Noms DNS et chemins d'accès

Cibles d'architecture uniquement — **l'état DNS réel du moment se lit dans
[09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026)**,
les zones, registrars et serveurs autoritaires dans
[14-noms-de-domaine.md](14-noms-de-domaine.md) — ne pas maintenir deux tables :

| Nom | Cible d'architecture | Service rendu |
|---|---|---|
| `pacs-secours.teleimagerie.net` | `57.130.34.122` (proxy-tim) | PACS de secours (backend OVH) |
| `syngo.teleimagerie.net`, `syngo.isoteam.mn` | `57.130.34.122` | redirections 301 vers `syngo-via.*` |
| `syngo-via.teleimagerie.net`, `syngo-via.isoteam.mn` | `57.130.34.122` → relais TLS → TSplus (DC TELLIS) | portail et RemoteApp Syngo Via |
| `headscale.teleimagerie.net` | `57.130.34.123` | plan de contrôle du tailnet |
| `pve{1,2,3}.infra.teleimagerie.net` | IP publiques des nœuds | administration du cluster |

---

## Où lire le détail

| Sujet | Fichier |
|---|---|
| Le tunnel `wg2` vu du DC OVH (OPNsense, filtrage, validation) | [08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822) |
| Les zones DNS : registrars, échéances, inventaire des six zones | [14-noms-de-domaine.md](14-noms-de-domaine.md) |
| Le DC TELLIS : inventaire, pfSense, flux internes, checklist de collecte | [13-tellis.md](13-tellis.md) |
| Le relais TLS `syngo-via.*` et la bascule DNS | [09-proxy-tim.md](09-proxy-tim.md) |
| Le tailnet headscale (passerelles DICOM, ACL) | [11-headscale.md](11-headscale.md) |
| L'authentification centralisée (Keycloak, SSO, raccordements) | [16-keycloak.md](16-keycloak.md) |
| Points ouverts du lien inter-sites (tests manquants, clés exposées) | [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts) |
| Sauvegardes et NAS-HA de Roubaix | [10-sauvegardes.md](10-sauvegardes.md) |
