# Démonstrateur — analyse de données ouvertes corses

Analyse reproductible construite sur des données publiques (data.corsica, Etalab/DVF,
INSEE), avec traçabilité systématique : chaque fichier collecté est daté et empreinté,
chaque visuel cite sa source. Livrable : visualisations HTML autonomes intégrables
sur [methodes-revelations.fr](https://methodes-revelations.fr).

## Arborescence

    sources.yaml          ← manifeste des sources (URL, licence, producteur)
    data/raw/             ← brut téléchargé (non versionné) + _manifest.json (versionné)
    data/processed/       ← Parquet analysable (non versionné, régénérable)
    notebooks/            ← exploration Jupyter
    src/demonstrateur/    ← pipeline propre : fetch → prepare → viz
    outputs/              ← HTML finaux pour la vitrine
    docs/BRIEF.md         ← question, critères, définition de « fini »

## Démarrage

    # environnement (au choix)
    uv venv && uv pip install -e ".[dev]"
    # ou : python -m venv .venv && .venv/Scripts/activate && pip install -e ".[dev]"

    # pipeline
    fetch-data                        # télécharge + trace (data/raw/_manifest.json)
    python -m demonstrateur.prepare   # csv.gz -> Parquet via DuckDB
    pytest                            # tests de fumée

## Principes

1. **Reproductible** : tout se régénère depuis `sources.yaml` ; rien à la main.
2. **Daté, sourcé** : la date de collecte et la licence accompagnent chaque visuel
   (voir `viz.export_html`, qui rend la mention de source obligatoire).
3. **Notebooks = brouillon** : ce qui part en livrable passe par `src/`.

## Licences des données

Données publiques sous Licence Ouverte 2.0 (Etalab) sauf mention contraire sur la
fiche du jeu — réutilisation libre avec mention du producteur, ce que ce projet fait
systématiquement.
