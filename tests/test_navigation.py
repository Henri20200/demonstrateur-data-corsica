"""Verrous de la passe navigation : les quatre propriétés arrêtées, et rien d'autre.

Ces verrous tiennent de la NAVIGATION, pas de la mise en forme : aucun ne dit où placer
un lien, comment le styler, ni dans quel ordre. Ils disent qu'on peut aller quelque part.

Ils rendent les cinq pages **sans données** : chaque module expose un gabarit
(`_html`, `rendre_page`) qu'on peut appeler avec des chiffres factices. C'est délibéré —
un verrou de navigation qui se sauterait faute de Parquet ne prédirait rien dans le job
`valider`, et la navigation ne dépend d'aucune donnée. Le seul verrou qui lit `outputs/`
est celui des titres d'iframe, et il ne lit que des fichiers versionnés.

Deux points où le verrou nomme une forme, parce qu'une propriété doit être repérable pour
être tenue : le sommaire est un `<nav class="sommaire">` et la navigation de pied vit dans
le `<footer>`. Ce sont les éléments sémantiques justes — ce qui les rend repérables par un
lecteur d'écran les rend repérables ici.
"""

from __future__ import annotations

import json
import re

import plotly.graph_objects as go
import pytest

from demonstrateur import accueil, compile_etude, note_air, note_elec, page_air
from demonstrateur import figures_air as fa
from demonstrateur.config import ETUDE_SOURCE, OUTPUTS

# --- Les cinq pages du livrable, et ce que chacune doit pouvoir joindre ---------------

ACCUEIL = "index.html"
ETUDE = "etude.html"
AIR = "air_ozone.html"
NOTE_ETUDE = "t0_note_methodologique.html"
NOTE_AIR = "a0_note_methodologique.html"

# Page courante -> pages qu'elle doit permettre de rejoindre, en plus de l'accueil.
# Règle : accueil, étude parente, autre sujet, note méthodologique — moins la page
# courante elle-même. Un lien vers soi n'est pas une navigation, c'est du bruit.
CONTEXTE = {
    ETUDE: {AIR, NOTE_ETUDE},
    AIR: {ETUDE, NOTE_AIR},
    NOTE_ETUDE: {ETUDE, AIR},
    NOTE_AIR: {AIR, ETUDE},
}
FILLES = tuple(CONTEXTE)


class _Rien(int):
    """Un zéro qui répond aussi à n'importe quelle clé, à n'importe quelle profondeur.

    Les notes méthodologiques recalculent leurs chiffres depuis les Parquet ; leur
    GABARIT, lui, n'en a pas besoin. Ce faux dictionnaire rend le gabarit seul, sans que
    le verrou ait à connaître — ni à suivre — la liste des clés que la note publie.

    Il hérite d'`int` et non de `dict` : la note électricité calcule dans son gabarit
    (`{c["an2"] - c["an1"] + 1} années pleines`), et un faux dictionnaire aurait demandé
    de réimplémenter l'arithmétique et le formatage. Un entier les a déjà.
    """

    def __getitem__(self, cle):
        return self

    def get(self, cle, defaut=None):
        return self

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0


def _page_air_rendue(monkeypatch) -> str:
    """La page air rendue avec cinq sections vides — le gabarit, sans les figures.

    L'encart d'actualité lit les données ; il est neutralisé, il n'est pas l'objet ici.
    Les identifiants de section, eux, viennent du module : c'est ce qui fait que le
    sommaire testé est celui de la vraie page et non celui du test.
    """
    monkeypatch.setattr(fa, "phrase_actualite_courte", lambda: "")
    blocs = [(f"<p>section {sid}</p>", sid, go.Figure()) for sid in page_air.SECTIONS]
    return page_air._html(blocs, "01/01/2026")


@pytest.fixture
def rendues(monkeypatch):
    """Rend une page à la demande — `rendues(ETUDE)`.

    Paresseux, et c'est le point : construire les cinq d'un coup ferait échouer les
    vingt et un verrous au premier gabarit cassé, tous avec la même erreur de fixture.
    Chaque propriété doit pouvoir échouer pour sa propre raison, sinon le verrou dit
    seulement « quelque chose ne va pas ».
    """
    constructeurs = {
        ACCUEIL: lambda: accueil._html("31/08/2026", [], 0, 0),
        ETUDE: lambda: compile_etude.rendre_page(ETUDE_SOURCE.read_text(encoding="utf-8")),
        AIR: lambda: _page_air_rendue(monkeypatch),
        NOTE_ETUDE: lambda: note_elec._html(_Rien()),
        NOTE_AIR: lambda: note_air._html(_Rien()),
    }
    cache: dict[str, str] = {}

    def rendre(page: str) -> str:
        if page not in cache:
            cache[page] = constructeurs[page]()
        return cache[page]

    return rendre


def _liens(html: str) -> set[str]:
    """Cibles des liens sortants — les ancres internes ne sont pas de la navigation."""
    return {h for h in re.findall(r'href="([^"]+)"', html) if not h.startswith("#")}


