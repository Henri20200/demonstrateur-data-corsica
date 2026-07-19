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
    """Template Plotly : fond neutre, sans-serif, texte lisible, filets discrets.

    Lisibilité : étiquettes d'axes et légende en **encre pleine** (pas de gris) et
    généreusement dimensionnées ; seuls la grille et les filets restent discrets. Le
    tooltip est blanc sur encre — contraste garanti quelle que soit la couleur tracée.
    """
    # Échelle typographique : plancher 14px pour tout texte (usage dataviz — RSS,
    # Datawrapper, gov.uk) ; ticks/légende/étiquettes à 16, titres d'axes à 18. Encre
    # pleine partout (contraste ~18:1, WCAG AAA) — seuls grille et filets sont discrets.
    axis = dict(
        gridcolor=PALETTE["rule_soft"], griddash="solid", zeroline=False,
        linecolor=PALETTE["rule"], ticks="outside", tickcolor=PALETTE["rule"],
        tickfont=dict(family=SANS, size=16, color=PALETTE["ink"]),
        title=dict(font=dict(family=SANS, size=18, color=PALETTE["ink"]), standoff=18),
    )
    return go.layout.Template(layout=dict(
        paper_bgcolor=PALETTE["surface"], plot_bgcolor=PALETTE["surface"],
        font=dict(family=SANS, size=16, color=PALETTE["ink"]),
        title=dict(
            font=dict(family=SANS, size=27, color=PALETTE["ink"]),
            x=0.01, xanchor="left",
            subtitle=dict(font=dict(family=SANS, size=17, color=PALETTE["ink_soft"])),
        ),
        colorway=[PALETTE["solaire"], PALETTE["renouv"], PALETTE["hydro"],
                  PALETTE["imports"], PALETTE["thermique"]],
        xaxis=axis, yaxis=axis,
        legend=dict(font=dict(family=SANS, size=16, color=PALETTE["ink"]),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=144, b=120, l=116, r=56),
        hoverlabel=dict(bgcolor=PALETTE["ink"], bordercolor=PALETTE["ink"],
                        font=dict(family=SANS, size=15, color="#FFFFFF")),
    ))


def date_collecte(source_id: str) -> str:
    """Renvoie la date de collecte enregistrée par fetch pour une source."""
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def export_html(fig, name: str, source: str, collecte: str, sous_titre: str = "",
                note: str = "") -> str:
    """Écrit outputs/<name>.html (Plotly, JS via CDN => fichier léger).

    Applique le template, incruste la mention de source obligatoire.
    fig       : figure Plotly
    name      : nom de fichier sans extension, ex. "t4_heure_verte"
    source    : mention de source, ex. "EDF — Open Data Groupe EDF"
    collecte  : date de collecte, ex. date_collecte("edf_courbe_charge_horaire")
    sous_titre: ligne de contexte (périmètre, définition) sous le titre
    note      : note méthodologique courte, en pied sous la mention de source
                (ex. statut estimé des données)
    """
    fig.update_layout(template=template())
    if sous_titre:
        # Commentaire = sous-titre NATIF (un seul bloc avec le titre) : contrairement à
        # une annotation flottante, il ne peut plus télescoper la légende.
        fig.update_layout(title=dict(subtitle=dict(text=sous_titre)))
    pied = f"Source : {source} — données collectées le {collecte}"
    if note:
        pied += f"<br>{note}"
    fig.add_annotation(
        text=pied,
        xref="paper", yref="paper", x=0, y=-0.22,
        showarrow=False, align="left", xanchor="left",
        # 14px + ink_soft : plancher dataviz + contraste WCAG AA (le gris muted échouait).
        font=dict(family=SANS, size=14, color=PALETTE["ink_soft"]),
    )
    dest = OUTPUTS / f"{name}.html"
    fig.write_html(dest, include_plotlyjs="cdn", full_html=True)
    print(f"[ok] {dest}")
    return str(dest)
