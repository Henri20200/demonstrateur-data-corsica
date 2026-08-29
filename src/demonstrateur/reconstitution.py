"""Retrouver les millésimes DÉJÀ PASSÉS dans l'historique Git du manifeste.

`archive.py` ne tient le registre des millésimes que depuis le 20/08/2026. Avant cette
date, la chaîne a pourtant détenu des centaines de versions successives : le cron passe
toutes les six heures depuis le 19/07/2026, et `data/raw/_manifest.json` — le seul fichier
de `data/` qui soit versionné — a enregistré à chaque passage l'empreinte de ce que chaque
source disait ce jour-là. Cet historique est déjà dans Git ; il n'y est simplement pas
sous une forme interrogeable.

Ce module le rend interrogeable, et rien de plus :

    python -m demonstrateur.reconstitution            # rapport, n'écrit rien
    python -m demonstrateur.reconstitution --ecrire   # écrit data/archive/_versions.json

CE QUI SE RECONSTITUE ET CE QUI NE SE RECONSTITUE PAS. Le manifeste porte des
métadonnées : url résolue, empreinte, taille, date de collecte. Il ne porte pas les
OCTETS — `data/raw/` n'est pas versionné, et les versions écrasées avant le 20/08/2026 ont
disparu pour de bon. Une version reconstituée dit donc « à cet instant, la chaîne détenait
ce contenu-là », et ne permettra jamais d'en produire le contenu. C'est la moitié de la
promesse, mais c'est la moitié IRREMPLAÇABLE : un intervalle de connaissance ne se
reconstitue pas à partir de rien, alors que des octets, un producteur les republie
parfois.

D'où le marquage `origine: "manifeste_git"` et `payload_key: null`. Ce n'est pas un détail
d'étiquetage. Une version reconstituée n'a pas d'adresse dans le dépôt durable, donc :

- `retenter_depots_en_attente()` ne peut pas la reprendre, et ne l'essaie pas ;
- `versions_non_deposees()` ne la compte pas — sinon le CI avertirait, toutes les six
  heures et pour toujours, de mille versions qu'aucune reprise ne peut sauver, et
  l'avertissement qui compte, celui d'une panne réseau d'hier, se perdrait dedans ;
- `versions_sans_octets()` les compte, elles et elles seules : un trou définitif reste un
  trou et mérite d'être vu — une fois, pas quatre fois par jour.

QUELLE LIGNE D'HISTOIRE FAIT FOI : LE PREMIER PARENT, par défaut. Le dépôt a deux lignes
qui écrivent le manifeste — le cron, sur master, et les branches de travail, où un
`fetch-data` local committe un manifeste lui aussi. Les fusionner par ordre chronologique
produit une oscillation : la branche détient A, master détient B, la branche continue avec
A parce qu'elle n'a pas été rafraîchie — et le registre affirmerait que la chaîne est
REVENUE à A, ce qui n'est jamais arrivé. Le premier parent suit la ligne d'intégration
seule, où l'état d'une branche n'entre qu'au moment de sa fusion, sous sa forme
réconciliée. `--toutes-branches` existe pour regarder, pas pour écrire.

Conséquence assumée : une source collectée sur une branche le 1er août et fusionnée le 4
est datée du 4. La date est donc TARDIVE, jamais précoce — et c'est le bon sens de
l'erreur. Un backtest qui se croit informé plus tôt qu'en réalité fuit ; un backtest qui
se croit informé plus tard se prive seulement. Ce que le manifeste déclarait, lui, est
conservé tel quel dans `date_collecte` : l'indice d'une connaissance antérieure n'est pas
perdu, il est tenu hors de l'intervalle qui fait foi.

CE MODULE N'INVENTE AUCUNE VERSION, et n'applique PAS `archive_demandee()`. C'est
délibéré : cette fonction arbitre le coût de CONSERVER DES OCTETS pour une source qui n'a
qu'une version possible. Une version reconstituée n'a pas d'octets, donc pas de coût — et
l'historique montre des cas, une source figée recertifiée à la main, où la chaîne a bel et
bien détenu deux contenus successifs. Écarter une preuve déjà en main au nom d'une
politique de stockage serait une perte sèche.

Enfin, il ne réécrit jamais une version observée pour de vrai. Si le registre existe déjà,
la reconstitution vient DEVANT lui et s'arrête à la première version vivante de chaque
source. Un seul cas la fait toucher à une entrée vivante : quand la dernière version
reconstituée porte la MÊME empreinte que la première version vivante, les deux n'en font
qu'une, et c'est sa date de début qui recule. Le registre dit alors « nous détenions ce
contenu depuis le 4 août », ce qui est vrai, au lieu de « depuis le jour où nous avons
allumé l'archive », qui ne l'est pas.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

# `_sauver` plutôt qu'un `json.dump` local : le registre doit sortir aux mêmes octets que
# ceux qu'écrit la collecte vivante, sinon le premier run du cron le reformaterait et
# fabriquerait un diff sur un fichier dont le contenu n'a pas bougé.
from .archive import ORIGINE_RECONSTITUEE, _charger, _sauver
from .config import MANIFEST_FILE, ROOT, VERSIONS_FILE

CHEMIN_MANIFESTE = MANIFEST_FILE.relative_to(ROOT).as_posix()

# La ligne d'histoire qui fait foi. Écrire depuis une AUTRE référence pose un registre
# amputé SANS RIEN SIGNALER : parcouru depuis une branche de travail où `master` vient
# d'être fusionné, le premier parent traverse la fusion en UN pas et saute tout ce que
# l'intégration a fait pendant ce temps. Mesuré le 29/08/2026 : 969 millésimes depuis une
# telle branche, 1 410 depuis la ligne d'intégration — un tiers manquant, en silence.
# Le nom ne suffit pas à se garder : en CI on travaille en HEAD détachée, où « être sur
# master » ne veut rien dire. C'est le COMMIT RÉSOLU qui est comparé.
REF_FAISANT_AUTORITE = "origin/master"
_SEPARATEUR = "\x1f"  # unit separator : ne peut pas apparaître dans un sujet de commit


class HistoriqueIllisible(RuntimeError):
    """Git n'a pas répondu — dépôt absent, référence inconnue, binaire manquant."""


