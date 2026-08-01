"""Export des visualisations en HTML déployable en iframe sans dépendance tierce.

Plotly n'est pas chargé depuis un CDN : `plotly.min.js` est écrit UNE fois dans
outputs/ et partagé par tous les visuels — le dossier outputs/ se déploie d'un bloc.

La mention de source « Source … — données collectées le … » est câblée dans
l'export : le sourçage n'est pas optionnel. Le style (palette énergie lisible,
fond neutre clair, sans-serif) est porté par le template appliqué à chaque figure.
"""

from __future__ import annotations

import json

import plotly.graph_objects as go

from .config import BUILD_FILE, MANIFEST_FILE, OUTPUTS

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
    "accent":    "#A23D2A",  # terracotta — repère / emphase, et l'OZONE du sujet air
    "azote":     "#2E6E9E",  # bleu — le NO2, antagoniste de l'ozone (titre 3 de l'air)
}

# Couple catégoriel du sujet air, VALIDÉ au script (mode light, surface #FCFCFB) :
# bande de clarté, plancher de chroma, séparation CVD ΔE 17,9 (deutan) et 23,0 en vision
# normale, contraste ≥ 3:1. Le bleu-nuit « thermique » de l'étude électricité a été essayé
# d'abord et REFUSÉ pour cet emploi : trop sombre et trop désaturé, il échoue au plancher de
# chroma et « lit comme du gris » dès qu'il sert de série à part entière plutôt que de
# couleur sémantique du fossile.
AIR_OZONE = PALETTE["accent"]
AIR_AZOTE = PALETTE["azote"]

SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# Rampe séquentielle « or solaire » (magnitude, heatmap T5) : clarté monotone,
# pas >= 0.06, teinte unique — validée (validateur dataviz, mode ordinal). Le bout
# clair reste volontairement proche de la surface (un zéro doit se lire « rien ») :
# compensé par étiquettes directes sur les fortes valeurs, tooltip et colorbar.
RAMPE_SOLAIRE = ["#F0E1BD", "#DEC28A", "#C9A057", "#B07A2B", "#8D5E1E", "#6A4616"]
# Teinte « aucun événement » des cellules à zéro : neutre chaud, hors rampe, pour
# distinguer « rien » de « un peu » (deux natures, pas deux magnitudes).
NEUTRE_ZERO = "#EFEDE8"


def template() -> go.layout.Template:
    """Template Plotly : fond neutre, sans-serif, texte lisible, filets discrets.

    Lisibilité : étiquettes d'axes et légende en **encre pleine** (pas de gris) et
    généreusement dimensionnées ; seuls la grille et les filets restent discrets. Le
    tooltip est blanc sur encre — contraste garanti quelle que soit la couleur tracée.
    """
    # Échelle typographique (relevée le 22/07/2026, demande de lisibilité) : plancher
    # 16px pour tout texte — pied de source compris ; ticks/légende/étiquettes à 17,
    # titres d'axes à 19. Encre pleine partout (contraste ~18:1, WCAG AAA) — seuls
    # grille et filets sont discrets.
    axis = dict(
        gridcolor=PALETTE["rule_soft"], griddash="solid", zeroline=False,
        linecolor=PALETTE["rule"], ticks="outside", tickcolor=PALETTE["rule"],
        tickfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        title=dict(font=dict(family=SANS, size=19, color=PALETTE["ink"]), standoff=18),
    )
    return go.layout.Template(layout=dict(
        paper_bgcolor=PALETTE["surface"], plot_bgcolor=PALETTE["surface"],
        font=dict(family=SANS, size=17, color=PALETTE["ink"]),
        title=dict(
            font=dict(family=SANS, size=28, color=PALETTE["ink"]),
            x=0.01, xanchor="left",
            subtitle=dict(font=dict(family=SANS, size=18, color=PALETTE["ink_soft"])),
        ),
        colorway=[PALETTE["solaire"], PALETTE["renouv"], PALETTE["hydro"],
                  PALETTE["imports"], PALETTE["thermique"]],
        xaxis=axis, yaxis=axis,
        legend=dict(font=dict(family=SANS, size=17, color=PALETTE["ink"]),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=144, b=170, l=116, r=56),
        hoverlabel=dict(bgcolor=PALETTE["ink"], bordercolor=PALETTE["ink"],
                        font=dict(family=SANS, size=16, color="#FFFFFF")),
    ))


