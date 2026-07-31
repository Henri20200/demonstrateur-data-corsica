"""Tests de résultats : les chiffres affichés par les visuels tiennent dans la donnée.

Complément analytique des tests de fumée (décision du 19/07/2026, post-audit) : chaque
test verrouille une affirmation publiée — une régression silencieuse de `prepare` ou une
mise à jour de la source qui déplacerait un chiffre-titre doit faire échouer la suite,
pas passer inaperçue. Nécessite le pipeline : `fetch-data` puis
`python -m demonstrateur.prepare` (sans data/processed, ces tests sont sautés).
"""

import duckdb
import pytest

from demonstrateur.config import DATA_PROCESSED, DATA_RAW

COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"
MIX = DATA_PROCESSED / "edf_mix_corse.parquet"
ECRET = DATA_PROCESSED / "edf_ecretement_corse.parquet"
SARD = DATA_PROCESSED / "entsoe_sardaigne.parquet"
SARD_XML = DATA_RAW / "entsoe_sardaigne_2023.xml"
AIR = DATA_PROCESSED / "air_corse.parquet"

besoin_courbe = pytest.mark.skipif(
    not COURBE.exists(), reason="data/processed absent — lancer fetch-data puis prepare"
)
besoin_mix = pytest.mark.skipif(
    not MIX.exists(), reason="data/processed absent — lancer fetch-data puis prepare"
)
besoin_ecret = pytest.mark.skipif(
    not ECRET.exists(), reason="data/processed absent — lancer fetch-data puis prepare"
)
besoin_sard = pytest.mark.skipif(
    not SARD.exists(), reason="parquet Sardaigne absent — fetch-data (jeton ENTSO-E) puis prepare"
)
besoin_sard_xml = pytest.mark.skipif(
    not SARD_XML.exists(), reason="XML Sardaigne absent — fetch-data (jeton ENTSO-E) requis"
)
besoin_air = pytest.mark.skipif(
    not AIR.exists(), reason="parquet air absent — lancer fetch-data puis prepare"
)


@pytest.fixture(scope="module")
def con():
    return duckdb.connect()


@besoin_courbe
def test_bond_juin_juillet(con):
    """T2 titre le « +22 % en juillet » : le bond recalculé doit encore l'arrondir à 22."""
    juin, juillet = con.execute(
        f"""SELECT avg(production_totale_mw) FILTER (WHERE mois_local = 6),
                   avg(production_totale_mw) FILTER (WHERE mois_local = 7)
            FROM '{COURBE.as_posix()}'"""
    ).fetchone()
    bond = 100 * (juillet - juin) / juin
    assert bond == pytest.approx(21.9, abs=0.5), (
        f"bond juin→juillet = {bond:.2f} % — le chiffre publié par T2 ne tient plus"
    )
    assert round(bond) == 22, "le titre de T2 écrit « +22 % » en dur : à réaligner"


