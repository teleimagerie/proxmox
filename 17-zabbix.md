# `zabbix` — supervision d'entreprise

Conteneur LXC **204**, Debian 13, **Zabbix 7.0.30 LTS** (MariaDB 11.8, nginx,
PHP 8.4). **Migré le 29/08/2026** depuis le VPS OVH `vps-41b1229b`
(`51.178.36.192`, Ubuntu 24.04, Zabbix 7.0.22, MariaDB 10.11) — bascule DNS à
15:51 UTC, **gel de collecte total : ~3-4 minutes**, les 6 hôtes supervisés
re-collectés dans les 4 minutes suivant le switch.

| | |
|---|---|
| Adresse interne | `10.40.0.60/24` (VLAN 400), passerelle `10.40.0.1` |
| Nom public | `zabbix.teleimagerie.net` — derrière **proxy-tim** (VIP `.122`), pas de VIP dédiée |
| Ressources | **2 vCPU, 4 Go RAM** (réduits le 30/08 sur mesures : 608 Mio utilisés, load 0,00 — caches Zabbix ramenés à 128M/128M, remplis à 2 %/0 %, et `innodb_buffer_pool_size` **monté** 128M → 512M pour la base de 3,2 Gio), disque 40 Go sur Ceph |
| Accès | `ssh root@10.40.0.60` depuis un nœud (clés cluster + clé WSL de matt) |
| Haute dispo | ressource HA depuis le 29/08/2026 (`max_restart 3`, `max_relocate 3`) |
| Bascule mesurée | **~19-20 s** (relocalisation pve2 → pve3, sonde 1 s sur l'UI publique) |
| Nœud courant | **pve3** (relocalisé pour équilibrage post-migration) |
| UI | `https://zabbix.teleimagerie.net/` (l'ancien chemin `/zabbix/` est redirigé 301) |
| Base | `zabbix`, utf8mb4/utf8mb4_bin, ~3,2 Gio ; dump quotidien 01:15 (`zbx-dump.timer`, 7 jours glissants dans `/var/backups/zabbix/`) |
| Sauvegarde | job PBS quotidien 02:00 (`all` sauf 102) — le dump 01:15 est dedans |

---

## Le problème que ce service résout

Le VPS Zabbix était le dernier service d'infrastructure hors du cluster :
sans sauvegarde documentée, sans HA, et invisible du dossier (l'angle mort
noté dans [14-noms-de-domaine.md](14-noms-de-domaine.md)). L'incident du
28/08/2026 (ci-dessous) a démontré le risque : **32 h de supervision aveugle
sans que personne ne soit prévenu** — le monitoring ne se surveille pas
lui-même. La migration le fait entrer dans le périmètre HA + PBS, et répond au
point ouvert de [06-reste-a-faire.md §4](06-reste-a-faire.md#4-supervision---traité-le-29082026-reste-la-sonde-externe)
(« mutualiser plutôt que construire un deuxième monitoring ? »).

---

## Incident du 28-29/08/2026 sur le VPS (résolu)

**La supervision est restée morte ~32 h** (28/08 06:06 → 29/08 14:12 UTC),
découvert par hasard pendant l'audit de migration. Mécanique :

1. unattended-upgrades déroule un gros lot (~135 paquets : systemd, libc6,
   openssl, noyau…) ; needrestart redémarre `mariadb` + `zabbix-server` ;
2. **deadlock** : l'arrêt de `zabbix-server` ne finit jamais quand la base est
   déjà tombée (il veut y vider son cache d'historique, et l'unité amont est
   livrée avec `TimeoutStopSec=infinity`) — et le démarrage de MariaDB attend
   derrière ce job d'arrêt dans la file systemd ;
3. la transaction apt garde le verrou dpkg pendant tout ce temps.

Résolution : `systemctl kill -s SIGKILL zabbix-server` pour crever le job
d'arrêt, la file se vide, MariaDB repart, la transaction apt se termine.
**Garde-fou posé sur le VPS** : drop-in
`/etc/systemd/system/zabbix-server.service.d/stop-timeout.conf`
(`TimeoutStopSec=60`) — validé en réel le jour même : le cycle needrestart
suivant a reproduit le deadlock et systemd l'a résolu seul en 60 s.
Perte : ~32 h d'historique de collecte ; shutdown MariaDB propre, aucune
corruption. Un reboot du VPS reste en attente (noyau + libc6) — sans objet si
la bascule a lieu avant.

> À reproduire sur le CT 204 ? Le paquet Debian a le même
> `TimeoutStopSec=infinity`. **Le même drop-in a sa place sur le CT** — à poser
> au jour J (noté dans la checklist ci-dessous).

---

## Ce que supervise ce Zabbix (audit du 29/08/2026)

7 hôtes réels (le reste : 345 templates + prototypes de découverte), 6 comptes
frontend (auth interne, ni LDAP ni SAML), et **un seul média d'alerte : Mailjet**
(`in-v3.mailjet.com:465`, authentifié, `no-reply@teleimagerie.net` — déjà dans
le SPF, la configuration voyage dans le dump).

| Hôte | Mode | IP constatée (tcpdump 10051) | Après bascule (29/08, 15:55 UTC) |
|---|---|---|---|
| Zabbix server | passif local | 127.0.0.1 | ✅ agent2 du CT |
| `pacs03.teleimagerie.net` | **passif** (197 items) | 188.165.77.137 | ⚠️ corrigé le 30/08 : rejetait la source `.121` (whitelist = le nom → VIP) — **réparé par le NAT sortant `.122`**. **Seuils disque `IMAGE(F:)` (4,6 To, ~80 %) personnalisés le 30/08** : Warning 90 % (macro contextuelle `"IMAGE(F:)"`), **High 95 %** et **Disaster 98 %** (déclencheurs dédiés, mail ; le High se tait quand le Disaster est actif), CRIT template neutralisé à 100 |
| `gestion.teleimagerie.net` | **passif** (137 items) | 51.210.24.59 | ✝ serveur décommissionné (mort depuis le 27/08) — **hôte supprimé de Zabbix le 30/08** |
| `prod01.teleimagerie.net` | **actif** (62 items) | 37.61.243.245 | ✝ **hôte supprimé de Zabbix le 30/08** sur instruction (agent muet depuis le 27/08) |
| `WIN-SRV-TSPLUS` | **actif** (156 items) | 37.61.243.246 (TSplus, TELLIS) | ✅ a suivi le DNS (< 4 min) ; récupération automatique du service armée le 02/09/2026 (comme pacs03) |
| `SYNGOVIA-135104` | **SNMP v2c + ICMP + sondes TCP** (Windows by SNMP), depuis le **02/09/2026** | `192.168.101.98` par `wg2` | ✅ **agent impossible** : WDAC Siemens refuse le MSI (code 1625) — supervision sans agent, voir [§ Syngo Via](#serveurs-syngo-via-de-tellis--sans-agent-02092026) |
| `SYNGOVIA-135113` | idem | `192.168.101.100` par `wg2` | ✅ idem |
| `TIMWFMCORE` | **actif Windows** | IP non capturée (agent actif) | ✅ **rétabli le 30/08** : muet depuis la bascule (agent accroché à l'ancienne résolution DNS), reparti après **redémarrage de l'agent sur la machine** — 63/77 items frais en 2 min. Épisode du 30/08 au matin : cru à tort Linux à cause de `162.19.25.107` (voir ligne suivante), re-templaté ~1 h puis rétabli. **Seuils disque `Database(F:)` personnalisés le 30/08** : Warning à 90 % (macro `{$VFS.FS.PUSED.MAX.WARN:"Database(F:)"}` — ⚠️ le contexte est `{#FSLABEL}({#FSNAME})`, pas la lettre seule), palier template neutralisé (CRIT à 100) et remplacé par un déclencheur **High ≥ 95 %** qui part en mail |
| ~~`162.19.25.107`~~ (`vps-2e178199.vps.ovh.net`) | — | 162.19.25.107 | **ancien serveur MYTIM** : ne sert plus mais toujours allumé, agent Zabbix 7.4 actif et whitelist ouverte sur zabbix — **pas de supervision souhaitée** (décidé le 30/08). Candidat à l'extinction/résiliation : une machine oubliée allumée est une surface d'attaque |
| `TIM-VENUS1-AP` | **actif** (65 items) + ICMP et sondes TCP | `192.168.111.63` par `wg2` | ✅ **raccordé le 05/09/2026** — voir [§ RIS VENUS](#serveurs-ris-venus-de-tellis--agent-actif-05092026) |
| `TIM-VENUS2-IF` | idem (60 items) | `192.168.111.64` par `wg2` | ✅ idem |
| `TIM-VENUS3-DB` | idem (63 items) | `192.168.111.65` par `wg2` | ✅ idem |
| `CMSI-LES-HERBIERS` | 1 item, quasi mort | pas vu en 3 min | toujours muet — à trancher (supprimer ?) |

Pas de proxy Zabbix, pas de traps SNMP (trapper désactivé), pas de JMX/IPMI,
répertoires `externalscripts`/`alertscripts` vides, aucun cron personnalisé.

---

## Architecture (identique au patron auth/Keycloak)

```
   navigateur / agents actifs (externe)          interne VLAN 400
            │                                          │
  DNS public : zabbix → VIP .122          Unbound : zabbix → 10.40.0.10
            │                                          │
            ▼                                          ▼
   57.130.34.122 : tcp/443 ──rdr──▶ proxy-tim (CT 201) ── http://10.40.0.60:8080
                   tcp/10051 ─rdr────────────────────────▶ 10.40.0.60:10051
                                                           Zabbix (CT 204)
                                                           + MariaDB locale
```

- **443** : routeur SNI du CT 201 → vhost `zabbix.teleimagerie.net.conf`
  (TLS terminé, `/zabbix/*` → 301 `/*`) → HTTP clair VLAN 400. Vhost archivé :
  [configs/zabbix.teleimagerie.net.conf](configs/zabbix.teleimagerie.net.conf).
- **10051** : le trapper n'est pas du HTTP — redirection NAT directe sur la
  VIP `.122` vers le CT 204, `pass` porté par la règle
  ([08-opnsense.md](08-opnsense.md#filtrage)). Testé ouvert de l'extérieur le 29/08.
- **Certificat** : DNS-01 acme.sh sur pve1 (patron syngo), déployé par
  [scripts/deploy-zabbix.sh](scripts/deploy-zabbix.sh), renouvelé par
  `acme-renew.timer` ([09-proxy-tim.md](09-proxy-tim.md#certificats)).
- **Vue interne** : override Unbound `zabbix → 10.40.0.10`
  ([08-opnsense.md](08-opnsense.md#résolution-interne--override-unbound)).
  Un client du VLAN 400 qui aurait besoin de 10051 viserait `10.40.0.60`
  en direct (l'override, lui, mène au proxy qui ne sert que le web).

**Répétition générale mesurée le 29/08/2026** (base 3,13 Gio, VPS en service) :
dump à chaud **1 min 05 s** (304 Mo gz) · transfert VPS→CT **7,8 s** ·
import **1 min 15 s** · upgrade de schéma 7.0.22→7.0.30 automatique et
instantané. **Fenêtre de gel réelle du jour J : ~3 minutes** (l'estimation
initiale « 1 à 3 h » était très pessimiste).

fping fonctionne dans le CT non privilégié (testé sous l'uid zabbix), sans
setcap ni privilège.

---

## Bascule du 29/08/2026 — mesures réelles

Méthode maison (TTL 60 posé à 14:45 UTC, vérifié sur `ns17`/`dns17`, une
heure d'attente pour l'expiration des caches 3600) :

| Étape | Heure UTC | Durée |
|---|---|---|
| Gel du VPS (`systemctl stop + disable zabbix-server`) | 15:48:09 | — |
| Dump final à chaud (302 Mo gz) | | **1 min 03 s** |
| Tirage VPS → CT | | **7,7 s** |
| Import + drop-in `TimeoutStopSec=60` + redémarrage | 15:50:57 | **1 min 15 s** |
| Bascule DNS (`bascule-zabbix.py switch`) | 15:51:49 | propagée immédiatement (ns17, dns17, 1.1.1.1, 8.8.8.8) |
| **Gel de collecte total** | | **~3-4 min** (première valeur CT : 15:51:09) |

Contrôles post-bascule, tous ✅ le jour même :

- les 3 agents actifs (TSplus, prod01, TIMWFMCORE) référençaient le **nom**
  et ont suivi le DNS en < 4 min ;
- ⚠️ **corrigé le 30/08 : les passifs n'ont PAS suivi.** Les « données
  fraîches » vues le soir de la bascule n'étaient que le sous-ensemble actif.
  En réalité : **pacs03** rejette les polls depuis la nouvelle source `.121`
  (whitelist `Server=` de son agent — problème « agent not available » ouvert
  depuis 15:55 le 29/08, sévérité Average donc jamais mailé), et **gestion**
  était déjà morte **avant** la migration (refus TCP depuis le 27/08 07:16 —
  et pour cause : **serveur décommissionné**, hôte supprimé de Zabbix le
  30/08 sur instruction). **Résolution pacs03 le 30/08, sans toucher à
  Windows** : test depuis le CT 201 (qui sort en `.122`) → `agent.ping=1`,
  preuve que sa whitelist contient le *nom* (→ VIP `.122`) ; une règle de
  NAT sortant fait désormais sortir le CT 204 en `.122` (son identité
  publique) et la collecte passive est repartie en ~60 s
  ([08-opnsense.md](08-opnsense.md#filtrage)) ;
- UI par le vrai DNS : `200 via 57.130.34.122` ; schéma migré 7.0.22 → 7.0.30
  automatiquement à la première connexion ;
- **drainage instantané : zéro paquet** sur 10051/443 du VPS 10 min après le
  switch (60 s de tcpdump) ;
- média Mailjet réactivé, bannière `220 in.mailjet.com` vérifiée depuis le CT
  (le média voyage dans le dump, identique au VPS) ;
- HA : `ha-manager add ct:204` puis **relocalisation mesurée pve2 → pve3 :
  ~19-20 s** (sonde 1 s sur l'UI publique, un `502` puis six timeouts entre
  15:58:27 et 15:58:47) ;
- clé SSH temporaire `ct204-migration-temporaire` retirée du VPS, dumps
  intermédiaires purgés des deux côtés.

**Rollback (tant que le VPS existe)** : `bascule-zabbix.py revert` (~60 s,
TTL encore à 60) + `systemctl enable --now zabbix-server` sur le VPS. Seule
perte : ce que le CT a collecté entre-temps.

### Reste à faire (fenêtre d'observation)

- [x] ~~**test mail depuis l'UI** (*Alerts → Media types → Test*)~~ — **prouvé
  en réel** : chaîne complète validée le 29/08 (nearfull) puis re-validée le
  30/08 avec les déclencheurs sauvegardes — 2 problèmes High → 4 mails
  (mcapon@ + support@) **reçus en boîte** (labels INBOX, pas spam), vérifié
  dans Gmail. À noter : ces mails Zabbix ne figurent pas dans la liste
  `GET /v3/REST/message` de la clé API « keycloack » — le média Zabbix utilise
  d'autres identifiants Mailjet (hérités du VPS, dans le dump) ;
- [ ] vérifier la **première sauvegarde PBS** du CT 204 (job de 02:00) puis
  **restauration de test sous l'ID 299** ([10-sauvegardes.md](10-sauvegardes.md#rejouer-le-test-de-restauration)) ;
- [ ] `bascule-zabbix.py ttl3600` après quelques jours de stabilité (précédent
  proxy : 3 jours) — le `revert` devient alors lent (~1 h) ;
- [ ] **résiliation du VPS** après J+7 : drainage déjà nul, mais laisser la
  fenêtre par prudence ; archivage à froid (dump + `/etc/zabbix`) vers
  `nas-vm`, `poweroff`, puis espace client OVH — et marquer `revert` caduque
  dans `bascule-zabbix.py` (précédent `bascule-3noms.py`) ;
- [ ] `CMSI-LES-HERBIERS` : hôte quasi mort (1 item), à supprimer ou réparer ;
- [x] ~~agent Zabbix de pacs03 planté le 30/08 ~08:08~~ — **traité le 30/08** :
  service redémarré par l'utilisateur (198/213 items re-collectés, alerte
  refermée seule) puis **récupération automatique armée** en console élevée :
  `sc.exe failure "Zabbix Agent 2" reset= 86400 actions= restart/60000/restart/60000/restart/60000`
  (le crash — agent2 7.4.1, survenu juste après une découverte de services
  forcée — ne restera plus silencieux : Windows relance sous 60 s). La
  production PACS n'avait pas été affectée ;
- [ ] **backlog d'alertes purgé le 30/08** (13 problèmes anciens fermés, dont
  services XnTELEMEDCLOUD arrêtés sur pacs03 depuis le 15/08, disques F: > 80 %
  sur pacs03 et TSplus) : ces conditions persistantes **re-déclencheront** —
  c'est voulu, elles reviendront datées d'aujourd'hui ; les traiter sur les
  machines ([15-pacs-secours.md](15-pacs-secours.md#reste-à-faire)).

---

## Serveurs Syngo Via de TELLIS — sans agent (02/09/2026)

Les deux serveurs syngo.via (`syngovia-135104` `.98` et `syngovia-135113`
`.100`, inventoriés dans [13-tellis.md](13-tellis.md#syngo-via)) n'avaient
aucune supervision. **L'agent Zabbix ne peut pas y être installé** : Siemens
verrouille ces machines par Device Guard / WDAC en mode appliqué (noyau et
utilisateur), et le MSI officiel `zabbix_agent2-7.0.30-windows-amd64-openssl.msi`
(signé « Zabbix SIA », signature vérifiée sur place) est refusé par `msiexec`
avec le code **1625, « installation interdite par la stratégie système »**,
avant même de copier un fichier — journal MSI : `SOFTWARE RESTRICTION POLICY:
Verifying package … MainEngineThread is returning 1625`. Aucun contournement
tenté (désactiver WDAC sur un dispositif médical n'est pas notre décision),
fichiers déposés supprimés, hôtes Zabbix conservés mais reconfigurés **sans
agent** :

| | |
|---|---|
| Chemin | le CT 204 (`10.40.0.60`) joint le LAN TELLIS **par `wg2`** (route via `10.40.0.1`) : ping, TCP et SNMP passent — les deux syngo sortent par le pfSense principal `.110`, aucune route retour à poser (contrairement à TIMWFMCORE) |
| Gabarit | **Windows by SNMP** (SNMP v2c, `bulk`), qui inclut déjà ICMP (« Unavailable by ICMP ping » en High) — le gabarit *ICMP Ping* est **incompatible** en plus (clé `icmpping` en double), ne pas l'ajouter |
| Côté serveur syngo | le service SNMP Windows tournait déjà (communauté `public` lecture seule, managers = `localhost`, pare-feu UDP 161 limité au sous-réseau local — l'usage Siemens/HPE local n'est pas touché). Ajouté sur chacun : une **communauté dédiée, lecture seule** (24 caractères aléatoires), `10.40.0.60` dans `PermittedManagers`, une règle pare-feu `SNMP - Zabbix TIM (UDP 161 depuis 10.40.0.60)`, puis redémarrage du service SNMP (quelques secondes, sans effet sur syngo). Réversible : supprimer la valeur de registre `ValidCommunities`, l'entrée `PermittedManagers` et la règle |
| Secret | la communauté vit **dans le registre SNMP des deux serveurs** (`HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities`), dans la macro **secrète** `{$SNMP_COMMUNITY}` de chaque hôte et dans `/root/.snmp-community-syngo` du CT 204 (mode 600, à côté du jeton API). Elle ne figure pas dans ce dépôt |
| Sondes TCP | items *simple check* à la minute, déclencheurs `max(…,3m)=0` : **SCP DICOM tcp/104** (High → mail), **web syngo/IIS tcp/443** (High → mail), RDP tcp/3389 (Average) |
| Ce qu'on voit | CPU, mémoire, **tous les volumes** (dont `N:` System_Backup, déjà à plus de 90 % : le déclencheur Average du gabarit sonne, c'est voulu), interfaces réseau, uptime, ICMP ; ce qu'on **ne voit pas** sans agent : services Windows, journaux d'événements, compteurs de performance |
| Vérifié | 02/09/2026 14:34 UTC : `enabling SNMP agent checks on host "SYNGOVIA-1351xx": interface became available` sur les deux ; systèmes de fichiers C:, D:, E:, M:, N:, S: découverts ; sondes TCP à 1 |

Pour obtenir un jour l'agent (services, journaux) : demander à Siemens
l'ajout de l'agent Zabbix à la liste blanche WDAC — point porté dans la
[checklist TELLIS](13-tellis.md#checklist-de-collecte).

Au passage, **TSplus** (`WIN-SRV-TSPLUS`, agent actif 7.4.3, 156 items frais)
n'a rien eu à installer ; son service a reçu la **même récupération
automatique que pacs03** (`sc failure … restart/60000 ×3`, `reset= 86400`),
qu'il n'avait pas.

---

## Serveurs RIS VENUS de TELLIS — agent actif (05/09/2026)

Les trois serveurs du RIS VENUS de Softway Medical
([13-tellis.md](13-tellis.md#ris-venus-softway-medical)) étaient les derniers
serveurs de TELLIS sans supervision, alors que leur inventaire de la veille y
avait trouvé deux points durs à surveiller : le `D:` de `.63` proche de la
saturation et la base `isotim` de `.65` sans sauvegarde.

**Ici l'agent passe**, contrairement aux syngo : aucun Device Guard / WDAC,
PowerShell en *FullLanguage* sur les trois — c'est donc la méthode « avec
agent » qui s'applique, et elle donne les services Windows et les journaux
d'événements, invisibles en SNMP. SNMP aurait de toute façon exigé d'**installer
une fonctionnalité Windows** sur des serveurs sans correctif depuis avril 2023,
là où les syngo n'avaient qu'un service existant à reconfigurer.

| | |
|---|---|
| Chemin | vérifié avant tout le reste, le 05/09 : le CT 204 (`10.40.0.60`) joint les trois en ICMP **par `wg2`**, et surtout les trois joignent `10.40.0.60:10051` **en sortie**. Passerelle `.254` (pfSense principal) : **aucune route retour à poser**, comme pour les syngo. Cela lève la réserve « reste à tester `10.40.0.0/24` → `192.168.111.x` » de [06-reste-a-faire.md](06-reste-a-faire.md) |
| Mode | **agent 2 en mode ACTIF** (gabarit `Windows by Zabbix agent active`, comme TIMWFMCORE et TSplus) : l'agent se connecte au serveur, **aucun port entrant à ouvrir** — décisif sur `.63`, le seul des trois dont le pare-feu Windows est allumé |
| Agent | **7.0.30**, la version du serveur ; MSI officiel signé « Zabbix SIA », **signature vérifiée avant `msiexec`**. `Server` et `ServerActive` visent **`10.40.0.60`, l'adresse privée et non le nom** : depuis TELLIS le nom résout en public et le trafic ressortirait par Internet vers la VIP `.122`, alors que l'adresse garde le flux dans `wg2` |
| Gabarits | `Windows by Zabbix agent active` **+ `ICMP Ping`** — vérifié en base : le gabarit agent actif ne contient **aucun** item `icmpping`, le cumul est donc sans risque. ⚠️ Ne pas transposer ce cumul aux hôtes SNMP, où il crée une clé en double (piège rencontré sur les syngo) |
| Interface | une interface agent est déclarée bien qu'inutile en mode actif : elle sert d'**ancre `{HOST.CONN}` aux *simple checks***. ⚠️ Cela ne suffit pas : par l'API, un *simple check* dont la clé laisse l'adresse vide part en « non supporté » (« *Check service item must have IP parameter or host interface specified* ») tant que l'item ne porte pas explicitement `interfaceid` — l'interface web le fait toute seule, l'API non |
| Sondes TCP | *simple checks* à la minute, déclencheurs `max(…,3m)=0`, sur le motif syngo : **SFTP de dépôt des sites `2222`** (`.64`, High), **MariaDB `3306`** (`.63` et `.65`, High), **web/IIS `443`** (`.63`, High), Tomcat JasperReports `8081` (`.64`, Average), RDP `3389` (les trois, Average) |
| Services | **Mirth Connect** est surveillé **par l'agent** (`service.info["Mirth Connect Service",state]`, High si ≠ 0) et non par une sonde TCP : Mirth écoute bien sur 8080, mais sur `.63` le port n'est **pas publié sur le réseau** (pare-feu actif, aucune règle) — vérifié depuis le serveur Zabbix *et* depuis le poste, alors qu'il répond en local. Une sonde externe y aurait alarmé en permanence sur un service en parfait état ; le même capteur est utilisé sur `.64` pour que les deux serveurs se lisent pareil |
| Volume `D:` de `.63` | le gabarit classe « *critically low* » en **Average, donc sans mail**. Palier du gabarit neutralisé par macro contextuelle `{$VFS.FS.PUSED.MAX.CRIT:"VENUS(D:)"}` = 100 (⚠️ le contexte est `{#FSLABEL}({#FSNAME})`) et remplacé par un déclencheur **High** avec hystérésis : problème si `min(…,5m) > 90 %`, retour à la normale seulement si `max(…,30m) < 85 %`. L'hystérésis n'est pas décorative — ce volume oscille (4,8 Go libres le 04/09 au soir, 5,4 Go le 05/09 à 10 h 55, **16,4 Go à 11 h 03** après passage de `Venus_Clean_Daemon`), un seuil sec produirait une rafale de mails à chaque purge |
| Récupération | `sc failure … restart/60000 ×3`, `reset= 86400` sur les trois, comme pacs03 et TSplus |
| Vérifié | 05/09/2026 : **65 / 60 / 63 items, aucun non supporté**, données fraîches ; volumes découverts `C: D: E:` sur `.63` et `.65`, `C: D:` sur `.64` ; ICMP et toutes les sondes à 1 ; **la chaîne de mail testée en réel** — le déclencheur `D:` est parti en High et le mail est enregistré comme envoyé à `mcapon@` et `support@` |
| Secrets | **aucun** : l'agent actif ne demande ni communauté SNMP ni jeton. Rien de nouveau hors dépôt |

Deux signaux de fond que la supervision montre désormais, et qui ne sont pas
des faux positifs : `TIM-VENUS3-DB` est en **Average « High memory
utilization »** — 8 Go pour le serveur de base du RIS, déjà relevé à
l'inventaire — et le `D:` de `.63` reste au-dessus de 90 % même après purge.

> **Attention en cas de changement de macro.** Neutraliser le palier d'un
> déclencheur déjà en problème remet bien le déclencheur à l'état normal, mais
> **ne referme pas l'événement ouvert** : Zabbix ne génère pas d'événement OK
> sur un simple changement de configuration. Il faut recharger le cache
> (`zabbix_server -R config_cache_reload`) et, si le problème persiste,
> le fermer une fois à la main.

---

## Diagnostic

```bash
# état du service (depuis un nœud)
ssh root@10.40.0.60 'systemctl status zabbix-server zabbix-agent2 nginx mariadb'
ssh root@10.40.0.60 'tail -20 /var/log/zabbix/zabbix_server.log'
# chaîne publique sans dépendre du DNS
curl -sS --resolve zabbix.teleimagerie.net:443:57.130.34.122 -o /dev/null -w '%{http_code}\n' https://zabbix.teleimagerie.net/
# trapper depuis l'extérieur
nc -zv 57.130.34.122 10051
# vue interne
ssh root@10.40.0.60 'getent hosts zabbix.teleimagerie.net'   # attendu : 10.40.0.10
# où tourne le CT
ha-manager status | grep 204   # (après ajout HA)
```

---

## Supervision du cluster — depuis le 29/08/2026

Le point 3 de [06 §4](06-reste-a-faire.md#4-supervision---traité-le-29082026-reste-la-sonde-externe) est traité : Zabbix
supervise le cluster qui l'héberge, par **l'API PVE en HTTPS**, avec un token
**lecture seule** :

> ⚠️ **Le chemin a changé le 31/08/2026.** À la mise en service, tout passait
> par le **chemin public** (le CT sortait en NAT `57.130.34.122` vers `:8006`,
> alors ouvert à tous). Depuis les overrides Unbound `pveN.infra → 10.40.0.x`,
> le CT 204 résout en privé et interroge les nœuds **directement sur le VLAN
> 400** — meilleur (plus d'épingle à cheveux publique, plus de risque de
> bannissement fail2ban de `.122`), mais **conditionné à une règle explicite** :
> `IN ACCEPT -source 10.40.0.60 -p tcp -dport 8006`, placée **avant** le
> `IN DROP -source 10.40.0.0/24` de `cluster.fw`, sinon elle est avalée et
> **toute la supervision du cluster s'éteint en silence**. Constaté le 31/08 :
> la supervision est tombée à la seconde où les overrides ont pris effet.
> Depuis la fermeture publique du 01/09, c'est la **seule** voie d'accès de
> Zabbix à l'API.

- principal `zabbix@pve`, rôle `PVEAuditor` sur `/`, token
  `zabbix@pve!monitoring` (privsep 0). Le secret ne vit **que** dans la macro
  secrète `{$PVE.TOKEN.SECRET}` de l'hôte `cluster-pve` — révocable par
  `pveum user token remove zabbix@pve monitoring` ;
- provisioning par l'API Zabbix : jeton nommé `provisioning` (rattaché à
  `supportTIM`, visible et révocable dans *Users → API tokens*), stocké dans
  `/root/.zbx-api-token` du CT. Script rejouable :
  [scripts/zabbix-provision-pve.py](scripts/zabbix-provision-pve.py).

### Ce qui est surveillé

| Vue | Source | Contenu |
|---|---|---|
| Cluster | template officiel **Proxmox VE by HTTP** (hôte `cluster-pve`) | quorum, API, découverte des 3 nœuds (CPU, RAM, load, iowait, FS racine, swap, réseau), stockages, **les 7 VM/CT** (statut, CPU, RAM, disque LXC, réseau) |
| Ceph | template maison **TIM Cluster PVE** (`/cluster/ceph/status`, même token) | `HEALTH_*`, OSD up/in/total |
| Nœuds (indépendant du point d'entrée API) | simple checks | `:8006` joignable sur chaque nœud |
| Invités (vue interne) | **agents dans les 7 invités** | Linux by Zabbix agent (201, 202, 203, 101, 102, 204) · FreeBSD by Zabbix agent (OPNsense, plugin `os-zabbix7-agent`, écoute `10.40.0.1:10050` seule) |
| Certificats | 9 hôtes `cert-*`, template Website certificate by Zabbix agent 2 | zabbix, auth, pacs-secours, odoo, syngo, headscale + `pveX:8006` — expiration < 14 j |
| Sauvegardes | template TIM (API PVE par nœud + API PBS, token `zabbix@pbs!monitoring`) | échec **et absence** de vzdump, verify/GC/prune PBS — [§ dédié](#supervision-des-sauvegardes--depuis-le-30082026) |

Tableau de bord **« Cluster PVE »** (partagé) : état instantané (quorum, Ceph,
OSD, API) + problèmes, graphes nœuds, stockage, invités vus par l'API, FS et
charge vus par les agents, échéances des certificats. Depuis le 30/08/2026,
les invités figurent aussi dans les deux tableaux **« Top hosts by CPU
utilization » et « Top hosts by RAM utilization » de « Global view »**, mêlés
à la flotte historique (groupe « Infrastructure PVE » ajouté à ces deux
widgets seulement, limite d'affichage relevée à 20 lignes — 11 hôtes
éligibles, les invités idle passaient sous la coupe des 10 par défaut).
OPNsense n'y apparaît pas : son agent FreeBSD nomme ses items autrement ; sa
santé est sur le tableau de bord « Cluster PVE ». Les tableaux de bord vivent
dans la base : couverts par le dump 01:15 + PBS 02:00.

### Alertes (mail = High/Disaster via « ALERTE HAUTE » → support@ + mcapon@)

**Partent en mail** : quorum perdu · API PVE injoignable · nœud hors-ligne ·
`:8006` injoignable par nœud · VM/CT arrêté · `HEALTH_ERR` (Disaster) · OSD
down/out · **vm-storage ≥ 85 %** (nearfull — le template officiel pré-alerte
en Warning à 80) · mémoire nœud ≥ 90 % · mémoire invité ≥ 95 % (sauf VM 100 et 102 : faux
signal hyperviseur, voir les pièges ci-dessous) · disque LXC
≥ 90 % · FS des VM (`pbs` dont `/mnt/datastore/tim`, `odoo`) ≥ 90 % ·
certificat < 14 j ou invalide · tâche vzdump en échec ou sauvegarde absente ·
verify/GC/prune PBS en échec ou absents
([§ sauvegardes](#supervision-des-sauvegardes--depuis-le-30082026)). **Tableau de bord seulement** : CPU/RAM/swap
élevés, `HEALTH_WARN` (état *attendu* pendant une perte de nœud — le
« nœud hors-ligne » a déjà sonné), redémarrages, agent injoignable (l'arrêt
de l'invité sonne déjà via l'API).

**Chaîne validée en réel le 29/08** : seuil nearfull abaissé temporairement →
problème High à 19:40:29 → **mails partis vers support@ et mcapon@** (statut
`sent`, zéro erreur) → seuil restauré → problème résolu.

### Pièges propres à ce montage

- **fail2ban `proxmox`** (5 échecs → ban 1 h, pas d'ignoreip) : un token PVE
  invalide dans Zabbix bannirait `57.130.34.121` = toute la sortie VLAN 400.
  Toujours valider un nouveau token par `curl` **avant** de le poser en macro.
  Vérifié : 0 ban après le déploiement.
- **Le template n'interroge que pve1** (`{$PVE.URL.HOST}`) : si pve1 meurt,
  « API service not available » sonne mais la vue cluster est aveugle le temps
  de la bascule — les simple checks `:8006` par nœud et les agents internes
  restent, eux, indépendants.
- **Piège n° 32 sur les checks de certificats** : les 2 premières minutes des
  hôtes `cert-*` (avant la pose de `{$CERT.WEBSITE.IP}`) ont visé la VIP
  `.122` et vu le certificat de la GUI OPNsense — fausse alerte « invalid »
  réelle reçue par mail. L'IP de connexion est forcée à `10.40.0.10`/`.30`.
- **VM FreeBSD sans balloon** : l'hyperviseur voit la RAM d'OPNsense toujours
  pleine → le trigger « high memory usage » de la VM 100 est **désactivé**
  (faux signal structurel) ; la mémoire réelle est suivie par l'agent interne.
- **VM pbs : le cache disque gonfle la vue hyperviseur.** PBS garde ~7 Gio de
  cache de pages (réellement utilisés dans la VM : ~0,5 Gio, `available`
  ≈ 7,3 Gio) → `mem/maxmem` oscille autour de 95 % et le trigger « high memory
  usage » **bagotait** (5 cycles problème/résolu le 31/08 après le redémarrage
  de la VM, mails reçus). **Neutralisé le 31/08/2026** par macro contextuelle
  `{$PVE.VM.MEMORY.PUSE.MAX.WARN:"qemu/102"}` = `100` sur `cluster-pve`
  (expression résolue vérifiée `>100`, inatteignable — les autres VM restent
  à 95). Préféré au « désactivé » d'OPNsense : la macro garde l'intention et
  le seuil visibles. Les deux méthodes survivent aux migrations — la
  découverte **renomme** ses entités sans les recréer (constaté : le trigger
  désactivé de la VM 100 a suivi pve2 → pve3). La mémoire réelle de PBS reste
  surveillée par l'agent interne de l'hôte `pbs` (seuil 95 %), le datastore
  par le trigger FS ≥ 90 %.
- La règle `tcp/10050 depuis 10.40.0.60` a été ajoutée au firewall dédié de
  la VM PBS ([configs/firewall-102-pbs.fw](configs/firewall-102-pbs.fw)) ; ufw
  d'odoo autorise la même source.
- Le dépôt `pbs-enterprise` (sans abonnement) fait échouer `apt update` sur
  PBS — tolérer l'erreur (`|| true`) pour installer depuis les autres dépôts.

## Supervision des sauvegardes — depuis le 30/08/2026

Les mails vzdump (« backup successful ») arrivaient en spam — envoi direct par
le Postfix local des nœuds, expéditeur `root@pveN`, PTR OVH, IP hors SPF — et
la décision a été plus radicale que « réparer le mail » : **plus aucun mail de
succès**. Zabbix détient l'information et alerte en cas de problème ; le mail
direct ne subsiste qu'en filet de secours, filtré sur les erreurs.

Tout est posé par [scripts/zabbix-provision-backups.py](scripts/zabbix-provision-backups.py)
(script frère de `zabbix-provision-pve.py`, mêmes helpers, idempotent) dans le
template **TIM Cluster PVE**.

### Ce que Zabbix voit

- **vzdump** : 1 item HTTP par nœud sur
  `/api2/json/nodes/{n}/tasks?typefilter=vzdump&source=archive&limit=50`
  (token `zabbix@pve!monitoring` existant, macro réutilisée à l'identique —
  zéro risque fail2ban). **Pas `/cluster/tasks`** : sa liste « récente » n'a
  aucune garantie de couverture ni de champ `status`. Le champ `id` de la
  tâche discrimine les jobs : `""` = job quotidien 02:00, `"102"` = hebdo
  samedi 03:30 — un vzdump manuel (`id=<vmid>`) ne rafraîchit donc pas l'âge
  du quotidien. L'âge du hebdo est replié en `min()` des 3 nœuds (la VM 102
  migre).
- **PBS** : 3 items HTTP sur
  `{$PBS.URL}/api2/json/nodes/localhost/tasks?typefilter=<type>&limit=20` avec
  `garbage_collection`, `verificationjob`, `prunejob` — le typefilter est un
  « contains », ces valeurs excluent les GC/verify/prune **manuels** : on suit
  les jobs planifiés. Header `PBSAPIToken={$PBS.TOKEN.ID}:{$PBS.TOKEN.SECRET}`
  (séparateur **`:`**, pas `=` comme PVE). Vérification TLS désactivée sur ces
  items (certificat auto-signé, flux interne VLAN 400 — assumé).

### Déclencheurs (tous High → mail via « ALERTE HAUTE », rien changé à l'action)

| Déclencheur | Expression (idée) | Fenêtre |
|---|---|---|
| tâche vzdump en échec (par nœud) | nb de tâches `status ≠ OK` < 26 h `> 0` | 26 h glissantes, manuelles comprises (`WARNINGS:` compte) |
| quotidien absent (par nœud) | âge du dernier succès du job > **26 h** | 02:00 + marge ; `or nodata(3h)` — sans lui, un item cassé gèlerait `last()` et l'absence deviendrait invisible |
| hebdo VM 102 absent (cluster) | `min()` des âges > **8 j** | samedi 03:30 + marge |
| verify / GC / prune PBS en échec | dernier verdict `≠ "OK"` | se referme au succès suivant (pas de fenêtre qui traîne) |
| verify / GC absents | âge du dernier succès > **8 j** | dimanche 04:00 / 05:30 |
| prune absent | âge > **26 h** | quotidien 03:00 |

### Accès API PBS

- principal `zabbix@pbs` + token `zabbix@pbs!monitoring`, rôle **Audit** posé
  sur l'utilisateur **et** le jeton (intersection — piège n° 26). Secret
  uniquement dans la macro secrète `{$PBS.TOKEN.SECRET}` de `cluster-pve` ;
  révocation : `proxmox-backup-manager user delete-token zabbix@pbs monitoring`.
- règle firewall ajoutée à la VM 102 : `tcp/8007 depuis 10.40.0.60`
  ([configs/firewall-102-pbs.fw](configs/firewall-102-pbs.fw)) — validée par
  curl depuis le CT 204 sur `10.40.0.20:8007` (même L2, pas de transit
  OPNsense).

### Plus aucun mail de succès — matchers PVE et PBS

Les deux systèmes de notifications (PVE 9 et PBS 4, `notification-mode
notification-system` déjà partout) sont réglés pareil, le 30/08/2026 :

- endpoint SMTP `mailjet` (`in-v3.mailjet.com:587` STARTTLS, même clé API que
  Keycloak, expéditeurs `pve@`/`pbs@teleimagerie.net` — couverts par le sender
  wildcard `*@teleimagerie.net` validé Actif) ; le mot de passe atterrit dans
  `/etc/pve/priv/notifications.cfg` (répliqué) et
  `/etc/proxmox-backup/notifications-priv.cfg` ;
- matcher `erreurs-mailjet` : `match-severity warning,error,unknown` →
  `mailjet`. vzdump succès = `info` → avalé ; échec = `error` → mail ; fencing
  = `error` → mail ; `unknown` = **system-mail** (cron/smartd forwardés à root
  par proxmox-mail-forward) → délivrés via Mailjet, ce qui règle au passage le
  résiduel Postfix sans relayhost ;
- builtin `default-matcher` **désactivé** (`disable`, origin
  `modified-builtin`). Rollback : supprimer `erreurs-mailjet` et l'override du
  `default-matcher` (le builtin réapparaît intact, cible `mail-to-root`).

Copies : [configs/notifications.cfg](configs/notifications.cfg) et
[configs/notifications-pbs.cfg](configs/notifications-pbs.cfg) (username =
placeholder). ⚠️ Les targets SMTP n'ont **ni file ni reprise** : un envoi raté
est perdu (journalisé seulement) — c'est précisément pourquoi Zabbix, qui
re-teste en continu, est le canal principal et le mail le filet.

### Vérifié le 30/08/2026

- valeurs réelles cohérentes dès la première collecte : quotidien ~19 h,
  hebdo ~42 h, GC ~15,6 h, verify ~17,2 h, prune ~18,2 h — chaque fenêtre
  validée par les vraies données ;
- tests des targets PVE et PBS : messages `sent` chez Mailjet (contrôle
  `GET /v3/REST/message` — un retour SMTP OK ne prouve rien, leçon Keycloak ;
  penser `Sort=ArrivedAt+DESC`, la liste sort en ascendant par défaut) ;
- déclencheurs testés en réel par la méthode du 29/08 (constante abaissée →
  problème High → mail → restauration).

- **SPOF OPNsense** : tous les polls sortants sortent en **`.122`** (NAT
  sortant dédié depuis le 30/08 — l'identité publique de zabbix, celle que
  les whitelists `Server=` des agents reconnaissent via le nom) et le 10051
  entrant arrive par la même VIP — une panne d'OPNsense (~2 min de bascule
  HA) aveugle la supervision, exactement la fenêtre du test 6
  ([08-opnsense.md](08-opnsense.md#points-dattention)).
- **Le monitoring ne se surveille toujours pas lui-même** : l'incident du 28/08
  le prouve. Une sonde externe minimale sur `https://zabbix.teleimagerie.net/`
  (Uptime robot ou équivalent) reste à mettre en place —
  [06-reste-a-faire.md §4](06-reste-a-faire.md#4-supervision---traité-le-29082026-reste-la-sonde-externe).
- **Il ne supervise pas non plus le cluster** : depuis le VLAN 400, les
  hyperviseurs sont inaccessibles par construction (blocages OPNsense +
  `cluster.fw`). L'étendre au cluster = patron PBS (2ᵉ carte VLAN 300), une
  décision de sécurité à part entière — point ouvert de 06 §4.
- **Items « self » via lxcfs** : l'agent local du CT voit des valeurs
  conteneur (CPU/mémoire), pas machine. Sans effet sur les hôtes distants.
- **Locale `fr_FR` absente du template Debian** (le VPS Ubuntu l'avait) :
  l'UI en français l'exige — corrigé le 29/08/2026 (`fr_FR.UTF-8` dans
  `/etc/locale.gen`, `locale-gen`, restart `php8.4-fpm`). À refaire si le CT
  est un jour reconstruit depuis le template.
- **Base sur Ceph** : latence supérieure au NVMe du VPS ; l'import de 3 Gio en
  75 s montre que c'est large. Surveiller housekeeper et *Monitoring → Queue*
  les premières semaines.
- **HDS** : un Zabbix qui détient identifiants et métriques de systèmes de
  santé relève de la même revue contractuelle que Keycloak
  ([12-architecture-hds.md](12-architecture-hds.md),
  [16-keycloak.md](16-keycloak.md#risques-et-limites)). Question documentée,
  non bloquante.
- **SSO Keycloak** : candidat SAML/OIDC — après stabilisation
  ([16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026)).
