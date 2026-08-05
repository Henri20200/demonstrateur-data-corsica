"""Page d'entrée du livrable : outputs/index.html.

C'est la porte du dossier `outputs/`, déployé d'un bloc. Elle tient trois rôles et
pas un de plus : dire ce qu'on regarde, mener aux deux études, et **rendre la preuve
vérifiable en quelques secondes** — cachet de fraîcheur et manifeste des sources.

Parti pris de forme : dépouillement. La signature d'une page générée à la va-vite,
c'est l'ornement — bandeau décoratif, dégradés, cartes de « fonctionnalités ». Ici
les chiffres et les sources sont le seul décor, et le vocabulaire graphique est celui
déjà posé par `page_air.py` (même palette, même échelle typographique) pour que
l'ensemble se lise comme un seul objet.

**La fraîcheur est écrite deux fois, et c'est voulu.** La date absolue est posée dans
le HTML à la compilation : elle reste vraie sans JavaScript. L'âge relatif, lui, est
recalculé À LA LECTURE par quelques lignes de script. Une page statique qui aurait figé
« rafraîchi il y a 2 h » mentirait dès le lendemain ; recalculé, l'âge dit la vérité même
quand la chaîne s'arrête — et il le dit franchement au-delà d'un cycle manqué.
"""

from __future__ import annotations

import html
import json
import subprocess
from collections import defaultdict

from .config import BUILD_FILE, MANIFEST_FILE, OUTPUTS
from .viz import PALETTE, SANS

TITRE = "L'électricité et l'air en Corse"


def _txt(valeur: str) -> str:
    """Échappe pour du CONTENU de balise, sans toucher aux apostrophes.

    `html.escape` échappe aussi `'` en `&#x27;` : correct, mais illisible dans une page
    française où l'apostrophe est partout, et ce dépôt est fait pour être lu. Les valeurs
    d'ATTRIBUT gardent l'échappement complet (`html.escape`), elles, puisque là le guillemet
    et l'apostrophe ferment vraiment quelque chose.
    """
    return html.escape(valeur, quote=False)


# Les deux sujets publiés. (page principale, titre, phrase de conduite, pages annexes)
SUJETS = [
    (
        "etude.html",
        "De quoi est faite l'électricité corse",
        "Le soleil, le fioul, les barrages, les câbles : ce qui compose le courant au fil "
        "de la journée et des saisons, et l'heure où il est le plus renouvelable.",
        [("t0_note_methodologique.html", "Note méthodologique")],
    ),
    (
        "air_ozone.html",
        "L'air les jours où rien n'est signalé",
        "L'ozone est le seul polluant que l'été fabrique. Il ne déclenche presque jamais "
        "d'alerte en Corse, ce qui ne veut pas dire qu'il est absent.",
        [("a0_note_methodologique.html", "Note méthodologique")],
    ),
]


