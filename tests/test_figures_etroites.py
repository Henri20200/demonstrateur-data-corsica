"""La mise en page étroite générique (viz.disposition_etroite) — sans données.

Depuis le 01/11/2026, toute figure exportée reçoit une seconde mise en page pour les
cadres de téléphone, dérivée de la large et choisie chez le lecteur (script_etroit).
Avant, sur un téléphone, titres, sous-titres et sources étaient coupés à droite, les
légendes posées sur le titre, et le tracé de t7 réduit à 28 px. Ces verrous construisent
des figures inventées et vérifient ce que la dérivation promet : chaque ligne tient dans
le plus petit cadre, rien n'est retiré du pied, et ce qui ne se dérive pas lève.
"""

import json
import re

import plotly.graph_objects as go
import pytest

from demonstrateur import compile_etude, viz
from demonstrateur.viz import (ETROIT_DISPO_PX, ETROIT_MARGE_GAUCHE_PX, ETROIT_TAILLES,
                               ETROIT_TRACE_MIN_PX, SEUIL_ETROIT_PX, disposition_etroite,
                               insecables, largeur_px, preparer_figure, script_etroit)

SOURCE = "EDF — Open Data Groupe EDF (Corse & Outre-mer)"
NOTE = ("Moyennes horaires : un maximum instantané peut les dépasser. Les deux hivers de "
        "bord du jeu<br>sont tronqués par ses dates de début et de fin, donc exclus.")


def _courbes(titre="Le renouvelable atteint son maximum autour de midi"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1, 2], y=[10, 40, 20], name="Thermique",
                             text=["10 %", "", "20 %"], mode="lines+markers+text"))
    fig.add_trace(go.Scatter(x=[0, 1, 2], y=[5, 30, 15],
                             name="Sardaigne — rapporté à sa génération locale"))
    fig.update_layout(title=dict(text=titre), yaxis=dict(title="Part du mix (%)"),
                      xaxis=dict(title="Heure légale"),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
                      margin=dict(t=200, b=330, l=116, r=56), height=800)
    preparer_figure(fig, SOURCE, "2026-07-22",
                    "Moyenne heure par heure, Corse 2019-2024.<br>12-13 h : 35 % de "
                    "renouvelable décentralisé, 48 % avec les grands barrages.", NOTE)
    return fig


def _barres_h(libelles):
    fig = go.Figure(go.Bar(y=libelles, x=[55, 66], orientation="h", name="Thermique"))
    fig.update_layout(title=dict(text="Corse : plus d'eau, Sardaigne : plus de vent"),
                      margin=dict(t=150, b=330, l=116, r=56), height=680)
    preparer_figure(fig, SOURCE, "2026-07-22", "Part de chaque source — 2024.")
    return fig


def _lignes(e: dict) -> list[tuple[str, int]]:
    """Toutes les lignes de texte de la mise en page étroite, avec leur corps."""
    d = e["disposition"]
    lignes = [(li, d["title"]["font"]["size"]) for li in d["title"]["text"].split("<br>")]
    st = d["title"]["subtitle"]
    lignes += [(li, st["font"]["size"]) for li in st["text"].split("<br>") if li]
    for a in d["annotations"]:
        lignes += [(li, a["font"]["size"]) for li in a["text"].split("<br>")]
    return lignes


def test_chaque_ligne_tient_dans_le_plus_petit_cadre():
    """Contre-mesure indépendante de la dérivation : on relit le texte posé, ligne à
    ligne, au corps où il s'affiche."""
    e = disposition_etroite(_courbes(), SOURCE, "2026-07-22", NOTE)
    trop = [(li, t) for li, t in _lignes(e)
            if largeur_px(li.replace(" ", " "), t) > ETROIT_DISPO_PX]
    assert not trop
    noms = [n for n in e["traces"]["name"] if n]
    assert all(largeur_px(li, ETROIT_TAILLES["legende"]) <= ETROIT_DISPO_PX - 44
               for n in noms for li in n.split("<br>"))
    assert "<br>" in noms[1], "le nom long de la légende aurait dû se replier"


def test_le_pied_est_garde_en_entier():
    """Le pied porte le sourçage obligatoire et les réserves : on le replie, on n'en
    retire rien."""
    e = disposition_etroite(_courbes(), SOURCE, "2026-07-22", NOTE)
    pied = e["disposition"]["annotations"][-1]["text"]
    a_plat = re.sub(r"\s+", " ", pied.replace("<br>", " ").replace(" ", " "))
    assert f"Source : {SOURCE} — données collectées le 2026-07-22" in a_plat
    assert re.sub(r"\s+", " ", NOTE.replace("<br>", " ")) in a_plat
    assert pied.count("<br>") >= 4 and e["disposition"]["annotations"][-1]["font"]["size"] == 16


