"""T1 tient dans ses deux cadres, quel que soit le cas — sans données.

Depuis le 01/11/2026, T1 dit la part du solaire sur les six dernières heures de relevés,
avec ses quantités et un repère annuel. Son message est du texte : rogné, il ne garde
que le pourcentage, sans la période ni le repère qui le bornent. D'où deux mises en page
(large ; étroite sous viz.SEUIL_ETROIT_PX, choisie chez le lecteur) et ces verrous, qui
tournent sans pipeline : la figure se construit sur des cas inventés, les pires
possibles, et c'est elle qui lève si une ligne ou une hauteur ne tient pas. Un cas réel
qui casserait ici casserait le cron, donc la publication de tout le livrable.
"""

import itertools
import json
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import pytest

from demonstrateur import compile_etude, figures as F
from demonstrateur.viz import (CADRE_ETROIT_MIN_PX, MARGE_PAGE_PX, SEUIL_ETROIT_PX,
                               largeur_px, texte_pied)

PIED = texte_pied(F.SRC_MIX, "2026-10-31", F.note_t1("2026-07-22"))

# Bornes : même jour aux heures les plus longues, puis à cheval sur deux mois et sur
# deux années, avec « 1er » et « septembre ».
PERIODES = [
    (datetime(2026, 9, 30, 10, 15), datetime(2026, 9, 30, 16, 0)),
    (datetime(2026, 9, 30, 20, 15), datetime(2026, 10, 1, 2, 0)),
    (datetime(2026, 12, 31, 20, 15), datetime(2027, 1, 1, 2, 0)),
]
# Complet, un puis deux relevés estimés, relevés manquants (quantités masquées).
QUANTITES = [dict(mwh_solaire=9990.0, mwh_total=9990.0, estimes=e, disponibles=24 - e)
             for e in (0, 1, 2)]
QUANTITES.append(dict(mwh_solaire=None, mwh_total=None, estimes=0, disponibles=21))
AGES = [0.5, F.FRAICHEUR_AVERTIR_H + 1, F.FRAICHEUR_BLOQUER_H + 1]


def _figure(debut, fin, quantites, age_h=0.5, statut="Estimé", part=100.0):
    f = dict(part=part, debut=debut, fin=fin, **quantites)
    quand = f"{F._jour_fr(fin)} {fin.year} à {F._heure_fr(fin)}"
    sous_titre = F.sous_titre_t1(quand, statut, age_h)
    return F.figure_t1(f, 10, 13, sous_titre, PIED), sous_titre


@pytest.mark.parametrize("debut, fin", PERIODES)
@pytest.mark.parametrize("quantites", QUANTITES)
@pytest.mark.parametrize("age_h", AGES)
@pytest.mark.parametrize("statut", ["Estimé", "Consolidé"])
def test_t1_tient_dans_ses_deux_cadres(debut, fin, quantites, age_h, statut):
    """Chaque ligne tient, en large au seuil étroit et en étroit à 320 px, et la hauteur
    étroite fixe contient le texte : sinon `figure_t1` lève. On revérifie ici, en plus,
    ce que la page déclare à l'étude."""
    fig, _ = _figure(debut, fin, quantites, age_h, statut)
    etroit = fig.layout.meta["etroit"]
    assert etroit["seuil"] == SEUIL_ETROIT_PX
    assert etroit["hauteur"] == F.T1_HAUTEUR_ETROITE_PX
    assert etroit["disposition"]["height"] == etroit["hauteur"]
    assert fig.layout.height == 200 + F.T1_HAUTEUR_TRACE_PX + 150


def test_les_lignes_etroites_tiennent_a_320_px():
    """Contre-mesure indépendante du constructeur : on relit le texte posé et on le
    mesure, ligne à ligne, au corps où il s'affiche."""
    fig, _ = _figure(*PERIODES[1], QUANTITES[1], age_h=F.FRAICHEUR_BLOQUER_H + 1)
    disposition = fig.layout.meta["etroit"]["disposition"]
    dispo = CADRE_ETROIT_MIN_PX - 2 * MARGE_PAGE_PX - 2 * F.T1_MARGE_ETROITE_PX
    textes = [(a["text"], a["font"]["size"]) for a in disposition["annotations"]]
    titre = disposition["title"]
    textes += [(titre["text"], titre["font"]["size"]),
               (titre["subtitle"]["text"], titre["subtitle"]["font"]["size"])]
    for texte, taille in textes:
        for ligne in texte.split("<br>"):
            assert largeur_px(ligne.replace(" ", " "), taille) <= dispo, ligne


