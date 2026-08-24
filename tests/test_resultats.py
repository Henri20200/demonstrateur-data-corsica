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
SERIE = DATA_PROCESSED / "air_serie.parquet"
MDA8 = DATA_PROCESSED / "air_o3_mda8.parquet"
CROISE = DATA_PROCESSED / "air_temperature_jour.parquet"
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
besoin_serie = pytest.mark.skipif(
    not SERIE.exists(), reason="série ozone AEE absente — lancer fetch-data puis prepare"
)
besoin_croise = pytest.mark.skipif(
    not CROISE.exists(), reason="croisement air x température absent — fetch-data puis prepare"
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
def test_creneau_le_plus_vert_autour_de_midi(con):
    """T4 : un CRÉNEAU 12-13 h, et l'écart d'une heure entre les deux définitions.

    Ce verrou a tenu « 14 h pour les deux définitions » jusqu'au 23/08/2026. L'heure était
    fausse et la coïncidence avec elle : corrigée, la définition décentralisée culmine à
    13 h, celle qui inclut les grands barrages à 12 h. On ne remplace donc pas un `== 14`
    par un `== 13` — ce serait publier une précision que le signal ne porte pas, 0,13 point
    séparant les deux premières heures. Le verrou tient ce que la figure affiche : les
    bornes du créneau, l'écart d'une heure, et le fait qu'aucune heure du dehors ne fasse
    mieux.
    """
    df = con.execute(
        f"""SELECT heure_locale,
              100*sum(enr_distrib_mw)/sum(production_totale_mw)                AS decentralise,
              100*sum(enr_distrib_mw+hydraulique_mw)/sum(production_totale_mw) AS avec_hydro
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    h_dec = int(df.loc[df["decentralise"].idxmax(), "heure_locale"])
    h_tot = int(df.loc[df["avec_hydro"].idxmax(), "heure_locale"])
    assert {h_dec, h_tot} == {12, 13}, (
        f"créneau le plus vert : {h_dec} h (décentralisé) / {h_tot} h (avec grande hydro) "
        "— T4 surligne 12-13 h et l'étude écrit « autour de midi »"
    )
    assert abs(h_dec - h_tot) == 1, (
        "les deux définitions désignent la même heure : l'écart d'une heure est écrit dans "
        "le sous-titre de T4 et dans l'étude, il ne peut pas disparaître sans les corriger"
    )

    creneau = df[df["heure_locale"].isin((12, 13))]
    dehors = df[~df["heure_locale"].isin((12, 13))]
    for col, libelle in (("decentralise", "décentralisé"), ("avec_hydro", "avec grande hydro")):
        assert creneau[col].min() > dehors[col].max(), (
            f"une heure hors du créneau fait mieux que 12-13 h ({libelle}) — "
            "le cadre de T4 n'entoure plus le sommet"
        )

    part = con.execute(
        f"""SELECT 100*sum(enr_distrib_mw)/sum(production_totale_mw)                AS dec,
                   100*sum(enr_distrib_mw+hydraulique_mw)/sum(production_totale_mw) AS tot
            FROM '{COURBE.as_posix()}' WHERE heure_locale BETWEEN 12 AND 13"""
    ).df().iloc[0]
    assert float(part["dec"]) == pytest.approx(34.6, abs=0.5), (
        "T4 affiche « 35 % renouvelable décentralisé » sur le créneau : valeur à revoir"
    )
    assert float(part["tot"]) == pytest.approx(48.3, abs=0.5), (
        "T4 affiche « 48 % avec la grande hydraulique » sur le créneau : valeur à revoir"
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
    """T6 : Sardaigne ~69 % thermique (majoritaire), Corse ~55 % (génération seule).

    69 et non 65 depuis le 22/08/2026 : B20 (« Other ») était rangé en « autre » alors que
    le bilan régional de Terna le compte dans le thermique — il n'a nulle part ailleurs où
    le mettre. Cf. docs/VERIF_ENTSOE_TERNA.md § 3.1.
    """
    s = con.execute(
        f"""SELECT 100.0*sum(thermique_mw)/sum(production_totale_mw),
                   100.0*sum(eolien_mw)/sum(production_totale_mw),
                   100.0*sum(autre_mw)/sum(production_totale_mw)
            FROM '{SARD.as_posix()}'"""
    ).fetchone()
    assert s[0] == pytest.approx(69.1, abs=1.0), (
        f"thermique sarde = {s[0]:.1f} % — le titre « deux îles thermiques » de T6 à revoir"
    )
    # Le poste « autre » sarde n'a AUCUNE contrepartie corse (T6 code un « autre » corse à
    # 0,0 en dur). S'il redevient non nul, la figure recommence à empiler un bloc qui n'a
    # pas d'équivalent en face : c'est le défaut que le reclassement de B20 a corrigé.
    assert s[2] == pytest.approx(0.0, abs=0.05), (
        f"« autre » sarde = {s[2]:.2f} % — un code PSR non thermique est réapparu ; T6 "
        "empile de nouveau un segment sans contrepartie corse (cf. PSR_VERS_FILIERE)"
    )
    # Contraste éolien du sous-titre : Sardaigne ~15 %, Corse ~1 % (≈ 15×).
    c_eol = con.execute(
        f"""SELECT 100.0*sum(eolien_mw)/sum(thermique_mw+hydraulique_mw+photovoltaique_mw
                   +eolien_mw+bioenergies_mw) FROM '{COURBE.as_posix()}'"""
    ).fetchone()[0]
    assert s[1] / c_eol >= 10, (
        f"éolien sarde {s[1]:.1f} % vs corse {c_eol:.1f} % — le « 15 fois plus » de T6 ne tient plus"
    )


@besoin_sard
@besoin_courbe
def test_t6_compare_bien_deux_fois_la_meme_periode():
    """T6 annonce « moyenne 2019-2024 » : les deux barres doivent couvrir cette période.

    Le piège n'est pas théorique — la courbe corse porte déjà une heure de 2025, et EDF
    publiera l'année entière. Sans borne, la figure comparerait une Corse plus longue à une
    Sardaigne arrêtée en 2024, sans rien afficher de ce décalage. On interroge la fonction
    qui construit la figure, pas les Parquet : c'est la BORNE qu'on verrouille, et elle ne
    se voit que là. Cf. docs/VERIF_ENTSOE_TERNA.md § 5.
    """
    from demonstrateur.figures import FENETRE_T6, mix_t6

    _, _, span_corse, span_sard = mix_t6()
    assert span_corse == span_sard == FENETRE_T6, (
        f"T6 compare une Corse {span_corse} à une Sardaigne {span_sard}, "
        f"alors que la figure annonce {FENETRE_T6} — la borne a sauté d'un côté"
    )


@besoin_sard
def test_heure_locale_sarde_est_bien_locale(con):
    """`heure_locale` côté sarde doit être l'heure de Rome, pas l'heure UTC.

    Le verrou n'interroge aucune convention déclarée, mais le soleil : la fenêtre de
    production solaire doit se poser sur le lever et le coucher réels. C'est ce qui a
    révélé le défaut du 22/08/2026 — `timezone()` INTERPRÈTE un TIMESTAMP naïf au lieu de
    le convertir, si bien que la colonne portait l'heure UTC, fausse d'une heure l'hiver et
    de deux l'été (pic solaire à 11 h, impossible à 9° de longitude). Aucune figure ne
    lisait alors cette colonne : le défaut était invisible et le serait resté jusqu'au
    premier profil horaire comparé. Cf. docs/VERIF_ENTSOE_TERNA.md § 5.
    """
    # Seuil à 20 MW : bien au-dessus du bruit d'un parc de ~1,3 GW, bien en dessous d'une
    # vraie heure de production — on cherche les BORDS de la journée solaire.
    for mois, lever, coucher in ((1, 8, 17), (7, 6, 21)):
        a, b = con.execute(
            f"""SELECT min(heure_locale), max(heure_locale) FROM '{SARD.as_posix()}'
                WHERE extract('month' FROM (date_heure AT TIME ZONE 'UTC')
                                            AT TIME ZONE 'Europe/Rome') = {mois}
                  AND solaire_mw > 20"""
        ).fetchone()
        assert abs(a - lever) <= 1 and abs(b - coucher) <= 1, (
            f"mois {mois} : le solaire sarde produit de {a} h à {b} h, alors que le soleil "
            f"se lève vers {lever} h et se couche vers {coucher} h — `heure_locale` n'est "
            "plus l'heure de Rome (conversion de fuseau perdue dans prepare)"
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


# Le gradient ville/campagne ne se lit PAS sur le flux du jour (corrigé le 24/08/2026).
# L'y avoir mis a bloqué la publication : VENACO, seule station rurale de l'île, s'est tue
# le 21/08/2026 à 10 h — le site entier, ses trois polluants d'un coup — pendant que le
# référentiel Geod'air la donne toujours « En service ». Une panne d'analyseur, pas un
# périmètre qui bouge, et la série 2013 -> aujourd'hui n'en perd pas une heure. Même leçon
# que le 19/08 pour BASTIA LA MARANA : ce que la journée fraîche sait dire n'est pas ce
# qu'on lui demandait.
#
# L'affirmation « l'air de campagne n'est pas meilleur » se tient là où vit sa donnée, et
# elle s'y tenait déjà : `test_l_air_de_campagne_n_est_pas_meilleur` la rejoue sur les étés
# 2020-2025, `test_la_serie_couvre_les_six_stations_sur_douze_ans` garde les six stations,
# et `tests/test_stations_air.py` confronte au référentiel le classement « Rurale
# régionale » comme l'état en service — deux contrôles qui répondent analyseur éteint.
# Il n'y avait donc rien à déplacer, seulement une copie de trop, et c'était la seule
# qu'une panne de terrain pouvait casser.

@besoin_air
def test_air_corse_le_perimetre_ozone_reste_hors_trafic(con):
    """Ce dont le flux du jour est le bon témoin : le périmètre, qui s'y montre en premier.

    Près des moteurs, le monoxyde d'azote détruit l'ozone — aucune station trafic n'en
    mesure. Si l'une s'y mettait, ou si une station changeait de classement, la journée
    fraîche le dirait avant la série ; et la mêler à une comparaison ville/campagne
    confondrait des populations non comparables.

    Le décompte non nul garde l'autre bout : le jour où le producteur renomme son code
    polluant, le flux continuerait de passer tous les autres contrôles en silence.
    """
    src = AIR.as_posix()
    mesures, trafic = con.execute(
        f"""SELECT count(*), count(*) FILTER (WHERE influence = 'Trafic')
            FROM '{src}' WHERE polluant = 'O3'"""
    ).fetchone()
    assert mesures, "aucune mesure d'ozone dans le flux du jour — code polluant modifié ?"
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
#
# Les deux sens du contrôle ne se lisent pas sur la même source (corrigé le 19/08/2026).
# Une station de plus se montre dès le flux du jour ; une entrée qui ne désigne rien est
# un défaut du CODE, qui se lit sur la série entière. Les avoir confondus a arrêté la
# chaîne : l'analyseur d'ozone de BASTIA LA MARANA est muet depuis le 05/08/2026 à 14 h
# (sa station publie toujours NO2 et PM10 ; l'AEE la donne à 0 heure valide sur 318), et
# l'appariement s'est trouvé accusé d'un défaut qu'il n'a pas.

@besoin_air
def test_aucune_station_d_ozone_ne_reste_sans_poste(con):
    """Le jour où Qualitair Corse ouvre une septième station, elle apparaîtra dans le
    Parquet sans température associée : ce test le dit, au lieu de laisser la station
    disparaître silencieusement du croisement. Le flux du jour est ici la bonne source —
    c'est là qu'une station neuve se voit en premier.
    """
    stations = {
        r[0]
        for r in con.execute(
            f"SELECT DISTINCT code_site FROM '{AIR.as_posix()}' WHERE polluant = 'O3'"
        ).fetchall()
    }
    sans_poste = stations - set(APPARIEMENT_AIR_METEO)
    assert not sans_poste, f"station(s) d'ozone sans poste météo : {sorted(sans_poste)}"


@besoin_serie
def test_aucun_apparie_ne_designe_une_station_sans_ozone(con):
    """L'autre sens : pas d'entrée d'appariement qui ne corresponde à rien.

    Contrôlé sur la SÉRIE (2013 -> aujourd'hui), jamais sur le flux du jour : ce qu'on
    cherche est un code de station faux ou périmé, qui n'a alors jamais porté d'ozone.
    Une station qui en a mesuré puis s'arrête, elle, reste correctement appariée — son
    silence est un fait de terrain, pas une erreur de table.
    """
    stations = {
        r[0]
        for r in con.execute(
            f"SELECT DISTINCT code_site FROM '{SERIE.as_posix()}' WHERE polluant = 'O3'"
        ).fetchall()
    }
    fantomes = set(APPARIEMENT_AIR_METEO) - stations
    assert not fantomes, (
        f"apparié(s) sans aucune mesure d'ozone dans la série : {sorted(fantomes)}"
    )


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
        f"""SELECT annee_locale AS an,
                   100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
                   100.0*sum(thermique_mw)/sum(production_totale_mw)   AS thermique
            FROM '{COURBE.as_posix()}'
            WHERE annee_locale BETWEEN 2019 AND 2024
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
        nom, lat, lon = STATIONS_AIR[code_site][:3]
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


@besoin_serie
@besoin_air
def test_la_serie_aee_et_le_flux_lcsqa_coincident(con):
    """Contrôle croisé de deux canaux indépendants — le seul garde-fou sérieux du fuseau.

    L'AEE et le LCSQA servent la même mesure par deux chemins différents, avec deux
    conventions horaires différentes : UTC+1 en fin de période pour l'un, UTC+1 en début
    pour l'autre. D'où deux heures à retirer d'un côté, une seule de l'autre. Une erreur
    d'une heure ne se verrait sur AUCUNE figure — le profil serait simplement décalé, et
    « le pire créneau pour un effort en plein air » désignerait la mauvaise heure.

    Sur l'axe UTC reconstruit, les valeurs doivent être IDENTIQUES, pas seulement proches.
    """
    n, ecart = con.execute(
        f"""SELECT count(*), max(abs(a.valeur - l.valeur))
            FROM '{SERIE.as_posix()}' a
            JOIN (SELECT date_heure_utc, station, polluant, valeur FROM '{AIR.as_posix()}'
                  WHERE polluant IN ('O3', 'NO2')) l
              ON a.date_heure_utc = l.date_heure_utc AND a.station = l.station
             AND a.polluant = l.polluant"""
    ).fetchone()
    assert n > 0, (
        "aucune heure commune entre la série AEE et le flux LCSQA — le recouvrement doit "
        "exister (le flux publie J-2, l'AEE va jusqu'au jour même)"
    )
    assert ecart == 0, (
        f"{n} heures appariées mais écart max {ecart} µg/m³ — les deux canaux divergent, "
        "donc l'axe UTC d'au moins l'un des deux est faux"
    )


@besoin_serie
def test_la_serie_couvre_les_six_stations_sur_douze_ans(con):
    """La série doit porter les six stations et remonter à 2013, sinon un titre repose
    sur moins de profondeur qu'annoncé."""
    n, stations, debut, fin = con.execute(
        f"""SELECT count(*), count(DISTINCT station), min(date_locale), max(date_locale)
            FROM '{SERIE.as_posix()}'"""
    ).fetchone()
    assert stations == 6, f"{stations} stations dans la série (attendu 6)"
    assert str(debut) <= "2013-01-02", f"série commençant le {debut} — 2013 attendu"
    assert n > 400_000, f"{n:,} heures — la série paraît tronquée"


@besoin_serie
def test_les_depassements_se_produisent_sans_alerte(con):
    """TITRE N° 1 : l'objectif de qualité est franchi des jours où aucun seuil
    d'information n'est approché.

    C'est l'affirmation qui définit le sujet, et le chiffre est sans appel : sur les étés
    2013-2025, la totalité des journées dépassant 120 µg/m³ en maximum journalier sur 8 h
    l'ont fait sans qu'aucune heure n'atteigne les 180 µg/m³ du seuil d'information. Si
    cette proportion cessait d'être totale, le titre devrait être réécrit — pas la figure.
    """
    total, sans_alerte = con.execute(
        f"""WITH j AS (
              SELECT date_locale, station, mda8 FROM '{MDA8.as_posix()}'
              WHERE valide AND extract('month' FROM date_locale) IN (6, 7, 8)
                AND extract('year' FROM date_locale) BETWEEN 2013 AND 2025),
            h AS (SELECT date_locale, station, max(valeur) AS mx
                  FROM '{SERIE.as_posix()}' WHERE polluant = 'O3' GROUP BY 1, 2)
            SELECT count(*) FILTER (WHERE j.mda8 > 120),
                   count(*) FILTER (WHERE j.mda8 > 120 AND h.mx < 180)
            FROM j JOIN h USING (date_locale, station)"""
    ).fetchone()
    assert total > 500, f"{total} jour-station de dépassement — le titre attend des centaines"
    assert sans_alerte == total, (
        f"{sans_alerte}/{total} dépassements sans alerte — le titre n° 1 affirme la "
        "totalité ; à réécrire si ce n'est plus vrai"
    )


@besoin_serie
def test_le_pic_d_ozone_n_est_pas_a_l_heure_de_pointe(con):
    """TITRE N° 3 : l'ozone et le NO2 culminent à des heures opposées.

    Comparaison à STATION CONSTANTE — les cinq qui mesurent les deux polluants, Venaco
    exclue puisqu'elle n'a plus de NO2 et n'a pas d'heure de pointe à opposer. Le NO2 suit
    les moteurs et culmine le matin ; l'ozone se fabrique sous le soleil et culmine
    l'après-midi. Si les deux pics se rapprochaient à moins de quatre heures, le titre
    n'aurait plus de sens.
    """
    pics = dict(
        con.execute(
            f"""SELECT polluant, arg_max(heure_locale, m) FROM (
                  SELECT polluant, heure_locale, avg(valeur) AS m
                  FROM '{SERIE.as_posix()}'
                  WHERE extract('month' FROM date_locale) IN (6, 7, 8)
                    AND station <> 'VENACO'
                  GROUP BY 1, 2) GROUP BY 1"""
        ).fetchall()
    )
    assert 13 <= pics["O3"] <= 18, f"pic d'ozone à {pics['O3']} h — attendu l'après-midi"
    assert 5 <= pics["NO2"] <= 10, f"pic de NO2 à {pics['NO2']} h — attendu le matin"
    assert pics["O3"] - pics["NO2"] >= 4, (
        f"pics distants de {pics['O3'] - pics['NO2']} h seulement — le titre n° 3 oppose "
        "l'heure de pointe et l'heure du soleil, il lui faut un écart net"
    )


@besoin_croise
def test_le_croisement_porte_le_poste_et_non_la_commune(con):
    """Chaque ligne nomme le poste météo dont vient sa température.

    Sans cette colonne, la figure écrirait « température à Venaco » là où le thermomètre
    est à Vivario, dix kilomètres plus loin et cent vingt mètres plus haut. Le brief exige
    que l'approximation soit assumée à l'écrit — encore faut-il que la donnée la porte.
    """
    lignes = con.execute(
        f"SELECT DISTINCT station, poste FROM '{CROISE.as_posix()}' ORDER BY 1"
    ).fetchall()
    assert len(lignes) == 6, f"{len(lignes)} couples station/poste (attendu 6)"
    couples = dict(lignes)
    assert couples["VENACO"].startswith("VIVARIO"), (
        f"Venaco croisée avec {couples['VENACO']} — Vivario attendu"
    )
    assert all(p for p in couples.values()), "poste météo non renseigné sur certaines lignes"


@besoin_croise
def test_l_ozone_monte_avec_la_chaleur_mais_plafonne(con):
    """TITRE N° 2, avec sa nuance : la relation existe, et elle n'est pas monotone.

    Sur les étés 2020-2025 et les seules stations de fond, l'ozone gagne près de neuf
    µg/m³ entre les journées sous 25 °C et celles de 30 à 35 °C. Mais il REDESCEND
    au-delà de 35 °C. Un titre qui promettrait « plus il fait chaud, plus il y en a »
    serait donc faux dans sa partie haute — ce test fige la montée ET le plafond, pour
    qu'une figure ne puisse pas extrapoler la première en oubliant le second.

    Association, jamais causalité : ce sont des journées chaudes qui portent plus d'ozone,
    pas la chaleur qui le fabrique (cf. la garde du brief).
    """
    par_tranche = dict(
        con.execute(
            f"""SELECT CASE WHEN t_max < 25 THEN 'froid'
                            WHEN t_max < 30 THEN 'doux'
                            WHEN t_max < 35 THEN 'chaud'
                            ELSE 'tres_chaud' END, avg(mda8)
                FROM '{CROISE.as_posix()}'
                WHERE influence = 'Fond' AND extract('month' FROM date_locale) IN (6, 7, 8)
                  AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025
                GROUP BY 1"""
        ).fetchall()
    )
    assert par_tranche["chaud"] > par_tranche["froid"] + 5, (
        f"écart chaud − froid = {par_tranche['chaud'] - par_tranche['froid']:.1f} µg/m³ — "
        "le titre n° 2 annonce une montée nette"
    )
    assert par_tranche["froid"] < par_tranche["doux"] < par_tranche["chaud"], (
        "la montée doit être régulière jusqu'à 35 °C"
    )
    assert par_tranche["tres_chaud"] < par_tranche["chaud"], (
        "au-delà de 35 °C l'ozone REDESCEND : c'est la nuance du titre n° 2, et elle "
        "interdit d'extrapoler la montée"
    )


@besoin_croise
def test_l_air_de_campagne_n_est_pas_meilleur(con):
    """TITRE N° 4 : Venaco dépasse les stations urbaines, en moyenne et en fréquence.

    Comparaison entre stations « de fond » uniquement — y mêler la station industrielle ou
    les stations trafic mélangerait les populations (cf. le brief). Les effectifs diffèrent
    (une station rurale contre quatre urbaines), d'où la comparaison en TAUX et non en
    nombre de jours.
    """
    venaco, urbain = con.execute(
        f"""SELECT
              avg(mda8) FILTER (WHERE station = 'VENACO'),
              avg(mda8) FILTER (WHERE station <> 'VENACO')
            FROM '{CROISE.as_posix()}'
            WHERE influence = 'Fond' AND extract('month' FROM date_locale) IN (6, 7, 8)
              AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025"""
    ).fetchone()
    assert venaco > urbain, (
        f"Venaco {venaco:.1f} µg/m³ contre {urbain:.1f} en ville — le titre n° 4 affirme "
        "que la campagne n'est pas épargnée"
    )
    tx_v, tx_u = con.execute(
        f"""SELECT
              100.0 * count(*) FILTER (WHERE station = 'VENACO' AND mda8 > 120)
                    / nullif(count(*) FILTER (WHERE station = 'VENACO'), 0),
              100.0 * count(*) FILTER (WHERE station <> 'VENACO' AND mda8 > 120)
                    / nullif(count(*) FILTER (WHERE station <> 'VENACO'), 0)
            FROM '{CROISE.as_posix()}'
            WHERE influence = 'Fond' AND extract('month' FROM date_locale) IN (6, 7, 8)
              AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025"""
    ).fetchone()
    assert tx_v > tx_u, (
        f"taux de dépassement : Venaco {tx_v:.1f} %, ville {tx_u:.1f} % — la campagne doit "
        "dépasser plus souvent, pas moins"
    )


@besoin_serie
def test_le_pire_creneau_estival_est_l_apres_midi(con):
    """TITRE N° 5 : la conclusion actionnable du livrable.

    Sur les étés 2020-2025 et les stations de fond, l'ozone dessine un plateau très net de
    11 h à 18 h, à plus de 95 % de son maximum, contre un creux au petit matin. C'est ce
    créneau que la figure nomme — et il doit rester CONTIGU : une plage trouée ne se
    résumerait pas en « entre X et Y heures », et le titre devrait changer de forme.

    Le chiffre publié est un niveau d'exposition, pas une prescription : la figure dit à
    quelle heure l'air est le plus chargé, elle ne délivre pas de conseil médical.
    """
    profil = dict(
        con.execute(
            f"""SELECT heure_locale, avg(valeur) FROM '{SERIE.as_posix()}'
                WHERE polluant = 'O3' AND influence = 'Fond'
                  AND extract('month' FROM date_locale) IN (6, 7, 8)
                  AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025
                GROUP BY 1"""
        ).fetchall()
    )
    assert len(profil) == 24, f"{len(profil)} heures dans le profil (attendu 24)"
    pic_h = max(profil, key=profil.get)
    creux_h = min(profil, key=profil.get)
    assert 13 <= pic_h <= 16, f"pic à {pic_h} h — attendu au cœur de l'après-midi"
    assert 4 <= creux_h <= 8, f"creux à {creux_h} h — attendu au petit matin"

    plateau = sorted(h for h, v in profil.items() if v >= 0.95 * profil[pic_h])
    assert plateau == list(range(plateau[0], plateau[-1] + 1)), (
        f"plateau troué {plateau} — « entre X et Y heures » suppose une plage contiguë"
    )
    assert plateau[0] == 11 and plateau[-1] == 18, (
        f"créneau {plateau[0]}-{plateau[-1]} h — le brief publie « 11 h à 18 h »"
    )
    ecart = 100 * (profil[pic_h] - profil[creux_h]) / profil[creux_h]
    assert ecart > 25, f"écart creux→pic de {ecart:.0f} % — trop faible pour un titre"


@besoin_serie
def test_l_heure_la_plus_propre_en_ozone_est_la_pire_en_no2(con):
    """La nuance qui empêche le titre n° 5 de devenir un mauvais conseil.

    Le creux d'ozone du petit matin coïncide avec le PIC de NO2 : l'air le moins chargé en
    l'un est le plus chargé en l'autre, et pour la même raison chimique — le monoxyde d'azote
    des moteurs détruit l'ozone. Publier « courez le matin » sans cette réserve reviendrait
    à déplacer l'exposition plutôt qu'à la réduire.
    """
    pics = {}
    for pol, extremum in (("O3", "min"), ("NO2", "max")):
        rows = con.execute(
            f"""SELECT heure_locale, avg(valeur) FROM '{SERIE.as_posix()}'
                WHERE polluant = '{pol}' AND influence = 'Fond' AND station <> 'VENACO'
                  AND extract('month' FROM date_locale) IN (6, 7, 8)
                  AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025
                GROUP BY 1"""
        ).fetchall()
        d = dict(rows)
        pics[pol] = min(d, key=d.get) if extremum == "min" else max(d, key=d.get)
    assert abs(pics["O3"] - pics["NO2"]) <= 2, (
        f"creux d'ozone à {pics['O3']} h, pic de NO2 à {pics['NO2']} h — la coïncidence "
        "fonde la réserve du titre n° 5 ; si elle disparaît, la réserve est à réécrire"
    )


# --- Titre 7 : la dépendance, deux périmètres qu'on ne compare pas de tête -----
def test_les_postes_oreges_forment_bien_cent_pour_cent():
    """La décomposition recopiée de la Lettre OREGES 2021 (p. 4) est complète et cohérente.

    Ces cinq postes ne sont pas calculés : ils sont RECOPIÉS d'une publication de l'AUE
    (énergie primaire 2020, 605 ktep). Le test tient les deux propriétés qui rendent la
    recopie vérifiable : la somme fait 100 % du mix primaire, et les deux postes venus de
    l'extérieur reconstituent EXACTEMENT le taux de dépendance de 86,1 % annoncé par le
    producteur. Une faute de saisie dans un poste casse l'une ou l'autre.
    """
    from demonstrateur.figures import OREGES_2020, OREGES_CARBURANTS, OREGES_DEPENDANCE

    assert sum(OREGES_2020.values()) == pytest.approx(100.0, abs=0.05), (
        f"les postes OREGES somment à {sum(OREGES_2020.values()):.2f} % — recopie incomplète"
    )
    importe = OREGES_2020["petrole"] + OREGES_2020["liaisons"]
    assert importe == pytest.approx(OREGES_DEPENDANCE, abs=0.05), (
        f"pétrole + liaisons = {importe:.2f} %, or l'OREGES publie un taux de dépendance "
        f"de {OREGES_DEPENDANCE} % — les deux doivent coïncider, c'est la même quantité"
    )
    assert OREGES_CARBURANTS < OREGES_2020["petrole"], (
        "les carburants des transports sont un SOUS-poste des produits pétroliers"
    )


@besoin_courbe
def test_la_dependance_electrique_est_bien_en_deca_du_taux_energetique(con):
    """Le fait du titre n° 7 : deux périmètres emboîtés que le débat public confond.

    Le taux de dépendance de 86,1 % (OREGES, 2020) porte sur TOUTE l'énergie primaire,
    carburants et chauffage compris ; il est régulièrement rattaché à la seule
    électricité, qui reste nettement en deçà. Si cet écart se refermait, le titre serait
    à réécrire.

    Ce docstring citait jusqu'au 05/08/2026 une phrase de presse attribuée à un journal
    et à une date précis. Recherche faite, la citation n'était pas vérifiable et a été
    retirée (cf. la fiche « Une source qui n'existait pas » de docs/SOURCES_LOCALES.md).
    Le fait testé ici n'en dépendait pas : il tient à l'écart entre deux périmètres.
    """
    from demonstrateur.figures import OREGES_DEPENDANCE

    th, im = con.execute(
        f"""SELECT 100.0*sum(thermique_mw)/sum(production_totale_mw),
                   100.0*sum(importations_mw)/sum(production_totale_mw)
            FROM '{COURBE.as_posix()}'"""
    ).fetchone()
    importe = th + im
    assert 66.0 <= importe <= 70.0, (
        f"part de l'électricité venue de l'extérieur : {importe:.1f} % "
        f"(thermique {th:.1f} + imports {im:.1f}) — hors de la fourchette publiée (~67,8 %)"
    )
    assert OREGES_DEPENDANCE - importe > 15.0, (
        f"l'écart entre les deux périmètres n'est plus que de "
        f"{OREGES_DEPENDANCE - importe:.1f} points — le titre n° 7 repose sur cet écart"
    )


@besoin_courbe
def test_le_controle_croise_2020_recolle_a_la_publication_de_l_oreges(con):
    """Notre pipeline et le producteur régional disent la même chose sur la même année.

    L'OREGES publie, pour 2020 : 36 % de thermique et 29,8 % de liaisons électriques.
    C'est le contrôle croisé le plus fort dont dispose l'étude — une source officielle,
    indépendante de notre chaîne, sur exactement le même périmètre. Il est affiché en note
    du visuel : s'il se met à diverger, la note ment.
    """
    th, im = con.execute(
        f"""SELECT 100.0*sum(thermique_mw)/sum(production_totale_mw),
                   100.0*sum(importations_mw)/sum(production_totale_mw)
            FROM '{COURBE.as_posix()}'
            WHERE annee_locale = 2020"""
    ).fetchone()
    assert th == pytest.approx(36.0, abs=0.5), (
        f"thermique 2020 = {th:.1f} %, l'OREGES publie 36 % — écart trop grand pour "
        "que le contrôle croisé affiché en note du visuel tienne"
    )
    assert im == pytest.approx(29.8, abs=0.5), (
        f"liaisons 2020 = {im:.1f} %, l'OREGES publie 29,8 %"
    )


# --- Titre 8 : le seuil de déconnexion est déjà franchi, de plus en plus ------
@besoin_courbe
def test_le_seuil_de_deconnexion_est_deja_largement_franchi(con):
    """Le fait du titre n° 8 : le plafond n'est pas devant la Corse, il est derrière.

    Le seuil de l'arrêté du 23 avril 2008 (30 % ailleurs, 35 % en Corse) est un DROIT de
    débrancher, pas un mur : la part intermittente peut le dépasser, et elle le fait plus
    de mille heures par an. Même le seuil visé par la PPE (45 %) est déjà franchi des
    centaines d'heures. Si ce n'était plus vrai, le visuel raconterait l'inverse.
    """
    from demonstrateur.figures import SEUIL_CORSE, SEUIL_VISE

    part = """100.0*(greatest(photovoltaique_mw,0)+greatest(eolien_mw,0))
               /production_totale_mw"""
    corse, vise = con.execute(
        f"""SELECT sum(CASE WHEN {part} > {SEUIL_CORSE} THEN 1 ELSE 0 END),
                   sum(CASE WHEN {part} > {SEUIL_VISE}  THEN 1 ELSE 0 END)
            FROM '{COURBE.as_posix()}'
            WHERE annee_locale = 2024"""
    ).fetchone()
    assert corse > 1000, (
        f"2024 : {corse} h au-dessus du seuil corse de {SEUIL_CORSE} % — le titre annonce "
        "plus de mille heures par an"
    )
    assert vise > 100, (
        f"2024 : {vise} h au-dessus du seuil visé de {SEUIL_VISE} % — le visuel affirme "
        "que même le seuil futur est déjà franchi des centaines d'heures"
    )


@besoin_courbe
def test_la_pression_sur_le_seuil_croit_avec_le_parc(con):
    """La pente du visuel : la contrainte se resserre, elle ne se desserre pas.

    Comparaison en deux moitiés (2019-2021 contre 2022-2024) plutôt qu'année contre
    année : une seule année sèche ou venteuse ne doit pas faire basculer le constat.
    """
    from demonstrateur.figures import SEUIL_CORSE

    part = """100.0*(greatest(photovoltaique_mw,0)+greatest(eolien_mw,0))
               /production_totale_mw"""
    tot, recent = con.execute(
        f"""WITH h AS (
              SELECT annee_locale AS annee,
                     {part} AS p
              FROM '{COURBE.as_posix()}')
            SELECT sum(CASE WHEN p > {SEUIL_CORSE} AND annee BETWEEN 2019 AND 2021
                            THEN 1 ELSE 0 END),
                   sum(CASE WHEN p > {SEUIL_CORSE} AND annee BETWEEN 2022 AND 2024
                            THEN 1 ELSE 0 END)
            FROM h"""
    ).fetchone()
    assert recent > tot, (
        f"heures au-dessus du seuil : {tot} h en 2019-2021 contre {recent} h en 2022-2024 "
        "— le visuel montre une pression croissante ; si elle s'inverse, il est à refaire"
    )


@besoin_serie
def test_le_total_affiche_compte_des_journees_et_non_des_couples(con):
    """Le chiffre mis en avant par A1 est un nombre de JOURNÉES du calendrier.

    Une journée chargée fait dépasser plusieurs stations à la fois : additionner les
    barres donne un total de couples journée-station (173), très supérieur au nombre de
    journées réellement concernées (106). Publier le premier en disant « journées »
    laisserait entendre qu'il y a eu 173 jours de dépassement sur la période. Le test
    tient l'écart entre les deux : s'il disparaissait, c'est que le calcul a glissé.
    """
    couples, journees = con.execute(
        f"""SELECT count(*) FILTER (WHERE mda8 > 120),
                   count(DISTINCT CASE WHEN mda8 > 120 THEN date_locale END)
            FROM '{MDA8.as_posix()}'
            WHERE valide AND influence = 'Fond'
              AND extract('month' FROM date_locale) IN (6, 7, 8)
              AND extract('year' FROM date_locale) BETWEEN 2020 AND 2025"""
    ).fetchone()
    assert journees < couples, (
        f"{journees} journées pour {couples} couples journée-station : les deux devraient "
        "différer (plusieurs stations dépassent le même jour). Si elles se rejoignent, "
        "vérifier le périmètre avant de publier le total comme un nombre de journées"
    )
    from demonstrateur.figures_air import fig_a1_depassements_sans_alerte

    textes = [a.text for a in fig_a1_depassements_sans_alerte().layout.annotations]
    assert any(f"{journees} journées" in t for t in textes), (
        f"A1 doit afficher les {journees} journées distinctes, jamais les {couples} "
        "couples journée-station"
    )

# --- Verrous de l'étude en prose (docs/etude.md) -----------------------------
# Chaque chiffre écrit dans l'étude est tenu par un test : une révision de la donnée
# EDF qui déplacerait un nombre publié doit casser la suite, pas passer inaperçue.
# Rapatriés depuis `etude-brouillon` avec l'étude elle-même.


@besoin_courbe
def test_etude_creneau_le_plus_corse(con):
    """Étude/T4 : le créneau de midi est aussi le plus insulaire (84 %), et les câbles
    dépassent le tiers de 23 h à 7 h.

    La fenêtre de nuit est RE-DÉRIVÉE, pas translatée : l'ancienne (1-8 h) était calée sur
    l'horodatage faux, et 8 h est aujourd'hui en plein jour — les câbles n'y font plus que
    29 %. On mesure donc les heures où ils passent effectivement le tiers, et l'étude écrit
    celles-là.
    """
    df = con.execute(
        f"""SELECT heure_locale,
              100*sum(importations_mw)/sum(production_totale_mw) AS imports
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    df["locale"] = 100 - df["imports"]
    top3 = set(df.nlargest(3, "locale")["heure_locale"].astype(int))
    assert top3 == {12, 13, 14}, (
        f"les trois heures les plus « corses » sont {sorted(top3)} — l'étude écrit "
        "que le créneau de midi et l'heure qui le suit tiennent le haut du classement"
    )
    creneau = float(
        con.execute(
            f"""SELECT 100-100*sum(importations_mw)/sum(production_totale_mw)
                FROM '{COURBE.as_posix()}' WHERE heure_locale BETWEEN 12 AND 13"""
        ).fetchone()[0]
    )
    assert creneau == pytest.approx(84.5, abs=0.5), (
        f"part locale sur 12-13 h = {creneau:.1f} % — l'étude écrit « 84 % produits sur l'île »"
    )
    nuit = sorted(df.loc[df["imports"] > 100 / 3, "heure_locale"].astype(int))
    assert nuit == [0, 1, 2, 3, 4, 5, 6, 7, 23], (
        f"les câbles dépassent le tiers aux heures {nuit} — l'étude écrit « de 23 heures "
        "à 7 heures »"
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
            WHERE annee_locale BETWEEN 2019 AND 2024"""
    ).fetchone()
    assert part == pytest.approx(27.8, abs=0.4), (
        f"part importée = {part:.1f} % — l'étude écrit « 27,8 % »"
    )
    assert part > 25, "part importée sous le quart — l'étude écrit « plus du quart »"
    assert exp == pytest.approx(607, abs=5), (
        f"{exp} heures d'export — l'étude écrit « 607 heures, à peine plus de 1 % du temps »"
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
    # Clé de lecture incrustée dans T5 (30/07/2026) : le pire mois sert d'exemple chiffré
    # au lecteur non initié, ramené à une durée quotidienne. Les deux chiffres bougent
    # ensemble ou la légende ment.
    an, mois, pire = con.execute(
        f"SELECT annee, mois_cal, duree_h FROM '{ECRET.as_posix()}' ORDER BY duree_h DESC LIMIT 1"
    ).fetchone()
    assert (int(an), int(mois)) == (2020, 5) and pire == pytest.approx(141, abs=0.5), (
        f"pire mois = {int(mois):02d}/{int(an)} à {pire:.0f} h — T5 et l'étude écrivent "
        "« mai 2020, 141 h »"
    )
    assert pire / 31 == pytest.approx(4.5, abs=0.2), (
        f"{pire / 31:.1f} h par jour en mai 2020 — la clé de lecture de T5 écrit "
        "« près de 4 h 30 par jour »"
    )


@besoin_courbe
def test_etude_hydro_trois_perimetres(con):
    """Étude/section 4 et T6-T7 : l'hydraulique est citée sur trois bases différentes, et
    c'est le piège de lecture le plus facile du document. Ce test fige les trois d'un coup,
    pour qu'aucune ne dérive vers l'autre au fil des mises à jour :
      - grande hydraulique / génération locale  = 25 % -> « un quart de ce que l'île produit »
      - hydraulique totale  / génération locale = 28 % -> T6 (micro-hydraulique incluse)
      - grande hydraulique / mix total          = 18 % -> base de T7, 12 à 22 % selon l'année
    Écrire « près du quart » à côté d'une figure qui affiche 12-22 % n'est faux qu'à la
    lecture : les deux nombres sont justes, sur des populations différentes. D'où la règle
    du document — le périmètre est écrit à côté du chiffre, jamais sous-entendu."""
    grande_loc, totale_loc, grande_mix = con.execute(
        f"""WITH b AS (
              SELECT sum(thermique_mw) th, sum(hydraulique_mw) hy,
                     sum(coalesce(micro_hydraulique_mw, 0)) mh, sum(photovoltaique_mw) so,
                     sum(eolien_mw) eo, sum(bioenergies_mw) bi, sum(production_totale_mw) tot
              FROM '{COURBE.as_posix()}')
            SELECT 100*hy/(th+hy+mh+so+eo+bi), 100*(hy+mh)/(th+hy+mh+so+eo+bi), 100*hy/tot
            FROM b"""
    ).fetchone()
    assert grande_loc == pytest.approx(25.0, abs=0.7), (
        f"grande hydraulique / génération locale = {grande_loc:.1f} % — la section 4 écrit "
        "« un quart de ce que l'île produit elle-même »"
    )
    assert round(totale_loc) == 28, (
        f"hydraulique totale / génération locale = {totale_loc:.1f} % — T6 écrit 28 %"
    )
    assert grande_mix == pytest.approx(18.1, abs=1.0), (
        f"grande hydraulique / mix total = {grande_mix:.1f} % — base de T7 (12 à 22 % par an)"
    )
    assert grande_loc > totale_loc - 5 and grande_mix < grande_loc, (
        "l'ordre des trois périmètres s'est inversé — la prose de la section 4 est à relire"
    )


@besoin_courbe
@besoin_sard
def test_etude_mix_generation_locale(con):
    """Étude/T6 : Corse (génération seule, convention de la figure) = 55/28/15/1 ;
    Sardaigne : hydro 4 %, solaire 9 %, éolien 15 %. Verrouille aussi la comparaison
    des deux vents citée en prose — le rapport, pas seulement les deux arrondis, car
    « quinze fois » se lit sur 15 %/1 % alors qu'il vaut 15,6 dans la donnée."""
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
    hy_s, so_s, eo_s, th_s = con.execute(
        f"""SELECT 100*sum(hydraulique_mw)/sum(production_totale_mw),
                   100*sum(solaire_mw)/sum(production_totale_mw),
                   100*sum(eolien_mw)/sum(production_totale_mw),
                   100*sum(thermique_mw)/sum(production_totale_mw) FROM '{SARD.as_posix()}'"""
    ).fetchone()
    # Le thermique sarde manquait ici, et c'est ce qui a failli laisser passer une phrase
    # fausse : le reclassement de B20 (22/08/2026) a déplacé ce chiffre de 65 à 69 % sans
    # qu'aucun verrou ne voie que la section 4 écrivait encore 65. Le seul test qui aurait
    # cassé était celui de T6 — c'est-à-dire précisément celui qu'on retouchait.
    assert round(th_s) == 69, (
        f"thermique sarde = {th_s:.1f} % — l'étude écrit « 69 % en Sardaigne »"
    )
    assert round(hy_s) == 4 and round(so_s) == 9, (
        f"Sardaigne hydro/solaire = {hy_s:.1f} % / {so_s:.1f} % — l'étude écrit 4 % et 9 %"
    )
    assert round(eo_s) == 15, f"éolien sarde = {eo_s:.1f} % — l'étude écrit « 15 % de vent »"
    rapport = eo_s / corse[3]
    assert rapport >= 15, (
        f"le vent sarde ne pèse que {rapport:.1f} fois le vent corse — "
        "l'étude écrit « plus de quinze fois la part corse »"
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


@besoin_courbe
def test_etude_profil_ete_parts(con):
    """Étude/T3 : été, mi-journée (12-13 h) = 36/43/16 (solaire/thermique/câbles),
    soir (18-21 h) = 6/58/25, et plus de huit dixièmes du kWh du soir en moteurs + câbles.

    Les deux fenêtres sont NOMMÉES dans l'étude, et re-dérivées après la correction
    d'horodatage : la mi-journée est le créneau de T4, le soir est la fenêtre où le solaire
    est retombé sans que la pointe du soir soit passée. Les anciennes (13-15 h et 20-23 h)
    étaient calées sur une heure fausse — les translater aurait reconstruit l'ancien récit
    au lieu de le remesurer.
    """
    def parts(a: int, b: int):
        return con.execute(
            f"""SELECT 100*sum(photovoltaique_mw)/sum(production_totale_mw) AS sol,
                       100*sum(thermique_mw)/sum(production_totale_mw)      AS th,
                       100*sum(importations_mw)/sum(production_totale_mw)   AS imp
                FROM '{COURBE.as_posix()}'
                WHERE mois_local IN (6, 7, 8) AND heure_locale BETWEEN {a} AND {b}"""
        ).df().iloc[0]

    m, s = parts(12, 13), parts(18, 21)
    assert (round(m["sol"]), round(m["th"]), round(m["imp"])) == (36, 43, 16), (
        f"mi-journée d'été = {m['sol']:.1f}/{m['th']:.1f}/{m['imp']:.1f} — l'étude écrit 36/43/16"
    )
    assert (round(s["sol"]), round(s["th"]), round(s["imp"])) == (6, 58, 25), (
        f"soir d'été = {s['sol']:.1f}/{s['th']:.1f}/{s['imp']:.1f} — l'étude écrit 6/58/25"
    )
    assert s["th"] + s["imp"] > 80, (
        "moteurs + câbles ≤ 80 % le soir d'été — le « huit dixièmes » de l'étude à revoir"
    )
    # Le titre de T3 tient sur l'heure, pas sur la fenêtre : à son zénith le solaire reste
    # derrière le thermique. C'est l'invariant que la figure vérifie avant de se tracer.
    heures = con.execute(
        f"""SELECT heure_locale AS h,
              100*sum(photovoltaique_mw)/sum(production_totale_mw) AS sol,
              100*sum(thermique_mw)/sum(production_totale_mw)      AS th
            FROM '{COURBE.as_posix()}' WHERE mois_local IN (6, 7, 8) GROUP BY 1"""
    ).df()
    zenith = int(heures.loc[heures["sol"].idxmax(), "h"])
    assert zenith == 13, (
        f"zénith solaire d'été à {zenith} h — l'étude et l'axe de T3 le placent à 13 h, "
        "soit le midi solaire corse en heure d'été (13 h 25)"
    )


@besoin_courbe
def test_etude_soleil_remplace_les_cables(con):
    """Étude/T4 (encadré) : de 8 h à 13 h, les imports reculent de ~77 à ~43 MW pendant
    que le thermique ne bouge pas.

    Les deux bornes sont re-choisies sur la courbe corrigée, et mieux qu'avant : à 8 h le
    socle thermique diurne est déjà en place (104 MW), si bien que « le thermique ne bouge
    pas » se lit sur 1 MW d'écart au lieu de 4.
    """
    df = (
        con.execute(
            f"""SELECT heure_locale, avg(importations_mw) AS imp, avg(thermique_mw) AS th
            FROM '{COURBE.as_posix()}' WHERE heure_locale IN (8, 13) GROUP BY 1"""
        )
        .df()
        .set_index("heure_locale")
    )
    assert float(df.loc[8, "imp"]) == pytest.approx(77, abs=2), "imports de 8 h ≠ ~77 MW"
    assert float(df.loc[13, "imp"]) == pytest.approx(43, abs=2), "imports de 13 h ≠ ~43 MW"
    assert abs(float(df.loc[13, "th"]) - float(df.loc[8, "th"])) < 4, (
        "le thermique bouge entre 8 h et 13 h — l'étude écrit qu'il « ne bouge pas »"
    )


@besoin_courbe
def test_etude_thermique_premier(con):
    """Étude/T4 : ce que « le plus vert » veut dire, mesuré. Le thermique ne recule que de
    près d'un cinquième entre son maximum et le créneau de midi, aucune heure ne le voit
    dépassé par le renouvelable décentralisé, et le total avec les barrages ne passe devant
    que de 9 h à 15 h. Verrouille aussi la garde de lecture du sous-titre de la figure.
    """
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
    assert large == [9, 10, 11, 12, 13, 14, 15], (
        f"total renouvelable devant le thermique aux heures {large} — "
        "l'étude écrit « de 9 heures à 15 heures »"
    )
    haut = float(df["thermique"].max())
    creneau = float(
        con.execute(
            f"""SELECT 100*sum(thermique_mw)/sum(production_totale_mw)
                FROM '{COURBE.as_posix()}' WHERE heure_locale BETWEEN 12 AND 13"""
        ).fetchone()[0]
    )
    recul = 100 * (haut - creneau) / haut
    assert recul == pytest.approx(18.5, abs=2), (
        f"recul relatif du thermique jusqu'au créneau de midi = {recul:.0f} % — "
        "l'étude écrit « près d'un cinquième de moins »"
    )


@besoin_courbe
def test_etude_thermique_socle_et_aube(con):
    """Étude/T4 (encadré) : thermique au plus bas en volume au cœur de la nuit, socle
    diurne ~107 MW ; en part, 36 % sur le créneau de midi contre 44 % à l'aube."""
    df = con.execute(
        f"""SELECT heure_locale, avg(thermique_mw) AS mw,
              100*sum(thermique_mw)/sum(production_totale_mw) AS pct
            FROM '{COURBE.as_posix()}' GROUP BY 1"""
    ).df()
    h_min = int(df.loc[df["mw"].idxmin(), "heure_locale"])
    assert h_min in (3, 4), (
        f"minimum de volume thermique à {h_min} h — l'étude écrit « vers 3 ou 4 heures » "
        "(les deux heures sont à 86,5 MW, à un dixième près)"
    )
    socle = df[df["heure_locale"].between(9, 18)]["mw"].mean()
    assert socle == pytest.approx(107, abs=4), (
        f"socle thermique diurne = {socle:.0f} MW — l'étude écrit « environ 107 MW »"
    )
    creneau = float(
        con.execute(
            f"""SELECT 100*sum(thermique_mw)/sum(production_totale_mw)
                FROM '{COURBE.as_posix()}' WHERE heure_locale BETWEEN 12 AND 13"""
        ).fetchone()[0]
    )
    aube = float(df.loc[df["heure_locale"] == 4, "pct"].iloc[0])
    assert round(creneau) == 36 and round(aube) == 44, (
        f"parts thermiques créneau / aube = {creneau:.1f} / {aube:.1f} — l'étude écrit "
        "36 % et 44 %"
    )


@besoin_courbe
def test_t9_hydro_secheresse(con):
    """T9 : d'une année à l'autre, part hydraulique et part thermique varient à l'opposé
    (corrélation forte négative) ; l'année la plus pauvre en hydraulique (2022) est aussi
    celle du thermique le plus haut, et l'amplitude interannuelle du thermique passe la
    dizaine de points. Chiffres publiés au pied de la figure."""
    df = con.execute(
        f"""SELECT annee_locale::INTEGER AS annee,
              100.0*sum(hydraulique_mw)/sum(production_totale_mw) AS hydro,
              100.0*sum(thermique_mw)/sum(production_totale_mw)   AS therm
            FROM '{COURBE.as_posix()}'
            WHERE annee_locale BETWEEN 2019 AND 2024
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
    # Bornes citées en prose (section 4), lues sur cette figure : l'année sèche et
    # l'année arrosée s'opposent sur les deux filières à la fois.
    th_haut, th_bas = round(float(df["therm"].max())), round(float(df["therm"].min()))
    assert (th_haut, th_bas) == (48, 35), (
        f"thermique de {th_bas} à {th_haut} % — la section 4 écrit « 48 % » (2022) et « 35 % » (2023)"
    )
    an_arrosee = int(df.loc[df["hydro"].idxmax(), "annee"])
    assert an_arrosee == int(df.loc[df["therm"].idxmin(), "annee"]) == 2023, (
        f"année la plus arrosée = {an_arrosee}, thermique min = "
        f"{int(df.loc[df['therm'].idxmin(), 'annee'])} — la section 4 écrit « 35 % en 2023, la "
        "plus arrosée »"
    )
