"""Export des visualisations en HTML autonome, intégrable en iframe sur la vitrine.

Chaque visuel embarque son pied de page « Source … — données collectées le … » :
le sourçage n'est pas une option, il est dans la fonction d'export.
"""

from __future__ import annotations

import json

from .config import MANIFEST_FILE, OUTPUTS


def date_collecte(source_id: str) -> str:
    """Renvoie la date de collecte enregistrée par fetch pour une source."""
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def export_html(fig, name: str, source: str, collecte: str) -> str:
    """Écrit outputs/<name>.html (Plotly, JS via CDN => fichier léger).

    fig      : figure Plotly
    name     : nom de fichier sans extension, ex. "prix_m2_communes"
    source   : mention de source, ex. "DVF géolocalisées (DGFiP/Etalab), Licence Ouverte 2.0"
    collecte : date de collecte, ex. date_collecte("dvf_2a_2024")
    """
    fig.add_annotation(
        text=f"Source : {source} — données collectées le {collecte}",
        xref="paper", yref="paper", x=0, y=-0.14,
        showarrow=False, align="left",
        font=dict(size=11, color="#666"),
    )
    fig.update_layout(margin=dict(b=90))

    dest = OUTPUTS / f"{name}.html"
    fig.write_html(dest, include_plotlyjs="cdn", full_html=True)
    print(f"[ok] {dest}")
    return str(dest)
