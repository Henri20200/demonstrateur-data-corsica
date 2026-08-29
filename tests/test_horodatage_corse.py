"""Quatre verrous sur l'horodatage de la courbe EDF corse — indépendants entre eux.

Contexte. Jusqu'au 23/08/2026, `heure_locale` sortait d'une conversion qui prenait
l'étiquette `+00:00` d'EDF au mot. Elle est fausse : ce jeu porte l'heure légale corse.
Trois figures publiées (T2b, T3, T4) et plusieurs phrases de l'étude lisaient donc une
heure en retard d'une à deux heures selon la saison — « l'heure la plus verte est 14 h »
en tête.

Ce qui a manqué la première fois n'est pas un test, c'est une **contrainte extérieure au
système**. Un test dérivé du même code aurait confirmé qu'on avait codé ce qu'on croyait
coder, pas que ce qu'on croyait était vrai. Les quatre verrous ci-dessous ont donc été
choisis pour que leur erreur ne PUISSE PAS être corrélée à celle de la chaîne :

- **V1** le comportement aux deux bascules d'heure légale — une convention humaine ;
- **V2** la stabilité sous un fuseau de session hostile — la machine ne doit rien décider ;
- **V3** la cohérence avec le pyranomètre `GLO` de Météo-France — autre producteur, autre
  instrument, même soleil — et avec le témoin sarde, qui disculpe l'instrument ;
- **V4** le midi solaire, calculé ici en astronomie pure : ni DuckDB, ni `zoneinfo`, ni
  une ligne du dépôt n'entrent dans ce repère.

V1 et V3 partagent le pyranomètre mais pas la question : V3 demande « la série est-elle
posée sur le soleil ? », V1 « son décalage bouge-t-il quand seule l'heure légale bouge ? ».
Une erreur d'instrument casserait V3 sans casser V1 ; un double comptage d'heure d'été
casse V1 sans forcément déplacer la moyenne annuelle de V3.
"""

from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
import pytest

from demonstrateur.config import DATA_PROCESSED, DATA_RAW

COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"
SARD = DATA_PROCESSED / "entsoe_sardaigne.parquet"
METEO_FIGE = DATA_RAW / "meteo_horaire_corse_2020_2024.csv.gz"
METEO_GLISSANT = DATA_RAW / "meteo_horaire_corse.csv.gz"

pytestmark = pytest.mark.skipif(
    not (COURBE.exists() and METEO_FIGE.exists() and METEO_GLISSANT.exists()),
    reason="courbe corse ou météo brute absente — lancer fetch-data puis prepare",
)

PARIS = ZoneInfo("Europe/Paris")
# Ajaccio (poste Météo-France 20004002). La longitude est le seul paramètre qui compte
# pour le midi solaire ; les trois postes corses tiennent dans 0,7° (2,8 min de soleil).
LAT_AJACCIO, LON_AJACCIO = 41.918, 8.7927
LAGS = range(-3, 4)


# --------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def glo() -> pd.Series:
    """Rayonnement global horaire, moyenne des trois pyranomètres corses.

    L'étiquette `AAAAMMJJHH` de Météo-France est en UTC — établi sur la structure du
    fichier, pas sur une déclaration : les deux dimanches de changement d'heure portent
    24 heures chacun, ce que seule une échelle à décalage fixe permet (cf. la docstring
    de `meteo_corse_to_parquet`). On garde les codes qualité 1 (validée) et 9 (filtrée),
    comme la préparation.
    """
    return duckdb.connect().execute(
        f"""SELECT strptime(AAAAMMJJHH, '%Y%m%d%H') AS t,
                   avg(CAST(GLO AS DOUBLE)) AS glo
            FROM read_csv(['{METEO_FIGE.as_posix()}', '{METEO_GLISSANT.as_posix()}'],
                          delim=';', header=true, all_varchar=true, union_by_name=true)
            WHERE GLO IS NOT NULL AND QGLO IN ('1', '9')
            GROUP BY 1"""
    ).df().set_index("t")["glo"]


