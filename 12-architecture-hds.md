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
| Rôle | infrastructure transverse : pare-feu, reverse proxy, VPN, sauvegardes, futur PACS | production imagerie : PACS Philips, Syngo Via, RIS VENUS, passerelles IA, téléradiologie IMADIS |
| IP publiques | bloc `57.130.34.120/29` + les 3 nœuds | `37.61.243.246` (WAN pfSense) |
| Documentation | fichiers [01](01-architecture.md) à [11](11-headscale.md) | [13-tellis.md](13-tellis.md) |

> **Périmètre HDS** : l'hébergement de données de santé impose des hébergeurs
> certifiés. OVHcloud est certifié HDS ; le statut du prestataire TELLIS et le
> périmètre exact couvert par chaque contrat restent **⚠️ à formaliser** — ne
> rien affirmer avant vérification contractuelle.

Un troisième lieu intervient, sans être un datacenter opéré : le **NAS-HA
OVH de Roubaix**, qui reçoit les sauvegardes du cluster
([10-sauvegardes.md](10-sauvegardes.md)) — hors site par rapport à Gravelines.

---

## Schéma d'ensemble

```
                         utilisateurs (radiologues, sites)
                            │                    │
              https://syngo-via.*   (b) tailnet headscale 100.72.0.0/16
                            │            passerelles DICOM des sites
   aujourd'hui : DNS → ─────┤                    ┆ (à venir)
   37.61.243.246 direct     │                    ┆
   cible : DNS → ───────┐   │                    ┆
   57.130.34.122        │   │                    ┆
┌─── DC OVH (GRA4) ─────▼───┼────┐   ┌─── DC TELLIS ──┼──────────────────┐
│                           │    │   │                ┆                  │
│  proxy-tim (CT 201)       │    │   │  pfSense ══════╪═ WAN 37.61.243.246
│    .122 · relais TLS ─────┼────┼───┼──► NAT 443 → TSplus .102          │
│  OPNsense (VM 100)        │    │   │       │                           │
│    .121 · wg2 ════════════╪════╪═══╪══ tun_wg2 (UDP 51822)             │
│  headscale (CT 202) ·.123 ┆    │   │                                   │
│  PBS (VM 102) → NAS Roubaix    │   │  192.168.101.48/28  imagerie      │
│  futur PACS ·············┆     │   │  192.168.101.96/28  Syngo Via     │
│                                │   │  192.168.111.0/24   RIS VENUS     │
└────────────────────────────────┘   └───────────────────────────────────┘
        (a) chemin public : TLS relayé ou direct, selon l'état du DNS
        ═══  tunnel WireGuard wg2 (site-à-site)
        ┆┆┆  tailnet headscale — à venir
```

Trois liens distincts entre les deux mondes :

- **(a) le chemin public** — `syngo-via.*` en TLS sur le 443. Aujourd'hui le
  DNS pointe **directement** sur `37.61.243.246` ; après la bascule DNS il
  passera par `57.130.34.122` (relais TLS de `proxy-tim`,
  [09-proxy-tim.md](09-proxy-tim.md)) ;
- **le tunnel `wg2`** — site-à-site WireGuard entre OPNsense et le pfSense
  TELLIS, pour l'administration et les flux privés
  ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) ;
- **(b) le tailnet headscale** — plan de contrôle VPN des passerelles DICOM des
  sites d'acquisition vers le futur PACS ([11-headscale.md](11-headscale.md)),
  pointillé : rien n'y est encore enrôlé en production.

---

## Flux inter-datacenters

| Flux | Source | Destination | Port/proto | Chemin | Statut |
|---|---|---|---|---|---|
| Utilisateurs → TSplus (`syngo-via.*`) | Internet | `37.61.243.246` | TCP `443` | public, direct (DNS actuel) | ✅ en production |
| Idem, après bascule DNS | Internet | `57.130.34.122` → relais TLS → `37.61.243.246` | TCP `443` | public, via `proxy-tim` | ✅ prêt et vérifié ; bascule **avant le 17/10/2026** ([09-proxy-tim.md](09-proxy-tim.md#checklist-pour-le-jour-de-la-bascule)) |
| Défis ACME du certificat TSplus | Internet | `57.130.34.122` → relais → `37.61.243.246` | TCP `80` | public, via `proxy-tim` | ✅ testé le 24/08/2026 |
| Transport du tunnel site-à-site | `57.130.34.121` | `37.61.243.246` | UDP `51822` | public (WireGuard) | ✅ monté le 14/08/2026 |
| Admin / nomades → Vue PACS | `10.40.0.0/24`, `10.90.0.0/24` | `192.168.101.52` | — | dans `wg2` | ✅ testé le 14/08/2026 |
| Admin → autres machines TELLIS | idem | `192.168.101.x`, `192.168.111.x` | — | dans `wg2` | ⚠️ routes retour posées sur `.52` seulement ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)) |
| TELLIS → nos VM | `192.168.101.x`, `192.168.111.x` | `10.40.0.0/24` | — | dans `wg2` | ⚠️ jamais testé dans ce sens ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)) |
| Passerelles DICOM des sites → futur PACS | sites d'acquisition | futur PACS (DC OVH) | DICOM `104`, `11112` | tailnet (`tag:gateway` → `tag:pacs`) | 📋 à venir ([11-headscale.md](11-headscale.md)) |

---

## Noms DNS et chemins d'accès

Cibles d'architecture uniquement — **l'état DNS réel du moment se lit dans
[09-proxy-tim.md](09-proxy-tim.md#la-bascule-dns-nest-pas-faite--le-proxy-ne-reçoit-pas-la-production)**,
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
| Points ouverts du lien inter-sites (tests manquants, clés exposées) | [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts) |
| Sauvegardes et NAS-HA de Roubaix | [10-sauvegardes.md](10-sauvegardes.md) |
