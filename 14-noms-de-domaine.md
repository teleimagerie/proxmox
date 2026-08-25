# Noms de domaine — zones, registrars et résolution

> ✅ vérifié/mesuré · 📋 déclaré (non contrôlé sur machine) · ⚠️ à vérifier / inconnu

Le compte OVH qui porte le DNS du cluster héberge **six zones publiques**, pas
une : jusqu'ici la documentation ne parlait que de `teleimagerie.net`, et
d'`isoteam.mn` en creux (via les certificats syngo). Ce fichier est la
référence des zones elles-mêmes — registrar, échéances, serveurs autoritaires —
et de tout ce qu'aucun autre fichier ne possède : mail, web, noms de la
production d'imagerie, reverse DNS, résolution interne.

Relevé du 25/08/2026 : serveurs autoritaires interrogés directement (jamais le
résolveur local — [piège n°30](07-pieges.md#30-le-fichier-hosts-windows-fausse-tout-diagnostic-dns-sous-wsl2)),
zones exportées via l'API OVH **en lecture seule** depuis pve1, registrars lus
en RDAP. Les exports bruts sont archivés tels quels dans `configs/zone-*`.

> **Règle de partage** (même esprit que [12-architecture-hds.md](12-architecture-hds.md)) :
> ce fichier ne recopie jamais l'état réel d'un nom possédé par un autre
> fichier — ni IP, ni TTL, ni échéance de certificat : il renvoie.
> [09-proxy-tim.md](09-proxy-tim.md) reste la vérité des cinq noms du proxy,
> [08-opnsense.md](08-opnsense.md#bloc-public-ovh-571303412029) celle du bloc
> public, [11-headscale.md](11-headscale.md) celle de headscale et du MagicDNS,
> [04-securite.md](04-securite.md#tls) celle de la clé API et des secrets.

---

## Les zones

| Zone | Usages constatés (25/08/2026) | Export |
|---|---|---|
| `teleimagerie.net` | cluster, proxy, production imagerie, mail Google Workspace, web, outils (crm, zabbix, voip, odoo…) | [configs/zone-teleimagerie.net](configs/zone-teleimagerie.net) |
| `isoteam.mn` | Syngo Via, accès TELLIS (`sftp`, `vpn-angers`), mail Microsoft 365, SharePoint, site Wix | [configs/zone-isoteam.mn](configs/zone-isoteam.mn) |
| `isoteam.healthcare` | redirection + `gestion` vers TELLIS | [configs/zone-isoteam.healthcare](configs/zone-isoteam.healthcare) |
| `teleimage.net` | domaine-alias : redirige vers `www.teleimagerie.net`, reçoit du mail Google | [configs/zone-teleimage.net](configs/zone-teleimage.net) |
| `teleimagerie.com` | parking (déposé le 24/03/2026 pour dix ans) | [configs/zone-teleimagerie.com](configs/zone-teleimagerie.com) |
| `teleimagerie.fr` | redirection — **cassée**, voir [Anomalies](#anomalies-relevées-25082026) | [configs/zone-teleimagerie.fr](configs/zone-teleimagerie.fr) |
| `tim.lan` | interne au cluster, `/etc/hosts` seulement — voir [Résolution interne](#résolution-interne) | [configs/hosts](configs/hosts) |
| `ts.teleimagerie.net` | MagicDNS du tailnet (`<machine>.ts.teleimagerie.net`) | → [11-headscale.md](11-headscale.md#architecture) |

`infra.teleimagerie.net` n'est **pas** une zone déléguée : c'est une simple
convention de nommage à l'intérieur de la zone parente. De même `ts.` n'existe
que pour les clients du tailnet (résolveur `100.100.100.100`), il n'est pas
publié sur Internet.

## Registrars et échéances

Source : RDAP (Verisign pour `.net`, registre pour `.com`/`.fr`/`.healthcare`),
relevé du 25/08/2026. Les statuts `clientTransferProhibited` /
`clientDeleteProhibited` (verrous registrar, normaux) sont posés partout.

| Domaine | Registrar | Créé | Expire | DNSSEC |
|---|---|---|---|---|
| `teleimagerie.net` | OVH sas | 28/02/2017 | **28/02/2027** | non |
| `isoteam.mn` | ⚠️ inconnu | ⚠️ | ⚠️ | non |
| `isoteam.healthcare` | OVH SAS | 20/12/2023 | **20/12/2026** ⚠️ | non |
| `teleimage.net` | OVH sas | 02/03/2020 | 02/03/2027 | non |
| `teleimagerie.com` | OVH sas | 24/03/2026 | 24/03/2036 | **oui** ✅ |
| `teleimagerie.fr` | OVH | 23/07/2024 | 23/07/2027 | non |

Le `.fr` était en période « auto renew » au moment du relevé (renouvelé le
23/07/2026) — signe que le renouvellement automatique est actif au moins pour
lui. Pour les autres, rien ne le prouve depuis l'extérieur ⚠️. Le `.mn` est
invisible en RDAP comme en whois public : registrar et expiration ne se lisent
que dans l'espace client ⚠️. L'API du cluster ne peut pas répondre non plus :
`GET /domain/*/serviceInfos` renvoie 403, la clé étant limitée à
`/domain/zone/*`.

> **L'expiration d'un domaine tue tout d'un coup** : les noms du proxy, le
> tailnet (le `server_url` de headscale est sous `teleimagerie.net`), les six
> mécanismes ACME, le mail de l'entreprise et les noms de la production
> imagerie. La plus proche est **`isoteam.healthcare` au 20/12/2026** ; qui
> reçoit les rappels de renouvellement OVH n'est pas documenté ⚠️.

## Serveurs autoritaires

| Zone | NS autoritaires | Serial SOA (25/08/2026) |
|---|---|---|
| `teleimagerie.net` | `ns17.ovh.net`, `dns17.ovh.net` | 2086787425 |
| `isoteam.mn` | `ns102.ovh.net`, `dns102.ovh.net` | 2086618585 |
| `isoteam.healthcare` | `ns102.ovh.net`, `dns102.ovh.net` | 2024011001 |
| `teleimage.net` | `ns20.ovh.net`, `dns20.ovh.net` | 2020030210 |
| `teleimagerie.com` | `ns14.ovh.net`, `dns14.ovh.net` | 2085951314 |
| `teleimagerie.fr` | `ns104.ovh.net`, `dns104.ovh.net` | 2026032400 |

**Chaque zone a sa propre paire de NS OVH** (seules `isoteam.mn` et
`isoteam.healthcare` partagent la leur). Mélanger les paires est exactement
l'erreur du [piège n°10](07-pieges.md#10-dig-interrogé-sur-le-mauvais-serveur-de-noms) —
et celle qui s'était glissée dans le constat de bascule de 09 (corrigée le
25/08/2026). Le contact SOA est `tech.ovh.net` partout : aucune alerte
technique n'arrive chez nous par ce canal. Les serials figés de
`isoteam.healthcare` (2024) et `teleimage.net` (2020) confirment des zones
dormantes.

---

## Inventaire des noms publiés

Relevé exhaustif du 25/08/2026 (export API des zones — `dig` ne sait pas
énumérer). TTL 3600 sauf mention. Les cibles marquées 📋 sont des
recoupements de noms, pas des vérifications sur machine.

### `teleimagerie.net` — périmètre cluster (renvois)

| Nom | Rôle | L'état réel se lit dans |
|---|---|---|
| `pve{1,2,3}.infra` | administration des nœuds | [README](README.md#les-3-serveurs), [04](04-securite.md#tls) |
| `headscale` | plan de contrôle du tailnet | [11-headscale.md](11-headscale.md) |
| `pacs-secours`, `syngo`, `syngo-via` | proxy — bascule DNS pas faite | [09-proxy-tim.md](09-proxy-tim.md#la-bascule-dns-nest-pas-faite--le-proxy-ne-reçoit-pas-la-production) |

### `teleimagerie.net` — production imagerie

Deux adresses reviennent en double A sur les noms de production :
`37.61.243.245` (voisine du WAN pfSense TELLIS `.246`, sans PTR) et
`77.158.128.112` (PTR chez SFR) — vraisemblablement les deux accès Internet
du site TELLIS 📋, à confirmer avec [13-tellis.md](13-tellis.md).

| Nom | Cible(s) | Rôle |
|---|---|---|
| `pacs01`, `pacs02` | `37.61.243.245` (TTL 60) + `77.158.128.112` | PACS de production 📋 TELLIS |
| `prod01` | `37.61.243.245` + `77.158.128.112` (TTL 60) | VM `prod01` du DC TELLIS 📋 |
| `pacs03` | `188.165.77.137` | serveur OVH — le backend du PACS de secours ✅ ([09](09-proxy-tim.md#ce-qui-est-publié)) |
| `pacs04` | `162.19.25.107` | ⚠️ (IP partagée avec `api`/`www1`) |
| `secours-tellis` | `37.61.243.245` | ⚠️ |
| `dev.gestion` | `37.61.243.245` + `77.158.128.112` | environnement de dev côté TELLIS 📋 |
| `dlmbox01` | **cassé** | voir [Anomalies](#anomalies-relevées-25082026) |

### `teleimagerie.net` — gestion et outils

| Nom | Cible(s) | Rôle |
|---|---|---|
| `app`, `gestion`, `d69eeb3e` | `51.210.24.59` | application de gestion 📋 (`d69eeb3e` ⚠️) |
| `gestion2` | `46.105.57.169` | ⚠️ |
| `crm`, `www.crm`, `testwp` | `51.83.79.119` | CRM (les tickets `support` y redirigent) 📋 |
| `auth` | `146.59.233.102` | ⚠️ |
| `api`, `api1`, `www1`, `test01` | `162.19.25.107` (+ AAAA) | API 📋 |
| `e-learning`, `elearning` | `51.210.149.58` | e-learning 📋 |
| `odoo` | `91.134.75.199` | ERP Odoo 📋 |
| `zabbix` | `51.178.36.192` | supervision 📋 — jamais citée dans [06 §4](06-reste-a-faire.md#4-supervision) ⚠️ |
| `voip` | `51.38.33.236` | téléphonie 📋 |
| `bastion` | `51.38.189.223` | bastion d'accès 📋 |
| `sms` / `smsnotifier` | `51.75.30.101` / CNAME `vps589173.ovh.net` | envoi de SMS 📋 |
| `hds-1-tim`, `rappro-cmsi` | `46.105.64.17` | ⚠️ |
| `timfact`, `www3` | `77.158.128.112` | facturation ? ⚠️ (via l'accès SFR TELLIS) |
| `bureau` | `82.127.36.38` + AAAA Orange (TTL 60) | accès du bureau 📋 |
| `*.staging`, `app-staging`, `gestion-staging` | `79.137.100.185` | pré-production 📋 |
| `test-01`…`test-09` | `37.59.114.69` | ⚠️ |

### `teleimagerie.net` — web, redirections et mail

- **Web** : l'apex (`213.186.33.5`, redirection OVH `"1|www.teleimagerie.net"`)
  mène à `www` → `46.105.57.169` (hébergement mutualisé OVH, opérateur du site
  ⚠️). `facturation` et `gru` redirigent vers `https://app.teleimagerie.net`,
  `support`/`www.support` vers le guichet de tickets du CRM, `welcome` est un
  CNAME `ghs.googlehosted.com` (Google Sites 📋). `mariage`/`www.mariage` →
  `46.105.57.169` ⚠️.
- **Mail** : MX **Google Workspace** sur l'apex (et sur `www`), SPF
  `"v=spf1 include:mx.ovh.com include:_spf.google.com include:spf.mailjet.com ~all"`,
  DKIM publiés pour Google (`google._domainkey`), Mailjet et le mail mutualisé
  OVH (`ovhmo3202129-selector{1,2}`). Les sous-domaines `protocoles` et
  `support` ont leurs **propres MX chez OVH** (adresses de service 📋).
  `imap`/`smtp`/`pop3` sont des CNAME de confort vers Gmail.
- **Divers** : `_4e7786b6….` CNAME de validation Sectigo/Comodo — vestige d'un
  certificat commercial ⚠️ ; TXT `hamidou.at.protocoles` ⚠️.

### `isoteam.mn`

| Nom | Cible(s) | Rôle |
|---|---|---|
| `syngo-via` | → état réel dans [09](09-proxy-tim.md#la-bascule-dns-nest-pas-faite--le-proxy-ne-reçoit-pas-la-production) | portail + RemoteApp Syngo Via |
| `syngo` | **aucun enregistrement** | incohérence connue — [09](09-proxy-tim.md#la-bascule-dns-nest-pas-faite--le-proxy-ne-reçoit-pas-la-production) |
| `sftp`, `vpn-angers` | `37.61.243.246` | droit sur le WAN pfSense TELLIS 📋 → [13](13-tellis.md) |
| `venus` | `77.158.128.112` + `37.61.243.245` | RIS VENUS du DC TELLIS 📋 → [13](13-tellis.md) |
| `app`, `gestion` | `146.59.233.170` | gestion 📋 |
| `*.staging`, `app-staging`, `gestion-staging`, `preprod-app`, `preprod-gestion` | `79.137.100.184` | pré-production 📋 |
| `preprod-facturation` | `46.105.64.17` | ⚠️ (même IP que `hds-1-tim`) |
| `espace`, `www.espace` | redirection OVH → `https://telimet.sharepoint.com/` | SharePoint « telimet » 📋 |
| `www` | CNAME `pointing.wixdns.net` | site vitrine Wix |

Mail : MX **Microsoft 365** (`isoteam-mn.mail.protection.outlook.com`),
`autodiscover` CNAME `autodiscover.outlook.com`, DKIM Mailjet, TXT de
vérification Microsoft et Google. SPF :
`"v=spf1 a mx ptr ip4:37.61.243.245 ip4:77.158.128.112 include:spf.protection.outlook.com include:spf.mailjet.com ~all"`
— du courrier est donc censé sortir **directement des accès TELLIS** 📋
(mécanisme `ptr` déprécié, voir [Anomalies](#anomalies-relevées-25082026)).

### Les trois zones dormantes

- **`isoteam.healthcare`** : apex et `www` en redirection OVH ; `gestion` →
  `77.158.128.112` + `37.61.243.245` (TELLIS) ; MX mutualisé OVH, SPF
  `-all` strict.
- **`teleimage.net`** : apex en redirection vers `www.teleimagerie.net` ; MX
  **Google** sur apex et `www` — mais SPF limité à `mx.ovh.com` et CNAME
  clients (`imap`, `smtp`…) vers `ssl0.ovh.net`, voir Anomalies.
- **`teleimagerie.com`** : redirection vers `www.teleimagerie.com` (page
  « welcome » OVH) ; MX mutualisé OVH, SPF `-all`. Seule zone signée DNSSEC.

---

## Anomalies relevées (25/08/2026)

1. **`dlmbox01` est cassé** ✅ : le FQDN complet a été saisi dans le champ
   sous-domaine — l'enregistrement réel est
   `dlmbox01.teleimagerie.net.teleimagerie.net` → `77.158.128.112`, et le nom
   voulu `dlmbox01.teleimagerie.net` ne résout pas.
2. **`syngo.isoteam.mn` n'existe pas** alors que le proxy le sert et qu'un
   certificat le couvre — connu, à créer le jour de la bascule
   ([09](09-proxy-tim.md#checklist-pour-le-jour-de-la-bascule)).
3. **La redirection `.fr` ne mène nulle part** ✅ : l'apex redirige vers
   `www.teleimagerie.fr`, or `www` ne porte qu'un DNAME vers
   `teleimagerie.net` — qui ne s'applique qu'aux noms *en dessous* de `www`,
   pas à `www` lui-même. Aucune adresse : le domaine est inutilisable tel quel.
4. **`teleimage.net` : réception Google, configuration d'envoi OVH** — MX
   Google mais SPF limité à `mx.ovh.com` : un mail expédié en
   `@teleimage.net` depuis Google échoue au contrôle SPF ⚠️.
5. **`isoteam.mn` : vestiges OVH sous MX Microsoft** — les SRV
   `_autodiscover`/`_imaps`/`_submission` pointent encore sur `ssl0.ovh.net`,
   et le SPF utilise le mécanisme `ptr`, déprécié et ignoré par certains
   destinataires ⚠️.
6. **Aucune zone n'a de DMARC ni de CAA** ; DNSSEC seulement sur
   `teleimagerie.com`. Sans DMARC, l'usurpation d'adresse `@teleimagerie.net`
   ou `@isoteam.mn` n'est pas freinée — décision à prendre ⚠️.

---

## Reverse DNS

Relevé du 25/08/2026 (`dig -x @1.1.1.1`) :

| IP | PTR | Commentaire |
|---|---|---|
| `91.134.84.222`, `51.68.240.48`, `51.68.240.191` | `ns….ip-91-134-84.eu` / `ns….ip-51-68-240.eu` | défauts OVH des nœuds, jamais personnalisés |
| `57.130.34.121`–`123` | `ip12N.ip-57-130-34.eu` | défauts OVH du bloc public |
| `51.75.203.20` | `vps-f89a8456.vps.ovh.net` | l'ancien VPS |
| `188.165.77.137` | `ns3062628.ip-188-165-77.eu` | backend PACS (`pacs03`) |
| `77.158.128.112` | `112.128.158.77.rev.sfr.net` | accès **SFR** — TELLIS 📋 |
| `37.61.243.245`, `37.61.243.246` | *(aucun)* | TELLIS, pas de reverse |

Personne ne gère les PTR aujourd'hui. Le seul incident connu est le PTR IPv6
des nœuds, non conforme aux exigences Gmail et **contourné** (Postfix forcé en
IPv4) plutôt que corrigé —
[piège n°6](07-pieges.md#6-postfix--gmail-rejette-lipv6). À reprendre si du
mail doit un jour sortir en IPv6 ou depuis TELLIS ⚠️.

## ACME : ce qui dépend de quelle zone

Les échéances et le détail des renouvellements restent chez leurs
propriétaires ; ici, seulement la dépendance DNS de chacun.

| Certificat | Challenge | Dépendance DNS | Détail |
|---|---|---|---|
| `pve{1,2,3}.infra` | DNS-01 (plugin ovh) | écrit des TXT dans `teleimagerie.net` | [04](04-securite.md#tls) |
| `syngo-teleimagerie` | DNS-01 (acme.sh sur pve1) | TXT dans `teleimagerie.net` | [09](09-proxy-tim.md#certificats) |
| `syngo-isoteam` | DNS-01 (acme.sh sur pve1) | TXT dans **`isoteam.mn`** | [09](09-proxy-tim.md#certificats) |
| `pacs-secours` (certbot CT 201) | HTTP-01 | l'A doit pointer sur le proxy — bloqué tant que la bascule n'est pas faite (avant le **17/10/2026**) | [09](09-proxy-tim.md#checklist-pour-le-jour-de-la-bascule) |
| TSplus (Let's Encrypt intégré) | HTTP-01 | l'A de `syngo-via.*` + le relais ACME port 80 après bascule | [09](09-proxy-tim.md#certificats) |
| headscale (certmagic) | TLS-ALPN-01 | l'A de `headscale` | [11](11-headscale.md) |

> **La clé API du renouvellement écrit dans les six zones.**
> `GET /auth/currentCredential` (25/08/2026) : règles
> `GET|PUT|POST|DELETE /domain/zone/*`, sans restriction de zone. Une erreur
> de script DNS peut donc toucher le mail ou le web de l'entreprise, pas
> seulement les certificats. La règle maison reste : cette clé ne vit que sur
> pve1, jamais sur une machine exposée —
> [04-securite.md](04-securite.md#secrets--où-ils-vivent).

## Résolution interne

- **`tim.lan`** : les FQDN du `/etc/hosts` des nœuds (`pveN.tim.lan`) — un
  domaine qui n'existe **que là**, aucun serveur DNS ne le sert. C'est lui qui
  force le trafic inter-nœuds sur le vRack
  ([01-architecture.md](01-architecture.md#résolution-de-noms)). Un
  `ping pve1.tim.lan` depuis un CT échoue : normal.
- **Résolveur des nœuds** : pve1 utilise `213.186.33.99` (cache DNS OVH),
  `search ip-91-134-84.eu` (relevé du 25/08/2026). pve2/pve3 et les CT 201/202
  ⚠️ non relevés — vraisemblablement identiques 📋.
- **Tailnet** : MagicDNS sur `100.100.100.100`, `override_local_dns: false`
  (les passerelles gardent le DNS de leur site) —
  [11-headscale.md](11-headscale.md#architecture).
- **Postes de test Windows/WSL2** : le fichier hosts Windows fausse même
  `dig` — [piège n°30](07-pieges.md#30-le-fichier-hosts-windows-fausse-tout-diagnostic-dns-sous-wsl2).

## Diagnostic

```bash
# les NS d'une zone, puis interroger l'autoritaire (jamais le résolveur local)
dig +short NS teleimagerie.net
dig @ns17.ovh.net +noall +answer pacs-secours.teleimagerie.net A

# ce que la machine résout réellement (fichiers hosts compris)
getent ahostsv4 syngo-via.teleimagerie.net

# expiration d'un domaine sans client whois (RDAP)
curl -s https://rdap.verisign.com/net/v1/domain/teleimagerie.net \
  | python3 -m json.tool | grep -B1 -A1 expiration

# inventaire exhaustif d'une zone — dig ne sait pas énumérer :
# API OVH depuis pve1 (identifiants /root/.secrets/ovh.ini),
# GET /domain/zone/<zone>/export ; mécanique de signature dans
# scripts/ovh-dns.py — NE PAS l'exécuter tel quel : il CRÉE des enregistrements
```

## Où lire le détail

| Sujet | Fichier |
|---|---|
| État DNS réel des noms du proxy, bascule, certificats syngo | [09-proxy-tim.md](09-proxy-tim.md) |
| Bloc public `57.130.34.120/29`, IP libres | [08-opnsense.md](08-opnsense.md#bloc-public-ovh-571303412029) |
| Clé API OVH, ACME du cluster, secrets | [04-securite.md](04-securite.md#tls) |
| headscale, MagicDNS, tailnet | [11-headscale.md](11-headscale.md) |
| Cibles d'architecture des noms | [12-architecture-hds.md](12-architecture-hds.md) |
| Pièges DNS n°2, 6, 10, 30 | [07-pieges.md](07-pieges.md) |
| Le DC TELLIS (cibles `37.61.243.24x`, VENUS, nginx `.61`) | [13-tellis.md](13-tellis.md) |
| Échéance de bascule (17/10/2026) | [06-reste-a-faire.md](06-reste-a-faire.md#2-bascule-dns-vers-proxy-tim) |

## À vérifier / à documenter ⚠️

- [ ] **Renouvellement automatique des six domaines** et destinataire des
      rappels OVH — en particulier `isoteam.healthcare`, qui expire le
      **20/12/2026**
- [ ] Registrar et expiration d'`isoteam.mn` (invisibles publiquement —
      espace client OVH)
- [ ] Titulaire du compte OVH et contacts admin/tech des domaines
- [ ] Corriger `dlmbox01` (recréer avec le bon sous-domaine) ; décider du sort
      de la redirection `.fr`
- [ ] Rôle réel des noms marqués ⚠️ (`d69eeb3e`, `auth`, `gestion2`,
      `secours-tellis`, `pacs04`, `hds-1-tim`, `rappro-cmsi`, `timfact`,
      `test-01`…`09`, `mariage`, `hamidou.at.protocoles`, `_4e7786b6…`)
- [ ] Décisions DMARC et CAA (aucune zone n'en a) ; étendre DNSSEC au-delà de
      `teleimagerie.com` ?
- [ ] SPF de `teleimage.net` vs MX Google ; SRV OVH résiduels d'`isoteam.mn`
- [ ] PTR absents des accès TELLIS (`37.61.243.245`/`.246`)
- [ ] Résolveurs de pve2/pve3 et des CT 201/202
- [ ] Noms servis par le nginx `192.168.101.61` du DC TELLIS
      ([checklist de 13](13-tellis.md))
