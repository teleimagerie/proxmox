# Rendu de carte-reseau.d2 en SVG. Ne contient que D2.
#
# Ce conteneur n'a AUCUN accès à l'infrastructure : la collecte (qui, elle,
# ouvre une session SSH sur pve1) est faite hors conteneur par
# scripts/genere-carte.py. Le conteneur ne voit qu'un fichier texte.
#
# Construction et usage : voir le Makefile (« make carte »).

FROM alpine:3.20

ARG D2_VERSION=0.7.0

RUN apk add --no-cache curl \
 && curl -fsSL "https://github.com/terrastruct/d2/releases/download/v${D2_VERSION}/d2-v${D2_VERSION}-linux-amd64.tar.gz" \
    | tar -xz -C /tmp \
 && mv "/tmp/d2-v${D2_VERSION}/bin/d2" /usr/local/bin/d2 \
 && rm -rf /tmp/d2-v${D2_VERSION} \
 && apk del curl \
 && d2 --version

WORKDIR /travail

# Le dépôt est monté sur /travail ; la commande est fournie par le Makefile.
ENTRYPOINT ["d2"]
