# Inventaire dicomproxy (ProxyVia) - 09/09/2026

_Relevé par SSH (`ssh dicom@192.168.101.58`, clé du poste posée le 09/09) avec des
commandes en lecture seule. Aucun fichier déposé ni modifié sur la machine, aucun
fichier de mot de passe lu. À fusionner dans [13-tellis.md](../13-tellis.md)._

## Identité

| | |
|---|---|
| Hostname | `dicomproxy` |
| Modèle | QEMU Standard PC (i440FX + PIIX, 1996) — KVM, virtualisation complète |
| OS | Debian GNU/Linux 11 (bullseye) |
| Noyau | `5.10.0-35-amd64` (5.10.237-1, 19/05/2025) — **tourne encore sur le -35** |
| Uptime | **439 jours** (aucun redémarrage) |
| Fuseau | Europe/Paris (CEST, +0200) |
| Rôle | Siemens syngo.via **DicomProxy VB10B** — répartiteur DICOM |

## Matériel (VM QEMU/KVM du Proxmox de site)

| | |
|---|---|
| vCPU | 4 × QEMU Virtual CPU version 2.5+ |
| RAM | 7,8 Gio (2,4 utilisés, 5,2 en cache) ; swap 974 Mio |
| Disque | `sda` 128 Go → `sda1` 127 Go ext4 `/` (**13 % utilisé, 103 Go libres**), `sda5` 975 Mo swap ; `sr0` cdrom |
| Agent | QEMU Guest Agent actif, VirtIO — MAC `bc:24:11:*` (même parc que VENUS/syngo) |

## Réseau (double patte confirmée)

| Interface | Adresse | MAC | Rôle |
|---|---|---|---|
| `ens18` | `192.168.101.103/28` | `bc:24:11:80:2d:13` | bloc syngo, **passerelle par défaut `.110`** |
| `ens19` | `192.168.101.58/28` | `bc:24:11:d0:b1:82` | bloc imagerie |

Routes statiques (`/etc/network/interfaces.d/routes`) vers les réseaux des sites,
toutes **par `192.168.101.59` (pfSense principal)** sur `ens19` :
`10.0.241.54`, `172.18.162.40`, `172.29.88.6`, `172.31.0.0/24`, `172.32.0.0/24`.

DNS déclarés : `192.168.150.1`, `192.168.250.1` — **injoignables** (résolution KO,
voir Horloge). `/etc/hosts` associe `192.168.101.103` à `dicomproxy`.

## Ports en écoute

| Port | Proc | Portée | Rôle |
|---|---|---|---|
| 22 | sshd | 0.0.0.0 | SSH |
| 5432 | postgres | **0.0.0.0** | PostgreSQL `registry` — voir point d'attention |
| 8443 | tomcat (java) | * | portail d'administration DicomProxy |
| 9104 | dp-ec (java) | * | **AET `DP_EC`, le répartiteur DICOM** |
| 5445 | dp-ec (java) | * | port RRT (relais retrieve) du DicomProxy |

## Rôle DICOM (config `/opt/dicomproxy/ec/cfg/`)

`/opt/DicomProxy.info` : `DP_VERSION=VB10B`, base `/opt/dicomproxy/ec`, `PORT=9104`.
`proxy.properties` : `serialNumber 200147`, `setupNumber 2017701`, `proxy.aet DP_EC`,
`proxy.host 0.0.0.0:9104`, `clusterAet VIACLUSTER`, `map.usePatientId true`.

**Deux syngo.via en aval, en répartition round-robin (`viaGroup RR`) avec repli croisé :**

| AET | Hôte | Port | loadIndex | Repli |
|---|---|---|---|---|
| `SYNGOVIA-135104` | `192.168.101.98` | 104 | 1 | vers 135113 |
| `SYNGOVIA-135113` | `192.168.101.100` | 104 | 1 | vers 135104 |

`viaQr.order = SYNGOVIA-135104\SYNGOVIA-135113`, `rrtServer = SYNGOVIA-135104`,
`viaMapper.auto = true` (mapping par PatientID, base `registry`).

**PACS amont** (`pacs.0`) : `timwfmcoreFIR` = **TIMWFMCORE `192.168.101.52:2104`**
(alias `ST,QR` — store + query/retrieve). C'est la destination des `MoveDestination`
réécrites (journal `modifiedMessages.log` : `SYNGOVIA-* -> VIACLUSTER -> timwfmcoreFIR`).

**12 SCP déclarés** (`ae.properties`, `scp.count = 12`) :

| AET | Hôte:port | Site |
|---|---|---|
| `XPLORE_PACS` | `10.0.241.54:104` | PACS Xplore |
| `ISO-TELE`, `ISO-SAI1`, `TELI_VALENCE`, `ISO-CHAN`, `ISO-ANGERS`, `ISO_CIMROD`, `ISO-CHPOIT`, `ISO-CHARP`, `ISO-CHB`, `TELI_DENIS` | `172.18.162.40:11112` | ISO-TELE + Saintes, Valence, Agen, Angers, Périgueux, Poitiers, Quimper, Rouen CHB, St-Denis Réunion |
| `DP_TEST` | `localhost:9105` | SCU de test dcm4che |

