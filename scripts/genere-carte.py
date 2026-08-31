#!/usr/bin/env python3
"""Carte réseau du cluster, régénérée depuis l'infrastructure réelle.

Fusionne deux sources et écrit carte-reseau.d2 à la racine du dépôt :

  - l'INVENTAIRE, découvert par SSH sur pve1 (pvesh get /cluster/resources et
    la config réseau de chaque invité) — ce qui tourne, où, avec quelle IP et
    quel VLAN ;
  - les INTENTIONS, lues dans topologie.yml — zones, rôles, cloisonnements,
    règles. Écrites à la main : aucune API ne dit pourquoi le VLAN 300 est
    fermé au LAN.

Les règles de topologie.yml sont vérifiées à chaque passage. Un écart
n'interrompt pas la génération : la machine fautive est peinte en rouge sur la
carte, et les écarts non rattachables à une machine sont listés en encart. Une
carte qui montre ce qui cloche vaut mieux qu'une carte qui refuse de sortir.

Ce script ne produit QUE le .d2 — le rendu SVG est fait par D2 dans un
conteneur (« make carte »). La séparation est délibérée : le conteneur de rendu
n'a ainsi aucun accès à l'infrastructure de production.

Aucune dépendance hors stdlib + PyYAML, comme les autres scripts du dépôt.

Usage :
  genere-carte.py                  régénère carte-reseau.d2
  genere-carte.py --inventaire     affiche l'inventaire découvert, sans écrire
  genere-carte.py --controle       n'affiche que les écarts aux règles
  genere-carte.py --hote HOTE      autre point d'entrée SSH (défaut : pve1)

Référence : 01-architecture.md (VLAN), 08-opnsense.md (filtrage).
"""
import argparse
import json
import pathlib
import subprocess
import sys

import yaml

RACINE = pathlib.Path(__file__).resolve().parent.parent
INTENTIONS = RACINE / "topologie.yml"
SORTIE = RACINE / "carte-reseau.d2"
HOTE_DEFAUT = "pve1"


# ─── Collecte ────────────────────────────────────────────────────────────────

def ssh(hote, commande):
    """Exécute une commande sur le nœud d'entrée et rend sa sortie."""
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", hote,
         f"LC_ALL=C {commande}"],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ssh {hote}: {r.stderr.strip() or 'échec'}")
    return r.stdout


def collecte(hote):
    """Inventaire des invités : type, nœud, état, IP, VLAN."""
    brut = json.loads(ssh(hote, "pvesh get /cluster/resources --output-format json"))

    noeuds, invites = [], []
    for r in brut:
        if r["type"] == "node":
            noeuds.append({"nom": r["node"], "etat": r["status"]})
        elif r["type"] in ("qemu", "lxc"):
            invites.append({
                "vmid": r["vmid"],
                "nom": r.get("name", f"vm{r['vmid']}"),
                "type": "vm" if r["type"] == "qemu" else "ct",
                "noeud": r["node"],
                "etat": r["status"],
                "ha": r.get("hastate", "") == "started",
            })

    # Config réseau : une requête par invité, sur son nœud porteur.
    for g in invites:
        chemin = "qemu" if g["type"] == "vm" else "lxc"
        cfg = json.loads(ssh(
            hote,
            f"pvesh get /nodes/{g['noeud']}/{chemin}/{g['vmid']}/config "
            f"--output-format json",
        ))
        g["onboot"] = bool(cfg.get("onboot", 0))
        g["ip"], g["tags"] = ip_et_tags(cfg, g["type"])

    invites.sort(key=lambda g: g["vmid"])
    noeuds.sort(key=lambda n: n["nom"])
    return {"noeuds": noeuds, "invites": invites}


