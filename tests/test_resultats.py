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
from demonstrateur.prepare import APPARIEMENT_AIR_METEO, STATIONS_AIR

COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"
MIX = DATA_PROCESSED / "edf_mix_corse.parquet"
ECRET = DATA_PROCESSED / "edf_ecretement_corse.parquet"
SARD = DATA_PROCESSED / "entsoe_sardaigne.parquet"
SARD_XML = DATA_RAW / "entsoe_sardaigne_2023.xml"
AIR = DATA_PROCESSED / "air_corse.parquet"
METEO = DATA_PROCESSED / "meteo_corse.parquet"

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
besoin_meteo = pytest.mark.skipif(
    not METEO.exists(), reason="parquet météo absent — lancer fetch-data puis prepare"
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


@besoin_meteo
def test_meteo_corse_conversion_utc_vers_heure_legale(con):
    """Météo-France publie en UTC, le LCSQA en heure légale : la conversion doit tenir.

    C'est le verrou le plus lourd de conséquences des deux sources d'air. Une erreur de
    fuseau ne casse rien — elle décale simplement le pic de deux heures, et le
    titre-affirmation n° 4 du BRIEF_AIR (« le pire moment pour un effort en plein air se
    situe entre XX h et XX h ») devient un conseil faux, énoncé avec aplomb.

    Deux écarts, et deux seulement, doivent exister entre l'axe UTC et l'axe légal :
    +1 h l'hiver, +2 h l'été. Le contrôle par mois attrape en plus une conversion
    INVERSÉE, qui produirait les mêmes deux valeurs mais aux mauvaises saisons.
    """
    src = METEO.as_posix()
    ecarts = [
        r[0] for r in con.execute(
            f"SELECT DISTINCT date_diff('hour', date_heure_utc, date_heure_locale) "
            f"FROM '{src}' ORDER BY 1"
        ).fetchall()
    ]
    assert ecarts == [1, 2], (
        f"écarts UTC -> heure légale observés : {ecarts} h (attendu [1, 2]) — la "
        "conversion de fuseau de meteo_corse_to_parquet ne tient plus"
    )
    janvier, juillet = con.execute(
        f"""SELECT max(ecart) FILTER (WHERE mois = 1), min(ecart) FILTER (WHERE mois = 7)
            FROM (SELECT extract('month' FROM date_locale) AS mois,
                         date_diff('hour', date_heure_utc, date_heure_locale) AS ecart
                  FROM '{src}')"""
    ).fetchone()
    assert janvier == 1 and juillet == 2, (
        f"écart de janvier = {janvier} h, de juillet = {juillet} h — conversion inversée "
        "(l'heure d'été s'applique l'hiver)"
    )


@besoin_meteo
def test_meteo_corse_la_cle_est_l_axe_utc(con):
    """L'axe UTC est la clé ; l'axe local ne l'est pas — et c'est un piège de jointure.

    Le dimanche du retour à l'heure d'hiver, 00 h et 01 h UTC donnent toutes deux 02 h
    en heure légale : le couple (poste, heure locale) est en double une fois par an et
    par poste. Ce n'est pas une anomalie de préparation — cette heure a réellement lieu
    deux fois — mais une jointure bâtie sur l'axe local double-compterait cette heure-là.

    Ce test fige les deux moitiés de la règle : l'unicité DOIT tenir sur l'axe UTC, et
    la duplication locale est attendue, pas subie. Si un jour elle disparaissait (le
    producteur changeant de convention), il faudrait le savoir avant de croiser.
    """
    src = METEO.as_posix()
    doublons_utc, doublons_loc = con.execute(
        f"""SELECT
              (SELECT count(*) FROM (SELECT num_poste, date_heure_utc FROM '{src}'
                                     GROUP BY 1, 2 HAVING count(*) > 1)),
              (SELECT count(*) FROM (SELECT num_poste, date_heure_locale FROM '{src}'
                                     GROUP BY 1, 2 HAVING count(*) > 1))"""
    ).fetchone()
    assert doublons_utc == 0, (
        f"{doublons_utc} couple(s) (poste, heure UTC) en double — la clé du Parquet "
        "n'est plus unique"
    )
    if doublons_loc:
        heures = con.execute(
            f"""SELECT DISTINCT CAST(date_locale AS VARCHAR), heure_locale FROM '{src}'
                WHERE (num_poste, date_heure_locale) IN (
                  SELECT num_poste, date_heure_locale FROM '{src}'
                  GROUP BY 1, 2 HAVING count(*) > 1)"""
        ).fetchall()
        assert all(h == 2 for _, h in heures), (
            f"doublons d'heure locale ailleurs qu'à 02 h : {heures} — ce n'est plus le "
            "seul passage à l'heure d'hiver, la conversion est à revoir"
        )


@besoin_meteo
def test_meteo_corse_ne_garde_que_des_mesures_fiables(con):
    """Pendant du verrou `validité` de l'air : `QT` doit avoir filtré, et rien d'autre.

    Le code 2 (« douteuse, en cours de vérification ») ne doit jamais franchir prepare ;
    aucun code inconnu non plus — sur une nomenclature qui bouge, un tri silencieux
    laisserait passer de la donnée mise en doute par le producteur lui-même.
    """
    from demonstrateur.prepare import QT_RETENUS

    src = METEO.as_posix()
    codes = {r[0] for r in con.execute(f"SELECT DISTINCT qt FROM '{src}'").fetchall()}
    assert codes <= set(QT_RETENUS), (
        f"code(s) qualité {sorted(codes - set(QT_RETENUS))} ont franchi prepare"
    )
    nulles = con.execute(
        f"SELECT count(*) FROM '{src}' WHERE temperature_c IS NULL"
    ).fetchone()[0]
    assert nulles == 0, f"{nulles} température(s) NULL ont franchi prepare"


@besoin_meteo
def test_meteo_corse_journees_completes(con):
    """Aucune journée tronquée : sinon un maximum journalier serait calculé sur un fragment.

    Les deux extrémités du brut le sont par construction — le décalage UTC -> heure légale
    ampute la première, la coupure de publication la dernière (6 h le 31/07/2026). Elles
    sont retirées dans prepare, qui REFUSE en outre de publier une série trouée. Ce test
    est le second filet : il porte sur le Parquet tel qu'il est sur le disque, et attrape
    donc aussi une sortie laissée par une version antérieure du code. Le seuil est 23 h et
    non 24 : le dimanche du passage à l'heure d'été n'en compte légitimement que 23.
    """
    creuses = con.execute(
        f"""SELECT CAST(date_locale AS VARCHAR), count(DISTINCT heure_locale) AS h
            FROM '{METEO.as_posix()}' GROUP BY 1 HAVING h < 23 ORDER BY 1"""
    ).fetchall()
    assert not creuses, (
        f"{len(creuses)} journée(s) incomplète(s) ont franchi prepare : {creuses[:5]} — "
        "tout maximum journalier calculé dessus serait faux"
    )


@besoin_meteo
def test_meteo_corse_cycle_diurne_physique(con):
    """Contrôle de sens, indépendant du code : le jour doit réchauffer, et l'après-midi
    être le moment chaud.

    Le test précédent vérifie la MÉCANIQUE de la conversion (des écarts de +1/+2 h) ; ce
    test-ci vérifie qu'elle produit un monde plausible. Une erreur de lecture de la date
    elle-même — un strptime qui décalerait tout — passerait le premier et échouerait ici.
    """
    df = con.execute(
        f"""SELECT heure_locale, avg(temperature_c) AS t FROM '{METEO.as_posix()}'
            WHERE extract('month' FROM date_locale) = 7 GROUP BY 1 ORDER BY 1"""
    ).df()
    assert len(df) == 24, f"{len(df)} heures locales en juillet (attendu 24)"
    h_chaud = int(df.loc[df["t"].idxmax(), "heure_locale"])
    h_froid = int(df.loc[df["t"].idxmin(), "heure_locale"])
    assert 13 <= h_chaud <= 18, (
        f"maximum thermique moyen de juillet à {h_chaud} h locale — hors de l'après-midi : "
        "l'axe horaire est décalé"
    )
    assert 3 <= h_froid <= 8, (
        f"minimum thermique moyen de juillet à {h_froid} h locale — le creux doit précéder "
        "le lever du jour, pas le suivre"
    )


# --- Appariement station d'air <-> poste météo ---------------------------------------
# Cette table est une DÉCISION, pas un calcul : rien dans les données ne la vérifie
# d'elle-même, et une erreur y serait invisible — le pipeline tournerait, les figures
# sortiraient, et la température affichée en face de l'ozone serait celle d'un autre
# endroit. D'où ces verrous.

@besoin_air
def test_appariement_couvre_toutes_les_stations_ozone(con):
    """Aucune station d'ozone ne doit rester sans poste, ni l'inverse.

    Le jour où Qualitair Corse ouvre une septième station, elle apparaîtra dans le Parquet
    sans température associée : ce test le dit, au lieu de laisser la station disparaître
    silencieusement du croisement.
    """
    stations = {
        r[0]
        for r in con.execute(
            f"SELECT DISTINCT code_site FROM '{AIR.as_posix()}' WHERE polluant = 'O3'"
        ).fetchall()
    }
    sans_poste = stations - set(APPARIEMENT_AIR_METEO)
    assert not sans_poste, f"station(s) d'ozone sans poste météo : {sorted(sans_poste)}"
    fantomes = set(APPARIEMENT_AIR_METEO) - stations
    assert not fantomes, f"apparié(s) mais absent(s) des mesures d'ozone : {sorted(fantomes)}"


@besoin_meteo
def test_les_postes_apparies_existent_et_mesurent(con):
    """Chaque poste cité existe dans la météo et y porte de vraies températures."""
    postes = {
        r[0]: r[1]
        for r in con.execute(
            f"SELECT num_poste, count(temperature_c) FROM '{METEO.as_posix()}' GROUP BY 1"
        ).fetchall()
    }
    for code_site, num_poste in APPARIEMENT_AIR_METEO.items():
        assert num_poste in postes, (
            f"{code_site} apparié au poste {num_poste}, absent du fichier Météo-France"
        )
        assert postes[num_poste] > 0, f"poste {num_poste} sans aucune température"


@besoin_meteo
def test_venaco_va_a_vivario_et_pas_a_corte(con):
    """Verrou de la décision du 01/08/2026, contre-intuitive donc fragile.

    Corte est plus proche de Venaco en distance ET en altitude ; c'est pourtant Vivario
    qui est retenu, parce que la cuvette de Corte creuse l'amplitude diurne — un écart qui
    varie selon l'heure et la saison, là où un simple biais d'altitude serait inoffensif.
    Quelqu'un qui « corrigerait » vers le plus proche casserait la relation que le titre
    n° 1 cherche à mesurer. Le test vérifie aussi que Corte EXISTE : l'écarter doit rester
    un choix, jamais une absence subie.
    """
    corte = "20096008"
    assert APPARIEMENT_AIR_METEO["FR41024"] == "20354008", (
        "Venaco doit être apparié à VIVARIO_SAPC (cf. la justification dans prepare.py)"
    )
    dispo = {
        r[0] for r in con.execute(f"SELECT DISTINCT num_poste FROM '{METEO.as_posix()}'").fetchall()
    }
    assert corte in dispo, "CORTE doit être disponible — son écartement est délibéré"
    assert APPARIEMENT_AIR_METEO["FR41024"] != corte


@besoin_meteo
def test_le_poste_nomme_bastia_n_est_pas_a_bastia(con):
    """Piège de nommage : « BASTIA » (20148 = Lucciana) est l'aéroport de Poretta, dans la
    plaine ; Bastia ville est « BASTIA_SAPC » (20033). `num_poste` porte le code commune,
    ce qui rend le contrôle possible sans coordonnées.

    Les deux stations urbaines vont donc à la ville, et la station de la plaine de la
    Marana au poste de la plaine. Les intervertir sur la foi du nom mettrait le
    thermomètre de la plaine au pied des analyseurs urbains.
    """
    for code_site in ("FR41002", "FR41017"):  # Giraud, Montesoro — dans Bastia
        assert APPARIEMENT_AIR_METEO[code_site].startswith("20033"), (
            f"{code_site} est une station de Bastia ville : son poste doit être sur la "
            "commune 2B033, pas celui qui s'appelle « BASTIA » (Lucciana)"
        )
    assert APPARIEMENT_AIR_METEO["FR41004"].startswith("20148"), (
        "BASTIA LA MARANA est dans la plaine : poste de Lucciana/Poretta attendu"
    )
    assert APPARIEMENT_AIR_METEO["FR41002"] != APPARIEMENT_AIR_METEO["FR41004"], (
        "ville et plaine ne peuvent pas partager le même thermomètre"
    )


@besoin_courbe
def test_2022_creux_hydraulique_et_pic_thermique(con):
    """BRIEF_AIR cite 2022 comme exemple de confusion : deux causes candidates ont bougé
    ensemble cette année-là — la chaleur ET les précurseurs, le thermique ayant compensé
    des barrages au plus bas.

    Ces chiffres sont destinés à la prose du livrable ; ils se verrouillent donc comme
    tout chiffre publié. Le test vérifie les valeurs ET le fait que 2022 soit bien l'extrême
    de la série dans les deux sens : c'est cette simultanéité, pas les décimales, qui fait
    l'argument. 2025 est exclu — le Parquet n'en contient qu'une heure, débordement du
    passage UTC vers l'heure locale.
    """
    df = con.execute(
        f"""SELECT extract('year' FROM date_heure) AS an,
                   100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
                   100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique
            FROM '{COURBE.as_posix()}'
            WHERE extract('year' FROM date_heure) BETWEEN 2019 AND 2024
            GROUP BY 1 ORDER BY 1"""
    ).df()
    assert len(df) == 6, f"{len(df)} années pleines (attendu 2019-2024)"

    an_min_hydro = int(df.loc[df["hydro"].idxmin(), "an"])
    an_max_therm = int(df.loc[df["thermique"].idxmax(), "an"])
    assert an_min_hydro == 2022 and an_max_therm == 2022, (
        f"creux hydraulique en {an_min_hydro}, pic thermique en {an_max_therm} — "
        "l'exemple de confusion du BRIEF_AIR repose sur leur coïncidence en 2022"
    )
    ligne_2022 = df.loc[df["an"] == 2022].iloc[0]
    assert float(ligne_2022["hydro"]) == pytest.approx(12.3, abs=0.2), (
        "BRIEF_AIR cite « 12,3 % d'hydraulique » pour 2022"
    )
    assert float(ligne_2022["thermique"]) == pytest.approx(47.5, abs=0.2), (
        "BRIEF_AIR cite « 47,5 % de thermique » pour 2022"
    )
    ligne_2023 = df.loc[df["an"] == 2023].iloc[0]
    assert float(ligne_2023["thermique"]) == pytest.approx(34.8, abs=0.2), (
        "BRIEF_AIR oppose 2022 à « 34,8 % l'année suivante »"
    )


@besoin_meteo
def test_les_deux_stations_d_ajaccio_ne_partagent_pas_leur_poste(con):
    """Les deux stations d'Ajaccio vont à des postes DIFFÉRENTS, et c'est délibéré.

    Elles sont distantes de 5,6 km et ne partagent pas leur environnement. Le Canetto
    (39 m, en ville) va aux Milelli ; Confina 2 (70 m, dominant la plaine de la Gravona)
    va à Campo dell'Oro.

    Un même critère produit ces deux choix opposés, et c'est ce que le test protège : dans
    les deux cas l'écart d'altitude reste sous ~0,3 °C de gradient, donc l'altitude ne
    départage pas — ce sont la distance et l'exposition qui décident, et elles pointent
    dans des directions contraires selon la station. Uniformiser les deux « par cohérence »
    serait précisément l'erreur : c'est la cohérence du CRITÈRE qui compte, pas celle du
    résultat.
    """
    milelli, campo = "20004014", "20004002"
    assert APPARIEMENT_AIR_METEO["FR41001"] == milelli, (
        "AJACCIO CANETTO doit aller aux Milelli (1,97 km, contre 4,77 pour Campo dell'Oro)"
    )
    assert APPARIEMENT_AIR_METEO["FR41063"] == campo, (
        "AJACCIO CONFINA 2 doit aller à Campo dell'Oro (3,31 km, contre 6,31 pour Milelli)"
    )
    assert APPARIEMENT_AIR_METEO["FR41001"] != APPARIEMENT_AIR_METEO["FR41063"], (
        "les deux stations d'Ajaccio sont à 5,6 km l'une de l'autre : rien n'impose "
        "qu'elles partagent un thermomètre"
    )
    dispo = {
        r[0] for r in con.execute(f"SELECT DISTINCT num_poste FROM '{METEO.as_posix()}'").fetchall()
    }
    assert {milelli, campo} <= dispo, "les deux postes doivent exister dans la météo"


@besoin_meteo
def test_appariement_coherent_avec_les_coordonnees_officielles(con):
    """L'appariement se vérifie contre les COORDONNÉES, plus seulement contre lui-même.

    Les positions viennent du référentiel du producteur (Dataset D du LCSQA) et non plus
    de relevés à la main. Un poste apparié doit donc figurer parmi les DEUX plus proches
    de sa station : le critère retenu autorise à préférer le second — c'est le cas de
    Venaco, où Corte est plus proche mais écarté pour son amplitude — mais jamais à choisir
    un poste lointain, qui signalerait une coquille de code plutôt qu'un arbitrage.
    """
    from math import asin, cos, radians, sin, sqrt

    def km(a, b):
        (la1, lo1), (la2, lo2) = a, b
        h = (sin(radians(la2 - la1) / 2) ** 2
             + cos(radians(la1)) * cos(radians(la2)) * sin(radians(lo2 - lo1) / 2) ** 2)
        return 2 * 6371 * asin(sqrt(h))

    postes = con.execute(
        f"SELECT DISTINCT num_poste, lat, lon FROM '{METEO.as_posix()}'"
    ).fetchall()
    for code_site, num_poste in APPARIEMENT_AIR_METEO.items():
        nom, lat, lon, _alt, _debut = STATIONS_AIR[code_site]
        classement = sorted(postes, key=lambda p: km((lat, lon), (p[1], p[2])))
        deux_plus_proches = [p[0] for p in classement[:2]]
        assert num_poste in deux_plus_proches, (
            f"{nom} appariée au poste {num_poste}, absent des deux plus proches "
            f"{deux_plus_proches} — coquille probable"
        )


def test_confina_2_est_trop_jeune_pour_l_historique():
    """Confina 2 n'existe que depuis 2024 : toute figure comparant les stations sur
    plusieurs années doit le dire, sous peine de faire passer une série courte pour
    une série trouée. Le référentiel du producteur fait foi ; ce test fige le fait."""
    debuts = {code: STATIONS_AIR[code][4] for code in STATIONS_AIR}
    assert debuts["FR41063"] == "2024-01-31", "date de mise en service de Confina 2"
    autres = [d for c, d in debuts.items() if c != "FR41063"]
    assert all(d < "2012-01-01" for d in autres), (
        "les cinq autres stations mesurent depuis 2006-2011 — l'écart de profondeur "
        "avec Confina 2 est le point à écrire sur les figures"
    )


@besoin_air
def test_le_flux_lcsqa_est_en_fuseau_fixe_pas_en_heure_legale(con):
    """Le test qui manquait, et dont l'absence a laissé passer un axe UTC faux en été.

    Le brief a longtemps affirmé que le flux LCSQA publiait en heure légale française. Une
    seule observation le fondait — le fichier publiait 19:00 alors qu'il était 20 h 07 locale
    — qui écarte bien l'UTC mais s'accommode tout aussi bien d'UTC+1 fixe. Les archives des
    deux dimanches de changement d'heure 2025 ont tranché : 24 heures publiées, de 00:00 à
    23:00, sans doublon, là où une heure légale en compterait 23 et 25.

    D'où l'axe UTC par soustraction d'une heure. Ce test verrouille les deux faces :
    l'écart doit être CONSTANT — c'est la signature d'un fuseau fixe, et une conversion de
    fuseau le ferait varier d'une saison à l'autre — et la grille doit rester régulière.
    """
    ecarts, mini, maxi = con.execute(
        f"""SELECT count(DISTINCT date_diff('minute', date_heure_utc, debut)),
                   min(date_diff('minute', date_heure_utc, debut)),
                   max(date_diff('minute', date_heure_utc, debut))
            FROM '{AIR.as_posix()}'"""
    ).fetchone()
    assert ecarts == 1 and mini == 60, (
        f"écart brut→UTC : {ecarts} valeur(s) distincte(s), de {mini} à {maxi} min — "
        "attendu 60 min partout. Un écart variable signalerait une heure légale, et "
        "l'axe UTC ne pourrait plus se déduire par soustraction"
    )
    attendues, distinctes = con.execute(
        f"""SELECT date_diff('hour', min(debut), max(debut)) + 1, count(DISTINCT debut)
            FROM '{AIR.as_posix()}'"""
    ).fetchone()
    assert distinctes == attendues, (
        f"grille horaire irrégulière : {distinctes} horodatages pour {attendues} heures — "
        "trou ou doublon, donc bascule possible du producteur vers l'heure légale"
    )


@besoin_air
def test_l_heure_locale_derive_de_l_utc_et_non_du_brut(con):
    """L'heure des titres est l'heure VÉCUE, pas l'étiquette du producteur.

    En été, l'heure locale vaut UTC+2 quand le brut est en UTC+1 : la colonne heure_locale
    doit donc différer de l'heure du brut. Les lire comme identiques — ce que faisait le
    code avant correction — décalerait d'une heure « le pire créneau pour un effort en plein
    air », qui est la conclusion actionnable du brief.
    """
    ecart_ete = con.execute(
        f"""SELECT DISTINCT (heure_locale - extract('hour' FROM date_heure_utc) + 24) % 24
            FROM '{AIR.as_posix()}'
            WHERE extract('month' FROM date_locale) IN (5, 6, 7, 8, 9)"""
    ).fetchall()
    if ecart_ete:  # le flux ne porte qu'une journée : muet hors saison d'été
        assert [r[0] for r in ecart_ete] == [2], (
            f"décalage heure locale − UTC en été : {[r[0] for r in ecart_ete]} h, attendu 2"
        )
