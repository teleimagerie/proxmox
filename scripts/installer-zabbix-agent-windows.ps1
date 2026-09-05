#Requires -Version 5.1
<#
Installation et raccordement d'un agent Zabbix 2 sur un serveur Windows, en
mode ACTIF, tel qu'applique aux trois serveurs RIS VENUS (192.168.111.63/.64/
.65) le 05/09/2026 - rejouable tel quel (idempotent).

Usage (PowerShell ADMINISTRATEUR, sur le serveur ; ou par SSH :
scp + powershell -ExecutionPolicy Bypass -NoProfile -File) :

  powershell -ExecutionPolicy Bypass -NoProfile -File .\installer-zabbix-agent-windows.ps1

  -ServeurZabbix : adresse du serveur Zabbix, defaut 10.40.0.60 (le CT 204).
                   On vise l'ADRESSE PRIVEE et non le nom zabbix.teleimagerie.net :
                   depuis TELLIS le nom resout en public (VIP .122) et le trafic
                   ressortirait par Internet, alors que 10.40.0.60 reste dans le
                   tunnel wg2 - verifie le 05/09/2026, les trois VENUS joignent
                   10.40.0.60:10051 en sortie.
  -NomHote       : valeur de Hostname= dans la conf. Defaut : le nom NetBIOS de
                   la machine. DOIT etre exactement le nom de l'hote cote Zabbix,
                   sinon l'agent actif n'est pas reconnu et reste muet.
  -Msi           : chemin du paquet ; par defaut cherche
                   zabbix_agent2-7.0.30-windows-amd64-openssl.msi a cote du script.
                   Version 7.0.30 = celle du serveur (LTS).
  -ForcerConfigExistante : si un agent Zabbix etait DEJA installe avant ce script,
                   il s'arrete apres un diagnostic sans rien modifier (la conf
                   peut appartenir a l'editeur ou au prestataire). Ce commutateur
                   applique quand meme les etapes 2 a 5.

Ce que fait ce script, dans l'ordre :
 0. releve : machine, OS, compte, passerelle, etat des trois profils pare-feu ;
 1. installe l'agent 2 si absent - la signature Authenticode du MSI est
    verifiee (" Zabbix SIA ") AVANT msiexec, et l'installation est refusee si
    elle ne l'est pas ;
 2. ecrit Server / ServerActive / Hostname dans zabbix_agent2.conf (ASCII sans
    BOM), en conservant l'original en .orig ;
 3. pose la regle pare-feu 'zabbix-agent' (TCP 10050 depuis le serveur Zabbix),
    sur le modele de scripts/parefeu-pacs03.ps1. En mode actif elle n'est pas
    necessaire - on la pose quand meme : elle ne coute rien, survit a un
    rallumage du pare-feu et autorise un zabbix_get de diagnostic ;
 4. arme la recuperation automatique du service, comme sur pacs03 et TSplus :
    sc.exe failure reset= 86400 actions= restart/60000 x3 ;
 5. demarre, verifie, et rappelle ou regarder cote serveur.

Pieges evites, ne pas " simplifier " :
 - Set-Content -Encoding UTF8 de PowerShell 5.1 ecrit un BOM ; l'agent lit sa
   conf ligne a ligne et la premiere directive serait ignoree -> ASCII ;
 - les directives sont REMPLACEES (y compris commentees) puis reecrites une
   seule fois : le fichier livre contient deja Server= et ServerActive=
   commentes, les laisser en double prete a confusion ;
 - Hostname doit correspondre au nom de l'hote Zabbix, pas au FQDN ;
 - compatible ConstrainedLanguage : cmdlets et operateurs seulement, pas
   d'appel .NET.

Retour arriere : voir le message de fin.
#>
param(
    [string]$ServeurZabbix = '10.40.0.60',
    [string]$NomHote = $env:COMPUTERNAME,
    [string]$Msi = '',
    [switch]$ForcerConfigExistante
)
$ErrorActionPreference = 'Stop'

