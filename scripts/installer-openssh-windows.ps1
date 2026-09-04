#Requires -Version 5.1
<#
Installation et verrouillage d'OpenSSH serveur sur un serveur Windows, tel
qu'applique aux trois serveurs RIS VENUS (192.168.111.63/.64/.65) le
04/09/2026 - rejouable tel quel (idempotent) sur toute machine Windows a
administrer par cle depuis le poste.

Usage (PowerShell ADMINISTRATEUR, sur le serveur) :
  powershell -ExecutionPolicy Bypass -NoProfile -File .\installer-openssh-windows.ps1 `
      -ClePublique 'ssh-ed25519 AAAA... commentaire'
  -SourceAutorisee : sources admises sur le port 22 (liste), defaut 172.31.0.3
                     (le poste sur le VPN nomade du pfSense TELLIS, tunnel
                     DC-TELLIS2 : c'est ce que voient les serveurs TELLIS, verifie
                     le 04/09/2026 par netstat sur syngovia1 et tsplus) et
                     10.90.0.0/24 (VPN nomade OPNsense, sans NAT sur wg2)
  -Msi             : chemin du paquet OpenSSH-Win64-v10.0.0.0.msi (repli, voir 1.) ;
                     par defaut cherche a cote du script
  -ForcerConfigExistante : si un sshd etait DEJA installe avant ce script, le
                     script s'arrete apres un diagnostic (chemin, version, port
                     d'ecoute, directives actives, cles deja autorisees) sans
                     rien modifier - un sshd preexistant peut servir a l'editeur
                     ou au prestataire (SFTP d'interfaces, maintenance : c'etait
                     le cas sur TIM-VENUS2-IF le 04/09/2026, OpenSSH 9.8p2 dans
                     C:\OpenSSH-Win64). Relire, puis relancer avec ce commutateur
                     pour appliquer les etapes 2 a 5 en connaissance de cause.

Ce que fait ce script, dans l'ordre :
 0. releve : machine, OS, compte, passerelle par defaut, profils pare-feu
    (valeurs a reporter dans la fiche) ;
 1. installe sshd s'il manque : capacite Windows native OpenSSH.Server
    (Server 2019+, sans transfert de fichier), sinon le MSI Microsoft
    OpenSSH-Win64 (Server 2016, ou erreur 0x800f0954 = pas d'acces a
    Windows Update / WSUS) - le MSI n'est installe que si sa signature
    Authenticode Microsoft est valide ;
 2. demarrage automatique, premier demarrage (cree C:\ProgramData\ssh :
    cles d'hote et sshd_config) ;
 3. depose la cle dans C:\ProgramData\ssh\administrators_authorized_keys
    (ASCII sans BOM) et restreint son ACL aux SID S-1-5-32-544
    (Administrateurs) et S-1-5-18 (SYSTEM) - sans cette ACL sshd ignore le
    fichier EN SILENCE (piege consigne sur pacs03, 30/08/2026). Ce fichier
    vaut pour tout compte membre du groupe Administrateurs ; pour eux
    ~\.ssh\authorized_keys est ignore ;
 4. durcit sshd_config (cle seule : PasswordAuthentication,
    KbdInteractiveAuthentication, ChallengeResponseAuthentication a no,
    MaxAuthTries 3, LoginGraceTime 30 - cf. configs/sshd-10-hardening.conf),
    valide avec `sshd -t` AVANT de redemarrer le service, restaure
    l'original en cas de refus ;
 5. remplace la regle pare-feu posee par l'installation (portee Any) par
    `ssh-in` limitee a la source autorisee (meme forme que
    scripts/parefeu-pacs03.ps1) et desactive toute autre regle entrante
    active sur le port 22. L'ETAT des profils n'est PAS modifie (decision
    exploitant, comme TIMWFMCORE).
Shell par defaut laisse a cmd.exe (comme syngo.via et TSplus), ssh-agent
non touche.

Pieges evites, ne pas " simplifier " :
 - `Set-Content -Encoding UTF8` de PowerShell 5.1 ecrit un BOM : sshd refuse
   alors la premiere directive de sshd_config et ne lit pas la cle -> ASCII ;
 - les directives sont inserees EN TETE de sshd_config, avant tout bloc
   Match (placees apres, elles ne vaudraient que pour ce Match) ; le bloc
   `Match Group administrators` de Microsoft, qui pointe
   administrators_authorized_keys, est conserve tel quel ;
 - compatible WDAC / ConstrainedLanguage : cmdlets et operateurs seulement,
   pas d'appel .NET (Get-Item, Test-Path, whoami, icacls).

Ne pas fermer la session RDP avant d'avoir teste la cle depuis le poste :
  ssh -o BatchMode=yes <compte>@<ip> "hostname && whoami"
Retour arriere : voir le message de fin (Stop-Service, Set-Service Disabled,
Remove-NetFirewallRule ssh-in, sshd_config.orig).
#>
param(
    [Parameter(Mandatory = $true)][string]$ClePublique,
    [string[]]$SourceAutorisee = @('172.31.0.3', '10.90.0.0/24'),
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
$gw = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
      Sort-Object RouteMetric | Select-Object -First 1
if ($gw) { 'passerelle : {0} (via {1})' -f $gw.NextHop, $gw.InterfaceAlias }
else     { 'passerelle : AUCUNE route par defaut' }
$profils = Get-NetFirewallProfile
foreach ($p in $profils) {
    $etat = if ($p.Enabled) { 'actif' } else { 'DESACTIVE' }
    'pare-feu {0,-8} : {1} (entrant par defaut : {2})' -f $p.Name, $etat, $p.DefaultInboundAction
}

# --- 1. installation --------------------------------------------------------
'=== 1. Installation ==='
$preexistant = $false
$svc = Get-Service sshd -ErrorAction SilentlyContinue
if ($svc) {
    $preexistant = $true
    'sshd DEJA PRESENT avant ce script : {0}' -f $svc.Status
} else {
    $installe = $false
    $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if ($cap) {
        'capacite Windows {0} : {1}' -f $cap.Name, $cap.State
        if ($cap.State -eq 'Installed') {
            $installe = $true
        } else {
            try {
                $r = Add-WindowsCapability -Online -Name $cap.Name
                'capacite installee (redemarrage requis : {0})' -f $r.RestartNeeded
                $installe = $true
            } catch {
                'echec de la capacite native : {0}' -f $_.Exception.Message
                '(0x800f0954 = pas d''acces a Windows Update / WSUS : passage par le MSI)'
            }
        }
    } else {
        'capacite OpenSSH.Server absente de cette version de Windows (Server 2016 ?) : passage par le MSI'
    }
    if (-not $installe) {
        if (-not $Msi) {
            $base = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
            $Msi = Join-Path $base 'OpenSSH-Win64-v10.0.0.0.msi'
        }
        if (-not (Test-Path $Msi)) {
            throw ('Ni capacite native ni MSI trouve ({0}) : poser OpenSSH-Win64-v10.0.0.0.msi ' +
                   '(release 10.0.0.0p2-Preview de github.com/PowerShell/Win32-OpenSSH) a cote du script ' +
                   'ou passer -Msi, puis relancer.') -f $Msi
        }
        $sig = Get-AuthenticodeSignature $Msi
        if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Microsoft') {
            throw ('Signature du MSI invalide ({0}) : NE PAS installer.' -f $sig.Status)
        }
        'MSI signe : {0}' -f $sig.SignerCertificate.Subject
        $proc = Start-Process msiexec.exe -ArgumentList ('/i "{0}" /qn /norestart' -f $Msi) -Wait -PassThru
        if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
            throw ('msiexec a rendu le code {0}' -f $proc.ExitCode)
        }
        'MSI installe (code {0})' -f $proc.ExitCode
    }
    $svc = Get-Service sshd
}

# --- 2. service -------------------------------------------------------------
'=== 2. Service ==='
$dossier = Join-Path $env:ProgramData 'ssh'
$conf    = Join-Path $dossier 'sshd_config'
if ($preexistant -and -not $ForcerConfigExistante) {
    $svcCim = Get-CimInstance Win32_Service -Filter "Name='sshd'"
    $exe = $svcCim.PathName.Trim('"')
    'DIAGNOSTIC (rien n''est modifie) - sshd installe avant ce script :'
    '   executable : {0} (version {1}, cree le {2:dd/MM/yyyy})' -f $exe, (Get-Item $exe).VersionInfo.ProductVersion, (Get-Item $exe).CreationTime
    '   service    : {0}, demarrage {1}, compte {2}' -f $svcCim.State, $svcCim.StartMode, $svcCim.StartName
    '   ecoute     : ' + ((netstat -ano | Select-String 'LISTENING' | Where-Object { $_ -match ('\s{0}$' -f $svcCim.ProcessId) } | ForEach-Object { ($_.Line -split '\s+')[2] }) -join ', ')
    if (Test-Path $conf) {
        '   directives actives de {0} :' -f $conf
        Get-Content $conf | Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' } | ForEach-Object { '      ' + $_ }
    }
    $akDiag = Join-Path $dossier 'administrators_authorized_keys'
    if (Test-Path $akDiag) {
        '   cles admin deja autorisees : ' + ((Get-Content $akDiag | Where-Object { $_ -match '\S' } | ForEach-Object { ($_ -split ' ')[0] + ' ' + (($_ -split ' ')[2..9] -join ' ') }) -join ' | ')
    }
    Write-Warning 'sshd preexistant : configuration, cles et pare-feu NON modifies, service NON redemarre.'
    Write-Warning 'Relire le diagnostic ci-dessus, puis relancer avec -ForcerConfigExistante si les etapes 2 a 5 sont voulues.'
    exit 2
}
Set-Service sshd -StartupType Automatic
if ((Get-Service sshd).Status -ne 'Running') { Start-Service sshd }
$n = 0
while (-not (Test-Path $conf) -and $n -lt 30) { Start-Sleep -Seconds 1; $n++ }
if (-not (Test-Path $conf)) { throw ('sshd_config absent apres demarrage : {0}' -f $conf) }
$sshdExe = (Get-CimInstance Win32_Service -Filter "Name='sshd'").PathName.Trim('"')
'sshd : {0} (version {1})' -f $sshdExe, (Get-Item $sshdExe).VersionInfo.ProductVersion

# --- 3. cle administrateur --------------------------------------------------
'=== 3. Cle administrateur ==='
$ak  = Join-Path $dossier 'administrators_authorized_keys'
$cle = $ClePublique.Trim()
if ($cle -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp\d+|sk-[a-z0-9-]+@openssh\.com) [A-Za-z0-9+/=]+') {
    throw 'ClePublique ne ressemble pas a une cle publique OpenSSH (type + base64).'
}
$cleId = ($cle -split ' ')[0..1] -join ' '
$lignes = @()
if (Test-Path $ak) { $lignes = @(Get-Content $ak | Where-Object { $_.Trim() }) }
$deja = $false
foreach ($l in $lignes) {
    $id = ($l.Trim() -split ' ')[0..1] -join ' '
    if ($id -eq $cleId) { $deja = $true }
}
if ($deja) { 'cle deja presente' } else { $lignes += $cle; 'cle ajoutee' }
Set-Content -Path $ak -Value $lignes -Encoding Ascii
& icacls $ak /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
'ACL : {0}' -f ((& icacls $ak | Select-Object -First 1).Trim())

# --- 4. durcissement sshd_config --------------------------------------------
'=== 4. sshd_config ==='
$durcissement = @(
    '# Durcissement TIM (scripts/installer-openssh-windows.ps1) : authentification par cle seule'
    'PasswordAuthentication no'
    'KbdInteractiveAuthentication no'
    'ChallengeResponseAuthentication no'
    'MaxAuthTries 3'
    'LoginGraceTime 30'
    ''
)
$motifs = '^\s*(PasswordAuthentication|KbdInteractiveAuthentication|ChallengeResponseAuthentication|MaxAuthTries|LoginGraceTime)\b'
$orig = $conf + '.orig'
if (-not (Test-Path $orig)) { Copy-Item $conf $orig }
$reste = @(Get-Content $conf | Where-Object { ($_ -notmatch $motifs) -and ($_ -notmatch '^# Durcissement TIM') })
try {
    Set-Content -Path $conf -Value ($durcissement + $reste) -Encoding Ascii
    # sshd -t ecrit ses avertissements (" Deprecated option ... ") sur stderr : sous
    # $ErrorActionPreference = 'Stop', PowerShell 5.1 en ferait une erreur fatale
    # (NativeCommandError) alors que le code de retour est 0 - vu sur VENUS2 le 04/09/2026
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $test = & $sshdExe -t -f $conf 2>&1
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $eap
    if ($rc -ne 0) { throw ('sshd -t refuse la configuration : {0}' -f (($test | ForEach-Object { "$_" }) -join ' ')) }
    foreach ($t in $test) { 'avertissement sshd -t : {0}' -f $t }
} catch {
    Copy-Item $orig $conf -Force
    throw ('{0} - version d''origine restauree depuis {1}, service non redemarre.' -f $_.Exception.Message, $orig)
}
'configuration validee (sshd -t), original conserve dans {0}' -f $orig
Restart-Service sshd
'sshd redemarre : {0}' -f (Get-Service sshd).Status

# --- 5. pare-feu ------------------------------------------------------------
'=== 5. Pare-feu ==='
Remove-NetFirewallRule -Name 'ssh-in' -ErrorAction SilentlyContinue
New-NetFirewallRule -Name 'ssh-in' -DisplayName 'SSH depuis le poste admin (VPN nomades)' -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort 22 -RemoteAddress $SourceAutorisee | Out-Null
'regle posee : ssh-in, TCP 22 depuis {0}' -f ($SourceAutorisee -join ', ')
# toute autre regle entrante active sur le port 22 (OpenSSH-Server-In-TCP posee par
# l'installation, portee Any) court-circuiterait la restriction : desactivee, pas supprimee
$autres = Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq 22 -or $_.LocalPort -eq '22' } |
          Get-NetFirewallRule | Where-Object { $_.Direction -eq 'Inbound' -and $_.Enabled -eq 'True' -and $_.Name -ne 'ssh-in' }
foreach ($r in $autres) {
    Disable-NetFirewallRule -Name $r.Name
    'regle desactivee : {0} ({1})' -f $r.Name, $r.DisplayName
}
if (-not ($profils | Where-Object Enabled)) {
    'ATTENTION : le pare-feu Windows est desactive sur tous les profils - la regle est posee mais sans effet, le filtrage repose sur le pfSense.'
}

# --- resume -----------------------------------------------------------------
'=== Resume ==='
'OpenSSH  : {0}' -f (Get-Item $sshdExe).VersionInfo.ProductVersion
'service  : {0}, demarrage {1}' -f (Get-Service sshd).Status, (Get-Service sshd).StartType
'ecoute   : {0}' -f ((netstat -an | Select-String 'LISTENING' | Select-String ':22 ' | ForEach-Object { $_.Line.Trim() }) -join ' | ')
''
'Tester MAINTENANT depuis le poste, avant de fermer cette session :'
'  ssh -o BatchMode=yes {0}@<ip> "hostname && whoami"' -f $env:USERNAME
'  ssh -o BatchMode=yes -o PubkeyAuthentication=no {0}@<ip> true   # attendu : Permission denied (publickey)' -f $env:USERNAME
'Retour arriere : Stop-Service sshd ; Set-Service sshd -StartupType Disabled ;'
'  Remove-NetFirewallRule -Name ssh-in ; Copy-Item {0} {1}' -f $orig, $conf
