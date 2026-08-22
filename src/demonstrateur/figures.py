"""Construit les 6 visuels du démonstrateur depuis data/processed, exporte outputs/*.html.

Chaque figure : une question du BRIEF, un périmètre écrit sur la figure, la charte
Pacioli (via viz.export_html). Usage :
    python -m demonstrateur.figures

Fraîcheur du temps réel (décision du 19/07/2026, post-audit) : au-delà de 24 h,
T1 porte un avertissement visible ; au-delà de 48 h, le titre « en ce moment »
est bloqué (titre dégradé en « au dernier relevé ») et le run termine en code 1.
"""

from __future__ import annotations

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
FRAICHEUR_AVERTIR_H = 24
FRAICHEUR_BLOQUER_H = 48


def _con():
    return duckdb.connect()


# --- Titre 1 : « en ce moment, X % de soleil » -------------------------------
def fig_t1_soleil() -> tuple[go.Figure, str, str, float]:
    con = _con()
    r = con.execute(
        f"""SELECT part_soleil, strftime(timezone('Europe/Paris',"date"),'%d/%m/%Y à %Hh%M'),
                   statut, extract(epoch FROM (now() - "date"))/3600.0
            FROM '{MIX}' ORDER BY "date" DESC LIMIT 1"""
    ).fetchone()
    val, quand, statut, age_h = r
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
    # Au-delà du seuil de blocage, l'affirmation « en ce moment » n'est plus tenable :
    # titre dégradé (garde-fou 7 de RECONNAISSANCE.md — « dégrader proprement »).
    titre = ("En ce moment, votre kWh corse est fait de <b>soleil</b>"
             if age_h <= FRAICHEUR_BLOQUER_H
             else "Au dernier relevé, votre kWh corse était fait de <b>soleil</b>")
    fig.update_layout(title=dict(text=titre), height=520)
    return fig, quand, statut, float(age_h)


# --- Titre 2 : la demande grimpe l'été (le « combien », bond juin→juillet) -----
# On montre le fait (+22 %) sans lui coller de cause : « touristes + climatiseurs »
# agrège deux effets non désagrégeables avec les seules données EDF (production par
# filière ≠ décomposition de la demande). Le « quand » — indice de la cause — est laissé
# à fig_t2b_surcroit_horaire (surcroît concentré le soir), à chacun d'en tirer sa lecture.
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
        title=dict(text="L'été, la demande d'électricité grimpe (+22 % en juillet)"),
        yaxis=dict(title="Demande moyenne (MW)"), bargap=0.38, height=560,
    )
    return fig


