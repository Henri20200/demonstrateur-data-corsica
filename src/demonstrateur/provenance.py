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

Ce module est le point unique où l'empreinte est calculée : fetch l'utilise pour
CERTIFIER (au téléchargement) et VÉRIFIER (une source figée, à chaque run) ; prepare
l'utilise pour REFUSER de construire depuis un brut non certifié.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

_BLOC = 1 << 20  # lecture par blocs de 1 Mo (empreinte brute en streaming)


class EmpreinteDivergente(ValueError):
    """Le fichier local ne correspond plus à l'empreinte certifiée du manifeste."""


def empreinte(chemin: Path, meta: dict) -> str:
    """SHA-256 de traçabilité du fichier.

    Si `meta` déclare `empreinte_ignore_xml` (chemins XML précis depuis la racine),
    calcule l'empreinte sur une forme CANONIQUE du XML (contenu de ces balises neutralisé)
    — reproductible d'un téléchargement à l'autre. Sinon, empreinte des octets bruts, en
    streaming.

    `meta` peut être l'entrée de sources.yaml (côté fetch) ou l'entrée de manifeste
    (côté prepare) : les deux portent `empreinte_ignore_xml`, ce qui évite à prepare
    de relire sources.yaml.
    """
    ignore = meta.get("empreinte_ignore_xml")
    if ignore:
        return _empreinte_canonique_xml(chemin, ignore)
    h = hashlib.sha256()
    with Path(chemin).open("rb") as flux:
        for bloc in iter(lambda: flux.read(_BLOC), b""):
            h.update(bloc)
    return h.hexdigest()


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
    EmpreinteDivergente sinon. `entree` porte `sha256` et, le cas échéant,
    `empreinte_ignore_xml` : la politique de calcul voyage avec l'empreinte.
    """
    attendue = entree.get("sha256")
    obtenue = empreinte(chemin, entree)
    if not attendue or obtenue != attendue:
        raise EmpreinteDivergente(
            f"{Path(chemin).name} : empreinte {obtenue[:12]}… ne correspond pas au "
            f"manifeste ({(attendue or '—')[:12]}…) — donnée non certifiée."
        )
    return obtenue
