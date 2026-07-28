"""Tests de fumée : le manifeste est bien formé, le package s'importe,
le garde-fou de validation refuse ce qui n'est pas la donnée attendue."""

import pytest
import yaml

from demonstrateur.config import ROOT, SOURCES_FILE
from demonstrateur.fetch import _expanser_env, _masquer, _valider
from demonstrateur.viz import LARGEUR_PIED, replier_pied


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


def test_expansion_env(monkeypatch):
    """Un ${NOM} dans l'url est remplacé par la variable d'environnement."""
    monkeypatch.setenv("JETON_TEST", "abc123")
    url, secrets = _expanser_env("https://api.example/data?securityToken=${JETON_TEST}")
    assert url == "https://api.example/data?securityToken=abc123"
    assert secrets == ["abc123"]


def test_expansion_env_variable_absente(monkeypatch):
    """Variable absente (ou vide) = erreur claire citant le NOM, jamais de valeur."""
    monkeypatch.delenv("JETON_TEST", raising=False)
    with pytest.raises(ValueError, match=r"\$\{JETON_TEST\}"):
        _expanser_env("https://api.example/data?securityToken=${JETON_TEST}")
    monkeypatch.setenv("JETON_TEST", "")
    with pytest.raises(ValueError, match=r"\$\{JETON_TEST\}"):
        _expanser_env("https://api.example/data?securityToken=${JETON_TEST}")


def test_expansion_env_sans_variable():
    """Une url ordinaire traverse sans modification ni secret."""
    url, secrets = _expanser_env("https://files.data.gouv.fr/x.csv.gz")
    assert url == "https://files.data.gouv.fr/x.csv.gz"
    assert secrets == []


def test_masquage_secret():
    """Un message d'erreur (ex. httpx citant l'url) ne doit jamais exposer le jeton."""
    msg = "HTTP 401 pour https://api.example/data?securityToken=abc123"
    assert "abc123" not in _masquer(msg, ["abc123"])


def test_masquage_secret_url_encode():
    """Régression CI 20/07 : httpx encode l'url (espace -> %20), déjouant le simple
    remplacement de valeur. Le caviardage de securityToken= doit tenir quand même."""
    # Secret parasité par un préfixe « valeur = » (incident du secret GitHub mal collé).
    secret = "valeur = 7a5e6020-dead-beef"
    msg = ("Client error '400' for url 'https://web-api.tp.entsoe.eu/api?"
           "securityToken=valeur%20=%207a5e6020-dead-beef&documentType=A75'")
    masque = _masquer(msg, [secret])
    assert "7a5e6020" not in masque, "le jeton (même url-encodé) ne doit pas fuiter"
    assert "securityToken=•••" in masque


def test_arborescence():
    for rel in ("data/raw", "data/processed", "outputs", "src/demonstrateur"):
        assert (ROOT / rel).exists(), f"dossier manquant : {rel}"


def test_repli_du_pied_borne_les_lignes():
    """Une annotation Plotly ne replie pas : au-delà de la largeur, la fin de la phrase
    est rognée en silence. Le repli est donc câblé dans l'export — et vérifié ici, parce
    que le défaut est invisible tant qu'on développe sur écran large."""
    long = (
        "81 % des heures de bridage ont lieu de mars à juin. Même au pire mois "
        "(mai 2020 : 141 h), 90,5 % de la production ENR intermittente a été acceptée."
    )
    lignes = replier_pied(long).split("<br>")
    assert len(lignes) > 1, "un texte de 146 caractères doit être replié"
    assert all(len(x) <= LARGEUR_PIED for x in lignes), (
        f"ligne trop longue après repli : {[len(x) for x in lignes]}"
    )
    assert " ".join(lignes) == long, "le repli ne doit rien perdre ni rien ajouter"


def test_repli_du_pied_respecte_les_coupures_voulues():
    """Un appelant qui coupe à un endroit précis (avant la date, entre deux phrases)
    garde la main : le repli s'ajoute aux <br> existants, il ne les efface pas."""
    texte = "Source : EDF — Open Data Groupe EDF (Corse & Outre-mer)<br>— collectées le 2026-07-22"
    assert replier_pied(texte).split("<br>") == texte.split("<br>"), (
        "deux lignes déjà courtes doivent traverser le repli intactes"
    )
