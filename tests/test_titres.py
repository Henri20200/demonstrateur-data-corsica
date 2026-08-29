"""Le titre d'une figure tient dans la largeur où elle est publiée.

Un titre Plotly ne se replie jamais : au-delà de la largeur du visuel, il est rogné
sans un mot, et le défaut reste invisible tant qu'on relit sur un écran large. Le
06/08/2026, huit des dix figures de l'étude étaient dans ce cas.

Le verrou lui-même est câblé dans `viz.export_html`, par où passe toute figure publiée :
ces tests vérifient qu'il mesure juste et qu'il mord. Ils ne demandent pas le pipeline
de données — c'est voulu, la CI de PR n'a pas de Parquet.
"""

import plotly.graph_objects as go
import pytest

from demonstrateur.viz import (
    GABARIT_PAR_CAR,
    LARGEUR_VISUEL,
    RETRAIT_TITRE_PX,
    largeur_px,
    marge_basse_minimale,
    marge_haute_minimale,
    rangees_de_legende,
    verifier_pied,
    verifier_titres,
)

DISPO = LARGEUR_VISUEL - RETRAIT_TITRE_PX


def figure(titre: str = "Titre court", sous_titre: str = "", marge_t: int = 400) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=dict(text=titre, subtitle=dict(text=sous_titre)),
                      margin=dict(t=marge_t))
    return fig


# --- Le gabarit mesure juste ---------------------------------------------------

# ÉTALONS FIGÉS, ce ne sont pas des titres vivants. Les trois largeurs de droite ont été
# relevées au VRAI rendu (Segoe UI, la `system-ui` de Windows) le 06/08/2026 ; c'est cette
# observation extérieure qui donne sa valeur au test, et elle ne se refait pas depuis le
# code — mesurer un texte neuf avec `largeur_px` puis vérifier `largeur_px` contre lui-même
# ne prouverait rien. Les chaînes restent donc telles quelles même quand le document
# change : la première a été le titre de T3 jusqu'au 27/08/2026 et ne l'est plus.
@pytest.mark.parametrize("texte, taille, attendu", [
    ("Même à son zénith, le soleil ne détrône pas le fossile", 28, 655),
    ("Une journée d'été (juin-août) heure par heure — parts du mix, Corse 2019-2024.", 18, 631),
    ("Interconnexions = câbles SACOI (Italie via la Sardaigne).", 18, 438),
])
def test_le_gabarit_colle_au_rendu_reel(texte, taille, attendu):
    mesure = largeur_px(texte, taille)
    assert abs(mesure - attendu) <= 0.03 * attendu, (
        f"gabarit dérivé : {mesure:.0f} px mesurés contre {attendu} px rendus"
    )


def test_les_balises_ne_comptent_pas_dans_la_largeur():
    """`<b>` occupe de la place dans la chaîne, aucune à l'écran."""
    assert largeur_px("<b>gras</b>", 18) == largeur_px("gras", 18)


def test_un_caractere_inconnu_ne_passe_pas_sous_le_radar():
    """Hors table, on compte LARGE : un signe non prévu doit faire déborder plus tôt,
    jamais plus tard — sinon le verrou se tait précisément là où il ne sait pas."""
    inconnu = "字"  # idéogramme : hors de tout ce que nos titres emploient
    assert inconnu not in GABARIT_PAR_CAR
    assert largeur_px(inconnu, 18) >= largeur_px("e", 18)


# --- Le verrou mord ------------------------------------------------------------

def test_un_titre_trop_long_est_refuse():
    trop = "Titre délibérément interminable " * 4
    assert largeur_px(trop, 28) > DISPO
    with pytest.raises(ValueError, match="hors gabarit"):
        verifier_titres(figure(titre=trop), "t_essai")


def test_un_sous_titre_trop_long_est_refuse():
    trop = "Sous-titre qui court sur toute la largeur et bien au-delà encore. " * 2
    with pytest.raises(ValueError, match="hors gabarit"):
        verifier_titres(figure(sous_titre=trop), "t_essai")


def test_une_ligne_repliee_sur_br_est_acceptee():
    """La correction attendue est le repli, pas le raccourcissement : deux lignes
    courtes passent là où leur concaténation échouait."""
    moitie = "Sous-titre qui court sur toute la largeur et bien au-delà encore."
    with pytest.raises(ValueError):
        verifier_titres(figure(sous_titre=f"{moitie} {moitie}"), "t_essai")
    verifier_titres(figure(sous_titre=f"{moitie}<br>{moitie}"), "t_essai")


