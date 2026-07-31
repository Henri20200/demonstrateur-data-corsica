"""Compile `docs/etude.md` -> `outputs/etude.html` : la page assemblée de l'étude.

Pas de dépendance tierce. Le markdown de l'étude est un sous-ensemble **connu et
borné** — titres H1-H4, gras/italique, listes à puces et numérotées, une table, des
encadrés « Pour aller plus loin », et les balises `{{visuel:}}`. Un convertisseur sur
mesure suffit et garde le livrable fidèle à son exigence : déployable sans dépendance
tierce, `outputs/` d'un bloc.

Conventions (cf. l'en-tête de `docs/etude.md`) :
  - `{{visuel:nom}}`                          -> `<iframe>` vers `outputs/nom.html`
  - blockquote « **Pour aller plus loin** »   -> `<details>` repliable (couche initié)
  - `# Titre` suivi d'une ligne `*en italique*` -> titre + sous-titre de page

La page ne charge aucun JS : ce sont les iframes des visuels qui tirent (chacun dans
son coin) le `plotly.min.js` mutualisé de `outputs/`. Le style reprend la palette et
les règles de lisibilité des figures (encre pleine, plancher 16 px, contraste WCAG AA).
"""

from __future__ import annotations

import re

from .config import ETUDE_HTML, ETUDE_SOURCE, OUTPUTS
from .viz import PALETTE, SANS

# --- Rendu inline : échappement + le seul balisage inline présent (gras, italique) ---


def _echapper(txte: str) -> str:
    """Échappe les trois caractères qui ont un sens en HTML. Rien d'autre : le reste
    (« » — ≠ ₂ ·) est de l'UTF-8 qui passe tel quel."""
    return txte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(txte: str) -> str:
    """Échappe puis rend `**gras**` et `*italique*` — dans cet ordre, pour que `**`
    ne soit pas capté comme deux `*`. L'étude n'a ni lien ni code inline."""
    txte = _echapper(txte)
    txte = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", txte)
    txte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", txte)
    return txte


# --- Visuels : hauteur lue dans le HTML du visuel, jamais devinée ni codée en dur ---


def _hauteur_visuel(nom: str) -> int:
    """Hauteur de l'iframe = hauteur de mise en page du visuel, lue dans son propre
    HTML (la clé `"height"` du layout Plotly). Le visuel reste la source de vérité ;
    la page ne redéclare pas une hauteur qui divergerait à la prochaine refonte."""
    chemin = OUTPUTS / f"{nom}.html"
    if not chemin.exists():
        raise FileNotFoundError(
            f"Visuel manquant pour la compilation : {chemin}. "
            "Lancer `python -m demonstrateur.figures` d'abord."
        )
    hauteurs = [int(h) for h in re.findall(r'"height":\s*(\d+)', chemin.read_text(encoding="utf-8"))]
    return max(hauteurs) if hauteurs else 560


def _iframe(nom: str) -> str:
    # +16 px : petite réserve pour la barre d'outils Plotly qui apparaît au survol.
    hauteur = _hauteur_visuel(nom) + 16
    return (
        f'<figure class="visuel"><iframe src="{nom}.html" height="{hauteur}" '
        f'loading="lazy" scrolling="no" title="Visualisation : {nom}"></iframe></figure>'
    )


# --- Blocs de niveau paragraphe ------------------------------------------------------


def _est_special(ligne: str) -> bool:
    """Vrai si la ligne ouvre un bloc non-paragraphe : elle ferme le paragraphe courant."""
    nu = ligne.lstrip()
    return bool(
        re.match(r"#{1,4}\s", ligne)
        or nu.startswith(">")
        or nu.startswith("|")
        or re.match(r"-\s+", ligne)
        or re.match(r"\d+\.\s+", ligne)
        or re.fullmatch(r"\{\{visuel:[a-z0-9_]+\}\}", nu)
    )


