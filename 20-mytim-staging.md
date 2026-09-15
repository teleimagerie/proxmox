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
| Ressources | 2 vCPU `host`, 8 Go (sans ballooning), **150 Go** Ceph `vm-storage` (100 à la création, étendu le 15/09), `onboot` | idem, 100 Go |
| OS | Ubuntu 24.04 cloud-init (`noble-server-cloudimg-amd64.img` de `nas-vm`), `qemu-guest-agent` | idem |
| Noms publics | `app.`, `gestion.` (legacy), `mailer.` (Mailpit) `.staging.teleimagerie.net` | `.staging.isoteam.mn` |
| Alias 301 | `app-staging`, `gestion-staging` | `app-staging`, `gestion-staging`, `preprod-app`, `preprod-gestion` |
| Base | MySQL 8.4 en conteneur, **copie de la prod** (dump OVH du 14/09/2026, 27 Go) | MySQL 8.4 en conteneur, reprise de l'ancien staging (500 Ko) |
| HA | **aucune** — c'est du staging (décision du 14/09/2026) | idem |
| Sauvegarde | **hebdomadaire, une seule copie** (dimanche 03:00, `keep-last=1`, exclues du job quotidien) — [10-sauvegardes.md](10-sauvegardes.md) | idem |
| Supervision | agent Zabbix 2 (7.0.30) passif + découverte PVE + `cert-staging-tim` — [17-zabbix.md](17-zabbix.md). ⚠️ Sans balloon, l'hyperviseur voit la RAM à 101 % en permanence : faux signal neutralisé le 15/09 (macro à 200), la mémoire réelle porte un High « > 90 % pendant 1 h » côté agent ([piège n° 42](07-pieges.md#42-une-vm-sans-balloon-est-toujours-pleine-pour-lhyperviseur-et-une-escalade-sans-fin-transforme-un-faux-positif-en-80-mails)) | idem, `cert-staging-isoteam` |

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
| 10:20 → 10:28 | dédiés laissés servants quelques minutes (résolveurs à cache chaud, TTL 3600 pris avant 10:18) |
| ~10:28 | **gel des dédiés** par l'admin (`docker compose stop` sur `.185` et `.184`, 0 conteneur) — sans attendre la fin de l'heure de cache, staging sans utilisateur ; les noms publics répondent 200 par la VIP juste après |

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
- Espace disque : **150 Go sur la VM 103** (portés de 100 à 150 le 15/09, voir
  plus bas), 100 Go sur la 104 — `check-disk` du deploy refuse au-delà de 90 %.
  Relevé du 15/09 sur la 103 : 70 Go utilisés dont **64 Go de `/var/lib/docker`,
  presque entièrement le volume MySQL** (67,8 Go de volumes locaux), contre
  2,9 Go d'images et 1 Go de cache de build. **`docker system prune` ne rend donc
  presque rien ici** (Docker annonce 0 % récupérable, ~235 Mo) : sur ces VM le
  disque se libère en purgeant la base ou les binlogs, pas le cache Docker.
- **Binlogs MySQL** : l'import du dump en a produit 22 Go (purgés le 14/09 à mi-import,
  disque à 70 %) ; `binlog_expire_logs_seconds=86400` posé par `SET PERSIST`
  (survit aux redémarrages, `mysqld-auto.cnf` du volume) sur les deux VM — 1 jour
  au lieu de 30, un staging n'a pas de réplication à rejouer.

## Disque de la VM 103 porté à 150 Go (15/09/2026)

Le disque de 100 Go, dimensionné avant l'import de la base, était à **73 %**
(`/dev/sda1` ext4, 96 Go utiles, 70 Go occupés, 26 Go libres) — soit ~16 Go
avant le refus du `check-disk` Ansible à 90 %. La base est une copie de la prod
rafraîchie périodiquement : elle grossit, et chaque rafraîchissement demande
transitoirement de la place. `docker system prune` n'était pas une issue (voir
ci-dessus : 0 % récupérable).

Marge Ceph au moment de la décision : pool `vm-storage` à **12,61 %**,
`MAX AVAIL` 1,1 Tio, `HEALTH_OK` — les 150 Go bruts (`size=3`) ne pèsent rien
face à la cible de 1,22 Tio.

**+50 Go plutôt que +100** : l'occupation retombe sous la moitié, et l'opération
étant sans retour arrière (`qm resize` ne réduit pas une image RBD, ext4 ne
rétrécit pas à chaud), on n'immobilise pas d'espace « au cas où ». **La VM 104
n'est pas touchée** : sa base fait 500 Ko contre 27 Go pour la 103.

