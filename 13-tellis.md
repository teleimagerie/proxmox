# DC TELLIS — fiche de référence du site distant

Deuxième datacenter de l'architecture HDS, opéré par un prestataire. C'est le
site désigné « le site distant » dans les fichiers antérieurs à ce document —
celui que joint le tunnel WireGuard `wg2`
([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) et que dessert le
relais TLS `syngo-via.*` ([09-proxy-tim.md](09-proxy-tim.md)).

L'inventaire ci-dessous a été **déclaré le 25/08/2026** par le responsable
infrastructure, puis contrôlé sur machine au fil des relevés : TIMWFMCORE
(29-30/08), les deux syngo.via et TSplus (02/09), les trois VENUS (04/09),
ProxyVia (09/09) et Vue Motion (11/09). Le reste (pfSense, `prod01`,
équipements) est encore
déclaratif. Chaque information porte donc son statut :

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
| `192.168.101.48/28` | `.49` → `.62` | bloc imagerie et production (PACS, IA, passerelles, équipements réseau) | ✅ **`.62`** (second pfSense) — constaté sur prod01 (25/08) et TIMWFMCORE (29/08), distribué par DHCP ; le `.59` ne sert que les routes vers nos réseaux |
| `192.168.101.96/28` | `.97` → `.110` | bloc Syngo Via (serveurs, TSplus, ProxyVia) | ✅ **`.110`** (pfSense principal) — constaté le 02/09/2026 sur les trois serveurs inventoriés ; ⚠️ **masques incohérents** : `.98` est en /28 mais `.100` et `.102` sont en **/24** (voir [Syngo Via](#syngo-via)) |
| `192.168.111.0/24` | `.1` → `.254` | RIS VENUS | ✅ **`.254`** (pfSense principal) — constaté le 04/09/2026 sur `TIM-VENUS1-AP` (`Get-NetRoute`, masque /24) |
| `192.168.171.0/24` | `.1` = TIMWFMCORE (2ᵉ patte) | ⚠️ **découvert le 29/08/2026** dans l'inventaire du PACS — réseau sans passerelle, rôle inconnu (réseau d'imagerie/stockage ? lié au volume `Images02` ?) | — |

> Les trois réseaux `192.168.101.x`/`111.x` sont exactement ceux annoncés dans
> les `AllowedIPs` du tunnel `wg2`, et le contrôle de non-recouvrement avec nos
> plages a déjà été fait
> ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)). Attention
> aux `/28` : `.63` et `.111` sont des adresses de broadcast, pas des hôtes.
> `192.168.171.0/24` est hors AllowedIPs : invisible depuis chez nous, mais à
> garder dans le contrôle de recouvrement si un jour il devait être annoncé.

---

## Inventaire par bloc fonctionnel

### Réseau et sécurité

Le site compte **deux pfSense** et son propre reverse proxy nginx — trois
équipements dont la configuration précise reste à collecter.

| IP | Machine | Rôle | Mainteneur | Statut |
|---|---|---|---|---|
| `192.168.101.59` | pfSense principal | pare-feu du site, serveur du tunnel `wg2` et du VPN nomades `tun_wg0` ; pattes `192.168.101.59`, `192.168.101.110`, `192.168.111.254` | ⚠️ | pattes ✅ (`.59`/`.110` : mise en place du tunnel, 14/08/2026 ; `.254` : passerelle par défaut constatée sur VENUS1 le 04/09/2026) ; règles, NAT et WireGuard ⚠️ à vérifier précisément |
| `192.168.101.62` | pfSense « FW-Passerelle » | **second pfSense** — c'est lui la **passerelle par défaut des serveurs du bloc production** (et leur DHCP : route `proto dhcp` sur prod01) ; rôle complet et règles ⚠️ | ⚠️ | ✅ passerelle+DHCP constatés sur prod01 le 25/08/2026 ; le reste ⚠️ |
| `192.168.101.61` | Reverse proxy nginx | reverse proxy local du site — noms servis, certificats et backends inconnus | ⚠️ | 📋 existence, ⚠️ rôle |
| `192.168.101.60` | Routeur vers Philips | routage vers l'environnement Philips (lié au PACS et à la télémaintenance ?) | ⚠️ | 📋 existence, ⚠️ rôle |

### Imagerie Philips

