# Cluster Proxmox `tim-cluster` — documentation

Cluster de virtualisation haute disponibilité à **5 nœuds** (3 à GRA4, 2 à GRA3
depuis le 15/09/2026), stockage Ceph répliqué synchrone sur les deux
datacentres, hébergé chez OVHcloud à Gravelines.

**Déployé le 11 août 2026.** État : **en production**. Dix machines y tournent :
le pare-feu OPNsense (VM 100), le reverse proxy `proxy-tim` (CT 201), le
serveur de sauvegarde PBS (VM 102), le plan de contrôle VPN `headscale`
(CT 202, pour les passerelles DICOM des sites distants), le serveur
d'authentification centralisée `keycloak` (CT 203, SSO OpenID Connect),
la supervision `zabbix` (CT 204), l'ERP `odoo` (VM 101), les deux
pré-productions de l'application de gestion, `mytim-staging` (VM 103) et
`myisoteam-staging` (VM 104) — sans HA, migrées des dédiés OVH le 14/09/2026 —
et le coffre de mots de passe `vaultwarden` (VM 105, déployé le 18/09/2026).

Ce cluster est l'un des **deux datacenters** de l'architecture HDS ; l'autre,
le **DC TELLIS** (production imagerie), est opéré par un prestataire — vue
d'ensemble dans [12-architecture-hds.md](12-architecture-hds.md), inventaire
dans [13-tellis.md](13-tellis.md).

---

## Les 5 serveurs

| | **pve1** | **pve2** | **pve3** | **pve4** | **pve5** |
|---|---|---|---|---|---|
| Datacentre | GRA4 | GRA4 | GRA4 | **GRA3** | **GRA3** |
| **Nom OVH** | `ns3245256.ip-91-134-84.eu` | `ns3245278.ip-51-68-240.eu` | `ns3258339.ip-51-68-240.eu` | `ns3240079.ip-79-137-100.eu` | `ns3240118.ip-79-137-100.eu` |
| **FQDN** | `pve1.infra.teleimagerie.net` | `pve2.infra…` | `pve3.infra…` | `pve4.infra…` | `pve5.infra…` |
| **IP publique** | `91.134.84.222` | `51.68.240.48` | `51.68.240.191` | `79.137.100.184` | `79.137.100.185` |
| Corosync (VLAN 100) | `10.100.0.11` | `10.100.0.12` | `10.100.0.13` | `10.100.0.14` | `10.100.0.15` |
| Ceph (VLAN 200) | `10.200.0.11` | `10.200.0.12` | `10.200.0.13` | `10.200.0.14` | `10.200.0.15` |
| VM (VLAN 300) | `10.30.0.11` | `10.30.0.12` | `10.30.0.13` | `10.30.0.14` | `10.30.0.15` |
| RAM | 64 Go | 64 Go | 64 Go | **32 Go** | **32 Go** |

Repère : **le dernier octet vRack = le numéro du nœud**. pve1 est le seul en
`91.134.84.x`, pve2 et pve3 partagent `51.68.240.x` (c'est là qu'on se trompe),
pve4 et pve5 partagent `79.137.100.x` et ne diffèrent que par `.184`/`.185`.
pve4 et pve5 sont les **ex-dédiés de staging** réinstallés le 15/09/2026
([20-mytim-staging.md](20-mytim-staging.md)).

