"""Construit les 5 visuels du sujet AIR depuis data/processed, exporte outputs/*.html.

Un visuel par titre-affirmation du BRIEF_AIR. Usage :
    python -m demonstrateur.figures_air

Périmètre commun à toutes les figures, et écrit sur chacune : **étés 2020-2025**
(juin-juillet-août), **stations de fond**, **maximums journaliers réglementairement
valides**. Ce périmètre unique n'est pas un confort de code — c'est ce qui autorise à lire
deux chiffres de deux figures l'un à côté de l'autre. Une figure qui en sort le dit dans
son sous-titre.

Deux règles de rédaction héritées du brief, et qui se voient dans les libellés :
 - **association, jamais causalité** : « les jours à 30 °C portent X de plus », et non
   « la chaleur ajoute X » ;
 - **la figure nomme le POSTE météo**, jamais la commune de la station d'air : le
   thermomètre de Venaco est à Vivario, dix kilomètres plus loin et cent vingt mètres
   plus haut.
"""

from __future__ import annotations

import sys

import duckdb
import plotly.graph_objects as go

from .config import DATA_PROCESSED
from .prepare import verifier_sorties
from .viz import AIR_AZOTE, AIR_OZONE, PALETTE, SANS, date_collecte, export_html

SERIE = (DATA_PROCESSED / "air_serie.parquet").as_posix()
MDA8 = (DATA_PROCESSED / "air_o3_mda8.parquet").as_posix()
CROISE = (DATA_PROCESSED / "air_temperature_jour.parquet").as_posix()

SRC_AIR = ("Agence européenne pour l'environnement — mesures Qualitair Corse, "
           "rapportées par le LCSQA/Ineris")
SRC_AIR_METEO = (SRC_AIR + " ; températures Météo-France")

# Seuils réglementaires (art. R221-1 du code de l'environnement, vérifié le 01/08/2026).
# Ils ne comptent PAS la même chose et ne se mêlent jamais dans une même lecture :
# l'objectif de qualité porte sur le maximum journalier de la moyenne sur 8 heures,
# le seuil d'information sur une moyenne HORAIRE.
OBJECTIF_QUALITE = 120  # µg/m³, maximum journalier de la moyenne sur 8 h
SEUIL_INFORMATION = 180  # µg/m³, moyenne horaire

ETES = "extract('month' FROM date_locale) IN (6, 7, 8)"
ANNEES = "extract('year' FROM date_locale) BETWEEN 2020 AND 2025"
PERIMETRE = "Étés 2020-2025 (juin-août), stations de fond, journées réglementairement valides."


def _con():
    return duckdb.connect()


def _sous_titre(ligne: str) -> str:
    return f"{ligne}<br>{PERIMETRE}"


