"""Ancrage des heures sur les conventions publiées, pas sur un accord entre sources.

AEE : Start est le début de période en UTC+1 fixe (guide de téléchargement, p. 18
et aide Parquet). LCSQA : Date de début est en UTC (DRC-18-174316-08157A, p. 6).
Les attendus explicites couvrent hiver, été et changement de jour local.
"""

import csv
from datetime import datetime

import duckdb
import pytest

from demonstrateur import prepare


@pytest.mark.parametrize(
    "debut_aee,debut_utc,debut_local",
    [
        ("2025-01-15 07:00:00", "2025-01-15 06:00:00", "2025-01-15 07:00:00"),
        ("2025-07-15 07:00:00", "2025-07-15 06:00:00", "2025-07-15 08:00:00"),
        ("2025-07-15 23:00:00", "2025-07-15 22:00:00", "2025-07-16 00:00:00"),
        ("2025-03-30 02:00:00", "2025-03-30 01:00:00", "2025-03-30 03:00:00"),
    ],
)
@pytest.mark.parametrize("source", ["aee", "lcsqa"])
def test_conversion_des_debuts_horaires(
    tmp_path, monkeypatch, source, debut_aee, debut_utc, debut_local
):
    dest = tmp_path / "air.parquet"
    if source == "aee":
        brut = tmp_path / "aee.parquet"
        with duckdb.connect() as con:
            con.execute(
                "CREATE TABLE brut AS SELECT 'SPO-FR41001_7' AS Samplingpoint, "
                "CAST(? AS TIMESTAMP) AS Start, 50.0 AS Value, "
                "1 AS Validity, 1 AS Verification",
                [debut_aee],
            )
            con.execute(f"COPY brut TO '{brut.as_posix()}' (FORMAT PARQUET)")
        monkeypatch.setattr(prepare, "AEE_MESURES", brut.as_posix())
        monkeypatch.setattr(prepare, "STATIONS_AIR", {"FR41001": prepare.STATIONS_AIR["FR41001"]})
        prepare.air_serie_to_parquet(dest.as_posix())
    else:
        brut = tmp_path / "lcsqa.csv"
        ligne = {
            "Organisme": "QUALITAIR CORSE",
            "Date de début": debut_utc,
            "Zas": "Corse",
            "code site": "FR41001",
            "nom site": "CANETTO",
            "type d'implantation": "Urbaine",
            "type d'influence": "Fond",
            "Polluant": "O3",
            "valeur": 50.0,
            "unité de mesure": "µg/m3",
            "validité": 1,
        }
        with brut.open("w", encoding="utf-8", newline="") as fichier:
            writer = csv.DictWriter(fichier, fieldnames=ligne, delimiter=";")
            writer.writeheader()
            writer.writerow(ligne)
        monkeypatch.setattr(prepare, "AIR", brut.as_posix())
        prepare.air_corse_to_parquet(dest.as_posix())

    with duckdb.connect() as con:
        resultat = con.execute(
            f"SELECT date_heure_utc, date_heure_locale, date_locale, heure_locale "
            f"FROM '{dest.as_posix()}'"
        ).fetchone()
    local = datetime.fromisoformat(debut_local)
    assert resultat == (datetime.fromisoformat(debut_utc), local, local.date(), local.hour)
