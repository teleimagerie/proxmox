# Reste à faire

Par ordre décroissant d'importance. Ne figure ici que ce qui reste ouvert : ce
qui a été fait est consigné dans la fiche thématique et dans le journal git.

---

## 1. Sauvegardes — ✅ TRAITÉ le 13/08/2026

Proxmox Backup Server 4.2.5 en VM 102, datastore sur le NAS-HA `zpool-130899`
(Roubaix), sauvegarde quotidienne de tout le cluster à 02:00 (VM 102 exclue,
couverte par le job hebdomadaire vers `nas-vm`), rétention
7 jours / 4 semaines / 6 mois, restauration testée et mesurée.

Tout le détail dans [10-sauvegardes.md](10-sauvegardes.md).

Ce qui reste ouvert sur le sujet :

- **chiffrement client PBS** non activé — arbitrage entre confidentialité et
  risque de perte de clé, à reprendre avec séquestre hors cluster ;
- **une seule copie** des sauvegardes, atténuée par les snapshots ZFS d'OVH et
  l'option de réplication distante ;
- `backup-opnsense.timer` ne tourne que sur **pve1**.

---

## 2. Bascule DNS vers `proxy-tim` — ✅ TRAITÉ le 29/08/2026

`pacs-secours.teleimagerie.net`, `syngo.teleimagerie.net` et `syngo.isoteam.mn`
pointent sur `57.130.34.122` depuis le 26/08/2026 ; l'ancien VPS est résilié
depuis le 29/08/2026. Détail dans
[09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026).

Seul point encore ouvert : **`syngo-via.*` restent en direct sur TSplus**
(`37.61.243.246`) — les faire passer par le relais TLS du proxy est une
décision séparée, non prise ; le relais ACME du port 80 vers TSplus est prêt
depuis le 24/08 si elle se prend un jour.

---

## 4. Supervision — ✅ TRAITÉ le 29/08/2026

