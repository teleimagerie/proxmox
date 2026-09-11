# Audit de `TIMWFMCORE` (Vue PACS Philips, 192.168.101.52) — 11/09/2026

Relevé **en lecture seule** par SSH (rebond pacs03, compte `Administrator`,
PowerShell *FullLanguage*), entre 12 h 05 et 13 h 05. Rien n'a été déposé ni
modifié sur la machine pendant l'audit : les commandes PowerShell ont été
passées par l'entrée standard, l'archive 7z des journaux lue en flux (`7z e -so`).
Les seules modifications de la journée sont postérieures et documentées
([13-tellis.md](../13-tellis.md), [17-zabbix.md](../17-zabbix.md)) : reconfiguration
de l'agent Zabbix, route retour `172.31.0.0/24` (session parallèle).

Aucun nom de patient ne figure ici ; les deux dossiers analysés sont désignés
par leurs horodatages.

## Machine

| | |
|---|---|
| Dernier démarrage | 01/06/2026 16:48 — **102 jours** d'uptime |
| RAM | 11 Go libres / 64 |
| Disques physiques | 4 × VirtIO SCSI (350 Go, 2 To, 700 Go, 4 To), tous `Healthy`, pas de compteurs SMART (VM) |
| Lecteurs réseau | `M:` `\\192.168.171.3\FIR_TIM\fir_fs_04` et `N:` `\\192.168.171.2\FIR_TIM` : **Unavailable** (déjà le 30/08) |
| Services auto non démarrés | uniquement du Windows bénin (Remote Registry, Software Protection, Google Updater…) ; **tout l'applicatif Imaginet/Oracle/Mirth/Kafka tourne** |

## Volumes (12 h 10)

| Vol. | Label | Taille | Libre | % libre | Depuis le 30/08 |
|---|---|---|---|---|---|
| C: | SYSTEM | 299 Go | 97 Go | 32 % | — |
| D: | Service | 50 Go | 47 Go | 93 % | — |
| F: | Database | 2 000 Go | **301 Go** | 15 % | **−36 Go** (≈ 3 Go/j) |
| G: | BACKUP | 1 000 Go | **259 Go** | 26 % | **−120 Go** |
| I: | Images02_TO_NOT_USED | 4 096 Go | 4 056 Go | 99 % | — |
| E: | (sans label) | 0 | — | — | volume fantôme, `OperationalStatus Unknown` |

`F:\imaginet_db` = 1 696 Go (4 737 fichiers), plus un `save_room_can_be_deleted.txt`
de 1,9 Go (11/08/2025) : la réserve d'urgence habituelle des DBA.

## Sauvegarde RMAN sur `G:`

`G:\Backup` = 740,7 Go, 3 943 fichiers :

| Dossier | Taille | Dernier fichier |
|---|---|---|
| `oradata\mst1\backup` | 739,8 Go | 11/09 09:32 `back_archive_detailed.ok_…` |
| `DBInfo` | 0,7 Go | 11/09 00:35 `DBInfo_TIMWFMCORE_mst1_2026-09-11_FRI-001557.zip` |
| `cfg_backup` | 0,1 Go | 10/09 23:02 `TIMWFMCORE_cfg.exp.1.log` |
| `scripts` | — | verrou `backup_RMAN_mstore.lck` 11/09 09:30 |

Rythme constaté sur 30 jours (Go écrits par jour) : **~30-38 Go/j d'archivelogs**
(`AL_*`, toutes les 3 h : 00:30, 03:30, 06:30, 09:30…) et une **copie complète
des datafiles le vendredi** (`COPY\DF_*` : 211 Go le 29/08, 197 Go le 05/09).
Aucun fichier de plus de 1 Go antérieur au 29/08 : la rétention effective est
d'**environ deux semaines**, la copie de la semaine N−2 étant purgée après celle
de la semaine N. Marge au moment du relevé : 259 Go libres pour une copie de
~200 Go attendue le 12/09.

