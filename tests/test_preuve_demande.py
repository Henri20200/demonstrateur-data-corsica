"""Calcul indépendant, périmètre complet et dossier effectivement rejouable."""

import csv
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta

import pytest

from demonstrateur.calcul_demande import ANNEES, CHAMPS, calculer
from demonstrateur.config import OUTPUTS


@pytest.fixture
def extrait(tmp_path):
    fichier = tmp_path / "demande.csv"
    with fichier.open("w", encoding="utf-8", newline="") as flux:
        writer = csv.DictWriter(flux, fieldnames=CHAMPS, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for annee in ANNEES:
            date = datetime(annee, 6, 1)
            while date.month in (6, 7):
                writer.writerow({
                    "territoire": "Corse", "statut": "Estimé",
                    "date_heure": date.isoformat() + "+00:00",
                    "production_totale_mw": "100.49" if date.month == 6 else "122.49",
                })
                date += timedelta(hours=1)
    return fichier


def test_le_calcul_compare_des_moyennes_pas_des_volumes(extrait):
    r = calculer(extrait)
    assert r["juin"]["heures"] == 4320
    assert r["juillet"]["heures"] == 4464
    assert r["juin"]["moyenne_mw"] == pytest.approx(100.49)
    assert r["juillet"]["moyenne_mw"] == pytest.approx(122.49)
    assert r["ecart_pct"] == pytest.approx(100 * 22 / 100.49)
    assert r["ecart_affiche_pct"] == 22


def test_une_heure_absente_empeche_la_reproduction(extrait):
    lignes = extrait.read_text(encoding="utf-8").splitlines(keepends=True)
    extrait.write_text("".join(lignes[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="Mois incomplet"):
        calculer(extrait)


def test_un_doublon_ne_compense_pas_une_heure_absente(extrait):
    lignes = extrait.read_text(encoding="utf-8").splitlines(keepends=True)
    lignes[-1] = lignes[-2]
    extrait.write_text("".join(lignes), encoding="utf-8")
    with pytest.raises(ValueError, match="Heure en double"):
        calculer(extrait)


@pytest.mark.skipif(
    not (OUTPUTS / "verification-demande.zip").exists(),
    reason="dossier absent — lancer python -m demonstrateur.preuve_demande",
)
def test_le_dossier_publie_se_rejoue_sans_le_projet(tmp_path):
    with zipfile.ZipFile(OUTPUTS / "verification-demande.zip") as archive:
        for nom in ("demande-juin-juillet.csv", "provenance.json", "verifier_demande.py"):
            (tmp_path / nom).write_bytes(archive.read(nom))
    commande = [sys.executable, "-I", "-B", str(tmp_path / "verifier_demande.py")]
    resultat = subprocess.run(commande, cwd=tmp_path, capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "Annotation du graphique : +22 %" in resultat.stdout
    provenance = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["source"]["sha256"]
    assert provenance["source"]["date_collecte"]
    csv_path = tmp_path / "demande-juin-juillet.csv"
    contenu = csv_path.read_bytes()
    csv_path.write_bytes(contenu.replace(b"Corse", b"corse", 1))
    refuse = subprocess.run(commande, cwd=tmp_path, capture_output=True, text=True)
    assert refuse.returncode == 1
    assert "empreinte du CSV" in refuse.stderr
