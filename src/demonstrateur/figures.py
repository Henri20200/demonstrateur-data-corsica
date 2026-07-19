"""Construit les 5 visuels du démonstrateur depuis data/processed, exporte outputs/*.html.

Chaque figure : une question du BRIEF, un périmètre écrit sur la figure, la charte
Pacioli (via viz.export_html). Usage :
    python -m demonstrateur.figures

Fraîcheur du temps réel (décision du 19/07/2026, post-audit) : au-delà de 24 h,
T1 porte un avertissement visible ; au-delà de 48 h, le titre « en ce moment »
est bloqué (titre dégradé en « au dernier relevé ») et le run termine en code 1.
"""

from __future__ import annotations

import sys

import duckdb
import plotly.graph_objects as go

from .config import DATA_PROCESSED
from .viz import PALETTE, SANS, date_collecte, export_html

MIX = (DATA_PROCESSED / "edf_mix_corse.parquet").as_posix()
COURBE = (DATA_PROCESSED / "edf_courbe_corse.parquet").as_posix()
MOIS = ["jan", "fév", "mar", "avr", "mai", "juin", "juil", "août", "sep", "oct", "nov", "déc"]

SRC_MIX = "EDF — Open Data Groupe EDF (production corse, temps réel)"
SRC_HIST = "EDF — Open Data Groupe EDF (Corse & Outre-mer)"

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
                      tickfont=dict(family=SANS, size=15, color=PALETTE["ink_soft"])),
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
        textposition="outside", textfont=dict(family=SANS, size=16, color=PALETTE["ink"]),
        hovertemplate="%{x} : %{y:.0f} MW<extra></extra>",
    ))
    juin, juil = float(charge[df["m"] == 6].iloc[0]), float(charge[df["m"] == 7].iloc[0])
    fig.add_annotation(
        x=6.0, y=juil, ax=5.0, ay=juin, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=PALETTE["accent"],
    )
    fig.add_annotation(
        x=6.0, y=juil, yshift=28, text=f"<b>+{round(100*(juil-juin)/juin):d} %</b>",
        showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
        font=dict(family=SANS, size=18, color=PALETTE["accent"]),
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
        font=dict(family=SANS, size=17, color=PALETTE["accent"]),
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
        textfont=dict(family=SANS, size=16, color=PALETTE["thermique"]),
        hovertemplate="Thermique : %{y:.0f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=h, y=df["solaire"], name="Soleil", mode="lines+text", legendrank=2,
        line=dict(color=PALETTE["solaire"], width=2.8),
        text=txt_sol, textposition="bottom center",
        textfont=dict(family=SANS, size=16, color=PALETTE["solaire"]),
        hovertemplate="Soleil : %{y:.0f} %<extra></extra>",
    ))
    # Repère au zénith solaire : le thermique reste au-dessus du soleil à son maximum.
    fig.add_vline(x=h_pic, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    fig.update_layout(
        title=dict(text="Même à son zénith, le soleil ne détrône pas le fossile"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h"),
        yaxis=dict(title="Part du mix (%)", ticksuffix=" %"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        height=600,
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
    fig.add_shape(type="rect", x0=13.45, x1=14.55, y0=0, y1=110,
                  line=dict(color=PALETTE["accent"], width=2.8),
                  fillcolor="rgba(0,0,0,0)", layer="above")
    fig.add_annotation(x=14, y=110, yshift=16, text=f"<b>14 h · {vert14:.0f} % renouvelable</b>",
                       showarrow=False, bgcolor="rgba(252,252,251,0.9)", borderpad=4,
                       font=dict(family=SANS, size=17, color=PALETTE["accent"]))
    fig.update_layout(
        title=dict(text="L'heure la plus verte pour consommer en Corse"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
        yaxis=dict(title="Part du mix (%)", range=[0, 122], ticksuffix=" %"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        height=640,
    )
    return fig


def main() -> int:
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
                sous_titre="Demande moyenne mois par mois — Corse, 2019-2024")
    export_html(fig_t2b_surcroit_horaire(), "t2b_surcroit_horaire", SRC_HIST, d_hist,
                sous_titre="Écart de demande moyenne juillet − juin, heure par heure — Corse, "
                           "2019-2024. La cause (résidents, tourisme, climatisation) n'est pas "
                           "désagrégeable ici : on montre quand, pas pourquoi.")
    export_html(fig_t3_profil(), "t3_profil_horaire", SRC_HIST, d_hist,
                sous_titre="Une journée d'été (juin-août) heure par heure — parts du mix, Corse "
                           "2019-2024. Interconnexions = câbles SACOI (Italie via la Sardaigne).")
    export_html(fig_t4_heure_verte(), "t4_heure_verte", SRC_HIST, d_hist,
                sous_titre="Part renouvelable heure par heure, moyenne annuelle — Corse 2019-2024. "
                           "Renouvelable décentralisé = solaire + éolien + bioénergies + petite hydro.")
    print("\n5 visuels exportés dans outputs/")
    return code


if __name__ == "__main__":
    sys.exit(main())