def ip_et_tags(cfg, type_):
    """Extrait les IP et les VLAN d'une config d'invité.

    Les deux familles ne stockent pas l'adresse au même endroit : un conteneur
    la porte dans netN (ip=...), une VM dans ipconfigN de cloud-init. Une carte
    sans « tag= » est raccordée au bloc public — c'est le cas du WAN OPNsense,
    et c'est justement ce qu'on veut pouvoir détecter.
    """
    ips, tags = [], []
    for cle, val in sorted(cfg.items()):
        if not cle.startswith("net") or not isinstance(val, str):
            continue
        champs = dict(p.split("=", 1) for p in val.split(",") if "=" in p)
        tags.append(int(champs["tag"]) if "tag" in champs else None)
        if type_ == "ct" and "ip" in champs:
            ips.append(champs["ip"].split("/")[0])

    if type_ == "vm":
        for cle, val in sorted(cfg.items()):
            if cle.startswith("ipconfig") and isinstance(val, str):
                champs = dict(p.split("=", 1) for p in val.split(",") if "=" in p)
                if "ip" in champs:
                    ips.append(champs["ip"].split("/")[0])
    return ips, tags


# ─── Contrôle des règles ─────────────────────────────────────────────────────

def controle(inv, intentions):
    """Confronte l'inventaire aux règles déclarées.

    Rend une liste de (gravité, machine, message). « machine » vaut None quand
    l'écart ne se rattache à aucun nœud de la carte : il ira dans l'encart.
    """
    ecarts = []
    par_nom = {g["nom"]: g for g in inv["invites"]}
    machines = intentions.get("machines", {})

    for regle in intentions.get("regles", []):
        rid = regle["id"]
        gravite = regle.get("gravite", "avertissement")
        exceptions = set(regle.get("exceptions", []))
        porte_sur = regle.get("porte_sur")
        cibles = porte_sur if porte_sur else [
            n for n in par_nom if n not in exceptions
        ]

        for nom in cibles:
            g = par_nom.get(nom)
            if g is None:
                ecarts.append((gravite, None,
                               f"{nom} : visée par « {rid} », absente du cluster"))
                continue

            if rid == "tag-400-obligatoire":
                # Deux contrôles distincts : une machine peut porter à la fois
                # une carte en 400 et une carte sans tag. C'est cette dernière
                # qui expose sur le bloc public — c'est elle qu'on traque.
                if None in g["tags"]:
                    ecarts.append((gravite, nom,
                                   f"net{g['tags'].index(None)} sans tag — bloc public"))
                elif 400 not in g["tags"]:
                    ecarts.append((gravite, nom, "aucune carte en tag=400"))
            elif rid == "onboot" and not g["onboot"]:
                ecarts.append((gravite, nom, "onboot désactivé"))
            elif rid == "ha-pare-feu" and not g["ha"]:
                ecarts.append((gravite, nom, "pas de ressource HA active"))

    # Écart entre l'IP attendue et l'IP réelle.
    for nom, decl in machines.items():
        g = par_nom.get(nom)
        if g is None:
            ecarts.append(("critique", None,
                           f"{nom} : déclarée dans topologie.yml, absente du cluster"))
            continue
        attendue = decl.get("attendu", {}).get("ip")
        if attendue and attendue not in g["ip"]:
            ecarts.append(("avertissement", nom,
                           f"IP attendue {attendue}, relevée "
                           f"{', '.join(g['ip']) or 'aucune'}"))

    # Machines présentes mais non déclarées : la carte ne saura pas les placer.
    for nom in par_nom:
        if nom not in machines:
            ecarts.append(("avertissement", None,
                           f"{nom} : absente de topologie.yml, non placée"))

    ordre = {"critique": 0, "avertissement": 1}
    ecarts.sort(key=lambda e: (ordre.get(e[0], 2), e[1] or "", e[2]))
    return ecarts


# ─── Rendu D2 ────────────────────────────────────────────────────────────────

