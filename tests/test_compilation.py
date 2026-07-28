"""Test de fumée du compilateur d'étude : la page s'assemble sans artefact markdown
résiduel, et chaque visuel cité existe vraiment. Ne nécessite pas le pipeline de données
— il lit les visuels déjà versionnés dans outputs/ (dont il tire la hauteur d'iframe)."""

import re

from demonstrateur.compile_etude import compiler
from demonstrateur.config import ETUDE_SOURCE, OUTPUTS


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
