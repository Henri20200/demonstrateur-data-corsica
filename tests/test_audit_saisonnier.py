"""Le document d'audit saisonnier dit ce que la donnée dit — vérifié, pas supposé.

`docs/AUDIT_SAISONNIER.md` porte les tableaux qui fondent le chapitre des pointes
estivales et la figure T10. Ils y sont recopiés depuis
`python -m demonstrateur.audit_saisonnier`, et rien n'empêcherait ce document de vieillir
en silence pendant que la donnée EDF bouge — sinon ce test, qui régénère les tableaux et
exige de les retrouver VERBATIM dans la page.

C'est le pendant documentaire des verrous `t10_*` de `test_resultats.py` : ceux-là tiennent
les chiffres écrits dans l'étude, celui-ci tient le tableau qui permet de les reproduire.
"""

import pytest

from demonstrateur import audit_saisonnier
from demonstrateur.config import DATA_PROCESSED, ROOT

COURBE = DATA_PROCESSED / "edf_courbe_corse.parquet"
AUDIT = ROOT / "docs" / "AUDIT_SAISONNIER.md"

besoin_courbe = pytest.mark.skipif(
    not COURBE.exists(), reason="data/processed absent — lancer fetch-data puis prepare"
)


def test_le_document_d_audit_existe():
    assert AUDIT.exists(), "docs/AUDIT_SAISONNIER.md manquant — le chapitre T10 s'y appuie"


@besoin_courbe
def test_chaque_tableau_du_document_correspond_a_la_donnee():
    """Les cinq tableaux régénérés se retrouvent tels quels dans la page."""
    page = AUDIT.read_text(encoding="utf-8")
    for bloc in audit_saisonnier.rapport().split("\n\n**"):
        bloc = bloc if bloc.startswith("**") else "**" + bloc
        titre = bloc.splitlines()[0]
        assert bloc in page, (
            f"le tableau {titre} de docs/AUDIT_SAISONNIER.md ne correspond plus à la "
            "donnée — régénérer la page avec `python -m demonstrateur.audit_saisonnier`"
        )


@besoin_courbe
def test_le_document_rappelle_les_conventions_qui_font_le_resultat():
    """Trois réserves sans lesquelles les tableaux se liraient de travers.

    Elles ne sont pas décoratives : l'heure légale corrigée est ce qui rend les mois
    justes, la définition de l'hiver complet est ce qui écarte les deux saisons de bord,
    et la distinction traçabilité / statut est ce qui empêche de lire « fichier vérifié »
    comme « valeur validée ».
    """
    # Blancs normalisés : la page est repliée à 90 colonnes, et une expression cherchée
    # telle quelle peut se trouver à cheval sur deux lignes — « heure légale corse » l'est.
    page = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for attendu in ("heure légale corse", "hiver est dit complet", "2 100",
                    "validées", "estimées", "juillet-août"):
        assert attendu in page, (
            f"docs/AUDIT_SAISONNIER.md ne mentionne plus « {attendu} » — la page doit "
            "porter les conventions qui rendent ses tableaux lisibles"
        )
