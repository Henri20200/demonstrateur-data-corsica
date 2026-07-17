"""Tests de fumée : le manifeste est bien formé, le package s'importe."""

import yaml

from demonstrateur.config import ROOT, SOURCES_FILE


def test_sources_yaml_est_valide():
    cfg = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    assert "sources" in cfg and cfg["sources"], "sources.yaml doit déclarer au moins une source"
    for source_id, meta in cfg["sources"].items():
        for champ in ("url", "filename", "licence", "producteur"):
            assert champ in meta, f"{source_id} : champ manquant '{champ}'"


def test_arborescence():
    for rel in ("data/raw", "data/processed", "outputs", "src/demonstrateur"):
        assert (ROOT / rel).exists(), f"dossier manquant : {rel}"
