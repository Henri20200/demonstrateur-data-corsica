"""Moyenne glissante sur 8 heures : le calcul est confronté au guide du producteur.

Cette statistique n'est servie par aucune de nos deux sources — ni le flux temps réel,
ni l'API Geod'air, qui s'arrêtent aux moyennes horaires. Elle est donc recalculée dans
`prepare`, et le chiffre qui en sortira sera présenté comme réglementaire. Un test qui
se contenterait de vérifier une moyenne de huit nombres ne prouverait rien : ce qui
compte, ce sont les règles de bord — quelles heures entrent dans la fenêtre, par quoi
on divise quand il en manque, à quel jour la moyenne est attribuée, et à partir de quand
un maximum journalier cesse d'être opposable.

Le cas de référence n'est donc pas inventé ici : c'est le **tableau 26** du guide
méthodologique LCSQA/Ineris (« Guide Calcul des statistiques relatives à la Qualité de
l'Air », Ineris-219621-2801775-v1.0, mars 2024, § 5.3.3 et 5.3.4), deux journées d'ozone
réelles des 2 et 3 août 2015, avec ses moyennes et ses validités déjà calculées par le
producteur de nos données. Si notre calcul en diverge d'une heure ou d'un diviseur, il
diverge du décompte officiel.

UN PIÈGE, et c'est lui que le tableau permet d'attraper : le guide étiquette ses heures à
la FIN de la période (01 h → 24 h), là où le flux LCSQA les étiquette au DÉBUT
(00 h → 23 h). Les données ci-dessous sont donc converties en heures de début — un décalage
d'une heure ferait tomber quatre des assertions.
"""

import duckdb
import pytest

from demonstrateur.prepare import (
    MIN_HEURES_8H,
    MIN_MOYENNES_MDA8,
    _sql_glissant_8h,
    _sql_mda8,
)

# Tableau 26 du guide, en (heure de FIN telle qu'imprimée, valeur, validité).
# « - » = pas de mesure ; validité -1 = invalide. Les lignes invalides sont écartées en
# amont par air_corse_to_parquet (filtre validité > 0) : on les laisse ici pour que la
# fidélité au tableau soit vérifiable à l'œil, et le fixture les retire comme le ferait
# le pipeline.
TABLEAU_26 = [
    ("2015-08-02 18:00", None, -1), ("2015-08-02 19:00", None, -1),
    ("2015-08-02 20:00", None, -1), ("2015-08-02 21:00", None, -1),
    ("2015-08-02 22:00", None, -1), ("2015-08-02 23:00", 207.2, -1),
    ("2015-08-02 24:00", 208.1, -1),
    ("2015-08-03 01:00", 85.6, 1), ("2015-08-03 02:00", 99.2, 1),
    ("2015-08-03 03:00", 101.1, 1), ("2015-08-03 04:00", 104.3, 1),
    ("2015-08-03 05:00", 106.2, 1), ("2015-08-03 06:00", 107.1, 1),
    ("2015-08-03 07:00", 114.7, 1), ("2015-08-03 08:00", 118.8, 1),
    ("2015-08-03 09:00", 123.5, 1), ("2015-08-03 10:00", 123.8, 1),
    ("2015-08-03 11:00", 127.2, 1), ("2015-08-03 12:00", 132.9, 1),
    ("2015-08-03 13:00", None, -1), ("2015-08-03 14:00", None, -1),
    ("2015-08-03 15:00", None, -1), ("2015-08-03 16:00", 141.2, 1),
    ("2015-08-03 17:00", 142.4, 1), ("2015-08-03 18:00", 143.8, 1),
    ("2015-08-03 19:00", 146.8, 1), ("2015-08-03 20:00", 148.4, 1),
    ("2015-08-03 21:00", 154.1, 1), ("2015-08-03 22:00", 155.1, 1),
    ("2015-08-03 23:00", 153.2, 1), ("2015-08-03 24:00", 148.3, 1),
]

# Moyennes glissantes attendues, indexées par heure de FIN du guide (§ 5.3.3).
MOYENNES_ATTENDUES = {
    "2015-08-03 01:00": (85.6000, False), "2015-08-03 02:00": (92.4000, False),
    "2015-08-03 03:00": (95.3000, False), "2015-08-03 04:00": (97.5500, False),
    "2015-08-03 05:00": (99.2800, False), "2015-08-03 06:00": (100.5833, True),
    "2015-08-03 07:00": (102.6000, True), "2015-08-03 08:00": (104.6250, True),
    "2015-08-03 09:00": (109.3625, True), "2015-08-03 10:00": (112.4375, True),
    "2015-08-03 11:00": (115.7000, True), "2015-08-03 12:00": (119.2750, True),
    "2015-08-03 13:00": (121.1429, True), "2015-08-03 14:00": (123.4833, True),
    "2015-08-03 15:00": (125.2400, False), "2015-08-03 16:00": (129.7200, False),
    "2015-08-03 17:00": (133.5000, False), "2015-08-03 18:00": (137.5000, False),
    "2015-08-03 19:00": (141.4200, False), "2015-08-03 20:00": (144.5200, False),
    "2015-08-03 21:00": (146.1167, True), "2015-08-03 22:00": (147.4000, True),
    "2015-08-03 23:00": (148.1250, True), "2015-08-03 24:00": (149.0125, True),
}


def _fin_vers_debut(etiquette: str) -> str:
    """« 2015-08-03 24:00 » (fin, guide) -> « 2015-08-03 23:00 » (début, flux LCSQA)."""
    jour, heure = etiquette.split(" ")
    return f"{jour} {int(heure.split(':')[0]) - 1:02d}:00:00"


