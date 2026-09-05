# Cluster Proxmox `tim-cluster` — documentation

Cluster de virtualisation haute disponibilité à 3 nœuds, stockage Ceph répliqué
synchrone, hébergé chez OVHcloud (datacenter GRA4).

**Déployé le 11 août 2026.** État : **en production**. Sept machines y tournent :
le pare-feu OPNsense (VM 100), le reverse proxy `proxy-tim` (CT 201), le
serveur de sauvegarde PBS (VM 102), le plan de contrôle VPN `headscale`
(CT 202, pour les passerelles DICOM des sites distants), le serveur
d'authentification centralisée `keycloak` (CT 203, SSO OpenID Connect),
la supervision `zabbix` (CT 204) et l'ERP `odoo` (VM 101).

Ce cluster est l'un des **deux datacenters** de l'architecture HDS ; l'autre,
le **DC TELLIS** (production imagerie), est opéré par un prestataire — vue
d'ensemble dans [12-architecture-hds.md](12-architecture-hds.md), inventaire
dans [13-tellis.md](13-tellis.md).

---

## Les 3 serveurs

| | **pve1** | **pve2** | **pve3** |
|---|---|---|---|
| **Nom OVH** | `ns3245256.ip-91-134-84.eu` | `ns3245278.ip-51-68-240.eu` | `ns3258339.ip-51-68-240.eu` |
| **FQDN** | `pve1.infra.teleimagerie.net` | `pve2.infra.teleimagerie.net` | `pve3.infra.teleimagerie.net` |
| **IP publique** | `91.134.84.222` | `51.68.240.48` | `51.68.240.191` |
| Corosync (VLAN 100) | `10.100.0.11` | `10.100.0.12` | `10.100.0.13` |
| Ceph (VLAN 200) | `10.200.0.11` | `10.200.0.12` | `10.200.0.13` |
| VM (VLAN 300) | `10.30.0.11` | `10.30.0.12` | `10.30.0.13` |

Repère : **le dernier octet vRack = le numéro du nœud**. Et pve1 est le seul en
`91.134.84.x` — pve2 et pve3 partagent `51.68.240.x`, c'est là qu'on se trompe.

