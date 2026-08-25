# PACS de secours (pacs03) — fiche du serveur bare-metal

Serveur dédié OVH hors cluster Proxmox, hébergeant le backend de
`pacs-secours.teleimagerie.net` — le service principal du reverse proxy
(~25 000 requêtes/semaine, [09-proxy-tim.md](09-proxy-tim.md)). Rattaché au
vRack `pn-1165892` le 25/08/2026 et doté d'une IP privée sur le VLAN 400 :
depuis cette date, le flux proxy→backend ne transite plus en HTTP clair sur
l'Internet public.

> ✅ vérifié/mesuré · 📋 déclaré · ⚠️ à vérifier / à faire

---

## Fiche d'identité

| | |
|---|---|
| Nom DNS public | `pacs03.teleimagerie.net` → `188.165.77.137` ([14-noms-de-domaine.md](14-noms-de-domaine.md)) |
| Hostname | `ns3062628` ✅ (PTR : `ns3062628.ip-188-165-77.eu`) |
| Serveur OVH | ID `1693386`, datacentre **GRA3**, baie `GRA0328A03B` 📋 |
| Matériel | Xeon-E 2386G (6c/12t, 3,5/4,7 GHz), 32 Go ECC 3200 MHz 📋 |
| Disques | 2×512 Go SSD NVMe + 2×6 To HDD SATA, soft RAID 📋 |
| OS | Windows Server 2022 Standard 21H2 ✅ |
| Statut | HDS 📋 |
| Rôle | backend HTTP de `pacs-secours.teleimagerie.net` ✅ ; réplication depuis TELLIS par tunnel WireGuard direct ✅ |

Le cluster est en **GRA4**, ce serveur en **GRA3** : le vRack s'étend entre les
deux datacentres et la latence mesurée est sub-milliseconde (voir
[Mesures](#mesures-du-25082026)) — sans conséquence pour un flux HTTP, mais à
garder en tête si un jour un flux synchrone type Ceph était envisagé.

---

## Réseau

Trois chemins distincts, chacun avec son rôle :

| Interface | Adresse | Rôle |
|---|---|---|
| « Ethernet » (X550, MAC `74-56-3C-5C-7C-69`) | `188.165.77.137/24` (DHCP OVH), gw `188.165.77.254` ; IPv6 `2001:41d0:306:4589::1` | patte publique — **porte la route par défaut**, ne pas toucher |
| « Ethernet 2 » (X550 #2, MAC `74-56-3C-5C-7C-6A`) | `10.40.0.40/24`, **sans passerelle**, VLAN 400, MTU 1500 | patte vRack — flux proxy-tim→backend et accès privé |
| « DC-TELLIS-PARTENAIRES » (WireGuard, `tun_wg1` côté pfSense TELLIS) | `172.32.0.2/32` | tunnel direct avec le site TELLIS — réplication PACS |

### La patte vRack (posée le 25/08/2026)

`10.40.0.40` suit la convention par dizaines du VLAN 400
([01-architecture.md](01-architecture.md#réseau)) : `.1` OPNsense, `.10`
proxy-tim, `.20` PBS, `.30` headscale, **`.40` pacs03**. Le tag 802.1Q est posé
au niveau du pilote Intel (propriété « ID du VLAN », keyword `VlanId`) — la
règle du cluster s'applique aussi à un bare-metal : **une trame non taguée sur
le vRack atterrit dans le bloc public `57.130.34.120/29`**, à côté du WAN
d'OPNsense.

Configuration exacte, rejouable telle quelle après réinstallation (PowerShell
administrateur) :

```powershell
Set-NetIPInterface -InterfaceAlias "Ethernet 2" -Dhcp Disabled
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -RegistryKeyword "VlanId" -RegistryValue 400
New-NetIPAddress -InterfaceAlias "Ethernet 2" -IPAddress 10.40.0.40 -PrefixLength 24
New-NetRoute -InterfaceAlias "Ethernet 2" -DestinationPrefix 10.90.0.0/24 -NextHop 10.40.0.1
Set-DnsClient -InterfaceAlias "Ethernet 2" -RegisterThisConnectionsAddress $false
```

Tout est persistant (PersistentStore vérifié pour l'IP et la route). Pas de
passerelle sur cette carte : la route par défaut reste sur la patte publique,
seule la plage des nomades `10.90.0.0/24` est renvoyée vers OPNsense
(`10.40.0.1`) pour que les réponses aux accès VPN reviennent par le bon chemin.

### Routes volontairement absentes — ne pas les « corriger »

- **`192.168.101.48/28` et `192.168.101.96/28` (TELLIS)** : déjà routées par le
  tunnel direct `DC-TELLIS-PARTENAIRES` (on-link `172.32.0.2`, métrique 5,
  relevé `route print` du 25/08/2026). Les doubler via `10.40.0.1` créerait un
  conflit de routage. Les machines TELLIS de ces plages joignent le serveur par
  `172.32.0.2`, pas par `10.40.0.40`.
- **`192.168.111.0/24` (RIS VENUS)** : ce serveur n'a pas besoin de joindre
  cette plage — décision du 25/08/2026.

### Le tunnel direct TELLIS

AllowedIPs relevés : `192.168.101.48/28`, `192.168.101.96/28`, `172.32.0.2/32`.
La plage `172.32.0.0/24` est intégrée au contrôle de recouvrement
([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)) — elle ne croise
ni `172.33.0.0/24` (notre `wg2`) ni aucune autre plage documentée.

**Ce tunnel doit perdurer pour le moment.** Sa suppression au profit du
vRack/`wg2` est un chantier futur, consigné dans
[06-reste-a-faire.md](06-reste-a-faire.md#8-vpn-site-à-site--points-ouverts).

---

## Mesures du 25/08/2026

| Mesure | Résultat |
|---|---|
| ping pacs03 → OPNsense (`10.40.0.1`) | ✅ <1 ms, TTL 64 |
| ping proxy-tim (CT 201) → `10.40.0.40` | ✅ 0,16–0,37 ms (moy. 0,25 ms), TTL 128 — trajet direct de niveau 2, aucun routeur intermédiaire |
| MTU du chemin (payload 1472, DF) | ✅ passe — MTU 1500 confirmé de bout en bout, GRA4↔GRA3 compris |
| HTTP backend privé vs public | ✅ réponses identiques (`404` de référence, `Microsoft-HTTPAPI/2.0`, 315 octets) |
| Chaîne complète client → VIP `57.130.34.122` → nginx → `10.40.0.40` | ✅ répond après la bascule du vhost |

---

## Reste à faire

- ⚠️ **Désactiver NetBIOS sur « Ethernet 2 »** (propriétés IPv4 → WINS, ou clé
  `NetbiosOptions=2` de l'interface) — encore actif au 25/08/2026.
- ⚠️ **Restreindre le pare-feu Windows sur la patte vRack** : en entrée,
  autoriser le port HTTP depuis `10.40.0.10` (proxy-tim), ICMP, et RDP depuis
  `10.90.0.0/24` ; bloquer le reste. Sans risque de verrouillage : l'accès
  public n'est pas concerné.
- 📋 À terme, enrôler le serveur dans le tailnet headscale avec `tag:pacs`
  (clé sous le user `infra`, client Windows + « Run unattended » —
  [11-headscale.md](11-headscale.md#enrôler-une-passerelle-dicom-procédure-par-site))
  s'il doit recevoir du DICOM des passerelles de sites — c'est le rôle prévu
  par les ACL.
- 📋 Chantier futur : supprimer le tunnel `DC-TELLIS-PARTENAIRES`
  ([06-reste-a-faire.md](06-reste-a-faire.md)).
