"""Construit les 5 visuels du sujet AIR depuis data/processed, exporte outputs/*.html.

Un visuel par titre-affirmation du BRIEF_AIR. Usage :
    python -m demonstrateur.figures_air

Périmètre commun à toutes les figures, et écrit sur chacune : **étés 2020-2025**
(juin-juillet-août), **stations de fond**, **maximums journaliers réglementairement
valides**. Ce périmètre unique n'est pas un confort de code — c'est ce qui autorise à lire
deux chiffres de deux figures l'un à côté de l'autre. Une figure qui en sort le dit dans
son sous-titre.

Deux règles de rédaction héritées du brief, et qui se voient dans les libellés :
 - **association, jamais causalité** : « les jours à 30 °C portent X de plus », et non
   « la chaleur ajoute X » ;
 - **la figure nomme le POSTE météo**, jamais la commune de la station d'air : le
   thermomètre de Venaco est à Vivario, dix kilomètres plus loin et cent vingt mètres
   plus haut.
"""

from __future__ import annotations

import sys

import duckdb
import plotly.graph_objects as go

from .config import DATA_PROCESSED
from .prepare import verifier_sorties
from .viz import AIR_AZOTE, AIR_OZONE, PALETTE, SANS, date_collecte, export_html

SERIE = (DATA_PROCESSED / "air_serie.parquet").as_posix()
MDA8 = (DATA_PROCESSED / "air_o3_mda8.parquet").as_posix()
CROISE = (DATA_PROCESSED / "air_temperature_jour.parquet").as_posix()

# Mention courte : « rapportées par le LCSQA/Ineris » en toutes lettres portait la
# première ligne du pied au-delà de la largeur de la page, où elle se faisait rogner.
SRC_AIR = "Agence européenne pour l'environnement — mesures Qualitair Corse (LCSQA/Ineris)"
# Coupure EXPLICITE avant la seconde source : le pied de figure ne replie pas le texte
# (annotation Plotly), et la mention cumulée dépassait la largeur en iframe étroite.
SRC_AIR_METEO = (SRC_AIR + "<br>Températures : Météo-France")

# Seuils réglementaires (art. R221-1 du code de l'environnement, vérifié le 01/08/2026).
# Ils ne comptent PAS la même chose et ne se mêlent jamais dans une même lecture :
# l'objectif de qualité porte sur le maximum journalier de la moyenne sur 8 heures,
# le seuil d'information sur une moyenne HORAIRE.
OBJECTIF_QUALITE = 120  # µg/m³, maximum journalier de la moyenne sur 8 h
SEUIL_INFORMATION = 180  # µg/m³, moyenne horaire

ETES = "extract('month' FROM date_locale) IN (6, 7, 8)"
# Bornes de la fenêtre d'étude, écrites UNE fois : `ANNEES` en dérive et `actualite_air`
# s'en sert pour savoir ce qui tombe HORS d'elle. Tant que la borne haute ne vivait que
# dans une chaîne SQL, tout encart d'actualité aurait dû la recopier — et aurait dérivé le
# jour où la fenêtre bougerait. Elles ne bougent PAS avec le calendrier : passer l'analyse
# à 2020-2026 est une décision éditoriale à revalider, jamais un effet de l'année courante.
AN_DEBUT, AN_FIN = 2020, 2025
ANNEES = f"extract('year' FROM date_locale) BETWEEN {AN_DEBUT} AND {AN_FIN}"
# Périmètre de A3 écrit UNE fois, parce que le nombre de stations annoncé au lecteur doit
# sortir du filtre qui trace les courbes. Tant que ce nombre était une constante, il a
# annoncé cinq stations là où le filtre en retient quatre.
OU_A3 = f"influence = 'Fond' AND station <> 'VENACO' AND {ETES} AND {ANNEES}"
# Périmètre de A1 (24/08/2026), plus court d'une station que le périmètre commun.
# A1 compte des JOURNÉES : la longueur d'une barre y est l'affirmation, et une barre ne
# se compare qu'à dénominateur comparable. Ajaccio Confina 2 est ouverte depuis le
# 31/01/2024 — 180 journées d'été mesurées, contre 520 à 544 pour les quatre autres. Ses
# 4 dépassements la plaçaient donc SOUS les 8 de Canetto, quand sur la fenêtre où les
# cinq stations existent toutes (2024-2025) elle dépasse quatre fois plus souvent que
# lui. La figure classait deux stations à l'envers. Écrire « 4 sur 180 » à côté de la
# barre n'y aurait rien changé : c'est la longueur qu'on lit, pas l'étiquette.
# Elle reste dans A4, qui compte en PART des journées mesurées — là, une fenêtre courte
# ne fausse plus la comparaison, c'est même la raison d'être de cette figure-là.
RECENTE = "AJACCIO CONFINA 2"
OU_A1 = (f"valide AND {ETES} AND {ANNEES} AND influence = 'Fond' "
         f"AND station <> '{RECENTE}'")
# Périmètre dit en langue courante (04/08/2026) : « stations de fond, journées
# réglementairement valides » est exact mais illisible pour qui n'est pas du métier — or
# cette ligne est la SEULE que tous les lecteurs voient, sur les cinq figures. Renvoyer
# le non-initié au mini-dictionnaire, en bas de page, revient à parier qu'il ira le lire :
# la ligne doit se suffire. Le détail réglementaire vit dans la note méthodologique.
PERIMETRE = ("Six étés de mesures — 2020 à 2025, de juin à août — sur les stations de "
             "l'île installées loin des routes.")

# Titre d'axe : 17 px contre 19 au template. Long et centré sur la hauteur du tracé, un
# titre vertical monte jusque dans le sous-titre de la figure.
AXE = dict(family=SANS, size=17)

# A2 porte un titre d'axe horizontal ET une note de trois lignes : son pied descend plus
# bas que le défaut, pour que le graphique et le texte ne se touchent pas.
PIED_A2 = -105


def _con():
    return duckdb.connect()


def _sous_titre(ligne: str) -> str:
    return f"{ligne}<br>{PERIMETRE}"


def stations_a3() -> list[str]:
    """Stations que A3 compare : celles où les DEUX polluants sont mesurés."""
    return [s for (s,) in _con().execute(f"""
        SELECT station FROM '{SERIE}' WHERE {OU_A3} GROUP BY 1
        HAVING count(*) FILTER (WHERE polluant = 'O3') > 0
           AND count(*) FILTER (WHERE polluant = 'NO2') > 0
        ORDER BY 1
    """).fetchall()]


