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

## Ce qui est publié

| Nom | Traitement | Destination |
|---|---|---|
| `pacs-secours.teleimagerie.net` | terminaison TLS | `http://188.165.77.137` |
| `syngo.teleimagerie.net` | redirection 301 | → `syngo-via.teleimagerie.net` |
| `syngo.isoteam.mn` | redirection 301 | → `syngo-via.isoteam.mn` |
| `syngo-via.teleimagerie.net` | **relais TLS brut** | `37.61.243.246:443` (TSplus) |
| `syngo-via.isoteam.mn` | **relais TLS brut** | `37.61.243.246:443` (TSplus) |

> **`37.61.243.246` est aussi le WAN du pfSense** du tunnel site-à-site monté le
> 14/08/2026 ([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)). Les deux
> chantiers desservent donc le même site distant, par deux chemins indépendants :
> ce relais sort sur l'Internet public, le tunnel passe par WireGuard. Le relais
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
plus un bloc port 80 pour les quatre noms.

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

Relevé sur le conteneur le 14/08/2026 (`openssl x509 -noout -enddate -ext
subjectAltName`) :

| Certificat | Emplacement | Noms (SAN) | Échéance |
|---|---|---|---|
| `pacs-secours` | `/etc/letsencrypt/live/pacs-secours.teleimagerie.net/` | `pacs-secours.teleimagerie.net` | **17/10/2026** |
| `syngo-teleimagerie` | `/etc/nginx/certs/syngo-teleimagerie/` | `syngo.teleimagerie.net`, `syngo-via.teleimagerie.net` | **10/11/2026** |
| `syngo-isoteam` | `/etc/nginx/certs/syngo-isoteam/` | `syngo.isoteam.mn`, `syngo-via.isoteam.mn` | **10/11/2026** |

Les certificats `syngo` ne servent qu'aux **redirections 301** — le relais présente
celui de TSplus.

> **Résidu à nettoyer** : `/etc/letsencrypt/live/syngo.teleimagerie.net/`
> (échéance 05/10/2026, SAN `syngo.teleimagerie.net` seul) n'est **référencé par
> aucune configuration nginx**. C'est un vestige de la migration, que certbot
> continuera de renouveler pour rien. À supprimer avec
> `certbot delete --cert-name syngo.teleimagerie.net`.

Émis par **DNS-01 depuis pve1** (`/opt/acme`), délibérément : la clé API OVH donne
un droit d'écriture sur toute la zone et n'a pas à séjourner sur une machine
exposée à Internet.

**Après bascule DNS**, tous les noms pointeront ici et le renouvellement pourra
passer en HTTP-01 depuis le conteneur, sans aucune clé. C'est la transition à
faire, avec le retrait d'acme.sh de pve1.

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
```

**Lire `stream_access.log`** : chaque connexion relayée y apparaît deux fois — une
ligne client → `10.40.0.10:443`, une ligne `127.0.0.1` → `127.0.0.1:8445`.
L'absence de la seconde signifie que la connexion **n'a pas été relayée** vers
TSplus. Une entrée `bytes=309/19 time=0.000` est la signature d'un `ClientHello`
suivi d'une alerte TLS : le nom a été refusé par le serveur par défaut.
