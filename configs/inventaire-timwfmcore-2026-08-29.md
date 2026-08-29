# Inventaire timwfmcore - 29/08/2026 16:48

_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._

> Releve fait SANS droits administrateur : certaines sections seront incompletes.

## Identite

| | |
|---|---|
| Hostname | `TIMWFMCORE` (workgroup WORKGROUP) |
| Modele | QEMU Standard PC (i440FX + PIIX, 1996) |
| OS | Microsoft Windows Server 2019 Datacenter 1809 (build 17763) |
| Installe le | 27/02/2023 |
| Dernier boot | 01/06/2026 16:48 (uptime 89 j 0 h) |
| Fuseau | Romance Standard Time |
| Licence | active - Retail |

## CPU

| Socket | Modele | Coeurs / threads | Frequence |
|---|---|---|---|
| CPU 0 | Common KVM processor | 12c/12t | 2.6 GHz |

## RAM

**64 Go** en 4 barrette(s) sur 4 slot(s), 64 Go max, ECC multi-bit

| Slot | Capacite | Type | Vitesse | Reference |
|---|---|---|---|---|
| DIMM 0 | 16 Go | type 7 |  MHz | QEMU  |
| DIMM 1 | 16 Go | type 7 |  MHz | QEMU  |
| DIMM 2 | 16 Go | type 7 |  MHz | QEMU  |
| DIMM 3 | 16 Go | type 7 |  MHz | QEMU  |

## Carte mere / BIOS

| | |
|---|---|
| Carte mere |   |
| Numero de serie |  |
| BIOS | rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org du 01/04/2014 |

## Disques physiques

| # | Modele | Bus | Type | Taille | Sante |
|---|---|---|---|---|---|
| 0 | Red Hat VirtIO | SCSI | Unspecified | 350 Go | Healthy |
| 1 | Red Hat VirtIO | SCSI | Unspecified | 2000 Go | Healthy |
| 2 | Red Hat VirtIO | SCSI | Unspecified | 700 Go | Healthy |
| 3 | Red Hat VirtIO | SCSI | Unspecified | 4096 Go | Healthy |

## Volumes

| Lettre | Label | FS | Taille | Libre |
|---|---|---|---|---|
| - | System Reserved | NTFS | 0.5 Go | 0.1 Go |
| C: | SYSTEM | NTFS | 299.5 Go | 100.8 Go |
| D: | Service | NTFS | 50 Go | 46.5 Go |
| F: | Database | NTFS | 2000 Go | 336 Go |
| G: | BACKUP | NTFS | 1000 Go | 388.2 Go |
| I: | Images02_TO_NOT_USED | NTFS | 4096 Go | 4055.8 Go |

## Reseau

| Interface | Description | MAC | Vitesse | Etat |
|---|---|---|---|---|
| Ethernet | Red Hat VirtIO Ethernet Adapter #2 | `BC-24-11-61-C4-EB` | 10 Gbps | Up |
| Ethernet Instance 0 | Red Hat VirtIO Ethernet Adapter | `02-D5-1E-40-16-18` | 10 Gbps | Up |

| Interface | IPv4 | Passerelle | DNS |
|---|---|---|---|
| Ethernet | 192.168.171.1/24 |  |  |
| Ethernet Instance 0 | 192.168.101.52/28 | 192.168.101.62 | 192.168.101.62, 8.8.8.8 |

## Roles et fonctionnalites

- **File and Storage Services** (`FileAndStorage-Services`)
- **Web Server (IIS)** (`Web-Server`)

