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

    return [
        (
            "<p>Quand l'air se dégrade franchement, on le sait : Qualitair Corse alerte, les "
            "médias relaient. Ce dispositif fonctionne. Mais il ne se déclenche qu'au-delà "
            "d'un seuil rarement atteint sur l'île. Voici ce qui se passe en dessous.</p>",
            "a1",
            preparer_figure(
                fa.fig_a1_depassements_sans_alerte(), fa.SRC_AIR, d_air,
                sous_titre=fa.ST_A1, note=fa.note_a1(),
            ),
        ),
        (
            "<p>L'ozone n'est émis par rien : il se fabrique sur place, sous le soleil. On "
            "s'attend donc à en trouver davantage les jours de forte chaleur — c'est le cas, "
            "mais pas indéfiniment.</p>",
            "a2",
            preparer_figure(
                fa.fig_a2_ozone_et_chaleur(), fa.SRC_AIR_METEO, d_meteo,
                sous_titre=fa.ST_A2, note=fa.NOTE_A2,
                pied_decalage_px=fa.PIED_A2,
            ),
        ),
        (
            "<p>Reste à savoir quand. Le réflexe est de penser aux heures de circulation — "
            "c'est l'inverse.</p>",
            "a3",
            preparer_figure(
                fa.fig_a3_ozone_contre_azote(), fa.SRC_AIR, d_air,
                sous_titre=fa.st_a3(),
            ),
        ),
        (
            "<p>Et où ? Là encore, l'intuition trompe : le gaz se forme pendant que l'air se "
            "déplace, et il s'accumule loin des moteurs qui, eux, le détruisent.</p>",
            "a4",
            preparer_figure(
                fa.fig_a4_campagne_contre_ville(), fa.SRC_AIR, d_air,
                sous_titre=fa.ST_A4,
            ),
        ),
        (
            "<p>De tout cela découle une seule chose utile, et la voici.</p>",
            "a5",
            preparer_figure(
                fa.fig_a5_creneau_a_eviter(), fa.SRC_AIR, d_air,
                sous_titre=fa.ST_A5, note=fa.NOTE_A5,
            ),
        ),
    ]


# Mini-dictionnaire : la page s'adresse d'abord à des habitants, pas à des spécialistes.
# Chaque entrée se lit sans en avoir lu une autre, et aucune définition n'emploie un mot
# qu'il faudrait aller chercher ailleurs — une définition qui suppose le vocabulaire
# qu'elle est censée donner ne sert à rien. Les chiffres réglementaires viennent des
# constantes de `figures_air`, jamais recopiés à la main.
MOTS = [
    # Le renversement ouvre l'entrée plutôt que de la clore : le lecteur arrive avec « la
    # couche d'ozone nous protège », et une définition qui commence par le contraire sans
    # traiter cette idée reçue se fait relire à travers elle. La distinction et les effets
    # sont ceux de Qualitair Corse (« Polluants surveillés »), producteur des mesures —
    # « stratosphère » et « troposphère » restent dans la note méthodologique : le
    # dictionnaire s'interdit les mots qu'il faudrait aller chercher ailleurs.
    ("Ozone",
     "Un gaz qui pique les bronches — mais seulement au ras du sol. Très haut dans le "
     "ciel, le même gaz forme un filtre naturel contre les rayons ultraviolets : c'est "
     "le « bon ozone », celui de la fameuse couche. En bas, il ne protège de rien ; "
     "respiré à forte dose, il enflamme les bronches et irrite les yeux. Personne ne "
     "l'émet : il se fabrique tout seul dans l'air, quand le soleil tape sur les gaz "
     "d'échappement et les vapeurs d'essence. C'est pour ça qu'il apparaît l'été, "
     "l'après-midi, et qu'il est le seul polluant que le beau temps favorise."),
    ("Dioxyde d'azote",
     "Un gaz qui sort, lui, directement des pots d'échappement. Il suit donc la "
     "circulation : beaucoup aux heures de pointe, peu la nuit. Curiosité utile — là où "
     "il y en a beaucoup, il détruit une partie de l'ozone."),
    ("µg/m³ (microgramme par mètre cube)",
     "L'unité qui dit combien de gaz on trouve dans l'air. Un microgramme, c'est un "
     "millionième de gramme ; un mètre cube, c'est un cube d'un mètre de côté, à peu "
     "près l'air d'une cabine de douche. Autant dire de très petites quantités — qui "
     "comptent quand même pour les poumons."),
    ("Objectif de qualité",
     f"Le niveau à ne pas dépasser pour protéger la santé : {fa.OBJECTIF_QUALITE} µg/m³ "
     "d'ozone, mesuré sur les huit heures les plus chargées de la journée. Ce n'est pas "
     "une interdiction, c'est une cible. On peut la dépasser sans que personne ne soit "
     "prévenu — c'est précisément le sujet de cette page."),
    ("Seuil d'information",
     f"Le niveau, bien plus haut ({fa.SEUIL_INFORMATION} µg/m³ sur une heure), à partir "
     "duquel les autorités préviennent la population et conseillent d'éviter l'effort. "
     "En Corse, il n'est presque jamais atteint."),
    ("Station de fond",
     "Un appareil de mesure placé loin d'une route ou d'une usine, pour mesurer l'air "
     "que tout le monde respire — et non celui d'un carrefour précis. Toutes les mesures "
     "de cette page viennent de stations de ce type."),
    ("Journée valide",
     "Une journée où l'appareil a suffisamment mesuré pour que le chiffre compte "
     "vraiment. Les journées trop incomplètes sont écartées plutôt que rafistolées."),
]


