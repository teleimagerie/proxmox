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
| Accès | `ssh root@10.40.0.30` depuis un nœud ayant accès au VLAN 400 |
| Haute dispo | **ressource HA** depuis le 15/08/2026 (`max_restart 3`, `max_relocate 3`) |
| Nœud courant | **pve1** depuis le test de bascule du 15/08/2026 |
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
| users `site-<code>` | un par site distant, créés au fil des déploiements | clés pré-auth `tag:gateway` — révoquer un site = supprimer ses nœuds sans toucher au reste |
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

**Poste admin (Windows/WSL2)** : installer le client Tailscale **Windows** (il
couvre aussi WSL2 via le réseau de l'hôte — ne pas doubler d'un tailscaled dans
WSL2), puis `tailscale login --login-server https://headscale.teleimagerie.net`
et, sur le CT 202, `headscale nodes register --user admin --key mkey:...`
(la commande exacte s'affiche dans le navigateur).

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