Le cœur métier du site : le PACS (*Picture Archiving and Communication
System*), qui archive les examens d'imagerie et les distribue aux stations de
lecture.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.52` | Vue PACS — **`TIMWFMCORE`** | **PACS principal de TIM** : archivage et distribution des examens, tout l'applicatif + base Oracle 19 locale ; alias pfSense `SRV_TIM_WFMCORE` | Philips | ✅ joignabilité `wg2` testée (14/08) ; ✅ **inventorié le 29/08/2026** (voir ci-dessous) ; ✅ route retour `172.31.0.0/24` posée le 11/09/2026 — RDP et SSH directs depuis le poste |
| `192.168.101.53` | Vue Motion — **`TIMVUEEXPLORER`** | visualiseur web « zéro empreinte » de la gamme Vue : consultation des images depuis un simple navigateur, sans client lourd ; **Vue Motion + Vue Explorer 12.2.8**, frontal web qui lit les images sur TIMWFMCORE | Philips | ✅ **inventorié le 11/09/2026** (voir ci-dessous) ; ✅ route retour `172.31.0.0/24` posée le 11/09/2026 ([diagnostic](#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)) ; ✅ SSH par clé le 11/09 |
| `192.168.101.57` | Passerelle firewall SRSA | boîtier pare-feu de la télémaintenance Philips : canal d'accès distant de l'éditeur vers ses équipements | Philips | 📋 ; signification exacte du sigle et flux ⚠️ |

Le routeur `192.168.101.60` (bloc réseau ci-dessus) fait partie de cet
environnement.

#### `TIMWFMCORE` — le PACS principal, inventorié le 29/08/2026

Relevés : [`configs/inventaire-timwfmcore-2026-08-29.md`](configs/inventaire-timwfmcore-2026-08-29.md)
(premier produit du script `scripts/inventaire-windows.ps1`, sans droits admin) puis
[`configs/inventaire-timwfmcore-2026-08-30.md`](configs/inventaire-timwfmcore-2026-08-30.md)
(**avec droits admin**, par SSH — complète les partages, tâches planifiées et
la sauvegarde applicative, voir [Accès SSH](#accès-ssh-30082026) plus bas). L'essentiel :

| | |
|---|---|
| Machine | **VM QEMU/KVM** (i440FX, VirtIO partout, guest agent actif) — 12 vCPU « Common KVM processor », 64 Go |
| OS | Windows Server 2019 **Datacenter** 1809, installé le 27/02/2023, workgroup |
| Réseau | `192.168.101.52/28` (gw `.62`, DNS `.62` + `8.8.8.8`) **+ 2ᵉ patte `192.168.171.1/24`** sans passerelle (rôle ⚠️) |
| Stockage | C: 300 Go système · D: 50 Go Service · **F: 2 To Database** (Oracle) · G: 1 To BACKUP · I: 4 To « `Images02_TO_NOT_USED` » quasi vide |
| Base de données | **Oracle 19 locale**, SID `mst1`, listener 1521 lié à `127.0.0.1` + `.52` |
| Applicatif | pile Vue PACS complète (Carestream/Algotec « Imaginet », `System5`) : MVSMAIN (2104, sécurisé 22104), **Loader DICOM** (2001/2105), AutoRouter, Medilink HL7, **Mirth Connect 3.5.2** (moteur d'interfaces), DataGrid Kafka/Zookeeper/Ignite, Tomcat 7 (8080), IIS (80/443), licences FLEXlm (7789) ; services applicatifs sous le compte local `philipsadm` |
| Supervision | exporters Philips MEMO Prometheus (9090, 9182), NXLog serveur syslog (514/tcp) ; **Zabbix Agent 2 (7.4.1) installé mais ARRÊTÉ** — candidat naturel au raccordement sur notre Zabbix ([17-zabbix.md](17-zabbix.md)) |
| Accès distants | **AnyDesk (7070) + TeamViewer + Philips Telemedicine Remote Agent + stunnel** — plusieurs canaux tiers actifs sur le PACS de production ; RDP, SMB (partages `Devices`, `temp`) et WinRM (5985) ouverts |
| Déploiement | Octopus Deploy Tentacle (28/04/2026) — quelqu'un déploie de l'applicatif dessus, qui ? ⚠️ |

Deux indices convergents sur l'hyperviseur du site : la MAC `BC:24:11:…` de la
2ᵉ carte est **le préfixe des MAC générées par Proxmox VE** — le PACS principal
tourne vraisemblablement sur un Proxmox chez TELLIS (lequel ? où ? ⚠️ ajouté à
la [checklist](#checklist-de-collecte)). **Confirmé le 04/09/2026 par les trois
VENUS** : MAC `BC:24:11:…` toutes les trois, matériel QEMU (i440FX et Q35),
`QEMU Guest Agent`, pilotes VirtIO et agent Spice — **le site fait bien tourner
un Proxmox VE**, et VENUS1/VENUS2 y ont été *migrés depuis VMware* (VMware Tools
10.3 encore installé mais à l'arrêt, cartes toujours nommées `vmxnet3`).

> ⚠️ **Points de vigilance relevés** : correctifs Windows **figés depuis mars
> 2025** (aucun KB depuis — 17 mois au moment du relevé) sur un Windows Server
> 2019 build 1809 ; uptime 89 j.

##### Sauvegarde applicative — éclaircie en admin le 30/08/2026

L'accès admin lève le doute : la sauvegarde n'est **pas** Windows Server Backup
mais une **chaîne de tâches planifiées Carestream** écrivant sur le volume
**`G:` (BACKUP, 1 To, 379 Go libres)** — `run_full_backups.pl`,
`run_cfg_backups.pl` (export Data Pump Oracle `CFG_EXPDP`),
`run_software_backup.pl`, tous sous `G:\Backup\scripts\` (logs sous
`…\System5\log\Scheduled_Tasks\`).

✅ **Reprise hors-machine assurée par TELLIS** : le prestataire exploitant du DC
**sauvegarde `G:` quotidiennement** (confirmé par l'utilisateur le 30/08/2026) —
c'est la copie externe qui manquait au raisonnement « `G:` est local ». La
chaîne Carestream produit donc le jeu de sauvegarde sur `G:`, que TELLIS
rapatrie ensuite. Nous ne maîtrisons ni la destination ni la rétention côté
TELLIS : à documenter auprès d'eux si une restauration devait un jour être
pilotée depuis notre côté.

Autres découvertes de l'inventaire admin (~80 tâches planifiées, toutes
`Ready`) : deux **lecteurs réseau mappés vers la 2ᵉ patte `192.168.171.x`** —
`M: \\192.168.171.3\FIR_TIM\fir_fs_04` et `N: \\192.168.171.2\FIR_TIM`, tous
deux `Unavailable` au moment du relevé — ce qui **éclaire enfin le réseau
`192.168.171.0/24`** : c'est le réseau de stockage FIR (« Fast Image
Repository ») du PACS, servi par au moins deux serveurs de fichiers `.2` et
`.3`. Un volume local **`I:` « `Images02_TO_NOT_USED` » (4 To, quasi vide)**
confirme son nom : ne pas s'en servir. Watchdogs Philips (`C:\PhilipsWD\`) et
tâches `wfm_*`/`fir_*` très nombreux — l'applicatif s'auto-surveille.

##### Accès SSH (30/08/2026)

OpenSSH serveur activé sur TIMWFMCORE, clé `id_ed25519` du poste d'admin dans
`C:\ProgramData\ssh\administrators_authorized_keys` (compte **`Administrator`**),
`PasswordAuthentication no`. Alias `ssh timwfmcore` du `~/.ssh/config`, en
direct ; le rebond par pacs03 a été **obligatoire du 30/08 au 11/09/2026** et
survit comme chemin de secours sous l'alias `timwfmcore-via-pacs03`. La
connexion directe poste→`192.168.101.52` par
le VPN nomade (`tun_wg0` du pfSense, poste = `172.31.0.3`) échouait à l'échange
de bannière alors que le port TCP s'ouvrait ; la fiche a d'abord attribué
l'échec à un trou noir MTU, ce qui était faux — la cause était une **route
retour manquante pour la plage des nomades `172.31.0.0/24`**, posée le
11/09/2026 (voir [le diagnostic](#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)). Depuis, la bannière arrive en direct
(`SSH-2.0-OpenSSH_for_Windows_7.7`) ; le rebond reste un chemin de secours
valable, pacs03 ayant sa propre route retour (`172.32.0.0/24`).

> **Pare-feu Windows : laissé désactivé, volontairement.** Contrairement à
> pacs03 (nu sur Internet), TIMWFMCORE est un serveur **de production interne
> derrière les deux pfSense de TELLIS**, opéré par le prestataire, avec des
> dizaines de flux LAN (modalités, RIS, IA, Vue Motion, syngo, FIR…). Poser un
> pare-feu local ici sans cartographie complète couperait la production. C'est
> une décision à prendre **avec l'exploitant du DC**, pas un oubli — le point
> reste ouvert dans la [checklist](#checklist-de-collecte).

#### `TIMVUEEXPLORER` (`.53`) — Vue Motion, le visualiseur web, inventorié le 11/09/2026

Relevé : [`configs/inventaire-timvueexplorer-2026-09-11.md`](configs/inventaire-timvueexplorer-2026-09-11.md)
(par SSH avec droits admin, script copié, exécuté puis supprimé — rien laissé
sur la machine ; voir [Accès SSH](#accès-ssh-11092026) plus bas).

**Ce que c'est** : le **frontal web** de la pile Vue — la même base logicielle
que TIMWFMCORE (Carestream/Algotec « Imaginet », `System5`, **Vue PACS/VNA
12.2.8.100**), mais dans le rôle **Vue Motion + Vue Explorer** (dossiers de
sauvegarde `VueMotion_12.2.8.100_20230609` et `VueExplorer_12.2.8.100_20230609`,
configuration système mise à jour le 07/11/2024). Ni Oracle, ni Loader DICOM, ni
AutoRouter : ce n'est **pas une archive**, c'est un serveur de rendu et un
portail qui **lit les images sur TIMWFMCORE `.52:2104`** — connexions permanentes
constatées, ce qui tranche le flux « présumé » de la
[matrice des flux internes](#flux-internes).

| | |
|---|---|
| Machine | **VM QEMU/KVM** (i440FX, VirtIO disque et réseau, guest agent, balloon, agent Spice) — 4 vCPU « Common KVM processor », **16 Go**, 1 disque de 300 Go ; MAC `26:F6:24:…` administrée localement (pas le préfixe Proxmox `BC:24:11`), l'hyperviseur reste ⚠️ présumé être le Proxmox du site |
| OS | Windows Server 2019 **Datacenter** 1809, installé le **27/02/2023** (même jour que TIMWFMCORE), workgroup, licence Retail active ; dernier redémarrage le 29/05/2026 (jour des derniers correctifs), uptime 104 j |
| Réseau | `192.168.101.53/28`, passerelle `.62`, DNS `.62` + `8.8.8.8` ; **une seule route retour**, `172.31.0.0/24` via `.59` (11/09/2026) — rien vers `10.40.0.0/24` ni `10.90.0.0/24`, donc **le CT 204 Zabbix ne le joint pas** et un agent actif n'en sortirait pas non plus |
| Stockage | C: 249,5 Go SYSTEM (186 Go libres) · D: 50 Go SERVICE (30,7 Go libres) : `PortalCachedFiles` et le certificat `timvueexplorer.pfx` du 09/12/2025 |
| Applicatif | IIS site **`PACS`** sur **80/443** (portail web : .NET Core 2.2 Hosting, ARR 3.0, URL Rewrite, UrlScan, Web Deploy, AppFabric 1.1) ; **MVSMAIN** en trois instances : serveur `2104`, sécurisé `22104`, LightViewer `29032` ; DataGrid (Filebeat, Metricbeat, Ignite) ; SessionManager `25817` local ; 8888 et 5357 en écoute ; Perl 5.16, Python 3.6 et JDK 8 pour les scripts Carestream ; 10 tâches planifiées Carestream (`syscheck`, rotation des journaux, snapshot, nettoyage DICOM `NDF`, `FilesCleaner`, `zip_and_clean`), **toutes en succès le 11/09** |
| Sauvegarde | tâche `backup_files` à 02:00 = **versions des fichiers de configuration locaux seulement** (`System5\Backup\Files`, « no candidates » le 11/09) ; pas de données propres à sauvegarder (cache de rendu), la configuration Vue est réinstallable ; copie de la VM hors machine par TELLIS ⚠️ inconnue |
| Correctifs | **posés le 29/05/2026** (KB5082118, KB5082123, KB5087066), lot précédent du 30/10/2024 — plus à jour que TIMWFMCORE (figé depuis mars 2025) ; **Defender actif** en temps réel, signatures du 10/09/2026 |
| Accès distants | **AnyDesk service actif, à l'écoute sur `0.0.0.0:7070`** ; TeamViewer 15.47 installé, service arrêté ; RDP, SMB (partage `temp`), WinRM 5985 ouverts — mêmes canaux tiers que sur le PACS |
| Comptes | 9 comptes locaux (6 actifs) ; **4 administrateurs** : `Administrator` (dernière session 22/10/2024), `philipsadm` (compte de l'éditeur, sert aux interventions), `xadministrator` (dernière session 18/08/2026 à 01:58), `mcapon` (créé le 11/09/2026 pour l'accès SSH) ; `PortalAppPoolUser` et `SysCFGAppPoolUser` portent les pools IIS |

**Pare-feu Windows : sans effet.** Le profil *Domain* est actif, mais la carte
est classée *Private* et ce profil est **désactivé** (comme *Public*) : aucune
règle n'est appliquée, exactement la situation de VENUS2/VENUS3. Le filtrage
repose entièrement sur les deux pfSense. Même décision à prendre avec
l'exploitant que pour TIMWFMCORE — mais ici la cartographie est simple
(80/443 entrants, `.52:2104` sortant), ce qui rend un pare-feu local envisageable.

##### Accès SSH (11/09/2026)

OpenSSH serveur **9.5p2** (capacité Windows native) installé le 11/09/2026 par
[scripts/installer-openssh-windows.ps1](scripts/installer-openssh-windows.ps1)
lancé depuis le compte `philipsadm` : clé `id_ed25519` du poste dans
`administrators_authorized_keys` (ACL SYSTEM + Administrateurs vérifiée),
`PasswordAuthentication no` **vérifié** (`Permission denied (publickey)` sans clé).
Alias `ssh vuemotion` (ou `timvueexplorer`) du `~/.ssh/config`, compte
**`mcapon`**, **en direct depuis le poste** (`172.31.0.3`, sans rebond par
pacs03) grâce à la route retour posée le même jour. L'étape 5 du script (règle
pare-feu `ssh-in`) a échoué sur la première exécution — liste d'adresses passée
par `-File`, piège n° 40, corrigé dans le script — si bien que la règle
d'installation `OpenSSH-Server-In-TCP` (portée *Any*) est restée en place ;
sans conséquence tant que le profil pare-feu est désactivé, à remplacer par
`ssh-in` restreinte à `172.31.0.3` pour rester cohérent avec les autres serveurs
([checklist](#checklist-de-collecte)).

> ⚠️ **Points de vigilance** : pare-feu Windows sans effet (profil *Private*
> désactivé) ; AnyDesk exposé sur le LAN (7070) ; aucune route vers nos réseaux
> `10.40.0.0/24`/`10.90.0.0/24`, à poser avant tout raccordement à Zabbix ;
> DNS public `8.8.8.8` en secours ; certificat `timvueexplorer.pfx` de décembre
> 2025 dont l'échéance et le nom servi restent à rapprocher de
> [14-noms-de-domaine.md](14-noms-de-domaine.md).


##### Audit du 11/09/2026 — disques, sauvegarde, plantages, réception DICOM

Relevé en lecture seule ([`configs/audit-timwfmcore-2026-09-11.md`](configs/audit-timwfmcore-2026-09-11.md)),
déclenché par deux envois EDL refusés la nuit du 10/09 et par la volonté de
superviser enfin l'applicatif, pas seulement Windows
([17-zabbix.md](17-zabbix.md#vue-pacs-timwfmcore--supervision-applicative-11092026)).

| | |
|---|---|
| Disques | `F:` Database **301 Go libres sur 2 To** (−36 Go en 12 jours, ≈ 3 Go/j) ; `G:` BACKUP **259 Go libres sur 1 To** (−120 Go en 12 jours) ; `C:` 32 % libre ; `I:` toujours vide ; `M:`/`N:` (FIR) toujours `Unavailable` ; 4 disques VirtIO sains ; 102 j d'uptime |
| Sauvegarde | la chaîne Carestream est du **RMAN** : archivelogs **toutes les 3 h** (~30-38 Go/j), **copie complète des datafiles le vendredi** (~200 Go), `DBInfo` quotidien. Rétention effective **≈ 2 semaines** (rien d'antérieur au 29/08) : `G:` oscille de 74 à ~94 % chaque vendredi avant purge. Le snapshot hyperviseur quotidien de TELLIS est **visible** : deux erreurs VSS 8194 (bénignes) chaque jour à 23:30, gel par le QEMU Guest Agent |
| Oracle | `/ as sysdba` refusé en session SSH (ORA-01017) ; le contrôle interne du PACS répète que le tablespace **`MEDISTORE_MEDIUM_INX` est à 6,5 % libre** (721 Go / 771 Go) |
| Plantages | **3 à 17 vidages par jour (56 le 08/09)** depuis au moins le 12/08 : `svstream.exe` (streaming, `conn.dll` et corruption de tas), **`svdser.exe` le serveur DICOM (5 fois le 10/09)**, `svar`, `svfload`, `w3wp`. Le PACS Restarter relance ; chaque plantage de `svdser` emporte les associations de son processus. `Watchdog_SvMax` est cassé (exécutable invalide), Mirth est muet sur 8014 (CRITICAL du contrôle interne), 19 864 études sans ordre RIS |
| Journaux | 135 000 ERROR/24 h dans `SVDSER.log` (SOP classes refusées vers `192.168.101.56`, routage `grid_name is empty`…), ~1 000 « Token Validity Time is Wrong »/j dans `svar.log` (horloge d'un client en dérive ?) — du bruit de fond que personne ne lit, le PACS s'auto-surveillant sans lecteur |
| Agent Zabbix | sortait **par Internet** (nom → VIP `.122`, `i/o timeout` quotidiens), s'était arrêté inopinément le 05/09 sans récupération : repointé sur `10.40.0.60` par `wg2` et récupération armée le 11/09 |

**Les deux envois EDL du 10/09.** `TODAY` est un AE title de ce serveur, appelé
par `XPLORE_PACS` (`10.0.241.54`, le PACS Xplore central d'EDL) et
`XPLORE_SECOURS` (pacs03). Les cinq ruptures des journaux EDL (00:18:41,
00:19:20, 02:06:20, 02:06:29 ×2) se retrouvent à la milliseconde dans le journal
DICOM du serveur : à chaque fois le Vue PACS **a acquitté SUCCESS toutes les
images reçues** (118, 31, 676, 219 et 102) puis a **reçu un abort du pair 16 à
30 ms après** son dernier acquittement ; il n'a émis aucun abort de la journée
et n'a pas planté à ces heures. À 02:06:29, **deux associations distinctes**
(`TODAY` et `URGENCE`) tombent à 10 ms d'écart : l'événement est du côté de
l'émetteur EDL (« Exception processing PDU » sur un C-STORE-RSP de ~100 octets)
ou du chemin réseau EDL → TELLIS, pas du PACS. Les séries restent incomplètes
tant qu'EDL ne rejoue pas l'envoi. Constat annexe à leur remonter : leurs objets
JPEG Lossless arrivent avec un pixel data encapsulé en VR `OW` au lieu de `OB`
(« Incorrectly encoded encapsulated data… trying to recover »), corrigé à la
volée et stocké — sans lien avec les ruptures.

##### Notification des nouvelles études vers MyTIM — relevé du 11/09/2026

Question posée le 11/09 : le Vue PACS peut-il appeler MyTIM et MyISOTEAM en
HTTPS quand un examen arrive ? **Oui, et sans code à déposer sur le serveur.**
Relevé en lecture seule par SSH (PowerShell en `-EncodedCommand`, rien laissé
sur la machine).

**Réseau, prouvé.** Depuis `.52`, un HEAD HTTPS sur `app.teleimagerie.net` et
`app.isoteam.mn` répond 200 (180 à 700 ms), `curl.exe` 7.83 (Schannel) valide
le certificat, sortie Internet directe par la passerelle `.62` sans proxy, **IP
publique source `77.158.128.112`** (la seconde adresse publique du site, pas
`37.61.243.245`). Le tunnel `wg2` vers `10.40.0.0/24` et les récepteurs DICOM
de pacs03 (`172.32.0.2:11112/11113`) sont aussi joignables depuis `.52`.

**L'Info Router est la bonne porte.** L'Auto-Router Algotec
(`System5\autorouter`, services `Imaginet Auto-Router Execution/Scheduling
Module`) déclenche des règles sur des sondes et exécute des commandes, relevées
dans `ar_server.jar` :

| Commande de règle (nom dans l'UI) | Ce qu'elle fait |
|---|---|
| **Run An Executable** (la « fonction personnalisée ») | Executable Name + Full Path + Parameters ; espaces réservés `#CLE#` (obligatoire) et `?#CLE#` (optionnel) remplacés par les propriétés de l'événement ; stdout/stderr et code de sortie journalisés dans le statut de la commande. L'outil mammo Philips `loader\exe\tool_image_processor\execute_mg_tool.bat` s'appelle ainsi (`-p "#PATIENT_ID#" -i "#ISSUER_OF_PATIENT_ID#"`) : le mécanisme est en production sur cette machine |
| **Sending Http URL Request** | une URL avec les mêmes `#CLE#`, `HttpsURLConnection` avec trust manager local (pas de souci de CA), POST possible, succès = HTTP 200 (« HTTP response OK »), erreurs tracées dans `AutoRouter.ExecutionModule.log` |
| HTTP Call | variante liée au Patient Portal (jeton de sécurité Vue, réponse `Status/Message/Success`) — pas pour nous |