Sauvegarde hyperviseur : le journal Application porte **deux erreurs VSS 8194
chaque jour à 23:30** (System Writer, « Access is denied », bénigne) depuis au
moins le 28/08 — signature d'un snapshot Proxmox quotidien avec gel par le
`QEMU Guest Agent` (service actif ; `QEMU Guest Agent VSS Provider` arrêté).

## Oracle 19 (`mst1`)

- `ORACLE_HOME = C:\oracle\product\19\db`, `ORA_DBA` = `Administrator`, `SYSTEM`.
- `sqlplus / as sysdba` en session SSH : **ORA-01017** (l'authentification OS ne
  passe pas dans un jeton de session SSH). Aucune requête en base possible sans
  mot de passe applicatif.
- `alert_mst1.log` : 24 Ko, aucune ORA- récente.
- Le contrôle interne du PACS (`check_oracle_free_space.pl`) répète toutes les
  15 min : **`MEDISTORE_MEDIUM_INX` à 6,5 % libre** (721 237 Mo utilisés /
  771 053 Mo, plus gros espace contigu 8,7 Go).

## Journaux applicatifs (`C:\Program Files\Carestream\System5\log`)

Archivage quotidien en `logs_backup\logs_<date>.7z` (~125-130 Mo/jour) ; le
`SVDSER.log` du jour fait 190 Mo à midi, le `Dicom_Log\SVDSER_Dicom_Log.log`
du 10/09 pèse 2,4 Go décompressé.

Occurrences `ERROR|FATAL|SEVERE` dans les journaux modifiés depuis 24 h (extrait) :