def date_collecte(source_id: str) -> str:
    """Date de collecte de la donnée RÉELLEMENT présente dans le Parquet.

    Lue dans la lignée de build (data/processed/_build.json, écrite par prepare) : elle
    reflète les octets certifiés que prepare a consommés, pas le dernier passage de fetch
    (qui peut avoir rafraîchi le manifeste sans que prepare soit rejoué — sinon la figure
    afficherait une date plus récente que la donnée qu'elle montre). Repli sur le manifeste
    si la lignée est absente (figure hors pipeline, ex. exploration)."""
    if BUILD_FILE.exists():
        build = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
        entree = build.get("sources", {}).get(source_id)
        if entree and entree.get("date_collecte"):
            return entree["date_collecte"]
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def export_html(fig, name: str, source: str, collecte: str, sous_titre: str = "",
                note: str = "", pied_decalage_px: int = -85) -> str:
    """Écrit outputs/<name>.html (fichier léger, plotly.min.js mutualisé dans outputs/).

    Applique le template, incruste la mention de source obligatoire.
    fig       : figure Plotly
    name      : nom de fichier sans extension, ex. "t4_heure_verte"
    source    : mention de source, ex. "EDF — Open Data Groupe EDF"
    collecte  : date de collecte, ex. date_collecte("edf_courbe_charge_horaire")
    sous_titre: ligne de contexte (périmètre, définition) sous le titre
    note      : note méthodologique courte, en pied sous la mention de source
                (ex. statut estimé des données)
    pied_decalage_px : décalage du HAUT du pied sous l'axe, en pixels — stable quelle
                que soit la hauteur de la figure (une fraction de zone de tracé ne
                l'est pas). Le défaut (-85) passe sous ticks + titre d'axe ; à creuser
                quand une légende occupe la bande basse (cf. T6)
    """
    preparer_figure(fig, source, collecte, sous_titre, note, pied_decalage_px)
    dest = OUTPUTS / f"{name}.html"
    # "directory" : pas de CDN (le visuel se charge sans réseau tiers) ni de JS
    # embarqué par fichier (~4,5 Mo x5) — une seule copie partagée dans outputs/.
    # div_id fixe : sans lui, Plotly tire un UUID à chaque export et deux runs sur les
    # mêmes données produisent des fichiers différents — or la planification ne committe
    # que ce qui a réellement changé.
    fig.write_html(dest, include_plotlyjs="directory", full_html=True, div_id=name)
    print(f"[ok] {dest}")
    return str(dest)


def preparer_figure(fig, source: str, collecte: str, sous_titre: str = "",
                    note: str = "", pied_decalage_px: int = -85):
    """Applique le template et incruste la mention de source obligatoire. Renvoie `fig`.

    Extraite d'`export_html` pour que la page d'assemblage obtienne EXACTEMENT les mêmes
    figures que les fichiers individuels : le sourçage est câblé une seule fois, et une
    figure ne peut pas se retrouver publiée sans sa mention parce qu'elle a pris un autre
    chemin de sortie.
    """
    fig.update_layout(template=template())
    if sous_titre:
        # Commentaire = sous-titre NATIF (un seul bloc avec le titre) : contrairement à
        # une annotation flottante, il ne peut plus télescoper la légende.
        fig.update_layout(title=dict(subtitle=dict(text=sous_titre)))
    # Mention longue : la date passe à la ligne, sinon elle est rognée à droite
    # dans une iframe étroite (les annotations Plotly ne replient pas le texte).
    sep = "<br>" if len(source) > 45 else " "
    pied = f"Source : {source}{sep}— données collectées le {collecte}"
    if note:
        pied += f"<br>{note}"
    fig.add_annotation(
        text=pied,
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=pied_decalage_px,
        showarrow=False, align="left", xanchor="left",
        # 16px + ink_soft : plancher relevé (22/07) + contraste WCAG AA (muted échouait).
        font=dict(family=SANS, size=16, color=PALETTE["ink_soft"]),
    )
    return fig
