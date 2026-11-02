"""Export des visualisations en HTML déployable en iframe sans dépendance tierce.

Plotly n'est pas chargé depuis un CDN : un bundle nommé par son empreinte est écrit dans
outputs/ et partagé par tous les visuels — le dossier outputs/ se déploie d'un bloc.

La mention de source « Source … — données collectées le … » est câblée dans
l'export : le sourçage n'est pas optionnel. Le style (palette énergie lisible,
fond neutre clair, sans-serif) est porté par le template appliqué à chaque figure.
"""

from __future__ import annotations

import json
import hashlib
import re
import textwrap
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

from .config import BUILD_FILE, MANIFEST_FILE, OUTPUTS

# --- Palette (validée en distinction + couleurs choisies pour les filières) ---
PALETTE = {
    "page":      "#F7F6F3",  # fond de page (neutre chaud léger)
    "surface":   "#FCFCFB",  # surface de figure
    "ink":       "#1A1A18",  # texte primaire
    "ink_soft":  "#4A4A48",  # texte secondaire
    "muted":     "#8A8781",  # axes / labels atténués
    "rule":      "#E4E2DB",  # filet / grille
    "rule_soft": "#EEECE6",  # grille douce
    "solaire":   "#B07A2B",  # or — le solaire (ligne T3)
    "renouv":    "#3B6B57",  # vert forêt — renouvelable décentralisé
    "hydro":     "#7CA593",  # sauge — grande hydraulique
    "thermique": "#1B2238",  # bleu-nuit — thermique (fossile)
    "imports":   "#5B5566",  # violet-gris — interconnexions
    "accent":    "#A23D2A",  # terracotta — repère / emphase, et l'OZONE du sujet air
    "azote":     "#2E6E9E",  # bleu — le NO2, antagoniste de l'ozone (titre 3 de l'air)
}

# Couple catégoriel du sujet air, VALIDÉ au script (mode light, surface #FCFCFB) :
# bande de clarté, plancher de chroma, séparation CVD ΔE 17,9 (deutan) et 23,0 en vision
# normale, contraste ≥ 3:1. Le bleu-nuit « thermique » de l'étude électricité a été essayé
# d'abord et REFUSÉ pour cet emploi : trop sombre et trop désaturé, il échoue au plancher de
# chroma et « lit comme du gris » dès qu'il sert de série à part entière plutôt que de
# couleur sémantique du fossile.
AIR_OZONE = PALETTE["accent"]
AIR_AZOTE = PALETTE["azote"]

SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# Retrait du pied de figure par rapport au bord gauche de la figure (px). Le pied ne suit
# pas la marge gauche du tracé : sinon une figure à libellés longs le repousserait vers
# la droite, où il déborde. Cf. `preparer_figure`.
PIED_BORD_PX = 20

# Rampe séquentielle « or solaire » (magnitude, heatmap T5) : clarté monotone,
# pas >= 0.06, teinte unique — validée (validateur dataviz, mode ordinal). Le bout
# clair reste volontairement proche de la surface (un zéro doit se lire « rien ») :
# compensé par étiquettes directes sur les fortes valeurs, tooltip et colorbar.
RAMPE_SOLAIRE = ["#F0E1BD", "#DEC28A", "#C9A057", "#B07A2B", "#8D5E1E", "#6A4616"]
# Teinte « aucun événement » des cellules à zéro : neutre chaud, hors rampe, pour
# distinguer « rien » de « un peu » (deux natures, pas deux magnitudes).
NEUTRE_ZERO = "#EFEDE8"


def template() -> go.layout.Template:
    """Template Plotly : fond neutre, sans-serif, texte lisible, filets discrets.

    Lisibilité : étiquettes d'axes et légende en **encre pleine** (pas de gris) et
    généreusement dimensionnées ; seuls la grille et les filets restent discrets. Le
    tooltip est blanc sur encre — contraste garanti quelle que soit la couleur tracée.
    """
    # Échelle typographique (relevée le 22/07/2026, demande de lisibilité) : plancher
    # 16px pour tout texte — pied de source compris ; ticks/légende/étiquettes à 17,
    # titres d'axes à 19. Encre pleine partout (contraste ~18:1, WCAG AAA) — seuls
    # grille et filets sont discrets.
    axis = dict(
        gridcolor=PALETTE["rule_soft"], griddash="solid", zeroline=False,
        linecolor=PALETTE["rule"], ticks="outside", tickcolor=PALETTE["rule"],
        tickfont=dict(family=SANS, size=17, color=PALETTE["ink"]),
        title=dict(font=dict(family=SANS, size=19, color=PALETTE["ink"]), standoff=18),
    )
    return go.layout.Template(layout=dict(
        paper_bgcolor=PALETTE["surface"], plot_bgcolor=PALETTE["surface"],
        font=dict(family=SANS, size=17, color=PALETTE["ink"]),
        title=dict(
            font=dict(family=SANS, size=28, color=PALETTE["ink"]),
            x=0.01, xanchor="left",
            subtitle=dict(font=dict(family=SANS, size=18, color=PALETTE["ink_soft"])),
        ),
        colorway=[PALETTE["solaire"], PALETTE["renouv"], PALETTE["hydro"],
                  PALETTE["imports"], PALETTE["thermique"]],
        xaxis=axis, yaxis=axis,
        legend=dict(font=dict(family=SANS, size=17, color=PALETTE["ink"]),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=144, b=170, l=116, r=56),
        hoverlabel=dict(bgcolor=PALETTE["ink"], bordercolor=PALETTE["ink"],
                        font=dict(family=SANS, size=16, color="#FFFFFF")),
    ))


LARGEUR_PIED = 64
"""Caractères par ligne du pied de figure, mesuré à 620 px de large, corps 16."""


