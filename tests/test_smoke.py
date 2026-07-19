"""Tests de fumée : le manifeste est bien formé, le package s'importe,
le garde-fou de validation refuse ce qui n'est pas la donnée attendue."""

import pytest
import yaml

from demonstrateur.config import ROOT, SOURCES_FILE
from demonstrateur.fetch import _valider


def test_sources_yaml_est_valide():
    cfg = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    assert "sources" in cfg and cfg["sources"], "sources.yaml doit déclarer au moins une source"
    for source_id, meta in cfg["sources"].items():
        for champ in ("url", "filename", "licence", "producteur"):
            assert champ in meta, f"{source_id} : champ manquant '{champ}'"


def test_valider_rejette_html(tmp_path):
    """Une page d'erreur HTML (200 OK) ne doit jamais être acceptée comme donnée."""
    p = tmp_path / "faux.csv"
    p.write_text("<!DOCTYPE html><html><body>portail</body></html>", encoding="utf-8")
    meta = {"filename": "faux.csv", "format": "csv", "delimiter": ";"}
    with pytest.raises(ValueError):
        _valider(p, meta, "text/html; charset=utf-8")


def test_valider_rejette_colonnes_manquantes(tmp_path):
    """Un CSV bien formé mais aux mauvaises colonnes est refusé."""
    p = tmp_path / "faux.csv"
    p.write_text("a;b;c\n1;2;3\n", encoding="utf-8")
    meta = {"filename": "faux.csv", "format": "csv", "delimiter": ";",
            "colonnes_attendues": ["territoire", "date_heure"]}
    with pytest.raises(ValueError):
        _valider(p, meta, "text/csv")


def test_valider_accepte_csv_conforme(tmp_path):
    """Le bon CSV, avec les colonnes attendues, passe sans lever."""
    p = tmp_path / "ok.csv"
    p.write_text("territoire;date_heure;production_totale_mw\nCorse;2019-01-01;339\n", encoding="utf-8")
    meta = {"filename": "ok.csv", "format": "csv", "delimiter": ";",
            "colonnes_attendues": ["territoire", "date_heure"]}
    _valider(p, meta, "text/csv; charset=utf-8")


def test_arborescence():
    for rel in ("data/raw", "data/processed", "outputs", "src/demonstrateur"):
        assert (ROOT / rel).exists(), f"dossier manquant : {rel}"