Détail complet (NIC, OSD, ID Corosync) dans
[01-architecture.md](01-architecture.md#inventaire-des-nœuds--table-de-correspondance).

## Accès

| | |
|---|---|
| **VPN obligatoire** | depuis le 01/09/2026, l'administration n'est plus joignable depuis Internet. Deux portes : **VPN nomade wg0** (le nom `pveN.infra` résout alors en `10.40.0.2/.3/.4`) ou **tailnet** (`100.72.0.6` pve1, `.5` pve2, `.7` pve3) — [04-securite.md](04-securite.md#accès-dadministration-par-vpn-31082026) |
| Interface web | `https://pve{1,2,3}.infra.teleimagerie.net:8006` (VPN monté) |
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
| [06-reste-a-faire.md](06-reste-a-faire.md) | Abonnement, supervision, IP publiques VM, points ouverts du VPN |
| [07-pieges.md](07-pieges.md) | **Les 37 pièges rencontrés et leur résolution** |
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
| [19-carte-reseau.md](19-carte-reseau.md) | **Carte réseau régénérable** : `make carte` interroge l'API Proxmox, confronte aux intentions de `topologie.yml` et réécrit le schéma — les écarts aux règles sont peints en rouge sur la carte |
| [20-mytim.md](20-mytim.md) | **MyTIM sur le cluster** : 📋 plan validé le 31/08 — l'app d'abord (VPS → VM 104), MySQL ensuite (clouddb OVH → VM 103), exécution non commencée |
| `scripts/` | `enroll-totp.py` (enrôlement TOTP sûr), `ovh-dns.py` (DNS via API OVH), `ovh-nasha.py` (partitions et ACL du NAS-HA), `stun-tailnode.py` (sonde STUN headscale), `inventaire-windows.ps1` (relevé matériel/logiciel d'un serveur Windows, sortie Markdown prête pour une fiche — passe aussi sous WDAC/*ConstrainedLanguage*), `parefeu-pacs03.ps1` (verrouillage pare-feu de pacs03, rejouable après réinstallation), `installer-zabbix-agent-windows.ps1` (agent Zabbix 2 en mode actif sur un serveur Windows : MSI signé vérifié, configuration, règle pare-feu, récupération du service — rejouable), `zabbix-provision-venus.py` (hôtes, sondes et déclencheurs des trois serveurs RIS VENUS, idempotent), `installer-openssh-windows.ps1` (OpenSSH serveur par clé sur un serveur Windows : installation native ou MSI, clé administrateur avec ACL, mot de passe interdit, port 22 limité au VPN nomade — rejouable), `genere-carte.py` (carte réseau depuis l'API Proxmox — voir `make aide`) |
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
tim-cluster  ·  3 nœuds  ·  quorum 2/3  ·  Corosync 2 anneaux
Proxmox VE 9.2.10        (Debian 13 Trixie, noyau 7.0.14-11-pve)
Ceph Tentacle 20.2.2     HEALTH_OK · 6 OSD · 4,3 Tio bruts → 1,4 Tio utilisables
Réseau                   vRack 25 Gb/s · bridge VLAN-aware · jumbo MTU 9000 validé
                         VLAN 100 Corosync · 200 Ceph · 300 infra · 400 LAN VM
                         non tagué = bloc public 57.130.34.120/29
HA                       7 ressources : vm:100 à vm:102 · ct:201 à ct:204
                         watchdog softdog · fencing testé en conditions réelles
Sécurité                 firewall actif · SSH par clé · fail2ban · TLS · TOTP
                         admin VPN-only depuis le 01/09 (8006/22/3128 fermés
                         à Internet) · 2 portes : wg0 + tailnet · KVM OVH testé
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
```

**Capacité réellement exploitable** : ~1,36 Tio de disque Ceph (seuil `nearfull` à
85 %), **700 Gio de plus sur le NAS** pour le stockage froid, et **~100 Go de RAM
VM cumulée** sur tout le cluster si l'on veut pouvoir absorber la perte d'un nœud.
Voir [01-architecture.md](01-architecture.md#dimensionnement).

---

## Les trois choses à ne pas oublier

1. **Les sauvegardes existent depuis le 13/08/2026, et une sauvegarde se vérifie.**
   Ceph protège d'une panne matérielle, pas d'une suppression, d'un ransomware ou
   d'une corruption applicative : les trois répliques sont détruites ensemble.
   C'est PBS qui couvre ce risque — encore faut-il que les tâches passent.
   Refaire une restauration de test après toute évolution majeure.
   Voir [10-sauvegardes.md](10-sauvegardes.md).

2. **Avec 3 nœuds, Ceph ne se répare pas seul.** La perte d'un nœud laisse le cluster
   en `HEALTH_WARN` dégradé — les VM tournent, mais aucune 3ᵉ réplique n'est recréée
   faute d'un 4ᵉ hôte. C'est normal, pas une avarie.

3. **La clé SSH `~/.ssh/id_ed25519` ne suffit plus seule.** Elle reste
   indispensable (désactiver un TOTP perdu, réparer un firewall), mais depuis la
   fermeture du 01/09/2026 il faut **une porte VPN pour l'utiliser** : wg0, ou
   le tailnet (`ssh root@100.72.0.6`), qui a l'avantage de ne pas dépendre
   d'OPNsense. **L'issue de secours ultime est désormais la console KVM/IPMI
   OVH** — testée et validée le 31/08/2026, procédure et identifiants dans
   [04-securite.md](04-securite.md#console-kvmipmi-ovh--laccès-de-dernier-recours).
