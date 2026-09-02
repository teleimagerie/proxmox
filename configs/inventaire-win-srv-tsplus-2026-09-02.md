# Inventaire win-srv-tsplus - 02/09/2026 15:59

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

## Identite

| | |
|---|---|
| Hostname | `win-srv-tsplus` (workgroup WORKGROUP) |
| Modele | HPE ProLiant DL360 Gen11 |
| OS | Microsoft Windows Server 2022 Standard 21H2 (build 20348) |
| Installe le | 14/05/2025 |
| Dernier boot | 06/06/2026 17:44 (uptime 87 j 22 h) |
| Fuseau | Romance Standard Time |
| Licence | active - OEM:SLP |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| Proc 1 | INTEL(R) XEON(R) SILVER 4510 | 12c/24t | 2.4 GHz |

## RAM

**32 Go** en 2 barrette(s) sur 16 slot(s), ECC multi-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| PROC 1 DIMM 3 | 16 Go | DDR5 | 4400 MHz | Micron MTC10F1084S1RC56BG1 |
| PROC 1 DIMM 10 | 16 Go | DDR5 | 4400 MHz | Micron MTC10F1084S1RC56BG1 |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere | HPE ProLiant DL360 Gen11 |
| Numero de serie | CZUD2L01LZ |
| BIOS | 2.44 du 17/01/2025 |

## GPU

| Carte | Pilote | VRAM annoncee |
|---|---|---|
| Microsoft Remote Display Adapter | 10.0.20348.3451 du 21/06/2006 | - |
| Microsoft Remote Display Adapter | 10.0.20348.3451 du 21/06/2006 | - |
| Microsoft Remote Display Adapter | 10.0.20348.3451 du 21/06/2006 | - |
| Microsoft Remote Display Adapter | 10.0.20348.3451 du 21/06/2006 | - |
| NVIDIA T1000 | 32.0.15.7306 du 22/04/2025 | 4 Go |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | HPE MR408i-o Gen11 | RAID | SSD | 446.6 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| A: |  | NTFS | 0.6 Go | 0.1 Go |
| B: |  | FAT32 | 0.1 Go | 0 Go |
| C: |  | NTFS | 201.8 Go | 51.9 Go |
| D: | Backup | NTFS | 244.1 Go | 194.7 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| PCIe Slot 15 Port 2 | Broadcom NetXtreme Gigabit Ethernet #3 | `8C-84-74-EF-9C-47` | 0 bps | Not Present |
| PCIe Slot 1 Port 2 | Broadcom P210tep NetXtreme-E Dual-port 10GBASE-T Ethernet PCIe Adapter #2 | `8C-84-74-39-3E-61` | 0 bps | Not Present |
| PCIe Slot 15 Port 4 | Broadcom NetXtreme Gigabit Ethernet #4 | `8C-84-74-EF-9C-49` | 1 Gbps | Up |
| PCIe Slot 1 Port 1 | Broadcom P210tep NetXtreme-E Dual-port 10GBASE-T Ethernet PCIe Adapter | `8C-84-74-39-3E-60` | 0 bps | Not Present |
| PCIe Slot 15 Port 3 | Broadcom NetXtreme Gigabit Ethernet #2 | `8C-84-74-EF-9C-48` | 0 bps | Not Present |
| PCIe Slot 15 Port 1 | Broadcom NetXtreme Gigabit Ethernet | `8C-84-74-EF-9C-46` | 0 bps | Not Present |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| PCIe Slot 15 Port 4 | 192.168.101.102/24 | 192.168.101.110 | 8.8.8.8 |

## Roles et fonctionnalites

- **File and Storage Services** (`FileAndStorage-Services`)
- **Web Server (IIS)** (`Web-Server`)

