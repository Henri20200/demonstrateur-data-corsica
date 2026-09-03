"""Les octets téléchargés sont hostiles — S-04 et S-07 de l'audit du 30/08/2026.

Deux constats, un même axe : ce que `fetch` écrit sur le disque du runner vient d'un
serveur qu'on ne contrôle pas. Le vecteur réaliste est étroit (source authentifiée en
HTTPS, donc serveur compromis ou MITM TLS) et l'enjeu est un déni de service, pas une
exfiltration — mais le premier geste de `_valider` est justement de parser cet octet-là.

- **S-04** : `xml.etree` développe les entités internes. Un « billion laughs » de
  quelques ko sature la mémoire. Le verrou est `defusedxml`, qui refuse AVANT de
  développer. Les trois modules qui parsent du XML téléchargé l'utilisent : `fetch`
  (validation), `provenance` (empreinte canonique), `prepare` (lecture ENTSO-E).
- **S-07** : `_download` écrivait `iter_bytes()` sans borne. Le verrou est un plafond
  d'octets, qui rend l'échec propre et immédiat plutôt que lent.

Chaque test vérifie d'abord que sa charge MORD — qu'une bombe est bien une bombe — sans
quoi il passerait pour la mauvaise raison, sur un document simplement malformé.
"""

from contextlib import contextmanager

import pytest
import xml.etree.ElementTree as ET_STDLIB
from defusedxml.common import EntitiesForbidden

from demonstrateur import fetch, provenance

# Quatre niveaux suffisent : 10^4 « lol » à développer, assez pour prouver l'expansion,
# assez peu pour que la stdlib y survive et que le test reste instantané.
BOMBE = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<lolz>&lol4;</lolz>"""


@pytest.fixture
def bombe(tmp_path):
    """Le fichier piégé, et la preuve qu'il est bien piégé."""
    p = tmp_path / "piege.xml"
    p.write_text(BOMBE, encoding="utf-8")
    # La charge mord : la stdlib, elle, développe — 30 000 caractères pour moins d'un ko
    # de fichier. Sans ce contrôle, un document simplement malformé ferait passer les
    # tests ci-dessous pour la mauvaise raison.
    developpe = ET_STDLIB.parse(p).getroot().text
    assert p.stat().st_size < 1024 and len(developpe) > 20_000
    return p


def test_la_bombe_est_refusee_a_la_validation(bombe):
    """`_valider` refuse le document sans le développer, avec un message lisible."""
    with pytest.raises(ValueError, match="entités internes"):
        fetch._valider(bombe, {"format": "xml", "racine_attendue": "lolz"}, "application/xml")


def test_la_bombe_est_refusee_au_calcul_d_empreinte(bombe):
    """Une empreinte canonique parse l'arbre entier : c'est le chemin le plus exposé."""
    with pytest.raises(EntitiesForbidden):
        provenance.empreinte(bombe, {"empreinte_ignore_xml": ["lolz"]})


def test_un_xml_sain_passe_toujours(tmp_path):
    """Le verrou ne doit pas refuser un document ordinaire — sans DOCTYPE ni entité."""
    p = tmp_path / "sain.xml"
    p.write_text(
        '<?xml version="1.0"?><GL_MarketDocument xmlns="urn:test"><mRID>x</mRID>'
        "</GL_MarketDocument>",
        encoding="utf-8",
    )
    fetch._valider(p, {"format": "xml", "racine_attendue": "GL_MarketDocument"}, "text/xml")
    # Et l'empreinte canonique reste calculable, neutralisation comprise.
    assert len(provenance.empreinte(p, {"empreinte_ignore_xml": ["GL_MarketDocument/mRID"]})) == 64


class _ReponseInterminable:
    """Réponse httpx réduite à ce que `_download` consomme, mais qui ne finit jamais."""

    status_code = 200
    headers = {"content-type": "text/csv"}
    is_redirect = False

    def raise_for_status(self):
        return None

    def iter_bytes(self, taille=None):
        while True:  # un serveur hostile n'a aucune raison de s'arrêter
            yield b"x" * 4096


def _client_interminable(**_kwargs):
    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        @contextmanager
        def stream(self, methode, url, headers=None):
            yield _ReponseInterminable()

    return _Client()


def test_le_telechargement_s_arrete_au_plafond(tmp_path, monkeypatch):
    """Un flux sans fin échoue vite, et le disque ne se remplit pas au passage."""
    monkeypatch.setattr(fetch, "_MAX_OCTETS", 64 * 1024)
    monkeypatch.setattr(fetch.httpx, "Client", _client_interminable)
    dest = tmp_path / "flux.csv"
    with pytest.raises(ValueError, match="plafond"):
        fetch._download("https://api.exemple.fr/flux", dest)
    # Un seul bloc de dépassement toléré : le compte se fait AVANT l'écriture suivante.
    assert dest.stat().st_size <= 64 * 1024 + 4096


def test_le_plafond_ne_descend_pas_sous_les_sources_reelles():
    """Verrou contre un resserrage : la plus grosse source réelle pèse 86 Mo (08/2026).

    Un plafond trop bas ne se verrait pas en revue — il casserait la collecte le jour où
    une source annuelle grossit. 256 Mio est le plancher qu'on s'interdit de franchir.
    """
    assert fetch._MAX_OCTETS >= 256 * 1024 * 1024