Fonctionnalites : File-Services, FS-FileServer, Storage-Services, Web-WebServer, Web-Common-Http, Web-Default-Doc, Web-Dir-Browsing, Web-Http-Errors, Web-Static-Content, Web-Health, Web-Http-Logging, Web-Log-Libraries, Web-Request-Monitor, Web-Http-Tracing, Web-Performance, Web-Stat-Compression, Web-Security, Web-Filtering, Web-Basic-Auth, Web-IP-Security, Web-Url-Auth, Web-App-Dev, Web-Net-Ext45, Web-AppInit, Web-ASP, Web-Asp-Net45, Web-CGI, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Mgmt-Tools, Web-Mgmt-Console, Web-Mgmt-Compat, Web-Metabase, Web-WMI, NET-Framework-45-Features, NET-Framework-45-Core, NET-Framework-45-ASPNET, NET-WCF-Services45, NET-WCF-HTTP-Activation45, NET-WCF-Pipe-Activation45, NET-WCF-TCP-PortSharing45, Server-Media-Foundation, Multipath-IO, System-DataArchiver, Telnet-Client, Windows-Defender, PowerShellRoot, PowerShell, PowerShell-ISE, WAS, WAS-Process-Model, WAS-Config-APIs, Windows-Server-Backup, WoW64-Support, XPS-Viewer

## Logiciels installes

| Logiciel | Version | Editeur | Installe le |
|---|---|---|---|
| 7-Zip 19.00 (x64 edition) | 19.00.00.0 | Igor Pavlov | 07/03/2023 |
| ActivePerl 5.16.3 Build 1603 (64-bit) | 5.16.1603 | ActiveState | 07/03/2023 |
| AnyDesk | ad 9.0.14 | AnyDesk Software GmbH |  |
| Apache Ignite ODBC 64-bit Driver | 2.8.1.46481 | The Apache Software Foundation | 07/03/2023 |
| Apache Tomcat 7.0 Tomcat7 (remove only) | 7.0.109 | The Apache Software Foundation |  |
| AppFabric 1.1 for Windows Server | 1.1.2106.32 | Microsoft Corporation |  |
| Eclipse Temurin JDK with Hotspot 8u312-b07 (x64) | 8.0.312.7 | Eclipse Adoptium | 07/03/2023 |
| Effective File Search 6.8.1 | 6.8.1 | SOW |  |
| Google Chrome | 151.0.7922.174 | Google LLC | 25/08/2026 |
| IIS URL Rewrite Module 2 | 7.2.2 | Microsoft Corporation | 07/03/2023 |
| Microsoft .NET Core 2.2.6 - Windows Server Hosting | 2.2.6.0 | Microsoft Corporation |  |
| Microsoft .NET Core Runtime - 2.2.6 (x64) | 2.2.6.27818 | Microsoft Corporation |  |
| Microsoft .NET Core Runtime - 2.2.6 (x86) | 2.2.6.27818 | Microsoft Corporation |  |
| Microsoft Application Request Routing 3.0 | 3.0.1750 | Microsoft Corporation | 07/03/2023 |
| Microsoft ASP.NET MVC 4 | 4.0.20714.0 | Microsoft Corporation |  |
| Microsoft Visual C++ 2012 Redistributable (x64) - 11.0.60610 | 11.0.60610.1 | Microsoft Corporation |  |
| Microsoft Visual C++ 2015-2019 Redistributable (x64) - 14.20.27508 | 14.20.27508.1 | Microsoft Corporation |  |
| Microsoft Web Farm Framework | 1.1.1292 | Microsoft Corporation | 07/03/2023 |
| Mirth Connect 3.5.2.b204 | 3.5.2.b204 | Mirth Corporation |  |
| Notepad++ (64-bit x64) | 8.8.7 | Notepad++ Team |  |
| NXLog-CE | 2.9.1347 | NXLog Ltd | 07/03/2023 |
| Octopus Deploy Tentacle | 9.1.3772 | Octopus Deploy Pty. Ltd. | 28/04/2026 |
| Oracle 12.1 Client | 12.0.0.0 | Carestream | 07/03/2023 |
| Philips Telemedicine Remote Agent version 3.4.0 | 3.4.0 | Philips France Commercial | 02/05/2023 |
| PhilipsMEMOProductExporter | 1.7.1.8 | Philips | 26/06/2026 |
| PhilipsMEMOProductExporterWrapperWin | 1.0.0.0 | Philips | 26/06/2026 |
| PhilipsMEMOPrometheusWin | 2.53.5.0 | Philips | 26/06/2026 |
| PhilipsMEMOWindowsExporter | 0.29.2.0 | Philips | 26/06/2026 |
| Python 3.6.4 (64-bit) | 3.6.4150.0 | Python Software Foundation |  |
| Python Launcher | 3.6.6196.0 | Python Software Foundation | 07/03/2023 |
| stunnel installed for AllUsers | 5.56 | Michal Trojnara |  |
| TeamViewer | 15.81.5 | TeamViewer |  |
| Virtio-win-guest-tools | 0.1.225 | Red Hat, Inc. |  |
| Vue PACS NXLog Server | 1.0.64065 | Philips | 07/03/2023 |
| Zabbix Agent 2 (64-bit) | 7.4.1.2400 | Zabbix SIA | 15/08/2025 |

