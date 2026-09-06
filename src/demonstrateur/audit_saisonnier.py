"""Audit saisonnier de la courbe de charge corse : les tableaux qui fondent T10.

Ce module existe pour une raison : le chapitre « En été, les heures les plus chargées
gagnent 64 MW en six ans » avance une quinzaine de nombres, et une figure ne se relit
pas. Ici, chaque tableau se régénère d'une commande, sur le Parquet certifié, avec les
requêtes écrites en clair :

    python -m demonstrateur.audit_saisonnier

La sortie est du Markdown, recopiée telle quelle dans `docs/AUDIT_SAISONNIER.md`. Un test
(`tests/test_audit_saisonnier.py`) régénère les tableaux et vérifie qu'ils figurent
VERBATIM dans ce document : une donnée qui bouge fait donc échouer la suite, elle ne
laisse pas un document se désaligner en silence.

Deux conventions, écrites une fois et partagées avec la figure (`figures.py`) et les
verrous (`test_resultats.py`) :

- l'été est juin-septembre. Le découpage est sans effet : juillet-août seuls,
  juin-septembre ou mai-octobre donnent les six mêmes maxima ;
- un hiver enjambe deux années civiles et porte le millésime de son mois de décembre.
  Les hivers de bord du jeu (2018/19 sans décembre, 2024/25 réduit à décembre) sont
  incomplets et exclus — les inclure fabrique une bascule qui n'existe pas.
"""

from __future__ import annotations

import sys

import duckdb

from .config import DATA_PROCESSED

COURBE = (DATA_PROCESSED / "edf_courbe_corse.parquet").as_posix()

ETE = "mois_local BETWEEN 6 AND 9"
HIVER = "mois_local IN (12, 1, 2)"
HIVER_COMPLET_H = 2100
"""Plancher d'heures d'un hiver complet : déc+janv+févr ≈ 2 160 h, un mois seul ≈ 744."""

# Millésime d'un hiver = l'année de son mois de décembre.
AN_HIVER = "CASE WHEN mois_local = 12 THEN annee_locale ELSE annee_locale - 1 END"


def _md(titre: str, entetes: list[str], lignes: list[list[str]]) -> str:
    """Un tableau Markdown, colonnes alignées à droite sauf la première."""
    aligne = ["---"] + ["---:"] * (len(entetes) - 1)
    corps = [f"| {' | '.join(entetes)} |", f"| {' | '.join(aligne)} |"]
    corps += [f"| {' | '.join(li)} |" for li in lignes]
    return f"**{titre}**\n\n" + "\n".join(corps)