# --- L'implantation : la nomenclature du producteur, et rien au-dessus -------
# TROIS NIVEAUX, dont deux seulement existent. Le producteur publie une INFLUENCE (Fond,
# Trafic, Industrielle) — c'est le filtre du périmètre commun, contrôlé contre le flux
# LCSQA temps réel (`tests/test_stations_air.py`) — et une IMPLANTATION en nomenclature
# LCSQA : Urbaine, Périurbaine, Rurale régionale pour nos six stations. Les figures s'en
# tiennent désormais à ces mots-là.
# Le troisième niveau a été SUPPRIMÉ le 29/08/2026. « Ville » et « campagne » n'étaient
# d'aucun référentiel : ils fusionnaient Urbaine et Périurbaine sous un nom à nous, ce qui
# faisait une nomenclature de plus sans que l'analyse la demande — et laissait entendre
# qu'elle était officielle. Là où une phrase désigne plusieurs catégories, elle les
# ÉNUMÈRE (« urbaines ou périurbaines ») plutôt que de leur inventer un nom commun.
# Autre défaut au passage : le milieu se lisait dans le NOM de la station
# (`'campagne' if station == 'VENACO'`), recopié dans A1 et dans A4. Une station reclassée
# par son producteur aurait gardé son mot.
IMPLANTATIONS = ("Urbaine", "Périurbaine", "Rurale régionale")


def adjectif(implantation: str, pluriel: bool = False, famille: bool = False) -> str:
    """L'implantation du producteur, telle qu'elle s'écrit dans une phrase. Inconnue = arrêt.

    `famille` n'en garde que le PREMIER mot — « rurale régionale » devient « rurale ». Ce
    n'est pas un raccourci de confort : le second mot de la nomenclature dit l'échelle de
    représentativité de la station (proche, régionale, nationale), pas la nature du lieu.
    Une phrase qui oppose des milieux n'a que faire de l'échelle ; la barre de la station,
    elle, porte la catégorie entière, où la précision ne coûte rien.

    La Corse ne présente que trois des catégories de la nomenclature. Le jour où une
    quatrième arrive, la figure s'arrête : l'accorder, l'énumérer et relire le texte
    publié est une décision de rédaction, elle ne se déduit pas.
    """
    if implantation not in IMPLANTATIONS:
        raise ValueError(
            f"implantation « {implantation} » hors nomenclature connue ({list(IMPLANTATIONS)}) "
            "— l'inscrire ICI et relire le texte des figures, qui énumère les catégories."
        )
    mots = implantation.lower().split()[:1] if famille else implantation.lower().split()
    return " ".join(f"{m}s" for m in mots) if pluriel else " ".join(mots)


def enumeration(implantations, pluriel: bool = True, famille: bool = False) -> str:
    """« urbaines ou périurbaines » : les catégories présentes, dans l'ordre du producteur.

    C'est ce qui remplace le mot-valise : une phrase qui désigne plusieurs catégories les
    nomme toutes. Elle s'allonge un peu, et elle cesse d'inventer un référentiel. En
    `famille`, deux catégories d'une même famille n'en font qu'une — « rurale proche » et
    « rurale régionale » se diraient « rurales », pas deux fois.
    """
    presentes = {adjectif(i, famille=famille) for i in implantations}
    return " ou ".join(dict.fromkeys(
        adjectif(i, pluriel, famille) for i in IMPLANTATIONS
        if adjectif(i, famille=famille) in presentes))


def est_rurale(implantation: str) -> bool:
    """A4 oppose la station RURALE aux autres — le contraste se lit dans la nomenclature.

    Le producteur préfixe « Rurale » ses trois catégories rurales (proche, régionale,
    nationale) ; la Corse n'en a qu'une. Lire le préfixe n'invente rien, et surtout ne
    dépend pas du nom de la station.
    """
    return adjectif(implantation).startswith("rurale")


def libelles(stations, implantations) -> list[str]:
    """Libellés de barres, communs à A1 et A4 : mêmes stations, mêmes mots.

    Les deux figures se suivent dans la page — une station ne peut pas s'y appeler de deux
    façons, ni y changer d'implantation. Casse de phrase plutôt que capitales de fichier :
    ce sont des lieux.
    """
    return [f"{s.title()} <i>({adjectif(i)})</i>" for s, i in zip(stations, implantations)]


def perimetre_a4():
    """Le périmètre d'A4 calculé UNE fois : par station, son implantation et son taux.

    Une seule structure, trois rendus — le sous-titre y compte ses stations, la figure y
    prend ses barres, son encart et ses libellés. Le sous-titre était une CONSTANTE
    (« une station de campagne, quatre de ville ») pendant que l'encart de la même figure
    dérivait son `len(urbaines)` de la donnée : deux décomptes indépendants du même
    périmètre, libres de se contredire sans que rien ne le dise.
    """
    return _con().execute(f"""
        SELECT station, implantation,
               100.0 * count(*) FILTER (WHERE mda8 > {OBJECTIF_QUALITE}) / count(*) AS taux,
               count(*) AS jours
        FROM '{MDA8}'
        WHERE valide AND influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1, 2 ORDER BY 3
    """).df()


def contraste_a4() -> dict:
    """Le contraste qu'A4 publie, compté UNE fois — la figure et la note y puisent.

    Même raison que `perimetre_a4`, un cran plus haut : ce n'est plus le périmètre qui
    vivait à deux endroits, c'est la CONCLUSION. Le 29/08/2026, « c'est à la campagne
    qu'on en mesure le plus » a été jugé faux — Bastia Montesoro dépasse 15,1 % de ses
    journées contre 10,4 % à Venaco — puis réécrit dans le titre d'A4 et dans l'encadré
    de la page. La note méthodologique, elle, a continué de publier le superlatif : la
    correction s'était arrêtée où s'arrêtaient les verrous, et c'est la note — la caution
    du sérieux — qui a porté la version fausse pendant que la page portait la juste.
    Ce qui se compte ici ne peut plus se contredire d'un fichier à l'autre.

    Rend la station rurale, les autres, et le nombre de celles qu'elle devance.
    """
    df = perimetre_a4()
    rurales = df.loc[[est_rurale(i) for i in df["implantation"]]]
    # Le titre NOMME la station rurale (« À Venaco… ») : il n'a de sens que s'il n'y en a
    # qu'une. Deux, et c'est le titre qui est faux, pas la figure — d'où l'arrêt, plutôt
    # qu'un `iloc[0]` qui en choisirait une au hasard.
    if len(rurales) != 1:
        raise ValueError(
            f"A4 : {len(rurales)} station(s) rurale(s) ({list(rurales['station'])}) — "
            "le titre n'en nomme qu'une. À réécrire avant de publier."
        )
    rurale = rurales["station"].iloc[0]
    taux_rural = float(rurales["taux"].iloc[0])
    autres = df.loc[[not est_rurale(i) for i in df["implantation"]]]
    devancees = int((autres["taux"] < taux_rural).sum())
    # Le titre se compte, donc il ne peut plus mentir. Cette garde protège désormais ce
    # qui l'entoure : la page introduit la figure en disant que l'ozone « s'accumule loin
    # des moteurs », la note méthodologique le redit à sa façon, et A4 n'en est la preuve
    # que tant que la station rurale devance la MAJORITÉ des autres. Exiger la première
    # place serait plus strict que ce qui est publié, et ce serait déjà tombé : Bastia
    # Montesoro dépasse plus souvent que Venaco.
    if devancees * 2 <= len(autres):
        raise ValueError(
            f"A4 : {rurale} ne devance que {devancees} station(s) non rurale(s) sur "
            f"{len(autres)} — la figure ne soutient plus ni la phrase qui l'introduit "
            "(« il peut s'accumuler loin du trafic routier »), ni l'encadré qui la conclut "
            "(« plus souvent que la majorité »), ni la note méthodologique. À rejuger "
            "avant de publier."
        )
    return dict(df=df, rurale=rurale, autres=autres, devancees=devancees,
                implantations=enumeration(autres["implantation"]))


