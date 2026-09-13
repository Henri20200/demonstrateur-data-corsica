"""Le contrôle de couverture attrape bien les trous qu'il vise.

Les scénarios sont joués sur des jeux SYNTHÉTIQUES, pas sur une copie des données
réelles. C'est délibéré : éprouvés à la main, ils ne valaient que le jour où on les a
joués et ne disaient plus rien au run suivant ; ici ils tournent à chaque passage, y
compris dans le job de PR qui ne collecte pas. Un test sur la donnée réelle complète la
série quand elle est présente.

Chaque cas correspond à une panne observée ou plausible, et non à une variation
d'écriture du code : 2025 retirée est l'état exact du runner le 13/09/2026 ; 2023
retirée est le cas qui traversait `prepare`, toute la suite, les figures et les pages
sans un seul échec ; une station qui perd sa dernière année est la forme qu'aurait prise
une bascule ne touchant qu'une partie des stations.
"""

import duckdb
import pytest

from demonstrateur import couverture
from demonstrateur import figures_air as fa
from demonstrateur.couverture import (
    AN_DEBUT,
    AN_FIN,
    PREMIER_ETE,
    STATIONS_NO2,
    STATIONS_O3,
    controler,
    sorties_manquantes,
)

# Le référentiel vient du module : deux listes séparées dériveraient l'une de
# l'autre, et un test « jeu complet » finirait par valider une couverture que le
# module n'attend plus.
RECENTE = "AJACCIO CONFINA 2"           # ouverte le 31/01/2024
OUVERTURE_RECENTE = PREMIER_ETE[RECENTE]


def _reference() -> set[tuple[str, str, int]]:
    """La couverture attendue : (polluant, station, année), telle qu'observée en réel."""
    triplets = set()
    for an in range(AN_DEBUT, AN_FIN + 1):
        for polluant, stations in (("O3", STATIONS_O3), ("NO2", STATIONS_NO2)):
            for station in stations:
                if an >= PREMIER_ETE.get(station, AN_DEBUT):
                    triplets.add((polluant, station, an))
    return triplets


def _ecrire(tmp_path, monkeypatch, triplets, jours=None):
    """Fabrique les trois Parquet à partir de `triplets` et y branche le module.

    `jours` permet de raccourcir un été précis : {(polluant, station, an): nombre}.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    jours = jours or {}
    lignes = []
    for polluant, station, an in sorted(triplets):
        n = jours.get((polluant, station, an), 92)
        for i in range(n):
            lignes.append((polluant, station, f"{an}-06-01", i))
    con = duckdb.connect()
    con.execute("CREATE TABLE brut (polluant VARCHAR, station VARCHAR, "
                "debut VARCHAR, decalage INTEGER)")
    con.executemany("INSERT INTO brut VALUES (?, ?, ?, ?)", lignes)
    con.execute("""CREATE VIEW v AS SELECT polluant, station,
                   (CAST(debut AS DATE) + INTERVAL (decalage) DAY) AS date_locale
                   FROM brut""")

    chemins = {}
    for nom, sql in (
        ("air_o3_mda8.parquet",
         "SELECT date_locale, station, true AS valide FROM v WHERE polluant = 'O3'"),
        ("air_serie.parquet", "SELECT date_locale, station, polluant FROM v"),
        ("air_temperature_jour.parquet",
         "SELECT date_locale, station FROM v WHERE polluant = 'O3'"),
    ):
        chemin = tmp_path / nom
        con.execute(f"COPY ({sql}) TO '{chemin.as_posix()}' (FORMAT PARQUET)")
        chemins[nom] = chemin

    monkeypatch.setattr(couverture, "MDA8", chemins["air_o3_mda8.parquet"])
    monkeypatch.setattr(couverture, "SERIE", chemins["air_serie.parquet"])
    monkeypatch.setattr(couverture, "CROISE", chemins["air_temperature_jour.parquet"])
    monkeypatch.setattr(couverture, "PARQUETS_REQUIS", tuple(chemins.values()))
    return chemins


def test_un_jeu_complet_ne_declenche_rien(tmp_path, monkeypatch):
    """Sans ce test, tous les autres pourraient passer pour une garde bloquée au rouge."""
    _ecrire(tmp_path, monkeypatch, _reference())
    assert controler() == []


def test_une_sortie_absente_est_un_echec_pas_un_saut(tmp_path, monkeypatch):
    """Un contrôle qui se tait quand le fichier manque protège autant qu'aucun contrôle.

    C'est le défaut du premier jet : les tests étaient `skipif(not ...exists())`, donc
    une préparation qui n'aurait rien produit les aurait tous fait sauter en silence.
    """
    chemins = _ecrire(tmp_path, monkeypatch, _reference())
    chemins["air_o3_mda8.parquet"].unlink()
    assert sorties_manquantes()
    anomalies = controler()
    assert anomalies and "air_o3_mda8.parquet" in anomalies[0]


def test_la_derniere_annee_retiree(tmp_path, monkeypatch):
    """L'état exact du runner le 13/09/2026 : 2025 disparue des deux jeux AEE."""
    _ecrire(tmp_path, monkeypatch, {t for t in _reference() if t[2] != AN_FIN})
    anomalies = controler()
    assert any(str(AN_FIN) in a for a in anomalies)


