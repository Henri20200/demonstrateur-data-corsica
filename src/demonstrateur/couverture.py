"""Contrôle de couverture : la fenêtre d'analyse annoncée est réellement peuplée.

BLOQUANT, et placé entre `prepare` et les figures — pas dans la suite de tests, qui ne
s'exécute qu'après la génération. Le 13/09/2026, l'AEE a basculé 2025 du flux continu
vers le jeu validé ; le jeu validé n'étant alors pas re-téléchargé, l'été 2025 a disparu
des deux côtés à la fois. Rien n'était armé pour le dire.

CE QUE CE MODULE AJOUTE. Toute la traçabilité du dépôt répond à « les octets que je
détiens sont-ils ceux que j'ai certifiés » : `fetch` revérifie les empreintes, `prepare`
refuse un brut non certifié, `_build.json` relie chaque sortie à ses sources. Aucune de
ces gardes ne répond à « la donnée couvre-t-elle la période que l'étude prétend
analyser ». Mesuré plutôt que supposé : une année retirée du MILIEU de la fenêtre (2023)
traverse `prepare`, la suite entière, les figures et les pages sans un seul échec, et A1
se recompte alors « deux de ces cinq étés » — auto-cohérente, publiable, fausse.

Le contrôle porte sur la DONNÉE, jamais sur le texte d'une figure : il tient quelle que
soit la cause du trou — bascule du producteur, jointure ratée, filtre trop large, fuseau
déplacé. La fenêtre vient de `figures_air` (`AN_DEBUT`, `AN_FIN`) et n'est pas recopiée
ici : déplacer la fenêtre publiée déplace ce qui est exigé.

L'ABSENCE D'UNE SORTIE EST UN ÉCHEC, pas un motif de saut. Un contrôle qui se tait quand
le fichier manque protège exactement autant qu'un contrôle absent.

    python -m demonstrateur.couverture     # code 1 si la couverture est insuffisante
"""

import sys
from pathlib import Path

import duckdb

from demonstrateur.config import DATA_PROCESSED
from demonstrateur.figures_air import AN_DEBUT, AN_FIN, ETES

MDA8 = DATA_PROCESSED / "air_o3_mda8.parquet"
SERIE = DATA_PROCESSED / "air_serie.parquet"
CROISE = DATA_PROCESSED / "air_temperature_jour.parquet"
PARQUETS_REQUIS = (MDA8, SERIE, CROISE)

# Seuils RELEVÉS sur la donnée du 13/09/2026, pas choisis à vue. Sur 2020-2025 :
# 5 stations d'ozone par été (6 depuis l'ouverture d'Ajaccio Confina 2 en 2024),
# 4 stations de NO2 (5 depuis 2024 ; Venaco ne mesure pas le NO2), et de 75 à 92
# journées valides par station-année. Les planchers sont posés SOUS le minimum observé.
STATIONS_MIN = {"O3": 5, "NO2": 4}
JOURS_MIN_PAR_ETE = 60  # minimum réel 75, sur 92 journées d'été

# Le référentiel des couples (polluant, station) ATTENDUS. Un effectif et une continuité
# ne suffisent pas : tous deux se calculent sur ce qui est PRÉSENT, et une station
# totalement absente n'a ni ligne à compter ni années à enchaîner. Éprouvé le
# 13/09/2026 — Confina 2 retirée du seul NO2 laissait l'effectif à 4, son plancher, et
# la continuité muette faute d'observation. Ce qui n'est nulle part ne se voit qu'en le
# comparant à une liste écrite.
STATIONS_O3 = ("AJACCIO CANETTO", "AJACCIO CONFINA 2", "BASTIA GIRAUD",
               "BASTIA LA MARANA", "BASTIA MONTESORO", "VENACO")
STATIONS_NO2 = ("AJACCIO CANETTO", "AJACCIO CONFINA 2", "BASTIA GIRAUD",
                "BASTIA LA MARANA", "BASTIA MONTESORO")  # Venaco ne mesure pas le NO2
PREMIER_ETE = {"AJACCIO CONFINA 2": 2024}  # ouverte le 31/01/2024 ; sinon AN_DEBUT

# Stations arrêtées, par (polluant, station), et l'été de leur dernière mesure. Vide au
# 13/09/2026. Y inscrire une station est une décision : cela retire de la fenêtre une
# mesure que les figures comptaient, donc cela se vérifie auprès du producteur d'abord.
STATIONS_CLOSES: dict[tuple[str, str], int] = {}

ANNEES_ATTENDUES = tuple(range(AN_DEBUT, AN_FIN + 1))


class CouvertureInsuffisante(RuntimeError):
    """La fenêtre publiée n'est pas peuplée — rien ne doit être généré ni publié."""


def sorties_manquantes() -> list[Path]:
    """Les Parquet requis qui n'existent pas. Leur absence est un échec, pas un saut."""
    return [p for p in PARQUETS_REQUIS if not p.exists()]


