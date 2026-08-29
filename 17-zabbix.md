# `zabbix` — supervision (migration VPS → CT 204, **en cours**)

Conteneur LXC **204**, Debian 13, **Zabbix 7.0.30 LTS** (MariaDB 11.8, nginx,
PHP 8.4). Provisionné le 29/08/2026 pour reprendre le serveur de supervision
d'entreprise hébergé sur le VPS OVH `vps-41b1229b` (`51.178.36.192`,
Ubuntu 24.04, Zabbix 7.0.22, MariaDB 10.11).

> ⚠️ **État au 29/08/2026 : toute la plomberie est en place et testée, la
> bascule DNS n'est PAS faite.** `zabbix.teleimagerie.net` pointe toujours sur
> le VPS, qui reste la production. Le CT 204 porte une copie de la base
> (répétition du 29/08) avec **médias d'alerte désactivés**. Jour J : voir
> [Bascule restante](#bascule-restante--jour-j).

| | |
|---|---|
| Adresse interne | `10.40.0.60/24` (VLAN 400), passerelle `10.40.0.1` |
| Nom public | `zabbix.teleimagerie.net` — derrière **proxy-tim** (VIP `.122`), pas de VIP dédiée |
| Ressources | 4 vCPU, 8 Go RAM (plafond LXC), disque 40 Go sur Ceph |
| Accès | `ssh root@10.40.0.60` depuis un nœud (clés cluster + clé WSL de matt) |
| Haute dispo | **pas encore** — `ha-manager add ct:204` prévu après la bascule |
| UI | `https://zabbix.teleimagerie.net/` (l'ancien chemin `/zabbix/` est redirigé 301) |
| Base | `zabbix`, utf8mb4/utf8mb4_bin, **3,13 Gio** à l'audit |
| Sauvegarde | prise automatiquement par le job PBS quotidien 02:00 (`all` sauf 102) |

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

| Hôte | Mode | IP constatée (tcpdump 10051) | Après bascule |
|---|---|---|---|
| Zabbix server | passif local | 127.0.0.1 | remplacé par l'agent2 du CT |
| `pacs03.teleimagerie.net` | **passif** (197 items) | 188.165.77.137 | le poll sortira en `.121` → à whitelister dans le `Server=` de son agent |
| `gestion.teleimagerie.net` | **passif** (137 items) | 51.210.24.59 | idem `.121` |
| `prod01.teleimagerie.net` | **actif** (62 items) | 37.61.243.245 | suit le DNS si `ServerActive` = nom ⚠️ à vérifier |
| `WIN-SRV-TSPLUS` | **actif** (156 items) | 37.61.243.246 (TSplus, TELLIS) | idem ⚠️ |
| `TIMWFMCORE` | **actif** (187 items) | 162.19.25.107 (`vps-2e178199.vps.ovh.net`) 📋 | idem ⚠️ |
| `CMSI-LES-HERBIERS` | 1 item, quasi mort | pas vu en 3 min | à trancher (supprimer ?) |

Pas de proxy Zabbix, pas de traps SNMP (trapper désactivé), pas de JMX/IPMI,
répertoires `externalscripts`/`alertscripts` vides, aucun cron personnalisé.

---

## Architecture (identique au patron auth/Keycloak)

```
   navigateur / agents actifs (externe)          interne VLAN 400
            │                                          │
  DNS public : zabbix → VIP .122          Unbound : zabbix → 10.40.0.10
  (⚠️ encore 51.178.36.192 avant le jour J)            │
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

## Bascule restante — jour J

Prérequis : prévenir les intéressés (fenêtre de supervision aveugle de
quelques minutes), et avoir vérifié le `ServerActive=` des 3 agents actifs
(nom ou IP ? voir tableau — si IP en dur, les reconfigurer vers le nom
**avant**, sans risque tant que le nom pointe sur le VPS).

1. H-1 : `python3 /root/bascule-zabbix.py ttl60` (pve1) — vérifier sur
   `ns17.ovh.net`. Santé cluster (quorum, Ceph, HA).
2. Gel : sur le VPS `systemctl stop zabbix-server && systemctl disable zabbix-server`.
3. Rejouer la répétition : dump → tirage (`root@10.40.0.60` tire en
   `ubuntu@51.178.36.192`, clé `ct204-migration-temporaire`) → drop/create
   utf8mb4 → import → `UPDATE media_type SET status=1;` → start. (~3 min.)
4. Poser le drop-in `TimeoutStopSec=60` sur le CT (voir incident).
5. Vérifier : journal propre, UI interne `http://10.40.0.60:8080` (dernières
   valeurs = horodatage du gel), chaîne publique
   `curl --resolve zabbix.teleimagerie.net:443:57.130.34.122 https://…`.
6. Réactiver le média : `UPDATE media_type SET status=0 WHERE mediatypeid=1;`
   → **test mail réel reçu** (Alerts → Media types → Test).
7. `python3 /root/bascule-zabbix.py switch` → vérifier `@ns17.ovh.net`,
   `@1.1.1.1`, `@8.8.8.8` (jamais le résolveur WSL — piège 30), navigateur
   externe, `getent hosts` interne → `10.40.0.10`. Les agents actifs en « nom »
   se représentent en quelques minutes (TTL 60).
8. Post-bascule : `ha-manager add ct:204 --state started --max_restart 3
   --max_relocate 3` + bascule HA mesurée (sonde 1 s — CT 201 : 14 s,
   CT 203 : 19 s) ; dump DB quotidien interne (modèle `kc-pgdump`) ;
   restauration de test sous l'ID 299 ; `ttl3600` après quelques jours.

**Rollback (tant que le VPS existe)** : `bascule-zabbix.py revert` (~60 s)
+ `systemctl enable --now zabbix-server` sur le VPS. Seule perte : ce que le
CT a collecté entre-temps.

**Drainage avant résiliation du VPS** (précédent ancien VPS proxy) : J+7 à
J+14, `tcpdump -ni any port 10051 or port 443` sur le VPS — chaque IP encore
vue est un agent non reconfiguré. Zéro trafic + archivage à froid vers
`nas-vm` → résiliation, et marquer `revert` caduque dans `bascule-zabbix.py`.

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
