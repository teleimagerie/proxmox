# `headscale` — plan de contrôle VPN (tailnet)

Conteneur LXC **202**, Debian 13, headscale **v0.29.3**. Déployé le 15/08/2026
pour que des **passerelles DICOM sur sites distants** montent des VPN WireGuard
vers le cluster — dans les deux sens : pousser des images vers les serveurs
hébergés ici (PACS à venir), et être administrées depuis ici.

| | |
|---|---|
| Adresse interne | `10.40.0.30/24` (VLAN 400), passerelle `10.40.0.1` |
| Adresse publique | `57.130.34.123` — IP virtuelle sur OPNsense |
| Nom public | `headscale.teleimagerie.net` (A → `.123`, TTL 300, record OVH 5429302185) |
| Ports exposés | **443/tcp** (contrôle + DERP) · **3478/udp** (STUN) |
| Ressources | 2 vCPU, 2 Go RAM, disque 10 Go sur Ceph (`vm-storage`) |
| Accès | `ssh -t root@pve1.infra.teleimagerie.net pct enter 202` (sur le nœud qui héberge le CT — `ha-manager status`) · ou `ssh root@10.40.0.30` depuis un nœud du VLAN 400 (première fois : accepter la clé d'hôte du CT — jamais fait depuis pve1 au 25/08/2026, un accès non-interactif échoue) |
| Haute dispo | **ressource HA** depuis le 15/08/2026 (`max_restart 3`, `max_relocate 3`) |
| Nœud courant | **pve1** depuis le test 6 du 27/08/2026 (récupération après coupure de pve2 — [05-tests-ha.md](05-tests-ha.md#test-6--triple-coupure-matérielle-un-nœud-après-lautre-interface-ovh)) |
| Plage tailnet | **`100.72.0.0/16`** (v4) · `fd7a:115c:a1e0::/48` (v6) |

> Le serveur headscale est un **plan de contrôle pur** : il enrôle les machines,
> distribue clés, IPs et ACLs. Le trafic de données circule en WireGuard
> **directement entre les nœuds** — mesuré le 15/08/2026 : pendant une bascule HA
> du CT 202 (plan de contrôle arrêté ~30 s), un flux entre deux nœuds du tailnet
> n'a **perdu aucune requête** (120/120). Un plan de contrôle indisponible
> n'interrompt pas les tunnels établis ; seuls les enrôlements, rotations de
> clés et changements d'ACL attendent.

---

## Architecture

```
 passerelle DICOM (site N)                    poste admin
   tailscale client                        tailscale client
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
         headscale.teleimagerie.net = 57.130.34.123
                443/tcp (TLS)  ·  3478/udp (STUN)
                       │  (redirection NAT OPNsense)
                       ▼
              CT 202 · 10.40.0.30 (VLAN 400)
              headscale v0.29.3 + DERP embarqué
                       ·
        trafic DICOM : WireGuard DIRECT passerelle ⇄ serveur
        (le CT 202 ne voit ce trafic que si le direct échoue,
         et alors seulement chiffré, relayé par son DERP)
```

- **La plage `100.72.0.0/16`** est prise dans `100.64.0.0/10` (imposé par les
  clients Tailscale) mais évite délibérément `100.64.0.0/24` : **`100.64.0.1`
  est la passerelle publique OVH des trois hyperviseurs** (CGNAT). Corollaire :
  **ne jamais enrôler un nœud Proxmox dans le tailnet.** Elle évite aussi
  `100.100.100.100` (résolveur MagicDNS des clients) et ne croise aucune plage
  du cluster ni des sites (10.40/10.90/10.30/10.100/10.200, 172.33,
  192.168.101/111 — TELLIS, [13-tellis.md](13-tellis.md)).
- **DERP embarqué** (région 999 « tim », `verify_clients: true` : seuls les nœuds
  du tailnet peuvent relayer) — aucun relais public Tailscale (`urls: []`),
  aucune télémétrie (`logtail: false`). Même relayé, le trafic reste chiffré de
  bout en bout : le relais ne voit jamais les images en clair.
- **Pas de subnet router** : chaque futur serveur hébergé (PACS…) enrôle son
  propre client tailscale. Décision délibérée — ne pas cumuler « exposé à
  Internet » et « routeur vers le VLAN 400 » sur la même machine, et garder des
  ACLs par tag, plus fines qu'un filtrage par IP. Si un équipement ne peut pas
  porter le client, créer un CT dédié (203) — jamais sur le CT 202.
- **TLS autonome** : Let's Encrypt intégré en **TLS-ALPN-01** sur le 443
  (`certmagic` renouvelle seul, cache persistant `/var/lib/headscale/cache`,
  sauvegardé avec le CT). Conforme à la règle maison : **aucune clé API OVH sur
  une machine exposée**. Contrainte assumée : le 443 public doit être joignable
  à chaque (re)nouvellement. Certificat émis le 15/08/2026, échéance 13/11/2026.
- **MagicDNS** : `<machine>.ts.teleimagerie.net` (domaine disjoint du
  `server_url`, exigence headscale). `override_local_dns: false`, délibéré :
  les passerelles gardent le DNS local de leur site hospitalier — MagicDNS ne
  résout que les noms du tailnet, via `100.100.100.100`.
- Base **SQLite** (`/var/lib/headscale/db.sqlite`, WAL) — dimensionné pour des
  dizaines de nœuds, part dans le vzdump quotidien avec le CT.

Configs archivées : [configs/headscale-config.yaml](configs/headscale-config.yaml)
et [configs/headscale-acl.hujson](configs/headscale-acl.hujson).

---

## Organisation du tailnet

| Objet | Valeur | Rôle |
|---|---|---|
| user `admin` (ID 1) | postes d'administration | enrôlement interactif |
| user `infra` (ID 2) | serveurs hébergés sur le cluster | clés pré-auth `tag:pacs` |
| users `site-<code>` | un par site distant, créés au fil des déploiements | portent les clés pré-auth `tag:gateway` ; **leurs nœuds atterrissent sous `tagged-devices`** — révoquer un site = `headscale nodes delete` de ses `gw-<code>` ([07-pieges.md, piège 31](07-pieges.md#31-les-nœuds-enrôlés-par-clé-taguée-nappartiennent-pas-au-user-de-la-clé)) |
| user `tagged-devices` (synthétique) | créé par headscale | propriétaire de tous les nœuds tagués — le tag remplace le user comme identité (constaté le 25/08/2026) |
| `tag:gateway` | passerelles DICOM | n'atteint que `tag:pacs:104,11112` |
| `tag:pacs` | serveurs DICOM hébergés | n'initie rien |

L'ACL est en **deny par défaut** : aucune règle n'autorise le trafic
passerelle ↔ passerelle, et c'est voulu. Matrice **vérifiée le 15/08/2026** avec
deux CT jetables enrôlés (`tag:gateway` et `tag:pacs`) :

| Test | Attendu | Mesuré |
|---|---|---|
| gateway → pacs, port 11112 | passe | **HTTP 200** |
| gateway → pacs, autre port | bloqué | timeout |
| pacs → gateway (tout port) | bloqué | timeout |
| chemin retenu | direct | `direct`, pas de relais |
| `tailscale netcheck` | une seule région DERP | `tim` uniquement, 200 µs |

Les ports 104/11112 sont les ports DICOM usuels — **à resserrer au port réel
quand le PACS existera**.

---

## Enrôler une passerelle DICOM (procédure par site)

Deux modes d'enrôlement coexistent, et le choix n'est pas cosmétique. Les
machines sans humain devant (passerelles, serveurs hébergés) s'enrôlent par
**clé pré-auth taguée** : l'identité ACL vient du **tag**, l'opération est
scriptable. Les appareils d'administration s'enrôlent en **interactif** sous le
user `admin` (section suivante) : l'identité vient du **user**. Une passerelle,
donc, toujours par clé `tag:gateway` :

```bash
# 1. Sur le CT 202 : créer le user du site (une fois), puis une clé
headscale users create site-<code>
headscale users list                     # relever l'ID
headscale preauthkeys create --user <ID> --expiration 24h --tags tag:gateway
```

La clé est à **usage unique**, expire en 24 h (fenêtre d'enrôlement seulement —
le nœud, lui, n'expire jamais : `node.expiry: 0`), et porte le tag d'office.
**C'est un secret** : la transmettre par le canal des secrets, jamais par mail,
jamais dans ce dossier.

```bash
# 2. Sur la passerelle (Debian/Ubuntu)
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --login-server=https://headscale.teleimagerie.net \
  --auth-key=<clé> --hostname=gw-<code>

# 3. Vérifications
tailscale status          # le nœud apparaît, IP en 100.72.x
tailscale netcheck        # une seule région DERP : "tim"
```

**Passerelle Windows** : même logique, seule la pose du client change.
Installer le client Tailscale Windows officiel, puis dans un PowerShell
administrateur :

```powershell
tailscale up --login-server=https://headscale.teleimagerie.net `
  --auth-key=<clé> --hostname=gw-<code>
```

Ensuite **activer « Run unattended »** (icône Tailscale de la zone de
notification → préférences) : sans cette option le tunnel s'arrête à la
fermeture de la session Windows — rédhibitoire pour une passerelle. Si
l'enrôlement boucle en erreur (procédure officielle) : arrêter Tailscale,
supprimer `C:\Users\<user>\AppData\Local\Tailscale`, supprimer le nœud côté
headscale, relancer. L'instance publie aussi ses instructions par OS sur
`/windows` et `/apple` (ex. `https://headscale.teleimagerie.net/windows`).

Première passerelle de production enrôlée le 25/08/2026 par la procédure
Windows ci-dessus : `gw-qum` (clé du user `site-QUM`, `100.72.0.2`,
`tag:gateway` posé, en ligne du premier coup). Mesuré depuis le site le même
jour : `netcheck` **UDP ok** (sortie publique découverte, DERP `tim` seul à
22,3 ms) ; `tailscale ping` vers le téléphone admin passe mais reste
`via DERP(tim)` — direct non établi avec un mobile en CGNAT, attendu et non
représentatif du futur flux gateway → pacs (deux extrémités fixes). Entre
extrémités fixes, justement, le direct est confirmé le même jour : poste
admin ↔ `gw-qum` en `direct` à 32 ms (contre ~40 ms via DERP). **La montée
en direct prend quelques dizaines de secondes** : les premiers pongs d'un
`tailscale ping` passent par DERP, ce n'est pas un échec — laisser tourner
avant de conclure.

**Serveur hébergé ici (futur PACS)** : clé `--tags tag:pacs` sous le user
`infra`. En VM, rien de spécial. En **CT non privilégié**, tailscaled a besoin
de `/dev/net/tun` — ajouter à `/etc/pve/lxc/<id>.conf` **avant** le premier
démarrage :

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

Depuis le VLAN 400, `headscale.teleimagerie.net` se joint par la VIP publique en
épingle à cheveux — fonctionne grâce au correcteur de réflexion NAT
([07-pieges.md, piège 29](07-pieges.md#29-la-réflexion-nat-seule-ne-suffit-pas--il-faut-aussi-le-nat-sortant-du-retour)).

---

## Enrôler un appareil d'administration (poste, téléphone)

Les appareils personnels s'enrôlent sous le user `admin`, en **interactif** —
jamais par clé pré-auth taguée : leurs droits viennent du **user** (`admin@`
dans l'ACL), pas d'un tag. Le principe est le même sur tous les OS : le client
est pointé vers `https://headscale.teleimagerie.net`, il ouvre une page web qui
affiche une demande d'enregistrement (`hskey-authreq-...`), et l'enrôlement
s'approuve **sur le CT 202** :

```bash
# La commande exacte s'affiche dans le navigateur du client, avec USERNAME
# en placeholder : headscale ne sait pas à qui est l'appareil, c'est ici
# qu'on le déclare — remplacer USERNAME par admin.
headscale auth register --auth-id hskey-authreq-... --user admin
headscale nodes list          # le nœud apparaît, IP en 100.72.x
```

> Syntaxe **v0.29** — `headscale nodes register --key mkey:...`, que montrent
> encore d'anciennes docs, est **déprécié** (constaté le 25/08/2026 sur le
> CT 202). La demande `hskey-authreq` est éphémère : si l'approbation tarde
> et que la commande échoue, relancer la connexion côté client pour obtenir
> un nouvel identifiant.

Le `hskey-authreq-...` est une **session en attente**, pas une clé stockée :
l'approbation la consomme, `headscale auth reject --auth-id hskey-authreq-...`
l'annule, et elle expire seule sinon. Une fois consommée ou expirée il n'y a
**rien à nettoyer** — vérifié le 25/08/2026 : un `reject` sur un identifiant
déjà consommé répond `NotFound`. Ce qui persiste et se gère, ce sont les clés
pré-auth taguées : `headscale preauthkeys list|expire|delete --user <ID>`.

Premiers appareils de production enrôlés le 25/08/2026, procédures vérifiées
en réel : le téléphone du poste d'administration (`z-fold4-de-matthieu`,
Android, `100.72.0.1`) puis le poste Windows/WSL2 (`lenovo-mca2`,
`100.72.0.3`), tous deux sous `admin`, sans expiration. Constaté au passage :
les deux appareils admin **ne se voient pas** dans `tailscale status` —
aucun flux `admin ↔ admin` n'étant autorisé, headscale ne les présente même
pas l'un à l'autre. C'est voulu, pas une panne.

Mise en route par OS (chemins d'interface vérifiés le 25/08/2026, doc
headscale, pages `usage/connect/`) :

- **Windows/WSL2** : installer le client Tailscale **Windows** (il couvre aussi
  WSL2 via le réseau de l'hôte — **ne pas doubler d'un tailscaled dans WSL2**),
  puis `tailscale login --login-server https://headscale.teleimagerie.net`.
- **Linux** : `curl -fsSL https://tailscale.com/install.sh | sh` puis
  `tailscale up --login-server=https://headscale.teleimagerie.net` — sans
  `--auth-key`, la commande imprime l'URL d'enrôlement à ouvrir.
- **Android** (app Tailscale du Play Store) : menu réglages en haut à droite →
  `Accounts` → menu ⋮ → **Use an alternate server** → saisir l'URL du serveur
  et suivre les instructions. Le client se connecte seul dès le `register`.
- **iOS** (app Tailscale de l'App Store) : icône de compte → `Log in…` → menu
  en haut à droite → **Use custom coordination server** → saisir l'URL, même
  approbation côté CT 202.

Nommer chaque appareil clairement (`--hostname` sur les postes, nom de
l'appareil dans l'app mobile) : c'est ce nom qui devient
`<machine>.ts.teleimagerie.net` en MagicDNS.

Ce que l'ACL ([configs/headscale-acl.hujson](configs/headscale-acl.hujson),
deny par défaut) donne à chaque type de client :

| Client | Initie vers | Reçoit de |
|---|---|---|
| appareil `admin@` | `tag:gateway:*`, `tag:pacs:*` | personne — **pas non plus de trafic téléphone ↔ poste** (aucune règle `admin@ → admin@`, Taildrop désactivé) |
| `tag:gateway` | `tag:pacs:104,11112` uniquement | `admin@` |
| `tag:pacs` | rien | `tag:gateway` (ports DICOM), `admin@` |

---

## Authentification OIDC — Keycloak (depuis le 27/08/2026)

La config porte une section `oidc` pointant sur
`https://auth.teleimagerie.net/realms/tim` (client `headscale`, secret dans
`/etc/headscale/oidc_secret`, mode 600) — copie à jour dans
[configs/headscale-config.yaml](configs/headscale-config.yaml), détail côté
IdP dans [16-keycloak.md](16-keycloak.md).

C'est une **voie d'enrôlement supplémentaire**, pas un remplacement : les
users locaux (`admin`, `infra`, `site-<code>`) et les clés de pré-enrôlement
des passerelles continuent de fonctionner à l'identique. Un login OIDC crée
son propre user headscale à la volée.

Deux dépendances à connaître :

- **headscale ne démarre pas si l'issuer est injoignable** (validé au boot —
  constaté en crash-loop le 27/08/2026). Secours si Keycloak est durablement
  mort : commenter la section `oidc` de `/etc/headscale/config.yaml` et
  redémarrer — les nœuds déjà enrôlés n'en ont pas besoin ;
- le CT doit résoudre `auth` par la **vue interne** (`nameserver 10.40.0.1`,
  posé par `pct set 202 --nameserver` le 27/08/2026) —
  [pièges n° 32 et 33](07-pieges.md#32-joindre-la-vip-122-depuis-lintérieur-aboutit-sur-la-gui-dopnsense).

---

## Mesures — bascule HA du CT 202 (15/08/2026)

Deux bascules chronométrées (méthode du test 4, [05-tests-ha.md](05-tests-ha.md)) :
une boucle `curl /health` (1 req/s, chemin public) pour le plan de contrôle, et
une boucle entre deux nœuds du tailnet (1 req/s, port 11112) pour le data plane.

| Mesure | Bascule 1 (pve1→pve2) | Bascule 2 (pve2→pve1) |
|---|---|---|
| Durée totale de l'opération | 41 s | 29 s |
| Coupure du **plan de contrôle** | ~22 s (10:06:25→10:06:47 UTC) | ~12 s (10:10:15→10:10:27 UTC) |
| Coupure du **data plane** (tunnel direct) | — | **0 s — 120/120 requêtes servies** |

Les clients (`tailscale status`) sont redevenus sains sans aucune intervention.

> **Artefact de mesure à connaître** : après chaque bascule, la boucle `curl`
> du poste d'admin a montré des échecs intermittents pendant ~3 min alors que le
> data plane était continu et que le service répondait à des connexions neuves.
> Cause : les connexions abandonnées pendant la coupure laissent dans `pf` des
> états à moitié ouverts ; le NAT du poste réutilise les mêmes ports source, qui
> tombent sur ces états morts jusqu'à leur expiration. Ce n'est **pas** une
> panne du service — les vrais clients ré-ouvrent des connexions sur des ports
> frais.

---

## Diagnostic

```bash
# Depuis n'importe où
curl -s https://headscale.teleimagerie.net/health        # {"status":"pass"}

# Sur le CT 202
headscale nodes list                # qui est enrôlé, en ligne, tagué
headscale users list
journalctl -u headscale -f
curl -s 127.0.0.1:9090/metrics     # métriques Prometheus (supervision future)

# Sur un client
tailscale status                    # pairs et chemin (direct / via DERP "tim")
tailscale netcheck                  # STUN/DERP vus depuis le client
tailscale ping <ip-100.72.x>        # affiche le chemin réellement emprunté
```

> **Le STUN embarqué ne répond qu'aux clients Tailscale.** Constaté le
> 15/08/2026 : une sonde STUN générique (Binding Request RFC 5389, même avec
> FINGERPRINT) reste **sans réponse** — le socket écoute mais le parseur exige
> l'attribut SOFTWARE `tailnode` et jette le reste en silence, par conception.
> Un timeout d'une sonde générique sur `3478/udp` ne prouve donc **aucune**
> panne. Tester avec `tailscale netcheck` depuis un vrai client, ou avec
> `scripts/stun-tailnode.py` qui imite l'en-tête attendu (vérifié : réponse en
> local, depuis pve1 et depuis le poste d'admin via la VIP publique).

---

## Risques et limites

- **OPNsense (VM 100) est devant tout** : sa bascule HA (~2 min) coupe contrôle
  **et** data plane vers les serveurs hébergés. Les clients retentent seuls.
- **Bascule du CT 202** : ~12-22 s de coupure du plan de contrôle, data plane
  intact (mesuré, tableau ci-dessus). Les flux passant par le DERP embarqué,
  eux, cassent et se rétablissent seuls.
- **Renouvellement TLS** : le 443 public doit rester joignable (TLS-ALPN).
  Ne jamais boucler sur un échec d'émission — rate-limits Let's Encrypt
  (5 échecs de validation/heure). Le cache de certs est persistant et sauvegardé.
- **Ne jamais enrôler un hyperviseur** (passerelle OVH `100.64.0.1` dans la
  plage Tailscale ; la route du tailnet l'écraserait).
- **Le paquet .deb démarre headscale dès l'installation avec sa config
  d'exemple** (constaté le 15/08/2026) : après avoir posé la vraie config,
  `systemctl restart headscale` — un `enable --now` ne redémarre pas un service
  déjà actif, qui continue alors d'écouter sur `127.0.0.1:8080`.
- Montées de version : lire le changelog headscale — les champs de
  `config.yaml` et la syntaxe des ACL bougent entre versions mineures
  (`headscale policy check --file` valide une ACL avant redémarrage).