# --- Propriété 1 : on peut toujours revenir, et rejoindre son contexte ----------------


@pytest.mark.parametrize("page", FILLES)
def test_chaque_page_ramene_a_l_accueil(rendues, page):
    """Le défaut principal mesuré le 31/08/2026 : les quatre pages filles étaient des
    culs-de-sac. `etude.html` et `air_ozone.html` portaient un seul lien sortant, à 99 %
    de leur hauteur ; les deux notes méthodologiques n'en portaient aucun. Un lecteur
    qui arrive en direct depuis la vitrine ne pouvait revenir nulle part."""
    assert ACCUEIL in _liens(rendues(page)), (
        f"{page} ne ramène pas à l'accueil — la page est un cul-de-sac pour qui y arrive "
        "en direct, ce qui est le cas normal depuis la vitrine"
    )


@pytest.mark.parametrize("page", FILLES)
def test_chaque_page_rejoint_son_contexte(rendues, page):
    """Revenir à l'accueil ne suffit pas : depuis une étude on doit joindre l'autre sujet
    et sa note, depuis une note son étude parente."""
    manquants = CONTEXTE[page] - _liens(rendues(page))
    assert not manquants, (
        f"{page} ne permet pas de rejoindre {sorted(manquants)} — contexte attendu : "
        f"{sorted(CONTEXTE[page])}"
    )


@pytest.mark.parametrize("page", (ACCUEIL, *FILLES))
def test_aucune_page_ne_pointe_vers_elle_meme(rendues, page):
    """Un gabarit commun qui exposerait les quatre entrées partout ferait figurer, sur la
    note méthodologique, un lien « Note méthodologique » vers la page courante. Le pied
    expose selon le contexte, il ne récite pas une liste."""
    assert page not in _liens(rendues(page)), (
        f"{page} porte un lien vers elle-même — le pied de navigation récite sa liste au "
        "lieu de l'adapter à la page courante"
    )


def test_l_accueil_mene_aux_quatre_pages_filles(rendues):
    """La propriété inverse, et elle était déjà tenue : l'accueil reste la racine."""
    manquantes = set(FILLES) - _liens(rendues(ACCUEIL))
    assert not manquantes, f"l'accueil ne mène pas à {sorted(manquantes)}"


# --- Propriété 2 : l'étude s'ancre et se sommaire -------------------------------------


def _titres(html: str) -> list[tuple[str, str, str]]:
    """(niveau, attributs, texte) de chaque h2/h3, dans l'ordre du document."""
    return [(m.group(1), m.group(2), re.sub(r"<[^>]+>", "", m.group(3)).strip())
            for m in re.finditer(r"<(h[23])([^>]*)>(.*?)</\1>", html, re.S)]