@pytest.fixture(scope="module")
def pv_corse() -> pd.Series:
    """Photovoltaïque corse, daté par l'INSTANT interprété — la colonne à mettre en cause."""
    return duckdb.connect().execute(
        f"""SELECT date_heure_utc AS t, photovoltaique_mw AS pv
            FROM '{COURBE.as_posix()}'"""
    ).df().set_index("t")["pv"]


# ----------------------------------------------------------------------- outils
def _correlations(serie: pd.Series, glo: pd.Series, garder=None) -> dict[int, float]:
    """Corrélation de `serie` avec `glo` pour chaque décalage entier, en heures."""
    out = {}
    for lag in LAGS:
        s = serie.copy()
        s.index = s.index + pd.Timedelta(hours=int(lag))
        j = pd.concat({"pv": s, "glo": glo}, axis=1).dropna()
        if garder is not None:
            j = j[garder(j.index)]
        out[lag] = float(j["pv"].corr(j["glo"])) if len(j) > 200 else float("nan")
    return out


def _optimum_fin(cor: dict[int, float]) -> float:
    """Décalage optimal affiné : parabole sur le sommet et ses deux voisins.

    Sans cet affinage, un test à l'heure entière ne distinguerait pas +0,55 h de +1,45 h,
    et laisserait passer une demi-heure de dérive.
    """
    k = max((c for c in cor if not math.isnan(cor[c])), key=lambda c: cor[c])
    if k - 1 not in cor or k + 1 not in cor:
        return float(k)
    a, b, c = cor[k - 1], cor[k], cor[k + 1]
    d = a - 2 * b + c
    return k + (0.5 * (a - c) / d if d else 0.0)


def _est_heure_ete(index: pd.DatetimeIndex) -> np.ndarray:
    """Vrai quand l'instant UTC tombe en heure d'été légale (CEST)."""
    return np.array([
        dt.datetime(t.year, t.month, t.day, t.hour, tzinfo=dt.timezone.utc)
        .astimezone(PARIS).utcoffset().total_seconds() == 7200
        for t in index
    ])


def _bascules(an1: int, an2: int) -> list[tuple[str, int, pd.Timestamp]]:
    """Les dimanches de changement d'heure, en instants UTC (01 h UTC, règle européenne)."""
    out = []
    for an in range(an1, an2 + 1):
        for mois, nom in ((3, "printemps"), (10, "automne")):
            d = pd.Timestamp(year=an, month=mois, day=31)
            while d.dayofweek != 6:
                d -= pd.Timedelta(days=1)
            out.append((nom, an, d + pd.Timedelta(hours=1)))
    return out


def _midi_solaire_legal(an: int, mois: int, jour: int, lon: float) -> float:
    """Midi solaire vrai, en heure légale décimale — ASTRONOMIE PURE.

    Équation du temps par la formule NOAA (année fractionnaire). Le seul emprunt au reste
    du monde logiciel est le décalage légal du jour, qui est une donnée de calendrier et
    non un traitement de la donnée EDF. Aucun code du dépôt n'intervient : c'est ce qui
    fait de ce repère une contrainte EXTÉRIEURE, et non un miroir de la conversion testée.
    """
    n = dt.date(an, mois, jour).timetuple().tm_yday
    g = 2 * math.pi / 365.0 * (n - 1 + 0.5)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
        - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g)
    )  # minutes
    utc = 12.0 - lon / 15.0 - eqtime / 60.0
    offset = dt.datetime(an, mois, jour, 12, tzinfo=dt.timezone.utc).astimezone(
        PARIS
    ).utcoffset().total_seconds() / 3600.0
    return utc + offset


