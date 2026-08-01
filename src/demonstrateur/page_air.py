"""Assemble le sujet air en UNE page : outputs/air_ozone.html.

Usage :
    python -m demonstrateur.page_air

Les cinq figures restent publiées séparément (chacune reste déployable seule en iframe) ;
cette page les rassemble dans un récit. Elle n'emboîte pas d'iframes : chaque graphique y
est inséré comme un bloc Plotly, et `plotly.min.js` — déjà mutualisé dans outputs/ — n'est
chargé qu'une fois pour les cinq.

Les figures passent par `viz.preparer_figure`, exactement comme les fichiers individuels :
une figure ne peut pas se retrouver ici sans sa mention de source parce qu'elle aurait pris
un autre chemin.

Le texte est court par construction — le brief demande une page qui se parcourt en trois
minutes. Les liaisons disent ce que la figure suivante va montrer, jamais ce qu'elle montre
déjà : une légende répétée en prose est du temps de lecture pris à autre chose.
"""

from __future__ import annotations

import sys

from .config import OUTPUTS
from .prepare import verifier_sorties
from .viz import PALETTE, SANS, date_collecte, preparer_figure
from . import figures_air as fa

TITRE = "L'air corse les jours où rien n'est signalé"


def _blocs() -> list[tuple[str, str, str]]:
    """(texte de liaison, identifiant de div, figure prête) pour chaque étape du récit.

    L'ordre est le récit : le constat, puis sa coïncidence apparente, puis deux idées
    reçues démontées, puis la seule chose qu'on puisse en faire.
    """
    d_air = date_collecte("aee_o3_venaco_continu")
    d_meteo = date_collecte("meteo_horaire_corse")
    p = fa._sous_titre  # périmètre commun, écrit sur chaque figure

    return [
        (
            "<p>Quand l'air se dégrade franchement, on le sait : Qualitair Corse alerte, les "
            "médias relaient. Ce dispositif fonctionne. Mais il ne se déclenche qu'au-delà "
            "d'un seuil rarement atteint sur l'île — et en dessous, personne ne dit rien. "
            "Voici ce qui s'y passe.</p>",
            "a1",
            preparer_figure(
                fa.fig_a1_depassements_sans_alerte(), fa.SRC_AIR, d_air,
                sous_titre=p("L'objectif de qualité pour la santé vaut 120 µg/m³ en maximum "
                             "journalier sur 8 heures ; l'information du public se déclenche "
                             "à 180 µg/m³ en moyenne horaire."),
            ),
        ),
        (
            "<p>L'ozone n'est émis par rien : il se fabrique sur place, sous le soleil. On "
            "s'attend donc à en trouver davantage les jours de forte chaleur — c'est le cas, "
            "mais pas indéfiniment.</p>",
            "a2",
            preparer_figure(
                fa.fig_a2_ozone_et_chaleur(), fa.SRC_AIR_METEO, d_meteo,
                sous_titre=p("Températures du poste météo apparié à chaque station — ce n'est "
                             "pas la même mesure au même endroit."),
                note="Les journées chaudes portent plus d'ozone ; chaleur, ensoleillement et "
                     "air stagnant vont de pair, et ces mesures ne les démêlent pas.",
            ),
        ),
        (
            "<p>Reste à savoir quand. Le réflexe est de penser aux heures de circulation — "
            "c'est l'inverse.</p>",
            "a3",
            preparer_figure(
                fa.fig_a3_ozone_contre_azote(), fa.SRC_AIR, d_air,
                sous_titre=p("Cinq stations mesurant les deux polluants. Chaque courbe est "
                             "ramenée à son propre maximum : la figure compare des heures, "
                             "pas des concentrations."),
            ),
        ),
        (
            "<p>Et où ? Là encore, l'intuition trompe : le gaz se forme pendant que l'air se "
            "déplace, et il s'accumule loin des moteurs qui, eux, le détruisent.</p>",
            "a4",
            preparer_figure(
                fa.fig_a4_campagne_contre_ville(), fa.SRC_AIR, d_air,
                sous_titre=p("En part des journées mesurées, et non en nombre de jours : une "
                             "station rurale contre quatre urbaines."),
            ),
        ),
        (
            "<p>De tout cela découle une seule chose utile, et la voici.</p>",
            "a5",
            preparer_figure(
                fa.fig_a5_creneau_a_eviter(), fa.SRC_AIR, d_air,
                sous_titre=p("Moyenne de chaque heure de la journée."),
                note="Le creux du petit matin est aussi le maximum de dioxyde d'azote : l'air "
                     "y est moins chargé en ozone, pas plus pur.",
            ),
        ),
    ]


