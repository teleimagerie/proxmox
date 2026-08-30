# ERP Odoo — migration VPS → VM 101

> **✅ EN PRODUCTION sur le cluster depuis le 29/08/2026, 16:18 UTC —
> migration terminée et soldée le 30/08/2026.** Bascule vérifiée de bout en
> bout (récit chiffré plus bas), sauvegardes 3 niveaux validées dont une
> restauration réelle, **VPS résilié le 30/08** : il n'y a plus d'« ancien
> chemin », l'action `revert` de `bascule-odoo.py` est caduque (comme celle
> de `bascule-3noms.py` avant elle).

## Identité

| | |
|---|---|
| Invité | **VM 101** `odoo`, QEMU, Ubuntu 24.04 (cloud-init noble) |
| Ressources | 4 vCPU `host`, 4 Go RAM, 40 Go sur `vm-storage` (Ceph) |
| Réseau | vmbr1 `tag=400`, `10.40.0.70/24`, gw `10.40.0.1`, DNS `10.40.0.1` |
| Nom public | `odoo.teleimagerie.net` → `57.130.34.122` (TTL 3600 depuis le 30/08), AAAA supprimé ; vue interne : override Unbound → `10.40.0.10` |
| Application | Odoo 17 (Docker Compose), PostgreSQL 16, base `odoo` ~175 Mo, filestore ~586 Mo |
| Dépôt | `github.com:teleimagerie/odoo.git`, **branche `proxmox`** déployée dans `/srv/odoo` |
| Source remplacée | VPS OVH `vps-f18bcfe7.vps.ovh.net` — éteint le 29/08, **résilié le 30/08/2026** (les données MySQL Dolibarr sont parties avec lui, décision actée) ; l'accès `ssh ubuntu@91.134.75.199` n'existe plus |
| HA | **ressource HA depuis le 29/08/2026** (`max_restart 3`, `max_relocate 3`), démarrée sur pve1 |

Choix structurants : **VM plutôt que CT** (Docker en LXC non privilégié =
fragile, et une VM migre à chaud en ~1 s), **Ubuntu plutôt que Debian**
(iso-fonctionnel avec le VPS, le provisioning Ansible du dépôt se rejoue tel
quel), **Ubuntu 24.04 identique à la source**. Ubuntu devient le seul invité
non-Debian du cluster — assumé.

## Architecture

```
Internet ── 57.130.34.122:443 ── routeur SNI (CT 201) ── 127.0.0.1:8443 ssl proxy_protocol
                                                              │ vhost odoo.teleimagerie.net
                                                              ▼
                                                    http://10.40.0.70:8069 (VM 101)
                                                    docker: web (odoo) ── db (postgres:16)
```

- **Traefik abandonné** : sur le VPS, Traefik terminait le TLS et posait les
  en-têtes ; tout est transposé dans le vhost nginx du CT 201
  ([configs/odoo.teleimagerie.net.conf](configs/odoo.teleimagerie.net.conf)) —
  en-têtes sécurité (HSTS, nosniff, X-Frame-Options, X-Robots-Tag), CORS,
  routeur « images » (`/web/image|/web/content|/web/assets|/meips`, CORS
  permissif pour les intégrations), `client_max_body_size 1G`, bloc
  `location /websocket` avec en-têtes `Upgrade` (mode threadé : tout sur 8069).
  **Aucun basic auth** : le middleware Traefik était commenté sur le VPS,
  la cible reproduit ce comportement (le `BASIC_AUTH` du `.env` est inutilisé).
- Le service `mysql-dolibarr` (legacy de l'import Dolibarr→Odoo, arrêté depuis
  des semaines) **disparaît** — décision du 29/08 : suppression sans archive,
  les données partent avec la résiliation du VPS.
- `config/odoo.conf` et `.env` ne sont pas dans git (secrets) : copiés du VPS,
  inchangés (`proxy_mode=True`, `web.base.url` figée — le nom ne change pas).
- Image : le Dockerfile part du tag glissant `odoo:17` ; la reconstruction du
  29/08 a produit le build `17.0-20260817` (le VPS tournait `17.0-20250618`).
  Le `-u base --stop-after-init` (procédure standard du deploy.yml du dépôt)
  a mis les 152 modules à niveau **sans une erreur**. À rejouer après la
  restauration finale du jour J.

## Ce qui a été fait le 29/08/2026 (préparation + répétition générale)

1. Image cloud `noble-server-cloudimg-amd64.img` téléchargée sur
   `nas-vm/template/iso/` (SHA256 vérifié), VM 101 créée depuis pve1
   (cloud-init : IP, DNS `10.40.0.1` — piège 33 —, clés admin + root@pve1),
   qemu-guest-agent opérationnel.