@dataclass(frozen=True)
class Instantane:
    """Ce que le manifeste disait à un commit donné."""

    commit: str
    instant: str  # ISO 8601 UTC, microsecondes forcées
    sujet: str
    entrees: dict[str, dict]


@dataclass
class Rapport:
    """Ce que la reconstitution a vu — y compris ce qu'elle n'a pas su lire."""

    commits: int = 0
    fenetre: tuple[str, str] | None = None
    illisibles: list[str] = field(default_factory=list)
    disparitions: Counter = field(default_factory=Counter)
    sans_empreinte: Counter = field(default_factory=Counter)
    intervalles_inverses: list[str] = field(default_factory=list)
    intervalles_plats: list[str] = field(default_factory=list)
    collectes_posterieures: list[str] = field(default_factory=list)
    fusion: list[str] = field(default_factory=list)

    @property
    def bloquant(self) -> list[str]:
        """Anomalies qui rendraient le registre FAUX, et pas seulement incomplet.

        Un intervalle inversé ou de largeur nulle ne se rattrape pas par une convention :
        il rend une version invisible à `version_connue_a`, qui la sauterait en silence.
        Mieux vaut refuser d'écrire et montrer les commits en cause.
        """
        return self.intervalles_inverses + self.intervalles_plats


def _git(*args: str) -> bytes:
    resultat = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)
    if resultat.returncode != 0:
        detail = resultat.stderr.decode("utf-8", "replace").strip()
        raise HistoriqueIllisible(f"git {' '.join(args[:2])} : {detail}")
    return resultat.stdout


def commit_de(ref: str) -> str:
    """SHA du commit désigné par `ref`, quelle que soit la forme (branche, tag, HEAD, SHA).

    `^{commit}` déréférence un tag annoté : sans lui, deux références qui désignent le même
    commit pourraient se comparer inégales pour une raison qui n'a rien à voir avec
    l'histoire.
    """
    return _git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()


