# Tests de haute disponibilité

Mesures réelles : tests 1 à 3 réalisés le 11 août 2026 sur une VM Debian 13
cloud jetable (2 Go RAM, disque 3 Go sur Ceph, IP `10.30.0.200`), supprimée
depuis ; test 4 réalisé le 15 août 2026 sur le CT 201 en production. Chiffres
mesurés, pas estimés.

## Test 1 — Migration à chaud

`ha-manager crm-command migrate vm:9000 pve2`, ping à 200 ms depuis un tiers nœud.

| Mesure | Valeur |
|---|---|
| Durée totale de l'opération | 26 s |
| **Coupure réseau réelle** | **1,0 s** (5 paquets perdus) |

Le transfert emprunte le VLAN 200 (`migration: secure,network=10.200.0.0/24`).

## Test 2 — `sysrq-b` : le test qui ne prouve rien

`echo b > /proc/sysrq-trigger` sur le nœud portant la VM.

| Heure UTC | Événement |
|---|---|
| ~10:53 | Reset brutal de pve2 |
| 10:54:46 | pve3 acquiert `ha_manager_lock`, devient maître ; pve2 → `unknown` |
| 10:54:58 | **pve2 a fini de redémarrer** |
| 10:55:19 | Le LRM de pve2 reprend son verrou et relance la VM |
| 10:55:29 | VM démarrée — **sur pve2 lui-même** |

**Ce test ne valide pas la relocalisation.** `sysrq-b` redémarre en ~65 s, plus
vite que le délai de fencing : le nœud revient et reprend son propre service
avant que le CRM ne décide de le déplacer.

Ce qu'il valide tout de même : la réélection du maître HA et le redémarrage
automatique de la VM.

> **À retenir pour tout futur test** : un reboot rapide ne teste pas la HA.
> Il faut que le nœud reste absent plus longtemps que le fencing.

## Test 3 — Isolation durable : le vrai test

Méthode : `systemctl mask corosync && systemctl stop corosync` sur pve2. Le nœud
perd le quorum, s'auto-fence par watchdog, et **ne rejoint pas** au redémarrage
puisque corosync est masqué — ce qui force la relocalisation.

Un filet de sécurité (`corosync-restore.service`, démasquage automatique 10 min
après boot) avait été armé avant, puis retiré.

| Heure UTC | Δ | Événement |
|---|---|---|
| 11:10:55 | 0 s | Isolation de pve2 |
| 11:10:56 | +1 s | CRM : pve2 `online` → `unknown` |
| 11:11:46 | +51 s | CRM : pve2 → `fence`, service → `fence` |
| ~11:12:01 | +66 s | **Watchdog : auto-reset de pve2 — la VM tombe** |
| 11:13:06 | +131 s | CRM récupère `ha_agent_pve2_lock`, décide `pve2 → pve1` |
| 11:13:10 | +135 s | **VM démarrée sur pve1** |

| Mesure | Valeur |
|---|---|
| Détection de la défaillance | 51 s |
| De l'incident à la VM relancée ailleurs | **2 min 15 s** |
| **Indisponibilité réelle de la VM** | **~84 s** |