2. Provisioning Ansible du dépôt rejoué depuis le poste d'admin (ProxyJump
   pve1) : Docker CE, fail2ban, ufw (ssh/80/443 — sans objet pour 8069 : les
   ports publiés par Docker contournent ufw ; pas de firewall PVE non plus,
   comme les autres invités du VLAN 400).
3. Branche `proxmox` créée et poussée : compose sans Traefik ni
   mysql-dolibarr, `ports: 8069`. Clone dans `/srv/odoo` de la VM.
   ⚠️ Le clone initial a utilisé le forwarding d'agent SSH du poste d'admin :
   **déclarer la clé de la VM en deploy key GitHub** pour l'autonomie des pulls
   (clé : `/home/ubuntu/.ssh/id_ed25519.pub`, commentaire `odoo-vm101`).
4. Le VPS avait un écart git (module `tim_hr_leave_hierarchy` présent mais
   non commité chez lui, et sa deploy key GitHub morte) : vérifié fichier par
   fichier identique au commit `4b7b061` de `main` → la branche `proxmox`
   part de `main`, aucun rattrapage à prévoir.
5. Copie des données (dump 22 Mo + rsync filestore 586 Mo), restauration,
   **neutralisation des effets de bord sur la copie**
   (`ir_mail_server`/`fetchmail_server`/`ir_cron` désactivés — sinon double
   relève IMAP et doubles envois Mailjet), `-u base`, démarrage.