**Trafic le jour du relevé** (`dicominfo.log`/`statistic.log` du 09/09) : ~38 000
`C-STORE-RQ` en entrée, dont **ISO-TELE 10 085** et **XPLORE_SECOURS 638** ; ~425
associations en sortie vers `timwfmcoreFIR` (135113 : 228, 135104 : 197). Le proxy
fonctionne normalement. `proxy.log` montre des `EOFException`/fermetures inattendues
sporadiques côté `SYNGOVIA-135113 -> timwfmcoreFIR` (associations coupées, non bloquant).

## Services et logiciels

| Service | État | Détail |
|---|---|---|
| `dp-ec.service` | actif | DicomProxy, JVM `-Xmx2048M`, dcm4che 2.0.29, log4j 2.19.0 |
| `tomcat-main.service` | actif | Apache Tomcat 9.0.104, portail admin sur 8443 (User=tomcat, durci systemd) |
| `postgresql@13-main` | actif | PostgreSQL 13.23, base `registry` |
| `qemu-guest-agent`, `ssh`, `cron`, `rsyslog`, `unattended-upgrades` | actifs | — |

Java = OpenJDK 11.0.32 (paquet Debian). Dépôt APT propre à l'éditeur :
`https://dicomproxy.siemens-healthineers.com/debian bullseye main` (+ `-security`).
`unattended-upgrades` actif ; dernières transactions apt les 11, 22 et 27/08/2026.
Certificats : `/opt/dicomproxy/ssl/djppdsasyglb01.imed*`, `/opt/tomcat/ssl/2ndWildcard2024_full_seimens.jks`.

## Base de données `registry` (PostgreSQL 13)

| | |
|---|---|
| Base | `registry`, propriétaire `dicom`, ~37 Mo |
| Tables | `location` (**61 577 lignes**), `usersettings` |
| Contenu de `location` | patid, **patname, patdob, patsex**, studyuid, accno, modalities, studydesc, viaaet (serveur cible), srcaet… — donc des **identités patients** |
| Écoute | `listen_addresses = '*'` sur `0.0.0.0:5432` |

## Sauvegarde

Cron `dicom` : `02 1 * * *` → `tar` de `/opt/dicomproxy` vers `/backup`, purge à
`25 2` de ce qui dépasse 6 jours. Présent : 7 jours de `ec_dicomproxy_*.tgz` (7,7 Mo)
et `ec_tomcat_*.tgz` (56 Mo). **Ni la base `registry` ni la config du portail admin
ne sont sauvegardées.** (Le portail dispose d'un `BackupCreator`/`ConfigDistributor`
interne pour distribuer `ae.properties` entre nœuds, sans rapport avec une sauvegarde.)

## Comptes et accès

| Compte | uid | Détail |
|---|---|---|
| `dicom` | 1000 | admin applicatif, membre `sudo` (dont `NOPASSWD: CFG_CMDS`), home actif |
| `siemens` | 1001 | **compte de maintenance éditeur**, membre `sudo`, home quasi vide |
| `tomcat` | 998 | service Tomcat |
| `postgres` | 106 | service PostgreSQL |

`~dicom/.ssh/authorized_keys` : une clé RSA préexistante **+ la clé ed25519 du poste**
(déposée le 09/09 à 14:50). Historique `last` : connexions depuis `194.138.39.18`
(Siemens) jusqu'en octobre, et depuis `172.31.0.3` (le poste par le `tun_wg0`) le 09/09.
`sshd` : mot de passe autorisé (défaut), aucun `sshd_config.d`.

## Points d'attention

1. **PostgreSQL exposé sur le LAN sans mot de passe (données patients).** Écoute
   `0.0.0.0:5432` et `pg_hba` fait confiance au bloc syngo : depuis le réseau, via
   `192.168.101.103`, une connexion `psql` aboutit **sans mot de passe** pour `dicom`
   **et pour `postgres` (superutilisateur)** — vérifié le 09/09. La table `location`
   contient des identités patients. (Le même essai via `192.168.101.58` est refusé :
   `pg_hba` ne couvre pas ce bloc.) → **ticket Siemens, priorité 1**.
2. **Horloge décalée d'environ 10 min 20 s en retard.** `System clock synchronized: no` ;
   NTP actif mais `Server: n/a`, car `*.pool.ntp.org` ne résout pas (DNS injoignables).
   La sortie 443 et la passerelle fonctionnent. → ticket Siemens.
3. **Redémarrage en attente depuis le 05/08/2026** (`/var/run/reboot-required`, noyau)
   et **439 jours d'uptime** ; 10 noyaux installés. → ticket Siemens (fenêtre).
4. **Journaux à 12 Go**, niveau DEBUG (`/opt/dicomproxy/ec/log`, ~850 Mo/jour ;
   log4j2 conserve 2-3 jours d'archives gz). → ticket Siemens (repasser en INFO ?).
5. **Sauvegarde incomplète** : base `registry` et config portail hors du `tar`. → ticket Siemens.
6. **Supervision** : hôte `DICOMPROXY` ajouté à Zabbix le 09/09 (ICMP + sondes TCP
   9104/5432/8443 depuis le CT 204) — voir [17-zabbix.md](../17-zabbix.md).