def _html(blocs, collecte: str) -> str:
    corps = []
    for i, (texte, div_id, fig) in enumerate(blocs):
        # include_plotlyjs=False sur TOUS les blocs : la balise <script> est posée une
        # seule fois dans l'en-tête, sur le plotly.min.js déjà présent dans outputs/.
        graphique = fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
        corps.append(f'<section>{texte}\n<figure>{graphique}</figure></section>')
        if i == 0:
            corps.append(
                '<p class="cle">Aucune de ces journées n\'a atteint le seuil qui déclenche '
                "une information du public. Elles n'ont donc jamais fait l'objet d'un "
                "communiqué, ni d'un article.</p>"
            )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITRE}</title>
<script src="plotly.min.js"></script>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; padding:2.2rem 1.2rem 3.4rem; background:{PALETTE["page"]};
          color:{PALETTE["ink"]}; font-family:{SANS}; font-size:17px; line-height:1.62; }}
  main {{ max-width:62rem; margin:0 auto; }}
  h1 {{ font-size:2rem; line-height:1.2; margin:0 0 .5rem; max-width:22em; }}
  .chapeau {{ font-size:1.1rem; color:{PALETTE["ink_soft"]}; max-width:44em; margin:0 0 .4rem; }}
  section {{ margin:2.6rem 0 0; }}
  section p {{ max-width:44em; margin:0 0 .2rem; }}
  figure {{ margin:.4rem 0 0; background:{PALETTE["surface"]};
            border:1px solid {PALETTE["rule"]}; border-radius:6px; overflow-x:auto; }}
  .cle {{ max-width:44em; margin:1rem 0 0; padding:.9rem 1.1rem;
          background:{PALETTE["surface"]}; border-left:4px solid {PALETTE["accent"]};
          border-radius:0 4px 4px 0; }}
  footer {{ margin-top:3rem; padding-top:1.2rem; border-top:1px solid {PALETTE["rule"]};
            max-width:44em; font-size:15.5px; color:{PALETTE["ink_soft"]}; }}
  footer a {{ color:{PALETTE["accent"]}; }}
  .plotly-graph-div {{ width:100% !important; }}
</style></head><body><main>

<h1>{TITRE}</h1>
<p class="chapeau">L'ozone est le seul polluant que l'été fabrique. On ne le sent pas, il ne
noircit rien, et il ne déclenche presque jamais d'alerte en Corse — ce qui ne veut pas dire
qu'il est absent. Six étés de mesures, sur les six stations de l'île.</p>
<p class="chapeau">Données collectées le {collecte}.</p>

{"".join(corps)}

<footer>
<p>Mesures : Qualitair Corse, via l'Agence européenne pour l'environnement (CC-BY 4.0) et le
LCSQA / Ineris. Températures : Météo-France (Licence Ouverte 2.0). Ces organismes ne sont pas
associés à cette étude et n'en ont pas validé les conclusions.</p>
<p><a href="a0_note_methodologique.html">Comment ces chiffres ont été obtenus</a> — sources,
calculs, limites et approximations assumées.</p>
</footer>

</main></body></html>
"""


def main() -> int:
    verifier_sorties()
    blocs = _blocs()
    dest = OUTPUTS / "air_ozone.html"
    dest.write_text(_html(blocs, date_collecte("aee_o3_venaco_continu")), encoding="utf-8")
    print(f"[ok] {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