def _collecter_liste(lignes: list[str], i: int, marqueur: str) -> tuple[list[str], int]:
    """Collecte les items d'une liste à partir de `i`. Un item peut être replié sur
    plusieurs lignes (continuation indentée) : on les recolle. S'arrête à la ligne vide."""
    items: list[str] = []
    n = len(lignes)
    while i < n:
        m = re.match(marqueur + r"(.*)$", lignes[i])
        if m:
            items.append(m.group(1).strip())
            i += 1
            while i < n and lignes[i].strip() and lignes[i].startswith(" ") \
                    and not re.match(marqueur, lignes[i].strip()):
                items[-1] += " " + lignes[i].strip()
                i += 1
        else:
            break
    return items, i


def _encadre(bloc: list[str]) -> str:
    """Rend un blockquote. « **Pour aller plus loin** … » -> `<details>` repliable
    (le premier gras devient le résumé cliquable) ; tout autre -> `<blockquote>`."""
    texte = "\n".join(bloc).strip()
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", texte) if p.strip()]
    if not paras:
        return ""
    if paras[0].startswith("**Pour aller plus loin"):
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", paras[0])
        resume, reste = (m.group(1), m.group(2)) if m else ("Pour aller plus loin", paras[0])
        corps_paras = ([reste] if reste else []) + paras[1:]
        corps = "".join(f"<p>{_inline(p)}</p>" for p in corps_paras)
        return f"<details><summary>{_inline(resume)}</summary>{corps}</details>"
    corps = "".join(f"<p>{_inline(p)}</p>" for p in paras)
    return f"<blockquote>{corps}</blockquote>"


def _table(lignes: list[str]) -> str:
    """Table GFM -> `<table>`. La 2e ligne (`| --- | --- |`) est le séparateur, ignorée."""
    def cellules(rang: str) -> list[str]:
        return [c.strip() for c in rang.strip().strip("|").split("|")]

    entete = "".join(f"<th>{_inline(c)}</th>" for c in cellules(lignes[0]))
    corps = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cellules(rang)) + "</tr>"
        for rang in lignes[2:]
    )
    return f"<table><thead><tr>{entete}</tr></thead><tbody>{corps}</tbody></table>"


def compiler(md: str) -> str:
    """Convertit le markdown de l'étude en corps HTML. Convertisseur ligne à ligne
    d'un sous-ensemble borné — pas un parseur markdown général."""
    # Purge d'abord les commentaires (méta d'en-tête + balises PROVISOIRE), avant tout :
    # l'en-tête contient un exemple `{{visuel:nom}}` qu'il ne faut surtout pas transformer.
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lignes = md.split("\n")
    sortie: list[str] = []
    i, n = 0, len(lignes)
    while i < n:
        ligne = lignes[i]
        if not ligne.strip():
            i += 1
            continue

        m = re.match(r"(#{1,4})\s+(.*)$", ligne)
        if m:
            niveau, texte = len(m.group(1)), m.group(2)
            if niveau == 1:
                # Sous-titre = la ligne italique isolée qui suit le titre (on la consomme).
                j = i + 1
                while j < n and not lignes[j].strip():
                    j += 1
                sous = None
                if j < n and re.fullmatch(r"\*[^*].*[^*]\*", lignes[j].strip()):
                    sous = lignes[j].strip()[1:-1]
                    i = j
                entete = f"<h1>{_inline(texte)}</h1>"
                if sous:
                    entete += f'<p class="sous-titre">{_inline(sous)}</p>'
                sortie.append(f'<header class="titre">{entete}</header>')
            else:
                sortie.append(f"<h{niveau}>{_inline(texte)}</h{niveau}>")
            i += 1
            continue

        m = re.fullmatch(r"\{\{visuel:([a-z0-9_]+)\}\}", ligne.strip())
        if m:
            sortie.append(_iframe(m.group(1)))
            i += 1
            continue

        if ligne.startswith(">"):
            bloc = []
            while i < n and lignes[i].startswith(">"):
                bloc.append(re.sub(r"^> ?", "", lignes[i]))
                i += 1
            sortie.append(_encadre(bloc))
            continue

        if ligne.lstrip().startswith("|"):
            tbl = []
            while i < n and lignes[i].lstrip().startswith("|"):
                tbl.append(lignes[i].strip())
                i += 1
            sortie.append(_table(tbl))
            continue

        if re.match(r"-\s+", ligne):
            items, i = _collecter_liste(lignes, i, r"-\s+")
            sortie.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        if re.match(r"\d+\.\s+", ligne):
            items, i = _collecter_liste(lignes, i, r"\d+\.\s+")
            sortie.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # Paragraphe : jusqu'à la ligne vide ou l'ouverture d'un bloc. Un paragraphe
        # entièrement en italique est un lede de chapitre (styling distinct).
        para = []
        while i < n and lignes[i].strip() and not _est_special(lignes[i]):
            para.append(lignes[i].strip())
            i += 1
        texte = " ".join(para)
        classe = ' class="lede"' if re.fullmatch(r"\*[^*].*[^*]\*", texte) else ""
        sortie.append(f"<p{classe}>{_inline(texte)}</p>")

    return "\n".join(sortie)