# --- Titre 2b : le « quand » — le surcroît de juillet se joue le soir ----------
# Écart horaire juillet − juin de la demande moyenne : la bosse est le soir (16-22h)
# et la nuit, pas un pic de milieu de journée. On donne l'indice, pas la conclusion.
def fig_t2b_surcroit_horaire() -> go.Figure:
    con = _con()
    df = con.execute(
        f"""SELECT heure_locale h,
              avg(production_totale_mw) FILTER (WHERE mois_local = 7)
              - avg(production_totale_mw) FILTER (WHERE mois_local = 6) AS delta
            FROM '{COURBE}' GROUP BY 1 ORDER BY 1"""
    ).df()
    delta = df["delta"].round(0)
    soir = df["h"].between(16, 22)
    couleurs = [PALETTE["accent"] if s else PALETTE["muted"] for s in soir]
    fig = go.Figure(go.Bar(
        x=df["h"], y=delta, marker_color=couleurs,
        hovertemplate="%{x}h : %{y:+.0f} MW<extra></extra>",
    ))
    fig.add_annotation(
        x=19, y=float(delta.max()), yshift=22, text="<b>le soir (16-22 h)</b>",
        showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
        font=dict(family=SANS, size=18, color=PALETTE["accent"]),
    )
    fig.update_layout(
        title=dict(text="Ce surcroît se joue surtout le soir"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
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
        title=dict(text="Même à son zénith, le soleil ne détrône pas le fossile"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h"),
        yaxis=dict(title="Part du mix (%)", ticksuffix=" %"),
        # Marge haute élargie : la légende (au-dessus du tracé) a SA bande, sous le
        # sous-titre — sans quoi les deux se recouvrent en iframe étroite.
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        margin=dict(t=200, b=170, l=116, r=56),
        height=640,
    )
    return fig


# --- Titre 4 : « l'heure la plus verte = 14h » -------------------------------
def fig_t4_heure_verte() -> go.Figure:
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
    # repère 14h : cadre net (sans ombre ni trame), étendu au-dessus de la pile pour ressortir
    vert14 = float(df["decentralise"][df["h"] == 14].iloc[0])
    tot14 = vert14 + float(df["grande_hydro"][df["h"] == 14].iloc[0])
    fig.add_shape(type="rect", x0=13.45, x1=14.55, y0=0, y1=110,
                  line=dict(color=PALETTE["accent"], width=2.8),
                  fillcolor="rgba(0,0,0,0)", layer="above")
    # Libellé (décision du 19/07/2026, post-audit) : le chiffre principal reste l'ENR
    # décentralisée, TOUJOURS qualifiée — jamais « renouvelable » seul ; le total avec
    # la grande hydraulique (déjà dans la pile) est donné juste dessous.
    fig.add_annotation(x=14, y=110, yshift=16,
                       text=f"<b>14 h · {vert14:.0f} % renouvelable décentralisé</b>",
                       showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
                       font=dict(family=SANS, size=18, color=PALETTE["accent"]))
    fig.add_annotation(x=14, y=110, yanchor="top", yshift=-6,
                       text=f"{tot14:.0f} % avec la grande hydraulique",
                       showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=3,
                       font=dict(family=SANS, size=16, color=PALETTE["ink"]))
    fig.update_layout(
        title=dict(text="L'heure la plus verte pour consommer en Corse"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
        yaxis=dict(title="Part du mix (%)", range=[0, 122], ticksuffix=" %"),
        # Marge haute élargie : à 4 entrées la légende se replie sur 2 rangées en
        # iframe étroite — il lui faut sa bande entière sous le sous-titre.
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        margin=dict(t=210, b=170, l=116, r=56),
        height=690,
    )
    return fig


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


# --- Titre 6 : « deux îles thermiques, mais la Sardaigne brûle du charbon » ---
# Fenêtre de la comparaison, bornée des DEUX côtés. La courbe corse déborde déjà de son
# millésime — elle porte une heure de 2025 — et EDF publiera 2025 en entier : sans borne,
# la figure comparerait une Corse 2019-2025 à une Sardaigne 2019-2024 sans que rien ne le
# signale, sous un sous-titre qui annonce « moyenne 2019-2024 ». Le côté sarde n'en a pas
# besoin aujourd'hui (le Parquet ne contient que ces six années), mais la borne y est
# répétée pour que la propriété tenue soit « les deux barres couvrent la même période », et
# non « la requête est juste aujourd'hui ». Cf. docs/VERIF_ENTSOE_TERNA.md § 5.
FENETRE_T6 = (2019, 2024)


def mix_t6() -> tuple:
    """Les deux mix de T6, avec la période effectivement couverte de chaque côté.

    Renvoie (corse, sardaigne, span_corse, span_sard) — les deux `span` étant des couples
    (année min, année max). Ils sortent d'ici plutôt que d'être supposés : c'est ce qui
    permet à un test de casser si une des deux bornes disparaît (cf. `FENETRE_T6`).
    """
    con = _con()
    a, b = FENETRE_T6
    borne = f"WHERE extract('year' FROM date_heure) BETWEEN {a} AND {b}"
    sard = con.execute(f"""
      SELECT 'Sardaigne' AS ile,
        100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique,
        100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydraulique,
        100.0*sum(solaire_mw)/sum(production_totale_mw)     AS solaire,
        100.0*sum(eolien_mw)/sum(production_totale_mw)      AS eolien,
        100.0*sum(bioenergies_mw)/sum(production_totale_mw) AS bioenergies,
        100.0*sum(autre_mw)/sum(production_totale_mw)       AS autre,
        min(extract('year' FROM date_heure))::INT           AS an_min,
        max(extract('year' FROM date_heure))::INT           AS an_max
      FROM '{SARD}' {borne}""").df().iloc[0]
    corse = con.execute(f"""
      WITH b AS (
        SELECT sum(thermique_mw) th,
               sum(hydraulique_mw+coalesce(micro_hydraulique_mw,0)) hy,
               sum(photovoltaique_mw) so, sum(eolien_mw) eo, sum(bioenergies_mw) bi,
               min(extract('year' FROM date_heure))::INT an_min,
               max(extract('year' FROM date_heure))::INT an_max
        FROM '{COURBE}' {borne})
      SELECT 100.0*th/(th+hy+so+eo+bi) thermique, 100.0*hy/(th+hy+so+eo+bi) hydraulique,
             100.0*so/(th+hy+so+eo+bi) solaire, 100.0*eo/(th+hy+so+eo+bi) eolien,
             100.0*bi/(th+hy+so+eo+bi) bioenergies, 0.0 autre, an_min, an_max
      FROM b""").df().iloc[0]
    return (corse, sard,
            (int(corse["an_min"]), int(corse["an_max"])),
            (int(sard["an_min"]), int(sard["an_max"])))


def fig_t6_corse_sardaigne() -> go.Figure:
    """Barres 100 % empilées : mix de génération local, Corse vs Sardaigne (2019-2024).

    Comparaison honnête = GÉNÉRATION seule : on exclut les imports corses (27,8 % de la
    demande) et on renormalise, car la Sardaigne (exportatrice) n'a pas de poste import
    dans les données ENTSO-E. Les deux îles sont thermiques (~55 / 69 %), mais la Sardaigne
    brûle du charbon (+ gaz de synthèse IGCC) quand la Corse tient au fioul + grande hydro.
    """
    corse, sard, _, _ = mix_t6()

    # Ordre d'empilement : deux verts (hydro sauge / éolien forêt) jamais adjacents.
    # Plus de segment « Autre » depuis le reclassement de B20 (22/08/2026) : il vaut zéro
    # des deux côtés, et une clé de légende qui ne montre aucun segment pose au lecteur une
    # question que la figure ne répond pas. Ce qui garantit qu'on ne perd rien en le
    # retirant n'est pas ce commentaire, c'est `test_sardaigne_thermique_domine`, qui tient
    # ce poste à zéro : s'il redevient non nul, la suite casse avant la publication.
    filieres = [
        ("thermique",   "Thermique",   PALETTE["thermique"]),
        ("hydraulique", "Gde hydraulique", PALETTE["hydro"]),
        ("solaire",     "Solaire",     PALETTE["solaire"]),
        ("eolien",      "Éolien",      PALETTE["renouv"]),
        ("bioenergies", "Bioénergies", PALETTE["accent"]),
    ]
    iles = ["Corse", "Sardaigne"]
    fig = go.Figure()
    for cle, libelle, couleur in filieres:
        vals = [float(corse[cle]), float(sard[cle])]
        # Étiquette directe si le segment est plus large que le texte au plancher
        # 16 px (seuil ~3 %) ; en dessous, le tooltip prend le relais.
        textes = [f"{v:.0f}%" if v >= 3 else "" for v in vals]
        fig.add_trace(go.Bar(
            y=iles, x=vals, name=libelle, orientation="h",
            marker=dict(color=couleur, line=dict(width=2, color=PALETTE["surface"])),
            text=textes, textposition="inside", insidetextanchor="middle",
            textfont=dict(family=SANS, size=16, color="#FFFFFF"),
            hovertemplate="%{y} — " + libelle + " : %{x:.1f}%<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text="Deux îles thermiques — mais la Sardaigne brûle du charbon"),
        barmode="stack",
        # Axe X masqué : les segments portent déjà leur %, l'axe ne ferait que
        # télescoper le pied de page (barres à 100 %, l'échelle est évidente).
        xaxis=dict(range=[0, 100], showgrid=False, showticklabels=False,
                   ticks="", showline=False, zeroline=False),
        yaxis=dict(showgrid=False, ticks="", autorange="reversed"),  # Corse en haut
        # Légende UNE LIGNE SOUS les barres (décision du 22/07), puis le pied
        # (source + note) une bande plus bas — chacun chez soi, plus de télescopage.
        # La marge basse absorbe la légende même repliée sur 3 rangées (iframe étroite) ;
        # le pied est abaissé d'autant via pied_y à l'export.
        legend=dict(orientation="h", y=-0.10, yanchor="top", x=0, traceorder="normal"),
        # t : de quoi loger le titre (28) et SES TROIS lignes de sous-titre (18) sans que
        # le tracé remonte dans le propos — cf. `marge_haute_minimale` dans viz.
        margin=dict(t=180, b=350, l=116, r=56),
        height=750,
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
              "L'électricité seule<br>(EDF, 2019-2024)"]

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
        SELECT extract('year' FROM timezone('Europe/Paris', date_heure)) AS annee,
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
        f"""SELECT extract(year from date_heure)::INTEGER AS annee,
              100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
              100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique
            FROM '{COURBE}' WHERE extract(year from date_heure) BETWEEN 2019 AND 2024
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
        title=dict(text="Moins d'eau, plus de thermique"),
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


def main() -> int:
    # Garde de publication (AUD-01) : aucune figure ne se dessine depuis une sortie
    # altérée — chaque Parquet est re-vérifié contre la lignée de build AVANT tout
    # export. Échec bruyant, comme prepare devant un brut non certifié : la CI le
    # re-contrôle via pytest, mais l'appel local direct à figures est gardé aussi.
    verifier_sorties()

    d_mix = date_collecte("edf_mix_temps_reel")
    d_hist = date_collecte("edf_courbe_charge_horaire")
    code = 0

    fig1, quand, statut, age_h = fig_t1_soleil()
    sous_titre_t1 = f"Dernier relevé du {quand} (statut : {statut.lower()})"
    if age_h > FRAICHEUR_BLOQUER_H:
        # Repli explicite : l'avertissement rallonge le sous-titre au-delà de la largeur
        # du visuel, et un titre Plotly se fait rogner plutôt que replier — le message
        # d'alerte disparaîtrait précisément quand il est le plus utile.
        sous_titre_t1 = ("⚠ Relevé de plus de 48 h : l'affichage « en ce moment » est "
                         "suspendu.<br>" + sous_titre_t1)
        print(f"[!] t1 : relevé vieux de {age_h:.0f} h (> {FRAICHEUR_BLOQUER_H} h) — "
              "titre « en ce moment » bloqué, visuel dégradé, run en échec.")
        code = 1
    elif age_h > FRAICHEUR_AVERTIR_H:
        sous_titre_t1 = (f"⚠ Relevé de plus de {FRAICHEUR_AVERTIR_H} h — collecte à "
                         "relancer.<br>" + sous_titre_t1)
        print(f"[!] t1 : relevé vieux de {age_h:.0f} h (> {FRAICHEUR_AVERTIR_H} h) — "
              "avertissement affiché sur le visuel.")
    export_html(fig1, "t1_soleil_live", SRC_MIX, d_mix, sous_titre=sous_titre_t1)
    export_html(fig_t2_demande_mensuelle(), "t2_demande_mensuelle", SRC_HIST, d_hist,
                sous_titre="Demande moyenne mois par mois — Corse, 2019-2024",
                note=NOTE_ESTIME)
    export_html(fig_t2b_surcroit_horaire(), "t2b_surcroit_horaire", SRC_HIST, d_hist,
                sous_titre="Écart de demande moyenne juillet − juin, heure par heure — Corse, "
                           "2019-2024.<br>La cause (résidents, tourisme, climatisation) n'est pas "
                           "désagrégeable ici : on montre quand, pas pourquoi.",
                note=NOTE_ESTIME)
    export_html(fig_t3_profil(), "t3_profil_horaire", SRC_HIST, d_hist,
                sous_titre="Une journée d'été (juin-août) heure par heure — parts du mix, Corse "
                           "2019-2024.<br>Interconnexions = câbles SACOI (Italie via la Sardaigne).",
                note=NOTE_ESTIME)
    export_html(fig_t4_heure_verte(), "t4_heure_verte", SRC_HIST, d_hist,
                sous_titre="Part renouvelable heure par heure, moyenne annuelle — Corse 2019-2024."
                           "<br>Renouvelable décentralisé = solaire + éolien + bioénergies + petite hydro.",
                note=NOTE_ESTIME)
    export_html(fig_t5_ecretement(), "t5_ecretement_solaire", SRC_ECRET,
                date_collecte("edf_ecretement_corse"),
                sous_titre="Heures de limitation ou de déconnexion imposées au photovoltaïque par "
                           "le plafond d'injection<br>— durée maximale subie par un producteur, "
                           "mois par mois. Corse, 2016-2023.",
                note="81 % des heures de bridage ont lieu de mars à juin. Même au pire mois "
                     "(mai 2020 : 141 h),<br>90,5 % de la production ENR intermittente a été "
                     "acceptée — l'écrêtement borne une durée, pas l'énergie perdue du réseau.")
    fig7, importe_elec = fig_t7_dependance_perimetres()
    export_html(
        fig7, "t7_dependance_perimetres",
        "OREGES de Corse / AUE (Lettre 2021, données 2020) & EDF — Open Data Groupe EDF",
        d_hist,
        sous_titre="Deux périmètres emboîtés, deux bases différentes — ils ne se comparent "
                   "pas de tête.<br>En haut : toute l'énergie consommée en 2020, chauffage et "
                   "carburants compris — 605 ktep,<br>soit 605 000 tonnes d'équivalent pétrole. "
                   "En bas : l'électricité servie en Corse, 2019-2024.",
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
                    sous_titre="Mix de génération électrique, moyenne 2019-2024. Comparaison à "
                               "périmètre égal :<br>génération locale seule (les 27,8 % d'imports "
                               "corses sont exclus et le reste<br>renormalisé ; la Sardaigne, "
                               "exportatrice, n'importe pas).",
                    # Plus de « 10× plus grande » : aucun multiplicateur unique ne décrit
                    # cet écart de taille — 4,5× en population, 2,8× en superficie, 7,4× en
                    # production. Un raccourci chiffré sans dénominateur est exactement ce
                    # que le §8 de l'orientation interdit. La formule redevient qualitative ;
                    # si un rapport compte pour une comparaison précise, on donnera celui-là.
                    # Elle s'arrête à deux qualificatifs, et c'est une contrainte mesurée :
                    # « dotée d'un système électrique de plus grande taille » porte le pied
                    # à 8 lignes, soit 354 px de marge basse pour 350 disponibles. On coupe
                    # le texte plutôt que de pousser `b` et `height` — la place manque au
                    # pied, pas dans la prose de l'étude, qui peut porter la phrase entière.
                    note="La Sardaigne, plus vaste et plus peuplée, fait 32 % de son courant "
                         "au charbon et 32 % au gaz de synthèse (IGCC), quasi absents en "
                         "Corse ;<br>elle a 15 fois plus d'éolien. La Corse compense par la "
                         "grande hydraulique et les câbles. Corse estimée à partir de 2021.",
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
