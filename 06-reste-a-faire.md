# Reste à faire

Par ordre décroissant d'importance.

---

## 1. Sauvegardes — ✅ TRAITÉ le 13/08/2026

Proxmox Backup Server 4.2.5 en VM 102, datastore sur le NAS-HA `zpool-130899`
(Roubaix), sauvegarde quotidienne de tout le cluster à 02:00, rétention
7 jours / 4 semaines / 6 mois, restauration testée et mesurée.

Tout le détail dans [10-sauvegardes.md](10-sauvegardes.md).

> **Le plan esquissé ici était faux sur un point de fond** : le NAS-HA **ne peut
> pas rejoindre le vRack**, et son ACL attend les **IP publiques** des nœuds, pas
> leurs IP vRack. Le VLAN 300 avait été réservé pour rien.
> Voir [07-pieges.md](07-pieges.md#24-le-nas-ha-nest-pas-raccordable-au-vrack).

> **Corrigé le 14/08/2026** : la tâche quotidienne échouait chaque nuit sur la
> VM 102, PBS ne pouvant pas se sauvegarder dans son propre datastore. La 102 en
> est désormais exclue et reste couverte par le job hebdomadaire vers `nas-vm`,
> vérifié le jour même.
> Voir [07-pieges.md](07-pieges.md#28-pbs-ne-peut-pas-se-sauvegarder-dans-son-propre-datastore).

Ce qui reste ouvert sur le sujet :

- **chiffrement client PBS** non activé — arbitrage entre confidentialité et
  risque de perte de clé, à reprendre avec séquestre hors cluster ;
- **une seule copie** des sauvegardes, atténuée par les snapshots ZFS d'OVH et
  l'option de réplication distante ;
- `backup-opnsense.timer` ne tourne que sur **pve1**.

---

## 2. Bascule DNS vers `proxy-tim` — faite le 26/08/2026, reste le nettoyage

**Bascule faite le 26/08/2026** : `pacs-secours.teleimagerie.net`,
`syngo.teleimagerie.net` et `syngo.isoteam.mn` (créé à cette occasion) pointent
sur `57.130.34.122`, TTL 60. Vérifiée de bout en bout — détail dans
[09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026).

Reste à faire :

- **Décommissionner l'ancien VPS** `51.75.203.20` — **drainage vérifié le
  27/08/2026** (accès `ssh ubuntu@51.75.203.20`, sudo) : sur les ~23 h suivant
  la bascule, ~1 200 requêtes reçues, **zéro** sur les chemins légitimes
  (`/xaconsolepacs`, `/PACS_TIM_BCK`), zéro connexion TLS sur le relais 443 —
  uniquement des scanners (dont du bruit RDP :3389 en `502`). Plus aucun nom
  des six zones ne pointe sur cette IP. **Prêt à résilier** (espace client
  OVH) ; par prudence, prendre un snapshot avant. Rien à récupérer dessus :
  config nginx et certificats déjà migrés sur le CT 201 le 12/08.
- **Remonter le TTL** des trois noms (60 → 3600) une fois la stabilité
  confirmée.
- **`syngo-via.*` restent en direct sur TSplus** (`37.61.243.246`) : les faire
  passer par le relais TLS du proxy est une décision séparée, non prise —
  le relais ACME du port 80 vers TSplus est prêt depuis le 24/08 si elle
  se prend un jour.

---

## 3. Abonnement Proxmox

Le cluster fonctionne sur `pve-no-subscription` : bandeau à chaque connexion, et
surtout paquets **moins validés**.

Proxmox VE est libre (AGPLv3) et sans limitation fonctionnelle. L'abonnement
achète l'accès au dépôt entreprise et, à partir de Basic, du support éditeur.
Tarifs au socket et par an ; les 3 machines sont **mono-socket**.

| Niveau | € HT/socket/an | Cluster (×3) | Contenu |
|---|---|---|---|
| Community | 120 | **360 €** | dépôt entreprise, pas de ticket |
| Basic | 370 | 1 110 € | + 3 tickets/an, réponse J+1 |
| Standard | 550 | 1 650 € | + 10 tickets/an, réponse 4 h ouvrées |
| Premium | 1 100 | 3 300 € | + tickets illimités, réponse 2 h |

Tous les nœuds d'un cluster doivent porter le même niveau.

**Recommandation** : la Community à 360 €/an se justifie ici — non pour le
bandeau, mais pour les paquets testés. Sur un cluster Ceph à 3 nœuds sans
auto-guérison, une mise à jour qui se passe mal coûte cher.

Bascule après souscription :

```bash
# sur chaque nœud
pvesubscription set <clé>
# activer pve-enterprise.sources, désactiver pve-no-subscription
apt update && apt full-upgrade
```

---

## 4. Supervision

Aucun monitoring. Le cluster expose des métriques exploitables :

- `Datacenter → Metric Server` : InfluxDB ou Graphite en natif
- Le module `prometheus` de Ceph MGR : `ceph mgr module enable prometheus`

À surveiller en priorité : `%USE` des OSD (seuil `nearfull` à 85 %), état du
quorum Corosync, `HEALTH_*` de Ceph, RAM par nœud face au plafond de ~100 Go
cumulés, et expiration des certificats. Depuis le 15/08/2026, headscale expose
aussi ses métriques Prometheus sur `127.0.0.1:9090` du CT 202
([11-headscale.md](11-headscale.md)) — nœuds en ligne et santé du plan de
contrôle des passerelles DICOM.

Les notifications mail fonctionnent déjà (fencing, tâches en échec) vers
`mcapon@teleimagerie.net`.

---

## 5. IP publiques pour les VM

Les VM sont aujourd'hui sur le réseau privé `10.30.0.0/24` (vmbr1), sans accès
entrant ni sortant.

Deux voies :

- **IP failover OVH** avec MAC virtuelles, routées vers les VM par `vmbr0` —
  chaque IP est facturée, la MAC doit être déclarée dans l'espace client
- **NAT sortant** via un pare-feu/routeur virtuel sur `vmbr1`, plus économique
  si seul l'accès sortant est nécessaire

À arbitrer selon l'usage réel des VM à venir.

---

## 6. Swap non redondé

`p4` est une partition de swap **indépendante sur chaque disque**, hors RAID —
défaut du template OVH. La perte d'un NVMe fait disparaître la moitié du swap et
peut déclencher des OOM sur les processus concernés.

Avec 64 Go de RAM et une réservation Ceph maîtrisée, le risque reste faible.
Deux corrections possibles si l'on veut le supprimer :

- désactiver totalement le swap (`swapoff` + retrait de `/etc/fstab`) et régler
  `vm.swappiness=0` — l'approche recommandée sur les hyperviseurs Ceph
- reconstruire les deux partitions en RAID1 `mdadm`

---

## 7. Divers

- **Un 4ᵉ nœud** rendrait l'auto-guérison Ceph possible et supprimerait la
  dégradation durable après panne. À considérer si la charge grandit.
- ~~**CephFS** pour partager ISO et templates~~ — sans objet depuis le
  13/08/2026 : le stockage `nas-vm` porte `iso` et `vztmpl` et les rend communs
  aux trois nœuds.
- **Le matériel livré ne correspond pas au devis demandé** : la demande du
  05/08/2026 portait sur 128 Go de RAM et 2 × 1,92 To de NVMe supplémentaires par
  serveur ; les machines ont 64 Go et 2 disques. À vérifier auprès d'OVH — c'est
  la voie la plus directe pour agrandir *Ceph*, là où le NAS n'apporte qu'un
  stockage lent.
- **Faire le ménage dans les tokens OVH** : deux clés antérieures ont été révoquées
  le 11/08/2026 et n'ont plus d'usage. **Deux applications doivent subsister** :
  `proxmox` (AK `0357cf99f1ed0548`), qui porte le renouvellement TLS, et
  `Proxmox Nas-HA` (AK `e13e89cf414da916`), qui pilote les partitions et l'ACL du
  NAS depuis le 13/08/2026. Supprimer l'une ou l'autre casse silencieusement une
  fonction : ne pas les confondre.
- **Rejouer les tests HA** après toute mise à jour majeure
  ([05-tests-ha.md](05-tests-ha.md#rejouer-les-tests)).
- ~~**`proxy-tim` (CT 201) n'est pas une ressource HA**~~ — **réglé le
  15/08/2026** : `ha-manager add ct:201` exécuté, bascule testée vers pve3
  (~14 s d'interruption). Voir [09-proxy-tim.md](09-proxy-tim.md) et
  [05-tests-ha.md](05-tests-ha.md#test-4--bascule-planifiée-dun-conteneur).

---

## 8. VPN site-à-site — points ouverts

Le tunnel vers le pfSense TELLIS ([13-tellis.md](13-tellis.md)) est opérationnel depuis le 14/08/2026
([08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822)). Ce qui n'a pas été
fait ou pas été prouvé :

- ~~**Le sens TELLIS → nos VM n'a jamais été testé.**~~ — **réglé le
  25/08/2026**, en deux temps. Premier essai depuis `prod01` (route retour
  `via .59` posée) : 100 % de perte vers `10.40.0.40`, `10.40.0.10` et même
  `10.40.0.1`, capture vide sur l'interface du CT 201 — cause : **la patte
  `.59` du pfSense n'avait aucune règle `pass`** (deny par défaut ; le test du
  14/08 « le pfSense joint `10.40.0.1` » partait du pfSense lui-même). Après
  ajout d'une règle `pass` côté pfSense : ping prod01 → pacs03 en 17–23 ms
  TTL 126, et session TCP complète (`curl http://10.40.0.40/` → 404 de
  référence) — MSS/MTU 1420 compris. Les règles posées (interface `OPT1_TIM`,
  alias `SRV_TIM_WFMCORE` et `DC_OVH_TIM`) sont transcrites dans
  [13-tellis.md](13-tellis.md#règles-posées-sur-opt1_tim-le-25082026-sens-tellis--dc-ovh).
  Restes de ce chantier : **(a)** ⚠️ relever le contenu des deux alias ;
  **(b)** décider de la persistance des routes de test (`10.40.0.0/24 via
  .59` sur prod01 et les `/32` ActiveStore sur pacs03 — toutes volatiles, un
  reboot les efface), en retenant que **les deux côtés vont par paire** : si
  la `/32` de pacs03 disparaît (reboot) alors que prod01 garde sa route, les
  réponses de pacs03 partiront dans le tunnel direct avec la source
  `10.40.0.40` et le pfSense les jettera (cryptokey routing) — poser ou
  retirer **les deux ensemble** ; **(c)** à terme, restreindre les règles « tout
  protocole / tout port » aux hôtes et ports réellement nécessaires.
- **La segmentation n'a pas été éprouvée depuis TELLIS.** Les règles
  bloquant Corosync, Ceph et `10.30.0.0/24` sont bien chargées dans `pf`, ce qui
  a été vérifié — mais une règle chargée n'est pas une règle prouvée.
- **Le comportement du tunnel pendant une bascule HA de la VM 100 n'est pas
  mesuré.** Le keepalive de 25 s devrait le rétablir en moins d'une minute après
  les ~2 min de relance ; c'est une déduction, pas un chiffre.
- **Les routes ne sont posées que sur `192.168.101.52`.** Les autres serveurs à
  joindre doivent recevoir le même traitement, ou le pfSense doit masquer notre
  trafic derrière une de ses adresses locales.
- **À terme : supprimer le tunnel direct « DC-TELLIS-PARTENAIRES » (`tun_wg1`)
  entre pacs03 et le pfSense TELLIS** ([15-pacs-secours.md](15-pacs-secours.md)),
  une fois les flux TELLIS↔pacs03 basculés sur `wg2`/vRack. Décision du
  25/08/2026 : **pour le moment il doit perdurer** — c'est lui qui route
  `192.168.101.48/28` et `.96/28` vers le serveur, et aucune route équivalente
  n'a été posée via OPNsense (les doubler créerait un conflit). Premier jalon
  mesuré le 25/08/2026 : pacs03 joint le pfSense (`172.33.0.1`) par wg2 en
  15 ms (route `/32` de test temporaire). Restent à prouver : un hôte TELLIS
  de bout en bout dans les deux sens, et la tenue du MTU 1420 de wg2 pour un
  flux de réplication.

### ⚠️ Deux clés privées ont été exposées

Le 13 et le 14/08/2026, lors de l'extraction des configurations, deux clés
privées WireGuard ont transité en clair dans un historique de terminal :

| Clé | Portée |
|---|---|
| instance `wg-nomades` (OPNsense) | notre VPN nomades |
| tunnel `tun_wg0` (pfSense TELLIS) | **le VPN nomades du DC TELLIS, en production** |

Les régénérer impose de redistribuer les profils clients des deux côtés — d'où
le report. Tant que ce n'est pas fait, quiconque a eu accès à cet historique peut
usurper l'un ou l'autre serveur VPN. La seconde n'est pas sous notre contrôle :
c'est au prestataire TELLIS d'arbitrer, et il doit en être informé.

> **Voie de sortie proposée depuis le 15/08/2026** : le tailnet headscale
> ([11-headscale.md](11-headscale.md)) sait aussi faire le VPN nomades — enrôler
> les postes itinérants dans le tailnet (user `admin`), puis **désactiver `wg0`
> et sa clé compromise**. Le pair `nomade-01` n'a plus été vu depuis le
> 13/08/2026 : la migration ne dérangerait personne. Réglerait la première ligne
> du tableau ci-dessus sans redistribution de profils WireGuard.

---

## 9. DC TELLIS — collecte et vérification de l'inventaire

Le DC TELLIS a désormais sa fiche de référence ([13-tellis.md](13-tellis.md)),
mais l'inventaire y est **majoritairement déclaratif** : une seule adresse a été
contrôlée par le tunnel. La liste détaillée de ce qu'il reste à collecter est
dans [13-tellis.md](13-tellis.md#checklist-de-collecte) — ne pas la dupliquer
ici. Les trois points saillants :

- **l'export `config.xml` des deux pfSense** (`192.168.101.59` et `.62`) —
  règles, NAT, WireGuard ; à conserver hors dépôt, il contient des clés privées ;
- **le contenu de la VM `prod01`** (`192.168.101.54`) — personne ne sait
  précisément ce qui y tourne ;
- **informer le prestataire de l'exposition de la clé `tun_wg0`** et suivre sa
  rotation (voir le § 8 ci-dessus).