def test_une_annee_du_milieu_retiree(tmp_path, monkeypatch):
    """Le cas qui traversait toute la chaîne sans un échec avant ce module."""
    milieu = AN_DEBUT + 3
    _ecrire(tmp_path, monkeypatch, {t for t in _reference() if t[2] != milieu})
    anomalies = controler()
    assert any(str(milieu) in a for a in anomalies)


def test_une_station_perd_sa_derniere_annee(tmp_path, monkeypatch):
    """Ses années restent contiguës et l'effectif reste au plancher : rien ne bougeait."""
    _ecrire(tmp_path, monkeypatch,
            {t for t in _reference() if not (t[1] == RECENTE and t[2] == AN_FIN)})
    anomalies = controler()
    assert any(RECENTE in a and "dernier été" in a for a in anomalies)


def test_une_station_perd_sa_derniere_annee_sur_le_no2_seulement(tmp_path, monkeypatch):
    """La continuité porte sur les deux polluants, pas sur le seul ozone du MDA8."""
    _ecrire(tmp_path, monkeypatch, {
        t for t in _reference()
        if not (t[0] == "NO2" and t[1] == "BASTIA GIRAUD" and t[2] == AN_FIN)
    })
    anomalies = controler()
    assert any("NO2" in a and "BASTIA GIRAUD" in a for a in anomalies)


def test_une_station_absente_de_toute_la_fenetre(tmp_path, monkeypatch):
    """Perte franche d'une station : l'effectif passe sous le plancher."""
    _ecrire(tmp_path, monkeypatch, {t for t in _reference() if t[1] != "VENACO"})
    anomalies = controler()
    assert any("plancher" in a for a in anomalies)


def test_un_ete_ampute_de_ses_journees(tmp_path, monkeypatch):
    """Le trou peut être intra-annuel : un mois manquant déplace une moyenne d'été."""
    _ecrire(tmp_path, monkeypatch, _reference(),
            jours={("O3", "VENACO", AN_DEBUT + 1): 30})
    anomalies = controler()
    assert any("VENACO" in a and "amputé" in a for a in anomalies)


def test_une_station_fermee_et_declaree_ne_declenche_rien(tmp_path, monkeypatch):
    """La porte de sortie existe, mais elle s'écrit — elle ne se déduit pas d'un vide."""
    ferme = AN_FIN - 1
    _ecrire(tmp_path, monkeypatch, {
        t for t in _reference() if not (t[1] == "VENACO" and t[2] > ferme)
    })
    monkeypatch.setitem(couverture.STATIONS_CLOSES, ("O3", "VENACO"), ferme)
    anomalies = controler()
    assert not any("VENACO" in a and "dernier été" in a for a in anomalies)


@pytest.mark.skipif(
    sorties_manquantes(), reason="data/processed absent — lancer fetch-data puis prepare"
)
def test_la_donnee_reelle_couvre_la_fenetre_publiee():
    """Le pipeline, lui, ne saute pas : `python -m demonstrateur.couverture` bloque."""
    assert controler() == []


# --- Le sous-titre d'A1 : zéro, un, plusieurs -------------------------------------
# C'est sur ce sous-titre que le cron est tombé deux fois le 13/09/2026 (`NOMBRES[1]`).
# La formulation est corrigée, mais elle ne doit surtout pas devenir une façon de
# publier une fenêtre trouée : zéro reste une erreur, et c'est ce que vérifie la série.

