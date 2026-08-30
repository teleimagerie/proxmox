#Requires -Version 5.1
<#
Verrouillage pare-feu de pacs03, tel qu'applique le 30/08/2026 — rejouable
tel quel apres reinstallation (PowerShell administrateur, ou par SSH :
scp + powershell -ExecutionPolicy Bypass -File).

Ce que fait ce script, dans l'ordre :
 1. pose la liste blanche des flux de production (6 regles, voir la fiche
    15-pacs-secours.md section "Acces SSH et pare-feu") ;
 2. desactive TOUTES les regles entrantes actives a portee "Any" qui
    court-circuiteraient le blocage par defaut (regles heritees : Bureau a
    distance, partage de fichiers, RPC, regles applicatives Any/Any...),
    en preservant les CoreNet-* — l'IP publique est en DHCP OVH, couper
    CoreNet-DHCP-In tuerait le renouvellement du bail ;
 3. allume les trois profils en blocage entrant par defaut, journal des
    rejets actif (%systemroot%\system32\LogFiles\Firewall\pfirewall.log).

Prerequis pour ne pas se verrouiller dehors : arriver par le VPN nomade
(source 10.90.0.x) en SSH ou RDP — ces deux chemins sont dans la liste
blanche. Retour arriere : Set-NetFirewallProfile -All -Enabled False
#>
$ErrorActionPreference = 'Stop'

# --- 1. liste blanche -------------------------------------------------------
$regles = @(
    @{ Name = 'ssh-in'; Display = 'SSH depuis VPN nomade'
       Params = @{ Protocol = 'TCP'; LocalPort = 22; RemoteAddress = '10.90.0.0/24' } }
    @{ Name = 'rdp-vpn'; Display = 'RDP depuis VPN nomade'
       Params = @{ Protocol = 'TCP'; LocalPort = 3389; RemoteAddress = '10.90.0.0/24' } }
    @{ Name = 'pacs-http-proxy'; Display = 'HTTP backend depuis proxy-tim'
       Params = @{ Protocol = 'TCP'; LocalPort = 80; RemoteAddress = '10.40.0.10' } }
    @{ Name = 'zabbix-agent'; Display = 'Zabbix agent depuis serveur zabbix'
       Params = @{ Protocol = 'TCP'; LocalPort = 10050; RemoteAddress = '10.40.0.0/24', '57.130.34.122' } }
    @{ Name = 'tunnel-tellis'; Display = 'Tout flux entrant via tunnel TELLIS'
       Params = @{ InterfaceAlias = 'DC-TELLIS-PARTENAIRES' } }
    @{ Name = 'wg-endpoint'; Display = 'WireGuard depuis pfSense TELLIS'
       Params = @{ Protocol = 'UDP'; LocalPort = 51736; RemoteAddress = '37.61.243.246' } }
    @{ Name = 'icmp-prive'; Display = 'ICMPv4 depuis reseaux prives'
       Params = @{ Protocol = 'ICMPv4'; RemoteAddress = '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16' } }
)
foreach ($r in $regles) {
    Remove-NetFirewallRule -Name $r.Name -ErrorAction SilentlyContinue
    $p = $r.Params
    New-NetFirewallRule -Name $r.Name -DisplayName $r.Display -Direction Inbound -Action Allow @p | Out-Null
    'regle posee : {0}' -f $r.Name
}

# --- 2. purge des regles heritees a portee Any ------------------------------
# tunnel-tellis est remote=Any mais liee a l'interface du tunnel : on la garde.
$gardees = 'tunnel-tellis'
$aDesactiver = Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow |
    Where-Object { $_.Name -notlike 'CoreNet-*' -and $_.Name -notin $gardees } |
    Where-Object { (($_ | Get-NetFirewallAddressFilter).RemoteAddress -join ',') -eq 'Any' }
'{0} regles heritees a desactiver' -f @($aDesactiver).Count
$aDesactiver | Disable-NetFirewallRule

# --- 3. allumage ------------------------------------------------------------
Set-NetFirewallProfile -All -DefaultInboundAction Block -DefaultOutboundAction Allow `
    -LogBlocked True -LogMaxSizeKilobytes 16384
Set-NetFirewallProfile -All -Enabled True

'--- profils :'
Get-NetFirewallProfile | ForEach-Object { '{0} enabled={1} inbound={2}' -f $_.Name, $_.Enabled, $_.DefaultInboundAction }
'--- regles entrantes actives restantes :'
Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow | ForEach-Object {
    $pf = $_ | Get-NetFirewallPortFilter
    $af = $_ | Get-NetFirewallAddressFilter
    '  {0} | {1}/{2} | remote={3}' -f $_.Name, $pf.Protocol, ($pf.LocalPort -join ','), ($af.RemoteAddress -join ',')
}
