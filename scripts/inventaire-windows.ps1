#Requires -Version 5.1
<#
Releve complet d'un serveur Windows (materiel + logiciel) en Markdown,
pret a fusionner dans une fiche du depot (modele : 15-pacs-secours.md).

A copier sur le serveur (presse-papier RDP, ou scp la ou OpenSSH est en
place), puis en PowerShell ADMINISTRATEUR :

    powershell -ExecutionPolicy Bypass -File .\inventaire-windows.ps1

Produit inventaire-<hostname>-<date>.md dans le dossier courant (ou -OutDir).

Par SSH (OpenSSH Windows, shell cmd.exe), depuis le poste d'admin, sans rien
laisser sur la machine :

    scp scripts/inventaire-windows.ps1 <user>@<ip>:inventaire-windows.ps1
    ssh <user>@<ip> "powershell -ExecutionPolicy Bypass -NoProfile -File inventaire-windows.ps1"
    scp "<user>@<ip>:inventaire-*.md" configs/
    ssh <user>@<ip> "del inventaire-windows.ps1 inventaire-*.md"

Fonctionne sans module externe (PowerShell 5.1 natif de Windows Server).
Chaque section est isolee : une classe WMI absente ou un droit manquant
n'empeche pas le reste du releve.

Pieges connus, expliques ici pour ne pas etre "simplifies" plus tard :
- surtout pas Win32_Product pour les logiciels : chaque requete declenche
  une reconfiguration msiexec de TOUS les paquets MSI (lent, et peut
  modifier l'etat du serveur). On lit le registre Uninstall (x64 + x86).
- wmic est deprecie (retire des builds recents) : tout passe par
  Get-CimInstance.
- les serveurs sous Device Guard / WDAC (syngo.via de Siemens, par exemple)
  executent PowerShell en mode ConstrainedLanguage : pas de ::new() ni de
  types .NET hors du noyau (List[string], WindowsPrincipal, SecurityIdentifier).
  D'ou le tableau PowerShell, le repli sur whoami pour le test admin, le
  groupe Administrateurs cherche par SID en comparaison de chaines, et les
  arrondis par cast [int] (meme regle bancaire que [math]::Round, refuse dans
  ce mode).
#>
param(
    # Dossier de sortie du .md (defaut : dossier courant)
    [string]$OutDir = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
$md = @()

function Ajoute { param([string]$Ligne) $script:md += $Ligne }

# Une cellule de tableau Markdown ne doit contenir ni pipe ni retour ligne
function Esc {
    param($Valeur)
    (("$Valeur" -replace '\|', '\|') -replace "[`r`n]+", ' ').Trim()
}

function Go { param($Octets) ([int]($Octets / 1GB * 10)) / 10 }

function Section {
    param([string]$Titre, [scriptblock]$Bloc)
    Write-Host "  $Titre"
    Ajoute ''
    Ajoute "## $Titre"
    Ajoute ''
    try { & $Bloc }
    catch { Ajoute "_Section indisponible : $(Esc $_.Exception.Message)_" }
}

try {
    $estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
                ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {
    # ConstrainedLanguage : le jeton eleve porte le niveau d'integrite High
    $estAdmin = [bool]((whoami /groups) -match 'S-1-16-12288')
}

$hostname = $env:COMPUTERNAME.ToLower()
Write-Host "Inventaire de $hostname..."

Ajoute "# Inventaire $hostname - $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
Ajoute ''
Ajoute '_Genere par `scripts/inventaire-windows.ps1`. A fusionner dans la fiche du serveur._'
if (-not $estAdmin) {
    Ajoute ''
    Ajoute '> Releve fait SANS droits administrateur : certaines sections seront incompletes.'
}

Section 'Identite' {
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $ver = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    $release = $ver.DisplayVersion; if (-not $release) { $release = $ver.ReleaseId }
    $uptime = (Get-Date) - $os.LastBootUpTime

    $domaine = if ($cs.PartOfDomain) { "domaine $($cs.Domain)" } else { "workgroup $($cs.Domain)" }
    # Etat d'activation de la licence Windows (ApplicationID = produit Windows)
    $etatLic = '?'
    try {
        $lic = Get-CimInstance SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL" |
            Where-Object { $_.ApplicationID -eq '55c92734-d682-4d71-983e-d6ec3f16059f' } |
            Select-Object -First 1
        if ($lic) {
            $etatLic = if ($lic.LicenseStatus -eq 1) { 'active' } else { "NON active (statut $($lic.LicenseStatus))" }
            $etatLic += " - $($lic.ProductKeyChannel)"
        }
    } catch { }

    Ajoute '| | |'
    Ajoute '|---|---|'
    Ajoute "| Hostname | ``$($cs.DNSHostName)`` ($domaine) |"
    Ajoute "| Modele | $(Esc $cs.Manufacturer) $(Esc $cs.Model) |"
    Ajoute "| OS | $(Esc $os.Caption) $release (build $($os.BuildNumber)) |"
    Ajoute "| Installe le | $($os.InstallDate.ToString('dd/MM/yyyy')) |"
    Ajoute "| Dernier boot | $($os.LastBootUpTime.ToString('dd/MM/yyyy HH:mm')) (uptime $($uptime.Days) j $($uptime.Hours) h) |"
    Ajoute "| Fuseau | $((Get-TimeZone).Id) |"
    Ajoute "| Licence | $etatLic |"
}

Section 'CPU' {
    Ajoute '| Socket | Modele | Coeurs / threads | Frequence |'
    Ajoute '|---|---|---|---|'
    Get-CimInstance Win32_Processor | ForEach-Object {
        $ghz = ([int]($_.MaxClockSpeed / 100)) / 10
        Ajoute "| $($_.SocketDesignation) | $(Esc $_.Name) | $($_.NumberOfCores)c/$($_.NumberOfLogicalProcessors)t | $ghz GHz |"
    }
}

Section 'RAM' {
    $typesRam = @{ 20 = 'DDR'; 21 = 'DDR2'; 24 = 'DDR3'; 26 = 'DDR4'; 27 = 'LPDDR'
                   28 = 'LPDDR2'; 29 = 'LPDDR3'; 30 = 'LPDDR4'; 34 = 'DDR5'; 35 = 'LPDDR5' }
    $ecc = @{ 3 = 'sans ECC'; 4 = 'parite'; 5 = 'ECC single-bit'; 6 = 'ECC multi-bit' }
    $barrettes = @(Get-CimInstance Win32_PhysicalMemory)
    $total = ($barrettes | Measure-Object Capacity -Sum).Sum

    $enTete = "**$(Go $total) Go** en $($barrettes.Count) barrette(s)"
    try {
        $baie = Get-CimInstance Win32_PhysicalMemoryArray | Select-Object -First 1
        $maxGo = if ($baie.MaxCapacityEx) { [int]($baie.MaxCapacityEx / 1MB) }
                 else { [int]($baie.MaxCapacity / 1MB) }
        $enTete += " sur $($baie.MemoryDevices) slot(s)"
        # certains firmwares (laptops surtout) annoncent une capacite max
        # fantaisiste : on ne l'affiche que si elle est vraisemblable
        if ($maxGo -ge (Go $total) -and $maxGo -le 65536) { $enTete += ", $maxGo Go max" }
        if ($ecc.ContainsKey([int]$baie.MemoryErrorCorrection)) { $enTete += ", $($ecc[[int]$baie.MemoryErrorCorrection])" }
    } catch { }
    Ajoute $enTete
    Ajoute ''
    Ajoute '| Slot | Capacite | Type | Vitesse | Reference |'
    Ajoute '|---|---|---|---|---|'
    foreach ($b in $barrettes) {
        $type = $typesRam[[int]$b.SMBIOSMemoryType]; if (-not $type) { $type = "type $($b.SMBIOSMemoryType)" }
        $vitesse = if ($b.ConfiguredClockSpeed) { "$($b.ConfiguredClockSpeed) MHz" } else { "$($b.Speed) MHz" }
        Ajoute "| $(Esc $b.DeviceLocator) | $(Go $b.Capacity) Go | $type | $vitesse | $(Esc $b.Manufacturer) $(Esc $b.PartNumber) |"
    }
}

Section 'Carte mere / BIOS' {
    $cm = Get-CimInstance Win32_BaseBoard
    $prod = Get-CimInstance Win32_ComputerSystemProduct
    $bios = Get-CimInstance Win32_BIOS
    Ajoute '| | |'
    Ajoute '|---|---|'
    Ajoute "| Carte mere | $(Esc $cm.Manufacturer) $(Esc $cm.Product) |"
    Ajoute "| Numero de serie | $(Esc $prod.IdentifyingNumber) |"
    $dateBios = if ($bios.ReleaseDate) { " du $($bios.ReleaseDate.ToString('dd/MM/yyyy'))" } else { '' }
    Ajoute "| BIOS | $(Esc $bios.SMBIOSBIOSVersion)$dateBios |"
}

Section 'GPU' {
    # Cartes graphiques : decisif pour le rendu (Syngo Via, RDS/TSplus), vide ailleurs.
    # AdapterRAM est un uint32 : plafonne a 4 Go, on l'annonce comme tel.
    $cartes = @(Get-CimInstance Win32_VideoController)
    Ajoute '| Carte | Pilote | VRAM annoncee |'
    Ajoute '|---|---|---|'
    foreach ($g in $cartes) {
        $vram = if ($g.AdapterRAM) { "$(Go $g.AdapterRAM) Go" } else { '-' }
        $date = if ($g.DriverDate) { " du $($g.DriverDate.ToString('dd/MM/yyyy'))" } else { '' }
        Ajoute "| $(Esc $g.Name) | $(Esc $g.DriverVersion)$date | $vram |"
    }
}

Section 'Disques physiques' {
    Ajoute '| # | Modele | Bus | Type | Taille | Sante |'
    Ajoute '|---|---|---|---|---|---|'
    Get-PhysicalDisk | Sort-Object DeviceId | ForEach-Object {
        Ajoute "| $($_.DeviceId) | $(Esc $_.FriendlyName) | $($_.BusType) | $($_.MediaType) | $(Go $_.Size) Go | $($_.HealthStatus) |"
    }
    # Storage Spaces eventuels (RAID logiciel Windows)
    $pools = @(Get-StoragePool -IsPrimordial $false -ErrorAction SilentlyContinue)
    foreach ($p in $pools) {
        Ajoute ''
        Ajoute "Pool Storage Spaces **$(Esc $p.FriendlyName)** ($(Go $p.Size) Go) :"
        Get-VirtualDisk -StoragePool $p | ForEach-Object {
            Ajoute "- $(Esc $_.FriendlyName) : $($_.ResiliencySettingName), $(Go $_.Size) Go, $($_.HealthStatus)"
        }
    }
}

Section 'Volumes' {
    Ajoute '| Lettre | Label | FS | Taille | Libre |'
    Ajoute '|---|---|---|---|---|'
    Get-Volume | Where-Object { $_.Size -gt 0 } | Sort-Object DriveLetter | ForEach-Object {
        $lettre = if ($_.DriveLetter) { "$($_.DriveLetter):" } else { '-' }
        Ajoute "| $lettre | $(Esc $_.FileSystemLabel) | $($_.FileSystem) | $(Go $_.Size) Go | $(Go $_.SizeRemaining) Go |"
    }
}

Section 'Reseau' {
    Ajoute '| Interface | Description | MAC | Vitesse | Etat |'
    Ajoute '|---|---|---|---|---|'
    Get-NetAdapter | Sort-Object ifIndex | ForEach-Object {
        Ajoute "| $(Esc $_.Name) | $(Esc $_.InterfaceDescription) | ``$($_.MacAddress)`` | $($_.LinkSpeed) | $($_.Status) |"
    }
    Ajoute ''
    Ajoute '| Interface | IPv4 | Passerelle | DNS |'
    Ajoute '|---|---|---|---|'
    Get-NetIPConfiguration | Sort-Object InterfaceIndex | ForEach-Object {
        $ips = ($_.IPv4Address | ForEach-Object { "$($_.IPAddress)/$($_.PrefixLength)" }) -join ', '
        $gw = ($_.IPv4DefaultGateway | ForEach-Object { $_.NextHop }) -join ', '
        $dns = ($_.DNSServer | Where-Object { $_.AddressFamily -eq 2 } |
                ForEach-Object { $_.ServerAddresses }) -join ', '
        Ajoute "| $(Esc $_.InterfaceAlias) | $ips | $gw | $dns |"
    }
}

Section 'Roles et fonctionnalites' {
    if (Get-Command Get-WindowsFeature -ErrorAction SilentlyContinue) {
        # Windows Server : la vraie liste des roles installes
        Get-WindowsFeature | Where-Object { $_.Installed -and $_.FeatureType -eq 'Role' } | ForEach-Object {
            Ajoute "- **$(Esc $_.DisplayName)** (``$($_.Name)``)"
        }
        $fonc = (Get-WindowsFeature | Where-Object { $_.Installed -and $_.FeatureType -ne 'Role' }).Name -join ', '
        Ajoute ''
        Ajoute "Fonctionnalites : $fonc"
    } else {
        # Windows client : pas de Get-WindowsFeature (module ServerManager)
        $act = Get-WindowsOptionalFeature -Online | Where-Object { $_.State -eq 'Enabled' }
        Ajoute "Windows client - fonctionnalites optionnelles actives : $(($act.FeatureName | Sort-Object) -join ', ')"
    }
}

Section 'Logiciels installes' {
    # Registre Uninstall x64 + x86 + par-utilisateur. SystemComponent=1 et
    # ParentKeyName designent des composants et mises a jour, pas des applis.
    $cles = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    $logiciels = Get-ItemProperty $cles -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -and $_.SystemComponent -ne 1 -and -not $_.ParentKeyName } |
        Sort-Object DisplayName -Unique
    Ajoute '| Logiciel | Version | Editeur | Installe le |'
    Ajoute '|---|---|---|---|'
    foreach ($l in $logiciels) {
        $date = $l.InstallDate
        if ($date -match '^(\d{4})(\d{2})(\d{2})$') { $date = "$($Matches[3])/$($Matches[2])/$($Matches[1])" }
        Ajoute "| $(Esc $l.DisplayName) | $(Esc $l.DisplayVersion) | $(Esc $l.Publisher) | $date |"
    }
}

Section 'Services auto non-Microsoft' {
    # Filtre grossier mais efficace : tout ce qui ne tourne pas depuis \Windows\
    $services = Get-CimInstance Win32_Service |
        Where-Object { $_.StartMode -eq 'Auto' -and $_.PathName -notmatch '\\Windows\\' } |
        Sort-Object Name
    Ajoute '| Service | Etat | Compte | Binaire |'
    Ajoute '|---|---|---|---|'
    foreach ($s in $services) {
        Ajoute "| $(Esc $s.DisplayName) (``$($s.Name)``) | $($s.State) | $(Esc $s.StartName) | $(Esc $s.PathName) |"
    }
}

Section 'Ports en ecoute' {
    # PID -> nom(s) de service Windows, pour distinguer les multiples svchost
    $svcParPid = @{}
    Get-CimInstance Win32_Service | Where-Object { $_.ProcessId -gt 0 } | ForEach-Object {
        $svcParPid[[int]$_.ProcessId] = (@($svcParPid[[int]$_.ProcessId], $_.Name) -ne $null) -join ', '
    }
    function NomProcessus {
        param([int]$Pid_)
        $nom = try { (Get-Process -Id $Pid_ -ErrorAction Stop).ProcessName } catch { '?' }
        if ($svcParPid.ContainsKey($Pid_)) { "$nom ($($svcParPid[$Pid_]))" } else { $nom }
    }
    Ajoute '| Proto | Port | Adresse(s) | Processus |'
    Ajoute '|---|---|---|---|'
    Get-NetTCPConnection -State Listen | Group-Object LocalPort, OwningProcess |
        Sort-Object { [int]$_.Group[0].LocalPort } | ForEach-Object {
            $c = $_.Group[0]
            $adr = ($_.Group.LocalAddress | Sort-Object -Unique) -join ', '
            Ajoute "| TCP | $($c.LocalPort) | $adr | $(Esc (NomProcessus $c.OwningProcess)) |"
        }
    # UDP : on saute les ports ephemeres (>= 49152), sans interet en doc
    Get-NetUDPEndpoint | Where-Object { $_.LocalPort -lt 49152 } |
        Group-Object LocalPort, OwningProcess |
        Sort-Object { [int]$_.Group[0].LocalPort } | ForEach-Object {
            $c = $_.Group[0]
            $adr = ($_.Group.LocalAddress | Sort-Object -Unique) -join ', '
            Ajoute "| UDP | $($c.LocalPort) | $adr | $(Esc (NomProcessus $c.OwningProcess)) |"
        }
}

Section 'Partages SMB' {
    $partages = @(Get-SmbShare | Where-Object { -not $_.Special })
    if ($partages) {
        Ajoute '| Partage | Chemin | Description |'
        Ajoute '|---|---|---|'
        foreach ($p in $partages) { Ajoute "| $(Esc $p.Name) | $(Esc $p.Path) | $(Esc $p.Description) |" }
    } else { Ajoute 'Aucun partage non administratif.' }
}

Section 'Taches planifiees hors Microsoft' {
    $taches = @(Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft*' })
    if ($taches) {
        Ajoute '| Tache | Etat | Action |'
        Ajoute '|---|---|---|'
        foreach ($t in $taches) {
            $action = ($t.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join ' ; '
            Ajoute "| $(Esc ($t.TaskPath + $t.TaskName)) | $($t.State) | $(Esc $action) |"
        }
    } else { Ajoute 'Aucune.' }
}

Section 'Correctifs recents' {
    Ajoute '| KB | Type | Installe le |'
    Ajoute '|---|---|---|'
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 15 | ForEach-Object {
        $date = if ($_.InstalledOn) { $_.InstalledOn.ToString('dd/MM/yyyy') } else { '?' }
        Ajoute "| $($_.HotFixID) | $($_.Description) | $date |"
    }
}

Section 'Securite locale' {
    # Etat Defender et profils du pare-feu Windows : un temps reel coupe ou un
    # profil desactive se voit ici, pas dans la liste des services.
    try {
        $mp = Get-MpComputerStatus -ErrorAction Stop
        $tr = if ($mp.RealTimeProtectionEnabled) { 'active' } else { '**DESACTIVEE**' }
        $sig = if ($mp.AntivirusSignatureLastUpdated) { $mp.AntivirusSignatureLastUpdated.ToString('dd/MM/yyyy') } else { '?' }
        Ajoute "Microsoft Defender : service $(if ($mp.AMServiceEnabled) { 'actif' } else { '**inactif**' }), protection temps reel $tr, signatures du $sig, moteur $($mp.AMEngineVersion)"
    } catch { Ajoute "Microsoft Defender : etat illisible ($(Esc $_.Exception.Message))" }
    Ajoute ''
    Ajoute '| Profil pare-feu | Actif | Entrant par defaut | Sortant par defaut |'
    Ajoute '|---|---|---|---|'
    Get-NetFirewallProfile | ForEach-Object {
        $actif = if ($_.Enabled) { 'oui' } else { '**NON**' }
        Ajoute "| $($_.Name) | $actif | $($_.DefaultInboundAction) | $($_.DefaultOutboundAction) |"
    }
}

Section 'Comptes locaux' {
    # Effectifs seulement : la liste nominative (parfois des centaines de vrais
    # utilisateurs) n'a rien a faire dans un depot. Les administrateurs, si.
    $comptes = @(Get-LocalUser)
    $actifs = @($comptes | Where-Object Enabled).Count
    Ajoute "**$($comptes.Count) comptes locaux** : $actifs actifs, $($comptes.Count - $actifs) desactives."
    Ajoute ''
    # SID du groupe Administrateurs plutot que son nom, qui depend de la langue
    $admins = @(Get-LocalGroup | Where-Object { "$($_.SID)" -eq 'S-1-5-32-544' } |
        Get-LocalGroupMember -ErrorAction SilentlyContinue |
        ForEach-Object { "``$(Esc $_.Name)`` ($($_.ObjectClass), $($_.PrincipalSource))" })
    if ($admins) { Ajoute "Membres du groupe Administrateurs : $($admins -join ', ')" }
    else { Ajoute 'Groupe Administrateurs illisible.' }
}

$fichier = Join-Path $OutDir ("inventaire-{0}-{1}.md" -f $hostname, (Get-Date -Format 'yyyy-MM-dd'))
$md | Out-File -FilePath $fichier -Encoding UTF8
Write-Host "OK -> $fichier"