def actualite_air() -> dict | None:
    """Le millésime le plus récent mesuré HORS de la fenêtre d'étude, ou None.

    Deux couches, et elles ne se mélangent jamais : l'étude de référence est figée sur
    2020-2025 — ses cinq figures, ses conclusions, ses verrous — pendant que cet encart
    dit seulement où en est l'année la plus récente. Il ne raisonne donc ni sur « 2026 »
    ni sur l'année du calendrier, mais sur la dernière année PRÉSENTE DANS LES DONNÉES
    au-delà de `AN_FIN` : début 2027, tant qu'aucun été 2027 n'est mesuré, il continue
    d'afficher 2026 plutôt que de se vider parce que la date a changé. C'est ce qui
    évite de reposer le problème de la fenêtre figée à chaque printemps.

    Le décompte est en journées CALENDAIRES — celles où au moins une station de fond
    dépasse l'objectif de qualité — là où A1 compte des journées-station. Les deux
    nombres diffèrent d'un facteur deux : « l'été compte N journées » ne peut pas
    désigner un cumul sur plusieurs stations sans se lire comme une erreur.

    Rend l'année, le décompte, la dernière journée mesurée et le nombre de journées
    d'été mesurées — jamais un jugement : ce millésime est incomplet et révisable, et il
    ne sert pas de point de comparaison aux six étés de l'étude.
    """
    con = _con()
    an = con.execute(f"""
        SELECT max(extract('year' FROM date_locale)) FROM '{MDA8}'
        WHERE valide AND {ETES} AND influence = 'Fond'
          AND extract('year' FROM date_locale) > {AN_FIN}
    """).fetchone()[0]
    if an is None:
        return None
    jours, mesurees, arret = con.execute(f"""
        SELECT count(DISTINCT date_locale) FILTER (WHERE mda8 > {OBJECTIF_QUALITE}),
               count(DISTINCT date_locale),
               max(date_locale)
        FROM '{MDA8}'
        WHERE valide AND {ETES} AND influence = 'Fond'
          AND extract('year' FROM date_locale) = {int(an)}
    """).fetchone()
    return dict(annee=int(an), jours=int(jours), mesurees=int(mesurees), arret=arret)


# Noms de mois écrits ici et non tirés de `strftime("%B")` : celui-ci suit la locale du
# système, qui n'est pas la même sur ce poste et sur le runner — la page publierait
# « August » un jour sur deux sans que rien n'échoue.
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre")


def phrase_actualite_courte() -> str:
    """La même actualité, pour la PAGE, qui vit sous le plafond de lecture du brief.

    La page est à 682 mots sur les 700 que le brief autorise : l'encart complet ne tient
    pas, et le plafond ne se relève pas pour laisser passer un ajout — ce serait
    neutraliser un critère de « fini ». Ce qui est sacrifié, ce sont les mots de liaison,
    jamais le périmètre : « dans au moins une station de fond » reste, parce que le même
    jeu produit 71 journées-station contre 33 journées calendaires. Sans lui, le chiffre
    est ambigu — et c'est précisément ce sur quoi l'étude se défend.

    Le hors-périmètre, lui, est porté par l'intitulé du bloc et non répété ici.
    """
    a = actualite_air()
    if a is None:
        return ""
    return (f"Au {a['arret'].day} {MOIS[a['arret'].month - 1]}, {a['jours']} journées "
            f"{a['annee']} dépassent {OBJECTIF_QUALITE} µg/m³ dans au moins une station "
            f"de fond — données provisoires.")


def phrase_actualite() -> str:
    """La phrase de l'encart, écrite UNE fois pour la page ET pour la note.

    La leçon de `contraste_a4` appliquée d'avance : deux formulations d'un même chiffre
    finissent par diverger, et c'est la note — la caution du sérieux — qui porte alors la
    version périmée. Le risque est ici plus grand encore, le chiffre changeant à chaque
    passage du cron, par révision rétroactive du flux comme par arrivée de journées.

    L'ordre des propositions est délibéré : le statut provisoire et le hors-périmètre
    sont dits DANS la même phrase que le chiffre, pas dans une note de bas de page qu'on
    peut ne pas lire.
    """
    a = actualite_air()
    if a is None:
        return ""
    return (f"Au {a['arret']:%d/%m/%Y}, l'été {a['annee']} compte {a['jours']} journées "
            f"où au moins une station de fond a dépassé l'objectif de qualité, sur "
            f"{a['mesurees']} journées mesurées. Données provisoires, encore révisables "
            f"par leurs producteurs : cet été n'entre pas dans la fenêtre d'analyse "
            f"{AN_DEBUT}-{AN_FIN}.")


