"""Recalcul autonome du dossier juin-juillet : Python 3, bibliothèque standard seule.

Le CSV contient les lignes EDF Corse de juin et juillet 2019-2024. Les étiquettes
horaires sont lues comme heures locales, sans convertir leur suffixe +00:00 erroné.
Aucun changement d'heure ne tombe dans ces deux mois. Aucun accès réseau.
"""

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ANNEES = tuple(range(2019, 2025))
CHAMPS = ("territoire", "statut", "date_heure", "production_totale_mw")


def calculer(fichier: Path) -> dict:
    valeurs = defaultdict(list)
    heures = set()
    effectifs = defaultdict(int)
    with fichier.open(encoding="utf-8-sig", newline="") as flux:
        lecteur = csv.DictReader(flux, delimiter=";")
        if not set(CHAMPS).issubset(lecteur.fieldnames or []):
            raise ValueError("Colonnes attendues absentes du CSV.")
        for ligne in lecteur:
            etiquette = ligne["date_heure"]
            if not etiquette.endswith("+00:00"):
                raise ValueError("L'étiquetage EDF a changé : vérifier la convention horaire.")
            instant = datetime.fromisoformat(etiquette).replace(tzinfo=None)
            if (ligne["territoire"] != "Corse" or instant.year not in ANNEES
                    or instant.month not in (6, 7) or instant.minute or instant.second):
                raise ValueError("Ligne hors du périmètre horaire Corse, juin-juillet 2019-2024.")
            if instant in heures:
                raise ValueError(f"Heure en double : {etiquette}")
            heures.add(instant)
            valeur = float(ligne["production_totale_mw"])
            if not math.isfinite(valeur) or valeur <= 0:
                raise ValueError(f"Mesure absente ou non positive : {etiquette}")
            valeurs[instant.month].append(valeur)
            effectifs[instant.year, instant.month] += 1
    for annee in ANNEES:
        for mois, jours in ((6, 30), (7, 31)):
            if effectifs[annee, mois] != jours * 24:
                raise ValueError(f"Mois incomplet : {annee}-{mois:02d}.")
    resultat = {}
    for mois, nom in ((6, "juin"), (7, "juillet")):
        moyenne = math.fsum(valeurs[mois]) / len(valeurs[mois])
        resultat[nom] = {
            "heures": len(valeurs[mois]), "moyenne_mw": moyenne, "affiche_mw": round(moyenne),
        }
    juin, juillet = resultat["juin"], resultat["juillet"]
    resultat["ecart_pct"] = 100 * (juillet["moyenne_mw"] / juin["moyenne_mw"] - 1)
    # La figure arrondit ses deux barres au MW avant de calculer son annotation.
    resultat["ecart_affiche_pct"] = round(
        100 * (juillet["affiche_mw"] - juin["affiche_mw"]) / juin["affiche_mw"]
    )
    return resultat


def main() -> int:
    dossier = Path(__file__).resolve().parent
    try:
        fichier = dossier / "demande-juin-juillet.csv"
        preuve = json.loads((dossier / "provenance.json").read_text(encoding="utf-8"))
        if hashlib.sha256(fichier.read_bytes()).hexdigest() != preuve["extrait_sha256"]:
            raise ValueError("L'empreinte du CSV ne correspond plus au dossier fourni.")
        resultat = calculer(fichier)
        if resultat["ecart_affiche_pct"] != preuve["resultat"]["ecart_affiche_pct"]:
            raise ValueError("Le calcul ne correspond plus au résultat annoncé.")
        for nom in ("juin", "juillet"):
            r = resultat[nom]
            print(f"{nom.capitalize()} : {r['heures']} heures, {r['moyenne_mw']:.6f} MW")
        print(f"Ecart sur les moyennes non arrondies : {resultat['ecart_pct']:.6f} %")
        print(f"Annotation du graphique : +{resultat['ecart_affiche_pct']} %")
        return 0
    except (OSError, ValueError, KeyError) as erreur:
        print(f"Verification impossible : {erreur}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