Les propriétés remplaçables dépendent de la sonde : **First image arrived /
Whole Study Arrived** (`NewStudyProbe`, fin d'étude par
`wait_for_study_in_minutes` + `study_idle_time_in_minutes`) fournissent
`STUDY_INSTANCE_UID`, `ACCESSION_NUMBER`, `PATIENT_ID`, `ISSUER_OF_PATIENT_ID`,
`PATIENT_NAME`, `PATIENTS_LAST_NAME`, `PATIENTS_FIRST_NAME`, `MODALITY`,
`NUMBER_OF_IMAGES`, `TAMAR_STUDY_INSERT_TIME`, `TAMAR_SITE_ID`,
`TRIGGER_REASON` — **ni date de naissance ni date d'étude** ; **New Study
Metadata** (`NewStudyMetadataProbe`) ajoute `PATIENTS_BIRTH_DATE`,
`PATIENTS_SEX`, `STUDY_DATE`, `STUDY_TIME`, `STUDY_DESCRIPTION`,
`MODALITIES_IN_STUDY`, `TAMAR_SOURCE_AE` et tout tag DICOM déclaré dans la
sonde, mais se déclenche au début de l'étude. Un espace réservé absent de
l'événement arrive en clair (`#PATIENTS_BIRTH_DATE#`) : l'application le
traite comme vide.

**Ce qui ne marche pas, ou n'est pas à nous.** Mirth Connect 3.5.2
(`C:\Program Files\Mirth Connect`, base Oracle `mirth`) porte le canal Philips
**SCN** (« Send SCN messages », Web Service Listener → HL7 TCP), le mécanisme
natif de notification d'étude (module `Algotec.MST.EventNotification.*`) ;
mais le service tourne **sans aucun port en écoute** : keystore
`appdata\keystore.jks` invalide (`Could not initialize security settings…
Invalid keystore format`, `Could not start web server`, depuis le redémarrage
du 19/08), serveur web 8014/9443 mort, aucun canal déployé. C'est la cause du
« Mirth muet sur 8014 » de la liste Philips. `/ExternalAutoRouter` (IIS)
répond « No methods available » ; `/FHIRAutoEventsService` et
`/KafkaProxy/topics/events` sont internes Philips. QIDO-RS
(`/QidoRS/qidors.svc/timwfmcoreFIR/studies`, public via
`pacs01.teleimagerie.net` → nginx TELLIS `.61`) fonctionne avec `includefield`,
`limit`, `offset`, `fuzzymatching`, mais **sans filtre « reçu depuis »** ;
MyTIM l'appelle déjà **~31 000 fois entre 0 h et 14 h 30** (comptage d'images
étude par étude, toutes les minutes) — le journal IIS du PACS
(`System5\log\IISLogFiles\W3SVC1`) les voit arriver de `.61`.

**Constat annexe** : la règle Auto-Router « copy to VIACLUSTER » échoue en
boucle (`Move operation failed… Communication error while storing instances`,
14:22 le 11/09) — à remonter à Philips avec le reste.

