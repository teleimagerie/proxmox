# Inventaire ns3062628 - 30/08/2026 14:07

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

## Identite

| | |
|---|---|
| Hostname | `ns3062628` (workgroup WORKGROUP) |
| Modele | GIGABYTE MX33-BS1-V1 |
| OS | Microsoft Windows Server 2022 Standard 21H2 (build 20348) |
| Installe le | 13/05/2024 |
| Dernier boot | 30/08/2026 12:45 (uptime 0 j 1 h) |
| Fuseau | Romance Standard Time |
| Licence | active - Volume:GVLK |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| U3E1 | Intel(R) Xeon(R) E-2386G CPU @ 3.50GHz | 6c/12t | 3.5 GHz |

## RAM

**32 Go** en 2 barrette(s) sur 4 slot(s), 64 Go max, ECC single-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| DIMM_P0_A0 | 16 Go | DDR4 | 3200 MHz | Samsung M391A2G43BB2-CWE |
| DIMM_P0_B0 | 16 Go | DDR4 | 3200 MHz | Samsung M391A2G43BB2-CWE |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere | GIGABYTE MX33-BS1-V1 |
| Numero de serie | 01234567890123456789AB |
| BIOS | F09d du 27/08/2023 |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | ST6000NM021B-2TG113 | SATA | HDD | 5589 Go | Healthy |
| 1 | ST6000NM021B-2TG113 | SATA | HDD | 5589 Go | Healthy |
| 2 | SAMSUNG MZVL2512HCJQ-00B07 | NVMe | SSD | 476.9 Go | Healthy |
| 3 | SAMSUNG MZVL2512HCJQ-00B07 | NVMe | SSD | 476.9 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| - | EFI | FAT32 | 0.3 Go | 0.3 Go |
| C: | Windows | NTFS | 181.4 Go | 124.9 Go |
| D: | TEMP | NTFS | 295 Go | 242.6 Go |
| E: | BDD | NTFS | 976.6 Go | 901.7 Go |
| F: | IMAGE | NTFS | 4612.5 Go | 921.5 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| Ethernet | Intel(R) Ethernet Controller X550 | `74-56-3C-5C-7C-69` | 1 Gbps | Up |
| Ethernet 2 | Intel(R) Ethernet Controller X550 #2 | `74-56-3C-5C-7C-6A` | 1 Gbps | Up |
| DC-TELLIS-PARTENAIRES | WireGuard Tunnel | `` | 100 Gbps | Up |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| Ethernet | 188.165.77.137/24 | 188.165.77.254 | 213.186.33.99 |
| Ethernet 2 | 10.40.0.40/24 |  |  |
| DC-TELLIS-PARTENAIRES | 172.32.0.2/32 |  |  |

## Roles et fonctionnalites

- **Services de fichiers et de stockage** (`FileAndStorage-Services`)

