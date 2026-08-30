"""Garde commune à toute la suite : aucun test n'écrit dans le vrai `data/archive/`.

`data/archive/_versions.json` est VERSIONNÉ, et le rafraîchissement planifié le committe
(`git add data/archive/_versions.json`) — après avoir lancé pytest, dans le même run. Un
test qui pilote `fetch.main()` sur un dépôt jetable, comme `tests/test_secrets.py`,
n'isole que ce que `fetch` connaît : `sources.yaml`, `data/raw`, le manifeste. Les chemins
de l'archive, eux, vivent dans les globales de `archive.py`. Sans cette redirection, la
source fictive d'un test entrait dans l'index des millésimes, puis dans un commit du cron,
toutes les six heures — constaté le 20/08/2026, `faux_geodair` écrit pour de bon.

Redirigé pour TOUS les tests, y compris ceux qui ne touchent pas à l'archive : la garantie
ne doit pas dépendre de ce dont l'auteur du prochain test se souviendra. Les tests qui ont
besoin d'un chemin à eux (`tests/test_archive.py`) le redéfinissent par-dessus, ce qui ne
change rien à la propriété tenue ici.
"""

import pytest

from demonstrateur import archive

# Identifiants de source inventés par la suite de tests. Les nommer ici sert à deux
# choses : documenter ce qui n'est PAS une source réelle, et permettre au verrou de
# `test_archive.py` de vérifier qu'aucun d'eux n'a atterri dans le registre versionné.
# Un test qui invente un nouvel identifiant l'ajoute ici — c'est le prix d'entrée.
SOURCES_FICTIVES = frozenset({"faux_geodair", "mix", "tranche"})


@pytest.fixture(autouse=True)
def _archive_hors_du_depot(tmp_path, monkeypatch):
    racine = tmp_path / "archive_de_test"
    monkeypatch.setattr(archive, "DATA_ARCHIVE", racine)
    monkeypatch.setattr(archive, "VERSIONS_FILE", racine / "_versions.json")
    monkeypatch.setattr(archive, "LAST_CHECKED_FILE", racine / "_last_checked.json")
    # Le disjoncteur de volume est un état de RUN, porté par des globales. Remis à zéro ici
    # et pas dans les fixtures locales, pour la raison qui vaut au-dessus : le premier test
    # qui le fait sauter condamnerait tous les suivants, et un dépôt refusé ressemble en
    # tout point à un dépôt que personne n'a demandé.
    monkeypatch.setattr(archive, "_VOLUME_DEPOSE", None)
    monkeypatch.setattr(archive, "_DISJONCTEUR", None)
    # Même raison pour le verrou de configuration : un test qui pose une clé malformée
    # rendrait tous les suivants muets, et un dépôt refusé ressemble à un dépôt réussi
    # vu de l'index — c'est exactement la confusion que ce chantier corrige.
    monkeypatch.setattr(archive, "_MAL_CONFIGURE", None)