# Sous-titres et notes DÉFINIS UNE FOIS et consommés à la fois par `main()` (fichiers
# individuels) et par `page_air` (page assemblée). Ils étaient recopiés dans les deux
# modules : toute correction n'était appliquée que d'un côté, et les deux versions d'une
# même figure se mettaient à raconter des choses différentes.
def st_a1() -> str:
    """Sous-titre d'A1 — une fonction, comme `st_a3()`, et pour deux raisons.

    A1 sort du périmètre commun (une station de fond de moins, cf. `OU_A1`), et la règle
    du module veut qu'une figure qui en sort le dise ICI, pas seulement en pied : le
    sous-titre se lit AVEC le titre, le pied se lit après — or c'est en lisant le titre
    qu'on décide ce que la figure compare. Et ce qu'il annonce se compte dans la donnée,
    sans quoi l'annonce survivrait à ce qu'elle décrit.
    """
    con = _con()
    tracees, etes = con.execute(f"""
        SELECT count(DISTINCT station), count(DISTINCT extract('year' FROM date_locale))
        FROM '{MDA8}' WHERE {OU_A1}
    """).fetchone()
    fond, = con.execute(f"""
        SELECT count(DISTINCT station) FROM '{MDA8}'
        WHERE valide AND {ETES} AND {ANNEES} AND influence = 'Fond'
    """).fetchone()
    debut, etes_recente = con.execute(f"""
        SELECT min(extract('year' FROM date_locale)),
               count(DISTINCT extract('year' FROM date_locale))
        FROM '{MDA8}'
        WHERE valide AND {ETES} AND {ANNEES} AND station = '{RECENTE}'
    """).fetchone()
    return (_sous_titre(
        f"Objectif de qualité : {OBJECTIF_QUALITE} µg/m³ sur 8 heures. "
        f"Information du public : {SEUIL_INFORMATION} µg/m³ sur une heure.")
        + f"<br>{NOMBRES[tracees]} stations sur {NOMBRES[fond].lower()} : "
          f"{RECENTE.title()}, ouverte en {int(debut)}, ne couvre que "
          f"{NOMBRES[etes_recente].lower()} de ces {NOMBRES[etes].lower()} étés.")
ST_A2 = _sous_titre(
    "La température vient du poste météo le plus ressemblant, pas toujours le plus proche.")
# Note tenue en lignes COURTES (< 90 signes) : le pied de figure est une annotation
# Plotly, qui ne replie pas le texte — une ligne trop longue se fait rogner à droite
# dans la page, plus étroite que le fichier isolé.
NOTE_A2 = ("Les journées chaudes portent plus d'ozone. Pourquoi il plafonne ensuite, "
           "ces mesures ne le disent pas :<br>chaleur, fort soleil et air immobile vont "
           "ensemble, et rien ici ne permet de les séparer.<br>Au-delà de 35 °C, c'est "
           "aussi la tranche la moins fournie en mesures.")
# Nombres en lettres pour les textes publiés — partagée avec `page_air`, qui compte ses
# entrées de dictionnaire par le même chemin. Un effectif annoncé au lecteur se dérive de
# ce qu'il désigne ; écrit à la main, il devient faux le jour où la liste bouge, sans que
# rien ne le signale.
NOMBRES = {2: "Deux", 3: "Trois", 4: "Quatre", 5: "Cinq", 6: "Six", 7: "Sept",
           8: "Huit", 9: "Neuf", 10: "Dix"}


def _stations(n: int) -> str:
    """« une station » ou « quatre stations ».

    `NOMBRES` commence à deux, et pour cause : au singulier le nombre s'accorde en genre
    (« une station », mais « un été ») quand la table sert les deux. L'accord se fait donc
    ici, où le nom est connu.
    """
    return "une station" if n == 1 else f"{NOMBRES[n].lower()} stations"


def st_a3() -> str:
    """Sous-titre de A3 — une fonction, pas une constante : il compte ses stations.

    Écrit à la main, ce nombre a annoncé cinq stations pendant que la figure en traçait
    quatre : l'île compte cinq stations de fond, Venaco comprise, et A3 l'exclut faute de
    NO2. Le lire dans la donnée est la seule façon qu'il ne redevienne pas faux.
    """
    n = len(stations_a3())
    return _sous_titre(
        f"{NOMBRES.get(n, str(n))} stations mesurant les deux polluants.<br>Chaque courbe "
        "est ramenée à son propre maximum : on compare des heures, pas des concentrations.")


def _comptes_a1() -> tuple[int, int]:
    """Les deux nombres qu'A1 publie : journées en dépassement, journées mesurées.

    Un seul calcul pour DEUX porteurs de texte — le titre, qui affirme que le seuil
    d'information n'est jamais atteint, et la note de pied, qui porte les chiffres depuis
    que l'encadré a quitté la zone de tracé (02/09/2026). Le contrôle du seuil vit donc
    ici plutôt que dans la figure : une garde posée sur un seul porteur laisse passer la
    même erreur écrite ailleurs, et A1 en a fait la démonstration le 31/08, où un titre
    corrigé cohabitait avec un encadré qui ne l'était pas.

    Le total compte des JOURNÉES DISTINCTES, jamais la somme des barres : une journée
    chargée déclenche plusieurs stations à la fois, et additionner les colonnes donnerait
    169 « journées » là où le calendrier n'en compte que 106 — un lecteur comprendrait
    qu'il y a eu 169 jours de dépassement sur la période. Les barres, elles, comptent
    bien des journées PAR STATION : chacune est juste dans son périmètre. Ce total est
    celui des quatre stations tracées, et il vaut celui des cinq : Confina 2 n'apporte ni
    une journée mesurée ni un dépassement que les autres n'aient déjà.
    """
    con = _con()
    # Le seuil d'information est une moyenne HORAIRE : le maximum journalier sur 8 h ne
    # peut pas en décider, d'où la série. `air_o3_mda8` dérivant d'`air_serie`, toute
    # journée-station comptée ici a ses heures en face — la jointure ne filtre rien.
    alertes, = con.execute(f"""
        WITH j AS (SELECT date_locale, station FROM '{MDA8}' WHERE {OU_A1}),
             h AS (SELECT date_locale, station, max(valeur) AS horaire_max
                   FROM '{SERIE}' WHERE polluant = 'O3' GROUP BY 1, 2)
        SELECT count(*) FILTER (WHERE h.horaire_max >= {SEUIL_INFORMATION})
        FROM j JOIN h USING (date_locale, station)
    """).fetchone()
    if alertes:
        raise ValueError(
            f"A1 : {alertes} journée(s) atteignent {SEUIL_INFORMATION} µg/m³ — le titre "
            "ET la note affirment que le seuil d'information n'est jamais atteint. "
            "À réécrire avant de publier."
        )
    return con.execute(f"""
        SELECT count(DISTINCT CASE WHEN mda8 > {OBJECTIF_QUALITE} THEN date_locale END),
               count(DISTINCT date_locale)
        FROM '{MDA8}' WHERE {OU_A1}
    """).fetchone()