def replier_pied(texte: str, largeur: int = LARGEUR_PIED) -> str:
    """Replie un texte de pied en lignes courtes, sur les espaces.

    Les annotations Plotly ne replient PAS le texte : au-delà de la largeur de la
    figure, la fin de la phrase est rognée — silencieusement, et invisible tant qu'on
    développe sur écran large. C'est arrivé aux notes de T5 et à la source de T6.
    Le repli est donc câblé dans l'export, comme la mention de source elle-même : un
    appelant ne peut plus produire un pied tronqué par distraction.

    Les `<br>` déjà présents sont respectés — qui coupe à un endroit voulu garde la main.
    """
    lignes = []
    for bloc in texte.split("<br>"):
        lignes.extend(textwrap.wrap(bloc, largeur) or [""])
    return "<br>".join(lignes)


# --- Mesure des titres : un titre Plotly ne se replie JAMAIS ------------------
# Le pied de figure est replié par `replier_pied` ; le titre et le sous-titre, eux,
# sont rendus tels quels et se font rogner sans un mot d'avertissement — invisible
# tant qu'on relit sur écran large. Huit des dix figures de l'étude ont vécu ainsi
# (constat du 06/08/2026). D'où ce gabarit, qui rend la largeur MESURABLE, donc
# vérifiable en test.
#
# Ratios largeur/corps relevés sur Segoe UI (la `system-ui` de Windows, celle qui
# rend nos figures ici) et figés dans le code : un test qui lirait la police du
# système donnerait un résultat différent d'un runner Linux à un poste Windows, et
# ne verrouillerait plus rien. Le comptage de caractères, lui, surestimait de 15 %.
GABARIT = {
    0.217: ",.:;·", 0.229: "‘’", 0.230: "'", 0.239: "|", 0.242: "ijlîï",
    0.266: "IÎÏ", 0.268: "`", 0.274: " ", 0.284: "!", 0.302: "()[]{}",
    0.313: "f", 0.339: "t", 0.348: "r", 0.357: "J", 0.366: "²³",
    0.377: "°“”", 0.379: "\\", 0.390: "/", 0.392: '"', 0.400: "-",
    0.415: "_", 0.417: "*", 0.424: "s", 0.448: "?", 0.452: "z",
    0.459: "x", 0.462: "cç", 0.471: "L", 0.479: "v", 0.484: "yÿ",
    0.488: "F", 0.497: "k", 0.500: "–", 0.506: "EÉÈÊË«»", 0.509: "aàâä",
    0.523: "eéèêë", 0.524: "T", 0.531: "S", 0.539: "$0123456789€", 0.553: "Y",
    0.560: "P", 0.566: "hnuùûü", 0.570: "Z", 0.573: "B", 0.577: "µ",
    0.580: "K", 0.586: "oôö", 0.588: "bp", 0.589: "dgq", 0.590: "X",
    0.591: "#", 0.598: "R", 0.619: "CÇ", 0.621: "V", 0.645: "AÀÂÄ",
    0.646: "▾▴✓⚠", 0.684: "+<=>^~×−", 0.686: "G", 0.687: "UÙÛÜ", 0.701: "D",
    0.710: "H", 0.723: "w", 0.733: "…", 0.748: "N", 0.754: "OQÔÖ",
    0.800: "&", 0.818: "%", 0.832: "æ", 0.860: "Æ", 0.861: "m",
    0.898: "M", 0.928: "œ", 0.931: "Œ", 0.934: "W", 0.955: "@",
    1.000: "—",
}
GABARIT_PAR_CAR = {car: ratio for ratio, cars in GABARIT.items() for car in cars}
GABARIT_DEFAUT = 0.60
"""Ratio d'un caractère hors table — pris large, pour que l'inconnu ne passe pas sous le radar."""

LARGEUR_VISUEL = 992
"""Largeur de RÉFÉRENCE d'affichage d'un visuel du livrable (colonne « figure » de l'étude,
page air à 62rem). C'est à elle que titres et sous-titres doivent tenir. Elle vit ici, avec
la mesure qui l'utilise : sans point fixe écrit quelque part, chaque retouche de titre se
calibrerait sur la fenêtre de qui la relit."""

TAILLE_TITRE = 28
TAILLE_SOUS_TITRE = 18
TAILLE_PIED = 16
"""Corps du titre, du sous-titre et du pied, tels que le template les fixe."""

INTERLIGNE = 1.3
"""Interligne de Plotly (`LINE_SPACING`), pour un bloc de texte à plusieurs lignes."""

GARDE_BASSE_PX = 18
"""Sous la dernière ligne du pied : jambages, plus de quoi absorber l'écart entre
l'interligne théorique et ce que rend vraiment le navigateur. Un pied qui tient à un
pixel près ne tient pas."""

RETRAIT_TITRE_PX = 18
"""Largeur perdue par le titre : x=0.01 du conteneur, plus une garde à droite."""


def largeur_px(texte: str, taille: int) -> float:
    """Largeur rendue d'UNE ligne, en pixels. Les balises (`<b>`, `<i>`) ne comptent pas.

    Ne coupe pas sur `<br>` : à l'appelant de découper d'abord — une ligne, une mesure.
    """
    nu = re.sub(r"<[^>]+>", "", texte)
    return sum(GABARIT_PAR_CAR.get(car, GABARIT_DEFAUT) for car in nu) * taille


def lignes_de_titre(fig) -> list[tuple[str, int]]:
    """Les lignes du titre et du sous-titre d'une figure, avec leur corps.

    Lit le layout de la figure, pas le HTML : les titres d'AXES portent le même nom
    et une recherche textuelle les ramasserait, donnant des largeurs fausses.
    """
    titre = fig.layout.title
    lignes = []
    if titre and titre.text:
        lignes += [(li, TAILLE_TITRE) for li in titre.text.split("<br>")]
    if titre and titre.subtitle and titre.subtitle.text:
        lignes += [(li, TAILLE_SOUS_TITRE) for li in titre.subtitle.text.split("<br>")]
    return lignes


