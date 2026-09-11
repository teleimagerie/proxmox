# Inventaire timvueexplorer - 11/09/2026 13:12

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

## Identite

| | |
|---|---|
| Hostname | `TIMVUEEXPLORER` (workgroup WORKGROUP) |
| Modele | QEMU Standard PC (i440FX + PIIX, 1996) |
| OS | Microsoft Windows Server 2019 Datacenter 1809 (build 17763) |
| Installe le | 27/02/2023 |
| Dernier boot | 29/05/2026 17:24 (uptime 104 j 19 h) |
| Fuseau | Romance Standard Time |
| Licence | active - Retail |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| CPU 0 | Common KVM processor | 4c/4t | 3.3 GHz |

## RAM

**16 Go** en 1 barrette(s) sur 1 slot(s), 16 Go max, ECC multi-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| DIMM 0 | 16 Go | type 7 |  MHz | QEMU  |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere |   |
| Numero de serie |  |
| BIOS | rel-1.16.1-0-g3208b098f51a-prebuilt.qemu.org du 01/04/2014 |

## GPU

| Carte | Pilote | VRAM annoncee |
|---|---|---|
| Microsoft Basic Display Adapter | 10.0.17763.1 du 21/06/2006 | - |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | Red Hat VirtIO | SCSI | Unspecified | 300 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| - | System Reserved | NTFS | 0.5 Go | 0.1 Go |
| C: | SYSTEM | NTFS | 249.5 Go | 186 Go |
| D: | SERVICE | NTFS | 50 Go | 30.7 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| Ethernet Instance 0 | Red Hat VirtIO Ethernet Adapter | `26-F6-24-B7-5F-D3` | 10 Gbps | Up |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| Ethernet Instance 0 | 192.168.101.53/28 | 192.168.101.62 | 192.168.101.62, 8.8.8.8 |

## Roles et fonctionnalites

- **File and Storage Services** (`FileAndStorage-Services`)
- **Web Server (IIS)** (`Web-Server`)

