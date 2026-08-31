# Instructions pour Claude Code

Ce dépôt est de la **documentation d'infrastructure en production**, pas du code
applicatif. Le cluster décrit héberge à terme des données de santé (HDS). Un
document faux y est plus dangereux qu'un document absent : quelqu'un l'appliquera
un jour de panne, à 3 h du matin.

## Le cluster est accessible — s'en servir

```bash
ssh root@pve1.infra.teleimagerie.net
```

**Toute affirmation sur l'état du cluster doit être vérifiée sur le cluster**,
jamais déduite des fichiers du dépôt. `configs/` est une copie qui dérive : elle
a déjà été prise en défaut (le CT 203 manquait dans `ha-resources.cfg`).

Citer la commande et sa sortie dans le document produit. C'est la convention du
dépôt : `05-tests-ha.md` contient des mesures réelles, pas des estimations.

### Lecture seule par défaut

Lire, diagnostiquer, comparer : librement. **Ne jamais écrire sur le cluster sans
demande explicite** — pas de `vzdump`, `pct push`, `systemctl restart`, ni
modification d'ACL ou de firewall. Préparer la commande, l'expliquer, laisser
l'exécution au responsable.

### Pièges de diagnostic déjà rencontrés

- **Les horodatages de `/etc/pve` (pmxcfs) ne sont pas des dates de création.**
  Ils reflètent la dernière synchronisation du système de fichiers de cluster.
  Pour dater un invité : `pct exec <CTID> -- journalctl --list-boots`.
- **Lire un `sshd_config` induit en erreur** — beaucoup de lignes sont commentées
  et les `sshd_config.d/*` priment. Utiliser `sshd -T`, qui donne la
  configuration effective.
- **Les invités sont des ressources HA : ils changent de nœud.** Localiser avec
  `ha-manager status` avant d'agir, ne pas présumer du nœud.
- **`export LC_ALL=C`** avant les commandes Proxmox distantes, sinon Perl noie la
  sortie sous des avertissements de locale.

## Secrets

Le dépôt ne contient aucun secret et ne doit jamais en contenir.

- **`/etc/pve/domains.cfg` ne doit jamais être copié dans `configs/`** : il porte
  le `client-key` OIDC en clair et n'est pas sous `/etc/pve/priv/`.
- Masquer toute valeur sensible relevée sur une machine (`<secret>`), y compris
  dans les blocs de sortie de commande.
- Ne pas interroger la base d'identités de Keycloak (comptes, rôles, empreintes).
  Documenter l'infrastructure ne l'exige pas.

## Langue et style

**Tout est en français** : documents, commentaires de scripts, messages de commit.
Les fichiers de `configs/` sont sans accents (ce sont des configurations lues par
des démons).

Le style du dépôt, à respecter :

- expliquer le **pourquoi**, pas seulement le quoi — c'est ce qui fait la valeur
  de `07-pieges.md` ;
- encadrés `>` pour les pièges et les mises en garde ;
- tableaux pour les inventaires ;
- distinguer ce qui est **vérifié** de ce qui est **déclaré** ou **supposé**
  (convention de `13-tellis.md`) ;
- dater les constats (`relevé le 27/08/2026`), convertir les dates relatives.

## Organisation

Documents numérotés `NN-sujet.md`, référencés dans le sommaire du `README.md` —
**mettre le sommaire à jour** en ajoutant un document.

`configs/` contient des copies du réel. Un fichier décrivant un état **non encore
appliqué** doit le dire dans son en-tête (voir `sshd-10-hardening-ct.conf`).

## Commits

Sujet à l'impératif en français, corps en puces par fichier touché, expliquant le
pourquoi. Voir `git log` pour le modèle.

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

Ne commiter que sur demande, et jamais les captures d'écran ou fichiers de travail.

## Honnêteté des constats

Ne pas conclure au-delà de ce que la preuve permet. « Aucun instantané de
sauvegarde » signifie qu'il n'y en a aucun — pas que la sauvegarde est en panne :
le conteneur pouvait ne pas exister au dernier passage. Vérifier l'explication
banale avant d'annoncer un incident.

Quand un constat antérieur du dépôt se révèle faux, le corriger explicitement
dans le document concerné plutôt que de le réécrire en silence : la trace de
l'erreur a une valeur.
