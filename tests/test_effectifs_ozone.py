"""Les effectifs affichés distinguent dépassement, validité et période disponible."""

import duckdb
import pytest

from demonstrateur import figures_air as fa
from demonstrateur.viz import (lignes_de_titre, marge_effective, marge_haute_minimale,
                              preparer_figure)


def test_les_effectifs_ne_comptent_que_les_jours_valides_du_perimetre(tmp_path, monkeypatch):
    source = tmp_path / "ozone.parquet"
    with duckdb.connect() as con:
        con.execute("""
            CREATE TABLE mesures AS
            SELECT 'VENACO' AS station, 'Rurale régionale' AS implantation,
                   influence, CAST(jour AS DATE) AS date_locale, valide, mda8
            FROM (VALUES
                ('Fond', '2020-06-01', true, 121.0),
                ('Fond', '2020-06-02', true, 120.0),
                ('Fond', '2022-08-31', true, 90.0),
                ('Fond', '2021-07-01', false, 150.0),
                ('Fond', '2023-06-01', false, 80.0),
                ('Fond', '2019-07-01', true, 150.0),
                ('Fond', '2026-07-01', true, 150.0),
                ('Fond', '2020-05-31', true, 150.0),
                ('Fond', '2020-09-01', true, 150.0),
                ('Trafic', '2020-07-01', true, 150.0)
            ) AS t(influence, jour, valide, mda8)
        """)
        con.execute("COPY mesures TO ? (FORMAT PARQUET)", [str(source)])
    monkeypatch.setattr(fa, "MDA8", source.as_posix())

    ligne = fa.perimetre_a4().iloc[0]
    assert ligne["depassements"] == 1  # L'égalité à 120 ne constitue pas un dépassement.
    assert ligne["jours"] == 3
    assert ligne["taux"] == pytest.approx(100 / 3)
    assert list(ligne["etes"]) == [2020, 2022]  # Aucun été sans journée valide n'est annoncé.


def _parquet(tmp_path, nom: str, stations) -> str:
    """Un MDA8 de substitut : (station, implantation, étés, jours, dont en dépassement)."""
    lignes = []
    for station, implantation, etes, jours, hauts in stations:
        for an in etes:
            for i in range(jours):
                mda8 = 150.0 if i < hauts else 90.0
                lignes.append(f"('{station}', '{implantation}', '{an}-06-{i + 1:02d}', {mda8})")
    source = tmp_path / nom
    with duckdb.connect() as con:
        con.execute(f"""
            CREATE TABLE mesures AS
            SELECT station, implantation, 'Fond' AS influence,
                   CAST(jour AS DATE) AS date_locale, true AS valide, mda8
            FROM (VALUES {", ".join(lignes)}) AS t(station, implantation, jour, mda8)
        """)
        con.execute("COPY mesures TO ? (FORMAT PARQUET)", [str(source)])
    return source.as_posix()


COMPLETS = list(range(fa.AN_DEBUT, fa.AN_FIN + 1))
RECENTS = COMPLETS[-2:]
# Le classement réel en miniature : une périurbaine en tête, la rurale en deuxième,
# trois stations derrière elle. Avec quatre stations non rurales, c'est le seul
# classement que les gardes d'A4 acceptent. La dernière station n'a que deux étés,
# comme Confina 2 : elle ajoute la ligne de sous-titre sur la couverture.
CINQ_STATIONS = [
    ("BASTIA MONTESORO", "Périurbaine", COMPLETS, 6, 3),
    ("VENACO", "Rurale régionale", COMPLETS, 6, 2),
    ("BASTIA GIRAUD", "Urbaine", COMPLETS, 6, 1),
    ("AJACCIO CANETTO", "Urbaine", COMPLETS, 12, 1),
    ("AJACCIO CONFINA 2", "Périurbaine", RECENTS, 6, 0),
]


