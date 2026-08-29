# Sécurité

Posture retenue avec l'utilisateur : **interface web ouverte sur Internet, second
facteur obligatoire**. Le choix assume une surface d'exposition plus large en
échange de la souplesse d'accès ; il n'a de sens que si le TOTP est réellement en
place sur tous les comptes.

## Comptes

| Compte | Realm | Rôle | TOTP | Usage |
|---|---|---|---|---|
| `matt@pve` | pve | `Administrator` sur `/` | **actif + 10 clés de secours** | quotidien |
| `root@pam` | pam | intégré | **actif + 10 clés de secours** | urgence uniquement |

Les deux comptes sont protégés par un second facteur depuis le 11/08/2026.
La configuration TFA est répliquée par pmxcfs : elle vaut pour les 3 nœuds.

Le mot de passe de `root@pam` est **local à chaque nœud** et n'est pas répliqué
par le cluster : le changer impose de le faire sur les trois.

### Realm `keycloak` (OIDC) — depuis le 27/08/2026

L'authentification est centralisée sur Keycloak ([16-keycloak.md](16-keycloak.md)) :
realm `keycloak` de type OpenID Connect sur le cluster **et** sur PBS, compte
`matt@keycloak` Administrator sur `/`.

> ⚠️ **Décision de sécurité** : pour les connexions via ce realm, le second
> facteur est porté par Keycloak (TOTP obligatoire du realm `tim`), plus par
> Proxmox. `matt@pve` et `root@pam` restent la **voie de secours locale** —
> ne jamais les supprimer ni retirer leur TOTP : ils doivent fonctionner
> l'IdP éteint (bascule HA = ~19 s sans authentification fédérée).

### Se connecter

Dans le formulaire, le realm est dans la liste déroulante — **ne pas le retaper**
dans le nom d'utilisateur :

| Champ | Valeur |
|---|---|
| User name | `matt` |
| Realm | *Proxmox VE authentication server* |

Saisir `matt@pve` produit `matt@pve@pve` et un `no such user`.

## Second facteur

### Enrôler un TOTP

Le script [`scripts/enroll-totp.py`](scripts/enroll-totp.py) est déployé dans
`/root/` sur les 3 nœuds. **À lancer depuis votre propre terminal**, jamais via
un intermédiaire — le secret ne doit transiter par personne :

```bash
ssh -t root@pve1.infra.teleimagerie.net 'python3 /root/enroll-totp.py matt@pve'
```

Il supprime toute entrée existante, impose de vider les entrées « Proxmox » du
téléphone, vérifie le code saisi **avant** d'activer quoi que ce soit, puis
génère les clés de secours.

### Pourquoi ce script plutôt que l'interface web

La fenêtre TOTP de l'interface exige le mot de passe du compte **connecté**
(« the current password of the user performing the change »). Le navigateur
pré-remplit souvent ce champ avec un mot de passe enregistré différent, d'où un
`invalid credentials (500)` incompréhensible. En ligne de commande, `root@pam`
est **exempté** de cette vérification, ce qui contourne le problème.

### Clés de secours

Stockées **hachées en SHA-256 avec sel** dans `/etc/pve/priv/tfa.cfg`. Elles sont
donc **irrécupérables** après affichage — personne, pas même root, ne peut les
relire. Une clé mal notée est une clé perdue.

Chacune ne sert qu'une fois. À conserver ailleurs que sur le téléphone qui porte
le TOTP, sinon les deux facteurs disparaissent ensemble.

