# MyTIM — migration VPS → VM 103 (staging) et 104 (prod)

> **🚧 EN PRÉPARATION — plan validé le 31/08/2026, aucune VM créée à ce
> jour.** Ce fichier porte les décisions, les mesures et le runbook ; il
> deviendra le récit chiffré des deux bascules, comme [18-odoo.md](18-odoo.md).
> Côté application, les changements vivent dans la branche
> `feature/proxmox-hosting` du dépôt `gestion`
> (`docs/technique/hebergement-proxmox.md`).

MyTIM est l'application interne de gestion (Symfony 7.4 / PHP 8.4 / FrankenPHP,
Docker Compose, RabbitMQ, Redis, Mercure, solveur OR-Tools, Playwright),
déployée par Ansible depuis le poste d'admin. Deux tenants (`tim`, `isoteam`),
deux environnements chacun. **Ce chantier ne couvre que le tenant `tim`** :
staging d'abord (répétition générale), prod ensuite. isoteam suivra avec le
même patron.

## Identité (cible)

| | tim-staging | tim-prod |
|---|---|---|
| Invité | **VM 103** `tim-staging`, QEMU, Ubuntu 24.04 (cloud-init noble) | **VM 104** `tim-prod`, idem |
| Ressources | 4 vCPU `host`, 8 Go RAM, **150 Go** `vm-storage` | 8 vCPU `host`, 16 Go RAM, **200 Go** `vm-storage` |
| Réseau | vmbr1 `tag=400`, `10.40.0.90/24`, gw et DNS `10.40.0.1` | vmbr1 `tag=400`, `10.40.0.80/24`, gw et DNS `10.40.0.1` |
| Noms publics | `app.staging`, `gestion.staging`, `mailer.staging.teleimagerie.net` → `57.130.34.122` | `app`, `gestion.teleimagerie.net` → `57.130.34.122` |
| Base | conteneur `database` local (MySQL 8.4, **27 Go**) | **OVH Web Cloud DB inchangée** `cm496290-001.eu.clouddb.ovh.net:35525` |
| Dépôt | `github.com:teleimagerie/gestion.git`, branche `staging`, dans `/srv/gestion` | idem, branche `main` |
| Source remplacée | VPS `ns3240118.ovh.net` (`79.137.100.185`, 12 vCPU / 30 Go) | VPS `ns3267715.ip-51-210-24.eu` (`51.210.24.59`, 16 vCPU / 62 Go) |
| HA | après validation | après 3 jours d'observation |

Noms Proxmox = noms d'hôtes Ansible = clés `machines:` de
[topologie.yml](topologie.yml) (à ajouter **à la création des VM**, pas avant :
une machine déclarée mais absente est un écart sur la carte).

## Choix structurants (31/08/2026)

- **VM plutôt que CT** — même raison qu'Odoo ([18-odoo.md](18-odoo.md)) :
  Docker en LXC non privilégié est fragile, une VM migre à chaud en ~1 s, et
  le provisioning/deploy Ansible du dépôt se rejoue tel quel.
