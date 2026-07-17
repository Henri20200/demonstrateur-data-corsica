"""Préparation des données : brut (data/raw) -> analysable (data/processed, Parquet).

DuckDB lit les .csv.gz directement, sans les charger en mémoire.
Usage :
    python -m demonstrateur.prepare
"""

from __future__ import annotations

import sys

import duckdb

from .config import DATA_PROCESSED, DATA_RAW


def dvf_corse_to_parquet() -> None:
    """Consolide les fichiers DVF 2A + 2B en un Parquet unique, ventes uniquement."""
    src = (DATA_RAW / "dvf_2*_2024.csv.gz").as_posix()
    dest = (DATA_PROCESSED / "dvf_corse_2024.parquet").as_posix()

    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT *
            FROM read_csv_auto('{src}', header = true, union_by_name = true)
            WHERE nature_mutation = 'Vente'
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {dest} — {n:,} mutations (ventes)")


def main() -> int:
    dvf_corse_to_parquet()
    # Ajouter ici la préparation du jeu data.corsica une fois sélectionné.
    return 0


if __name__ == "__main__":
    sys.exit(main())
