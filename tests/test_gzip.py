"""Q6 : vérifier tous les octets gzip avant de remplacer un brut certifié."""

import gzip
import json

import pytest
import yaml

from demonstrateur import fetch
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