# --- Assemblage de la page -----------------------------------------------------------

# Variables CSS dérivées de la palette des figures : la page et les visuels partagent
# la même encre, les mêmes filets. Un seul endroit où la couleur vit (viz.PALETTE).
_VARS = ":root{" + ";".join(
    [f"--{cle.replace('_', '-')}:{val}" for cle, val in PALETTE.items()] + [f"--sans:{SANS}"]
) + "}"

_CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);
  font-size:18px;line-height:1.62;-webkit-font-smoothing:antialiased}
article{max-width:760px;margin:0 auto;padding:3.5rem 1.25rem 5rem}
.titre{margin-bottom:2.5rem}
h1{font-size:2.1rem;line-height:1.18;margin:0 0 .5rem}
.sous-titre{font-size:1.2rem;color:var(--ink-soft);font-style:italic;margin:0}
h2{font-size:1.55rem;margin:3.25rem 0 1rem;padding-top:1.5rem;border-top:1px solid var(--rule)}
h3{font-size:1rem;color:var(--ink-soft);margin:2.5rem 0 .5rem;
  text-transform:uppercase;letter-spacing:.05em;font-weight:600}
h4{font-size:1.32rem;line-height:1.25;margin:2.25rem 0 .25rem}
.lede{color:var(--ink-soft);margin:.25rem 0 1.25rem}
p{margin:0 0 1.1rem}
ul,ol{margin:0 0 1.2rem;padding-left:1.4rem}
li{margin:.45rem 0}
strong{font-weight:650}
.visuel{margin:2.25rem 0}
.visuel iframe{width:100%;border:0;display:block}
details{background:var(--surface);border:1px solid var(--rule);border-radius:8px;
  padding:.8rem 1.15rem;margin:1.35rem 0}
summary{cursor:pointer;font-weight:600;color:var(--accent)}
details[open] summary{margin-bottom:.6rem}
details p:last-child{margin-bottom:0}
table{border-collapse:collapse;width:100%;font-size:.95rem;margin:1.25rem 0}
th,td{border:1px solid var(--rule);padding:.55rem .7rem;text-align:left;vertical-align:top}
th{background:var(--surface);font-weight:650}
"""


def _page(corps: str, titre: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{titre}</title>\n<style>{_VARS}{_CSS}</style>\n</head>\n"
        f"<body>\n<article>\n{corps}\n</article>\n</body>\n</html>\n"
    )


def rendre_page(md: str) -> str:
    """Page HTML complète pour un markdown d'étude — exactement ce que `main` publie.

    Sortie de `main` (31/07/2026) pour que les tests puissent comparer le fichier publié
    à ce que produit la source, sans redupliquer l'assemblage : `outputs/etude.html` est
    un fichier généré, mais il est versionné et déployé tel quel, donc une retouche à la
    main y survivrait sans que rien ne l'attrape.
    """
    m = re.search(r"^#\s+(.*)$", md, flags=re.M)
    titre = _echapper(m.group(1)) if m else "Étude"
    return _page(compiler(md), titre)


def main() -> int:
    ETUDE_HTML.write_text(rendre_page(ETUDE_SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"[ok] {ETUDE_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
