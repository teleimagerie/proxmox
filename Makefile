# Carte réseau du cluster — deux étapes délibérément séparées.
#
#   1. collecte   hors conteneur, en Python : ouvre une session SSH sur pve1,
#                 interroge l'API Proxmox, confronte aux règles de
#                 topologie.yml, écrit carte-reseau.d2 ;
#   2. rendu      dans un conteneur ne portant que D2, sans aucun accès à
#                 l'infrastructure : lit le .d2, écrit carte-reseau.svg.
#
# Les deux fichiers produits sont versionnés : le .d2 se relit et se diffe en
# revue, le .svg s'affiche directement dans la forge sans rien installer.

IMAGE      := tim-carte-d2
D2_VERSION := 0.7.0
SOURCE     := carte-reseau.d2
CIBLE      := carte-reseau.svg
HOTE       ?= pve1

.PHONY: carte collecte rendu image controle inventaire propre aide

# « make » nu affiche l'aide : les autres cibles interrogent la production ou
# réécrivent des fichiers versionnés, ce n'est pas ce qu'on veut déclencher
# par accident. Déclaré ici plutôt que par l'ordre des règles, pour qu'un
# déplacement de bloc ne change pas le comportement.
.DEFAULT_GOAL := aide

## carte        régénère le .d2 depuis l'infra, puis le SVG
carte: collecte rendu

## collecte     interroge l'API Proxmox et écrit carte-reseau.d2
collecte:
	python3 scripts/genere-carte.py --hote $(HOTE)

## rendu        convertit carte-reseau.d2 en SVG, dans le conteneur
rendu: image
	docker run --rm --network none \
	  -v "$(CURDIR):/travail" \
	  -u "$(shell id -u):$(shell id -g)" \
	  $(IMAGE) --layout elk --pad 24 $(SOURCE) $(CIBLE)
	@chmod 644 $(CIBLE)
	@echo "$(CIBLE) écrit"

## image        construit l'image de rendu si elle manque
image:
	@docker image inspect $(IMAGE) >/dev/null 2>&1 \
	  || docker build --build-arg D2_VERSION=$(D2_VERSION) -t $(IMAGE) .

## controle     liste les écarts aux règles, sans rien écrire
controle:
	python3 scripts/genere-carte.py --hote $(HOTE) --controle

## inventaire   affiche l'inventaire découvert, sans rien écrire
inventaire:
	python3 scripts/genere-carte.py --hote $(HOTE) --inventaire

## propre       supprime l'image de rendu
propre:
	-docker image rm $(IMAGE)

## aide         cette aide
aide:
	@echo
	@echo "  Carte réseau du cluster — voir 19-carte-reseau.md"
	@echo
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  make /'
	@echo
	@echo "  Seul topologie.yml s'édite à la main ; le .d2 et le .svg sont générés."
	@echo "  La collecte passe par $(HOTE) — « make carte HOTE=pve2 » pour en changer."
	@echo
