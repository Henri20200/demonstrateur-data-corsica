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

# Mention courte : « rapportées par le LCSQA/Ineris » en toutes lettres portait la
# première ligne du pied au-delà de la largeur de la page, où elle se faisait rogner.
SRC_AIR = "Agence européenne pour l'environnement — mesures Qualitair Corse (LCSQA/Ineris)"
# Coupure EXPLICITE avant la seconde source : le pied de figure ne replie pas le texte
# (annotation Plotly), et la mention cumulée dépassait la largeur en iframe étroite.
SRC_AIR_METEO = (SRC_AIR + "<br>Températures : Météo-France")

# Seuils réglementaires (art. R221-1 du code de l'environnement, vérifié le 01/08/2026).
# Ils ne comptent PAS la même chose et ne se mêlent jamais dans une même lecture :
# l'objectif de qualité porte sur le maximum journalier de la moyenne sur 8 heures,
# le seuil d'information sur une moyenne HORAIRE.
OBJECTIF_QUALITE = 120  # µg/m³, maximum journalier de la moyenne sur 8 h
SEUIL_INFORMATION = 180  # µg/m³, moyenne horaire

ETES = "extract('month' FROM date_locale) IN (6, 7, 8)"
ANNEES = "extract('year' FROM date_locale) BETWEEN 2020 AND 2025"
# Périmètre dit en langue courante (04/08/2026) : « stations de fond, journées
# réglementairement valides » est exact mais illisible pour qui n'est pas du métier — or
# cette ligne est la SEULE que tous les lecteurs voient, sur les cinq figures. Renvoyer
# le non-initié au mini-dictionnaire, en bas de page, revient à parier qu'il ira le lire :
# la ligne doit se suffire. Le détail réglementaire vit dans la note méthodologique.
PERIMETRE = ("Six étés de mesures — 2020 à 2025, de juin à août — sur les stations de "
             "l'île installées loin des routes.")

# Titre d'axe : 17 px contre 19 au template. Long et centré sur la hauteur du tracé, un
# titre vertical monte jusque dans le sous-titre de la figure.
AXE = dict(family=SANS, size=17)

# A2 porte un titre d'axe horizontal ET une note de trois lignes : son pied descend plus
# bas que le défaut, pour que le graphique et le texte ne se touchent pas.
PIED_A2 = -105


def _con():
    return duckdb.connect()


def _sous_titre(ligne: str) -> str:
    return f"{ligne}<br>{PERIMETRE}"


# Sous-titres et notes DÉFINIS UNE FOIS et consommés à la fois par `main()` (fichiers
# individuels) et par `page_air` (page assemblée). Ils étaient recopiés dans les deux
# modules : toute correction n'était appliquée que d'un côté, et les deux versions d'une
# même figure se mettaient à raconter des choses différentes.
ST_A1 = _sous_titre(
    f"Objectif de qualité : {OBJECTIF_QUALITE} µg/m³ sur 8 heures. "
    f"Information du public : {SEUIL_INFORMATION} µg/m³ sur une heure.")
ST_A2 = _sous_titre(
    "La température est celle du poste météo le plus proche de chaque station.")
# Note tenue en lignes COURTES (< 90 signes) : le pied de figure est une annotation
# Plotly, qui ne replie pas le texte — une ligne trop longue se fait rogner à droite
# dans la page, plus étroite que le fichier isolé.
NOTE_A2 = ("Les journées chaudes portent plus d'ozone. Pourquoi il plafonne ensuite, "
           "ces mesures ne le disent pas :<br>chaleur, fort soleil et air immobile vont "
           "ensemble, et rien ici ne permet de les séparer.<br>Au-delà de 35 °C, c'est "
           "aussi la tranche qui compte le moins de journées mesurées.")
ST_A3 = _sous_titre(
    "Cinq stations mesurant les deux polluants.<br>Chaque courbe est ramenée à son "
    "propre maximum : on compare des heures, pas des concentrations.")
ST_A4 = _sous_titre(
    "En part des journées mesurées, et non en nombre de jours — "
    "une station de campagne, quatre de ville.")