def test_legende_au_dessus_titre_d_axe_a_l_horizontale_marges_figees():
    e = disposition_etroite(_courbes(), SOURCE, "2026-07-22", NOTE)
    d = e["disposition"]
    assert d["legend"]["orientation"] == "v" and d["legend"]["yref"] == "container"
    assert d["yaxis.title.text"] == "" and d["yaxis.automargin"] is False
    titres = [a for a in d["annotations"] if a["text"] == "Part du mix (%)"]
    assert titres and titres[0]["yref"] == "y domain"
    m = d["margin"]
    assert m["autoexpand"] is False and m["l"] == ETROIT_MARGE_GAUCHE_PX
    assert d["height"] == e["hauteur"]
    assert e["hauteur"] - m["t"] - m["b"] >= ETROIT_TRACE_MIN_PX
    assert e["traces"]["textfont.size"] == [ETROIT_TAILLES["valeurs"], None]


def test_un_titre_ne_commence_jamais_par_deux_points():
    """« Dépendance corse / : 86 % » le 01/11/2026 : l'espace insécable, recopiée en
    espace ordinaire, ne retenait plus « : » ni « % » contre le mot qui les précède."""
    assert insecables("corse : 86 %") == "corse : 86 %"
    titre = "Dépendance corse : 86 % de l'énergie, 68 % de l'électricité"
    e = disposition_etroite(_courbes(titre), SOURCE, "2026-07-22")
    lignes = e["disposition"]["title"]["text"].split("<br>")
    assert len(lignes) > 1
    assert not [li for li in lignes if li.startswith((":", "%", " "))]


def test_des_libelles_de_barres_trop_longs_exigent_un_reglage():
    with pytest.raises(ValueError, match="réglage"):
        disposition_etroite(_barres_h(["Toute l'énergie consommée (OREGES, 2020)",
                                       "L'électricité consommée (EDF, 2019-2024)"]),
                            SOURCE, "2026-07-22")
    e = disposition_etroite(_barres_h(["Corse", "Sardaigne"]), SOURCE, "2026-07-22")
    assert ETROIT_MARGE_GAUCHE_PX < e["disposition"]["margin"]["l"] <= 120


def test_les_reglages_fusionnent_retirent_ajoutent_et_sont_mesures():
    fig = _courbes()
    fig.add_annotation(x=1, y=40, text="<b>2022 · l'eau au plus bas</b>", showarrow=False)
    fig.add_annotation(x=2, y=20, text="à retirer", showarrow=False)
    # preparer_figure a posé le pied AVANT : on le remet en dernier, comme à l'export.
    annotations = list(fig.layout.annotations)
    fig.layout.annotations = annotations[1:] + annotations[:1]
    ajout = dict(text="Ajout pleine largeur", xref="paper", x=0, xanchor="left",
                 xshift=-(ETROIT_MARGE_GAUCHE_PX - 8), yref="paper", y=1, showarrow=False,
                 font=dict(size=14))
    e = disposition_etroite(fig, SOURCE, "2026-07-22", reglages=dict(
        annotations={0: dict(yshift=-6), 1: None}, ajouts=[ajout],
        disposition={"bargap": 0.5}, traces={"text": [None, None]}))
    textes = [a["text"] for a in e["disposition"]["annotations"]]
    assert "à retirer" not in textes and "Ajout pleine largeur" in textes
    assert e["disposition"]["annotations"][0]["yshift"] == -6
    assert e["disposition"]["bargap"] == 0.5 and e["traces"]["text"] == [None, None]
    with pytest.raises(ValueError, match="plus large"):
        disposition_etroite(fig, SOURCE, "2026-07-22", reglages=dict(
            ajouts=[dict(ajout, text="Un ajout bien trop long pour tenir sur une seule "
                                     "ligne de téléphone")]))


# --- Export, script et étude ---------------------------------------------------------


def _exporter(tmp_path, monkeypatch, fig, **k) -> str:
    monkeypatch.setattr(viz, "OUTPUTS", tmp_path)
    monkeypatch.setattr(compile_etude, "OUTPUTS", tmp_path)
    viz.export_html(fig, "t_essai", SOURCE, "2026-07-22", **k)
    return (tmp_path / "t_essai.html").read_text(encoding="utf-8")