**Le Zabbix d'entreprise tourne dans le cluster** (CT 204, migré le 29/08 —
[17-zabbix.md](17-zabbix.md)) **et supervise le cluster lui-même depuis le
même jour** : quorum, nœuds, Ceph (`HEALTH_*`, OSD), stockages avec seuil
nearfull 85 %, les 7 VM/CT (vue hyperviseur **et** agents internes, OPNsense
compris), certificats TLS — tableau de bord « Cluster PVE », alertes
High/Disaster par mail vers support@ + mcapon@, chaîne testée en réel.
Détail, seuils et pièges :
[17-zabbix.md §Supervision du cluster](17-zabbix.md#supervision-du-cluster--depuis-le-29082026).

Les notifications mail Proxmox ne partent plus qu'en cas de problème depuis le
30/08/2026 : matchers `erreurs-mailjet` (warning/error/unknown → Mailjet) sur
PVE et PBS, builtin `default-matcher` désactivé — plus aucun mail de succès.
Zabbix est le canal principal (échec **et absence** de sauvegarde,
[17-zabbix.md](17-zabbix.md#supervision-des-sauvegardes--depuis-le-30082026)) ;
le mail direct n'est que le filet si Zabbix tombe.

---

## 7. Divers

- **pacs03** : patché, redémarré et allégé le 30/08/2026 (précédent
  correctif : 20/02/2024), pare-feu Windows verrouillé et surface publique
  scannée le même jour. Reste : revérifier fin septembre que le canal de mise
  à jour continue de fonctionner — et noter que **hors cluster, hors PBS : sa
  seule sauvegarde est la tâche Oracle** —
  [15-pacs-secours.md](15-pacs-secours.md#reste-à-faire).
- **Le matériel livré ne correspond pas au devis demandé** : la demande du
  05/08/2026 portait sur 128 Go de RAM et 2 × 1,92 To de NVMe supplémentaires par
  serveur ; les machines ont 64 Go et 2 disques. À vérifier auprès d'OVH — c'est
  la voie la plus directe pour agrandir *Ceph*, là où le NAS n'apporte qu'un
  stockage lent.
- **Faire le ménage dans les tokens OVH** : deux clés antérieures ont été révoquées
  le 11/08/2026 et n'ont plus d'usage. **Deux applications doivent subsister** :
  `proxmox` (AK `0357cf99f1ed0548`), qui porte le renouvellement TLS, et
  `Proxmox Nas-HA` (AK `e13e89cf414da916`), qui pilote les partitions et l'ACL du
  NAS depuis le 13/08/2026. Supprimer l'une ou l'autre casse silencieusement une
  fonction : ne pas les confondre.
- **Rejouer les tests HA** après toute mise à jour majeure
  ([05-tests-ha.md](05-tests-ha.md#rejouer-les-tests)).

---

## 8. VPN site-à-site — points ouverts

Le tunnel vers le pfSense TELLIS ([13-tellis.md](13-tellis.md)) est
opérationnel depuis le 14/08/2026
([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)), et dans les
deux sens depuis le 25/08/2026 : la patte `.59` du pfSense (interface
`OPT1_TIM`) n'avait aucune règle `pass`, deux règles ont été posées
([13-tellis.md](13-tellis.md#règles-posées-sur-opt1_tim-le-25082026-sens-tellis--dc-ovh))
et validées (ping prod01 → pacs03 en 17–23 ms, session TCP complète, MSS/MTU
1420 compris). Ce qui n'a pas été fait ou pas été prouvé :

- ⚠️ **relever le contenu de l'alias `DC_OVH_TIM`** du pfSense
  (vraisemblablement `10.40.0.0/24` — inclut-il `10.90.0.0/24` ?) ;
  `SRV_TIM_WFMCORE` est identifié depuis le 29/08/2026 (la Vue PACS
  `TIMWFMCORE`, `192.168.101.52`).
- **décider de la persistance des routes de test** (`10.40.0.0/24 via .59` sur
  prod01 et les `/32` ActiveStore sur pacs03 — toutes volatiles, un reboot les
  efface), en retenant que **les deux côtés vont par paire** : si la `/32` de
  pacs03 disparaît (reboot) alors que prod01 garde sa route, les réponses de
  pacs03 partiront dans le tunnel direct avec la source `10.40.0.40` et le
  pfSense les jettera (cryptokey routing) — poser ou retirer **les deux
  ensemble**. Constat du 11/09/2026 : depuis pacs03, prod01 (`.54`) ne répond
  plus au SYN sur le port 22 alors que `.52`, dont les routes sont
  persistantes, répond — l'une au moins des deux routes volatiles a disparu.
  Le point est donc à trancher, pas à constater.
- **restreindre les règles « tout protocole / tout port »** de `OPT1_TIM` aux
  hôtes et ports réellement nécessaires.
- **La segmentation n'a pas été éprouvée depuis TELLIS.** Les règles
  bloquant Corosync, Ceph et `10.30.0.0/24` sont bien chargées dans `pf`, ce qui
  a été vérifié — mais une règle chargée n'est pas une règle prouvée.
- **Le comportement du tunnel pendant une bascule HA de la VM 100 n'est pas
  mesuré.** Le keepalive de 25 s devrait le rétablir en moins d'une minute après
  les ~2 min de relance ; c'est une déduction, pas un chiffre.
- **Routes retour côté TELLIS** : seuls les serveurs dont la passerelle est le
  second pfSense (`.62`, bloc production) en ont besoin ; VENUS (`.254`) et
  Syngo (`.110`) répondent déjà au pfSense principal — tranché le 05/09/2026,
  `10.40.0.0/24` ↔ `192.168.111.x` fonctionne dans les deux sens
  ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026)).
  `192.168.101.52` en a pour `10.40.0.0/24`, `10.90.0.0/24`, `172.32.0.0/24`
  et `172.31.0.0/24`, `.53` pour `172.31.0.0/24`. Le poste d'admin joint
  TELLIS par le `tun_wg0` du pfSense (`172.31.0.3`), pas par `wg2`
  ([13-tellis.md](13-tellis.md#tun_wg0--vpn-nomades-du-site)), et a besoin de
  la même route : sans elle, RDP et SSH vers `.52`/`.53` ouvraient le port puis
  se taisaient — corrigé le 11/09/2026
  ([13-tellis.md](13-tellis.md#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)). Reste : les autres serveurs du bloc
  production (`.51`, `.55`, `.56`, `.57`) s'il faut un jour les joindre, et
  demander au prestataire s'il préfère autoriser l'asymétrie sur `.62`.
- **Le tunnel direct « DC-TELLIS-PARTENAIRES » (`tun_wg1`) entre pacs03 et le
  pfSense TELLIS doit perdurer** (décision du 25/08/2026) : c'est lui qui route
  `192.168.101.48/28` et `.96/28` vers le serveur, et aucune route équivalente
  n'a été posée via OPNsense — les doubler créerait un conflit
  ([15-pacs-secours.md](15-pacs-secours.md)). Jalon mesuré le 25/08/2026 :
  pacs03 joint le pfSense (`172.33.0.1`) par wg2 en 15 ms (route `/32` de test
  temporaire). Restent à prouver par `wg2` : un hôte TELLIS de bout en bout
  dans les deux sens, et la tenue du MTU 1420 pour un flux de réplication.

### ⚠️ Une clé privée a été exposée

Les 13-14/08/2026, lors de l'extraction des configurations, la clé privée
WireGuard du tunnel `tun_wg0` du pfSense TELLIS — **le VPN nomades du DC
TELLIS, en production** — a transité en clair dans un historique de terminal.
Elle n'est pas sous notre contrôle : c'est au prestataire TELLIS d'arbitrer, et
il doit en être informé. Tant qu'elle n'est pas régénérée, quiconque a eu accès
à cet historique peut usurper le serveur VPN nomades du DC TELLIS.

---

## 9. DC TELLIS — collecte et vérification de l'inventaire

Le DC TELLIS a sa fiche de référence ([13-tellis.md](13-tellis.md)) : neuf
serveurs y ont été contrôlés sur machine entre le 29/08 et le 11/09/2026
(TIMWFMCORE, les deux syngo.via, TSplus, les trois VENUS, ProxyVia, Vue Motion). La liste
détaillée de ce qu'il reste à collecter est dans
[13-tellis.md](13-tellis.md#checklist-de-collecte) — ne pas la dupliquer ici.
Les trois points saillants :

- **l'export `config.xml` des deux pfSense** (`192.168.101.59` et `.62`) —
  règles, NAT, WireGuard ; à conserver hors dépôt, il contient des clés privées ;
- **le contenu de la VM `prod01`** (`192.168.101.54`) — personne ne sait
  précisément ce qui y tourne ;
- **informer le prestataire de l'exposition de la clé `tun_wg0`** et suivre sa
  rotation (voir le § 8 ci-dessus).

### ⛔ La base de production du RIS VENUS n'est pas sauvegardée (04/09/2026)

Constaté à l'inventaire des trois serveurs VENUS
([13-tellis.md](13-tellis.md#tim-venus3-db-65--la-base-partagée-inventorié-le-04092026)) :
la base **`isotim` (≈ 2,1 Go)** de `TIM-VENUS3-DB` (`192.168.111.65`), qu'appellent
en permanence les deux serveurs applicatifs, **n'a aucune sauvegarde**. Le volume
`E:` nommé « BACKUP BDD », dimensionné à 750 Go, est **vide (0 fichier)** ; il
n'existe **aucune tâche planifiée** de sauvegarde ; les seuls exports retrouvés
sont manuels et anciens (`isotim_backup.sql` de 883 Mo du **10/12/2025**, dans le
dossier `Downloads` d'un compte d'administration). Les données sont de surcroît
dans `C:\Program Files\MariaDB 11.8\data`, le chemin d'installation par défaut,
alors que 750 Go dédiés (`D:`) sont vides.

À porter **à Softway Medical** (c'est son applicatif, `mariadb-dump` planifié vers
`E:` au minimum) **et au prestataire TELLIS** : aucune sauvegarde n'étant visible
*dans* les VM, la seule protection possible est celle de l'hyperviseur Proxmox du
site — **personne ne nous a confirmé qu'elle existe**. Tant que ce point n'est pas
levé, une perte de la VM fait perdre le RIS. Deux points voisins, moins graves
mais du même inventaire : `D:` de `TIM-VENUS1-AP` n'a plus que **4,8 Go libres**
sur 200, et les trois serveurs sont **sans correctif Windows** (avril 2023 pour
deux d'entre eux).

Depuis le 05/09/2026 les trois sont **supervisés** ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026)) :
le volume `D:` est sous déclencheur High qui part en mail, et la mémoire de
`TIM-VENUS3-DB` (8 Go) est en alerte permanente. **L'absence de sauvegarde,
elle, reste invisible de Zabbix** — il n'y a rien à mesurer tant qu'aucune
sauvegarde n'existe. Le jour où elle sera en place, surveiller l'âge du dernier
fichier de `E:` fermera la boucle.

### ⚠️ ProxyVia (`dicomproxy`) — cinq points partis en ticket Siemens (09/09/2026)

Constaté à l'inventaire du répartiteur DICOM
([13-tellis.md](13-tellis.md#dicomproxy-103--proxyvia-le-répartiteur-dicom-inventorié-le-09092026)).
C'est une **appliance gérée par Siemens** : on ne touche pas à sa configuration,
**les cinq points sont adressés par un ticket éditeur** (contenu rédigé, ouverture
du ticket à la main de TIM). Par priorité :

1. **⛔ Base PostgreSQL `registry` joignable depuis le LAN sans mot de passe.**
   Le service écoute `0.0.0.0:5432` et, depuis le réseau via `192.168.101.103`,
   une connexion `psql` aboutit **sans authentification** pour le compte applicatif
   `dicom` **et pour le superutilisateur `postgres`** (vérifié le 09/09). La table
   `location` contient des **identités patients** (nom, date de naissance, sexe,
   numéro d'accession). Toute machine du bloc `192.168.101.96/28` peut lire et
   écrire cette base. Demander à Siemens la configuration supportée (écoute sur
   `localhost` et/ou mot de passe) — le proxy accède à la base en `localhost`.
2. **Horloge en retard d'environ 10 minutes.** `System clock synchronized: no` ;
   NTP actif mais ne résout plus `*.pool.ntp.org`, les DNS déclarés
   (`192.168.150.1`, `192.168.250.1`) étant injoignables. Horodatage DICOM et
   journaux qui dérivent.
3. **Redémarrage en attente** depuis le 05/08/2026 (noyau) et **439 jours
   d'uptime** — convenir d'une fenêtre.
4. **Journaux DEBUG à 12 Go** (`/opt/dicomproxy/ec/log`, ~850 Mo/jour) — repasser
   en INFO en exploitation normale ?
5. **Sauvegarde quotidienne incomplète** : le `tar` de `/opt/dicomproxy` n'inclut
   **ni la base `registry`** (mapping patient→serveur) **ni la config du portail**.

Depuis le 09/09 le serveur est **supervisé** ([17-zabbix.md](17-zabbix.md#proxyvia--sans-agent-sondes-tcp--icmp-09092026))
par ICMP et trois sondes TCP (9104/5432/8443) depuis le CT 204. La supervision ne
corrige aucun des points ci-dessus ; elle prévient si le répartiteur, sa base ou
son portail tombent.


### ⚠️ Vue PACS `TIMWFMCORE` — ce que l'audit du 11/09/2026 laisse ouvert

Constaté à l'audit en lecture seule du PACS principal
([13-tellis.md](13-tellis.md#audit-du-11092026--disques-sauvegarde-plantages-réception-dicom),
[relevé](configs/audit-timwfmcore-2026-09-11.md)). Le serveur est **supervisé
jusqu'à l'applicatif depuis le 11/09** ([17-zabbix.md](17-zabbix.md#vue-pacs-timwfmcore--supervision-applicative-11092026)) ;
la supervision rend ces points visibles, elle n'en corrige aucun. Par
destinataire :

- **Philips** : tempête de plantages `svstream.exe`/`svdser.exe` (3 à 56 par
  jour depuis au moins le 12/08, `svdser` — le serveur DICOM — 5 fois le 10/09),
  `Watchdog_SvMax` cassé, Mirth muet sur 8014, tablespace `MEDISTORE_MEDIUM_INX`
  à 6,5 % libre, correctifs Windows figés depuis mars 2025 ;
- **TELLIS** : `G:` BACKUP porte ~2 semaines de RMAN sur 1 To avec une copie
  complète de 200 Go chaque vendredi (259 Go libres le 11/09, pic à ~94 % avant
  purge) — capacité et rétention à confirmer, ainsi que la destination du
  snapshot Proxmox de 23:30 que la VM voit passer ;
- **EDL** : deux envois vers l'AET `TODAY` rompus la nuit du 10/09 ; le Vue PACS
  a acquitté SUCCESS toutes les images et a **reçu** l'abort (deux connexions à
  10 ms d'écart à 02:06:29) — la cause est chez l'émetteur ou sur leur chemin
  réseau ; leur demander le renvoi des deux séries et la correction du VR
  `OW`/`OB` de leur pixel data encapsulé ;
- **nous** : rétrograder l'agent Zabbix 7.4.1 vers le 7.0.30 LTS du serveur.

---

## 10. Authentification centralisée — suites du déploiement du 27/08/2026

Keycloak est en production ([16-keycloak.md](16-keycloak.md)) : realm `tim`,
Proxmox VE, PBS, headscale, Odoo et MyTIM (prod TIM) raccordés en OIDC,
brokering Google Workspace et SMTP Mailjet en place. Ce qui reste :

- **Éprouver headscale par une connexion OIDC réelle** (PVE et PBS le sont
  depuis le 27/08/2026, en SSO sur une même session) : un
  `tailscale up --login-server https://headscale.teleimagerie.net` de test.
- **Microsoft 365** (`isoteam.mn`) pourra suivre par la même mécanique que le
  brokering Google Workspace.
- **MyTIM** : **validation pilotes** puis communication à tout l'interne TIM
  (phase 3 du runbook `docs/technique/sso-keycloak.md` du dépôt gestion) ;
  **realm `isoteam`** (copie de `tim`) + ses 2 clients + redirect URI
  `…/realms/isoteam/broker/google/endpoint` dans la console Google Cloud, pour
  le tenant `app.isoteam.mn` ; secret de `mytim-staging` à vaulter
  (`group_vars/default/secrets/`) ; plus tard `sso-default`, médecins,
  back-channel logout
  ([16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026)).
- **Odoo** : **valider la connexion navigateur réelle** (pilote
  `mcapon@teleimagerie.net`, seul compte rapproché), puis généraliser aux
  internes actifs. Deux points relevés au passage : le provider `Odoo.com
  Accounts` est resté actif (second bouton inutile sur la page de login) et
  `web.base.url.freeze` n'est pas positionné
  ([18-odoo.md](18-odoo.md#sso-keycloak)).
- **Applications d'entreprise** (Zabbix en SAML/LDAP, CRM, e-learning,
  bastion) : collecter les accès, tableau des candidats dans
  [16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026).
- **Applications médicales** (Syngo Via, Vue PACS, RIS VENUS, TSplus) : cible
  à terme, à instruire éditeur par éditeur via la
  [checklist TELLIS](13-tellis.md#checklist-de-collecte).
- **Durcissement optionnel** : restreindre `/admin/` du vhost aux IP
  d'administration ; tester une restauration de la base depuis un dump
  `kc-pgdump` (le vzdump du CT, lui, suit la procédure standard de
  [10-sauvegardes.md](10-sauvegardes.md)).

---

## 11. Migration Odoo (VPS → VM 101) — ✅ TRAITÉ, soldé le 30/08/2026

En production sur le cluster depuis le 29/08/2026, VPS résilié le 30/08,
sauvegardes des trois niveaux et restauration vérifiées
([18-odoo.md](18-odoo.md#bascule-du-29082026--récit-chiffré)). Reste : la
**relève du mail entrant**, à l'état `draft` depuis le VPS (constat
post-bascule, pas une régression) — à réactiver depuis l'interface.

---

## 12. Fermeture de l'exposition publique du cluster — ✅ terminée le 01/09/2026

**Pourquoi** : `cluster.fw` ouvrait `8006`, `22`, `3128` et `5900-5999` à
tout Internet. Le journal `pveproxy` montrait des scanners qui sondaient l'API
en continu (`65.49.1.38/40/47`, `204.76.203.49`…), et le verrouillage de
pacs03 le 30/08 a montré ce que devient une surface publique non filtrée. Les
protections en place (clé seule, TOTP, fail2ban) tenaient le bruteforce ;
l'objectif était de **retirer `pveproxy` et `sshd` de la vue d'Internet** —
donc de se protéger d'une CVE d'authentification, que le 2FA ne couvre pas.

### ✅ Étape 1 — chemin privé d'administration (31/08/2026)

Les 3 nœuds ont une patte VLAN 400 (`.2`, `.3`, `.4`) **et** la route retour
`10.90.0.0/24 via 10.40.0.1` qui manquait. Depuis le VPN nomade, SSH et 8006
répondent sur les trois, **certificat valide** grâce aux overrides Unbound
`pveN.infra → 10.40.0.x`. Aucune règle OPNsense n'a été nécessaire. La
supervision Zabbix est passée au chemin privé (exception `10.40.0.60 → 8006`
posée **avant** le DROP du VLAN 400) — ce qui supprime au passage l'épingle à
cheveux publique et le risque de bannissement fail2ban de `57.130.34.122`
([04-securite.md](04-securite.md#accès-dadministration-par-vpn-31082026)).

### ✅ Étape 2 — seconde porte VPN (31/08/2026)

Les 3 nœuds sont enrôlés dans le tailnet (`tag:pve` — `pve1` `100.72.0.6`,
`pve2` `100.72.0.5`, `pve3` `100.72.0.7`) en **`--tun=userspace-networking`** :
routes vérifiées **identiques** avant/après, aucune interface créée, passerelle
OVH `100.64.0.1` intacte. `udp/41641` ouvert dans `cluster.fw` sans restriction
de source, ce qui donne un chemin **direct sur l'IP publique du nœud** —
mesuré : `direct 91.134.84.222:41641`, sans traverser OPNsense
([11-headscale.md](11-headscale.md#les-hyperviseurs--seconde-porte-dadministration-31082026)).
Test « porte 2 seule » réussi le 01/09/2026 : wg0 coupé sur le poste, les
3 nœuds restent joignables par le tailnet en SSH et 8006
([11-headscale.md](11-headscale.md#test--porte-2-seule---01092026)).

### ✅ Étape 3 — fermeture par vagues (31/08 et 01/09/2026)

`cluster.fw` étant répliqué par pmxcfs, la fermeture est **atomique et
globale** : il n'y a pas de nœud canari, la progressivité s'est obtenue **par
port**, avec 24 h de recul entre deux vagues.

| Vague | Fermé | Filet restant | Date |
|---|---|---|---|
| V1 | `3128` restreint ; `5900:5999` **supprimé** (rien n'y écoutait, les consoles passent par le WebSocket du 8006) | 8006 et 22 publics | ✅ 31/08/2026 |
| V2 | `8006` | 22 public | ✅ 01/09/2026 |
| V3 | `22` | tailnet, timers, console KVM | ✅ 01/09/2026 |

`8006`, `22` et `3128` sont restreints à l'ipset `admin` (`10.90.0.0/24`) ;
`5900-5999` supprimé. Depuis Internet, les trois ports expirent sur les 3 IP
publiques et **seul le ping répond**. Les 6 chemins d'administration (3 nœuds
× 2 portes) ont été vérifiés sur connexions neuves, et les compteurs
`iptables` confirment que les règles sont réellement empruntées. Quorum 3/3,
corosync **4 liens** (le ring1 sur IP publiques passe par `+cluster`), Ceph
`HEALTH_OK`, 7 ressources HA, NAS monté, SSH inter-nœuds opérationnel,
supervision Zabbix verte par le chemin privé — `57.130.34.122` a disparu des
journaux.

`ignoreip` fail2ban est posé sur les 3 nœuds depuis le 31/08
(`configs/fail2ban-proxmox.local`) : `10.90.0.0/24`, `10.40.0.60` et les
réseaux vRack ne peuvent plus être bannis — sinon 5 échecs enfermeraient
dehors la seule source d'administration restante. Le tailnet n'a pas besoin
d'y figurer : il livre depuis `127.0.0.1`.

**Ce que la fermeture a failli casser, et comment on l'a vu** : l'inventaire des
sources (P2) a révélé deux administrateurs sur le chemin public —
`82.127.36.38` (IP partagée du bureau, portant les clés `matt@LENOVO-MCA2`,
`matt@LENOVO-MCA2-windows` et `brtrnd@thinkpad`) et `88.171.147.68` (Bertrand
depuis un autre site), avec 570 connexions SSH sur pve1 pour la première. V2 a
été **retardée d'une journée** le temps que Bertrand bascule sur son pair VPN
`10.90.0.3`. Sans cet inventaire, la fermeture coupait un collègue en pleine
session. **À refaire avant toute fermeture du même genre.**

### Reste ouvert sur ce chantier

- ⚠️ **Test complet restant** (arrêt réel de la VM 100) : ce qui reste à
  mesurer est le **rétablissement** d'un pair, plan de contrôle headscale
  éteint (poste redémarré, endpoint changé) — les pairs déjà établis, eux,
  dialoguent en direct sans lui. **Non joué à dessein** : il coupe le réseau de
  toutes les VM de production (Odoo, pacs-secours, Keycloak, Zabbix) — à
  programmer dans une fenêtre de maintenance. Tant qu'il n'est pas fait,
  l'indépendance de la seconde porte est **démontrée par construction**
  (chemin direct constaté) mais **pas mesurée de bout en bout**.
- 📋 **Relire `/var/log/pve-firewall.log`** pour attraper un flux légitime
  rare que l'ipset `admin` aurait manqué.
- 📋 **`3128` (SPICE)** : compteur à 0 depuis la fermeture — candidat à la
  suppression pure comme `5900-5999`, à confirmer sur 30 jours (échéance
  01/10/2026).