6. Vhost posé sur le CT 201 avec **certificat auto-signé provisoire**
   (`/etc/nginx/certs/odoo-selfsigned/`, 30 jours) — remplacé par Let's
   Encrypt au jour J. Entrée `/etc/hosts` de la VM : `10.40.0.10
   odoo.teleimagerie.net` (à remplacer par l'override Unbound à la bascule).
7. Tests chaîne complète (VIP → SNI → vhost → VM) : login 200, en-têtes
   sécurité et CORS conformes, redirection port 80, route images OK,
   handshake websocket synthétique → 400 **identique à la prod Traefik**
   (comportement Odoo, pas un défaut du vhost). Flux sortants depuis la VM :
   Mailjet **25 et 587 OK**, imap.gmail.com 993 OK.
8. Timer `odoo-pgdump.{service,timer}` armé (01:15, 7 dumps glissants dans
   `/var/backups/odoo/`, repris par le vzdump de 02:00) — premier dump validé.
9. `/root/bascule-odoo.py` déployé sur pve1
   ([scripts/bascule-odoo.py](scripts/bascule-odoo.py)) :
   `status|ttl60|switch|revert|ttl3600`, garde-fous doublons et cible
   inattendue. `status` vérifié : A → `91.134.75.199`, AAAA présent, TTL 3600
   (défaut de zone).

## Bascule du 29/08/2026 — récit chiffré

Déroulé réel (heures UTC), sur le runbook ci-dessous exécuté tel quel :

- **16:11** — `ttl60` : TTL de l'A **et** de l'AAAA abaissés à 60, vérifiés
  sur `ns17` et `dns17.ovh.net`. Choix assumé de ne pas attendre l'heure de
  propagation (samedi après-midi, aucune activité dans les logs) : les
  clients à cache chaud risquaient jusqu'à 1 h de `502`, aucun constaté.
- **16:14:48** — gel : `docker compose stop web` sur le VPS. Début de la coupure.
- **16:15 → 16:17** — sync finale sur la VM : dump 22 Mo tiré du VPS, rsync
  delta du filestore (quelques secondes), drop/create + `pg_restore`,
  `-u base` (152 modules, ~50 s — seule trace : un avertissement docutils
  `(ERROR/3) Unexpected indentation` dans le rendu de la description du
  module `mail`, cosmétique), redémarrage complet **sans neutralisation**.
- **16:18:08** — `switch` : A → `57.130.34.122`, AAAA supprimé, vérifié sur
  les deux autoritaires + `1.1.1.1` + `8.8.8.8`. **Fin de coupure effective
  ~16:19** (TTL 60). Coupure totale : **~4 min**.
- **~16:20** — certbot webroot dans le CT 201 : certificat émis (échéance
  **27/11/2026**), chemins remplacés dans le vhost, reload. Fenêtre d'erreur
  TLS entre bascule et émission : **~2 min**, assumée (décision du 29/08).
- Override Unbound `odoo.teleimagerie.net → 10.40.0.10` ajouté dans
  `config.xml` d'OPNsense (sauvegarde `/conf/config.xml.bak-odoo-20260829`,
  entrée clonée sur celles d'`auth`/`zabbix`, `configctl unbound restart` —
  `unbound reconfigure` n'existe pas sur cette version). Entrée `/etc/hosts`
  de test retirée de la VM.
- **Vérifications** : `200` par les deux chemins (externe DNS réel avec
  certificat valide en 0,27 s ; interne VLAN 400 via l'override), **IP
  réelles** des clients dans l'access.log du CT 201 (preuve proxy_protocol),
  **mail sortant réel `sent`** via Mailjet:25 (odoo shell → mcapon@),
  logo `/web/image` 200, handshake websocket iso-prod. HA déclarée dans la
  foulée (`vm:101` started sur pve1).
- Constat sans régression : le serveur de mail **entrant** était déjà à
  l'état `draft` sur le VPS (vérifié sur sa base après bascule) — la relève
  IMAP était donc déjà inopérante avant la migration. À réactiver un jour
  depuis l'interface (Paramètres → Techniques → Serveurs entrants,
  bouton *Confirmer*), chantier indépendant.
- **16:38** — migration à chaud de validation pve1 → pve2 sous sonde HTTP
  (2 requêtes/s) : **1 seule sonde perdue sur 120** (~1 s de gel), 119 × 200.
  La promesse HA est démontrée en production réelle.
- **16:40** — validation exhaustive des pièces jointes sur la VM : les
  **3 918 références filestore** de `ir_attachment` vérifiées une à une
  (existence + **SHA1 conforme au champ `checksum`**) — 0 manquant,
  0 corrompu ; les 226 restantes vivent en base (`db_datas`, portées par le
  dump). Comparaison VPS/VM : la VM a 4 attachments et 20 fichiers de plus —
  dérive normale de la production vivante (assets régénérés par `-u base`).
- **16:42** — **VPS éteint** (`systemctl poweroff`, ping muet, production
  intacte). Décision utilisateur du 29/08 au soir : extinction immédiate
  après la validation des documents, sans les 3 jours d'observation du
  patron habituel — redémarrage possible depuis la console OVH tant que la
  résiliation n'est pas faite.

## Runbook utilisé (archivé)

**H-1 ou plus** (TTL de zone 3600) — sur pve1 :
```bash
python3 /root/bascule-odoo.py ttl60      # A ET AAAA (piège : l'AAAA aussi)
dig @ns17.ovh.net +noall +answer odoo.teleimagerie.net A odoo.teleimagerie.net AAAA
```

**H** :
```bash
# 1. Gel de la source (le VPS) — Traefik rendra 502, coupure franche
ssh ubuntu@91.134.75.199 'cd /srv/odoo && sudo docker compose stop web'

# 2. Sync finale (sur la VM, ssh ubuntu@10.40.0.70 depuis pve1)
cd /srv/odoo && sudo docker compose stop
ssh ubuntu@91.134.75.199 'sudo docker exec odoo-db-1 pg_dump -U odoo -Fc odoo' > /srv/transfert/odoo-final.dump
sudo rsync -aH --numeric-ids --delete -e "ssh -i /home/ubuntu/.ssh/id_ed25519" \
  --rsync-path="sudo rsync" \
  ubuntu@91.134.75.199:/var/lib/docker/volumes/odoo_odoo-web-data/_data/ \
  /var/lib/docker/volumes/odoo_odoo-web-data/_data/
sudo docker compose up -d db   # puis attendre pg_isready
sudo docker compose exec -T db psql -U odoo -d postgres -c 'DROP DATABASE odoo;' -c 'CREATE DATABASE odoo OWNER odoo;'
sudo docker compose exec -T db pg_restore -U odoo -d odoo --no-owner < /srv/transfert/odoo-final.dump
sudo docker compose run --rm web odoo -d odoo -u base --stop-after-init   # ~1 min
sudo docker compose up -d      # SANS neutralisation cette fois
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8069/web/login   # 200

# 3. Bascule DNS (pve1)
python3 /root/bascule-odoo.py switch
dig @ns17.ovh.net +short odoo.teleimagerie.net ; dig @dns17.ovh.net +short odoo.teleimagerie.net
dig @1.1.1.1 +short odoo.teleimagerie.net ; dig @8.8.8.8 +short odoo.teleimagerie.net

# 4. Certificat (CT 201, dès que l'A répond) — fenêtre TLS ~1-2 min assumée
certbot certonly --webroot -w /var/www/html -d odoo.teleimagerie.net
sed -i 's|/etc/nginx/certs/odoo-selfsigned/fullchain.pem|/etc/letsencrypt/live/odoo.teleimagerie.net/fullchain.pem|;
        s|/etc/nginx/certs/odoo-selfsigned/privkey.pem|/etc/letsencrypt/live/odoo.teleimagerie.net/privkey.pem|' \
  /etc/nginx/sites-available/odoo.teleimagerie.net.conf
nginx -t && systemctl reload nginx

# 5. Split-horizon : override Unbound OPNsense odoo.teleimagerie.net -> 10.40.0.10
#    (GUI Services > Unbound > Overrides ; sauvegarder config.xml avant)
#    puis retirer l'entrée /etc/hosts de la VM :
sudo sed -i '/odoo.teleimagerie.net/d' /etc/hosts && getent hosts odoo.teleimagerie.net  # -> 10.40.0.10
```

**Vérifications avant d'annoncer la réouverture** : login réel depuis
l'extérieur (4G), chat/présence (websocket 101 dans l'onglet réseau), upload
volumineux, IP clients réelles dans l'access.log du CT 201, chemin interne
VLAN 400, mail de test **sortant** (en-têtes Mailjet, SPF pass) et
**entrant** (boîte ticket@), synchro Google Calendar manuelle.

