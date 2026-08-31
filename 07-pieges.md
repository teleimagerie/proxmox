# Pièges rencontrés

Les obstacles réellement rencontrés du 11 au 15 août 2026, avec leur cause et
leur résolution. C'est le fichier à relire avant toute intervention comparable.

Ordre chronologique : 1 à 21 le déploiement (11/08), 22 le proxy et le premier
tunnel (12-13/08), 23 le site-à-site pfSense vers TELLIS (14/08), 24 à 28 le NAS-HA et les
sauvegardes (13-15/08), 29 le déploiement headscale (15/08), 30 le diagnostic
certificats syngo-via (24/08), 31 les premiers enrôlements headscale (25/08).

---

## 1. Le template OVH laissait déjà la place à Ceph

**Symptôme** — Le plan initial prévoyait une réinstallation complète des 3 serveurs
pour maîtriser le partitionnement.

**Réalité** — Le template `proxmox9` laisse spontanément **738,4 Gio libres et
contigus** par disque, et place déjà `/var/lib/vz` sur un miroir ZFS. Exactement
la cible.

**Leçon** — Inspecter l'existant avant de planifier une réinstallation.
`sgdisk -p /dev/nvme0n1` aurait suffi dès le départ.

---

## 2. Clé API OVH avec des chemins vides

**Symptôme** — `403 Client::Forbidden "This call has not been granted"` sur tous
les appels, y compris `/me`, alors que la clé s'authentifie correctement.

**Cause** — Les règles du token étaient :

```json
"rules":[{"method":"GET","path":""},{"method":"POST","path":""}, ...]
```

Toutes les méthodes autorisées, mais sur un **chemin vide** — qui ne correspond
à rien. Le champ « path » n'avait pas été renseigné à la création.

**Diagnostic** — `GET /auth/currentCredential` fonctionne toujours et révèle les
règles réelles. C'est le premier appel à tenter face à un 403 inexpliqué.

**Résolution** — Recréer le token en renseignant explicitement :

```
GET /domain/zone          ← sans astérisque, requis pour lister les zones
GET|PUT|POST|DELETE /domain/zone/*
```

---

## 3. `pvecm add` réclame un mot de passe

**Symptôme** — `EOF while reading password` en exécution non interactive.

**Cause** — Par défaut, `pvecm add` s'authentifie sur l'**API** du nœud existant
et demande le mot de passe `root@pam`. Les clés SSH ne l'aident pas.

**Résolution** — `pvecm add <ip> --link0 … --link1 … --use_ssh 1`, qui bascule
sur la jonction historique par SSH et accepte l'authentification par clé.

---

## 4. `pveceph install` bloque sur une confirmation apt

**Symptôme** — `Do you want to continue? [Y/n] Abort.` puis
`apt failed during ceph installation (256)`.

**Cause** — `pveceph install` appelle `apt` sans `-y`. `DEBIAN_FRONTEND=noninteractive`
ne suffit pas.

**Résolution** — `yes | pveceph install --repository no-subscription`

---

## 5. `pvenode acme account register` bloque sur les CGU

**Symptôme** — `Cannot continue without agreeing to ToS, aborting.` Il n'existe
pas d'option `--tos_url`.

**Résolution** — `printf "y\n" | pvenode acme account register …`

Accepter les CGU de Let's Encrypt est un engagement contractuel : à faire
explicitement valider par le responsable, pas à glisser dans un script.

---

## 6. Postfix : Gmail rejette l'IPv6

**Symptôme** — Les notifications HA n'arrivent pas. Journal :

```
status=bounced (550-5.7.1 [2001:41d0:34b:de00::] Gmail has detected that this
message does not meet IPv6 sending guidelines regarding PTR records)
```

**Cause** — Postfix privilégie l'IPv6, dont le PTR ne satisfait pas les exigences
de Google. Le même message repassé en IPv4 est accepté (`250 2.0.0 OK`).

**Résolution** — Sur les 3 nœuds :

```bash
postconf -e "smtp_address_preference = ipv4" && systemctl restart postfix
```

**Diagnostic** — `journalctl | grep "to=<"` montre le relais utilisé et le
verdict. Il n'y a pas de `/var/log/mail.log` sur Debian 13, tout est dans journald.