def note_a1() -> str:
    """Note d'A1 : ce que les barres ne peuvent pas dire, et l'objection du périmètre.

    Elle porte depuis le 02/09/2026 les trois faits qui vivaient dans un encadré posé sur
    la zone de tracé — le total en journées distinctes, l'absence de dépassement du seuil
    d'information, et l'avertissement qu'on n'additionne pas les barres. Cet encadré
    était OPAQUE et recouvrait le bas de la barre de Venaco (cf.
    `fig_a1_depassements_sans_alerte`). Le pied garde ces faits VISIBLES — ils soutiennent
    directement le titre, ils n'ont pas à attendre qu'on ouvre la note méthodologique —
    tout en les mettant hors d'atteinte de la donnée.

    Les 180 µg/m³ y sont CHIFFRÉS et non nommés : le sous-titre définit les deux seuils
    trois lignes plus haut, et les renommer ici coûtait une ligne de pied — donc une de
    hauteur de figure — pour une définition déjà lue. Ce qui ne se négocie pas, c'est
    qu'on ne les appelle jamais « alerte » : ce mot désigne les 240 µg/m³, un test le
    tient sur tous les porteurs de texte de la figure.

    S'y ajoute la seule objection que le sous-titre laisse ouverte : l'écart de périmètre
    ne coûte rien au total. Sans elle, un lecteur attentif peut croire qu'il manque des
    journées — et il aurait raison de se poser la question. La station y est désormais
    NOMMÉE : « Ses », qui se désignait tout seul quand la phrase suivait l'encadré, n'a
    plus d'antécédent lisible à deux phrases de distance.
    """
    journees, mesurees = _comptes_a1()
    con = _con()
    depassements, = con.execute(f"""
        SELECT count(*) FILTER (WHERE mda8 > {OBJECTIF_QUALITE}) FROM '{MDA8}'
        WHERE valide AND {ETES} AND {ANNEES} AND station = '{RECENTE}'
    """).fetchone()
    # Aucun <br> : `replier_pied` remplit les lignes. Couper par phrase coûterait deux
    # lignes de pied de plus, donc deux de hauteur de figure, pour un confort de lecture
    # que le pied — quatre phrases courtes — n'exige pas.
    return (f"Sur {mesurees} journées d'été observées, {journees} dépassent "
            f"{OBJECTIF_QUALITE} µg/m³ dans au moins une station ; aucune n'atteint "
            f"{SEUIL_INFORMATION} µg/m³. Les barres ne s'additionnent pas, une même "
            f"journée pouvant concerner plusieurs stations. Les {depassements} "
            f"dépassements d'{RECENTE.title()} tombent tous des jours déjà comptés.")


def st_a4() -> str:
    """Sous-titre d'A4 — une fonction, parce qu'il annonce un DÉCOMPTE d'implantations.

    Ce qu'il dit se compte dans la structure que la figure trace, jamais à côté d'elle.
    Le verrou porte sur cet accord, pas sur la phrase : si une station change légitimement
    de catégorie, le texte doit suivre la donnée sans qu'on réécrive un test éditorial.
    """
    implantations = list(perimetre_a4()["implantation"])
    rurales = [i for i in implantations if est_rurale(i)]
    autres = [i for i in implantations if not est_rurale(i)]
    # Familles, pas catégories entières : « une station rurale » et non « rurale
    # régionale ». L'échelle de représentativité n'apprend rien à qui lit un décompte de
    # milieux, la barre de la station la porte, et la ligne y gagne 77 px — elle mesurait
    # 976 px pour 974 disponibles, `export_html` la refusait.
    return _sous_titre(
        "En part des journées mesurées, non en nombre de jours — "
        f"{_stations(len(rurales))} {enumeration(rurales, len(rurales) > 1, famille=True)}, "
        f"{NOMBRES[len(autres)].lower()} {enumeration(autres, famille=True)}.")


ST_A5 = _sous_titre("Moyenne de chaque heure de la journée.")
NOTE_A5 = ("Le creux du petit matin est aussi le maximum de dioxyde d'azote : l'air y est "
           "moins chargé en ozone, pas plus pur.")


# --- A1 : « on dépasse les jours où personne n'alerte » -----------------------
# Marge basse d'A1, mesurée sur le pied qu'elle publie (`marge_basse_minimale`) : huit
# lignes depuis que la note a repris les phrases de l'encadré, contre quatre avant. La
# valeur est écrite ici plutôt que calculée, comme partout dans le module ; `verifier_pied`
# la refuse bruyamment si le pied grandit encore, ce qui vaut mieux qu'une figure qui
# s'étire toute seule à chaque mot ajouté.
#
# Ce que la mesure a appris, si l'on cherche à alléger encore : la note ne pèse que cinq
# de ces huit lignes, soit 104 px. Le reste — 85 px sous l'axe, deux lignes de source,
# une de date, la garde — vaut 165 px et ne dépend pas de ce qu'on écrit. Raccourcir la
# note d'une phrase gagne donc 21 px sur 680, pas le tiers qu'on imagine.
MARGE_BASSE_A1 = 269
# Hauteur hors marge basse : 590 - 200 avant le déplacement. La conserver telle quelle est
# ce qui garantit que la zone de tracé n'a pas bougé d'un pixel.
HAUTEUR_HORS_PIED_A1 = 390