# --- 0. releve --------------------------------------------------------------
'=== 0. Releve ==='
if (-not ((whoami /groups) -match 'S-1-16-12288')) {
    throw 'Lancer ce script dans un PowerShell administrateur (eleve).'
}
$os = Get-CimInstance Win32_OperatingSystem
'machine    : {0}' -f $env:COMPUTERNAME
'OS         : {0} (build {1})' -f $os.Caption, $os.BuildNumber
'compte     : {0}' -f (whoami)
'nom Zabbix : {0}' -f $NomHote
'serveur    : {0}' -f $ServeurZabbix
$gw = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
      Sort-Object RouteMetric | Select-Object -First 1
if ($gw) { 'passerelle : {0} (via {1})' -f $gw.NextHop, $gw.InterfaceAlias }
$profils = Get-NetFirewallProfile
foreach ($p in $profils) {
    $etat = if ($p.Enabled) { 'actif' } else { 'DESACTIVE' }
    'pare-feu {0,-8} : {1}' -f $p.Name, $etat
}
$sortie = Test-NetConnection -ComputerName $ServeurZabbix -Port 10051 -WarningAction SilentlyContinue
'sortie vers {0}:10051 : {1}' -f $ServeurZabbix, $sortie.TcpTestSucceeded
if (-not $sortie.TcpTestSucceeded) {
    'ATTENTION : le serveur Zabbix est injoignable en sortie - un agent ACTIF ne pourra rien envoyer.'
}

# --- 1. installation --------------------------------------------------------
'=== 1. Installation ==='
$preexistant = $false
$svc = Get-Service -Name 'Zabbix Agent*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($svc) {
    $preexistant = $true
    'agent DEJA PRESENT avant ce script : {0} ({1})' -f $svc.Name, $svc.Status
} else {
    if (-not $Msi) {
        $base = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
        $Msi = Join-Path $base 'zabbix_agent2-7.0.30-windows-amd64-openssl.msi'
    }
    if (-not (Test-Path $Msi)) {
        throw ('MSI introuvable ({0}) : deposer zabbix_agent2-7.0.30-windows-amd64-openssl.msi ' +
               'a cote du script (cdn.zabbix.com) ou passer -Msi, puis relancer.') -f $Msi
    }
    $sig = Get-AuthenticodeSignature $Msi
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Zabbix SIA') {
        throw ('Signature du MSI invalide ou inattendue ({0} / {1}) : NE PAS installer.' -f $sig.Status, $sig.SignerCertificate.Subject)
    }
    'MSI signe : {0}' -f $sig.SignerCertificate.Subject
    # HOSTNAME/SERVER/SERVERACTIVE sont passes a msiexec, mais la conf est
    # reecrite a l'etape 2 : c'est elle qui fait foi et qui est rejouable.
    $args = '/i "{0}" /qn /norestart SERVER="{1}" SERVERACTIVE="{1}" HOSTNAME="{2}" ENABLEPATH=1' -f $Msi, $ServeurZabbix, $NomHote
    $proc = Start-Process msiexec.exe -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
        throw ('msiexec a rendu le code {0} (1625 = interdit par la strategie systeme / WDAC)' -f $proc.ExitCode)
    }
    'MSI installe (code {0})' -f $proc.ExitCode
    $svc = Get-Service -Name 'Zabbix Agent*' | Select-Object -First 1
}

$svcCim = Get-CimInstance Win32_Service -Filter ("Name='{0}'" -f $svc.Name)
$exe = ($svcCim.PathName -split '" ')[0].Trim('"')
$conf = Join-Path (Split-Path $exe -Parent) 'zabbix_agent2.conf'
# le chemin de la conf est aussi lisible dans la ligne de service (-c "..."),
# via l'operateur -match plutot qu'un appel .NET (ConstrainedLanguage)
if (-not (Test-Path $conf)) {
    if ($svcCim.PathName -match '-c\s+"([^"]+)"') { $conf = $matches[1] }
}
'binaire    : {0} (version {1})' -f $exe, (Get-Item $exe).VersionInfo.ProductVersion
'conf       : {0}' -f $conf

