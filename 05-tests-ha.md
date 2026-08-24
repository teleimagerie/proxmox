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
racine n'est pas servie — vérifié identique avant la bascule).

## Synthèse

| Scénario | Indisponibilité | Perte de données |
|---|---|---|
| Migration planifiée | 1 s | aucune |
| Migration planifiée d'un CT | ~14 s | aucune |
| Panne d'un nœud | ~2 min 15 s | **aucune** (RPO = 0) |
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