def instant_utc(iso: str) -> str:
    """Date Git -> instant du registre, MICROSECONDES COMPRISES même à zéro.

    Deux raisons, et la seconde n'est pas cosmétique. D'abord Git date en heure locale
    avec décalage (`2026-07-20T15:58:16+02:00`) là où le registre est en UTC : comparer
    les deux sous forme de texte, comme le fait `version_connue_a`, donnerait un ordre
    faux d'une ou deux heures. Ensuite le registre compare ses instants
    LEXICOGRAPHIQUEMENT, et `'.'` (0x2E) précède `'Z'` (0x5A) : `...:21.999999Z` passerait
    AVANT `...:21Z`, alors qu'il le suit d'une seconde presque entière. Tant que tous les
    instants ont la même largeur, l'ordre du texte est l'ordre du temps ; il suffit d'un
    seul écrit sans microsecondes pour que ce ne soit plus vrai.
    """
    horodatage = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return horodatage.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def instantanes(ref: str = "HEAD", premier_parent: bool = True) -> tuple[list[Instantane], Rapport]:
    """Les états successifs du manifeste, du plus ancien au plus récent.

    `git log` rend l'ordre topologique, enfant avant parent ; on l'inverse, et on n'ordonne
    PAS par date : la topologie dit ce qui a suivi quoi, l'horloge n'en est que la trace.
    Un désaccord entre les deux est une anomalie qu'on signale, pas un tri qu'on corrige
    en douce.
    """
    options = ["log", f"--format=%H{_SEPARATEUR}%aI{_SEPARATEUR}%s"]
    if premier_parent:
        options.append("--first-parent")
    options += [ref, "--", CHEMIN_MANIFESTE]

    lignes = _git(*options).decode("utf-8", "replace").splitlines()
    rapport = Rapport()
    vus: list[Instantane] = []
    for ligne in reversed(lignes):
        if not ligne.strip():
            continue
        commit, date, sujet = ligne.split(_SEPARATEUR, 2)
        try:
            entrees = json.loads(_git("show", f"{commit}:{CHEMIN_MANIFESTE}").decode("utf-8"))
        except (HistoriqueIllisible, UnicodeDecodeError, json.JSONDecodeError) as exc:
            # Un commit qui supprime le manifeste, ou un manifeste d'un format antérieur :
            # on saute cet état sans perdre les autres, et on le dit.
            rapport.illisibles.append(f"{commit[:8]} {sujet[:60]} — {type(exc).__name__}")
            continue
        vus.append(Instantane(
            commit=commit,
            instant=instant_utc(date),
            sujet=sujet,
            entrees={k: v for k, v in entrees.items() if isinstance(v, dict)},
        ))
    rapport.commits = len(vus)
    if vus:
        rapport.fenetre = (vus[0].instant, vus[-1].instant)
    return vus, rapport


def _entree(manifeste: dict, snap: Instantane) -> dict:
    """Une entrée de registre, de la MÊME forme que celles de la collecte vivante.

    `revision_policy` reste `unknown` sans consulter `sources.yaml` : la déclaration
    d'aujourd'hui n'a pas à être prêtée à un millésime d'il y a un mois, où rien n'était
    déclaré. `date_collecte` est recopiée du manifeste — c'est ce que la chaîne DÉCLARAIT
    ce jour-là, à distinguer de `first_observed_at`, qui est ce qu'elle PROUVE.
    """
    return {
        "sha256": manifeste["sha256"],
        "resolved_url": manifeste.get("url", ""),
        "first_observed_at": snap.instant,
        "superseded_at": None,
        "fichier_archive": None,
        "payload_key": None,
        "payload_archived": False,
        "taille_octets": manifeste.get("taille_octets"),
        "revision_policy": "unknown",
        "origine": ORIGINE_RECONSTITUEE,
        "commit": snap.commit,
        "date_collecte": manifeste.get("date_collecte"),
    }


def reconstituer(vus: list[Instantane], rapport: Rapport | None = None) -> tuple[dict, Rapport]:
    """Registre déduit des instantanés — une version par changement d'empreinte.

    Même règle que la collecte vivante : on ne compare qu'à la DERNIÈRE version connue de
    la source, jamais à l'ensemble. Un contenu qui revient après en avoir remplacé un
    autre ouvre donc une nouvelle version, avec son propre intervalle — c'est arrivé le
    22/07/2026, quand la fusion d'une branche a ramené sur master un manifeste antérieur à
    un rafraîchissement du cron. Le registre le dit, parce que c'est ce qui s'est passé.

    Une source qui DISPARAÎT du manifeste ne voit pas son intervalle se refermer : le
    registre vivant ne le fermerait pas davantage (il ne sait rien d'une source que
    `fetch` ne lui présente plus), et une entrée ouverte dit « c'est le dernier contenu que
    nous ayons détenu », ce qui reste vrai. Les disparitions sont comptées dans le rapport.
    """
    rapport = rapport or Rapport()
    index: dict[str, list[dict]] = {}
    derniere_empreinte: dict[str, str] = {}
    deja_vues: set[str] = set()

    for snap in vus:
        presentes = set(snap.entrees)
        for source_id in sorted(deja_vues - presentes):
            rapport.disparitions[source_id] += 1
        deja_vues |= presentes

        for source_id, manifeste in sorted(snap.entrees.items()):
            sha = manifeste.get("sha256")
            if not sha:
                rapport.sans_empreinte[source_id] += 1
                continue
            if derniere_empreinte.get(source_id) == sha:
                continue

            versions = index.setdefault(source_id, [])
            if versions:
                precedente = versions[-1]
                debut = precedente["first_observed_at"]
                if snap.instant < debut:
                    rapport.intervalles_inverses.append(
                        f"{source_id} : {snap.commit[:8]} ({snap.instant}) précède "
                        f"{precedente['commit'][:8]} ({debut}) alors qu'il le suit dans Git"
                    )
                elif snap.instant == debut:
                    rapport.intervalles_plats.append(
                        f"{source_id} : {precedente['commit'][:8]} et {snap.commit[:8]} "
                        f"portent le même instant ({debut}) — intervalle de largeur nulle"
                    )
                precedente["superseded_at"] = snap.instant

            collecte = manifeste.get("date_collecte")
            if collecte and collecte > snap.instant[:10]:
                rapport.collectes_posterieures.append(
                    f"{source_id} : date_collecte {collecte} postérieure au commit "
                    f"{snap.commit[:8]} du {snap.instant[:10]}"
                )
            versions.append(_entree(manifeste, snap))
            derniere_empreinte[source_id] = sha

    return index, rapport


