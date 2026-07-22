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
        margin=dict(t=144, b=200, l=116, r=56),
        height=690,
    )
    return fig


# --- Titre 6 : « deux îles thermiques, mais la Sardaigne brûle du charbon » ---
def fig_t6_corse_sardaigne() -> go.Figure:
    """Barres 100 % empilées : mix de génération local, Corse vs Sardaigne (2019-2024).

    Comparaison honnête = GÉNÉRATION seule : on exclut les imports corses (27,8 % de la
    demande) et on renormalise, car la Sardaigne (exportatrice) n'a pas de poste import
    dans les données ENTSO-E. Les deux îles sont thermiques (~55 / 65 %), mais la Sardaigne
    brûle du charbon (+ gaz de synthèse IGCC) quand la Corse tient au fioul + grande hydro.
    """
    con = _con()
    sard = con.execute(f"""
      SELECT 'Sardaigne' AS ile,
        100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique,
        100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydraulique,
        100.0*sum(solaire_mw)/sum(production_totale_mw)     AS solaire,
        100.0*sum(eolien_mw)/sum(production_totale_mw)      AS eolien,
        100.0*sum(bioenergies_mw)/sum(production_totale_mw) AS bioenergies,
        100.0*sum(autre_mw)/sum(production_totale_mw)       AS autre
      FROM '{SARD}'""").df().iloc[0]
    corse = con.execute(f"""
      WITH b AS (
        SELECT sum(thermique_mw) th,
               sum(hydraulique_mw+coalesce(micro_hydraulique_mw,0)) hy,
               sum(photovoltaique_mw) so, sum(eolien_mw) eo, sum(bioenergies_mw) bi
        FROM '{COURBE}')
      SELECT 100.0*th/(th+hy+so+eo+bi) thermique, 100.0*hy/(th+hy+so+eo+bi) hydraulique,
             100.0*so/(th+hy+so+eo+bi) solaire, 100.0*eo/(th+hy+so+eo+bi) eolien,
             100.0*bi/(th+hy+so+eo+bi) bioenergies, 0.0 autre
      FROM b""").df().iloc[0]

    # Ordre d'empilement : deux verts (hydro sauge / éolien forêt) jamais adjacents.
    filieres = [
        ("thermique",   "Thermique",   PALETTE["thermique"]),
        ("hydraulique", "Gde hydraulique", PALETTE["hydro"]),
        ("solaire",     "Solaire",     PALETTE["solaire"]),
        ("eolien",      "Éolien",      PALETTE["renouv"]),
        ("bioenergies", "Bioénergies", PALETTE["accent"]),
        ("autre",       "Autre",       PALETTE["imports"]),
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
        margin=dict(t=144, b=260, l=116, r=56),
        height=660,
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
        sous_titre_t1 = ("⚠ Relevé de plus de 48 h : l'affichage « en ce moment » est "
                         "suspendu. " + sous_titre_t1)
        print(f"[!] t1 : relevé vieux de {age_h:.0f} h (> {FRAICHEUR_BLOQUER_H} h) — "
              "titre « en ce moment » bloqué, visuel dégradé, run en échec.")
        code = 1
    elif age_h > FRAICHEUR_AVERTIR_H:
        sous_titre_t1 = (f"⚠ Relevé de plus de {FRAICHEUR_AVERTIR_H} h — collecte à "
                         "relancer. " + sous_titre_t1)
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
                           "2019-2024. Interconnexions = câbles SACOI (Italie via la Sardaigne).",
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
    if Path(SARD).exists():
        export_html(fig_t6_corse_sardaigne(), "t6_corse_sardaigne",
                    "EDF (Corse) & ENTSO-E / Terna (Sardaigne)",
                    date_collecte("entsoe_sardaigne_2024"),
                    sous_titre="Mix de génération électrique, moyenne 2019-2024. Comparaison à "
                               "périmètre égal :<br>génération locale seule (les 27,8 % d'imports "
                               "corses sont exclus et le reste renormalisé ; la Sardaigne, "
                               "exportatrice, n'importe pas).",
                    note="La Sardaigne (10× plus grande) fait 32 % de son courant au charbon et "
                         "32 % au gaz de synthèse (IGCC), quasi absents en Corse ;<br>elle a 15 "
                         "fois plus d'éolien. La Corse compense par la grande hydraulique et les "
                         "câbles. Corse estimée à partir de 2021.",
                    pied_decalage_px=-170)
        print("\n7 visuels exportés dans outputs/")
    else:
        print("\n6 visuels exportés dans outputs/ (t6 Sardaigne sauté — parquet ENTSO-E absent)")
    return code


if __name__ == "__main__":
    sys.exit(main())
