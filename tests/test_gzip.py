"""Q6 : vérifier tous les octets gzip avant de remplacer un brut certifié.

Et empreinter un gzip par son CONTENU quand son producteur le recompresse : la tranche
météo 2020-2024 change d'octets chaque mois sans changer de contenu (31/10/2026).
"""

import gzip
import hashlib
import json

import pytest
import yaml

from demonstrateur import archive, fetch
from demonstrateur.provenance import empreinte


@pytest.mark.parametrize("defaut", ["tronque", "crc", "second_membre"])
def test_un_gzip_invalide_conserve_le_brut_et_son_manifeste(tmp_path, monkeypatch, defaut):
    meta = {
        "url": "https://exemple.test/mix.csv.gz",
        "filename": "mix.csv.gz",
        "format": "csv.gz",
        "glissant": True,
        "colonnes_attendues": ["a", "b"],
    }
    contenu = b"a,b\n" + b"1,2\n" * 10000
    complet = gzip.compress(contenu)
    if defaut == "tronque":
        invalide = complet[:-8]
    elif defaut == "crc":
        invalide = complet[:-8] + bytes([complet[-8] ^ 1]) + complet[-7:]
    else:
        invalide = complet + gzip.compress(b"3,4\n" * 10000)[:-8]
    with pytest.raises((EOFError, gzip.BadGzipFile)):
        gzip.decompress(invalide)
    piege = tmp_path / "piege.gz"
    piege.write_bytes(invalide)
    # Preuve que l'ancien contrôle, limité à l'en-tête, ne voit pas ce défaut.
    assert fetch._entete_csv(piege, gz=True) == "a,b"

    brut = tmp_path / meta["filename"]
    ancien = gzip.compress(b"a,b\n9,8\n")
    brut.write_bytes(ancien)
    entree = fetch._entree_certifiee(
        {},
        meta,
        brut,
        empreinte(brut, meta),
        content_type="application/gzip",
        date_collecte="2026-09-20",
    )
    manifeste = tmp_path / "_manifest.json"
    manifeste.write_text(
        json.dumps({"mix": entree}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    avant = manifeste.read_bytes()
    sources = tmp_path / "sources.yaml"
    sources.write_text(yaml.safe_dump({"sources": {"mix": meta}}), encoding="utf-8")
    monkeypatch.setattr(fetch, "DATA_RAW", tmp_path)
    monkeypatch.setattr(fetch, "MANIFEST_FILE", manifeste)
    monkeypatch.setattr(fetch, "SOURCES_FILE", sources)

    def telecharger(_url, dest, _entetes=None):
        dest.write_bytes(invalide)
        return "application/gzip"

    monkeypatch.setattr(fetch, "_download", telecharger)
    assert fetch.main([]) == 1
    assert brut.read_bytes() == ancien
    assert manifeste.read_bytes() == avant
    assert not brut.with_name(brut.name + ".part").exists()


def test_le_gzip_est_borne_sur_le_volume_decompresse(tmp_path, monkeypatch):
    fichier = tmp_path / "mix.csv.gz"
    fichier.write_bytes(gzip.compress(b"a,b\n" + b"1,2\n" * 1000))
    monkeypatch.setattr(fetch, "_MAX_OCTETS_DECOMPRESSES", 1024, raising=False)
    with pytest.raises(ValueError, match="plafond"):
        fetch._valider(fichier, {"format": "csv.gz"}, "application/gzip")


def test_un_gzip_complet_a_plusieurs_membres_reste_valide(tmp_path):
    fichier = tmp_path / "mix.csv.gz"
    fichier.write_bytes(gzip.compress(b"a,b\n1,2\n") + gzip.compress(b"3,4\n"))
    fetch._valider(fichier, {"format": "csv.gz"}, "application/gzip")


# Contenu d'une tranche météo miniature, et les instants de compression que portaient
# les copies réelles de Météo-France : 01/09/2026 06:04:33 et 01/10/2026 07:51:59 UTC.
CONTENU = b"NUM_POSTE;NOM_USUEL;AAAAMMJJHH;T;QT\n" + b"20004002;AJACCIO;2024123123;9.1;1\n" * 500
SEPTEMBRE, OCTOBRE = 1788242673, 1790841119
FIGEE = {
    "url": "https://exemple.test/tranche.csv.gz",
    "filename": "tranche.csv.gz",
    "format": "csv.gz",
}


def _gz(contenu: bytes, instant: int) -> bytes:
    return gzip.compress(contenu, mtime=instant)


def test_l_empreinte_decompressee_ignore_l_instant_de_compression(tmp_path):
    """Même contenu recompressé un mois plus tard : octets différents, même empreinte."""
    septembre = tmp_path / "septembre.csv.gz"
    septembre.write_bytes(_gz(CONTENU, SEPTEMBRE))
    octobre = tmp_path / "octobre.csv.gz"
    octobre.write_bytes(_gz(CONTENU, OCTOBRE))
    autre = tmp_path / "autre.csv.gz"
    autre.write_bytes(_gz(CONTENU + b"20004002;AJACCIO;2025010100;9.0;1\n", SEPTEMBRE))
    regle = {"empreinte_decompressee": True}

    assert empreinte(septembre, {}) != empreinte(octobre, {}), "le défaut constaté"
    assert empreinte(septembre, regle) == empreinte(octobre, regle)
    # Recalculable hors de la chaîne : zcat fichier | sha256sum.
    assert empreinte(septembre, regle) == hashlib.sha256(CONTENU).hexdigest()
    assert empreinte(autre, regle) != empreinte(septembre, regle)


@pytest.fixture
def tranche_certifiee_en_brut(tmp_path, monkeypatch):
    """Une source figée certifiée sur ses octets bruts, à qui sources.yaml déclare
    désormais `empreinte_decompressee` — l'état du cron au lendemain de la fusion.

    Renvoie une fonction qui pose les octets locaux et rend (brut, manifeste).
    """
    monkeypatch.setattr(archive, "_depot_durable", lambda: None)
    monkeypatch.setattr(fetch, "DATA_RAW", tmp_path)
    manifeste = tmp_path / "_manifest.json"
    monkeypatch.setattr(fetch, "MANIFEST_FILE", manifeste)
    sources = tmp_path / "sources.yaml"
    sources.write_text(
        yaml.safe_dump({"sources": {"tranche": {**FIGEE, "empreinte_decompressee": True}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fetch, "SOURCES_FILE", sources)

    def _interdit(*_args, **_kwargs):
        raise AssertionError("une source figée présente ne se retélécharge pas")

    monkeypatch.setattr(fetch, "_download", _interdit)

    def poser(octets_certifies: bytes, octets_locaux: bytes):
        brut = tmp_path / FIGEE["filename"]
        brut.write_bytes(octets_certifies)
        entree = fetch._entree_certifiee(
            {}, FIGEE, brut, empreinte(brut, FIGEE),
            content_type="application/gzip", date_collecte="2026-08-04",
        )
        brut.write_bytes(octets_locaux)
        manifeste.write_text(
            json.dumps({"tranche": entree}, indent=2, ensure_ascii=False),
            encoding="utf-8", newline="\n",
        )
        return brut, manifeste

    return poser


def test_la_nouvelle_regle_s_adopte_apres_verification_sous_l_ancienne(
    tranche_certifiee_en_brut,
):
    """Octets certifiés présents : vérifiés en brut, puis ré-empreintés sur leur contenu,
    sans téléchargement. La copie recompressée du mois suivant passe ensuite le contrôle."""
    octets = _gz(CONTENU, SEPTEMBRE)
    brut, manifeste = tranche_certifiee_en_brut(octets, octets)

    assert fetch.main([]) == 0
    entree = json.loads(manifeste.read_text(encoding="utf-8"))["tranche"]
    assert entree["sha256"] == hashlib.sha256(CONTENU).hexdigest()
    assert entree["empreinte_decompressee"] is True, "la règle doit voyager avec l'empreinte"
    assert entree["date_collecte"] == "2026-08-04", "la donnée n'a pas été recueillie de nouveau"
    assert "recertifie_le" in entree
    assert brut.read_bytes() == octets

    brut.write_bytes(_gz(CONTENU, OCTOBRE))
    assert fetch.main([]) == 0
    assert json.loads(manifeste.read_text(encoding="utf-8"))["tranche"] == entree
    versions = json.loads(archive.VERSIONS_FILE.read_text(encoding="utf-8"))["tranche"]
    assert len(versions) == 1, "une recompression n'est pas un nouveau millésime"


def test_la_nouvelle_regle_ne_certifie_pas_des_octets_non_verifies(tranche_certifiee_en_brut):
    """Copie recompressée à la place des octets certifiés : même contenu, sans doute, mais
    l'ancienne empreinte ne le prouve pas. Le changement de règle n'est pas une porte
    d'entrée : échec, manifeste intact."""
    _, manifeste = tranche_certifiee_en_brut(_gz(CONTENU, SEPTEMBRE), _gz(CONTENU, OCTOBRE))
    avant = manifeste.read_bytes()

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant
