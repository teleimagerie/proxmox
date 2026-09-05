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

## 2. Bascule DNS vers `proxy-tim` — ✅ TRAITÉ le 29/08/2026

**Bascule faite le 26/08/2026** : `pacs-secours.teleimagerie.net`,
`syngo.teleimagerie.net` et `syngo.isoteam.mn` (créé à cette occasion) pointent
sur `57.130.34.122`. Vérifiée de bout en bout — détail dans
[09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026).

Nettoyage terminé :

- **ancien VPS `51.75.203.20` résilié le 29/08/2026** (espace client OVH).
  Auparavant : drainage contrôlé les 27 et 29/08 (accès `ssh ubuntu@`, sudo) —
  du 26 au 29/08, ~6 800 requêtes reçues, **zéro** sur les chemins légitimes
  (`/xaconsolepacs`, `/PACS_TIM_BCK`), zéro connexion TLS sur le relais 443,
  uniquement des scanners (dont du bruit RDP :3389 en `502`) — puis **éteint
  le 29/08** (`systemctl poweroff`, ping muet, production intacte via le
  proxy). Rien n'avait à être récupéré : config nginx et certificats migrés
  sur le CT 201 le 12/08. L'accès `ssh ubuntu@51.75.203.20` n'existe plus.
- **TTL des trois noms remonté** 60 → 3600 le 29/08/2026, vérifié sur les deux
  paires d'autoritaires ; exports de zone rafraîchis dans `configs/`.

Seul point encore ouvert : **`syngo-via.*` restent en direct sur TSplus**
(`37.61.243.246`) — les faire passer par le relais TLS du proxy est une
décision séparée, non prise ; le relais ACME du port 80 vers TSplus est prêt
depuis le 24/08 si elle se prend un jour.

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

## 4. Supervision — ✅ TRAITÉ le 29/08/2026 (reste la sonde externe)

