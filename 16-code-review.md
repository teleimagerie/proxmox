# Revue de code du dépôt — 27/08/2026

Revue de l'intégralité du dépôt (4 784 lignes : 13 documents, 15 configurations,
6 scripts), **chaque constat vérifié contre le cluster en production** par SSH
sur `pve1` le 27/08/2026. Les commandes de vérification sont citées telles
quelles pour que chaque point soit rejouable.

**Le dépôt est de bonne tenue** : le « pourquoi » est écrit, `07-pieges.md` a une
vraie valeur d'usage, les scripts sont idempotents et portent de vrais garde-fous.
Le problème n'est pas la qualité, c'est la **dérive** : le dépôt décrit le cluster
du 15/08, la production a avancé depuis.

Deux points sont **bloquants**, et le fil rouge de la revue est le même angle
mort : le **CT 203 `keycloak`**, qui tourne en production et n'existait nulle part
dans le dépôt.

> **Correction du 27/08 (après enquête)** : le §1 était initialement classé
> bloquant sur le constat « jamais sauvegardé ». Vérification faite, **le
> conteneur a été créé le 27/08 à 06:50 UTC, après le passage de la sauvegarde de
> 02:00** : il n'existait pas encore. La tâche `all 1` le prendra automatiquement
> au prochain passage. Le constat reste à vérifier le lendemain matin, mais ce
> n'est pas un défaut de sauvegarde. Le §1 est reclassé **Important**.
> Inventaire complet du conteneur : [17-keycloak.md](17-keycloak.md).

---

## Table des priorités

| # | Point | Gravité | Décision à prendre ? |
|---|---|---|---|
| 1 | CT 203 `keycloak` non documenté, sauvegarde à confirmer | **Important** | Oui — §1 |
| 2 | `matt@keycloak` Administrator sans 2FA | **Bloquant** | Oui — §2 |
| 3 | README : « aucun secret » est faux | **Bloquant** | Non — correction directe |
| 4 | ~~`ha-resources.cfg` et comptages obsolètes~~ **traité** | — | Non |
| 5 | Automatismes présents sur pve1 seul (SPOF) | Important | Oui — §5 |
| 6 | `backup-opnsense` : échecs silencieux | Important | Non |
| 7 | ~~`configs/` sans détection de dérive~~ **traité** | — | Non |
| 8 | `ovh-dns.py` : sentinelle `"ERROR"` en ligne | Moyen | Non |
| 9 | `ovh-nasha.py` : `/auth/time` à chaque appel | Moyen | Non |
| 10 | `deploy-syngo.sh` : `$SSH_OPTS` non quoté | Mineur | Non |
| 11 | `enroll-totp.py` : retour non vérifié | Mineur | Non |
| 12 | `stun-tailnode.py` : `tid` fixe, `argv` nu | Mineur | Non |
| 13 | `firewall=0` sur CT 202 et 203 non expliqué | Mineur | Non |

---

# Le fil rouge : le CT 203

## 1. Le CT 203 `keycloak` tourne en production sans aucune documentation

Le conteneur n'est mentionné dans **aucun** des 13 documents. En production il est
pourtant ressource HA, `onboot: 1`, `10.40.0.50/24` sur le VLAN 400, 4 Go de RAM,
2 vCPU, disque 20 Go sur Ceph :

```
ha-manager status
  service ct:203 (pve2, started)      ← absent de configs/ha-resources.cfg
```

Il porte **Keycloak 26.7.2 + PostgreSQL 17**, sert `https://auth.teleimagerie.net`
et constitue le serveur d'identité du cluster.

> **Traité le 27/08** : inventaire complet reconstitué par lecture de la machine
> dans [17-keycloak.md](17-keycloak.md).

### Sur la sauvegarde : constat initial corrigé

La première passe de revue relevait :

```
pvesm list pbs | grep -c "/203/"
0
```

et concluait à un défaut de la tâche de sauvegarde. **C'était une erreur de ma
part** — la conclusion allait au-delà de ce que la preuve permettait.

Vérification faite dans le journal interne du conteneur :

```
pct exec 203 -- journalctl --list-boots
 -1  ...  Thu 2026-08-27 06:50:14 UTC   ← premier démarrage : création du CT
```

