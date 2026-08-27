"""Export des visualisations en HTML déployable en iframe sans dépendance tierce.

Plotly n'est pas chargé depuis un CDN : `plotly.min.js` est écrit UNE fois dans
outputs/ et partagé par tous les visuels — le dossier outputs/ se déploie d'un bloc.

La mention de source « Source … — données collectées le … » est câblée dans
l'export : le sourçage n'est pas optionnel. Le style (palette énergie lisible,
fond neutre clair, sans-serif) est porté par le template appliqué à chaque figure.
"""

from __future__ import annotations

import json
import re
import textwrap

import plotly.graph_objects as go

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
    "solaire":   "#B07A2B",  # or — le solaire (jauge T1, ligne T3)
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
    si la lignée est absente (figure hors pipeline, ex. exploration)."""
    if BUILD_FILE.exists():
        build = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
        entree = build.get("sources", {}).get(source_id)
        if entree and entree.get("date_collecte"):
            return entree["date_collecte"]
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest[source_id]["date_collecte"]


def export_html(fig, name: str, source: str, collecte: str, sous_titre: str = "",
                note: str = "", pied_decalage_px: int = -85,
                script_apres: str | None = None) -> str:
    """Écrit outputs/<name>.html (fichier léger, plotly.min.js mutualisé dans outputs/).

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
                pas être calculé à la génération parce que la réponse dépend de
                l'instant de LECTURE — la péremption d'un relevé, et rien d'autre.
                Aucune ressource tierce, aucun appel réseau : le script ne lit que des
                valeurs déjà écrites dans la page.
    """
    preparer_figure(fig, source, collecte, sous_titre, note, pied_decalage_px, nom=name)
    dest = OUTPUTS / f"{name}.html"
    # "directory" : pas de CDN (le visuel se charge sans réseau tiers) ni de JS
    # embarqué par fichier (~4,5 Mo x5) — une seule copie partagée dans outputs/.
    # div_id fixe : sans lui, Plotly tire un UUID à chaque export et deux runs sur les
    # mêmes données produisent des fichiers différents — or la planification ne committe
    # que ce qui a réellement changé.
    fig.write_html(dest, include_plotlyjs="directory", full_html=True, div_id=name,
                   post_script=script_apres)
    print(f"[ok] {dest}")
    return str(dest)


def preparer_figure(fig, source: str, collecte: str, sous_titre: str = "",
                    note: str = "", pied_decalage_px: int = -85, nom: str = "figure"):
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
    # Le titre est posé : on vérifie qu'il TIENT, avant de dessiner quoi que ce soit.
    verifier_titres(fig, nom)
    # Coupure VOULUE avant la date quand la source est longue : elle tombe à un endroit
    # qui a du sens, plutôt qu'au hasard du repli. Le repli automatique ci-dessous prend
    # le relais pour tout ce qui dépasse encore, source ou note.
    sep = "<br>" if len(source) > 45 else " "
    pied = f"Source : {source}{sep}— données collectées le {collecte}"
    if note:
        pied += f"<br>{note}"
    pied = replier_pied(pied)
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