# ------------------------------------------------------- V1 : bascules d'heure légale
def test_v1_le_decalage_ne_saute_pas_aux_bascules_d_heure_legale(pv_corse, glo):
    """Le décalage optimal doit être le MÊME de part et d'autre du changement d'heure.

    C'est le verrou qui a révélé le défaut. Trois semaines avant, trois semaines après :
    même saison, même parc, même soleil — seule l'heure légale a bougé. Avec l'ancienne
    lecture, le décalage sautait d'exactement une heure aux dix bascules de 2020-2024
    (0,66 à 1,11 h) ; le témoin sarde, lui, ne bougeait pas de plus de 0,28 h. Aucune
    propriété physique d'un parc ne produit un saut discret calé sur une convention
    humaine : ce test ne peut échouer que sur un traitement d'horodatage.
    """
    fenetre = pd.Timedelta(days=21)
    sauts = {}
    for nom, an, t in _bascules(2020, 2024):
        avant = _correlations(pv_corse, glo, lambda i, t=t, f=fenetre: (i >= t - f) & (i < t))
        apres = _correlations(pv_corse, glo, lambda i, t=t, f=fenetre: (i >= t) & (i < t + f))
        if any(math.isnan(v) for v in (*avant.values(), *apres.values())):
            continue
        sauts[f"{nom} {an}"] = _optimum_fin(apres) - _optimum_fin(avant)

    assert len(sauts) >= 8, f"trop peu de bascules mesurables ({len(sauts)}) — donnée tronquée ?"
    fautives = {k: round(v, 2) for k, v in sauts.items() if abs(v) > 0.5}
    assert not fautives, (
        f"le décalage au pyranomètre saute au changement d'heure légale : {fautives} — "
        "l'heure d'été est comptée deux fois quelque part. Mesuré à 0,34 h au maximum "
        "le 23/08/2026, contre 1,11 h avant correction."
    )


# ------------------------------------------------- V2 : indépendance au fuseau de session
@pytest.mark.parametrize("zone", ["UTC", "Pacific/Kiritimati", "Pacific/Niue"])
def test_v2_la_preparation_ne_depend_pas_du_fuseau_de_la_session(tmp_path, monkeypatch, zone):
    """Rebâtir la courbe sous un fuseau de session hostile doit donner la MÊME table.

    `extract()` sur un horodatage à fuseau se lit dans le fuseau de la SESSION : la même
    donnée découpait donc ses années autrement sur un poste français et sur le runner
    d'intégration, qui tourne en UTC. Kiritimati (UTC+14) et Niue (UTC−11) encadrent
    l'amplitude réelle des fuseaux ; si une seule ligne bouge, une borne d'année ou une
    heure de la journée dépend de la machine, ce qui est une autre façon de ne pas savoir.
    """
    from demonstrateur import prepare

    connect = duckdb.connect

    def connect_zone(*a, **k):
        con = connect(*a, **k)
        con.execute(f"SET TimeZone='{zone}'")
        return con

    monkeypatch.setattr(prepare.duckdb, "connect", connect_zone)
    assert connect_zone().execute("SELECT current_setting('TimeZone')").fetchone()[0] == zone, (
        "le fuseau de session n'a pas été imposé — le test serait vide de sens"
    )
    autre = tmp_path / "courbe.parquet"
    prepare.courbe_corse_to_parquet(autre.as_posix())

    ecart = connect().execute(
        f"""SELECT count(*) FROM (
              (SELECT * FROM '{COURBE.as_posix()}' EXCEPT SELECT * FROM '{autre.as_posix()}')
              UNION ALL
              (SELECT * FROM '{autre.as_posix()}' EXCEPT SELECT * FROM '{COURBE.as_posix()}')
            )"""
    ).fetchone()[0]
    assert ecart == 0, (
        f"{ecart} ligne(s) diffèrent entre le fuseau du poste et {zone} — la courbe "
        "dépend de la machine qui la construit."
    )


