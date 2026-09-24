"""Régressions : aucune publication depuis une sortie locale étrangère à la lignée."""

import json

import pytest

from demonstrateur import prepare, viz
from demonstrateur.provenance import empreinte


@pytest.fixture
def generation(tmp_path, monkeypatch):
    sortie = tmp_path / "courbe.parquet"
    sortie.write_bytes(b"sortie de la generation courante")
    lignee = {
        "sources": {"edf": {
            "filename": "courbe.csv", "sha256": "a" * 64, "date_collecte": "2026-09-21",
        }},
        "sorties": {sortie.name: {"sha256": empreinte(sortie, {}), "sources": ["edf"]}},
    }
    fichier = tmp_path / "_build.json"
    fichier.write_text(json.dumps(lignee), encoding="utf-8")
    monkeypatch.setattr(prepare, "DATA_PROCESSED", tmp_path)
    monkeypatch.setattr(prepare, "BUILD_FILE", fichier)
    return fichier, lignee


def test_un_ancien_parquet_optionnel_empeche_tout_export(generation, monkeypatch):
    from demonstrateur import figures

    fichier, _ = generation
    ancien = fichier.parent / "entsoe_sardaigne.parquet"
    ancien.write_bytes(b"ancienne generation")
    exports = []
    monkeypatch.setattr(figures, "verifier_sorties", prepare.verifier_sorties)
    monkeypatch.setattr(figures, "export_html", lambda *a, **kw: exports.append(a))
    with pytest.raises(ValueError, match="hors lignée.*entsoe_sardaigne"):
        figures.main()
    assert not exports
    assert ancien.read_bytes() == b"ancienne generation"


@pytest.mark.parametrize("contenu", [{}, [], {"sorties": {}}, {"sources": {}, "sorties": {}}])
def test_une_lignee_vide_ne_certifie_jamais_un_dossier(generation, contenu):
    fichier, _ = generation
    fichier.write_text(json.dumps(contenu), encoding="utf-8")
    with pytest.raises(ValueError, match="Lignée"):
        prepare.verifier_sorties()


def test_une_sortie_sans_source_certifiee_est_refusee(generation):
    fichier, lignee = generation
    lignee["sorties"]["courbe.parquet"]["sources"] = ["source_oubliee"]
    fichier.write_text(json.dumps(lignee), encoding="utf-8")
    with pytest.raises(ValueError, match="sources absentes"):
        prepare.verifier_sorties()


def test_la_date_ne_se_replie_pas_sur_un_autre_telechargement(generation, monkeypatch):
    fichier, _ = generation
    manifeste = fichier.parent / "_manifest.json"
    manifeste.write_text(json.dumps({"autre": {"date_collecte": "2026-09-22"}}), encoding="utf-8")
    monkeypatch.setattr(viz, "BUILD_FILE", fichier)
    monkeypatch.setattr(viz, "MANIFEST_FILE", manifeste)
    with pytest.raises(ValueError, match="absent de la lignée"):
        viz.date_collecte("autre")