Dans une vraie panne matérielle (perte d'alimentation), la VM tombe à t=0 au lieu
de t+66 s : l'indisponibilité attendue est alors de **~2 min 15 s**.

### Ceph pendant l'incident

```
health: HEALTH_WARN
        1/3 mons down, quorum pve1,pve3
        2 osds down
        1 host (2 osds) down
        Degraded data redundancy: 279/837 objects degraded (33.333%),
        33 pgs degraded, 33 pgs undersized
pgs:    33 active+undersized+degraded
io:     client: 544 KiB/s rd, 44 KiB/s wr
```

Un tiers des objets dégradés — une réplique sur trois. **`active`** : les I/O
n'ont jamais été bloquées, et le trafic client apparaît bien dans les compteurs.

Le cluster Proxmox est resté `Quorate` avec 2 votes sur 3.

### Retour à la normale

Après démasquage et redémarrage de corosync sur pve2 : quorum reformé en quelques
secondes, Ceph revenu `HEALTH_OK` avec les 33 PG `active+clean` en **moins d'une
minute**. La VM est restée sur pve1 — pas de retour arrière automatique, faute de
groupe HA définissant une préférence de nœud.

## Test 4 — Bascule planifiée d'un conteneur

Réalisé le **15 août 2026** lors de la mise en HA du CT 201 (`proxy-tim`), **en
production**. Mesure : 1 requête HTTPS/s sur `pacs-secours.teleimagerie.net`
depuis le poste d'admin (`curl --max-time 2`), le CT partant de pve1.

```bash
ha-manager crm-command migrate ct:201 pve3
```

| Heure UTC | Δ | Événement |
|---|---|---|
| 08:41:42 | 0 s | Commande envoyée |
| 08:41:57 | +15 s | Dernière requête servie depuis pve1 — **le CT tombe** |
| 08:42:11 | +29 s | **Première requête servie depuis pve3** |
| 08:42:13 | +31 s | `ha-manager status` : `ct:201 (pve3, started)` |

| Mesure | Valeur |
|---|---|
| Durée totale de l'opération | ~31 s |
| **Interruption de service réelle** | **~14 s** |

Contrairement à une VM (Test 1 : 1,0 s de coupure), un CT ne migre pas à chaud :
le HA manager l'**arrête** sur le nœud d'origine puis le **redémarre** sur la
cible (*restart migration*). Le disque étant sur Ceph, rien n'est copié — les
14 s couvrent le stop, le start et la relance de nginx.

Vérifications après bascule : `pct exec 201 -- nginx -t` OK, les 5 URLs publiées
répondent (le 404 sur `/` de `pacs-secours` est le comportement de base — la
racine n'est pas servie, l'application vit sous `/xaconsolepacs/` qui doit
répondre `200` — vérifié identique avant la bascule ;
[15-pacs-secours.md](15-pacs-secours.md#mesures-du-25082026)).

## Test 5 — Redémarrage planifié d'un nœud entier (politique `migrate`)

Réalisé le **27 août 2026**, **en production**, à la demande : pve1 rebooté
avec les CT 201 (proxy-tim) et 203 (keycloak) placés dessus au préalable —
pve1 ne portait rien ce jour-là, il fallait des témoins réels. Mesure : sonde
HTTPS toutes les 2 s sur `auth.teleimagerie.net` (well-known OIDC) et toutes
les 10 s sur `pacs-secours.teleimagerie.net`, depuis le poste d'admin.

```bash
ssh root@pve1... reboot     # datacenter.cfg : ha: shutdown_policy=migrate
```

| Heure UTC | Δ | Événement |
|---|---|---|
| 10:54:09 | 0 s | `reboot` envoyé à pve1 |
| 10:54:25 | +16 s | **Les deux CT sont déjà réaffectés** (201→pve3, 203→pve2), avant même la chute du nœud |
| 10:54:43 | +34 s | pve1 tombe — quorum 2/3, Ceph `HEALTH_WARN` (dégradé, normal) |
| 10:57:28 | +3 min 19 s | pve1 répond au ping — **absence totale : 2 min 45 s** |
| 10:57:33 | +3 min 24 s | Quorum 3/3 |
| 10:57:36→58 | +3 min 27 s | La politique `migrate` **ramène automatiquement les deux CT sur pve1** |
| 10:58:10 | +4 min 01 s | Ceph `HEALTH_OK` (37 s après le retour du quorum) |

| Mesure | Valeur |
|---|---|
| Coupure `auth` à l'évacuation (les 2 CT bougent ensemble) | **~32 s** |
| Coupure `pacs-secours` à l'évacuation | ≤ ~26 s |
| Coupure `auth` au **retour automatique** | **~22 s** |
| Coupure `pacs-secours` au retour | ≤ ~20 s |
| Production pendant l'absence du nœud (2 min 45 s) | **aucune coupure** hors fenêtres de migration |

Trois choses apprises :

1. **L'évacuation planifiée fonctionne et elle est rapide** : 16 s entre
   l'ordre de reboot et la réaffectation des services — le nœud attend que
   ses ressources soient parties pour s'éteindre.
2. **La politique `migrate` ramène les services à leur nœud d'origine dès
   son retour** — donc une maintenance planifiée provoque **deux** fenêtres
   de coupure par CT (aller et retour), pas une. À intégrer dans toute
   annonce de maintenance.
3. Les coupures se **cumulent en cascade** : proxy-tim porte le chemin réseau
   de keycloak, donc quand les deux bougent, `auth` cumule les deux restarts
   (~32 s contre ~14 s pour un CT seul, test 4).

Au passage, confirmation du comportement connu : l'adresse temporaire
`10.40.0.2` de pve1 (VLAN 400) a disparu au reboot et a été reposée à la main
([06 §7](06-reste-a-faire.md#7-divers)).

> ⚠️ **Queue d'instabilité observée après le retour** : pendant ~4 min
> (10:58 → 11:02 UTC), des timeouts **intermittents** sur le chemin public
> vers la VIP `.122` (4 échecs isolés relevés, dont 1 sur 20 sur une sonde à
> 3 s) — les requêtes en échec ne figurent dans **aucun** journal nginx :
> elles mouraient avant le conteneur. Le chemin VPN, lui, n'a jamais bronché,
> et le flux d'alimentation PACS des sites a été servi en `200` en pleine
> fenêtre. Résorbé seul, re-testé propre sur trois chemins pendant 90 s.
> Cause non prouvée ; hypothèse : amortissement des déplacements de MAC côté
> vRack après **trois migrations du proxy en cinq minutes** (aller, évacuation,
> retour) — un enchaînement qu'aucun test précédent ne produisait.
> **Leçon** : après déplacement d'un CT porté par une VIP publique, prévoir
> quelques minutes de flottement possible du chemin public et re-sonder
> avant de conclure — une sonde « verte » via le VPN ne prouve rien pour le
> chemin public ([piège n° 30](07-pieges.md#30-le-fichier-hosts-windows-fausse-tout-diagnostic-dns-sous-wsl2)
> version réseau : les deux chemins n'ont rien en commun).

## Test 6 — Triple coupure matérielle, un nœud après l'autre (interface OVH)

Réalisé le **27 août 2026**, **en production**, coupures lancées par
l'utilisateur depuis l'espace client OVH (reset matériel — pas d'arrêt
propre, donc pas d'évacuation : c'est le **fencing** qui travaille, comme au
test 3). Sondes : 6 services HTTPS toutes les 3 s + état du cluster toutes
les 10 s, depuis le poste d'admin (sous VPN — détail qui compte, voir plus
bas). Règle appliquée : jamais deux nœuds coupés à la fois, reprise de Ceph
entre chaque phase.

### Phase 1 — pve1 (portait proxy-tim et keycloak)

| Heure UTC | Événement |
|---|---|
| 11:15:09 | pve1 tombe — quorum 2/3, Ceph `HEALTH_WARN` |
| ≤11:17:37 | Fencing + récupération : **ct:201→pve3, ct:203→pve2** |
| 11:17:52 | pve1 de retour (**absence 2 min 43 s**) ; `pacs-secours` répond à nouveau — **coupure 2 min 43 s** |
| 11:18:51 | `auth` répond (JVM Keycloak) — **coupure 3 min 23 s** |

### Phase 2 — pve2 (portait PBS, headscale, et keycloak récupéré en phase 1)

| Heure UTC | Événement |
|---|---|
| 11:23:11 | pve2 tombe ; au passage `pacs-secours` bafouille **31 s** (pause de peering Ceph probable — le CT du proxy, sur pve3, a son disque sur Ceph) |
| ≤11:25:49 | Fencing + récupération : **ct:202→pve1, ct:203→pve1, vm:102→pve1** |
| 11:25:52 | pve2 de retour (**absence 2 min 41 s**) |
| 11:26:57 | `auth` répond — **coupure 3 min 46 s** (keycloak a déménagé deux fois en deux phases) |
| 11:27:01 | headscale répond — **coupure 3 min 50 s** |

### Phase 3 — pve3 (portait OPNsense — le pare-feu de tout)

| Heure UTC | Événement |
|---|---|
| 11:30:17 | pve3 tombe. **Depuis le poste sous VPN, TOUT devient invisible** — y compris pve1 et pve2 pourtant vivants |
| ≤11:34:20 | Fencing + récupération : **vm:100→pve2, ct:201→pve2** |
| 11:34:23 | pve3 de retour, VPN/DNS revenus, headscale répond — **coupure ~4 min 06 s** |
| 11:35:08 | `auth` et `pacs-secours` répondent — **coupure 4 min 51 s** |

> ⚠️ **Le piège de diagnostic de la phase 3** : le poste d'admin utilise le
> DNS du VPN (`10.40.0.1` = OPNsense). OPNsense mort, **plus aucun nom ne se
> résout** : les sondes ont vu pve1 et pve2 « morts » alors qu'ils étaient
> parfaitement vivants (l'enregistreur d'état, qui joint les nœuds par leur
> nom, a été aveugle 3 min 20 s pour la même raison). En cas de panne réelle,
> **diagnostiquer par IP publiques directes**, jamais par les noms depuis le
> VPN — sous peine de conclure à une panne totale qui n'existe pas.

### Ce que le test prouve

- **Chaque nœud peut mourir brutalement** : les cinq machines ont toutes été
  récupérées automatiquement, quorum et Ceph revenus sains après chaque
  phase, **zéro perte de données** et flux PACS reparti seul à chaque fois.
- **Ordre de grandeur à retenir : 3 à 5 min d'indisponibilité** par service
  porté par le nœud coupé (fencing ~2 min + redémarrage du service — la JVM
  Keycloak ajoute ~40 s ; OPNsense est le pire cas car il ajoute sa propre
  coupure à celle des autres).
- **Une récupération est définitive** : contrairement au test 5 (politique
  `migrate` sur arrêt propre), les services ne reviennent pas sur leur nœud
  d'origine. Après le test : OPNsense et proxy-tim sur **pve2**, headscale,
  keycloak et PBS sur **pve1**, **pve3 vide**. C'est le comportement
  documenté (« le service reste où la bascule l'a posé »).
- Mêmes queues d'instabilité brèves (~10-35 s) que le test 5 dans les minutes
  suivant chaque retour.
- `10.40.0.2` de pve1 à nouveau perdue puis reposée ([06 §7](06-reste-a-faire.md#7-divers)).

## Synthèse

| Scénario | Indisponibilité | Perte de données |
|---|---|---|
| Migration planifiée | 1 s | aucune |
| Migration planifiée d'un CT | ~14 s | aucune |
| Reboot planifié d'un nœud portant 2 CT | ~32 s (évacuation) **puis** ~22 s (retour auto) | aucune |
| Panne d'un nœud | ~2 min 15 s | **aucune** (RPO = 0) |
| Coupure matérielle d'un nœud, services réels (test 6) | **2 min 43 s à 4 min 51 s** selon le service porté (pire cas : OPNsense) | aucune |
| Panne d'un disque | 0 s | aucune |
| Panne de deux nœuds | **totale** | aucune, mais quorum perdu |

La dernière ligne est la limite structurelle d'un cluster à 3 nœuds : deux pertes
simultanées font tomber le quorum Corosync **et** violent `min_size=2`. Le
stockage se met en lecture seule et les VM gèlent. Seul un 4ᵉ nœud, ou un QDevice
sur un site tiers, changerait cela.

## Rejouer les tests

Après toute modification structurelle (mise à jour majeure, remplacement de
nœud), il vaut mieux revalider. Créer une VM jetable en HA, puis :

```bash
# depuis un nœud tiers, mesurer en continu
ping -i 0.2 -w 600 <ip-vm> > /tmp/ping.txt &

# isoler durablement le nœud cible
ssh pveX 'systemctl mask corosync; systemctl stop corosync'

# suivre la bascule
watch -n5 'ha-manager status | grep -E "master|vm:"'

# remettre en service
ssh pveX 'systemctl unmask corosync; systemctl start corosync; systemctl start pve-ha-lrm'
```

Deux précautions apprises à nos dépens :

- **Détacher la mesure du terminal** : `systemd-run --unit=... --property=StandardOutput=file:...`
  plutôt qu'un `nohup ... &` à travers SSH, qui meurt avec la session.
- **Ne pas surveiller depuis une session SSH ouverte vers le nœud qu'on tue** :
  la connexion reste suspendue sans jamais expirer (la machine meurt sans fermer
  le TCP). Toujours superviser depuis un nœud tiers, avec `timeout`.