**Ce qui est fait côté MyTIM** (dépôt `gestion`, branche
`feat/pacs-study-events`, commit `db4e47390`) : endpoint
`GET|POST /api/pacs/study-events` authentifié par `?access_token=` (un
`ApiClient` par tenant, rôle `ROLE_PACS_EVENT`), qui accepte query-string, corps
form-encoded ou JSON, ignore les espaces réservés non remplacés, répond 200
même pour un événement ignoré (tout non-200 est un échec pour le PACS) ;
rapprochement par StudyInstanceUID puis nom + prénom + date de naissance + date
d'étude ±1 j, enrichissement QIDO-RS par UID, rapprochement QIDO périodique
toutes les 15 min en filet de sécurité, liste blanche IP `77.158.128.112`
d'abord en mode observation. Contrat, body de la règle et runbook :
`docs/technique/pacs-study-events.md` du dépôt `gestion`. **Reste à faire** :
déployer la branche, créer les clés AppConfig et les deux `ApiClient`, poser
les deux règles Info Router (sonde Whole Study Arrived, POST vers chaque
tenant), informer Philips et TELLIS de la règle ajoutée.

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
TLS `syngo-via.*` décrit dans [09-proxy-tim.md](09-proxy-tim.md). **Les trois
serveurs ont été inventoriés le 02/09/2026** par SSH avec droits admin (relevés
bruts dans `configs/`, synthèses ci-dessous).

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.98` | **`syngovia-135104`** — Syngo Via serveur 1 | **instance syngo.via VB80 complète** (serveur 10.6, SQL Server 2022 locale, AD LDS, licences FLEXlm, SCP DICOM 104, 16,6 To d'images) — **jumelle** du serveur 2, les deux étant fédérées par l'*Enterprise Browser* | Siemens Healthineers | ✅ **inventorié le 02/09/2026** (voir ci-dessous) |
| `192.168.101.100` | **`syngovia-135113`** — Syngo Via serveur 2 | idem : même matériel, même logiciel, même base d'utilisateurs ; c'est le **serveur par défaut** du client publié par TSplus | Siemens Healthineers | ✅ **inventorié le 02/09/2026** |
| `192.168.101.102` | **`win-srv-tsplus`** — TSplus | publication de l'*Enterprise Browser* Siemens (« SyngoVIA EC ») à 618 comptes par le portail web + RemoteApp de **TS2log 18** (marque blanche TSplus), multiplexés sur le 443 ; joint depuis Internet par le NAT du pfSense, le WAN `37.61.243.246` étant « son » adresse publique | TSplus | ✅ **inventorié le 02/09/2026** ; ✅ **NAT 443 → `.102` confirmé** (même certificat, même numéro de série, vu depuis Internet et depuis le LAN) |
| `192.168.101.103` | **`dicomproxy`** — ProxyVia | **répartiteur DICOM `DicomProxy VB10B`** (Debian 11, dcm4che sur Tomcat 9, base PostgreSQL `registry`) : reçoit les examens des sites et du PACS Xplore sur l'AET `DP_EC` (9104) et les répartit en **round-robin** entre les deux syngo.via | Siemens Healthineers | ✅ **inventorié le 09/09/2026** (voir ci-dessous) |

> **ProxyVia est double-attaché** : `192.168.101.103` dans ce bloc **et**
> `192.168.101.58` dans le bloc imagerie — `.58` n'est donc pas une adresse
> libre. ✅ **Confirmé le 09/09/2026** : `ens18` porte `.103` (bloc syngo,
> passerelle par défaut `.110`), `ens19` porte `.58` (bloc imagerie) et
> route les réseaux des sites par le pfSense principal `.59`. C'est bien le
> pont DICOM entre les deux sous-réseaux — voir [section ProxyVia](#dicomproxy-103--proxyvia-le-répartiteur-dicom-inventorié-le-09092026).

#### `syngovia-135104` (`.98`) et `syngovia-135113` (`.100`) — deux syngo.via jumeaux, inventoriés le 02/09/2026

Relevés : [`configs/inventaire-syngovia-135104-2026-09-02.md`](configs/inventaire-syngovia-135104-2026-09-02.md)
et [`configs/inventaire-syngovia-135113-2026-09-02.md`](configs/inventaire-syngovia-135113-2026-09-02.md)
(`scripts/inventaire-windows.ps1` par SSH, droits admin — voir
[Accès SSH](#accès-ssh-aux-serveurs-syngo-et-tsplus-02092026)).

La question « répartition des rôles entre les deux serveurs » est tranchée :
**il n'y a pas de répartition de rôles**. Ce sont deux installations syngo.via
complètes et indépendantes, identiques au matériel et au logiciel près (le
`diff` des deux relevés ne montre que les MAC, les numéros de série et l'espace
libre), chacune avec sa base SQL, son annuaire AD LDS, sa licence et ses
16,6 To d'images. Elles se connaissent (le cache de configuration de l'autre
serveur est présent sur chacune) et l'*Enterprise Browser* publié par TSplus
interroge les deux : un utilisateur voit les examens des deux serveurs et ouvre
chacun sur celui qui le détient. **Ce qui décide qu'un examen va sur l'un ou
l'autre est en amont, dans le routage DICOM de ProxyVia** — ✅ tranché le
09/09/2026 : **répartition round-robin** entre les deux, sans règle par examen
(voir [section ProxyVia](#dicomproxy-103--proxyvia-le-répartiteur-dicom-inventorié-le-09092026)).
Les statistiques d'ouverture de session sont identiques sur les deux
(38 comptes distincts sur 7 jours, 70 sur 30 jours) : les deux servent.

| | |
|---|---|
| Machine | **HPE ProLiant DL380 Gen11** physique (numéros de série dans les relevés) — 2 × Xeon Gold 6426Y (32 c / 64 t), **384 Go** DDR5-4800 ECC (12 × 32 Go, 16 slots), **NVIDIA RTX A4000**, Smart Array : 2 volumes logiques SAS SSD de 640 Go et **17,2 To** ; carte 25 GbE OCP (port 1 en lien 10 Gbps, port 2 déconnecté), carte 4 × 1 GbE non câblée |
| OS | Windows Server 2022 **Standard** 21H2 (build 20348), OEM, installé le **27/01/2025** sur les deux, workgroup, locale en-US, fuseau Paris ; **Device Guard / WDAC actif** (catalogues Siemens) — PowerShell tourne en *ConstrainedLanguage*, ce qui a demandé d'adapter le script d'inventaire |
| Réseau | `.98/28` et `.100/24` (⚠️ masques différents pour deux jumeaux), passerelle **`.110`** (pfSense principal), DNS `8.8.8.8` (+ `1.1.1.1` sur `.98`) ; commutateurs virtuels Hyper-V `nat` et `WSL` en `172.x` (voir Docker ci-dessous) |
| Stockage | C: 140 Go System · D: 100 Go DB_Data · **E: 16 644 Go Image_Data (4,8 To libres, ~71 % occupés)** · M: 200 Go DB_Backup · N: 200 Go System_Backup (**16,7 Go libres sur `.98`, 8 Go sur `.100`**) · S: 200 Go Service · un second volume « System 2 » de 140 Go, vide |
| Applicatif | **syngo.via VB80** : serveur et client 10.6, `syngo.Sphere.Server` 13.15, modules 11.x (installés le 17/06/2025), options CT/MR/MI (packs `SiemensH_OH_CT_VB80_*`, Breast Care, MM Breast Reading, CT Liver Analysis, LungCAD, modèles AiM deep-learning, OncoBoard…), Organ Processing, SceniumRE, FHIR/FHIRCast ; **SQL Server 2022** instance nommée `MSSQLSERVER_SYDS` liée à `127.0.0.1` (bases `Patient` ≈ 5,4 Go, `Patient_Data` ≈ 13 Go, `Patient_InstanceData` ≈ 32 Go) ; **AD LDS** `SyngoConfiguration` (ADWS 9389) ; licences **FLEXlm** (`lmgrd` 27000, `SAG_med_daemon` 27010) ; **SCP DICOM sur 104** (`syngo.Common.Container`), récepteur HL7 9974/9975, IIS 80/443, serveur d'autorisation 47101, Tomcat 9 (8090), MSMQ, SNMP ; **Docker + WSL 2** (rôle Hyper-V, `dockerd` sert le DNS du vSwitch `nat`) — vraisemblablement les conteneurs d'algorithmes IA de Siemens (📋 présumé) ; **TSplus for Siemens 19.40.8.11** (`C:\Siemens\svcmain.exe`, mis à jour le 15/08/2026, cinq versions précédentes conservées) : chaque serveur peut aussi publier son client directement |
| Télémaintenance Siemens | canal **SRS** (*Smart Remote Services*) : `syngo RemoteConnectionSupport Service`, TeamViewer « Siemens Repack » (ModeratorGateway, TeamConnector), VNC Viewer, agents **Micro Focus Operations (HP OpenView)** 12.23 et **RCA/Radia** (`radexecd` 8226, `Radstgms` 3460 — distribution logicielle Siemens), Sentient Application Manager, `SystemStatusMonitoringRSC` (5555/9995/9996) ; journaux de visites `C:\Siemens\SupportLog*` datés 17/06/2025, 18/10/2025, 12/02/2026, 18/07/2026, 15/08/2026 |
| Supervision | **Zabbix depuis le 02/09/2026, sans agent** : SNMP v2c (gabarit *Windows by SNMP*, communauté dédiée lecture seule, manager `10.40.0.60` seul) + ICMP + sondes TCP 104/443/3389 depuis le CT 204 par `wg2` — l'agent est **refusé par WDAC** (MSI signé Zabbix SIA, code 1625), détail dans [17-zabbix.md](17-zabbix.md#serveurs-syngo-via-de-tellis--sans-agent-02092026) ; HPE AMS (iLO) actif, `hponcfg` absent — adresse iLO ⚠️ inconnue |
| Sauvegarde | tâche **`\Siemens\Backup_syngo.via`** (base → `M:`, partition système → `N:`) + **Windows Server Backup quotidien à 03:00** (7 versions, dernier ✅ 02/09/2026 03:00) — **tout sur disques locaux**, `N:` quasi plein ; **`E:` (16,6 To d'images) n'est pas sauvegardé**, cohérent si syngo.via ne fait que du post-traitement (l'archive reste le PACS) ⚠️ à confirmer ; copie hors-machine par TELLIS ⚠️ inconnue |
| Correctifs | **à jour** : KB5120241/5120242/5120705 posés le 27/08 (`.98`) et le 31/08/2026 (`.100`), lot précédent du 11/12/2025 ; Windows Update en « télécharger et notifier », service à l'arrêt : les correctifs sont posés par lots lors d'interventions (Siemens ? TELLIS ? ⚠️), suivis d'un redémarrage (31/08 04:33 et 01/09 01:06). Le `Setup` SQL Server de `.100` est passé en 16.0.1190 le 31/08, `.98` est resté en 16.0.1000 |
| Sécurité | pare-feu Windows **actif** sur les trois profils (≈ 700 règles) ; **Defender : protection temps réel DÉSACTIVÉE sur les deux** (service actif, signatures à jour) — WDAC compense en partie, mais reste à confirmer comme exigence Siemens ⚠️ ; RDP, WinRM (5985) et SMB (partages Siemens `Activity Settings`, `WorkflowTemplates`) ouverts |
| Comptes | **634 / 635 comptes locaux** (629 / 630 actifs) — la même base d'utilisateurs que TSplus, recréée sur chaque serveur ; 9 et 10 administrateurs : `adminUser`, `alocal`, `aremote`, `jbouteiller`, `MedAdmin`, `RemoteAdmin`, `siemens_apps`, `SyngoCmd0`, plus `mcapon` (`.98`) et `matthieu` **et** `Matthieu CAPON` (`.100`, doublon à nettoyer) |

> ⚠️ **Points de vigilance** : Defender temps réel coupé sur les deux serveurs ;
> `N:` (System_Backup) presque plein sur les deux — la sauvegarde système
> finira par échouer (désormais visible dans Zabbix) ; aucune sauvegarde
> hors-machine visible ; 630 comptes locaux à mot de passe, non fédérés
> ([candidats SSO](16-keycloak.md#candidats-au-raccordement--étude-du-27082026)) ;
> masques réseau incohérents entre jumeaux.

#### `dicomproxy` (`.103`) — ProxyVia, le répartiteur DICOM, inventorié le 09/09/2026

Relevé : [`configs/inventaire-dicomproxy-2026-09-09.md`](configs/inventaire-dicomproxy-2026-09-09.md)
(par SSH `ssh dicom@192.168.101.58`, lecture seule, clé du poste posée le 09/09 ;
rien déposé ni modifié sur la machine).

**Ce que c'est** : une VM Debian 11 (QEMU/KVM du Proxmox de site, 4 vCPU, 8 Gio,
disque 128 Go rempli à 13 %, **439 jours d'uptime**) qui fait tourner **Siemens
syngo.via DicomProxy VB10B** (`serialNumber 200147`) : le service `dp-ec` (dcm4che
2.0.29 en JVM) écoute l'AET **`DP_EC` sur `0.0.0.0:9104`**, un Tomcat 9 sert le
portail d'administration sur **8443**, et un **PostgreSQL 13** local héberge la base
`registry` du mapping patient→serveur. C'est **la réponse à la question laissée
ouverte** sur la répartition entre les deux syngo.via.

**Le routage, tranché** (`proxy.properties`) : le proxy reçoit les examens des sites
et du PACS Xplore, puis les **répartit en round-robin (`viaGroup RR`, `loadIndex 1`
chacun) entre `SYNGOVIA-135104` (`.98:104`) et `SYNGOVIA-135113` (`.100:104`)**, avec
**repli croisé** si l'un est indisponible et **mapping par PatientID** (un patient
déjà connu retourne sur le même serveur, via la base `registry`). **Il n'y a pas de
règle par type d'examen** : `routing.rule.count = 0`. En amont, le PACS `timwfmcoreFIR`
= **TIMWFMCORE `192.168.101.52:2104`** (store + query/retrieve) reçoit les
`MoveDestination` réécrites. **12 sources DICOM** sont déclarées : le PACS Xplore
(`10.0.241.54:104`) et dix AET de sites agrégés sur `172.18.162.40:11112` (ISO-TELE,
Saintes, Valence, Agen, Angers, Périgueux, Poitiers, Quimper, Rouen CHB, Réunion). Le
jour du relevé, ~38 000 images reçues (ISO-TELE 10 085), ~425 associations en sortie
vers TIMWFMCORE : le proxy travaille normalement.

**Double patte** (voir tableau ci-dessus) : `.103` bloc syngo (passerelle `.110`),
`.58` bloc imagerie, routes des sites par le pfSense `.59`.

**Supervision** : hôte `DICOMPROXY` ajouté à Zabbix le 09/09 (ICMP + sondes TCP
9104/5432/8443 depuis le CT 204) — [17-zabbix.md](17-zabbix.md#proxyvia--sans-agent-sondes-tcp--icmp-09092026).

> ⚠️ **Points de vigilance** (partis en ticket Siemens, l'appliance est gérée par
> l'éditeur) : **PostgreSQL `registry` joignable depuis le LAN sans mot de passe**
> — depuis le réseau via `.103`, `psql` aboutit sans authentification pour `dicom`
> **et pour le superutilisateur `postgres`**, alors que la base contient des
> identités patients (nom, date de naissance, sexe) ; **horloge en retard d'environ
> 10 min** (NTP muet faute de DNS résolvant) ; **redémarrage en attente** depuis le
> 05/08 et 439 jours sans reboot ; **12 Go de journaux DEBUG** ; **sauvegarde
> quotidienne incomplète** (ni la base `registry`, ni la config du portail).

#### `win-srv-tsplus` (`.102`) — la porte d'entrée des utilisateurs, inventorié le 02/09/2026

Relevé : [`configs/inventaire-win-srv-tsplus-2026-09-02.md`](configs/inventaire-win-srv-tsplus-2026-09-02.md).
C'est la machine que voit Internet derrière `syngo-via.*` : le portail web et
les sessions RemoteApp de **TS2log** (marque blanche de TSplus) y publient
l'*Enterprise Browser* Siemens, qui ouvre ensuite les examens sur l'un des deux
serveurs syngo.via.

| | |
|---|---|
| Machine | **HPE ProLiant DL360 Gen11** physique — 1 × Xeon Silver 4510 (12 c / 24 t), **32 Go** DDR5-4400 ECC (2 × 16 Go, 16 slots), **NVIDIA T1000 4 Go** (rendu des sessions, `prefer-hardware-gpu=yes`), contrôleur **HPE MR408i-o** : 1 volume RAID SSD de 447 Go ; 1 GbE en service (slot 15 port 4), carte 2 × 10GBASE-T non câblée |
| OS | Windows Server 2022 **Standard** 21H2, OEM, installé le **14/05/2025**, workgroup, en-US, fuseau Paris ; dernier redémarrage le **06/06/2026** (jour de la mise à jour TS2log 17 → 18) |
| Réseau | `.102/24` (⚠️ le plan dit /28), passerelle `.110`, DNS `8.8.8.8` |
| Stockage | C: 202 Go (52 Go libres) · **D: 244 Go « Backup »** (195 Go libres) |
| Applicatif | **TS2log 18.2026.5.12** (précédent 17.2025.6.10) : portail HTML5 sur **80/443** (`HTML5service`, lié à `.102` ; ports de repli 81/444), RDP 3389, ports `http.sys` 7443/8501/19955/19956/26551 (passerelle et RemoteApp TS2log — 19955/19956 sont ceux que relayait l'ancien VPS, [09-proxy-tim.md](09-proxy-tim.md)) ; application publiée **« SyngoVIA EC »** = `PatientBrowser.exe launch-via-browser` (Enterprise Browser Siemens) + panneau flottant, pour le groupe local **`GG-SIEMENS-REMAPP` (618 membres)** ; « Microsoft Remote Desktop » publié à un seul compte d'administration ; 218 profils d'applications utilisateur ; **client syngo.via 10.6 + Enterprise Launcher 2.5.0** (serveur par défaut `.100`, caches de configuration des deux serveurs) ; impression universelle (novaPDF / Universal Printer), Virtual Printer, redirection USB FabulaTech ; IIS installé mais **arrêté** (TS2log tient 80/443 lui-même) ; mode RDS « administration » (pas de rôle RDS : TS2log fait le multi-session) |
| Certificat | Let's Encrypt `CN=syngo-via.teleimagerie.net`, SAN `syngo-via.isoteam.mn`, **valide du 05/08 au 03/11/2026**, renouvelé par le gestionnaire ACME intégré de TS2log (`FreeCertificateManager.ini`) — même certificat vu depuis Internet sur `37.61.243.246:443`, et même redirection `302` sur le 80 : **le NAT 443 et 80 → `.102` est confirmé** |
| Accès distants | **Datto RMM** (agent CentraStage, UDP 13300) + **Splashtop Streamer** (07/06/2026, 6783) — un RMM opéré par quelqu'un (TELLIS ? ⚠️) ; TeamViewer 15.81 + repack Siemens ; SSH depuis le 02/09 ; WinRM 5985 |
| Supervision | **Zabbix Agent 2 7.4.3** → hôte `WIN-SRV-TSPLUS` ✅ ([17-zabbix.md](17-zabbix.md)), récupération automatique du service armée le 02/09 (comme pacs03) ; HPE AMS |
| Sauvegarde | **Windows Server Backup : dernière sauvegarde réussie le 09/09/2025**, 1 version — **rien depuis un an** ⚠️ ; aucune tâche de sauvegarde planifiée ; `D:` « Backup » n'héberge que cette vieille image |
| Correctifs | **figés depuis le 11/12/2025** (KB5071547) — 9 mois sans correctif sur un serveur **exposé à Internet** ⚠️ ; Windows Update à l'arrêt, sans stratégie |
| Sécurité | Defender temps réel actif, signatures du 01/09 ; pare-feu actif (4 350 règles, TS2log en ajoute par application) ; **pas de second facteur** : l'add-on 2FA de TS2log n'a jamais été activé (essai expiré le 10/07/2025) — **622 comptes locaux à mot de passe** derrière un portail ouvert sur Internet ⚠️ |
| Comptes | **627 comptes locaux** (622 actifs, 5 désactivés), 6 administrateurs : `Administrator`, `Info100T`, `matthieu`, `remoteadmin`, `sebastien`, `siemens_apps` ; 4 sessions RemoteApp actives au moment du relevé (16 h) |

> ⚠️ **Points de vigilance** — les trois plus sérieux du site à ce jour :
> (1) serveur exposé à Internet **sans correctif depuis 9 mois**, (2) **sans
> sauvegarde depuis un an**, (3) **sans second facteur** devant 622 comptes. À
> porter au prestataire et à Siemens (le TS2log est-il dans leur périmètre ?).
> Le raccordement SSO ([16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026))
> ou au moins l'activation du 2FA TS2log traiterait le point 3.

##### Accès SSH aux serveurs Syngo et TSplus (02/09/2026)

OpenSSH serveur (10.0) **installé le 02/09/2026** sur les trois machines, clé
`id_ed25519` du poste d'admin dans `administrators_authorized_keys` ; comptes
**`remoteadmin`** sur les deux syngo.via et **`matthieu`** sur TSplus, shell
`cmd.exe`, PowerShell 5.1 (en *ConstrainedLanguage* sur les syngo). Alias
`syngovia1`, `syngovia2` et `tsplus` dans le `~/.ssh/config` du poste.
**La connexion directe poste → serveur par le VPN nomade fonctionne ici sans
rebond par pacs03** : scp et sessions longues passent. La différence avec
TIMWFMCORE (jusqu'au 11/09/2026) tenait bien au chemin retour — ces trois
serveurs répondent au pfSense principal (`.110`), TIMWFMCORE au second pfSense
(`.62`), qui ne relaie pas les données d'une connexion dont il n'a pas vu
l'aller ; hypothèse du 02/09, **vérifiée le 11/09/2026**
([diagnostic](#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)). Précision du 04/09/2026 : ce « VPN nomade » est le
**`tun_wg0` du pfSense** (le poste y est le pair `172.31.0.3`, adresse vue par
`netstat` sur les deux serveurs), pas le VPN nomade OPNsense — voir
[`tun_wg0`](#tun_wg0--vpn-nomades-du-site).

Le script d'inventaire est copié, exécuté puis supprimé : **rien n'est laissé
sur les serveurs** (mode d'emploi en tête de
[scripts/inventaire-windows.ps1](scripts/inventaire-windows.ps1)).

### RIS VENUS (Softway Medical)

Le RIS (*Radiology Information System*) gère le versant administratif et
organisationnel de l'imagerie : demandes d'examens, planning, comptes rendus,
facturation. Déploiement classique en trois tiers — **inventorié le 04/09/2026**,
ce qui en précise la réalité : les deux premiers serveurs portent **le même socle
applicatif** (IIS + PHP 7.2, Mirth Connect 3.9.1, JasperReports, MariaDB 10.6
locale), `.64` y ajoute le **SFTP de dépôt des sites** et les démons d'import,
et **`.65` est la base partagée** que les deux interrogent (base `isotim`).
Les trois sont des **VM Proxmox** du site, en Windows Server 2022 Standard,
workgroup, DNS publics `8.8.8.8`/`8.8.4.4`, passerelle `.254`, avec
**TeamViewer 15.81.5 actif** sur chacune.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.111.63` | `TIM-VENUS1-AP` | serveur application (IIS/PHP, Mirth, JasperReports) | Softway Medical | ✅ **inventorié le 04/09/2026** |
| `192.168.111.64` | `TIM-VENUS2-IF` | serveur interfaces — **SFTP de dépôt des sites** + démons d'import, Mirth | Softway Medical | ✅ **inventorié le 04/09/2026** ; ⚠️ contenu des échanges et chemin de publication |
| `192.168.111.65` | `TIM-VENUS3-DB` | base de données **partagée** (MariaDB 11.8, base `isotim`) | Softway Medical | ✅ **inventorié le 04/09/2026** ; ⚠️ **aucune sauvegarde** |

