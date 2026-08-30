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
| Matériel | carte mère GIGABYTE MX33-BS1-V1 (BIOS F09d de 08/2023) ✅ ; Xeon-E 2386G (6c/12t, 3,5/4,7 GHz) ✅ ; 32 Go ECC DDR4-3200 (2×16 Go Samsung, 2 slots libres, 64 Go max) ✅ |
| Disques | 2×512 Go SSD NVMe + 2×6 To HDD SATA, soft RAID 📋 — volumes relevés : [Inventaire](#inventaire-du-29082026) |
| OS | Windows Server 2022 Standard 21H2 (build 20348) ✅, installé le 13/05/2024, licence volume (KMS), hors domaine (WORKGROUP) |
| Statut | HDS 📋 |
| Rôle | **PACS complet EDL Xplore sur Oracle 19c** ✅ ([Inventaire](#inventaire-du-29082026)) — backend HTTP de `pacs-secours.teleimagerie.net` ✅ ; réplication depuis TELLIS par tunnel WireGuard direct ✅ |
| Accès admin | RDP et **SSH par clé** (compte `admin`) sur `10.40.0.40`, **via VPN nomade uniquement** depuis le 30/08/2026 — pare-feu allumé, IP publique fermée ([Accès SSH et pare-feu](#accès-ssh-et-pare-feu-30082026)) ✅ |

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
| Application par la chaîne complète | ✅ `https://pacs-secours.teleimagerie.net/xaconsolepacs/` → `200` |
| pacs03 → pfSense TELLIS (`172.33.0.1`) par wg2 | ✅ 15–16 ms, TTL 63, traceroute `10.40.0.1` → `172.33.0.1` — route de test `/32` temporaire (ActiveStore) via OPNsense |
| pacs03 → `192.168.101.52` par le tunnel direct (référence) | ✅ 20–21 ms, TTL 127 |
| pacs03 → prod01 (`192.168.101.54`) par wg2 | ✅ 16–39 ms, TTL 62 (OPNsense + pfSense) — route `/32` de test + route retour `via 192.168.101.59` posée sur prod01 |
| MTU wg2 depuis pacs03 | ✅ payload 1392 passe ; 1472+DF refusé **proprement** par `10.40.0.1` (ICMP « à fragmenter ») → PMTUD fonctionnel, MTU 1420 confirmé |
| prod01 → pacs03 (initiation TELLIS→OVH) | ✅ **réussi après ajout d'une règle `pass` sur le pfSense** (25/08/2026 au soir) — le premier échec (capture vide côté cluster) avait bien pour cause la patte `.59` sans règle. Ping 17–23 ms, TTL 126 ; `curl http://10.40.0.40/` → `404 Microsoft-HTTPAPI` : session TCP complète à travers wg2, MSS/MTU 1420 OK. Bonus : le pare-feu Windows de pacs03 accepte ICMP et TCP 80 depuis une source hors sous-réseau local. Règles pfSense : voir [13-tellis.md](13-tellis.md#règles-posées-sur-opt1_tim-le-25082026-sens-tellis--dc-ovh) |

> **L'application vit sous `/xaconsolepacs/`** — la racine `/` renvoie un `404`
> (page par défaut de `http.sys`), et c'est le comportement de base : vérifié
> identique octet pour octet entre l'ancien VPS de production et le nouveau
> chemin. Un `404` sur `/` n'est donc **pas** un signe de panne ; pour tester le
> service, viser `/xaconsolepacs/`.
>
> Constaté à la bascule DNS du 26/08/2026 : la console n'est pas le gros du
> trafic — le volume vient de l'**alimentation en études sous
> `/PACS_TIM_BCK/`** (`POST …/VAL9/studies`, ~300–650 Ko, toutes les ~30 s
> depuis les sites). Deux chemins à contrôler, donc, pour juger le service
> ([09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026)).

---

## Inventaire du 30/08/2026

Relevé complet par [scripts/inventaire-windows.ps1](scripts/inventaire-windows.ps1),
**avec droits administrateur** cette fois (post-patching et désinstallation de
Veeam B&R), archivé brut dans
[configs/inventaire-pacs03-2026-08-30.md](configs/inventaire-pacs03-2026-08-30.md)
(remplace celui du 29/08, conservé dans l'historique git).
Ci-dessous ce que la fiche doit en retenir.

Matériel désormais connu : GIGABYTE MX33-BS1-V1, Xeon E-2386G (6c/12t),
32 Go ECC (64 max), **2 × 6 To HDD SATA + 2 × 512 Go NVMe Samsung, les 4
« Healthy »**. Les tailles de volumes (C:+D: ≈ un NVMe ; E:+F: ≈ un HDD)
suggèrent **deux miroirs** 📋 — à confirmer (gestionnaire de disques ou BIOS).
BIOS F09d de 2023 : une mise à jour existe probablement, à regarder lors d'une
prochaine fenêtre.

### Ce que fait réellement ce serveur

Le « backend HTTP » est un **PACS complet de l'éditeur EDL (gamme Xplore)** :
une douzaine de services `Xn*` sous `E:\EDL\` (tous sous le compte local
`.\admin`), adossés à **Oracle Database 19c** (instance `XPLORE`, `E:\ORACLE`,
listener 1521). `XnCONSOLEPACS` porte la console web (`/xaconsolepacs/`,
publiée par http.sys sur le port 80) et écoute aussi en **DICOM sur le
port 104** ; `XnXPLOREVIEWWEB` est le viewer web, `XnPUSH` (8005) et
`XnTELEMEDGATEWAY` (109) les échanges télémédecine — six services
`XnTELEMEDCLOUD_TLMTIM723x` sont à l'arrêt.

S'y ajoutent trois **agents DICOM « MyTIM »** hors gamme EDL :
`DicomAgent-isoteam` (**11112**), `DicomAgent-tim` (**11113**) et
`isoteam-sender`. Les ports 104 et 11112 sont précisément ceux prévus par les
ACL du tailnet pour `tag:pacs` ([11-headscale.md](11-headscale.md)) :
l'enrôlement futur collera au trafic déjà en place.

Les tâches planifiées « Sauvegarde de la base de données »
(`E:\__XPLORE32\Backup\Scripts\Save_base.bat`) et « Optimisation » sont le
mécanisme de sauvegarde *applicatif* — horaires et destination à lire avec des
droits admin ⚠️.

### Stockage

| Volume | Label | Taille | Libre |
|---|---|---|---|
| C: | Windows | 181,4 Go | 130,7 Go |
| D: | TEMP | 295 Go | 242,6 Go |
| E: | BDD | 976,6 Go | 901,8 Go |
| F: | IMAGE | 4 612,5 Go | 915,9 Go |

Recoupement avec le matériel déclaré 📋 : C:+D: (≈ 476 Go) sur le miroir NVMe
512 Go, E:+F: (≈ 5,6 To) sur le miroir HDD 6 To. **F: (les images) est plein à
80 %** — premier volume à surveiller. Le relevé des disques physiques étant
vide sans admin, l'état du RAID logiciel est aujourd'hui invérifiable ⚠️
(smartmontools est installé, sans doute pour ça). Partages SMB : `PACS`
(`F:\PACS`) et `VBRCatalog` (`F:\VBRCatalog`).

### Veeam B&R — ✅ désinstallé le 30/08/2026 (n'avait jamais rien sauvegardé)

La machine portait **Veeam Backup & Replication 12.1 serveur entier** (installé
le 28/06/2024) : ~20 services, tous les plugins, catalogue dans `F:\VBRCatalog`,
une quinzaine de ports à l'écoute — mais **jamais configuré, zéro sauvegarde**
(précision utilisateur du 29/08). Une surface d'attaque sans contrepartie.
Chronologie de la résolution : au reboot post-patching du 30/08 ses services
ne sont pas repartis (salve d'alertes Zabbix), l'utilisateur a **désinstallé**
dans la foulée. Vérifié depuis le vRack : **111, 2049, 6160, 9392 fermés**.
Les 21 alertes ont été fermées manuellement ; les items découverts
disparaîtront d'eux-mêmes à l'échéance de rétention LLD (7 j).

L'inventaire de 13:55 avait révélé une désinstallation partielle (Agent,
VSS Integration, VSS HW Provider, VDDK encore actifs) — **soldée dans la
foulée : l'inventaire de 14:07 ne montre plus aucun composant Veeam**, ni
logiciel, ni service, ni port. Restes passifs à nettoyer un jour : le partage
SMB `VBRCatalog` (`F:\VBRCatalog`) et le **PostgreSQL 15** (l'ex-base de
config B&R, service toujours en marche sur 127.0.0.1:5432 pour rien).

### Services critiques — supervision renforcée depuis le 30/08/2026

Déclarés critiques par l'utilisateur le 30/08/2026 : **`XnCONSOLEPACS`**
(console web, port 104), **`XnDicomSCU`**, **`XnDICOMVIEWER`**,
**`XnTELEMEDGATEWAY`** (port 109) et **`XnXPLOREVIEWWEB`**. Pour chacun,
Zabbix porte un déclencheur dédié **High** « SERVICE CRITIQUE … en anomalie »
qui sonne (et **part en mail** via ALERTE HAUTE) dès que l'état du service
n'est plus *Running* — arrêté, en pause, bloqué en démarrage, ou disparu.
Les déclencheurs Average « is not running » du template sont désactivés pour
ces cinq-là (anti-doublon). Le ménage du même jour : les `XnTELEMEDCLOUD_*`
(7230-7235) passés en **manuel + arrêtés**, WireGuard mis à jour 0.5.3 → 1.1.

> ⚠️ **Situation de sauvegarde à garder en tête** : pacs03 est un **serveur
> physique hors cluster — PBS ne le couvre pas**, et Veeam parti, la seule
> sauvegarde active est la tâche applicative `Save_base.bat` (Oracle —
> destination et horaires à relever avec des droits admin ⚠️). Les images de
> `F:` n'ont **aucune copie** : cohérent avec le rôle de la machine, qui est
> *elle-même* le secours du PACS principal — mais c'est un choix, pas un oubli,
> et il doit rester visible ici.

### Sécurité — relevé du 29/08/2026

- ✅ **Correctifs Windows appliqués et machine redémarrée le 30/08/2026**
  (précédent : KB5034770 du 20/02/2024, deux ans et demi de retard — c'était
  le point noir de la fiche). Même fenêtre : **fichier d'échange porté de
  2 Go (plein à 100 % depuis décembre, allocations en danger) à 16 Go fixes**
  — l'alerte swap Zabbix s'est refermée seule. Reste à s'assurer que le canal
  de mise à jour **continue** de fonctionner (vérifier dans un mois).
- ✅ ~~RDP (3389), WinRM (5985), SMB (445), RPC (135), Oracle (1521), NFS
  Veeam (111/2049) écoutent sur toutes les adresses, le filtrage réel est
  inconnu~~ — **tranché le 30/08/2026 : le pare-feu était entièrement
  désactivé, tout était exposé et attaqué ; allumé et fermé le jour même**
  ([Accès SSH et pare-feu](#accès-ssh-et-pare-feu-30082026)).
- NetBIOS (137/139) toujours lié aux **trois pattes**, vRack et tunnel TELLIS
  compris — confirme le point ouvert du 25/08.
- **TeamViewer Host** actif (accès distant tiers permanent) et **AzureArcSetup**
  présent — deux canaux d'administration à inventorier/statuer ⚠️.
- Defender actif ✅. **Zabbix Agent 2** (7.4, port 10050) déjà en place depuis
  le 15/08/2025 — à raccorder au Zabbix du cluster ([17-zabbix.md](17-zabbix.md)).

### Accès SSH et pare-feu (30/08/2026)

**SSH opérationnel et verrouillé.** OpenSSH serveur (natif Windows) activé le
30/08 ; la clé `id_ed25519` du poste d'admin est dans
`C:\ProgramData\ssh\administrators_authorized_keys` (ACL restreinte par SID
`S-1-5-18`/`S-1-5-32-544` — obligatoire, sinon sshd ignore le fichier en
silence ; et c'est **ce** fichier qui vaut pour tout compte admin, pas
`~\.ssh\authorized_keys`). Connexion : `ssh admin@10.40.0.40` **depuis le VPN
nomade uniquement** ; `PasswordAuthentication no` + `KbdInteractiveAuthentication
no` dans `sshd_config`. Une session SSH d'un compte admin porte le jeton complet
(pas de filtre UAC) : le serveur se pilote intégralement depuis WSL
(`scp` + `powershell -File`), inventaire compris
(`scripts/inventaire-windows.ps1`, laissé dans `C:\Users\admin\`).

**Découverte en verrouillant : le pare-feu Windows était entièrement désactivé**
(les trois profils `Enabled=False`) — c'était la réponse au « filtrage réel
inconnu » du relevé du 29/08 et au « bonus » troublant des mesures du 25/08 :
tout ce qui écoutait était exposé sur l'IP publique. Et la surface était
**activement attaquée** : 7–11 connexions SMB établies depuis `189.253.31.199`
(aucune session authentifiée derrière — pré-auth uniquement), 3 sessions RDP
établies depuis des IP APAC/Huawei Cloud, **> 5 000 échecs de connexion (4625)
sur les dernières 24 h**. Audit des réussites (4624 réseau/RDP) : **aucune
depuis une IP publique** autre que `88.140.70.114` (IP résidentielle de
l'utilisateur) — fenêtre couverte ≈ 24 h (plafond de 5 000 événements),
un audit plus profond reste possible.

**Allumage le 30/08 vers 15 h 15** : `DefaultInboundAction Block` sur les trois
profils, journal des rejets activé (`pfirewall.log`, 16 Mo), et purge de
~60 règles d'autorisation héritées à portée « Any » (Bureau à distance, partage
de fichiers 445/139/137, RPC, une règle 80/443, les règles applicatives
`Any/Any` des services Xn/TeamViewer/iperf, un reliquat 10051…). Les règles
`CoreNet-*` sont **préservées** — l'IP publique est en DHCP OVH, couper
`CoreNet-DHCP-In` tuerait le renouvellement du bail. Liste blanche posée :

| Règle | Flux autorisé |
|---|---|
| `ssh-in` | TCP 22 depuis `10.90.0.0/24` (VPN nomade) |
| `rdp-vpn` | TCP 3389 depuis `10.90.0.0/24` |
| `pacs-http-proxy` | TCP 80 depuis `10.40.0.10` (proxy-tim — seul client HTTP observé) |
| `zabbix-agent` | TCP 10050 depuis `10.40.0.0/24` + `57.130.34.122` (serveur Zabbix) |
| `tunnel-tellis` | **tout** flux entrant arrivant par l'interface `DC-TELLIS-PARTENAIRES` (même confiance qu'avant, réplication comprise) |
| `wg-endpoint` | UDP 51736 depuis `37.61.243.246` (ceinture-bretelles : pacs03 initie le tunnel, keepalive 25 s) |
| `icmp-prive` | ICMPv4 depuis `10/8`, `172.16/12`, `192.168/16` |

**Vérifications après bascule** : 22/80/135/445/3389/5985/11112 injoignables
depuis Internet ✅ ; flux proxy→80 vivant ✅ ; Zabbix interroge toujours
(source `57.130.34.122`) ✅ ; handshake WireGuard frais ✅ ; sessions RDP
hostiles coupées par la bascule, connexions SMB restantes tuées à la main ✅.
TeamViewer (sortant vers son cloud) n'est **pas** affecté par le pare-feu — le
« statuer » du reste-à-faire garde tout son sens. Retour arrière si un flux
légitime imprévu casse : `Set-NetFirewallProfile -All -Enabled False` par SSH,
puis lire `%systemroot%\system32\LogFiles\Firewall\pfirewall.log`.

---

## Reste à faire

- ✅ ~~Reprendre le patching Windows~~ — **patché et redémarré le 30/08/2026**
  ([Sécurité](#sécurité--relevé-du-29082026)). Reste : vérifier fin septembre
  que le canal de mise à jour continue de fonctionner.
- ✅ ~~Scanner la surface publique depuis l'extérieur~~ — fait le 30/08/2026,
  verdict sans appel : pare-feu désactivé, tout exposé. Fermé le jour même
  ([Accès SSH et pare-feu](#accès-ssh-et-pare-feu-30082026)).
- ⚠️ **Changer le mot de passe du compte `admin`** : il a essuyé un bruteforce
  massif (> 5 000 tentatives/24 h) pendant une durée indéterminée, sur un nom
  de compte évident. Aucune réussite détectée sur la fenêtre auditée (~24 h),
  mais la fenêtre est courte — rotation prudente, et l'occasion d'auditer les
  journaux plus en profondeur si le cœur nous en dit.
- 📋 **Relire `pfirewall.log` d'ici quelques jours** (rejets journalisés) pour
  attraper un éventuel flux légitime rare que la liste blanche du 30/08 aurait
  manqué — un client DICOM direct oublié, par exemple.
- ⚠️ **Désactiver NetBIOS sur « Ethernet 2 »** (propriétés IPv4 → WINS, ou clé
  `NetbiosOptions=2` de l'interface) — confirmé encore actif au 29/08/2026
  (ports 137/139 liés aux trois pattes). Exposition **bloquée** par le pare-feu
  depuis le 30/08, mais la désactivation propre reste à faire.
- ✅ ~~Restreindre le pare-feu Windows sur la patte vRack~~ — **dépassé le
  30/08/2026 : pare-feu allumé sur les trois profils avec liste blanche
  complète**, patte publique comprise
  ([Accès SSH et pare-feu](#accès-ssh-et-pare-feu-30082026)).
- ✅ ~~Statuer sur Veeam B&R~~ — **entièrement désinstallé le 30/08/2026**
  (B&R puis, dans la foulée, Agent + VSS Integration + VSS HW Provider +
  VDDK — l'inventaire de 14:07 ne montre plus aucun composant). Restes
  passifs à nettoyer un jour : partage SMB `VBRCatalog` et PostgreSQL 15
  (l'ex-base de config, service actif sur 127.0.0.1:5432 pour rien).
- ✅ ~~`XnTELEMEDCLOUD_TLMTIM7235` arrêté~~ — tranché le 30/08/2026 :
  **tous les `XnTELEMEDCLOUD_*` (7230-7235) sont passés en démarrage manuel
  et arrêtés** (pas besoin de tourner en automatique). Ils sortent du champ
  de la découverte de services Zabbix (qui ne suit que les services
  automatiques) : plus d'alertes à leur sujet, par construction.
- ⚠️ **Services GoogleUpdater** (`GoogleUpdaterService…` ×2) : toujours en
  automatique + arrêtés → les deux alertes Average subsistent. Même recette
  que les TELEMEDCLOUD (passage en manuel) ou désinstallation de l'updater.
- ⚠️ **Documenter la tâche applicative `Save_base.bat`** (avec droits admin) :
  quoi, vers où, à quelle fréquence, et qui surveille ses échecs — c'est la
  **seule** sauvegarde active du serveur.
- ⚠️ **Statuer sur TeamViewer et Azure Arc** : les garder comme canaux
  d'administration, ou les remplacer par le tailnet.
- 📋 À terme, enrôler le serveur dans le tailnet headscale avec `tag:pacs`
  (clé sous le user `infra`, client Windows + « Run unattended » —
  [11-headscale.md](11-headscale.md#enrôler-une-passerelle-dicom-procédure-par-site))
  s'il doit recevoir du DICOM des passerelles de sites — c'est le rôle prévu
  par les ACL, et les ports attendus (104, 11112) sont déjà servis.
- 📋 Chantier futur : supprimer le tunnel `DC-TELLIS-PARTENAIRES`
  ([06-reste-a-faire.md](06-reste-a-faire.md)).
