"""Verrou de régression sur le recoupement SARCO — ENTSO-E/Terna contre EDF SEI.

Ce que ce fichier tient, et ce qu'il ne prétend pas tenir.

La liaison SARCO relie le réseau sarde au réseau corse. ENTSO-E publie ses flux physiques
mesurés du côté **italien** : autre opérateur, autre pays, autres compteurs. C'est la
seule mesure de l'approvisionnement corse trouvée le 23/08/2026 dont l'erreur ne puisse
pas être corrélée à celle d'EDF — les bilans EDF SEI, l'OREGES et RTE ayant tous été
écartés pour cette raison (cf. `docs/VERIF_ENTSOE_TERNA.md` § 9).

**Ce n'est pas un test de validité.** La tolérance ci-dessous a été choisie APRÈS avoir
observé les écarts ; en faire une bande de validation serait circulaire. C'est un verrou
de **régression** : il tient les trois résultats publiés et casse si le parseur A11, la
convention de signe, le calcul du solde ou la donnée amont changent. Ce que ces résultats
signifient est écrit dans le document, pas ici.

Il ne dit rien non plus des 70,2 % de génération locale que compare T6 : SARCO pèse
17,8 % de l'offre corse 2020, SACOI 12,0 % sans témoin extérieur.
"""

from __future__ import annotations

import duckdb
import pytest

from demonstrateur.config import DATA_PROCESSED
from demonstrateur.prepare import SARCO_ANNEES, SARCO_EDF_SEI_GWH, SARCO_SENS

SARCO = DATA_PROCESSED / "entsoe_sarco.parquet"

pytestmark = pytest.mark.skipif(
    not SARCO.exists(),
    reason="entsoe_sarco.parquet absent — lancer fetch-data puis prepare (jeton ENTSO-E)",
)

# Mesuré le 23/08/2026, lecture « positions déclarées ». Les sources étant figées et
# vérifiées par empreinte, ces valeurs sont déterministes : la tolérance sert à absorber
# l'arithmétique flottante, pas une variabilité de la donnée.
ATTENDU = {
    #        entrant    sortant       net
    2020: (397.6553, 4.1137, 393.5417),
    2021: (418.4764, 1.6047, 416.8717),
    2023: (396.4995, 0.9194, 395.5800),
}
ECARTS_PCT = {2020: +0.1378, 2021: -0.2699, 2023: -0.1061}


@pytest.fixture(scope="module")
def con():
    return duckdb.connect()


def _energie(con, reconduire: bool):
    """GWh par année et par sens. `reconduire` applique la règle A03 du curveType."""
    filtre = "" if reconduire else "WHERE declare"
    rows = con.execute(
        f"""SELECT annee, sens, sum(mw * minutes / 60.0) / 1000 AS gwh
            FROM '{SARCO.as_posix()}' {filtre} GROUP BY 1, 2"""
    ).fetchall()
    return {(int(a), s): g for a, s, g in rows}


def test_les_deux_sens_et_les_trois_annees_sont_presents(con):
    """La table couvre exactement ce que `sources.yaml` déclare — ni plus, ni moins.

    Le « ni plus » compte autant : 2019, 2022 et 2024 se mesurent tout aussi bien, et ont
    été délibérément laissés hors du registre faute de contrepartie EDF SEI à confronter.
    Si un jour ils y entrent, que ce soit une décision, pas une dérive.
    """
    trouves = {(int(a), s) for a, s in con.execute(
        f"SELECT DISTINCT annee, sens FROM '{SARCO.as_posix()}'").fetchall()}
    attendus = {(an, s) for an in SARCO_ANNEES for s in SARCO_SENS}
    assert trouves == attendus, f"couples (année, sens) présents : {sorted(trouves)}"


def test_les_flux_bruts_de_chaque_sens_ne_bougent_pas(con):
    """Les deux quantités MESURÉES, séparément — avant toute soustraction."""
    e = _energie(con, reconduire=False)
    for an, (ent, sor, _) in ATTENDU.items():
        assert e[(an, "entrant")] == pytest.approx(ent, abs=0.05), (
            f"flux Sardaigne->Corse {an} : {e[(an, 'entrant')]:.4f} GWh au lieu de {ent}"
        )
        assert e[(an, "sortant")] == pytest.approx(sor, abs=0.05), (
            f"flux Corse->Sardaigne {an} : {e[(an, 'sortant')]:.4f} GWh au lieu de {sor}"
        )