def fig_a1_depassements_sans_alerte() -> go.Figure:
    """Nombre de journées franchissant l'objectif de qualité, station par station.

    Forme : barres horizontales — la donnée compare des quantités entre entités nommées,
    et les noms de stations sont longs. Une seule série : pas de légende, le titre la
    nomme.

    Le second chiffre du titre (« jamais le seuil d'information ») ne se dessine pas en
    barres : il vaudrait zéro pixel. Il a vécu jusqu'au 02/09/2026 dans un encadré posé
    sur la zone de tracé, à fond OPAQUE. Le 24/08 la figure est passée de cinq stations à
    quatre (cf. `OU_A1`) ; les bandes se sont élargies de 44 à 55 px, tout est descendu
    d'un cran, et l'encadré a recouvert 50 x 13 px du bas de la barre de Venaco — mesuré
    à 992 px, la largeur servie, et pire à mesure que la page se resserre. Aucun
    replacement ne le sauvait : la zone libre sous cette barre fait 115 px pour un
    encadré de 119, et le pousser à droite sort du tracé.

    Le fait est donc au pied (`note_a1`), hors de la zone de tracé, où la donnée ne peut
    plus le rencontrer. La leçon n'est pas le placement mais ce qui le tenait : « la zone
    est libre » était une hypothèse écrite en commentaire, vraie le jour où elle a été
    écrite, et rien ne la rejouait quand le périmètre changeait.
    """
    _comptes_a1()  # verrou du titre : rien n'atteint le seuil d'information
    con = _con()
    df = con.execute(f"""
        SELECT station, implantation,
               count(*) FILTER (WHERE mda8 > {OBJECTIF_QUALITE}) AS depassements
        FROM '{MDA8}' WHERE {OU_A1}
        GROUP BY 1, 2 ORDER BY 3
    """).df()

    # Mêmes libellés qu'en A4, et par la MÊME fonction : le milieu vient de l'implantation
    # publiée par le producteur, jamais du nom de la station.
    etiquettes = libelles(df["station"], df["implantation"])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["depassements"], y=etiquettes, orientation="h",
        marker=dict(color=AIR_OZONE, line=dict(color=PALETTE["surface"], width=2)),
        text=[str(v) for v in df["depassements"]], textposition="outside",
        textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        hovertemplate="%{y}<br>%{x} journées au-dessus de "
                      f"{OBJECTIF_QUALITE} µg/m³<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Six étés de dépassements, jamais le seuil d'information"),
        # Libellé aligné sur celui d'A4 (24/08/2026), qui le suit dans la page et le disait
        # juste : c'est L'OZONE qui dépasse, pas la station — laquelle ne dépasse rien, elle
        # mesure. Le seuil est nommé et pas seulement chiffré : le sous-titre en annonce
        # DEUX (objectif de qualité et information du public), et un « 120 µg/m³ » nu
        # laissait au lecteur le soin d'apparier. « (six étés cumulés) » disparaît : la
        # période est déjà dite trois fois sur cette figure — titre, et les deux dernières
        # lignes du sous-titre. Reste à empêcher d'additionner les barres, ce que faisaient
        # les capitales de « CETTE » ; « station par station » le dit sans crier, et le
        # pied tient l'autre bout avec ses journées distinctes.
        xaxis=dict(title=dict(text=f"Journées où l'ozone dépasse l'objectif de qualité "
                                   f"({OBJECTIF_QUALITE} µg/m³), station par station",
                              font=AXE)),
        yaxis=dict(title=""),
        # `b` et `height` montent ENSEMBLE de la même quantité (02/09/2026) : le pied a
        # gagné les phrases de l'encadré, et `verifier_pied` réclame la marge qui les
        # loge. Les augmenter de concert laisse la zone de tracé exactement où elle
        # était — l'y rogner serait reprendre d'une main la place qu'on rend de l'autre.
        margin=dict(t=170, b=MARGE_BASSE_A1, l=250, r=90),
        height=HAUTEUR_HORS_PIED_A1 + MARGE_BASSE_A1,
    )
    return fig


# --- A2 : « l'air se dégrade quand il fait beau » -----------------------------
def fig_a2_ozone_et_chaleur() -> go.Figure:
    """Ozone moyen par tranche de température, avec l'effectif de chaque tranche.

    Forme : des POINTS, pas des barres (refonte du 04/08/2026). L'écart à montrer est de
    9 µg/m³ sur des valeurs de 90 à 99 : des barres imposent une base à zéro, et sur une
    échelle de 0 à 120 les quatre tranches paraissaient identiques — la figure démentait
    son propre titre. Un point ne porte pas de surface proportionnelle : il n'engage donc
    pas la base zéro, l'axe peut se resserrer sans tromper, et la montée puis le plafond
    se voient enfin. Les points ne sont pas reliés : entre deux tranches, rien n'est mesuré.

    L'effectif se lit au survol, et la note de pied signale que la tranche la plus chaude
    est la moins fournie : un lecteur doit pouvoir en tenir compte.

    Cet effectif compte des RELEVÉS, soit une station un jour donné, et non des journées
    du calendrier — cinq stations mesurent la même journée. C'est aussi la pondération de
    la moyenne : chaque couple station-jour y pèse pareil. A1 est tombée dans ce piège
    avant d'en sortir (cf. le total de journées distinctes qu'elle affiche) ; ici il est
    dans le libellé, qui ne dit jamais « jours ».
    """
    con = _con()
    df = con.execute(f"""
        SELECT CASE WHEN t_max < 25 THEN '< 25 °C'
                    WHEN t_max < 30 THEN '25 à 30 °C'
                    WHEN t_max < 35 THEN '30 à 35 °C'
                    ELSE '≥ 35 °C' END AS tranche,
               min(t_max) AS borne, avg(mda8) AS ozone, count(*) AS releves
        FROM '{CROISE}'
        WHERE influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1 ORDER BY borne
    """).df()
    i_max = int(df["ozone"].idxmax())
    if i_max == len(df) - 1:
        raise ValueError(
            "A2 : l'ozone culmine sur la tranche la plus chaude — le plafond que le titre "
            "annonce n'existe plus. Titre et sous-titre à revoir."
        )
    couleurs = [AIR_OZONE if i <= i_max else PALETTE["muted"] for i in range(len(df))]

    # Repère horizontal sur la tranche la plus fraîche : il donne à l'œil le « départ »
    # que la base zéro ne fournit plus, et rend l'écart mesurable sans le calculer.
    base = float(df.loc[0, "ozone"])
    fig = go.Figure()
    fig.add_hline(y=base, line=dict(color=PALETTE["rule"], width=1, dash="dot"))
    # UNE seule étiquette par point (04/08/2026) : la valeur et l'écart à la tranche
    # fraîche tiennent ensemble, « 99 (+9) ». En deux textes superposés, la figure portait
    # huit étiquettes sur quatre points, plus les effectifs sous l'axe — illisible. L'unité
    # n'est écrite qu'une fois, sur le premier point : au-delà, elle se répète pour rien.
    etiquettes = []
    for i, v in enumerate(df["ozone"]):
        val = f"{v:.0f} µg/m³" if i == 0 else f"{v:.0f}"
        etiquettes.append(val if i == 0 else f"{val} (+{v - base:.0f})")
    fig.add_trace(go.Scatter(
        x=df["tranche"], y=df["ozone"], mode="markers+text",
        marker=dict(color=couleurs, size=26,
                    line=dict(color=PALETTE["surface"], width=2)),
        text=etiquettes, textposition="top center",
        textfont=dict(family=SANS, size=18, color=PALETTE["ink"]),
        cliponaxis=False,
        customdata=df["releves"],
        hovertemplate="%{x}<br>%{y:.1f} µg/m³ en moyenne<br>"
                      "sur %{customdata} relevés — une station, une journée<extra></extra>",
    ))
    fig.add_annotation(
        x=df.loc[len(df) - 1, "tranche"], y=float(df.loc[len(df) - 1, "ozone"]),
        text="au-delà, l'ozone<br>ne monte plus", showarrow=True, arrowhead=0,
        # Annotation SOUS le point : au-dessus, quelle que soit l'inclinaison, la flèche
        # traversait l'étiquette de valeur. En dessous, la zone est vide.
        arrowcolor=PALETTE["ink_soft"], ax=0, ay=72,
        font=dict(family=SANS, size=16, color=PALETTE["ink"]),
    )
    # Axe resserré autour des valeurs observées — légitime avec des points, jamais avec
    # des barres. Amplitude forcée à au moins 20 µg/m³ pour qu'un écart réel de 9 ne
    # devienne pas, à l'inverse, un précipice.
    bas, haut = float(df["ozone"].min()), float(df["ozone"].max())
    marge = max((20 - (haut - bas)) / 2, 3)
    fig.update_layout(
        title=dict(text="Plus il fait chaud, plus l'air est chargé — jusqu'à 35 °C"),
        # Titre d'axe court, et posé loin de l'axe : il servait de séparation entre le
        # graphique et le pied de page, les trois se touchaient.
        xaxis=dict(title=dict(text="Température maximale de la journée", font=AXE,
                              standoff=32)),
        yaxis=dict(title=dict(text="Ozone (µg/m³)", font=AXE),
                   range=[bas - marge, haut + marge]),
        # Bande basse généreuse : le graphique se termine franchement avant que le texte
        # de bas de figure ne commence (cf. pied_decalage_px à l'export).
        margin=dict(t=170, b=350, l=120, r=70),
        height=740,
    )
    return fig


