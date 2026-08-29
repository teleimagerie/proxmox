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
| Ressources | 4 vCPU, 8 Go RAM (plafond LXC), disque 40 Go sur Ceph |
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
point ouvert de [06-reste-a-faire.md §4](06-reste-a-faire.md#4-supervision)
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
| `pacs03.teleimagerie.net` | **passif** (197 items) | 188.165.77.137 | ✅ accepte les polls depuis `.121` sans reconfiguration |
| `gestion.teleimagerie.net` | **passif** (137 items) | 51.210.24.59 | ✅ idem |
| `prod01.teleimagerie.net` | **actif** (62 items) | 37.61.243.245 | ✅ a suivi le DNS (< 4 min) |
| `WIN-SRV-TSPLUS` | **actif** (156 items) | 37.61.243.246 (TSplus, TELLIS) | ✅ a suivi le DNS (< 4 min) |
| `TIMWFMCORE` | **actif** (187 items) | 162.19.25.107 (`vps-2e178199.vps.ovh.net`) 📋 | ✅ a suivi le DNS (< 4 min) |
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

- **les 6 hôtes re-collectés < 4 min après le switch** — les 3 agents actifs
  (TSplus, prod01, TIMWFMCORE) référençaient le **nom**, et les agents passifs
  (pacs03, gestion) ont accepté les polls depuis la nouvelle source `.121`
  sans reconfiguration : la « campagne agents » redoutée n'a pas eu lieu ;
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

- [ ] **test mail depuis l'UI** (*Alerts → Media types → Test*) : le chemin
  SMTP est vérifié jusqu'à la bannière Mailjet, mais seul un envoi authentifié
  le prouve de bout en bout. Non simulable sans compte UI — et l'action
  « ALERTE HAUTE » ne notifie que High/Disaster (masque 48), un incident de
  test banal reste muet ;
- [ ] vérifier la **première sauvegarde PBS** du CT 204 (job de 02:00) puis
  **restauration de test sous l'ID 299** ([10-sauvegardes.md](10-sauvegardes.md#rejouer-le-test)) ;
- [ ] `bascule-zabbix.py ttl3600` après quelques jours de stabilité (précédent
  proxy : 3 jours) — le `revert` devient alors lent (~1 h) ;
- [ ] **résiliation du VPS** après J+7 : drainage déjà nul, mais laisser la
  fenêtre par prudence ; archivage à froid (dump + `/etc/zabbix`) vers
  `nas-vm`, `poweroff`, puis espace client OVH — et marquer `revert` caduque
  dans `bascule-zabbix.py` (précédent `bascule-3noms.py`) ;
- [ ] `CMSI-LES-HERBIERS` : hôte quasi mort (1 item), à supprimer ou réparer.

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

Le point 3 de [06 §4](06-reste-a-faire.md#4-supervision) est traité : Zabbix
supervise le cluster qui l'héberge. **Aucun changement réseau** — contrairement
à l'hypothèse « 2ᵉ carte VLAN 300 » de la doc, tout passe par **l'API PVE en
HTTPS sur le chemin public existant** (NAT `.121` → `:8006`, déjà ouvert),
avec un token **lecture seule** :

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

Tableau de bord **« Cluster PVE »** (partagé) : état instantané (quorum, Ceph,
OSD, API) + problèmes, graphes nœuds, stockage, invités vus par l'API, FS et
charge vus par les agents, échéances des certificats.

### Alertes (mail = High/Disaster via « ALERTE HAUTE » → support@ + mcapon@)

**Partent en mail** : quorum perdu · API PVE injoignable · nœud hors-ligne ·
`:8006` injoignable par nœud · VM/CT arrêté · `HEALTH_ERR` (Disaster) · OSD
down/out · **vm-storage ≥ 85 %** (nearfull — le template officiel pré-alerte
en Warning à 80) · mémoire nœud ≥ 90 % · mémoire invité ≥ 95 % · disque LXC
≥ 90 % · FS des VM (`pbs` dont `/mnt/datastore/tim`, `odoo`) ≥ 90 % ·
certificat < 14 j ou invalide. **Tableau de bord seulement** : CPU/RAM/swap
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
- La règle `tcp/10050 depuis 10.40.0.60` a été ajoutée au firewall dédié de
  la VM PBS ([configs/firewall-102-pbs.fw](configs/firewall-102-pbs.fw)) ; ufw
  d'odoo autorise la même source.
- Le dépôt `pbs-enterprise` (sans abonnement) fait échouer `apt update` sur
  PBS — tolérer l'erreur (`|| true`) pour installer depuis les autres dépôts.

## Risques et limites

- **SPOF OPNsense** : tous les polls sortants passent par le NAT `.121` et le
  10051 entrant par la VIP `.122` — une panne d'OPNsense (~2 min de bascule HA)
  aveugle la supervision, exactement la fenêtre du test 6
  ([08-opnsense.md](08-opnsense.md#risques-et-limites)).
- **Le monitoring ne se surveille toujours pas lui-même** : l'incident du 28/08
  le prouve. Une sonde externe minimale sur `https://zabbix.teleimagerie.net/`
  (Uptime robot ou équivalent) reste à mettre en place —
  [06-reste-a-faire.md §4](06-reste-a-faire.md#4-supervision).
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
