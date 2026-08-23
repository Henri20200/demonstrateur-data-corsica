"""Verrou de régression : émissions vérifiées SEQE-UE contre production thermique corse.

Ce que ce fichier tient — et la formulation compte, parce qu'il serait facile d'en dire
trop. Les trois installations thermiques corses déclarent chaque année leurs émissions au
titre du système d'échange de quotas ; ces émissions sont vérifiées par une tierce partie
accréditée et engagent financièrement l'exploitant. C'est une **contrainte physique
extérieure à la série de production**, dans une chaîne de déclaration distincte.

Ce n'est PAS une validation indépendante du niveau absolu du thermique. Les deux chaînes
peuvent partager la même mesure de combustible en amont, auquel cas l'indépendance s'arrête
au vérificateur. Et un biais constant sur les six années serait absorbé sans laisser de
trace : c'est une rupture de RÉGIME qu'on cherche ici, pas un étalonnage.

Le résultat tenu, tel qu'il est publié au § 10 de `docs/VERIF_ENTSOE_TERNA.md` :

    Aucune rupture propre aux années « Estimé » n'est détectable dans le rapport entre
    production thermique EDF et émissions vérifiées : le ratio reste compris entre 684 et
    695 tCO2/GWh sur 2019-2024, et sa moyenne diffère de 0,5 % entre années Validé et
    Estimé.

Le rendement implicite qu'on peut en tirer (~40 %) n'est délibérément PAS verrouillé ici :
il dépend d'un facteur d'émission et d'un pouvoir calorifique de littérature, pas de
l'installation. Il a sa place dans le document, avec ses hypothèses, pas dans une assertion
qui laisserait croire qu'on connaît le rendement réel des centrales.
"""

from __future__ import annotations

import duckdb
import pytest

from demonstrateur.config import DATA_PROCESSED
from demonstrateur.prepare import SEQE_ANNEES, SEQE_CORSE

SEQE = DATA_PROCESSED / "seqe_corse.parquet"
COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"

pytestmark = pytest.mark.skipif(
    not (SEQE.exists() and COURBE.exists()),
    reason="Parquet SEQE ou courbe absent — lancer fetch-data puis prepare",
)

# Mesurés le 23/08/2026. Sources figées et vérifiées par empreinte : ces valeurs sont
# déterministes, la tolérance absorbe l'arithmétique flottante et rien d'autre.
RATIOS = {
    2019: 693.52, 2020: 694.76, 2021: 694.86,
    2022: 684.25, 2023: 692.64, 2024: 691.28,
}
BORNES = (684.0, 695.0)          # ce que le document publie
ECART_REGIME_PCT = -0.487        # (moyenne Estimé − moyenne Validé) / moyenne Validé


@pytest.fixture(scope="module")
def ratios():
    """tCO2 vérifiés par GWh thermique déclaré, année par année, avec le statut EDF."""
    return duckdb.connect().execute(
        f"""SELECT c.annee, e.tco2 / c.gwh AS ratio, c.statut
            FROM (SELECT annee, sum(tco2) AS tco2
                  FROM '{SEQE.as_posix()}' GROUP BY 1) e
            JOIN (SELECT annee_locale AS annee, sum(thermique_mw) / 1000 AS gwh,
                         any_value(statut) AS statut
                  FROM '{COURBE.as_posix()}' GROUP BY 1) c USING (annee)
            ORDER BY c.annee"""
    ).df()


def test_les_deux_series_couvrent_la_meme_fenetre(ratios):
    """Le rapport n'a de sens qu'entre deux séries qui parlent des mêmes années.

    Une année présente d'un seul côté disparaîtrait silencieusement de la jointure, et la
    comparaison de régime porterait alors sur un échantillon amputé sans le dire.
    """
    assert list(ratios["annee"].astype(int)) == list(SEQE_ANNEES), (
        f"années appariées : {list(ratios['annee'].astype(int))} — attendu {list(SEQE_ANNEES)}"
    )
    sites = duckdb.connect().execute(
        f"SELECT count(DISTINCT eutl_id) FROM '{SEQE.as_posix()}'").fetchone()[0]
    assert sites == len(SEQE_CORSE), (
        f"{sites} installation(s) au registre au lieu de {len(SEQE_CORSE)} — une centrale "
        "manquante ferait chuter le rapport sans que rien ne le signale"
    )


def test_le_rapport_emissions_production_ne_bouge_pas(ratios):
    """Les six valeurs observées, année par année. Verrou de régression pur."""
    obtenu = dict(zip(ratios["annee"].astype(int), ratios["ratio"]))
    for an, attendu in RATIOS.items():
        assert obtenu[an] == pytest.approx(attendu, abs=0.05), (
            f"{an} : {obtenu[an]:.2f} tCO2/GWh au lieu de {attendu} — la donnée amont ou "
            "le périmètre des installations a bougé"
        )


def test_le_rapport_reste_dans_les_bornes_publiees(ratios):
    """Les bornes 684-695 sont écrites dans le document ; elles doivent rester vraies.

    Ce sont les valeurs OBSERVÉES, pas une bande de tolérance choisie d'avance : si le
    ratio en sort, ce n'est pas le test qu'il faut élargir, c'est la phrase publiée qu'il
    faut refaire.
    """
    bas, haut = BORNES
    hors = {int(a): round(r, 2) for a, r in zip(ratios["annee"], ratios["ratio"])
            if not bas <= r <= haut}
    assert not hors, (
        f"ratio hors des bornes publiées {BORNES} : {hors} — le § 10 du document annonce "
        "« compris entre 684 et 695 tCO2/GWh »"
    )


def test_aucune_rupture_au_passage_valide_estime(ratios):
    """LE test que ce jeu de données sert à faire.

    Si le passage au statut « Estimé » avait introduit une discontinuité de niveau sur la
    filière thermique, le rapport à une grandeur physique extérieure aurait dû sauter à
    2021. Il ne saute pas. La réserve reste écrite au § 10 : un biais CONSTANT sur les six
    années passerait au travers, et l'indépendance amont des deux chaînes est inconnue.
    """
    valide = ratios.loc[ratios["statut"] == "Validé", "ratio"]
    estime = ratios.loc[ratios["statut"] == "Estimé", "ratio"]
    assert len(valide) == 2 and len(estime) == 4, (
        f"répartition des statuts inattendue : {len(valide)} validées, {len(estime)} estimées"
    )
    ecart = 100 * (estime.mean() - valide.mean()) / valide.mean()
    assert ecart == pytest.approx(ECART_REGIME_PCT, abs=0.05), (
        f"écart de régime Validé -> Estimé : {ecart:+.2f} % au lieu de "
        f"{ECART_REGIME_PCT:+.2f} % — le § 10 publie « 0,5 % »"
    )