## Services auto non-Microsoft

| Service | Etat | Compte | Binaire |
|---|---|---|---|
| AnyDesk Service (`AnyDesk`) | Running | LocalSystem | "C:\Program Files (x86)\AnyDesk\AnyDesk.exe" --service |
| AppFabric Event Collection Service (`AppFabricEventCollectionService`) | Running | NT AUTHORITY\LocalService | "C:\Program Files\AppFabric 1.1 for Windows Server\EventCollectorService.exe" |
| AppFabric Workflow Management Service (`AppFabricWorkflowManagementService`) | Running | NT AUTHORITY\LocalService | "C:\Program Files\AppFabric 1.1 for Windows Server\WorkflowManagementService.exe" |
| BalloonService (`BalloonService`) | Running | LocalSystem | "C:\Program Files\Virtio-Win\Balloon\blnsvr.exe" |
| DataGridTransmitter (`DataGridTransmitter`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mv\exe\Algotec.DataGrid.AnalyticsGridTransmitterService.exe service |
| Filebeat (`Filebeat`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Filebeat |
| FLEXlm Service (`FLEXlm Service`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\FLEXlm\lmgrd.exe |
| Google Updater Internal Service (GoogleUpdaterInternalService152.0.7933.0) (`GoogleUpdaterInternalService152.0.7933.0`) | Stopped | LocalSystem | "C:\Program Files (x86)\Google\GoogleUpdater\152.0.7933.0\updater.exe" --system --windows-service --service=update-internal |
| Google Updater Service (GoogleUpdaterService152.0.7933.0) (`GoogleUpdaterService152.0.7933.0`) | Stopped | LocalSystem | "C:\Program Files (x86)\Google\GoogleUpdater\152.0.7933.0\updater.exe" --system --windows-service --service=update |
| Ignite Server Node (`Ignite`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Ignite |
| Imaginet Auto-Router Execution Module (`Imaginet Auto-Router Execution Module`) | Running | .\philipsadm | C:\PROGRA~1\CAREST~1\System5\autorouter\exe\ARExecution.exe AutoRouter.ExecutionModule EXECUTE_BATCH_CONTENT STDIN C:\PROGRA~1\CAREST~1\System5\autorouter\admin\run_ar_engine.bat "AutoRouter.ExecutionModule algotec.autoRouter.engine.ExecutionModule" |
| Imaginet Auto-Router Scheduling Module (`Imaginet Auto-Router Scheduling Module`) | Running | .\philipsadm | C:\PROGRA~1\CAREST~1\System5\autorouter\exe\ARScheduling.exe AutoRouter.SchedulingModule EXECUTE_BATCH_CONTENT STDIN C:\PROGRA~1\CAREST~1\System5\autorouter\admin\run_ar_engine.bat "AutoRouter.SchedulingModule algotec.autoRouter.engine.SchedulingModule" |
| Imaginet Connectivity Monitor (`Imaginet Connectivity Monitor`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mv\exe\ConnectivityMonitorService.exe service |
| Imaginet DataGrid Controller (`Imaginet DataGrid Controller`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Wrapper.exe service Zookeeper Kafka Filebeat Metricbeat Ignite |
| Imaginet DB Audit Server (`Imaginet DB Audit Server`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\infra\exe\db_audit.exe |
| Imaginet Failover Service (`Imaginet Failover Service`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\failover_srvc.exe |
| Imaginet IOCM Probe (`Imaginet IOCM Probe`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\iocm_probe_service.exe |
| Imaginet Loader Server (`Imaginet Loader Server`) | Running | .\philipsadm | C:\PROGRA~1\CAREST~1\System5\loader\exe\LoaderSrv.exe -u -e 36 -s -a dicom_loader |
| Imaginet Medilink Converter (`Imaginet Medilink Converter`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\medilink\exe\MDLConverter.exe converter EXECUTE_BATCH_CONTENT CONTROL_PORT C:\PROGRA~1\CAREST~1\System5\medilink\admin\converter.bat |
| Imaginet Medilink Listener (`Imaginet Medilink Listener`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\medilink\exe\MDLListener.exe listener EXECUTE_BATCH_CONTENT CONTROL_PORT C:\PROGRA~1\CAREST~1\System5\medilink\admin\listener.bat listener |
| Imaginet Medilink Sync Listener (`Imaginet Medilink Sync Listener`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\medilink\exe\SYNC_Listener.exe |
| Imaginet MVSMain Secured Server (`Imaginet MVSMain Secured Server`) | Running | .\philipsadm | C:\PROGRA~1\CAREST~1\System5\mv\exe\MVSMAIN.exe /SECURED |
| Imaginet MVSMain Server (`Imaginet MVSMain Server`) | Running | .\philipsadm | C:\PROGRA~1\CAREST~1\System5\mv\exe\MVSMAIN.exe |
| Imaginet PACS Restarter Service (`Imaginet PACS Restarter Service`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mv\exe\RestarterService.exe pacs |
| Imaginet RisSync Server (`Imaginet RisSync Server`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\ris_sync_service.exe |
| Imaginet Startup-Shutdown (`Imaginet Startup-Shutdown`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\SrvS.exe |
| Imaginet System Check (`Imaginet System Check`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\utils\srvany.exe |
| Imaginet Task Dispatcher (`Imaginet Task Dispatcher`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\TaskHandler\exe\TaskManagerDispatcher.exe |
| Imaginet Task Scanner (`Imaginet Task Scanner`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\TaskHandler\exe\TaskManagerScanner.exe |
| Imaginet WCF (`Imaginet WCF`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\XDSb\Registry\XDSRegistry.exe |
| Imaginet WFM Scheduled Queries Dispatcher (`Imaginet WFM Scheduled Queries Dispatcher`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\Algotec.MST.WfmScheduledQueries.Dispatcher.WindowsService.exe |
| Kafka (`Kafka`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Kafka |
| Kafka Http Proxy (`Kafka Http Proxy`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mv\exe\KafkaProxy.exe kafka_http_proxy EXECUTE_BATCH_CONTENT KILL C:\PROGRA~1\CAREST~1\System5\infra\admin\kafka_proxy.bat |
| Metricbeat (`Metricbeat`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Metricbeat |
| Mirth3.5.2 (`Mirth3.5.2`) | Running | LocalSystem | C:\PROGRA~1\MIRTHC~1\mcservice.exe |
| Imaginet MST Normalizer (`MSTNormalizer`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\mst\exe\MSTNormalizer.exe |
| OctopusDeploy Tentacle (`OctopusDeploy Tentacle`) | Running | LocalSystem | "C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe" run --instance="Tentacle" |
| OracleOraDB19Home1TNSListener (`OracleOraDB19Home1TNSListener`) | Running | LocalSystem | C:\oracle\product\19\db\BIN\TNSLSNR |
| OracleServicemst1 (`OracleServicemst1`) | Running | LocalSystem | c:\oracle\product\19\db\bin\ORACLE.EXE mst1 |
| Philips Memo ProductExporterWrapper Service (`PhilipsMemoProductExporterWrapperService`) | Running | LocalSystem | "C:\Program Files\philips-memo\ProductExporterWrapper\Philips.Memo.productexporterwrappersvc.exe" |
| Philips Memo Prometheus Service (`PhilipsMemoPrometheusService`) | Running | LocalSystem | "C:\Program Files\philips-memo\Prometheus\prometheussvc.exe" |
| Philips Memo Product Exporter Service (`ProductExporterService`) | Running | LocalSystem | "C:\Program Files\philips-memo\ProductExporter\Philips.MEMO.ProductExporter.exe" |
| QEMU Guest Agent (`QEMU-GA`) | Running | LocalSystem | "C:\Program Files\Qemu-ga\qemu-ga.exe" -d --retry-path |
| TeamViewer (`TeamViewer`) | Running | LocalSystem | "C:\Program Files\TeamViewer\TeamViewer_Service.exe" |
| Philips Telemedicine priors engine (`TlmPriorsSce`) | Running | LocalSystem | "C:\Carestream\Interfaces\TlmPriorsSce\TlmPriorsService.exe" |
| Carestream Telemedicine Remote Engine (`TlmRemoteSce`) | Running | LocalSystem | "c:\Carestream\Interfaces\TlmRemoteSce\TlmRemoteSce.exe" |
| Apache Tomcat (`Tomcat7`) | Running | LocalSystem | C:\PROGRA~1\APACHE~1\TOMCAT~1.0\bin\Tomcat7.exe //RS//Tomcat7 |
| Philips Memo Windows Exporter Service (`windows_exporter`) | Running | LocalSystem | "C:\Program Files\philips-memo\WindowsExporter\Philips.Memo.WindowsExporter.exe" --config.file="C:\Program Files\philips-memo\WindowsExporter\config\windows_exporter_config.yml" --web.config.file="C:\Program Files\philips-memo\WindowsExporter\config\tls_config_file\web-config.yml" --log.format=logfmt --log.file="C:\Program Files\philips-memo\WindowsExporter\windows_exporter_log.txt" |
| Zabbix Agent 2 (`Zabbix Agent 2`) | Stopped | LocalSystem | "C:\Program Files\Zabbix Agent 2\zabbix_agent2.exe" -c "C:\Program Files\Zabbix Agent 2\zabbix_agent2.conf" -f=false |
| Zookeeper (`Zookeeper`) | Running | LocalSystem | C:\PROGRA~1\CAREST~1\System5\bin\Algotec.DataGrid.Service.Controller.exe Zookeeper |

## Ports en ecoute

| Proto | Port | Adresse(s) | Processus |
|---|---|---|---|
| TCP | 80 | :: | System |
| TCP | 135 | ::, 0.0.0.0 | svchost (RpcEptMapper, RpcSs) |
| TCP | 139 | 192.168.101.52, 192.168.171.1 | System |
| TCP | 443 | :: | System |
| TCP | 445 | :: | System |
| TCP | 514 | 0.0.0.0 | nxlog (nxlog) |
| TCP | 1325 | :: | System |
| TCP | 1521 | 127.0.0.1, 192.168.101.52 | tnslsnr (OracleOraDB19Home1TNSListener) |
| TCP | 2001 | 0.0.0.0 | LoaderSrv (Imaginet Loader Server) |
| TCP | 2104 | 0.0.0.0 | MVSMAIN (Imaginet MVSMain Server) |
| TCP | 2105 | 0.0.0.0 | LoaderSrv (Imaginet Loader Server) |
| TCP | 2112 | :: | java |
| TCP | 2181 | :: | java |
| TCP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| TCP | 5357 | :: | System |
| TCP | 5939 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 5985 | :: | System |
| TCP | 6868 | :: | System |
| TCP | 7070 | ::, 0.0.0.0 | AnyDesk (AnyDesk) |
| TCP | 7789 | :: | lmgrd |
| TCP | 8009 | ::1, 127.0.0.1 | Tomcat7 (Tomcat7) |
| TCP | 8080 | :: | Tomcat7 (Tomcat7) |
| TCP | 8082 | :: | java |
| TCP | 8888 | :: | System |
| TCP | 9090 | :: | Philips.Memo.Prometheus |
| TCP | 9092 | :: | java |
| TCP | 9182 | :: | Philips.Memo.WindowsExporter (windows_exporter) |
| TCP | 9925 | :: | System |
| TCP | 9927 | 127.0.0.1 | Philips.Memo.ProductExporterWrapper |
| TCP | 10010 | :: | java |
| TCP | 11110 | :: | Apache.Ignite |
| TCP | 11211 | :: | Apache.Ignite |
| TCP | 13241 | :: | System |
| TCP | 14415 | :: | java |
| TCP | 14416 | :: | java |
| TCP | 17600 | :: | java |
| TCP | 17601 | :: | java |
| TCP | 22104 | 0.0.0.0 | MVSMAIN (Imaginet MVSMain Secured Server) |
| TCP | 35840 | ::, 0.0.0.0 | wininit |
| TCP | 35841 | ::, 0.0.0.0 | svchost (EventLog) |
| TCP | 35842 | ::, 0.0.0.0 | svchost (Schedule) |
| TCP | 35843 | ::, 0.0.0.0 | svchost (SessionEnv) |
| TCP | 35846 | ::, 0.0.0.0 | svchost (PolicyAgent) |
| TCP | 35895 | ::, 0.0.0.0 | lsass (KeyIso, SamSs) |
| TCP | 36929 | ::, 0.0.0.0 | services |
| TCP | 37014 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 37114 | 127.0.0.1 | TeamViewer_Service (TeamViewer) |
| TCP | 42542 | ::1 | tnslsnr (OracleOraDB19Home1TNSListener) |
| TCP | 42572 | :: | oracle (OracleServicemst1) |
| TCP | 42619 | :: | java |
| TCP | 42649 | :: | java |
| TCP | 42651 | :: | algotec |
| TCP | 47001 | :: | System |
| TCP | 47100 | :: | Apache.Ignite |
| UDP | 123 | ::, 0.0.0.0 | svchost (W32Time) |
| UDP | 137 | 192.168.101.52, 192.168.171.1 | System |
| UDP | 138 | 192.168.101.52, 192.168.171.1 | System |
| UDP | 500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 3389 | ::, 0.0.0.0 | svchost (TermService) |
| UDP | 3702 | ::, 0.0.0.0 | svchost (FDResPub) |
| UDP | 4500 | ::, 0.0.0.0 | svchost (IKEEXT) |
| UDP | 5353 | 0.0.0.0 | chrome |
| UDP | 5353 | ::1, 192.168.101.52, 192.168.171.1 | TeamViewer_Service (TeamViewer) |
| UDP | 5355 | 0.0.0.0 | svchost (Dnscache) |

## Partages SMB

| Partage | Chemin | Description |
|---|---|---|
| Devices | C:\NDF\Devices |  |
| temp | C:\temp |  |

## Taches planifiees hors Microsoft

Aucune.

## Correctifs recents

| KB | Type | Installe le |
|---|---|---|
| KB5050110 | Security Update | 18/03/2025 |
| KB5022840 | Security Update | 18/03/2025 |
| KB5022511 | Update | 18/03/2025 |
| KB4486153 | Update | 07/03/2023 |
| KB4589208 | Update | 03/03/2023 |
| KB5020374 | Security Update | 27/02/2023 |
| KB5012170 | Security Update | 27/02/2023 |
| KB4512577 | Security Update | 07/09/2019 |
