# Keycloak — CT 203 (`auth.teleimagerie.net`)

Serveur d'identité (SSO) du cluster. Fournit à Proxmox — et aux applications à
venir — un annuaire de comptes unique, au lieu d'une liste d'utilisateurs par
application.

> **Document reconstitué par lecture de la machine, le 27/08/2026.**
> Le conteneur a été créé **le matin même à 06:50 UTC** et n'était documenté nulle
> part. Tout ce qui suit a été relevé sur le CT en fonctionnement, sans
> intervention. Les points que la machine ne peut pas révéler — qui l'a installé,
> pour quel usage cible, quelle politique de mot de passe dans le realm — sont
> rassemblés en fin de document, section [À confirmer](#à-confirmer).

---

## Carte d'identité

| | |
|---|---|
| Type | Conteneur LXC **non privilégié**, `features: nesting=1` |
| VMID | **203** |
| Nom d'hôte | `keycloak` |
| Nœud | pve2 (ressource HA, se déplace) |
| Ressources | 2 vCPU, 4 Go RAM, swap 512 Mo, disque **20 Go** sur Ceph (`vm-storage`) |
| Adresse | `10.40.0.50/24` (VLAN **400**), passerelle `10.40.0.1` (OPNsense) |
| DNS | `10.40.0.1` |
| Système | Debian 13 Trixie |
| Haute dispo | **ressource HA**, `max_restart 3`, `max_relocate 3` |
| Démarrage auto | `onboot: 1` |
| Accès | `ssh root@10.40.0.50` depuis un nœud ayant accès au VLAN 400 |
| URL publique | `https://auth.teleimagerie.net` |

Créé le **27/08/2026 à 06:50 UTC** (premier démarrage du journal interne), migré
sur pve2 dans la foulée.

## Pile logicielle

| Composant | Version | Rôle |
|---|---|---|
| Keycloak | **26.7.2** (`/opt/keycloak-26.7.2`, lien `/opt/keycloak`) | serveur d'identité |
| OpenJDK | 21.0.12.1 (paquet Debian) | machine virtuelle Java |
| PostgreSQL | **17** (`postgresql@17-main`) | base de données de Keycloak |
| Postfix | — | envoi de courriel (vérification de compte, oubli de mot de passe) |

Installé depuis les paquets Debian pour Java et PostgreSQL, Keycloak déposé à la
main dans `/opt` (ce n'est pas un paquet). Une seule ligne dans l'historique APT :

```
2026-08-27 06:50:36
apt-get install -y -qq openjdk-21-jre-headless postgresql curl ca-certificates
```

### Service `systemd`

`/etc/systemd/system/keycloak.service` :

```ini
[Unit]
Description=Keycloak (serveur d'authentification)
After=network-online.target postgresql.service
Requires=postgresql.service

[Service]
User=keycloak
Group=keycloak
Environment=JAVA_OPTS_KC_HEAP=-Xms512m -Xmx2g
ExecStart=/opt/keycloak/bin/kc.sh start --optimized
Restart=on-failure
RestartSec=5
LimitNOFILE=102400
TimeoutStartSec=300
```

Bien construit : compte de service dédié (pas de `root`), `Requires=postgresql`
(pas seulement `After`, donc Keycloak ne démarre pas sans sa base), redémarrage
automatique, tas Java plafonné à 2 Go sur les 4 Go du conteneur.

> `--optimized` signifie que la phase de construction (`kc.sh build`) a déjà été
> jouée. **Après toute modification de `keycloak.conf` touchant `db`, `features`
> ou `health`, il faut relancer `kc.sh build`**, sinon le démarrage échoue ou
> ignore le changement.

### Configuration

`/opt/keycloak/conf/keycloak.conf` — secrets masqués :

```properties
db=postgres
db-url=jdbc:postgresql://localhost:5432/keycloak
db-username=keycloak
db-password=<secret>
hostname=auth.teleimagerie.net
http-enabled=true
http-host=10.40.0.50
http-port=8080
proxy-headers=xforwarded
```

**Keycloak ne fait pas de TLS lui-même.** Il écoute en clair sur `10.40.0.50:8080`,
le chiffrement est assuré en amont par `proxy-tim`. C'est le montage attendu — à
condition que le port 8080 ne soit joignable que depuis le proxy (voir
[Exposition réseau](#exposition-réseau)).

`proxy-headers=xforwarded` fait confiance aux en-têtes `X-Forwarded-*`. **C'est
sûr uniquement parce que rien d'autre que le proxy ne peut atteindre le port
8080** : sinon n'importe qui pourrait usurper son adresse IP d'origine dans les
journaux, voire forcer des URL de redirection.

## Exposition réseau

Ports en écoute dans le conteneur (hors `localhost`) :

| Port | Écoute sur | Service |
|---|---|---|
| 22 | `*` | SSH |
| **8080** | `10.40.0.50` uniquement | Keycloak HTTP |
| 7800 | `10.40.0.50` uniquement | Infinispan (cache JGroups) |
| 57800 | `*` | Infinispan (canal secondaire) |

Keycloak est correctement lié à la seule adresse du VLAN 400 — il **n'écoute pas
sur `0.0.0.0`**. Le VLAN 400 est un réseau interne derrière OPNsense, sans route
depuis Internet.

> **Point à surveiller** : `57800` écoute sur `*`. C'est un port de cache
> Infinispan, utile seulement en grappe de plusieurs Keycloak — il n'y en a qu'un
> ici. Sans conséquence tant que le VLAN 400 reste fermé, mais c'est une surface
> ouverte sans usage. Voir [À confirmer](#à-confirmer).

## Chaîne d'accès depuis Internet

```
navigateur
  │  https://auth.teleimagerie.net
  ▼
OPNsense (VM 100) — WAN 57.130.34.121
  │  rdr 443 vers .122 → 10.40.0.10
  ▼
proxy-tim (CT 201) — aiguillage SNI
  │  vhost auth.teleimagerie.net, 127.0.0.1:8443 ssl proxy_protocol
  │  terminaison TLS (certificat Let's Encrypt dédié)
  ▼
Keycloak (CT 203) — http://10.40.0.50:8080
  │
  ▼
PostgreSQL 17 — localhost:5432
```

Le vhost `/etc/nginx/sites-available/auth.teleimagerie.net.conf` sur le CT 201
suit exactement le schéma décrit dans
[09-proxy-tim.md](09-proxy-tim.md) : écoute sur `127.0.0.1:8443` avec
`proxy_protocol`, derrière l'aiguilleur SNI. Il ajoute `proxy_buffer_size 16k` —
nécessaire, les jetons OIDC dans les en-têtes dépassent souvent les tampons par
défaut de nginx.

Le port 80 est servi pour `/.well-known/acme-challenge/` (renouvellement du
certificat) et redirige tout le reste vers HTTPS.

## Réalm `tim` et intégration Proxmox

Proxmox est déclaré comme client OIDC. `/etc/pve/domains.cfg` :

```
openid: keycloak
	comment Keycloak (CT 203) - realm tim
	client-id proxmox
	issuer-url https://auth.teleimagerie.net/realms/tim
	autocreate 0
	client-key <secret, EN CLAIR dans le fichier>
	username-claim username
```

Le realm répond publiquement et son certificat est valide :

```
$ curl https://auth.teleimagerie.net/realms/tim/.well-known/openid-configuration
issuer:                 https://auth.teleimagerie.net/realms/tim
authorization_endpoint: .../protocol/openid-connect/auth
token_endpoint:         .../protocol/openid-connect/token
end_session_endpoint:   .../protocol/openid-connect/logout
```

Deux réglages notables :

- **`autocreate 0`** — bon réglage. Un utilisateur inconnu de Proxmox ne se crée
  pas tout seul en se connectant par Keycloak. Il faut l'avoir déclaré des deux
  côtés.
- **`username-claim username`** — l'identifiant Proxmox est repris du champ
  `username` de Keycloak, d'où le compte `matt@keycloak`.

### Ce que voit l'utilisateur

Le realm apparaît dans le menu déroulant de l'écran de connexion Proxmox, libellé
**« Keycloak (CT 203) - realm tim »**. Trois entrées y coexistent :

| Realm affiché | Compte | Second facteur |
|---|---|---|
| Proxmox VE authentication server | `matt` | TOTP (dans `tfa.cfg`) |
| Linux PAM standard authentication | `root` | TOTP (dans `tfa.cfg`) |
| **Keycloak (CT 203) - realm tim** | `matt@keycloak` | **à imposer dans Keycloak** |

> Le libellé expose l'identifiant interne « CT 203 » sur un écran de connexion
> public. Sans gravité, mais un intitulé neutre (« SSO TIM ») ne renseigne pas un
> visiteur sur la topologie interne. Le libellé vient du champ `comment` de
> `domains.cfg`.

---

## Sécurité — points ouverts

### 1. `matt@keycloak` est Administrator sans TOTP côté Proxmox

```
/etc/pve/user.cfg
user:matt@keycloak:1:0:Matthieu:Capon:mcapon@teleimagerie.net:::
acl:1:/:matt@keycloak,matt@pve:Administrator:

/etc/pve/priv/tfa.cfg
matt@pve  {'totp': 1, 'recovery': 3}
root@pam  {'totp': 1, 'recovery': 3}
```

Le compte a **les pleins pouvoirs sur `/`** et **ne figure pas dans `tfa.cfg`**.

Ce n'est pas un oubli d'enrôlement : **l'authentification OIDC ne passe jamais par
la couche TOTP de Proxmox**. Le second facteur d'un compte OIDC doit être exigé
*dans le realm Keycloak*. Tant que ce n'est pas vérifié, la règle « TOTP
obligatoire » annoncée au README a une porte de sortie qui donne l'administration
complète du cluster.

**À vérifier dans la console Keycloak** (`https://auth.teleimagerie.net/admin`) :
*Realm `tim` → Authentication → Required actions → `Configure OTP`*, ou un flux
d'authentification conditionnel imposant l'OTP.

Arbitrage détaillé en [§2 de 16-code-review.md](16-code-review.md).

### 2. Dépendance circulaire

**Si le CT 203 est arrêté, la connexion par Keycloak ne fonctionne plus.** Le
serveur qui autorise l'accès au cluster est hébergé *sur* ce cluster.

Ce n'est pas bloquant tant que les voies de secours existent — et elles existent :

- `matt@pve` (realm *Proxmox VE authentication server*) + TOTP
- `root@pam` (realm *Linux PAM*) + TOTP
- `ssh root@pve1...` avec la clé `~/.ssh/id_ed25519`

> **Ne jamais supprimer `matt@pve` ni son TOTP** au motif que « le SSO fait
> doublon ». C'est l'issue de secours quand Keycloak est indisponible, au même
> titre que la clé SSH (point 3 du README).

### 3. Le secret client est en clair dans `/etc/pve/domains.cfg`

`domains.cfg` n'est **pas** sous `/etc/pve/priv/` : c'est une configuration de
cluster lisible par `www-data`. Le `client-key` OIDC y figure en clair.

**Ce fichier ne doit jamais être copié dans `configs/`**, contrairement aux autres
fichiers de `/etc/pve/`. C'est le piège naturel de la convention du dossier.

### 4. Durcissement du conteneur : à faire

Relevé sur la machine :

| Point | État |
|---|---|
| `unattended-upgrades` | **absent** (`not-found`) |
| `PermitRootLogin` | valeur par défaut Debian, **non durci** |
| `fail2ban` | **absent** |
| Pare-feu Proxmox sur `net0` | **`firewall=0`** — désactivé |
| Port 57800 | écoute sur `*` sans usage |

Le CT 202 (headscale) porte aussi `firewall=0`, alors que la VM 102 (PBS) est en
`firewall=1`. L'asymétrie se défend — les CT du VLAN 400 sont derrière OPNsense —
mais elle n'est écrite nulle part. Voir §13 de
[16-code-review.md](16-code-review.md).

Le durcissement SSH appliqué aux hyperviseurs
([`configs/sshd-10-hardening.conf`](configs/sshd-10-hardening.conf)) **n'a pas été
propagé ici**. Le conteneur n'est joignable que depuis le VLAN 400, ce qui limite
la portée, mais c'est un écart avec la ligne de conduite décrite dans
[04-securite.md](04-securite.md).

---

## Sauvegardes

### État

**Aucun instantané PBS à ce jour** :

```
pvesm list pbs | grep -c "/203/"
0
```

**Ce n'est pas une anomalie de la tâche de sauvegarde.** Le conteneur a été créé à
**06:50 UTC**, la dernière tâche quotidienne est passée à **02:00 UTC** le même
jour : le CT 203 n'existait pas encore.

Le job quotidien est déclaré `all 1` avec pour seule exclusion la VM 102 — il
**prendra donc le CT 203 automatiquement** au prochain passage.

> **À vérifier le lendemain matin de la mise en service** :
> ```
> pvesm list pbs | grep /203/
> ```
> Si rien n'apparaît après un passage à 02:00, il y a alors un vrai défaut à
> diagnostiquer (voir §1 de [16-code-review.md](16-code-review.md)).

### Dump PostgreSQL local

```
/var/backups/keycloak/keycloak-4.sql.gz   49 555 octets   27/08/2026 06:58
```

Un unique export, réalisé à l'installation (`pg_dump` 17.11). Base de 68 Mo.

Ce fichier **n'est pas une sauvegarde** au sens du plan de reprise : il vit sur le
disque du conteneur qu'il est censé protéger, et rien ne le régénère. Il dépannera
une erreur de manipulation dans la console d'administration, rien de plus. La
vraie protection est l'instantané PBS du conteneur entier.

> Un `pg_dump` périodique vers le NAS resterait utile en complément : restaurer un
> realm supprimé par erreur est bien plus simple depuis un export SQL que depuis
> un instantané de conteneur. À arbitrer, sur le modèle de
> [`scripts/backup-opnsense.sh`](scripts/backup-opnsense.sh).

### Pourquoi c'est le composant le plus sensible du cluster

Keycloak porte le référentiel d'identités et de droits. Ceph protège d'une panne
matérielle, **pas** d'une suppression ni d'une corruption applicative : les trois
répliques disparaissent ensemble. Perdre le CT 203 sans copie, c'est perdre les
comptes — donc l'accès. En contexte HDS, c'est le composant qui garde l'accès aux
données de santé.

---

## Exploitation

### Vérifier que tout va bien

```bash
# depuis un nœud
ha-manager status | grep 203              # doit afficher "started"

# dans le conteneur (pct enter 203 depuis le nœud qui l'héberge)
systemctl status keycloak postgresql@17-main
ss -ltnp | grep 8080

# depuis n'importe où
curl -sS https://auth.teleimagerie.net/realms/tim/.well-known/openid-configuration
```

Le dernier appel doit renvoyer du JSON avec `"issuer":
"https://auth.teleimagerie.net/realms/tim"`. C'est le test de bout en bout : il
valide à la fois OPNsense, le proxy, le certificat, Keycloak et PostgreSQL.

### Trouver le conteneur

Le CT est une ressource HA : **il change de nœud**. Ne pas présumer qu'il est sur
pve2.

```bash
ha-manager status | grep ct:203
```

### Redémarrage propre

```bash
pct exec 203 -- systemctl restart keycloak      # service seul
pct reboot 203                                  # conteneur entier
```

Compter jusqu'à une minute avant que le service réponde : Keycloak démarre une JVM
et vérifie le schéma de sa base.

### Journaux

```bash
pct exec 203 -- journalctl -u keycloak -n 50 --no-pager
pct exec 203 -- journalctl -u postgresql@17-main -n 50 --no-pager
```

### Après modification de `keycloak.conf`

Le service tourne en `--optimized`. Si la modification touche `db`, `features` ou
`health` :

```bash
pct exec 203 -- su - keycloak -c '/opt/keycloak/bin/kc.sh build'
pct exec 203 -- systemctl restart keycloak
```

Un changement de `hostname` ou `proxy-headers` seul ne nécessite qu'un
redémarrage.

---

## À confirmer

Ce que la machine ne peut pas dire, et qui reste à documenter :

- [ ] **Qui a installé ce conteneur, quand, et dans quel but précis** — le SSO
      est-il destiné aux seuls administrateurs Proxmox, ou aux applications
      métier à venir (PACS, syngo) ?
- [ ] **Le MFA est-il imposé dans le realm `tim`** ? C'est la question la plus
      importante : voir [Sécurité §1](#1-mattkeycloak-est-administrator-sans-totp-côté-proxmox).
- [ ] **Combien de comptes existent dans le realm**, et avec quels droits. Je n'ai
      volontairement pas interrogé la base d'identités.
- [ ] **Politique de mot de passe** du realm (longueur, expiration, verrouillage
      après échecs répétés).
- [ ] **Où est stocké le mot de passe de l'administrateur Keycloak initial**, et
      s'il a été changé après installation.
- [ ] **Le certificat `auth.teleimagerie.net` est-il renouvelé automatiquement** ?
      Le vhost sert bien `/.well-known/acme-challenge/`, mais le renouvellement
      côté CT 201 n'a pas été vérifié — et le timer ACME ne tourne que sur pve1
      (§5 de [16-code-review.md](16-code-review.md)).
- [ ] **Faut-il fermer le port 57800** (Infinispan, sans usage en instance unique) ?
- [ ] **Un `pg_dump` périodique vers le NAS** est-il souhaité en complément de PBS ?

---

## Références

- [16-code-review.md](16-code-review.md) — revue du dépôt : §1 sauvegarde, §2 le
  2FA du compte `matt@keycloak`, §3 le secret en clair, §13 le pare-feu par invité
- [09-proxy-tim.md](09-proxy-tim.md) — l'aiguillage SNI qui sert ce vhost
- [04-securite.md](04-securite.md) — durcissement, TOTP, emplacement des secrets
- [10-sauvegardes.md](10-sauvegardes.md) — PBS, rétention, restauration
- [01-architecture.md](01-architecture.md) — plan d'adressage, VLAN 400