def _mda8_pour_a1(tmp_path, monkeypatch, etes_recente: int, etes: int = 6):
    """Un MDA8 minimal : cinq stations de fond sur `etes` étés, la récente sur moins."""
    lignes = []
    for i, an in enumerate(range(fa.AN_DEBUT, fa.AN_DEBUT + etes)):
        for station in ("AJACCIO CANETTO", "BASTIA GIRAUD", "BASTIA LA MARANA",
                        "BASTIA MONTESORO", "VENACO"):
            lignes.append((station, f"{an}-07-01", "Fond"))
        if i >= etes - etes_recente and etes_recente:
            lignes.append((fa.RECENTE, f"{an}-07-01", "Fond"))
    con = duckdb.connect()
    con.execute("CREATE TABLE b (station VARCHAR, jour VARCHAR, influence VARCHAR)")
    con.executemany("INSERT INTO b VALUES (?, ?, ?)", lignes)
    chemin = tmp_path / "mda8.parquet"
    con.execute(f"""COPY (SELECT station, CAST(jour AS DATE) AS date_locale,
                          influence, true AS valide FROM b)
                    TO '{chemin.as_posix()}' (FORMAT PARQUET)""")
    monkeypatch.setattr(fa, "MDA8", chemin.as_posix())
    return chemin


def test_st_a1_au_pluriel(tmp_path, monkeypatch):
    _mda8_pour_a1(tmp_path, monkeypatch, etes_recente=2)
    assert "ne couvre que deux de ces six étés" in fa.st_a1()


def test_st_a1_au_singulier_elide_correctement(tmp_path, monkeypatch):
    """« qu'un », pas « que un » — et surtout pas un KeyError."""
    _mda8_pour_a1(tmp_path, monkeypatch, etes_recente=1)
    rendu = fa.st_a1()
    assert "ne couvre qu'un de ces six étés" in rendu
    assert "que un" not in rendu


def test_st_a1_refuse_une_couverture_nulle(tmp_path, monkeypatch):
    """Zéro n'est pas une tournure à écrire : c'est une donnée qui manque."""
    _mda8_pour_a1(tmp_path, monkeypatch, etes_recente=0)
    with pytest.raises(ValueError, match="compte nul"):
        fa.st_a1()


def test_st_a1_ne_se_contente_pas_de_savoir_ecrire_un(tmp_path, monkeypatch):
    """La correction du texte ne doit pas suffire à publier une étude incomplète.

    Une fenêtre réduite à un seul été se formule très bien — et reste une fenêtre
    amputée. Le sous-titre n'a pas à le savoir : c'est `couverture` qui bloque.
    """
    _mda8_pour_a1(tmp_path, monkeypatch, etes_recente=1, etes=1)
    assert fa.st_a1()                     # la phrase se forme, sans lever
    # La même amputation, vue par le contrôle : un seul été sur les six annoncés.
    _ecrire(tmp_path / "couv", monkeypatch,
            {t for t in _reference() if t[2] == AN_FIN})
    assert controler(), "une fenêtre réduite à un seul été doit bloquer la chaîne"


# --- Deux absences qui ne changent ni l'effectif ni la continuité observée ---------
# Signalées le 13/09/2026 : dans les deux cas `controler()` renvoyait [] parce que la
# continuité ne parcourait QUE les couples présents dans la donnée, et que le MDA8
# n'était contrôlé que par effectif. Une station qui n'apparaît nulle part n'a pas
# d'années à vérifier — elle ne peut donc être vue qu'en la comparant à un attendu.

def test_une_station_absente_d_un_seul_polluant(tmp_path, monkeypatch):
    """Confina 2 sans NO2 : l'effectif NO2 reste à 4, son plancher."""
    _ecrire(tmp_path, monkeypatch, {
        t for t in _reference() if not (t[0] == "NO2" and t[1] == RECENTE)
    })
    anomalies = controler()
    assert any("NO2" in a and RECENTE in a for a in anomalies), anomalies


def test_une_station_perd_une_annee_dans_le_mda8_seul(tmp_path, monkeypatch):
    """La perte est dans le résultat journalier, pas dans la série horaire.

    `prepare` dérive le MDA8 d'`air_serie` : une règle de validité qui se resserre, une
    jointure qui échoue, et l'ozone journalier perd une station-année que la série
    horaire porte toujours. La continuité mesurée sur la série ne le voit pas.
    """
    chemins = _ecrire(tmp_path, monkeypatch, _reference())
    duckdb.connect().execute(f"""
        COPY (SELECT * FROM '{chemins["air_o3_mda8.parquet"].as_posix()}'
              WHERE NOT (station = '{RECENTE}'
                         AND extract('year' FROM date_locale) = {AN_FIN}))
        TO '{(tmp_path / "mda8_ampute.parquet").as_posix()}' (FORMAT PARQUET)
    """)
    (tmp_path / "mda8_ampute.parquet").replace(chemins["air_o3_mda8.parquet"])
    anomalies = controler()
    assert any(RECENTE in a for a in anomalies), anomalies