**Le Zabbix d'entreprise tourne dans le cluster** (CT 204, migré le 29/08 —
[17-zabbix.md](17-zabbix.md)) **et supervise le cluster lui-même depuis le
même jour** : quorum, nœuds, Ceph (`HEALTH_*`, OSD), stockages avec seuil
nearfull 85 %, les 7 VM/CT (vue hyperviseur **et** agents internes, OPNsense
compris), certificats TLS — tableau de bord « Cluster PVE », alertes
High/Disaster par mail vers support@ + mcapon@, chaîne testée en réel.
Détail, seuils et pièges :
[17-zabbix.md §Supervision du cluster](17-zabbix.md#supervision-du-cluster--depuis-le-29082026).

> La contrainte « depuis le VLAN 400 les hyperviseurs sont inaccessibles »
> annoncée ici s'est révélée contournable proprement : **l'API PVE répond par
> le chemin public existant** avec un token lecture seule — la 2ᵉ carte
> VLAN 300 (patron PBS) n'a pas été nécessaire.

Restent ouverts :

1. **une sonde externe** sur `https://zabbix.teleimagerie.net/` — l'incident du
   28/08 (32 h de supervision morte sans alerte) montre que le monitoring ne
   peut pas être son propre témoin ;
2. options non retenues pour l'instant : templates applicatifs dans les
   invités (nginx du proxy, PostgreSQL de Keycloak, Docker d'odoo, datastore
   PBS), SNMP OPNsense, Metric Server/InfluxDB natif, Prometheus headscale
   (`127.0.0.1:9090` du CT 202).

Les notifications mail Proxmox ne partent plus qu'en cas de problème depuis le
30/08/2026 : matchers `erreurs-mailjet` (warning/error/unknown → Mailjet) sur
PVE et PBS, builtin `default-matcher` désactivé — plus aucun mail de succès.
Zabbix est le canal principal (échec **et absence** de sauvegarde,
[17-zabbix.md](17-zabbix.md#supervision-des-sauvegardes--depuis-le-30082026)) ;
le mail direct n'est que le filet si Zabbix tombe.

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

- ✅ **pacs03 patché, redémarré et allégé le 30/08/2026** (précédent
  correctif : 20/02/2024) — swap porté de 2 à 16 Go, **Veeam désinstallé**
  (jamais configuré ; ports 111/2049/6160/9392 vérifiés fermés). Restent au
  plan d'action : scan de surface, pare-feu, canal de mise à jour à revérifier
  dans un mois — et noter que **hors cluster, hors PBS : sa seule sauvegarde
  est la tâche Oracle** — [15-pacs-secours.md](15-pacs-secours.md#reste-à-faire).
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
- ~~**L'adresse `10.40.0.2` de pve1 ne survit pas aux redémarrages**~~ —
  **tranché et fait le 27/08/2026** (après trois pertes le même jour, tests
  5-6) : **pérennisée** (stanza `vmbr1.400` dans les interfaces de pve1) et
  **durcie** (règle `cluster.fw` : `DROP` de tout `10.40.0.0/24` vers les
  hyperviseurs — patte sortante uniquement, vérifié dans les deux sens).
  Hook des certificats rejoué de bout en bout après coup.
  [08-opnsense.md](08-opnsense.md#accès-dadministration).
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
  Restes de ce chantier : **(a)** ⚠️ relever le contenu de l'alias
  `DC_OVH_TIM` (`SRV_TIM_WFMCORE` identifié le 29/08/2026 : c'est la Vue PACS
  `TIMWFMCORE` `192.168.101.52` — la règle prépare la réplication PACS
  principal → PACS de secours par `wg2`) ;
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
  trafic derrière une de ses adresses locales. Nuance du 04/09/2026 : seuls les
  serveurs dont la passerelle est le second pfSense (`.62`) en ont besoin —
  VENUS (`.254`) et Syngo (`.110`) répondent déjà au pfSense principal ; et le
  poste d'admin joint TELLIS par le `tun_wg0` du pfSense (`172.31.0.3`), pas
  par `wg2` ([13-tellis.md](13-tellis.md#tun_wg0--vpn-nomades-du-site)).
  **Tranché le 05/09/2026** : `10.40.0.0/24` ↔ `192.168.111.x` fonctionne dans
  les deux sens — le CT 204 joint les trois VENUS, et leurs agents Zabbix
  sortent vers `10.40.0.60:10051` ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026)).
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

| Clé | Portée | État |
|---|---|---|
| ~~instance `wg-nomades` (OPNsense)~~ | notre VPN nomades | **réglé le 31/08/2026** : paire régénérée à l'occasion de l'ajout du pair `brtrnd` ([08-opnsense.md](08-opnsense.md#wireguard)) — nouvelle clé privée fabriquée par script sur OPNsense, jamais affichée dans un terminal |
| tunnel `tun_wg0` (pfSense TELLIS) | **le VPN nomades du DC TELLIS, en production** | **ouvert** — pas sous notre contrôle : c'est au prestataire TELLIS d'arbitrer, et il doit en être informé |

Tant que la clé TELLIS n'est pas régénérée, quiconque a eu accès à cet
historique peut usurper le serveur VPN nomades du DC TELLIS.

> L'encadré du 15/08/2026 proposait de migrer les nomades vers le tailnet
> headscale et de **désactiver `wg0`**. Option écartée le 31/08/2026 : le
> tailnet ne route pas le VLAN 400 (pas de subnet router —
> [11-headscale.md](11-headscale.md)), or c'est précisément l'accès dont les
> nomades ont besoin. `wg0` est conservé, sur une paire de clés saine.

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

### ⛔ La base de production du RIS VENUS n'est pas sauvegardée (04/09/2026)

Constaté à l'inventaire des trois serveurs VENUS
([13-tellis.md](13-tellis.md#tim-venus3-db-65--la-base-partagée-inventorié-le-04092026)) :
la base **`isotim` (≈ 2,1 Go)** de `TIM-VENUS3-DB` (`192.168.111.65`), qu'appellent
en permanence les deux serveurs applicatifs, **n'a aucune sauvegarde**. Le volume
`E:` nommé « BACKUP BDD », dimensionné à 750 Go, est **vide (0 fichier)** ; il
n'existe **aucune tâche planifiée** de sauvegarde ; les seuls exports retrouvés
sont manuels et anciens (`isotim_backup.sql` de 883 Mo du **10/12/2025**, dans le
dossier `Downloads` d'un compte d'administration). Les données sont de surcroît
dans `C:\Program Files\MariaDB 11.8\data`, le chemin d'installation par défaut,
alors que 750 Go dédiés (`D:`) sont vides.

À porter **à Softway Medical** (c'est son applicatif, `mariadb-dump` planifié vers
`E:` au minimum) **et au prestataire TELLIS** : aucune sauvegarde n'étant visible
*dans* les VM, la seule protection possible est celle de l'hyperviseur Proxmox du
site — **personne ne nous a confirmé qu'elle existe**. Tant que ce point n'est pas
levé, une perte de la VM fait perdre le RIS. Deux points voisins, moins graves
mais du même inventaire : `D:` de `TIM-VENUS1-AP` n'a plus que **4,8 Go libres**
sur 200, et les trois serveurs sont **sans correctif Windows** (avril 2023 pour
deux d'entre eux).

Depuis le 05/09/2026 les trois sont **supervisés** ([17-zabbix.md](17-zabbix.md#serveurs-ris-venus-de-tellis--agent-actif-05092026)) :
le volume `D:` est sous déclencheur High qui part en mail, et la mémoire de
`TIM-VENUS3-DB` (8 Go) est en alerte permanente. **L'absence de sauvegarde,
elle, reste invisible de Zabbix** — il n'y a rien à mesurer tant qu'aucune
sauvegarde n'existe. Le jour où elle sera en place, surveiller l'âge du dernier
fichier de `E:` fermera la boucle.

---

## 10. Authentification centralisée — suites du déploiement du 27/08/2026

Keycloak est en production ([16-keycloak.md](16-keycloak.md)) : realm `tim`,
Proxmox VE, PBS et headscale raccordés en OIDC. Ce qui reste :

- ~~**Distribuer les mots de passe temporaires et ranger les secrets**~~ —
  soldé le 27/08/2026 : `matt` et `brtrnd` connectés (mots de passe changés,
  TOTP enrôlés), secrets recopiés dans le gestionnaire et
  `/etc/pve/priv/keycloak/credentials` **détruit des serveurs**
  ([04-securite.md](04-securite.md#secrets--où-ils-vivent)).
- **Éprouver headscale par une connexion OIDC réelle** (PVE et PBS le sont
  depuis le 27/08/2026, en SSO sur une même session) : un
  `tailscale up --login-server https://headscale.teleimagerie.net` de test.
- ~~**Décider du rôle de `brtrnd@keycloak`**~~ — tranché le 27/08/2026 :
  **Administrator sur `/`** côté PVE et **Admin sur `/`** côté PBS, comme
  `matt@keycloak` (vérifié dans les deux ACL le jour même).
- ~~**Brokering Google Workspace**~~ — **en place et testé en réel le
  27/08/2026** (client OAuth interne au Workspace, `hd` vérifié, PKCE,
  liaison avec confirmation ; compte Workspace technique passé puis supprimé —
  [16-keycloak.md](16-keycloak.md#brokering-google-workspace--en-place-depuis-le-27082026)).
  Microsoft 365 (`isoteam.mn`) pourra suivre par la même mécanique.
- ~~**SMTP Mailjet — en attente de la clé API**~~ — **en place le
  30/08/2026** : relais `in-v3.mailjet.com:587` sur le realm `tim`,
  expéditeur `auth@teleimagerie.net`, « mot de passe oublié » activé,
  e-mail de test réellement expédié (`testSMTPConnection` → 204) —
  [16-keycloak.md](16-keycloak.md#e-mail-sortant--smtp-mailjet-en-place-depuis-le-30082026).
- **MyTIM** (application interne de gestion) : ~~documenter hébergement et
  technologie~~ (fait le 29/08/2026 : `app`/`gestion` → `51.210.24.59`,
  Symfony 7.4/FrankenPHP chez OVH, deux tenants). ~~Intégration OIDC côté
  appli~~ (fait le 29/08/2026, branche `feature/sso` du dépôt gestion, mergée).
  ~~Clients `mytim` + `mytim-staging` du realm `tim`~~ (créés le 30/08/2026).
  ~~Prod TIM : audit du client `mytim`, secret vaulté dans l'Ansible du dépôt
  gestion, déploiement prod, mode `local+sso`~~ (**fait le 01/09/2026**,
  secret déployé vérifié par hash —
  [16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026)).
  Reste : **validation pilotes** puis communication à tout l'interne TIM
  (phase 3 du runbook `docs/technique/sso-keycloak.md` du dépôt gestion) ;
  **realm `isoteam`** (copie de `tim`) + ses 2 clients + redirect URI
  `…/realms/isoteam/broker/google/endpoint` dans la console Google Cloud, pour
  le tenant `app.isoteam.mn` ; secret de `mytim-staging` à vaulter
  (`group_vars/default/secrets/`) ; plus tard `sso-default`, médecins,
  back-channel logout.
- **Odoo** : ~~raccordement SSO~~ **fait le 31/08/2026** (module OCA
  `auth_oidc`, client `odoo`, flux code + PKCE S256, aucun provisioning —
  [18-odoo.md](18-odoo.md#sso-keycloak)). Reste : **valider la connexion
  navigateur réelle** (pilote `mcapon@teleimagerie.net`, seul compte
  rapproché), puis généraliser aux internes actifs. Deux points relevés au
  passage : le provider `Odoo.com Accounts` est resté actif (second bouton
  inutile sur la page de login) et `web.base.url.freeze` n'est pas positionné.
- **Applications d'entreprise** (Zabbix en SAML/LDAP, CRM, e-learning,
  bastion) : collecter les accès, tableau des candidats dans
  [16-keycloak.md](16-keycloak.md#candidats-au-raccordement--étude-du-27082026).
- **Applications médicales** (Syngo Via, Vue PACS, RIS VENUS, TSplus) : cible
  à terme, à instruire éditeur par éditeur via la
  [checklist TELLIS](13-tellis.md#checklist-de-collecte).
- **Durcissement optionnel** : restreindre `/admin/` du vhost aux IP
  d'administration ; tester une restauration de la base depuis un dump
  `kc-pgdump` (le vzdump du CT, lui, suit la procédure standard de
  [10-sauvegardes.md](10-sauvegardes.md)).
- **Supervision de l'IdP** : voir [§ 4](#4-supervision---traité-le-29082026-reste-la-sonde-externe).

---

## 11. Migration Odoo (VPS → VM 101) — ✅ TRAITÉ, soldé le 30/08/2026

**En production sur le cluster depuis le 29/08/2026 16:18 UTC** — préparation,
répétition générale et bascule le même jour, coupure ~4 min + ~2 min de
fenêtre TLS, vérifiée de bout en bout (récit chiffré dans
[18-odoo.md](18-odoo.md#bascule-du-29082026--récit-chiffré)). HA `vm:101`
déclarée. Nettoyage restant :

- ✅ vzdump du 30/08 vérifié (backup 02:00 présent, tâches OK) et
  **restauration testée** en VM 299 le 30/08 : Odoo a répondu 200 dans la VM
  restaurée, détruite ensuite. Le cron `auto_backup` échouait en droits sur
  `./backups` (dossier du clone git) — corrigé (`chown` uid 101), sauvegarde
  de preuve produite ;
- ✅ migration à chaud de validation faite le 29/08 au soir (pve1 → pve2, ~1 s) ;
- ✅ deploy key `odoo-vm101` déclarée et testée le 30/08, branche `proxmox`
  fusionnée dans `main` (la VM suit `main`), inventaire Ansible basculé sur
  `10.40.0.70` ;
- ✅ documents joints validés (3 918 fichiers, SHA1 conformes), **VPS
  éteint le 29/08 16:42 UTC puis résilié le 30/08** (drainage de 3 jours
  sauté sur décision utilisateur ; les données MySQL Dolibarr sont parties
  avec lui, sans archive, décision actée), TTL remonté à 3600 et export de
  zone rafraîchi le 30/08 ;
- **relève du mail entrant** : déjà à l'état `draft` sur le VPS (constat
  post-bascule, pas une régression) — à réactiver un jour depuis l'interface.

---

## 12. Fermeture de l'exposition publique du cluster — en cours

**Pourquoi** : `cluster.fw` ouvre encore `8006`, `22`, `3128` et `5900-5999` à
tout Internet. Le journal `pveproxy` montre des scanners qui sondent l'API en
continu (`65.49.1.38/40/47`, `204.76.203.49`…), et le verrouillage de pacs03 le
30/08 a montré ce que devient une surface publique non filtrée. Les protections
en place (clé seule, TOTP, fail2ban) tiennent le bruteforce ; l'objectif est de
**retirer `pveproxy` et `sshd` de la vue d'Internet** — donc de se protéger
d'une CVE d'authentification, que le 2FA ne couvre pas.

### ✅ Étape 1 — chemin privé d'administration (31/08/2026)

Les 3 nœuds ont une patte VLAN 400 (`.2`, `.3`, `.4`) **et** la route retour
`10.90.0.0/24 via 10.40.0.1` qui manquait. Depuis le VPN nomade, SSH et 8006
répondent sur les trois, **certificat valide** grâce aux overrides Unbound
`pveN.infra → 10.40.0.x`. Aucune règle OPNsense n'a été nécessaire. La
supervision Zabbix est passée au chemin privé (exception `10.40.0.60 → 8006`
posée **avant** le DROP du VLAN 400) — ce qui supprime au passage l'épingle à
cheveux publique et le risque de bannissement fail2ban de `57.130.34.122`
([04-securite.md](04-securite.md#accès-dadministration-par-vpn-31082026)).

### ✅ Étape 2 — seconde porte VPN (31/08/2026)

Les 3 nœuds sont enrôlés dans le tailnet (`tag:pve` — `pve1` `100.72.0.6`,
`pve2` `100.72.0.5`, `pve3` `100.72.0.7`) en **`--tun=userspace-networking`** :
routes vérifiées **identiques** avant/après, aucune interface créée, passerelle
OVH `100.64.0.1` intacte. `udp/41641` ouvert dans `cluster.fw` sans restriction
de source, ce qui donne un chemin **direct sur l'IP publique du nœud** —
mesuré : `direct 91.134.84.222:41641`, sans traverser OPNsense
([11-headscale.md](11-headscale.md#les-hyperviseurs--seconde-porte-dadministration-31082026)).

⚠️ **Test d'acceptation restant** : arrêter la VM 100 et vérifier que les 3
nœuds restent joignables par le tailnet. **Non joué le 31/08 à dessein** — il
coupe le réseau de toutes les VM de production (Odoo, pacs-secours, Keycloak,
Zabbix) : à programmer dans une fenêtre de maintenance. Tant qu'il n'est pas
fait, l'indépendance de la seconde porte est **démontrée par construction**
(chemin direct constaté) mais **pas mesurée de bout en bout** : le plan de
contrôle headscale (CT 202) est lui aussi derrière OPNsense.

### ⚠️ Étape 3 — fermeture proprement dite (à faire)

Préalable **bloquant** : ouvrir la console KVM OVH sur **chacun** des 3 nœuds et
**vérifier le mot de passe root** (il est local, non répliqué, donc
potentiellement différent d'un nœud à l'autre — procédure et identifiants dans
[04-securite.md](04-securite.md#console-kvmipmi-ovh--laccès-de-dernier-recours)).

`cluster.fw` étant répliqué par pmxcfs, la fermeture est **atomique et
globale** : il n'y a pas de nœud canari, la progressivité s'obtient **par
port**, avec 24 h de recul entre deux vagues.

| Vague | On ferme | Filet restant | État |
|---|---|---|---|
| V1 | `3128`, `5900:5999` | 8006 et 22 publics | ✅ **31/08/2026** |
| V2 | `8006` | 22 public | ✅ **01/09/2026** |
| V3 | `22` | tailnet, timers, console KVM | ✅ **01/09/2026** |

## ✅ 12 bis. Fermeture terminée le 01/09/2026

`8006`, `22` et `3128` sont restreints à l'ipset `admin` ; `5900-5999` supprimé.
Depuis Internet, les trois ports expirent sur les 3 IP publiques et **seul le
ping répond**. Les 6 chemins d'administration (3 nœuds × 2 portes) ont été
vérifiés sur connexions neuves, et les compteurs `iptables` confirment que les
règles sont réellement empruntées. Quorum 3/3, corosync **4 liens** (le ring1
sur IP publiques passe par `+cluster`), Ceph `HEALTH_OK`, 7 ressources HA, NAS
monté, SSH inter-nœuds opérationnel, supervision Zabbix verte par le chemin
privé — `57.130.34.122` a disparu des journaux, la bascule est complète.

**Ce que la fermeture a failli casser, et comment on l'a vu** : l'inventaire des
sources (P2) a révélé deux administrateurs sur le chemin public —
`82.127.36.38` (IP partagée du bureau, portant les clés `matt@LENOVO-MCA2`,
`matt@LENOVO-MCA2-windows` et `brtrnd@thinkpad`) et `88.171.147.68` (Bertrand
depuis un autre site), avec 570 connexions SSH sur pve1 pour la première. V2 a
été **retardée d'une journée** le temps que Bertrand bascule sur son pair VPN
`10.90.0.3`. Sans cet inventaire, la fermeture coupait un collègue en pleine
session. **À refaire avant toute fermeture du même genre.**

### Reste ouvert sur ce chantier

- ✅ **Test « porte 2 seule » réussi le 01/09/2026** : wg0 coupé sur le poste,
  les 3 nœuds restent joignables par le tailnet en SSH et 8006, chaîne
  `tailnet → nœud → qm terminal 100` vérifiée
  ([11-headscale.md](11-headscale.md#test--porte-2-seule---01092026)). Au
  passage : le chemin direct bascule en **IPv6**, couvert parce que la règle
  `udp/41641` est sans source — ne jamais la restreindre à de l'IPv4.
- ⚠️ **Test complet restant** (arrêt réel de la VM 100) : ce qui reste à
  mesurer est le **rétablissement** d'un pair, plan de contrôle headscale
  éteint (poste redémarré, endpoint changé) — les pairs déjà établis, eux,
  dialoguent en direct sans lui. À programmer en fenêtre de maintenance.
- 📋 **Relire `/var/log/pve-firewall.log`** dans quelques jours pour attraper un
  flux légitime rare que l'ipset `admin` aurait manqué.
- 📋 **`3128` (SPICE)** : compteur à 0 depuis la fermeture — candidat à la
  suppression pure comme `5900-5999`, à confirmer sur 30 jours.
- 📋 Sonde externe de disponibilité : depuis Internet il ne reste que l'ICMP —
  la supervision de l'API se fait désormais **depuis l'intérieur**.

**V1 faite le 31/08** : `[IPSET admin]` créé (`10.90.0.0/24`), `3128` restreint,
`5900-5999` **supprimé** (rien n'y écoutait). Vérifié depuis l'extérieur : les
deux ports expirent sur les 3 IP publiques, le ping répond, les deux portes
VPN fonctionnent, quorum/Ceph/supervision intacts.

### ⛔ V2 bloquée : un second administrateur utilise le chemin public

L'inventaire des sources de l'API (préalable P2) a évité une coupure : outre
Zabbix et les scanners, **`82.127.36.38` totalise ~24 000 requêtes sur pve1 et
pve2 — c'est `brtrnd@keycloak`**, l'interface web de Bertrand Leroux, avec un
tableau de bord ouvert qui interroge `/cluster/resources` et `/cluster/tasks`
toutes les 2 secondes. Fermer le 8006 le couperait **en pleine session**.

Son pair VPN existe (`brtrnd`, `10.90.0.3/32`, créé le 31/08) et **le tunnel
est monté** — handshake mesuré à 1 min 35 — mais le trafic y est résiduel
(13 Ko reçus) : le tunnel est au repos, **le navigateur passe par l'IP
publique**. Vraisemblablement parce que son client n'utilise pas Unbound
(`10.40.0.1`) comme résolveur : sans cela `pveN.infra` continue de résoudre en
IP publique, même VPN monté.

**Avant V2**, il faut donc que Bertrand : VPN monté, ait `DNS = 10.40.0.1` dans
sa configuration WireGuard (ou vise `10.40.0.2/.3/.4`), et confirme que
`https://pve1.infra.teleimagerie.net:8006` s'ouvre bien **par le VPN** — la
preuve étant une source `10.90.0.3` dans `/var/log/pveproxy/access.log`, et
non plus `82.127.36.38`. Le contrôle est le même pour tout autre accès qui
apparaîtrait dans cet inventaire.

✅ **`ignoreip` fail2ban déjà posé** sur les 3 nœuds le 31/08
(`configs/fail2ban-proxmox.local`) : `10.90.0.0/24`, `10.40.0.60` et les
réseaux vRack ne peuvent plus être bannis — sinon 5 échecs enfermeraient
dehors la seule source d'administration restante. Le tailnet n'a pas besoin
d'y figurer : il livre depuis `127.0.0.1`.

Restent à prévoir dans la passe de fermeture : un **second timer
anti-verrouillage** `pve-firewall stop` (celui de
[04-securite.md](04-securite.md#modifier-le-firewall-sans-se-verrouiller) écrit
dans `/etc/pve` et **échoue en silence si le quorum est perdu**) ; et des tests
en `-o ControlMaster=no`, faute de quoi on teste une session déjà ouverte —
elle survit à la fermeture et donne une fausse assurance.

`5900-5999` : rien n'écoute au repos (les consoles passent par le WebSocket du
8006) — **candidats à la suppression pure** plutôt qu'à la restriction, à
confirmer par les compteurs `iptables` sur 30 jours.
