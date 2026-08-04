"""Non-fuite des jetons d'API — le verrou, pas la vigilance.

Le 20/07/2026, un jeton ENTSO-E s'est retrouvé dans un log de CI. La leçon n'est
pas « faire attention » : c'est que le chemin d'un secret doit être tenu par des
tests qui échouent bruyamment si quelqu'un — humain ou modèle — ajoute un jour un
`print` de confort. Trois sorties existent pour un secret, elles sont couvertes
ici toutes les trois :

1. la sortie standard et les messages d'erreur (`test_le_jeton_ne_fuit_pas_en_log`) ;
2. le manifeste versionné, qui part sur GitHub (`..._dans_le_manifeste`) ;
3. le réseau lui-même, si une redirection emmène l'en-tête chez un tiers
   (`..._apres_une_redirection`) — la fuite silencieuse, celle sans message.

Les jetons de ce fichier sont évidemment factices.
"""

import json
from contextlib import contextmanager

import pytest
import yaml

from demonstrateur import fetch

JETON = "7a5e6020-dead-beef-cafe"
CSV_VALIDE = b"a;b\n1;2\n"


class _Reponse:
    """Réponse httpx réduite à ce que `_download` en consomme."""

    def __init__(self, statut: int, entetes: dict, corps: bytes = b""):
        self.status_code = statut
        self.headers = entetes
        self._corps = corps

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308) and "location" in self.headers

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code} pour la source de test")

    def iter_bytes(self, taille=None):
        yield self._corps


def _client_espion(etapes: list[_Reponse], vus: list):
    """Fabrique un faux httpx.Client qui rejoue `etapes` et note les en-têtes reçus.

    `vus` accumule un (url, en-têtes) par requête — redirections comprises : c'est
    ce qui permet d'affirmer qu'un jeton n'a pas franchi un changement d'hôte.
    """

    class _Client:
        def __init__(self, **kwargs):
            self._i = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        @contextmanager
        def stream(self, methode, url, headers=None):
            vus.append((str(url), dict(headers) if headers else None))
            reponse = etapes[min(self._i, len(etapes) - 1)]
            self._i += 1
            yield reponse

    return _Client


def _mini_depot(tmp_path, monkeypatch, **surcharges):
    """Isole fetch sur un dépôt jetable : sources.yaml, data/raw, manifeste."""
    raw = tmp_path / "raw"
    raw.mkdir()
    source = {
        "url": "https://api.exemple.fr/export",
        "filename": "faux.csv",
        "licence": "Licence Ouverte 2.0",
        "producteur": "Producteur de test",
        "format": "csv",
        "delimiter": ";",
        "colonnes_attendues": ["a", "b"],
        "entetes": {"apikey": "${JETON_DE_TEST}"},
        **surcharges,
    }
    sources = tmp_path / "sources.yaml"
    sources.write_text(
        yaml.safe_dump({"sources": {"faux_geodair": source}}, allow_unicode=True),
        encoding="utf-8",
    )
    manifeste = raw / "_manifest.json"
    monkeypatch.setattr(fetch, "SOURCES_FILE", sources)
    monkeypatch.setattr(fetch, "MANIFEST_FILE", manifeste)
    monkeypatch.setattr(fetch, "DATA_RAW", raw)
    monkeypatch.setenv("JETON_DE_TEST", JETON)
    return manifeste


def test_le_jeton_ne_fuit_pas_en_log(tmp_path, monkeypatch, capsys):
    """Une exception qui cite l'en-tête ne doit jamais ressortir en clair.

    Cas volontairement hostile : le téléchargement échoue en recrachant les en-têtes
    qu'il a reçus, exactement comme un `print` de débogage oublié. `main` doit le
    caviarder — ce qui n'arrive que si les secrets d'en-tête rejoignent bien la liste
    passée à `_masquer`, et pas seulement ceux de l'url.
    """
    _mini_depot(tmp_path, monkeypatch)

    def _download_bavard(url, dest, entetes=None):
        raise RuntimeError(f"échec du transport — headers={entetes}")

    monkeypatch.setattr(fetch, "_download", _download_bavard)
    assert fetch.main([]) == 1, "la source doit échouer"
    sortie = capsys.readouterr().out
    assert JETON not in sortie, "le jeton a fuité sur la sortie standard"
    assert "•••" in sortie, "le message doit montrer qu'il a été caviardé"


