"""Test de fumée du compilateur d'étude : la page s'assemble sans artefact markdown
résiduel, et chaque visuel cité existe vraiment. Ne nécessite pas le pipeline de données
— il lit les visuels déjà versionnés dans outputs/ (dont il tire la hauteur d'iframe)."""

import re

import pytest

from demonstrateur.compile_etude import compiler, rendre_page
from demonstrateur.config import ETUDE_HTML, ETUDE_SOURCE, OUTPUTS


def test_compilation_sans_artefact_ni_visuel_manquant():
    """Compile etude.md et vérifie : aucune balise {{visuel:}} non convertie, aucun
    commentaire HTML (méta d'en-tête, marqueurs PROVISOIRE) fui dans la page publiée, et
    tout visuel cité pointe vers un fichier réellement présent dans outputs/. La compilation
    elle-même lève déjà si un visuel manque (hauteur d'iframe introuvable) ; on re-vérifie
    ici pour un message clair plutôt qu'une trace."""
    corps = compiler(ETUDE_SOURCE.read_text(encoding="utf-8"))
    assert "{{visuel" not in corps, "une balise {{visuel:}} n'a pas été convertie en iframe"
    assert "<!--" not in corps, "un commentaire HTML (méta / PROVISOIRE) a fui dans la page"
    cites = re.findall(r'src="([a-z0-9_]+)\.html"', corps)
    assert cites, "aucun visuel cité — la page devrait embarquer des figures"
    for nom in cites:
        assert (OUTPUTS / f"{nom}.html").exists(), (
            f"visuel cité mais absent d'outputs/ : {nom}.html — lancer `python -m demonstrateur.figures`"
        )


def test_page_publiee_est_bien_celle_de_la_source():
    """`outputs/etude.html` est GÉNÉRÉ, mais versionné et déployé tel quel : rien
    n'empêchait une retouche à la main d'y survivre. Le 31/07/2026, une balise
    `<fie></fie>` s'y est glissée — auto-complétion d'un éditeur ouvert sur le fichier —
    et aucun test ne pouvait la voir : la suite compilait la source en mémoire sans
    jamais la comparer au fichier publié.

    Ce test ferme les deux portes d'un coup. La retouche manuelle d'abord. Mais aussi la
    dérive silencieuse : les hauteurs d'iframe sont lues dans les visuels au moment de la
    compilation, donc une figure qui change de hauteur périme la page sans rien casser.
    D'où l'étape `compile_etude` ajoutée au pipeline planifié, après les figures.
    """
    if not ETUDE_HTML.exists():
        pytest.skip("page non compilée — lancer `compile-etude`")
    attendu = rendre_page(ETUDE_SOURCE.read_text(encoding="utf-8"))
    assert ETUDE_HTML.read_text(encoding="utf-8") == attendu, (
        "outputs/etude.html ne correspond plus à docs/etude.md ni aux visuels d'outputs/ : "
        "relancer `compile-etude`. La page publiée ne se retouche jamais à la main."
    )