Fonctionnalites : File-Services, FS-FileServer, Storage-Services, NET-Framework-45-Features, NET-Framework-45-Core, NET-WCF-Services45, NET-WCF-TCP-PortSharing45, Windows-Defender, AzureArcSetup, WoW64-Support, System-DataArchiver, PowerShellRoot, PowerShell, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| 7-Zip 19.00 (x64) | 19.00 | Igor Pavlov |  |
| FileZilla 3.67.0 | 3.67.0 | Tim Kosse |  |
| Google Chrome | 151.0.7922.174 | Google LLC | 25/08/2026 |
| Microsoft ASP.NET Core 6.0.29 - Shared Framework (x64) | 6.0.29.24171 | Microsoft Corporation |  |
| Microsoft Edge | 152.0.4191.53 | Microsoft Corporation | 29/08/2026 |
| Microsoft Edge WebView2 Runtime | 151.0.4129.107 | Microsoft Corporation | 25/08/2026 |
| Microsoft Report Viewer 2015 Runtime | 12.0.2402.15 | Microsoft Corporation | 28/06/2024 |
| Microsoft System CLR Types for SQL Server 2014 | 12.0.2402.11 | Microsoft Corporation | 28/06/2024 |
| Microsoft Visual C++ 2010  x64 Redistributable - 10.0.30319 | 10.0.30319 | Microsoft Corporation | 31/05/2024 |
| Microsoft Visual C++ 2010  x86 Redistributable - 10.0.30319 | 10.0.30319 | Microsoft Corporation | 31/05/2024 |
| Microsoft Visual C++ 2013 Redistributable (x64) - 12.0.30501 | 12.0.30501.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2013 Redistributable (x86) - 12.0.30501 | 12.0.30501.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2019 Redistributable (x86) - 14.27.29112 | 14.27.29112.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2022 Redistributable (x64) - 14.32.31332 | 14.32.31332.0 | Microsoft Corporation |  |
| Microsoft Windows Desktop Runtime - 6.0.29 (x64) | 6.0.29.33521 | Microsoft Corporation |  |
| PostgreSQL 15 | 15.6 | PostgreSQL Global Development Group | 28/06/2024 |
| smartmontools | 7.5 2025-04-30 r5714 (AppVeyor) | smartmontools.org |  |
| TeamViewer Host | 15.81.5 | TeamViewer |  |
| WireGuard | 1.1 | WireGuard LLC | 30/08/2026 |
| Zabbix Agent 2 (64-bit) | 7.4.1.2400 | Zabbix SIA | 15/08/2025 |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| DICOM Agent for MyTIM (isoteam) (`DicomAgent-isoteam`) | Running | LocalSystem | "e:\ISOTEAM\dicom-agent.exe" |
| DICOM Agent for MyTIM (isoteam-sender) (`DicomAgent-isoteam-sender`) | Running | LocalSystem | "E:\ISOTEAM_SENDER\dicom-agent.exe" |
| DICOM Agent for MyTIM (tim) (`DicomAgent-tim`) | Running | LocalSystem | "E:\TIM\dicom-agent.exe" |
| Microsoft Edge Update Service (edgeupdate) (`edgeupdate`) | Stopped | LocalSystem | "C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /svc |
| Service interne de mise à jour Google (GoogleUpdaterInternalService152.0.7933.0) (`GoogleUpdaterInternalService152.0.7933.0`) | Stopped | LocalSystem | "C:\Program Files (x86)\Google\GoogleUpdater\152.0.7933.0\updater.exe" --system --windows-service --service=update-internal |
| Service de mise à jour Google (GoogleUpdaterService152.0.7933.0) (`GoogleUpdaterService152.0.7933.0`) | Stopped | LocalSystem | "C:\Program Files (x86)\Google\GoogleUpdater\152.0.7933.0\updater.exe" --system --windows-service --service=update |
| Service Google Update (gupdate) (`gupdate`) | Stopped | LocalSystem | "C:\Program Files (x86)\Google\Update\GoogleUpdate.exe" /svc |
| Microsoft Defender Service de base (`MDCoreSvc`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26070.9-0\MpDefenderCoreService.exe" |
| OracleOraDB19Home1MTSRecoveryService (`OracleOraDB19Home1MTSRecoveryService`) | Running | LocalSystem | E:\ORACLE\DB_HOME\bin\omtsreco.exe OracleOraDB19Home1MTSRecoveryService |
| OracleOraDB19Home1TNSListener (`OracleOraDB19Home1TNSListener`) | Running | LocalSystem | E:\ORACLE\DB_HOME\BIN\TNSLSNR |
| OracleServiceXPLORE (`OracleServiceXPLORE`) | Running | LocalSystem | e:\oracle\db_home\bin\ORACLE.EXE XPLORE |
| OracleVssWriterXPLORE (`OracleVssWriterXPLORE`) | Running | LocalSystem | E:\ORACLE\DB_HOME\bin\OraVSSW.exe XPLORE |
| postgresql-x64-15 - PostgreSQL Server 15 (`postgresql-x64-15`) | Running | NT AUTHORITY\NetworkService | "C:\Program Files\PostgreSQL\15\bin\pg_ctl.exe" runservice -N "postgresql-x64-15" -D "C:\Program Files\PostgreSQL\15\data" -w |
| TeamViewer (`TeamViewer`) | Running | LocalSystem | "C:\Program Files\TeamViewer\TeamViewer_Service.exe" |
| Service antivirus Microsoft Defender (`WinDefend`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26070.9-0\MsMpEng.exe" |
| WireGuard Manager (`WireGuardManager`) | Running | LocalSystem | "C:\Program Files\WireGuard\wireguard.exe" /managerservice |
| WireGuard Tunnel: DC-TELLIS-PARTENAIRES (`WireGuardTunnel$DC-TELLIS-PARTENAIRES`) | Running | LocalSystem | "C:\Program Files\WireGuard\wireguard.exe" /tunnelservice "C:\Program Files\WireGuard\Data\Configurations\DC-TELLIS-PARTENAIRES.conf.dpapi" |
| XnADDONS service (`XnADDONS`) | Running | .\admin | E:\EDL\\XnADDONS\XnADDONS.exe |
| XnCONSOLEPACS service (`XnCONSOLEPACS`) | Running | .\admin | E:\EDL\\XnCONSOLEPACS\XnCONSOLEPACS.exe |
| XnDicomSCU service (`XnDicomSCU`) | Running | .\admin | E:\EDL\\XnDicomSCU\XnDicomSCU.exe |
| XnDICOMVIEWER service (`XnDICOMVIEWER`) | Running | .\admin | E:\EDL\\XnDICOMVIEWER\XnDICOMVIEWER.exe |
| XnDOCUMENTATION service (`XnDOCUMENTATION`) | Running | .\admin | E:\EDL\\XnDOCUMENTATION\XnDOCUMENTATION.exe |
| XnPUSH service (`XnPUSH`) | Running | .\admin | E:\EDL\\XnPUSH\XnPUSH.exe |
| XnTELEMEDGATEWAY service (`XnTELEMEDGATEWAY`) | Running | .\admin | E:\EDL\\XnTELEMEDGATEWAY\XnTELEMEDGATEWAY.exe |
| XnXPLOREUPDATE service (`XnXPLOREUPDATE`) | Running | .\admin | E:\EDL\\XnXPLOREUPDATE\XnXPLOREUPDATE.exe |
| XnXPLOREVIEWWEB service (`XnXPLOREVIEWWEB`) | Running | .\admin | E:\EDL\\XnXPLOREVIEWWEB\XnXPLOREVIEWWEB.exe |
| Zabbix Agent 2 (`Zabbix Agent 2`) | Running | LocalSystem | "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -c "C:\Program Files\Zabbix Agent 2\zabbix_agent2.conf" -f=false |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 80 | :: | System |
| TCP | 104 | 0.0.0.0 | XnCONSOLEPACS (XnCONSOLEPACS) |
| TCP | 109 | 0.0.0.0 | XnTELEMEDGATEWAY (XnTELEMEDGATEWAY) |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 10.40.0.40, 172.32.0.2, 188.165.77.137 | System |
| TCP | 445 | :: | System |
| TCP | 1521 | :: | tnslsnr (OracleOraDB19Home1TNSListener) |
| TCP | 2030 | ::1, 172.32.0.2 | omtsreco (OracleOraDB19Home1MTSRecoveryService) |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 5432 | ::1, 127.0.0.1 | postgres |
| TCP | 5500 | :: | tnslsnr (OracleOraDB19Home1TNSListener) |
| TCP | 5939 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 5985 | :: | System |
| TCP | 8005 | 0.0.0.0 | XnPUSH (XnPUSH) |
| TCP | 10050 | :: | zabbix_agent2 (Zabbix Agent 2) |
| TCP | 11112 | 0.0.0.0 | dicom-agent (DicomAgent-isoteam) |
| TCP | 11113 | 0.0.0.0 | dicom-agent (DicomAgent-tim) |
| TCP | 37014 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 37114 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 47001 | :: | System |
| TCP | 49664 | ::, 0.0.0.0 | lsass (KeyIso, SamSs) |
| TCP | 49665 | ::, 0.0.0.0 | wininit |
| TCP | 49666 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 49667 | ::, 0.0.0.0 | svchost (SessionEnv) |
| TCP | 49668 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 49669 | ::, 0.0.0.0 | spoolsv (Spooler) |
| TCP | 49670 | ::, 0.0.0.0 | svchost (PolicyAgent) |
| TCP | 49672 | ::1 | tnslsnr (OracleOraDB19Home1TNSListener) |
| TCP | 49762 | :: | oracle (OracleServiceXPLORE) |
| TCP | 49781 | ::, 0.0.0.0 | services |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 10.40.0.40, 172.32.0.2, 188.165.77.137 | System |
| UDP | 138 | 10.40.0.40, 172.32.0.2, 188.165.77.137 | System |
| UDP | 500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| UDP | 4500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 5353 | ::1, 10.40.0.40, 172.32.0.2, 188.165.77.137 | TeamViewer_Service (TeamViewer) |
| UDP | 5353 | ::, 0.0.0.0 | svchost (Dnscache) |
| UDP | 5355 | ::, 0.0.0.0 | svchost (Dnscache) |

## Partages SMB

| Partage | Chemin | Description |
|---|---|---|
| PACS | F:\PACS |  |
| VBRCatalog | F:\VBRCatalog |  |

## Taches planifiees hors Microsoft

| Tache | Etat | Action |
|---|---|---|
| \MicrosoftEdgeUpdateTaskMachineCore | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /c |
| \MicrosoftEdgeUpdateTaskMachineUA | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /ua /installsource scheduler |
| \Optimisation de la base de données | Ready | E:\__XPLORE32\Backup\Scripts\optimize.bat |
| \Sauvegarde de la base de données | Ready | E:\__XPLORE32\Backup\Scripts\Save_base.bat |
| \User_Feed_Synchronization-{0AE908DC-4C48-49E6-A1C1-984962DE07F3} | Ready | C:\Windows\system32\msfeedssync.exe sync |
| \GoogleSystem\GoogleUpdater\GoogleUpdaterTaskSystem152.0.7933.0{C2709AC2-AD6A-417B-ACD6-C80AE62CE69B} | Ready | "C:\Program Files (x86)\Google\GoogleUpdater\152.0.7933.0\updater.exe" --wake --system |

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5120241 | Security Update | 30/08/2026 |
| KB5120242 | Security Update | 30/08/2026 |
| KB5120705 | Update | 30/08/2026 |
| KB5034439 | Security Update | 20/02/2024 |
| KB5034869 | Security Update | 20/02/2024 |