ENTETE = """\
# Carte réseau du cluster {cluster} — {vm} VM, {ct} conteneurs, {nd} nœuds.
#
# FICHIER GÉNÉRÉ par scripts/genere-carte.py — ne pas éditer à la main.
# L'inventaire vient de l'API Proxmox ; les zones, rôles et cloisonnements
# viennent de topologie.yml. Rendu du SVG : make carte.

direction: down

classes: {{
  zone: {{
    style: {{
      fill: "#EFF2F2"
      stroke: "#B4BFC2"
      font-size: 16
    }}
  }}
  machine: {{
    shape: rectangle
    style: {{
      fill: "#FFFFFF"
      stroke: "#B4BFC2"
      font-size: 14
    }}
  }}
  pivot: {{
    style: {{
      stroke: "#0B7C87"
      stroke-width: 3
    }}
  }}
  parefeu: {{
    style: {{
      fill: "#E2F1F2"
      stroke: "#0B7C87"
      stroke-width: 3
    }}
  }}
  publique: {{
    style: {{
      stroke: "#5F7F2E"
      stroke-width: 2
    }}
  }}
  wan: {{
    style: {{
      stroke: "#8A6A3B"
      stroke-width: 2
    }}
  }}
  externe: {{
    style: {{
      stroke-dash: 4
    }}
  }}
  # Machines en écart aux règles de topologie.yml.
  faute: {{
    style: {{
      fill: "#F7E7E3"
      stroke: "#B0432E"
      stroke-width: 3
      font-color: "#8A2F1E"
    }}
  }}
  alerte: {{
    style: {{
      fill: "#FBF3E7"
      stroke: "#B8862B"
      stroke-width: 2
    }}
  }}
  flux: {{
    style: {{
      stroke: "#0B7C87"
      stroke-width: 2
      font-size: 12
    }}
  }}
  bloque: {{
    style: {{
      stroke: "#B0432E"
      stroke-width: 2
      stroke-dash: 4
      font-size: 12
    }}
  }}
}}
"""


def ident(nom):
    """Identifiant D2 sûr : le point est un séparateur de portée en D2."""
    return nom.replace(".", "_").replace(" ", "_").replace("-", "_")


def noeud_machine(nom, g, decl, faute, indent=""):
    """Un nœud D2 : libellé multiligne, classes, anomalie éventuelle."""
    genre = "VM" if g["type"] == "vm" else "CT"
    # Une VM peut n'avoir aucune IP côté Proxmox : OPNsense configure les
    # siennes en interne, cloud-init n'est pas utilisé. On retombe alors sur
    # l'adresse déclarée dans topologie.yml.
    ip = (g["ip"] or [decl.get("adresse", "adressage interne")])[0]
    titre = f"{nom}\\n{genre} {g['vmid']} · {g['noeud']}\\n{ip}"

    classes = ["machine"]
    if decl.get("pare_feu"):
        classes.append("parefeu")
    elif decl.get("pivot"):
        classes.append("pivot")
    if faute:
        titre += f"\\n⚠ {faute[2]}"
        classes.append("faute" if faute[0] == "critique" else "alerte")

    return f'{indent}{ident(nom)}: "{titre}" {{ class: [{"; ".join(classes)}] }}'


