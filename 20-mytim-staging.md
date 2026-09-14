# Pré-productions MyTIM / MyISOTEAM — VM 103 et 104

Les deux pré-productions de l'application de gestion (dépôt `teleimagerie/gestion`,
Symfony 7.4 / FrankenPHP en Docker Compose) tournent depuis le **14/09/2026** sur
le cluster, derrière [proxy-tim](09-proxy-tim.md). Elles remplacent deux
**serveurs dédiés OVH** identiques et très surdimensionnés (AsrockRack B650D4U,
EPYC 4244P 6c/12t, 30 Go, 2 × NVMe 960 Go RAID1, 714 jours d'uptime, ~3 Go de
RAM réellement utilisés) : `ns3240118.ip-79-137-100.eu` (`79.137.100.185`,
`tim-staging`) et `ns3240079.ip-79-137-100.eu` (`79.137.100.184`,
`isoteam-staging`).

| | VM 103 `mytim-staging` | VM 104 `myisoteam-staging` |
|---|---|---|
| Rôle | staging TIM (`BASE_SITE=tim`) | staging Isoteam (`BASE_SITE=isoteam`) |
| Adresse | `10.40.0.80/24` (`vmbr1` **tag 400**), gw + DNS `10.40.0.1` | `10.40.0.90/24`, idem |
| Ressources | 2 vCPU `host`, 8 Go (sans ballooning), 100 Go Ceph `vm-storage`, `onboot` | idem |
| OS | Ubuntu 24.04 cloud-init (`noble-server-cloudimg-amd64.img` de `nas-vm`), `qemu-guest-agent` | idem |
| Noms publics | `app.`, `gestion.` (legacy), `mailer.` (Mailpit) `.staging.teleimagerie.net` | `.staging.isoteam.mn` |
| Alias 301 | `app-staging`, `gestion-staging` | `app-staging`, `gestion-staging`, `preprod-app`, `preprod-gestion` |
| Base | MySQL 8.4 en conteneur, **copie de la prod** (dump OVH du 14/09/2026, 27 Go) | MySQL 8.4 en conteneur, reprise de l'ancien staging (500 Ko) |
| HA | **aucune** — c'est du staging (décision du 14/09/2026) | idem |
| Sauvegarde | **hebdomadaire, une seule copie** (dimanche 03:00, `keep-last=1`, exclues du job quotidien) — [10-sauvegardes.md](10-sauvegardes.md) | idem |
| Supervision | agent Zabbix 2 (7.0.30) passif + découverte PVE + `cert-staging-tim` — [17-zabbix.md](17-zabbix.md) | idem, `cert-staging-isoteam` |

**Choix structurants**, repris de la [migration Odoo](18-odoo.md) : VM QEMU plutôt
que CT (Docker), Ubuntu 24.04 identique à la source (le provisioning Ansible du
dépôt applicatif se rejoue tel quel), une VM par tenant (l'Ansible suppose
`/srv/gestion` et les ports 80/443 par hôte). **Ce qui diffère d'Odoo** : pas de
HA, sauvegarde minimale, dimensionnement léger — un staging n'a besoin ni de la
disponibilité ni de la rétention de la production.

---

## Ce que faisaient les dédiés OVH (relevé du 14/09/2026)

Une seule chose : le projet Compose `gestion` (`compose.yaml` + `compose.prod.yaml`,
profil `staging`). Sur `.185` : `php` (FrankenPHP + Caddy, image construite **sur
le serveur**, 31 Go), deux workers Messenger (`notifier`, `priority`),
`database` (MySQL 8.4, base `tim` de 27 Go, volume de 52 Go dont 8 Go de
binlogs), `rabbitmq`, `redis`, `mailer` (Mailpit, capture tous les mails).
Sur `.184` : idem sans worker, base de 300 Mo.

Hors Docker : sshd, fail2ban, ufw, un cron `docker system prune` hebdomadaire.
**Aucune sauvegarde**, pas de VPN. Une seconde carte vRack (`192.168.163.10/.11`)
sans aucun voisin. Une règle ufw `5002/tcp` orpheline.

