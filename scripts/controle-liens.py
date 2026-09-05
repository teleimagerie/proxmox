#!/usr/bin/env python3
"""Contrôle des liens internes des fiches Markdown du dépôt.

Vérifie que chaque lien `[texte](fiche.md#ancre)` ou `[texte](#ancre)` vise un
titre qui existe réellement, et signale le titre le plus proche quand ce n'est
pas le cas. Ne modifie rien ; sort en code 1 s'il reste un lien mort, pour
servir de contrôle avant commit (`make liens`).

Pourquoi ce script existe : un lien mort ne casse rien à l'exécution, il envoie
seulement le lecteur en haut du fichier — il passe donc inaperçu pendant des
semaines. Le contrôle du 05/09/2026 en a trouvé 13 d'un coup, dont 9 dus à des
titres renommés après coup (voir 07-pieges.md, piège n° 38).

La règle de fabrication des ancres, celle de GitHub, tient en trois points et
c'est le troisième qui surprend :
  1. le titre est passé en minuscules ;
  2. tout ce qui n'est ni lettre, ni chiffre, ni « _ », ni « - », ni espace est
     SUPPRIMÉ (guillemets, tirets cadratins, emojis, points, parenthèses…) ;
  3. chaque espace restant devient UN tiret — les suites d'espaces ne sont pas
     fusionnées. Une ponctuation retirée entre deux espaces laisse donc DEUX
     tirets, et un emoji en tête de titre n'en laisse aucun.

Usage : controle-liens.py [--silencieux]
"""
import difflib
import glob
import os
import re
import sys

LIEN = re.compile(r'\[([^\]]*)\]\(([0-9A-Za-z._-]+\.md)?(#[^)]+)\)')
CODE = re.compile(r'`[^`]*`')


def ancre(titre):
    """L'ancre que GitHub fabrique pour ce texte de titre."""
    t = titre.strip().lower()
    t = re.sub(r'[^\w\s-]', '', t, flags=re.UNICODE)
    return t.strip().replace(' ', '-')


def sans_code(lignes):
    """Neutralise ce qui est du code, pas du lien : les blocs délimités par ```
    et les passages entre accents graves. Une fiche cite légitimement un lien
    cassé en exemple (le piège n° 38 le fait) — le compter serait un faux
    positif. Les caractères sont remplacés par des espaces, pas supprimés, pour
    que les numéros de ligne et de colonne restent justes."""
    dans_bloc = False
    for ligne in lignes:
        if ligne.lstrip().startswith('```'):
            dans_bloc = not dans_bloc
            yield ''
            continue
        yield '' if dans_bloc else CODE.sub(lambda m: ' ' * len(m.group(0)), ligne)


def titres(fichier):
    """{ancre: (texte du titre, ligne)} — le premier titre gagne, comme GitHub
    (les doublons y reçoivent un suffixe -1, -2 ; le dépôt n'en a pas)."""
    trouves = {}
    with open(fichier, encoding='utf-8') as f:
        for n, ligne in enumerate(f, 1):
            if ligne.startswith('#'):
                texte = ligne.lstrip('#').strip()
                trouves.setdefault(ancre(texte), (texte, n))
    return trouves


def main():
    silencieux = '--silencieux' in sys.argv
    fiches = sorted(glob.glob('*.md'))
    if not fiches:
        sys.exit('aucune fiche .md dans le dossier courant')
    connus = {f: titres(f) for f in fiches}

    morts, liens = [], 0
    for f in fiches:
        with open(f, encoding='utf-8') as fh:
            for n, ligne in enumerate(sans_code(fh), 1):
                for m in LIEN.finditer(ligne):
                    cible = m.group(2) or f
                    nom = m.group(3)[1:]
                    if cible not in connus:
                        # lien vers un fichier hors du dossier (configs/, scripts/)
                        if not os.path.exists(cible):
                            morts.append((f, n, m.group(1), cible, nom, None,
                                          'fichier introuvable'))
                        continue
                    liens += 1
                    if nom not in connus[cible]:
                        proches = difflib.get_close_matches(
                            nom, list(connus[cible]), n=1, cutoff=0.5)
                        morts.append((f, n, m.group(1), cible, nom,
                                      proches[0] if proches else None, None))

    if not silencieux:
        for f, n, texte, cible, nom, proche, note in morts:
            print(f"{f}:{n}  [{texte[:40]}]({cible}#{nom})")
            if note:
                print(f"    {note}")
            elif proche:
                titre, ln = connus[cible][proche]
                print(f"    titre le plus proche : #{proche}")
                print(f"    soit « {titre} » ({cible}:{ln})")
            else:
                print(f"    aucun titre approchant dans {cible}")
            print()

    total = f"{liens} liens internes contrôlés dans {len(fiches)} fiches"
    if morts:
        print(f"{total} — {len(morts)} MORT(S)")
        return 1
    print(f"{total} — aucun lien mort")
    return 0


if __name__ == '__main__':
    sys.exit(main())