def _ancres(html: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', html)


def test_chaque_titre_de_l_etude_porte_une_ancre_unique(rendues):
    """27 titres, zéro ancre au 31/08/2026 : impossible de renvoyer quelqu'un au § 6
    « Deux façons de compter les renouvelables ». Les h3 s'ancrent aussi — le lien
    profond est le vrai gain, et il ne coûte pas un mot de plus au sommaire."""
    titres = _titres(rendues(ETUDE))
    sans_ancre = [t for _, attrs, t in titres if 'id="' not in attrs]
    assert not sans_ancre, f"titres sans ancre : {sans_ancre}"

    ids = [re.search(r'id="([^"]+)"', attrs).group(1) for _, attrs, _ in titres]
    doublons = sorted({i for i in ids if ids.count(i) > 1})
    assert not doublons, (
        f"ancres en double : {doublons} — un lien profond ne désignerait plus une section"
    )


def test_le_sommaire_de_l_etude_liste_les_six_sections(rendues):
    """Les six h2 au sommaire, les h3 ancrables sans y entrer : un sommaire de 27 entrées
    ne se lit plus. L'ordre est celui du document, sinon le sommaire ment sur le parcours."""
    html = rendues(ETUDE)
    m = re.search(r'<nav class="sommaire".*?</nav>', html, re.S)
    assert m, 'l\'étude n\'a pas de sommaire (`<nav class="sommaire">`)'
    sommaire = m.group(0)

    vises = re.findall(r'href="#([^"]+)"', sommaire)
    h2 = [re.search(r'id="([^"]+)"', attrs).group(1)
          for niveau, attrs, _ in _titres(html) if niveau == "h2"]
    assert vises == h2, (
        f"le sommaire vise {vises} alors que les sections de l'étude sont {h2} — "
        "il doit lister les h2, tous les h2, et dans l'ordre du document"
    )


@pytest.mark.parametrize("page", (ETUDE, AIR))
def test_les_liens_internes_pointent_sur_une_ancre_existante(rendues, page):
    """Un sommaire dont une entrée ne mène nulle part est pire que pas de sommaire :
    il se lit comme une promesse."""
    html = rendues(page)
    ancres = set(_ancres(html))
    morts = sorted({a for a in re.findall(r'href="#([^"]+)"', html) if a not in ancres})
    assert not morts, f"{page} : liens internes sans ancre correspondante : {morts}"


# --- Propriété 3 : le sommaire air cible les cinq figures -----------------------------


def test_le_sommaire_air_cible_les_cinq_figures(rendues):
    """Les ancres `a1`…`a5` existaient déjà au 31/08/2026 — rien ne pointait dessus.
    C'était le geste le moins cher de la passe."""
    assert tuple(page_air.SECTIONS) == ("a1", "a2", "a3", "a4", "a5"), (
        f"sections de la page air : {tuple(page_air.SECTIONS)}"
    )
    m = re.search(r'<nav class="sommaire".*?</nav>', rendues(AIR), re.S)
    assert m, 'la page air n\'a pas de sommaire (`<nav class="sommaire">`)'
    assert re.findall(r'href="#([^"]+)"', m.group(0)) == list(page_air.SECTIONS), (
        "le sommaire air ne vise pas exactement les cinq sections, dans l'ordre du récit"
    )


# --- Propriété 4 : chaque iframe s'annonce par le titre de sa figure ------------------


def _sans_balises(txte: str) -> str:
    """Le titre d'une figure peut porter du balisage Plotly (`<b>soleil</b>` en T1) et
    des retours à la ligne : un attribut `title` ne prend que du texte."""
    return " ".join(re.sub(r"<[^>]+>", " ", txte).split())


def _titre_humain(nom: str) -> str:
    """Titre de la figure, lu dans SON HTML par un chemin différent de celui du
    générateur — première occurrence de `"title":{"text":…}`, la figure venant avant ses
    axes dans le layout sérialisé. Deux chemins vers la même chaîne : c'est ce qui fait
    du verrou un recoupement et non une tautologie.

    `json.loads` sur le littéral, jamais la chaîne brute : le runner Linux échappe les
    accents en `\\uXXXX` (constat du 29/08/2026), et une lecture brute publierait
    « En juillet, la hausse est surtout marqu\\u00e9e » dans l'attribut.
    """
    html = (OUTPUTS / f"{nom}.html").read_text(encoding="utf-8")
    m = re.search(r'"title":\{"text":("(?:[^"\\]|\\.)*")', html)
    assert m, f"aucun titre trouvé dans le visuel {nom}.html"
    return _sans_balises(json.loads(m.group(1)))


def _iframes(html: str) -> list[tuple[str, str]]:
    """(visuel visé, titre annoncé) pour chaque iframe de la page."""
    paires = []
    for balise in re.findall(r"<iframe[^>]*>", html):
        src = re.search(r'src="([^"]+)\.html"', balise)
        titre = re.search(r'title="([^"]*)"', balise)
        paires.append((src.group(1) if src else "", titre.group(1) if titre else ""))
    return paires


def test_chaque_iframe_porte_le_titre_humain_de_son_visuel(rendues):
    """Au 31/08/2026 les dix iframes s'annonçaient « Visualisation : t2b_surcroit_horaire » :
    un lecteur d'écran lisait l'identifiant de fichier.

    Le titre ne se REDÉCLARE pas dans la page — il se lit chez le visuel, comme sa hauteur
    (`_hauteur_visuel` : « le visuel reste la source de vérité »). Une figure retitrée
    entraîne son iframe sans que personne y pense.
    """
    paires = _iframes(rendues(ETUDE))
    assert paires, "aucune iframe dans l'étude — le verrou ne mesurerait rien"
    for nom, titre in paires:
        attendu = _titre_humain(nom)
        assert titre == attendu, (
            f"iframe de {nom} : annoncée « {titre} », alors que la figure s'intitule "
            f"« {attendu} »"
        )


def test_les_titres_d_iframe_ne_sont_ni_generiques_ni_techniques(rendues):
    """`title != nom_de_fichier` est trop faible : `title="Visualisation"` partout le
    passerait. Ce qui distingue un titre utile, c'est qu'il distingue — et qu'il ait
    traversé le décodage JSON."""
    paires = _iframes(rendues(ETUDE))
    titres = [t for _, t in paires]
    repetes = sorted({t for t in titres if titres.count(t) > 1})
    assert not repetes, (
        f"titres d'iframe non distincts : {repetes} — un libellé générique ne dit pas au "
        "lecteur ce qu'il va trouver"
    )
    for nom, titre in paires:
        assert nom not in titre, f"l'iframe de {nom} annonce son identifiant de fichier"
        assert "\\u" not in titre, (
            f"iframe de {nom} : « {titre} » — titre lu sans décodage JSON, les accents "
            "échappés par le runner Linux sortiraient tels quels"
        )
    assert any(any(ord(c) > 127 for c in t) for t in titres), (
        "aucun titre accentué parmi les iframes : le décodage n'est pas éprouvé — "
        "huit des dix titres de l'étude portaient un accent au 31/08/2026"
    )