Détail complet (NIC, OSD, ID Corosync) dans
[01-architecture.md](01-architecture.md#inventaire-des-nœuds--table-de-correspondance).

## Accès

| | |
|---|---|
| **VPN obligatoire** | depuis le 01/09/2026, l'administration n'est plus joignable depuis Internet. Deux portes : **VPN nomade wg0** (le nom `pveN.infra` résout alors en `10.40.0.2/.3/.4/.5/.6`) ou **tailnet** (`100.72.0.6` pve1, `.5` pve2, `.7` pve3, `.8` pve4, `.9` pve5) — [04-securite.md](04-securite.md#accès-dadministration-par-vpn-31082026) |
| Interface web | `https://pve{1..5}.infra.teleimagerie.net:8006` (VPN monté) |
| Compte | `matt` / realm *Proxmox VE authentication server* (**pas** `matt@pve` dans le champ nom) |
| Second facteur | TOTP obligatoire sur `matt@pve` et `root@pam`, 10 clés de secours chacun |
| SSH | `ssh root@pve1.infra.teleimagerie.net` (clé `~/.ssh/id_ed25519` uniquement) |
| SSO | realm *keycloak* dans la liste déroulante (`auth.teleimagerie.net`, TOTP porté par l'IdP) — le realm PVE reste la voie de secours ([16-keycloak.md](16-keycloak.md)) |

Le certificat est un Let's Encrypt valide : aucun avertissement navigateur attendu.
Si vous en voyez un, c'est le signe d'un problème — ne cliquez pas au travers.

---

## Sommaire

| Fichier | Contenu |
|---|---|
| [01-architecture.md](01-architecture.md) | Matériel, réseau, disques, plan d'adressage |
| [02-deploiement.md](02-deploiement.md) | Journal de ce qui a été fait, et pourquoi |
| [03-exploitation.md](03-exploitation.md) | Diagnostic, pannes disque et nœud, procédures courantes |
| [04-securite.md](04-securite.md) | Durcissement, TOTP, firewall, emplacement des secrets |
| [05-tests-ha.md](05-tests-ha.md) | Mesures réelles de bascule (chiffres, pas estimations) |
| [06-reste-a-faire.md](06-reste-a-faire.md) | Points ouverts : sauvegardes, VPN site-à-site, DC TELLIS, authentification |
| [07-pieges.md](07-pieges.md) | **Les pièges rencontrés et leur résolution** (numérotés pour les renvois des fiches) |
| [08-opnsense.md](08-opnsense.md) | Pare-feu OPNsense : WAN, filtrage, WireGuard, accès |
| [09-proxy-tim.md](09-proxy-tim.md) | Reverse proxy nginx : aiguillage SNI, relais TLS TSplus, certificats |
| [10-sauvegardes.md](10-sauvegardes.md) | **NAS-HA, Proxmox Backup Server, restauration** |
| [11-headscale.md](11-headscale.md) | Plan de contrôle VPN (tailnet) : passerelles DICOM, ACLs, DERP, enrôlement |
| [12-architecture-hds.md](12-architecture-hds.md) | Vue d'ensemble HDS : les deux datacenters, interconnexions, flux, DNS |
| [13-tellis.md](13-tellis.md) | **DC TELLIS (site distant)** : inventaire, pfSense, tunnels WireGuard, checklist de collecte |
| [14-noms-de-domaine.md](14-noms-de-domaine.md) | **Les 6 zones DNS** : registrars, échéances, serveurs autoritaires, inventaire des noms, reverse, résolution interne |
| [15-pacs-secours.md](15-pacs-secours.md) | PACS de secours `pacs03` : bare-metal Windows GRA3, patte vRack `10.40.0.40`, tunnel direct TELLIS |
| [16-keycloak.md](16-keycloak.md) | **Authentification centralisée Keycloak** : realm `tim`, raccordements OIDC (PVE, PBS, headscale, Odoo, MyTIM prod TIM depuis le 01/09), brokering Google Workspace, SMTP Mailjet, split-horizon `auth.*`, identités par application, candidats SSO |
| [17-zabbix.md](17-zabbix.md) | **Supervision Zabbix** : migration VPS → CT 204 (audit, incident du 28/08, plomberie) + supervision des sauvegardes (échec **et absence**, 30/08) |
| [18-odoo.md](18-odoo.md) | **ERP Odoo** : migration VPS → VM 101 terminée le 29/08 (récit de bascule chiffré, sauvegardes 3 niveaux, restauration testée) |
| [20-mytim-staging.md](20-mytim-staging.md) | **Pré-productions MyTIM / MyISOTEAM** : VM 103/104 derrière proxy-tim (TLS terminé au proxy, wildcards DNS-01), migrées des dédiés OVH le 14/09 — sans HA, sauvegarde hebdo une copie, récit de bascule, retour arrière |
| [21-vaultwarden.md](21-vaultwarden.md) | **Coffre de mots de passe Vaultwarden** (VM 105, `vault.teleimagerie.net`) : déployé le 18/09 — SSO Keycloak obligatoire (OIDC, Google Workspace via le broker existant, pas de SAML), comptes auto-créés au premier login SSO, dump 01:15, HA, Zabbix |
| [19-carte-reseau.md](19-carte-reseau.md) | **Carte réseau régénérable** : `make carte` interroge l'API Proxmox, confronte aux intentions de `topologie.yml` et réécrit le schéma — les écarts aux règles sont peints en rouge sur la carte |
| `scripts/` | `enroll-totp.py` (enrôlement TOTP sûr), `ovh-dns.py` (enregistrements A `pve{1..5}.infra` via API OVH), `ovh-nasha.py` (partitions et ACL du NAS-HA, cinq nœuds), `unbound-overrides-pve.py` (overrides Unbound `pveN.infra → patte VLAN 400` des cinq hyperviseurs, idempotent, à exécuter sur OPNsense), `stun-tailnode.py` (sonde STUN headscale), `inventaire-windows.ps1` (relevé matériel/logiciel d'un serveur Windows, sortie Markdown prête pour une fiche — passe aussi sous WDAC/*ConstrainedLanguage*), `parefeu-pacs03.ps1` (verrouillage pare-feu de pacs03, rejouable après réinstallation), `installer-zabbix-agent-windows.ps1` (agent Zabbix 2 en mode actif sur un serveur Windows : MSI signé vérifié, configuration, règle pare-feu, récupération du service — rejouable), `zabbix-provision-venus.py` (hôtes, sondes et déclencheurs des trois serveurs RIS VENUS, idempotent), `zabbix-provision-dicomproxy.py` (hôte ProxyVia sans agent : ICMP + sondes TCP 9104/8443 depuis le CT 204 ; la sonde 5432 est retirée depuis que Siemens a fermé le port — idempotent), `zabbix-provision-timwfmcore.py` (supervision applicative de la Vue PACS : sondes TCP, services critiques en High, fraîcheur RMAN, plantages, contrôles internes du PACS — idempotent), `zabbix-provision-syngo.py` (deux syngo.via : temporisation à 15 min des alertes de disponibilité, les serveurs redémarrant chaque dimanche ~02:30, et filtre des interfaces réseau sur `ifAlias` pour ne garder que les ports HPE 10G — idempotent), `installer-openssh-windows.ps1` (OpenSSH serveur par clé sur un serveur Windows : installation native ou MSI, clé administrateur avec ACL, mot de passe interdit, port 22 limité au VPN nomade — rejouable), `controle-liens.py` (ancres des fiches : signale les liens morts et le titre le plus proche — `make liens`), `genere-carte.py` (carte réseau depuis l'API Proxmox — voir `make aide`), `bascule-staging.py` (bascule DNS des pré-productions, deux zones et huit enregistrements : `status|ttl60|switch|revert|ttl3600`), `deploy-staging-teleimagerie.sh` / `deploy-staging-isoteam.sh` (hooks acme.sh des wildcards `*.staging.*` vers le CT 201), `unbound-overrides-staging.py` (overrides split-horizon des noms staging sur OPNsense, idempotent), `dns-vaultwarden.py` (création de `vault.teleimagerie.net` → proxy-tim : `status|create|ttl3600`), `unbound-override-vaultwarden.py` (override split-horizon de `vault.*`, idempotent), `zabbix-provision-vaultwarden.py` (hôte agent + certificat de la VM 105, macro mémoire d'emblée — idempotent), `zabbix-provision-staging.py` (hôtes agents et certificats des VM 103/104 ; faux signal mémoire hyperviseur des VM sans balloon neutralisé par macro, High « mémoire réelle > 90 % pendant 1 h » côté agent — idempotent) |
| `topologie.yml` | Intentions d'architecture — zones, rôles, cloisonnements, règles vérifiées à chaque génération de la carte. **Seul fichier de la carte à éditer à la main** |
| `configs/` | Copie des configurations en production, pour comparaison ou restauration |

Si vous reprenez ce dossier après une longue interruption, lisez
[07-pieges.md](07-pieges.md) en premier : il contient ce qui a réellement coûté
du temps.

Aucun secret ne figure dans ces fichiers — ils vivent tous dans `/etc/pve/priv/`
sur le cluster. Voir [04-securite.md](04-securite.md#secrets--où-ils-vivent).

---

## État en une page

```
tim-cluster  ·  5 nœuds (GRA4 ×3 + GRA3 ×2 depuis le 15/09)  ·  quorum 3/5
                         Corosync 2 anneaux · 8 liens
Proxmox VE 9.2.20        (Debian 13 Trixie, noyau 7.0.14-17 sur les 5 nœuds)
Ceph Tentacle 20.2.4     10 OSD · 5 MON · 7,2 Tio bruts · size 4 / min_size 2
                         → MAX AVAIL 1,5 Tio · cephx aes256k seul (migration
                         terminée le 15/09 au soir)
Réseau                   vRack 25 Gb/s · bridge VLAN-aware · jumbo MTU 9000 validé
                         GRA3 ↔ GRA4 compris (0,15-0,3 ms)
                         VLAN 100 Corosync · 200 Ceph · 300 infra · 400 LAN VM
                         non tagué = bloc public 57.130.34.120/29
HA                       8 ressources : vm:100 à vm:102, vm:105 · ct:201 à ct:204
                         watchdog softdog · fencing testé en conditions réelles
                         perte de GRA3 (2 nœuds) mesurée le 15/09 : 0 PG bloqué
Sécurité                 firewall actif · SSH par clé · fail2ban · TLS · TOTP
                         admin VPN-only depuis le 01/09 (8006/22/3128 fermés
                         à Internet) · 2 portes : wg0 + tailnet · KVM OVH testé
                         sur les 5 nœuds
Pare-feu VM              OPNsense 26.1.6 (VM 100) · WAN 57.130.34.121
                         WireGuard wg0 nomades · wg2 site-à-site TELLIS (51822)
Site distant             DC TELLIS (prestataire) · pfSense 37.61.243.246
                         wg2 · relais TLS syngo-via → TSplus · Syngo Via ×2 et
                         TSplus inventoriés et supervisés le 02/09 (syngo en
                         SNMP, agent refusé par WDAC ; TSplus : ni correctif ni
                         sauvegarde depuis 2025, pas de 2FA)
                         RIS VENUS ×3 (Softway, VM Proxmox du site) : SSH par
                         clé et inventaire le 04/09, supervisés le 05/09
                         (agent actif) ; .64 = SFTP de dépôt des 7 sites ;
                         .65 = base isotim ⛔ SANS SAUVEGARDE
                         ProxyVia (dicomproxy, .103/.58) : répartiteur DICOM
                         Siemens, inventorié et supervisé le 09/09 ; répartit
                         en round-robin sur les 2 Syngo Via ; ⚠️ base patients
                         PostgreSQL ouverte sans mot de passe (ticket Siemens)
                         Vue PACS TIMWFMCORE (.52) : audité le 11/09 et
                         supervisé jusqu'à l'applicatif (DICOM, Oracle, RMAN,
                         plantages) ; ⚠️ svstream plante 3 à 56×/j (svdser :
                         normal selon Philips, auto-terminaison),
                         G: à 26 % libre, tablespace à 6,5 % (Philips/TELLIS)
                         Vue Motion (TIMVUEEXPLORER .53) : frontal web Vue
                         12.2.8 lisant TIMWFMCORE, SSH par clé et inventaire
                         le 11/09 ; pare-feu Windows sans effet, AnyDesk actif
PACS de secours          pacs03 (bare-metal Windows, GRA3) · vRack VLAN 400
                         10.40.0.40 · backend pacs-secours servi en privé
VPN DICOM                headscale 0.29.3 (CT 202) · tailnet 100.72.0.0/16
                         DERP embarqué · data plane testé continu pendant bascule
Sauvegardes              PBS 4.2.5 (VM 102) · NAS-HA zpool-130899 à Roubaix
                         quotidien 02:00 sauf VM 102 · rétention 7j/4s/6m
                         restauration testée et mesurée
Authentification         Keycloak 26.7.2 (CT 203) · auth.teleimagerie.net
                         realm tim · TOTP obligatoire · broker Google Workspace
                         OIDC : PVE, PBS, headscale, Odoo, MyTIM (prod TIM 01/09)
Supervision              Zabbix 7.0 (CT 204) · zabbix.teleimagerie.net
                         migré du VPS le 29/08 · supervise aussi le cluster :
                         quorum, Ceph, nearfull 85 %, 7 invités (API + agents),
                         certificats, sauvegardes (échec + absence, vzdump/PBS)
                         · dashboard « Cluster PVE » · mail testé
Notifications            plus aucun mail de succès depuis le 30/08 · Zabbix
                         alerte (High) · filet : erreurs PVE/PBS via Mailjet
ERP                      Odoo 17 (VM 101, Ubuntu 24.04 + Docker) · odoo.teleimagerie.net
                         en production depuis le 29/08 · VPS résilié le 30/08
Coffre de mots de passe  Vaultwarden 1.37.2 (VM 105, Ubuntu 24.04 + Docker)
                         vault.teleimagerie.net · SSO Keycloak obligatoire
                         (OIDC, broker Google) · déployé le 18/09
```

**Capacité réellement exploitable** : ~1,5 Tio de disque Ceph (seuil `nearfull` à
85 %, 4 répliques), **700 Gio de plus sur le NAS** pour le stockage froid, et
**~140 Go de RAM VM cumulée** sur tout le cluster si l'on veut pouvoir absorber la
perte d'un nœud. Voir [01-architecture.md](01-architecture.md#dimensionnement).

---

## Les trois choses à ne pas oublier

1. **Les sauvegardes existent depuis le 13/08/2026, et une sauvegarde se vérifie.**
   Ceph protège d'une panne matérielle, pas d'une suppression, d'un ransomware ou
   d'une corruption applicative : les trois répliques sont détruites ensemble.
   C'est PBS qui couvre ce risque — encore faut-il que les tâches passent.
   Refaire une restauration de test après toute évolution majeure.
   Voir [10-sauvegardes.md](10-sauvegardes.md).

2. **Cinq nœuds sur deux datacentres, quatre répliques.** Depuis le 15/09/2026, la
   perte de **deux nœuds quelconques** (GRA3 entier compris) laisse deux répliques
   par PG : les I/O continuent, le quorum PVE (3/5) et MON (3/5) tiennent. Ceph
   se répare seul après la perte d'un nœud (il reste quatre hôtes pour quatre
   répliques). La perte de GRA4 (trois nœuds) reste fatale, comme avant.

3. **La clé SSH `~/.ssh/id_ed25519` ne suffit plus seule.** Elle reste
   indispensable (désactiver un TOTP perdu, réparer un firewall), mais depuis la
   fermeture du 01/09/2026 il faut **une porte VPN pour l'utiliser** : wg0, ou
   le tailnet (`ssh root@100.72.0.6`), qui a l'avantage de ne pas dépendre
   d'OPNsense. **L'issue de secours ultime est désormais la console KVM/IPMI
   OVH** — testée et validée le 31/08/2026 sur pve1-3 et le 15/09/2026 sur
   pve4/5, procédure et identifiants dans
   [04-securite.md](04-securite.md#console-kvmipmi-ovh--laccès-de-dernier-recours).