Le conteneur a été créé à **06:50 UTC**, la tâche quotidienne est passée à
**02:00 UTC** le même jour. **Le CT 203 n'existait pas encore** : son absence des
instantanés est normale, pas anormale.

Le job est déclaré `all 1` avec pour seule exclusion la VM 102 — il prendra donc
le CT 203 **automatiquement** au prochain passage.

> **Leçon de méthode** : les horodatages de `/etc/pve` (pmxcfs) sont inutilisables
> comme date de création — ils reflètent la dernière synchronisation du système de
> fichiers de cluster, pas l'âge du fichier. C'est le journal *interne* du
> conteneur qui donne la bonne réponse.

> ### Décision à prendre
>
> Rien à corriger dans l'immédiat, mais **une vérification à faire** le lendemain
> matin du prochain passage à 02:00 :
>
> ```
> pvesm list pbs | grep /203/
> ```
>
> - **Si un instantané apparaît** — le sujet est clos, la couverture est
>   automatique.
> - **Si rien n'apparaît** — il y a alors un vrai défaut, et il faudra lancer
>   `vzdump 203 --storage pbs --mode snapshot` à la main pour lire l'erreur. Cette
>   commande écrit en production : ce sera votre appel.
>
> Reste ouvert dans les deux cas : un **`pg_dump` périodique** de la base Keycloak
> vers le NAS, en complément de PBS. Restaurer un realm supprimé par erreur est
> bien plus simple depuis un export SQL que depuis un instantané de conteneur
> entier. Voir [17-keycloak.md](17-keycloak.md#sauvegardes).

---

# Bloquants

## 2. `matt@keycloak` est Administrator sur `/` sans second facteur

```
grep -E "^acl" /etc/pve/user.cfg
acl:1:/:matt@keycloak,matt@pve:Administrator:

/etc/pve/priv/tfa.cfg
matt@pve  {'totp': 1, 'recovery': 3}
root@pam  {'totp': 1, 'recovery': 3}
```

Le compte `matt@keycloak` détient **Administrator à la racine** et **ne figure pas
dans `tfa.cfg`**. Le README annonce pourtant :

> Second facteur | TOTP obligatoire sur `matt@pve` et `root@pam`, 10 clés de secours chacun

Ce n'est pas un oubli d'enrôlement : **l'authentification OIDC de Proxmox ne passe
pas par la couche `tfa.cfg`**. Le second facteur d'un compte OIDC doit être imposé
*dans le realm Keycloak lui-même*. La règle « TOTP obligatoire » a donc désormais
une porte de sortie qui n'est ni tracée ni documentée, et qui donne les pleins
pouvoirs sur le cluster.

Le realm est déclaré avec `autocreate 0` — un compte ne peut donc pas apparaître
tout seul, ce qui limite la portée. Mais `matt@keycloak`, lui, existe déjà.

> ### Décision à prendre
>
> - **Option A — imposer le MFA dans le realm `tim` de Keycloak** (Required
>   action `Configure OTP`, ou flux d'authentification conditionnel), puis
>   documenter que le second facteur des comptes OIDC vit là et pas dans
>   `tfa.cfg`. C'est la voie cohérente avec l'usage prévu du SSO.
> - **Option B — restreindre l'ACL `matt@keycloak`** à un rôle moindre que
>   `Administrator`, et réserver l'administration aux comptes `matt@pve` /
>   `root@pam` qui portent déjà le TOTP.
> - **Option C — retirer l'ACL** en attendant l'arbitrage.
>
> **Complément du 27/08 — l'administration de Keycloak elle-même.** En cherchant
> à vérifier le MFA du realm, trois constats se sont ajoutés : le compte
> d'administration est **`tmpadmin`**, l'admin *temporaire* créé au premier
> démarrage et jamais remplacé ; son mot de passe vit **en clair** dans
> `/root/.kc-secrets`, à l'intérieur du conteneur qu'il protège ; et le script
> d'installation `/root/kc-setup.sh` qui le lit est resté sur la machine.
>
> Trois corrections à mener : créer un compte nominatif avec OTP puis supprimer
> `tmpadmin` ; déplacer le secret vers `/etc/pve/priv/` ; documenter l'emplacement
> retenu dans `04-securite.md`. Détail en
> [§4 de 17-keycloak.md](17-keycloak.md#4-ladministration-repose-sur-le-compte-de-bootstrap-tmpadmin).
>
> La vérification du MFA reste **ouverte** : elle demande de s'authentifier avec
> ce mot de passe, que personne n'avait sous la main. Les commandes `kcadm.sh`
> sont prêtes (lecture seule) — voir la même section.

> À trancher aussi : ce SSO introduit une **dépendance circulaire**. Si le CT 203
> est indisponible, la connexion par Keycloak ne fonctionne plus. `matt@pve` et
> `root@pam` restent la porte de secours — cela mérite une ligne explicite dans
> `04-securite.md`, au même titre que la clé SSH.

## 3. L'affirmation « aucun secret dans ces fichiers » est fausse

Le README conclut :

> Aucun secret ne figure dans ces fichiers — ils vivent tous dans `/etc/pve/priv/`
> sur le cluster.

Or `/etc/pve/domains.cfg` contient le secret client OIDC **en clair** :

```
openid: keycloak
	client-key <secret de 86 caracteres, en clair dans le fichier>
```

`domains.cfg` **n'est pas sous `priv/`** : c'est une configuration de cluster
lisible par `www-data`. La phrase du README reste vraie du *dépôt* — j'ai vérifié,
aucun secret n'y figure — mais elle est fausse sur le cluster, et c'est justement
là qu'elle sert de règle.

Deux corrections, sans arbitrage :

1. reformuler la phrase (« le dépôt ne contient aucun secret » ≠ « tous les
   secrets vivent dans `priv/` ») ;
2. inscrire noir sur blanc que **`domains.cfg` ne doit jamais être copié dans
   `configs/`**, contrairement aux autres fichiers de `/etc/pve/`. C'est le piège
   naturel de la convention actuelle du dossier.

---

# Importants

## 4. `configs/ha-resources.cfg` et les comptages sont périmés

> **Traité le 27/08** : `configs/` resynchronisé, README corrigé (cinq machines,
> cinq ressources HA).

`configs/ha-resources.cfg` déclare 4 ressources, la production en a 5 (`ct: 203`
manque). Le même écart se propage :

- `README.md:6` — « **Quatre machines** y tournent »
- `README.md:87` — « HA  4 ressources : vm:100 · vm:102 · ct:201 · ct:202 »
> **Correction** : j'avais aussi cité `03-exploitation.md:26` (« Si les quatre
> sont verts »). Relecture faite, « les quatre » y désigne les **commandes du bloc
> de diagnostic**, pas les machines — mon rapprochement était faux. Le bloc en
> compte cinq : la formulation a été clarifiée, mais ce n'était pas le même défaut.

Le reste de l'inventaire est en revanche **exact** — vérifié pièce par pièce :
CT 201 40 Go / 2 Go RAM, CT 202 10 Go / 2 Go RAM, VM 100 8 Go, VM 102 8 Go,
empreinte PBS, IP, VLAN, tout correspond.

## 5. Les automatismes ne vivent que sur pve1

Dans un cluster HA à 3 nœuds, deux mécanismes reposent sur une seule machine :

| | pve1 | pve2 | pve3 |
|---|---|---|---|
| `backup-opnsense.timer` | `enabled` | `not-found` | `not-found` |
| `/usr/local/sbin/backup-opnsense.sh` | présent | **absent** | **absent** |
| `acme-renew.timer` | `enabled` | `not-found` | `not-found` |

Si pve1 tombe, les sauvegardes de configuration OPNsense **et tout le
renouvellement de certificats** s'arrêtent — silencieusement. Le cluster, lui,
continue : rien n'alertera. Les certificats se remarquent au bout de 90 jours,
c'est-à-dire trop tard.

`10-sauvegardes.md:391` documente bien le repli `ProxyJump` quand pve1 perd son
adresse VLAN 400, et `06-reste-a-faire.md:32` note que le timer ne tourne que sur
pve1 — mais **le fait que le script lui-même n'existe pas ailleurs** n'est écrit
nulle part. Le repli documenté laisse croire que la bascule est couverte.

> ### Décision à prendre
>
> - **Option A — accepter et documenter.** Écrire explicitement dans
>   `10-sauvegardes.md` et `09-proxy-tim.md` : « si pve1 est perdu durablement,
>   redéployer le script et réarmer le timer sur un autre nœud », avec la marche
>   à suivre. Coût nul, protection par la procédure.
> - **Option B — déployer sur les trois nœuds.** Le script est idempotent et daté
>   par jour ; trois exécutions concurrentes écriraient le même fichier. Il faut
>   donc un verrou (`flock` sur le NAS) ou un garde « je n'agis que si je suis le
>   nœud maître HA ».
> - **Option C — en faire une ressource du cluster** portée par le CT qui va bien.
>
> L'option A suffit sans doute pour `backup-opnsense` (hebdomadaire, perte tolérable).
> **Le sujet ACME mérite un vrai arbitrage** : une expiration de certificat est
> visible de l'extérieur et touche `syngo.*`.

## 6. `backup-opnsense` : trois exécutions muettes et un trou de six jours

```
ls /mnt/pve/nas-vm/opnsense-config/
config-2026-08-13.xml
config-2026-08-14.xml
config-2026-08-15.xml
config-2026-08-22.xml     ← rien entre le 15 et le 22
```

Le timer est hebdomadaire (`sat 04:30`), donc le trou 16→21 est **normal**. Ce qui
ne l'est pas, c'est le journal : les trois dernières exécutions se terminent en
`Deactivated successfully` **sans jamais émettre la ligne
`logger -t backup-opnsense "sauvegarde OK"`** que le script écrit en dernier.

Le fichier du 22/08 existe pourtant et fait 49 096 octets. L'explication la plus
probable est que `logger` écrit dans le journal sous une autre unité que celle
qu'on interroge — donc pas un défaut de sauvegarde. Mais **en l'état, on ne peut
pas distinguer « a réussi » de « a échoué après avoir écrit le fichier »**, et
c'est précisément ce que la ligne de log était censée permettre.

À corriger dans le script : sortir le résultat sur `stdout` en plus de `logger`,
pour que `systemd` le capture dans l'unité `backup-opnsense.service`.

Le reste du script est solide : `set -euo pipefail`, `umask 077`, répertoire en
700, double garde-fou (taille > 10 Ko **et** en-tête `<?xml`), suppression du
fichier suspect avant sortie en erreur, rotation à 12 copies. La copie du dépôt
est **identique** à celle déployée (diff vérifié).

## 7. `configs/` ne détecte pas sa propre dérive

> **Traité le 27/08** : [`scripts/check-drift.sh`](scripts/check-drift.sh) compare
> `configs/` à la production (liste blanche explicite, lecture seule), et chaque
> fichier porte désormais sa provenance en en-tête. Le README dit maintenant que
> `configs/` est **documentaire**, pas un plan de restauration.
>
> **Le script a immédiatement trouvé une seconde dérive** que la revue manuelle
> avait manquée : `headscale-config.yaml` ne contenait pas le bloc `oidc:` ajouté
> en production le 27/08, qui branche headscale sur Keycloak — avec une dépendance
> critique en commentaire (« sans l'override Unbound auth → 10.40.0.10, headscale
> ne démarre pas »). C'est la justification de l'outil.

J'ai comparé les copies du dépôt aux fichiers en production : `cluster.fw`,
`storage.cfg`, `jobs.cfg`, `backup-opnsense.sh`, `deploy-syngo.sh` sont
**identiques**. `ha-resources.cfg` ne l'est pas (§4).

Le dossier remplit donc son office aujourd'hui, mais rien ne signale le jour où il
cesse de le faire — et le §4 montre que c'est déjà arrivé sans que personne le voie.

> ### Décision à prendre
>
> - **Option A — script de vérification** (`scripts/check-drift.sh`) qui compare
>   `configs/` au cluster et sort en erreur sur écart. Lancé à la main avant
>   chaque commit, ou par un timer hebdomadaire qui notifie.
> - **Option B — laisser en revue manuelle**, avec une ligne dans le README
>   rappelant de resynchroniser après toute modification du cluster.
>
> Si vous prenez l'option A, attention : le script doit porter une **liste
> blanche** de fichiers, jamais une copie en masse de `/etc/pve/` — sinon il
> ramène `domains.cfg` et son secret dans le dépôt (§3).

---

# Points de détail sur les scripts

## 8. `ovh-dns.py` — la sentinelle `"ERROR"` circule avec les vraies valeurs

`call()` renvoie la **chaîne** `"ERROR"` en cas d'échec HTTP, puis le résultat est
utilisé comme une donnée normale :

```python
ids = call("GET", f"/domain/zone/{ZONE}/record?fieldType=A")
if ids == "ERROR":
    sys.exit("Identifiants ou droits invalides.")
print(f"  OK : {len(ids)} enregistrements A existants dans {ZONE}")
```

Ici le garde-fou est présent et fait son travail. Mais la forme est fragile : sans
lui, `len("ERROR")` vaut **5** — le script annoncerait « OK : 5 enregistrements »
puis itérerait sur les caractères `E`, `R`, `R`, `O`, `R` comme identifiants. Le
même motif se répète plus bas (`if rec != "ERROR" and rec`) où un échec devient un
saut silencieux.

Correction : lever une exception plutôt que renvoyer une sentinelle. Le script est
interactif et ponctuel, l'arrêt net est le bon comportement.

## 9. `ovh-nasha.py` — `/auth/time` rappelé à chaque requête, sans filet

```python
def call(method, path, body=None):
    ...
    with urllib.request.urlopen(f"{BASE}/auth/time", timeout=15) as r:
        ts = str(int(r.read()))
```

Deux allers-retours HTTP par appel d'API, et cette requête-là n'est protégée par
aucun `try`. Sur un script qui boucle avec `wait_task` (jusqu'à 120 itérations),
une micro-coupure réseau produit une trace Python et un état partiel — au milieu
d'une création de partition.

Correction : mesurer l'écart **une seule fois** au démarrage
(`delta = temps_serveur - temps_local`) puis calculer l'horodatage localement.
C'est la méthode du SDK OVH officiel.

Le reste est bien fait : idempotence réelle, `wait_task` qui distingue
`customerError` / `ovhError`, `norm()` pour les ACL en `/32`, et le commentaire qui
explique *pourquoi* les IP sont publiques (le NAS-HA n'est pas raccordable au
vRack) — exactement le genre de « pourquoi » qui fait la valeur du dépôt.

## 10. `deploy-syngo.sh` — `$SSH_OPTS` non quoté, et pose non atomique

```bash
SSH_OPTS="-o ConnectTimeout=10 -o BatchMode=yes"
scp $SSH_OPTS "$D/$name/fullchain.pem" ...
```

Ne fonctionne que grâce au découpage de mots. Utiliser un tableau, comme
`backup-opnsense.sh` le fait déjà correctement :

```bash
SSH_OPTS=(-o ConnectTimeout=10 -o BatchMode=yes)
scp "${SSH_OPTS[@]}" ...
```

Par ailleurs, les deux `scp` déposent le certificat puis la clé. Si le second
échoue, `set -e` interrompt **avant** le `nginx -t && reload` — nginx garde donc
son ancienne paire, il n'y a pas de panne. Mais le conteneur conserve un
`fullchain.pem` neuf avec une `privkey.pem` ancienne : la prochaine exécution
réussie repartira d'un état incohérent. Copier en `.new` puis renommer sur place
lève l'ambiguïté.

## 11. `enroll-totp.py` — très bon, une réserve

Le script fait exactement ce qu'il faut : table rase avant enrôlement, **vérification
du code avant enregistrement** (impossible de s'enfermer dehors), tolérance d'une
fenêtre pour la dérive d'horloge, clés de secours affichées une seule fois,
consigne de tester dans un autre navigateur. C'est la bonne façon d'écrire un outil
de 2FA.

Une réserve : le retour de `pveum user tfa delete` n'est pas vérifié
(`capture_output=True` puis résultat ignoré). Si la suppression échoue, le script
poursuit et l'objectif annoncé — « un seul secret à la fin » — n'est plus garanti.

## 12. `stun-tailnode.py` — sonde de diagnostic, deux détails

- `tid = b"ClaudeTest12"` : identifiant de transaction **fixe**, là où la RFC 5389
  demande 96 bits aléatoires. Sans conséquence pour une sonde, mais une réponse
  retardée d'un essai précédent est indiscernable d'une réponse fraîche.
- `sys.argv[1]` sans garde : appelé sans argument, le script sort sur `IndexError`
  au lieu d'afficher son propre `Usage:` — pourtant déjà écrit dans la docstring.

## 13. Asymétrie de pare-feu non expliquée

```
CT 201 (proxy-tim)  net0: ...                 ← pas de firewall=
CT 202 (headscale)  net0: ...,firewall=0,...
CT 203 (keycloak)   net0: ...,firewall=0,...
VM 102 (pbs)        net0: ...,firewall=1,...
```

Le pare-feu par invité est **désactivé** sur headscale et keycloak, **activé** sur
PBS. C'est défendable — les CT du VLAN 400 sont derrière OPNsense, la VM 102 est
sur le VLAN 300 exposé aux nœuds — mais ce n'est écrit nulle part. Une ligne dans
`04-securite.md` évitera qu'on « corrige » un jour cette différence voulue.

---

# Ce qui est juste, et mérite d'être noté

Vérifié en production le 27/08/2026 :

```
ceph -s          HEALTH_OK · 6/6 OSD up · mon quorum pve1,pve2,pve3 · 33 pgs active+clean
ha-manager       quorum OK · master pve3 · fencing armed (CRM watchdog active)
pveversion       pve-manager/9.2.10 · noyau 7.0.14-11-pve
```

- **Ceph `size=3` / `min_size=2`** : le bon réglage. `min_size=1` invite à la perte
  de données silencieuse.
- **Corosync à deux anneaux** sur des chemins réellement indépendants (vRack
  `10.100.0.x` **et** IP publiques) avec `link_mode: passive` et `secauth: on`.
  Beaucoup de clusters à deux anneaux les font passer par le même commutateur ;
  ici non.
- **VLAN 100 à MTU 1500 alors que Ceph tourne en 9000.** Choix délibéré et
  correct : le jumbo sur Corosync est un piège à latence connu, et Corosync ne
  gagne rien à des trames longues.
- **`shutdown_policy=migrate`**, migration chiffrée sur le VLAN 200 dédié.
- **Durcissement SSH** cohérent : clé seule, `MaxAuthTries 3`, `LoginGraceTime 30`,
  `PermitRootLogin prohibit-password`, `X11Forwarding no`.
- **Sauvegardes réellement en place** : instantanés PBS quotidiens vérifiés pour
  VM 100, CT 201, CT 202 jusqu'au 27/08 inclus — le mécanisme fonctionne, ce qui
  rend l'absence du 203 (§1) d'autant plus anormale.
- Les **exclusions** `--exclude 102` et le job hebdomadaire séparé vers `nas-vm`
  résolvent proprement le problème « PBS ne peut pas se sauvegarder lui-même ».

---

# Récapitulatif des décisions qui vous reviennent

| Sujet | Question posée | Où |
|---|---|---|
| **Sauvegarde CT 203** | Vérifier demain matin que l'instantané apparaît. Et faut-il un `pg_dump` périodique vers le NAS en complément ? | §1 |
| **2FA sur `matt@keycloak`** | MFA imposé dans le realm Keycloak, ACL restreinte, ou ACL retirée ? Et où documente-t-on la porte de secours si le SSO tombe ? | §2 |
| **Administration de Keycloak** | Créer un compte nominatif avec OTP puis supprimer `tmpadmin` ; déplacer `/root/.kc-secrets` hors du conteneur vers `/etc/pve/priv/` ; documenter l'emplacement retenu. **La vérification du MFA reste à faire** — elle demande ce mot de passe. | §2 |
| **SPOF pve1** | Documenter la procédure de reprise, déployer sur les 3 nœuds avec verrou, ou porter par une ressource de cluster ? Arbitrage distinct pour ACME et pour `backup-opnsense`. | §5 |
| ~~**Dérive de `configs/`**~~ | **Traité** — `scripts/check-drift.sh`, à lancer avant tout commit touchant `configs/` | §7 |

Les autres points (§3, §4, §6, §8 à §13) sont des corrections sans arbitrage :
elles peuvent être appliquées telles quelles.

---

## Méthode

Revue menée le 27/08/2026 sur le commit `65aaeda`. Lecture intégrale des 13
documents, des 15 fichiers de `configs/` et des 6 scripts, puis vérification par
SSH sur `pve1.infra.teleimagerie.net` : état Ceph et HA, inventaire des invités,
historique des sauvegardes PBS, `user.cfg` / `tfa.cfg` / `domains.cfg`, présence
des scripts et des timers sur les trois nœuds, comparaison de `configs/` aux
fichiers en production.

Aucune modification n'a été apportée au cluster. Deux commandes ont été
volontairement **non exécutées** parce qu'elles écrivent en production : le
`vzdump 203` de diagnostic (§1) et toute modification d'ACL (§2).
