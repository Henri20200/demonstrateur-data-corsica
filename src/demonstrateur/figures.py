"""Construit les 4 visuels du démonstrateur depuis data/processed, exporte outputs/*.html.

Chaque figure : une question du BRIEF, un périmètre écrit sur la figure, la charte
Pacioli (via viz.export_html). Usage :
    python -m demonstrateur.figures
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


def _con():
    return duckdb.connect()


# --- Titre 1 : « en ce moment, X % de soleil » -------------------------------
def fig_t1_soleil() -> go.Figure:
    con = _con()
    r = con.execute(
        f"""SELECT part_soleil, strftime(timezone('Europe/Paris',"date"),'%d/%m à %Hh%M'), statut
            FROM '{MIX}' ORDER BY "date" DESC LIMIT 1"""
    ).fetchone()
    val, quand, statut = r
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number=dict(suffix=" %", font=dict(family=SANS, size=64, color=PALETTE["solaire"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=PALETTE["rule"],
                      tickfont=dict(family=SANS, size=12, color=PALETTE["muted"])),
            bar=dict(color=PALETTE["solaire"], thickness=0.32),
            bgcolor=PALETTE["rule_soft"], borderwidth=0,
        ),
        domain=dict(x=[0, 1], y=[0, 0.82]),
    ))
    fig.update_layout(
        title=dict(text="En ce moment, votre kWh corse est fait de <b>soleil</b>"),
        height=460,
    )
    return fig, quand, statut


# --- Titre 2 : « on voit les touristes arriver » (bond juin→juillet) ----------
def fig_t2_touristes() -> go.Figure:
    con = _con()
    df = con.execute(
        f"SELECT mois_local m, avg(production_totale_mw) charge FROM '{COURBE}' GROUP BY 1 ORDER BY 1"
    ).df()
    charge = df["charge"].round(0)
    couleurs = [PALETTE["accent"] if m in (6, 7) else PALETTE["muted"] for m in df["m"]]
    fig = go.Figure(go.Bar(
        x=MOIS, y=charge, marker_color=couleurs, width=0.62,
        text=[f"{int(v)}" if m in (6, 7) else "" for v, m in zip(charge, df["m"])],
        textposition="outside", textfont=dict(family=SANS, size=12, color=PALETTE["ink"]),
        hovertemplate="%{x} : %{y:.0f} MW<extra></extra>",
    ))
    juin, juil = float(charge[df["m"] == 6].iloc[0]), float(charge[df["m"] == 7].iloc[0])
    fig.add_annotation(
        x=6.0, y=juil, ax=5.0, ay=juin, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=PALETTE["accent"],
    )
    fig.add_annotation(
        x=6.0, y=juil, yshift=26, text=f"<b>+{round(100*(juil-juin)/juin):d} %</b>",
        showarrow=False, font=dict(family=SANS, size=15, color=PALETTE["accent"]),
    )
    fig.update_layout(
        title=dict(text="On voit les touristes arriver dans la courbe"),
        yaxis=dict(title="Demande moyenne (MW)"), bargap=0.38, height=520,
    )
    return fig


# --- Titre 3 : « à midi le soleil culmine ; le soir il retombe » --------------
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
    series = [
        ("Thermique", df["thermique"], PALETTE["thermique"]),
        ("Soleil", df["solaire"], PALETTE["solaire"]),
        ("Interconnexions", df["imports"], PALETTE["imports"]),
    ]
    fig = go.Figure()
    for nom, y, col in series:
        fig.add_trace(go.Scatter(
            x=h, y=y, name=nom, mode="lines", line=dict(color=col, width=2.6),
            hovertemplate=nom + " : %{y:.0f} %<extra></extra>",
        ))
    # repères midi/soir
    for hh, lab in [(14, "midi"), (21, "soir")]:
        fig.add_vline(x=hh, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    fig.add_annotation(x=14, y=float(df["solaire"].max()), yshift=14,
                       text="35 % à midi", showarrow=False,
                       font=dict(family=SANS, size=12, color=PALETTE["solaire"]))
    fig.add_annotation(x=21, y=float(df["solaire"][df["h"] >= 20].iloc[1]), yshift=-18,
                       text="6 % le soir", showarrow=False,
                       font=dict(family=SANS, size=12, color=PALETTE["solaire"]))
    fig.update_layout(
        title=dict(text="À midi le soleil culmine ; le soir, l'île rallume ses moteurs"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h"),
        yaxis=dict(title="Part du mix (%)", ticksuffix=" %"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        height=520,
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
    # repère 14h — cadre légèrement surélevé pour le détacher de la bande
    vert14 = float(df["decentralise"][df["h"] == 14].iloc[0])
    fig.add_shape(type="rect", x0=13.72, x1=14.58, y0=0, y1=104,   # ombre portée (relief)
                  line=dict(width=0), fillcolor="rgba(27,34,56,0.16)", layer="above")
    fig.add_shape(type="rect", x0=13.55, x1=14.45, y0=0, y1=105,   # cadre terracotta surélevé
                  line=dict(color=PALETTE["accent"], width=2.6),
                  fillcolor="rgba(162,61,42,0.05)", layer="above")
    fig.add_annotation(x=14, y=105, yshift=13, text=f"<b>14 h · {vert14:.0f} % renouvelable</b>",
                       showarrow=False, font=dict(family=SANS, size=13, color=PALETTE["accent"]))
    fig.update_layout(
        title=dict(text="L'heure la plus verte pour consommer en Corse"),
        xaxis=dict(title="Heure locale", dtick=3, ticksuffix="h", range=[-0.5, 23.5]),
        yaxis=dict(title="Part du mix (%)", range=[0, 112], ticksuffix=" %"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        height=560,
    )
    return fig


def main() -> int:
    d_mix = date_collecte("edf_mix_temps_reel")
    d_hist = date_collecte("edf_courbe_charge_horaire")

    fig1, quand, statut = fig_t1_soleil()
    export_html(fig1, "t1_soleil_live", SRC_MIX, d_mix,
                sous_titre=f"Dernier relevé du {quand} (statut : {statut.lower()})")
    export_html(fig_t2_touristes(), "t2_touristes", SRC_HIST, d_hist,
                sous_titre="Demande moyenne mois par mois — Corse, 2019-2024")
    export_html(fig_t3_profil(), "t3_profil_horaire", SRC_HIST, d_hist,
                sous_titre="Une journée d'été (juin-août) heure par heure — parts du mix, Corse "
                           "2019-2024. Interconnexions = câbles SACOI (Italie via la Sardaigne).")
    export_html(fig_t4_heure_verte(), "t4_heure_verte", SRC_HIST, d_hist,
                sous_titre="Part renouvelable heure par heure, moyenne annuelle — Corse 2019-2024. "
                           "Renouvelable décentralisé = solaire + éolien + bioénergies + petite hydro.")
    print("\n4 visuels exportés dans outputs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
