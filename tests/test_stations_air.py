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

DEUX ANCRES, PARCE QU'UN SEUL PRODUCTEUR NE PUBLIE PAS TOUT. Le référentiel Geod'air
ne porte AUCUNE colonne « type d'influence » (vérifié le 29/08/2026 : il donne Type de
site, Implantation, Dispersion régionale/locale, et la version datée de la fiche). Or
l'influence est le filtre de TOUTES les figures d'air — `influence = 'Fond'` décide
lesquelles des six stations sont tracées. Elle était donc le seul caractère de la table
qu'aucune donnée ne tenait. Le flux LCSQA temps réel, lui, la publie et il est collecté
chaque jour : `data/processed/air_corse.parquet` en porte la dernière valeur observée.
C'est là qu'est l'ancre, et le contrôle est bloquant — une divergence arrête et se
regarde, elle ne s'adopte JAMAIS d'office : une reclassification a une date d'effet, et
la recopier en silence reclasserait rétroactivement des années de mesures publiées.
"""

import csv

import duckdb
import pytest

from demonstrateur.config import DATA_PROCESSED, DATA_RAW
from demonstrateur.prepare import STATIONS_AIR

REFERENTIEL = DATA_RAW / "geodair_stations.csv"
FLUX = DATA_PROCESSED / "air_corse.parquet"

besoin_referentiel = pytest.mark.skipif(
    not REFERENTIEL.exists(),
    reason="data/raw/geodair_stations.csv absent — lancer fetch-data (clé GEODAIR_KEY)",
)
besoin_flux = pytest.mark.skipif(
    not FLUX.exists(),
    reason="data/processed/air_corse.parquet absent — lancer fetch-data puis prepare",
)

# Les 8 sites corses au 07/08/2026. Les 6 premiers sont notre périmètre d'ozone ; les
# deux derniers ne le sont PAS et sont listés ici pour que leur apparition ne soit plus
# une surprise — AJACCIO NAPOLEON est entrée en service le 11/07/2025 sans qu'aucun test
# ne le dise. Un site de plus fait échouer `test_aucun_site_corse_inconnu` : ce n'est pas
# une erreur, c'est une invitation à vérifier s'il mesure l'ozone.
SITES_CORSES_CONNUS = {
    "FR41001", "FR41002", "FR41004", "FR41017", "FR41024",  # périmètre ozone (5 anciennes)
    "FR41063",                                              # périmètre ozone (Confina 2)
    # Ces deux-là ne mesurent PAS l'ozone — vérifié le 07/08/2026 sur le référentiel des
    # points de prélèvement : AJACCIO NAPOLEON est d'influence Trafic (C6H6, CO, NO, NO2,
    # NOx, PM10). Ils sont listés pour que leur présence ne fasse pas échouer la suite ;
    # un NEUVIÈME site, lui, doit la faire échouer.
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
    # `_influence` reste à l'écart ICI, et seulement ici : ce référentiel ne la publie
    # pas. Elle se contrôle plus bas, contre le flux qui la porte.
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


# --- Seconde ancre : l'influence, contre le flux LCSQA temps réel ---------------------
def influences_declarees() -> dict[str, str]:
    """Ce que la table RECOPIE : l'influence de chaque station du périmètre."""
    return {code: caracteristiques[-1] for code, caracteristiques in STATIONS_AIR.items()}


def _influences_observees() -> dict[str, str]:
    """Ce que le flux LCSQA a publié EN DERNIER pour chaque site corse.

    `arg_max` et non la valeur la plus fréquente : ce qui compte est celle que porte
    l'observation la plus récente. Un site reclassé le serait sur ses dernières heures
    avant de l'être sur ses premières.
    """
    lignes = duckdb.connect().execute(
        f"SELECT code_site, arg_max(influence, date_heure_utc) FROM '{FLUX.as_posix()}' "
        "GROUP BY 1"
    ).fetchall()
    return dict(lignes)


def divergences(declarees: dict[str, str], observees: dict[str, str]) -> dict[str, tuple]:
    """Sites dont l'influence observée dément celle qui est recopiée.

    Fonction PURE, et c'est délibéré : le falsificateur l'appelle sur une observation
    trafiquée, sans donnée collectée. Un contrôle qu'on n'a jamais vu casser ne protège
    de rien.

    Un site ABSENT de l'observation n'est pas une divergence : le flux temps réel est une
    fenêtre de 24 h, et une station en maintenance en sort une journée. L'absence ne dit
    rien, ni dans un sens ni dans l'autre.
    """
    return {
        code: (declaree, observees[code])
        for code, declaree in declarees.items()
        if code in observees and observees[code] != declaree
    }


@besoin_flux
def test_influence_conforme_au_dernier_flux_lcsqa():
    """L'influence recopiée dit ce que le producteur publie — sinon, arrêt.

    C'est le filtre de toutes les figures d'air : `influence = 'Fond'` décide lesquelles
    des six stations sont tracées, et donc ce que les titres publiés affirment.
    """
    observees = _influences_observees()
    declarees = influences_declarees()
    vues = sorted(set(declarees) & set(observees))
    assert vues, (
        f"le flux LCSQA n'observe aucune station du périmètre ({sorted(observees)}) — "
        "c'est l'ancre du contrôle qui est rompue, pas la table : vérifier que "
        "air_corse.parquet couvre bien les sites corses avant de conclure quoi que ce soit"
    )
    ecarts = divergences(declarees, observees)
    assert not ecarts, (
        f"influence démentie par le flux LCSQA : {ecarts} (recopiée, observée). "
        "NE PAS recopier la valeur observée sans décider de sa portée : une "
        "reclassification a une date d'effet, et l'adopter ici la ferait rétroagir sur "
        "six étés de figures déjà publiées."
    )


def test_le_controle_d_influence_casse_si_une_station_est_reclassee():
    """Falsificateur du contrôle ci-dessus, et il vise le scénario qui coûterait le plus.

    Bastia La Marana est la seule station du périmètre qui ne soit PAS de fond — elle est
    d'influence industrielle, et c'est ce qui la tient hors de A1, A3, A4 et A5. Reclassée
    « Fond » sans que rien ne le dise, elle entrerait d'un coup dans les quatre figures :
    une station de plus dans les décomptes annoncés, et des taux calculés sur un site que
    le périmètre publié exclut.
    """
    declarees = influences_declarees()
    assert declarees["FR41004"] == "Industrielle", "La Marana n'est plus le scénario visé"

    conformes = dict(declarees)
    assert divergences(declarees, conformes) == {}

    reclassee = conformes | {"FR41004": "Fond"}
    assert divergences(declarees, reclassee) == {"FR41004": ("Industrielle", "Fond")}
