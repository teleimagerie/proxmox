# Inventaire tim-venus3-db - 04/09/2026 23:34

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

## Identite

| | |
|---|---|
| Hostname | `TIM-VENUS3-DB` (workgroup WORKGROUP) |
| Modele | QEMU Standard PC (Q35 + ICH9, 2009) |
| OS | Microsoft Windows Server 2022 Standard 21H2 (build 20348) |
| Installe le | 13/07/2025 |
| Dernier boot | 30/07/2026 10:17 (uptime 36 j 13 h) |
| Fuseau | Romance Standard Time |
| Licence | active - OEM:DM |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| CPU 0 | QEMU Virtual CPU version 2.5+ | 4c/4t | 2.6 GHz |

## RAM

**8 Go** en 1 barrette(s) sur 1 slot(s), 8 Go max, ECC multi-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| DIMM 0 | 8 Go | type 7 |  MHz | QEMU  |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere |   |
| Numero de serie |  |
| BIOS | 3.20230228-4 du 06/06/2023 |

## GPU

| Carte | Pilote | VRAM annoncee |
|---|---|---|
| Microsoft Basic Display Adapter | 10.0.20348.1 du 21/06/2006 | - |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | Red Hat VirtIO | SCSI | Unspecified | 120 Go | Healthy |
| 1 | Red Hat VirtIO | SCSI | Unspecified | 750 Go | Healthy |
| 2 | Red Hat VirtIO | SCSI | Unspecified | 750 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| - |  | FAT32 | 0.1 Go | 0.1 Go |
| - |  | NTFS | 0.6 Go | 0.1 Go |
| C: |  | NTFS | 119.3 Go | 82.9 Go |
| D: | VENUS | NTFS | 750 Go | 747.7 Go |
| E: | BACKUP BDD | NTFS | 750 Go | 749.9 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| Ethernet | Red Hat VirtIO Ethernet Adapter | `BC-24-11-34-A0-21` | 10 Gbps | Up |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| Ethernet | 192.168.111.65/24 | 192.168.111.254 | 8.8.8.8, 8.8.4.4 |

## Roles et fonctionnalites

- **Serveur Web (IIS)** (`Web-Server`)
- **Services de fichiers et de stockage** (`FileAndStorage-Services`)

Fonctionnalites : Web-WebServer, Web-Common-Http, Web-Static-Content, Web-Default-Doc, Web-Http-Errors, Web-Dir-Browsing, Web-Health, Web-Http-Logging, Web-Performance, Web-Stat-Compression, Web-Security, Web-Filtering, Web-App-Dev, Web-Asp-Net45, Web-CGI, Web-Net-Ext45, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-WebSockets, Web-Mgmt-Tools, Web-Mgmt-Console, Storage-Services, NET-Framework-45-Features, NET-Framework-45-Core, NET-Framework-45-ASPNET, NET-WCF-Services45, NET-WCF-TCP-PortSharing45, Windows-Defender, AzureArcSetup, WoW64-Support, System-DataArchiver, PowerShellRoot, PowerShell, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| 7-Zip 25.00 (x64) | 25.00 | Igor Pavlov |  |
| Agent Ransack | 9.3.3522.1 | Mythicsoft Ltd | 22/07/2025 |
| MariaDB 11.8 (x64) | 11.8.2.0 | MariaDB Corporation Ab |  |
| Microsoft Edge | 152.0.4191.62 | Microsoft Corporation | 04/09/2026 |
| Microsoft Visual C++ 2015 Redistributable (x64) - 14.0.23026 | 14.0.23026.0 | Microsoft Corporation |  |
| QuickViewHL7 |  |  |  |
| TeamViewer | 15.81.5 | TeamViewer |  |
| Virtio-win-guest-tools | 0.1.271 | Red Hat, Inc. |  |
| WinSCP 6.1.2 | 6.1.2 | Martin Prikryl | 23/07/2025 |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| BalloonService (`BalloonService`) | Running | LocalSystem | "C:\Program Files\Virtio-Win\Balloon\blnsvr.exe" |
| Microsoft Edge Update Service (edgeupdate) (`edgeupdate`) | Stopped | LocalSystem | "C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /svc |
| MariaDB (`MariaDB`) | Running | NT SERVICE\MariaDB | "C:\Program Files\MariaDB 11.8\bin\mysqld.exe" "--defaults-file=C:\Program Files\MariaDB 11.8\data\my.ini" "MariaDB" |
| Microsoft Defender Service de base (`MDCoreSvc`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MpDefenderCoreService.exe" |
| QEMU Guest Agent (`QEMU-GA`) | Running | LocalSystem | "C:\Program Files\Qemu-ga\qemu-ga.exe" -d --retry-path |
| Spice Agent (`spice-agent`) | Stopped | LocalSystem | "C:\Program Files\Spice Agent\vdservice.exe" |
| TeamViewer (`TeamViewer`) | Running | LocalSystem | "C:\Program Files\TeamViewer\TeamViewer_Service.exe" |
| Service antivirus Microsoft Defender (`WinDefend`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MsMpEng.exe" |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 22 | ::, 0.0.0.0 | sshd (sshd) |
| TCP | 80 | :: | System |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 192.168.111.65 | System |
| TCP | 445 | :: | System |
| TCP | 3306 | ::, 0.0.0.0 | mysqld (MariaDB) |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 5357 | :: | System |
| TCP | 5939 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 5985 | :: | System |
| TCP | 47001 | :: | System |
| TCP | 49664 | ::, 0.0.0.0 | lsass (KeyIso, SamSs, VaultSvc) |
| TCP | 49665 | ::, 0.0.0.0 | wininit |
| TCP | 49666 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 49667 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 49668 | ::, 0.0.0.0 | svchost (SessionEnv) |
| TCP | 49669 | ::, 0.0.0.0 | spoolsv (Spooler) |
| TCP | 49670 | ::, 0.0.0.0 | svchost (PolicyAgent) |
| TCP | 49671 | ::, 0.0.0.0 | services |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 192.168.111.65 | System |
| UDP | 138 | 192.168.111.65 | System |
| UDP | 500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| UDP | 3702 | ::, 0.0.0.0 | svchost (FDResPub) |
| UDP | 4500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 5353 | ::1, 192.168.111.65 | TeamViewer_Service (TeamViewer) |
| UDP | 5353 | ::, 0.0.0.0 | svchost (Dnscache) |
| UDP | 5355 | ::, 0.0.0.0 | svchost (Dnscache) |

## Partages SMB

Aucun partage non administratif.

## Taches planifiees hors Microsoft

| Tache | Etat | Action |
|---|---|---|
| \MicrosoftEdgeUpdateTaskMachineCore | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /c |
| \MicrosoftEdgeUpdateTaskMachineUA | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /ua /installsource scheduler |

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5062793 | Security Update | 13/07/2025 |
| KB5062572 | Security Update | 13/07/2025 |
| KB5062063 | Update | 13/07/2025 |

## Securite locale

Microsoft Defender : service actif, protection temps reel active, signatures du 03/09/2026, moteur 1.1.26080.3

| Profil pare-feu | Actif | Entrant par defaut | Sortant par defaut |
|---|---|---|---|
| Domain | **NON** | NotConfigured | NotConfigured |
| Private | **NON** | NotConfigured | NotConfigured |
| Public | **NON** | NotConfigured | NotConfigured |

## Comptes locaux

**5 comptes locaux** : 2 actifs, 3 desactives.

Membres du groupe Administrateurs : `TIM-VENUS3-DB\Administrateur` (Utilisateur, Local), `TIM-VENUS3-DB\Nicesoft_Appli` (Utilisateur, Local)
