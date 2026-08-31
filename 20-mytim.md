# 20 — MyTIM sur le cluster : l'app d'abord (VM 104), MySQL ensuite (VM 103)

> 📋 **PLAN** — validé le 31/08/2026, exécution non commencée. Rien de ce qui suit n'existe encore sur les machines. Les chiffres marqués « mesuré » viennent des fiches 05/10/17/18 ; tout le reste est une attente à confirmer en répétition générale. À l'exécution, cette fiche devient le récit de l'étape 1 (app) et l'étape 2 (base) sera extraite en `21-mysql.md`.

Signalétique : ✅ vérifié/mesuré · 📋 déclaré/attendu · ⚠️ à vérifier

## Le problème que ce plan résout

La base de production de MyTIM (`timgestion`, 38 Go dont `consultation` ≈ 30 Go) tourne sur une instance managée OVH Web Cloud Database (`cm496290-001.eu.clouddb.ovh.net:35525`, Percona 8.0.46) sous-dimensionnée : 4 Go de RAM, `innodb_buffer_pool_size` **128M**, dépassements fréquents, et une sauvegarde managée à 00:58 UTC qui provoque des stalls quotidiens (documentés dans `docs/plans/plan-slow-query-optimization.md` du dépôt gestion). L'app tourne sur un VPS OVH (`ns3267715.ip-51-210-24.eu` = 51.210.24.59, Docker Compose + FrankenPHP, déployée par Ansible depuis le dépôt gestion). L'objectif : rapatrier les deux sur le cluster.

