"""Navigation entre les cinq pages du livrable : une seule carte, un pied contextuel.

Constat du 31/08/2026 : les quatre pages filles étaient des culs-de-sac. `etude.html` et
`air_ozone.html` ne portaient qu'un lien sortant, à 99 % de leur hauteur ; les deux notes
méthodologiques n'en portaient aucun. Or presque personne n'arrive par l'accueil — la
vitrine expose les pages, et chaque visuel se déploie seul en iframe.

Le pied expose **Accueil · Étude parente · Autre sujet · Note méthodologique**, moins la
page courante : un lien vers soi n'est pas une navigation, c'est du bruit. La carte vit
ici et nulle part ailleurs, pour que les cinq gabarits ne divergent pas.

L'accueil n'a pas de pied de navigation : il est la racine, et il liste déjà ses filles.
"""

from __future__ import annotations

from .viz import PALETTE

ACCUEIL = "index.html"
ETUDE = "etude.html"
AIR = "air_ozone.html"
NOTE_ETUDE = "t0_note_methodologique.html"
NOTE_AIR = "a0_note_methodologique.html"

# Libellés de navigation : courts, et distincts des titres de page. Un titre d'étude est
# une phrase (« De quoi est faite l'électricité corse ? ») ; un libellé de pied doit se
# lire d'un coup d'œil, sans quoi la ligne de navigation devient elle-même un paragraphe.
_LIBELLE = {
    ACCUEIL: "Accueil",
    ETUDE: "L'électricité corse",
    AIR: "L'air corse",
    NOTE_ETUDE: "Note méthodologique",
    NOTE_AIR: "Note méthodologique",
}

# Étude parente de chaque page — une étude est sa propre parente, ce qui la fait
# disparaître de son propre pied sans qu'aucun cas particulier soit écrit.
_PARENTE = {ETUDE: ETUDE, NOTE_ETUDE: ETUDE, AIR: AIR, NOTE_AIR: AIR}
_AUTRE_SUJET = {ETUDE: AIR, AIR: ETUDE}
_NOTE = {ETUDE: NOTE_ETUDE, AIR: NOTE_AIR}

# Style du pied, pour les deux notes méthodologiques qui n'avaient aucun `<footer>` —
# les trois autres pages stylent déjà le leur.
CSS = (
    "  footer { margin-top:2.6rem; padding-top:1.1rem; "
    f'border-top:1px solid {PALETTE["rule"]}; '
    "}\n"
    "  .entre-pages { font-size:15.5px; line-height:1.9; }\n"
    f'  .entre-pages a {{ color:{PALETTE["accent"]}; }}'
)


def entrees(page: str) -> list[tuple[str, str]]:
    """(cible, libellé) du pied de `page`, la page courante retirée."""
    if page not in _PARENTE:
        raise KeyError(
            f"{page} n'a pas de pied de navigation. L'accueil est la racine du livrable : "
            "il mène à ses quatre filles et n'a nulle part où remonter."
        )
    parente = _PARENTE[page]
    ordre = (ACCUEIL, parente, _AUTRE_SUJET[parente], _NOTE[parente])
    return [(cible, _LIBELLE[cible]) for cible in ordre if cible != page]


def pied(page: str) -> str:
    """Le bloc de navigation de `page`, à poser dans son `<footer>`."""
    liens = " · ".join(f'<a href="{cible}">{libelle}</a>' for cible, libelle in entrees(page))
    return f'<nav class="entre-pages">{liens}</nav>'