@pytest.fixture
def mesures():
    """Table des mesures du tableau 26, en heures de début et déjà filtrée en validité.

    L'ozone français est mesuré en heure légale ; août 2015 est en UTC+2, sans changement
    d'heure dans la fenêtre — l'axe UTC est donc un décalage constant, et le jour local
    reste celui de l'étiquette de début.
    """
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE o3 (code_site VARCHAR, station VARCHAR, implantation VARCHAR, "
        "influence VARCHAR, date_heure_utc TIMESTAMP, date_locale DATE, "
        "heure_locale BIGINT, valeur DOUBLE)"
    )
    for etiquette, valeur, validite in TABLEAU_26:
        if validite <= 0:
            continue  # écarté en amont par air_corse_to_parquet
        debut = _fin_vers_debut(etiquette)
        con.execute(
            "INSERT INTO o3 SELECT 'FR00001', 'STATION TEST', 'Urbaine', 'Fond', "
            "timezone('UTC', timezone('Europe/Paris', d)), CAST(d AS DATE), "
            "extract('hour' FROM d), ? FROM (SELECT CAST(? AS TIMESTAMP) AS d)",
            [valeur, debut],
        )
    return con


def test_moyennes_glissantes_conformes_au_tableau_26(mesures):
    """Les 24 moyennes du 03/08/2015 et leur validité, au dix-millième près.

    La comparaison se fait sur l'heure de DÉBUT — celle du flux réel — et les étiquettes
    du guide y sont ramenées par `_fin_vers_debut`. C'est le sens dans lequel le décalage
    doit être franchi : dans l'autre, on comparerait notre calcul à lui-même.
    """
    lignes = mesures.execute(
        f"SELECT date_locale, heure_locale, moyenne_8h, n_heures "
        f"FROM ({_sql_glissant_8h('o3')}) ORDER BY date_heure_utc"
    ).fetchall()
    obtenu = {
        f"{jour} {heure:02d}:00:00": (round(moyenne, 4), n >= MIN_HEURES_8H)
        for jour, heure, moyenne, n in lignes
    }

    for etiquette_fin, (attendue, valide_attendue) in MOYENNES_ATTENDUES.items():
        cle = _fin_vers_debut(etiquette_fin)
        assert cle in obtenu, f"aucune moyenne pour {etiquette_fin} (début {cle})"
        moyenne, valide = obtenu[cle]
        assert moyenne == pytest.approx(attendue, abs=1e-4), (
            f"{etiquette_fin} : obtenu {moyenne}, guide {attendue}"
        )
        assert valide is valide_attendue, (
            f"{etiquette_fin} : validité {valide}, guide {valide_attendue}"
        )
    assert len(MOYENNES_ATTENDUES) == 24, "le guide en calcule 24 sur une journée complète"


def test_maximum_journalier_et_sa_validite(mesures):
    """Le maximum du 03/08 vaut 149,0125 — et n'est PAS opposable.

    Le tableau 26 le marque invalide : la journée ne compte que 13 moyennes glissantes
    valides, sous les 18 exigées. C'est le cœur du garde-fou — publier ce maximum dans un
    décompte de dépassements annoncerait un chiffre que le producteur lui-même rejette.
    """
    lignes = mesures.execute(
        f"SELECT date_locale, mda8, n_moyennes_valides, valide "
        f"FROM ({_sql_mda8(_sql_glissant_8h('o3'))}) ORDER BY date_locale"
    ).fetchall()
    par_jour = {str(j): (mda8, n, ok) for j, mda8, n, ok in lignes}

    mda8, n, valide = par_jour["2015-08-03"]
    assert mda8 == pytest.approx(149.0125, abs=1e-4)
    assert n == 13, f"13 moyennes valides attendues (tableau 26), obtenu {n}"
    assert valide is False, "moins de 18 moyennes valides : le maximum n'est pas opposable"


def test_la_fenetre_porte_sur_le_temps_et_non_sur_les_lignes(mesures):
    """Une heure manquante ne doit pas faire remonter la fenêtre plus loin que 8 heures.

    Régression : avec `ROWS BETWEEN 7 PRECEDING`, la moyenne de 16 h (étiquette de fin)
    ramasserait huit LIGNES et non huit heures — les trois heures invalides de 13 h, 14 h
    et 15 h la feraient remonter jusqu'à 06 h du matin, gonflant une valeur d'après-midi
    d'un morceau de matinée fraîche, et la déclarant valide par-dessus le marché.
    """
    ligne = mesures.execute(
        f"SELECT moyenne_8h, n_heures FROM ({_sql_glissant_8h('o3')}) "
        "WHERE heure_locale = 15"  # étiquette de début = 15 h -> fin 16 h du guide
    ).fetchone()
    moyenne, n = ligne
    assert n == 5, f"5 heures valides dans la fenêtre 09h-16h, obtenu {n}"
    assert moyenne == pytest.approx(129.7200, abs=1e-4)
    assert n < MIN_HEURES_8H, "cette moyenne doit être écartée, pas publiée"


def test_les_deux_seuils_ne_se_confondent_pas():
    """Garde-fou de lecture : 6 et 18 ne sont pas interchangeables (§ 5.3.3 vs § 5.3.4)."""
    assert MIN_HEURES_8H == 6, "75 % de 8 heures — critère d'une moyenne glissante"
    assert MIN_MOYENNES_MDA8 == 18, "75 % de 24 moyennes — critère d'un maximum journalier"
