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
from demonstrateur.figures import FRAICHEUR_BLOQUER_H

COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"
MIX = DATA_PROCESSED / "edf_mix_corse.parquet"
ECRET = DATA_PROCESSED / "edf_ecretement_corse.parquet"
SARD = DATA_PROCESSED / "entsoe_sardaigne.parquet"
SARD_XML = DATA_RAW / "entsoe_sardaigne_2023.xml"

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
    charbon = 100 * energie["B05"] / tot  # houille
    igcc = 100 * energie["B03"] / tot  # gaz de synthèse (Sarlux)
    assert charbon + igcc >= 55, (
        f"charbon+IGCC = {charbon + igcc:.0f} % (2023) — la note de T6 sur le charbon ne tient plus"
    )


@besoin_mix
def test_fraicheur_temps_reel(con):
    """Le dernier relevé du mix doit tenir sous le seuil de blocage « en ce moment »
    (FRAICHEUR_BLOQUER_H) — sinon la source live est trop vieille pour être publiée."""
    age_h = con.execute(
        f"""SELECT extract(epoch FROM (now() - max("date")))/3600.0 FROM '{MIX.as_posix()}'"""
    ).fetchone()[0]
    assert age_h <= FRAICHEUR_BLOQUER_H, (
        f"dernier relevé vieux de {age_h:.0f} h (> {FRAICHEUR_BLOQUER_H} h) — relancer "
        "fetch-data puis prepare avant toute publication « en ce moment »"
    )


# --- Verrous de l'étude (docs/etude.md, section 3) : chaque chiffre cité en prose ---