def test_textes_valides_le_31_10():
    """Les formulations retenues avec l'utilisateur : la durée en quarts d'heure (les
    bornes seules se lisaient « 5 h 45 »), le pourcentage sur les seuls relevés présents
    quand il en manque, l'unité de la facture à côté des MWh."""
    jour = (datetime(2026, 10, 30, 7, 45), datetime(2026, 10, 30, 13, 30))
    complet = F.textes_t1(dict(part=42.0, debut=jour[0], fin=jour[1], **QUANTITES[0]), 9, 12)
    assert complet["periode"].startswith(
        "Sur les 24 quarts d'heure associés aux relevés du 30 octobre, de 7h45 à 13h30,")
    assert "1 MWh = 1 000 kWh, l'unité de votre facture d'électricité." in complet["quantites"]
    assert complet["repere"].startswith("Repère : sur une année entière, le solaire fournit 9 à 12 %")

    masque = F.textes_t1(dict(part=23.0, debut=jour[0], fin=jour[1], **QUANTITES[3]), 9, 12)
    assert masque["periode"].startswith("Sur 21 des 24 quarts d'heure associés")
    assert "MWh" not in masque["quantites"]
    assert "le pourcentage porte sur ces relevés" in masque["quantites"]

    deux_jours = F.textes_t1(
        dict(part=2.0, debut=PERIODES[1][0], fin=PERIODES[1][1], **QUANTITES[0]), 9, 12)
    assert "allant du 30 septembre à 20h15<br>au 1er octobre à 2h00" in deux_jours["periode"]


# --- Le pourcentage se retrouve à partir des MWh affichés (convention du 01/11/2026) ---


def _lu(f: dict) -> tuple[int, list[int]]:
    """Ce que lit le lecteur : le pourcentage et les MWh, relus dans les textes posés."""
    t = F.textes_t1(f, 9, 12)
    part = int(re.search(r"<b>(\d+) %</b>", t["part"]).group(1))
    ligne = t["quantites"].split("<br>")[0]
    # Milliers séparés par une espace fine insécable (U+202F), comme à l'affichage.
    return part, [int(n.replace("\u202f", ""))
                  for n in re.findall(r"(\d[\d\u202f]*) MWh", ligne)]


def _fenetre(solaire, total, part=None, disponibles=24):
    debut, fin = PERIODES[0]
    if part is None:
        part = 100 * solaire / total
    return dict(part=part, mwh_solaire=solaire, mwh_total=total, estimes=0,
                disponibles=disponibles, debut=debut, fin=fin)


def test_le_cas_publie_le_01_11_se_recalcule():
    """Page publiée le 01/11/2026 : 47,96 MWh sur 1 085,88 font 4 %, mais les MWh à la
    dizaine affichaient « 50 sur 1 090 », qui font 5 %."""
    assert _lu(_fenetre(47.96, 1085.88)) == (4, [48, 1086])


def test_le_pourcentage_se_retrouve_a_partir_des_mwh_affiches():
    """Pour toute fenêtre complète, le pourcentage affiché est celui que le lecteur
    calcule sur les MWh affichés, arrondi demi vers le haut ; et il ne s'écarte jamais
    d'un point entier de la part exacte, qui reste celle de la fenêtre."""
    for solaire in [x / 7 for x in range(0, 2100, 11)]:
        for total in (180.4, 499.5, 1085.88, 1500.5, 2999.49):
            f = _fenetre(solaire, total)
            part, (s, t) = _lu(f)
            attendu = (Decimal(100 * s) / Decimal(t)).quantize(Decimal(1), ROUND_HALF_UP)
            assert part == int(attendu), (solaire, total)
            assert abs(part - f["part"]) < 1, (solaire, total)
    assert _lu(_fenetre(9, 200))[0] == 5          # 4,5 % : demi vers le haut


def test_sans_mwh_le_pourcentage_porte_sur_les_valeurs_disponibles():
    """Quantités masquées : pas d'arrondi intermédiaire, la part exacte s'arrondit seule."""
    assert _lu(_fenetre(None, None, part=23.49, disponibles=21)) == (23, [])
    assert _lu(_fenetre(None, None, part=23.5, disponibles=21)) == (24, [])


def test_le_sous_titre_avertit_aux_seuils_du_code():
    """Le sous-titre est composé une fois (sous_titre_t1) pour les deux mises en page et
    pour main() : ses seuils sont ceux qui décident du code de sortie."""
    quand = "30 octobre 2026 à 13h30"
    assert "⚠" not in F.sous_titre_t1(quand, "Estimé", F.FRAICHEUR_AVERTIR_H - 0.1)
    assert "collecte à relancer" in F.sous_titre_t1(quand, "Estimé", F.FRAICHEUR_AVERTIR_H + 0.1)
    assert "trop ancienne" in F.sous_titre_t1(quand, "Estimé", F.FRAICHEUR_BLOQUER_H + 0.1)


def test_le_script_choisit_la_mise_en_page_sans_composer_de_texte():
    """Le script lit la mise en page étroite dans la page et ses mots dans le code : un
    texte qui ne serait écrit QUE dans le JavaScript échapperait à toute mesure."""
    script = F.script_fraicheur("2026-10-30T12:30:00Z", "Dernières données disponibles : x.")
    assert "L.meta && L.meta.etroit" in script
    assert "window.innerWidth < E.seuil" in script
    mots = json.dumps(F.T1_MOTS_AGE)
    assert mots in script
    # Les mots ne sont écrits qu'une fois, dans la table mesurée par le code.
    assert script.count("ge de ce relev") == 1