def _glossaire() -> str:
    entrees = "".join(
        f"<div class='mot'><dt>{terme}</dt><dd>{texte}</dd></div>"
        for terme, texte in MOTS
    )
    return (
        "<section class='lexique'>"
        "<h2>Les mots, en clair</h2>"
        # Compté, pas écrit : « Sept » à la main devenait faux dès qu'une entrée
        # s'ajoutait, en silence — le défaut corrigé en A3 le même jour.
        f"<p>{fa.NOMBRES.get(len(MOTS), str(len(MOTS)))} termes reviennent dans cette "
        "page. Aucun n'est compliqué une fois dit simplement.</p>"
        f"<dl>{entrees}</dl></section>"
    )


# Encadrés de conclusion, indexés sur l'ordre de `_blocs()`. Ils se posent APRÈS la figure
# qui les démontre : une liaison annonce ce que la figure va montrer, jamais ce qu'elle
# vient de montrer, et une conclusion posée avant sa preuve n'est qu'une affirmation.
CLES = {
    # A1. La phrase s'arrête à ce que la série mesure. « Aucun communiqué, aucun article »
    # disait davantage : rien ici ne mesure la communication publique, qui peut naître
    # d'une prévision, d'un autre polluant ou d'une autre autorité. Le seuil, lui, est
    # calculé — et A1 échoue s'il est franchi.
    0: "Aucune de ces journées n'a atteint le seuil qui déclenche une information du "
       "public. Rien n'obligeait donc à les signaler.",
    # A4. Le lecteur arrive avec « pollution = cheminée » et range l'ozone dedans — d'autant
    # qu'il a lu la presse sur les installations de l'île. Le démenti n'importe aucun
    # mécanisme : Qualitair Corse, producteur des mesures, qualifie l'ozone de polluant
    # SECONDAIRE, que personne n'émet. Ce seul fait casse le lien, et la figure au-dessus
    # vient de le montrer sur nos propres stations. Aucune installation n'est nommée : la
    # nommer pour l'écarter attirerait l'attention sur elle, et le mécanisme couvre tous
    # les cas sans qu'on ait à en désigner un.
    3: "L'ozone ne sort d'aucun tuyau. C'est un polluant secondaire : il se fabrique dans "
       "l'air, sous le soleil, à partir d'autres gaz. Aucune cheminée ne l'émet, et sa "
       "quantité ne dit donc pas ce qu'une installation rejette près de chez soi. La "
       "preuve est dans cette figure : c'est à la campagne, loin des moteurs, qu'on en "
       "mesure le plus.",
}


def _html(blocs, collecte: str) -> str:
    corps = []
    for i, (texte, div_id, fig) in enumerate(blocs):
        # include_plotlyjs=False sur TOUS les blocs : la balise <script> est posée une
        # seule fois dans l'en-tête, sur le plotly.min.js déjà présent dans outputs/.
        graphique = fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
        corps.append(f'<section>{texte}\n<figure>{graphique}</figure></section>')
        if i in CLES:
            corps.append(f'<p class="cle">{CLES[i]}</p>')
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
  .lexique {{ margin-top:3.2rem; padding-top:1.6rem;
              border-top:1px solid {PALETTE["rule"]}; }}
  .lexique h2 {{ font-size:1.35rem; margin:0 0 .3rem; }}
  .lexique dl {{ margin:1.2rem 0 0; }}
  /* Deux colonnes quand la place existe, une seule sur téléphone — les définitions
     restent courtes, donc aucune ne se coupe en colonne étroite. */
  .lexique dl {{ display:grid; gap:1.1rem 2.2rem;
                 grid-template-columns:repeat(auto-fit, minmax(19rem, 1fr)); }}
  .lexique dt {{ font-weight:600; margin:0 0 .15rem; }}
  .lexique dd {{ margin:0; color:{PALETTE["ink_soft"]}; }}
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

{_glossaire()}

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
    # newline="\n" : cf. la note de `accueil.main` — même diff fantôme Windows/Linux.
    dest.write_text(_html(blocs, date_collecte("aee_o3_venaco_continu")),
                    encoding="utf-8", newline="\n")
    print(f"[ok] {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