@besoin_courbe
def test_etude_14h_heure_la_plus_corse(con):
    """Étude/T4 : part produite sur l'île max à 14 h (84 %), top 3 = 14/15/13 h,
    imports au-dessus du tiers à chaque heure de nuit (1-8 h)."""
    df = con.execute(
        f"""SELECT heure_locale,
              100*sum(importations_mw)/sum(production_totale_mw) AS imports
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    df["locale"] = 100 - df["imports"]
    top3 = df.nlargest(3, "locale")["heure_locale"].astype(int).tolist()
    assert top3[0] == 14 and set(top3) == {13, 14, 15}, (
        f"top 3 des heures les plus « corses » = {top3} — l'étude écrit 14 h, 15 h, 13 h"
    )
    v14 = float(df.loc[df["heure_locale"] == 14, "locale"].iloc[0])
    assert v14 == pytest.approx(84.5, abs=0.5), (
        f"part locale à 14 h = {v14:.1f} % — l'étude écrit « 84 % produits sur l'île »"
    )
    nuit = df[df["heure_locale"].between(1, 8)]["imports"]
    assert (nuit > 100 / 3).all(), (
        "imports sous le tiers sur une heure de nuit — l'étude écrit « dépasse le tiers la nuit »"
    )


@besoin_courbe
def test_etude_thermique_socle_et_aube(con):
    """Étude/T4 (encadré) : thermique au plus bas vers 5 h en volume, socle diurne ~104 MW ;
    en part, 36 % à 14 h contre 44 % à l'aube."""
    df = con.execute(
        f"""SELECT heure_locale, avg(thermique_mw) AS mw,
              100*sum(thermique_mw)/sum(production_totale_mw) AS pct
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    h_min = int(df.loc[df["mw"].idxmin(), "heure_locale"])
    assert h_min == 5, f"minimum de volume thermique à {h_min} h — l'étude écrit « vers 5 heures »"
    socle = df[df["heure_locale"].between(9, 18)]["mw"].mean()
    assert socle == pytest.approx(104, abs=4), (
        f"socle thermique diurne = {socle:.0f} MW — l'étude écrit « environ 104 MW »"
    )
    p14 = float(df.loc[df["heure_locale"] == 14, "pct"].iloc[0])
    p5 = float(df.loc[df["heure_locale"] == 5, "pct"].iloc[0])
    assert round(p14) == 36 and round(p5) == 44, (
        f"parts thermiques 14 h / aube = {p14:.1f} / {p5:.1f} — l'étude écrit 36 % et 44 %"
    )


@besoin_courbe
def test_etude_thermique_premier(con):
    """Étude/T4 : ce que « la plus verte » veut dire, mesuré. Le thermique ne recule que
    de près d'un cinquième entre son maximum et 14 h, aucune heure ne le voit dépassé par
    le renouvelable décentralisé, et le total avec les barrages ne passe devant qu'entre
    11 h et 16 h. Verrouille aussi la garde de lecture du sous-titre de la figure."""
    df = con.execute(
        f"""SELECT heure_locale,
              100*sum(enr_distrib_mw)/sum(production_totale_mw) AS decentralise,
              100*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
              100*sum(thermique_mw)/sum(production_totale_mw)   AS thermique
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    depasse = sorted(df.loc[df["decentralise"] > df["thermique"], "heure_locale"].astype(int))
    assert not depasse, (
        f"le renouvelable décentralisé passe devant le thermique aux heures {depasse} — "
        "l'étude et le sous-titre de T4 écrivent qu'il ne le fait à aucune"
    )
    large = sorted(
        df.loc[df["decentralise"] + df["hydro"] > df["thermique"], "heure_locale"].astype(int)
    )
    assert large == [11, 12, 13, 14, 15, 16], (
        f"total renouvelable devant le thermique aux heures {large} — "
        "l'étude écrit « entre 11 heures et 16 heures »"
    )
    haut = float(df["thermique"].max())
    p14 = float(df.loc[df["heure_locale"] == 14, "thermique"].iloc[0])
    recul = 100 * (haut - p14) / haut
    assert recul == pytest.approx(18, abs=2), (
        f"recul relatif du thermique jusqu'à 14 h = {recul:.0f} % — "
        "l'étude écrit « près d'un cinquième de moins »"
    )


@besoin_courbe
def test_etude_soleil_remplace_les_cables(con):
    """Étude/T4 (encadré) : de 9 h à 14 h, les imports reculent de ~80 à ~44 MW
    pendant que le thermique ne bouge pas."""
    df = (
        con.execute(
            f"""SELECT heure_locale, avg(importations_mw) AS imp, avg(thermique_mw) AS th
            FROM '{COURBE.as_posix()}' WHERE heure_locale IN (9, 14) GROUP BY 1"""
        )
        .df()
        .set_index("heure_locale")
    )
    assert float(df.loc[9, "imp"]) == pytest.approx(80, abs=2), "imports de 9 h ≠ ~80 MW"
    assert float(df.loc[14, "imp"]) == pytest.approx(44, abs=2), "imports de 14 h ≠ ~44 MW"
    assert abs(float(df.loc[14, "th"]) - float(df.loc[9, "th"])) < 8, (
        "le thermique bouge entre 9 h et 14 h — l'étude écrit qu'il « ne bouge pas »"
    )


@besoin_courbe
def test_etude_profil_ete_parts(con):
    """Étude/T3 : été, midi = 35/43/16 (solaire/thermique/câbles), soir = 6/58/25,
    et plus de 80 % du kWh du soir en moteurs + câbles."""
    df = (
        con.execute(
            f"""SELECT CASE WHEN heure_locale BETWEEN 13 AND 15 THEN 'midi' ELSE 'soir' END AS c,
              100*sum(photovoltaique_mw)/sum(production_totale_mw) AS sol,
              100*sum(thermique_mw)/sum(production_totale_mw)      AS th,
              100*sum(importations_mw)/sum(production_totale_mw)   AS imp
            FROM '{COURBE.as_posix()}'
            WHERE mois_local IN (6, 7, 8)
              AND (heure_locale BETWEEN 13 AND 15 OR heure_locale BETWEEN 20 AND 23)
            GROUP BY 1"""
        )
        .df()
        .set_index("c")
    )
    m, s = df.loc["midi"], df.loc["soir"]
    assert (round(m["sol"]), round(m["th"]), round(m["imp"])) == (35, 43, 16), (
        f"midi d'été = {m['sol']:.1f}/{m['th']:.1f}/{m['imp']:.1f} — l'étude écrit 35/43/16"
    )
    assert (round(s["sol"]), round(s["th"]), round(s["imp"])) == (6, 58, 25), (
        f"soir d'été = {s['sol']:.1f}/{s['th']:.1f}/{s['imp']:.1f} — l'étude écrit 6/58/25"
    )
    assert s["th"] + s["imp"] > 80, (
        "moteurs + câbles ≤ 80 % le soir d'été — le « huit dixièmes » de l'étude à revoir"
    )


@besoin_courbe
def test_etude_niveaux_mensuels(con):
    """Étude/T2 : 231 MW en juin, 281 en juillet, 307 de moyenne d'hiver (chiffres en dur)."""
    juin, juillet, hiver = con.execute(
        f"""SELECT round(avg(production_totale_mw) FILTER (WHERE mois_local = 6)),
                   round(avg(production_totale_mw) FILTER (WHERE mois_local = 7)),
                   round(avg(production_totale_mw) FILTER (WHERE mois_local IN (12, 1, 2)))
            FROM '{COURBE.as_posix()}'"""
    ).fetchone()
    assert (juin, juillet, hiver) == (231, 281, 307), (
        f"niveaux juin/juillet/hiver = {juin}/{juillet}/{hiver} — l'étude écrit 231/281/307"
    )


@besoin_ecret
def test_etude_ecretement_progression(con):
    """Étude/T5 : 54 heures de bridage sur 2016, 356 sur 2023."""
    d16, d23 = con.execute(
        f"""SELECT sum(duree_h) FILTER (WHERE annee = 2016),
                   sum(duree_h) FILTER (WHERE annee = 2023) FROM '{ECRET.as_posix()}'"""
    ).fetchone()
    assert d16 == pytest.approx(54, abs=0.5) and d23 == pytest.approx(356, abs=0.5), (
        f"bridage annuel = {d16:.0f} h (2016) → {d23:.0f} h (2023) — l'étude écrit 54 → 356"
    )


@besoin_courbe
def test_etude_dependance_imports(con):
    """Cadrage / T6 : « plus du quart » de l'électricité corse est importée — 27,8 % de la
    production totale en moyenne 2019-2024 ; et « en moyenne » car l'île exporte aussi
    (607 heures, à peine plus de 1 % du temps). Publié en sections 1 et 6 et au pied de T6."""
    part, exp = con.execute(
        f"""SELECT 100.0*sum(importations_mw)/sum(production_totale_mw),
                   count(*) FILTER (WHERE importations_mw < 0)
            FROM '{COURBE.as_posix()}'
            WHERE extract(year from date_heure) BETWEEN 2019 AND 2024"""
    ).fetchone()
    assert part == pytest.approx(27.8, abs=0.4), (
        f"part importée = {part:.1f} % — l'étude écrit « 27,8 % »"
    )
    assert part > 25, "part importée sous le quart — l'étude écrit « plus du quart »"
    assert exp == pytest.approx(607, abs=5), (
        f"{exp} heures d'export — l'étude écrit « 607 heures, à peine plus de 1 % du temps »"
    )


@besoin_courbe
def test_t7_hydro_secheresse(con):
    """T7 : d'une année à l'autre, part hydraulique et part thermique varient à l'opposé
    (corrélation forte négative) ; l'année la plus pauvre en hydraulique (2022) est aussi
    celle du thermique le plus haut, et l'amplitude interannuelle du thermique passe la
    dizaine de points. Chiffres publiés au pied de la figure."""
    df = con.execute(
        f"""SELECT extract(year from date_heure)::INTEGER AS annee,
              100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
              100.0*sum(thermique_mw)/sum(production_totale_mw)   AS therm
            FROM '{COURBE.as_posix()}'
            WHERE extract(year from date_heure) BETWEEN 2019 AND 2024
            GROUP BY 1 ORDER BY 1"""
    ).df()
    assert len(df) == 6, f"{len(df)} années pleines retenues (attendu 6, 2019-2024)"
    r = float(df["hydro"].corr(df["therm"]))
    assert r <= -0.9, f"corrélation hydro/thermique = {r:+.2f} — la figure écrit « −0,95 »"
    an_hydro_min = int(df.loc[df["hydro"].idxmin(), "annee"])
    an_therm_max = int(df.loc[df["therm"].idxmax(), "annee"])
    assert an_hydro_min == an_therm_max == 2022, (
        f"hydraulique min en {an_hydro_min}, thermique max en {an_therm_max} — la figure pointe 2022"
    )
    ampl = float(df["therm"].max() - df["therm"].min())
    assert ampl >= 10, (
        f"amplitude interannuelle du thermique = {ampl:.1f} pts (attendu ≥ 10 — l'année sèche pèse)"
    )


@besoin_courbe
@besoin_sard
def test_etude_mix_generation_locale(con):
    """Étude/T6 : Corse (génération seule, convention de la figure) = 55/28/15/1 ;
    Sardaigne : hydro 4 %, solaire 9 %."""
    corse = con.execute(
        f"""WITH b AS (
              SELECT sum(thermique_mw) th,
                     sum(hydraulique_mw + coalesce(micro_hydraulique_mw, 0)) hy,
                     sum(photovoltaique_mw) so, sum(eolien_mw) eo, sum(bioenergies_mw) bi
              FROM '{COURBE.as_posix()}')
            SELECT 100*th/(th+hy+so+eo+bi), 100*hy/(th+hy+so+eo+bi),
                   100*so/(th+hy+so+eo+bi), 100*eo/(th+hy+so+eo+bi) FROM b"""
    ).fetchone()
    assert tuple(round(v) for v in corse) == (55, 28, 15, 1), (
        f"mix corse génération locale = {tuple(round(v, 1) for v in corse)} "
        "— l'étude écrit 55/28/15/1"
    )
    hy_s, so_s = con.execute(
        f"""SELECT 100*sum(hydraulique_mw)/sum(production_totale_mw),
                   100*sum(solaire_mw)/sum(production_totale_mw) FROM '{SARD.as_posix()}'"""
    ).fetchone()
    assert round(hy_s) == 4 and round(so_s) == 9, (
        f"Sardaigne hydro/solaire = {hy_s:.1f} % / {so_s:.1f} % — l'étude écrit 4 % et 9 %"
    )