def test_l_age_se_lit_comme_une_duree():
    """« Le dernier relevé remonte à 8 h 50 », sous « 1er novembre 2026 à 9h15 », se
    lisait comme une heure (page publiée le 01/11/2026). Toute durée en heures porte donc
    « min », dans le script comme dans les lignes qu'on mesure pour lui."""
    script = F.script_fraicheur("2026-10-30T12:30:00Z", "Dernières données disponibles : x.")
    assert "' h ' + ('0' + (m % 60)).slice(-2) + ' min'" in script
    assert F.T1_MOTS_AGE["age"] == "Âge de ce relevé :"
    for etroit in (False, True):
        heures = [li for li in F._lignes_age_t1(etroit) if " h " in li]
        assert heures and all(" min" in li for li in heures), heures


def test_la_source_de_t1_ne_laisse_pas_de_mot_seul():
    """Au repli commun (64 caractères), la source de T1 se coupait avant « réel) », seul
    sur sa ligne. T1 replie son pied à la largeur de son corps, en lignes équilibrées."""
    import inspect

    from demonstrateur.viz import preparer_figure

    fig, sous_titre = _figure(*PERIODES[0], QUANTITES[1])
    preparer_figure(fig, F.SRC_MIX, "2026-11-01", sous_titre, F.note_t1("2026-07-22"),
                    -20, nom="t1_soleil_live", pied_largeur_px=F.T1_CORPS_LARGE_PX)
    lignes = fig.layout.annotations[-1].text.split("<br>")
    assert lignes[0] == f"Source : {F.SRC_MIX}"
    assert all(" " in li for li in lignes), lignes
    # Et c'est bien ce repli que main() demande à l'export.
    assert "pied_largeur_px=T1_CORPS_LARGE_PX" in inspect.getsource(F.main)


# --- L'étude : le cadre prend la hauteur étroite au même seuil que la figure ----------


def _visuel(tmp_path, monkeypatch, meta: dict | None) -> str:
    layout = {"height": 720, "title": {"text": "Quelle place le solaire ?"}}
    if meta is not None:
        layout["meta"] = meta
    (tmp_path / "t1_test.html").write_text(
        f'<script>Plotly.newPlot("t1_test", [], {json.dumps(layout)}, {{}})</script>',
        encoding="utf-8")
    monkeypatch.setattr(compile_etude, "OUTPUTS", tmp_path)
    return compile_etude._iframe("t1_test")


def test_le_cadre_d_un_visuel_etroit_change_de_hauteur(tmp_path, monkeypatch):
    iframe = _visuel(tmp_path, monkeypatch,
                     {"etroit": {"seuil": SEUIL_ETROIT_PX, "hauteur": 1080}})
    assert 'height="736"' in iframe
    assert 'class="adaptable"' in iframe and "--hauteur-etroite:1096px" in iframe
    # Même seuil des deux côtés : la requête de conteneur mesure le cadre, comme la
    # figure mesure sa fenêtre ; la requête média le double à 2,5rem près.
    assert f"@container (max-width:{SEUIL_ETROIT_PX - 0.02:.2f}px)" in compile_etude._CSS_ETROIT
    assert f"@media (max-width:{SEUIL_ETROIT_PX + 40 - 0.02:.2f}px)" in compile_etude._CSS_ETROIT


def test_un_visuel_sans_mise_en_page_etroite_garde_son_cadre(tmp_path, monkeypatch):
    assert "adaptable" not in _visuel(tmp_path, monkeypatch, None)


def test_un_seuil_qui_diverge_est_refuse(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="couperait la figure"):
        _visuel(tmp_path, monkeypatch, {"etroit": {"seuil": SEUIL_ETROIT_PX - 1, "hauteur": 900}})


def test_l_enumeration_couvre_bien_le_pire_cas():
    """Le pire cas mesuré (1 076 px le 01/11/2026) tient sous la constante, avec moins de
    5 % de marge : une constante gonflée laisserait sur téléphone un vide sous la source."""
    pire = 0
    for (debut, fin), q, age in itertools.product(PERIODES, QUANTITES, AGES):
        fig, _ = _figure(debut, fin, q, age, "Consolidé")
        d = fig.layout.meta["etroit"]["disposition"]
        pied = d["annotations"][-1]
        lignes = pied["text"].count("<br>") + 1
        pire = max(pire, d["margin"]["t"] - pied["yshift"] + lignes * 16 * 1.3)
    assert pire <= F.T1_HAUTEUR_ETROITE_PX
    assert pire >= 0.95 * F.T1_HAUTEUR_ETROITE_PX - 40