> L'autre RIS utilisé, **Xplore (EDL)**, est hébergé directement chez EDL :
> **hors périmètre** de cette documentation.

#### `TIM-VENUS1-AP` (`.63`) — le serveur applicatif, inventorié le 04/09/2026

Relevé : [`configs/inventaire-tim-venus1-ap-2026-09-04.md`](configs/inventaire-tim-venus1-ap-2026-09-04.md).

| | |
|---|---|
| Machine | **VM Proxmox** (QEMU i440FX, MAC `BC:24:11:CC:9D:F6`) — 8 vCPU, **16 Go**, 3 disques SATA virtuels (100 + 200 + 1024 Go) ; **migrée depuis VMware** (VMware Tools 10.3 à l'arrêt, carte encore nommée `vmxnet3`), QEMU Guest Agent et VirtIO actifs |
| OS | Windows Server 2022 **Standard** 21H2 (build 20348), installé le **29/12/2022**, workgroup, fuseau Paris ; dernier démarrage le 24/04/2026 (**uptime 133 j**) ; ⚠️ **licence Retail NON activée** (statut 5) |
| Réseau | `.63/24`, passerelle `.254`, **DNS `8.8.8.8`/`8.8.4.4`** (publics) |
| Stockage | C: 99 Go (39 libres) · **D: « VENUS » 200 Go — 4,8 Go libres** (`_VENUS` pèse 181 Go, `MariaDB` 1 Go) ⚠️ · E: « ARCHIVES » 1 To **vide** (1023,8 Go libres) |
| Applicatif | **IIS + PHP 7.2** (Windows Cache Extension, Composer, URL Rewrite) servant l'applicatif `D:\_VENUS\VENUS_PHP` ; **Mirth Connect 3.9.1.b263** (NextGen) sur **8080/8443** ; **MariaDB 10.6** locale (`--defaults-file=D:\MariaDB\data\my.ini`) — bases `venus` **485 Mo** et `mirthdb` 11 Mo ; **JasperReports Server 8.1.1 *et* 8.2.0** + Jaspersoft Studio (édition des comptes rendus), Java 8u481 ; service `Venus_Clean_Daemon` (via `srvany.exe`) ; QuickViewHL7, Git/TortoiseGit, Agent Ransack |
| Partages SMB | `deployment$` (`D:\nicesoft\02_deployment`), `VENUS_ARCHIVES`, `VENUS_DOCS` |
| Ports ouverts | 22 (notre sshd), 135, 139, **443**, 445, **3306**, 3389, 5357, 5985, **8080/8443** (Mirth) |
| Correctifs | ⚠️ **derniers KB d'avril 2023** (KB5025230/KB5022507/KB5025314) — plus rien depuis 3 ans |
| Sécurité | pare-feu **actif sur les 3 profils** ✅ ; Defender temps réel **actif**, signatures du 03/09/2026 ✅ ; **TeamViewer 15.81.5 en service** ⚠️ ; **Microsoft Office 2021 et OneDrive installés** sur un serveur de production ⚠️ |
| Comptes | 6 comptes locaux (2 actifs) ; administrateurs : `Administrateur`, `nicesoft_appli` |

> ⚠️ **`D:` est à 4,8 Go libres sur 200** — c'est le volume qui porte
> l'applicatif, la base et les archives de production. C'est le point le plus
> urgent des trois serveurs avec la sauvegarde de `.65` : `E:` (1 To) est
> pourtant vide et disponible.

#### `TIM-VENUS2-IF` (`.64`) — interfaces, SFTP des sites, inventorié le 04/09/2026

Relevé : [`configs/inventaire-tim-venus2-if-2026-09-04.md`](configs/inventaire-tim-venus2-if-2026-09-04.md).
Jumeau applicatif de `.63`, auquel s'ajoutent **le SFTP de dépôt des sites** et
**12 démons d'interface**.

| | |
|---|---|
| Machine | **VM Proxmox** (QEMU i440FX, MAC `BC:24:11:F1:C6:B7`) — 8 vCPU, **16 Go**, 2 disques (100 + 200 Go) ; migrée depuis VMware comme `.63` |
| OS | Windows Server 2022 **Standard** 21H2, installé le **29/12/2022** ; dernier démarrage le **03/09/2025 — uptime 366 jours** ⚠️ |
| Réseau | `.64/24`, passerelle `.254`, DNS publics |
| Stockage | C: 99 Go (22 libres) · D: « VENUS » 200 Go (88 libres) |
| Applicatif | même socle que `.63` : IIS/PHP 7.2, **Mirth Connect 3.9.1** (8080/8443), **MariaDB 10.6** locale, **JasperReports 8.1.1/8.2.0** (Tomcat 9 sur **8081**, **PostgreSQL** local sur 5432) ; Java 8u201, WinSCP 6.5.3, QuickViewHL7 |
| Démons d'interface | **12 services `Venus_*_Daemon`** lancés par `srvany.exe` depuis `D:\_VENUS\VENUS_PHP\services` : `Import_` Agen, Angers, Niort, Quimper, RouenCHB, Valence, Yon · `Capture_` Agen, Niort, Quimper · `Export` · `Clean`. ⚠️ Plusieurs tournent sous le **compte local `Nicesoft_Appli`** (mot de passe stocké dans le service), les autres en `LocalSystem` |
| SFTP des sites | **OpenSSH 9.8p2 de l'éditeur** (`C:\OpenSSH-Win64`, 18/04/2025) sur **`2222`**, `PubkeyAuthentication no`, mot de passe, **8 comptes `isoteam<site>` chrootés** vers `D:\_VENUS\VENUS_ITF\<SITE>`, algorithmes anciens activés « pour JSch/Mirth » (`ssh-rsa`, `dh-group1-sha1`, `aes*-cbc`, `hmac-sha1`) |
| Dépôts au 04/09/2026 | **7 sites actifs, tous écrits le jour même** : Agen 21 613 fichiers · Angers CH 17 217 · Rouen CHB 16 078 · Valence 10 123 · Quimper 9 772 · Yon 4 535 · Niort 2 597. Le 8ᵉ dossier est `POITIERSGIE-NE PAS UTILISE` (vide) — et ⚠️ **le chroot `…\VENUS_ITF\POITIERS` du compte `isoteampoitiers` n'existe pas** : ce compte ne peut pas se connecter |
| Ports ouverts | **2222** (SFTP éditeur), 135, 139, 445, **3306**, 3389, 5357, 5985, **8080/8443** (Mirth), 8081 (Tomcat), 5432 et 8005 en local |
| Correctifs | ⚠️ **derniers KB d'avril 2023** |
| Sécurité | ⚠️ **pare-feu désactivé sur les 3 profils** ; Defender temps réel actif, signatures du 04/09/2026 ✅ ; TeamViewer en service ⚠️ ; Office 2021 + OneDrive (**13 SID utilisateurs** ont des tâches OneDrive : beaucoup de sessions interactives sur ce serveur) ⚠️ |
| Partages SMB | `deployment$` (`D:\nicesoft\02_deployment`) |

> **Le SFTP reçoit bien des connexions venues d'Internet.** Au moment du relevé,
> 14 sessions étaient établies sur `2222` depuis **six adresses publiques
> distinctes** (sans enregistrement inverse) — ce sont les sites qui déposent.
> Mais le port **ne répond pas** depuis un VPS OVH sur les trois adresses
> publiques connues du site (`37.61.243.245`, `37.61.243.246`,
> `77.158.128.112`) : la publication est donc **filtrée par adresse source**, ou
> faite sur une autre adresse — ⚠️ **à faire préciser par le prestataire**, c'est
> le seul flux entrant d'Internet du RIS. Un SFTP en mot de passe, à
> chiffrement ancien, sur une machine sans correctif depuis avril 2023 et sans
> pare-feu local, mérite que ce filtrage soit **vérifié et documenté**.

#### `TIM-VENUS3-DB` (`.65`) — la base partagée, inventorié le 04/09/2026

Relevé : [`configs/inventaire-tim-venus3-db-2026-09-04.md`](configs/inventaire-tim-venus3-db-2026-09-04.md).
**C'est la base de données de production du RIS** : `.63` et surtout `.64` s'y
connectent en permanence (nombreuses sessions établies vers `3306` au moment du
relevé). Machine bien plus récente que les deux autres.

| | |
|---|---|
| Machine | **VM Proxmox** (QEMU **Q35**, VirtIO, MAC `BC:24:11:34:A0:21`, lien **10 Gbps**) — **4 vCPU, 8 Go** seulement pour le serveur de base ⚠️ ; 3 disques VirtIO (120 + 750 + 750 Go) |
| OS | Windows Server 2022 **Standard** 21H2, installé le **13/07/2025**, licence **OEM active** ; dernier démarrage le 30/07/2026 (uptime 36 j) |
| Réseau | `.65/24`, passerelle `.254`, DNS publics |
| Stockage | C: 119 Go (83 libres) · D: « VENUS » 750 Go — **748 libres** (ne contient que `D:\sql`, des exports ponctuels de sept. 2025) · **E: « BACKUP BDD » 750 Go — 0 fichier, totalement vide** ⚠️ |
| Base | **MariaDB 11.8.2** — base de production **`isotim` ≈ 2,1 Go**, plus `mysql`/`sys`. ⚠️ Les données sont dans **`C:\Program Files\MariaDB 11.8\data`**, le chemin d'installation par défaut **sur `C:`** — ni sur `D:` (750 Go dédiés, vides) ni protégées par un volume séparé |
| Écoute | **3306 sur toutes les interfaces**, 22 (notre sshd), 80 (`http.sys`), 135, 139, 445, 3389, 5985 |
| Correctifs | ⚠️ **aucun depuis l'installation** : les 3 KB présents datent du 13/07/2025 |
| Sécurité | ⚠️ **pare-feu désactivé sur les 3 profils** ; Defender temps réel actif ✅ ; TeamViewer en service ⚠️ ; WinSCP, QuickViewHL7 |
| Comptes | 5 comptes locaux (2 actifs) ; administrateurs : `Administrateur`, `Nicesoft_Appli` |

> ⚠️⚠️ **La base de production du RIS n'est pas sauvegardée.** Le volume `E:`,
> nommé « BACKUP BDD » et dimensionné à 750 Go, est **vide (0 fichier)** ;
> **aucune tâche planifiée** de sauvegarde n'existe sur la machine (les seules
> tâches non-Microsoft sont celles d'Edge). Les seuls exports retrouvés sont
> **manuels et anciens** : `isotim_backup.sql` (883 Mo) du **10/12/2025** dans
> le dossier `Downloads` d'un compte d'administration, et `D:\sql\event\event.sql`
> (245 Mo) du 30/09/2025. **C'est le point le plus grave de l'inventaire** : une
> perte de la VM ou une corruption de `isotim` ferait perdre neuf mois de RIS.
> À porter à Softway Medical **et** au prestataire (qui sauvegarde les VM du
> Proxmox du site ? ⚠️ inconnu — voir [checklist](#checklist-de-collecte)).

> ⚠️ **Points de vigilance communs aux trois VENUS** : Windows Server 2022 **sans
> correctif** (avril 2023 pour `.63`/`.64`, juillet 2025 pour `.65`) ;
> **pare-feu Windows désactivé sur `.64` et `.65`** (le filtrage repose
> entièrement sur le pfSense, dont les règles nous sont ⚠️ inconnues) ;
> **TeamViewer actif sur les trois** (canal d'accès tiers, comme sur le PACS et
> les syngo) ; DNS publics `8.8.8.8` sur des serveurs de données de santé ;
> `.64` n'a pas redémarré depuis **366 jours** ; licence Windows **non activée**
> sur `.63`. Ces serveurs sont **supervisés depuis le 05/09/2026**
> ([Supervision](#supervision-05092026)) — mais toujours **pas sauvegardés** à
> notre connaissance.

##### Accès SSH aux serveurs VENUS (04/09/2026)

Accès par clé posé sur les **trois** serveurs, tous **Windows Server 2022
Standard** (build 20348), compte local **`nicesoft_appli`** (membre du groupe
Administrateurs), passerelle par défaut `192.168.111.254` (pfSense principal).
Clé `id_ed25519` du poste dans `C:\ProgramData\ssh\administrators_authorized_keys`
(ACL SID `S-1-5-32-544`/`S-1-5-18`), mot de passe interdit. Alias `venus1`,
`venus2`, `venus3` dans le `~/.ssh/config` du poste. Chemin : **le poste est
pair du VPN nomades du pfSense** (`172.31.0.3`, tunnel `DC-TELLIS2`, voir
[`tun_wg0`](#tun_wg0--vpn-nomades-du-site)) — c'est cette source, et non
`10.90.0.0/24`, qu'admet la règle pare-feu.

| Serveur | Ce qui a été fait | Détail |
|---|---|---|
| `venus1` (.63) | OpenSSH **installé** par nos soins | capacité Windows native **8.1p1**, service auto, clé seule, règle pare-feu `ssh-in` (TCP 22 depuis `172.31.0.3`, `10.90.0.0/24`) — pare-feu **actif** sur les 3 profils |
| `venus3` (.65) | idem | capacité native **9.5p1** ; pare-feu **désactivé** sur les 3 profils (règle posée mais inerte, filtrage au pfSense) |
| `venus2` (.64) | **cohabitation** dans un sshd préexistant | ⚠️ un **OpenSSH 9.8p2** de l'éditeur (`C:\OpenSSH-Win64`, 18/04/2025) écoutait déjà sur **`2222`** : serveur **SFTP de dépôt HL7**, mot de passe, `PubkeyAuthentication no` global, chroot par site — **8 comptes** `isoteam<site>` (Valence, Agen, Angers CH, Poitiers, Quimper, Rouen CHB, Yon, Niort) vers `D:\_VENUS\VENUS_ITF\<SITE>`, algorithmes anciens « pour JSch/Mirth » |

> **VENUS2-IF est le point d'entrée SFTP des interfaces.** L'inventaire du même
> jour a tranché : **Mirth Connect tourne sur les VENUS eux-mêmes** (`.63` et
> `.64`, ports 8080/8443), pas seulement sur TIMWFMCORE — la mention
> « JSch/Mirth » de la config désigne la bibliothèque SSH de Mirth. Les dépôts
> viennent des **7 sites, par Internet** (voir la fiche de `.64` ci-dessus).
> **Ne pas durcir ce sshd** :
> interdire le mot de passe couperait les dépôts. Notre accès admin par clé
> **cohabite** sans y toucher — un bloc `Match Group administrators`
> (`PubkeyAuthentication yes` + `administrators_authorized_keys`) ajouté en fin
> de `sshd_config` **avec l'accord de Softway (04/09/2026)** : la clé n'ouvre que
> les comptes administrateurs, les 8 comptes SFTP restent en mot de passe
> (vérifié). Sauvegarde de la config d'origine dans
> `sshd_config.avant-tim-<horodatage>`. `ssh venus2` vise donc le **port 2222**.

> Le script [scripts/installer-openssh-windows.ps1](scripts/installer-openssh-windows.ps1)
> a servi aux trois : installation native ou MSI signé en repli, clé + ACL,
> durcissement validé par `sshd -t` avant redémarrage, règle pare-feu limitée à
> la source admin. Il **s'arrête en diagnostic** devant un sshd préexistant
> (cas de `.64`) — rien n'est modifié sans `-ForcerConfigExistante`.

> ⚠️ **À signaler** : les trois VENUS sont en Windows Server 2022 **sans
> correctif depuis avril 2023** (`.63` : KB de 04/2023) ; le pare-feu Windows est
> **désactivé** sur `.64` et `.65` (actif sur `.63`) — le filtrage repose
> entièrement sur le pfSense. OpenSSH 8.1/9.5 sans échange de clés
> post-quantique.

##### Supervision (05/09/2026)

Les trois sont dans **Zabbix depuis le 05/09/2026**, par **agent 2 en mode
actif** (`TIM-VENUS1-AP`, `TIM-VENUS2-IF`, `TIM-VENUS3-DB`) : l'agent sort vers
`10.40.0.60:10051` par `wg2`, donc **aucun port entrant n'a été ouvert** — ce
qui compte sur `.63`, seul des trois à avoir son pare-feu allumé. Sont
surveillés le processeur, la mémoire, tous les volumes, les services et les
journaux d'événements, plus des sondes de service : **SFTP `2222` des sites**
et **MariaDB `3306`** en High (donc mail), web/IIS `443`, Tomcat `8081`,
RDP `3389`, ICMP. **Mirth Connect est suivi par l'état de son service** et non
par son port : il écoute sur 8080 mais n'est pas publié sur le réseau du `.63`
(pare-feu actif, aucune règle), une sonde externe y aurait alarmé en permanence
sur un service sain. Le `D:` saturé a un **déclencheur High dédié à hystérésis**
(problème au-dessus de 90 %, retour sous 85 %), le gabarit seul l'aurait laissé
en Average sans mail. Mise en œuvre, chiffres et pièges :
[17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026).

### À identifier

| IP | Machine | Rôle | Statut |
|---|---|---|---|
| `192.168.101.54` | VM Ubuntu `prod01` (`tim-ubuntu`) | bannière « **PROD01 GESTION ISOTEAM Prod server** » ✅ (25/08/2026) — serveur de production de l'application de gestion ISOTEAM ; VM (NIC virtio `ens18`), adresse par DHCP depuis `.62` ; services précis ⚠️ ([checklist](#checklist-de-collecte)) | ⚠️ |
| `.49`, `.50`, `.97`, `.99`, `.101`, `.104` → `.109`, et l'essentiel de `192.168.111.0/24` | — | jamais déclarées : libres ou occupées ? | ⚠️ demander la liste au prestataire |

---

## Les deux pfSense et le routage interne

Ce qui est établi :

- le pfSense principal a une patte dans chacun des trois sous-réseaux
  (`192.168.101.59`, `192.168.101.110`, `192.168.111.254`) — constaté lors de la
  mise en place du tunnel ;
- il porte des **routes statiques** vers `10.40.0.0/24` et `10.90.0.0/24` via le
  tunnel `wg2` ;
- les **routes retour explicites** ne concernent que les serveurs dont la
  passerelle est le second pfSense `.62` (bloc production) : VENUS (`.254`) et
  Syngo (`.110`) répondent déjà au pfSense principal — vérifié dans les deux
  sens le 05/09/2026
  ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026)).
  Elles existent sur `192.168.101.52` (`10.40.0.0/24`, `10.90.0.0/24`,
  `172.32.0.0/24` et, depuis le 11/09/2026, `172.31.0.0/24`) et sur
  `192.168.101.53` (`172.31.0.0/24` seulement, 11/09/2026) — voir
  [le diagnostic](#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données) ;
- constaté le 25/08/2026 sur `prod01` : la passerelle par défaut des serveurs
  du bloc production est **le second pfSense `.62`** (via DHCP), pas le `.59` —
  d'où la nécessité des routes retour explicites ;
- le 25/08/2026, il a été prouvé que **les connexions *initiées* depuis le LAN
  TELLIS vers nos réseaux étaient bloquées** (depuis `prod01` : `10.40.0.1`,
  `.10` et `.40` injoignables, capture vide côté cluster, alors que les
  *réponses* aux flux initiés de chez nous passaient) : la patte `.59` — 
  interface **`OPT1_TIM`** dans le pfSense — n'avait **aucune règle `pass`**,
  donc deny par défaut.

### Règles posées sur `OPT1_TIM` le 25/08/2026 (sens TELLIS → DC OVH)

| Proto | Source | Destination | Description |
|---|---|---|---|
| IPv4 * | alias `SRV_TIM_WFMCORE` | alias `DC_OVH_TIM` | — |
| IPv4 * | `192.168.101.54` (prod01) | alias `DC_OVH_TIM` | « prod01 vers DC OVH » |

Validées aussitôt : ping prod01 → `10.40.0.40` en 17–23 ms TTL 126, session
TCP complète ([15-pacs-secours.md](15-pacs-secours.md#mesures-du-25082026)).
✅ **`SRV_TIM_WFMCORE` identifié le 29/08/2026** : c'est la Vue PACS
`TIMWFMCORE` (`192.168.101.52`), le PACS principal — la règle l'autorise vers
`DC_OVH_TIM` ; aucun flux ne l'emprunte à ce jour.
⚠️ Reste à relever le contenu de l'alias `DC_OVH_TIM` (vraisemblablement
`10.40.0.0/24` — inclut-il `10.90.0.0/24` ?) — dans la
[checklist de collecte](#checklist-de-collecte) du pfSense. Règles en
« tout protocole / tout port » : à restreindre quand les flux réels seront
arrêtés ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)).

Ce qui est inconnu ⚠️ : les règles de filtrage internes et le NAT du second
pfSense `.62` — on sait désormais (25 et 29/08/2026) qu'il est **passerelle par
défaut + DHCP + DNS du bloc production**, mais pas ce qu'il filtre ; et qui
route réellement entre les trois sous-réseaux (lui seul ? le routeur `.60` ?).

### Diagnostic du 11/09/2026 — le retour par le second pfSense coupe les données

**Symptôme.** Depuis le poste, `mstsc` vers `192.168.101.52` et `.53` échoue,
et le SSH direct vers `.52` n'a jamais rendu sa bannière (constat du 30/08,
attribué à tort à un trou noir MTU). Pourtant le port s'ouvre : le SYN-ACK
revient, un paquet RDP malformé reçoit son RST en 30 ms, `ping` passe, et un
paquet de 1392 octets sans fragmentation aussi. Seuls les **segments qui
portent des données** du serveur n'arrivent jamais — réponse X.224 du RDP,
bannière SSH, `ServerHello` TLS de Vue Motion.

**Ce qui l'a tranché : le TTL des réponses.** Les serveurs Windows partent de
128, chaque routeur retire 1 ; depuis WSL, le NAT du poste compte un saut de
plus.

| Cible | TTL reçu | Routeurs sur le retour côté site | Données du serveur |
|---|---|---|---|
| `.52`, `.53` depuis le poste, **avant** correction | 125 | 2 : `.62` puis `.59` | ❌ perdues |
| `.98` syngo, `.63` VENUS1 depuis le poste | 126 | 1 : le pfSense principal | ✅ |
| `.52` depuis pacs03 (`172.32.0.2`, route retour existante) | 127 | 1 | ✅ RDP négocie, bannière SSH |
| `.53` depuis pacs03 (aucune route retour vers `172.32.0.0/24`) | — | — | ❌ rien ne revient |
| `.52`, `.53` depuis le poste, **après** correction | 126 | 1 | ✅ |

La table de routage de TIMWFMCORE (`route print -4`, lecture seule, par
pacs03) l'a confirmé : routes **persistantes** via `.59` pour `10.40.0.0/24`,
`10.90.0.0/24`, `172.32.0.0/24` (pacs03) et trois pairs du prestataire
(`10.0.241.54` le PACS Xplore, `172.29.88.6`, `10.0.101.1`), une route
`192.68.36.0/29` via `.57` (SRSA Philips), route par défaut `.62` — et **rien
pour `172.31.0.0/24`**, la plage des nomades. Les paquets du poste entrent par
`.59`, la réponse ressort par `.62` ; ce second pfSense relaie bien vers `.59`
(d'où le SYN-ACK, le RST et le ping qui reviennent) mais, ne voyant que la
moitié de la connexion, jette les segments de données.

**Correction, posée le 11/09/2026 sur `.52` et `.53`**, la même que celle que
le prestataire applique à ses propres pairs VPN :

```
route -p add 172.31.0.0 mask 255.255.255.0 192.168.101.59
```

Vérifié aussitôt depuis le poste : TTL 125 → 126 sur les deux, négociation RDP
complète (`RDP_NEG_RSP`, protocole NLA), bannière SSH de `.52` en direct, HTTPS
de Vue Motion `.53` en 0,6 s. L'alternative, si le prestataire préfère corriger
à la source, est d'autoriser les flux asymétriques sur `.62` (« bypass firewall
rules for traffic on the same interface » ou règle à état *sloppy*). Le piège
est consigné
([07-pieges.md](07-pieges.md#39-une-connexion-qui-souvre-puis-se-tait--la-réponse-revient-par-lautre-pare-feu)).

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

**Le poste d'administration est lui-même un pair de ce VPN** (tunnel
« DC-TELLIS2 » côté Windows, adresse `172.31.0.3/32`, `AllowedIPs`
`192.168.101.48/28`, `192.168.101.96/28` et `192.168.111.0/24`) — constaté le
04/09/2026 en cherchant pourquoi une règle pare-feu « SSH depuis `10.90.0.0/24` »
jetait les paquets du poste sur VENUS1. C'est par ce tunnel, et non par
`wg0`→OPNsense→`wg2`, que le poste joint les serveurs TELLIS : le tunnel
OPNsense du poste ne porte que `10.40.0.0/24` et `10.90.0.0/24`. Les serveurs
voient donc le poste en **`172.31.0.3`** — vérifié par `netstat` sur syngovia1,
TSplus et VENUS1. Conséquences : (1) toute règle pare-feu locale « depuis le
poste » doit admettre `172.31.0.3` (et `10.90.0.0/24` seulement pour le jour où
la route basculerait sur OPNsense) — c'est le défaut de
[scripts/installer-openssh-windows.ps1](scripts/installer-openssh-windows.ps1) ;
(2) le « SSH direct » vers syngo, TSplus et VENUS ne prouve rien sur le chemin
`wg2`, qui n'a été éprouvé que vers `.52` ; (3) l'exposition de la clé
`tun_wg0` nous concerne aussi comme utilisateur : sa rotation changera la
configuration du poste.

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
| `.58`/`.103` ProxyVia (`dicomproxy`) | `.98`, `.100` Syngo Via | DICOM **104** | **répartition round-robin** des examens entre les deux (repli croisé, mapping par PatientID) | ✅ tranché le 09/09/2026 : `viaGroup RR`, aucune règle par examen ([inventaire](configs/inventaire-dicomproxy-2026-09-09.md)) |
| sites (`172.18.162.40:11112`), PACS Xplore (`10.0.241.54:104`) | `.58`/`.103` ProxyVia `DP_EC:9104` | DICOM | arrivée des examens sur le répartiteur | ✅ 12 SCP déclarés, ~38 000 images le 09/09 |
| `.58`/`.103` ProxyVia | `.52` TIMWFMCORE `:2104` | DICOM (store, Q/R) | PACS amont (`MoveDestination` réécrites) | ✅ constaté le 09/09 |
| PACS Xplore EDL `10.0.241.54` (`XPLORE_PACS`), pacs03 `172.32.0.2` (`XPLORE_SECOURS`) | `.52` TIMWFMCORE `:2104`, AET **`TODAY`** (et `URGENCE`) | DICOM C-STORE | envoi des examens Xplore vers le Vue PACS | ✅ constaté le 11/09 dans le journal DICOM du serveur (5 315 et 294 associations le 10/09) |
| `.53` Vue Motion | `.52` Vue PACS `:2104` | MVSMAIN (protocole Vue) | lecture des images pour le visualiseur web | ✅ constaté le 11/09/2026 : connexions permanentes `.53` → `.52:2104` ([inventaire](configs/inventaire-timvueexplorer-2026-09-11.md)) |
| `.102` TSplus | `.98`, `.100` Syngo Via | client syngo.via (47101, 80/443, 32912…) | l'Enterprise Browser publié par TSplus interroge **les deux** serveurs | ✅ constaté le 02/09 (caches de configuration des deux serveurs sur TSplus, mêmes statistiques de connexion sur les deux) |
| `.98` ↔ `.100` Syngo Via | — | syngo (fédération) | chaque serveur connaît l'autre (Enterprise Browser) | ✅ constaté le 02/09 |
| Internet | `.102` TSplus | TCP 443 (+ 80 : redirection et défis ACME) | NAT du pfSense principal, WAN `37.61.243.246` | ✅ confirmé le 02/09 (même certificat et même redirection des deux côtés) |
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
- [x] ~~port forwards NAT — confirmer `443` et `80` → `192.168.101.102` (TSplus)~~ — **confirmés le 02/09/2026** de l'extérieur (même certificat sur 443, même redirection sur 80 depuis Internet et depuis le LAN) ; la règle elle-même reste à lire dans l'export
- [ ] table de routage (qui route entre les trois sous-réseaux ?)
- [ ] baux DHCP statiques, s'il est serveur DHCP
- [ ] pairs des tunnels `tun_wg0` et `tun_wg2` (noms et `AllowedIPs`, pas les clés)

**pfSense principal `192.168.101.59`** (suite) :

- [ ] contenu de l'alias `DC_OVH_TIM` (règles `OPT1_TIM` — `SRV_TIM_WFMCORE`
      identifié le 29/08 : `192.168.101.52`)

**pfSense « FW-Passerelle » `192.168.101.62`** :

- [x] ~~son rôle~~ — **passerelle par défaut + DHCP + DNS du bloc production**
      (constaté sur prod01 le 25/08 et TIMWFMCORE le 29/08/2026)
- [ ] ce qu'il filtre, son NAT, interfaces, règles, export `config.xml`

**Vue PACS `TIMWFMCORE` `192.168.101.52`** — inventorié le 29/08/2026
([relevé](configs/inventaire-timwfmcore-2026-08-29.md)) ; reste :

- [x] refaire le relevé **avec droits admin** — fait le 30/08/2026 par SSH
      ([Accès SSH](#accès-ssh-30082026))
- [x] rôle de la 2ᵉ patte `192.168.171.1/24` et du réseau `192.168.171.0/24` —
      **réseau de stockage FIR** du PACS, serveurs de fichiers `.2`/`.3` montés
      en `M:`/`N:` (découvert en admin le 30/08)
- [ ] l'hyperviseur qui la porte (MAC `BC:24:11` → Proxmox VE probable) : où,
      qui l'administre, quelles autres VM ?
- [x] sauvegarde applicative et Oracle : **chaîne de tâches Carestream vers
      `G:` local** (30/08), **sauvegardé quotidiennement hors-machine par
      TELLIS** (confirmé 30/08) — reste à documenter côté TELLIS la destination
      et la rétention si une restauration doit être pilotée de notre côté
- [ ] **pare-feu Windows local** : désactivé, décision à prendre avec
      l'exploitant du DC après cartographie des flux (cf. Accès SSH)
- [ ] qui utilise AnyDesk / TeamViewer / Octopus Deploy sur cette machine ?
- [ ] politique de correctifs — figés depuis mars 2025, arbitrage éditeur
      Philips à clarifier
- [x] ~~l'hyperviseur sauvegarde-t-il la VM ?~~ — **oui, visible depuis la VM** :
      snapshot quotidien à 23:30 (erreurs VSS 8194 + QEMU Guest Agent), audit
      du 11/09/2026 ; destination et rétention côté TELLIS toujours à préciser
- [ ] **capacité de `G:`** (1 To pour ~2 semaines de RMAN, copie hebdo de
      200 Go, 259 Go libres le 11/09) et rétention : à faire préciser à TELLIS
- [ ] **plantages `svstream.exe`/`svdser.exe`** (3 à 56 par jour, audit du
      11/09), `Watchdog_SvMax` cassé, Mirth muet sur 8014 (cause connue le
      11/09 : keystore invalide, serveur web jamais démarré), règle Auto-Router
      « copy to VIACLUSTER » en échec en boucle, tablespace
      `MEDISTORE_MEDIUM_INX` à 6,5 % : à escalader à Philips
- [ ] **notification des nouvelles études vers MyTIM / MyISOTEAM** : endpoint
      livré côté `gestion`, règles Info Router à poser
      ([relevé du 11/09](#notification-des-nouvelles-études-vers-mytim--relevé-du-11092026))
- [ ] agent Zabbix 7.4.1 sur un serveur 7.0.30 : rétrograder vers l'agent LTS
      (le script d'installation impose 7.0.30, un 7.4.1 a déjà planté sur pacs03)
- [ ] envois EDL rompus (10/09) : transmettre à EDL le tableau de l'audit du
      11/09 (le PACS acquitte, le pair aborte), demander le renvoi des deux
      séries et la correction du VR `OW`/`OB`

**Vue Motion `TIMVUEEXPLORER` `192.168.101.53`** — inventorié le 11/09/2026
([relevé](configs/inventaire-timvueexplorer-2026-09-11.md)) ; reste :

- [ ] remplacer la règle d'installation `OpenSSH-Server-In-TCP` (portée *Any*)
      par `ssh-in` limitée à `172.31.0.3` — étape 5 du script, échouée le 11/09
      (piège n° 40) ; sans effet tant que le profil pare-feu *Private* est
      désactivé, mais à faire pour rester cohérent
- [ ] **pare-feu Windows sans effet** (profil *Private* désactivé) : décision à
      prendre avec l'exploitant du DC — cartographie simple ici (80/443
      entrants, `.52:2104` sortant)
- [ ] qui utilise AnyDesk (actif, 7070) / TeamViewer (installé) sur cette
      machine ? même question que pour TIMWFMCORE
- [ ] raccorder à Zabbix : l'agent passe (pas de WDAC), mais il faut d'abord
      une route vers `10.40.0.0/24` via `.59` (aucune aujourd'hui)
- [ ] nom servi par IIS sur 443 et échéance du certificat `timvueexplorer.pfx`
      (`D:`, 09/12/2025) — à rapprocher de
      [14-noms-de-domaine.md](14-noms-de-domaine.md)
- [ ] l'hyperviseur qui la porte (QEMU/KVM, MAC hors préfixe Proxmox) :
      le même Proxmox que TIMWFMCORE et les VENUS ?

**Syngo Via `syngovia-135104` `.98` et `syngovia-135113` `.100`** — inventoriés le 02/09/2026
([relevé `.98`](configs/inventaire-syngovia-135104-2026-09-02.md),
[relevé `.100`](configs/inventaire-syngovia-135113-2026-09-02.md)) ; reste :

- [x] ~~répartition des rôles entre les deux serveurs~~ — **pas de
      répartition : deux instances jumelles fédérées** (02/09/2026)
- [x] ~~règle de routage DICOM de ProxyVia : quels examens vont sur `.98`,
      lesquels sur `.100` ?~~ — **répartition round-robin**, aucune règle par
      examen, repli croisé et mapping par PatientID (09/09/2026, [inventaire](configs/inventaire-dicomproxy-2026-09-09.md))
- [ ] qui pose les correctifs Windows (lots du 11/12/2025, 27/08 et
      31/08/2026) — Siemens par SRS, ou TELLIS ?
- [ ] Defender temps réel désactivé sur les deux : exigence Siemens
      documentée, ou oubli ?
- [ ] `N:` System_Backup presque plein sur les deux — qui purge ? et la
      sauvegarde `M:`/`N:` est-elle copiée hors machine par TELLIS ?
- [x] ~~raccorder les deux serveurs à Zabbix~~ — **fait le 02/09/2026 sans
      agent** (SNMP + ICMP + sondes TCP par `wg2`,
      [17-zabbix.md](17-zabbix.md#serveurs-syngo-via-de-tellis--sans-agent-02092026)) ;
      l'agent est **refusé par WDAC** (MSI signé Zabbix SIA, code 1625)
- [ ] demander à Siemens l'ajout de l'agent Zabbix à la liste blanche WDAC
      (services et journaux Windows restent invisibles en SNMP)
- [ ] adresse iLO des deux DL380 (et du DL360 TSplus)
- [ ] harmoniser les masques (`.98` en /28, `.100` en /24)
- [ ] `.100` : supprimer le compte administrateur en doublon `Matthieu CAPON`

**TSplus `win-srv-tsplus` `.102`** — inventorié le 02/09/2026
([relevé](configs/inventaire-win-srv-tsplus-2026-09-02.md)) ; reste :

- [ ] **correctifs Windows figés depuis le 11/12/2025** sur un serveur exposé
      à Internet : qui en a la charge ?
- [ ] **aucune sauvegarde depuis le 09/09/2025** : décider quoi sauvegarder
      (configuration TS2log, profils) et où
- [ ] **second facteur** : activer l'add-on 2FA de TS2log ou raccorder au SSO
      ([16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026))
- [ ] qui opère le Datto RMM / Splashtop installé dessus ?
- [ ] masque `/24` alors que le plan d'adressage dit `/28`

**VM `prod01` `192.168.101.54`** :

- [ ] `ss -tlnp` — quels services écoutent ?
- [ ] `docker ps` le cas échéant, services systemd actifs
- [ ] version d'OS, qui l'administre et pour quoi faire

**Reverse proxy nginx `192.168.101.61`** :

- [ ] `nginx -T` — noms servis, backends, certificats et leurs échéances — à
  rapprocher de l'inventaire des noms ([14-noms-de-domaine.md](14-noms-de-domaine.md))

**RIS VENUS** (les trois serveurs sont inventoriés depuis le 04/09/2026) :

- [x] ~~flux HL7 de `TIM-VENUS2-IF` : correspondants, sens, ports~~ — **SFTP
  `2222`**, dépôt **entrant** des **7 sites actifs** (Agen, Angers CH, Rouen CHB,
  Valence, Quimper, Yon, Niort) dans des chroots par site, repris par 12 démons
  `Venus_*_Daemon` et Mirth Connect local ; résolu le 04/09/2026
- [x] ~~sauvegarde de la base `TIM-VENUS3-DB` : qui, comment, testée ?~~ —
  tranché le 04/09/2026 : **il n'y en a aucune** (volume `E:` « BACKUP BDD »
  vide, aucune tâche planifiée, dernier export manuel du 10/12/2025) →
  **action ouverte** dans [06-reste-a-faire.md](06-reste-a-faire.md)
- [ ] **par où le SFTP `2222` est-il publié ?** — connexions établies depuis 6 IP
  publiques, mais aucune réponse depuis un VPS externe sur `37.61.243.245/.246`
  ni `77.158.128.112` : NAT filtré par source, ou autre adresse ⚠️
- [ ] **qui sauvegarde les VM du Proxmox de TELLIS ?** (aucune sauvegarde
  visible *dans* les VM VENUS — la protection ne peut venir que de l'hyperviseur)
- [ ] `D:` de `TIM-VENUS1-AP` à **4,8 Go libres** : purge, extension, ou bascule
  des archives sur `E:` (1 To vide) — à traiter avec Softway
- [ ] chroot manquant de `isoteampoitiers` (`…\VENUS_ITF\POITIERS`) : compte à
  supprimer ou dossier à créer
- [x] ~~raccorder les trois serveurs à Zabbix~~ — **fait le 05/09/2026**, agent 2
  en mode actif ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026))
- [ ] superviser l'**existence** d'une sauvegarde de `isotim` le jour où elle
  existera (âge du dernier fichier de `E:`) ; la mémoire de `.65` (8 Go) est
  déjà en Average permanent depuis le raccordement
- [ ] contact support Softway Medical

**Prestataire** :

- [ ] identité, contacts, périmètre contractuel, statut HDS
- [ ] procédure d'accès admin (la nôtre et la sienne)
- [ ] **l'informer de l'exposition de la clé `tun_wg0`** et suivre la rotation
      ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts))

**Divers** :

- [x] ~~confirmer la double patte ProxyVia `.58`/`.103` et son rôle de pont DICOM~~ — ✅ **fait le 09/09/2026** : `ens18`=`.103` (bloc syngo), `ens19`=`.58` (bloc imagerie), répartiteur DICOM `DP_EC` ([inventaire](configs/inventaire-dicomproxy-2026-09-09.md))
- [ ] liste des adresses réellement occupées (la demander, ne pas scanner un
      site de production)
- [ ] poser les routes retour sur chaque serveur du bloc production que nous
      devons joindre, ou trancher pour un NAT côté pfSense — ✅ `.52`
      (`10.40.0.0/24`, `10.90.0.0/24`, `172.32.0.0/24`, `172.31.0.0/24`) et
      `.53` (`172.31.0.0/24`) au 11/09/2026 ([diagnostic](#diagnostic-du-11092026--le-retour-par-le-second-pfsense-coupe-les-données)) ; restent
      `.51`, `.55`, `.56`, `.57` si un jour il faut les joindre