Fait **à chaud, sans redémarrage ni coupure** — `scsihw: virtio-scsi-single`,
`sda1` dernière partition du GPT, pas de LVM. Procédure générique dans
[03-exploitation.md](03-exploitation.md#agrandir-le-disque-dune-vm) :

```bash
qm resize 103 scsi0 +50G                 # depuis pve1
sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1   # dans la VM
```

`growpart` a étendu `sda1` par la fin (`start` inchangé à 2099200,
`size` 207615967 → 312473567 secteurs, soit exactement +50 Gio) et `resize2fs`
a redimensionné l'ext4 monté (13 → 19 `desc_blocks`). Résultat :
**145 Go utiles, 70 Go occupés, 75 Go libres, 49 %** — de 26 à 75 Go de marge.

Vérifié dans la foulée : `parted` sans avertissement GPT (table de secours
réécrite), 8 conteneurs `healthy` (php, **3 workers Messenger** — `notifier`,
`priority`, `retryable` —, mailer, database, rabbitmq, redis), `/login` **200**
en 246 ms, cluster `HEALTH_OK`. Le `retryable_worker` vient du déploiement du
14/09 depuis `feat/staging-proxmox` : la fiche n'en décrivait que deux, hérités
des dédiés OVH.

Côté Ceph, le pool n'a bougé que de **12,61 à 12,74 %** : le provisionnement
fin RBD n'alloue que l'écrit, `qm resize` ne relève que le plafond de l'image.
Les 50 Go ajoutés ne coûteront leurs 150 Go bruts (`size=3`) qu'à mesure du
remplissage — la contrainte réelle du pool est la somme des plafonds si toutes
les images se remplissaient, pas la somme des tailles déclarées.

## Redémarrage des deux VM (15/09/2026)

Les deux VM traînaient un `/var/run/reboot-required` posé le **14/09 à 09:13**
par le provisioning Ansible (`libc6`, `linux-image-6.8.0-139-generic`,
`linux-base`) : noyau `-139` installé, `-138` en service, pas de livepatch.
Sans rapport avec l'extension du disque, relevé à cette occasion.

**`sudo reboot` seul suffit** : les conteneurs sont en `unless-stopped` et
`docker` est `enabled` au boot, tout remonte sans intervention. Ne **pas**
faire de `docker compose stop` avant — `unless-stopped` mémorise l'arrêt
manuel et laisserait les conteneurs à terre au démarrage suivant (il faudrait
un `docker compose start`). Si l'on veut vraiment border MySQL, le geste juste
est `systemctl stop docker` (arrête le service, ne marque aucun conteneur),
jamais `compose stop`.

Le point de vigilance envisagé — `StopTimeout` du conteneur non défini, donc
10 s par défaut avant `SIGKILL`, potentiellement court pour vider le buffer
pool des 27 Go de la 103 — **ne s'est pas matérialisé** : MySQL a redémarré
sur un `ready for connections` sans rejeu de journal InnoDB.

Fait une VM à la fois, en commençant par la 104 (base de 500 Ko, si quelque
chose casse c'est là que ça coûte le moins) :

| | VM 104 | VM 103 |
|---|---|---|
| SSH revenu | ~12 s | ~15 s |
| Conteneurs `healthy` | 5 (3 avec healthcheck) | **8/8** en ~50 s |
| Noyau | `-138` → **`-139`** | idem |
| `reboot-required` | levé | levé |

Vérifié après coup : `/login` **200** sur les trois noms (`app.` et `gestion.`
staging TIM, `app.` staging Isoteam), disque de la 103 toujours à 145 Go / 49 %,
cluster `HEALTH_OK`. Coupure réelle : quelques dizaines de secondes par VM, sans
utilisateur.

`unattended-upgrades` ne redémarre pas ces VM ; le drapeau ne se reposera qu'au
prochain lot de mises à jour. Un redémarrage hebdomadaire automatique (dimanche
avant la sauvegarde de 03:00, comme les syngo.via) reste à décider.

## Reste à faire

- [ ] extinction des dédiés (`systemctl poweroff`) après quelques jours de recul,
  puis **résiliation OVH** de `ns3240118` et `ns3240079` — à la main de l'admin ;
- [x] `bascule-staging.py ttl3600` — fait le 14/09 à 10:33 UTC, sans attendre la résiliation (bascule validée, aucun retour arrière envisagé) ;
- [x] `feat/staging-proxmox` fusionnée dans `main` du dépôt gestion (`28d57036`, 14/09) ;
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
  que les copies de prod des staging sont désormais sur le cluster ;
- [x] **redémarrage des deux VM** — fait le 15/09 (voir ci-dessous).