def fusionner(existant: dict, reconstitue: dict, rapport: Rapport) -> dict:
    """Place la reconstitution DEVANT le registre vivant, sans lui retirer une seule entrée.

    Une entrée vivante ne peut être touchée que d'une façon : sa date de début recule,
    quand la dernière version reconstituée porte la même empreinte qu'elle. Les deux ne
    sont alors pas deux versions mais une seule, dont nous savons maintenant qu'elle
    commençait plus tôt. Toute autre modification serait une réécriture de ce que la
    chaîne a réellement observé — et un registre historique fait foi, il ne se corrige pas
    après coup.
    """
    fusionne: dict[str, list[dict]] = {}
    for source_id in sorted(set(existant) | set(reconstitue)):
        vivantes = [dict(v) for v in existant.get(source_id, [])]
        anciennes = [dict(v) for v in reconstitue.get(source_id, [])]
        if not vivantes:
            fusionne[source_id] = anciennes
            continue

        debut_vivant = vivantes[0]["first_observed_at"]
        avant = [v for v in anciennes if v["first_observed_at"] < debut_vivant]
        ecartees = len(anciennes) - len(avant)
        if ecartees:
            rapport.fusion.append(
                f"{source_id} : {ecartees} version(s) reconstituée(s) écartée(s), le "
                f"registre vivant commence à {debut_vivant}"
            )
        if avant and avant[-1]["sha256"] == vivantes[0]["sha256"]:
            vivantes[0]["first_observed_at"] = avant[-1]["first_observed_at"]
            rapport.fusion.append(
                f"{source_id} : même empreinte de part et d'autre — la version vivante "
                f"commence en fait le {avant[-1]['first_observed_at'][:10]}"
            )
            avant = avant[:-1]
            debut_vivant = vivantes[0]["first_observed_at"]
        if avant:
            avant[-1]["superseded_at"] = debut_vivant
        fusionne[source_id] = avant + vivantes
    return fusionne