# --- A1 : « on dépasse les jours où personne n'alerte » -----------------------
def fig_a1_depassements_sans_alerte() -> go.Figure:
    """Nombre de journées franchissant l'objectif de qualité, et combien ont alerté.

    Forme : barres horizontales — la donnée compare des quantités entre entités nommées,
    et les noms de stations sont longs. Une seule série : pas de légende, le titre la
    nomme. Le second chiffre du titre (« zéro alerte ») ne se dessine pas en barres — il
    vaudrait zéro pixel — il est donc porté par une annotation, ce qui est sa juste place.
    """
    con = _con()
    df = con.execute(f"""
        WITH j AS (
          SELECT date_locale, station, mda8 FROM '{MDA8}'
          WHERE valide AND {ETES} AND {ANNEES} AND influence = 'Fond'),
        h AS (SELECT date_locale, station, max(valeur) AS horaire_max
              FROM '{SERIE}' WHERE polluant = 'O3' GROUP BY 1, 2)
        SELECT j.station,
               count(*) FILTER (WHERE j.mda8 > {OBJECTIF_QUALITE})                    AS depassements,
               count(*) FILTER (WHERE h.horaire_max >= {SEUIL_INFORMATION})           AS alertes
        FROM j JOIN h USING (date_locale, station)
        GROUP BY 1 ORDER BY 2
    """).df()
    total = int(df["depassements"].sum())
    alertes = int(df["alertes"].sum())
    if alertes:
        raise ValueError(
            f"A1 : {alertes} journée(s) atteignent {SEUIL_INFORMATION} µg/m³ — le titre "
            "affirme qu'aucune n'alerte. À réécrire avant de publier."
        )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["depassements"], y=df["station"], orientation="h",
        marker=dict(color=AIR_OZONE, line=dict(color=PALETTE["surface"], width=2)),
        text=[str(v) for v in df["depassements"]], textposition="outside",
        textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        hovertemplate="%{y}<br>%{x} journées au-dessus de "
                      f"{OBJECTIF_QUALITE} µg/m³<extra></extra>",
    ))
    fig.add_annotation(
        # Encadré ancré au COIN BAS DROIT et tenu court : les deux stations d'Ajaccio ont
        # des barres si brèves que la zone est libre, mais un texte large y redescendrait
        # quand même sur elles. Trois lignes courtes plutôt que deux longues.
        text=(f"<b>{total} journées</b> au-dessus<br>de l'objectif de qualité.<br>"
              f"<b>Aucune</b> n'a alerté."),
        xref="paper", yref="paper", x=0.99, y=0.04, xanchor="right", yanchor="bottom",
        showarrow=False, align="right",
        font=dict(family=SANS, size=18, color=PALETTE["ink"]),
        bgcolor=PALETTE["page"], borderpad=12,
    )
    fig.update_layout(
        title=dict(text="Six étés de dépassements, et pas une seule alerte"),
        xaxis=dict(title=f"Journées au-dessus de {OBJECTIF_QUALITE} µg/m³"),
        yaxis=dict(title=""),
        margin=dict(t=170, b=170, l=250, r=90),
        height=560,
    )
    return fig


# --- A2 : « l'air se dégrade quand il fait beau » -----------------------------
def fig_a2_ozone_et_chaleur() -> go.Figure:
    """Ozone moyen par tranche de température, avec l'effectif de chaque tranche.

    Forme : barres verticales sur des tranches ordonnées — la variable de découpage est
    continue, la lecture attendue est « ça monte, puis ça ne monte plus ». Une courbe
    laisserait croire à une progression lisse entre deux tranches où rien n'est mesuré.

    L'effectif est écrit sous chaque tranche : la dernière ne compte qu'une fraction des
    journées des autres, et un lecteur doit pouvoir en tenir compte sans aller le chercher.
    """
    con = _con()
    df = con.execute(f"""
        SELECT CASE WHEN t_max < 25 THEN '< 25 °C'
                    WHEN t_max < 30 THEN '25 à 30 °C'
                    WHEN t_max < 35 THEN '30 à 35 °C'
                    ELSE '≥ 35 °C' END AS tranche,
               min(t_max) AS borne, avg(mda8) AS ozone, count(*) AS jours
        FROM '{CROISE}'
        WHERE influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1 ORDER BY borne
    """).df()
    i_max = int(df["ozone"].idxmax())
    if i_max == len(df) - 1:
        raise ValueError(
            "A2 : l'ozone culmine sur la tranche la plus chaude — le plafond que le titre "
            "annonce n'existe plus. Titre et sous-titre à revoir."
        )
    couleurs = [AIR_OZONE if i <= i_max else PALETTE["muted"] for i in range(len(df))]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["tranche"], y=df["ozone"],
        marker=dict(color=couleurs, line=dict(color=PALETTE["surface"], width=2)),
        text=[f"{v:.0f}" for v in df["ozone"]], textposition="outside",
        textfont=dict(family=SANS, size=18, color=PALETTE["ink"]),
        customdata=df["jours"],
        hovertemplate="%{x}<br>%{y:.1f} µg/m³ en moyenne<br>"
                      "%{customdata} journées<extra></extra>",
    ))
    for i, r in df.iterrows():
        fig.add_annotation(
            x=r["tranche"], y=0, yshift=-34, text=f"{int(r['jours'])} j",
            showarrow=False, font=dict(family=SANS, size=15, color=PALETTE["ink_soft"]),
        )
    fig.add_annotation(
        x=df.loc[len(df) - 1, "tranche"], y=float(df.loc[len(df) - 1, "ozone"]),
        # Flèche OBLIQUE (ax non nul) : à la verticale, elle traversait l'étiquette de
        # valeur posée au-dessus de la barre.
        text="au-delà, l'ozone<br>ne monte plus", showarrow=True, arrowhead=0,
        arrowcolor=PALETTE["ink_soft"], ax=-78, ay=-58,
        font=dict(family=SANS, size=16, color=PALETTE["ink"]),
    )
    fig.update_layout(
        title=dict(text="Plus il fait chaud, plus l'air est chargé — jusqu'à 35 °C"),
        xaxis=dict(title="Température maximale de la journée"),
        yaxis=dict(title="Ozone, maximum journalier moyen (µg/m³)",
                   range=[0, float(df["ozone"].max()) * 1.25]),
        margin=dict(t=170, b=200, l=140, r=70),
        height=600,
    )
    return fig