ST_A5 = _sous_titre("Moyenne de chaque heure de la journée.")
NOTE_A5 = ("Le creux du petit matin est aussi le maximum de dioxyde d'azote : l'air y est "
           "moins chargé en ozone, pas plus pur.")


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
    # Le total affiché compte des JOURNÉES DISTINCTES, jamais la somme des barres : une
    # journée chargée déclenche plusieurs stations à la fois, et additionner les colonnes
    # donnerait 173 « journées » là où le calendrier n'en compte que 106 — un lecteur
    # comprendrait qu'il y a eu 173 jours de dépassement sur la période. Les barres, elles,
    # comptent bien des journées PAR STATION : chacune est juste dans son périmètre.
    journees, mesurees = con.execute(f"""
        SELECT count(DISTINCT CASE WHEN mda8 > {OBJECTIF_QUALITE} THEN date_locale END),
               count(DISTINCT date_locale)
        FROM '{MDA8}' WHERE valide AND {ETES} AND {ANNEES} AND influence = 'Fond'
    """).fetchone()
    alertes = int(df["alertes"].sum())
    if alertes:
        raise ValueError(
            f"A1 : {alertes} journée(s) atteignent {SEUIL_INFORMATION} µg/m³ — le titre "
            "affirme qu'aucune n'alerte. À réécrire avant de publier."
        )

    # Mêmes libellés qu'en A4 (casse de phrase, milieu précisé) : les deux figures se
    # suivent dans la page, et une station ne peut pas s'y appeler de deux façons.
    libelles = [f"{s.title()} <i>({'campagne' if s == 'VENACO' else 'ville'})</i>"
                for s in df["station"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["depassements"], y=libelles, orientation="h",
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
        text=(f"<b>{journees} journées d'été sur {mesurees}</b><br>où au moins une station "
              "dépasse<br>l'objectif. <b>Aucune</b> n'a alerté."),
        xref="paper", yref="paper", x=0.99, y=0.04, xanchor="right", yanchor="bottom",
        showarrow=False, align="right",
        font=dict(family=SANS, size=18, color=PALETTE["ink"]),
        bgcolor=PALETTE["page"], borderpad=12,
    )
    fig.update_layout(
        title=dict(text="Six étés de dépassements, et pas une seule alerte"),
        xaxis=dict(title=dict(text=f"Journées où CETTE station dépasse "
                                   f"{OBJECTIF_QUALITE} µg/m³ (six étés cumulés)",
                              font=AXE)),
        yaxis=dict(title=""),
        margin=dict(t=170, b=170, l=250, r=90),
        height=560,
    )
    return fig


# --- A2 : « l'air se dégrade quand il fait beau » -----------------------------
def fig_a2_ozone_et_chaleur() -> go.Figure:
    """Ozone moyen par tranche de température, avec l'effectif de chaque tranche.

    Forme : des POINTS, pas des barres (refonte du 04/08/2026). L'écart à montrer est de
    9 µg/m³ sur des valeurs de 90 à 99 : des barres imposent une base à zéro, et sur une
    échelle de 0 à 120 les quatre tranches paraissaient identiques — la figure démentait
    son propre titre. Un point ne porte pas de surface proportionnelle : il n'engage donc
    pas la base zéro, l'axe peut se resserrer sans tromper, et la montée puis le plafond
    se voient enfin. Les points ne sont pas reliés : entre deux tranches, rien n'est mesuré.

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

    # Repère horizontal sur la tranche la plus fraîche : il donne à l'œil le « départ »
    # que la base zéro ne fournit plus, et rend l'écart mesurable sans le calculer.
    base = float(df.loc[0, "ozone"])
    fig = go.Figure()
    fig.add_hline(y=base, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    # UNE seule étiquette par point (04/08/2026) : la valeur et l'écart à la tranche
    # fraîche tiennent ensemble, « 99 (+9) ». En deux textes superposés, la figure portait
    # huit étiquettes sur quatre points, plus les effectifs sous l'axe — illisible. L'unité
    # n'est écrite qu'une fois, sur le premier point : au-delà, elle se répète pour rien.
    etiquettes = []
    for i, v in enumerate(df["ozone"]):
        val = f"{v:.0f} µg/m³" if i == 0 else f"{v:.0f}"
        etiquettes.append(val if i == 0 else f"{val} (+{v - base:.0f})")
    fig.add_trace(go.Scatter(
        x=df["tranche"], y=df["ozone"], mode="markers+text",
        marker=dict(color=couleurs, size=26,
                    line=dict(color=PALETTE["surface"], width=2)),
        text=etiquettes, textposition="top center",
        textfont=dict(family=SANS, size=18, color=PALETTE["ink"]),
        cliponaxis=False,
        customdata=df["jours"],
        hovertemplate="%{x}<br>%{y:.1f} µg/m³ en moyenne<br>"
                      "sur %{customdata} journées mesurées<extra></extra>",
    ))
    fig.add_annotation(
        x=df.loc[len(df) - 1, "tranche"], y=float(df.loc[len(df) - 1, "ozone"]),
        text="au-delà, l'ozone<br>ne monte plus", showarrow=True, arrowhead=0,
        # Annotation SOUS le point : au-dessus, quelle que soit l'inclinaison, la flèche
        # traversait l'étiquette de valeur. En dessous, la zone est vide.
        arrowcolor=PALETTE["ink_soft"], ax=0, ay=72,
        font=dict(family=SANS, size=16, color=PALETTE["ink"]),
    )
    # Axe resserré autour des valeurs observées — légitime avec des points, jamais avec
    # des barres. Amplitude forcée à au moins 20 µg/m³ pour qu'un écart réel de 9 ne
    # devienne pas, à l'inverse, un précipice.
    bas, haut = float(df["ozone"].min()), float(df["ozone"].max())
    marge = max((20 - (haut - bas)) / 2, 3)
    fig.update_layout(
        title=dict(text="Plus il fait chaud, plus l'air est chargé — jusqu'à 35 °C"),
        # Titre d'axe court, et posé loin de l'axe : il servait de séparation entre le
        # graphique et le pied de page, les trois se touchaient.
        xaxis=dict(title=dict(text="Température maximale de la journée", font=AXE,
                              standoff=32)),
        yaxis=dict(title=dict(text="Ozone (µg/m³)", font=AXE),
                   range=[bas - marge, haut + marge]),
        # Bande basse généreuse : le graphique se termine franchement avant que le texte
        # de bas de figure ne commence (cf. pied_decalage_px à l'export).
        margin=dict(t=170, b=250, l=120, r=70),
        height=640,
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
        xaxis=dict(title=dict(text="Heure locale", font=AXE), dtick=3, ticksuffix=" h"),
        # Titre court : le sous-titre dit déjà de quel maximum il s'agit.
        yaxis=dict(title=dict(text="Part du maximum", font=AXE),
                   ticksuffix=" %", range=[0, 118]),
        # Séparation légende / propos d'introduction : c'est la BANDE HAUTE qu'on
        # élargit, pas la légende qu'on remonte — la remonter la rapprochait du
        # sous-titre au lieu de l'en éloigner. Elle reste collée au tracé, et c'est le
        # tracé qui descend ; la hauteur suit pour ne pas comprimer les courbes.
        legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0),
        margin=dict(t=310, b=170, l=140, r=60),
        height=700,
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
    # Explicitation (04/08/2026) : chaque station dit à quel milieu elle appartient, et
    # non la seule rurale — sans quoi le lecteur doit deviner que les quatre autres sont
    # urbaines. Casse de phrase plutôt que capitales de fichier : ce sont des lieux.
    libelles = [f"{s.title()} <i>({'campagne' if s == rurale else 'ville'})</i>"
                for s in df["station"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["taux"], y=libelles, orientation="h",
        marker=dict(color=couleurs, line=dict(color=PALETTE["surface"], width=2)),
        # L'unité est portée par chaque étiquette : « 15 » seul se lit comme un nombre
        # de jours, ce que la figure ne montre justement pas.
        text=[f"{v:.0f} %" for v in df["taux"]], textposition="outside",
        textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        customdata=df["jours"],
        hovertemplate="%{y}<br>%{x:.1f} % des journées au-dessus de "
                      f"{OBJECTIF_QUALITE} µg/m³"
                      "<br>sur %{customdata} journées mesurées<extra></extra>",
    ))
    fig.add_annotation(
        # L'explication avancée est celle que la figure précédente établit sur nos propres
        # mesures (le pic de NO2 coïncide avec le creux d'ozone) — pas un mécanisme importé.
        text=(f"Venaco, seule station de campagne de l'île,<br>dépasse plus souvent que "
              f"<b>{devancees} des {len(urbaines)} stations<br>de ville</b> : en ville, "
              "les gaz d'échappement<br>détruisent une partie de l'ozone."),
        xref="paper", yref="paper", x=0.99, y=0.04, xanchor="right", yanchor="bottom",
        showarrow=False, align="right",
        font=dict(family=SANS, size=17, color=PALETTE["ink"]),
        bgcolor=PALETTE["page"], borderpad=12,
    )
    fig.update_layout(
        title=dict(text="La campagne n'est pas l'endroit où l'air est le plus pur"),
        xaxis=dict(title=dict(text=f"Part des journées d'été où l'ozone dépasse "
                                   f"l'objectif de qualité ({OBJECTIF_QUALITE} µg/m³)",
                              font=AXE),
                   ticksuffix=" %",
                   # Air à droite : l'étiquette de la barre la plus longue est posée
                   # hors barre et se faisait rogner au bord du tracé.
                   range=[0, float(df["taux"].max()) * 1.14]),
        yaxis=dict(title=""),
        margin=dict(t=170, b=190, l=300, r=90),
        height=580,
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
        xaxis=dict(title=dict(text="Heure locale", font=AXE), dtick=3, ticksuffix=" h"),
        yaxis=dict(title=dict(text="Ozone (µg/m³)", font=AXE)),
        margin=dict(t=200, b=170, l=140, r=60),
        height=600,
    )
    return fig


def main() -> int:
    verifier_sorties()
    d_air = date_collecte("aee_o3_venaco_continu")
    d_meteo = date_collecte("meteo_horaire_corse")

    export_html(fig_a1_depassements_sans_alerte(), "a1_depassements_sans_alerte",
                SRC_AIR, d_air, sous_titre=ST_A1)
    export_html(fig_a2_ozone_et_chaleur(), "a2_ozone_et_chaleur",
                SRC_AIR_METEO, d_meteo, sous_titre=ST_A2, note=NOTE_A2,
                pied_decalage_px=PIED_A2)
    export_html(fig_a3_ozone_contre_azote(), "a3_ozone_contre_azote",
                SRC_AIR, d_air, sous_titre=ST_A3)
    export_html(fig_a4_campagne_contre_ville(), "a4_campagne_contre_ville",
                SRC_AIR, d_air, sous_titre=ST_A4)
    export_html(fig_a5_creneau_a_eviter(), "a5_creneau_a_eviter",
                SRC_AIR, d_air, sous_titre=ST_A5, note=NOTE_A5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
