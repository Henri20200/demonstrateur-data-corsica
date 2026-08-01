"""Préparation des données : brut (data/raw) -> analysable (data/processed, Parquet).

DuckDB lit les CSV(.gz) directement, sans les charger en mémoire.
Usage :
    python -m demonstrateur.prepare

Garde-fous (cf. docs/RECONNAISSANCE.md) :
 - mix temps réel : la ligne au bouclage cassé (`total` corrompu) est retirée
   (filtre par le bouclage, robuste au fuseau).
 - courbe Corse : **audit des NULL par colonne**. Une GRANDE filière NULL fait
   ÉCHOUER la préparation — on ne coalesce jamais aveuglément (un `+0` sur le PV ou
   le thermique fabriquerait un faux aplomb). Seule `micro_hydraulique_mw` tolère des
   NULL (absente en 2024) et est coalescée à 0, ce que le bouclage 2024 justifie
   (`production_totale_mw` l'exclut aussi). Un test `ENR >= solaire` verrouille la sortie.
 - météo Corse : les deux sources du sujet air N'ONT PAS le même fuseau — Météo-France
   publie en UTC, le flux LCSQA en heure légale. La conversion se fait ici, une fois, et
   `heure_locale` est le SEUL axe par lequel les deux séries se joignent. S'y ajoutent le
   filtre du code qualité `QT` (pendant de la `validité` de l'air) et le retrait des deux
   journées de bord, tronquées par construction.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

from .config import BUILD_FILE, DATA_PROCESSED, DATA_RAW, MANIFEST_FILE, ROOT
from .provenance import EmpreinteDivergente, empreinte, verifier

MIX = (DATA_RAW / "edf_mix_temps_reel.csv").as_posix()
COURBE = (DATA_RAW / "edf_courbe_charge_horaire.csv").as_posix()
ECRET = (DATA_RAW / "edf_ecretement_corse.csv").as_posix()
AIR = (DATA_RAW / "lcsqa_temps_reel.csv").as_posix()
METEO = (DATA_RAW / "meteo_horaire_corse.csv.gz").as_posix()
ENTSOE_ANNEES = range(2019, 2025)  # fenêtre alignée sur la courbe corse

# Codes qualité Météo-France (H_descriptif_champs.csv, relevé le 01/08/2026). Pendant
# exact de la `validité` du LCSQA. On garde ce qui a passé au moins les contrôles de
# premier niveau ; on écarte ce qui est explicitement mis en doute.
QT_RETENUS = (0, 1, 9)  # 0 protégée (validée par le climatologue), 1 validée, 9 filtrée
QT_ECARTES = (2,)       # 2 douteuse, en cours de vérification

# Codes PSR ENTSO-E -> filières (mêmes libellés que la Corse, pour comparer).
# On agrège les fossiles en « thermique » ; B10 (STEP) en génération -> hydraulique ;
# déchets (B17) avec bioénergies comme le classement EDF. La Sardaigne a du charbon (B05)
# et du gaz de synthèse IGCC (B03, centrale Sarlux), d'où un thermique majoritaire.
PSR_VERS_FILIERE = {
    "B02": "thermique", "B03": "thermique", "B04": "thermique", "B05": "thermique",
    "B06": "thermique", "B07": "thermique", "B08": "thermique",
    "B10": "hydraulique", "B11": "hydraulique", "B12": "hydraulique",
    "B16": "solaire",
    "B18": "eolien", "B19": "eolien",
    "B01": "bioenergies", "B17": "bioenergies",
    "B09": "autre", "B13": "autre", "B14": "autre", "B15": "autre", "B20": "autre",
    "B25": "autre",  # stockage (batteries, décharge) — apparu en 2024, pas d'équivalent EDF
}
_PT_MINUTES = {"PT15M": 15, "PT30M": 30, "PT60M": 60}

# Filières historiques toujours renseignées (leur NULL = incident à signaler, pas à masquer).
GRANDES_FILIERES = [
    "production_totale_mw", "thermique_mw", "hydraulique_mw",
    "photovoltaique_mw", "eolien_mw", "bioenergies_mw", "importations_mw",
]


def dvf_corse_to_parquet(dest: str) -> None:
    """Consolide les fichiers DVF 2A + 2B en un Parquet unique, ventes uniquement."""
    src = (DATA_RAW / "dvf_2*_2024.csv.gz").as_posix()

    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT *
            FROM read_csv_auto('{src}', header = true, union_by_name = true)
            WHERE nature_mutation = 'Vente'
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {Path(dest).name} — {n:,} mutations (ventes)")


def _auditer_null(con, table_expr: str, colonnes: list[str], source: str) -> None:
    """Échoue si une filière censée toujours renseignée contient des NULL.

    Règle (cf. RECONNAISSANCE.md) : un NULL dans un numérateur n'est pas neutre s'il
    reste au dénominateur. On ne coalesce PAS aveuglément une grande filière.
    """
    sel = ", ".join(f'count(*) FILTER (WHERE "{c}" IS NULL) AS "{c}"' for c in colonnes)
    row = con.execute(f"SELECT {sel} FROM {table_expr}").fetchone()
    fautives = {c: n for c, n in zip(colonnes, row) if n}
    if fautives:
        raise ValueError(
            f"{source} : NULL dans une filière toujours attendue {fautives} — trancher "
            "zéro-vrai vs donnée manquante avant de coalescer (cf. docs/RECONNAISSANCE.md)."
        )


def mix_temps_reel_to_parquet(dest: str) -> None:
    """Parquet du mix temps réel Corse (15 min), ligne au bouclage cassé retirée."""
    con = duckdb.connect()
    src = f"read_csv_auto('{MIX}', delim=';', header=true)"
    # `total` corrompu (ligne à −91 MW) -> bouclage cassé ; drop robuste au fuseau.
    propre = (
        f"(SELECT * FROM {src} "
        "WHERE abs(total-(filiere_thermique+filiere_enr_distrib+hydraulique+liaisons)) <= 50)"
    )
    con.execute(
        f"""
        COPY (
          SELECT *,
            extract('hour' FROM timezone('Europe/Paris', "date"))                 AS heure_locale,
            round(100.0*photovoltaique/total, 2)                                  AS part_soleil,
            round(100.0*(photovoltaique+eolien+bioenergies+micro_hydro)/total, 2) AS part_enr_sym
          FROM {propre}
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {Path(dest).name} — {n:,} pas de 15 min (Corse temps réel)")


def courbe_corse_to_parquet(dest: str) -> None:
    """Parquet de la courbe horaire, filtrée Corse, avec ENR distribuée symétrique.

    Colonnes Outre-mer vides (bagasse/geothermie/stockage) et coût (hors périmètre)
    écartées. `micro_hydraulique_mw` gardée brute + coalescée dans l'ENR (cf. audit).
    """
    con = duckdb.connect()
    src = f"read_csv_auto('{COURBE}', delim=';', header=true)"
    # `production_totale_mw > 0` retire 3 lignes à 0 MW (heure fantôme des passages à
    # l'heure d'été 2019, 2020 et 2024) : 52 605 h traitées sur les 52 608 h du brut.
    # Écart documenté (cf. RECONNAISSANCE.md) — c'est le dénominateur de tous les ratios.
    corse = f"(SELECT * FROM {src} WHERE territoire='Corse' AND production_totale_mw > 0)"

    _auditer_null(con, corse, GRANDES_FILIERES, "courbe Corse")  # micro exemptée (doc)

    enr = "(photovoltaique_mw+eolien_mw+bioenergies_mw+coalesce(micro_hydraulique_mw,0))"
    con.execute(
        f"""
        COPY (
          SELECT date_heure, statut,
            extract('hour'  FROM timezone('Europe/Paris', date_heure)) AS heure_locale,
            extract('month' FROM timezone('Europe/Paris', date_heure)) AS mois_local,
            production_totale_mw, thermique_mw, hydraulique_mw, micro_hydraulique_mw,
            photovoltaique_mw, eolien_mw, bioenergies_mw, importations_mw,
            {enr}                                       AS enr_distrib_mw,
            round(100.0*{enr}/production_totale_mw, 2)  AS part_enr_distrib
          FROM {corse}
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    # Garde de sortie : à l'AGRÉGAT (par heure), l'ensemble ENR ne peut passer sous son
    # sous-ensemble solaire — c'est l'invariant qui a révélé le bug NULL 2024. (Au niveau
    # ligne, la production nette nocturne peut être < 0 et le violer légitimement —
    # auxiliaires, convention EDF. Deux périmètres à ne pas confondre : PAR FILIÈRE,
    # c'est fréquent (PV < 0 : 20 429 h, soit 38,8 % ; éolien 13 017 ; bio 4 856 ;
    # micro 2 233) ; l'AGRÉGAT enr_distrib_mw < 0 est rare car les termes se
    # compensent : 2 750 h (5,2 %), part minimale −1,39 %. Sans objet à l'agrégat
    # horaire ; les figures clampent à 0 via greatest().)
    viol = con.execute(
        f"""SELECT count(*) FROM (
              SELECT heure_locale FROM '{dest}'
              GROUP BY heure_locale HAVING sum(enr_distrib_mw) < sum(photovoltaique_mw)
            )"""
    ).fetchone()[0]
    if viol:
        raise ValueError(f"courbe Corse : {viol} heures ENR<solaire (agrégat) — cohérence rompue.")
    n = con.execute(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
    print(f"[ok] {Path(dest).name} — {n:,} heures (Corse 2019-2024) — garde ENR>=solaire OK")


def ecretement_corse_to_parquet(dest: str) -> None:
    """Parquet de l'écrêtement PV (limitations sûreté système), filtré Corse.

    CSV bancal : BOM en tête et lignes à 3 champs avant 2019 (le taux accepté
    n'existe qu'à partir de 2019) — sniffing désactivé, colonnes déclarées,
    null_padding. Audit des NULL : `duree_h` doit être complète (ses zéros sont
    de vrais zéros — mois sans limitation) ; `taux_pct` NULL avant 2019 = donnée
    manquante DOCUMENTÉE, jamais coalescée (cf. règle NULL de RECONNAISSANCE.md).
    """
    con = duckdb.connect()
    src = (
        f"read_csv('{ECRET}', header=false, skip=1, delim=',', auto_detect=false, "
        "null_padding=true, columns={'territoire':'VARCHAR','mois':'VARCHAR',"
        "'duree_h':'DOUBLE','taux_pct':'DOUBLE'})"
    )
    corse = f"(SELECT * FROM {src} WHERE territoire='Corse')"

    _auditer_null(con, corse, ["mois", "duree_h"], "écrêtement Corse")

    con.execute(
        f"""
        COPY (
          SELECT mois, duree_h, taux_pct,
            cast(substr(mois, 1, 4) AS INTEGER) AS annee,
            cast(substr(mois, 6, 2) AS INTEGER) AS mois_cal
          FROM {corse}
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    # Garde : années PLEINES uniquement (12 mois chacune). Une année partielle
    # (ex. millésime en cours ajouté par EDF) fausserait la lecture calendaire de
    # la heatmap — la traiter explicitement le jour venu, pas la laisser passer.
    n, annees = con.execute(
        f"SELECT count(*), count(DISTINCT annee) FROM '{dest}'"
    ).fetchone()
    if n != annees * 12:
        raise ValueError(
            f"écrêtement Corse : {n} mois pour {annees} année(s) — série calendaire "
            "incomplète (année partielle ?) : adapter la heatmap avant de publier."
        )
    print(f"[ok] {Path(dest).name} — {n} mois ({annees} années pleines, Corse) — écrêtement PV")


def _lignes_entsoe_horaires(path) -> list[dict]:
    """Reconstruit la génération horaire (MW) d'un GL_MarketDocument ENTSO-E.

    Trois pièges gérés (validés empiriquement sur IT-Sardinia 2019-2024) :
     - **curveType A03** : les positions manquantes RECONDUISENT la dernière valeur
       (report), y compris du dernier point jusqu'à la fin de la période — jamais un
       zéro. Un remplissage à zéro fabriquerait un mix faux.
     - **direction** : on ne garde que les séries `inBiddingZone_Domain` (génération) ;
       les `outBiddingZone` (pompage STEP, artefacts) sont de la consommation.
     - **résolution mixte** : 2024 mêle PT60M et PT15M (bascule italienne) ; on
       reconstruit au pas natif puis on agrège à l'heure (moyenne des sous-pas).
    Renvoie des lignes {date_heure (UTC), code, mw} déjà agrégées à l'heure.
    """
    root = ET.parse(path).getroot()
    ns = root.tag[1:root.tag.find("}")]

    def q(tag):
        return f"{{{ns}}}{tag}"

    # (heure UTC, code) -> [somme des sous-pas, nombre de sous-pas] pour la moyenne.
    horaire: dict[tuple, list] = {}
    for ts in root.findall(q("TimeSeries")):
        if ts.find(q("inBiddingZone_Domain.mRID")) is None:
            continue  # série OUT = consommation, hors génération
        code = ts.find(q("MktPSRType") + "/" + q("psrType")).text
        for period in ts.findall(q("Period")):
            res = period.find(q("resolution")).text
            pas = _PT_MINUTES.get(res)
            if pas is None:
                raise ValueError(f"{path} : résolution {res!r} non gérée")
            debut = datetime.fromisoformat(
                period.find(q("timeInterval") + "/" + q("start")).text.replace("Z", "+00:00")
            )
            fin = datetime.fromisoformat(
                period.find(q("timeInterval") + "/" + q("end")).text.replace("Z", "+00:00")
            )
            n_pas = int((fin - debut) / timedelta(minutes=pas))
            valeurs = {
                int(p.find(q("position")).text): float(p.find(q("quantity")).text)
                for p in period.findall(q("Point"))
            }
            # Report A03 : on parcourt tous les pas, en gardant la dernière valeur connue.
            derniere = 0.0
            for i in range(1, n_pas + 1):
                if i in valeurs:
                    derniere = valeurs[i]
                instant = debut + timedelta(minutes=pas * (i - 1))
                # UTC naïf (tzinfo retiré) : même convention que la courbe corse, pour
                # que extract('year') reste en UTC et que timezone('Europe/Rome', …)
                # calcule l'heure locale comme pour la Corse (sinon dérive de bord d'année).
                heure = instant.replace(tzinfo=None, minute=0, second=0, microsecond=0)
                acc = horaire.setdefault((heure, code), [0.0, 0])
                acc[0] += derniere
                acc[1] += 1

    return [
        {"date_heure": heure, "code": code, "mw": somme / n}
        for (heure, code), (somme, n) in horaire.items()
    ]


def entsoe_sardaigne_to_parquet(dest: str) -> None:
    """Parquet de la génération sarde par filière (ENTSO-E), miroir de la courbe corse.

    Assemble les 6 fichiers annuels, mappe les codes PSR sur les filières EDF, convertit
    en heure locale (Europe/Rome = Europe/Paris), et écrit un pas horaire avec parts.
    Génération métrée : PAS d'imports (la Sardaigne exporte via SAPEI/SACOI, hors A75).
    """
    lignes = []
    for an in ENTSOE_ANNEES:
        src = DATA_RAW / f"entsoe_sardaigne_{an}.xml"
        if not src.exists():
            raise FileNotFoundError(f"{src} manquant — lancer fetch-data (jeton ENTSO-E requis)")
        lignes.extend(_lignes_entsoe_horaires(src))
    brut = pd.DataFrame(lignes)
    brut["filiere"] = brut["code"].map(PSR_VERS_FILIERE)
    inconnus = sorted(brut.loc[brut["filiere"].isna(), "code"].unique())
    if inconnus:
        raise ValueError(f"codes PSR ENTSO-E non mappés {inconnus} — compléter PSR_VERS_FILIERE")

    con = duckdb.connect()
    con.register("brut", brut)
    con.execute(
        f"""
        COPY (
          WITH large AS (
            SELECT date_heure, filiere, sum(mw) AS mw
            FROM brut GROUP BY 1, 2
          ),
          par_filiere AS (
            SELECT date_heure,
              coalesce(sum(mw) FILTER (WHERE filiere='thermique'), 0)   AS thermique_mw,
              coalesce(sum(mw) FILTER (WHERE filiere='hydraulique'), 0) AS hydraulique_mw,
              coalesce(sum(mw) FILTER (WHERE filiere='solaire'), 0)     AS solaire_mw,
              coalesce(sum(mw) FILTER (WHERE filiere='eolien'), 0)      AS eolien_mw,
              coalesce(sum(mw) FILTER (WHERE filiere='bioenergies'), 0) AS bioenergies_mw,
              coalesce(sum(mw) FILTER (WHERE filiere='autre'), 0)       AS autre_mw
            FROM large GROUP BY 1
          )
          SELECT date_heure,
            extract('year' FROM date_heure)                        AS annee,
            extract('hour' FROM timezone('Europe/Rome', date_heure)) AS heure_locale,
            thermique_mw, hydraulique_mw, solaire_mw, eolien_mw, bioenergies_mw, autre_mw,
            (thermique_mw + hydraulique_mw + solaire_mw + eolien_mw
             + bioenergies_mw + autre_mw)                          AS production_totale_mw
          FROM par_filiere
          WHERE (thermique_mw + hydraulique_mw + solaire_mw + eolien_mw
                 + bioenergies_mw + autre_mw) > 0
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n, a, b = con.execute(
        f"SELECT count(*), min(annee), max(annee) FROM '{dest}'"
    ).fetchone()
    print(f"[ok] {Path(dest).name} — {n:,} heures (Sardaigne {a}-{b}) — génération par filière")


def air_corse_to_parquet(dest: str) -> None:
    """Parquet des mesures d'air corses, extraites du flux E2 national.

    Deux filtres, tous deux tranchés sur le brut et non supposés :

    - **périmètre** `Organisme = 'QUALITAIR CORSE'`. Le brut est national (~48 000
      lignes/jour) et l'île en fait ~960. On retient l'AASQA plutôt qu'un préfixe de
      code de zone : c'est le critère que le producteur maîtrise.
    - **validité > 0**. Audit du 30/07/2026 : les 18 lignes corses à `validité = -1`
      portaient TOUTES une valeur NULL. Il n'y a donc rien à trancher entre zéro-vrai et
      donnée manquante (cf. RECONNAISSANCE.md) — ces lignes ne contiennent aucune mesure.
      Les valeurs 1 et 4 en portent toutes une.

    Horodatage en **heure légale française**, établi le 31/07/2026 : le fichier du jour
    publiait l'heure 19:00 alors qu'il était 20 h 07 locale (18 h 07 UTC) — un horodatage
    UTC aurait été dans le futur. `heure_locale` se lit donc directement, sans conversion.

    Aucune ligne corse = ÉCHEC : si le producteur renomme son organisme, il faut un arrêt
    bruyant, jamais un Parquet vide qui se propagerait en figures muettes.
    """
    con = duckdb.connect()
    src = f"read_csv_auto('{AIR}', delim=';', header=true)"
    corse = f"(SELECT * FROM {src} WHERE \"Organisme\" = 'QUALITAIR CORSE')"
    total, ecartees = con.execute(
        f'SELECT count(*), count(*) FILTER (WHERE "validité" <= 0) FROM {corse}'
    ).fetchone()
    if not total:
        raise ValueError(
            "aucune mesure corse dans le flux E2 — le libellé d'organisme "
            "'QUALITAIR CORSE' a-t-il changé ? (filtre à revoir avant de publier)"
        )
    con.execute(
        f"""
        COPY (
          SELECT "Date de début"                       AS debut,
                 extract('hour' FROM "Date de début")  AS heure_locale,
                 "Zas"                                 AS zone,
                 "code site"                           AS code_site,
                 "nom site"                            AS station,
                 "type d'implantation"                 AS implantation,
                 "type d'influence"                    AS influence,
                 "Polluant"                            AS polluant,
                 "valeur"                              AS valeur,
                 "unité de mesure"                     AS unite,
                 "validité"                            AS validite
          FROM {corse}
          WHERE "validité" > 0
          ORDER BY debut, station, polluant
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )
    n, stations, especes = con.execute(
        f"SELECT count(*), count(DISTINCT station), count(DISTINCT polluant) FROM '{dest}'"
    ).fetchone()
    print(f"[ok] {Path(dest).name} — {n:,} mesures ({stations} stations, {especes} polluants) "
          f"— {ecartees} ligne(s) sans mesure écartée(s) sur {total:,}")


def meteo_corse_to_parquet(dest: str) -> None:
    """Parquet des températures horaires corses (Météo-France, département 20).

    Quatre garde-fous, tous tranchés sur le brut et non supposés :

    - **fuseau.** `AAAAMMJJHH` est en UTC, et c'est PROUVÉ par la structure du fichier
      (01/08/2026) : les deux dimanches de changement d'heure de 2025 portent 24 heures
      chacun (30/03 et 26/10), là où en heure légale ils en comptent 23 et 25. Seule une
      échelle à décalage fixe donne 24 partout. `heure_locale` est donc CONVERTIE ici,
      alors que celle d'`air_corse` se lit directement : le flux LCSQA, lui, publie en
      heure légale. Une erreur de fuseau ne casserait rien — elle décalerait le pic de
      deux heures, et le titre-affirmation n° 4 du BRIEF_AIR (« le pire moment pour un
      effort en plein air ») deviendrait un conseil faux, énoncé avec aplomb.

    - **clé.** `(num_poste, date_heure_utc)` est unique ; `(num_poste,
      date_heure_locale)` ne l'est PAS. Le dimanche du retour à l'heure d'hiver, 00 h et
      01 h UTC donnent toutes deux 02 h locale — 54 couples en double, un par poste, une
      fois l'an. Ce n'est pas une anomalie (cette heure a bien lieu deux fois) mais un
      piège de jointure : l'axe UTC est la clé, l'axe local n'est qu'une étiquette de
      lecture. L'unicité est vérifiée en sortie.

    - **qualité.** `QT` est le pendant de la `validité` du LCSQA. On garde 0 (protégée),
      1 (validée) et 9 (filtrée) ; on écarte 2 (douteuse, en cours de vérification). Un
      code inconnu fait ÉCHOUER : pas de tri silencieux sur une nomenclature qui bouge.

    - **journées de bord.** Les deux extrémités sont tronquées PAR CONSTRUCTION : le
      décalage UTC -> heure légale ampute la première (23 h le 01/01/2025) et le fichier
      s'arrête aux petites heures du jour de publication (6 h le 31/07/2026). Une
      « journée » de six heures fabriquerait un faux maximum journalier. Les deux dates
      de bord sont donc retirées, puis TOUTE la série est vérifiée — pas seulement les
      nouvelles bornes : un trou de collecte au milieu produirait le même faux maximum,
      et rien ne dit qu'il se logerait aux extrémités. Le seuil est 23 heures et non 24,
      parce que le dimanche du passage à l'heure d'été n'en compte légitimement que 23.

    Lecture en `all_varchar` : le fichier porte ~200 colonnes dont on en lit 6. Laisser le
    sniffer typer les 194 autres, c'est autant d'occasions qu'une valeur inattendue dans
    une colonne INUTILISÉE fasse tomber le build. Les colonnes utiles, elles, sont
    converties explicitement et échouent bruyamment si leur format change. Sortie vérifiée
    identique à la lecture typée (01/08/2026).

    Les 57 postes sont tous conservés — 2 ne publient jamais de température et sortent
    d'eux-mêmes du filtre. L'appariement station d'air <-> poste météo est une décision de
    figure (cf. docs/BRIEF_AIR.md), pas de préparation.
    """
    con = duckdb.connect()
    con.execute(
        f"""
        CREATE TEMP TABLE meteo AS
        SELECT NUM_POSTE                          AS num_poste,
               NOM_USUEL                          AS poste,
               CAST(LAT  AS DOUBLE)               AS lat,
               CAST(LON  AS DOUBLE)               AS lon,
               CAST(ALTI AS INTEGER)              AS alti,
               strptime(AAAAMMJJHH, '%Y%m%d%H')   AS date_heure_utc,
               CAST(T    AS DOUBLE)               AS temperature_c,
               CAST(QT   AS INTEGER)              AS qt
        FROM read_csv('{METEO}', delim=';', header=true, all_varchar=true)
        WHERE T IS NOT NULL
        """
    )
    if not con.execute("SELECT count(*) FROM meteo").fetchone()[0]:
        raise ValueError(
            "météo Corse : aucune température dans le brut — la structure du fichier du "
            "département 20 a-t-elle changé ? (colonne T vide de bout en bout)"
        )
    # `timezone('UTC', ts)` interprète l'horodatage naïf comme un instant UTC ; le
    # `timezone('Europe/Paris', …)` externe le rend en heure légale naïve, convention de
    # toutes les autres sorties du dépôt.
    con.execute(
        """
        CREATE TEMP VIEW meteo_loc AS
        SELECT *, timezone('Europe/Paris', timezone('UTC', date_heure_utc)) AS date_heure_locale
        FROM meteo
        """
    )

    codes = {r[0] for r in con.execute("SELECT DISTINCT qt FROM meteo").fetchall()}
    inconnus = sorted(codes - set(QT_RETENUS) - set(QT_ECARTES))
    if inconnus:
        raise ValueError(
            f"météo Corse : code(s) qualité QT inconnu(s) {inconnus} — nomenclature "
            "Météo-France modifiée ? Trancher garder/écarter avant de publier."
        )

    premiere, derniere = con.execute(
        "SELECT min(CAST(date_heure_locale AS DATE)), max(CAST(date_heure_locale AS DATE)) "
        "FROM meteo_loc"
    ).fetchone()
    retenus = ", ".join(str(q) for q in QT_RETENUS)
    con.execute(
        f"""
        COPY (
          SELECT num_poste, poste, lat, lon, alti,
                 date_heure_utc,
                 date_heure_locale,
                 CAST(date_heure_locale AS DATE)          AS date_locale,
                 extract('hour' FROM date_heure_locale)   AS heure_locale,
                 temperature_c, qt
          FROM meteo_loc
          WHERE qt IN ({retenus})
            AND CAST(date_heure_locale AS DATE) > DATE '{premiere}'
            AND CAST(date_heure_locale AS DATE) < DATE '{derniere}'
          ORDER BY date_heure_utc, num_poste
        ) TO '{dest}' (FORMAT PARQUET)
        """
    )

    # Garde de sortie 1 : JAMAIS de Parquet vide. Sans elle, un brut réduit à une ou deux
    # journées (producteur en panne, fichier tronqué à la bascule de millésime) sortirait
    # à zéro ligne, et la garde de bords ci-dessous passerait sans rien dire — min() et
    # max() valant NULL, elle ne trouverait aucune borne à examiner.
    n, postes, d1, d2 = con.execute(
        f"SELECT count(*), count(DISTINCT num_poste), min(date_locale), max(date_locale) "
        f"FROM '{dest}'"
    ).fetchone()
    if not n:
        raise ValueError(
            f"météo Corse : sortie VIDE — le brut ne couvre que {premiere} .. {derniere}, "
            "dont il ne reste rien après retrait des deux journées de bord. Publier un "
            "Parquet vide propagerait des figures muettes."
        )

    # Garde de sortie 2 : AUCUNE journée tronquée, sur TOUTE la série et pas seulement aux
    # bornes — un maximum journalier calculé sur un fragment de journée serait faux sans
    # rien signaler, où qu'il tombe. Seuil à 23 h et non 24 : le dimanche du passage à
    # l'heure d'été n'en compte légitimement que 23. Les deux diagnostics sont distincts
    # et appellent des gestes différents, d'où le message qui les sépare : une borne
    # creuse dit que la troncature du producteur dépasse un jour (le retrait est à
    # élargir), une journée creuse au milieu dit qu'il manque de la donnée.
    creuses = con.execute(
        f"""SELECT CAST(date_locale AS VARCHAR), count(DISTINCT heure_locale) AS h
            FROM '{dest}' GROUP BY 1 HAVING h < 23 ORDER BY 1"""
    ).fetchall()
    if creuses:
        aux_bords = [c for c in creuses if c[0] in {str(d1), str(d2)}]
        au_milieu = [c for c in creuses if c not in aux_bords]
        details = []
        if aux_bords:
            details.append(
                f"aux bornes {aux_bords} — la troncature du producteur dépasse un jour "
                f"(dates extrêmes déjà retirées : {premiere}, {derniere}), élargir le retrait"
            )
        if au_milieu:
            details.append(
                f"{len(au_milieu)} au milieu de la série, dont {au_milieu[:5]} — trou de "
                "collecte chez le producteur, à trancher avant de publier"
            )
        raise ValueError("météo Corse : journée(s) incomplète(s) : " + " ; ".join(details))

    # Garde de sortie 3 : unicité sur l'axe UTC. Un doublon (poste, heure) doublerait
    # silencieusement le poids de cette heure dans toute moyenne ou tout maximum.
    doublons = con.execute(
        f"""SELECT count(*) FROM (SELECT num_poste, date_heure_utc FROM '{dest}'
            GROUP BY 1, 2 HAVING count(*) > 1)"""
    ).fetchone()[0]
    if doublons:
        raise ValueError(
            f"météo Corse : {doublons} couple(s) (poste, heure UTC) en double — la clé "
            "n'est plus unique, toute moyenne ou somme en serait faussée."
        )

    # Compté sur la MÊME fenêtre que la sortie : un décompte pris sur tout le brut
    # inclurait les journées de bord, que la sortie ne contient pas.
    ecartees = con.execute(
        f"""SELECT count(*) FROM meteo_loc
            WHERE qt IN ({', '.join(str(q) for q in QT_ECARTES)})
              AND CAST(date_heure_locale AS DATE) > DATE '{premiere}'
              AND CAST(date_heure_locale AS DATE) < DATE '{derniere}'"""
    ).fetchone()[0]
    # Pas de flèche ni d'autre caractère hors cp1252 : la console Windows du dépôt ne
    # sait pas les encoder, et un message de succès ne doit jamais faire tomber un build.
    print(f"[ok] {Path(dest).name} — {n:,} heures ({postes} postes, du {d1} au {d2}) "
          f"— {ecartees} douteuse(s) écartée(s), bords tronqués retirés")


# Plan de construction : chaque sortie Parquet, sa fonction de build et les sources brutes
# qui la nourrissent. Sert à la fois à VÉRIFIER les bons bruts (prepare ne bâtit QUE depuis
# des octets certifiés — AUD-01) et à écrire une lignée qui relie chaque sortie à ses entrées
# et à sa propre empreinte. La Sardaigne (ENTSO-E) n'est ajoutée que si ses 6 fichiers annuels
# sont présents (jeton requis pour les avoir).
_SORTIES_FIXES = [
    ("dvf_corse_2024.parquet", dvf_corse_to_parquet, ["dvf_2a_2024", "dvf_2b_2024"]),
    ("edf_mix_corse.parquet", mix_temps_reel_to_parquet, ["edf_mix_temps_reel"]),
    ("edf_courbe_corse.parquet", courbe_corse_to_parquet, ["edf_courbe_charge_horaire"]),
    ("edf_ecretement_corse.parquet", ecretement_corse_to_parquet, ["edf_ecretement_corse"]),
]


def _plan_construction(sardaigne_ok: bool, air_ok: bool = False,
                       meteo_ok: bool = False) -> list:
    plan = list(_SORTIES_FIXES)
    if sardaigne_ok:
        plan.append((
            "entsoe_sardaigne.parquet", entsoe_sardaigne_to_parquet,
            [f"entsoe_sardaigne_{an}" for an in ENTSOE_ANNEES],
        ))
    if air_ok:
        plan.append(("air_corse.parquet", air_corse_to_parquet, ["lcsqa_temps_reel"]))
    if meteo_ok:
        plan.append(("meteo_corse.parquet", meteo_corse_to_parquet, ["meteo_horaire_corse"]))
    return plan


def _verifier_bruts(source_ids: list[str]) -> dict:
    """Vérifie chaque brut contre son empreinte de manifeste avant toute construction.

    Renvoie {source_id: {sha256, date_collecte, filename}} (les entrées certifiées, qui
    datent ensuite les figures). Lève EmpreinteDivergente si un brut a dérivé sous le
    manifeste : la préparation ne part jamais d'une donnée non certifiée.
    """
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    entrees = {}
    for sid in source_ids:
        entry = manifest.get(sid)
        if entry is None:
            raise ValueError(f"{sid} absent du manifeste — lancer fetch-data d'abord.")
        chemin = DATA_RAW / entry["filename"]
        if not chemin.exists():
            raise FileNotFoundError(f"{chemin} manquant — lancer fetch-data d'abord.")
        sha = verifier(chemin, entry)  # lève si le brut a dérivé sous le manifeste
        entrees[sid] = {
            "sha256": sha,
            "date_collecte": entry["date_collecte"],
            "filename": entry["filename"],
        }
    return entrees


def construire(plan: list, entrees: dict) -> dict:
    """Construit chaque sortie en zone de staging puis bascule d'un bloc (atomicité).

    Un échec en cours de route laisse les sorties précédentes ET l'ancienne lignée
    INTACTES — rien n'est publié à moitié : chaque Parquet est écrit dans un dossier
    `.staging`, haché, et seulement si TOUTES les sorties réussissent, déplacé vers
    data/processed. Renvoie {nom_parquet: {sha256, sources: [source_id, …]}}.
    """
    staging = DATA_PROCESSED / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    sorties = {}
    try:
        for nom, build, sids in plan:
            tmp = staging / nom
            build(tmp.as_posix())
            sorties[nom] = {"sha256": empreinte(tmp, {}), "sources": sids}
        # Toutes construites : bascule (la seule fenêtre d'incohérence, minime, est ici ;
        # une sortie déjà basculée mais lignée pas encore écrite serait DÉTECTÉE par
        # verifier_sorties, jamais publiée en silence).
        for nom in sorties:
            (staging / nom).replace(DATA_PROCESSED / nom)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return sorties


def verifier_sorties() -> dict:
    """Vérifie que chaque Parquet sur disque correspond à l'empreinte de la lignée de build.

    Garde-fou de publication (AUD-01) : une sortie altérée après la préparation est
    refusée (EmpreinteDivergente). À appeler avant de publier (ex. en tête des figures).
    Renvoie la lignée.
    """
    build = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
    for nom, info in build.get("sorties", {}).items():
        chemin = DATA_PROCESSED / nom
        if not chemin.exists():
            raise FileNotFoundError(f"sortie {nom} manquante — relancer prepare.")
        obtenue = empreinte(chemin, {})
        if obtenue != info.get("sha256"):
            raise EmpreinteDivergente(
                f"{nom} : sortie altérée depuis la préparation (empreinte {obtenue[:12]}… "
                f"ne correspond pas à la lignée {(info.get('sha256') or '—')[:12]}…) — "
                "publication refusée."
            )
    return build


def _commit_courant() -> dict:
    """HEAD git + état de l'arbre, pour relier le build au code qui l'a produit (best-effort)."""
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        etat = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        return {"commit": rev.stdout.strip(), "arbre_modifie": bool(etat.stdout.strip())}
    except Exception:  # noqa: BLE001 — git absent ou hors dépôt : la lignée reste utile
        return {"commit": "inconnu", "arbre_modifie": None}


def _ecrire_lignee(entrees: dict, sorties: dict) -> None:
    """Écrit data/processed/_build.json : par sortie ses sources + son empreinte, plus le
    commit et l'horodatage exact. Écriture atomique (tmp puis remplacement)."""
    contenu = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **_commit_courant(),
        "sources": entrees,
        "sorties": sorties,
    }
    tmp = BUILD_FILE.with_name(BUILD_FILE.name + ".tmp")
    tmp.write_text(json.dumps(contenu, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(BUILD_FILE)
    print(f"[ok] {BUILD_FILE.name} — lignée : {len(sorties)} sorties, {len(entrees)} sources")


def main() -> int:
    # Garde-fou AUD-01 : on VÉRIFIE tous les bruts AVANT de construire, on construit en
    # staging et on bascule d'un bloc, puis on écrit la lignée sortie -> entrées.
    sardaigne_ok = all((DATA_RAW / f"entsoe_sardaigne_{an}.xml").exists() for an in ENTSOE_ANNEES)
    air_ok = Path(AIR).exists()
    meteo_ok = Path(METEO).exists()
    plan = _plan_construction(sardaigne_ok, air_ok, meteo_ok)
    source_ids = [sid for _, _, sids in plan for sid in sids]

    entrees = _verifier_bruts(source_ids)
    sorties = construire(plan, entrees)
    if not sardaigne_ok:
        print("[=] entsoe_sardaigne : fichiers annuels absents (jeton ENTSO-E ?) — étape sautée.")
    if not air_ok:
        print("[=] lcsqa_temps_reel : brut absent — étape air sautée (lancer fetch-data).")
    if not meteo_ok:
        print("[=] meteo_horaire_corse : brut absent — étape météo sautée (lancer fetch-data).")
    _ecrire_lignee(entrees, sorties)

    print("\nPréparation terminée : data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
