"""Préparation des données : brut (data/raw) -> analysable (data/processed, Parquet).

DuckDB lit les CSV(.gz) directement, sans les charger en mémoire.
Usage :
    python -m demonstrateur.prepare

Garde-fous (cf. docs/RECONNAISSANCE.md) :
 - mix temps réel : la ligne au bouclage cassé (`total` corrompu) est retirée
   (filtre par le bouclage, robuste au fuseau).
 - courbe Corse : **audit des NULL par colonne**. Une GRANDE filière NULL fait
   ÉCHOUER la préparation — on ne coalesce jamais aveuglément (un `+0` sur le PV ou
   le thermique fabriquerait un faux aplomb). Seule `micro_hydraulique_mw` tolère des
   NULL (absente en 2024) et est coalescée à 0, ce que le bouclage 2024 justifie
   (`production_totale_mw` l'exclut aussi). Un test `ENR >= solaire` verrouille la sortie.
"""

from __future__ import annotations

import sys

import duckdb

from .config import DATA_PROCESSED, DATA_RAW

MIX = (DATA_RAW / "edf_mix_temps_reel.csv").as_posix()
COURBE = (DATA_RAW / "edf_courbe_charge_horaire.csv").as_posix()

# Filières historiques toujours renseignées (leur NULL = incident à signaler, pas à masquer).
GRANDES_FILIERES = [
    "production_totale_mw", "thermique_mw", "hydraulique_mw",
    "photovoltaique_mw", "eolien_mw", "bioenergies_mw", "importations_mw",
]


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


def _auditer_null(con, table_expr: str, colonnes: list[str], source: str) -> None:
    """Échoue si une filière censée toujours renseignée contient des NULL.

    Règle (cf. RECONNAISSANCE.md) : un NULL dans un numérateur n'est pas neutre s'il
    reste au dénominateur. On ne coalesce PAS aveuglément une grande filière.
    """
    sel = ", ".join(f'count(*) FILTER (WHERE "{c}" IS NULL) AS "{c}"' for c in colonnes)
    row = con.execute(f"SELECT {sel} FROM {table_expr}").fetchone()
    fautives = {c: n for c, n in zip(colonnes, row) if n}
    if fautives:
        raise ValueError(
            f"{source} : NULL dans une filière toujours attendue {fautives} — trancher "
            "zéro-vrai vs donnée manquante avant de coalescer (cf. docs/RECONNAISSANCE.md)."
        )


def mix_temps_reel_to_parquet() -> None:
    """Parquet du mix temps réel Corse (15 min), ligne au bouclage cassé retirée."""
    dest = (DATA_PROCESSED / "edf_mix_corse.parquet").as_posix()
    con = duckdb.connect()
    src = f"read_csv_auto('{MIX}', delim=';', header=true)"
    # `total` corrompu (ligne à −91 MW) -> bouclage cassé ; drop robuste au fuseau.
    propre = (
        f"(SELECT * FROM {src} "
        "WHERE abs(total-(filiere_thermique+filiere_enr_distrib+hydraulique+liaisons)) <= 50)"
    )
    con.execute(
        f"""
        COPY (
          SELECT *,
            extract('hour' FROM timezone('Europe/Paris', "date"))                 AS heure_locale,
            round(100.0*photovoltaique/total, 2)                                  AS part_soleil,
            round(100.0*(photovoltaique+eolien+bioenergies+micro_hydro)/total, 2) AS part_enr_sym
          FROM {propre}
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {dest} — {n:,} pas de 15 min (Corse temps réel)")


def courbe_corse_to_parquet() -> None:
    """Parquet de la courbe horaire, filtrée Corse, avec ENR distribuée symétrique.

    Colonnes Outre-mer vides (bagasse/geothermie/stockage) et coût (hors périmètre)
    écartées. `micro_hydraulique_mw` gardée brute + coalescée dans l'ENR (cf. audit).
    """
    dest = (DATA_PROCESSED / "edf_courbe_corse.parquet").as_posix()
    con = duckdb.connect()
    src = f"read_csv_auto('{COURBE}', delim=';', header=true)"
    corse = f"(SELECT * FROM {src} WHERE territoire='Corse' AND production_totale_mw > 0)"

    _auditer_null(con, corse, GRANDES_FILIERES, "courbe Corse")  # micro exemptée (doc)

    enr = "(photovoltaique_mw+eolien_mw+bioenergies_mw+coalesce(micro_hydraulique_mw,0))"
    con.execute(
        f"""
        COPY (
          SELECT date_heure, statut,
            extract('hour'  FROM timezone('Europe/Paris', date_heure)) AS heure_locale,
            extract('month' FROM timezone('Europe/Paris', date_heure)) AS mois_local,
            production_totale_mw, thermique_mw, hydraulique_mw, micro_hydraulique_mw,
            photovoltaique_mw, eolien_mw, bioenergies_mw, importations_mw,
            {enr}                                       AS enr_distrib_mw,
            round(100.0*{enr}/production_totale_mw, 2)  AS part_enr_distrib
          FROM {corse}
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    # Garde de sortie : à l'AGRÉGAT (par heure), l'ensemble ENR ne peut passer sous son
    # sous-ensemble solaire — c'est l'invariant qui a révélé le bug NULL 2024. (Au niveau
    # ligne, la production nette nocturne peut être < 0 et le violer légitimement : PV/micro
    # négatifs = auxiliaires, convention EDF ; ~1 % des lignes, sans objet à l'agrégat.)
    viol = con.execute(
        f"""SELECT count(*) FROM (
              SELECT heure_locale FROM '{dest}'
              GROUP BY heure_locale HAVING sum(enr_distrib_mw) < sum(photovoltaique_mw)
            )"""
    ).fetchone()[0]
    if viol:
        raise ValueError(f"courbe Corse : {viol} heures ENR<solaire (agrégat) — cohérence rompue.")
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {dest} — {n:,} heures (Corse 2019-2024) — garde ENR>=solaire OK")


def main() -> int:
    dvf_corse_to_parquet()
    mix_temps_reel_to_parquet()
    courbe_corse_to_parquet()
    print("\nPréparation terminée : data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