**Retour arrière** (~3 min, tant que le VPS existe) :
`bascule-odoo.py revert` + `docker compose start web` sur le VPS + retrait de
l'override Unbound + `docker compose stop` sur la VM. Les écritures faites
sur la VM entre bascule et revert sont perdues. Le point de non-retour est la
**résiliation du VPS**, pas la bascule.

## Post-bascule — reste à faire

1. ✅ HA déclarée le 29/08 ; ✅ migration à chaud de validation faite le soir
   même (pve1 → pve2, ~1 s, voir récit) — la VM tourne sur **pve2**.
2. ✅ Sauvegardes vérifiées le 30/08 — les trois niveaux :
   - **vzdump** : `vm/101/2026-08-30T02:00:05Z` présent sur PBS, tâches OK ;
   - **odoo-pgdump** : `odoo-7.dump` de 01:15 présent (22 Mo) ;
   - **restauration testée** : `qmrestore` du backup de la nuit en VM 299
     (28 s à 1,45 Go/s), `net0` retiré avant boot, **Odoo a répondu 200 dans
     la VM restaurée**, puis 299 détruite. Noter : sans carte réseau, le
     boot prend ~2 min (timeouts cloud-init/réseau) avant que l'agent réponde ;
   - **auto_backup** : avait échoué à 03:00 (`Permission denied` sur
     `/var/lib/odoo/backups/odoo`) — le dossier `./backups` recréé par le
     clone git appartenait à `ubuntu` au lieu de l'uid 101 du process odoo
     (c'est le `messagebus` observé sur le VPS). Corrigé par `chown 101`,
     sauvegarde de preuve produite (470 Mo, rétention 30 j). Les erreurs
     `.map … debug assets` des logs sont cosmétiques (sourcemaps d'anciennes
     versions d'assets après le `-u base`).
3. ✅ Le 30/08 : deploy key `odoo-vm101` déclarée sur GitHub et **testée**
   (fetch depuis la VM avec sa propre clé), branche `proxmox` **fusionnée
   dans `main`** (fast-forward) et la VM repasse sur `main` ; inventaire
   Ansible basculé sur `10.40.0.70` (clé ed25519, ProxyJump pve1).
4. ✅ Documents joints validés (SHA1, voir récit) ; ✅ VPS éteint le 29/08
   16:42 UTC puis **résilié le 30/08** ; ✅ TTL remonté à 3600 et export de
   zone rafraîchi le 30/08.
5. Reste (chantiers séparés) : réactiver un jour la relève du mail entrant
   (état `draft` hérité du VPS, voir récit) ; raccordement Keycloak
   ([16-keycloak.md](16-keycloak.md)).

## Restauration

- **VM entière** : vzdump PBS (quotidien 02:00).
- **Base seule** : 7 dumps glissants `pg_dump -Fc` dans `/var/backups/odoo/`
  (timer `odoo-pgdump`, 01:15) —
  `sudo docker compose exec -T db pg_restore -U odoo -d odoo --no-owner < odoo-N.dump`
  sur une base recréée.
- **Applicatif** : sauvegardes du module `auto_backup` dans
  `/srv/odoo/backups` (cron Odoo quotidien).

## Mail et intégrations

| Flux | Détail |
|---|---|
| Sortant | Mailjet `in-v3.mailjet.com:25` STARTTLS (SPF de la zone déjà conforme) ; le 587 fonctionne aussi depuis le VLAN 400 si le 25 devait fermer |
| Entrant | `imap.gmail.com` OAuth, boîte `ticket@teleimagerie.net` |
| Agenda | synchro Google Calendar (12 h) |
| SSO | candidat Keycloak (OAuth) — **chantier séparé**, après migration ([16-keycloak.md](16-keycloak.md)) ; `auth_oauth` et `auth_totp` déjà installés |