def test_le_solde_recalcule_par_la_chaine_ne_bouge_pas(con):
    """Le solde net, que NOTRE chaîne calcule — EDF SEI en publie un, ENTSO-E deux bruts.

    C'est la soustraction que ce test verrouille, pas une valeur reçue.
    """
    e = _energie(con, reconduire=False)
    for an, (_, _, net) in ATTENDU.items():
        obtenu = e[(an, "entrant")] - e[(an, "sortant")]
        assert obtenu == pytest.approx(net, abs=0.05), (
            f"solde net SARCO {an} : {obtenu:.4f} GWh au lieu de {net}"
        )


def test_les_trois_ecarts_avec_edf_sei_ne_bougent_pas(con):
    """Les trois écarts publiés au § 9 du document de vérification.

    Verrou de TEXTE autant que de calcul : ces trois nombres sont écrits dans
    `docs/VERIF_ENTSOE_TERNA.md`. S'ils bougent, la phrase publiée est fausse.
    """
    e = _energie(con, reconduire=False)
    assert set(SARCO_EDF_SEI_GWH) == set(ATTENDU), (
        "les millésimes publiés par EDF SEI et ceux du verrou ont divergé"
    )
    for an, ref in SARCO_EDF_SEI_GWH.items():
        net = e[(an, "entrant")] - e[(an, "sortant")]
        ecart = 100 * (net - ref) / ref
        assert ecart == pytest.approx(ECARTS_PCT[an], abs=0.02), (
            f"écart {an} contre EDF SEI ({ref} GWh) : {ecart:+.4f} % au lieu de "
            f"{ECARTS_PCT[an]:+.4f} % — le § 9 du document publie l'ancienne valeur"
        )


def test_la_conclusion_ne_depend_pas_de_la_convention_a03(con):
    """La règle `curveType A03` ne change pas la conclusion — c'est un acquis à tenir.

    Les positions absentes d'une `Period` reconduisent la dernière valeur connue. Fallait-il
    les compter ? Sur ces trois millésimes la question ne tranche rien : les deux lectures
    donnent des écarts de même ordre et de même petitesse. Ce test empêche qu'une future
    correction du parseur transforme un choix indifférent en choix décisif sans qu'on le
    voie — auquel cas il faudrait trancher la convention pour de bon, et le dire.
    """
    declare, reconduit = _energie(con, False), _energie(con, True)
    for an, ref in SARCO_EDF_SEI_GWH.items():
        ecarts = [
            100 * ((e[(an, "entrant")] - e[(an, "sortant")]) - ref) / ref
            for e in (declare, reconduit)
        ]
        assert max(abs(x) for x in ecarts) < 0.5, (
            f"{an} : écarts {ecarts[0]:+.2f} % (déclarées) et {ecarts[1]:+.2f} % (report) "
            "— l'un des deux sort de l'ordre de grandeur publié"
        )
        assert abs(ecarts[0] - ecarts[1]) < 0.25, (
            f"{an} : la convention A03 déplace l'écart de {abs(ecarts[0]-ecarts[1]):.2f} "
            "point — elle n'est plus indifférente, il faut la trancher et l'écrire"
        )


def test_aucun_flux_negatif_ni_solde_stocke(con):
    """Un sens porte un FLUX, jamais un solde — sinon la soustraction compterait deux fois.

    Doublon volontaire de la garde de `prepare` : celle-ci protège la construction, ce
    test protège le fichier publié, y compris s'il a été produit par une version
    antérieure de la chaîne.
    """
    neg, colonnes = con.execute(
        f"""SELECT count(*) FILTER (WHERE mw < 0),
                   (SELECT count(*) FROM (DESCRIBE SELECT * FROM '{SARCO.as_posix()}'))
            FROM '{SARCO.as_posix()}'"""
    ).fetchone()
    assert neg == 0, f"{neg} point(s) de flux négatif dans la table SARCO"
    assert colonnes == 6, (
        f"la table SARCO a {colonnes} colonnes — si un solde y a été ajouté, il est "
        "calculé et n'a rien à faire à côté des deux mesures"
    )