# --- A3 : « le pic n'est pas à l'heure de pointe » ----------------------------
def fig_a3_ozone_contre_azote() -> go.Figure:
    """Cycles diurnes de l'ozone et du NO2, chacun ramené à son propre maximum.

    Forme : deux courbes sur une échelle RELATIVE, et surtout pas deux axes verticaux.
    Les deux polluants n'ont pas le même ordre de grandeur (l'ozone dépasse 90 µg/m³
    quand le NO2 plafonne sous 20) ; un second axe donnerait à leurs hauteurs une
    comparabilité qui n'existe pas. Ce que la figure compare, ce sont des HEURES, pas des
    concentrations — d'où l'indexation sur 100 % du maximum de chaque série. Les valeurs
    absolues restent lisibles au survol.

    Venaco est écartée : elle ne mesure plus le NO2, et comparer deux polluants exige
    qu'ils soient mesurés au même endroit. Restent les stations de fond des deux villes.
    Leur nombre n'est pas écrit ici : le sous-titre le compte (cf. `st_a3`).
    """
    con = _con()
    # Les deux courbes doivent porter sur les MÊMES stations : une station qui ne
    # mesurerait qu'un polluant nourrirait une courbe et pas l'autre, et le sous-titre
    # compterait des stations qui ne comparent rien.
    appariees = stations_a3()
    tracees = [s for (s,) in con.execute(
        f"SELECT DISTINCT station FROM '{SERIE}' WHERE {OU_A3} ORDER BY 1").fetchall()]
    if tracees != appariees:
        raise ValueError(
            f"A3 : {sorted(set(tracees) - set(appariees))} ne mesure(nt) qu'un seul des "
            "deux polluants — les courbes ne porteraient pas sur les mêmes stations."
        )
    df = con.execute(f"""
        SELECT heure_locale AS h, polluant, avg(valeur) AS v
        FROM '{SERIE}' WHERE {OU_A3}
        GROUP BY 1, 2 ORDER BY 1
    """).df()
    pivot = df.pivot(index="h", columns="polluant", values="v")
    fig = go.Figure()
    for pol, couleur, nom in (("NO2", AIR_AZOTE, "Dioxyde d'azote (moteurs)"),
                              ("O3", AIR_OZONE, "Ozone")):
        serie = pivot[pol]
        rel = 100 * serie / serie.max()
        h_pic = int(rel.idxmax())
        fig.add_trace(go.Scatter(
            x=rel.index, y=rel, name=nom, mode="lines",
            line=dict(color=couleur, width=2.8),
            customdata=serie,
            hovertemplate=f"{nom}<br>%{{customdata:.1f}} µg/m³"
                          "<br>%{y:.0f} % de son maximum<extra></extra>",
        ))
        fig.add_annotation(
            x=h_pic, y=100, text=f"<b>{h_pic} h</b>", showarrow=True, arrowhead=0,
            arrowcolor=couleur, ax=0, ay=-38,
            font=dict(family=SANS, size=19, color=couleur),
        )
    fig.update_layout(
        title=dict(text="L'heure de pointe n'est pas l'heure de l'ozone"),
        xaxis=dict(title=dict(text="Heure locale", font=AXE), dtick=3, ticksuffix=" h"),
        # Titre court : le sous-titre dit déjà de quel maximum il s'agit.
        yaxis=dict(title=dict(text="Part du maximum", font=AXE),
                   ticksuffix=" %", range=[0, 118]),
        # Séparation légende / propos d'introduction : c'est la BANDE HAUTE qu'on
        # élargit, pas la légende qu'on remonte — la remonter la rapprochait du
        # sous-titre au lieu de l'en éloigner. Elle reste collée au tracé, et c'est le
        # tracé qui descend ; la hauteur suit pour ne pas comprimer les courbes.
        legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0),
        margin=dict(t=310, b=170, l=140, r=60),
        height=700,
    )
    return fig


