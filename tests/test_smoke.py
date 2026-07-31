"""Tests de fumée : le manifeste est bien formé, le package s'importe,
le garde-fou de validation refuse ce qui n'est pas la donnée attendue."""

import pytest
import yaml

from demonstrateur.config import ROOT, SOURCES_FILE
from demonstrateur.fetch import _expanser_date, _expanser_env, _masquer, _valider


def test_sources_yaml_est_valide():
    cfg = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    assert "sources" in cfg and cfg["sources"], "sources.yaml doit déclarer au moins une source"
    for source_id, meta in cfg["sources"].items():
        for champ in ("url", "filename", "licence", "producteur"):
            assert champ in meta, f"{source_id} : champ manquant '{champ}'"
        # Les deux déclarations vont par paire : un jeton de date sans `date_url` (ou
        # l'inverse) téléchargerait silencieusement la mauvaise journée.
        _expanser_date(meta["url"], meta.get("date_url"))


def test_expanser_date_resout_hier_et_aujourdhui():
    """Les jetons {AAAA}/{MM}/{JJ} donnent la journée demandée, sur deux chiffres."""
    from datetime import date, timedelta

    gabarit = "https://ex.fr/{AAAA}/F_{AAAA}-{MM}-{JJ}.csv"
    hier = date.today() - timedelta(days=1)
    attendu = f"https://ex.fr/{hier.year:04d}/F_{hier:%Y-%m-%d}.csv"
    assert _expanser_date(gabarit, "hier") == attendu
    aujourdhui = date.today()
    assert _expanser_date(gabarit, "aujourdhui").endswith(f"F_{aujourdhui:%Y-%m-%d}.csv")


def test_expanser_date_refuse_les_declarations_incoherentes():
    """Jeton sans date_url, date_url sans jeton, valeur inconnue : tous des échecs."""
    with pytest.raises(ValueError):
        _expanser_date("https://ex.fr/F_{AAAA}.csv", None)
    with pytest.raises(ValueError):
        _expanser_date("https://ex.fr/fixe.csv", "hier")
    with pytest.raises(ValueError):
        _expanser_date("https://ex.fr/F_{JJ}.csv", "demain")


def test_expanser_date_laisse_intacte_une_url_sans_jeton():
    """Une url ordinaire — y compris avec des %XX encodés — n'est jamais réécrite."""
    url = "https://ex.fr/api?d=18%2F11%2F2025%2000%3A00&t=a1"
    assert _expanser_date(url, None) == url


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