Fonctionnalites : File-Services, FS-FileServer, Storage-Services, Web-WebServer, Web-Common-Http, Web-Default-Doc, Web-Dir-Browsing, Web-Http-Errors, Web-Static-Content, Web-Health, Web-Http-Logging, Web-Log-Libraries, Web-Request-Monitor, Web-Http-Tracing, Web-Performance, Web-Stat-Compression, Web-Dyn-Compression, Web-Security, Web-Filtering, Web-Basic-Auth, Web-Url-Auth, Web-App-Dev, Web-Net-Ext45, Web-AppInit, Web-ASP, Web-Asp-Net45, Web-CGI, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-WebSockets, Web-Mgmt-Tools, Web-Mgmt-Console, Web-Mgmt-Compat, Web-Metabase, Web-WMI, NET-Framework-45-Features, NET-Framework-45-Core, NET-Framework-45-ASPNET, NET-WCF-Services45, NET-WCF-HTTP-Activation45, NET-WCF-Pipe-Activation45, NET-WCF-TCP-PortSharing45, Server-Media-Foundation, System-DataArchiver, Telnet-Client, Windows-Defender, PowerShellRoot, PowerShell, PowerShell-ISE, WAS, WAS-Process-Model, WAS-Config-APIs, WoW64-Support, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| 7-Zip 19.00 (x64 edition) | 19.00.00.0 | Igor Pavlov | 09/06/2023 |
| ActivePerl 5.16.3 Build 1603 (64-bit) | 5.16.1603 | ActiveState | 09/06/2023 |
| AnyDesk | ad 9.0.14 | AnyDesk Software GmbH |  |
| AppFabric 1.1 for Windows Server | 1.1.2106.32 | Microsoft Corporation |  |
| Eclipse Temurin JDK with Hotspot 8u312-b07 (x64) | 8.0.312.7 | Eclipse Adoptium | 09/06/2023 |
| IIS URL Rewrite Module 2 | 7.2.2 | Microsoft Corporation | 09/06/2023 |
| Microsoft .NET Core 2.2.6 - Windows Server Hosting | 2.2.6.0 | Microsoft Corporation |  |
| Microsoft .NET Core Runtime - 2.2.6 (x64) | 2.2.6.27818 | Microsoft Corporation |  |
| Microsoft .NET Core Runtime - 2.2.6 (x86) | 2.2.6.27818 | Microsoft Corporation |  |
| Microsoft Application Request Routing 3.0 | 3.0.1750 | Microsoft Corporation | 09/06/2023 |
| Microsoft UrlScan Filter v3.1 | 3.1.0303 | Microsoft Corporation | 09/06/2023 |
| Microsoft Visual C++ 2012 Redistributable (x64) - 11.0.60610 | 11.0.60610.1 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2019 Redistributable (x64) - 14.20.27508 | 14.20.27508.1 | Microsoft Corporation |  |
| Microsoft Web Deploy 3.6 | 10.0.1973 | Microsoft Corporation | 09/06/2023 |
| Microsoft Web Farm Framework | 1.1.1292 | Microsoft Corporation | 09/06/2023 |
| Python Launcher | 3.6.6196.0 | Python Software Foundation | 09/06/2023 |
| TeamViewer | 15.47.3 | TeamViewer |  |
| Virtio-win-guest-tools | 0.1.225 | Red Hat, Inc. |  |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| AnyDesk Service (`AnyDesk`) | Running | LocalSystem | "C:\Program Files (x86)\AnyDesk\AnyDesk.exe" --service |
| AppFabric Event Collection Service (`AppFabricEventCollectionService`) | Stopped | NT AUTHORITY\LocalService | "c:\Program Files\AppFabric 1.1 for Windows Server\EventCollectorService.exe" |
| AppFabric Workflow Management Service (`AppFabricWorkflowManagementService`) | Running | NT AUTHORITY\LocalService | "c:\Program Files\AppFabric 1.1 for Windows Server\WorkflowManagementService.exe" |
| BalloonService (`BalloonService`) | Running | LocalSystem | "C:\Program Files\Virtio-Win\Balloon\blnsvr.exe" |
| Filebeat (`Filebeat`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Filebeat |
| Imaginet DataGrid Controller (`Imaginet DataGrid Controller`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Wrapper.exe service Filebeat Metricbeat Ignite |
| Imaginet MVSMain LightViewer Server (`Imaginet MVSMain LightViewer Server`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\Portal\Dll\SVRender\MVSMAIN.exe /lightviewer |
| Imaginet MVSMain Secured Server (`Imaginet MVSMain Secured Server`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\Portal\Dll\SVRender\MVSMAIN.exe /SECURED |
| Imaginet MVSMain Server (`Imaginet MVSMain Server`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\Portal\Dll\SVRender\MVSMAIN.exe |
| Imaginet Portal Restarter Service (`Imaginet Portal Restarter Service`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\Portal\Utils\RestarterService.exe Portal |
| Imaginet System Check (`Imaginet System Check`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\utils\srvany.exe |
| Imaginet VUEEXPLORER Restarter Service (`Imaginet VUEEXPLORER Restarter Service`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\Archive\Utils\RestarterService.exe vueexplorer |
| Microsoft Defender Core Service (`MDCoreSvc`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MpDefenderCoreService.exe" |
| Metricbeat (`Metricbeat`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Metricbeat |
| QEMU Guest Agent (`QEMU-GA`) | Running | LocalSystem | "C:\Program Files\Qemu-ga\qemu-ga.exe" -d --retry-path |
| Spice Agent (`spice-agent`) | Stopped | LocalSystem | "C:\Program Files\Spice Agent\vdservice.exe" |
| TeamViewer (`TeamViewer`) | Stopped | LocalSystem | "C:\Program Files\TeamViewer\TeamViewer_Service.exe" |
| Microsoft Defender Antivirus Service (`WinDefend`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MsMpEng.exe" |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 22 | ::, 0.0.0.0 | sshd (sshd) |
| TCP | 80 | :: | System |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 192.168.101.53 | System |
| TCP | 443 | :: | System |
| TCP | 445 | :: | System |
| TCP | 2104 | 0.0.0.0 | MVSMAIN (Imaginet MVSMain Server) |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 5357 | :: | System |
| TCP | 5985 | :: | System |
| TCP | 6039 | 127.0.0.1 | TeamViewer |
| TCP | 7070 | ::, 0.0.0.0 | AnyDesk (AnyDesk) |
| TCP | 8888 | :: | System |
| TCP | 22104 | 0.0.0.0 | MVSMAIN (Imaginet MVSMain Secured Server) |
| TCP | 25817 | 127.0.0.1 | SessionManagerService |
| TCP | 29032 | 0.0.0.0 | MVSMAIN (Imaginet MVSMain LightViewer Server) |
| TCP | 37014 | 127.0.0.1 | TeamViewer |
| TCP | 37114 | 127.0.0.1 | TeamViewer |
| TCP | 47001 | :: | System |
| TCP | 49664 | ::, 0.0.0.0 | wininit |
| TCP | 49665 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 49666 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 49667 | ::, 0.0.0.0 | lsass (KeyIso, SamSs) |
| TCP | 49668 | ::, 0.0.0.0 | svchost (SessionEnv) |
| TCP | 49669 | ::, 0.0.0.0 | svchost (PolicyAgent) |
| TCP | 49672 | ::, 0.0.0.0 | services |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 192.168.101.53 | System |
| UDP | 138 | 192.168.101.53 | System |
| UDP | 500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| UDP | 3702 | ::, 0.0.0.0 | svchost (FDResPub) |
| UDP | 4500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 5353 | ::1, 192.168.101.53 | TeamViewer |
| UDP | 5353 | ::, 0.0.0.0 | svchost (Dnscache) |
| UDP | 5355 | ::, 0.0.0.0 | svchost (Dnscache) |

## Partages SMB

| Partage | Chemin | Description |
|---|---|---|
| temp | C:\temp |  |

## Taches planifiees hors Microsoft

| Tache | Etat | Action |
|---|---|---|
| \backup_files | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "perl \"C:\PROGRA~1\CAREST~1\System5\scripts\backup_files.pl\" \"C:\PROGRA~1\CAREST~1\System5\scripts\backup_files.ini\"" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\backup_files.log" 2>&1 |
| \FilesCleaner_Portal | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "C:\PROGRA~1\CAREST~1\System5\Portal\utils\Algotec.infra.FilesCleaner.exe portal applications\webportal\services" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\FilesCleaner_Portal.log" 2>&1 |
| \make_sure_datagrid_up | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "datagrid_services.py start -only_if_imaginet_up -auto_only -skip_running" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\make_sure_datagrid_up.log" 2>&1 |
| \NDF_dicom_cleanup | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "python C:\PROGRA~1\CAREST~1\System5\NDF\scripts\NDF_dicom_clean.py" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\NDF_dicom_cleanup.log" 2>&1 |
| \rotatelogs | Ready | Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "C:\PROGRA~1\CAREST~1\System5\scripts\rotatelogs.cmd" |
| \rotate_mvs_stat | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "python \"C:\PROGRA~1\CAREST~1\System5\scripts\rotate_mvs_stat.py\"" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\rotate_mvs_stat.log" 2>&1 |
| \short_server_snapshot | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "perl \"C:\PROGRA~1\CAREST~1\System5\scripts\server_snapshot.pl\" --short" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\short_server_snapshot.log" 2>&1 |
| \syscheck | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "Perl \"C:\PROGRA~1\CAREST~1\System5\syscheck\syscheck.pl\" -v -a -o" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\syscheck.log" 2>&1 |
| \syscheck_force | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "Perl \"C:\PROGRA~1\CAREST~1\System5\syscheck\syscheck.pl\" -f" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\syscheck_force.log" 2>&1 |
| \zip_and_clean | Ready | cmd /c Perl "C:\PROGRA~1\CAREST~1\System5\scripts\CNR.pl" -n "C:\PROGRA~1\CAREST~1\System5\utils\Algotec.infra.ZipAndClean.exe" >> "C:\PROGRA~1\CAREST~1\System5\log\Scheduled_Tasks\zip_and_clean.log" 2>&1 |

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5082118 | Security Update | 29/05/2026 |
| KB5082123 | Security Update | 29/05/2026 |
| KB5087066 | Update | 29/05/2026 |
| KB5043126 | Security Update | 30/10/2024 |
| KB4486153 | Update | 09/06/2023 |
| KB4589208 | Update | 03/03/2023 |
| KB5020374 | Security Update | 27/02/2023 |
| KB4512577 | Security Update | 07/09/2019 |

## Securite locale

Microsoft Defender : service actif, protection temps reel active, signatures du 10/09/2026, moteur 1.1.26080.3

| Profil pare-feu | Actif | Entrant par defaut | Sortant par defaut |
|---|---|---|---|
| Domain | oui | Block | Allow |
| Private | **NON** | Block | Allow |
| Public | **NON** | Block | Allow |

## Comptes locaux

**9 comptes locaux** : 6 actifs, 3 desactives.

Membres du groupe Administrateurs : `TIMVUEEXPLORER\Administrator` (User, Local), `TIMVUEEXPLORER\mcapon` (User, Local), `TIMVUEEXPLORER\philipsadm` (User, Local), `TIMVUEEXPLORER\xadministrator` (User, Local)
