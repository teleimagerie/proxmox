# Inventaire syngovia-135113 - 02/09/2026 16:03

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

## Identite

| | |
|---|---|
| Hostname | `syngovia-135113` (workgroup WORKGROUP) |
| Modele | HPE ProLiant DL380 Gen11 |
| OS | Microsoft Windows Server 2022 Standard 21H2 (build 20348) |
| Installe le | 27/01/2025 |
| Dernier boot | 01/09/2026 01:06 (uptime 1 j 14 h) |
| Fuseau | Romance Standard Time |
| Licence | active - OEM:SLP |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| Proc 1 | Intel(R) Xeon(R) Gold 6426Y | 16c/32t | 2.5 GHz |
| Proc 2 | Intel(R) Xeon(R) Gold 6426Y | 16c/32t | 2.5 GHz |

## RAM

**384 Go** en 12 barrette(s) sur 16 slot(s), ECC multi-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| PROC 1 DIMM 3 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 1 DIMM 5 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 1 DIMM 7 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 1 DIMM 10 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 1 DIMM 14 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 1 DIMM 16 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 3 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 5 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 7 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 10 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 14 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |
| PROC 2 DIMM 16 | 32 Go | DDR5 | 4800 MHz | Samsung M321R4GA3PB0-CWMCJ |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere | HPE ProLiant DL380 Gen11 |
| Numero de serie | CZ2D260F4T |
| BIOS | 2.22 du 19/06/2024 |

## GPU

| Carte | Pilote | VRAM annoncee |
|---|---|---|
| Microsoft Remote Display Adapter | 10.0.20348.3451 du 21/06/2006 | - |
| NVIDIA RTX A4000 | 31.0.15.2911 du 14/06/2023 | 4 Go |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | HPE LOGICAL VOLUME | SAS | SSD | 640.6 Go | Healthy |
| 1 | HPE LOGICAL VOLUME | SAS | SSD | 17244.1 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| - | Recovery | NTFS | 0.5 Go | 0.5 Go |
| - | System 2 | NTFS | 140 Go | 139.9 Go |
| - | EFI | FAT32 | 0.1 Go | 0.1 Go |
| C: | System | NTFS | 140 Go | 38.3 Go |
| D: | DB_Data | NTFS | 100 Go | 38.9 Go |
| E: | Image_Data | NTFS | 16644.1 Go | 4858.4 Go |
| M: | DB_Backup | NTFS | 200 Go | 171.9 Go |
| N: | System_Backup | NTFS | 200 Go | 8.9 Go |
| S: | Service | NTFS | 200 Go | 123.5 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| HPE Network Port 3 | Broadcom NetXtreme 5719 Quad Port Gigabit PCIe Adapter #4 | `8C-84-74-0C-B3-32` | 0 bps | Not Present |
| HPE Network Port 2 | Broadcom NetXtreme 5719 Quad Port Gigabit PCIe Adapter #3 | `8C-84-74-0C-B3-31` | 0 bps | Not Present |
| HPE Network Port 10G 2 | Broadcom NetXtreme E-Series Dual-port 25Gb SFP28 Ethernet OCP 3.0 Adapter #2 | `8C-84-74-80-4D-A7` | 0 bps | Disconnected |
| HPE Network Port 10G 1 | Broadcom NetXtreme E-Series Dual-port 25Gb SFP28 Ethernet OCP 3.0 Adapter | `8C-84-74-80-4D-A6` | 10 Gbps | Up |
| HPE Network Port 1 | Broadcom NetXtreme 5719 Quad Port Gigabit PCIe Adapter | `8C-84-74-0C-B3-30` | 0 bps | Not Present |
| HPE Network Port 4 | Broadcom NetXtreme 5719 Quad Port Gigabit PCIe Adapter #2 | `8C-84-74-0C-B3-33` | 0 bps | Not Present |
| vEthernet (nat) | Hyper-V Virtual Ethernet Adapter | `00-15-5D-2B-B2-A3` | 10 Gbps | Up |
| vEthernet (WSL) | Hyper-V Virtual Ethernet Adapter #2 | `00-15-5D-56-60-30` | 10 Gbps | Up |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| HPE Network Port 10G 2 | 169.254.99.78/16 |  |  |
| HPE Network Port 10G 1 | 192.168.101.100/24 | 192.168.101.110 | 8.8.8.8 |
| vEthernet (nat) | 172.25.0.1/20 |  |  |
| vEthernet (WSL) | 172.28.128.1/20 |  |  |

## Roles et fonctionnalites

- **File and Storage Services** (`FileAndStorage-Services`)
- **Hyper-V** (`Hyper-V`)
- **Web Server (IIS)** (`Web-Server`)