Points relevés au passage : `database` publiait `0.0.0.0:3306` (Docker contourne
ufw — joignable d'Internet, aucune connexion externe constatée) ; le dépôt
`gestion` ne référençait ces serveurs que par leur reverse OVH
(`ns3240118.ovh.net`, `ns3240079.ovh.net`) dans les deux inventaires Ansible ;
**rien d'externe n'appelle un staging** (PACS, agent DICOM, Xplore, 3CX visent la
prod). La base de staging était une copie de la prod (dump déposé à la main
dans `frankenphp/initdb.d/` sur volume neuf — procédure non documentée, désormais
dans `docs/technique/staging-proxmox.md` du dépôt).

---

## Architecture retenue

```
Internet ── 57.130.34.122 (VIP proxy-tim) ── rdr OPNsense ── CT 201 nginx
        routeur SNI :443 → 127.0.0.1:8443 ssl proxy_protocol
        vhost staging.teleimagerie.net.conf : TLS terminé, X-Forwarded-Proto https
                │ HTTP clair
                ▼
        VM 103 10.40.0.80:80  Caddy (FrankenPHP)  → app / legacy / Mailpit
```

**Côté dépôt `gestion`** (commit `0d2720a5` sur `feat/staging-proxmox`,
cherry-pick `47c8cdd7` sur `staging`) : un drapeau Ansible **`behind_tls_proxy`**
(vrai dans `group_vars/{tim,isoteam}/staging/vars.yaml`, faux ailleurs — rendu
prod vérifié byte pour byte identique) fait deux choses dans `env.j2` :

- `SERVER_NAME`, `LEGACY_SERVER_NAME`, `MAILPIT_SERVER_NAME` préfixés `http://`
  → Caddy sert ces vhosts **en HTTP, sans ACME ni redirection** (préfixer un
  site par `http://` est le mécanisme Caddy pour désactiver l'auto-HTTPS site
  par site) ;
- `SYMFONY_TRUSTED_PROXIES=private_ranges` → Symfony honore `X-Forwarded-Proto`
  et `X-Forwarded-For` du proxy (`framework.trusted_proxies` lit cette variable
  par défaut en 7.x) : `isSecure()`, URLs absolues, `redirect_uri` OIDC et IP
  client réelle.

Les inventaires pointent sur `10.40.0.80/.90` avec
`ProxyJump=root@pve1.infra.teleimagerie.net` (VPN nomade requis), et
`provisioning.yaml` ouvre `10050/tcp` depuis `10.40.0.60` (variable
`zabbix_server_ip` du groupe `staging`).

**Certificats** : deux wildcards **DNS-01 depuis pve1** (`acme.sh`, clé API OVH
qui ne quitte pas l'hyperviseur — HTTP-01 ne sait pas émettre un wildcard),
`*.staging.teleimagerie.net` (+ SAN `app-staging`, `gestion-staging`) et
`*.staging.isoteam.mn` (+ 4 alias), déployés vers
`/etc/nginx/certs/staging-{teleimagerie,isoteam}/` du CT 201 par les hooks
[scripts/deploy-staging-teleimagerie.sh](scripts/deploy-staging-teleimagerie.sh)
/ [`-isoteam.sh`](scripts/deploy-staging-isoteam.sh), renouvelés par
`acme-renew.timer`. Vhosts :
[configs/staging.teleimagerie.net.conf](configs/staging.teleimagerie.net.conf),
[configs/staging.isoteam.mn.conf](configs/staging.isoteam.mn.conf) — `/.well-known/mercure`
(SSE) sans tamponnage, `client_max_body_size 512m`, alias en 301.

**Vue interne** : six overrides Unbound (`app./gestion./mailer.staging.*` →
`10.40.0.10`, [piège n° 32](07-pieges.md#32-joindre-la-vip-122-depuis-lintérieur-aboutit-sur-la-gui-dopnsense)),
posés par [scripts/unbound-overrides-staging.py](scripts/unbound-overrides-staging.py).

**DNS** : [scripts/bascule-staging.py](scripts/bascule-staging.py) (copie
`/root/bascule-staging.py` sur pve1), même squelette que `bascule-odoo.py` mais
**deux zones et huit enregistrements** ; `status|ttl60|switch|revert|ttl3600`.

---

## Ce qui a été fait le 14/09/2026 (préparation, sans coupure)

1. VM 103/104 créées depuis pve1 (`qm create … --cpu host --cores 2 --memory 8192
   --balloon 0 --net0 virtio,bridge=vmbr1,tag=400 --agent 1 --serial0 socket
   --onboot 1`, `qm disk import` de l'image noble, `--ide2 vm-storage:cloudinit`,
   `--ipconfig0 ip=10.40.0.80/24,gw=10.40.0.1 --nameserver 10.40.0.1`,
   `qm disk resize … 100G`), clés SSH = les 4 clés de `ssh_authorized_keys` du
   dépôt + `root@pve1`. `qemu-guest-agent` installé à la main (absent de
   l'image cloud). Vérifié : `resolv.conf` → `10.40.0.1` (piège 33),
   `ip route get 10.90.0.2` par `eth0` (piège 37), `auth.teleimagerie.net` →
   `10.40.0.10` depuis la VM.
2. `provisioning.yaml` du dépôt rejoué (Docker CE, compose 2.40.3 épinglé,
   fail2ban, ufw 22/80/443 + 10050 depuis `.60`, sshd sans mot de passe,
   `authorized_keys` exclusif, journald). Rôles galaxy `Oefenweb.fail2ban` /
   `geerlingguy.docker` installés sur le poste (ils manquaient).
3. Clé GitHub `/home/ubuntu/.ssh/id_ed25519` **copiée** depuis chaque dédié (même
   identité, rotation possible plus tard), clone `git@github.com:teleimagerie/gestion.git`
   branche `staging` dans `/srv/gestion`, `resources/` rsyncé (3,1 Go TIM, 13 Mo
   Isoteam), ancien `.env` copié pour démarrer `database` seule avant le
   déploiement.
4. Bases : TIM reconstruite depuis le dump prod OVH du jour
   (`rappro:/home/ubuntu/tim-gestion-backups/ovh/ovhdb-dump-20260914-011556.sql.gz`,
   5,5 Go, rapatrié en 48 s à 110 Mo/s) posé dans `frankenphp/initdb.d/` avec
   `00-definer-user.sql` (les dumps OVH portent `DEFINER=teleimagaamcapon@%` sur
   les vues legacy) ; Isoteam par `mysqldump` de l'ancien staging, `DEFINER`
   retirés. Import par l'entrypoint MySQL sur volume neuf.
5. Certificats émis (`acme.sh --issue --dns dns_ovh`, ~2 min par zone),
   `--install-cert` avec hooks, déployés sur le CT 201.
6. Vhosts posés, testés depuis l'extérieur par `curl --resolve …:443:57.130.34.122`
   avant tout changement DNS : TLS valide (Let's Encrypt), `502` tant que le
   backend n'est pas déployé, alias en `301`, port 80 en `301`, nom inconnu
   rejeté (`ssl_reject_handshake`).
7. Overrides Unbound posés (sauvegarde `config.xml.bak-staging-20260914`,
   `configctl unbound restart`, `host_entries.conf` contrôlé) ; jobs de
   sauvegarde reconfigurés (`exclude 102,103,104` + job hebdomadaire) ; agents
   Zabbix installés et hôtes créés
   ([scripts/zabbix-provision-staging.py](scripts/zabbix-provision-staging.py)) ;
   `topologie.yml` complété, `make controle` sans écart.

## Déploiement applicatif (14/09, 11:45–12:30 Paris)

Lancé par l'admin (`make deploy-isoteam-staging` OK du premier coup ; TIM en trois
temps) — deux échecs instructifs, tous deux dus au **retard de la branche `staging`
du dépôt sur `main`** (outillage Ansible d'avant août) :

1. depuis `feat/staging-proxmox` (basée sur `main`) : « Recreate worker containers »
   échoue — les `group_vars` de `main` listent `retryable_worker`, absent du
   `compose.prod.yaml` de la branche `staging` clonée sur la VM ;
2. depuis `staging` : « DockerHub Sign-In » échoue en 401 — son secret Docker Hub
   chiffré est l'ancien mot de passe, vidé sur `main` le 04/08 ;
3. depuis `feat/staging-proxmox` avec la liste de workers surchargée
   (`-e '{"services":[{"name":"notifier_worker","scale":1},{"name":"priority_worker","scale":1}]}'`) :
   **OK**. La base n'a pas été touchée (volume conservé, migrations Doctrine
   passées).

Vérifications avant bascule, depuis l'extérieur par `curl --resolve …:443:57.130.34.122`
(les noms pointaient encore sur les dédiés) : `/login` **200** sur les deux
tenants (90 ms), legacy `gestion.` 200, Mailpit 401 (basic auth), assets 200,
`/.well-known/mercure` **200 `text/event-stream`**, redirection `/` → `https://…/login`
(URL absolue générée par Symfony : `X-Forwarded-Proto` bien honoré), alias en
301. Dans les VM : Caddy sans la moindre tentative ACME, tous les conteneurs
`healthy` (php, 2 workers, mailer, database, rabbitmq, redis),
`auth.teleimagerie.net` → `10.40.0.10` (override), sortants Xplore / ITIS /
GitHub / Mailjet OK. **Seul échec : SFTP GRU `81.255.38.171:2222`**, joignable
depuis l'ancien dédié seulement → filtre par IP source à faire lever (reste à
faire). Trafic HTTP sur les dédiés dans les 90 dernières minutes : **aucun** ;
aucune écriture sur la base Isoteam depuis le 31/07 (dump de 09:25 UTC valide).

## Bascule du 14/09/2026 — récit chiffré

| Heure UTC | Événement |
|---|---|
| 10:18:36 | `bascule-staging.py ttl60` — 8 enregistrements (2 zones) passent de 3600 (défaut de zone) à 60 |
| 10:20:08 | `bascule-staging.py switch` — A → `57.130.34.122` ; aucun AAAA n'existait |
| 10:20:15 | `1.1.1.1` et `8.8.8.8` répondent déjà `57.130.34.122` (TTL 60) pour les 8 noms ; chemin réel (sans `--resolve`) : `/login` 200 par la VIP, certificat valide |
| 10:20 → 11:20 | dédiés laissés **allumés et servants** pour les résolveurs à cache chaud (TTL 3600 pris avant 10:18) — staging sans utilisateur, la base TIM des dédiés est de toute façon abandonnée |
| ≥ 11:20 | gel des dédiés (`docker compose stop`) **à faire** une fois l'heure de cache écoulée — puis extinction et résiliation (reste à faire) |

Choix assumé, inverse d'Odoo : pas de gel *avant* la bascule. Rien n'écrivait sur
les dédiés (aucune requête en 90 min, base Isoteam figée depuis juillet), et
laisser l'ancien répondre pendant l'heure de cache évitait toute erreur aux
clients à cache chaud. **Coupure : aucune.**

Vue interne : depuis le VPN nomade, le poste résout `app.staging.teleimagerie.net`
en `10.40.0.10` (override Unbound) et obtient 200 — les deux chemins testés
(piège 32).

**Retour arrière** (~3 min, tant que les dédiés existent) :
`bascule-staging.py revert` + `docker compose start` sur les dédiés + retrait des
six overrides Unbound + `docker compose stop` sur les VM. Le point de non-retour
est la **résiliation des dédiés**, pas la bascule.

## Exploitation

- Déploiement : `make deploy-tim-staging` / `make deploy-isoteam-staging` depuis le
  poste (VPN monté) — inchangé, Ansible passe par pve1.
- Accès : `ssh tim-staging` / `ssh isoteam-staging` (alias `ProxyJump`), MySQL
  joignable depuis le VPN sur `10.40.0.80:3306` (le conteneur publie le port sur
  la VM ; plus d'accès direct depuis Internet).
- Rafraîchir la base depuis la prod : `docs/technique/staging-proxmox.md` du dépôt.
- Espace disque : 100 Go dont ~30 Go de base, ~35 Go d'images/cache de build,
  5 Go de `/srv` — `check-disk` du deploy refuse au-delà de 90 % ; `docker system
  prune` au besoin.
- **Binlogs MySQL** : l'import du dump en a produit 22 Go (purgés le 14/09 à mi-import,
  disque à 70 %) ; `binlog_expire_logs_seconds=86400` posé par `SET PERSIST`
  (survit aux redémarrages, `mysqld-auto.cnf` du volume) sur les deux VM — 1 jour
  au lieu de 30, un staging n'a pas de réplication à rejouer.

## Reste à faire

- [ ] **gel des dédiés** (`cd /srv/gestion && sudo docker compose -f compose.yaml -f compose.prod.yaml --profile staging stop` sur `ubuntu@79.137.100.185` et `.184`) à partir de 11:20 UTC le 14/09 ;
- [ ] extinction des dédiés (`systemctl poweroff`) après quelques jours de recul,
  puis **résiliation OVH** de `ns3240118` et `ns3240079` — à la main de l'admin ;
- [ ] `bascule-staging.py ttl3600` après résiliation ;
- [ ] fusionner `feat/staging-proxmox` dans `main` du dépôt gestion ;
- [ ] **SFTP GRU** (`81.255.38.171:2222`, compte `sftp_timgru_test`) : **filtre par IP
  source**, vérifié le 14/09 — joignable depuis l'ancien dédié `79.137.100.185`,
  refusé depuis les VM (sortie `57.130.34.121`), depuis pve1 et depuis le poste.
  Demander à l'exploitant du SFTP d'autoriser `57.130.34.121` ; d'ici là l'import
  GRU par SFTP du staging TIM échoue (la prod, sur `51.210.24.59`, n'est pas
  concernée) ;
- [ ] branche `staging` du dépôt gestion **en retard sur `main`** (outillage Ansible
  d'avant août : mot de passe Docker Hub périmé, `docker-pull.yaml` ancien, pas de
  `retryable_worker` dans son compose) — le 14/09 le déploiement TIM a dû être
  lancé depuis `feat/staging-proxmox` avec la liste de workers surchargée en
  `-e '{"services":[…]}'`. Remettre `staging` au niveau de `main` (fusion) pour
  que `make deploy-tim-staging` redevienne suffisant ;
- [ ] consigner dans la revue HDS ([12-architecture-hds.md](12-architecture-hds.md))
  que les copies de prod des staging sont désormais sur le cluster.