# --- A3 : « le pic n'est pas à l'heure de pointe » ----------------------------
def fig_a3_ozone_contre_azote() -> go.Figure:
    """Cycles diurnes de l'ozone et du NO2, chacun ramené à son propre maximum.

    Forme : deux courbes sur une échelle RELATIVE, et surtout pas deux axes verticaux.
    Les deux polluants n'ont pas le même ordre de grandeur (l'ozone dépasse 90 µg/m³
    quand le NO2 plafonne sous 20) ; un second axe donnerait à leurs hauteurs une
    comparabilité qui n'existe pas. Ce que la figure compare, ce sont des HEURES, pas des
    concentrations — d'où l'indexation sur 100 % du maximum de chaque série. Les valeurs
    absolues restent lisibles au survol.

    Cinq stations et non six : Venaco ne mesure plus le NO2, et comparer deux polluants
    exige qu'ils soient mesurés au même endroit.
    """
    con = _con()
    df = con.execute(f"""
        SELECT heure_locale AS h, polluant, avg(valeur) AS v
        FROM '{SERIE}'
        WHERE influence = 'Fond' AND station <> 'VENACO' AND {ETES} AND {ANNEES}
        GROUP BY 1, 2 ORDER BY 1
    """).df()
    pivot = df.pivot(index="h", columns="polluant", values="v")
    fig = go.Figure()
    for pol, couleur, nom in (("NO2", AIR_AZOTE, "Dioxyde d'azote (moteurs)"),
                              ("O3", AIR_OZONE, "Ozone")):
        serie = pivot[pol]
        rel = 100 * serie / serie.max()
        h_pic = int(rel.idxmax())
        fig.add_trace(go.Scatter(
            x=rel.index, y=rel, name=nom, mode="lines",
            line=dict(color=couleur, width=2.8),
            customdata=serie,
            hovertemplate=f"{nom}<br>%{{customdata:.1f}} µg/m³"
                          "<br>%{y:.0f} % de son maximum<extra></extra>",
        ))
        fig.add_annotation(
            x=h_pic, y=100, text=f"<b>{h_pic} h</b>", showarrow=True, arrowhead=0,
            arrowcolor=couleur, ax=0, ay=-38,
            font=dict(family=SANS, size=19, color=couleur),
        )
    fig.update_layout(
        title=dict(text="L'heure de pointe n'est pas l'heure de l'ozone"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix=" h"),
        yaxis=dict(title="Part du maximum de chaque polluant (%)",
                   ticksuffix=" %", range=[0, 118]),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        margin=dict(t=230, b=170, l=140, r=60),
        height=620,
    )
    return fig