@pytest.mark.parametrize("zone", ["UTC", "Pacific/Kiritimati"])
def test_v2_les_chiffres_publies_ne_dependent_pas_du_fuseau_de_session(monkeypatch, zone):
    """Les nombres qui partent dans les figures et la note doivent être invariants aussi.

    La préparation peut être propre et la LECTURE fautive : c'est arrivé côté sarde, où
    `heure_locale` portait l'heure UTC parce qu'un `extract` relisait dans le fuseau de la
    machine. On rejoue donc les producteurs de chiffres publiés — le mix de T6 et la note
    méthodologique — et non des requêtes réécrites pour l'occasion.
    """
    from demonstrateur import figures, note_elec

    connect = duckdb.connect

    def connect_zone(*a, **k):
        con = connect(*a, **k)
        con.execute(f"SET TimeZone='{zone}'")
        return con

    reference = (figures.mix_t6()[2], figures.mix_t6()[3], note_elec._chiffres())
    monkeypatch.setattr(figures.duckdb, "connect", connect_zone)
    monkeypatch.setattr(note_elec.duckdb, "connect", connect_zone)
    obtenu = (figures.mix_t6()[2], figures.mix_t6()[3], note_elec._chiffres())

    assert obtenu[0] == reference[0], f"bornes corses de T6 déplacées sous {zone}"
    assert obtenu[1] == reference[1], f"bornes sardes de T6 déplacées sous {zone}"
    for cle, attendu in reference[2].items():
        assert obtenu[2][cle] == attendu, (
            f"la note méthodologique change de « {cle} » sous {zone} : "
            f"{obtenu[2][cle]} au lieu de {attendu}"
        )


# --------------------------------------------------------- V3 : cohérence au pyranomètre
def test_v3_le_pv_s_aligne_sur_le_pyranometre_sans_ecart_saisonnier(pv_corse, glo):
    """Même décalage l'hiver et l'été, et le même que le témoin sarde.

    Le pyranomètre date ses cumuls par la FIN de l'intervalle, EDF et ENTSO-E par le
    début : d'où un décalage attendu de +1 h, constant. Ce qui compte n'est pas sa valeur
    mais sa CONSTANCE — et qu'une série tierce, déjà validée contre le soleil, donne la
    même. Sans ce témoin, une dérive saisonnière de l'instrument resterait indiscernable
    d'une dérive de la donnée corse.
    """
    if not SARD.exists():
        pytest.skip("Sardaigne absente — le témoin manque (jeton ENTSO-E)")

    hiver = _optimum_fin(_correlations(pv_corse, glo, lambda i: ~_est_heure_ete(i)))
    ete = _optimum_fin(_correlations(pv_corse, glo, lambda i: _est_heure_ete(i)))
    assert abs(ete - hiver) <= 0.5, (
        f"décalage au pyranomètre : {hiver:+.2f} h l'hiver contre {ete:+.2f} h l'été — "
        "un écart saisonnier signale un double comptage de l'heure d'été."
    )

    sard = duckdb.connect().execute(
        f"SELECT date_heure AS t, solaire_mw AS pv FROM '{SARD.as_posix()}'"
    ).df().set_index("t")["pv"]
    temoin = _optimum_fin(_correlations(sard, glo))
    corse = _optimum_fin(_correlations(pv_corse, glo))
    assert abs(corse - temoin) <= 0.5, (
        f"la Corse se cale à {corse:+.2f} h du pyranomètre quand la Sardaigne — même "
        f"longitude, même fuseau, convention ENTSO-E connue — se cale à {temoin:+.2f} h. "
        "Les deux îles ne sont plus sur la même échelle de temps."
    )


# ------------------------------------------------------------------ V4 : midi solaire
def _mi_hauteur(heures: np.ndarray, valeurs: np.ndarray) -> float:
    """Milieu du profil à mi-hauteur : moyenne des deux passages à la moitié du maximum.

    Préféré au centre de masse, qui vit dans les queues du profil. Le parc corse produit
    en hiver nettement moins le matin que l'après-midi — jusqu'à +0,68 h de centre de
    masse en décembre — sans que le pyranomètre montre rien de tel : c'est une propriété
    du parc (relief à l'est, soleil rasant), pas un horodatage. La mi-hauteur l'ignore et
    garde toute sa sensibilité à ce qu'on cherche, un décalage en bloc.
    """
    ordre = np.argsort(heures)
    x, y = heures[ordre], valeurs[ordre]
    demi = y.max() / 2.0

    def passage(depart: int, sens: int) -> float:
        for i in range(depart, len(y) - 1 if sens > 0 else 0, sens):
            a, b = y[i], y[i + sens]
            if a < demi <= b:
                return float(x[i] + sens * (demi - a) / (b - a))
        return float("nan")

    return (passage(0, 1) + passage(len(y) - 1, -1)) / 2.0


