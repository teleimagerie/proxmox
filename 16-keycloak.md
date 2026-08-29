# `keycloak` — serveur d'authentification centralisée

Conteneur LXC **203**, Debian 13, **Keycloak 26.7.2** (OpenJDK 21, PostgreSQL 17).
Déployé le 27/08/2026. C'est l'**IdP** (fournisseur d'identité) du système : les
applications ne vérifient plus les mots de passe elles-mêmes, elles délèguent en
OpenID Connect (et à terme SAML) à `https://auth.teleimagerie.net`.

| | |
|---|---|
| Adresse interne | `10.40.0.50/24` (VLAN 400), passerelle `10.40.0.1` |
| Nom public | `auth.teleimagerie.net` — servi **derrière proxy-tim**, pas de VIP dédiée |
| Ressources | 2 vCPU, 4 Go RAM, disque 20 Go sur Ceph |
| Accès | `ssh root@10.40.0.50` depuis un nœud ayant accès au VLAN 400 (clés du cluster) |
| Haute dispo | ressource HA depuis le 27/08/2026 (`max_restart 3`, `max_relocate 3`) |
| Bascule mesurée | **~19 s** d'indisponibilité (voir [Bascule HA](#bascule-ha-mesurée)) |
| Realms | `master` (admin seul) · **`tim`** (tout le reste) |

> ⚠️ **Décision de sécurité du 27/08/2026** : pour les connexions OIDC, le
> second facteur est porté par Keycloak (TOTP obligatoire à la première
> connexion du realm `tim`), plus par Proxmox. `matt@pve` et `root@pam`
> (avec leur TOTP Proxmox) sont conservés comme **comptes de secours** si
> l'IdP est indisponible — voir [04-securite.md](04-securite.md#comptes).

---

## Le problème que ce service résout

Chaque brique avait son propre référentiel de comptes : realms `pam`/`pve` sur
Proxmox, comptes locaux PBS, users locaux headscale, root OPNsense, comptes
Windows sur pacs03 et côté TELLIS. Aucun partage, aucun SSO, un second facteur
seulement sur Proxmox.

Keycloak centralise comptes, mots de passe et TOTP. Une application raccordée
redirige le navigateur vers `auth.teleimagerie.net`, l'utilisateur s'y
authentifie, et revient avec un jeton signé. Une session IdP ouverte sert à
toutes les applications raccordées : c'est le SSO.

---

## Architecture

```
            navigateur (externe)                navigateur / service (interne VLAN 400)
                    │                                        │
      DNS public : auth → 57.130.34.122         DNS interne (Unbound OPNsense) :
                    │                              auth → 10.40.0.10  [split-horizon]
                    ▼                                        │
          VIP 57.130.34.122:443                              │
                    │ (rdr OPNsense)                         │
                    ▼                                        ▼
          ┌──────────────────────────────────────────────────────┐
          │  proxy-tim (CT 201) — routeur SNI :443               │
          │  auth.teleimagerie.net → 127.0.0.1:8443 (défaut)     │
          │  vhost auth : TLS Let's Encrypt, en-têtes X-Forwarded │
          └──────────────────────────┬───────────────────────────┘
                                     ▼
                        http://10.40.0.50:8080 (VLAN 400)
                        Keycloak (CT 203) + PostgreSQL local
```

Deux chemins pour un même nom :

- **De l'extérieur**, le trafic entre par la VIP du proxy comme pacs-secours.
- **De l'intérieur**, un override Unbound sur OPNsense envoie `auth` droit sur
  le proxy (`10.40.0.10`), car joindre la VIP publique depuis le VLAN 400
  aboutit sur l'interface web d'OPNsense, pas sur le proxy —
  [piège n° 32](07-pieges.md#32-joindre-la-vip-122-depuis-lintérieur-aboutit-sur-la-gui-dopnsense).
  L'override appartient à [08-opnsense.md](08-opnsense.md#résolution-interne--override-unbound) ;
  les CT doivent utiliser `10.40.0.1` comme résolveur —
  [piège n° 33](07-pieges.md#33-un-ct-sans-nameserver-hérite-du-résolveur-public-du-nœud).

Le flux proxy → Keycloak est en HTTP clair **sur le VLAN 400 uniquement**
(même posture que proxy → pacs03). Keycloak est configuré
`proxy-headers=xforwarded` et fait confiance aux en-têtes posés par le vhost.

---

## Ce qui est raccordé

| Service | Mécanisme | Compte créé | Repli si IdP indisponible |
|---|---|---|---|
| **Proxmox VE** | realm `keycloak` (openid, `username-claim username`, `autocreate 0`) | `matt@keycloak` et `brtrnd@keycloak` (27/08/2026), rôle Administrator sur `/` | `matt@pve`, `root@pam` + TOTP |
| **PBS** | realm `keycloak` (openid, idem) | `matt@keycloak` et `brtrnd@keycloak` (27/08/2026), ACL Admin sur `/` | `root@pam` local à la VM |
| **headscale** | section `oidc` de la config — voie d'**enrôlement supplémentaire** | users OIDC créés à la volée | users locaux + clés de pré-enrôlement inchangés |

> ✅ **Connexions réelles vérifiées le 27/08/2026** : login `matt@keycloak`
> sur Proxmox à 09:29 UTC (`successful openid auth`, journal `pvedaemon` de
> pve1, mot de passe temporaire changé et TOTP enrôlé), puis **PBS vers
> 10:00 sans nouvelle saisie** — même session SSO Keycloak servant les deux
> clients (vérifié par `kcadm get clients/<id>/user-sessions`). `brtrnd`
> s'est aussi authentifié (session client `proxmox` de 09:45) ;
> `brtrnd@keycloak` a été créé côté PVE puis promu **Administrator sur `/`**
> le jour même. Reste headscale à éprouver (au prochain enrôlement de nœud).
>
> Validation finale du 27/08/2026, après les pièges 34-35 : les trois chemins
> re-testés par l'utilisateur — page de login `tim` sur la racine, login
> `matt` + TOTP (flux `browser-totp`), login Google sans enrôlement TOTP.
>
> Les connexions réussies ne laissent **aucune trace** dans les journaux PBS
> ni Keycloak par défaut : pour vérifier, interroger les sessions actives
> (`kcadm get clients/<id>/user-sessions -r tim`) ou activer la conservation
> des événements de connexion dans le realm (*Realm settings → Sessions*).

Clients OIDC du realm `tim` (confidentiels, flux standard seul) :

| Client | Redirect URIs |
|---|---|
| `proxmox` | `https://pve{1,2,3}.infra.teleimagerie.net:8006/*` |
| `pbs` | `https://10.30.0.20:8007/*`, `https://10.40.0.20:8007/*`, `https://localhost:8007/*` (l'interface s'ouvre par tunnel SSH — [10-sauvegardes.md](10-sauvegardes.md#accès-à-linterface-pbs)) |
| `headscale` | `https://headscale.teleimagerie.net/oidc/callback` |

> ⚠️ **headscale ne démarre pas si l'issuer est injoignable** : la section
> `oidc` est validée au démarrage (constaté le 27/08/2026, crash-loop tant que
> la résolution interne n'était pas en place). Si Keycloak est durablement
> mort, commenter la section `oidc` de `/etc/headscale/config.yaml` et
> redémarrer headscale — les nœuds déjà enrôlés n'en ont pas besoin.

---

## Comptes, realm, secrets

- Realm **`tim`** : protection force brute active, auto-inscription fermée,
  **TOTP exigé à chaque connexion par mot de passe** — flux navigateur dédié
  `browser-totp` (copie du flux `browser`, sous-flux *Conditional 2FA* passé
  en *Required*, conditions retirées) : un compte local sans TOTP se le voit
  imposer à l'enrôlement. Les connexions **via Google n'y passent pas** —
  leur MFA est porté par Google ([piège n° 34](07-pieges.md#34-laction-requise-par-défaut-simpose-aussi-aux-arrivants-google)).
- Utilisateurs initiaux : `matt` (mcapon@teleimagerie.net) et `brtrnd`
  (bleroux@teleimagerie.net) — tous deux connectés le 27/08/2026, mots de
  passe temporaires remplacés et TOTP enrôlés.
- Console d'administration : `https://auth.teleimagerie.net/admin/`, compte
  `admin` du realm `master`. Elle est exposée publiquement comme le reste ;
  la restreindre aux IP d'administration dans le vhost est une option de
  durcissement notée dans [06-reste-a-faire.md](06-reste-a-faire.md).
- **Les URL qui comptent** : la racine `https://auth.teleimagerie.net/`
  redirige (302 posée dans le vhost le 27/08/2026) vers la **console de
  compte du realm `tim`** — `/realms/tim/account/` — où chaque utilisateur
  gère profil, TOTP, sessions et comptes liés. Sans cette redirection,
  Keycloak envoie la racine vers la console d'admin du realm `master`, ce qui
  déroute les utilisateurs normaux. La page de login `tim` (avec le bouton
  Google) n'apparaît que via une application ou cette console de compte.
- **Secrets** : le fichier de déploiement `/etc/pve/priv/keycloak/credentials`
  a été recopié dans le **gestionnaire de secrets puis détruit des serveurs
  le 27/08/2026**. Ne subsistent que les copies opérationnelles, chacune à
  son poste : mot de passe base dans `keycloak.conf` (CT 203), secrets
  clients dans `/etc/pve/domains.cfg`, le `domains.cfg` de PBS et
  `/etc/headscale/oidc_secret` — tableau dans
  [04-securite.md](04-securite.md#secrets--où-ils-vivent). Mot de passe admin
  perdu = re-bootstrap : `kc.sh bootstrap-admin user` sur le CT 203, puis
  `kcadm set-password` sur le compte `admin` et suppression de l'admin
  temporaire.

---

## Les fichiers (CT 203)

| Fichier | Rôle |
|---|---|
| `/opt/keycloak` | lien vers `/opt/keycloak-26.7.2` (bascule de version par le lien) |
| `/opt/keycloak/conf/keycloak.conf` | config — copie **sans secret** dans [configs/keycloak.conf](configs/keycloak.conf) |
| `/etc/systemd/system/keycloak.service` | unité — copie dans [configs/keycloak.service](configs/keycloak.service) |
| `/etc/systemd/system/kc-pgdump.{service,timer}` | dump PostgreSQL quotidien 01:15 |
| `/var/backups/keycloak/keycloak-<1..7>.sql.gz` | 7 dumps glissants (un par jour de semaine), repris par le vzdump de 02:00 |

**Mise à jour de version** : télécharger le tarball, `tar xzf` dans `/opt`,
`chown -R keycloak:`, rejouer `kc.sh build --db=postgres`, basculer le lien
`/opt/keycloak`, `systemctl restart keycloak`. Retour arrière = remettre le
lien sur l'ancien répertoire (attention aux migrations de schéma : vérifier
les notes de version avant tout saut majeur). Keycloak publie des correctifs
de sécurité fréquents — surveiller <https://www.keycloak.org/blog>.

**Restauration** : le vzdump restaure le CT entier ; pour la seule base,
`gunzip -c keycloak-N.sql.gz | runuser -u postgres -- psql keycloak` sur une
base vidée. Restauration à tester après toute évolution majeure
([10-sauvegardes.md](10-sauvegardes.md)).

---

## Certificat

| Certificat | Emplacement | Échéance | Renouvelé par |
|---|---|---|---|
| `auth.teleimagerie.net` | `/etc/letsencrypt/live/auth.teleimagerie.net/` dans le **CT 201** | **25/11/2026** | certbot du conteneur (webroot, patron pacs-secours) |

Le bloc port 80 du vhost laisse passer `/.well-known/acme-challenge/` en local
— **indispensable** : sans lui le défi serait redirigé vers Keycloak et le
renouvellement casserait silencieusement. Vhost archivé dans
[configs/auth.teleimagerie.net.conf](configs/auth.teleimagerie.net.conf).

Le DNS a été basculé le 27/08/2026 par [scripts/bascule-auth.py](scripts/bascule-auth.py)
depuis pve1 (`status|switch|revert`) : l'A pointait vers `146.59.233.102`, un
**ancien VPS résilié** (anomalie de [14-noms-de-domaine.md](14-noms-de-domaine.md)
soldée), et l'AAAA a été supprimé — le proxy n'a pas d'IPv6 de service.

---

## Bascule HA mesurée

Test du 27/08/2026 (pve1 → pve2, sonde externe à 1 s sur le well-known) :
**19 s d'indisponibilité** — ~12 s d'arrêt/redémarrage du CT (*restart
migration*, comme tout CT), puis ~7 s de `502` le temps que la JVM serve.
Pendant cette fenêtre, **toute authentification fédérée échoue** ; les
sessions déjà ouvertes et les jetons déjà émis survivent (sessions persistées
en base). Les applications raccordées restent utilisables pour qui est déjà
connecté ; seuls les nouveaux logins attendent.

---

## Candidats au raccordement — étude du 27/08/2026

État : ✅ raccordé · 📋 déclaré/à instruire · ⚠️ inconnu

| Application | Protocole possible | État |
|---|---|---|
| Proxmox VE, PBS, headscale | OIDC | ✅ fait |
| **Google Workspace** (brokering amont) | OIDC | ✅ en place et **testé en réel** le 27/08/2026 (compte Workspace technique : passage Google, création à la volée dans `tim` — compte de test supprimé après validation) |
| **MyTIM** (appli interne de gestion) | OIDC à intégrer dans l'appli | ⚠️ hébergement/techno à documenter — vérifier si c'est `app`/`gestion` → `51.210.24.59` ; **meilleur candidat** après l'infra si développée en interne. Identifiants utilisateurs = e-mail → voir [Identités par application](#identités-par-application) |
| Zabbix (`zabbix.teleimagerie.net`) | SAML ou LDAP | ⚠️ accès à collecter |
| Odoo (`odoo.teleimagerie.net`) | OAuth/LDAP natifs | ⚠️ accès à collecter |
| CRM, e-learning, bastion, app/gestion | à déterminer | ⚠️ hors périmètre du dépôt |
| Syngo Via (Siemens) · Vue PACS (Philips) · RIS VENUS (Softway) · TSplus | selon capacités éditeur (souvent SAML/OIDC dans les versions récentes) | 📋 cible à terme — à instruire éditeur par éditeur via la [checklist TELLIS](13-tellis.md#checklist-de-collecte) |
| Microsoft 365 / Entra ID (brokering amont) | OIDC | 📋 possible plus tard, même mécanique que Google |

### Brokering Google Workspace — en place depuis le 27/08/2026

Concept : Keycloak reste l'IdP que voient les applications ; Google n'est
qu'une **source d'identité en amont**. Les utilisateurs bureautiques cliquent
« Google Workspace » sur la page de login (MFA porté par Google), les admins
infra gardent leurs comptes locaux + TOTP Keycloak.

Configuration retenue (« le plus sécurisé », décision du 27/08/2026) :

| Réglage | Valeur | Effet |
|---|---|---|
| Application Google Auth Platform | audience **Interne** | seuls les comptes du Workspace passent l'écran Google |
| `hostedDomain` | `teleimagerie.net` | `hd` imposé à l'aller **et vérifié au retour** par Keycloak |
| PKCE | activé, `S256` | vérifié sur le fil (`code_challenge_method=S256`) |
| `storeToken` | `false` | Keycloak ne conserve aucun jeton Google |
| `trustEmail` | `true` | e-mails du domaine vérifiés par Google, pas de re-vérification |
| Première connexion | flux `first broker login` par défaut | e-mail inconnu → création à la volée ; e-mail d'un compte existant → **liaison avec confirmation** (mot de passe local exigé) |
| Comptes admin (`matt`, `brtrnd`) | **ne pas lier à Google** | décision organisationnelle : l'accès infra reste sur les comptes locaux + TOTP Keycloak ; le flux de confirmation empêche de toute façon une liaison sans le mot de passe local |
| TOTP Keycloak des arrivants Google | **non demandé** | leur MFA est celui de Google — corrigé le 27/08/2026, [piège n° 34](07-pieges.md#34-laction-requise-par-défaut-simpose-aussi-aux-arrivants-google) |

Client OAuth : projet Google Cloud du Workspace, ID
`990230308603-…apps.googleusercontent.com`, URI de retour
`https://auth.teleimagerie.net/realms/tim/broker/google/endpoint`. Le secret
client vit dans le **gestionnaire de secrets** (copie opérationnelle dans la
base Keycloak, config de l'IdP `google`) — la copie de transit sur pve1 a été
détruite après usage.

> La configuration a été posée via un **admin temporaire de bootstrap**
> (`kc.sh bootstrap-admin user`, supprimé aussitôt) : le mot de passe admin
> n'a pas eu à quitter le gestionnaire.

---

## Identités par application

Le même humain porte des identifiants différents selon les applications.
Principe Keycloak : **un seul compte, plusieurs présentations** — le compte
porte les identités en **attributs**, et chaque client reçoit la sienne dans
son jeton via un *protocol mapper* posé au raccordement. On ne renomme
jamais personne, ni dans Keycloak ni dans l'application.

Attributs déclarés dans le profil du realm `tim` le 29/08/2026 (édition
**admin uniquement** — un utilisateur ne modifie pas sa propre identité
RIS ; visibles en lecture seule dans sa console de compte) :

| Application | Identifiant (ex. matt) | Source dans le jeton |
|---|---|---|
| MyTIM, MyIsoteam | `mcapon@teleimagerie.net` | revendication standard `email` — **aucun attribut ni mapper à créer** |
| Xplore RIS + Xplore PACS central | `matthieu` | attribut `login_xplore` |
| Vue PACS Philips | `mcapon` | attribut `login_pacs_philips` |
| VoIP 3CX | `1001` | attribut `extension_3cx` |

Renseignés sur `matt` le 29/08/2026 ; `brtrnd` : à compléter quand ses
identifiants seront connus.

**Le jour d'un raccordement**, après création du client, poser le mapper qui
place l'attribut dans la revendication que l'application lit :

```bash
# OIDC : l'application lit preferred_username -> on le remplace par l'attribut
kcadm.sh create clients/<id-client>/protocol-mappers/models -r tim \
  -s name=identite-metier -s protocol=openid-connect \
  -s protocolMapper=oidc-usermodel-attribute-mapper \
  -s 'config."user.attribute"=login_xplore' \
  -s 'config."claim.name"=preferred_username' \
  -s 'config."id.token.claim"=true' -s 'config."access.token.claim"=true'
# SAML : meme logique avec le NameID (mapper "User Attribute Mapper For NameID")
```

Deux notes pour éviter des heures perdues :

- **Se connecter** à Keycloak accepte le nom d'utilisateur **ou** l'e-mail —
  pas d'autres alias nativement. Sans importance en SSO : on ne tape son
  identifiant qu'une fois, chez Keycloak, plus jamais dans les applications.
- **Vérifier des attributs avec l'API brute**, pas avec
  `kcadm get users/<id> --fields attributes` : ce filtre affiche `{}` même
  quand les attributs existent (constaté le 29/08/2026 —
  `GET /admin/realms/tim/users/<id>` sans filtre montre la réalité).

---

## E-mail sortant — SMTP Mailjet (préparé le 29/08/2026, ⚠️ en attente de la clé)

**Ce que le mail fait — et ne fait pas — dans Keycloak** : le TOTP n'a
besoin d'aucun e-mail (généré hors ligne par l'application — enrôlé pour
`matt` et `brtrnd` sans SMTP). Le SMTP sert à trois choses, toutes absentes
aujourd'hui :

1. **« Mot de passe oublié »** (`resetPasswordAllowed`, désactivé faute de
   SMTP) — aujourd'hui un mot de passe perdu = intervention admin, et pour
   le compte `admin` lui-même la procédure de re-bootstrap. Le lien de
   réinitialisation **ne contourne pas le TOTP** au login ;
2. **Onboarding** : l'e-mail « définissez votre mot de passe et enrôlez
   votre TOTP » (*execute actions email*) — remplace la transmission
   manuelle de mots de passe temporaires faite pour les deux premiers
   comptes ; indispensable à l'arrivée des utilisateurs MyTIM ;
3. Vérifications d'adresse et notifications, si activées un jour.

**Le domaine est déjà prêt** (vérifié le 29/08/2026 dans la zone) : SPF
`include:spf.mailjet.com`, DKIM `mailjet._domainkey` et TXT de validation
Mailjet présents — tout envoi `@teleimagerie.net` via Mailjet passera.

### Procédure de reprise, dès que la clé existe

1. Créer chez Mailjet une **clé API dédiée à Keycloak** si le plan le permet
   (révocable indépendamment), sinon la clé principale. La clé API sert de
   nom d'utilisateur SMTP, la clé secrète de mot de passe.
2. La déposer sur pve1 (gestionnaire de secrets d'abord) :
   ```bash
   install -m 600 /dev/null /root/.secrets/mailjet
   cat > /root/.secrets/mailjet <<'FIN'
   MJ_APIKEY=la-cle-api
   MJ_SECRET=la-cle-secrete
   FIN
   ```
3. Configurer le realm `tim` (admin de bootstrap éphémère, patron habituel) :
   ```bash
   kcadm.sh update realms/tim -s 'smtpServer={"host":"in-v3.mailjet.com",
     "port":"587","starttls":"true","auth":"true","ssl":"false",
     "user":"<MJ_APIKEY>","password":"<MJ_SECRET>",
     "from":"auth@teleimagerie.net",
     "fromDisplayName":"Authentification Téléimagerie"}'
   kcadm.sh update realms/tim -s resetPasswordAllowed=true
   ```
   Expéditeur retenu : `auth@teleimagerie.net` (la boîte n'a pas besoin
   d'exister, le domaine est validé chez Mailjet) — changer si une adresse
   de réponse est souhaitée.
4. **Test réel** : page de login `tim` → « Mot de passe oublié ? » avec
   `matt` → le mail doit arriver sur `mcapon@teleimagerie.net`, le lien
   fonctionner, et le TOTP rester exigé au login suivant. Détruire ensuite
   la copie de transit (`shred -u /root/.secrets/mailjet`) — la clé vit
   alors dans le gestionnaire + la config du realm (base Keycloak).
5. Mettre à jour le tableau des secrets de
   [04-securite.md](04-securite.md#secrets--où-ils-vivent) et cette section.

Le realm `master` reste sans SMTP (seul le compte `admin` y vit, sans
e-mail) — à équiper le jour où on voudra des notifications sur ce compte.

---

## Diagnostic

```bash
# la chaîne publique complète (VIP → routeur SNI → vhost → CT 203)
curl -sS --resolve auth.teleimagerie.net:443:57.130.34.122 -o /dev/null \
     -w '%{http_code}\n' https://auth.teleimagerie.net/realms/tim/.well-known/openid-configuration

# la vue interne (depuis un CT du VLAN 400) : doit résoudre 10.40.0.10
getent hosts auth.teleimagerie.net

# certificat présenté et échéance
echo | openssl s_client -connect 57.130.34.122:443 -servername auth.teleimagerie.net 2>/dev/null \
     | openssl x509 -noout -subject -enddate

# état du service et derniers événements (depuis le nœud portant le CT)
pct exec 203 -- systemctl status keycloak --no-pager
pct exec 203 -- journalctl -u keycloak -n 30 --no-pager

# les realms OIDC déclarés côté consommateurs
pveum realm list                                   # sur un nœud
ssh root@10.30.0.20 proxmox-backup-manager openid list   # PBS

# dumps de la base
pct exec 203 -- ls -la /var/backups/keycloak/
```

---

## Risques et limites

- **SPOF fonctionnel** : 19 s de coupure d'authentification à chaque bascule
  HA, et OPNsense (~2 min de bascule) reste devant tout. Parade : comptes de
  secours locaux sur chaque service raccordé — ne jamais les supprimer.
- **Aucune supervision** ([06-reste-a-faire.md](06-reste-a-faire.md#4-supervision)) :
  une panne de Keycloak ne se verrait qu'à la première connexion ratée. À
  raccorder au chantier supervision (l'échéance du certificat et le timer
  `kc-pgdump` aussi).
- **Périmètre HDS** : un IdP qui porte l'authentification d'accès aux données
  de santé entre dans le périmètre — question contractuelle à trancher, voir
  [12-architecture-hds.md](12-architecture-hds.md#où-lire-le-détail).
- **Les utilisateurs finaux (radiologues) sont côté TELLIS** : leur
  raccordement suppose de compléter la collecte
  [13-tellis.md](13-tellis.md#checklist-de-collecte), hors de ce chantier.