if ($preexistant -and -not $ForcerConfigExistante) {
    'DIAGNOSTIC (rien n''est modifie) - agent installe avant ce script :'
    '   service   : {0}, demarrage {1}, compte {2}' -f $svcCim.State, $svcCim.StartMode, $svcCim.StartName
    if (Test-Path $conf) {
        '   directives actives :'
        Get-Content $conf | Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' } | ForEach-Object { '      ' + $_ }
    }
    Write-Warning 'agent preexistant : configuration, pare-feu et service NON modifies.'
    Write-Warning 'Relire le diagnostic, puis relancer avec -ForcerConfigExistante si les etapes 2 a 5 sont voulues.'
    exit 2
}

# --- 2. configuration -------------------------------------------------------
'=== 2. Configuration ==='
if (-not (Test-Path $conf)) { throw ('conf introuvable : {0}' -f $conf) }
$orig = $conf + '.orig'
if (-not (Test-Path $orig)) { Copy-Item $conf $orig }
$directives = @(
    '# Raccordement TIM (scripts/installer-zabbix-agent-windows.ps1) - agent ACTIF'
    ('Server={0}' -f $ServeurZabbix)
    ('ServerActive={0}' -f $ServeurZabbix)
    ('Hostname={0}' -f $NomHote)
    ''
)
$motifs = '^\s*#?\s*(Server|ServerActive|Hostname|HostnameItem)\s*='
$reste = @(Get-Content $conf | Where-Object { ($_ -notmatch $motifs) -and ($_ -notmatch '^# Raccordement TIM') })
Set-Content -Path $conf -Value ($directives + $reste) -Encoding Ascii
'directives posees : Server / ServerActive / Hostname (original dans {0})' -f $orig

# --- 3. pare-feu ------------------------------------------------------------
'=== 3. Pare-feu ==='
Remove-NetFirewallRule -Name 'zabbix-agent' -ErrorAction SilentlyContinue
New-NetFirewallRule -Name 'zabbix-agent' -DisplayName 'Zabbix agent depuis serveur zabbix' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 10050 -RemoteAddress $ServeurZabbix | Out-Null
'regle posee : zabbix-agent, TCP 10050 depuis {0}' -f $ServeurZabbix
if (-not ($profils | Where-Object Enabled)) {
    '(pare-feu desactive sur tous les profils : la regle est inerte, mais survivra a un rallumage)'
}

# --- 4. recuperation automatique du service ---------------------------------
'=== 4. Recuperation du service ==='
& sc.exe failure $svc.Name reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null
'recuperation armee : 3 redemarrages a 60 s, compteur remis a zero apres 24 h'

# --- 5. demarrage et controle -----------------------------------------------
'=== 5. Demarrage ==='
Set-Service $svc.Name -StartupType Automatic
Restart-Service $svc.Name
Start-Sleep -Seconds 3
$svc = Get-Service $svc.Name
'service : {0}, demarrage {1}' -f $svc.Status, $svc.StartType
$log = Join-Path $env:ProgramFiles 'Zabbix Agent 2\zabbix_agent2.log'
if (Test-Path $log) {
    'dernieres lignes du journal :'
    Get-Content $log -Tail 6 | ForEach-Object { '   ' + $_ }
}

'=== Resume ==='
'agent    : {0} (version {1})' -f $svc.Name, (Get-Item $exe).VersionInfo.ProductVersion
'mode     : ACTIF vers {0}:10051 - aucun port entrant necessaire' -f $ServeurZabbix
'nom      : {0} (doit correspondre EXACTEMENT a l''hote cote Zabbix)' -f $NomHote
''
'Cote serveur Zabbix, l''hote doit recevoir des donnees en quelques minutes.'
'Retour arriere : Stop-Service "{0}" ; msiexec /x <MSI> /qn ;' -f $svc.Name
'  Remove-NetFirewallRule -Name zabbix-agent ; Copy-Item "{0}" "{1}"' -f $orig, $conf
