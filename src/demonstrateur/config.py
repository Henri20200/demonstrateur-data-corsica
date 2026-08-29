"""Chemins du projet. Tout le code passe par ici : aucun chemin en dur ailleurs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_ARCHIVE = ROOT / "data" / "archive"
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"

# Source éditoriale de l'étude (versionnée) et page compilée (déployée AVEC outputs/
# d'un bloc : ses iframes pointent vers les visuels voisins, plotly.min.js mutualisé).
ETUDE_SOURCE = DOCS / "etude.md"
ETUDE_HTML = OUTPUTS / "etude.html"

# Bucket PUBLIC de la vitrine, tenu comme reflet exact d'outputs/ par un `aws s3 sync
# --delete` (cf. .github/workflows/pipeline.yml). Nommé ici pour une seule raison : que le
# dépôt durable des millésimes REFUSE de s'y écrire. Un `--delete` y effacerait l'archive,
# et une archive effacée ne se signale pas — elle manque. À tenir aligné sur le workflow.
BUCKET_VITRINE = "air-et-energie-en-corse"

SOURCES_FILE = ROOT / "sources.yaml"
MANIFEST_FILE = DATA_RAW / "_manifest.json"
# Lignée de build écrite par prepare : quelle donnée certifiée (empreinte + date de
# collecte) a nourri quel Parquet. Régénérable -> non versionné (comme le reste de
# data/processed) ; c'est elle qui fait foi pour la date affichée par les figures.
BUILD_FILE = DATA_PROCESSED / "_build.json"

# Registre des millésimes : quelle version d'une source cette chaîne détenait, et entre
# quand et quand. VERSIONNÉ, comme le manifeste — il ne porte que des métadonnées, et
# c'est la seule partie de l'archive qui ne se reconstruit pas après coup. Le contenu
# archivé, lui, vit sous data/archive/<source_id>/ et n'est pas versionné (cf. archive.py).
VERSIONS_FILE = DATA_ARCHIVE / "_versions.json"
# Date de dernier contrôle par source. NON versionné à dessein : réécrit à chaque run, il
# ferait commiter le cron toutes les 6 h et démentirait « ne committe que ce qui a
# réellement changé », propriété que le dépôt met en avant.
LAST_CHECKED_FILE = DATA_ARCHIVE / "_last_checked.json"

for _d in (DATA_RAW, DATA_PROCESSED, DATA_ARCHIVE, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)