def test_une_marge_haute_trop_courte_est_refusee():
    """Le défaut de T7 : le titre tenait en largeur, mais le tracé remontait dedans."""
    fig = figure(sous_titre="Une ligne.<br>Deux lignes.<br>Trois lignes.", marge_t=150)
    with pytest.raises(ValueError, match="marge haute"):
        verifier_titres(fig, "t_essai")


def test_la_marge_minimale_croit_avec_le_nombre_de_lignes():
    court = marge_haute_minimale(figure(sous_titre="Une ligne."))
    long = marge_haute_minimale(figure(sous_titre="Une ligne.<br>Deux.<br>Trois.<br>Quatre."))
    assert long > court


# --- Le pied tient entier ------------------------------------------------------

def test_un_pied_qui_deborde_du_bas_est_refuse():
    """Le défaut de T7 et T8 : la ligne coupée était « données estimées » — la figure
    publiée était moins prudente que ce que le code affirmait."""
    pied = "<br>".join(["Source : EDF — données collectées le 2026-07-22"] + ["note"] * 7)
    fig = figure()
    fig.update_layout(margin=dict(t=400, b=250))
    with pytest.raises(ValueError, match="pied"):
        verifier_pied(fig, "t_essai", pied, -130)


def test_la_marge_basse_minimale_tient_compte_du_decalage_et_des_lignes():
    """Les deux termes comptent : éloigner le pied du tracé coûte autant qu'y ajouter
    des lignes. C'est ce qui rendait T6 (décalage -170) le plus exposé."""
    base = marge_basse_minimale("une ligne", -85)
    assert marge_basse_minimale("une ligne", -170) > base
    assert marge_basse_minimale("une<br>ligne", -85) > base


def test_un_pied_qui_tient_passe():
    fig = figure()
    fig.update_layout(margin=dict(t=400, b=330))
    pied = "<br>".join(["Source : EDF"] + ["note"] * 7)
    verifier_pied(fig, "t_essai", pied, -130)


def test_une_figure_sans_marge_declaree_passe():
    """Marge non déclarée = celle du template, que la figure n'a pas choisie : on ne
    peut pas la lui reprocher ici. Seule une marge posée à la main est contrôlée."""
    fig = go.Figure()
    fig.update_layout(title=dict(text="Titre court"))
    verifier_titres(fig, "t_essai")


# --- La légende ne recouvre plus rien ------------------------------------------

def _fig_legende(y, hauteur=700, t=150, b=300, titre_axe="Heure légale", noms=("A", "B")):
    fig = go.Figure()
    for n in noms:
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name=n))
    fig.update_layout(
        title=dict(text="Un titre", subtitle=dict(text="Un sous-titre")),
        xaxis=dict(title=dict(text=titre_axe)),
        legend=dict(orientation="h", y=y, yanchor="top", x=0),
        margin=dict(t=t, b=b), height=hauteur)
    return fig


def test_une_legende_qui_tombe_sur_le_titre_d_axe_est_refusee():
    """Le défaut réel de T4 le 27/08/2026 : y=-0,16 posait la légende sur « Heure légale »."""
    with pytest.raises(ValueError, match="l'axe x en occupe encore"):
        verifier_titres(_fig_legende(-0.16), "figure")


def test_une_legende_assez_basse_passe():
    verifier_titres(_fig_legende(-0.30), "figure")


def test_sans_titre_d_axe_la_legende_peut_remonter():
    """La garde MESURE ce qui est sous le tracé, elle ne le suppose pas : sans titre
    d'axe il n'y a que les étiquettes à dégager, et y=-0,16 redevient acceptable."""
    verifier_titres(_fig_legende(-0.16, titre_axe=None), "figure")


def test_une_legende_qui_deborde_de_la_marge_basse_est_refusee():
    with pytest.raises(ValueError, match="hors d'une marge b="):
        verifier_titres(_fig_legende(-0.80, b=120), "figure")


def test_une_legende_au_dessus_du_trace_qui_mord_le_sous_titre_est_refusee():
    """L'autre défaut, celui de T6 : légende à y=1,02 dans une marge haute déjà prise."""
    with pytest.raises(ValueError, match="elle remonte dans le sous-titre"):
        verifier_titres(_fig_legende(1.02, t=100), "figure")


def test_une_legende_se_replie_et_la_garde_le_voit():
    """Six entrées longues ne tiennent pas sur une rangée : la garde compte le repli."""
    longs = tuple(f"Une entrée de légende plutôt longue n° {i}" for i in range(6))
    assert rangees_de_legende(_fig_legende(-0.30, noms=longs), 992) >= 3