| Fichier | Occurrences | Motif dominant |
|---|---|---|
| `SVDSER.log` | 135 324 | `Unsupported store service or no TX accepted by peer` vers `192.168.101.56` (Secondary Capture, X-Ray Dose SR) ; `DIDB_StringNoCaseConv` ; `Illegal routing table entry grid_name is empty` ; `FIR_Access::WriteImage failed` |
| `SecurityManagerService.log` | 73 174 | `verify_initialization` (~10 000/j), `GetState: Last activity dictionary doesn't contain the SId` |
| `AutoRouter.SchedulingModule.log` | 19 122 | `Filters List: Failed to add filter` (~9 600/j) |
| `svar.log` | 6 741 | `Frame <n> is out of range` ; **`Token Validity Time is Wrong`** (~1 000/j — horloge d'un client en dérive ?) |
| `Loader.log` | 924 | `Error on recv - errno 10054`, `close connection to the application` |
| `Scheduled_Tasks\Watchdog_SvMax.log` | 438 | `admincommand status FAILED … The specified executable is not a valid application` — **watchdog cassé** |

Contrôles internes (`Imaginet System Check`, `system_checks\`) : `check_mirth` →
**CRITICAL « Mirth is not listening on port 8014 »**, `check_patient_data` →
CRITICAL 19 864 études sans ordre RIS, `check_oracle_free_space` → WARNING (voir
plus haut), `check_storage` → F: 82 % utilisé, `check_cpu` → charges 55-77,
`check_uptime` → WARNING permanent. Personne ne lisait ces résultats avant le
raccordement Zabbix du 11/09.

## Plantages

Dossier `crashes\` (vidages compressés) : **3 à 17 par jour, 56 le 08/09**,
depuis au moins le 12/08. Journal Application, événements 1000 des trois
derniers jours (extrait) :

| Date | Processus | Module | Code |
|---|---|---|---|
| 11/09 11:40, 03:15 ; 10/09 16:51 | `svstream.exe` | `ntdll.dll` | 0xc0000374 (corruption de tas) |
| 11/09 08:12, 05:45, 05:21 ; 10/09 19:13, 10:46, 09:27, 05:59 ; 09/09 17:24, 16:57, 05:44 ; 08/09 ×4 | `svstream.exe` | `conn.dll` | 0xc0000005 |
| **10/09 21:51, 18:41, 11:17, 10:32, 01:02** ; 09/09 10:04 ; 08/09 14:25 | **`svdser.exe`** (serveur DICOM) | `MSVCR100.dll` | 0xc0000005 |
| 10/09 22:00 | `fir_autodelete.exe` | `ADDll.dll` | 0xc0000409 |
| 10/09 00:50 | `svwfm.exe` | `ucrtbase.dll` | 0xc0000409 |
| 09/09 13:57 | `svar.exe` | `MSVCR100.dll` | 0xc0000005 |
| 08/09 12:30 | `svfload.exe` | `ntdll.dll` | 0xc0000374 |

`Imaginet PACS Restarter Service` relance les processus ; `SVDSER` est
multi-processus (500 à 650 démarrages/arrêts de processus par heure dans le
journal DICOM, un par association), donc un plantage n'emporte que les
associations servies par le processus touché. Le plantage de 01:02:53 suit
immédiatement, dans le même processus, un `PostUpdatePatientEx - new patient
already exist` puis `FIR WriteImage failed` sur une image venue de `10.0.241.54`.

## Agent Zabbix (avant correction)

- Agent 2 **7.4.1** (serveur 7.0.30 LTS), `Server=ServerActive=zabbix.teleimagerie.net`
  → résolu `57.130.34.122` : l'agent sortait **par Internet**, pas par `wg2`.
- `zabbix_agent2.log` : `cannot connect … i/o timeout` 1 à 5 fois par jour du
  07 au 11/09.
- Service **terminé inopinément le 05/09 14:08** (SCM 7034) ; `sc qfailure` :
  aucune action de récupération.
- Depuis `.52`, `10.40.0.60:10051` est joignable (TCP) par `wg2`.

## Les deux envois EDL du 10/09 (AET cible `TODAY`)

`TODAY` est un AE title du Vue PACS (5 572 `Called AE: TODAY` dans le journal
DICOM du jour, appelé par `XPLORE_PACS` 10.0.241.54 — 5 315 — et
`XPLORE_SECOURS` pacs03 — 294). Les cinq ruptures rapportées par les journaux
EDL se retrouvent à la milliseconde dans `SVDSER_Dicom_Log.log` du 10/09 :

| Association (pid,tid) | Called AE | Ouverte | C-STORE reçus | Dernier échange | Rupture |
|---|---|---|---|---|---|
| 20880,01156,0b | TODAY | 00:18:11 | 118, tous SUCCESS | C-STORE reçu 00:18:40.738, réponse pas encore partie | **abort reçu du pair 00:18:41.844** |
| 20880,01156,0c | TODAY | 00:18:42 (reprise) | 31, tous SUCCESS | réponse SUCCESS 00:19:20.093 | abort reçu du pair 00:19:20.110 |
| 03540,56492,0d | TODAY | — | 676, tous SUCCESS | réponse SUCCESS 02:06:20.397 | **abort reçu du pair 02:06:20.413** |
| 53908,07628,09 | TODAY | 02:06:00 | 219, tous SUCCESS | réponse SUCCESS 02:06:29.206 | **abort reçu du pair 02:06:29.233** |
| 26480,02144,06 | URGENCE | — | 102, tous SUCCESS | réponse SUCCESS 02:06:29.205 | **abort reçu du pair 02:06:29.223** |

Le serveur n'a **émis aucun abort** de la journée (0 `Sent ABORT`), n'a pas planté
à ces instants et n'a rien journalisé d'anormal dans `SVDSER.log` sur ces
créneaux, hormis des avertissements `Dicom_ME::ConstructFromBuffer -> Incorrectly
encoded encapsulated data within pixel data, OW instead of OB, trying to recover`
(126 sur les créneaux examinés, tous depuis 10.0.241.54, objets JPEG Lossless
— non-conformité d'encodage corrigée à la volée et stockée en SUCCESS, sans lien
avec les ruptures). Deux associations distinctes tombant à 10 ms d'écart
désignent l'émetteur EDL ou le chemin réseau EDL → TELLIS, pas le PACS.