Fonctionnalites : File-Services, FS-FileServer, Storage-Services, Web-WebServer, Web-Common-Http, Web-Default-Doc, Web-Dir-Browsing, Web-Http-Errors, Web-Static-Content, Web-Http-Redirect, Web-Health, Web-Http-Logging, Web-Custom-Logging, Web-Log-Libraries, Web-ODBC-Logging, Web-Request-Monitor, Web-Http-Tracing, Web-Performance, Web-Stat-Compression, Web-Dyn-Compression, Web-Security, Web-Filtering, Web-Basic-Auth, Web-Client-Auth, Web-Digest-Auth, Web-Cert-Auth, Web-IP-Security, Web-Windows-Auth, Web-App-Dev, Web-Net-Ext, Web-Net-Ext45, Web-ASP, Web-Asp-Net, Web-Asp-Net45, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Includes, Web-WebSockets, Web-Mgmt-Tools, Web-Mgmt-Console, Web-Mgmt-Compat, Web-Metabase, Web-Scripting-Tools, Web-Mgmt-Service, NET-Framework-Features, NET-Framework-Core, NET-HTTP-Activation, NET-Non-HTTP-Activ, NET-Framework-45-Features, NET-Framework-45-Core, NET-Framework-45-ASPNET, NET-WCF-Services45, NET-WCF-HTTP-Activation45, NET-WCF-TCP-PortSharing45, Containers, MSMQ, MSMQ-Services, MSMQ-Server, Windows-Defender, RSAT, RSAT-Role-Tools, RSAT-AD-Tools, RSAT-ADLDS, RSAT-Hyper-V-Tools, Hyper-V-Tools, Hyper-V-PowerShell, SNMP-Service, SNMP-WMI-Provider, System-DataArchiver, PowerShellRoot, PowerShell, WAS, WAS-Process-Model, WAS-NET-Environment, WAS-Config-APIs, Windows-Server-Backup, Microsoft-Windows-Subsystem-Linux, WoW64-Support, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| AD LDS Instance SyngoConfiguration |  | Microsoft Corporation |  |
| Adobe Acrobat Reader | 25.001.20531 | Adobe Systems Incorporated | 17/06/2025 |
| Agentless Management Service | 3.30.0.0 | Hewlett Packard Enterprise Development LP |  |
| ALGO.IVT_ALGO2.All 11.1 (x64) | 11.01.2409.1102 | Siemens Healthcare GmbH | 17/06/2025 |
| Azure Data Studio | 1.41.0 | Microsoft Corporation | 11/07/2023 |
| Boost (Siemens - Repack) 1.69 (x64) | 01.69.0000.0001 | Siemens Healthcare GmbH | 17/06/2025 |
| Browser for SQL Server 2022 | 16.0.1000.6 | Microsoft Corporation | 31/08/2026 |
| CAT.LungCAD.All 10.5 (x64) | 10.05.2411.2801 | Siemens Healthcare GmbH | 17/06/2025 |
| Extern.Intel.oneDNN 13.5 (x64) | 13.05.2411.1401 | Siemens Healthcare GmbH | 17/06/2025 |
| Extern.MeVis.LesionSegmentation 13.5 (x64) | 13.05.2411.1504 | Siemens Healthcare GmbH | 17/06/2025 |
| FHIRAdapter.All 14.0 (x64) | 14.00.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| HPE Lights-Out Online Configuration Utility | 6.0.0.0 | Hewlett Packard Enterprise | 11/07/2023 |
| IIS URL Rewrite Module 2 | 7.2.1993 | Microsoft Corporation | 17/06/2025 |
| InnerSource.AlgoCore.All 13.5 (x64) | 13.05.2411.1401 | Siemens Healthcare GmbH | 17/06/2025 |
| InnerSource.AlgoSyngoInt.All 13.5 (x64) | 13.05.2411.1401 | Siemens Healthcare GmbH | 17/06/2025 |
| InnerSource.CTLesSeg.All 13.5 (x64) | 13.05.2411.1504 | Siemens Healthcare GmbH | 17/06/2025 |
| InnerSource.CTOrganSeg.All 13.5 (x64) | 13.05.2411.1501 | Siemens Healthcare GmbH | 17/06/2025 |
| InnerSource.CTPneumonia.All 13.5 (x64) | 13.05.2411.1501 | Siemens Healthcare GmbH | 17/06/2025 |
| Integrated Smart Update Tools for Windows | 4.1.0.0 | Hewlett Packard Enterprise | 11/07/2023 |
| Intel(R) QuickAssist Technology 2.0.4.0004 | 2.0.4.0004 | Intel | 03/08/2023 |
| IPP (Siemens - Repack) 21.11.0.533 (x64) | 21.11.0.533 | Siemens Healthcare GmbH | 17/06/2025 |
| IS.BasicOncoTools.All 13.3 (x64) | 13.03.2411.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| IS.Calibration.All 13.3 (x64) | 13.03.2410.3101 | Siemens Healthcare GmbH | 17/06/2025 |
| IS.CineAnatomy.All 13.3 (x64) | 13.03.2410.1601 | Siemens Healthcare GmbH | 17/06/2025 |
| MI_via_VB80_Limitation List_D4 | 4.3.0.0 | Siemens Healthcare | 17/06/2025 |
| MI_via_VB80_MI Organ Processing_D4 | 4.3.0.0 | Siemens Healthcare | 17/06/2025 |
| MI_via_VB80_OncoBoard_D4 | 4.3.0.0 | Siemens Healthcare | 17/06/2025 |
| MI_via_VB80D_MM Oncology_HF | 4.4.0.0 | Siemens Healthcare | 17/06/2025 |
| MI_via_VB80F_MI General_HF | 4.7.0.0 | Siemens Healthcare | 17/06/2025 |
| Microsoft .NET 8.0.8 - Windows Server Hosting | 8.0.8.24369 | Microsoft Corporation |  |
| Microsoft Application Request Routing 3.0 | 3.0.1988 | Microsoft Corporation | 17/06/2025 |
| Microsoft Edge | 152.0.4191.53 | Microsoft Corporation | 29/08/2026 |
| Microsoft Help Viewer 2.3 | 2.3.28307 | Microsoft Corporation |  |
| Microsoft ODBC Driver 17 for SQL Server | 17.10.6.1 | Microsoft Corporation | 17/06/2025 |
| Microsoft OLE DB Driver for SQL Server | 18.7.4.0 | Microsoft Corporation | 16/07/2025 |
| Microsoft SQL Server 2016 Management Objects  (x64) | 13.0.1601.5 | Microsoft Corporation | 11/07/2023 |
| Microsoft SQL Server 2022 (64-bit) |  | Microsoft Corporation |  |
| Microsoft SQL Server 2022 Setup (English) | 16.0.1190.2 | Microsoft Corporation | 31/08/2026 |
| Microsoft SQL Server Management Studio - 19.0 | 19.0.20196.0 | Microsoft Corporation |  |
| Microsoft System CLR Types for SQL Server 2016 | 13.0.1601.5 | Microsoft Corporation | 11/07/2023 |
| Microsoft Visual C++ 2013 Redistributable (x64) - 12.0.21005 | 12.0.21005.1 | Microsoft Corporation |  |
| Microsoft Visual C++ 2013 Redistributable (x86) - 12.0.40664 | 12.0.40664.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2022 Redistributable (x64) - 14.34.31938 | 14.34.31938.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2022 Redistributable (x86) - 14.38.33135 | 14.38.33135.0 | Microsoft Corporation |  |
| Microsoft Visual Studio Tools for Applications 2019 | 16.0.31110 | Microsoft Corporation |  |
| Microsoft VSS Writer for SQL Server 2022 | 16.0.1000.6 | Microsoft Corporation | 31/08/2026 |
| MKL (Siemens - Repack) 24.01 (x64) | 24.1.0.696 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-AutoAlignModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-DeepLearningModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-FASTAlignModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-FASTPlanningModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-LandmarkingModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-QualityCheckModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AiM-SpineModels.All 11.12 (x64) | 11.12.2408.2101 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.AnT.All 11.17 (x64) | 11.17.2409.1901 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.CIP.All 11.17 (x64) | 11.17.2411.1802 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.CIP-AppBase.All 11.17 (x64) | 11.17.2411.1502 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.CIP-DataDistrExt.All 11.17 (x64) | 11.17.2409.1901 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.CIP-Kernel.All 11.17 (x64) | 11.17.2411.1502 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.CIP-WebOption.All 11.17 (x64) | 11.17.2409.1906 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Core.All 11.13 (x64) | 11.13.2412.1002 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Core-Collaboration.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-AppBase.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-BrowserDsk.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-CacheBase.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-CacheStd.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-ClFileAcc.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-DataDistr.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-Kernel.All 11.13 (x64) | 11.13.2412.0601 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DataStorage-Lifecycle.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom.All 11.17 (x64) | 11.17.2412.1603 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom-AdminConfigPages.All 11.17 (x64) | 11.17.2412.1003 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom-DataHandling.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom-DesktopApps.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom-JobHandling.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Dicom-JobView.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DsktCore-Kernel.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.DsktCore-Security.All 11.13 (x64) | 11.13.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Findings-ImgConn.All 11.17 (x64) | 11.17.2410.0901 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Findings-Kernel.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-AdminPortal.All 11.13 (x64) | 11.13.2409.1704 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-AlgoInfra.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-AuthSrv.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-CertManCl.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-CloudLic.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-CommuInfra.All 11.13 (x64) | 11.13.2411.1501 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-Database.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-Diagnostics.AuditingService 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-FileLic.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-Kernel.All 11.13 (x64) | 11.13.2411.0801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-KernelServices.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-Licensing.All 11.13 (x64) | 11.13.2409.3001 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-ToggleInfra.All 11.12 (x64) | 11.12.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Foundations-WebCollab.All 11.13 (x64) | 11.13.2412.0301 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.HL7.All 11.3 (x64) | 11.03.2312.1601 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Imaging.All 11.17 (x64) | 11.17.2409.2301 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Imaging-Display.All 11.17 (x64) | 11.17.2409.2501 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Imaging-IvtAlgo.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Imaging-Kernel.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.ITF.All 11.17 (x64) | 11.17.2409.1901 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.JobScheduler.All 11.13 (x64) | 11.13.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.LCO.All 11.17 (x64) | 11.17.2409.1901 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.OpenApps.All 11.17 (x64) | 11.17.2411.0601 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.OpenApps-BrowserInt.All 11.17 (x64) | 11.17.2409.1902 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.ResultHandling-Kernel.All 11.17 (x64) | 11.17.2410.0902 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Service.All 11.17 (x64) | 11.17.2412.0301 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Service-CloudLic.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Service-Licensing.All 11.17 (x64) | 11.17.2409.1801 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Service-SetupNavigator.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.WebCore.All 11.17 (x64) | 11.17.2409.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| Modules.Workflow.All 11.17 (x64) | 11.17.2412.1601 | Siemens Healthcare GmbH | 17/06/2025 |
| MR_MROH-002G_601_Brevis_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_Cardio_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_General_DOC_5.2.0.0.msi | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_Neuro_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_Onco_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_Spectro_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_601_Vascular_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| MR_MROH-002G_623_RI_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| NVIDIA Graphics Driver 529.11 | 529.11 | NVIDIA Corporation | 03/08/2023 |
| NVIDIA RTX Desktop Manager 204.26 | 204.26 | NVIDIA Corporation | 03/08/2023 |
| Open Inventor (Siemens - Repack) 9.7 (x64) | 9.7.1.1 | Siemens Healthcare GmbH | 17/06/2025 |
| OpenSSH | 10.0.0.0 | Microsoft Corporation | 02/09/2026 |
| Operations-agent | 12.23.006 | Micro Focus |  |
| OrganProcessing | 10.830.2403.901 | Siemens Medical Solutions USA, Inc | 17/06/2025 |
| Pegasus (Siemens - Repack) 2.0 (x64) | 02.00.0674.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| Products.CarbonClinicals.RegulatoryInfo.All 11.3 (x64) | 11.03.2411.2801 | Siemens Healthcare GmbH | 17/06/2025 |
| SceniumRE | 9.0.0.101096 | Siemens Medical Solutions USA, Inc. | 17/06/2025 |
| Sentient Application Manager Agent | 11.00.0001 | Accelerite | 17/06/2025 |
| Siemens Knowledge Gateway | 4.5.1.0 | Siemens Healthineers | 17/06/2025 |
| Siemens OPENLink 23.5-7 Common - Local |  |  |  |
| SiemensH_OH_CT_VB80_BH-G | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_BP | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_BQ-G | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_BR | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CA | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CF | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CFFR | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CO | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_Common | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CP | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_CS | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_DA | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_DE | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_DT | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_EF | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_LA | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_LVO | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_MP | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_ND | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_NP | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_P3 | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_RI | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_RT | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CT_VB80_VA | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| SiemensH_OH_CTH_VT-P10 | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |
| Smart Storage Administrator | 6.15.11.0 | Microchip Technology Inc. | 08/05/2021 |
| Smart Storage Administrator CLI | 6.15.11.0 | Microchip Technology Inc. | 08/05/2021 |
| Smart Storage Administrator Diagnostics and SSD Wear Gauge Utility | 6.15.11.0 | Microchip Technology Inc. | 08/05/2021 |
| Software Distribution GUI | 2.1.30 | Siemens Healthcare GmbH | 17/06/2025 |
| SSC.FHIRCast.All 14.0 (x64) | 14.00.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| SY_Carbon_Clinicals_VA31_IFUs | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_IFU_CN_P02-001 | 16.0.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_IfU_P02-001_ADD_OLH_VB60i | 16.0.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_IfU_P02-001_AM_VB60i | 16.0.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_IfU_P02-001_OM_VB60i | 16.0.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_IfU_P02-001_QSG_VB80A | 16.0.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_OH_Basic_ALL_VB60D | 11.1.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_OH_Collection_MMR-QG_EN | 3.1.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_OH_FindingTypes_ALL_VB60A | 3.1.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_RN_P01-001_RN | 11.1.0.0 | Siemens Healthcare | 17/06/2025 |
| SY_RN_SmartReports_ADD | 10.1.0.0 | Siemens Healthcare | 17/06/2025 |
| syngo Client DeviceGuard Catalog Files | 10.2.1.0 | Siemens Healthcare GbmH | 17/06/2025 |
| syngo InstallToolsSelfUpdate | 1.2.0.0 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo Server DeviceGuard Catalog Files | 10.5.2501.901 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.ExternalReportingApplicationHosting | 4.1.2501.901 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.FlightRecorder | 5.0.0.0 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.Sphere.Config.Main 13.15 (x64) | 13.15.2412.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.Sphere.Server 13.15 (x64) | 13.15.2412.1701 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - Bootstrapper 8.0 | 8.0.0.0 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - Breast Care Server 10.0 (x64) | 10.00.0014.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - Breast Care Server BreastCorrelation 2.2 (x64) | 02.02.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - Breast Care Server ScrBreast 2.9 (x64) | 02.09.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - Breast Care Server Serviceimages 2.2 (x64) | 02.02.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - CT Liver Analysis Server 10.0 (x64) | 10.00.0012.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - CT_Liver_Analysis MeVisLab App 9.0 (x64) | 09.00.0001.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - MM Breast Reading Server 10.0 (x64) | 10.00.0015.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - syngo.via Client 10.6 (x64) | 10.06.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| syngo.via - syngo.via Server 10.6 (x64) | 10.06.0000.0000 | Siemens Healthcare GmbH | 17/06/2025 |
| TeamViewer (Siemens - Repack) | 15.41.8.0 | Siemens Healthcare GmbH | 17/06/2025 |
| TeamViewer ModeratorGateway (Siemens - Repack) | 15.41.8.0 | Siemens Healthcare GmbH | 17/06/2025 |
| TeamViewer TeamConnector (Siemens - Repack) | 15.41.8.0 | Siemens Healthcare GmbH | 17/06/2025 |
| tomcat(x64) | 9.0.85 | Siemens Healthcare GmbH | 17/06/2025 |
| TSplus for Siemens version 19.40.8.11 | 19.40.8.11 | TSplus | 15/08/2026 |
| Uninstall Application Publishing |  |  |  |
| VNC Viewer (Siemens - Repack) 1.2 (x64) | 1.2.43.17 | Siemens Healthcare GmbH | 17/06/2025 |
| WPTx64 (OnecoreUAP) | 10.1.22621.1 | Microsoft | 17/06/2025 |
| XP_XP-VIAG_BreastCare-OM_syngo.via_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| XP_XP-VIAG_BreastCare-RI_syngo.via_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| XP_XP-VIAG_Mammovista-OM_syngo.via_DOC_5.1.0.0.msi | 5.1.0.0 | Siemens Healthcare | 17/06/2025 |
| XP_XP-VIAG_Mammovista-RI_syngo.via_DOC_5.2.0.0.msi | 5.2.0.0 | Siemens Healthcare | 17/06/2025 |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| Adobe Acrobat Update Service (`AdobeARMservice`) | Running | LocalSystem | "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\armsvc.exe" |
| Agentless Management Service (`ams`) | Running | LocalSystem | "C:\Program Files\OEM\AMS\service\ams.exe" |
| Microsoft Edge Update Service (edgeupdate) (`edgeupdate`) | Stopped | LocalSystem | "C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /svc |
| syngo.Services.FileTransferService (`FileTransferService`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo\bin\syngo.Services.FileTransferService.exe" |
| FLEXlm License Server (`FLEXlm License Server`) | Running | NT AUTHORITY\NetworkService | "C:\Program Files\Siemens\syngo\bin\lmgrd.exe" |
| HP Software Shared Trace Service (`HPOvTrcSvc`) | Running | LocalSystem | "C:\SysMgmt\EMAgent\bin\win64\ovtrcsvc.exe" |
| Microsoft Defender Core Service (`MDCoreSvc`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26070.9-0\MpDefenderCoreService.exe" |
| SQL Server (MSSQLSERVER_SYDS) (`MSSQL$MSSQLSERVER_SYDS`) | Running | NT Service\MSSQL$MSSQLSERVER_SYDS | "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER_SYDS\MSSQL\Binn\sqlservr.exe" -sMSSQLSERVER_SYDS |
| HP OpenView Ctrl Service (`OvCtrl`) | Running | LocalSystem | "C:\sysmgmt\EMAgent\bin\win64\ovcd.exe" |
| RCA Notify Daemon (`Radexecd`) | Running | LocalSystem | C:\SYSMGMT\SDAgent\radexecd.exe |
| RCA Scheduler Daemon (`Radsched`) | Running | LocalSystem | C:\SYSMGMT\SDAgent\radsched.exe |
| RCA MSI Redirector (`Radstgms`) | Running | LocalSystem | C:\SYSMGMT\SDAgent\Radstgms.exe |
| System Management Assistant Service (`sma`) | Running | LocalSystem | "C:\Program Files\OEM\AMS\service\sma.exe" |
| SQL Server Agent (MSSQLSERVER_SYDS) (`SQLAgent$MSSQLSERVER_SYDS`) | Running | NT Service\SQLAgent$MSSQLSERVER_SYDS | "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER_SYDS\MSSQL\Binn\SQLAGENT.EXE" -i MSSQLSERVER_SYDS |
| SQL Server CEIP service (MSSQLSERVER_SYDS) (`SQLTELEMETRY$MSSQLSERVER_SYDS`) | Running | NT Service\SQLTELEMETRY$MSSQLSERVER_SYDS | "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER_SYDS\MSSQL\Binn\sqlceip.exe" -Service MSSQLSERVER_SYDS |
| SQL Server VSS Writer (`SQLWriter`) | Running | LocalSystem | "C:\Program Files\Microsoft SQL Server\90\Shared\sqlwriter.exe" |
| OpenSSH Authentication Agent (`ssh-agent`) | Running | LocalSystem | "C:\Program Files\OpenSSH\ssh-agent.exe" |
| OpenSSH SSH Server (`sshd`) | Running | LocalSystem | "C:\Program Files\OpenSSH\sshd.exe" |
| Integrated Smart Update Tools (`SUTService`) | Running | LocalSystem | C:/Program Files/SUT/bin/sut.exe /svc |
| Application Publishing Service (APS) (`SVCM`) | Running | LocalSystem | "C:\Siemens\svcmain.exe" |
| syngo Client Update Service (`syngo Client Update Service`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo.client\bin\CUS\syngoClientBootstrapping.exe" |
| syngo RemoteConnectionSupport Service (`syngo RemoteConnectionSupport Service`) | Running | NT AUTHORITY\NetworkService | "C:\Program Files\Siemens\syngo\bin\syngo.RemoteServices.OPM.SrsBase.RemoteConnectionSupportService.exe" |
| syngo.Common.LCMService (`syngo.Common.LCMService`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo\bin\syngo.Common.LCMService.exe" |
| syngo.Services.TF.Component.Media.CDDVDServiceManager (`syngo.Services.TF.Component.Media.CDDVDServiceManager`) | Running | LocalSystem | "C:\Program Files\Siemens\syngo.client\bin\syngo.Services.TF.Component.Media.CDDVDServiceManager.exe" -config "C:\Program Files\Siemens\syngo.client\bin" |
| SysMgmt.WcfService (`SysMgmt.WcfService`) | Running | LocalSystem | "C:\SysMgmt\service\mwtools\SysMgmt.WcfService.exe" |
| Microsoft Defender Antivirus Service (`WinDefend`) | Running | LocalSystem | "C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26070.9-0\MsMpEng.exe" |
| ms-resource:AppName (`WslInstaller`) | Stopped | LocalSystem | "C:\Program Files\WindowsApps\MicrosoftCorporationII.WindowsSubsystemForLinux_2.2.4.0_x64__8wekyb3d8bbwe\wslinstaller.exe" |
| WSL Service (`WSLService`) | Running | LocalSystem | "C:\Program Files\WSL\wslservice.exe" |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 22 | ::, 0.0.0.0 | sshd (sshd) |
| TCP | 53 | 172.25.0.1 | dockerd (docker) |
| TCP | 80 | ::, 127.0.0.1 | System |
| TCP | 104 | :: | syngo.Common.Container |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 172.25.0.1, 172.28.128.1 | System |
| TCP | 443 | :: | System |
| TCP | 445 | :: | System |
| TCP | 1801 | ::, 0.0.0.0 | mqsvc (MSMQ) |
| TCP | 2103 | ::, 0.0.0.0 | mqsvc (MSMQ) |
| TCP | 2105 | ::, 0.0.0.0 | mqsvc (MSMQ) |
| TCP | 2107 | ::, 0.0.0.0 | mqsvc (MSMQ) |
| TCP | 2179 | ::, 0.0.0.0 | vmms (vmms) |
| TCP | 2762 | :: | syngo.Common.Container |
| TCP | 3125 | 127.0.0.1 | syngo.Common.Web.IdentityProxy |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 3460 | 0.0.0.0 | Radstgms (Radstgms) |
| TCP | 5053 | 0.0.0.0 | ovtrcsvc (HPOvTrcSvc) |
| TCP | 5357 | :: | System |
| TCP | 5445 | 0.0.0.0 | syngo.CT.Services.FtpTaskflowFileHandler |
| TCP | 5555 | ::, 0.0.0.0 | syngo.RemoteServices.OM.SystemStatusMonitoringRSC.Central.Service |
| TCP | 5559 | :: | System |
| TCP | 5570 | :: | System |
| TCP | 5571 | :: | System |
| TCP | 5985 | :: | System |
| TCP | 7680 | :: | svchost (DoSvc) |
| TCP | 8090 | :: | javaw |
| TCP | 8226 | ::, 0.0.0.0 | radexecd (Radexecd) |
| TCP | 8282 | :: | System |
| TCP | 8889 | :: | System |
| TCP | 9203 | ::, 0.0.0.0 | syngo.Common.LCMService |
| TCP | 9389 | ::, 0.0.0.0 | Microsoft.ActiveDirectory.WebServices (ADWS) |
| TCP | 9455 | :: | System |
| TCP | 9974 | :: | syngo.HL7.Services.ReceiverServer |
| TCP | 9975 | :: | syngo.HL7.Services.ReceiverServer |
| TCP | 9995 | ::, 0.0.0.0 | syngo.RemoteServices.OM.SystemStatusMonitoringRSC.Central.Service |
| TCP | 9996 | ::, 0.0.0.0 | syngo.RemoteServices.OM.LocalMonitoringServiceRSC.Local.Service |
| TCP | 12997 | 0.0.0.0 | IvtMemoryServer |
| TCP | 13001 | :: | ovbbccb |
| TCP | 27000 | :: | lmgrd |
| TCP | 27010 | :: | SAG_med_daemon |
| TCP | 32912 | ::, 0.0.0.0 | syngo.Common.Communication.PatternPublishService |
| TCP | 32914 | ::, 0.0.0.0 | SMSvcHost (NetTcpActivator, NetTcpPortSharing) |
| TCP | 34816 | :: | System |
| TCP | 44384 | :: | dotnet |
| TCP | 47001 | :: | System |
| TCP | 47097 | 127.0.0.1 | System |
| TCP | 47098 | :: | dotnet |
| TCP | 47101 | ::, 0.0.0.0 | syngo.Security.AuthorizationServer.Host |
| TCP | 47103 | fe80::9a11:13c7:e952:39d4%14 | syngo.Common.Diagnostics.Auditing.Service.Host |
| TCP | 47104 | 127.0.0.1 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 48100 | 127.0.0.1 | MeVisLabWorkerService |
| TCP | 48150 | 127.0.0.1 | MeVisLabWorkerService |
| TCP | 49664 | ::, 0.0.0.0 | lsass (KeyIso, SamSs) |
| TCP | 49665 | ::, 0.0.0.0 | wininit |
| TCP | 49666 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 49667 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 49668 | ::, 0.0.0.0 | svchost (SessionEnv) |
| TCP | 49671 | ::, 0.0.0.0 | spoolsv (Spooler) |
| TCP | 49672 | ::, 0.0.0.0 | mqsvc (MSMQ) |
| TCP | 49681 | ::, 0.0.0.0 | dsamain (ADAM_SyngoConfiguration) |
| TCP | 49690 | ::1 | ovcd (OvCtrl) |
| TCP | 49700 | ::, 0.0.0.0 | services |
| TCP | 49839 | ::1 | ovcd (OvCtrl) |
| TCP | 49840 | ::1, 127.0.0.1 | sqlservr (MSSQL$MSSQLSERVER_SYDS) |
| TCP | 49844 | ::1 | ovconfd |
| TCP | 49877 | ::1 | opcmsgi |
| TCP | 49897 | ::1 | opcmsga |
| TCP | 49946 | ::1 | opcacta |
| TCP | 50000 | ::, 0.0.0.0 | dsamain (ADAM_SyngoConfiguration) |
| TCP | 50001 | ::, 0.0.0.0 | dsamain (ADAM_SyngoConfiguration) |
| TCP | 50057 | 0.0.0.0 | syngo.Common.Container |
| TCP | 50058 | :: | syngo.Common.Container |
| TCP | 50065 | 0.0.0.0 | syngo.Common.Container |
| TCP | 50066 | :: | syngo.Common.Container |
| TCP | 51972 | 0.0.0.0 | syngo.Common.Container |
| TCP | 51973 | :: | syngo.Common.Container |
| TCP | 51975 | 0.0.0.0 | syngo.Common.Container |
| TCP | 51976 | :: | syngo.Common.Container |
| TCP | 51982 | 0.0.0.0 | syngo.Common.Container |
| TCP | 51983 | :: | syngo.Common.Container |
| TCP | 51987 | 0.0.0.0 | syngo.Common.Container |
| TCP | 51988 | :: | syngo.Common.Container |
| TCP | 52264 | 0.0.0.0 | syngo.Common.Container |
| TCP | 52265 | :: | syngo.Common.Container |
| TCP | 53296 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53297 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53300 | 127.0.0.1 | MeVisLabWorkerService |
| TCP | 53301 | 127.0.0.1 | MeVisLabWorkerService |
| TCP | 53308 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53309 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53399 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53400 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53407 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53408 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53450 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53451 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53454 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53455 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53458 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53459 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53463 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53464 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53470 | 0.0.0.0 | syngo.Common.Communication.PatternPublishService |
| TCP | 53471 | :: | syngo.Common.Communication.PatternPublishService |
| TCP | 53497 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53498 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53503 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53504 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53512 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53513 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53541 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53542 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53559 | 0.0.0.0 | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53560 | :: | syngo.Common.Communication.DynamicServices.Host |
| TCP | 53568 | 0.0.0.0 | w3wp |
| TCP | 53569 | :: | w3wp |
| TCP | 53591 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53592 | :: | syngo.Common.Container |
| TCP | 53658 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53660 | :: | syngo.Common.Container |
| TCP | 53670 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53671 | :: | syngo.Common.Container |
| TCP | 53672 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53673 | :: | syngo.Common.Container |
| TCP | 53731 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53732 | :: | syngo.Common.Container |
| TCP | 53758 | 0.0.0.0 | syngo.CT.BizLogic.PacsReady.Host.RRT |
| TCP | 53759 | :: | syngo.CT.BizLogic.PacsReady.Host.RRT |
| TCP | 53776 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53777 | :: | syngo.Common.Container |
| TCP | 53811 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53813 | :: | syngo.Common.Container |
| TCP | 53824 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53825 | :: | syngo.Common.Container |
| TCP | 53838 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53839 | :: | syngo.Common.Container |
| TCP | 53846 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53847 | :: | syngo.Common.Container |
| TCP | 53854 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53855 | :: | syngo.Common.Container |
| TCP | 53857 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53859 | :: | syngo.Common.Container |
| TCP | 53870 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53871 | :: | syngo.Common.Container |
| TCP | 53877 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53878 | :: | syngo.Common.Container |
| TCP | 53894 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53895 | :: | syngo.Common.Container |
| TCP | 53917 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53918 | :: | syngo.Common.Container |
| TCP | 53937 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53938 | :: | syngo.Common.Container |
| TCP | 53964 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53965 | :: | syngo.Common.Container |
| TCP | 53976 | 0.0.0.0 | syngo.Common.Container |
| TCP | 53977 | :: | syngo.Common.Container |
| TCP | 54003 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54004 | :: | syngo.Common.Container |
| TCP | 54015 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54016 | :: | syngo.Common.Container |
| TCP | 54030 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54031 | :: | syngo.Common.Container |
| TCP | 54041 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54042 | :: | syngo.Common.Container |
| TCP | 54052 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54053 | :: | syngo.Common.Container |
| TCP | 54060 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54061 | :: | syngo.Common.Container |
| TCP | 54065 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54066 | :: | syngo.Common.Container |
| TCP | 54071 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54072 | :: | syngo.Common.Container |
| TCP | 54096 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54097 | :: | syngo.Common.Container |
| TCP | 54105 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54106 | :: | syngo.Common.Container |
| TCP | 54128 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54131 | :: | syngo.Common.Container |
| TCP | 54150 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54151 | :: | syngo.Common.Container |
| TCP | 54167 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54168 | :: | syngo.Common.Container |
| TCP | 54186 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54187 | :: | syngo.Common.Container |
| TCP | 54202 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54203 | :: | syngo.Common.Container |
| TCP | 54214 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54215 | :: | syngo.Common.Container |
| TCP | 54224 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54225 | :: | syngo.Common.Container |
| TCP | 54240 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54241 | :: | syngo.Common.Container |
| TCP | 54247 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54248 | :: | syngo.Common.Container |
| TCP | 54250 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54251 | :: | syngo.Common.Container |
| TCP | 54347 | 0.0.0.0 | syngo.Services.Workflow.Server |
| TCP | 54348 | :: | syngo.Services.Workflow.Server |
| TCP | 54435 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54436 | :: | syngo.Common.Container |
| TCP | 54437 | 0.0.0.0 | syngo.Common.Container |
| TCP | 54438 | :: | syngo.Common.Container |
| TCP | 54446 | 0.0.0.0 | syngo.Services.ExtAppHosting.ServiceHost |
| TCP | 54447 | :: | syngo.Services.ExtAppHosting.ServiceHost |
| TCP | 55815 | 0.0.0.0 | syngo.Common.Container |
| TCP | 55816 | :: | syngo.Common.Container |
| TCP | 55898 | 0.0.0.0 | syngo.Common.Container |
| TCP | 55899 | :: | syngo.Common.Container |
| TCP | 56158 | 0.0.0.0 | syngo.Viewing.Shell.Host |
| TCP | 56159 | :: | syngo.Viewing.Shell.Host |
| TCP | 56250 | 0.0.0.0 | syngo.Common.Container |
| TCP | 56251 | :: | syngo.Common.Container |
| TCP | 56385 | 0.0.0.0 | syngo.Viewing.Shell.Host |
| TCP | 56386 | :: | syngo.Viewing.Shell.Host |
| TCP | 57235 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57236 | :: | syngo.Common.Container |
| TCP | 57253 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57254 | :: | syngo.Common.Container |
| TCP | 57272 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57273 | :: | syngo.Common.Container |
| TCP | 57284 | 0.0.0.0 | syngo.Common.Container |
| TCP | 57285 | :: | syngo.Common.Container |
| TCP | 58079 | 0.0.0.0 | syngo.Common.Container |
| TCP | 58080 | :: | syngo.Common.Container |
| TCP | 60269 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60270 | :: | syngo.Common.Container |
| TCP | 60581 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60582 | :: | syngo.Common.Container |
| TCP | 60600 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60601 | :: | syngo.Common.Container |
| TCP | 60611 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60612 | :: | syngo.Common.Container |
| TCP | 60957 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60958 | :: | syngo.Common.Container |
| TCP | 60988 | 0.0.0.0 | syngo.Common.Container |
| TCP | 60989 | :: | syngo.Common.Container |
| TCP | 61713 | 0.0.0.0 | syngo.Viewing.Shell.Host |
| TCP | 61714 | :: | syngo.Viewing.Shell.Host |
| TCP | 61732 | 0.0.0.0 | syngo.Viewing.Shell.Host |
| TCP | 61733 | :: | syngo.Viewing.Shell.Host |
| TCP | 62526 | 0.0.0.0 | syngo.Common.Container |
| TCP | 62527 | :: | syngo.Common.Container |
| TCP | 63288 | 0.0.0.0 | syngo.Common.Container |
| TCP | 63289 | :: | syngo.Common.Container |
| TCP | 63503 | 0.0.0.0 | syngo.Common.Container |
| TCP | 63504 | :: | syngo.Common.Container |
| TCP | 63785 | 0.0.0.0 | syngo.Common.Container |
| TCP | 63786 | :: | syngo.Common.Container |
| TCP | 63830 | 0.0.0.0 | syngo.Common.Container |
| TCP | 63831 | :: | syngo.Common.Container |
| TCP | 63924 | 0.0.0.0 | syngo.Common.Container |
| TCP | 63925 | :: | syngo.Common.Container |
| TCP | 64095 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64096 | :: | syngo.Common.Container |
| TCP | 64107 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64108 | :: | syngo.Common.Container |
| TCP | 64141 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64142 | :: | syngo.Common.Container |
| TCP | 64146 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64147 | :: | syngo.Common.Container |
| TCP | 64150 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64151 | :: | syngo.Common.Container |
| TCP | 64154 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64155 | :: | syngo.Common.Container |
| TCP | 64158 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64159 | :: | syngo.Common.Container |
| TCP | 64162 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64163 | :: | syngo.Common.Container |
| TCP | 64166 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64167 | :: | syngo.Common.Container |
| TCP | 64170 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64171 | :: | syngo.Common.Container |
| TCP | 64174 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64175 | :: | syngo.Common.Container |
| TCP | 64178 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64179 | :: | syngo.Common.Container |
| TCP | 64242 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64243 | :: | syngo.Common.Container |
| TCP | 64259 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64260 | :: | syngo.Common.Container |
| TCP | 64271 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64272 | :: | syngo.Common.Container |
| TCP | 64746 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64747 | :: | syngo.Common.Container |
| TCP | 64770 | 0.0.0.0 | syngo.Common.Container |
| TCP | 64771 | :: | syngo.Common.Container |
| TCP | 65366 | 0.0.0.0 | syngo.Common.Container |
| TCP | 65367 | :: | syngo.Common.Container |
| TCP | 65387 | 0.0.0.0 | syngo.Common.Container |
| TCP | 65388 | :: | syngo.Common.Container |
| TCP | 65505 | 0.0.0.0 | syngo.Common.Container |
| TCP | 65506 | :: | syngo.Common.Container |
| UDP | 53 | 172.25.0.1 | dockerd (docker) |
| UDP | 53 | 0.0.0.0 | svchost (SharedAccess) |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 172.25.0.1, 172.28.128.1 | System |
| UDP | 138 | 172.25.0.1, 172.28.128.1 | System |
| UDP | 161 | ::, 0.0.0.0 | snmp (SNMP) |
| UDP | 3702 | ::, 0.0.0.0 | svchost (FDResPub) |
| UDP | 5353 | :: | msedge |
| UDP | 5353 | 0.0.0.0 | svchost (Dnscache) |
| UDP | 5355 | ::, 0.0.0.0 | svchost (Dnscache) |

## Partages SMB

| Partage | Chemin | Description |
|---|---|---|
| Activity Settings | C:\Program Files (x86)\Siemens\OrganProcessing\Activity Settings |  |
| WorkflowTemplates | C:\Program Files (x86)\Siemens\OrganProcessing\Workflows\Template |  |

## Taches planifiees hors Microsoft

| Tache | Etat | Action |
|---|---|---|
| \Adobe Acrobat Update Task | Ready | C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARM.exe |
| \AssetInformationCollectionDaily | Ready | syngo.RemoteServices.OM.AssetInformationProvider.AssetInformationCollector.exe |
| \CleanManager | Ready | syngo.common.starter.exe -SY.VIA.SSM.EXT.Cleanup |
| \CollectLogStatistics | Ready | syngo.Common.Diagnostics.SDC.CollectorTask.exe -LS |
| \CollectSystemUsageInformation | Ready | syngo.Common.Diagnostics.SDC.CollectorTask.exe -SUI |
| \CollectUtilizationStatistics | Ready | syngo.Common.Diagnostics.SDC.CollectorTask.exe -U |
| \DeleteNVDIASettingsFlagFile | Ready | "c:\windows\system32\cmd.exe" /c del c:\store\nVidiaSettingsNeedReboot.txt |
| \HealthCheck | Ready | "C:\Program Files\Siemens\syngo\OperationalManagement\HealthCheck\runHealthCheck.bat" |
| \LogMessage Repository Database Scheduled Cleanup | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Common.Diagnostics.Logging.DBHelper.exe" -cleanup -keeptime 10 -recordlimit 5000 |
| \MicrosoftEdgeUpdateTaskMachineCore | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /c |
| \MicrosoftEdgeUpdateTaskMachineUA | Ready | C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe /ua /installsource scheduler |
| \nWizard_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} | Ready | C:\Program Files\NVIDIA Corporation\nview\nwiz.exe /installquiet |
| \Rebuild_DB_Index_Weekly | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Common.starter.exe" -v -f C:\Store\log\RebuildIndexRunner.log -sw.shell [ /c \"C:\Program Files\Siemens\syngo\bin\Services\MSSQL\RebuildIndex.bat\" ] |
| \renewIpSettings | Ready | "c:\windows\system32\ipconfig.exe" /renew |
| \Restart Terminal Services | Ready | "C:\Windows\System32\cmd.exe" /C C:\Siemens\RestartTerminalServices.bat > C:\Siemens\RestartTerminalServices.log |
| \StartServicesFix | Ready | C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy ByPass -Command &'C:\Program Files\Siemens\syngo\bin\Start-Services.ps1' |
| \syngo.CheckDatabaseCorruption | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Services.sDM.DatabaseTool.exe" -checkDB |
| \syngo.DeleteOldSqlDumps | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Services.sDM.DatabaseTool.exe" -deleteOldSqlDumps |
| \syngo.Ngen.Handling | Ready | C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe -SY.NgenService |
| \syngo.PreCheckAgent | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe" -SY.SYSA_SrsMaintenance.PreCheckAgent.Exec |
| \syngo.RDC | Ready | ReliabilityDataCollector.exe /i c:\store\log /ot /t yesterday /logdir c:\store\log |
| \syngo.Reporting_DbCleanup | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe" -Reporting.DbCleanup |
| \syngo.ServerOSRestart | Ready | "C:\Program Files\Siemens\syngo\bin\ServerRestart.exe" /operation OSRestart /RetryInterval 1 /RetryCount 60 |
| \syngo.ServerRestart | Ready | "C:\Program Files\Siemens\syngo\bin\ServerRestart.exe" /operation restart /RetryInterval 1 /RetryCount 60 |
| \syngo.Services.sDM.Maintenance | Ready | C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe -sDM.MaintenanceTask |
| \syngo.SilentInstallation | Ready | "C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe" -SY.SYSA_SrsMaintenance.SilentInstallation.Exec |
| \syngo.StsDefrag | Disabled | C:\Program Files\Siemens\syngo\bin\syngo.Services.sDM.STS.Defrag.exe -auto |
| \MNP\CheckFeedback | Ready | C:\sysmgmt\sdagent\nvdkit.exe c:\sysmgmt\sdagent\MedClient.tkd CheckFeedback |
| \Siemens\Backup_syngo.via | Ready | C:\Program Files\Siemens\syngo\bin\syngo.Common.Starter.exe -f "C:\Store\log\BackupRestore\backup.log" -SY.SYSA_BackupRestore.Backup.All [ var SYSTEMPARTITION_TARGETDRIVE=N: var DATABASE_TARGETDRIVE=M: ] |
| \Siemens\syngo.User.Cleanup | Ready | Powershell.exe -ExecutionPolicy ByPass -command & 'C:\Program Files\Siemens\syngo\Setup\Scripts\CleanupUserProfiles.ps1' |

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5120241 | Security Update | 31/08/2026 |
| KB5120242 | Security Update | 31/08/2026 |
| KB5120705 | Update | 31/08/2026 |
| KB5068786 | Security Update | 11/12/2025 |

## Securite locale

Microsoft Defender : service actif, protection temps reel **DESACTIVEE**, signatures du 01/09/2026, moteur 1.1.26070.7

| Profil pare-feu | Actif | Entrant par defaut | Sortant par defaut |
|---|---|---|---|
| Domain | oui | NotConfigured | NotConfigured |
| Private | oui | NotConfigured | NotConfigured |
| Public | oui | NotConfigured | NotConfigured |

## Comptes locaux

**635 comptes locaux** : 630 actifs, 5 desactives.

Membres du groupe Administrateurs : `SYNGOVIA-135113\adminUser` (User, Local), `SYNGOVIA-135113\alocal` (User, Local), `SYNGOVIA-135113\aremote` (User, Local), `SYNGOVIA-135113\jbouteiller` (User, Local), `SYNGOVIA-135113\matthieu` (User, Local), `SYNGOVIA-135113\Matthieu CAPON` (User, Local), `SYNGOVIA-135113\MedAdmin` (User, Local), `SYNGOVIA-135113\RemoteAdmin` (User, Local), `SYNGOVIA-135113\siemens_apps` (User, Local), `SYNGOVIA-135113\SyngoCmd0` (User, Local)