def _afficher(index: dict, rapport: Rapport, ecrire: bool) -> None:
    versions = sum(len(v) for v in index.values())
    reconstituees = sum(
        1 for entrees in index.values() for e in entrees
        if e.get("origine") == ORIGINE_RECONSTITUEE
    )
    print(f"Manifeste   : {CHEMIN_MANIFESTE}")
    print(f"Commits lus : {rapport.commits}")
    if rapport.fenetre:
        print(f"Fenêtre     : {rapport.fenetre[0][:19]}Z -> {rapport.fenetre[1][:19]}Z")
    print(f"Sources     : {len(index)}    versions : {versions} "
          f"(dont {reconstituees} reconstituées, sans octets)")

    for titre, lignes in (
        ("Manifestes illisibles", rapport.illisibles),
        ("Sources sans empreinte",
         [f"{k} : {n} fois" for k, n in rapport.sans_empreinte.items()]),
        ("Sources disparues du manifeste",
         [f"{k} : {n} fois" for k, n in rapport.disparitions.items()]),
        ("Dates de collecte postérieures au commit", rapport.collectes_posterieures),
        ("Fusion avec le registre existant", rapport.fusion),
        ("ANOMALIES BLOQUANTES", rapport.bloquant),
    ):
        if lignes:
            print(f"\n{titre} ({len(lignes)}) :")
            for ligne in lignes[:20]:
                print(f"  - {ligne}")
            if len(lignes) > 20:
                print(f"  ... et {len(lignes) - 20} autre(s)")

    print("\nVersions par source :")
    for source_id, entrees in sorted(index.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        debut, fin = entrees[0]["first_observed_at"], entrees[-1]["first_observed_at"]
        print(f"  {len(entrees):5d}  {source_id:34s} {debut[:16]}Z -> {fin[:16]}Z")

    if not ecrire:
        print(f"\nRien n'a été écrit. `--ecrire` pour poser {VERSIONS_FILE}.")


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        prog="python -m demonstrateur.reconstitution",
        description="Reconstitue les millésimes passés depuis l'historique Git du manifeste.",
    )
    analyseur.add_argument("--ecrire", action="store_true",
                           help="écrit le registre (sans ce drapeau : rapport seulement)")
    analyseur.add_argument("--ref", default=None,
                           help="référence Git à parcourir (défaut : HEAD pour le rapport, "
                                f"{REF_FAISANT_AUTORITE} pour --ecrire)")
    analyseur.add_argument("--ref-autorite", default=REF_FAISANT_AUTORITE,
                           help="référence dont le commit fait foi pour écrire "
                                f"(défaut : {REF_FAISANT_AUTORITE})")
    analyseur.add_argument("--toutes-branches", action="store_true",
                           help="suivre aussi les branches fusionnées (à regarder, pas à écrire)")
    options = analyseur.parse_args(argv)

    # Le rapport se lit d'où l'on veut ; l'ÉCRITURE part de la ligne d'intégration, jamais
    # de là où le poste de travail se trouve. Sans ce défaut, un `--ecrire` lancé depuis une
    # branche à jour poserait un registre amputé du tiers, et son rapport aurait l'air normal.
    ref = options.ref or (options.ref_autorite if options.ecrire else "HEAD")

    if options.ecrire:
        try:
            parcourue, autorite = commit_de(ref), commit_de(options.ref_autorite)
        except HistoriqueIllisible as exc:
            # Cas réel : un clone superficiel, où la référence distante n'a jamais été
            # rapatriée. Refuser est la bonne réponse — écrire depuis ce qu'on a sous la
            # main poserait un registre amputé — mais l'opérateur doit savoir quoi faire.
            print(f"[!] Écriture refusée : {options.ref_autorite} est introuvable ici "
                  f"({exc}).\n    Rapatrier l'histoire complète (`git fetch --unshallow` "
                  "ou `fetch-depth: 0` en CI),\n    ou nommer explicitement la référence "
                  "qui fait foi avec --ref-autorite.", file=sys.stderr)
            return 2
        if parcourue != autorite:
            print(f"\n[!] Écriture refusée : {ref} ({parcourue[:8]}) n'est pas "
                  f"{options.ref_autorite} ({autorite[:8]}).\n"
                  "    Le premier parent d'une autre ligne traverse les fusions d'un seul "
                  "pas et saute\n    ce que l'intégration a fait pendant ce temps : le "
                  "registre serait amputé sans le dire.\n"
                  "    Lire ailleurs est libre (sans --ecrire) ; écrire se fait depuis la "
                  "ligne qui fait foi.", file=sys.stderr)
            return 1

    try:
        vus, rapport = instantanes(ref, premier_parent=not options.toutes_branches)
    except HistoriqueIllisible as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 2
    if not vus:
        print(f"[!] Aucun état de {CHEMIN_MANIFESTE} sous {ref}.", file=sys.stderr)
        return 2

    index, rapport = reconstituer(vus, rapport)
    existant = _charger(VERSIONS_FILE)
    if existant:
        index = fusionner(existant, index, rapport)

    _afficher(index, rapport, options.ecrire)
    if not options.ecrire:
        return 0
    if rapport.bloquant:
        print("\n[!] Écriture refusée : les anomalies ci-dessus rendraient le registre faux.",
              file=sys.stderr)
        return 1
    if options.toutes_branches:
        print("\n[!] Écriture refusée : `--toutes-branches` mêle les lignes de travail à la "
              "ligne d'intégration et fabrique des retours en arrière que la chaîne n'a "
              "jamais faits. Écrire depuis le premier parent.", file=sys.stderr)
        return 1
    _sauver(VERSIONS_FILE, index)
    print(f"\n[ok] {VERSIONS_FILE} écrit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