# --- A4 : « l'air de campagne n'est pas meilleur » ----------------------------
def fig_a4_campagne_contre_ville() -> go.Figure:
    """Fréquence des dépassements, par station, la rurale mise en évidence.

    Forme : barres horizontales en TAUX et non en nombre de jours — une station rurale
    contre quatre urbaines, les effectifs ne sont pas comparables et un décompte brut
    ferait passer la campagne pour épargnée. Une seule teinte porte le propos (la station
    rurale) ; les autres restent en retrait, ce qui évite une palette de cinq couleurs
    pour une lecture qui n'en demande que deux.
    """
    c = contraste_a4()
    df, rurale, autres, devancees = c["df"], c["rurale"], c["autres"], c["devancees"]
    # LE TITRE SE COMPTE (29/08/2026). « La campagne n'est pas l'endroit où l'air est le
    # plus pur » extrapolait deux fois : une seule station rurale devenait « la campagne »,
    # et un résultat sur le seul ozone devenait « l'air ». Une station peut porter plus
    # d'ozone et moins de dioxyde d'azote — A3 le montre à quelques centimètres de là.
    # Le titre énonce donc l'observation, avec ses nombres, et s'arrête là.
    titre = (f"À {rurale.title()}, les dépassements d'ozone sont plus fréquents"
             f"<br>que dans {devancees} des {len(autres)} stations "
             f"{c['implantations']}")
    couleurs = [AIR_OZONE if s == rurale else PALETTE["muted"] for s in df["station"]]
    # Explicitation (04/08/2026) : chaque station dit son implantation, et non la seule
    # rurale — sans quoi le lecteur doit deviner celle des autres.
    etiquettes = libelles(df["station"], df["implantation"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["taux"], y=etiquettes, orientation="h",
        marker=dict(color=couleurs, line=dict(color=PALETTE["surface"], width=2)),
        # L'unité est portée par chaque étiquette : « 15 » seul se lit comme un nombre
        # de jours, ce que la figure ne montre justement pas.
        text=[f"{v:.0f} %" for v in df["taux"]], textposition="outside",
        textfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        customdata=df["jours"],
        hovertemplate="%{y}<br>%{x:.1f} % des journées au-dessus de "
                      f"{OBJECTIF_QUALITE} µg/m³"
                      "<br>sur %{customdata} journées mesurées<extra></extra>",
    ))
    fig.add_annotation(
        # L'encart ne répète plus le décompte : depuis que le titre le porte, il ne lui
        # reste que l'explication — et deux lignes au lieu de quatre rendent au tracé la
        # hauteur que le titre sur deux lignes lui prend.
        # « Peuvent détruire » : le mécanisme est établi, son poids dans l'écart mesuré ici
        # ne l'est pas. Ce que nous montrons est une coïncidence sur nos propres mesures
        # (le pic de NO2 tombe dans le creux d'ozone, cf. A3) — pas la démonstration que
        # c'est elle qui creuse l'écart entre ces cinq stations.
        text=("En ville, les gaz d'échappement peuvent"
              "<br>détruire une partie de l'ozone."),
        xref="paper", yref="paper", x=0.99, y=0.04, xanchor="right", yanchor="bottom",
        showarrow=False, align="right",
        font=dict(family=SANS, size=17, color=PALETTE["ink"]),
        bgcolor=PALETTE["page"], borderpad=12,
    )
    fig.update_layout(
        title=dict(text=titre),
        xaxis=dict(title=dict(text=f"Part des journées d'été où l'ozone dépasse "
                                   f"l'objectif de qualité ({OBJECTIF_QUALITE} µg/m³)",
                              font=AXE),
                   ticksuffix=" %",
                   # Air à droite : l'étiquette de la barre la plus longue est posée
                   # hors barre et se faisait rogner au bord du tracé.
                   range=[0, float(df["taux"].max()) * 1.14]),
        yaxis=dict(title=""),
        # t=175 et non 170 : le titre sur deux lignes en exige exactement 175, mesuré par
        # `marge_haute_minimale`, qui refusait la figure sinon. Les cinq pixels rendus par
        # le tracé sont largement repris à l'encart, passé de quatre lignes à deux.
        margin=dict(t=175, b=190, l=300, r=90),
        height=580,
    )
    return fig


# --- A5 : « le pire créneau » -------------------------------------------------
def fig_a5_creneau_a_eviter() -> go.Figure:
    """Cycle diurne de l'ozone en été, avec le plateau de forte charge mis en bande.

    Forme : une courbe unique (donc pas de légende — le titre nomme la série) et une bande
    verticale sur le créneau. La bande dit la PLAGE, la courbe dit la forme : deux
    informations que ni l'une ni l'autre ne porterait seule. Creux et pic sont étiquetés
    directement, ce qui évite d'écrire une valeur sur chacune des vingt-quatre heures.
    """
    con = _con()
    df = con.execute(f"""
        SELECT heure_locale AS h, avg(valeur) AS v
        FROM '{SERIE}'
        WHERE polluant = 'O3' AND influence = 'Fond' AND {ETES} AND {ANNEES}
        GROUP BY 1 ORDER BY 1
    """).df()
    pic = float(df["v"].max())
    plateau = sorted(int(h) for h, v in zip(df["h"], df["v"]) if v >= 0.95 * pic)
    if plateau != list(range(plateau[0], plateau[-1] + 1)):
        raise ValueError(
            f"A5 : créneau troué {plateau} — « entre X et Y heures » suppose une plage "
            "d'un seul tenant. Forme du titre à revoir."
        )
    h_pic = int(df.loc[df["v"].idxmax(), "h"])
    h_creux = int(df.loc[df["v"].idxmin(), "h"])
    creux = float(df["v"].min())

    fig = go.Figure()
    fig.add_vrect(
        x0=plateau[0] - 0.5, x1=plateau[-1] + 0.5,
        fillcolor=AIR_OZONE, opacity=0.10, line_width=0, layer="below",
    )
    fig.add_trace(go.Scatter(
        x=df["h"], y=df["v"], mode="lines", name="Ozone",
        line=dict(color=AIR_OZONE, width=3),
        hovertemplate="%{x} h — %{y:.0f} µg/m³<extra></extra>",
    ))
    for h, v, txt, dy in ((h_creux, creux, f"creux d'ozone<br><b>{creux:.0f} µg/m³</b>", 58),
                          (h_pic, pic, f"le plus chargé<br><b>{pic:.0f} µg/m³</b>", -58)):
        fig.add_annotation(
            x=h, y=v, text=txt, showarrow=True, arrowhead=0,
            arrowcolor=PALETTE["ink_soft"], ax=0, ay=dy, align="center",
            font=dict(family=SANS, size=16, color=PALETTE["ink"]),
        )
    fig.add_annotation(
        x=(plateau[0] + plateau[-1]) / 2, y=1.0, yref="paper", yanchor="bottom", yshift=6,
        text=f"<b>{plateau[0]} h – {plateau[-1]} h</b>", showarrow=False,
        font=dict(family=SANS, size=20, color=AIR_OZONE),
    )
    fig.update_layout(
        title=dict(text="L'été, l'air est le plus chargé de 11 h à 18 h"),
        xaxis=dict(title=dict(text="Heure locale", font=AXE), dtick=3, ticksuffix=" h"),
        yaxis=dict(title=dict(text="Ozone (µg/m³)", font=AXE)),
        margin=dict(t=200, b=220, l=140, r=60),
        height=650,
    )
    return fig


def main() -> int:
    verifier_sorties()
    d_air = date_collecte("aee_o3_venaco_continu")
    d_meteo = date_collecte("meteo_horaire_corse")

    export_html(fig_a1_depassements_sans_alerte(), "a1_depassements_sans_alerte",
                SRC_AIR, d_air, sous_titre=st_a1(), note=note_a1())
    export_html(fig_a2_ozone_et_chaleur(), "a2_ozone_et_chaleur",
                SRC_AIR_METEO, d_meteo, sous_titre=ST_A2, note=NOTE_A2,
                pied_decalage_px=PIED_A2)
    export_html(fig_a3_ozone_contre_azote(), "a3_ozone_contre_azote",
                SRC_AIR, d_air, sous_titre=st_a3())
    export_html(fig_a4_campagne_contre_ville(), "a4_campagne_contre_ville",
                SRC_AIR, d_air, sous_titre=st_a4())
    export_html(fig_a5_creneau_a_eviter(), "a5_creneau_a_eviter",
                SRC_AIR, d_air, sous_titre=ST_A5, note=NOTE_A5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