Fonctionnalites : Storage-Services, Web-WebServer, Web-App-Dev, Web-WebSockets, NET-Framework-45-Features, NET-Framework-45-Core, NET-WCF-Services45, NET-WCF-TCP-PortSharing45, AzureArcSetup, Windows-Defender, System-DataArchiver, PowerShellRoot, PowerShell, Windows-Server-Backup, WoW64-Support, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| Agentless Management Service | 3.30.0.0 | Hewlett Packard Enterprise Development LP |  |
| Datto RMM | 4.4.11965.11965 | Datto Inc. |  |
| HPE Lights-Out Online Configuration Utility | 6.0.0.0 | Hewlett Packard Enterprise | 23/06/2025 |
| HPE MR Storage Administrator | 008.002.019.000 | Hewlett Packard Enterprise Development LP | 23/06/2025 |
| HPE MR Storage Administrator StorCLI | 7.22.7.0 | Hewlett Packard Enterprise | 23/06/2025 |
| Integrated Smart Update Tools for Windows | 4.1.0.0 | Hewlett Packard Enterprise | 23/06/2025 |
| Matrox Graphics Software (remove only) | 4.5.0.5 | Matrox Graphics Inc. |  |
| Microsoft Edge | 152.0.4191.53 | Microsoft Corporation | 29/08/2026 |
| Microsoft Edge WebView2 Runtime | 152.0.4191.53 | Microsoft Corporation | 02/09/2026 |
| Microsoft Visual C++ 2010  x64 Redistributable - 10.0.40219 | 10.0.40219 | Microsoft Corporation | 19/08/2025 |
| Microsoft Visual C++ v14 Redistributable (x64) - 14.50.35719 | 14.50.35719.0 | Microsoft Corporation |  |
| Microsoft Visual C++ v14 Redistributable (x86) - 14.50.35719 | 14.50.35719.0 | Microsoft Corporation |  |
| NVIDIA Graphics Driver 573.06 | 573.06 | NVIDIA Corporation | 14/05/2025 |
| NVIDIA RTX Desktop Manager 205.28 | 205.28 | NVIDIA Corporation | 14/05/2025 |
| OpenSSH | 10.0.0.0 | Microsoft Corporation | 02/09/2026 |
| Splashtop Streamer | 3.8.0.1 | Splashtop Inc. | 07/06/2026 |
| syngo Client DeviceGuard Catalog Files | 10.2.1.0 | Siemens Healthcare GbmH | 11/12/2025 |
| syngo.FlightRecorder | 5.0.0.0 | Siemens Healthcare GmbH | 11/12/2025 |
| syngo.via - Bootstrapper 8.0 | 8.0.0.0 | Siemens Healthcare GmbH | 11/12/2025 |
| syngo.via - syngo.via Client 10.6 (x64) | 10.06.0000.0000 | Siemens Healthcare GmbH | 11/12/2025 |
| syngo.via Enterprise Launcher | 2.5.0 | Siemens Healthineers AG | 27/06/2025 |
| TeamViewer | 15.81.5 | TeamViewer |  |
| TeamViewer (Siemens - Repack) | 15.41.8.0 | Siemens Healthcare GmbH | 11/12/2025 |
| TeamViewer TeamConnector (Siemens - Repack) | 15.41.8.0 | Siemens Healthcare GmbH | 11/12/2025 |
| TS2log version 18.2026.5.12 | 18.2026.5.12 |  | 06/06/2026 |
| Universal Printer | 11.9.512 | Softland | 06/06/2026 |
| Universal Printer 11 Printer Driver | 11.9.512 | Softland | 06/06/2026 |
| Universal Printer 11 Tools | 11.9.512 | Softland | 06/06/2026 |
| Virtual Printer (Server) 1.7.2 | 1.7.2.1 | Virtual Devices | 25/06/2025 |
| VNC Viewer (Siemens - Repack) 1.2 (x64) | 1.2.43.17 | Siemens Healthcare GmbH | 11/12/2025 |
| Zabbix Agent 2 (64-bit) | 7.4.3.2400 | Zabbix SIA | 22/10/2025 |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| Agentless Management Service (`ams`) | Running | LocalSystem | "C:\Program Files\OEM\AMS\service\ams.exe" |
| Application Publishing Session Control (APSC) (`APSC`) | Running | LocalSystem | "C:\Program Files (x86)\TS2log\UserDesktop\files\APSC.exe" |
| Datto RMM (`CagService`) | Running | LocalSystem | "C:\Program Files (x86)\CentraStage\CagService.exe" |
| Microsoft Edge Update Service (edgeupdate) (`edgeupdate`) | Stopped | LocalSystem | "C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /svc |
| FabulaTech Netlink 3 supervisor service (`ftnlsv3`) | Running | LocalSystem | "C:\Program Files\Common Files\FabulaTech\Netlink 3\ftnlsv.exe" |
| LSAService (`LSAService`) | Running | LocalSystem | "C:\Program Files\HPEMRSA\LSIStorageAuthority\bin\LSAService.exe" |
| Microsoft Defender Core Service (`MDCoreSvc`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MpDefenderCoreService.exe" |
| NginxService (`NginxService`) | Running | LocalSystem | "C:\Program Files\HPEMRSA\LSIStorageAuthority\server\NginxService.exe" |
| novaPDF 11 Server (`NovaPdf11Server`) | Running | LocalSystem | "C:\Program Files\Softland\novaPDF 11\Server\novapdfs.exe" |
| Splashtop® Remote Service (`SplashtopRemoteService`) | Running | LocalSystem | "C:\Program Files (x86)\Splashtop\Splashtop Remote\Server\SRService.exe" |
| OpenSSH Authentication Agent (`ssh-agent`) | Running | LocalSystem | "C:\Program Files\OpenSSH\ssh-agent.exe" |
| OpenSSH SSH Server (`sshd`) | Running | LocalSystem | "C:\Program Files\OpenSSH\sshd.exe" |
| Integrated Smart Update Tools (`SUTService`) | Stopped | LocalSystem | C:/Program Files/SUT/bin/sut.exe /svc |
| Enterprise Service (`SVCE`) | Running | LocalSystem | "C:\Program Files (x86)\TS2log\UserDesktop\files\svcenterprise.exe" |
| Application Publishing Service (APS) (`SVCM`) | Running | LocalSystem | "C:\Program Files (x86)\TS2log\UserDesktop\files\svcmain.exe" |
| Web Server Service (`SVCW`) | Running | LocalSystem | "C:\Program Files (x86)\TS2log\UserDesktop\files\svcweb.exe" |
| syngo Client Update Service (`syngo Client Update Service`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo.via\bin\CUS\syngoClientBootstrapping.exe" |
| syngo.Services.TF.Component.Media.CDDVDServiceManager (`syngo.Services.TF.Component.Media.CDDVDServiceManager`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo.via\bin\syngo.Services.TF.Component.Media.CDDVDServiceManager.exe" -config "C:\Program Files\Siemens\syngo.via\bin" |
| TeamViewer (`TeamViewer`) | Running | LocalSystem | "C:\Program Files\TeamViewer\TeamViewer_Service.exe" |
| Microsoft Defender Antivirus Service (`WinDefend`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MsMpEng.exe" |
| Zabbix Agent 2 (`Zabbix Agent 2`) | Running | LocalSystem | "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -c "C:\Program Files\Zabbix Agent 2\zabbix_agent2.conf" -f=false |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 22 | ::, 0.0.0.0 | sshd (sshd) |
| TCP | 80 | :: | HTML5service |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 192.168.101.102 | System |
| TCP | 443 | :: | HTML5service |
| TCP | 445 | :: | System |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 5357 | :: | System |
| TCP | 5939 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 5985 | :: | System |
| TCP | 6783 | 0.0.0.0 | SRManager |
| TCP | 7443 | :: | System |
| TCP | 8501 | :: | System |
| TCP | 8763 | 127.0.0.1 | SRManager |
| TCP | 9527 | 127.0.0.1 | SRManager |
| TCP | 10050 | :: | zabbix_agent2 (Zabbix Agent 2) |
| TCP | 19955 | :: | System |
| TCP | 19956 | :: | System |
| TCP | 26551 | :: | System |
| TCP | 34543 | 127.0.0.1 | ftnlsv (ftnlsv3) |
| TCP | 34843 | 127.0.0.1 | ftnlsv (ftnlsv3) |
| TCP | 34943 | 127.0.0.1 | ftnlsv (ftnlsv3) |
| TCP | 44972 | 127.239.154.49 | HTML5service |
| TCP | 47001 | :: | System |
| TCP | 49553 | 0.0.0.0 | syngo.Common.Container |
| TCP | 49554 | :: | syngo.Common.Container |
| TCP | 49555 | 0.0.0.0 | syngo.Common.Container |
| TCP | 49556 | :: | syngo.Common.Container |
| TCP | 49664 | ::, 0.0.0.0 | lsass (KeyIso, SamSs, VaultSvc) |
| TCP | 49665 | ::, 0.0.0.0 | wininit |
| TCP | 49666 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 49667 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 49668 | ::, 0.0.0.0 | spoolsv (Spooler) |
| TCP | 49692 | ::, 0.0.0.0 | services |
| TCP | 52514 | 0.0.0.0 | syngo.Common.Container |
| TCP | 52515 | :: | syngo.Common.Container |
| TCP | 52516 | 0.0.0.0 | syngo.Common.Container |
| TCP | 52517 | :: | syngo.Common.Container |
| TCP | 57308 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57309 | :: | syngo.Common.Container |
| TCP | 57310 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57311 | :: | syngo.Common.Container |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 192.168.101.102 | System |
| UDP | 138 | 192.168.101.102 | System |
| UDP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| UDP | 3702 | ::, 0.0.0.0 | svchost (FDResPub) |
| UDP | 5353 | 0.0.0.0 | msedge |
| UDP | 5353 | ::1, 192.168.101.102 | TeamViewer_Service (TeamViewer) |
| UDP | 5355 | 0.0.0.0 | svchost (Dnscache) |
| UDP | 13300 | 0.0.0.0 | CagService (CagService) |

## Partages SMB

Aucun partage non administratif.

## Taches planifiees hors Microsoft

| Tache | Etat | Action |
|---|---|---|
| \MicrosoftEdgeUpdateTaskMachineCore | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /c |
| \MicrosoftEdgeUpdateTaskMachineUA | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /ua /installsource scheduler |
| \nWizard_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} | Ready | C:\Program Files\NVIDIA Corporation\nview\nwiz.exe /installquiet |
| \Siemens\ClientTracelogMonitor | Ready | PowerShell.exe -ExecutionPolicy Bypass -command "& {&'C:\Program Files\Siemens\syngo.via\bin\Scripts\ClientTraces\CheckLogSize.ps1' 'C:\Users\Default\AppData\Local\syngo\Containertraces\';;}" |

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5071547 | Security Update | 11/12/2025 |
| KB5068786 | Security Update | 12/11/2025 |
| KB5066139 | Update | 15/10/2025 |

## Securite locale

Microsoft Defender : service actif, protection temps reel active, signatures du 01/09/2026, moteur 1.1.26080.3

| Profil pare-feu | Actif | Entrant par defaut | Sortant par defaut |
|---|---|---|---|
| Domain | oui | NotConfigured | NotConfigured |
| Private | oui | NotConfigured | NotConfigured |
| Public | oui | NotConfigured | NotConfigured |

## Comptes locaux

**627 comptes locaux** : 622 actifs, 5 desactives.

Membres du groupe Administrateurs : `WIN-SRV-TSPLUS\Administrator` (User, Local), `WIN-SRV-TSPLUS\Info100T` (User, Local), `WIN-SRV-TSPLUS\matthieu` (User, Local), `WIN-SRV-TSPLUS\remoteadmin` (User, Local), `WIN-SRV-TSPLUS\sebastien` (User, Local), `WIN-SRV-TSPLUS\siemens_apps` (User, Local)