def _lignes(sql: str) -> list[tuple]:
    return duckdb.connect().execute(sql).fetchall()


def couples_attendus(polluants: tuple[str, ...]) -> dict[tuple[str, str], int]:
    """(polluant, station) -> premier été attendu dans la fenêtre."""
    stations = {"O3": STATIONS_O3, "NO2": STATIONS_NO2}
    return {
        (polluant, station): max(PREMIER_ETE.get(station, AN_DEBUT), AN_DEBUT)
        for polluant in polluants
        for station in stations[polluant]
    }


def _continuite(
    observees: dict[tuple[str, str], list[int]],
    polluants: tuple[str, ...] = ("O3", "NO2"),
    origine: str = "air_serie",
) -> list[str]:
    """Années contiguës, ET jusqu'à `AN_FIN`.

    La seconde moitié est celle qui manquait au premier jet : une station qui perd la
    DERNIÈRE année de la fenêtre garde des années contiguës et passe inaperçue. Éprouvé
    le 13/09/2026 — Confina 2 amputée de 2025 laissait tous les verrous au vert, son
    effectif tombant de 6 à 5 sans franchir le plancher. C'est pourtant la forme exacte
    qu'aurait prise une bascule ne touchant qu'une partie des stations.
    """
    anomalies = []
    attendus = couples_attendus(polluants)

    absents = [f"{p} / {s}" for (p, s) in sorted(attendus) if (p, s) not in observees]
    if absents:
        anomalies.append(
            f"{origine} : couple(s) attendu(s) totalement absent(s) — "
            + ", ".join(absents)
            + " ; ni l'effectif ni la continuité ne peuvent le voir, ils ne comptent "
            "que ce qui est présent."
        )

    # Regroupées par année d'arrêt : quand c'est l'année entière qui manque, toutes les
    # stations s'arrêtent ensemble, et onze lignes identiques noieraient la première
    # anomalie — celle qui nomme la cause — au milieu de ses propres conséquences.
    arretees: dict[int, list[str]] = {}
    for (polluant, station), annees in sorted(observees.items()):
        annees = sorted(annees)
        attendu = list(range(annees[0], annees[-1] + 1))
        if annees != attendu:
            anomalies.append(
                f"{origine} : {polluant} / {station} — étés {annees}, interruption "
                f"entre {annees[0]} et {annees[-1]}"
            )
        debut_attendu = attendus.get((polluant, station), AN_DEBUT)
        if annees[0] > debut_attendu:
            anomalies.append(
                f"{origine} : {polluant} / {station} — premier été mesuré en "
                f"{annees[0]}, attendu dès {debut_attendu} ; si la station a ouvert plus "
                "tard, corriger PREMIER_ETE, sinon la donnée manque."
            )
        fin_attendue = STATIONS_CLOSES.get((polluant, station), AN_FIN)
        if annees[-1] < fin_attendue:
            arretees.setdefault(annees[-1], []).append(f"{polluant} / {station}")
    for derniere, couples in sorted(arretees.items()):
        anomalies.append(
            f"{origine} : dernier été mesuré en {derniere}, attendu jusqu'à {AN_FIN} — "
            + ", ".join(couples)
            + " ; si une station a fermé, l'inscrire dans STATIONS_CLOSES, sinon la "
            "donnée manque et rien d'autre ne le dira."
        )
    return anomalies


