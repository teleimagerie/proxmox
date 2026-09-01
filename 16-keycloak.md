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
| **Odoo** | module OCA `auth_oidc` (flux code + PKCE S256), provider `TIM SSO` en base | aucun — rapprochement manuel par e-mail (`oauth_uid`), pilote `mcapon@teleimagerie.net` le 31/08/2026 | formulaire local mot de passe, toujours affiché |
| **MyTIM** (`app.teleimagerie.net`) | drenso/symfony-oidc-bundle (flux code + PKCE S256, claims lus dans l'id_token, JWKS en cache 1 h), client `mytim` du realm `tim` | aucun — rapprochement par e-mail (claim `email`, `emailVerified` exigé), aucun provisioning ; mode piloté par la clé AppConfig `sso_login_mode` (`local+sso` posée sur tim-prod le 01/09/2026 — ⚠️ callback en échec tant que la prod n'est pas redéployée avec le secret vaulté, voir *Risques et limites*) | formulaire local, toujours affiché en V1 (mode `disabled` = rollback instantané sans redéploiement) |

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
| `mytim` (créé le 30/08/2026, PKCE S256 imposé ; audité le 01/09/2026 : confidentiel, standard flow seul, scopes `email`/`profile` ; secret vaulté dans l'Ansible du dépôt gestion le 01/09/2026) | `https://app.teleimagerie.net/oidc/callback` |
| `mytim-staging` (créé le 30/08/2026, PKCE S256 imposé — sert staging **et** dev) | `https://app.staging.teleimagerie.net/oidc/callback`, `https://app.localhost/oidc/callback`, `http://app.localhost/oidc/callback` |
| `odoo` (créé le 31/08/2026, PKCE S256 imposé) | `https://odoo.teleimagerie.net/auth_oauth/signin` |

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
`chown -R keycloak:`, rejouer `kc.sh build --db=postgres`, **recopier le
thème** (`cp -a /opt/keycloak-<ancienne>/themes/tim /opt/keycloak-<nouvelle>/themes/`
— il vit dans le répertoire versionné, voir
[Personnalisation](#personnalisation--thème-de-connexion-tim)), basculer le
lien `/opt/keycloak`, `systemctl restart keycloak`. Retour arrière = remettre le
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
| **MyTIM** (appli interne de gestion) | OIDC | 🔶 **prod TIM en cours de raccordement (01/09/2026)** : tenant `app.teleimagerie.net`, realm `tim`, client `mytim` audité et secret vaulté le 01/09/2026, clé `local+sso` posée (bouton SSO + formulaire local en repli, internes `@teleimagerie.net` d'abord) — **reste le redéploiement prod avec le secret** (le `.env` prod porte encore `OIDC_CLIENT_SECRET=` vide) puis la validation pilotes. Intégration développée le 29/08/2026 (Symfony 7.4/FrankenPHP chez OVH, `app`/`gestion` → `51.210.24.59`, drenso/symfony-oidc-bundle, rapprochement par e-mail, aucun provisioning), clients `mytim` + `mytim-staging` créés le 30/08/2026 (tableau ci-dessus). 📋 **Reste** : tenant **Isoteam** (`app.isoteam.mn`) — créer le **realm `isoteam`** (copie de `tim` : force brute, `browser-totp`, broker Google avec redirect URI `…/realms/isoteam/broker/google/endpoint` à ajouter au client OAuth Google) et ses **2 clients** (`mytim`, `mytim-staging`) ; puis mode `sso-default` + médecins (phase ultérieure). Ce dépôt = relevé de ce qui est en place ; **runbook** (script kcadm, vaultage du secret, matrice de validation, phasage) : `docs/technique/sso-keycloak.md` du dépôt gestion |
| Zabbix (`zabbix.teleimagerie.net`) | SAML ou LDAP | 📋 accès SSH collecté le 29/08/2026 (clé, compte `ubuntu` sur le VPS `vps-41b1229b`) — raccordement à instruire après la migration vers le cluster (17-zabbix.md à venir) |
| **Odoo** (`odoo.teleimagerie.net`) | OIDC | ✅ **raccordé le 31/08/2026** — module OCA `auth_oidc` (flux code + PKCE S256, signature id_token vérifiée par JWKS), client `odoo`, rapprochement par e-mail, aucun provisioning, formulaire local en repli. Détail : [18-odoo.md](18-odoo.md#sso-keycloak) |
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

## Personnalisation — thème de connexion `tim`

Depuis le 30/08/2026, le realm `tim` est en **français par défaut**
(internationalisation activée, `fr` + `en` proposés) et sert un **thème de
connexion maison** calqué sur la page de login de gestion/MyTIM : **logo TIM
dans le bandeau haut** (125 px, centré — il remplace le nom du realm, servi
en blanc par le thème standard donc invisible sur fond clair), bleu `#1e3a8a`
sur fond `#eff6ff` — valeurs et logo repris du projet gestion
(`assets/styles/themes/tim.css`, `assets/images/logos/logo_main_tim.png`).
`displayName` du realm : **TIM** (onglet « Se connecter à TIM », titre
« Connexion à TIM »).

Mécanique : le thème **hérite de `keycloak.v2`** et ne pose qu'une surcouche
CSS + un fichier de messages — aucune structure HTML touchée, les pages
(TOTP, Google, reset…) restent celles de Keycloak. Fichiers dans
`/opt/keycloak/themes/tim/login/` sur le CT 203, copie conforme dans
[configs/keycloak-theme-tim/](configs/keycloak-theme-tim/).

> ⚠️ **Le thème vit dans le répertoire versionné**
> (`/opt/keycloak-26.7.2/themes/`) : à chaque mise à jour de Keycloak, le
> recopier dans la nouvelle version (étape ajoutée à la routine ci-dessus).
> Oubli = retour silencieux au thème standard au premier restart.
> Après toute modification du thème : `systemctl restart keycloak`
> (le cache de thèmes est actif en production) — **et renommer le fichier
> CSS** (`tim-2.css` → `tim-3.css`…, référencé dans `theme.properties`) :
> les ressources `/resources/` sont servies avec **30 jours de cache
> navigateur** et une URL stable — sans renommage, les clients gardent
> l'ancienne version (constaté le 30/08/2026 : deux déploiements invisibles
> pour l'utilisateur).

**Rendu validé visuellement par l'utilisateur le 30/08/2026** (logo dans le
bandeau, textes « TIM », après le correctif de cache `tim-2.css`).
Vérifié le 30/08/2026 sur la page réelle : `lang="fr"`, onglet « Se connecter
à TIM », `tim.css` et `logo.png` servis en 200, formulaire en français,
bouton Google Workspace présent. Premier essai raté instructif : un
`::before` posé dans le conteneur flex du titre n'a **aucune largeur** (logo
invisible) — le logo vit désormais dans `#kc-header-wrapper`
(texte masqué par `text-indent`, image en fond), ce qui règle du même coup
le nom du realm illisible en blanc.

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
  `kcadm get … --fields <champ-carte>` — le filtre affiche `{}` pour
  **toute carte** (`attributes`, `smtpServer`… constaté deux fois, les
  29 et 30/08/2026) même
  quand les attributs existent (constaté le 29/08/2026 —
  `GET /admin/realms/tim/users/<id>` sans filtre montre la réalité).

---

## E-mail sortant — SMTP Mailjet (en place depuis le 30/08/2026)

**Ce que le mail fait — et ne fait pas — dans Keycloak** : le TOTP n'a
besoin d'aucun e-mail (généré hors ligne par l'application). Le SMTP sert
au **« mot de passe oublié »**, à l'**onboarding** (*execute actions email* :
« définissez votre mot de passe et enrôlez votre TOTP » — remplace la
transmission manuelle de mots de passe temporaires, indispensable à
l'arrivée des utilisateurs MyTIM) et aux vérifications d'adresse.

Configuration du realm `tim` (posée le 30/08/2026 par admin de bootstrap
éphémère) :

| Réglage | Valeur |
|---|---|
| Relais | `in-v3.mailjet.com:587`, STARTTLS, authentifié |
| Identifiants | clé API Mailjet (utilisateur) + clé secrète (mot de passe) — **gestionnaire de secrets** ; copie opérationnelle dans la config du realm (base Keycloak) |
| Expéditeur | `auth@teleimagerie.net` — « Authentification Téléimagerie » (boîte inexistante, domaine validé chez Mailjet : SPF `spf.mailjet.com`, DKIM `mailjet._domainkey` en zone) |
| `resetPasswordAllowed` | **activé** — « Mot de passe oublié ? » sur la page de login (le lien ne contourne pas le TOTP) |

Vérifié le 30/08/2026, **après un faux départ instructif** : les deux
premiers tests renvoyaient `204` mais aucun mail n'arrivait — les
expéditeurs (`auth@` puis `*@teleimagerie.net`) étaient déclarés sur le
compte Mailjet mais **`Inactive`** : Mailjet accepte l'envoi en SMTP puis
le **jette silencieusement** tant que l'expéditeur n'est pas validé, sans
même une trace dans sa liste de messages. Validation déclenchée par l'API
(`POST /v3/REST/sender/<id>/validate`) — instantanée, le TXT de propriété
`mailjet._6d687b5a` étant déjà en zone (même compte que la validation
historique du domaine). Après validation : messages au statut **`sent`**
dans `/v3/REST/message`, réception confirmée.

> ⚠️ **Un `204` de `testSMTPConnection` ne prouve que l'acceptation par le
> relais, pas l'envoi.** Pour vérifier un problème de délivrance Mailjet :
> `GET /v3/REST/sender` (les expéditeurs doivent être `Active`) et
> `GET /v3/REST/message` (statut `sent`) — identifiants lisibles dans la
> base Keycloak (`realm_smtp_config`), le mot de passe n'est pas chiffré.

Le lien « Mot de passe oublié ? » apparaît sur la page de login. Copie de
transit de la clé détruite de pve1 après le test.

**Re-tester l'envoi sans la clé** (fait le 30/08/2026 après un réglage côté
Mailjet) : `POST /admin/realms/tim/testSMTPConnection` avec la config
stockée du realm et `"password": "**********"` — Keycloak substitue le mot
de passe enregistré ; le mail part vers l'e-mail de l'admin connecté.

**Rotation de la clé** : redéposer `/root/.secrets/mailjet`
(`MJ_APIKEY=`/`MJ_SECRET=`) sur pve1 et rejouer la mise à jour
`smtpServer` du realm (même commande kcadm que ci-dessus, l'historique du
30/08 fait foi), puis détruire la copie.

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
- **MyTIM dépendra de l'IdP pour ses nouveaux logins SSO** (prod TIM,
  raccordement en cours au 01/09/2026) : un Keycloak mort = bouton SSO en erreur (flash,
  jamais de 500), formulaire local intact, sessions ouvertes non affectées.
  Pas de dépendance circulaire (l'app est chez OVH, hors cluster) — et le jour
  où elle rejoindra le cluster ([20-mytim.md](20-mytim.md#risques-et-limites)),
  le formulaire local reste la porte de secours. Le secret du client vit
  **uniquement** dans le vault Ansible du dépôt gestion (relisible par
  `kcadm get clients/<id>/client-secret -r tim`) : un secret vide passe le
  déploiement sans erreur et ne casse qu'au retour du callback — c'est
  l'état de tim-prod au 01/09/2026 (clé `local+sso` posée avant le vaultage) :
  vérifier `OIDC_CLIENT_SECRET` non vide dans le `.env` déployé.
- **Les utilisateurs finaux (radiologues) sont côté TELLIS** : leur
  raccordement suppose de compléter la collecte
  [13-tellis.md](13-tellis.md#checklist-de-collecte), hors de ce chantier.