# --- Petit écran : une seconde mise en page, choisie chez le lecteur ------------------
# Une figure faite pour LARGEUR_VISUEL se fait rogner dans un cadre de téléphone : ses
# textes ne se replient pas. Pour une figure dont le message EST le texte (T1), c'est le
# message qui disparaît — le pourcentage reste, la période et le repère qui le bornent
# tombent hors cadre. Une telle figure peut donc déclarer, dans `layout.meta.etroit`,
# une seconde mise en page calculée et VÉRIFIÉE à la génération ; un script de la page la
# choisit selon la largeur du cadre, et l'étude donne à ce cadre la hauteur qui lui
# correspond (compile_etude). Le script choisit, il ne compose aucun texte.
SEUIL_ETROIT_PX = 900
"""Largeur de CADRE sous laquelle une figure qui en déclare une passe à sa mise en page
étroite. Une seule valeur pour la figure, qui bascule, et pour l'étude, dont le cadre
change de hauteur : deux seuils, et entre les deux le cadre couperait la figure."""

CADRE_ETROIT_MIN_PX = 320
"""Plus petit cadre pour lequel une mise en page étroite est conçue : l'étude sur un
téléphone de 360 px de large (le cadre y perd 2,5rem)."""

MARGE_PAGE_PX = 8
"""Marge du `<body>` de la page d'un visuel (défaut des navigateurs, que Plotly garde) :
la figure mesure la largeur du cadre moins deux fois cette marge."""


def replier_equilibre(texte: str, taille: int, dispo: float) -> str:
    """Replie chaque bloc (séparé par `<br>`) en lignes d'au plus `dispo` pixels,
    mesurées au gabarit, et ÉQUILIBRÉES : à nombre de lignes égal, la largeur la plus
    étroite, ce qui évite le mot orphelin en dernière ligne (« Corse ? » seul).

    Les espaces insécables (U+00A0) ne coupent pas et se mesurent comme des espaces.
    Lève si un mot seul dépasse : une ligne trop large serait rognée sans un mot.
    """
    def largeur(t: str) -> float:
        return largeur_px(t.replace(" ", " "), taille)

    def glouton(bloc: str, limite: float) -> list[str]:
        lignes, courante = [], ""
        for mot in bloc.split(" "):
            essai = f"{courante} {mot}" if courante else mot
            if not courante or largeur(essai) <= limite:
                courante = essai
            else:
                lignes.append(courante)
                courante = mot
        return lignes + [courante]

    lignes = []
    for bloc in texte.split("<br>"):
        n = len(glouton(bloc, dispo))
        bas, haut = 1, int(dispo)
        while bas < haut:
            milieu = (bas + haut) // 2
            if len(glouton(bloc, milieu)) <= n:
                haut = milieu
            else:
                bas = milieu + 1
        lignes += glouton(bloc, haut)
    trop = [li for li in lignes if largeur(li) > dispo]
    if trop:
        raise ValueError(f"mot plus large que {dispo:.0f} px à {taille} px : {trop}")
    return "<br>".join(lignes)


MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
              "septembre", "octobre", "novembre", "décembre"]


def insecables(t: str) -> str:
    """Espaces où une mise en page étroite ne coupe pas : avant %, : et ?, dans une date
    (« 30 octobre »), entre « à » et une heure, et dans « (statut EDF : estimé) »."""
    nb = "\u00a0"
    t = t.replace(" %", nb + "%").replace(" :", nb + ":").replace(" ?", nb + "?")
    t = re.sub(rf"(\d+(?:er)?) ({'|'.join(MOIS_LONGS)})", rf"\1{nb}\2", t)
    t = re.sub(r" à (\d+h\d\d)", rf" à{nb}\1", t)
    return t.replace(f"(statut EDF{nb}: ", f"(statut{nb}EDF{nb}:{nb}")


def dissoudre_br(t: str) -> str:
    """Retire les retours à la ligne qui ne servaient qu'à la largeur : un `<br>` qui suit
    un point, un deux-points ou un point d'interrogation finit une phrase et se garde."""
    return re.sub(r"(?<![.:?])<br>", " ", t or "")


# --- Mise en page étroite GÉNÉRIQUE (toutes les figures, depuis le 01/11/2026) --------
# T1 a la sienne, écrite à la main parce que son message est du texte. Les autres
# figures se faisaient rogner sur téléphone de la même façon : titres, sous-titres et
# sources coupés, légendes posées sur le titre, zone de tracé réduite à 28 px (t7).
# La seconde mise en page en est DÉRIVÉE ici, à l'export, puis vérifiée : chaque ligne
# de texte est mesurée à la largeur du plus petit cadre, et une ligne qui ne tient pas
# fait lever la génération plutôt que de partir rognée. Ce qui ne se dérive pas (des
# libellés de barres trop longs, une barre de couleur, un encadré qui recouvre des
# barres) se déclare figure par figure dans `reglages` — cf. figures.etroit_t7.
ETROIT_FIGURE_PX = CADRE_ETROIT_MIN_PX - 2 * MARGE_PAGE_PX
"""Largeur de la figure dans le plus petit cadre étroit : c'est à elle que tout tient."""
ETROIT_MARGE_PX = 8
"""Marge latérale des textes en étroit (titre, légende, pied)."""
ETROIT_DISPO_PX = ETROIT_FIGURE_PX - 2 * ETROIT_MARGE_PX - 6
"""Largeur d'une ligne de texte pleine largeur, avec 6 px de garde à droite."""
ETROIT_TAILLES = dict(titre=22, sous_titre=16, legende=15, pied=TAILLE_PIED, graduations=14,
                      axe=15, annotation=14, valeurs=12)
"""Corps des textes en étroit. Le pied garde son plancher de 16 px ; les étiquettes de
valeurs descendent à 12 px, faute de quoi elles se chevauchent sur un tracé de 220 px."""
ETROIT_HAUT_TITRE_PX = 44
"""Haut du titre étroit : sous la barre d'outils de Plotly (28 px)."""
ETROIT_MARGE_GAUCHE_PX = 52
"""Marge gauche du tracé quand l'axe vertical est numérique : ses graduations seules, son
titre passant à l'horizontale au-dessus de l'axe."""
ETROIT_MARGE_DROITE_PX = 16
ETROIT_ZONE_AXE_X_PX = 96
"""Sous le tracé, avant le pied : graduations de l'axe horizontal (éventuellement
tournées par Plotly faute de place) et son titre."""
ETROIT_TRACE_MIN_PX = 220
ETROIT_LIBELLES_MAX_PX = 120
"""Au-delà, des libellés de catégories mangeraient le tracé : la figure doit déclarer
un réglage (les poser au-dessus des barres, par exemple)."""