@besoin_courbe
def test_heure_la_plus_verte_14h(con):
    """T4 : argmax à 14 h pour les DEUX définitions, valeurs 34,4 % / 48,1 % (libellées)."""
    df = con.execute(
        f"""SELECT heure_locale,
              100*sum(enr_distrib_mw)/sum(production_totale_mw)                AS decentralise,
              100*sum(enr_distrib_mw+hydraulique_mw)/sum(production_totale_mw) AS avec_hydro
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    h_dec = int(df.loc[df["decentralise"].idxmax(), "heure_locale"])
    h_tot = int(df.loc[df["avec_hydro"].idxmax(), "heure_locale"])
    assert h_dec == 14 and h_tot == 14, (
        f"heure la plus verte : {h_dec} h (décentralisé) / {h_tot} h (avec grande hydro) "
        "— le « 14 h » publié par T4 ne tient plus"
    )
    v14 = df.loc[df["heure_locale"] == 14].iloc[0]
    assert float(v14["decentralise"]) == pytest.approx(34.4, abs=0.5), (
        "T4 affiche « 34 % renouvelable décentralisé » : valeur à revoir"
    )
    assert float(v14["avec_hydro"]) == pytest.approx(48.1, abs=0.5), (
        "T4 affiche « 48 % avec la grande hydraulique » : valeur à revoir"
    )


@besoin_courbe
def test_solaire_sous_thermique_ete(con):
    """T3 : à aucune heure moyenne d'été le solaire n'atteint le thermique."""
    marge = con.execute(
        f"""SELECT min(thermique - solaire) FROM (
              SELECT 100*sum(photovoltaique_mw)/sum(production_totale_mw) AS solaire,
                     100*sum(thermique_mw)/sum(production_totale_mw)      AS thermique
              FROM '{COURBE.as_posix()}' WHERE mois_local IN (6, 7, 8)
              GROUP BY heure_locale)"""
    ).fetchone()[0]
    assert marge > 0, (
        f"marge thermique − solaire minimale = {marge:.2f} pt — le titre de T3 ne tient plus"
    )


@besoin_courbe
def test_surcroit_juillet_le_soir(con):
    """T2b : surcroît juillet − juin positif aux 24 heures, maximal le soir (16-22 h)."""
    df = con.execute(
        f"""SELECT heure_locale,
              avg(production_totale_mw) FILTER (WHERE mois_local = 7)
              - avg(production_totale_mw) FILTER (WHERE mois_local = 6) AS delta
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    assert len(df) == 24 and (df["delta"] > 0).all(), (
        "le surcroît juillet − juin n'est plus positif à chaque heure — T2b à revoir"
    )
    h_max = int(df.loc[df["delta"].idxmax(), "heure_locale"])
    assert 16 <= h_max <= 22, (
        f"pic du surcroît à {h_max} h — hors de la plage « le soir (16-22 h) » de T2b"
    )


@besoin_ecret
def test_ecretement_printemps(con):
    """T5 : « 81 % de mars à juin », pic calendaire en mai, été quasi nul."""
    df = con.execute(
        f"SELECT mois_cal, sum(duree_h) AS h FROM '{ECRET.as_posix()}' GROUP BY 1"
    ).df()
    total = df["h"].sum()
    part_printemps = 100 * df[df["mois_cal"].isin([3, 4, 5, 6])]["h"].sum() / total
    assert round(part_printemps) == 81, (
        f"part mars-juin = {part_printemps:.1f} % — le « 81 % » publié par T5 ne tient plus"
    )
    pic = int(df.loc[df["h"].idxmax(), "mois_cal"])
    assert pic == 5, f"pic calendaire en {pic} — T5 raconte un pic en mai"
    part_ete = 100 * df[df["mois_cal"].isin([7, 8])]["h"].sum() / total
    assert part_ete < 1, (
        f"juillet-août = {part_ete:.1f} % du bridage — le « pas en été » de T5 ne tient plus"
    )


@besoin_ecret
def test_ecretement_record_mai_2020(con):
    """T5 note « mai 2020 : 141 h, 90,5 % d'ENR acceptée » : le record doit tenir."""
    mois, h, taux = con.execute(
        f"""SELECT mois, duree_h, taux_pct FROM '{ECRET.as_posix()}'
            ORDER BY duree_h DESC LIMIT 1"""
    ).fetchone()
    assert mois == "2020-05" and h == pytest.approx(141, abs=0.5), (
        f"pire mois = {mois} ({h:.0f} h) — la note de T5 cite mai 2020 : 141 h"
    )
    assert taux == pytest.approx(90.5, abs=0.1), (
        f"taux accepté du pire mois = {taux} % — la note de T5 cite 90,5 %"
    )


@besoin_sard
def test_sardaigne_thermique_domine(con):
    """T6 : Sardaigne ~65 % thermique (majoritaire), Corse ~55 % (génération seule)."""
    s = con.execute(
        f"""SELECT 100.0*sum(thermique_mw)/sum(production_totale_mw),
                   100.0*sum(eolien_mw)/sum(production_totale_mw)
            FROM '{SARD.as_posix()}'"""
    ).fetchone()
    assert s[0] == pytest.approx(65.1, abs=1.0), (
        f"thermique sarde = {s[0]:.1f} % — le titre « deux îles thermiques » de T6 à revoir"
    )
    # Contraste éolien du sous-titre : Sardaigne ~15 %, Corse ~1 % (≈ 15×).
    c_eol = con.execute(
        f"""SELECT 100.0*sum(eolien_mw)/sum(thermique_mw+hydraulique_mw+photovoltaique_mw
                   +eolien_mw+bioenergies_mw) FROM '{COURBE.as_posix()}'"""
    ).fetchone()[0]
    assert s[1] / c_eol >= 10, (
        f"éolien sarde {s[1]:.1f} % vs corse {c_eol:.1f} % — le « 15 fois plus » de T6 ne tient plus"
    )


@besoin_sard_xml
def test_sardaigne_charbon_igcc():
    """T6 note « 32 % charbon + 32 % IGCC » : reconstruit sur le XML brut 2023 (via le parser)."""
    from collections import defaultdict

    from demonstrateur.prepare import _lignes_entsoe_horaires

    energie = defaultdict(float)
    for ligne in _lignes_entsoe_horaires(SARD_XML):
        energie[ligne["code"]] += ligne["mw"]
    tot = sum(energie.values())
    charbon = 100 * energie["B05"] / tot   # houille
    igcc = 100 * energie["B03"] / tot      # gaz de synthèse (Sarlux)
    assert charbon + igcc >= 55, (
        f"charbon+IGCC = {charbon+igcc:.0f} % (2023) — la note de T6 sur le charbon ne tient plus"
    )


@besoin_mix
def test_fraicheur_temps_reel(con):
    """Le dernier relevé du mix doit avoir moins de 48 h (seuil de blocage « en ce moment »)."""
    age_h = con.execute(
        f"""SELECT extract(epoch FROM (now() - max("date")))/3600.0 FROM '{MIX.as_posix()}'"""
    ).fetchone()[0]
    assert age_h <= 48, (
        f"dernier relevé vieux de {age_h:.0f} h (> 48 h) — relancer fetch-data puis prepare "
        "avant toute publication « en ce moment »"
    )


@besoin_air
def test_air_corse_ne_garde_que_des_mesures_valides(con):
    """Le Parquet air ne contient que des lignes portant une VRAIE mesure.

    Verrou du garde-fou tranché le 30/07/2026 : dans le flux E2, une ligne de validité
    négative n'a pas de valeur du tout (elle n'est pas un zéro). Si un jour une valeur
    NULL ou une validité <= 0 franchissait prepare, tout calcul en aval — moyenne
    horaire, comptage de dépassements — serait faussé en silence.
    """
    sales, nulles = con.execute(
        f"""SELECT count(*) FILTER (WHERE validite <= 0),
                   count(*) FILTER (WHERE valeur IS NULL)
            FROM '{AIR.as_posix()}'"""
    ).fetchone()
    assert sales == 0, f"{sales} ligne(s) de validité <= 0 ont franchi prepare"
    assert nulles == 0, f"{nulles} valeur(s) NULL ont franchi prepare"


@besoin_air
def test_air_corse_couvre_le_gradient_ville_campagne(con):
    """L'ozone doit être mesuré en ville ET à la campagne, sinon le titre-affirmation
    « l'air de campagne n'est pas meilleur » (BRIEF_AIR) n'est pas adossé à la donnée.

    Venaco est le SEUL site rural de l'île : sa disparition du flux ne doit pas passer
    inaperçue. On vérifie aussi que les stations trafic restent hors du périmètre ozone
    — près des moteurs, le monoxyde d'azote le détruit, et les mêler à une comparaison
    ville/campagne mélangerait des populations non comparables.
    """
    src = AIR.as_posix()
    implantations = {
        r[0] for r in con.execute(
            f"SELECT DISTINCT implantation FROM '{src}' WHERE polluant = 'O3'"
        ).fetchall()
    }
    assert "Rurale régionale" in implantations, "plus aucune station rurale d'ozone (Venaco ?)"
    assert implantations & {"Urbaine", "Périurbaine"}, "plus aucune station urbaine d'ozone"
    trafic = con.execute(
        f"SELECT count(*) FROM '{src}' WHERE polluant = 'O3' AND influence = 'Trafic'"
    ).fetchone()[0]
    assert trafic == 0, "de l'ozone apparaît sur une station trafic — périmètre à revoir"


@besoin_air
def test_air_corse_horodatage_en_heure_locale(con):
    """L'heure locale se lit telle quelle : établi le 31/07/2026 (le flux publiait
    19:00 alors qu'il était 20 h 07 locale, soit 18 h 07 UTC — impossible en UTC).

    Verrou de bornes : une conversion de fuseau introduite par erreur en amont, ou un
    changement de convention du producteur, décalerait toutes les conclusions horaires.
    """
    mini, maxi = con.execute(
        f"SELECT min(heure_locale), max(heure_locale) FROM '{AIR.as_posix()}'"
    ).fetchone()
    assert 0 <= mini <= 23 and 0 <= maxi <= 23, f"heure_locale hors bornes ({mini}-{maxi})"