def table_ete(con) -> str:
    """Par été : heures, maximum, moyenne des vingt heures hautes, médiane, dépassements."""
    lignes = con.execute(
        f"""SELECT annee_locale, count(*),
              max(production_totale_mw),
              avg(production_totale_mw) FILTER (WHERE rk <= 20),
              median(production_totale_mw),
              count(*) FILTER (WHERE production_totale_mw >= 380)
            FROM (SELECT annee_locale, production_totale_mw,
                    row_number() OVER (PARTITION BY annee_locale
                                       ORDER BY production_totale_mw DESC) AS rk
                  FROM '{COURBE}' WHERE {ETE})
            GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    return _md(
        "Étés (juin-septembre)",
        ["Été", "heures", "maximum", "moy. 20 h hautes", "médiane", "heures ≥ 380 MW"],
        [[str(a), str(h), f"{mx:.1f}", f"{t20:.1f}", f"{med:.1f}", str(n)]
         for a, h, mx, t20, med, n in lignes],
    )


def table_hivers(con) -> str:
    """Par hiver : heures, complétude, maximum, mois du maximum."""
    lignes = con.execute(
        f"""SELECT h, n, p, mois FROM (
              SELECT {AN_HIVER} AS h, count(*) AS n, max(production_totale_mw) AS p,
                     arg_max(mois_local, production_totale_mw) AS mois
              FROM '{COURBE}' WHERE {HIVER} GROUP BY 1)
            ORDER BY h"""
    ).fetchall()
    return _md(
        "Hivers (décembre-février, millésimés par leur décembre)",
        ["Hiver", "heures", "complet", "maximum", "mois du maximum"],
        [[f"{h}/{str(h + 1)[2:]}", str(n),
          "oui" if n >= HIVER_COMPLET_H else "non — écarté",
          f"{p:.1f}", {1: "janvier", 2: "février", 12: "décembre"}[int(mois)]]
         for h, n, p, mois in lignes],
    )


def table_ecarts(con) -> str:
    """Pointe de l'été moins pointe de l'hiver qui le précède, hivers complets seulement."""
    lignes = con.execute(
        f"""WITH h AS (
              SELECT {AN_HIVER} AS an, count(*) AS n, max(production_totale_mw) AS p
              FROM '{COURBE}' WHERE {HIVER} GROUP BY 1),
            e AS (
              SELECT annee_locale AS an, max(production_totale_mw) AS p
              FROM '{COURBE}' WHERE {ETE} GROUP BY 1)
            SELECT e.an, e.p, h.p, e.p - h.p FROM e JOIN h ON h.an = e.an - 1
            WHERE h.n >= {HIVER_COMPLET_H} ORDER BY 1"""
    ).fetchall()
    return _md(
        "Écart été − hiver précédent (hivers complets)",
        ["Été", "pointe de l'été", "pointe de l'hiver précédent", "écart"],
        [[str(a), f"{pe:.1f}", f"{ph:.1f}", f"{d:+.1f}"] for a, pe, ph, d in lignes],
    )


def table_quantiles(con) -> str:
    """Quantiles des heures d'été : ce qui monte, et de combien."""
    q = {"médiane": 0.50, "q75": 0.75, "q90": 0.90, "q99": 0.99}
    cols = ", ".join(
        f"quantile_cont(production_totale_mw, {v}) AS \"{k}\"" for k, v in q.items()
    )
    lignes = con.execute(
        f"""SELECT annee_locale, {cols}, max(production_totale_mw) AS maximum
            FROM '{COURBE}' WHERE {ETE} GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    entetes = ["Été", *q, "maximum"]
    corps = [[str(li[0]), *(f"{v:.1f}" for v in li[1:])] for li in lignes]
    gains = [li[i] - lignes[0][i] for i in range(1, len(entetes)) for li in [lignes[-1]]]
    corps.append(["**2019 → 2024**", *(f"**{g:+.1f}**" for g in gains)])
    return _md("Quantiles des heures d'été (MW)", entetes, corps)


def table_perimetre(con) -> str:
    """Petite hydraulique : ce qui manque à 2024, et ce que cela pèse à la pointe."""
    lignes = con.execute(
        f"""SELECT annee_locale, count(*) FILTER (WHERE micro_hydraulique_mw IS NULL),
              avg(micro_hydraulique_mw),
              max(abs(micro_hydraulique_mw)) FILTER (WHERE rk <= 20 AND ete)
            FROM (SELECT annee_locale, micro_hydraulique_mw, {ETE} AS ete,
                    row_number() OVER (PARTITION BY annee_locale, {ETE}
                                       ORDER BY production_totale_mw DESC) AS rk
                  FROM '{COURBE}')
            GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    return _md(
        "Petite hydraulique : périmètre du total",
        # Pas de « |max| » : les barres verticales sont les séparateurs de colonne du
        # Markdown, et l'en-tête se scinderait en deux colonnes fantômes.
        ["Année", "heures sans valeur", "moyenne annuelle",
         "plus fort écart absolu aux 20 h d'été hautes"],
        [[str(a), str(n), "—" if m is None else f"{m:.2f}",
          "—" if p is None else f"{p:.2f}"] for a, n, m, p in lignes],
    )


def rapport() -> str:
    """Les cinq tableaux, dans l'ordre où le chapitre s'en sert."""
    con = duckdb.connect()
    return "\n\n".join([
        table_ete(con), table_quantiles(con), table_hivers(con),
        table_ecarts(con), table_perimetre(con),
    ])


def main() -> int:
    # La sortie est du Markdown destiné à être recopié : elle doit rester intacte quand
    # on la redirige. Sur une console Windows en cp1252, « ≥ » suffit à faire échouer
    # l'écriture — d'où l'UTF-8 déclaré ici plutôt qu'un caractère de repli.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not (DATA_PROCESSED / "edf_courbe_corse.parquet").exists():
        print("data/processed absent — lancer fetch-data puis python -m demonstrateur.prepare")
        return 1
    print(rapport())
    return 0


if __name__ == "__main__":
    sys.exit(main())