> **Note du 30/08/2026** — largement caduc : les notifications Proxmox (vzdump,
> fencing, system-mail) ne passent plus par le Postfix local mais par le
> système de notifications → endpoint SMTP Mailjet, et uniquement en cas de
> problème (matcher `erreurs-mailjet`, les succès sont avalés — canal principal :
> Zabbix, [17-zabbix.md](17-zabbix.md#supervision-des-sauvegardes--depuis-le-30082026)).
> Le contournement `smtp_address_preference = ipv4` reste en place et ne
> concerne plus que l'éventuel courrier Postfix résiduel hors notifications.

---

## 7. fail2ban n'active qu'une prison sur deux

**Symptôme** — Après installation, `fail2ban-client status` ne montre que `sshd`,
alors que `jail.d/proxmox.local` déclare aussi `proxmox`.

**Cause** — Le service a démarré avant d'avoir lu la configuration complète.

**Résolution** — `fail2ban-client reload`. Le filtre était valide
(`fail2ban-regex` le confirmait), seul le chargement avait échoué.

---

## 8. `sysrq-b` ne teste pas la haute disponibilité

**Symptôme** — Après un reset brutal, la VM redémarre **sur le même nœud**.
Aucune relocalisation.

**Cause** — `sysrq-b` redémarre en ~65 s, plus vite que le délai de fencing
(~130 s). Le nœud revient et reprend son propre service avant la décision du CRM.

**Résolution** — Pour tester la vraie relocalisation, isoler durablement :

```bash
systemctl mask corosync && systemctl stop corosync
```

Détail dans [05-tests-ha.md](05-tests-ha.md).

---

## 9. Une session SSH vers un nœud tué reste suspendue indéfiniment

**Symptôme** — La commande de test HA est restée bloquée **plus de 2 heures**,
faisant manquer toute la fenêtre de bascule.

**Cause** — `ssh pve2 'echo b > /proc/sysrq-trigger'` : la machine meurt sans
fermer la connexion TCP. `ConnectTimeout` ne couvre que l'établissement, pas un
gel après connexion.

**Résolution** — Toujours encadrer par `timeout`, superviser depuis un **nœud
tiers**, et détacher les mesures avec `systemd-run` plutôt qu'un `nohup … &`
à travers SSH (qui meurt avec la session).

---

## 10. `dig` interrogé sur le mauvais serveur de noms

**Symptôme** — Les enregistrements A venaient d'être créés mais `dig` ne
renvoyait rien. Faux négatif qui aurait pu faire recréer des entrées en double.

**Cause** — Requête envoyée à `dns108.ovh.net`, qui n'héberge pas la zone. Les
serveurs réels sont `ns17.ovh.net` et `dns17.ovh.net`. (Chaque zone du compte a
sa propre paire — `isoteam.mn` vit par exemple sur `ns102`/`dns102.ovh.net` :
[14-noms-de-domaine.md](14-noms-de-domaine.md#serveurs-autoritaires).)

**Résolution** — Récupérer les NS avant de tester :
`dig +short NS <zone>`, puis interroger `@1.1.1.1` **et** le NS faisant autorité.

---

## 11. Connexion web : le realm saisi deux fois

**Symptôme** — `no such user ('matt@pve@pve')`, `no such user ('matt@pve@pam')`.

**Cause** — Le realm est déjà dans la liste déroulante ; le retaper dans le champ
nom d'utilisateur le concatène.

**Résolution** — Champ *User name* = `matt` seul, realm choisi dans la liste.

---

## 12. `invalid credentials (500)` à l'ajout d'un TOTP

**Symptôme** — La fenêtre TOTP refuse le mot de passe, alors que la connexion
avec ce même mot de passe fonctionne, et **aucune erreur n'est journalisée**.

**Diagnostic** — Reproduction de la requête exacte via l'API sur un compte
jetable : **HTTP 200**, TOTP enrôlé. Le serveur est donc hors de cause, le
problème vient de ce que le navigateur envoie.

**Cause probable** — Remplissage automatique du gestionnaire de mots de passe
dans le champ « Password » de la fenêtre TFA. Ce champ attend le mot de passe du
compte **connecté** (« the current password of the user performing the change »),
pas celui du compte modifié.

**Résolution** — Effacer et retaper le champ, ou passer en navigation privée.
Contournement définitif : enrôler en ligne de commande, où **`root@pam` est
exempté** de cette vérification.

---

## 13. Le choix entre deux entrées TOTP a verrouillé le compte

**Symptôme** — Après nettoyage des doublons, plus aucune connexion possible.

**Cause** — Un script demandait à l'utilisateur laquelle des deux entrées TOTP
conserver. La mauvaise a été gardée : celle marquée `utilisee=False`, dont le
secret n'était pas dans le téléphone.

**Résolution immédiate** — `pveum user tfa delete matt@pve` par SSH, puis
réenrôlement propre.

**Correction de fond** — Le script ne pose plus la question. Il supprime
**tout**, impose de vider le téléphone, et **vérifie le code saisi avant
d'activer quoi que ce soit** — rendant le verrouillage impossible.

**Leçon** — Ne pas déléguer à l'utilisateur un choix dont une option casse
l'accès, quand la bonne réponse est déterminable automatiquement.

---

## 14. Les clés de secours sont irrécupérables

**Symptôme** — Clés de secours partiellement notées, demande de les réafficher.

**Réalité** — `/etc/pve/priv/tfa.cfg` ne contient que des empreintes **SHA-256
salées** (64 caractères hex), pas les clés au format `bf71-5a93-e362-ae0b`.
Personne, pas même root, ne peut les relire.

**Résolution** — Révoquer et régénérer :

```bash
pveum user tfa delete matt@pve --id recovery
pvesh create /access/tfa/matt@pve --type recovery
```

**Leçon** — L'affichage des clés de secours est un événement unique. Prévoir où
les consigner **avant** de lancer la commande qui les génère.

---

## 15. Un bridge classique aurait fait fuiter tous les VLAN

**Contexte** — Le bloc IP en vRack arrive **non tagué** ; le livrer à une VM impose
un bridge sur la carte physique, laquelle portait déjà `.100` (Corosync) et `.200`
(Ceph) en sous-interfaces.

**Piège** — Un bridge classique sur la carte physique aurait rendu ces
sous-interfaces muettes, *et* laissé toutes les VM voir et injecter dans n'importe
quel VLAN — y compris celui de Ceph.

**Résolution** — Bridge **VLAN-aware** avec filtrage par port. Migration faite à
chaud, nœud par nœud, sans aucune interruption : les deux configurations émettent
des trames 802.1Q identiques, un nœud migré parle donc à un nœud qui ne l'est pas.

---

## 16. Donner un VLAN à l'hôte demande deux gestes

**Symptôme** — `ip link add link vmbr1 name vmbr1.400 type vlan id 400` puis une
adresse : l'hôte ne joint rien.

**Cause** — Sur un bridge VLAN-aware, le VLAN doit aussi être autorisé sur le port
**interne** du bridge. `bridge vlan show dev vmbr1 self` ne listait que 1, 100, 200
et 300 — ifupdown2 les avait ajoutés en traitant les stanzas `vmbr1.N`.

**Résolution** — `bridge vlan add vid 400 dev vmbr1 self`

---

## 17. Un reboot depuis l'invité ne relit pas la config Proxmox

**Symptôme** — La VM OPNsense a redémarré sur son ISO d'installation malgré un
`qm set --boot order=scsi0` appliqué juste avant.

**Cause** — Le processus QEMU survit à un redémarrage déclenché depuis l'invité :
la configuration Proxmox n'est relue qu'au démarrage du processus.

**Résolution** — `qm stop` puis `qm start`, jamais un `reboot` interne.

---

## 18. Le shell root d'OPNsense est tcsh

**Symptôme** — `Ambiguous output redirect` sur toute commande contenant `2>/dev/null`.

**Résolution** — Encapsuler dans `sh -c "..."`. Coûte une bonne demi-heure quand on
ne l'a pas vu, les commandes semblant simplement ne rien produire.

---

## 19. Les flèches du clavier cassent les menus en console série

**Symptôme** — Un `\033[D` envoyé à l'installateur a été compris comme « Annuler »
et a fait reculer d'un écran.

**Cause** — Le `ESC` initial de la séquence peut arriver isolé ; `dialog` le traite
alors comme une annulation.

**Résolution** — N'utiliser que des octets uniques : **TAB** pour changer de champ,
la **première lettre** pour choisir dans un menu, **Ctrl+L** pour forcer un
redessin complet. Repérer le bouton actif à ses chevrons en gras (`ESC[1m`).

---

## 20. OPNsense réécrit `authorized_keys` à chaque démarrage

**Symptôme** — SSH fonctionnait, puis après un redémarrage : `Connection closed by
10.40.0.1 port 22`, et `/root/.ssh/authorized_keys` avait disparu.

**Cause** — OPNsense régénère ce fichier depuis `config.xml`
(`system/user/authorizedkeys`, en base64). Une clé posée à la main dans le fichier
ne survit pas.

**Résolution** — Inscrire la clé dans `config.xml`, encodée en base64.

---

## 21. Une configuration WireGuard écrite à la main a besoin de `configure`

**Symptôme** — Section `<OPNsense><wireguard>` correcte dans `config.xml`, module
`if_wg` chargé, mais aucune interface `wg0` et `configctl wireguard show` vide.

**Cause** — `configctl wireguard start` ne suffit pas. C'est l'action **`configure`**
qui déclenche la génération des fichiers et la création de l'interface.

**Résolution** — `configctl wireguard configure`

**Piège associé** — Renseigner `serveraddress`/`serverport` sur un pair *itinérant*
lui fabrique un `Endpoint` fixe dans la configuration serveur — en l'occurrence
notre propre IP publique. Ces champs ne servent que lorsque OPNsense est *client*
d'un serveur distant ; les laisser vides pour un nomade.

---

## 22. `configctl wireguard configure` ne régénère pas les modèles

**Symptôme** — Suite du piège n° 21, rencontré le 13/08/2026 en montant le tunnel
site-à-site. Section `<wireguard>` correcte dans `config.xml`, `configure` répond
`OK`, l'interface `wg1` monte et porte bien son adresse — mais
`configctl wireguard show` la donne sans clé publique, sur un **port d'écoute
aléatoire** (52981 au lieu de 51821), et sans aucun pair.

**Diagnostic** — `ls -l /usr/local/etc/wireguard/` : pas de `wg1.conf`, et
`wg0.conf` porte toujours sa date de la veille. Aucun modèle n'a été régénéré.
C'est le contrôle décisif : si les `.conf` n'ont pas bougé, `configure` n'a rien
eu à appliquer.

**Cause** — `configure` **applique** les fichiers de configuration existants, il
ne les **fabrique** pas. L'interface WireGuard est bien créée, d'où l'illusion
que la commande a fonctionné. Passer par l'interface web régénère les modèles au
moment d'enregistrer ; une écriture directe dans `config.xml` ne le fait pas.

**Résolution** — Régénérer explicitement, *puis* appliquer :

```bash
configctl template reload OPNsense/Wireguard
configctl wireguard configure
```

Ordre qui a fonctionné, pour une interface WireGuard assignée :

```bash
configctl template reload OPNsense/Wireguard   # fabrique wgN.conf
configctl interface reconfigure optN           # assigne l'interface
configctl wireguard configure                  # applique, en dernier
configctl filter reload
```

**Leçon** — Toute modification de `config.xml` en ligne de commande demande la
même précaution pour le service concerné. Vérifier la date des fichiers générés,
pas seulement le `OK` retourné par `configctl`.

> Ce `wg1`/51821 du 13/08 n'existe plus : le site-à-site a été reconstruit le
> 14/08 en **`wg2` / UDP 51822** sur l'interface `opt3`. Voir
> [08-opnsense.md](08-opnsense.md#site-à-site--wg2-udp-51822).

---

## 23. Côté pfSense, WireGuard ne se comporte pas comme sur OPNsense

Cinq obstacles rencontrés le 14/08/2026 en montant le site-à-site. Ils sont tous
propres à pfSense et invisibles depuis notre côté.

**a. Les `Allowed IPs` ne créent aucune route.** Sur OPNsense elles alimentent la
table de routage ; sur pfSense elles ne sont qu'un **filtre cryptographique**.
Symptôme : le handshake s'établit, les paquets sont acceptés, mais les réponses
partent vers la passerelle WAN par défaut et disparaissent. `netstat -rn` sur le
pfSense est le contrôle décisif — s'il n'y a pas de route vers nos réseaux, rien
ne fonctionnera. Il faut **assigner** le tunnel à une interface, lui créer une
passerelle, puis des routes statiques. Une passerelle exige une interface, une
interface exige l'assignation : la chaîne est obligatoire.

**b. Assigner un tunnel le retire du groupe d'interfaces `WireGuard`.** Ce groupe
ne contient que les tunnels **non assignés**. Les règles posées dessus cessent
donc de s'appliquer à l'instant de l'assignation, et l'interface neuve n'en a
aucune : tout est refusé par défaut. C'est ainsi que le tunnel des nomades du
site distant a été coupé, administrateur connecté compris. **Ne jamais assigner
un tunnel par lequel passe son propre accès**, et créer un tunnel dédié plutôt
que d'assigner un tunnel de production.

**c. Le champ `Protocol` d'une règle vaut TCP par défaut.** Une règle « pass »
créée sans y toucher laisse passer TCP et rejette ICMP — le tunnel semble mort
alors qu'il fonctionne, parce qu'on le teste au `ping`.

**d. `Save` n'applique rien.** pfSense écrit dans `config.xml` au *Save* et ne
charge le filtre qu'au clic sur **Apply Changes**. Une règle visible dans la
configuration peut être totalement absente du pare-feu en cours d'exécution.

**e. Assigner un tunnel lui fait perdre son MTU.** `tun_wg2` déclarait
`<mtu>1420</mtu>` comme les deux autres tunnels, et fonctionnait pourtant en
**1500**. Une fois le tunnel assigné, c'est le champ *MTU* de l'interface qui
gouverne ; laissé vide, il impose le défaut 1500 et écrase la valeur du tunnel.
Le champ MTU de *VPN → WireGuard → Tunnels* devient alors sans effet — c'est
**Interfaces → OPT*n* → MTU** qu'il faut renseigner. Symptôme différé et
trompeur : le `ping` passe, les transferts volumineux se figent, car après
chiffrement un paquet de 1500 octets en fait ~1560 sur le fil.

**Leçon transversale** — Face à un tunnel qui monte sans rien transporter,
descendre dans cet ordre : handshake présent ? routes des deux côtés ? règle
appliquée et non seulement enregistrée ? protocole de la règle ? Une capture
`tcpdump` sur l'interface tunnel sépare en une commande « nous n'émettons pas »
de « ils ne répondent pas ».

---

## 24. Le NAS-HA n'est pas raccordable au vRack

**Symptôme** — Le plan de sauvegarde prévoyait « raccorder le NAS-HA au vRack
`pn-1165892` et déclarer l'ACL avec les IP vRack des 3 nœuds ». Aucune de ces
deux choses n'est possible.

**Cause** — Limitation assumée du produit, écrite noir sur blanc dans la
documentation OVH : *« HA-NAS cannot be integrated into the vRack private
network. However, HA-NAS and vRack are not incompatible if you go via the public
IP path of the server connected to vRack. »*

**Conséquences concrètes** :

- le NAS n'est pas sur le VLAN 300, il vit sur son propre réseau OVH
  (`10.201.13.43`) et se joint par la **route par défaut**, donc par `vmbr0` ;
- l'ACL attend les **IP publiques** — `91.134.84.222`, `51.68.240.48`,
  `51.68.240.191`. Y déclarer une IP vRack ne produit aucune erreur, simplement
  un montage refusé ;
- MTU 1500 : **pas de jumbo frames** sur ce chemin, contrairement au VLAN 200.

**Vérification** — `ip route get 10.201.13.43` doit sortir
`via 100.64.0.1 dev vmbr0`. Si la réponse mentionne `vmbr1.x`, c'est qu'une route
locale entre en conflit.

**Leçon** — Vérifier la compatibilité réseau d'un service managé *avant* de bâtir
un plan d'adressage autour. Ici le VLAN 300 avait été réservé pendant trois mois
pour un usage qui ne pouvait pas exister.

---

## 25. L'API du NAS-HA : deux surprises de format

**Symptôme 1** — `HTTP 400 : "Description is invalid. Must be an alphanumerical
value not exceeding 50 characters."` sur la création d'une partition, alors que
la description précédente était passée.

**Cause** — La différence entre les deux : une **virgule**. « Datastore Proxmox
Backup Server » passe, « Disques VM, ISO et templates » non. Le champ n'accepte
que des lettres, des chiffres et des espaces — ni ponctuation, ni accents, ni
tirets. Le message parle d'« alphanumerical », il faut le prendre au pied de la
lettre.

**Symptôme 2** — Le paramètre `size` est documenté comme « Partition size », sans
unité.

**Réalité** — C'est un **Gio**, pas un Go. Une partition créée avec `size: 1800`
apparaît en `1887436800` KiB dans `df`, soit exactement 1800 Gio (1932 Go).
De même, le `zpoolSize: 3000` d'un service annoncé « 3 To » vaut 3000 Gio.

**Leçon** — Constater l'unité sur le résultat plutôt que la déduire du nom
commercial. `df -h` après montage tranche en une seconde.

---

## 26. Les droits d'un jeton PBS sont une intersection

**Symptôme** — `pvesm status` répond
`pbs: Cannot find datastore 'tim', check permissions and existence!`, alors que
le datastore existe, que l'ACL a bien été posée sur le jeton et que l'empreinte
du certificat est correcte.

**Diagnostic décisif** :

```bash
proxmox-backup-manager user permissions 'backup@pbs!pve'
# n'affiche que l'en-tête : aucun privilège effectif
```

**Cause** — Les droits effectifs d'un jeton d'API PBS sont l'**intersection** de
ses propres ACL et de celles de son compte propriétaire. Le compte `backup@pbs`
venait d'être créé et n'avait aucun droit : l'intersection était vide.

**Résolution** — Accorder le rôle **aux deux**, compte et jeton :

```bash
proxmox-backup-manager acl update /datastore/tim DatastorePowerUser --auth-id backup@pbs
proxmox-backup-manager acl update /datastore/tim DatastorePowerUser --auth-id 'backup@pbs!pve'
```

**Leçon** — Un jeton ne peut jamais dépasser son porteur. Le message d'erreur
parle de datastore introuvable là où le problème est un droit manquant : c'est
`user permissions` qui donne la réponse, pas le journal.

---

## 27. Le mot de passe d'un stockage PBS ne se lit pas sur l'entrée standard

**Symptôme** — `pvesm add pbs … --username … ` sans `--password`, le secret étant
fourni sur stdin :

```
Use of uninitialized value $password ... PBSPlugin.pm line 728
create storage failed: pbs: error fetching datastores - 401 Unauthorized
```

**Cause** — `pvesm` n'implémente pas de lecture du mot de passe sur l'entrée
standard. Il faut le passer en argument — donc le rendre visible dans `ps` le
temps de la commande.

**Résolution retenue** — Écrire le secret là où PVE le range de toute façon, puis
déclarer le stockage dans le fichier de configuration :

```bash
install -m 600 /dev/null /etc/pve/priv/storage/pbs.pw
# y écrire le secret, puis ajouter la strophe "pbs: pbs" à /etc/pve/storage.cfg
```

Les deux fichiers sont répliqués par pmxcfs : l'opération vaut pour les 3 nœuds.

**Leçon** — Quand un outil impose un secret en ligne de commande, regarder où il
le range : écrire directement dans ce fichier est souvent plus propre que la
commande officielle.

---

## 28. PBS ne peut pas se sauvegarder dans son propre datastore

**Symptôme** — Première exécution de la tâche quotidienne, le 14/08/2026 à 02:00.
Les VM 100 et CT 201 passent, la VM 102 — qui *est* le serveur PBS — échoue après
exactement deux minutes :

```
ERROR: Backup of VM 102 failed - VM 102 qmp command 'backup' failed -
       backup connect failed: command error: http upgrade request timed out
INFO: Backup job finished with errors
```

**Diagnostic décisif** — Le journal *de la VM PBS*, pas celui de l'hyperviseur :

```
02:00:06  qemu-ga: info: guest-fsfreeze called
02:02:07  qemu-ga: info: guest-fsthaw called
02:02:07  proxmox-backup-proxy: TASK ERROR: connection error:
                                connection closed before reading preface
```

**Cause** — En mode `snapshot`, vzdump commence par un `guest-fsfreeze` via l'agent
invité, **puis** ouvre la connexion de sauvegarde. Ici la cible de cette connexion
est le serveur PBS qui tourne *dans la VM qu'on vient de geler* : il ne peut plus
écrire, la connexion n'aboutit jamais, et le dégel n'a lieu qu'à l'expiration du
délai de deux minutes. Blocage par construction, pas incident passager.

**Effet de bord notable** — Pendant ces deux minutes, PBS est gelé pour *tout le
monde* : la sauvegarde de la CT 201 lancée depuis pve1 a mis **2 min 05 au lieu de
6 s**, attendant le dégel. Un invité qui gèle peut donc pénaliser les sauvegardes
des autres nœuds.

**`backup=0` sur `scsi1` ne suffit pas** : il exclut le *disque* du datastore, pas
la *VM*. Le journal affiche bien `exclude disk 'scsi1'` avant d'échouer.

**Résolution** — Exclure la VM du job quotidien, et la sauvegarder ailleurs :

```bash
pvesh set /cluster/backup/<uuid> --exclude 102     # job quotidien vers PBS
# la VM 102 reste couverte par le job hebdomadaire vers nas-vm (stockage NFS,
# indépendant de PBS : le gel de l'invité n'y bloque rien)
```

Vérification, depuis le nœud qui porte la VM :

```
INFO: starting new backup job: vzdump --exclude 102 --storage pbs --mode snapshot --all 1
INFO: skip external VMs: 100, 201
INFO: Backup job finished successfully
```

**Leçon** — Un serveur de sauvegarde ne se sauvegarde pas lui-même *chez lui*. La
règle vaut pour toute VM hébergeant le service que vzdump utilise : geler
l'invité, c'est geler le service dont dépend l'opération en cours.


## 29. La réflexion NAT seule ne suffit pas : il faut aussi le NAT sortant du retour

**Symptôme** — Rencontré le 15/08/2026 en déployant headscale. La redirection
`57.130.34.123:443 → 10.40.0.30` en réflexion `purenat` posait bien ses règles
`rdr` sur toutes les interfaces (visible dans `pfctl -sn` : `vtnet1`, `lo0`,
`wg0`, `wg2`). Pourtant, depuis un conteneur du VLAN 400,
`curl https://headscale.teleimagerie.net` restait muet — alors que la même URL
répondait parfaitement depuis Internet.

**Cause** — En épingle à cheveux (client et serveur sur le même sous-réseau),
la réflexion ne réécrit que la **destination**. Le paquet arrive au serveur avec
la source du client intacte : la réponse part alors **en direct** sur le LAN,
avec une source (`10.40.0.30`) que le client n'attend pas — il attend
`57.130.34.123`. Le retour court-circuite OPNsense, le client jette la réponse,
la poignée de main n'aboutit jamais.

**Résolution** — Activer le correcteur global qui ajoute le NAT **source** des
connexions réfléchies (le retour repasse alors par le pare-feu) : dans
`config.xml`, sous `<system>` :

```xml
<enablenatreflectionhelper>yes</enablenatreflectionhelper>
```

(équivalent GUI : *Firewall → Settings → Advanced → Automatic outbound NAT for
Reflection*), puis `configctl filter reload`. Vérification immédiate :
`{"status":"pass"}` depuis le CT du VLAN 400.

**Leçon** — Une règle de réflexion visible dans `pfctl -sn` ne prouve que
l'aller. En épingle à cheveux, toujours tester le flux **depuis le réseau
interne**, et se souvenir que le retour a besoin de son propre NAT.

---

## 30. Le fichier hosts Windows fausse tout diagnostic DNS sous WSL2

**Symptôme** — Le 24/08/2026, en cherchant pourquoi le proxy « semblait gérer »
les certificats syngo-via : `dig` renvoyait `57.130.34.122` pour les quatre
noms publiés. Tout indiquait que la bascule DNS avait eu lieu — trafic dans les
logs du relais, certificats cohérents, chaque test « confirmait » un état qui
n'existait pas sur Internet.

**Cause** — Sous WSL2, la résolution passe par le **résolveur Windows** (DNS
tunneling), qui applique le fichier `C:\Windows\System32\drivers\etc\hosts`.
Des entrées y avaient été forcées pour tester le proxy avant bascule. Même
`dig`, qui ignore pourtant le `/etc/hosts` Linux, recevait ces valeurs : c'est
le résolveur Windows qui répondait à sa place. Le trafic vu dans
`stream_access.log` n'était que celui des machines à hosts forcé.

**Résolution** — Retirer les entrées forcées, et surtout : tout diagnostic DNS
doit interroger le serveur **autoritaire** (`dig +short NS <zone>` puis
`dig @<ns> <nom>`), jamais le seul résolveur local. Comparer avec
`getent ahostsv4 <nom>`, qui montre ce que la machine utilise réellement.

**Leçon** — Le piège n° 10 (mauvais serveur de noms interrogé) a un jumeau
inversé : un résolveur local qui **répond avec conviction des valeurs
fausses**. Au passage, le vrai état DNS a révélé que la bascule vers le proxy
n'avait jamais été faite, et que `syngo.isoteam.mn` n'avait aucun
enregistrement — deux constats soldés par la bascule du 26/08/2026, voir
[09-proxy-tim.md](09-proxy-tim.md#bascule-dns-du-26082026).

---

## 31. Les nœuds enrôlés par clé taguée n'appartiennent pas au user de la clé

**Symptôme** — Le 25/08/2026, première passerelle réelle enrôlée (`gw-qum`,
clé pré-auth `tag:gateway` créée sous le user `site-QUM`) : dans
`headscale nodes list`, le nœud apparaît sous un user **`tagged-devices`**
(« Tagged Devices », ID 2147455555), que personne n'a créé — et pas sous
`site-QUM`.

**Cause** — Comportement de headscale v0.29 (policy v2) : dès qu'un nœud porte
un tag, **le tag remplace le user comme identité et comme propriétaire**. Les
nœuds tagués sont regroupés sous le user synthétique `tagged-devices` ; le user
de la clé ne subsiste que comme provenance, dans les métadonnées de la clé
(`pre_auth_key.user` de la sortie `headscale nodes list -o json-line`).

**Résolution** — Le modèle « révoquer un site = supprimer son user
`site-<code>` » ne supprime donc pas ses nœuds. Révoquer une passerelle :
`headscale nodes delete <id>` — les nœuds d'un site se retrouvent par leur nom
`gw-<code>`, ou par la clé d'origine dans la sortie JSON. Les users
`site-<code>` restent utiles pour ranger et tracer les clés, pas pour le cycle
de vie des nœuds.

**Leçon** — Vérifier un mécanisme de révocation **en réel** avant d'en faire
une promesse d'architecture : la matrice ACL avait été testée le 15/08 avec des
CT jetables, la révocation par user, jamais. Corrigé dans
[11-headscale.md](11-headscale.md#organisation-du-tailnet).

## 32. Joindre la VIP .122 depuis l'intérieur aboutit sur la GUI d'OPNsense

**Symptôme** — Le 27/08/2026, headscale part en crash-loop dès l'ajout de sa
section `oidc` : `tls: failed to verify certificate: x509: certificate is
valid for OPNsense.internal, not auth.teleimagerie.net`. Depuis un CT du
VLAN 400, `curl https://auth.teleimagerie.net` (VIP `57.130.34.122`) reçoit le
certificat auto-signé de l'interface web d'OPNsense — pas le proxy.

**Cause** — Les redirections de la VIP `.122` sont des règles NAT côté WAN
**sans réflexion** (contrairement à celles de `.123`, posées en `purenat` —
[piège n° 29](07-pieges.md#29-la-réflexion-nat-seule-ne-suffit-pas--il-faut-aussi-le-nat-sortant-du-retour)).
Vu du LAN, `.122` est une simple adresse locale d'OPNsense : le paquet
n'emprunte jamais la redirection, et c'est la GUI (lighttpd, qui écoute sur
toutes les adresses) qui répond en 443.

**Résolution** — Split-horizon plutôt qu'épingle NAT : un **override Unbound**
sert `auth.teleimagerie.net → 10.40.0.10` aux clients internes — le trafic va
droit au proxy, qui présente le bon certificat via son routeur SNI. Voir
[08-opnsense.md](08-opnsense.md#résolution-interne--override-unbound).

**Leçon** — Le correcteur global de réflexion (piège 29) ne joue que pour les
règles qui portent elles-mêmes une réflexion. Tout nouveau nom publié doit être
testé **depuis l'intérieur et depuis l'extérieur** — les deux chemins n'ont
rien en commun.

## 33. Un CT sans `nameserver` hérite du résolveur public du nœud

**Symptôme** — Toujours le 27/08/2026, l'override Unbound en place : le CT 203
voit bien `10.40.0.10`, mais le CT 202 (headscale) résout encore la VIP
publique et reste en crash-loop.

**Cause** — Sans option `nameserver` dans sa config LXC, `pct` recopie le
`resolv.conf` du nœud hôte au démarrage — soit le cache DNS d'OVH
(`213.186.33.99`), qui sert la vue **publique** et ignore l'override interne.
Le CT 201 avait l'option, le CT 202 non : deux conteneurs voisins, deux vues
DNS différentes.

**Résolution** — `pct set 202 --nameserver 10.40.0.1` (et `/etc/resolv.conf`
corrigé à chaud). Le CT 203 avait l'option dès sa création.

**Leçon** — Sur ce cluster, tout CT du VLAN 400 doit porter explicitement
`--nameserver 10.40.0.1`. À noter aussi : **headscale refuse de démarrer si
l'issuer OIDC est injoignable** — une erreur de DNS dans ce CT ne dégrade pas
le service, elle l'empêche de se lever ([16-keycloak.md](16-keycloak.md#ce-qui-est-raccordé)).

## 34. L'action requise « par défaut » s'impose aussi aux arrivants Google

**Symptôme** — Le 27/08/2026, premier test réel du brokering Google : le
compte Workspace passe l'écran Google… et tombe sur « Mobile Authenticator
Setup » — Keycloak lui réclame un TOTP local, alors que son MFA est déjà
porté par Google. Double MFA, friction sans gain.

**Cause** — Le TOTP obligatoire avait été posé comme *action requise par
défaut du realm* (`CONFIGURE_TOTP`, `defaultAction=true`). Une action par
défaut s'applique à **tout utilisateur nouvellement créé, fédérés compris** :
elle ne distingue pas un compte local d'un arrivant Google.

**Résolution** — L'obligation a été déplacée **dans le flux de connexion**,
là où la distinction existe : copie du flux `browser` → `browser-totp`,
sous-flux *Browser - Conditional 2FA* passé de *Conditional* à **Required**,
les deux conditions (`user configured`, `credential`) retirées de la copie.
Résultat : tout login **par mot de passe** exige l'OTP (enrôlement forcé au
premier passage — plus fort que l'action par défaut), tandis que les logins
Google, qui n'empruntent pas le sous-flux forms, n'en voient jamais.
`defaultAction` remis à `false`, action en attente retirée de l'utilisateur
fédéré déjà créé.

**Leçon** — Deux pièges en un : les *default required actions* sont globales
au realm, pas par voie d'entrée — pour différencier, c'est dans les **flux
d'authentification** que ça se joue ; et le sous-flux s'appelle « Conditional
**2FA** » depuis Keycloak 26.x (plus « Conditional OTP » comme dans toute la
littérature) — un script qui cherche l'ancien nom échoue en silence.

## 35. Un `kcadm update` partiel sur une exécution de flux remet sa priorité à zéro

**Symptôme** — Dans la foulée du piège 34, toute connexion par mot de passe
du realm `tim` échoue instantanément : « Invalid username or password »
**avant même l'affichage du formulaire**. Les logins Google et les sessions
déjà ouvertes fonctionnent — seuls les logins par formulaire sont morts.

**Cause** — Le passage du sous-flux 2FA en *Required* avait été fait par
`kcadm update authentication/flows/<flux>/executions -b '{"id":…,
"requirement":"REQUIRED"}'`. Ce `PUT` est un remplacement, pas un patch : les
champs absents du corps sont réinitialisés, dont **`priority`, retombée à
0** — le sous-flux 2FA est passé *devant* le formulaire mot de passe
(priorité 10). Keycloak évaluait donc l'OTP sans utilisateur authentifié →
échec immédiat.

**Résolution** — `POST authentication/executions/<id>/lower-priority`
(répété jusqu'à ce que l'index du sous-flux dépasse celui du formulaire),
vérifié dans la sortie `level/index/priority` puis sur la vraie page de
login (formulaire + bouton Google rendus).

**Leçon** — Après **toute** modification d'un flux d'authentification,
relire l'ordre (`level`/`index`) *et* recharger la page de login réelle
avant de rendre la main : le test structurel du piège 34 (« le sous-flux est
bien Required ») était passé, l'ordre d'exécution, lui, avait silencieusement
changé. Et préférer les endpoints `raise/lower-priority` à un `PUT` pour
tout ce qui touche à l'ordre.

## 36. `docker compose exec` court-circuite l'entrypoint de l'image Odoo

**Symptôme** — `docker compose exec -T web odoo shell -d odoo` échoue avec
`psycopg2.OperationalError: connection to server on socket
"/var/run/postgresql/.s.PGSQL.5432" failed` alors que le conteneur `web`
tourne parfaitement et sert l'application, et que `docker compose run` sur la
même image fonctionne.

**Cause** — L'image officielle `odoo` ne configure pas la base par un fichier
mais par un **entrypoint** qui traduit les variables `HOST`/`USER`/`PASSWORD`
en options `--db_host`/`--db_user`/`--db_password`. `docker compose run`
passe par cet entrypoint ; **`exec` non** — il lance la commande directement
dans le conteneur existant. Odoo ne voit alors aucun paramètre de connexion
et retombe sur la socket PostgreSQL locale, absente du conteneur.

**Résolution** — Pour toute commande Odoo (`shell`, `-u`, `-i`, scripts) :
`sudo docker compose run --rm -T web odoo shell -d odoo`. Réserver `exec` aux
commandes qui n'ont pas besoin de la base (ou lui passer explicitement
`--db_host=db --db_user=odoo --db_password=…`).

**Leçon** — Le symptôme désigne la base, la cause est le mode de lancement.
Deux corollaires appris le 31/08/2026 en posant le SSO : `odoo shell` **ne
commite pas** (il termine par un `cr.rollback()` — il faut un `env.cr.commit()`
explicite), et il faut se garder de filtrer la sortie d'un script distant sur
un marqueur de succès (`sed -n '/RESULTAT/,$p'`) : le filtre avale la trace
d'erreur et un échec devient un silence indistinguable d'une réussite muette.

---

## 37. Une patte réseau sans route retour rend le nœud sourd, sans rien bloquer

**Symptôme** — Depuis le VPN nomade, `10.40.0.2:8006` et `:22` (patte VLAN 400
de pve1) ne répondent pas : `nc` expire. Tout accuse le pare-feu, et la doc
elle-même l'avait conclu — « l'interface Proxmox (8006) injoignable, même
résultat depuis un client WireGuard » ([08-opnsense.md](08-opnsense.md#filtrage)).

**Cause** — Rien ne bloque. Le SYN **arrive** bien sur la patte VLAN 400 (la
source est `10.90.0.2`, que le `IN DROP -source 10.40.0.0/24` de `cluster.fw`
ne vise pas). Mais le nœud n'a **aucune route vers `10.90.0.0/24`** : sa route
par défaut part sur `100.64.0.1`, la passerelle publique OVH. Le SYN-ACK s'en
va donc par la mauvaise porte et disparaît. Routage asymétrique — jamais un
refus, toujours un silence, ce qui le fait passer pour du filtrage.

```bash
ip route get 10.90.0.2      # via 100.64.0.1 dev vmbr0  ← le diagnostic tient ici
```

**Résolution** — Une route retour explicite, persistante, sur chaque nœud :

```
post-up ip route add 10.90.0.0/24 via 10.40.0.1 dev vmbr1.400 || true
```

**Leçon** — Une machine dont la route par défaut sort ailleurs que par le VPN a
**toujours** besoin d'une route retour vers la plage VPN. Le piège a été payé
deux fois : sur pacs03 le 25/08/2026 (`New-NetRoute … 10.90.0.0/24`,
[15-pacs-secours.md](15-pacs-secours.md)) puis sur les hyperviseurs le
31/08/2026. Le réflexe de diagnostic : avant d'accuser un pare-feu, faire
`ip route get <IP du client>` **sur la cible**, et vérifier que le SYN arrive
(`tcpdump`). Un pare-feu qui bloque et une réponse qui part ailleurs donnent
exactement le même symptôme.