def controler() -> list[str]:
    """Renvoie la liste des anomalies de couverture. Vide = la fenêtre est peuplée."""
    manquants = sorties_manquantes()
    if manquants:
        return [
            f"sortie absente : {p.name} — lancer fetch-data puis prepare ; sans elle le "
            "contrôle ne prouve rien"
            for p in manquants
        ]

    anomalies: list[str] = []
    fenetre = f"extract('year' FROM date_locale) BETWEEN {AN_DEBUT} AND {AN_FIN}"

    # 1. Aucune année de la fenêtre n'est vide. Le verrou le plus simple, et le seul qui
    #    aurait parlé le 13/09/2026.
    peuplees = {
        an for (an,) in _lignes(f"""
            SELECT DISTINCT extract('year' FROM date_locale)::int
            FROM '{MDA8.as_posix()}' WHERE valide AND {ETES} AND {fenetre}
        """)
    }
    if manquantes := sorted(set(ANNEES_ATTENDUES) - peuplees):
        anomalies.append(
            f"aucune mesure d'ozone valide pour l'été {manquantes} alors que la fenêtre "
            f"publiée est {AN_DEBUT}-{AN_FIN} — vérifier si le producteur a basculé ces "
            "années d'un jeu à l'autre (cf. l'en-tête AEE de sources.yaml)"
        )

    # 2. L'effectif de stations ne s'effondre pas : une station de moins déplace les
    #    moyennes sans rien casser de visible.
    for an, n in _lignes(f"""
        SELECT extract('year' FROM date_locale)::int, count(DISTINCT station)
        FROM '{MDA8.as_posix()}' WHERE valide AND {ETES} AND {fenetre}
        GROUP BY 1 ORDER BY 1
    """):
        if n < STATIONS_MIN["O3"]:
            anomalies.append(
                f"été {an} : {n} station(s) d'ozone, plancher {STATIONS_MIN['O3']} — la "
                "population de la fenêtre a changé, les comparaisons entre étés ne "
                "portent plus sur le même terrain"
            )

    # 3. Le trou peut être intra-annuel : un mois manquant déplace une moyenne d'été.
    maigres = _lignes(f"""
        SELECT extract('year' FROM date_locale)::int, station, count(*)
        FROM '{MDA8.as_posix()}' WHERE valide AND {ETES} AND {fenetre}
        GROUP BY 1, 2 HAVING count(*) < {JOURS_MIN_PAR_ETE} ORDER BY 3
    """)
    if maigres:
        anomalies.append(
            f"été(s) amputé(s) sous le plancher de {JOURS_MIN_PAR_ETE} journées "
            "valides : " + ", ".join(f"{st} {an} ({j} j)" for an, st, j in maigres)
        )

    # 4. Les deux polluants, chacun sur son effectif propre : A3 les oppose, et un trou
    #    pourrait n'affecter que l'un des deux.
    vus = {
        (polluant, an): n
        for polluant, an, n in _lignes(f"""
            SELECT polluant, extract('year' FROM date_locale)::int, count(DISTINCT station)
            FROM '{SERIE.as_posix()}' WHERE {ETES} AND {fenetre} GROUP BY 1, 2
        """)
    }
    for polluant, plancher in STATIONS_MIN.items():
        for an in ANNEES_ATTENDUES:
            if (n := vus.get((polluant, an), 0)) < plancher:
                anomalies.append(
                    f"{polluant}, été {an} : {n} station(s), plancher {plancher}"
                )

    # 5. Continuité par station ET par polluant — sur `air_serie`, qui porte l'ozone et
    #    le NO2, et non sur le seul MDA8 qui ne connaît que l'ozone.
    observees: dict[tuple[str, str], list[int]] = {}
    for polluant, station, an in _lignes(f"""
        SELECT polluant, station, extract('year' FROM date_locale)::int
        FROM '{SERIE.as_posix()}' WHERE {ETES} AND {fenetre} GROUP BY 1, 2, 3
    """):
        observees.setdefault((polluant, station), []).append(an)
    anomalies += _continuite(observees, ("O3", "NO2"), "air_serie")

    # 5 bis. La MÊME vérification sur le résultat journalier, qui est ce que les figures
    #    lisent. `prepare` dérive le MDA8 d'`air_serie` : une règle de validité qui se
    #    resserre, une jointure qui échoue, et l'ozone journalier perd une station-année
    #    que la série horaire porte toujours. Contrôler la série ne dit rien du MDA8 —
    #    éprouvé le 13/09/2026, Confina 2 privée de 2025 dans le seul MDA8 passait.
    journalieres: dict[tuple[str, str], list[int]] = {}
    for station, an in _lignes(f"""
        SELECT station, extract('year' FROM date_locale)::int
        FROM '{MDA8.as_posix()}' WHERE valide AND {ETES} AND {fenetre} GROUP BY 1, 2
    """):
        journalieres.setdefault(("O3", station), []).append(an)
    anomalies += _continuite(journalieres, ("O3",), "air_o3_mda8")

    # 6. Le croisement météo : une jointure est un endroit où l'on perd.
    croisees = {
        an for (an,) in _lignes(f"""
            SELECT DISTINCT extract('year' FROM date_locale)::int
            FROM '{CROISE.as_posix()}' WHERE {ETES} AND {fenetre}
        """)
    }
    if absentes := sorted(set(ANNEES_ATTENDUES) - croisees):
        anomalies.append(
            f"croisement ozone/température absent pour l'été {absentes} — vérifier la "
            "couverture météo autant que celle de l'air avant de publier A2"
        )

    return anomalies


def verifier() -> None:
    """Lève `CouvertureInsuffisante` si la fenêtre publiée n'est pas peuplée."""
    if anomalies := controler():
        raise CouvertureInsuffisante("\n".join(anomalies))


def main() -> int:
    anomalies = controler()
    if not anomalies:
        print(
            f"[ok] couverture {AN_DEBUT}-{AN_FIN} complète — "
            f"{len(ANNEES_ATTENDUES)} étés peuplés, continuité des stations vérifiée."
        )
        return 0
    print(f"[!] COUVERTURE INSUFFISANTE ({len(anomalies)} anomalie(s)) :")
    for a in anomalies:
        print(f"    - {a}")
    print(
        "\nRien n'est généré ni publié : une figure se recompte sur la donnée qu'elle "
        "trouve et ne signale pas ce qui manque."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