def genere_d2(inv, intentions, ecarts):
    """Compose le .d2. D2 place les nœuds ; ici on décrit la structure."""
    par_nom = {g["nom"]: g for g in inv["invites"]}
    machines = intentions.get("machines", {})
    externes = {x["nom"]: x for x in intentions.get("externes", [])}
    meta = intentions.get("meta", {})

    # Une seule marque par machine : la plus grave, les écarts étant triés.
    faute_de = {}
    for e in ecarts:
        if e[1] and e[1] not in faute_de:
            faute_de[e[1]] = e

    L = [ENTETE.format(
        cluster=meta.get("cluster", ""),
        vm=sum(1 for g in inv["invites"] if g["type"] == "vm"),
        ct=sum(1 for g in inv["invites"] if g["type"] == "ct"),
        nd=len(inv["noeuds"]),
    )]

    # ── Internet ──
    L.append('internet: "Internet\\nclients · nomades · site distant" '
             "{ shape: cloud; class: [machine] }\n")

    # ── Bloc public ──
    pub = [a for a in intentions.get("adresses_publiques", []) if a["role"] != "libre"]
    zpub = next((z for z in intentions.get("zones", []) if z["id"] == "public"), None)
    if zpub and pub:
        L.append(f'public: "{zpub["titre"]} — {zpub["reseau"]}" {{')
        L.append("  class: [zone]")
        L.append("  direction: right")
        for a in pub:
            octet = a["ip"].split(".")[-1]
            cl = "wan" if a["role"] == "wan" else "publique"
            L.append(f'  ip{octet}: ".{octet}\\n{a["libelle"]}\\n{a.get("ports", "")}" '
                     f"{{ class: [machine; {cl}] }}")
        L.append("}\n")
        for a in pub:
            L.append(f'internet -> public.ip{a["ip"].split(".")[-1]} {{ class: [flux] }}')
        L.append("")

    # ── Pare-feu : hors zone, il EST le passage entre le public et le LAN ──
    fw = next((n for n, d in machines.items() if d.get("pare_feu") and n in par_nom), None)
    if fw:
        L.append(noeud_machine(fw, par_nom[fw], machines[fw], faute_de.get(fw)))
        L.append("")
        for a in pub:
            if a["role"] == "wan":
                etiq = "règles wan"
            else:
                etiq = f"rdr → {a.get('cible', '')}".strip(" →")
            L.append(f'public.ip{a["ip"].split(".")[-1]} -> {ident(fw)}: "{etiq}" '
                     f"{{ class: [flux] }}")
        L.append("")

    # ── Zones internes, dans l'ordre déclaré ──
    par_zone = {}
    for nom, d in machines.items():
        if nom in par_nom and not d.get("pare_feu"):
            par_zone.setdefault(d.get("zone", "vlan400"), []).append(nom)
    for x in intentions.get("externes", []):
        if str(x.get("zone", "")).startswith("vlan"):
            par_zone.setdefault(x["zone"], []).append(x["nom"])

    # Une zone visée par un cloisonnement est dessinée même si aucune machine
    # n'y est déclarée : c'est la cible du blocage, elle doit exister.
    visees = {c["vers"] for c in intentions.get("cloisonnements", [])}
    for z in intentions.get("zones", []):
        zid = z["id"]
        if zid == "public" or (zid not in par_zone and zid not in visees):
            continue
        sous = z.get("sous_titre", "")
        L.append(f'{zid}: "{z["titre"]} — {z["reseau"]}'
                 + (f"\\n{sous}" if sous else "") + '" {')
        L.append("  class: [zone]")
        for nom in par_zone.get(zid, []):
            if nom in externes:
                x = externes[nom]
                L.append(f'  {ident(nom)}: "{nom}\\nhors cluster\\n{x["ip"]}" '
                         f"{{ class: [machine; externe] }}")
            else:
                L.append(noeud_machine(nom, par_nom[nom], machines[nom],
                                       faute_de.get(nom), "  "))
        L.append("}\n")

    def zone_de(nom):
        return machines.get(nom, externes.get(nom, {})).get("zone", "vlan400")

    # ── Ce que le pare-feu dessert directement (une VIP pointe dessus) ──
    pivot = next((n for n, d in machines.items() if d.get("pivot") and n in par_nom), None)
    if fw:
        for a in pub:
            cible = a.get("cible")
            if not cible:
                continue
            nom = next((n for n, g in par_nom.items() if cible in g["ip"]), None)
            if nom and not machines.get(nom, {}).get("pare_feu"):
                L.append(f'{ident(fw)} -> {zone_de(nom)}.{ident(nom)}: "→ {cible}" '
                         f"{{ class: [flux] }}")
        L.append("")

    # ── Ce que le reverse proxy dessert ──
    if pivot:
        zp = zone_de(pivot)
        derriere_vip = {a.get("cible") for a in pub if a.get("cible")}
        desservis = [
            n for n in par_zone.get(zp, [])
            if n != pivot
            and not (n in par_nom and set(par_nom[n]["ip"]) & derriere_vip)
        ]
        for n in desservis:
            L.append(f"{zp}.{ident(pivot)} -> {zp}.{ident(n)}: \"proxy_pass\" "
                     f"{{ class: [flux] }}")
        L.append("")

    # ── Cloisonnements : de zone à zone, c'est leur vraie portée ──
    for c in intentions.get("cloisonnements", []):
        if c["depuis"] in par_zone:
            L.append(f'{c["depuis"]} -> {c["vers"]}: "bloqué — {c["libelle"]}" '
                     f"{{ class: [bloque] }}")
    L.append("")

    # ── Hyperviseurs ──
    L.append('noeuds: "Hyperviseurs — ils portent tous les invités ci-dessus" {')
    L.append("  class: [zone]")
    L.append("  direction: right")
    for n in inv["noeuds"]:
        n_inv = sum(1 for g in inv["invites"] if g["noeud"] == n["nom"])
        L.append(f'  {n["nom"]}: "{n["nom"]}\\n{n_inv} invités" {{ class: [machine] }}')
    L.append("}\n")

    # ── Écarts non rattachables à une machine, sinon état de conformité ──
    orphelins = [e for e in ecarts if e[1] is None]
    if orphelins:
        lignes = "\\n".join(f"· {m}" for _, _, m in orphelins[:8])
        if len(orphelins) > 8:
            lignes += f"\\n… et {len(orphelins) - 8} autre(s)"
        L.append(f'ecarts: "{len(orphelins)} écart(s) hors carte\\n{lignes}" '
                 f"{{ class: [machine; faute] }}\n")
    elif not ecarts:
        L.append('etat: "✓ Aucun écart — conforme à topologie.yml" '
                 '{ style.fill: "#EDF3E2"; style.stroke: "#5F7F2E"; '
                 'style.font-color: "#3F5720" }\n')

    for i, av in enumerate(intentions.get("avertissements", [])):
        L.append(f'avertissement_{i}: "⚠ {av["titre"]}" '
                 f'{{ style.fill: "#F7E7E3"; style.stroke: "#B0432E"; '
                 f'style.font-color: "#8A2F1E" }}')

    return "\n".join(L) + "\n"


