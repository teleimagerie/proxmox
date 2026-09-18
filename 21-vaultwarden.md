# Vaultwarden — coffre de mots de passe d'entreprise (VM 105)

> 📋 **PRÉPARÉ le 18/09/2026 — non déployé.** Cette fiche est le dossier de
> déploiement : décisions arrêtées, runbook complet, configurations prêtes
> ([configs/vault.teleimagerie.net.conf](configs/vault.teleimagerie.net.conf),
> [scripts/dns-vaultwarden.py](scripts/dns-vaultwarden.py),
> [scripts/unbound-override-vaultwarden.py](scripts/unbound-override-vaultwarden.py)).
> Au fil du déploiement, remplacer les 📋 par des ✅ et compléter la
> [checklist de fin de chantier](#checklist-de-fin-de-chantier).

> ✅ vérifié/mesuré · 📋 déclaré/préparé · ⚠️ à vérifier / inconnu

| | |
|---|---|
| Invité | **VM 105** `vaultwarden`, Ubuntu 24.04 (cloud-init), Docker Compose |
| Logiciel | [Vaultwarden](https://www.vaultwarden.net/) (serveur compatible Bitwarden, Rust) ≥ 1.35 + PostgreSQL 17, tous deux en conteneurs |
| Adresse interne | `10.40.0.100/24` (VLAN 400), passerelle et DNS `10.40.0.1` |
| Nom public | `vault.teleimagerie.net` → VIP `57.130.34.122` (proxy-tim), **pas d'AAAA** |
| Ressources | 2 vCPU (`host`), 4 Go RAM (`balloon 0`), 20 Go sur `vm-storage` (Ceph) |
| Accès | SSH par clé uniquement (VPN), interface web publique (voir plus bas) |
| HA | oui — service d'entreprise (`max_restart 3`, `max_relocate 3`) |
| Bascule mesurée | ⚠️ à mesurer au premier test HA |

---

## Le problème que ce service résout

Les mots de passe de l'entreprise vivent aujourd'hui dans des navigateurs,
des fichiers et des mémoires individuelles. Un coffre partagé donne aux
employés un endroit unique, chiffré de bout en bout, pour leurs secrets
personnels et les secrets d'équipe (collections par service), avec des
clients navigateur, mobile et desktop éprouvés — ceux de Bitwarden, dont
Vaultwarden implémente l'API.

L'authentification ne crée pas un nouveau silo : elle passe par le SSO
existant. Vaultwarden supporte OpenID Connect nativement depuis la
version 1.35.0 (août 2025) ; le realm `tim` de Keycloak fait le reste, y
compris la source d'identité Google Workspace déjà brokée en amont
([16-keycloak.md](16-keycloak.md#brokering-google-workspace--en-place-depuis-le-27082026)).

**Décisions du 18/09/2026 :**

- **Pas de SAML.** La demande initiale visait « SAML Google Workspace », mais
  Vaultwarden ne parle qu'OIDC, et Keycloak broker déjà Google **en OIDC**
  (IdP `google`, testé le 27/08/2026, `hostedDomain=teleimagerie.net`, MFA
  porté par Google). Monter un brokering SAML parallèle n'apporterait rien à
  l'utilisateur (même bouton Google) et créerait un second chemin d'identité
  à maintenir. Chaîne retenue :
  `Vaultwarden —OIDC→ Keycloak (realm tim) —OIDC broker→ Google Workspace`.
- **SSO obligatoire** (`SSO_ONLY=true`) : pas de login e-mail + mot de passe
  parallèle, inscriptions fermées hors SSO (`SIGNUPS_ALLOWED=false` ; le
  premier passage SSO crée le compte). Le **master password Bitwarden reste
  requis** : le SSO ne porte que l'authentification, jamais la clé de
  déchiffrement du coffre — c'est le modèle Bitwarden, pas une option.
- **VM, pas CT** : doctrine du cluster pour Docker
  ([18-odoo.md](18-odoo.md#architecture)). Pas de Traefik : TLS
  terminé sur proxy-tim, HTTP clair sur le VLAN 400 (même posture qu'Odoo et
  Keycloak).

---

## Architecture

```
employé (navigateur / app mobile / extension Bitwarden)
   │ https://vault.teleimagerie.net
   ▼
57.130.34.122 (VIP OPNsense) ── VLAN 400/VPN : override Unbound → 10.40.0.10
   │
CT 201 proxy-tim · routeur SNI :443 → vhost vault (127.0.0.1:8443, TLS, PROXY)
   │ http (VLAN 400 uniquement)
   ▼
VM 105 · 10.40.0.100:8080 ── vaultwarden/server ── PostgreSQL 17 (conteneur)
   │                             /data (pièces jointes, clés RSA)
   │ login SSO
   ▼
https://auth.teleimagerie.net/realms/tim (CT 203)
   │ bouton « Google Workspace »
   ▼
Google (audience Interne, hd=teleimagerie.net, MFA Google)
```

Le service est **publiquement accessible sans VPN** — indispensable pour les
clients mobiles et les employés en déplacement. La défense en profondeur :
SSO Keycloak + Google (MFA), master password individuel, chiffrement de bout
en bout (le serveur ne voit jamais les secrets en clair), limitation de débit
Vaultwarden sur `/identity` et `/admin` (IP réelle transmise par `X-Real-IP`).

Si Keycloak ou Google est indisponible : **aucun nouveau login**, mais les
clients déjà connectés gardent leur coffre local chiffré et le déverrouillent
au master password — la panne d'IdP ne prive personne de ses mots de passe.

---

## Runbook de déploiement

⚠️ Chaque commande touchant le cluster suppose le feu vert explicite et le
tunnel `wg-up tim` monté. Aucun secret ci-dessous : ils naissent dans le
gestionnaire de secrets et n'en sortent que vers leur poste opérationnel.

### 1. Créer la VM 105 (sur pve1)

Recette de la VM 103 ([20-mytim-staging.md](20-mytim-staging.md)) :

```bash
qm create 105 --name vaultwarden --cpu host --cores 2 --memory 4096 --balloon 0 \
  --net0 virtio,bridge=vmbr1,tag=400 --agent 1 --serial0 socket --onboot 1 \
  --scsihw virtio-scsi-single
qm disk import 105 /mnt/pve/nas-vm/template/iso/noble-server-cloudimg-amd64.img vm-storage
qm set 105 --scsi0 vm-storage:vm-105-disk-0,discard=on,iothread=1 --boot order=scsi0
qm set 105 --ide2 vm-storage:cloudinit \
  --ipconfig0 ip=10.40.0.100/24,gw=10.40.0.1 --nameserver 10.40.0.1 \
  --ciuser ubuntu --sshkeys /root/.ssh/id_ed25519.pub
qm disk resize 105 scsi0 20G
qm start 105
```

Puis dans la VM : `apt install qemu-guest-agent` (absent de l'image cloud),
provisioning habituel (Docker CE + compose épinglé, fail2ban, ufw : 22 en
VPN, 8080 depuis `10.40.0.10`, 10050 depuis `10.40.0.60`, sshd sans mot de
passe). Vérifications imposées : `resolv.conf → 10.40.0.1`
([piège n° 33](07-pieges.md#33-un-ct-sans-nameserver-hérite-du-résolveur-public-du-nœud)),
`ip route get 10.90.0.2` par `eth0`
([piège n° 37](07-pieges.md#37-une-patte-réseau-sans-route-retour-rend-le-nœud-sourd-sans-rien-bloquer)),
`getent hosts auth.teleimagerie.net → 10.40.0.10`.

HA (après validation du service) :
`ha-manager add vm:105 --state started --max_restart 3 --max_relocate 3`.

### 2. Client OIDC `vaultwarden` dans Keycloak (CT 203)

Patron des clients existants — confidentiel, standard flow seul, PKCE S256,
`webOrigins` vide ([16-keycloak.md](16-keycloak.md#ce-qui-est-raccordé)).
Admin de bootstrap éphémère, détruit aussitôt :

```bash
/opt/keycloak/bin/kc.sh bootstrap-admin user   # compte temporaire
KC=/opt/keycloak/bin/kcadm.sh
$KC config credentials --server http://10.40.0.50:8080 --realm master --user <tmp>
$KC create clients -r tim \
  -s clientId=vaultwarden -s protocol=openid-connect \
  -s publicClient=false -s standardFlowEnabled=true \
  -s implicitFlowEnabled=false -s directAccessGrantsEnabled=false \
  -s serviceAccountsEnabled=false \
  -s 'redirectUris=["https://vault.teleimagerie.net/identity/connect/oidc-signin"]' \
  -s 'webOrigins=[]' \
  -s 'attributes={"pkce.code.challenge.method":"S256","access.token.lifespan":"600"}'
$KC get clients -r tim -q clientId=vaultwarden --fields id,clientId
$KC get clients/<uuid>/client-secret -r tim        # → gestionnaire de secrets
$KC delete users/<uuid-tmp> -r master              # détruire l'admin temporaire
```

Deux réglages qui ne se devinent pas (wiki Vaultwarden, « Enabling SSO
support using OpenId Connect ») :

- **`access.token.lifespan=600` au niveau du client** : le défaut du realm
  (5 min) est plus court que l'expiration attendue par les clients Bitwarden
  → déconnexions intempestives. Override client, pour ne pas toucher le realm.
- **scope `offline_access` demandé par Vaultwarden** (`SSO_SCOPES`) : les
  clients Bitwarden vivent sur des refresh tokens longs. C'est un client
  scope *optionnel* par défaut dans Keycloak — rien à créer, le client le
  demande et l'obtient.

Rien à faire côté IdP `google` ni console Google Cloud : le brokering amont
sert tel quel.

### 3. Compose sur la VM (`/srv/vaultwarden`)

```yaml
# /srv/vaultwarden/compose.yaml
services:
  vaultwarden:
    image: vaultwarden/server:1.35.1   # vérifier la dernière 1.3x au déploiement
    restart: unless-stopped
    depends_on:
      - db
    # Lié à l'IP VLAN 400 : les ports publiés par Docker contournent ufw,
    # ne JAMAIS publier en 0.0.0.0 (18-odoo.md).
    ports:
      - "10.40.0.100:8080:80"
    volumes:
      - ./vw-data:/data
    env_file: .env          # secrets — jamais versionné
    environment:
      DOMAIN: https://vault.teleimagerie.net
      SIGNUPS_ALLOWED: "false"
      INVITATIONS_ALLOWED: "true"
      SSO_ENABLED: "true"
      SSO_ONLY: "true"
      SSO_AUTHORITY: https://auth.teleimagerie.net/realms/tim
      SSO_CLIENT_ID: vaultwarden
      SSO_SCOPES: "email profile offline_access"
      SMTP_HOST: in-v3.mailjet.com
      SMTP_PORT: "587"
      SMTP_SECURITY: starttls
      SMTP_FROM: vaultwarden@teleimagerie.net
      SMTP_FROM_NAME: Coffre TIM
      ORG_CREATION_USERS: bleroux@teleimagerie.net,mcapon@teleimagerie.net
  db:
    image: postgres:17
    restart: unless-stopped
    volumes:
      - ./pg-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: vaultwarden
      POSTGRES_USER: vaultwarden
    env_file: .env          # POSTGRES_PASSWORD
```

`.env` (mode 600, contenu depuis le gestionnaire de secrets) :
`SSO_CLIENT_SECRET`, `POSTGRES_PASSWORD`,
`DATABASE_URL=postgresql://vaultwarden:<mdp>@db:5432/vaultwarden`,
`ADMIN_TOKEN` (hash Argon2 : `docker run --rm -it vaultwarden/server:1.35.1
/vaultwarden hash`), `SMTP_USERNAME`/`SMTP_PASSWORD` (compte Mailjet).

`SSO_AUTHORITY` doit être **exactement** l'issuer du discovery — contrôle :
`curl -s https://auth.teleimagerie.net/realms/tim/.well-known/openid-configuration | jq -r .issuer`.

- `SSO_ONLY` : la page de login n'offre que « Enterprise single sign-on » ;
  le compte naît au premier passage SSO (l'e-mail Google vérifié fait foi).
- `ORG_CREATION_USERS` : seuls les admins créent des organisations — la
  structure des collections partagées reste gouvernée.
- `/admin` est protégé par l'`ADMIN_TOKEN` ; durcissement optionnel plus bas.

### 4. Expéditeur Mailjet

Déclarer `vaultwarden@teleimagerie.net` chez Mailjet **et le valider**
(`POST /v3/REST/sender/<id>/validate`) : un expéditeur non `Active` fait
jeter les mails **en silence** malgré un retour `204` — piège déjà payé par
Keycloak ([16-keycloak.md](16-keycloak.md#e-mail-sortant--smtp-mailjet-en-place-depuis-le-30082026)). SPF/DKIM
de la zone déjà conformes (`include:spf.mailjet.com`). Conclure par un
**mail réel reçu** (bouton de test SMTP de `/admin`).

### 5. Publication : DNS, split-horizon, vhost, certificat

```bash
# pve1 — création du nom (TTL 60 le temps de la mise en service)
scripts/dns-vaultwarden.py status && scripts/dns-vaultwarden.py create

# OPNsense — override interne, sinon le VLAN 400/VPN tombe sur la GUI
# d'OPNsense (piège n° 32)
python3 unbound-override-vaultwarden.py

# CT 201 — vhost + certificat (patron auth/odoo : webroot dans le conteneur)
# 1) poser d'abord le SEUL bloc port 80 de configs/vault.teleimagerie.net.conf
#    (le bloc 443 référence un certificat qui n'existe pas encore : nginx -t échouerait)
certbot certonly --webroot -w /var/www/html -d vault.teleimagerie.net
# 2) poser le vhost complet, activer, recharger
ln -s /etc/nginx/sites-available/vault.teleimagerie.net.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot renew --dry-run

# après validation du service
scripts/dns-vaultwarden.py ttl3600
```

Le nom entre ensuite dans le relevé : zone
([configs/zone-teleimagerie.net](configs/zone-teleimagerie.net)),
[14-noms-de-domaine.md](14-noms-de-domaine.md), tables de
[09-proxy-tim.md](09-proxy-tim.md) — voir la checklist.

### 6. Sauvegardes

- **vzdump quotidien 02:00** : le job `all 1` de
  [configs/jobs.cfg](configs/jobs.cfg) prend la VM 105 **automatiquement**
  (il n'exclut que 102/103/104). Vérifier la première exécution.
- **Dump PostgreSQL applicatif** — patron `kc-pgdump`/Odoo : timer 01:15,
  7 dumps glissants repris par le vzdump :

```ini
# /etc/systemd/system/vw-pgdump.service
[Unit]
Description=Dump quotidien PostgreSQL Vaultwarden (7 glissants)
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'docker compose -f /srv/vaultwarden/compose.yaml exec -T db \
  pg_dump -U vaultwarden vaultwarden | gzip > /var/backups/vaultwarden/vaultwarden-$(date +%%u).sql.gz'

# /etc/systemd/system/vw-pgdump.timer
[Unit]
Description=Dump PostgreSQL Vaultwarden a 01:15
[Timer]
OnCalendar=*-*-* 01:15:00
Persistent=true
[Install]
WantedBy=timers.target
```

`exec -T` convient ici (postgres tourne déjà — le
[piège n° 36](07-pieges.md#36-docker-compose-exec-court-circuite-lentrypoint-de-limage-odoo)
vise les commandes qui dépendent de l'entrypoint). Le volume `vw-data/`
(pièces jointes, clés RSA des jetons) est couvert par le vzdump snapshot.
**Restauration à tester** une fois le service peuplé
([10-sauvegardes.md](10-sauvegardes.md)).

### 7. Supervision Zabbix

Agent passif dans la VM + hôte certificat `cert-vault.teleimagerie.net`,
sur le patron idempotent de
[scripts/zabbix-provision-staging.py](scripts/zabbix-provision-staging.py) —
y compris la macro `{$PVE.VM.MEMORY.PUSE.MAX.WARN:"qemu/105"}` = 200 sur
`cluster-pve` (VM sans balloon,
[piège n° 42](07-pieges.md#42-une-vm-sans-balloon-est-toujours-pleine-pour-lhyperviseur-et-une-escalade-sans-fin-transforme-un-faux-positif-en-80-mails)).

---

## Vérification de bout en bout

```bash
# depuis l'extérieur ET depuis le VLAN 400/VPN (piège n° 32)
curl -sI https://vault.teleimagerie.net/alive        # 200, date
curl -sI http://vault.teleimagerie.net | head -1     # 301
```

1. Web-vault : « Enterprise single sign-on » → page Keycloak `tim` → bouton
   Google → compte `@teleimagerie.net` → création du compte, définition du
   master password, coffre ouvert.
2. Un login e-mail + master password direct est **refusé** (`SSO_ONLY`).
3. Extension navigateur + app mobile pointées sur
   `https://vault.teleimagerie.net` : login SSO, synchronisation, notification
   temps réel (créer un élément sur le web, le voir apparaître sur mobile),
   session > 10 min sans déconnexion (lifespan du jeton).
4. Mail réel reçu (test SMTP de `/admin`) — expéditeur Mailjet `Active`.
5. Lendemain : `vw-pgdump` présent, VM 105 dans le vzdump de 02:00, hôtes
   Zabbix verts.
6. Test HA : migration à chaud de la VM 105, coupure mesurée à consigner ici.

---

## Risques et limites

- **Périmètre HDS** : le coffre donnera accès aux applications de santé — il
  relève de la même logique que Keycloak
  ([12-architecture-hds.md](12-architecture-hds.md#les-deux-sites)) : hébergé
  sur le cluster, donc en offre HDS OVH (📋 déclaré le 29/08/2026), mais la
  couverture est **à consigner dans la revue contractuelle**.
- **Master password oublié = coffre perdu** : chiffrement de bout en bout,
  aucune récupération serveur. À dire explicitement dans la communication de
  lancement ; l'« emergency access » Bitwarden peut compléter, à instruire.
- **Keycloak/Google indisponible** : pas de nouveaux logins (19 s mesurées
  sur une bascule HA du CT 203 ; une vraie panne dure davantage). Les clients
  connectés déverrouillent leur cache local — communiquer ce comportement.
- **`/admin` exposé publiquement** (protégé par `ADMIN_TOKEN` Argon2 +
  limitation de débit) : restreindre le `location /admin` du vhost aux IP
  VPN est le même durcissement optionnel que la console Keycloak
  ([06-reste-a-faire.md](06-reste-a-faire.md#10-authentification-centralisée--suites-du-déploiement-du-27082026)).
- **Version à suivre** : le support OIDC est jeune (1.35.0, août 2025) —
  surveiller les releases <https://github.com/dani-garcia/vaultwarden/releases>
  et rejouer la matrice de vérification après chaque montée.

## Checklist de fin de chantier

- [ ] VM 105 créée, provisionnée, HA ajoutée, `make controle` sans écart
- [ ] Client `vaultwarden` créé (realm `tim`), secret vaulté, admin temporaire détruit
- [ ] Compose lancé, `/alive` → 200 en local
- [ ] Expéditeur Mailjet validé, mail de test reçu
- [ ] DNS créé + override Unbound + vhost + certificat, `certbot renew --dry-run` OK
- [ ] Matrice de vérification ci-dessus déroulée (extérieur + intérieur)
- [ ] `vw-pgdump` en place, première sauvegarde vzdump constatée, restauration testée
- [ ] Zabbix : hôte agent + `cert-vault.teleimagerie.net` + macro mémoire 200
- [ ] Relevés mis à jour : [configs/zone-teleimagerie.net](configs/zone-teleimagerie.net),
      [09-proxy-tim.md](09-proxy-tim.md) (tables « Ce qui est publié » et « Certificats »),
      [14-noms-de-domaine.md](14-noms-de-domaine.md),
      [16-keycloak.md](16-keycloak.md) (tables raccordé + clients),
      [README.md](README.md) (état en une page, compte de machines),
      [12-architecture-hds.md](12-architecture-hds.md) (revue contractuelle)
- [ ] `make liens` propre, cette fiche passée de 📋 à ✅ avec les chiffres réels
- [ ] Communication employés : lancement, master password irrécupérable,
      comportement hors-ligne, organisations/collections par service