def test_l_export_pose_la_mise_en_page_et_l_etude_adapte_son_cadre(tmp_path, monkeypatch):
    fig = go.Figure(go.Scatter(x=[0, 1], y=[1, 2], name="Thermique"))
    fig.update_layout(title=dict(text="Même en été, le solaire ne dépasse pas le thermique"),
                      margin=dict(t=144, b=330, l=116, r=56), height=760)
    page = _exporter(tmp_path, monkeypatch, fig, sous_titre="Une journée d'été.", note=NOTE)
    assert '"etroit"' in page and "gd.getBoundingClientRect().width + 2 * MARGE < E.seuil" in page
    hauteur = fig.layout.meta["etroit"]["hauteur"]
    iframe = compile_etude._iframe("t_essai")
    assert 'class="adaptable"' in iframe and f"--hauteur-etroite:{hauteur + 16}px" in iframe


def test_une_figure_peut_refuser_la_mise_en_page_etroite(tmp_path, monkeypatch):
    fig = go.Figure(go.Scatter(x=[0, 1], y=[1, 2]))
    page = _exporter(tmp_path, monkeypatch, fig, etroit=False)
    assert '"etroit"' not in page and "innerWidth" not in page


def test_une_figure_qui_a_sa_mise_en_page_la_garde(tmp_path, monkeypatch):
    """T1 déclare la sienne, écrite à la main : l'export n'y touche pas."""
    propre = {"seuil": SEUIL_ETROIT_PX, "hauteur": 1080, "disposition": {"height": 1080}}
    fig = go.Figure(go.Scatter(x=[0, 1], y=[1, 2]))
    fig.update_layout(meta=dict(etroit=propre))
    page = _exporter(tmp_path, monkeypatch, fig, script_apres="/* script propre */")
    assert fig.layout.meta["etroit"] == propre
    assert "/* script propre */" in page and "Plotly.update" not in page


def test_le_script_choisit_sans_composer_de_texte():
    """Le script lit la mise en page dans la page ; un texte écrit dans le JavaScript
    échapperait à toute mesure. Il redessine une barre de couleur qui change
    d'orientation, que Plotly ne recalcule pas (t5, 01/11/2026)."""
    s = script_etroit("t5_ecretement_solaire")
    assert json.dumps("t5_ecretement_solaire") in s
    assert "gd.layout.meta && gd.layout.meta.etroit" in s
    assert "Plotly.update" in s and "Plotly.newPlot" in s and "colorbar." in s
    assert not re.search(r"Source|données|relevé", s)


# --- Figures air et pleine largeur (02/11/2026) ------------------------------------


def test_un_nombre_ne_se_separe_pas_de_son_unite():
    """« 120 / µg/m³ » se lisait sur deux lignes dans le pied d'a1."""
    assert insecables("dépasse 120 µg/m³ au-delà de 35 °C") == (
        "dépasse 120 µg/m³ au-delà de 35 °C")


def test_un_titre_d_axe_horizontal_trop_long_se_replie_et_la_zone_grandit():
    """a1 : « Journées où l'ozone dépasse l'objectif de qualité (120 µg/m³), station par
    station » sortait de la figure. Un titre court ne bouge pas."""
    court = disposition_etroite(_courbes(), SOURCE, "2026-07-22")
    assert "xaxis.title.text" not in court["disposition"]
    fig = _courbes()
    fig.update_layout(xaxis=dict(title=dict(
        text="Journées où l'ozone dépasse l'objectif de qualité (120 µg/m³), station par "
             "station")))
    e = disposition_etroite(fig, SOURCE, "2026-07-22")
    titre = e["disposition"]["xaxis.title.text"]
    assert "<br>" in titre and "120 µg/m³" in titre
    assert all(largeur_px(li.replace(" ", " "), ETROIT_TAILLES["axe"]) <= ETROIT_DISPO_PX
               for li in titre.split("<br>"))
    assert e["disposition"]["margin"]["b"] > court["disposition"]["margin"]["b"]