- **La base tim-prod reste chez OVH** pour cette étape. Une bascule = un
  seul changement (l'hébergement) ; le retour arrière se fait **sans perte de
  données** puisque VPS et VM lisent la même base. Sa migration dans le
  cluster est un chantier suivant, avec sa propre fenêtre.
- **TLS terminé sur proxy-tim**, HTTP clair vers la VM — uniforme avec auth,
  zabbix, odoo. Coût : Caddy passe en HTTP pur (plus d'ACME ni de HTTP/3 dans
  la VM) et Symfony doit être averti qu'il est derrière un proxy de confiance
  (`SYMFONY_TRUSTED_PROXIES=10.40.0.10`, sinon URL générées en `http://`,
  cookies sans `Secure`, boucle de redirection OIDC).
- **Certificats émis avant la bascule** en DNS-01 depuis pve1 (patron zabbix)
  → pas de fenêtre d'erreur TLS, là où Odoo en a eu ~2 min.
- **Staging d'abord** : première exécution du playbook sur le cluster hors
  production, durées mesurées, runbook rodé.

## Architecture

```
Internet ── 57.130.34.122:443 ── routeur SNI (CT 201) ── 127.0.0.1:8443 ssl proxy_protocol
                                                              │ vhost mytim.teleimagerie.net.conf
                                                              │ (app + gestion, X-Forwarded-Proto https,
                                                              │  /.well-known/mercure sans tampon)
                                                              ▼
                                                    http://10.40.0.80:80 (VM 104)
                                                    Caddy/FrankenPHP ── aiguille par Host :
                                                      app.*     → Symfony (index.php)
                                                      gestion.* → legacy PHP (/app/legacy)
                                                    + 26 consumers Messenger, RabbitMQ, Redis,
                                                      solver, playwright
                                                              │
                                              MySQL OVH 35525 ◄┘ (NAT sortant 57.130.34.121)
```

Le routeur SNI envoie tout nom non `syngo-via.*` vers `8443` : **rien à
ajouter dans `443-router.conf`**. Vhosts :
[configs/mytim.teleimagerie.net.conf](configs/mytim.teleimagerie.net.conf) et
[configs/mytim-staging.teleimagerie.net.conf](configs/mytim-staging.teleimagerie.net.conf).
Le bloc `/.well-known/mercure` est le point délicat : les dicom-agents des
sites et les navigateurs tiennent une connexion SSE ouverte des heures ;
`proxy_buffering off` + `proxy_read_timeout 24h` sont obligatoires.

Ce qui change **dans le dépôt gestion** (branche `feature/proxmox-hosting`) :
variable d'inventaire `tls_upstream: true` sur les hôtes VM → `env.j2` émet
`SERVER_NAME=http://…` (désactive `auto_https` de Caddy), `LEGACY_SERVER_NAME`
et `MAILPIT_SERVER_NAME` préfixés de même, et `SYMFONY_TRUSTED_PROXIES`. Les
URL publiques (`APP_DEFAULT_URI`, `MERCURE_PUBLIC_URL`) restent en `https://`.
Inventaire : groupes `tim_staging_vm` / `tim_prod_vm` (`ProxyJump
root@pve1.infra.teleimagerie.net`, seul nœud raccordé au VLAN 400) ; le jour J
l'hôte VM prend la place du VPS dans `tim_staging` / `tim_prod`.

> Piège rencontré en écrivant la branche : `deploy.yaml` charge
> `group_vars/default/vars.yaml` par `include_vars` (précédence 18), qui
> **écrase** une variable d'inventaire (précédence 5). Un `tls_upstream: false`
> « par défaut » dans ce fichier aurait rendu le flag inopérant. Le template
> lit `tls_upstream | default(false)` et le fichier de défauts ne le déclare pas.

## Mesures du 31/08/2026 (lecture seule sur les VPS)

| | tim-prod (VPS) | tim-staging (VPS) |
|---|---|---|
| CPU / RAM | 16 vCPU, 62 Go, **7 Go utilisés** | 12 vCPU, 30 Go, 2 Go utilisés |
| Disque | 195 Go utilisés sur 878 | 121 Go sur 878 |
| `resources/` | **68 Go** — `cr/` 66 Go (comptes rendus), `key-images/` 1,7 Go, `media/` 660 Mo, `exports/` 349 Mo, `gru/` 56 Mo | 3,1 Go |
| Images Docker | `gestion-app-php:prod` 1,6 Go, playwright 2,9 Go, solver 0,5 Go | `gestion-app-php:staging` **31 Go** (à comprendre au rebuild : la VM repartira d'une image neuve) |
| Base | chez OVH (dump ~3,4 Go gzip, tiré chaque jour sur `rappro`) | volume local, schéma `tim` = **27 Go** |
| Conteneurs | 32 (php à ~900 Mo / 40 % d'un cœur, priority_worker ~240 Mo × 6, le reste 70–130 Mo) ; total ≈ 5,5 Go | 7 |
| RabbitMQ | 1 message en attente (`delay_retryable_…`) | files vides |
| Commit déployé | `a5436ddc6` (28/08/2026) | — |
| En-têtes de sécurité servis par Caddy | aucun (HSTS et nosniff seront ajoutés par le vhost nginx) | idem |

Conséquences sur le gabarit : la RAM du VPS prod est très surdimensionnée
(7 Go réels) → 16 Go suffisent ; le disque prod est dicté par `resources/`
(68 Go et croissant : **200 Go**) ; le disque staging par la base (27 Go) et
l'image (**150 Go**). Cluster au 31/08 : 32 Go de RAM alloués aux 7 invités
(plafond ~100 Go, [01-architecture.md](01-architecture.md#mémoire)), Ceph
`vm-storage` 62 Gio utilisés sur 1,3 Tio — +350 Go de disques virtuels
(provisionnés fins) tiennent largement.

DNS (autoritaires `ns17`/`dns17.ovh.net`, TTL de zone 3600) : `app`, `gestion`
et `d69eeb3e` → `51.210.24.59`, **pas d'AAAA**. `app.staging`,
`gestion.staging`, `mailer.staging` **n'ont aucun enregistrement explicite** :
ils ne résolvent que par le wildcard `*.staging → 79.137.100.185`. Le script
de bascule crée donc les A en staging (et les supprime au `revert`, le
wildcard reprenant la main).

## La contrainte qui structure la bascule prod : un seul `scheduler_worker`

VPS et VM partagent la base pendant la transition. Le `scheduler_worker`
consomme quinze transports `scheduler_*` (factures, SFTP GRU, alarmes, sync
Xplore…) et `LOCK_DSN` pointe sur le Redis **local à chaque stack** : aucun
verrou ne protège d'un second scheduler. Deux stacks actives = jobs planifiés
exécutés deux fois. Règle : **sur la VM prod, aucun worker ne démarre tant
que ceux du VPS tournent.** Mécanisme : `deploy.yaml` lancé avec
`-e '{"services": []}'` (les extra-vars priment sur tout) ne démarre que `php`
(+ `rabbitmq`/`redis`/`database` par `depends_on`) et saute
`restart-workers.yaml`.

## Plan

### Phase 0 — mesures ✅ (31/08/2026, tableau ci-dessus)

Reste à faire avant la phase 2 : **ajouter `57.130.34.121` à l'allowlist IP
de la Web Cloud DB `cm496290-001`** (manager OVH), sans rien retirer.

### Phase 1 — dépôt gestion ✅ (branche `feature/proxmox-hosting`, 31/08/2026)

`env.j2`, `group_vars/default/vars.yaml`, `inventory/hosts.yaml`,
`docs/technique/hebergement-proxmox.md`. Rendu du template vérifié dans les
deux modes. À fusionner dans `main` **et** `staging` avant les déploiements
(le playbook checkout la branche de l'environnement).

### Phase 2 — tim-staging (VM 103)

1. Image `noble-server-cloudimg-amd64.img` (déjà sur `nas-vm/template/iso/`,
   SHA256 vérifié le 26/08). Création depuis pve1 :
   ```bash
   qm create 103 --name tim-staging --memory 8192 --cores 4 --cpu host --ostype l26 \
     --net0 virtio,bridge=vmbr1,tag=400 --scsihw virtio-scsi-single --agent 1 --onboot 1 \
     --serial0 socket --vga serial0
   qm importdisk 103 /mnt/pve/nas-vm/template/iso/noble-server-cloudimg-amd64.img vm-storage
   qm set 103 --scsi0 vm-storage:vm-103-disk-0 --boot order=scsi0 --ide2 vm-storage:cloudinit
   qm resize 103 scsi0 150G
   qm set 103 --ipconfig0 ip=10.40.0.90/24,gw=10.40.0.1 --nameserver 10.40.0.1 \
     --ciuser ubuntu --sshkeys /root/.ssh/cloudinit-admin-keys.pub   # clés admin + root@pve1
   qm start 103
   ```
   Vérifier : `qm agent 103 ping`, `getent hosts auth.teleimagerie.net` → `10.40.0.10`
   (vue interne, piège 33), sortie Internet.
2. Clé de la VM (`ssh-keygen -t ed25519 -C tim-staging-vm103` sous `ubuntu`)
   déclarée en **deploy key GitHub** lecture seule sur `teleimagerie/gestion`
   (leçon Odoo : le clone par agent forwarding ne survit pas à l'admin).
3. Provisioning : `ansible-playbook -i inventory/hosts.yaml playbooks/provisioning.yaml -e target_host=tim_staging_vm`
   (`authorized_keys` **exclusif** : la clé du poste d'admin qui rebondit doit
   être dans `ssh_authorized_keys`).
4. Base : dump du VPS (`mysqldump --single-transaction` du schéma `tim`,
   27 Go → à mesurer compressé) déposé dans `frankenphp/initdb.d/` **avant**
   le premier démarrage du conteneur `database`, ou importé à la main ensuite.
   Chronométrer : c'est la durée de coupure staging.
5. `rsync -aH --numeric-ids` de `/srv/gestion/resources/` (3,1 Go) depuis le VPS.
6. Déploiement : `ansible-playbook -Ji inventory/hosts.yaml playbooks/deploy.yaml -e target_host=tim_staging_vm -e app_name=tim -e deploy_env=staging`.
   **Chronométrer le build** de l'image sur Ceph et comparer au VPS.
7. Certificat (pve1) : `acme.sh --issue --dns dns_ovh -d app.staging.teleimagerie.net -d gestion.staging.teleimagerie.net -d mailer.staging.teleimagerie.net --home /opt/acme`,
   puis `--install-cert` vers `/opt/acme/deployed/mytim-staging/` avec
   `--reloadcmd /opt/acme/deploy-mytim-staging.sh`
   ([scripts/deploy-mytim-staging.sh](scripts/deploy-mytim-staging.sh)) ;
   `mkdir /etc/nginx/certs/mytim-staging` sur le CT 201 au préalable.
8. Vhost [configs/mytim-staging.teleimagerie.net.conf](configs/mytim-staging.teleimagerie.net.conf)
   dans `sites-available` + lien `sites-enabled`, `nginx -t && systemctl reload nginx`.
9. Tests sans DNS :
   ```bash
   curl -sS --resolve app.staging.teleimagerie.net:443:57.130.34.122 -o /dev/null \
        -w '%{http_code} %{redirect_url}\n' https://app.staging.teleimagerie.net/login   # 200, pas de http://
   curl -N --resolve app.staging.teleimagerie.net:443:57.130.34.122 \
        'https://app.staging.teleimagerie.net/.well-known/mercure?topic=test'         # reste ouvert
   ```
   IP réelle dans l'access.log du CT 201 **et** dans les logs Symfony.
10. Bascule : `/root/bascule-mytim.py staging switch` (crée les 3 A, TTL 60),
    override Unbound OPNsense des 3 noms → `10.40.0.10` (sauvegarde
    `config.xml`, `configctl unbound restart`). Vérifs : login formulaire et
    SSO `mytim-staging` (Keycloak), legacy `gestion.staging`, Mailpit UI et
    mail capturé, upload, EventSource persistant dans l'onglet réseau, un
    `deploy` complet post-bascule.
11. HA : `ha-manager add vm:103 --state started --max_restart 3 --max_relocate 3`,
    migration à chaud pve1 → pve2 sous sonde HTTP, vzdump du lendemain sur PBS.

Passage en phase 3 : staging stable 48 h, durées notées ici, aucun écart
inexpliqué. Le VPS staging peut alors être éteint (pas résilié).

### Phase 3 — tim-prod (VM 104)

**Préparation (J-x, sans impact)** : VM 104 comme ci-dessus (`10.40.0.80`,
16384 Mo, 8 cœurs, 200 Go) ; deploy key `tim-prod-vm104` ; depuis la VM,
**avant tout déploiement** : `nc -zv cm496290-001.eu.clouddb.ovh.net 35525`
(allowlist), `in-v3.mailjet.com 587`, `81.255.38.171 2222` (SFTP GRU),
`itis.deeplink-medical.com 443`, `hdsedl.xplore.fr 443`,
`voip.teleimagerie.net 443`, `api.piste.gouv.fr 443`, `ghcr.io 443`,
`codeload.github.com 443`. Provisioning. **Déploiement sans workers** :
`… -e target_host=tim_prod_vm -e app_name=tim -e deploy_env=prod -e '{"services": []}'`
→ `docker compose ps` ne doit montrer aucun `*_worker`. Les migrations
Doctrine s'exécutent contre la base OVH : même commit que le VPS → rien à
faire ; **si une migration est en attente, aligner le VPS d'abord**. rsync
initial de `resources/` (68 Go, plusieurs dizaines de minutes par le VLAN
400 ← Internet : à lancer la veille). Certificat `mytim-prod` (DNS-01, hook
[scripts/deploy-mytim-prod.sh](scripts/deploy-mytim-prod.sh)), vhost
[configs/mytim.teleimagerie.net.conf](configs/mytim.teleimagerie.net.conf),
tests `--resolve` complets (login, SSO `mytim`, legacy, SSE, IP réelles),
`bin/console doctrine:query:sql 'SELECT 1'` depuis le conteneur php.
Prévenir d'une coupure de ~10 min, hors créneaux de facturation / SFTP GRU
planifiés.

**Runbook jour J** (heures UTC à consigner ici) :

```bash
# H-1 (pve1)
python3 /root/bascule-mytim.py prod ttl60
dig @ns17.ovh.net +noall +answer app.teleimagerie.net gestion.teleimagerie.net

# H — 1. VPS : arrêter les workers, SCHEDULER EN PREMIER
ssh ubuntu@ns3267715.ip-51-210-24.eu 'cd /srv/gestion && sudo docker compose -f compose.yaml -f compose.prod.yaml \
  stop -t 30 scheduler_worker notifier_worker priority_worker async_worker xplore_update_worker cmsi_worker'
# 2. VPS : attendre les files vides (ou accepter la perte des messages restants — décision à noter)
ssh ubuntu@ns3267715.ip-51-210-24.eu 'cd /srv/gestion && sudo docker compose exec -T rabbitmq rabbitmqctl list_queues name messages | awk "\$2>0"'
# 3. VPS : gel du web — début de coupure
ssh ubuntu@ns3267715.ip-51-210-24.eu 'cd /srv/gestion && sudo docker compose stop php'
# 4. Delta resources/ (poste d'admin ou VM) — sans --delete, la VM n'a rien écrit
rsync -aH --numeric-ids --rsync-path="sudo rsync" ubuntu@ns3267715.ip-51-210-24.eu:/srv/gestion/resources/ /srv/gestion/resources/
# 5. VM : démarrer les workers avec les scales de prod (= ce que génère restart-workers.yaml)
cd /srv/gestion && sudo docker compose -f compose.yaml -f compose.prod.yaml up -d --no-build \
  --scale priority_worker=6 --scale cmsi_worker=6 --scale async_worker=6 --scale xplore_update_worker=6 \
  notifier_worker scheduler_worker priority_worker cmsi_worker async_worker xplore_update_worker playwright solver
sudo docker compose -f compose.yaml -f compose.prod.yaml ps      # tout Up (healthy)
# 6. Bascule DNS (pve1)
python3 /root/bascule-mytim.py prod switch
dig @ns17.ovh.net +short app.teleimagerie.net ; dig @dns17.ovh.net +short gestion.teleimagerie.net
dig @1.1.1.1 +short app.teleimagerie.net ; dig @8.8.8.8 +short app.teleimagerie.net
# 7. Split-horizon : overrides Unbound OPNsense app/gestion.teleimagerie.net -> 10.40.0.10
```

**Vérifications avant d'annoncer la réouverture** : login externe (4G)
formulaire + SSO, legacy, page lourde, upload, EventSource persistant, un
dicom-agent de site reconnecté (logs applicatifs), appel de test du webhook
3CX, mail sortant réel (en-têtes Mailjet), IP réelles dans l'access.log du CT
201 et dans les logs Symfony, **un job `scheduler_*` observé exécuté une seule
fois**, files RabbitMQ qui se vident, canal Slack d'erreurs silencieux.

**Retour arrière** (~3 min, **sans perte de données** tant que le VPS existe) :
`bascule-mytim.py prod revert` → VM : `docker compose stop` de tous les
workers, scheduler d'abord → VPS : `docker compose start php` puis les
workers → retirer les overrides Unbound. Le point de non-retour est la
**résiliation du VPS**, pas la bascule.

**Après** : J+0 HA `vm:104` + migration à chaud de validation sous sonde ;
J+1 vzdump sur PBS + `qmrestore` de test en VM 299 (net0 retiré avant boot,
comme Odoo) ; J+3 VPS éteint, IP du VPS retirée de l'allowlist OVH DB,
`ttl3600`, hôte Zabbix pour la VM et retrait des VPS ; J+7 résiliation des
deux VPS, inventaire Ansible nettoyé (`tim_*_vm` → `tim_*`, `tls_upstream`
porté par les hôtes restants), `d69eeb3e` supprimé,
[14-noms-de-domaine.md](14-noms-de-domaine.md) et
[09-proxy-tim.md](09-proxy-tim.md) mis à jour, [topologie.yml](topologie.yml)
+ `make carte`.

## Restauration (cible)

- **VM entière** : vzdump PBS quotidien 02:00 (couvre `resources/` et les
  volumes Docker : RabbitMQ, Redis, base staging).
- **Base prod** : dump quotidien de la Web Cloud DB tiré par l'API OVH sur
  `rappro` (`46.105.64.17`, 05:30) — inchangé par ce chantier
  (`docs/technique/ovh-db-dump-fetch.md` du dépôt gestion).
- **Base staging** : dans le vzdump ; pas de dump applicatif prévu.

## Mail et intégrations (rappel des flux sortants à vérifier depuis la VM)

| Flux | Destination |
|---|---|
| Mail | Mailjet `in-v3.mailjet.com:587` STARTTLS |
| Base prod | OVH Web Cloud DB `:35525` (allowlist) |
| RIS / PACS | `hdsedl.xplore.fr:443` (Xplore, TelemedCloud, PACS), ITIS `itis.deeplink-medical.com:443` en mTLS, Venus `venus.isoteam.mn:443` |
| Métier | 3CX `voip.teleimagerie.net:443` (+ webhook entrant), Chorus Pro `api.piste.gouv.fr`, Pennylane, Odoo (`odoo.teleimagerie.net` → override interne), SISMIC (Azure), Nuance, OVH API (SMS, facturation, dump DB), Slack, Anthropic |
| Fichiers | SFTP GRU `81.255.38.171:2222` |
| Build | `ghcr.io`, `github.com`, `codeload.github.com` |
| Entrant | navigateurs, dicom-agents des sites (HTTPS + SSE Mercure), webhook 3CX — tous par `57.130.34.122` |
| SSO | Keycloak `auth.teleimagerie.net` (clients `mytim`, `mytim-staging`, [16-keycloak.md](16-keycloak.md)) — redirect URIs inchangées |

## Reste à faire après ce chantier

- isoteam-prod / isoteam-staging (même patron, zone `isoteam.mn`, realm
  Keycloak `isoteam` à créer — [16-keycloak.md](16-keycloak.md)).
- Base tim-prod dans le cluster (VM/CT MySQL dédiée ou conteneur local).
- Image `gestion-app-php` prébuild sur GHCR au lieu du build sur la VM, si le
  build sur Ceph s'avère lent.
- Le rôle de `rappro` (dumps) pourrait rejoindre le cluster.