Régénérer un jeu (révoque l'ancien) :

```bash
pveum user tfa delete matt@pve --id recovery
pvesh create /access/tfa/matt@pve --type recovery
```

### Déverrouillage d'urgence

Téléphone perdu, clés épuisées : l'accès SSH par clé reste la seule porte.

```bash
ssh root@pve1.infra.teleimagerie.net 'pveum user tfa delete matt@pve'
```

Le compte redevient accessible par mot de passe seul. **Réenrôler aussitôt.**

## SSH

`/etc/ssh/sshd_config.d/10-hardening.conf`, identique sur les 3 nœuds :

```
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
```

Clés autorisées (dans `/etc/pve/priv/authorized_keys`, répliqué par pmxcfs —
`/root/.ssh/authorized_keys` n'est qu'un lien symbolique, un ajout sur un nœud
vaut pour les trois) :

- `~/.ssh/id_ed25519` du poste d'administration, **côté WSL**
  (`SHA256:3ovvl+5zDbc2695U3wxZppukZYnvQSPUZuRuHqDp/Ik`) ;
- `matt@LENOVO-MCA2-windows` (ed25519, ajoutée le 2026-08-27,
  `SHA256:zQ/KVcnLegd0tmIEG2aHLkPaqP/2AoigMqROx2MwS1g`) — **le même poste,
  côté Windows natif** (`C:\Users\Matt\.ssh\`) : PowerShell et WSL ont chacun
  leur trousseau, une clé WSL ne sert pas à `ssh.exe`. Le commentaire
  d'origine (`matt@LENOVO-MCA2`) a été suffixé `-windows` pour pouvoir
  distinguer — et révoquer — chaque clé indépendamment ;
- les clés root croisées des 3 nœuds (nécessaires à `pvecm` et à la migration) ;
- `brtrnd@thinkpad` (ed25519, ajoutée le 2026-08-26).

> **Cette clé est l'issue de secours ultime du cluster.** Sa perte, combinée à un
> TOTP inaccessible, ne laisserait que la console KVM/IPMI OVH.

## Firewall

Actif au niveau datacenter (`/etc/pve/firewall/cluster.fw`), `policy_in: DROP`.

| Port | Source | Usage |
|---|---|---|
| 8006 | tout Internet | interface web |
| 22 | tout Internet | SSH (clé uniquement) |
| 3128 | tout Internet | proxy SPICE |
| 5900-5999 | tout Internet | consoles noVNC |
| tout | ipset `cluster` | Corosync, Ceph, migration, pmxcfs |
| **tout — DROP prioritaire** | `10.40.0.0/24` (LAN VM) | la patte `10.40.0.2` de pve1 est **sortante uniquement** (27/08/2026) : une VM compromise ne joint pas un hyperviseur — [08-opnsense.md](08-opnsense.md#accès-dadministration) |
| ICMP echo | tout Internet | diagnostic |

L'ipset `cluster` contient les 3 IP publiques et les trois sous-réseaux vRack.

**Fermé au passage** : `rpcbind` (111) et Postfix (25) écoutaient sur l'IP
publique. Ils ne sont plus joignables depuis Internet.

> Depuis le 13/08/2026, les montages du NAS-HA sont en **NFSv4.2**, qui n'utilise
> ni `rpcbind` ni `statd` et n'ouvre aucun canal de rappel du serveur vers le
> client. `rpcbind` n'a donc plus d'utilité ici : sa désactivation est un
> durcissement candidat. Aucune règle de firewall n'a eu à être ajoutée pour le
> NAS — le trafic est sortant et le filtrage Proxmox est à état.

**La VM PBS a son propre firewall** (`/etc/pve/firewall/102.fw`) : `policy_in:
DROP`, entrée limitée à l'ipset `cluster`. Sa seconde carte, sur le LAN des VM
(VLAN 400), ne sert qu'aux mises à jour sortantes — **une seule exception
depuis le 29/08/2026** : `tcp/10050` depuis `10.40.0.60` (l'agent Zabbix du
CT 204 est interrogé par cette patte —
[configs/firewall-102-pbs.fw](configs/firewall-102-pbs.fw)).

### Modifier le firewall sans se verrouiller

```bash
# 1. armer une restauration automatique sur les 3 nœuds
systemd-run --unit=fw-rollback --on-active=300 --collect \
  /bin/sed -i 's/^enable: 1/enable: 0/' /etc/pve/firewall/cluster.fw

# 2. valider la syntaxe avant d'activer
pve-firewall compile | grep -i 'cant parse'

# 3. appliquer, puis tester depuis l'EXTÉRIEUR avec des connexions neuves
ssh -o ControlMaster=no -o ControlPath=none root@<hôte> 'echo OK'
curl -s -o /dev/null -w '%{http_code}\n' https://pveN.infra.teleimagerie.net:8006/

# 4. désarmer seulement si tout répond
systemctl stop fw-rollback.timer && systemctl reset-failed fw-rollback.timer
```

## fail2ban

Prisons `sshd` et `proxmox`, backend `systemd`, bannissement 1 h après 5 échecs
en 10 min. Filtre Proxmox dans `/etc/fail2ban/filter.d/proxmox.conf`.

```bash
fail2ban-client status
fail2ban-client status sshd
fail2ban-client set sshd unbanip <ip>
```

Ces serveurs subissent du **brute-force SSH permanent** : des IP étaient déjà
bannies quelques minutes après l'installation. Ce n'est pas théorique.

> Après installation, `fail2ban-client reload` est nécessaire : le service
> démarre avant d'avoir lu la configuration complète et n'active que `sshd`.

## TLS

Certificats Let's Encrypt par nœud, challenge **DNS-01** via l'API OVH — aucun
port supplémentaire ouvert.

```
compte ACME   default → mcapon@teleimagerie.net (acct/3620811681)
plugin        ovh (dns), validation-delay 120 s
domaines      pve{1,2,3}.infra.teleimagerie.net
renouvellement pve-daily-update.timer, quotidien ~03:03 UTC
```

Vérifier depuis l'extérieur :

```bash
curl -s -o /dev/null -w 'code=%{http_code} tls_verify=%{ssl_verify_result}\n' \
  https://pve1.infra.teleimagerie.net:8006/       # attendu : 200 / 0
```

Forcer un renouvellement : `pvenode acme cert order --force`

## Secrets — où ils vivent

**Aucun secret n'est recopié dans cette documentation, volontairement.**

| Secret | Emplacement | Remarque |
|---|---|---|
| Clé API OVH (AK/AS/CK) | plugin ACME, `/etc/pve/priv/` | `pvenode acme plugin list` les affiche en clair à root |
| Clé de compte ACME | `/etc/pve/priv/acme/` | répliqué par pmxcfs |
| Secrets TOTP | `/etc/pve/priv/tfa.cfg` | en clair (nécessaire à la vérification) |
| Clés de secours | `/etc/pve/priv/tfa.cfg` | **hachées SHA-256 + sel**, irrécupérables |
| Mots de passe realm `pve` | `/etc/pve/priv/shadow.cfg` | hachés |
| Mot de passe `root@pam` | `/etc/shadow` de chaque nœud | **non répliqué** |
| Clés Ceph | `/etc/pve/priv/ceph.*.keyring` | |
| Clé API OVH NAS-HA | `/root/.secrets/ovh-nasha.ini` sur **pve1** | mode 600, **non répliqué** |
| Clé API OVH ACME (certbot) | `/root/.secrets/ovh.ini` sur **pve1** | mode 600, **non répliqué** |
| Jeton PBS `backup@pbs!pve` | `/etc/pve/priv/storage/pbs.pw` | répliqué |
| Mot de passe admin Keycloak (console, realm `master`) | **gestionnaire de secrets uniquement** | recopié puis **détruit des serveurs le 27/08/2026** (`rm /etc/pve/priv/keycloak/credentials`), comme le root OPNsense. Récupération possible sans lui : `kc.sh bootstrap-admin user` sur le CT 203 |
| Secrets opérationnels Keycloak (base, clients OIDC) | chacun à son poste de travail | mdp base : `keycloak.conf` du CT 203 · client `proxmox` : `/etc/pve/domains.cfg` · client `pbs` : `domains.cfg` de PBS · client `headscale` : `/etc/headscale/oidc_secret` — voir [16-keycloak.md](16-keycloak.md) |
| Config OPNsense sauvegardée | `/mnt/pve/nas-vm/opnsense-config/` | **contient les clés privées WireGuard**, répertoire 700 |
| Token PVE `zabbix@pve!monitoring` (PVEAuditor, lecture seule) | macro secrète `{$PVE.TOKEN.SECRET}` de l'hôte `cluster-pve` dans Zabbix | créé le 29/08/2026 pour la supervision du cluster — révocable par `pveum user token remove zabbix@pve monitoring` ([17-zabbix.md](17-zabbix.md#supervision-du-cluster--depuis-le-29082026)) |
| Jeton API Zabbix `provisioning` (Super admin, rattaché à `supportTIM`) | `/root/.zbx-api-token` sur le **CT 204**, mode 600 | révocable dans l'UI (*Users → API tokens*) — sert au script [scripts/zabbix-provision-pve.py](scripts/zabbix-provision-pve.py) |

`/etc/pve/priv/` est accessible à root seulement et répliqué par pmxcfs.
`/root/.secrets/` ne l'est pas : ces fichiers n'existent que sur pve1.

> **Deuxième application OVH depuis le 13/08/2026** : `Proxmox Nas-HA`
> (AK `e13e89cf414da916`), droits sur `/dedicated/nasha/*` uniquement. Elle pilote
> les partitions, l'ACL et les snapshots du NAS — voir
> [10-sauvegardes.md](10-sauvegardes.md#piloter-le-nas). Elle est **distincte** de
> celle qui porte le renouvellement TLS : ne pas confondre les deux au moment de
> faire le ménage dans les jetons.

> **La clé API OVH en service** (application `proxmox`, AK `0357cf99f1ed0548`,
> créée le 11/08/2026) a une **validité illimitée** et des droits en écriture
> sur **toutes les zones DNS du compte** — règles `/domain/zone/*`, donc les
> six zones, mail et web de l'entreprise compris (vérifié par
> `GET /auth/currentCredential` le 25/08/2026 —
> [14-noms-de-domaine.md](14-noms-de-domaine.md#acme--ce-qui-dépend-de-quelle-zone)).
> Elle sert au challenge DNS-01 du renouvellement automatique des certificats.
>
> **La supprimer casse le renouvellement** — silencieusement : rien ne se voit
> jusqu'à l'expiration des certificats. C'est arrivé une fois le 11/08/2026, la
> clé ayant été révoquée par erreur ; détecté et corrigé le jour même.
>
> Deux clés antérieures ont été révoquées et ne servent plus à rien.

### Vérifier que le renouvellement fonctionnera

Un `pvenode acme cert order --force` ne prouve rien : Let's Encrypt met en cache
les autorisations pendant ~30 jours et répond `already validated!` sans rejouer le
challenge DNS-01. Pour éprouver réellement la clé, il faut tester le chemin
d'écriture — créer puis supprimer un TXT dans la zone :

```bash
# créer, recharger, supprimer, recharger, vérifier l'absence de résidu
# via POST/DELETE /domain/zone/teleimagerie.net/record
```

Le script `scripts/ovh-dns.py` contient la mécanique de signature ; il lit les
identifiants depuis les variables `OVH_AK`, `OVH_AS` et `OVH_CK`.