def test_le_titre_d_a4_est_ancre_en_haut_et_la_place_lui_est_reservee(tmp_path, monkeypatch):
    """A4 est la seule figure dont le titre tient sur deux lignes.

    Sans ancrage, Plotly centre le bloc titre dans la marge haute. Un titre sur deux
    lignes suivi d'un sous-titre en déborde alors par le bas et recouvre la première
    barre. La capture du 22/09/2026 le montrait pendant que `marge_haute_minimale`
    validait la figure : le gabarit mesure la hauteur du texte, pas sa position.

    Le test vérifie deux choses : le titre déclare son ancrage, et la marge déclarée
    couvre ce que le texte demande. Il porte sur A4 seule. Apprendre l'ancrage au
    gabarit commun reste à faire.
    """
    monkeypatch.setattr(fa, "MDA8", _parquet(tmp_path, "cinq.parquet", CINQ_STATIONS))

    fig = fa.fig_a4_campagne_contre_ville()
    assert "<br>" in fig.layout.title.text, (
        "le titre d'A4 tient sur une ligne : ce verrou n'a plus d'objet, le relire"
    )
    assert (fig.layout.title.yref, fig.layout.title.yanchor) == ("container", "top"), (
        "le titre d'A4 n'est plus ancré en haut du conteneur — Plotly le recentre dans "
        "la marge haute et sa deuxième ligne redescend sur la première barre"
    )

    # `preparer_figure` refuse déjà une marge trop courte ; on le redit ici pour que
    # l'échec nomme A4 et non le gabarit générique, et pour mesurer le mou restant.
    preparer_figure(fig, fa.SRC_AIR, "2026-01-01", sous_titre=fa.st_a4(), note=fa.NOTE_A4)
    assert marge_effective(fig, "t") >= marge_haute_minimale(fig), (
        f"marge haute {marge_effective(fig, 't')} px pour un bloc titre qui en réclame "
        f"{marge_haute_minimale(fig)}"
    )

    # Le titre ne doit pas non plus être collé au bord haut. Il reçoit autant d'air
    # au-dessus de lui qu'entre le sous-titre et le tracé.
    bloc = sum(taille * 1.45 for _, taille in lignes_de_titre(fig))
    au_dessus = fig.layout.height * (1 - float(fig.layout.title.y))
    en_dessous = marge_effective(fig, "t") - au_dessus - bloc
    assert au_dessus == pytest.approx(en_dessous, abs=1), (
        f"{au_dessus:.0f} px au-dessus du titre contre {en_dessous:.0f} px sous le "
        "sous-titre : le bloc n'est plus centré dans la marge haute"
    )
    assert au_dessus >= 12, f"le titre est collé au bord haut ({au_dessus:.0f} px)"


def test_la_phrase_de_resultat_se_compte_dans_la_figure(tmp_path, monkeypatch):
    """La page et la figure lisent le même périmètre."""
    monkeypatch.setattr(fa, "MDA8", _parquet(tmp_path, "cinq.parquet", CINQ_STATIONS))

    phrase = fa.phrase_resultat_a4()
    assert "Bastia Montesoro, station périurbaine" in phrase
    assert "(50 %)" in phrase                         # 3 dépassements sur 6 journées
    assert "Venaco, seule station rurale étudiée, arrive deuxième (33 %)" in phrase
    assert "devant les trois autres stations" in phrase


def test_la_phrase_de_resultat_s_arrete_si_la_rurale_passe_en_tete(tmp_path, monkeypatch):
    """La phrase nomme une station de tête, puis la rurale derrière elle.

    C'est une tournure, pas un calcul. Si la rurale passait première, aucun recalcul ne
    la rendrait vraie : il faudrait la réécrire. La page s'arrête donc, comme elle
    s'arrête déjà quand la rurale ne devance plus la majorité des autres.
    """
    en_tete = [(s, i, e, j, 6 if s == "VENACO" else h) for s, i, e, j, h in CINQ_STATIONS]
    monkeypatch.setattr(fa, "MDA8", _parquet(tmp_path, "rurale_en_tete.parquet", en_tete))
    with pytest.raises(ValueError, match="est au rang 1"):
        fa.phrase_resultat_a4()