def pied_etroit(source: str, collecte: str, note: str = "") -> str:
    """Le pied d'une figure en étroit, avant repli : la source et sa date d'un seul tenant,
    puis la note, dont seuls les retours à la ligne de fin de phrase sont gardés."""
    pied = f"Source : {source} — données collectées le {collecte}"
    if note:
        pied += "<br>" + dissoudre_br(note)
    return pied


def _taille_annotation(a: dict) -> int:
    return int((a.get("font") or {}).get("size") or 17)


def _fusionner(base: dict, ajout: dict) -> dict:
    """Fusion récursive de deux dictionnaires Plotly (l'ajout l'emporte)."""
    out = dict(base)
    for k, v in ajout.items():
        out[k] = _fusionner(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def disposition_etroite(fig, source: str, collecte: str, note: str = "",
                        reglages: dict | None = None) -> dict:
    """La mise en page étroite d'une figure déjà préparée (preparer_figure), au format de
    `layout.meta.etroit` : seuil, hauteur, attributs de traces et `Plotly.update`.

    Dérivation : titre et sous-titre repliés à ETROIT_DISPO_PX ; légende en liste
    verticale sous le sous-titre ; titres des axes verticaux à l'horizontale au-dessus
    de leur axe ; graduations, étiquettes de valeurs et annotations à des corps réduits ;
    pied replié en entier, sans rien en retirer (il porte le sourçage obligatoire et les
    réserves de méthode). Marges FIXES (`autoexpand` coupé) : sans quoi Plotly élargit la
    marge gauche pour loger la légende et pousse tracé et pied hors du cadre. Hauteur
    fixe, que l'étude donne au cadre (compile_etude).

    `reglages`, propres à une figure, tous facultatifs :
    - `l`, `trace_px`, `zone_axe_x`, `marge_haute_px` : remplacent les valeurs dérivées ;
    - `annotations` : {rang: dict à fusionner, ou None pour la retirer}, rang compté
      dans les annotations de la figure hors pied ; `ajouts` : annotations en plus ;
    - `traces` : {attribut: valeur par trace} ; `disposition` : clés de layout en plus.
    Toute annotation, ajoutée ou non, est mesurée : une ligne trop large lève.
    """
    r = reglages or {}
    T = ETROIT_TAILLES
    dispo = ETROIT_DISPO_PX
    L = fig.layout

    titre = replier_equilibre(insecables(dissoudre_br(L.title.text)), T["titre"], dispo)
    st_brut = L.title.subtitle.text if L.title.subtitle else ""
    st = replier_equilibre(insecables(dissoudre_br(st_brut)), T["sous_titre"], dispo) if st_brut else ""
    haut_titre = ETROIT_HAUT_TITRE_PX + (titre.count("<br>") + 1) * T["titre"] * INTERLIGNE
    if st:
        haut_titre += (st.count("<br>") + 1) * T["sous_titre"] * INTERLIGNE + 6

    # Légende : une entrée par ligne, noms repliés au besoin (44 px pour le symbole).
    noms, haut_legende = [], 0.0
    legende = L.showlegend is not False
    for t in fig.data:
        nom = t.name
        if legende and nom and t.showlegend is not False:
            if largeur_px(nom, T["legende"]) > dispo - 44:
                nom = replier_equilibre(nom, T["legende"], dispo - 44)
            haut_legende += (nom.count("<br>") + 1) * T["legende"] * INTERLIGNE + 7
        noms.append(nom)

    # Marge gauche : graduations numériques, ou libellés de barres horizontales.
    l_marge = ETROIT_MARGE_GAUCHE_PX
    for t in fig.data:
        if getattr(t, "orientation", None) == "h" and t.y is not None:
            libelles = max(largeur_px(li, T["graduations"]) for v in t.y for li in str(v).split("<br>"))
            l_marge = max(l_marge, round(libelles + 14))
    l_marge = r.get("l", l_marge)
    if l_marge > ETROIT_LIBELLES_MAX_PX:
        raise ValueError(f"libellés de {l_marge} px en étroit : la figure doit déclarer un "
                         "réglage (cf. viz.disposition_etroite, `l`).")
    r_marge = ETROIT_MARGE_DROITE_PX
    trace_large = (L.height or template().layout.height or 600) - (
        L.margin.t if L.margin.t is not None else template().layout.margin.t) - (
        L.margin.b if L.margin.b is not None else template().layout.margin.b)
    trace_px = r.get("trace_px", max(ETROIT_TRACE_MIN_PX, round(trace_large)))
    largeur_trace = ETROIT_FIGURE_PX - l_marge - r_marge

    # Annotations de la figure (hors pied), au corps réduit, repliées si trop larges.
    annotations = []
    for a in list(L.annotations)[:-1]:
        d = a.to_plotly_json()
        d["font"] = dict(d.get("font") or {}, size=min(_taille_annotation(d), T["annotation"]))
        limite = largeur_trace * 0.8
        if max(largeur_px(li, _taille_annotation(d)) for li in d.get("text", "").split("<br>")) > limite:
            d["text"] = replier_equilibre(dissoudre_br(d["text"]), _taille_annotation(d), limite)
        annotations.append(d)
    for rang, ajout in (r.get("annotations") or {}).items():
        annotations[rang] = None if ajout is None else _fusionner(annotations[rang], ajout)
    annotations = [a for a in annotations if a is not None] + list(r.get("ajouts", []))

    # Titres des axes verticaux : à l'horizontale, au-dessus de leur axe.
    titres_y = []
    for cle in L:
        axe = L[cle] if re.match(r"yaxis\d*$", cle) else None
        if axe is not None and axe.title and axe.title.text and axe.visible is not False:
            titres_y.append(dict(
                text=axe.title.text, xref="paper", x=0, xanchor="left",
                xshift=-(l_marge - ETROIT_MARGE_PX), yref=f"y{cle[5:]} domain", y=1,
                yanchor="bottom", yshift=6, showarrow=False, align="left",
                font=dict(family=SANS, size=T["axe"] - 1, color=PALETTE["ink_soft"])))

    pied = replier_equilibre(insecables(pied_etroit(source, collecte, note)), T["pied"], dispo)
    zone_x = r.get("zone_axe_x", ETROIT_ZONE_AXE_X_PX)
    pied_annotation = L.annotations[-1].to_plotly_json()
    pied_annotation.update(text=pied, yshift=-zone_x + 8, xshift=-(l_marge - ETROIT_MARGE_PX),
                           font=dict(pied_annotation.get("font") or {}, size=T["pied"]))
    annotations += titres_y + [pied_annotation]

    # Mesure de TOUTES les annotations : pleine largeur si elles partent du bord de la
    # figure (xshift jusqu'à la marge), largeur du tracé sinon.
    for a in annotations:
        bord = a.get("xref") == "paper" and a.get("xshift") == -(l_marge - ETROIT_MARGE_PX)
        limite = dispo if bord else largeur_trace
        trop = [li for li in str(a.get("text", "")).split("<br>")
                if largeur_px(li.replace("\u00a0", " "), _taille_annotation(a)) > limite]
        if trop:
            raise ValueError(f"annotation étroite plus large que {limite:.0f} px : {trop}")

    haut_legende_px = haut_titre + 12
    marge_haute = haut_legende_px + (haut_legende + 18 if haut_legende else 6)
    marge_haute += (24 if titres_y else 0) + r.get("marge_haute_px", 0)
    marge_haute = round(marge_haute)
    marge_basse = round(zone_x + (pied.count("<br>") + 1) * T["pied"] * INTERLIGNE + GARDE_BASSE_PX)
    hauteur = marge_haute + trace_px + marge_basse

    disposition = {
        "title": dict(text=titre, xref="container", x=0, xanchor="left",
                      pad=dict(l=ETROIT_MARGE_PX, t=0), yref="container",
                      y=1 - ETROIT_HAUT_TITRE_PX / hauteur, yanchor="top",
                      font=dict(size=T["titre"]),
                      subtitle=dict(text=st, font=dict(size=T["sous_titre"]))),
        "margin": dict(t=marge_haute, b=marge_basse, l=l_marge, r=r_marge, autoexpand=False),
        "height": hauteur,
        "annotations": annotations,
    }
    if haut_legende:
        disposition["legend"] = dict(
            orientation="v", xref="container", x=ETROIT_MARGE_PX / ETROIT_FIGURE_PX,
            xanchor="left", yref="container", y=1 - haut_legende_px / hauteur, yanchor="top",
            font=dict(family=SANS, size=T["legende"], color=PALETTE["ink"]),
            tracegroupgap=0, itemsizing="constant", traceorder=L.legend.traceorder or "normal")
    for cle in L:
        if re.match(r"[xy]axis\d*$", cle):
            disposition[f"{cle}.tickfont.size"] = T["graduations"]
            disposition[f"{cle}.title.font.size"] = T["axe"]
            disposition[f"{cle}.title.standoff"] = 6
            # Sans `automargin` coupé, Plotly place le titre d'un axe vertical au milieu
            # du tracé quand les marges sont figées (constaté le 01/11/2026).
            disposition[f"{cle}.automargin"] = False
            if cle.startswith("yaxis"):
                disposition[f"{cle}.title.text"] = ""
    disposition.update(r.get("disposition", {}))

    a_du_texte = [getattr(t, "text", None) is not None or bool(getattr(t, "texttemplate", None))
                  for t in fig.data]
    traces = {"name": noms,
              "textfont.size": [T["valeurs"] if oui else None for oui in a_du_texte]}
    traces.update(r.get("traces", {}))
    return dict(seuil=SEUIL_ETROIT_PX, hauteur=hauteur, traces=traces, disposition=disposition)


def script_etroit(div_id: str) -> str:
    """Le script qui choisit, chez le lecteur, entre la mise en page large et l'étroite
    (`layout.meta.etroit`), au même seuil que le cadre de l'étude. Il garde de la page
    large exactement les clés que l'étroite change, pour les rétablir à l'identique ; il
    ne compose aucun texte."""
    return """
(function () {
  var gd = document.getElementById(%s);
  if (!gd || !gd.layout) return;
  var E = gd.layout.meta && gd.layout.meta.etroit;
  if (!E) return;
  function copie(o) { return o === undefined ? null : JSON.parse(JSON.stringify(o)); }
  function lire(o, chemin) {
    return chemin.split('.').reduce(function (a, k) { return a == null ? undefined : a[k]; }, o);
  }
  var LARGE = {}, TRACES = {};
  Object.keys(E.disposition).forEach(function (k) { LARGE[k] = copie(lire(gd.layout, k)); });
  Object.keys(E.traces).forEach(function (k) {
    TRACES[k] = gd.data.map(function (t) { return copie(lire(t, k)); });
  });
  LARGE.height = gd.layout.height;
  var HAUTEUR_DIV = gd.style.height;
  // Plotly ne recalcule pas une barre de couleur dont l'orientation change sur une
  // figure déjà dessinée (t5 : barre horizontale de 668 px de haut, constaté le
  // 01/11/2026) ; un nouveau tracé complet la dessine juste.
  var redessiner = Object.keys(E.traces).some(function (k) { return k.indexOf('colorbar.') === 0; });
  var etroit = false;
  function adapter() {
    var e = window.innerWidth < E.seuil;
    if (e === etroit) return;
    etroit = e;
    var d = copie(e ? E.disposition : LARGE);
    gd.style.height = e ? d.height + 'px' : HAUTEUR_DIV;
    var fait = Plotly.update(gd, copie(e ? E.traces : TRACES), d);
    if (redessiner) fait.then(function () {
      return Plotly.newPlot(gd, copie(gd.data), copie(gd.layout), gd._context);
    });
  }
  adapter();
  window.addEventListener('resize', adapter);
})();
""" % json.dumps(div_id)


# --- Légende : la zone que rien ne surveillait ---------------------------------
# Deux fois en une journée (T4, T6), une légende horizontale a recouvert soit le
# sous-titre, soit le titre d'axe, sans qu'aucune garde ne s'en aperçoive : elle vit
# hors du titre et hors du pied, les deux seules choses mesurées jusqu'ici. Les
# constantes ci-dessous sont des ORDRES DE GRANDEUR relevés au rendu, pas des valeurs
# que Plotly expose — d'où des marges volontairement généreuses : la garde doit
# refuser un chevauchement, pas placer la légende au pixel.
TAILLE_LEGENDE = 17          # cf. template()
RANGEE_LEGENDE_PX = 26       # hauteur d'une rangée d'entrées, interligne compris
PASTILLE_LEGENDE_PX = 46     # carré de couleur + espace avant le libellé + écart
TAILLE_TICK = 17             # cf. template()
TAILLE_TITRE_AXE = 19        # cf. template()
STANDOFF_AXE_PX = 18         # cf. template()


def entrees_de_legende(fig) -> list:
    """Libellés qui apparaîtront dans la légende, dans l'ordre du tracé."""
    return [tr.name for tr in fig.data
            if getattr(tr, "showlegend", None) is not False and getattr(tr, "name", None)]


def rangees_de_legende(fig, largeur: int) -> int:
    """Nombre de rangées qu'occupera une légende HORIZONTALE à cette largeur.

    Plotly replie les entrées quand elles ne tiennent plus sur une ligne ; c'est ce
    repli qui fait grandir une légende en iframe étroite. On le simule au lieu de le
    supposer.
    """
    entrees = entrees_de_legende(fig)
    if not entrees:
        return 0
    dispo, rangees, courante = largeur - RETRAIT_TITRE_PX, 1, 0.0
    for nom in entrees:
        besoin = largeur_px(nom, TAILLE_LEGENDE) + PASTILLE_LEGENDE_PX
        if courante and courante + besoin > dispo:
            rangees, courante = rangees + 1, besoin
        else:
            courante += besoin
    return rangees


def hauteur_sous_axe_px(fig) -> int:
    """Place occupée sous la zone de tracé par les étiquettes et le titre de l'axe x."""
    axe = fig.layout.xaxis
    sous = 0 if getattr(axe, "showticklabels", None) is False else round(TAILLE_TICK * 1.2)
    if getattr(getattr(axe, "title", None), "text", None):
        sous += STANDOFF_AXE_PX + round(TAILLE_TITRE_AXE * 1.2)
    return sous


def verifier_legende(fig, largeur: int = LARGEUR_VISUEL) -> list:
    """Fautes de placement de la légende. Liste vide si elle ne recouvre rien.

    Deux configurations, deux voisins. SOUS le tracé (`y < 0`), elle doit passer sous
    les étiquettes et le titre de l'axe x, et tenir dans la marge basse. AU-DESSUS
    (`y > 1`), elle partage la marge haute avec le titre et le sous-titre. Entre les
    deux la légende est DANS le tracé : ce dépôt ne s'en sert pas, et la garde ne s'y
    prononce pas plutôt que de prononcer au hasard.
    """
    lg = fig.layout.legend
    if getattr(lg, "orientation", None) != "h" or getattr(lg, "y", None) is None:
        return []
    hauteur = getattr(fig.layout, "height", None)
    if not hauteur:
        return []
    zone = hauteur - marge_effective(fig, "t") - marge_effective(fig, "b")
    if zone <= 0:
        return [f"    zone de tracé nulle ou négative ({zone} px) — marges à revoir"]
    rangees = rangees_de_legende(fig, largeur)
    haut = RANGEE_LEGENDE_PX * rangees
    y = float(lg.y)
    if y < 0:
        depart = abs(y) * zone
        besoin = hauteur_sous_axe_px(fig)
        if depart < besoin:
            return [f"    légende à y={y} : elle commence {depart:.0f} px sous le tracé, "
                    f"où l'axe x en occupe encore {besoin}. Descendre `y`."]
        if depart + haut > marge_effective(fig, "b"):
            return [f"    légende à y={y} sur {rangees} rangée(s) : son bas tombe à "
                    f"{depart + haut:.0f} px, hors d'une marge b="
                    f"{marge_effective(fig, 'b')}. Augmenter `b` ET `height`."]
    elif y > 1:
        depart = (y - 1) * zone
        besoin = marge_haute_minimale(fig)
        if marge_effective(fig, "t") - depart - haut < besoin - 30:
            return [f"    légende à y={y} sur {rangees} rangée(s) : elle remonte dans le "
                    f"sous-titre, qui réclame {besoin} px de marge haute. La passer sous "
                    "le tracé (y négatif), comme T6 depuis le 22/07/2026."]
    return []


def centrer_titre_ancre(fig) -> None:
    """Centre dans la marge haute le bloc titre d'une figure qui déclare son ancrage.

    Une figure peut ancrer son titre en haut du conteneur pour qu'un titre de deux lignes
    ne redescende pas sur le tracé. L'ancrage seul colle alors le titre au bord haut,
    alors que Plotly centre les autres titres dans leur marge. Le décalage se voyait
    sur A4, dont le titre paraissait rogné pendant qu'un large vide séparait le
    sous-titre de la première barre.

    La position est calculée après le sous-titre, donc sur le bloc complet. Le titre
    garde au moins 12 px au-dessus de lui.
    """
    if fig.layout.title.yref != "container":
        return
    hauteur = fig.layout.height or template().layout.height
    haut_bloc = sum(taille * 1.45 for _, taille in lignes_de_titre(fig))
    au_dessus = max((marge_effective(fig, "t") - haut_bloc) / 2, 12)
    fig.update_layout(title=dict(y=1 - au_dessus / hauteur, yanchor="top"))


def marge_haute_minimale(fig) -> int:
    """Marge haute qu'il faut à cette figure pour que le tracé ne remonte pas dans le titre.

    Interligne 1,45 (le titre respire plus qu'un bloc courant), plus une bande de
    respiration sous la dernière ligne de sous-titre : sans elle, le graphique
    s'entremêle au propos — c'était le cas de T7, dont la marge tombait à la ligne près.
    """
    hauteur = sum(taille * 1.45 for _, taille in lignes_de_titre(fig))
    return round(12 + hauteur + 30)


def marge_basse_minimale(pied: str, pied_decalage_px: int) -> int:
    """Marge basse qu'il faut pour que le pied tienne ENTIER dans la figure.

    Symétrique de `marge_haute_minimale`, et née du même aveuglement : sous la marge
    déclarée, Plotly ne replie ni ne rogne proprement — il coupe au bord du dessin. Six
    figures sur seize perdaient ainsi la fin de leur pied le 06/08/2026, et ce qui
    tombait n'était pas décoratif : sur T7 et T8, c'était la mention « données estimées ».

    Le pied est déjà replié à ce stade : ses `<br>` disent le nombre de lignes.
    `pied_decalage_px` mesure du bas de la zone de tracé au HAUT du texte ; le texte
    descend ensuite, d'où l'addition. La garde couvre les jambages de la dernière ligne.
    """
    lignes = pied.count("<br>") + 1
    return round(abs(pied_decalage_px) + lignes * TAILLE_PIED * INTERLIGNE + GARDE_BASSE_PX)


def marge_effective(fig, cote: str) -> int:
    """Marge d'un côté de la figure, celle du template si la figure n'en déclare pas."""
    marge = getattr(fig.layout.margin, cote)
    if marge is None:
        marge = getattr(template().layout.margin, cote)
    return marge


def verifier_pied(fig, nom: str, pied: str, pied_decalage_px: int) -> None:
    """Refuse une figure dont la marge basse couperait le pied — source ou note.

    Le pied est le porteur du sourçage obligatoire ET des réserves de méthode : le
    laisser se faire rogner revient à publier une figure moins prudente que ce que le
    code affirme. Cf. `marge_basse_minimale`.
    """
    besoin = marge_basse_minimale(pied, pied_decalage_px)
    marge = marge_effective(fig, "b")
    if marge < besoin:
        lignes = pied.count("<br>") + 1
        raise ValueError(
            f"{nom} : le pied ({lignes} lignes) déborde du bas de la figure — marge "
            f"b={marge}, il en faut {besoin}. Augmenter `b` ET `height` d'autant, pour "
            "ne pas écraser la zone de tracé.")


def verifier_titres(fig, nom: str = "figure", largeur: int = LARGEUR_VISUEL) -> None:
    """Refuse une figure dont le titre déborde, ou dont la marge haute est trop courte.

    Verrou posé le 06/08/2026, en réponse à la crainte — juste — qu'en corrigeant une
    figure les erreurs se déplacent ailleurs : la contrainte est écrite une fois, à
    l'endroit par lequel TOUTE figure publiée passe, plutôt que relue figure par figure.
    Échec bruyant : un run qui casse ici ne publie rien et laisse la vitrine précédente
    en place — un titre rogné, lui, part en ligne sans prévenir.
    """
    dispo = largeur - RETRAIT_TITRE_PX
    fautes = [
        f"    {taille} px — {largeur_px(li, taille):.0f} px (dispo {dispo}) : {li}"
        for li, taille in lignes_de_titre(fig)
        if largeur_px(li, taille) > dispo
    ]
    marge = marge_effective(fig, "t")
    besoin = marge_haute_minimale(fig)
    if marge < besoin:
        fautes.append(f"    marge haute t={marge} — il en faut {besoin} pour ce titre")
    fautes += verifier_legende(fig, largeur)
    if fautes:
        raise ValueError(
            f"{nom} : titre, marge ou légende hors gabarit à {largeur} px — couper "
            "sur <br>, raccourcir, ou déplacer la légende.\n"
            + "\n".join(fautes))


def date_collecte(source_id: str) -> str:
    """Date de collecte de la donnée RÉELLEMENT présente dans le Parquet.

    Lue dans la lignée de build (data/processed/_build.json, écrite par prepare) : elle
    reflète les octets certifiés que prepare a consommés, pas le dernier passage de fetch
    (qui peut avoir rafraîchi le manifeste sans que prepare soit rejoué — sinon la figure
    afficherait une date plus récente que la donnée qu'elle montre). Repli sur le manifeste
    si la lignée est absente (figure hors pipeline, ex. exploration). Une source absente
    d'une lignée existante ne peut pas emprunter la date d'un téléchargement plus récent."""
    if BUILD_FILE.exists():
        build = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
        entree = build.get("sources", {}).get(source_id)
        if entree and entree.get("date_collecte"):
            return entree["date_collecte"]
        raise ValueError(f"{source_id} absent de la lignée de build — date de figure non certifiée.")
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def ecrire_bundle_plotly(dossier: Path) -> str:
    """Écrit les octets de Plotly sous une URL immuable propre à leur SHA-256.

    Les anciennes URL restent disponibles pour les pages déjà en cache. Un fichier
    local altéré est réparé avant qu'une nouvelle page le référence.
    """
    contenu = get_plotlyjs().encode("utf-8")
    nom = f"plotly-{hashlib.sha256(contenu).hexdigest()}.min.js"
    dest = dossier / nom
    if not dest.exists() or dest.read_bytes() != contenu:
        temporaire = dest.with_name(dest.name + ".tmp")
        try:
            temporaire.write_bytes(contenu)
            temporaire.replace(dest)
        finally:
            temporaire.unlink(missing_ok=True)
    return nom


def export_html(fig, name: str, source: str, collecte: str, sous_titre: str = "",
                note: str = "", pied_decalage_px: int = -85,
                script_apres: str | None = None, pied_largeur_px: int | None = None,
                etroit=None) -> str:
    """Écrit outputs/<name>.html avec un bundle Plotly local partagé, nommé par empreinte.

    Applique le template, incruste la mention de source obligatoire.
    fig       : figure Plotly
    name      : nom de fichier sans extension, ex. "t4_heure_verte"
    source    : mention de source, ex. "EDF — Open Data Groupe EDF"
    collecte  : date de collecte, ex. date_collecte("edf_courbe_charge_horaire")
    sous_titre: ligne de contexte (périmètre, définition) sous le titre
    note      : note méthodologique courte, en pied sous la mention de source
                (ex. statut estimé des données)
    pied_decalage_px : décalage du HAUT du pied sous l'axe, en pixels — stable quelle
                que soit la hauteur de la figure (une fraction de zone de tracé ne
                l'est pas). Le défaut (-85) passe sous ticks + titre d'axe ; à creuser
                quand une légende occupe la bande basse (cf. T6)
    script_apres : JavaScript LOCAL exécuté après le tracé. Réservé à ce qui ne peut
                pas être calculé à la génération parce que la réponse dépend de la
                LECTURE, et à deux choses seulement : l'instant (la péremption d'un
                relevé) et la largeur du cadre (le choix entre deux mises en page,
                l'étroite étant calculée et vérifiée à la génération — cf.
                SEUIL_ETROIT_PX). Le script choisit ; il ne compose aucun texte.
                Élargi le 01/11/2026 pour T1, dont le message est du texte : rogné sur
                un téléphone, il ne gardait que le pourcentage, sans sa période ni son
                repère. Aucune ressource tierce, aucun appel réseau : le script ne lit
                que des valeurs déjà écrites dans la page.
    pied_largeur_px : largeur, en pixels, à laquelle replier le pied en lignes
                équilibrées (cf. replier_equilibre). Par défaut, repli commun à
                LARGEUR_PIED caractères.
    etroit    : réglages de la mise en page étroite propres à cette figure (dict, ou
                fonction de la figure qui le rend ; cf. disposition_etroite). Toute
                figure reçoit une mise en page étroite et son script de bascule, sauf
                celle qui déclare déjà la sienne dans `layout.meta.etroit` (T1) et celle
                qui passe `etroit=False` (figures air, pas encore traitées).
    """
    preparer_figure(fig, source, collecte, sous_titre, note, pied_decalage_px, nom=name,
                    pied_largeur_px=pied_largeur_px)
    scripts = [script_apres] if script_apres else []
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    if "etroit" not in meta and etroit is not False:
        reglages = etroit(fig) if callable(etroit) else etroit
        fig.update_layout(meta=dict(meta, etroit=disposition_etroite(
            fig, source, collecte, note, reglages)))
        scripts.append(script_etroit(name))
    dest = OUTPUTS / f"{name}.html"
    # Une URL par contenu : le cache immutable ne peut pas conserver un ancien bundle
    # sous le nom d'une version nouvelle. L'export "directory" conservait ce défaut.
    # div_id fixe : sans lui, Plotly tire un UUID à chaque export et deux runs sur les
    # mêmes données produisent des fichiers différents — or la planification ne committe
    # que ce qui a réellement changé.
    bundle = ecrire_bundle_plotly(OUTPUTS)
    fig.write_html(dest, include_plotlyjs=bundle, full_html=True, div_id=name,
                   post_script=scripts or None)
    print(f"[ok] {dest}")
    return str(dest)


def texte_pied(source: str, collecte: str, note: str = "") -> str:
    """Le pied de figure AVANT repli : source, date de collecte, note.

    Extrait de `preparer_figure` pour qu'une mise en page étroite (cf. SEUIL_ETROIT_PX)
    replie le même texte à sa largeur, sans le réécrire.
    """
    # Coupure VOULUE avant la date quand la source est longue : elle tombe à un endroit
    # qui a du sens, plutôt qu'au hasard du repli. Le repli automatique prend le relais
    # pour tout ce qui dépasse encore, source ou note.
    sep = "<br>" if len(source) > 45 else " "
    pied = f"Source : {source}{sep}— données collectées le {collecte}"
    if note:
        pied += f"<br>{note}"
    return pied


def preparer_figure(fig, source: str, collecte: str, sous_titre: str = "",
                    note: str = "", pied_decalage_px: int = -85, nom: str = "figure",
                    pied_largeur_px: int | None = None):
    """Applique le template et incruste la mention de source obligatoire. Renvoie `fig`.

    Extraite d'`export_html` pour que la page d'assemblage obtienne EXACTEMENT les mêmes
    figures que les fichiers individuels : le sourçage est câblé une seule fois, et une
    figure ne peut pas se retrouver publiée sans sa mention parce qu'elle a pris un autre
    chemin de sortie.
    """
    fig.update_layout(template=template())
    if sous_titre:
        # Commentaire = sous-titre NATIF (un seul bloc avec le titre) : contrairement à
        # une annotation flottante, il ne peut plus télescoper la légende.
        fig.update_layout(title=dict(subtitle=dict(text=sous_titre)))
    centrer_titre_ancre(fig)
    # Le titre est posé : on vérifie qu'il TIENT, avant de dessiner quoi que ce soit.
    verifier_titres(fig, nom)
    pied = texte_pied(source, collecte, note)
    # Repli commun au nombre de caractères ; une figure qui connaît la largeur de son
    # texte peut demander le repli mesuré et équilibré, sans mot orphelin (T1 seule).
    pied = (replier_equilibre(pied, TAILLE_PIED, pied_largeur_px) if pied_largeur_px
            else replier_pied(pied))
    # Le pied s'aligne sur le bord GAUCHE DE LA FIGURE, pas sur celui de la zone de tracé.
    # `xref="paper"` place x=0 au début du tracé : une figure à large marge gauche (barres
    # horizontales, dont les libellés de stations occupent 300 px) poussait donc sa source
    # d'autant vers la droite, où elle se faisait rogner. Plotly n'accepte pas
    # `xref="container"` sur une annotation ; le décalage se fait donc en pixels, depuis
    # la marge déjà fixée par la figure — une valeur en pixels, donc stable quelle que
    # soit la largeur d'affichage, contrairement à une fraction de zone de tracé.
    verifier_pied(fig, nom, pied, pied_decalage_px)
    marge_gauche = marge_effective(fig, "l")
    fig.add_annotation(
        text=pied,
        xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=pied_decalage_px,
        xshift=-(marge_gauche - PIED_BORD_PX),
        showarrow=False, align="left", xanchor="left",
        # 16px + ink_soft : plancher relevé (22/07) + contraste WCAG AA (muted échouait).
        font=dict(family=SANS, size=16, color=PALETTE["ink_soft"]),
    )
    return fig
