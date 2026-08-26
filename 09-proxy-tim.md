# `proxy-tim` — reverse proxy nginx

Conteneur LXC **201**, Debian 13, nginx 1.26.3. Migré depuis le VPS
`vps-f89a8456.vps.ovh.net` (`51.75.203.20`) le 12/08/2026.

| | |
|---|---|
| Adresse interne | `10.40.0.10/24` (VLAN 400), passerelle `10.40.0.1` |
| Adresse publique | `57.130.34.122` — IP virtuelle sur OPNsense |
| Ressources | 2 vCPU, 2 Go RAM, disque 40 Go sur Ceph |
| Accès | `ssh root@10.40.0.10` depuis un nœud ayant accès au VLAN 400 |
| Haute dispo | **ressource HA** depuis le 15/08/2026 (`max_restart 3`, `max_relocate 3`) |
| Nœud courant | **pve3** depuis le test de bascule du 15/08/2026 |

> ✅ **`proxy-tim` est une ressource HA depuis le 15/08/2026** :
> `ha-manager add ct:201 --state started --max_restart 3 --max_relocate 3`,
> mêmes paramètres que `vm:100` et `vm:102`. Bascule testée le jour même vers
> pve3 : **~14 s d'interruption** mesurée en production
> ([05-tests-ha.md](05-tests-ha.md#test-4--bascule-planifiée-dun-conteneur)).
>
> Deux particularités d'un **conteneur** en HA, par rapport aux VM :
>
> - un CT LXC ne migre jamais « à chaud » : tout déplacement est un
>   arrêt/redémarrage (*restart migration*) — ~14 s de coupure, là où la VM 100
>   migre avec ~1 s. Le disque étant sur Ceph, rien n'est copié ;
> - `onboot: 1` (présent dans sa config) est désormais **sans effet** : le HA
>   manager décide seul du démarrage, y compris au boot du nœud.
>
> Sans groupe HA ni règle d'affinité, aucun nœud n'est « préféré » : le conteneur
> reste où la dernière bascule l'a posé. La copie de la config HA est archivée
> dans [configs/ha-resources.cfg](configs/ha-resources.cfg).

---

## Bascule DNS du 26/08/2026

**Le proxy reçoit la production depuis le 26/08/2026** : les trois noms servis
en HTTP local pointent sur `57.130.34.122` (TTL 60). Modification par l'API OVH
depuis pve1, vérifiée sur les serveurs autoritaires (`ns17`/`dns17.ovh.net`
pour `teleimagerie.net`, `ns102`/`dns102.ovh.net` pour `isoteam.mn` — chaque
zone a sa paire, [14-noms-de-domaine.md](14-noms-de-domaine.md#serveurs-autoritaires)),
sur `1.1.1.1` et `8.8.8.8`.

| Nom | DNS réel (Internet) | TTL | Changement |
|---|---|---|---|
| `pacs-secours.teleimagerie.net` | `57.130.34.122` ✅ | 60 | était `51.75.203.20` (TTL 3600, abaissé à 60 une heure avant) |
| `syngo.teleimagerie.net` | `57.130.34.122` ✅ | 60 | était `51.75.203.20` |
| `syngo.isoteam.mn` | `57.130.34.122` ✅ | 60 | **créé** — n'existait pas (anomalie n°2 de [14](14-noms-de-domaine.md#anomalies-relevées-25082026), soldée) |
| `syngo-via.teleimagerie.net` | `37.61.243.246` — TSplus direct | 60 | inchangé, volontairement |
| `syngo-via.isoteam.mn` | `37.61.243.246` — TSplus direct | — | inchangé, volontairement |

Contrôles post-bascule (26/08/2026, ~07 h UTC) :

- `https://pacs-secours.teleimagerie.net/xaconsolepacs/` → `200` par la chaîne
  réelle VIP → nginx → `10.40.0.40`, certificat conforme (échéance 17/10/2026,
  série identique à celle encore servie par le VPS — copies synchrones) ;
- `syngo.teleimagerie.net` et `syngo.isoteam.mn` → `301` vers leur
  `syngo-via.*` respectif, certificat valide ;
- IP réelles des clients dans `access.log` du conteneur (proxy_protocol
  fonctionnel, pas de `127.0.0.1`) ;
- le certbot du conteneur peut de nouveau renouveler `pacs-secours` en HTTP-01
  (le port 80 répond au nom, l'A pointe sur le proxy — l'échéance du
  17/10/2026 n'est plus une contrainte) ;
- **production confirmée en charge réelle à 07:10 UTC** (~13 min après la
  bascule, le temps d'expiration des caches) : `POST /PACS_TIM_BCK/VAL9/studies`
  authentifiés (`200`, 300–650 Ko) toutes les ~30 s depuis une IP de site, et
  une session navigateur réelle sur `/xaconsolepacs/` — IP réelles des deux
  côtés dans `access.log`. Le gros du volume de `pacs-secours` est ce flux
  d'**alimentation sous `/PACS_TIM_BCK/`**, pas la console
  ([15-pacs-secours.md](15-pacs-secours.md)).

Retour arrière si besoin : `python3 /root/bascule-3noms.py revert` sur pve1
(repointe les deux noms sur `51.75.203.20` et supprime `syngo.isoteam.mn`),
effectif en ~60 s grâce au TTL abaissé. Copie du script archivée dans
[scripts/bascule-3noms.py](scripts/bascule-3noms.py).

### Après stabilisation (voir [06 §2](06-reste-a-faire.md#2-bascule-dns-vers-proxy-tim--faite-le-26082026-reste-le-nettoyage))

- décommissionner l'ancien VPS `51.75.203.20` quand ses logs ne montrent plus
  de trafic légitime ;
- remonter le TTL des trois noms (60 → 3600) ;
- décider (ou pas) de la bascule de `syngo-via.*` vers le relais TLS du proxy —
  session RemoteApp réelle et paires de lignes `stream_access.log` à contrôler
  ce jour-là ; le relais ACME du port 80 vers TSplus est prêt.

---

## Ce qui est publié

Ce que le proxy est **configuré** pour servir. Depuis la bascule du
26/08/2026, il reçoit réellement le trafic des trois premiers noms ; les
`syngo-via.*` continuent d'arriver en direct chez TSplus (voir ci-dessus).

| Nom | Traitement | Destination |
|---|---|---|
| `pacs-secours.teleimagerie.net` | terminaison TLS | `http://10.40.0.40` — pacs03 par le vRack |
| `syngo.teleimagerie.net` | redirection 301 | → `syngo-via.teleimagerie.net` |
| `syngo.isoteam.mn` | redirection 301 | → `syngo-via.isoteam.mn` |
| `syngo-via.teleimagerie.net` | **relais TLS brut** | `37.61.243.246:443` (TSplus, DC TELLIS) |
| `syngo-via.isoteam.mn` | **relais TLS brut** | `37.61.243.246:443` (TSplus, DC TELLIS) |

> **Bascule du backend `pacs-secours` le 25/08/2026** : `http://188.165.77.137`
> (IP publique de pacs03, trafic en HTTP clair sur Internet) →
> `http://10.40.0.40` (même serveur, par le vRack sur le VLAN 400 —
> [15-pacs-secours.md](15-pacs-secours.md)). Le segment proxy→backend ne quitte
> plus le réseau privé ; latence mesurée 0,25 ms, MTU 1500 vérifié. Sauvegarde
> de l'ancien vhost : `/root/pacs-secours.conf.bak-2026-08-25` dans le CT 201 ;
> retour arrière = remettre l'ancienne ligne `proxy_pass` + reload.

> **`37.61.243.246` est le WAN du pfSense du DC TELLIS**
> ([13-tellis.md](13-tellis.md)), le même que celui du tunnel site-à-site monté
> le 14/08/2026 ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)).
> Derrière ce NAT, la cible est le serveur TSplus `192.168.101.102` (📋 déclaré,
> non vérifié). Les deux chantiers desservent donc le même site, par deux
> chemins indépendants : ce relais sort sur l'Internet public, le tunnel passe
> par WireGuard — vue d'ensemble dans
> [12-architecture-hds.md](12-architecture-hds.md#flux-inter-datacenters). Le relais
> pourrait emprunter le tunnel et viser une adresse privée du site — le trafic
> serait chiffré de bout en bout et cesserait de dépendre de l'exposition du
> port 443 côté distant. **Non fait, et non trivial** : cela déplace une
> dépendance de production sur un lien monté la veille, dont le comportement en
> bascule HA n'a pas encore été mesuré.

---

## Le problème que cette configuration résout

**TSplus multiplexe le port 443** : il y sert son portail web *et* les sessions
RDP de RemoteApp, en distinguant les deux à la volée. Terminer le TLS sur le proxy
détruit le RDP — nginx ne voit alors qu'un paquet X.224 illisible et répond `400`.
C'était la cause de l'erreur `0x1104` côté client.

Il faut donc **transmettre le TLS intact** à TSplus. Mais un relais brut interdit
d'ajouter `X-Forwarded-For`, et `pacs-secours` — le service principal, 25 000
requêtes par semaine — doit conserver l'IP réelle de ses clients.

Deux exigences contradictoires sur un même port, une seule adresse publique.

---

## L'architecture retenue

```
                     client
                        │
              57.130.34.122:443
                        │  (redirection NAT OPNsense)
                        ▼
          ┌─────────────────────────────┐
          │  streams-enabled/           │   lit le SNI sans déchiffrer
          │  443-router.conf            │   AJOUTE l'en-tête PROXY
          └──────┬───────────────┬──────┘
      syngo-via.*│               │ autres noms
      ou sans SNI│               │
                 ▼               ▼
        127.0.0.1:8445    127.0.0.1:8443 (https)
        RETIRE l'en-tête  lit l'en-tête PROXY
        PROXY             → $remote_addr = vrai client
                 │               │
                 ▼               ▼
      37.61.243.246:443    pacs-secours, redirections syngo.*
           TSplus
```

Le protocole PROXY ne s'active pas conditionnellement dans un même bloc nginx.
L'astuce consiste à **l'ajouter pour tout le monde**, puis à le **retirer** sur un
saut intermédiaire avant TSplus : un listener déclaré `proxy_protocol` consomme
l'en-tête et ne le retransmet pas. TSplus reçoit donc un flux TLS rigoureusement
identique à celui d'un client direct, pendant que le bloc HTTPS local récupère
l'adresse réelle via `set_real_ip_from` / `real_ip_header proxy_protocol`.

> **Le client RDP n'envoie pas de SNI.** Ce n'est pas un navigateur : il ouvre une
> session TLS sans annoncer de nom d'hôte. La ligne `"" → 127.0.0.1:8445` de la
> table d'aiguillage est donc **indispensable** — sans elle, la connexion RDP tombe
> dans `default`, se fait rejeter par le serveur par défaut, et le client affiche
> `0x1104`. C'est exactement la panne rencontrée le 13/08.

---

## Les fichiers

### `/etc/nginx/nginx.conf`

Deux ajouts par rapport au fichier repris du VPS :

```nginx
http {
    set_real_ip_from 127.0.0.1;      # le routeur transmet l'IP réelle...
    real_ip_header   proxy_protocol; # ...via l'en-tête PROXY
    ...
}
```

`worker_cpu_affinity auto` a été **retiré** : inopérant en conteneur non
privilégié, il inondait le journal de `sched_setaffinity() failed`.

Le bloc `stream {}` (hérité du VPS) inclut `streams-enabled/*.conf` et journalise
dans `stream_access.log` — c'est là que se lisent les diagnostics de relais.

### `streams-enabled/443-router.conf`

L'aiguillage décrit ci-dessus. Deux blocs `server` : le routeur sur `:443` et le
saut de suppression d'en-tête sur `127.0.0.1:8445`.

### `sites-available/000-default.conf`

Serveur par défaut qui **refuse tout nom non déclaré**, en TLS via
`ssl_reject_handshake on`.

Sans lui, nginx sert le premier vhost chargé à n'importe quel nom, avec son
certificat et son backend : une erreur de DNS enverrait silencieusement du trafic
au mauvais service. Ce défaut existait sur le VPS.

Le port 80 y renvoie `421`, en laissant passer `/.well-known/acme-challenge/`.

### `sites-available/pacs-secours.teleimagerie.net.conf`

Repris du VPS sans modification de fond. Seul le `listen` a changé :
`443 ssl` → `127.0.0.1:8443 ssl proxy_protocol`, puisque le trafic arrive
désormais par le routeur.

`client_max_body_size 10G` — d'où le disque de 40 Go : nginx met le corps des
requêtes en tampon **sur disque**. `proxy_request_buffering off` supprimerait ce
besoin, à évaluer séparément.

### `sites-available/syngo.teleimagerie.net.conf`

Redirections 301 de `syngo.*` vers `syngo-via.*`, avec nos propres certificats,
plus deux blocs port 80 (scindés le 24/08/2026) :

- `syngo.*` : redirection https, défis ACME servis localement ;
- `syngo-via.*` : **les défis ACME sont relayés vers TSplus**
  (`proxy_pass http://37.61.243.246`). C'est ce qui permettra à TSplus de
  continuer à renouveler lui-même ses certificats si les A de `syngo-via.*`
  sont un jour basculés vers le proxy (non fait au 26/08/2026), le HTTP-01 de
  Let's Encrypt arrivant alors sur le proxy et non plus chez lui. Sans ce
  relais, son renouvellement casserait silencieusement ce jour-là.

Pourquoi rediriger plutôt que servir : en relais TLS c'est **le certificat de
TSplus** qui est présenté, et il ne couvre que les noms `syngo-via.*`.

### `streams-enabled/syngo-ports.conf` — **supprimé**

Relais TCP/UDP des ports 3389, 19955 et 19956 vers TSplus, repris du VPS.

**Ces trois flux n'ont jamais rien transporté** : 461 tentatives en `502` sur la
fenêtre journalisée, le backend refusant ces ports même depuis le VPS. Le RDP
passant par le 443, ils n'avaient plus d'usage — et le 3389 exposé attirait 851
sources de balayage distinctes.

**Fait** : le fichier a été retiré du conteneur et les redirections
correspondantes supprimées d'OPNsense. Vérifié le 14/08/2026 —
`streams-enabled/` ne contient plus que `443-router.conf`, et `pfctl -sn` sur
OPNsense ne mentionne plus aucun port 3389.

---

## Certificats

Relevé du 24/08/2026 :

| Certificat | Emplacement | Noms (SAN) | Échéance | Renouvelé par |
|---|---|---|---|---|
| TSplus | sur le serveur TSplus | `syngo-via.teleimagerie.net`, `syngo-via.isoteam.mn` | **03/11/2026** | TSplus lui-même (Let's Encrypt intégré, HTTP-01) |
| `pacs-secours` | `/etc/letsencrypt/live/pacs-secours.teleimagerie.net/` | `pacs-secours.teleimagerie.net` | **17/10/2026** | certbot du conteneur (`certbot.timer`) |
| `syngo-teleimagerie` | `/etc/nginx/certs/syngo-teleimagerie/` | `syngo.teleimagerie.net`, `syngo-via.teleimagerie.net` | **22/11/2026** | acme.sh sur pve1, déployé automatiquement |
| `syngo-isoteam` | `/etc/nginx/certs/syngo-isoteam/` | `syngo.isoteam.mn`, `syngo-via.isoteam.mn` | **10/11/2026** | idem |

**Le proxy ne gère aucun certificat pour `syngo-via.*`** : ces noms sont en
relais TLS brut, c'est TSplus qui présente et renouvelle le sien. Les SAN
`syngo-via.*` des certificats locaux sont un sous-produit de leur émission
groupée — seuls les noms `syngo.*` (redirections 301) les utilisent.

### Renouvellement automatisé depuis pve1 — mis en place le 24/08/2026

pve1 n'avait **aucun automate** (ni cron — le paquet n'est pas installé — ni
timer) : les certs syngo seraient morts le 10/11/2026 sans que rien ne les
renouvelle, et sans mécanisme pour les pousser vers le conteneur. Désormais :

- timer systemd **`acme-renew.timer`** sur pve1 (quotidien, ~03h17 UTC) lance
  `acme.sh --cron --home /opt/acme` ;
- à chaque renouvellement, acme.sh pose les fichiers dans
  `/opt/acme/deployed/<nom>/` puis exécute **`/opt/acme/deploy-syngo.sh`**
  (hook enregistré par `--install-cert`, copie archivée dans
  [scripts/deploy-syngo.sh](scripts/deploy-syngo.sh)), qui les copie en scp vers
  `root@10.40.0.10:/etc/nginx/certs/<nom>/` et recharge nginx après `nginx -t`.
  La cible est l'IP du CT, pas un nœud : insensible aux bascules HA. La clé
  publique de root@pve1 a été ajoutée aux `authorized_keys` du conteneur ;
- chaîne testée de bout en bout le 24/08 (`--renew --force` sur
  `syngo.teleimagerie.net` : émission DNS-01, déploiement, reload — d'où son
  échéance décalée au 22/11).

L'émission reste en **DNS-01 depuis pve1** (`/opt/acme`), délibérément : la clé
API OVH donne un droit d'écriture sur toute la zone et n'a pas à séjourner sur
une machine exposée à Internet. Passer en HTTP-01 local au conteneur après la
bascule DNS resterait possible, mais n'a plus d'intérêt : l'automate est en
place et la clé ne quitte pas pve1.

> Le résidu `/etc/letsencrypt/live/syngo.teleimagerie.net/` signalé ici a été
> **supprimé le 24/08/2026** (`certbot delete`). Ne restent sous certbot que
> les fichiers de `pacs-secours`.

---

## Incident : certificat TSplus expiré (19–24/08/2026)

Du 19 au 24/08, TSplus a présenté un certificat **expiré** aux utilisateurs
(qui le joignent en direct, la bascule DNS n'étant pas faite). Il avait
pourtant **renouvelé avec succès le 05/08** — son HTTP-01 fonctionne tant que
le DNS pointe droit sur lui — mais servait toujours l'ancien : le
renouvellement n'active pas le nouveau certificat tant que le serveur web
TSplus n'est pas relancé. La réinitialisation du certificat dans l'AdminTool le
24/08 a activé le bon (échéance 03/11/2026), vérifié ensuite sur tous les
chemins : direct, via le proxy avec chaque SNI, et sans SNI.

Leçon : surveiller l'échéance **présentée sur le fil** (`openssl s_client`),
pas la date du dernier renouvellement — les deux peuvent diverger.

---

## Diagnostic

```bash
# tester un nom sans dépendre du DNS
curl -sS --resolve <nom>:443:57.130.34.122 -o /dev/null \
     -w '%{http_code} cert=%{ssl_verify_result}\n' https://<nom>/

# quel certificat pour quel nom
echo | openssl s_client -connect 57.130.34.122:443 -servername <nom> 2>/dev/null \
     | openssl x509 -noout -subject

# simuler le client RDP (sans SNI) : doit rendre le certificat TSplus
echo | openssl s_client -connect 57.130.34.122:443 -noservername 2>/dev/null \
     | openssl x509 -noout -subject

# le relais ACME du port 80 vers TSplus : la réponse doit venir de TSplus
# (302 vers https), pas un 404 local
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Host: syngo-via.teleimagerie.net' \
     http://57.130.34.122/.well-known/acme-challenge/test
```

**Lire `stream_access.log`** : chaque connexion relayée y apparaît deux fois — une
ligne client → `10.40.0.10:443`, une ligne `127.0.0.1` → `127.0.0.1:8445`.
L'absence de la seconde signifie que la connexion **n'a pas été relayée** vers
TSplus. Une entrée `bytes=309/19 time=0.000` est la signature d'un `ClientHello`
suivi d'une alerte TLS : le nom a été refusé par le serveur par défaut.
