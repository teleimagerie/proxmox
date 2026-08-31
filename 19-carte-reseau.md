# Carte réseau régénérable

La carte du cluster n'est plus dessinée à la main : elle est **produite depuis
l'infrastructure réelle**, confrontée aux intentions déclarées, et versionnée.
Mise en place le 31/08/2026.

## Ce que ça résout

Un schéma dessiné une fois est faux dès le premier changement, et personne ne
sait quand il a cessé d'être vrai. Ici, `make carte` interroge l'API Proxmox et
réécrit la carte. Le vrai gain n'est pas la carte elle-même : c'est le
**diff**. `git diff carte-reseau.d2` après régénération montre exactement ce
qui a bougé dans l'infrastructure depuis la dernière fois.

## Les deux moitiés

La séparation est le cœur du dispositif.

| | Source | Écrit par | Régénérable |
|---|---|---|---|
| **Inventaire** | API Proxmox | découvert | ✅ à volonté |
| **Intentions** | `topologie.yml` | à la main | ❌ jamais |

L'inventaire dit *ce qui est* : VM, conteneurs, IP, VLAN, nœud porteur. Les
intentions disent *ce qui doit être et pourquoi* : les zones, les rôles, les
cloisonnements voulus, les règles à tenir. Aucune API ne dira jamais pourquoi
le VLAN 300 est fermé au LAN — c'est du raisonnement, pas de la donnée.

Sans cette séparation, on perd l'un ou l'autre : soit on régénère et le sens
disparaît, soit on fige et la carte dérive.

## Usage

```bash
make               # affiche l'aide — ne touche à rien
make carte         # régénère le .d2 depuis l'infra, puis le SVG
make controle      # liste les écarts aux règles, n'écrit rien
make inventaire    # affiche ce qui a été découvert, n'écrit rien
```

`make` nu affiche l'aide plutôt que de régénérer : les autres cibles
interrogent la production ou réécrivent des fichiers versionnés, ce n'est pas
ce qu'on veut déclencher par inadvertance. C'est fixé par `.DEFAULT_GOAL` et
non par l'ordre des règles, pour qu'un déplacement de bloc dans le Makefile ne
change pas le comportement en silence.

`make carte HOTE=pve2` si pve1 est indisponible — mais voir la réserve plus
bas : seul pve1 porte une patte sur le VLAN 400.

## Pourquoi le rendu est dans un conteneur

Deux étapes délibérément séparées :

1. **la collecte** tourne hors conteneur, en Python pur (stdlib + PyYAML,
   comme les autres scripts du dépôt). Elle ouvre une session SSH sur pve1 ;
2. **le rendu** tourne dans un conteneur ne portant que D2, lancé en
   `--network none`, qui ne voit qu'un fichier texte.

Un conteneur qui dessine une image n'a aucune raison d'accéder à la production.
Monter l'agent SSH dedans étendrait la surface d'exposition sans contrepartie —
la séparation supprime le besoin au lieu de le contourner.

Conséquence pratique : `carte-reseau.d2` se régénère et se relit **sans
Docker**. Le conteneur n'est requis que pour le SVG final.

## Les écarts sont montrés, pas fatals

Quand le réel s'écarte des règles de `topologie.yml`, la génération réussit
quand même et **la machine fautive est peinte sur la carte** :

| Gravité | Rendu | Exemple |
|---|---|---|
| `critique` | cadre et fond rouges | une carte réseau sans tag → bloc public |
| `avertissement` | cadre ambre | `onboot` désactivé |

L'anomalie s'écrit dans le nœud lui-même (`⚠ net0 sans tag — bloc public`), pas
dans une légende à côté. Les écarts non rattachables à une machine — une
machine déclarée mais absente du cluster, ou l'inverse — vont dans un encart.

Une carte qui montre ce qui cloche vaut mieux qu'une carte qui refuse de sortir.

## Les règles

Déclarées dans `topologie.yml`, section `regles`. Trois aujourd'hui :

| Règle | Gravité | Ce qu'elle protège |
|---|---|---|
| `tag-400-obligatoire` | critique | l'exposition accidentelle sur le bloc public |
| `onboot` | avertissement | un service qui ne revient pas après redémarrage |
| `ha-pare-feu` | critique | la perte du VLAN 400 vers l'extérieur |

> **Piège corrigé à l'écriture.** La règle du tag vérifiait d'abord « au moins
> une carte en tag=400 ». OPNsense porte `net0` sans tag **et** `net1` en 400 :
> elle passait, alors que c'est justement la carte sans tag qui expose. Le
> contrôle porte maintenant sur la condition dangereuse — la présence d'une
> carte sans tag — et non sur la conformité attendue. Les deux ne sont pas
> équivalentes dès qu'une machine a plusieurs cartes.

## Fichiers

| | |
|---|---|
| `topologie.yml` | intentions — **le seul fichier à éditer** |
| `scripts/genere-carte.py` | collecte, contrôle, écrit le `.d2` |
| `Dockerfile` | image de rendu, D2 seul, ~8 Mio |
| `Makefile` | enchaîne les deux étapes |
| `carte-reseau.d2` | généré, versionné — **c'est lui qu'on lit en revue** |
| `carte-reseau.svg` | généré, versionné — s'affiche dans la forge |

Les deux fichiers produits sont versionnés : le `.d2` se diffe et se relit, le
`.svg` s'affiche sans rien installer.

## Réserves

**Une dépendance à pve1.** La collecte passe par le seul nœud raccordé au
VLAN 400. Si pve1 est indisponible, la carte ne se régénère pas — la dernière
version versionnée reste consultable.

**Docker pour le rendu seul.** Les autres scripts du dépôt s'astreignent à la
stdlib pour tourner sur n'importe quel nœud. Ici la dépendance est déplacée,
pas supprimée : elle ne pèse que sur la production du SVG.

**Le placement est celui de D2.** Le moteur ELK décide de la disposition. On
gagne des VLAN en conteneurs imbriqués et des arêtes orthogonales sans coder
une seule coordonnée ; on perd le contrôle fin qu'on aurait en dessinant à la
main — notamment le bus de distribution unique sous le reverse proxy, rendu ici
en arêtes séparées.

**La carte ne dit pas si un service est tombé.** Ce n'est pas un outil de
supervision : c'est Zabbix qui surveille l'état ([17-zabbix.md](17-zabbix.md)),
et il découvre déjà VM, conteneurs et stockage par le template
« Proxmox VE by HTTP ». Surveiller et expliquer sont deux besoins distincts.
