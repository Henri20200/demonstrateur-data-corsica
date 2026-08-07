"""La table `prepare.STATIONS_AIR` dit ce que dit son producteur.

Ces caractéristiques (mise en service, implantation, altitude, coordonnées) sont
RECOPIÉES dans le code — elles ne se déduisent d'aucune mesure, et le flux qui porte
les concentrations ne les contient pas. Une recopie exacte le jour où elle est faite
reste une recopie : rien, jusqu'ici, n'aurait signalé qu'une valeur avait été mal lue,
ni qu'un site avait été déplacé depuis. Or une note du livrable en affirme le chiffré
(« Ajaccio Confina 2 ne mesure que depuis janvier 2024, quand les quatre autres
remontent à 2006-2011 »).

Le référentiel `geodair_stations` (source déclarée le 07/08/2026) ferme cet écart :
la table est confrontée à ce que Geod'air publie, et la suite échoue si les deux
divergent. Nécessite `fetch-data` — sans le brut, ces tests sont sautés.
"""

import csv

import pytest

from demonstrateur.config import DATA_RAW
from demonstrateur.prepare import STATIONS_AIR

REFERENTIEL = DATA_RAW / "geodair_stations.csv"

besoin_referentiel = pytest.mark.skipif(
    not REFERENTIEL.exists(),
    reason="data/raw/geodair_stations.csv absent — lancer fetch-data (clé GEODAIR_KEY)",
)

# Les 8 sites corses au 07/08/2026. Les 6 premiers sont notre périmètre d'ozone ; les
# deux derniers ne le sont PAS et sont listés ici pour que leur apparition ne soit plus
# une surprise — AJACCIO NAPOLEON est entrée en service le 11/07/2025 sans qu'aucun test
# ne le dise. Un site de plus fait échouer `test_aucun_site_corse_inconnu` : ce n'est pas
# une erreur, c'est une invitation à vérifier s'il mesure l'ozone.
SITES_CORSES_CONNUS = {
    "FR41001", "FR41002", "FR41004", "FR41017", "FR41024",  # périmètre ozone (5 anciennes)
    "FR41063",                                              # périmètre ozone (Confina 2)
    "FR41060",                                              # BASTIA FANGO — hors périmètre
    "FR41073",                                              # AJACCIO NAPOLEON — hors périmètre
}

# Coordonnées : le référentiel publie jusqu'à 8 décimales là où la table en porte 6
# (41.94768611 contre 41.947685). 1e-4 degré valant ~11 m, la tolérance distingue un
# arrondi d'écriture d'un déplacement de station, qui est le seul cas à attraper.
TOLERANCE_DEGRE = 1e-4


def _referentiel() -> dict[str, dict[str, str]]:
    lignes = REFERENTIEL.read_text(encoding="utf-8").splitlines()
    return {r["Code"]: r for r in csv.DictReader(lignes, delimiter=";")}


@besoin_referentiel
def test_les_six_stations_du_perimetre_sont_au_referentiel():
    ref = _referentiel()
    absentes = [code for code in STATIONS_AIR if code not in ref]
    assert not absentes, f"stations absentes du référentiel Geod'air : {absentes}"


@besoin_referentiel
@pytest.mark.parametrize("code", sorted(STATIONS_AIR))
def test_caracteristiques_conformes_au_referentiel(code):
    nom, lat, lon, altitude, mise_en_service, implantation, _influence = STATIONS_AIR[code]
    site = _referentiel()[code]

    assert site["Nom"] == nom, f"{code} : nom divergent"

    # Le référentiel écrit la date en JJ/MM/AAAA, la table en ISO : on compare les dates,
    # pas leur écriture.
    jour, mois, annee = site["Date d'entrée en service (à 00h00)"].split("/")
    assert f"{annee}-{mois}-{jour}" == mise_en_service, (
        f"{code} : mise en service {annee}-{mois}-{jour} au référentiel, "
        f"{mise_en_service} dans STATIONS_AIR"
    )

    assert site["Implantation"] == implantation, f"{code} : implantation divergente"
    assert float(site["Altitude"]) == pytest.approx(altitude), f"{code} : altitude divergente"
    assert float(site["Latitude"]) == pytest.approx(lat, abs=TOLERANCE_DEGRE), f"{code} : latitude"
    assert float(site["Longitude"]) == pytest.approx(lon, abs=TOLERANCE_DEGRE), f"{code} : longitude"


@besoin_referentiel
def test_aucun_site_corse_inconnu():
    """Un site de plus dans le référentiel = un périmètre à re-vérifier, pas un silence."""
    nouveaux = sorted(set(_referentiel()) - SITES_CORSES_CONNUS)
    assert not nouveaux, (
        f"sites corses non répertoriés : {nouveaux} — vérifier s'ils mesurent l'ozone "
        "avant de les ignorer, puis les inscrire dans SITES_CORSES_CONNUS"
    )


@besoin_referentiel
def test_les_stations_du_perimetre_sont_en_service():
    ref = _referentiel()
    arretees = {
        code: ref[code]["Date de fin de service (à 00h00)"]
        for code in STATIONS_AIR
        if ref[code]["Etat"] != "En service"
    }
    assert not arretees, f"stations plus en service : {arretees} — le périmètre a vieilli"


@besoin_referentiel
def test_la_note_air_dit_vrai_sur_la_profondeur_des_stations():
    """Verrou de la phrase publiée : Confina 2 en 2024, les autres de fond entre 2006 et 2011.

    « les quatre autres » vise les stations de fond hors Confina 2 — La Marana, d'influence
    industrielle, n'entre pas dans ce décompte.
    """
    ref = _referentiel()
    annees = {}
    for code, (_nom, *_r, influence) in ((c, STATIONS_AIR[c]) for c in STATIONS_AIR):
        if influence != "Fond":
            continue
        annees[code] = int(ref[code]["Date d'entrée en service (à 00h00)"].split("/")[2])

    assert annees.pop("FR41063") == 2024, "Confina 2 n'est plus une station de 2024"
    assert len(annees) == 4, f"« les quatre autres » en vaut {len(annees)} — la note ment"
    assert min(annees.values()) == 2006 and max(annees.values()) == 2011, (
        f"« 2006-2011 » dément par le référentiel : {sorted(annees.values())}"
    )
