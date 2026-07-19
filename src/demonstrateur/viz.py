"""Export des visualisations en HTML autonome, intégrable en iframe sur la vitrine.

La mention de source « Source … — données collectées le … » est câblée dans
l'export : le sourçage n'est pas optionnel. Le style (palette énergie lisible,
fond neutre clair, sans-serif) est porté par le template appliqué à chaque figure.
"""

from __future__ import annotations

import json

import plotly.graph_objects as go

from .config import MANIFEST_FILE, OUTPUTS

# --- Palette (validée en distinction + couleurs choisies pour les filières) ---
PALETTE = {
    "page":      "#F7F6F3",  # fond de page (neutre chaud léger)
    "surface":   "#FCFCFB",  # surface de figure
    "ink":       "#1A1A18",  # texte primaire
    "ink_soft":  "#4A4A48",  # texte secondaire
    "muted":     "#8A8781",  # axes / labels atténués
    "rule":      "#E4E2DB",  # filet / grille
    "rule_soft": "#EEECE6",  # grille douce
    "solaire":   "#B07A2B",  # or — le solaire (jauge T1, ligne T3)
    "renouv":    "#3B6B57",  # vert forêt — renouvelable décentralisé
    "hydro":     "#7CA593",  # sauge — grande hydraulique
    "thermique": "#1B2238",  # bleu-nuit — thermique (fossile)
    "imports":   "#5B5566",  # violet-gris — interconnexions
    "accent":    "#A23D2A",  # terracotta — repère / emphase
}

SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def template() -> go.layout.Template:
    """Template Plotly : fond neutre, sans-serif, filets discrets."""
    axis = dict(
        gridcolor=PALETTE["rule_soft"], griddash="solid", zeroline=False,
        linecolor=PALETTE["rule"], ticks="outside", tickcolor=PALETTE["rule"],
        tickfont=dict(family=SANS, size=12, color=PALETTE["ink_soft"]),
        title=dict(font=dict(family=SANS, size=14, color=PALETTE["ink"]), standoff=20),
    )
    return go.layout.Template(layout=dict(
        paper_bgcolor=PALETTE["surface"], plot_bgcolor=PALETTE["surface"],
        font=dict(family=SANS, size=13, color=PALETTE["ink"]),
        title=dict(font=dict(family=SANS, size=23, color=PALETTE["ink"]), x=0.01, xanchor="left"),
        colorway=[PALETTE["solaire"], PALETTE["renouv"], PALETTE["hydro"],
                  PALETTE["imports"], PALETTE["thermique"]],
        xaxis=axis, yaxis=axis,
        legend=dict(font=dict(family=SANS, size=12, color=PALETTE["ink_soft"]),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=88, b=96, l=90, r=48),
        hoverlabel=dict(font=dict(family=SANS, size=12)),
    ))


def date_collecte(source_id: str) -> str:
    """Renvoie la date de collecte enregistrée par fetch pour une source."""
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def export_html(fig, name: str, source: str, collecte: str, sous_titre: str = "") -> str:
    """Écrit outputs/<name>.html (Plotly, JS via CDN => fichier léger).

    Applique le template, incruste la mention de source obligatoire.
    fig       : figure Plotly
    name      : nom de fichier sans extension, ex. "t4_heure_verte"
    source    : mention de source, ex. "EDF — Open Data Groupe EDF"
    collecte  : date de collecte, ex. date_collecte("edf_courbe_charge_horaire")
    sous_titre: ligne de contexte (périmètre, définition) sous le titre
    """
    fig.update_layout(template=template())
    if sous_titre:
        fig.add_annotation(
            text=sous_titre, xref="paper", yref="paper", x=0.01, y=1.10,
            showarrow=False, align="left", xanchor="left",
            font=dict(family=SANS, size=13, color=PALETTE["ink_soft"]),
        )
    fig.add_annotation(
        text=f"Source : {source} — données collectées le {collecte}",
        xref="paper", yref="paper", x=0, y=-0.16,
        showarrow=False, align="left", xanchor="left",
        font=dict(family=SANS, size=11, color=PALETTE["muted"]),
    )
    dest = OUTPUTS / f"{name}.html"
    fig.write_html(dest, include_plotlyjs="cdn", full_html=True)
    print(f"[ok] {dest}")
    return str(dest)
