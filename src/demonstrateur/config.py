"""Chemins du projet. Tout le code passe par ici : aucun chemin en dur ailleurs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"

# Source éditoriale de l'étude (versionnée) et page compilée (déployée AVEC outputs/
# d'un bloc : ses iframes pointent vers les visuels voisins, plotly.min.js mutualisé).
ETUDE_SOURCE = DOCS / "etude.md"
ETUDE_HTML = OUTPUTS / "etude.html"

SOURCES_FILE = ROOT / "sources.yaml"
MANIFEST_FILE = DATA_RAW / "_manifest.json"
# Lignée de build écrite par prepare : quelle donnée certifiée (empreinte + date de
# collecte) a nourri quel Parquet. Régénérable -> non versionné (comme le reste de
# data/processed) ; c'est elle qui fait foi pour la date affichée par les figures.
BUILD_FILE = DATA_PROCESSED / "_build.json"

for _d in (DATA_RAW, DATA_PROCESSED, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)