**Décisions actées le 30-31/08/2026 :**
1. **Ordre : l'app d'abord, MySQL ensuite.** Conséquence majeure : pas de tunnel WireGuard permanent — à la fin, app et base sont dans le VLAN 400 (trafic commuté L2, sub-milliseconde, il ne traverse même pas OPNsense). La phase intermédiaire (app sur cluster → base restée chez OVH) porte le risque de latence, mesuré avec seuils avant tout engagement.
2. **Base : VM unique + HA Proxmox** (pas de réplica MySQL, pas d'InnoDB Cluster). RTO panne de nœud ≈ 2 min 15 ✅ + recovery InnoDB 📋 ; RPO 0 (Ceph synchrone + durabilité complète). Maintenances sans coupure (migration à chaud ~1 s ✅).
3. **Bascule base : quasi nulle si la réplication externe depuis OVH est possible** (à vérifier en premier — improbable sur cette offre ⚠️) ; repli accepté : fenêtre nocturne ~2-3 h (dump/import parallèle).

**Budget cluster après les deux étapes** : 32 Go de RAM VM actuels + 16 (app) + 16 (MySQL) = **64 Go ≤ plafond N-1 ~100 Go** (`01-architecture.md`). Ceph : ~200 + 175 Go logiques sur ~1,22 Tio pratiques. VMID : app = **104**, MySQL = **103**. IP (convention par dizaines) : app = **10.40.0.90**, MySQL = **10.40.0.80**.

---

# ÉTAPE 1 — L'app : VPS → VM 104 `mytim`

## Architecture cible

```
Internet ──► 57.130.34.122:443 ──► routeur SNI (CT 201 proxy-tim)
             ──► 127.0.0.1:8443 ssl proxy_protocol (vhosts app + gestion)
             ──► http://10.40.0.90:80 (VM 104 : Caddy/FrankenPHP en HTTP pur)

VM 104 ──sortie NAT dédiée 57.130.34.124──► cm496290-001.eu.clouddb.ovh.net:35525
        (phase intermédiaire, jusqu'à l'étape 2)
```

| Élément | Valeur |
|---|---|
| VM 104 `mytim` | Ubuntu 24.04 noble ✅ (le provisioning Ansible le cible : pin apt `…~ubuntu.24.04~noble`, `provisioning.yaml:27`), 8 vCPU `host`, **16 Go balloon=0** (24 si la phase 0 mesure > 10 Go sur le VPS), **200 Go Ceph `vm-storage`** |
| Réseau | `net0` vmbr1 **`tag=400`** (⚠️ sans tag = bloc public), 10.40.0.90/24, gw et **DNS 10.40.0.1** (piège n° 33) |
| Publication | terminaison TLS dans proxy-tim (patron auth/zabbix/odoo — pas de passthrough) ; cert multi-SAN `app.` + `gestion.teleimagerie.net` **pré-émis en DNS-01 depuis pve1** (acme.sh + hook `deploy-app.sh`, copie de `scripts/deploy-zabbix.sh`) → **zéro fenêtre TLS au jour J** ; vhost cloné de `configs/odoo.teleimagerie.net.conf` + `client_max_body_size 512M` + bloc `/.well-known/mercure` (SSE : `proxy_buffering off`, `proxy_read_timeout 24h`) |
| Identité sortante | **VIP dédiée `57.130.34.124`** (NAT sortant hybride, patron `.122`) — l'app cumule le plus de whitelists tierces du SI ; aucune redirection entrante sur `.124` ; `.125` reste libre |
| DNS | `scripts/bascule-app.py` (copie de `bascule-odoo.py`) : `app` + `gestion` → `57.130.34.122` ; pas d'AAAA ✅ ; post-bascule overrides Unbound `app.`/`gestion.` → 10.40.0.10 (piège n° 32) |

**Petite PR applicative requise** (à valider en répétition) : passer les adresses de site Caddy en HTTP pur (`server_name: app.teleimagerie.net:80`, idem `legacy_server_name` — une adresse `:80` désactive l'auto-HTTPS de Caddy sans toucher au Caddyfile) ; séparer un `public_hostname` pour les URLs Mercure dans `env.j2` (lignes 13 et 183) ; vérifier que `REMOTE_ADDR` reste l'IP client réelle de bout en bout (proxy_protocol → X-Forwarded-For ; `TRUSTED_PROXIES` couvre déjà 10.0.0.0/8).

**Découverte d'exploration à ne pas oublier** : `./resources` (cr, exports, factures, gru, protocoles…) est monté dans tous les conteneurs, gitignoré — **c'est du vrai état fichier**, traité comme le filestore Odoo : pré-rsync + delta au gel, rsync retour en cas de rollback.

## Le risque n° 1 : latence app(cluster) → clouddb(OVH)

1. Whitelist de `.124` sur le panel OVH clouddb **avant toute mesure** (garder l'IP du VPS jusqu'à résiliation).
2. Mesures symétriques VPS vs cluster : RTT TCP vers `:35525` ; boucle PDO `SELECT 1` × 50 (min/p50/p95) ; TTFB de 3 pages étalons (1 Symfony + 2 legacy « bavardes ») ; `SHOW SESSION STATUS LIKE 'Ssl_cipher'` (connexion actuelle probablement en clair ⚠️ — aucun `MYSQL_ATTR_SSL_*` dans le code ✅).
3. **Seuils go/no-go** : RTT cluster→clouddb ≤ RTT VPS→clouddb **+1 ms** ET ≤ **3 ms absolu** ; p50 boucle PDO ≤ 2× la référence ; TTFB étalons ≤ +25 %. No-go → on ne bascule pas et on rediscute l'ordre. Pas de zone grise.
4. TLS MySQL sur ce trajet public : si clouddb l'offre (`have_ssl=YES`), l'activer coûte peu (options PDO doctrine + `load_env.php`) ; sinon, acceptation documentée (exposition identique à aujourd'hui, l'étape 2 éteint le sujet).

## Whitelists tierces (IP à déclarer : 57.130.34.124)

| Service | Action |
|---|---|
| **OVH clouddb** (critique) | panel/API `/hosting/privateDatabase/…/whitelist` — en premier |
| **SFTP GRU** 81.255.38.171 (`gru-sftp-dry-run.md:14` : seule l'IP prod est autorisée ✅) | demande au partenaire à **J-14** (délai tiers) ; validation `app:gru:sftp:dry-run` |
| Venus API (`allowed_ips` côté serveur Venus), PACS TELLIS (pfSense), ITIS/Deeplink (mTLS + IP ?⚠️), Xplore HDS ⚠️, 3CX, fiche PISTE Chorus Pro ⚠️ | vérifier/demander un par un |
| Mailjet / SPF / DKIM | **rien** — l'app envoie via Mailjet, pas en direct ✅ |

## Déroulé

**Phase 0 — relever la réalité du VPS** (specs inconnues ⚠️) : `nproc`, `free`, `df`, `docker stats`, `du -sh /srv/gestion/resources`, crontabs (ubuntu + root + rappro), profondeur des files RabbitMQ, mémoire Redis, durée du mysqldump nocturne, logs Caddy sur le Host `d69eeb3e.teleimagerie.net` (rôle inconnu ⚠️, suppression probable), et les mesures de latence ci-dessus.

**Répétition — sur la VM cible elle-même** (pas de migration du staging) :
1. VM 104 + provisioning Ansible rejoué tel quel + VIP `.124` + mesures de latence ;
2. déploiement `deploy_env=staging` (autoporteur : DB conteneur, Mailpit) avec la PR Caddy-HTTP → prouve le build complet (php + ~26 workers + solver + playwright) ;
3. vhost `app.staging` + cert sur le CT 201, tests par `curl --resolve` **sans toucher au DNS public** → prouve la chaîne VIP→SNI→vhost→VM, le **login OIDC réel** (le client `mytim-staging` a déjà le bon callback, `16-keycloak.md`), Mercure, l'IP client réelle, l'upload 256 Mo ;
4. destruction/recréation de la VM (~30 min) pour repartir vierge ;
5. **J-1** : déploiement `prod` puis **arrêt immédiat** des conteneurs (deux schedulers sur la même base = doubles envois !), purge des files RabbitMQ de test, pré-rsync de `resources/`.

**Bascule** (coupure cible ≤ 10 min — la base ne bouge pas : rollback sans perte de données métier) :

| H | Action |
|---|---|
| H-1 | `bascule-app.py ttl60` + vérif sur la paire autoritaire OVH |
| H+0 | gel : `compose stop php` sur le VPS + **neutraliser la crontab** (sinon le dump de 23:30 repartirait du VPS) |
| H+1→5 | **drain RabbitMQ** (`list_queues` en boucle, timeout 5 min ; files non vides = GO avec perte documentée ou NO-GO) puis stop complet |
| H+5 | rsync delta `resources/` VPS→VM (`--delete`) |
| H+6 | `up -d` sur la VM ; `curl -H 'Host: app.teleimagerie.net' http://127.0.0.1` → 200/302 ; consumers visibles |
| H+7 | `bascule-app.py switch` — fin de coupure ≈ H+8 (TTL 60, zéro fenêtre TLS) |
| H+8 | overrides Unbound (sauvegarde `config.xml` préalable) ; puis vérifications : login OIDC depuis l'extérieur (4G), page legacy, SSE Mercure > 2 min, upload, IP réelles dans les logs, `gru:sftp:dry-run`, tick scheduler, mail Mailjet réel, latence étalons dans les seuils |

**Rollback (~3 min, tant que le VPS existe)** : `bascule-app.py revert` + `up -d` sur le VPS + restaurer sa crontab + rsync retour du delta `resources/` + retirer les overrides Unbound.

**Observation J+1→J+3** (flux tiers asynchrones : GRU, facturation, Chorus) puis : `ttl3600`, `ha-manager add vm:104 --state started --max_restart 3 --max_relocate 3`, migration à chaud de validation sous sonde, dump 23:30 vérifié depuis la VM, agent Zabbix + hôtes `cert-app`/`cert-gestion`, extinction puis résiliation du VPS, suppression de `d69eeb3e` si confirmé mort, retrait de l'IP VPS des whitelists.

---

# ÉTAPE 2 — MySQL : clouddb OVH → VM 103 `mysql-tim`

Simplifiée par l'étape 1 : app et base dans le même VLAN 400, **un seul point de bascule** : `frankenphp/ansible/group_vars/tim/prod/vars.yaml:8-11` ✅ → `mysql_host: 10.40.0.80`, `mysql_port: 3306` (user/password/database inchangés, secret vaulté conservé).

## Cible

- **VM 103** : Debian 13 (repli 12 si paquets absents ⚠️), 6 vCPU `host`, **16 Go balloon=0**, 25 + **150 Go Ceph** (`/var/lib/mysql` + `/var/backups/mysql`, `iothread=1`, `discard=on`), tag=400, 10.40.0.80, HA. Placement initial : nœud ne portant pas OPNsense. Jamais sur `nas-vm` (`01-architecture.md`).
- **Percona Server for MySQL 8.4 LTS natif** (dépôt `percona-release`, composant `ps-84-lts`) : 8.0 est EOL depuis avril 2026 ; Doctrine annonce déjà `serverVersion=8.4.0` ✅ ; même lignée que la source (Percona 8.0.46-37) ; XtraBackup + percona-toolkit dans le même dépôt. MariaDB exclu (7 tables `utf8mb4_0900_ai_ci` ✅). **Plan B décidable en répétition** : Percona 8.0 si blocage 8.4.
- `bind-address = 10.40.0.80,127.0.0.1` ; comptes : `timgestion-admin`@`10.40.0.90` (mêmes identifiants qu'OVH), admin local, `backup`@localhost, `zbx_monitor`@localhost. Vues `TIM_V_*` : réécrire le `DEFINER=teleimagaamcapon` par `sed` sur les DDL à l'import (pas de recréation de l'utilisateur orphelin).

## my.cnf (points clés — fichier complet à archiver dans `configs/my.cnf-vm103`)

| Paramètre | Valeur | Pourquoi |
|---|---|---|
| `sql_mode` | `NO_ENGINE_SUBSTITUTION` | **conserver le mode non strict** — l'app legacy en dépend ; le strict est un chantier séparé, jamais le jour d'une migration |
| `innodb_buffer_pool_size` | **10G** (OVH : 128M !) → 12G après observation | la raison d'être de la migration |
| `innodb_redo_log_capacity` | 2G | rafales LONGTEXT/JSON ; compromis avec la durée de recovery (mesurée en répétition) |
| `innodb_flush_log_at_trx_commit` / `sync_binlog` | 1 / 1 | durabilité complète — données de santé, on n'« optimise » pas |
| `max_connections` / `max_allowed_packet` | 300 / 256M | ~24 conteneurs + marge / blobs `consultation_data` (OVH : 100 / 8M) |
| `event_scheduler` OFF, `local_infile` ON, timeouts 600 | iso OVH | durcissement éventuel post-observation |
| binlog + `binlog_expire_logs_seconds=604800`, `gtid_mode=ON` | 7 j | **PITR : RPO ~0 contre 24 h aujourd'hui** |
| `slow_query_log=ON`, `long_query_time=1`, `log_slow_extra` | local | remplace le pull SFTP OVH (10 s = presque aveugle) |
| `restrict_fk_on_non_standard_key` | OFF | nouveau défaut 8.4 incompatible avec un schéma legacy ; inventaire des FK fautives en répétition |
| `log_bin_trust_function_creators` | **ne pas reporter** | variable supprimée en 8.4 (refus de démarrage) ; routines importées par un compte admin |
| `lower_case_table_names`, `default_time_zone` | lire chez OVH **avant** l'init du datadir | se figent à l'init / `CONVERT_TZ` utilisé en DQL → charger `mysql_tzinfo_to_sql` |

Garde-fous systemd posés dès la construction (transposition du piège Zabbix, `17-zabbix.md`) : drop-in `TimeoutStopSec=600` sur mysql.service (jamais `infinity`) + needrestart interdit de redémarrer mysql automatiquement.

## Sauvegardes (3 niveaux + hors cluster)

| Niveau | Quoi | Quand | Rétention |
|---|---|---|---|
| 0 | binlog (PITR) | continu | 7 j |
| 1 | mysqldump `--single-transaction --quick --hex-blob` **`--routines --events --triggers`** + zstd (timer systemd) | 01:15 (patron Odoo/Zabbix/Keycloak) | 3 locaux |
| 1bis | rsync vers **rappro** (46.105.64.17), motif `tim-dump-*` | après le dump | GFS 14 j/8 sem/12 mois inchangée |
| 2 | vzdump → PBS → NAS Roubaix + snapshots ZFS immuables | 02:00 (job `all=1`, automatique) | ~8 mois |

Corrections vs le script actuel (`mysql-dump.sh:70-81` ✅) : `--routines --events --triggers` absents aujourd'hui (**les routines ne sont dans aucune sauvegarde**), vues `TIM_V_*` exclues à réintégrer, zstd au lieu de gzip -9. Supervision par exception (Zabbix) : déclencheur « fraîcheur du dernier dump > 26 h », pas de mail de succès.

## Déroulé

**Phase 0** : ① ticket + test OVH : réplication externe possible ? → détermine le mode de bascule ; ② paquets Percona 8.4/Debian 13 ; ③ `ceph df` ; ④ whitelist de la sortie NAT côté clouddb pour le dump direct ; ⑤ fenêtre validée avec le métier (la nuit n'est pas creuse en téléradiologie de garde).

**Inventaire source** (archivé dans `configs/ovh-clouddb-variables-<date>.txt`) : `SHOW GLOBAL VARIABLES` complet ; **routines/events/triggers** (absents des dumps !) ; vues + DEFINER ; moteurs/collations (les 8 MyISAM latin1 migrent tels quels — conversion InnoDB = chantier post-migration) ; plugin d'auth du compte applicatif.

**Répétition générale** : dump réel mydumper 4 threads (de nuit, l'instance subit déjà le stall de 00:58) → `sed` DEFINER → import myloader 6 threads (durabilité relâchée le temps de l'import). Objectif **import ≤ 30 min** 📋 (repère ✅ : 3 Gio en 75 s sur Ceph, `17-zabbix.md`). Contrôles : COUNT par table, checksums ciblés, vues/routines, `CONVERT_TZ`, connexion test depuis la VM 104. Crash-test : arrêt brutal → **recovery InnoDB < 3 min** 📋 (sinon réduire le redo log). Staging pointé sur la cible : P95 des écrans clés ≤ +20 %.

**Bascule** :
- *Si réplication possible* : seed + réplication GTID 8.0.46→8.4 (sens supporté), arrêt app, catch-up (secondes), switch config — **fenêtre ~10 min**.
- *Sinon (fenêtre nocturne annoncée 3 h, visée ≤ 1 h 30)* : gel de l'app (`compose down` sur la VM 104) → dump final (source sans écritures) → import → contrôles → bascule `vars.yaml` + `ansible-playbook -l tim_prod playbooks/deploy.yaml` → smoke tests → réouverture. `mysql_version: 8.4` réaligné dans `group_vars/default/vars.yaml:15`.
- **Rollback à tout moment** : revert git + redéploiement (~10 min) — l'instance OVH n'a pas bougé.

**Observation J+1→J+14** (OVH en filet froid) : P95, slow.log, volume binlog, RAM (buffer pool → 12G si marge) ; preuves de restauration (qmrestore en VM 299, restauration de dump, **drill PITR chronométré**) ; migration à chaud sous trafic réel.

**Décommissionnement (J+14, le vrai point de non-retour)** : dump d'archive final → rappro + copie froide nas-vm ; retrait des crons `ovh-db-dump-fetch` (rappro) et `pull-slow-query-log` ; purge des secrets API OVH DB vaultés ; retrait des whitelists clouddb ; résiliation `cm496290-001`.

---

## Documents et modifications prévus

Dépôt proxmox : cette fiche (récit + runbooks à l'exécution), `21-mysql.md` (extraction étape 2), `configs/app.teleimagerie.net.conf` + vhost gestion, `configs/my.cnf-vm103`, `configs/ovh-clouddb-variables-<date>.txt`, réexports `ha-resources.cfg`, `scripts/bascule-app.py`, `scripts/deploy-app.sh`, `scripts/mysql-dump-vm103.sh` (+ unités systemd) ; mises à jour : `01-architecture.md` (allocations .80/.90), `08-opnsense.md` (VIP .124, NAT hybride, overrides Unbound), `14-noms-de-domaine.md` (sort de `d69eeb3e`), `06-reste-a-faire.md` (chantiers ouverts : MyISAM→InnoDB, sql_mode strict, réplica éventuel, CARP), `README.md` (sommaire).

Dépôt gestion : PR étape 1 (`server_name`/`legacy_server_name` en `:80`, `public_hostname` dans `env.j2`, inventaires `hosts.ini`/`hosts.yaml` → 10.40.0.90 avec ProxyJump root@pve1) ; étape 2 : `vars.yaml:8-11` (**LE** changement), script de dump corrigé, dépréciations (`ovh-db-dump-fetch`, `deploy-ovh-db-dump.yaml`, `pull-slow-query-log.sh`), nouveau `docs/technique/mysql-cluster.md`. Hygiène hors chemin critique : révoquer les identifiants en clair de `legacy/` (dbconfig.php, db.inc.php, facture/config.php…) et `frankenphp/scripts/cron_crm` — ils sont dans l'historique git.

## Risques et limites

1. **Latence intermédiaire app→clouddb** (étape 1) : seuils chiffrés avant engagement, rollback trivial (base partagée), horizon court (étape 2 planifiée).
2. **Whitelist tierce oubliée** : pannes asynchrones et silencieuses (GRU qui ne dépose plus, Venus en 403, PACS muet) → inventaire, tests dédiés au runbook, 3 jours d'observation avec le canal d'erreurs.
3. **OPNsense devient le SPOF total de MyTIM** (entrant `.122`, sortant `.124`, DNS) : panne du nœud porteur = ~2 min d'indisponibilité (HA relance). Le VPS n'a pas ce mode de panne aujourd'hui. Assumé, comme pour les services existants ; CARP = parade future.
4. **Messages Messenger en vol** à la bascule app : drain borné 5 min, critère GO/NO-GO explicite, perte résiduelle sur décision documentée.
5. La HA Proxmox ne couvre ni la corruption logique ni l'erreur humaine → chaîne PITR/dump/PBS/ZFS immuable + drills chronométrés.
6. **8.4 sur app legacy** : risque résiduel malgré la répétition ; plan B 8.0 décidable en répétition, pas le jour J.
7. Une panne cluster couche désormais l'IdP (Keycloak) **et** l'app ensemble — pas de dépendance circulaire (formulaire local en repli), comptes de secours Proxmox.
8. Perte d'un nœud = Ceph durablement dégradé (topologie 3 nœuds, pas d'auto-guérison) jusqu'au retour du nœud.
9. HDS : la base rejoint le périmètre du cluster (`12-architecture-hds.md`) ; chiffrement PBS et chiffrement au repos InnoDB non prévus — même statut que Keycloak/Zabbix, documenté.

## Ce qui devra être mesuré (récapitulatif « mesuré, pas déduit »)

Étape 1 : specs et charge réelles du VPS · RTT/boucle PDO/TTFB étalons VPS vs cluster · taille de `resources/` et durée du rsync · durée du drain RabbitMQ · coupure réelle à la bascule DNS.
Étape 2 : durée mydumper 38 Go depuis OVH · durée myloader parallèle · P95 staging pointé · recovery InnoDB après arrêt brutal · durée dump 01:15 + zstd + rsync rappro · 1ᵉʳ vzdump plein de la VM chargée · volume binlog quotidien · gel réel de la migration à chaud sous charge.