# ─── Entrée ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--hote", default=HOTE_DEFAUT,
                   help=f"point d'entrée SSH (défaut : {HOTE_DEFAUT})")
    p.add_argument("--inventaire", action="store_true",
                   help="affiche l'inventaire découvert, n'écrit rien")
    p.add_argument("--controle", action="store_true",
                   help="n'affiche que les écarts aux règles")
    args = p.parse_args()

    intentions = yaml.safe_load(INTENTIONS.read_text(encoding="utf-8"))

    try:
        inv = collecte(args.hote)
    except (RuntimeError, subprocess.TimeoutExpired) as err:
        sys.exit(f"collecte impossible via {args.hote} : {err}")

    if args.inventaire:
        for g in inv["invites"]:
            tags = ",".join(str(x) if x else "sans-tag" for x in g["tags"]) or "—"
            print(f"{g['vmid']:>4}  {g['nom']:<12} {g['type']:<3} {g['noeud']:<5} "
                  f"{','.join(g['ip']) or '—':<24} tag={tags}")
        return

    ecarts = controle(inv, intentions)

    if args.controle:
        if not ecarts:
            print("aucun écart")
        for grav, nom, msg in ecarts:
            print(f"{grav:<13} {(nom or '—'):<12} {msg}")
        return

    SORTIE.write_text(genere_d2(inv, intentions, ecarts), encoding="utf-8")
    critiques = sum(1 for x in ecarts if x[0] == "critique")
    print(f"{SORTIE.relative_to(RACINE)} écrit — "
          f"{len(inv['invites'])} invités, {len(ecarts)} écart(s)"
          + (f", dont {critiques} critique(s)" if critiques else "")
          + "\nrendu du SVG : make carte")


if __name__ == "__main__":
    main()
