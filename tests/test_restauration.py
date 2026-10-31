"""Une source figée absente de data/raw se RESTAURE, elle ne se réadopte pas.

Cache d'Actions évincé, poste neuf : l'entrée du manifeste est là, le fichier non. Jusqu'au
31/10/2026, `fetch` la traitait en source neuve et adoptait le contenu du jour sans le
comparer — quatre années ENTSO-E le 22/07/2026, la tranche météo 2020-2024 le 04/08. Et un
téléchargement raté retirait l'entrée, ce qui ouvrait la même porte au run suivant.
"""

import gzip
import json

import pytest
import yaml

from demonstrateur import archive, fetch
from demonstrateur.provenance import empreinte

CONTENU = b"NUM_POSTE;NOM_USUEL;AAAAMMJJHH;T;QT\n" + b"20004002;AJACCIO;2024123123;9.1;1\n" * 500
REVISE = CONTENU.replace(b";9.1;1\n", b";9.2;1\n", 1)
SEPTEMBRE, OCTOBRE = 1788242673, 1790841119
TRANCHE = {
    "url": "https://exemple.test/tranche.csv.gz",
    "filename": "tranche.csv.gz",
    "format": "csv.gz",
    "delimiter": ";",
    "empreinte_decompressee": True,
}


def _gz(contenu: bytes, instant: int) -> bytes:
    return gzip.compress(contenu, mtime=instant)


@pytest.fixture
def chaine(tmp_path, monkeypatch):
    """Une tranche certifiée dont le fichier local a disparu, et un producteur réglable.

    `certifier(octets, regle)` pose l'entrée de manifeste sous la règle voulue puis retire
    le fichier ; `servi["octets"]` est ce que le producteur rend (absent : injoignable).
    """
    monkeypatch.setattr(archive, "_depot_durable", lambda: None)
    monkeypatch.setattr(fetch, "DATA_RAW", tmp_path)
    manifeste = tmp_path / "_manifest.json"
    monkeypatch.setattr(fetch, "MANIFEST_FILE", manifeste)
    sources = tmp_path / "sources.yaml"
    sources.write_text(yaml.safe_dump({"sources": {"tranche": TRANCHE}}), encoding="utf-8")
    monkeypatch.setattr(fetch, "SOURCES_FILE", sources)
    brut = tmp_path / TRANCHE["filename"]
    servi: dict = {}

    def telecharger(_url, dest, _entetes=None):
        if "octets" not in servi:
            raise ConnectionError("producteur injoignable")
        dest.write_bytes(servi["octets"])
        return "application/gzip"

    monkeypatch.setattr(fetch, "_download", telecharger)

    def certifier(octets: bytes, regle: dict) -> None:
        brut.write_bytes(octets)
        meta = {**{k: v for k, v in TRANCHE.items() if k != "empreinte_decompressee"}, **regle}
        entree = fetch._entree_certifiee(
            {}, meta, brut, empreinte(brut, meta),
            content_type="application/gzip", date_collecte="2026-08-04",
        )
        manifeste.write_text(
            json.dumps({"tranche": entree}, indent=2, ensure_ascii=False),
            encoding="utf-8", newline="\n",
        )
        brut.unlink()

    def entree() -> dict:
        return json.loads(manifeste.read_text(encoding="utf-8"))["tranche"]

    return certifier, servi, brut, manifeste, entree


def test_le_contenu_certifie_se_restaure(chaine):
    """Le producteur sert le même contenu, recompressé : le fichier revient, l'empreinte
    reste."""
    certifier, servi, brut, _, entree = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    attendue = entree()["sha256"]
    servi["octets"] = _gz(CONTENU, OCTOBRE)

    assert fetch.main([]) == 0
    assert brut.read_bytes() == servi["octets"]
    assert entree()["sha256"] == attendue


@pytest.mark.parametrize(
    "regle, octets_servis",
    [
        # Le cas de la tranche météo d'août à septembre 2026 : le contenu a changé.
        ({"empreinte_decompressee": True}, _gz(REVISE, OCTOBRE)),
        # Même contenu, mais certifié sur ses octets bruts : l'ancienne empreinte ne
        # couvre pas la recompression, et la règle de sources.yaml n'y change rien.
        ({}, _gz(CONTENU, OCTOBRE)),
    ],
    ids=["contenu_revise", "regle_changee"],
)
def test_un_autre_contenu_n_est_pas_adopte(chaine, regle, octets_servis):
    certifier, servi, brut, manifeste, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), regle)
    avant = manifeste.read_bytes()
    servi["octets"] = octets_servis

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant, "l'entrée certifiée doit rester telle quelle"
    assert not brut.exists(), "un contenu refusé ne doit pas être posé dans data/raw"
    assert not brut.with_name(brut.name + ".part").exists()


def test_un_telechargement_rate_ne_retire_pas_l_entree(chaine):
    """Le chemin du 20/07/2026 : entrée retirée sur un échec, contenu adopté au run
    suivant. L'entrée reste, et le run suivant refuse encore le contenu révisé."""
    certifier, servi, brut, manifeste, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    avant = manifeste.read_bytes()

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant

    servi["octets"] = _gz(REVISE, OCTOBRE)
    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant
    assert not brut.exists()


def test_retirer_l_entree_adopte_le_contenu_revise(chaine):
    """La voie de la décision : sans entrée, la source est neuve et son contenu adopté."""
    certifier, servi, brut, manifeste, entree = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    manifeste.write_text("{}", encoding="utf-8", newline="\n")
    servi["octets"] = _gz(REVISE, OCTOBRE)

    assert fetch.main([]) == 0
    assert brut.read_bytes() == servi["octets"]
    assert entree()["sha256"] == empreinte(brut, TRANCHE)