def test_les_libelles_longs_passent_au_dessus_des_barres():
    """Le réglage d'a1 et a4 : libellés en annotations au-dessus de chaque barre, axe
    vertical sans libellé, et une bande trop étroite pour une ligne lève."""
    libelles = ["Bastia Montesoro (périurbaine)", "Venaco (rurale régionale)"]
    reglages = viz.libelles_au_dessus(_barres_h(libelles), trace_px=160, ecart=0.55)
    e = disposition_etroite(_barres_h(libelles), SOURCE, "2026-07-22", reglages=reglages)
    textes = [a["text"] for a in e["disposition"]["annotations"]]
    assert all(lib in textes for lib in libelles)
    assert e["disposition"]["yaxis.showticklabels"] is False
    assert e["disposition"]["margin"]["l"] < ETROIT_MARGE_GAUCHE_PX
    with pytest.raises(ValueError, match="place d'une ligne"):
        viz.libelles_au_dessus(_barres_h(libelles), trace_px=60, ecart=0.55)


def test_un_titre_d_axe_vertical_peut_etre_reecrit_en_etroit():
    """a3 : ses graduations imposées perdent leur « % », le titre d'axe le porte."""
    e = disposition_etroite(_courbes(), SOURCE, "2026-07-22",
                            reglages=dict(titres_y={"yaxis": "Part du mix (en %)"}))
    assert "Part du mix (en %)" in [a["text"] for a in e["disposition"]["annotations"]]


def test_le_script_mesure_la_figure_et_non_la_fenetre():
    """Dans la page air, sans iframe, la fenêtre peut dépasser le seuil quand la figure
    n'en a pas la largeur (862 px à 900 px d'écran : sous-titre d'a3 coupé). La figure
    plus deux marges de page, c'est exactement la largeur du cadre d'un visuel."""
    s = script_etroit("a3")
    assert "MARGE = 8" in s and "getBoundingClientRect().width + 2 * MARGE < E.seuil" in s
    assert "window.innerWidth" not in s


def test_le_script_laisse_la_largeur_au_cadre_et_rend_la_page_large_a_l_identique():
    """Trois défauts trouvés le 02/11/2026 en redimensionnant SANS recharger, ce qu'aucun
    banc ne faisait : (1) la hauteur imposée figeait la largeur — un téléphone ouvert en
    paysage puis tourné en portrait gardait des figures de 684 px dans des cadres de
    304 ; (2) l'enveloppe de Plotly gardait la hauteur large — dans la page air, le bas
    de la figure passait derrière un défilement intérieur ; (3) l'étendue d'axe imposée
    par l'étroite, rétablie seule, figeait l'axe large d'a1."""
    s = script_etroit("a1")
    assert "d.autosize = true;" in s and "d.width = null;" in s
    assert "Plotly.Plots.resize(gd)" in s
    assert "ENVELOPPE.style.height" in s
    assert "autorange" in s


def test_la_page_air_joint_la_bascule_aux_figures_qui_en_ont_une(monkeypatch):
    from demonstrateur import page_air

    monkeypatch.setattr(page_air.fa, "phrase_actualite_courte", lambda: "")
    avec = go.Figure(go.Scatter(x=[0, 1], y=[1, 2]))
    avec.update_layout(meta=dict(etroit={"seuil": SEUIL_ETROIT_PX, "hauteur": 800,
                                         "traces": {}, "disposition": {"height": 800}}))
    page = page_air._html([("<p>a</p>", "a1", avec), ("<p>b</p>", "a2", go.Figure())],
                          "01/01/2026", "plotly-test.min.js")
    assert page.count("getBoundingClientRect") == 1 and json.dumps("a1") in page


def test_sous_le_seuil_les_figures_prennent_la_largeur_de_l_ecran(monkeypatch):
    """À 320 px d'écran, l'étude ne laissait que 264 px à une figure mesurée pour 304.
    Les deux pages élargissent la figure, pas le texte ; l'étude part de la largeur de
    l'article, jamais de `100vw`, qui compte la barre de défilement. Et rien ne fait
    défiler la page de côté : ni le tableau des sources de l'étude (406 px), qui défile
    seul, ni le lexique de la page air, dont la colonne descend sous 19rem."""
    from demonstrateur import page_air

    seuil = f"@media (max-width:{SEUIL_ETROIT_PX - 0.02:.2f}px)"
    css = compile_etude._CSS_ETROIT
    assert (seuil + "{.visuel{width:max(calc(100% + 2.5rem),calc(100vw - 2.5rem))}"
            "table{display:block;overflow-x:auto}}") in css
    monkeypatch.setattr(page_air.fa, "phrase_actualite_courte", lambda: "")
    page = page_air._html([], "01/01/2026", "plotly-test.min.js")
    assert seuil in page and "margin-left:calc(7px - 1.2rem)" in page
    assert "minmax(min(19rem, 100%), 1fr)" in page
