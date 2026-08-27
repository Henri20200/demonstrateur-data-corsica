"""Construit les 6 visuels du démonstrateur depuis data/processed, exporte outputs/*.html.

Chaque figure : une question du BRIEF, un périmètre écrit sur la figure, la charte
Pacioli (via viz.export_html). Usage :
    python -m demonstrateur.figures

Fraîcheur du temps réel : l'âge du relevé est recalculé CHEZ LE LECTEUR (27/08/2026),
une page statique ne pouvant pas vieillir toute seule. Au-delà de 12 h elle signale
une donnée ancienne, au-delà de 24 h une donnée trop ancienne, et le run termine en
code 1. Le titre, lui, ne promet plus le présent en aucun cas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import plotly.graph_objects as go

from .config import DATA_PROCESSED
from .prepare import verifier_sorties
from .viz import NEUTRE_ZERO, PALETTE, RAMPE_SOLAIRE, SANS, date_collecte, export_html

MIX = (DATA_PROCESSED / "edf_mix_corse.parquet").as_posix()
COURBE = (DATA_PROCESSED / "edf_courbe_corse.parquet").as_posix()
ECRET = (DATA_PROCESSED / "edf_ecretement_corse.parquet").as_posix()
SARD = (DATA_PROCESSED / "entsoe_sardaigne.parquet").as_posix()
MOIS = ["jan", "fév", "mar", "avr", "mai", "juin", "juil", "août", "sep", "oct", "nov", "déc"]

SRC_MIX = "EDF — Open Data Groupe EDF (production corse, temps réel)"
SRC_HIST = "EDF — Open Data Groupe EDF (Corse & Outre-mer)"
SRC_ECRET = "EDF — Open Data Groupe EDF (limitations sûreté système)"

# Mention légère du statut EDF, portée par chaque visuel historique (note de pied,
# via export_html) ; l'explication complète est dans docs/RECONNAISSANCE.md.
NOTE_ESTIME = "Données EDF estimées à partir de 2021 (2019-2020 validées)."

# Seuils de fraîcheur du temps réel (heures) — cf. docstring du module.
# Seuils de validité ÉDITORIALE de l'instantané, pas de détection de panne : l'âge se
# calcule chez le lecteur depuis le 27/08/2026, donc ils sont enfin opérants sur la
# page qu'on a sous les yeux. Cadence normale mesurée de 5 à 7 h : à 24 h la page
# pouvait avoir manqué trois cycles sans rien signaler.
# Seuils de déconnexion — SERVENT À DEUX FIGURES (T6 et T8), d'où leur place ici.
# Référentiel (cherché, pas déduit) : arrêté du 23 avril 2008 modifié — le gestionnaire
# de réseau PEUT déconnecter les installations intermittentes SANS STOCKAGE dès que la
# somme des puissances qu'elles injectent atteint 30 % de la puissance transitant sur le
# réseau (« dernier arrivé, premier déconnecté »). La Corse bénéficie d'un seuil relevé
# à 35 %, que le projet de PPE vise à porter à 45 % (Lettre OREGES 2021, p. 8).
# Ce n'est donc pas un mur physique mais un DROIT de débrancher : la part réelle peut
# le dépasser, et c'est précisément ce que montre ce visuel.
SEUIL_NATIONAL = 30
SEUIL_CORSE = 35
SEUIL_VISE = 45
# Le relèvement à 45 % était visé POUR 2023 par le projet de PPE (Lettre OREGES 2021,
# p. 8). Il n'est pas entré en vigueur : le seuil applicable reste 35 %. La figure le dit,
# sinon « seuil visé » laisserait croire à une échéance encore devant nous — alors que la
# Corse dépasse déjà, et depuis des années, un seuil qui n'existe pas encore.
ANNEE_VISEE = 2023

FRAICHEUR_AVERTIR_H = 12
FRAICHEUR_BLOQUER_H = 24


def _con():
    return duckdb.connect()


# --- Titre 1 : « au dernier relevé, X % de soleil » --------------------------
def fig_t1_soleil() -> tuple[go.Figure, str, str, float, str]:
    con = _con()
    r = con.execute(
        f"""SELECT part_soleil, strftime(timezone('Europe/Paris',"date"),'%d/%m/%Y à %Hh%M'),
                   statut, extract(epoch FROM (now() - "date"))/3600.0,
                   -- UTC suffixé Z : `%z` de DuckDB rend « +02 » sans minutes, que
                   -- Date() de JavaScript n'est pas tenu de savoir lire (et Safari
                   -- refuse). L'instant est le même, écrit dans la seule forme que
                   -- toutes les implémentations acceptent.
                   strftime(timezone('UTC', "date"), '%Y-%m-%dT%H:%M:%SZ')
            FROM '{MIX}' ORDER BY "date" DESC LIMIT 1"""
    ).fetchone()
    val, quand, statut, age_h, instant_iso = r
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number=dict(suffix=" %", font=dict(family=SANS, size=64, color=PALETTE["solaire"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=PALETTE["rule"],
                      tickfont=dict(family=SANS, size=16, color=PALETTE["ink_soft"])),
            bar=dict(color=PALETTE["solaire"], thickness=0.32),
            bgcolor=PALETTE["rule_soft"], borderwidth=0,
        ),
        domain=dict(x=[0, 1], y=[0, 0.82]),
    ))
    # Le titre nomme le RELEVÉ, jamais l'instant présent. La page est statique et
    # republiée ~4 fois par jour : ce que lit le visiteur a de 0 à 7 h, et bien plus si un
    # run échoue — 18,1 h observées du 18/08 21:03 au 19/08 15:07, 11,7 h le 24/08 quand un
    # verrou du sujet air a bloqué la publication. Aucun seuil de fraîcheur ne peut voir ces
    # gels-là : ils s'évaluent DANS le run, et un run qui échoue ne publie rien — la page
    # que lit le visiteur n'a donc jamais été soumise au test. L'heure exacte du relevé est
    # au sous-titre ; l'écart, c'est le lecteur qui le fait, et il le peut.
    # Plus de variante dégradée au seuil haut : le titre ne promettant plus le présent, il n'y a
    # plus rien à dégrader. Le garde-fou 7 garde ses dents ailleurs, et elles ne bougent
    # pas — ⚠ en tête du sous-titre et `code = 1` (cf. main()).
    titre = "Quelle part de l'électricité corse vient du <b>soleil</b> ?"
    fig.update_layout(title=dict(text=titre), height=520)
    return fig, quand, statut, float(age_h), instant_iso


# --- Titre 2 : la demande grimpe l'été (le « combien », bond juin→juillet) -----
# On montre le fait (+22 %) sans lui coller de cause : « touristes + climatiseurs »
# agrège deux effets non désagrégeables avec les seules données EDF (production par
# filière ≠ décomposition de la demande). Le « quand » — indice de la cause — est laissé
# à fig_t2b_surcroit_horaire (surcroît concentré l'après-midi et en début de soirée),
# à chacun d'en tirer sa lecture.
def fig_t2_demande_mensuelle() -> go.Figure:
    con = _con()
    df = con.execute(
        f"SELECT mois_local m, avg(production_totale_mw) charge FROM '{COURBE}' GROUP BY 1 ORDER BY 1"
    ).df()
    charge = df["charge"].round(0)
    couleurs = [PALETTE["accent"] if m in (6, 7) else PALETTE["muted"] for m in df["m"]]
    fig = go.Figure(go.Bar(
        x=MOIS, y=charge, marker_color=couleurs, width=0.62,
        text=[f"{int(v)}" if m in (6, 7) else "" for v, m in zip(charge, df["m"])],
        textposition="outside", textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        hovertemplate="%{x} : %{y:.0f} MW<extra></extra>",
    ))
    juin, juil = float(charge[df["m"] == 6].iloc[0]), float(charge[df["m"] == 7].iloc[0])
    fig.add_annotation(
        x=6.0, y=juil, ax=5.0, ay=juin, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=PALETTE["accent"],
    )
    fig.add_annotation(
        # yshift 52 : au-dessus de l'étiquette de valeur du bar de juillet (courte
        # distance = les deux se recouvrent).
        x=6.0, y=juil, yshift=52, text=f"<b>+{round(100*(juil-juin)/juin):d} %</b>",
        showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
        font=dict(family=SANS, size=19, color=PALETTE["accent"]),
    )
    fig.update_layout(
        title=dict(text="En juillet, la demande d'électricité augmente de 22 %"),
        yaxis=dict(title="Demande moyenne (MW)"), bargap=0.38, height=560,
    )
    return fig


# --- Titre 2b : le « quand » — de l'après-midi au début de soirée -------------
# Le surcroît de juillet forme un plateau, et ce plateau n'est plus écrit à la main : il
# sort de la courbe (heures à 97 % du maximum) et le titre casse s'il quitte l'après-midi.
# Jusqu'au 23/08/2026 la figure disait « le soir » et surlignait 16-22 h — une fenêtre en
# partie fabriquée par l'ancien horodatage, qui décalait la journée d'une à deux heures.
# On ne la reconstitue pas par translation : la correction a le droit de redécouper la
# journée. On donne le quand, jamais le pourquoi (résidents, tourisme, climatisation).
def fig_t2b_surcroit_horaire() -> go.Figure:
    con = _con()
    df = con.execute(
        f"""SELECT heure_locale h,
              avg(production_totale_mw) FILTER (WHERE mois_local = 7)
              - avg(production_totale_mw) FILTER (WHERE mois_local = 6) AS delta
            FROM '{COURBE}' GROUP BY 1 ORDER BY 1"""
    ).df()
    delta = df["delta"].round(0)

    # Le plateau, mesuré : les heures qui restent à 97 % du maximum. Le seuil est un
    # choix, la fenêtre non — et les deux gardes ci-dessous tiennent le titre.
    plateau = sorted(df.loc[df["delta"] >= 0.97 * df["delta"].max(), "h"].astype(int))
    h1, h2 = plateau[0], plateau[-1]
    if plateau != list(range(h1, h2 + 1)):
        raise ValueError(
            f"T2b : le surcroît ne forme plus un plateau d'un seul tenant ({plateau}) — "
            "surligner un intervalle raconterait une continuité qui n'existe pas."
        )
    if not (12 <= h1 and h2 <= 21):
        raise ValueError(
            f"T2b : le plateau du surcroît va de {h1} h à {h2} h — il déborde de "
            "l'après-midi et du début de soirée, titre et annotation à revoir."
        )

    dans = df["h"].between(h1, h2)
    couleurs = [PALETTE["accent"] if d else PALETTE["muted"] for d in dans]
    fig = go.Figure(go.Bar(
        x=df["h"], y=delta, marker_color=couleurs,
        hovertemplate="%{x}h : %{y:+.0f} MW<extra></extra>",
    ))
    fig.add_annotation(
        x=(h1 + h2) / 2, y=float(delta.max()), yshift=22,
        text=f"<b>après-midi et début de soirée ({h1}-{h2} h)</b>",
        showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
        font=dict(family=SANS, size=18, color=PALETTE["accent"]),
    )
    fig.update_layout(
        title=dict(text="En juillet, la hausse est surtout marquée de 14 h à 20 h"),
        xaxis=dict(title="Heure légale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
        yaxis=dict(title="Surcroît juillet − juin (MW)"),
        bargap=0.2, height=560,
    )
    return fig


# --- Titre 3 : même à son zénith, le soleil ne détrône pas le fossile ----------
def fig_t3_profil() -> go.Figure:
    con = _con()
    df = con.execute(f"""
        SELECT heure_locale h,
          100.0*sum(photovoltaique_mw)/sum(production_totale_mw) AS solaire,
          100.0*sum(thermique_mw)/sum(production_totale_mw)      AS thermique,
          100.0*sum(importations_mw)/sum(production_totale_mw)   AS imports
        FROM '{COURBE}' WHERE mois_local IN (6,7,8) GROUP BY 1 ORDER BY 1
    """).df()
    h = df["h"]
    # Invariant qui fonde le titre : même à son maximum, le solaire ne passe JAMAIS
    # devant le thermique. On le vérifie sur la donnée avant de figer le message.
    if (df["solaire"] >= df["thermique"]).any():
        heures = df.loc[df["solaire"] >= df["thermique"], "h"].tolist()
        raise ValueError(f"T3 : le solaire atteint/dépasse le thermique aux heures {heures} — titre à revoir.")
    i_pic = int(df["solaire"].idxmax())
    h_pic = int(df.loc[i_pic, "h"])
    sol_pic = float(df.loc[i_pic, "solaire"])
    therm_pic = float(df.loc[i_pic, "thermique"])

    # Étiquettes de valeur au zénith PORTÉES PAR LA COURBE (mode texte, sur le seul
    # point du pic) : pas de pastille qui occulte les tracés, et elles se masquent avec
    # leur série au clic sur la légende (une annotation de layout, elle, resterait).
    txt_th = ["" if j != i_pic else f"{therm_pic:.0f} %" for j in range(len(df))]
    txt_sol = ["" if j != i_pic else f"{sol_pic:.0f} %" for j in range(len(df))]

    # Interconnexions en retrait (trait fin) ; soleil + thermique = protagonistes.
    # z-order : imports dessous ; l'ordre de légende est rétabli par legendrank.
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=h, y=df["imports"], name="Interconnexions", mode="lines", legendrank=3,
        line=dict(color=PALETTE["muted"], width=1.0),
        hovertemplate="Interconnexions : %{y:.0f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=h, y=df["thermique"], name="Thermique", mode="lines+text", legendrank=1,
        line=dict(color=PALETTE["thermique"], width=2.8),
        text=txt_th, textposition="top center",
        textfont=dict(family=SANS, size=17, color=PALETTE["thermique"]),
        hovertemplate="Thermique : %{y:.0f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=h, y=df["solaire"], name="Soleil", mode="lines+text", legendrank=2,
        line=dict(color=PALETTE["solaire"], width=2.8),
        text=txt_sol, textposition="bottom center",
        textfont=dict(family=SANS, size=17, color=PALETTE["solaire"]),
        hovertemplate="Soleil : %{y:.0f} %<extra></extra>",
    ))
    # Repère au zénith solaire : le thermique reste au-dessus du soleil à son maximum.
    fig.add_vline(x=h_pic, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    fig.update_layout(
        title=dict(text="Même en été, le solaire ne dépasse pas le thermique"),
        xaxis=dict(title="Heure légale", dtick=3, ticksuffix="h"),
        yaxis=dict(title="Part du mix (%)", ticksuffix=" %"),
        # Marge haute élargie : la légende (au-dessus du tracé) a SA bande, sous le
        # sous-titre — sans quoi les deux se recouvrent en iframe étroite.
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        margin=dict(t=200, b=170, l=116, r=56),
        height=640,
    )
    return fig


# --- Titre 4 : « le créneau le plus vert se situe autour de midi » -----------
# Cette figure a nommé UNE heure — 14 h — jusqu'au 23/08/2026, et les deux définitions du
# renouvelable la désignaient ensemble. L'heure était fausse : l'heure légale corse était
# relue comme de l'UTC. Corrigée, elle se dédouble — 13 h pour le renouvelable
# décentralisé, 12 h avec la grande hydraulique — et 0,13 point sépare les deux premières
# heures du décentralisé. Nommer une heure serait plus précis que le signal ne le permet.
# On publie donc le créneau, et l'écart d'une heure entre les deux définitions s'écrit
# (dans le sous-titre) au lieu d'être masqué par un choix arbitraire entre 12 et 13.
def fig_t4_heure_verte() -> tuple[go.Figure, int, int, float, float]:
    con = _con()
    df = con.execute(f"""
        SELECT heure_locale h,
          greatest(100.0*sum(enr_distrib_mw)/sum(production_totale_mw),0)    AS decentralise,
          greatest(100.0*sum(hydraulique_mw)/sum(production_totale_mw),0)    AS grande_hydro,
          greatest(100.0*sum(thermique_mw)/sum(production_totale_mw),0)      AS thermique,
          greatest(100.0*sum(importations_mw)/sum(production_totale_mw),0)   AS imports
        FROM '{COURBE}' GROUP BY 1 ORDER BY 1
    """).df()
    h = df["h"]

    # Les deux définitions donnent chacune leur heure ; le créneau est ce qu'elles
    # bornent. Deux gardes le tiennent — au-delà d'une heure d'écart il n'y a plus de
    # créneau à surligner, et hors de la mi-journée le titre ne veut plus rien dire.
    h_dec = int(df.loc[df["decentralise"].idxmax(), "h"])
    h_tot = int(df.loc[(df["decentralise"] + df["grande_hydro"]).idxmax(), "h"])
    if abs(h_dec - h_tot) > 1:
        raise ValueError(
            f"T4 : les deux définitions du renouvelable culminent à {h_dec} h et {h_tot} h — "
            "elles ne bornent plus un créneau, la figure doit dire autre chose."
        )
    h1, h2 = min(h_dec, h_tot), max(h_dec, h_tot)
    if not (11 <= h1 and h2 <= 14):
        raise ValueError(
            f"T4 : le créneau le plus vert va de {h1} h à {h2} h — il n'est plus « autour "
            "de midi », titre et repère à revoir."
        )

    # ordre d'empilement bas -> haut ; l'hydro (claire) est bordée de foncés.
    couches = [
        ("Renouvelable décentralisé", df["decentralise"], PALETTE["renouv"]),
        ("Grande hydraulique", df["grande_hydro"], PALETTE["hydro"]),
        ("Thermique", df["thermique"], PALETTE["thermique"]),
        ("Interconnexions", df["imports"], PALETTE["imports"]),
    ]
    fig = go.Figure()
    for nom, y, col in couches:
        fig.add_trace(go.Scatter(
            x=h, y=y, name=nom, mode="lines", line=dict(color=col, width=0.8),
            stackgroup="mix", fillcolor=col,
            hovertemplate=nom + " : %{y:.0f} %<extra></extra>",
        ))
    # Repère du créneau : cadre net (sans ombre ni trame), étendu au-dessus de la pile
    # pour ressortir. Les chiffres affichés sont ceux du créneau ENTIER — la part d'une
    # heure isolée dirait un maximum, pas ce que le cadre entoure.
    creneau = con.execute(f"""
        SELECT 100.0*sum(enr_distrib_mw)/sum(production_totale_mw)                AS dec,
               100.0*sum(enr_distrib_mw+hydraulique_mw)/sum(production_totale_mw) AS tot
        FROM '{COURBE}' WHERE heure_locale BETWEEN {h1} AND {h2}
    """).df().iloc[0]
    # L'axe s'arrête à 100 % : le mix EST une somme à 100, un axe qui monte à 122 pour
    # loger une annotation fait mentir l'échelle. Le cadre suit, et l'annotation passe
    # AU-DESSUS du tracé (yref papier), dans la marge haute libérée par la légende.
    fig.add_shape(type="rect", x0=h1 - 0.55, x1=h2 + 0.55, y0=0, y1=100,
                  line=dict(color=PALETTE["accent"], width=2.8),
                  fillcolor="rgba(0,0,0,0)", layer="above")
    # Plus d'annotation flottante. Elle vivait dans la marge haute, que `verifier_titres`
    # mesure pour le TITRE et le sous-titre seuls : tout ce qu'on y pose d'autre échappe à
    # la garde et recouvre le sous-titre au premier changement de gabarit — c'est arrivé
    # deux fois. Les chiffres du créneau descendent donc dans le SOUS-TITRE, qui est
    # mesuré ; le cadre rouge reste le lien visuel avec la plage concernée.
    fig.update_layout(
        title=dict(text="Le renouvelable atteint son maximum autour de midi"),
        xaxis=dict(title="Heure légale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
        yaxis=dict(title="Part du mix (%)", range=[0, 100], ticksuffix=" %"),
        # La légende passe SOUS le tracé (même solution qu'en T6, arrêtée le 22/07) :
        # au-dessus, elle partageait la marge haute avec le sous-titre et le recouvrait
        # dès que celui-ci dépassait deux lignes. On déplace la cause, pas les pixels.
        # La légende descend SOUS le titre d'axe, pas dessus : à -0,16 elle tombait
        # dessus. La valeur est en fraction de zone de tracé, donc elle bouge avec
        # `height` — d'où le contrôle à l'œil après tout changement de gabarit.
        legend=dict(orientation="h", y=-0.30, yanchor="top", x=0, traceorder="normal"),
        margin=dict(t=170, b=330, l=116, r=56),
        height=760,
    )
    return fig, h1, h2, float(creneau["dec"]), float(creneau["tot"])


# --- Titre 5 : « c'est au printemps que la Corse bride son solaire » ---------
def fig_t5_ecretement() -> go.Figure:
    """Heatmap année × mois des heures de limitation/déconnexion du PV.

    Deux faits sur une seule grille : le couloir mars-juin (saisonnalité — soleil
    généreux + demande molle = plafond d'injection atteint) et des lignes qui
    foncent d'année en année (progression du parc PV face au plafond).
    """
    con = _con()
    df = con.execute(
        f"SELECT annee, mois_cal, duree_h FROM '{ECRET}' ORDER BY annee, mois_cal"
    ).df()
    grille = df.pivot(index="annee", columns="mois_cal", values="duree_h")
    annees = [str(a) for a in grille.index]
    zmax = float(df["duree_h"].max())

    # Palier neutre pour le zéro exact (« rien ne s'est passé »), puis rampe or
    # continue (« combien »). Le décroché à 0,5 h évite qu'un mois à 2 h de
    # limitation se confonde avec un mois sans aucune limitation.
    eps = 0.5 / zmax
    echelle = [(0.0, NEUTRE_ZERO), (eps, NEUTRE_ZERO)]
    echelle += [
        (eps + (1 - eps) * i / (len(RAMPE_SOLAIRE) - 1), c)
        for i, c in enumerate(RAMPE_SOLAIRE)
    ]

    fig = go.Figure(go.Heatmap(
        z=grille.values, x=MOIS, y=annees,
        xgap=2, ygap=2, zmin=0, zmax=zmax,
        colorscale=echelle,
        colorbar=dict(
            title=dict(text="Heures de<br>limitation<br>dans le mois",
                       font=dict(family=SANS, size=16, color=PALETTE["ink"])),
            tickfont=dict(family=SANS, size=16, color=PALETTE["ink"]),
            outlinewidth=0, thickness=14, len=0.92,
        ),
        hovertemplate="%{x} %{y} : %{z:.0f} h de limitation<extra></extra>",
    ))
    # Étiquettes directes sélectives : uniquement les mois >= 100 h (cellules
    # sombres, texte blanc lisible) — jamais une valeur sur chaque cellule.
    # Sans unité : « h » ferait déborder l'étiquette de sa cellule en iframe
    # étroite, et l'unité est déjà portée par le titre de la colorbar.
    for _, r in df[df["duree_h"] >= 100].iterrows():
        fig.add_annotation(
            x=MOIS[int(r["mois_cal"]) - 1], y=str(int(r["annee"])),
            text=f"{r['duree_h']:.0f}", showarrow=False,
            font=dict(family=SANS, size=16, color="#FFFFFF"),
        )
    fig.update_layout(
        title=dict(text="C'est au printemps, pas en été, que la Corse bride son solaire"),
        # 2016 en haut : la lecture descend le temps, et le bas (récent) fonce.
        yaxis=dict(autorange="reversed", showgrid=False, ticks=""),
        xaxis=dict(showgrid=False, ticks=""),
        # Pied à quatre lignes (source repliée en 2 + note en 2) : marge basse
        # élargie ET hauteur relevée, sinon la zone de tracé rétrécit, l'axe des
        # années s'éclaircit et le pied remonte dans les libellés de mois.
        # b et height montent ensemble : la marge basse doit loger le pied ENTIER
        # (cf. viz.marge_basse_minimale), sans quoi c'est la zone de tracé qui paie.
        margin=dict(t=144, b=245, l=116, r=56),
        height=735,
    )
    return fig


# --- Titre 6 : « la Sardaigne est plus thermique, chaque année » --------------
FENETRE_T6 = (2019, 2024)


_AN_CORSE = "annee_locale"
_AN_SARD = "extract('year' FROM (date_heure AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Rome')"


def mix_t6() -> tuple:
    """Les deux mix de T6, avec la période effectivement couverte de chaque côté.

    Renvoie (corse, sardaigne, span_corse, span_sard) — les deux `span` étant des couples
    (année min, année max). Ils sortent d'ici plutôt que d'être supposés : c'est ce qui
    permet à un test de casser si une des deux bornes disparaît (cf. `FENETRE_T6`).
    """
    con = _con()
    a, b = FENETRE_T6
    borne_c = f"WHERE {_AN_CORSE} BETWEEN {a} AND {b}"
    borne_s = f"WHERE {_AN_SARD} BETWEEN {a} AND {b}"
    sard = con.execute(f"""
      SELECT 'Sardaigne' AS ile,
        100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique,
        100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydraulique,
        100.0*sum(solaire_mw)/sum(production_totale_mw)     AS solaire,
        100.0*sum(eolien_mw)/sum(production_totale_mw)      AS eolien,
        100.0*sum(bioenergies_mw)/sum(production_totale_mw) AS bioenergies,
        100.0*sum(autre_mw)/sum(production_totale_mw)       AS autre,
        min({_AN_SARD})::INT                                AS an_min,
        max({_AN_SARD})::INT                                AS an_max
      FROM '{SARD}' {borne_s}""").df().iloc[0]
    corse = con.execute(f"""
      WITH b AS (
        SELECT sum(thermique_mw) th,
               sum(hydraulique_mw+coalesce(micro_hydraulique_mw,0)) hy,
               sum(photovoltaique_mw) so, sum(eolien_mw) eo, sum(bioenergies_mw) bi,
               min({_AN_CORSE})::INT an_min,
               max({_AN_CORSE})::INT an_max
        FROM '{COURBE}' {borne_c})
      SELECT 100.0*th/(th+hy+so+eo+bi) thermique, 100.0*hy/(th+hy+so+eo+bi) hydraulique,
             100.0*so/(th+hy+so+eo+bi) solaire, 100.0*eo/(th+hy+so+eo+bi) eolien,
             100.0*bi/(th+hy+so+eo+bi) bioenergies, 0.0 autre, an_min, an_max
      FROM b""").df().iloc[0]
    return (corse, sard,
            (int(corse["an_min"]), int(corse["an_max"])),
            (int(sard["an_min"]), int(sard["an_max"])))

def mix_t6_annuel() -> tuple:
    """Les deux parts de thermique de T6, ANNÉE PAR ANNÉE, sur la fenêtre commune.

    Même découpage que `mix_t6` — mêmes bornes, mêmes conventions d'année de chaque
    côté — mais dégroupé. C'est ce dégroupage qui porte le résultat : une moyenne de six
    ans donne 13,7 points d'écart entre les deux îles, quand l'écart réel va de 6,8 à
    20,8 points selon l'année. Renvoie (annees, part_corse, part_sarde).
    """
    con = _con()
    a, b = FENETRE_T6
    sard = con.execute(f"""
      SELECT {_AN_SARD}::INT AS an,
             100.0*sum(thermique_mw)/sum(production_totale_mw) AS part
      FROM '{SARD}' WHERE {_AN_SARD} BETWEEN {a} AND {b} GROUP BY 1 ORDER BY 1""").df()
    corse = con.execute(f"""
      WITH b AS (
        SELECT {_AN_CORSE}::INT AS an, thermique_mw th,
               hydraulique_mw + coalesce(micro_hydraulique_mw, 0) hy,
               photovoltaique_mw so, eolien_mw eo, bioenergies_mw bi
        FROM '{COURBE}' WHERE {_AN_CORSE} BETWEEN {a} AND {b})
      SELECT an, 100.0*sum(th)/sum(th+hy+so+eo+bi) AS part
      FROM b GROUP BY 1 ORDER BY 1""").df()
    if list(sard["an"]) != list(corse["an"]):
        raise ValueError(
            f"T6 : périodes divergentes — Sardaigne {list(sard['an'])}, "
            f"Corse {list(corse['an'])} ; les deux courbes doivent couvrir les mêmes années."
        )
    return [int(x) for x in corse["an"]], list(corse["part"]), list(sard["part"])


def heures_au_dessus_du_seuil(seuil: int = SEUIL_CORSE) -> tuple:
    """Part des heures de l'année où solaire + éolien dépassent `seuil`, dans les deux îles.

    Même numérateur des deux côtés — solaire + éolien, les filières que l'arrêté du
    23/04/2008 vise, et qu'aucune des deux sources ne permet de restreindre aux seules
    installations SANS stockage.

    Le dénominateur, lui, ne se laisse PAS aligner, et c'est un résultat plutôt qu'un
    défaut. Côté corse, `production_totale_mw` est ce qui alimente la charge, imports
    compris : c'est bien « la puissance transitant sur le réseau » de l'arrêté. Côté
    sarde, les deux quantités divergent de 45 % — l'île produit structurellement plus
    qu'elle ne consomme —, et rien ne dit laquelle transpose la règle. On rend donc les
    DEUX bornes ; la conclusion ne dépend pas du choix, seule son amplitude en dépend.
    Renvoie (annees, corse, sarde_generation, sarde_charge), en % des heures de l'année.
    """
    con = _con()
    a, b = FENETRE_T6
    corse = con.execute(f"""
      WITH h AS (SELECT {_AN_CORSE}::INT an,
        100.0*(greatest(photovoltaique_mw,0)+greatest(eolien_mw,0))/production_totale_mw p
        FROM '{COURBE}' WHERE {_AN_CORSE} BETWEEN {a} AND {b})
      SELECT an, 100.0*avg(CASE WHEN p > {seuil} THEN 1.0 ELSE 0.0 END)
      FROM h GROUP BY 1 ORDER BY 1""").fetchall()
    sard = con.execute(f"""
      WITH h AS (SELECT annee::INT an,
        100.0*(greatest(solaire_mw,0)+greatest(eolien_mw,0))/production_totale_mw p_gen,
        100.0*(greatest(solaire_mw,0)+greatest(eolien_mw,0))/nullif(charge_mw,0) p_ch
        FROM '{SARD}' WHERE annee BETWEEN {a} AND {b})
      SELECT an, 100.0*avg(CASE WHEN p_gen > {seuil} THEN 1.0 ELSE 0.0 END),
                 100.0*avg(CASE WHEN p_ch  > {seuil} THEN 1.0 ELSE 0.0 END)
      FROM h GROUP BY 1 ORDER BY 1""").fetchall()
    if [x[0] for x in corse] != [x[0] for x in sard]:
        raise ValueError("T6 : les deux îles ne couvrent pas les mêmes années.")
    return ([x[0] for x in corse], [x[1] for x in corse],
            [x[1] for x in sard], [x[2] for x in sard])


ANNEE_MIX_T6 = 2024  # dernier millésime commun aux deux îles


def fig_t6_corse_sardaigne() -> go.Figure:
    """Mix de génération locale des deux îles, sur UNE année — barres empilées à 100 %.

    Sur une moyenne de six ans, cette figure effaçait la dynamique sarde et se faisait
    retirer le 27/08/2026. Sur un millésime unique elle ne moyenne rien, et elle porte ce
    que la figure du seuil ne peut pas montrer : de quoi chaque île est faite.

    Trois contrastes, dont le dernier est le plus parlant. L'hydraulique, 26 % contre 1 %
    — l'écart n'est si net que depuis la sortie de la STEP du total sarde. L'éolien,
    l'image inverse, 2 % contre 16 %. Et le solaire, 16 contre 14 % : quasiment le même.
    Deux îles au même soleil ont la même part solaire ; ce qui les sépare est l'eau d'un
    côté et le vent de l'autre.

    Plus de segment « Autre » : il vaut zéro des deux côtés depuis le reclassement de
    `B20` en thermique, et une clé de légende sans segment visible pose au lecteur une
    question à laquelle la figure ne répond pas.
    """
    con = _con()
    an = ANNEE_MIX_T6
    sard = con.execute(f"""
      SELECT 100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique,
             100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydraulique,
             100.0*sum(solaire_mw)/sum(production_totale_mw)     AS solaire,
             100.0*sum(eolien_mw)/sum(production_totale_mw)      AS eolien,
             100.0*sum(bioenergies_mw)/sum(production_totale_mw) AS bioenergies,
             100.0*sum(autre_mw)/sum(production_totale_mw)       AS autre
      FROM '{SARD}' WHERE annee = {an}""").df().iloc[0]
    corse = con.execute(f"""
      WITH b AS (
        SELECT sum(thermique_mw) th,
               sum(hydraulique_mw + coalesce(micro_hydraulique_mw, 0)) hy,
               sum(photovoltaique_mw) so, sum(eolien_mw) eo, sum(bioenergies_mw) bi
        FROM '{COURBE}' WHERE {_AN_CORSE} = {an})
      SELECT 100.0*th/(th+hy+so+eo+bi) thermique, 100.0*hy/(th+hy+so+eo+bi) hydraulique,
             100.0*so/(th+hy+so+eo+bi) solaire, 100.0*eo/(th+hy+so+eo+bi) eolien,
             100.0*bi/(th+hy+so+eo+bi) bioenergies, 0.0 autre
      FROM b""").df().iloc[0]
    if float(sard["autre"]) > 0.05:
        raise ValueError(
            f"T6 : « autre » sarde vaut {sard['autre']:.2f} % — un code PSR non classé est "
            "réapparu, et la figure empilerait un segment sans contrepartie corse."
        )
    filieres = [
        ("thermique",   "Thermique",       PALETTE["thermique"]),
        ("hydraulique", "Hydraulique",     PALETTE["hydro"]),
        ("solaire",     "Solaire",         PALETTE["solaire"]),
        ("eolien",      "Éolien",          PALETTE["renouv"]),
        ("bioenergies", "Bioénergies",     PALETTE["accent"]),
    ]
    iles = ["Corse", "Sardaigne"]
    fig = go.Figure()
    for cle, libelle, couleur in filieres:
        vals = [float(corse[cle]), float(sard[cle])]
        fig.add_trace(go.Bar(
            y=iles, x=vals, name=libelle, orientation="h",
            marker=dict(color=couleur, line=dict(width=2, color=PALETTE["surface"])),
            # Étiquette directe au-delà de 3 % : en deçà le texte au plancher de 16 px
            # déborde de son segment, et le survol prend le relais.
            text=[f"{v:.0f}%" if v >= 3 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(family=SANS, size=16, color="#FFFFFF"),
            hovertemplate="%{y} — " + libelle + " : %{x:.1f}%<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text="Deux mix très différents, sauf pour le solaire"),
        barmode="stack",
        xaxis=dict(range=[0, 100], showgrid=False, showticklabels=False,
                   ticks="", showline=False, zeroline=False),
        yaxis=dict(showgrid=False, ticks="", autorange="reversed"),
        legend=dict(orientation="h", y=-0.10, yanchor="top", x=0, traceorder="normal"),
        margin=dict(t=150, b=330, l=116, r=56),
        height=680,
    )
    return fig


def fig_t6b_seuil_35() -> go.Figure:
    """Part des heures où solaire + éolien dépassent le seuil corse, deux îles, 2019-2024.

    Ce que T6 apporte et qu'aucun des deux systèmes ne dit seul : 35 % n'est pas une
    limite générale des réseaux insulaires. La Corse y passe 14,7 % de ses heures en
    2024, la Sardaigne 36,1 à 51,7 % selon le dénominateur, par plages de huit heures
    médianes. La comparaison des mix moyens, qui occupait cette place jusqu'au
    27/08/2026, donnait un classement ; celle-ci pose une question.

    La BANDE entre les deux courbes sardes est une incertitude de CONVENTION, pas un
    intervalle statistique : on ne sait pas laquelle des deux quantités transpose la
    règle corse à une île qui produit 45 % de plus qu'elle ne consomme. Elle se trace
    plutôt que de se cacher, parce qu'elle montre ce que la prose dirait moins bien —
    même la borne basse reste nettement au-dessus de la Corse.
    """
    annees, corse, sard_gen, sard_charge = heures_au_dessus_du_seuil()
    # L'invariant du titre, vérifié avant de tracer : c'est la borne BASSE qui doit rester
    # au-dessus de la Corse, sinon la conclusion dépendrait du dénominateur choisi.
    faibles = [a for a, c, s in zip(annees, corse, sard_gen) if s <= c]
    if faibles:
        raise ValueError(
            f"T6 : la borne basse sarde n'excède plus la Corse en {faibles} — la "
            "conclusion dépendrait du dénominateur, le titre est à revoir."
        )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annees, y=sard_gen, name="Sardaigne — rapporté à sa génération locale",
        mode="lines", line=dict(color=PALETTE["thermique"], width=2.4),
        hovertemplate="Sardaigne (génération) %{x} : %{y:.1f} %<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=annees, y=sard_charge, name="Sardaigne — rapporté à sa consommation",
        mode="lines", line=dict(color=PALETTE["thermique"], width=2.4, dash="dot"),
        fill="tonexty", fillcolor="rgba(140,106,74,0.18)",
        hovertemplate="Sardaigne (charge) %{x} : %{y:.1f} %<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=annees, y=corse, name="Corse", mode="lines+markers+text",
        line=dict(color=PALETTE["accent"], width=3), marker=dict(size=9),
        text=[f"{v:.0f} %" for v in corse], textposition="bottom center",
        textfont=dict(family=SANS, size=15, color=PALETTE["accent"]),
        hovertemplate="Corse %{x} : %{y:.1f} %<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"La Sardaigne dépasse beaucoup plus souvent le seuil corse "
                        f"de {SEUIL_CORSE} %"),
        xaxis=dict(title="", dtick=1, tickformat="d"),
        yaxis=dict(title="Part des heures de l'année", range=[0, 60], ticksuffix=" %"),
        legend=dict(orientation="h", y=-0.14, yanchor="top", x=0, traceorder="normal"),
        margin=dict(t=150, b=330, l=116, r=56),
        height=710,
    )
    return fig


# --- Titre 7 : « 86 % de dépendance, mais pas pour l'électricité » ------------
# Chiffres RECOPIÉS de la Lettre de l'OREGES de Corse, édition 2021 (AUE), p. 4 :
# consommation d'énergie PRIMAIRE 2020, 605 ktep (7 039 GWh), tous usages confondus
# — carburants des transports et chauffage compris, pas seulement l'électricité.
# https://www.aue.corsica/L-OREGES-publie-sa-Lettre-d-information-annuelle-pour-2021_a510.html
# On ne les déduit pas de nos Parquet : ce périmètre (énergie primaire) n'est pas
# celui de nos sources EDF (électricité). Une part publiée par son producteur se
# recopie, comme la moyenne 8 h de l'ozone se recopie du guide LCSQA.
# Verrouillés par tests/test_resultats.py (somme des postes = 100 %, total importé
# = le taux de dépendance annoncé de 86,1 %).
OREGES_2020 = {
    "petrole": 76.8,       # carburants transports 39,9 + centrales 29,1 + GPL/fioul 7,8
    "liaisons": 9.3,       # électricité importée par les câbles (Italie, Sardaigne)
    "grande_hydro": 6.2,
    "autres_enr": 4.33,    # petite hydro 0,88 + éolien 0,16 + biogaz 0,09
                           # + solaire thermique 0,30 + bois 1,8 + aérothermie 1,1
    "solaire": 3.4,        # photovoltaïque
}
OREGES_CARBURANTS = 39.9   # le poste qui creuse l'écart : 0 kWh d'électricité
OREGES_DEPENDANCE = 86.1   # taux de dépendance énergétique publié (2020)


def fig_t7_dependance_perimetres() -> tuple[go.Figure, float]:
    """Barres 100 % empilées : la dépendance corse sur deux périmètres emboîtés.

    Née d'une confusion de périmètre courante dans le débat public sur l'énergie corse :
    le taux de dépendance de 86 % y est rattaché à l'électricité, alors qu'il porte sur
    TOUTE l'énergie primaire. Le chiffre est réel — 86,1 % en 2020, Lettre de l'OREGES
    de Corse 2021, p. 4. Sur l'électricité seule, nos données EDF donnent 67,8 %.
    Contrôle croisé : pour 2020, l'OREGES publie thermique 36 % / liaisons 29,8 %, nos
    Parquet donnent 36,0 / 29,8.

    Ce docstring attribuait jusqu'au 05/08/2026 une citation à un journal et à une date
    précis. La recherche n'a retrouvé ni l'article, ni la pétition qu'il mentionnait, ni
    la phrase citée : l'attribution a été retirée plutôt que laissée invérifiable
    (cf. la fiche « Une source qui n'existait pas » de docs/SOURCES_LOCALES.md). Le
    visuel n'en dépendait pas — il compare deux périmètres, il ne corrige personne.

    Deux populations différentes réunies sur une figure — c'est ici le SUJET, donc
    chaque barre écrit son périmètre et sa base ; elles ne se comparent pas de tête.
    Renvoie la figure et la part importée de l'électricité (contrôlée à l'export).
    """
    con = _con()
    e = con.execute(f"""
      WITH b AS (
        SELECT sum(production_totale_mw) tot, sum(thermique_mw) th,
               sum(importations_mw) im, sum(hydraulique_mw) hy,
               sum(photovoltaique_mw) so,
               sum(coalesce(micro_hydraulique_mw,0)+eolien_mw+bioenergies_mw) au
        FROM '{COURBE}')
      SELECT 100.0*th/tot petrole, 100.0*im/tot liaisons, 100.0*hy/tot grande_hydro,
             100.0*au/tot autres_enr, 100.0*so/tot solaire
      FROM b""").df().iloc[0]
    elec = {c: float(e[c]) for c in OREGES_2020}
    importe_elec = elec["petrole"] + elec["liaisons"]

    # Ordre d'empilement VALIDÉ (validateur dataviz, mode light, surface #FCFCFB) :
    # or solaire et sauge hydro séparés par le vert forêt, sinon la paire or↔sauge
    # tombe à ΔE 14,4 en vision normale — sous le plancher de 15. Dans cet ordre, la
    # pire adjacence est or↔vert forêt : ΔE 18,8 normal, 11,9 protan. Les deux postes
    # importés partagent la logique de couleur du reste de l'étude (bleu-nuit = fossile,
    # violet-gris = câbles) ; l'identité ne repose jamais sur la couleur seule, chaque
    # segment porte son nom en clair.
    postes = [
        ("petrole",      "Produits pétroliers importés", PALETTE["thermique"]),
        ("liaisons",     "Électricité importée (câbles)", PALETTE["imports"]),
        ("grande_hydro", "Grande hydraulique",           PALETTE["hydro"]),
        ("autres_enr",   "Autres renouvelables locaux",  PALETTE["renouv"]),
        ("solaire",      "Solaire",                      PALETTE["solaire"]),
    ]
    barres = ["Toute l'énergie consommée<br>(OREGES, 2020)",
              "L'électricité consommée<br>(EDF, 2019-2024)"]

    # Décimale française — ce sont les seuls chiffres à décimale des visuels (ailleurs
    # des entiers) : sans cela, un « 76.8 % » voisinerait le « 39,9 % » du même segment.
    def pct(v: float) -> str:
        return f"{v:.1f} %".replace(".", ",")

    fig = go.Figure()
    for cle, libelle, couleur in postes:
        vals = [OREGES_2020[cle], elec[cle]]
        # Étiquette directe au-delà de ~5 % : en deçà, le texte au plancher 16 px ne
        # tient pas dans le segment (le tooltip prend le relais).
        textes = [pct(v) if v >= 5 else "" for v in vals]
        # Le poste qui explique TOUT l'écart entre les deux barres se dit dans le
        # segment lui-même (il est assez large) plutôt qu'en annotation flottante :
        # une étiquette posée par-dessus les barres retombe en encre sombre sur fond
        # sombre dès que la figure change de hauteur.
        if cle == "petrole":
            textes[0] = (f"{pct(OREGES_2020['petrole'])}<br>dont {pct(OREGES_CARBURANTS)} de "
                         "carburants des transports — zéro kilowattheure")
        fig.add_trace(go.Bar(
            y=barres, x=vals, name=libelle, orientation="h",
            marker=dict(color=couleur, line=dict(width=2, color=PALETTE["surface"])),
            text=textes, textposition="inside", insidetextanchor="middle",
            textfont=dict(family=SANS, size=16, color="#FFFFFF"),
            hovertext=[pct(v) for v in vals],
            hovertemplate="%{y}<br>" + libelle + " : %{hovertext}<extra></extra>",
        ))

    # Frontière « extérieur | île » et son total, AU-DESSUS de la barre : les barres
    # sont volontairement fines (bargap) pour que cette bande reste libre.
    for i, val in enumerate([OREGES_DEPENDANCE, importe_elec]):
        fig.add_shape(type="line", x0=val, x1=val, y0=i - 0.30, y1=i + 0.30,
                      line=dict(color=PALETTE["ink"], width=2))
        # En GRAS, non pour insister mais pour SÉPARER : l'étiquette du haut arrive juste
        # sous la dernière ligne de sous-titre, et en graisse normale elle s'y lisait comme
        # une quatrième ligne de texte. La graisse la range du côté du graphique.
        # Les deux étiquettes sont le même objet : les distinguer inventerait une hiérarchie.
        fig.add_annotation(
            x=val, y=i, yshift=52, text=f"<b>{pct(val)} vient de l'extérieur ▾</b>",
            showarrow=False, xanchor="right", xshift=-4,
            font=dict(family=SANS, size=17, color=PALETTE["ink"]))

    fig.update_layout(
        title=dict(text="Dépendance corse : 86 % de l'énergie, 68 % de l'électricité"),
        barmode="stack", bargap=0.52,
        # Axe X masqué : les segments portent leur %, les deux barres font 100 %.
        xaxis=dict(range=[0, 100], showgrid=False, showticklabels=False,
                   ticks="", showline=False, zeroline=False),
        yaxis=dict(showgrid=False, ticks="", autorange="reversed"),
        legend=dict(orientation="h", y=-0.16, yanchor="top", x=0, traceorder="normal"),
        # t : titre + trois lignes de sous-titre. À 150, le tracé remontait dans le texte.
        margin=dict(t=180, b=330, l=250, r=56),
        height=740,
    )
    return fig, importe_elec


# --- Titre 8 : le plafond n'est pas devant la Corse, il est derrière elle -----


def fig_t8_seuil_deconnexion() -> tuple[go.Figure, int, int]:
    """Heures par an où le solaire et l'éolien corses dépassent les seuils de déconnexion.

    Le fait que le plafond explique : la Corse ne s'approche pas de son seuil, elle vit
    largement au-dessus, et de plus en plus — le seuil visé pour la décennie (45 %) est
    lui aussi déjà franchi des centaines d'heures par an. Toute nouvelle installation
    sans stockage se raccorde donc sous menace de déconnexion, ce qui déplace la question
    du gisement (le soleil ne manque pas) vers le stockage.

    RÉSERVE portée sur la figure : nos données EDF ne distinguent pas les installations
    avec stockage — exclues du calcul réglementaire — de celles sans ; la part tracée
    agrège tout le parc. Elle dit l'ordre de grandeur de la pression sur le seuil, pas
    la conformité d'une installation. Renvoie (figure, dernière année, heures > seuil corse).
    """
    con = _con()
    df = con.execute(f"""
      WITH h AS (
        SELECT annee_locale AS annee,
               100.0*(greatest(photovoltaique_mw,0)+greatest(eolien_mw,0))
                    /production_totale_mw AS part
        FROM '{COURBE}')
      SELECT annee,
             sum(CASE WHEN part > {SEUIL_CORSE} THEN 1 ELSE 0 END) AS sup_corse,
             sum(CASE WHEN part > {SEUIL_VISE}  THEN 1 ELSE 0 END) AS sup_vise
      FROM h WHERE annee BETWEEN 2019 AND 2024 GROUP BY 1 ORDER BY 1""").df()
    annees = [int(a) for a in df["annee"]]

    # Deux seuils suffisent : celui EN VIGUEUR en Corse et celui VISÉ. Le seuil national
    # de 30 % (dont la Corse est déjà dérogataire) est dit en sous-titre — une 3e ligne
    # n'ajouterait qu'un pas de rampe au contraste insuffisant (1,68:1, validateur).
    series = [
        ("sup_vise", f"Au-dessus de {SEUIL_VISE} % — seuil visé pour {ANNEE_VISEE}, "
                     "jamais entré en vigueur", "#6A4616"),
        ("sup_corse", f"Au-dessus de {SEUIL_CORSE} % — seuil corse en vigueur",
         PALETTE["solaire"]),
    ]
    def milliers(v: int) -> str:  # séparateur de milliers français
        return f"{v:,}".replace(",", " ")

    fig = go.Figure()
    for cle, libelle, couleur in series:
        vals = [int(v) for v in df[cle]]
        fig.add_trace(go.Scatter(
            x=annees, y=vals, name=libelle, mode="lines+markers",
            line=dict(color=couleur, width=3),
            marker=dict(size=10, color=couleur,
                        line=dict(width=2, color=PALETTE["surface"])),
            hovertemplate="%{x} — " + libelle + " : %{y} h<extra></extra>",
        ))
        # Étiquette sur CHAQUE point, en ANNOTATION et non en `text` de trace : seule
        # l'annotation donne un décalage en pixels, constant quelle que soit l'échelle.
        # Avec `textposition`, l'étiquette du point à 11 h se collait au millésime de
        # l'axe. Toutes au-dessus : les deux séries restent séparées de plusieurs
        # centaines d'heures, elles ne peuvent pas se rencontrer.
        for x, v in zip(annees, vals):
            fig.add_annotation(x=x, y=v, text=milliers(v), showarrow=False, yshift=30,
                               font=dict(family=SANS, size=16, color=couleur))

    h_fin = int(df["sup_corse"].iloc[-1])
    h_deb = int(df["sup_corse"].iloc[0])
    fig.update_layout(
        title=dict(text=f"{milliers(h_fin)} heures par an au-dessus du seuil qui permet "
                        "de débrancher le solaire"),
        xaxis=dict(title=dict(text=""), dtick=1, tickformat="d"),
        # Graduations imposées : en laissant Plotly choisir, une graduation apparaissait
        # tout en haut de l'axe et venait chevaucher le sous-titre. Le haut de l'échelle
        # est calé JUSTE au-dessus de la dernière graduation utile, avec de quoi loger
        # l'étiquette du point le plus haut — calculé, jamais en dur.
        yaxis=dict(title=dict(text="heures dans l'année"), rangemode="tozero",
                   tickmode="array",
                   tickvals=list(range(0, int(df["sup_corse"].max()), 500)),
                   range=[0, float(df["sup_corse"].max()) * 1.14]),
        legend=dict(orientation="h", y=-0.16, yanchor="top", x=0, traceorder="reversed"),
        # t : titre + QUATRE lignes de sous-titre — le plus chargé de l'étude.
        margin=dict(t=205, b=330, l=116, r=60),
        height=740,
    )
    return fig, annees[-1], h_fin - h_deb


# --- Titre 9 : « moins d'eau, plus de thermique » -----------------------------
# la cause « sécheresse » est ATTRIBUÉE (A. Orsini, docs/SOURCES_LOCALES.md fiche 2),
# pas affirmée — aucune mesure de pluie ici, et les barrages de montagne intègrent
# plusieurs mois de stock.
def fig_t9_hydro_secheresse() -> go.Figure:
    con = _con()
    df = con.execute(
        f"""SELECT annee_locale::INTEGER AS annee,
              100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
              100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique
            FROM '{COURBE}' WHERE annee_locale BETWEEN 2019 AND 2024
            GROUP BY 1 ORDER BY 1"""
    ).df()
    # Invariant qui fonde le titre : d'une année à l'autre, part hydraulique et part
    # thermique varient à l'OPPOSÉ (anticorrélation forte). Vérifié sur la donnée avant
    # de figer le message ; sinon le récit « moins d'eau = plus de moteurs » tombe.
    r = float(df["hydro"].corr(df["thermique"]))
    if r > -0.8:
        raise ValueError(
            f"T9 : corrélation hydro/thermique = {r:+.2f} (attendu forte négative) — titre à revoir."
        )
    an_sec = int(df.loc[df["hydro"].idxmin(), "annee"])   # année la plus pauvre en hydraulique
    an_ther = int(df.loc[df["thermique"].idxmax(), "annee"])  # ... et la plus riche en moteurs

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["annee"], y=df["thermique"], name="Thermique", mode="lines+markers+text",
        line=dict(color=PALETTE["thermique"], width=2.8), marker=dict(size=8),
        text=[f"{v:.0f} %" for v in df["thermique"]], textposition="top center",
        textfont=dict(family=SANS, size=15, color=PALETTE["thermique"]),
        hovertemplate="Thermique %{x} : %{y:.0f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["annee"], y=df["hydro"], name="Grande hydraulique", mode="lines+markers+text",
        line=dict(color=PALETTE["hydro"], width=2.8), marker=dict(size=8),
        text=[f"{v:.0f} %" for v in df["hydro"]], textposition="bottom center",
        textfont=dict(family=SANS, size=15, color=PALETTE["hydro"]),
        hovertemplate="Grande hydraulique %{x} : %{y:.0f} %<extra></extra>",
    ))
    # Repère sur l'année la plus pauvre en hydraulique : le creux d'eau répond au pic de
    # moteurs. Étiquette au-dessus de la pile (yref haut), pas sur les tracés. Elle se
    # termine sur « le thermique au plus haut », juste au-dessus de l'étiquette 48 % du
    # tracé thermique : ce nombre a ainsi son bon antécédent, et personne ne le rapporte
    # à l'hydraulique. Le libellé double n'a de sens que si les deux extrêmes tombent la
    # MÊME année (l'anticorrélation incarnée) ; sinon on retombe sur le seul creux d'eau.
    txt = (f"<b>{an_sec} · l'eau au plus bas, le thermique au plus haut</b>"
           if an_sec == an_ther else f"<b>{an_sec} · hydraulique au plus bas</b>")
    fig.add_vline(x=an_sec, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    fig.add_annotation(
        x=an_sec, y=57, text=txt,
        showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
        font=dict(family=SANS, size=16, color=PALETTE["accent"]),
    )
    fig.update_layout(
        title=dict(text="Hydraulique et thermique évoluent en sens inverse"),
        xaxis=dict(title="Année", dtick=1),
        yaxis=dict(title="Part du mix (%)", range=[0, 60], ticksuffix=" %"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        # Le pied est long (note en deux temps → 8 lignes une fois replié) : la bande
        # basse doit l'accueillir en entier, sinon le viewport de la figure rogne la fin
        # — invisible tant qu'on développe sur écran large. Aligné sur T5/T6, qui portent
        # des notes de même longueur (b >= 250).
        margin=dict(t=180, b=300, l=116, r=56),
        height=760,
    )
    return fig


def script_fraicheur(instant_iso: str, sous_titre: str) -> str:
    """JavaScript local : réécrit le sous-titre de T1 avec l'âge du relevé À L'OUVERTURE.

    Aucune ressource tierce, aucun appel réseau — le script ne lit que deux valeurs
    incrustées ici : l'instant du relevé et les seuils. Sans JavaScript, la page reste
    juste : le sous-titre porte déjà la date et l'heure exactes du relevé, et c'est
    l'affichage de repli. Rafraîchi toutes les cinq minutes pour l'onglet resté ouvert.
    """
    base = json.dumps(sous_titre)
    return f"""
(function () {{
  var instant = new Date({json.dumps(instant_iso)});
  var AVERTIR = {FRAICHEUR_AVERTIR_H}, BLOQUER = {FRAICHEUR_BLOQUER_H};
  var base = {base};
  var cible = document.getElementById('t1_soleil_live');
  if (!cible || isNaN(instant.getTime())) return;
  function age() {{
    var h = (Date.now() - instant.getTime()) / 3600000;
    if (!isFinite(h) || h < 0) return '';
    var d;
    if (h < 1) d = "il y a moins d'une heure";
    else if (h < 24) d = 'il y a ' + Math.round(h) + ' h';
    else d = 'il y a ' + Math.round(h / 24) + ' j';
    if (h > BLOQUER) return '<br>⚠ Relevé ' + d + ' : la collecte est en panne.';
    if (h > AVERTIR) return '<br>⚠ Relevé ' + d + ' — collecte à relancer.';
    return ' — ' + d + '.';
  }}
  function poser() {{
    Plotly.relayout(cible, {{'title.subtitle.text': base + age()}});
  }}
  poser();
  setInterval(poser, 300000);
}})();
"""


def main() -> int:
    # Garde de publication (AUD-01) : aucune figure ne se dessine depuis une sortie
    # altérée — chaque Parquet est re-vérifié contre la lignée de build AVANT tout
    # export. Échec bruyant, comme prepare devant un brut non certifié : la CI le
    # re-contrôle via pytest, mais l'appel local direct à figures est gardé aussi.
    verifier_sorties()

    d_mix = date_collecte("edf_mix_temps_reel")
    d_hist = date_collecte("edf_courbe_charge_horaire")
    code = 0

    fig1, quand, statut, age_h, instant_iso = fig_t1_soleil()
    sous_titre_t1 = f"Dernier relevé du {quand} (statut : {statut.lower()})"
    if age_h > FRAICHEUR_BLOQUER_H:
        # Repli explicite : l'avertissement rallonge le sous-titre au-delà de la largeur
        # du visuel, et un titre Plotly se fait rogner plutôt que replier — le message
        # d'alerte disparaîtrait précisément quand il est le plus utile.
        sous_titre_t1 = (f"⚠ Relevé de plus de {FRAICHEUR_BLOQUER_H} h : donnée trop "
                         "ancienne pour représenter la situation actuelle.<br>"
                         + sous_titre_t1)
        print(f"[!] t1 : relevé vieux de {age_h:.0f} h (> {FRAICHEUR_BLOQUER_H} h) — "
              "avertissement de panne affiché, run en échec.")
        code = 1
    elif age_h > FRAICHEUR_AVERTIR_H:
        sous_titre_t1 = (f"⚠ Relevé de plus de {FRAICHEUR_AVERTIR_H} h — collecte à "
                         "relancer.<br>" + sous_titre_t1)
        print(f"[!] t1 : relevé vieux de {age_h:.0f} h (> {FRAICHEUR_AVERTIR_H} h) — "
              "avertissement affiché sur le visuel.")
    # L'ÂGE SE CALCULE CHEZ LE LECTEUR, pas à la génération. La page est statique et
    # republiée ~4 fois par jour ; entre deux passages elle vieillit sans que rien ne
    # bouge, et un run EN ÉCHEC ne publie pas du tout — les gels de 18,1 h (19/08/2026)
    # et 11,7 h (24/08/2026) sont passés sous les seuils sans qu'aucun avertissement
    # puisse s'afficher, puisque le seul code qui les évalue tournait dans le run qui a
    # échoué. Un âge recalculé à l'ouverture ne dépend d'aucun run : c'est la seule
    # mesure qui couvre ce cas. Les seuils restent ceux de la génération, ce qui garde
    # UNE définition de la péremption des deux côtés.
    export_html(fig1, "t1_soleil_live", SRC_MIX, d_mix, sous_titre=sous_titre_t1,
                script_apres=script_fraicheur(instant_iso, sous_titre_t1))
    export_html(fig_t2_demande_mensuelle(), "t2_demande_mensuelle", SRC_HIST, d_hist,
                sous_titre="Demande moyenne mois par mois — Corse, 2019-2024",
                note=NOTE_ESTIME)
    export_html(fig_t2b_surcroit_horaire(), "t2b_surcroit_horaire", SRC_HIST, d_hist,
                sous_titre="Écart de demande moyenne juillet − juin, heure par heure — Corse, "
                           "2019-2024.<br>Ce graphique montre quand la demande augmente, pas ce "
                           "qui explique cette hausse.",
                note=NOTE_ESTIME)
    export_html(fig_t3_profil(), "t3_profil_horaire", SRC_HIST, d_hist,
                sous_titre="Une journée d'été (juin-août) heure par heure — parts du mix, Corse "
                           "2019-2024.<br>Interconnexions = liaisons SACOI + SARCO.",
                note=NOTE_ESTIME)
    fig4, c1, c2, c_dec, c_tot = fig_t4_heure_verte()
    export_html(fig4, "t4_heure_verte", SRC_HIST, d_hist,
                sous_titre=f"Moyenne heure par heure, Corse 2019-2024.<br>"
                           f"{c1}-{c2} h : {c_dec:.0f} % de renouvelable décentralisé, "
                           f"{c_tot:.0f} % avec les grands barrages.",
                note="Renouvelable décentralisé = solaire + éolien + bioénergies + petite "
                     "hydraulique.<br>" + NOTE_ESTIME,
                pied_decalage_px=-120)
    export_html(fig_t5_ecretement(), "t5_ecretement_solaire", SRC_ECRET,
                date_collecte("edf_ecretement_corse"),
                sous_titre="Durée maximale de limitation observée chez un producteur, mois par "
                           "mois<br>— Corse, 2016-2023.",
                note="81 % des heures de bridage ont lieu de mars à juin. Même au pire mois "
                     "(mai 2020 : 141 h),<br>90,5 % de la production ENR intermittente a été "
                     "acceptée — l'écrêtement borne une durée, pas l'énergie perdue du réseau.")
    fig7, importe_elec = fig_t7_dependance_perimetres()
    export_html(
        fig7, "t7_dependance_perimetres",
        "OREGES de Corse / AUE (Lettre 2021, données 2020) & EDF — Open Data Groupe EDF",
        d_hist,
        sous_titre="Deux façons de mesurer la dépendance : toute l'énergie consommée en "
                   "Corse, puis l'électricité seule.<br>En haut : toute l'énergie consommée en "
                   "2020, transports et chauffage compris.<br>En bas : l'électricité consommée "
                   "en Corse entre 2019 et 2024.",
        note="Les 86,1 % de l'OREGES couvrent toute l'énergie — carburants et chauffage "
             "compris.<br>Contrôle croisé 2020 : OREGES 36 % / 29,8 % (thermique / "
             "liaisons) ; nos données EDF, 36,0 % / 29,8 %.<br>" + NOTE_ESTIME,
        pied_decalage_px=-130)

    fig8, an8, hausse8 = fig_t8_seuil_deconnexion()
    export_html(
        fig8, "t8_seuil_deconnexion", SRC_HIST, d_hist,
        sous_titre=f"Heures où le solaire et l'éolien dépassent {SEUIL_CORSE} % puis "
                   f"{SEUIL_VISE} % de la puissance appelée — Corse, 2019-2024.<br>"
                   f"Au-delà de ce seuil (arrêté du 23 avril 2008 : {SEUIL_NATIONAL} % "
                   f"ailleurs, {SEUIL_CORSE} % en Corse), le gestionnaire de réseau peut "
                   "débrancher<br>une installation sans stockage — « dernier arrivé, "
                   f"premier déconnecté ». Le relèvement à {SEUIL_VISE} %, visé pour "
                   f"{ANNEE_VISEE},<br>n'est jamais entré en vigueur : la Corse le "
                   "dépassait déjà avant l'échéance.",
        note="Nos données EDF ne séparent pas les installations AVEC stockage, exclues du "
             "calcul réglementaire : la courbe dit la pression sur le seuil,<br>pas la "
             "conformité d'une installation. Moyennes horaires contre un seuil instantané "
             "— les dépassements réels sont plus nombreux.<br>" + NOTE_ESTIME,
        pied_decalage_px=-130)

    export_html(fig_t9_hydro_secheresse(), "t9_hydro_secheresse", SRC_HIST, d_hist,
                sous_titre="Part dans le mix électrique, année par année — Corse, 2019-2024.",
                note="La part hydraulique varie du simple à près du double selon les années ; le "
                     "thermique prend le relais (elles varient à l'opposé, corrélation −0,95)."
                     "<br>Le lien avec la sécheresse est une hypothèse extérieure, pas une mesure "
                     "de ce graphique. " + NOTE_ESTIME)

    if Path(SARD).exists():
        export_html(fig_t6_corse_sardaigne(), "t6_corse_sardaigne",
                    "EDF (Corse) & ENTSO-E / Terna (Sardaigne)",
                    date_collecte("entsoe_sardaigne_2024"),
                    sous_titre=f"Part de chaque source dans la production locale "
                               f"d'électricité — {ANNEE_MIX_T6}.",
                    note="Production locale seule : importations corses et restitution de "
                         "stockage sarde exclues<br>des deux côtés. " + NOTE_ESTIME,
                    pied_decalage_px=-150)
        export_html(fig_t6b_seuil_35(), "t6b_seuil_35",
                    "EDF (Corse) & ENTSO-E / Terna (Sardaigne)",
                    date_collecte("entsoe_sardaigne_2024"),
                    sous_titre=f"Part des heures où solaire + éolien dépassent "
                               f"{SEUIL_CORSE} % — 2019-2024.",
                    note="Pour la Sardaigne, les deux bornes correspondent à deux "
                         "dénominateurs possibles : sa génération<br>locale et sa "
                         "consommation. Les deux donnent la même conclusion. "
                         + NOTE_ESTIME,
                    pied_decalage_px=-170)
        print("\n9 visuels exportés dans outputs/")
    else:
        print("\n8 visuels exportés dans outputs/ (t6 Sardaigne sauté — parquet ENTSO-E absent)")
    print(f"[i] t7 — part de l'électricité venue de l'extérieur : {importe_elec:.1f} % "
          f"(fossile + câbles), contre {OREGES_DEPENDANCE} % sur toute l'énergie.")
    print(f"[i] t8 — heures au-dessus du seuil corse de {SEUIL_CORSE} % : +{hausse8} h/an "
          f"entre 2019 et {an8}.")
    return code


if __name__ == "__main__":
    sys.exit(main())