# --- A4 : « l'air de campagne n'est pas meilleur » ----------------------------
def fig_a4_campagne_contre_ville() -> go.Figure:
    """Fréquence des dépassements, par station, la rurale mise en évidence.

    Forme : barres horizontales en TAUX et non en nombre de jours — une station rurale
    contre quatre urbaines, les effectifs ne sont pas comparables et un décompte brut
    ferait passer la campagne pour épargnée. Une seule teinte porte le propos (la station
    rurale) ; les autres restent en retrait, ce qui évite une palette de cinq couleurs
    pour une lecture qui n'en demande que deux.
    """
    con = _con()
    df = con.execute(f"""
        SELECT station,
               100.0 * count(*) FILTER (WHERE mda8 > {OBJECTIF_QUALITE}) / count(*) AS taux,
               count(*) AS jours
        FROM '{MDA8}'
        WHERE valide AND influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1 ORDER BY 2
    """).df()
    rurale = "VENACO"
    taux_rural = float(df.loc[df["station"] == rurale, "taux"].iloc[0])
    urbaines = df.loc[df["station"] != rurale, "taux"]
    devancees = int((urbaines < taux_rural).sum())
    # Le titre affirme que la campagne n'est pas MEILLEURE — pas qu'elle mène. Une garde
    # exigeant la première place serait plus stricte que l'affirmation publiée, et elle a
    # d'ailleurs sauté : Bastia Montesoro dépasse plus souvent que Venaco. Ce qu'il faut
    # tenir, c'est que la station rurale devance la majorité des urbaines.
    if devancees * 2 <= len(urbaines):
        raise ValueError(
            f"A4 : {rurale} ne devance que {devancees} station(s) urbaine(s) sur "
            f"{len(urbaines)} — le titre « l'air de campagne n'est pas meilleur » ne tient "
            "plus. À réécrire avant de publier."
        )
    couleurs = [AIR_OZONE if s == rurale else PALETTE["muted"] for s in df["station"]]
    libelles = [f"{s} <i>(rurale)</i>" if s == rurale else s for s in df["station"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["taux"], y=libelles, orientation="h",
        marker=dict(color=couleurs, line=dict(color=PALETTE["surface"], width=2)),
        text=[f"{v:.0f}" for v in df["taux"]], textposition="outside",
        textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        customdata=df["jours"],
        hovertemplate="%{y}<br>%{x:.1f} % des journées au-dessus de "
                      f"{OBJECTIF_QUALITE} µg/m³"
                      "<br>sur %{customdata} journées mesurées<extra></extra>",
    ))
    fig.add_annotation(
        text=(f"La seule station rurale de l'île<br>dépasse plus souvent que<br>"
              f"<b>{devancees} des {len(urbaines)} stations urbaines</b>."),
        xref="paper", yref="paper", x=0.99, y=0.04, xanchor="right", yanchor="bottom",
        showarrow=False, align="right",
        font=dict(family=SANS, size=18, color=PALETTE["ink"]),
        bgcolor=PALETTE["page"], borderpad=12,
    )
    fig.update_layout(
        title=dict(text="La campagne n'est pas l'endroit où l'air est le plus pur"),
        xaxis=dict(title="Part des journées d'été au-dessus de l'objectif de qualité",
                   ticksuffix=" %"),
        yaxis=dict(title=""),
        margin=dict(t=170, b=170, l=280, r=90),
        height=560,
    )
    return fig


