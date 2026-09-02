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
| `192.168.101.48/28` | `.49` → `.62` | bloc imagerie et production (PACS, IA, passerelles, équipements réseau) | ✅ **`.62`** (second pfSense) — constaté sur prod01 (25/08) et TIMWFMCORE (29/08), distribué par DHCP ; le `.59` ne sert que les routes vers nos réseaux |
| `192.168.101.96/28` | `.97` → `.110` | bloc Syngo Via (serveurs, TSplus, ProxyVia) | ✅ **`.110`** (pfSense principal) — constaté le 02/09/2026 sur les trois serveurs inventoriés ; ⚠️ **masques incohérents** : `.98` est en /28 mais `.100` et `.102` sont en **/24** (voir [Syngo Via](#syngo-via)) |
| `192.168.111.0/24` | `.1` → `.254` | RIS VENUS | ⚠️ `.254` (patte pfSense) probable, à confirmer |
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
| `192.168.101.59` | pfSense principal | pare-feu du site, serveur du tunnel `wg2` et du VPN nomades `tun_wg0` ; pattes `192.168.101.59`, `192.168.101.110`, `192.168.111.254` | ⚠️ | pattes ✅ (mise en place du tunnel, 14/08/2026) ; règles, NAT et WireGuard ⚠️ à vérifier précisément |
| `192.168.101.62` | pfSense « FW-Passerelle » | **second pfSense** — c'est lui la **passerelle par défaut des serveurs du bloc production** (et leur DHCP : route `proto dhcp` sur prod01) ; rôle complet et règles ⚠️ | ⚠️ | ✅ passerelle+DHCP constatés sur prod01 le 25/08/2026 ; le reste ⚠️ |
| `192.168.101.61` | Reverse proxy nginx | reverse proxy local du site — noms servis, certificats et backends inconnus | ⚠️ | 📋 existence, ⚠️ rôle |
| `192.168.101.60` | Routeur vers Philips | routage vers l'environnement Philips (lié au PACS et à la télémaintenance ?) | ⚠️ | 📋 existence, ⚠️ rôle |

### Imagerie Philips

Le cœur métier du site : le PACS (*Picture Archiving and Communication
System*), qui archive les examens d'imagerie et les distribue aux stations de
lecture.

| IP | Machine | Rôle | Éditeur | Statut |
|---|---|---|---|---|
| `192.168.101.52` | Vue PACS — **`TIMWFMCORE`** | **PACS principal de TIM** : archivage et distribution des examens, tout l'applicatif + base Oracle 19 locale ; alias pfSense `SRV_TIM_WFMCORE` | Philips | ✅ joignabilité `wg2` testée (14/08) ; ✅ **inventorié le 29/08/2026** (voir ci-dessous) |
| `192.168.101.53` | Vue Motion | visualiseur web « zéro empreinte » de la gamme Vue : consultation des images depuis un simple navigateur, sans client lourd | Philips | 📋 |
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
la [checklist](#checklist-de-collecte)).

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
`PasswordAuthentication no`. **Chemin obligatoire : rebond par pacs03** —
l'alias `ssh timwfmcore` du `~/.ssh/config` le fait (`ProxyJump pacs03`). La
connexion directe poste→`192.168.101.52` par le VPN nomade **échoue à l'échange
de bannière** (trou noir MTU sur le chemin `wg0`→OPNsense→`wg2`) alors que le
port TCP s'ouvre : passer par pacs03, dont le tunnel direct TELLIS arrive en
`172.32.0.2`, contourne le problème.

> **Pare-feu Windows : laissé désactivé, volontairement.** Contrairement à
> pacs03 (nu sur Internet), TIMWFMCORE est un serveur **de production interne
> derrière les deux pfSense de TELLIS**, opéré par le prestataire, avec des
> dizaines de flux LAN (modalités, RIS, IA, Vue Motion, syngo, FIR…). Poser un
> pare-feu local ici sans cartographie complète couperait la production. C'est
> une décision à prendre **avec l'exploitant du DC**, pas un oubli — le point
> reste ouvert dans la [checklist](#checklist-de-collecte).

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
| `192.168.101.103` | ProxyVia | routage DICOM vers Syngo Via | — | 📋 |

> **ProxyVia est double-attaché** : `192.168.101.103` dans ce bloc **et**
> `192.168.101.58` dans le bloc imagerie — `.58` n'est donc pas une adresse
> libre. Vraisemblablement le pont DICOM entre les deux sous-réseaux
> (modalités/PACS → Syngo Via), ⚠️ à confirmer.

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
l'autre est en amont, dans le routage DICOM de ProxyVia** (⚠️ à documenter).
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
| Supervision | **aucune de notre côté** (pas d'agent Zabbix, contrairement à TSplus) ; SNMP et HPE AMS (iLO) actifs, `hponcfg` absent — adresse iLO ⚠️ inconnue |
| Sauvegarde | tâche **`\Siemens\Backup_syngo.via`** (base → `M:`, partition système → `N:`) + **Windows Server Backup quotidien à 03:00** (7 versions, dernier ✅ 02/09/2026 03:00) — **tout sur disques locaux**, `N:` quasi plein ; **`E:` (16,6 To d'images) n'est pas sauvegardé**, cohérent si syngo.via ne fait que du post-traitement (l'archive reste le PACS) ⚠️ à confirmer ; copie hors-machine par TELLIS ⚠️ inconnue |
| Correctifs | **à jour** : KB5120241/5120242/5120705 posés le 27/08 (`.98`) et le 31/08/2026 (`.100`), lot précédent du 11/12/2025 ; Windows Update en « télécharger et notifier », service à l'arrêt : les correctifs sont posés par lots lors d'interventions (Siemens ? TELLIS ? ⚠️), suivis d'un redémarrage (31/08 04:33 et 01/09 01:06). Le `Setup` SQL Server de `.100` est passé en 16.0.1190 le 31/08, `.98` est resté en 16.0.1000 |
| Sécurité | pare-feu Windows **actif** sur les trois profils (≈ 700 règles) ; **Defender : protection temps réel DÉSACTIVÉE sur les deux** (service actif, signatures à jour) — WDAC compense en partie, mais reste à confirmer comme exigence Siemens ⚠️ ; RDP, WinRM (5985) et SMB (partages Siemens `Activity Settings`, `WorkflowTemplates`) ouverts |
| Comptes | **634 / 635 comptes locaux** (629 / 630 actifs) — la même base d'utilisateurs que TSplus, recréée sur chaque serveur ; 9 et 10 administrateurs : `adminUser`, `alocal`, `aremote`, `jbouteiller`, `MedAdmin`, `RemoteAdmin`, `siemens_apps`, `SyngoCmd0`, plus `mcapon` (`.98`) et `matthieu` **et** `Matthieu CAPON` (`.100`, doublon à nettoyer) |

> ⚠️ **Points de vigilance** : Defender temps réel coupé sur les deux serveurs ;
> `N:` (System_Backup) presque plein sur les deux — la sauvegarde système
> finira par échouer ; aucune sauvegarde hors-machine visible ; aucune
> supervision de notre côté ; 630 comptes locaux à mot de passe, non fédérés
> ([candidats SSO](16-keycloak.md#candidats-au-raccordement--étude-du-27082026)) ;
> masques réseau incohérents entre jumeaux.

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
| Supervision | **Zabbix Agent 2 7.4.3** → hôte `WIN-SRV-TSPLUS` ✅ ([17-zabbix.md](17-zabbix.md)) ; HPE AMS |
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
**Contrairement à TIMWFMCORE, la connexion directe poste → serveur par le VPN
nomade fonctionne, sans rebond par pacs03** : scp et sessions longues passent.
La différence tient vraisemblablement au chemin retour — ces trois serveurs
sortent par le pfSense principal (`.110`), TIMWFMCORE par le second pfSense
(`.62`) — ⚠️ hypothèse, non vérifiée.

Le script d'inventaire est copié, exécuté puis supprimé : **rien n'est laissé
sur les serveurs** (mode d'emploi en tête de
[scripts/inventaire-windows.ps1](scripts/inventaire-windows.ps1)).

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
- mais **les routes retour n'ont été posées que sur `192.168.101.52`** : les
  autres serveurs répondent à leur passerelle par défaut et sont injoignables
  depuis chez nous tant qu'ils n'ont pas reçu le même traitement — point ouvert
  documenté dans
  [06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts) ;
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
`TIMWFMCORE` (`192.168.101.52`), le PACS principal — la règle prépare donc le
futur flux de réplication PACS principal → PACS de secours par `wg2`.
⚠️ Reste à relever le contenu de l'alias `DC_OVH_TIM` (vraisemblablement
`10.40.0.0/24` — inclut-il `10.90.0.0/24` ?) — dans la
[checklist de collecte](#checklist-de-collecte) du pfSense. Règles en
« tout protocole / tout port » : à restreindre quand les flux réels seront
arrêtés ([06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts)).

Ce qui est inconnu ⚠️ : les règles de filtrage internes et le NAT du second
pfSense `.62` — on sait désormais (25 et 29/08/2026) qu'il est **passerelle par
défaut + DHCP + DNS du bloc production**, mais pas ce qu'il filtre ; et qui
route réellement entre les trois sous-réseaux (lui seul ? le routeur `.60` ?).

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
| `.58`/`.103` ProxyVia | `.98`, `.100` Syngo Via | DICOM **104** | routage des examens vers Syngo Via | ✅ SCP DICOM 104 en écoute sur les deux serveurs (02/09) ; la source ProxyVia et la règle de répartition entre les deux restent 📋 |
| `.53` Vue Motion | `.52` Vue PACS | — | lecture des images pour le visualiseur web | 📋 présumé |
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

**Syngo Via `syngovia-135104` `.98` et `syngovia-135113` `.100`** — inventoriés le 02/09/2026
([relevé `.98`](configs/inventaire-syngovia-135104-2026-09-02.md),
[relevé `.100`](configs/inventaire-syngovia-135113-2026-09-02.md)) ; reste :

- [x] ~~répartition des rôles entre les deux serveurs~~ — **pas de
      répartition : deux instances jumelles fédérées** (02/09/2026)
- [ ] règle de routage DICOM de ProxyVia : quels examens vont sur `.98`,
      lesquels sur `.100` ?
- [ ] qui pose les correctifs Windows (lots du 11/12/2025, 27/08 et
      31/08/2026) — Siemens par SRS, ou TELLIS ?
- [ ] Defender temps réel désactivé sur les deux : exigence Siemens
      documentée, ou oubli ?
- [ ] `N:` System_Backup presque plein sur les deux — qui purge ? et la
      sauvegarde `M:`/`N:` est-elle copiée hors machine par TELLIS ?
- [ ] raccorder les deux serveurs à Zabbix (agent absent) — après accord
      Siemens (WDAC)
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
