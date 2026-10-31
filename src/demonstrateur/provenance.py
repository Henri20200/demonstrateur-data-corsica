"""Empreinte de traçabilité : SHA-256 canonique + vérification contre le manifeste.

Le SHA-256 est LE cœur de la traçabilité du dépôt. Pour la plupart des sources il
porte sur les octets bruts. Mais certaines API (ENTSO-E) réestampillent à CHAQUE
requête des champs d'enveloppe — `mRID` (identifiant de document) et
`createdDateTime` (instant du téléchargement) — SANS que la donnée change. Hasher
les octets bruts lierait alors l'empreinte au transport : non reproductible, et ne
certifiant pas la donnée. Pour ces sources, `empreinte_ignore_xml` liste les balises
dont le contenu est neutralisé avant le calcul — l'empreinte certifie la donnée, pas
l'instant de collecte. Deux réponses portant la même génération donnent la même
empreinte, quelle que soit l'enveloppe.

Même défaut, autre enveloppe : un `.gz` régénéré par son producteur. L'en-tête gzip
porte l'instant de compression, si bien qu'un contenu identique recompressé change
d'octets. `empreinte_decompressee: true` fait porter le SHA-256 sur le contenu
décompressé — le même que donne `zcat fichier | sha256sum`.

Ce module est le point unique où l'empreinte est calculée : fetch l'utilise pour
CERTIFIER (au téléchargement) et VÉRIFIER (une source figée, à chaque run) ; prepare
l'utilise pour REFUSER de construire depuis un brut non certifié.
"""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

# defusedxml : cette empreinte est calculée sur un fichier tout juste téléchargé, donc
# sur des octets non fiables (S-04). `tostring` y est le `tostring` de la stdlib, et
# l'empreinte canonique reste bit pour bit la même — vérifié sur les 20 sources ENTSO-E.
import defusedxml.ElementTree as ET

_BLOC = 1 << 20  # lecture par blocs de 1 Mo (empreinte brute en streaming)

# Clés de sources.yaml qui décident COMMENT l'empreinte se calcule. Recopiées dans
# l'entrée de manifeste, elles disent sous quelle règle son `sha256` a été certifié.
_CLES_REGLE = ("empreinte_ignore_xml", "empreinte_decompressee")


class EmpreinteDivergente(ValueError):
    """Le fichier local ne correspond plus à l'empreinte certifiée du manifeste."""


def empreinte(chemin: Path, meta: dict) -> str:
    """SHA-256 de traçabilité du fichier.

    Si `meta` déclare `empreinte_ignore_xml` (chemins XML précis depuis la racine),
    calcule l'empreinte sur une forme CANONIQUE du XML (contenu de ces balises neutralisé)
    — reproductible d'un téléchargement à l'autre. Si `meta` déclare
    `empreinte_decompressee`, empreinte du contenu décompressé d'un gzip. Sinon, empreinte
    des octets bruts, en streaming.

    `meta` peut être l'entrée de sources.yaml (côté fetch) ou l'entrée de manifeste
    (côté prepare) : les deux portent la règle (cf. `regle`), ce qui évite à prepare
    de relire sources.yaml.
    """
    ignore = meta.get("empreinte_ignore_xml")
    if ignore:
        return _empreinte_canonique_xml(chemin, ignore)
    ouvrir = gzip.open if meta.get("empreinte_decompressee") else open
    h = hashlib.sha256()
    with ouvrir(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(_BLOC), b""):
            h.update(bloc)
    return h.hexdigest()


def regle(meta: dict) -> dict:
    """La règle de calcul que déclare `meta` : ses seules clés `_CLES_REGLE` renseignées.

    Deux règles égales calculent la même empreinte sur les mêmes octets. C'est ce qui
    permet à fetch de voir qu'une source figée a changé de règle dans sources.yaml.
    """
    return {cle: meta[cle] for cle in _CLES_REGLE if meta.get(cle)}


def _empreinte_canonique_xml(chemin: Path, ignore_chemins) -> str:
    """SHA-256 d'un XML dont on neutralise le contenu de balises à des CHEMINS PRÉCIS.

    `ignore_chemins` liste des chemins de noms locaux depuis la racine incluse, ex.
    `GL_MarketDocument/mRID` : on ne neutralise que le mRID de document (enveloppe,
    réestampillée par requête), PAS les `mRID` imbriqués des TimeSeries, qui sont de la
    donnée stable. Cibler le chemin exact, et non le nom local n'importe où, évite de
    masquer une vraie différence de donnée. On reparse puis on re-sérialise (ET.tostring,
    déterministe pour un arbre donné) : deux réponses de même donnée mais d'enveloppe
    différente produisent la MÊME empreinte. La forme canonique ne ressemble pas au fichier
    d'origine — sans importance, on ne compare jamais que canonique à canonique.
    """
    ignore = set(ignore_chemins)
    racine = ET.parse(chemin).getroot()

    def _local(tag: str) -> str:
        # tag = '{namespace}local' -> nom local, sans le namespace.
        return tag.rsplit("}", 1)[-1]

    def parcourir(el, prefixe: str) -> None:
        chemin_local = f"{prefixe}/{_local(el.tag)}" if prefixe else _local(el.tag)
        if chemin_local in ignore:
            el.text = ""
        for enfant in el:
            parcourir(enfant, chemin_local)

    parcourir(racine, "")
    return hashlib.sha256(ET.tostring(racine, encoding="utf-8")).hexdigest()


def verifier(chemin: Path, entree: dict) -> str:
    """Vérifie qu'un fichier correspond à l'empreinte certifiée de son entrée de manifeste.

    Renvoie l'empreinte obtenue (à tracer dans la lignée de build). Lève
    EmpreinteDivergente sinon. `entree` porte `sha256` et, le cas échéant, sa règle
    (`empreinte_ignore_xml`, `empreinte_decompressee`) : la politique de calcul voyage
    avec l'empreinte.
    """
    attendue = entree.get("sha256")
    obtenue = empreinte(chemin, entree)
    if not attendue or obtenue != attendue:
        raise EmpreinteDivergente(
            f"{Path(chemin).name} : empreinte {obtenue[:12]}… ne correspond pas au "
            f"manifeste ({(attendue or '—')[:12]}…) — donnée non certifiée."
        )
    return obtenue