def _actualisations() -> int | None:
    """Nombre de rafraîchissements planifiés déjà commités.

    Compté sur les commits `chore(data)` : c'est la trace que la chaîne tourne vraiment,
    et elle est infalsifiable une fois le dépôt ouvert. Renvoie None hors dépôt git
    (archive téléchargée, par exemple) — auquel cas la page n'affiche simplement pas le
    compteur, plutôt qu'un nombre inventé.
    """
    try:
        sortie = subprocess.run(
            ["git", "log", "--grep=^chore(data)", "--format=%h"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    n = len([ligne for ligne in sortie.splitlines() if ligne.strip()])
    return n or None


def _manifeste() -> tuple[list[tuple[str, str, list[dict]]], int, int]:
    """Sources groupées par producteur, plus les deux totaux affichés en résumé.

    Le groupement n'est pas cosmétique : 37 fichiers dont 22 stations de mesure d'un
    même producteur, listés à plat, se lisent comme un mur. Groupés, on voit d'un coup
    d'œil de qui vient la donnée — ce que le lecteur veut savoir en premier.
    """
    sources = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    par_producteur: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for identifiant, s in sources.items():
        par_producteur[(s["producteur"], s["licence"])].append({**s, "id": identifiant})
    groupes = [
        (producteur, licence, sorted(items, key=lambda x: x["id"]))
        for (producteur, licence), items in sorted(par_producteur.items())
    ]
    return groupes, len(sources), len(groupes)


def _lignes_manifeste(groupes) -> str:
    blocs = []
    for producteur, licence, items in groupes:
        lignes = []
        for s in items:
            # Empreinte tronquée à l'affichage, entière au survol : la page reste lisible
            # sans amputer la preuve. 12 caractères hexadécimaux suffisent à comparer.
            court = _txt(s["sha256"][:12])
            entier = html.escape(s["sha256"])
            lignes.append(
                f'<tr><td>{_txt(s["id"])}</td>'
                f'<td>{_txt(s["date_collecte"])}</td>'
                f'<td class="emp" title="SHA-256 : {entier}">{court}…</td></tr>'
            )
        blocs.append(
            f'<div class="groupe"><h3>{_txt(producteur)}</h3>'
            f'<p class="licence">{_txt(licence)}</p>'
            f'<table><thead><tr><th>Source</th><th>Collectée le</th>'
            f'<th>Empreinte</th></tr></thead><tbody>{"".join(lignes)}</tbody></table></div>'
        )
    return "".join(blocs)


def _sujets() -> str:
    blocs = []
    for page, titre, phrase, annexes in SUJETS:
        liens = "".join(
            f' · <a href="{html.escape(href)}">{_txt(libelle)}</a>'
            for href, libelle in annexes
        )
        blocs.append(
            f'<article><h2><a href="{html.escape(page)}">{_txt(titre)}</a></h2>'
            f"<p>{_txt(phrase)}</p>"
            f'<p class="annexes"><a href="{html.escape(page)}">Lire l\'étude</a>{liens}</p>'
            "</article>"
        )
    return "".join(blocs)


def _html(genere_le: str, groupes, n_sources: int, n_prod: int,
          actualisations: int | None) -> str:
    compteur = (
        f" · {actualisations}<sup>e</sup> actualisation" if actualisations else ""
    )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_txt(TITRE)} — données publiques, datées et vérifiables</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; padding:3rem 1.2rem 4rem; background:{PALETTE["page"]};
          color:{PALETTE["ink"]}; font-family:{SANS}; font-size:17px; line-height:1.62; }}
  /* 48rem, et non les 62rem de la page de l'air : celle-ci porte des figures larges, pas
     celle-ci. Au-delà, les filets de séparation courent bien plus loin que le texte et la
     page paraît bancale à droite — un vide qui se lit comme un manque, pas comme du calme.
     Le seul élément large est le tableau des sources, qui défile dans sa propre boîte. */
  main {{ max-width:48rem; margin:0 auto; }}
  h1 {{ font-size:2rem; line-height:1.2; margin:0 0 .5rem; max-width:22em; }}
  .chapeau {{ font-size:1.1rem; color:{PALETTE["ink_soft"]}; max-width:44em; margin:0 0 1.6rem; }}
  .cachet {{ display:inline-block; padding:.55rem .9rem; background:{PALETTE["surface"]};
             border:1px solid {PALETTE["rule"]}; border-radius:5px; font-size:15.5px; }}
  .cachet.alerte {{ border-left:4px solid {PALETTE["accent"]}; }}
  .cachet .abs {{ color:{PALETTE["ink_soft"]}; }}
  article {{ margin:2.8rem 0 0; padding-top:1.6rem; border-top:1px solid {PALETTE["rule"]}; }}
  article h2 {{ font-size:1.45rem; margin:0 0 .35rem; }}
  article p {{ max-width:44em; margin:0 0 .3rem; }}
  a {{ color:{PALETTE["accent"]}; text-underline-offset:3px; }}
  /* Un titre de sujet EST un lien, mais il doit se lire comme un titre : souligné, il
     prend l'allure d'un lien de navigateur par défaut — la seule chose qui faisait
     « pas fini » sur cette page. Le soulignement revient au survol, où il sert. */
  h2 a {{ color:{PALETTE["ink"]}; text-decoration:none; }}
  h2 a:hover {{ text-decoration:underline; text-decoration-thickness:1px; }}
  .annexes {{ font-size:15.5px; }}
  .preuve {{ margin:3.2rem 0 0; padding-top:1.6rem; border-top:1px solid {PALETTE["rule"]}; }}
  .preuve h2 {{ font-size:1.45rem; margin:0 0 .6rem; }}
  .preuve li {{ max-width:44em; margin:0 0 .5rem; }}
  details {{ margin-top:1.6rem; }}
  summary {{ cursor:pointer; font-weight:600; }}
  .groupe {{ margin:1.8rem 0 0; }}
  .groupe h3 {{ font-size:1.02rem; margin:0; }}
  .licence {{ margin:.1rem 0 .5rem; color:{PALETTE["ink_soft"]}; font-size:15.5px; }}
  table {{ border-collapse:collapse; width:100%; font-size:15.5px; }}
  th, td {{ text-align:left; padding:.34rem .7rem .34rem 0;
            border-bottom:1px solid {PALETTE["rule_soft"]}; }}
  th {{ font-weight:600; color:{PALETTE["ink_soft"]}; }}
  .emp {{ font-family:ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .defile {{ overflow-x:auto; }}
  /* La largeur se limite sur les PARAGRAPHES, pas sur le pied : bornée sur le bloc, elle
     raccourcissait aussi son filet, qui s'arrêtait avant tous les autres. Un trait plus
     court que ses voisins se remarque sans qu'on sache dire pourquoi. */
  footer {{ margin-top:3.4rem; padding-top:1.2rem; border-top:1px solid {PALETTE["rule"]};
            font-size:15.5px; color:{PALETTE["ink_soft"]}; }}
  footer p {{ max-width:44em; }}
  footer a {{ color:{PALETTE["accent"]}; }}
</style></head><body><main>

<h1>{_txt(TITRE)}</h1>
<p class="chapeau">Deux études sur données publiques. Chaque chiffre porte sa source et sa
date, chaque fichier collecté porte son empreinte, et la chaîne qui produit ces pages
tourne toute seule.</p>

<p class="cachet" id="cachet" data-genere="{html.escape(genere_le)}">
  <span id="age"></span><span class="abs">Données compilées le
  <time datetime="{html.escape(genere_le)}">{_txt(genere_le[:10])}</time>{compteur}.</span>
</p>

{_sujets()}

<section class="preuve">
<h2>Comment vérifier que ces chiffres tiennent</h2>
<ul>
<li>Chaque fichier téléchargé est <strong>empreinté en SHA-256</strong> et re-vérifié à
chaque exécution : si un octet a bougé, la chaîne s'arrête au lieu de publier.</li>
<li>Aucune figure n'est dessinée depuis une donnée non certifiée, et une lignée relie
chaque visuel aux données exactes dont il est tiré — c'est elle qui le date.</li>
<li>Les nombres écrits dans les études sont <strong>tenus par des tests</strong> : si une
révision de la donnée source en déplace un, rien n'est publié. Plusieurs figures refusent
même de se dessiner quand la donnée cesse de soutenir leur titre.</li>
<li>Ces pages ne dépendent d'aucun service tiers : ni police distante, ni bibliothèque
appelée ailleurs, aucun appel réseau au chargement.</li>
</ul>

<details>
<summary>Les {n_sources} sources, leurs {n_prod} producteurs et leurs empreintes</summary>
<div class="defile">{_lignes_manifeste(groupes)}</div>
</details>
</section>

<footer>
<p>Données réutilisées sous la licence de leur producteur, indiquée source par source
ci-dessus. Ces organismes ne sont pas associés à ce travail et n'en ont pas validé les
conclusions.</p>
</footer>

</main>
<script>
/* L'âge est recalculé À LA LECTURE : une page statique qui aurait figé « il y a 2 h »
   mentirait dès le lendemain. Sans JavaScript, la date absolue ci-dessus reste juste —
   le script ajoute une information, il n'en remplace aucune. */
(function () {{
  var boite = document.getElementById("cachet");
  var t = Date.parse(boite.getAttribute("data-genere"));
  if (isNaN(t)) return;
  var h = (Date.now() - t) / 3600000;
  var texte;
  if (h < 0) return;                       /* horloge du lecteur en avance : on se tait */
  else if (h < 1) texte = "Rafraîchi il y a moins d'une heure. ";
  else if (h < 24) texte = "Rafraîchi il y a " + Math.round(h) + " h. ";
  else {{
    var j = Math.floor(h / 24);
    texte = "Dernier rafraîchissement il y a " + j + (j > 1 ? " jours" : " jour") + ". ";
    /* La chaîne tourne toutes les 6 h : au-delà d'une journée, le cycle est manqué et la
       page doit le dire elle-même plutôt que de laisser croire à de la donnée fraîche. */
    texte += j > 2 ? "La chaîne automatique semble interrompue. " : "Un cycle a été manqué. ";
    boite.className = "cachet alerte";
  }}
  document.getElementById("age").textContent = texte;
}})();
</script>
</body></html>
"""


def main() -> int:
    if not BUILD_FILE.exists():
        raise SystemExit(
            f"{BUILD_FILE} absent — lancer `python -m demonstrateur.prepare` d'abord. "
            "La page d'accueil affiche une date de compilation : la deviner serait mentir."
        )
    build = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
    groupes, n_sources, n_prod = _manifeste()
    dest = OUTPUTS / "index.html"
    # newline="\n" : sans lui, `write_text` traduit les fins de ligne selon la plateforme
    # et la page écrite sous Windows diffère de celle du runner Linux sur chaque ligne.
    # Git normalise au commit, mais le cron ne doit committer QUE ce qui a changé — mieux
    # vaut que le fichier soit identique dès l'écriture (cf. la règle dans CLAUDE.md).
    dest.write_text(
        _html(build["genere_le"], groupes, n_sources, n_prod, _actualisations()),
        encoding="utf-8", newline="\n",
    )
    print(f"[ok] {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