def test_le_jeton_ne_fuit_pas_dans_le_manifeste(tmp_path, monkeypatch):
    """Collecte réussie : le manifeste enregistre le gabarit, jamais la valeur."""
    manifeste = _mini_depot(tmp_path, monkeypatch)

    def _download_ok(url, dest, entetes=None):
        assert entetes == {"apikey": JETON}, "l'en-tête doit parvenir expansé au transport"
        dest.write_bytes(CSV_VALIDE)
        return "text/csv"

    monkeypatch.setattr(fetch, "_download", _download_ok)
    assert fetch.main([]) == 0

    brut = manifeste.read_text(encoding="utf-8")
    assert JETON not in brut, "le jeton a fuité dans le manifeste versionné"
    entree = json.loads(brut)["faux_geodair"]
    assert entree["entetes"] == {"apikey": "${JETON_DE_TEST}"}, (
        "le manifeste doit dire QUE la source est authentifiée et par quelle variable"
    )


def test_le_jeton_ne_fuit_pas_apres_une_redirection(tmp_path, monkeypatch):
    """Fuite silencieuse : un producteur qui redirige vers un stockage tiers ne doit
    pas recevoir le jeton. httpx retire `Authorization` tout seul, jamais un `apikey`."""
    vus: list = []
    etapes = [
        _Reponse(302, {"location": "https://cdn-tiers.example/objet/42"}),
        _Reponse(200, {"content-type": "text/csv"}, CSV_VALIDE),
    ]
    monkeypatch.setattr(fetch.httpx, "Client", _client_espion(etapes, vus))
    fetch._download("https://api.exemple.fr/export", tmp_path / "x.csv", {"apikey": JETON})

    assert len(vus) == 2, "une requête par saut"
    assert vus[0][1] == {"apikey": JETON}, "l'hôte d'origine reçoit bien le jeton"
    assert vus[1][1] is None, "le tiers ne doit RIEN recevoir du jeton"
    assert "cdn-tiers" in vus[1][0]


def test_la_redirection_interne_garde_l_entete(tmp_path, monkeypatch):
    """Contrepartie : une redirection sur le MÊME hôte conserve l'en-tête, sinon
    on casserait les API qui renvoient vers leur propre chemin de téléchargement."""
    vus: list = []
    etapes = [
        _Reponse(302, {"location": "https://api.exemple.fr/export/pret"}),
        _Reponse(200, {"content-type": "text/csv"}, CSV_VALIDE),
    ]
    monkeypatch.setattr(fetch.httpx, "Client", _client_espion(etapes, vus))
    fetch._download("https://api.exemple.fr/export", tmp_path / "x.csv", {"apikey": JETON})
    assert vus[1][1] == {"apikey": JETON}


def test_boucle_de_redirection_arretee(tmp_path, monkeypatch):
    """Une redirection circulaire s'arrête sur une erreur, pas sur un blocage."""
    vus: list = []
    etapes = [_Reponse(302, {"location": "https://api.exemple.fr/export"})]
    monkeypatch.setattr(fetch.httpx, "Client", _client_espion(etapes, vus))
    with pytest.raises(ValueError, match="redirections"):
        fetch._download("https://api.exemple.fr/export", tmp_path / "x.csv", {"apikey": JETON})


def test_variable_absente_echoue_sans_rien_certifier(tmp_path, monkeypatch, capsys):
    """Secret non défini : échec net citant le NOM de la variable, aucune entrée
    au manifeste — surtout pas une entrée d'apparence légitime."""
    manifeste = _mini_depot(tmp_path, monkeypatch)
    monkeypatch.delenv("JETON_DE_TEST", raising=False)
    assert fetch.main([]) == 1
    sortie = capsys.readouterr().out
    assert "JETON_DE_TEST" in sortie
    assert json.loads(manifeste.read_text(encoding="utf-8")) == {}