# --- A5 : « le pire créneau » -------------------------------------------------
def fig_a5_creneau_a_eviter() -> go.Figure:
    """Cycle diurne de l'ozone en été, avec le plateau de forte charge mis en bande.

    Forme : une courbe unique (donc pas de légende — le titre nomme la série) et une bande
    verticale sur le créneau. La bande dit la PLAGE, la courbe dit la forme : deux
    informations que ni l'une ni l'autre ne porterait seule. Creux et pic sont étiquetés
    directement, ce qui évite d'écrire une valeur sur chacune des vingt-quatre heures.
    """
    con = _con()
    df = con.execute(f"""
        SELECT heure_locale AS h, avg(valeur) AS v
        FROM '{SERIE}'
        WHERE polluant = 'O3' AND influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1 ORDER BY 1
    """).df()
    pic = float(df["v"].max())
    plateau = sorted(int(h) for h, v in zip(df["h"], df["v"]) if v >= 0.95 * pic)
    if plateau != list(range(plateau[0], plateau[-1] + 1)):
        raise ValueError(
            f"A5 : créneau troué {plateau} — « entre X et Y heures » suppose une plage "
            "d'un seul tenant. Forme du titre à revoir."
        )
    h_pic = int(df.loc[df["v"].idxmax(), "h"])
    h_creux = int(df.loc[df["v"].idxmin(), "h"])
    creux = float(df["v"].min())

    fig = go.Figure()
    fig.add_vrect(
        x0=plateau[0] - 0.5, x1=plateau[-1] + 0.5,
        fillcolor=AIR_OZONE, opacity=0.10, line_width=0, layer="below",
    )
    fig.add_trace(go.Scatter(
        x=df["h"], y=df["v"], mode="lines", name="Ozone",
        line=dict(color=AIR_OZONE, width=3),
        hovertemplate="%{x} h — %{y:.0f} µg/m³<extra></extra>",
    ))
    for h, v, txt, dy in ((h_creux, creux, f"le plus respirable<br><b>{creux:.0f} µg/m³</b>", 58),
                          (h_pic, pic, f"le plus chargé<br><b>{pic:.0f} µg/m³</b>", -58)):
        fig.add_annotation(
            x=h, y=v, text=txt, showarrow=True, arrowhead=0,
            arrowcolor=PALETTE["ink_soft"], ax=0, ay=dy, align="center",
            font=dict(family=SANS, size=16, color=PALETTE["ink"]),
        )
    fig.add_annotation(
        x=(plateau[0] + plateau[-1]) / 2, y=1.0, yref="paper", yanchor="bottom", yshift=6,
        text=f"<b>{plateau[0]} h – {plateau[-1]} h</b>", showarrow=False,
        font=dict(family=SANS, size=20, color=AIR_OZONE),
    )
    fig.update_layout(
        title=dict(text="L'été, l'air est le plus chargé de 11 h à 18 h"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix=" h"),
        yaxis=dict(title="Ozone, moyenne horaire (µg/m³)"),
        margin=dict(t=200, b=170, l=140, r=60),
        height=600,
    )
    return fig


def main() -> int:
    verifier_sorties()
    d_air = date_collecte("aee_o3_venaco_continu")
    d_meteo = date_collecte("meteo_horaire_corse")

    export_html(
        fig_a1_depassements_sans_alerte(), "a1_depassements_sans_alerte", SRC_AIR, d_air,
        sous_titre=_sous_titre(
            "L'objectif de qualité pour la santé vaut 120 µg/m³ en maximum journalier "
            "sur 8 heures ; l'information du public se déclenche à 180 µg/m³ en moyenne horaire."),
    )
    export_html(
        fig_a2_ozone_et_chaleur(), "a2_ozone_et_chaleur", SRC_AIR_METEO, d_meteo,
        sous_titre=_sous_titre(
            "Températures du poste météo apparié à chaque station — ce n'est pas la même "
            "mesure au même endroit."),
        note="Les journées chaudes portent plus d'ozone ; chaleur, ensoleillement et air "
             "stagnant vont de pair, et ces mesures ne les démêlent pas.",
    )
    export_html(
        fig_a3_ozone_contre_azote(), "a3_ozone_contre_azote", SRC_AIR, d_air,
        sous_titre=_sous_titre(
            "Cinq stations mesurant les deux polluants. Chaque courbe est ramenée à son "
            "propre maximum : la figure compare des heures, pas des concentrations."),
    )
    export_html(
        fig_a4_campagne_contre_ville(), "a4_campagne_contre_ville", SRC_AIR, d_air,
        sous_titre=_sous_titre(
            "En part des journées mesurées, et non en nombre de jours : une station rurale "
            "contre quatre urbaines."),
    )
    export_html(
        fig_a5_creneau_a_eviter(), "a5_creneau_a_eviter", SRC_AIR, d_air,
        sous_titre=_sous_titre("Moyenne de chaque heure de la journée."),
        note="Le creux du petit matin est aussi le maximum de dioxyde d'azote : l'air y est "
             "moins chargé en ozone, pas plus pur.",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