def _profil_mensuel(con, requete: str, milieu: float) -> dict[int, float]:
    """Milieu à mi-hauteur du profil moyen de chaque mois, en heure légale décimale.

    `milieu` place l'instant représentatif du créneau étiqueté : +0,5 h pour une série
    datée par le DÉBUT de son intervalle (EDF, ENTSO-E), −0,5 h pour une série datée par
    la FIN (les cumuls horaires de Météo-France).
    """
    df = con.execute(requete).df()
    return {
        m: _mi_hauteur(df[df["m"] == m]["h"].values + milieu, df[df["m"] == m]["v"].values)
        for m in range(1, 13)
    }


def test_v4_le_pyranometre_tombe_sur_le_midi_solaire(glo):
    """L'ANCRE d'abord : elle doit se valider avant de juger quoi que ce soit.

    Si ce test échoue, ce n'est pas la courbe EDF qui est en cause mais le repère lui-même
    — fuseau du fichier Météo-France, convention de datation de ses cumuls, ou l'équation
    du temps écrite ici. Le faire échouer en premier évite d'accuser la bonne série sur la
    foi d'une mauvaise règle. Mesuré à 0,13 h au maximum sur les douze mois le 23/08/2026.
    """
    ecarts = {}
    for m in range(1, 13):
        sous = glo[glo.index.month == m]
        loc = sous.index.tz_localize("UTC").tz_convert(PARIS)
        moyenne = sous.groupby(loc.hour).mean()
        milieu = _mi_hauteur(moyenne.index.values.astype(float) - 0.5, moyenne.values)
        ecarts[m] = round(milieu - _midi_solaire_legal(2022, m, 15, LON_AJACCIO), 2)

    fautifs = {m: e for m, e in ecarts.items() if abs(e) > 0.25}
    assert not fautifs, (
        f"le pyranomètre ne tombe plus au midi solaire pour les mois {fautifs} "
        f"(tous les écarts : {ecarts}) — c'est L'ANCRE qui est en cause, pas la courbe "
        "EDF : vérifier le fuseau du fichier Météo-France et la datation de ses cumuls "
        "AVANT de conclure quoi que ce soit sur l'horodatage corse."
    )


def test_v4_le_profil_solaire_corse_tombe_sur_le_midi_solaire():
    """Mois par mois, le profil solaire corse doit se poser sur le midi solaire.

    Repère calculé en astronomie pure (cf. `_midi_solaire_legal`) : la conversion mise en
    cause n'est pas son propre juge. On mesure sur `heure_locale`, la colonne que lisent
    T2b, T3 et T4 — c'est elle qu'il faut protéger, pas une colonne intermédiaire.

    Tolérance 0,4 h : les douze mois tenaient dans 0,20 h le 23/08/2026, et une erreur
    d'une heure les déplace tous du même montant, donc les fait tous sortir. Avec
    l'ancienne lecture, l'écart valait +1 h l'hiver et +2 h l'été.
    """
    con = duckdb.connect()
    profil = _profil_mensuel(
        con,
        f"""SELECT mois_local AS m, heure_locale AS h,
                   avg(greatest(photovoltaique_mw, 0)) AS v
            FROM '{COURBE.as_posix()}' GROUP BY 1, 2""",
        milieu=+0.5,
    )
    ecarts = {m: round(v - _midi_solaire_legal(2022, m, 15, LON_AJACCIO), 2)
              for m, v in profil.items()}

    fautifs = {m: e for m, e in ecarts.items() if abs(e) > 0.4}
    assert not fautifs, (
        f"le profil solaire ne tombe pas au midi solaire pour les mois {fautifs} "
        f"(tous les écarts : {ecarts}) — `heure_locale` ne peut pas servir à publier "
        "une heure de la journée."
    )
    # Et le biais ne doit pas être systématique : douze mois décalés du même côté
    # signaleraient un décalage constant, qu'une tolérance par mois laisserait passer.
    moyen = sum(ecarts.values()) / 12
    assert abs(moyen) <= 0.25, (
        f"biais moyen de {moyen:+.2f} h sur les douze mois — décalage constant, pas du bruit."
    )
