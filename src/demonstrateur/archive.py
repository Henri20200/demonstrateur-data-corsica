"""Millésimes : conserver ce qu'une source disait, et depuis quand nous le savions.

Le manifeste dit ce que la source dit AUJOURD'HUI. Il ne dit pas ce qu'elle disait le
15 mai — or c'est exactement ce qu'exige une prévision rejouée sans fuite temporelle :
« quelle version cette chaîne détenait-elle à l'instant T ? », et non « quelle est
aujourd'hui la meilleure version de cette série ? ».

Jusqu'ici `fetch` remplaçait le fichier d'un jeu rafraîchi (`part.replace(dest)`) : la
version précédente disparaissait. Comme `data/` n'est pas versionné, elle disparaissait
pour de bon. Le manifeste, lui, est commité — donc l'empreinte et la date de chaque
version passée restent lisibles dans l'historique Git, mais pas leur CONTENU. On sait
quand la donnée a changé ; on ne sait plus ce qu'elle disait avant.

Ce module ajoute de la mémoire, sans rien retirer :

    data/raw/<filename>                         inchangé — dernière version, tous les
                                                consommateurs existants continuent
    data/archive/<source_id>/
        20260819T060011Z_ab12cd34.csv.gz        copie locale du millésime
    data/archive/_versions.json                 index des versions — VERSIONNÉ
    <dépôt objet>/archive/<source_id>/2026/08/
        20260819T060011Z_<sha256>.csv.gz        les OCTETS, durables (cf. depot.py)

**Une archive n'est écrite que lorsque l'empreinte change.** Le cron passe toutes les
6 h : archiver à chaque passage produirait quatre copies identiques par jour et
transformerait un registre de millésimes en journal de scrutation.

TROIS DURABILITÉS, ET IL FAUT LES DISTINGUER.

1. l'INDEX (`_versions.json`) ne porte que des métadonnées : petit, versionné, il survit à
   tout. C'est la seule partie qui ne se reconstruit pas après coup ;
2. les OCTETS vivent dans un dépôt objet append-only, hors de Git et hors du cache de CI
   (`depot.py`). Sans lui, l'index promet une version dont plus personne ne peut produire
   le contenu : savoir QUELLE version s'appliquait à une date donnée est la moitié du
   problème, pouvoir en produire les octets est l'autre ;
3. la copie LOCALE sous `data/archive/` n'est ni l'un ni l'autre : commodité de poste, et
   filet de reprise quand le dépôt distant a refusé une version. En CI elle ne survit pas
   au run — le cache d'Actions n'est pas réécrit en régime établi.

D'où `payload_archived` / `payload_key` dans l'index. UNE VERSION EST INDEXÉE MÊME SI SES
OCTETS N'ONT PAS PU ÊTRE DÉPOSÉS, et elle est alors marquée `payload_archived: false` :
l'intervalle de connaissance, lui, n'est jamais perdu pour une panne réseau. Mais il faut
retenter, et c'est le vrai piège de ce module — au run suivant l'empreinte n'est PLUS
nouvelle, donc le chemin ordinaire ne fait rien. Sans reprise explicite, un incident
passager rendrait définitivement manquante une version que l'index jure connaître. Deux
reprises couvrent le cas : la version courante est reproposée à chaque
`enregistrer_version` (fetch en retélécharge ou en revérifie les octets), et
`retenter_depots_en_attente()` rattrape les versions déjà dépassées depuis leur copie
locale.

`last_checked_at` est écrit à part, dans un fichier NON versionné, et c'est délibéré : le
dépôt met en avant que le rafraîchissement planifié « ne committe que ce qui a réellement
changé ». Une date de dernier contrôle réécrite à chaque run dans un fichier versionné
produirait un commit toutes les 6 h et démentirait cette propriété.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from . import depot
from .config import DATA_ARCHIVE, LAST_CHECKED_FILE, VERSIONS_FILE

# Politiques de révision déclarables dans sources.yaml. Le défaut est `unknown`, et
# `unknown` s'archive : nous croyons savoir aujourd'hui quelles sources se révisent, nous
# découvrirons demain que non. Le coût disque d'un millésime est dérisoire devant le coût
# d'un millésime perdu, qui est infini.
POLITIQUES = ("immutable", "append_only", "revisable", "unknown")
_SANS_ARCHIVE = ("immutable", "append_only")

# D'où vient une entrée du registre, et ce n'est pas de la décoration. `collecte` : la
# chaîne a tenu ces octets, ils ont une adresse dans le dépôt durable, et un dépôt raté se
# retente. `manifeste_git` : la version a été RECONSTITUÉE après coup depuis l'historique
# du manifeste (cf. `reconstitution.py`) — l'intervalle de connaissance est sûr, les octets
# n'existent nulle part et n'existeront jamais, `data/raw/` n'ayant jamais été versionné.
# Confondre les deux ferait retenter sans fin des dépôts impossibles et noierait les vrais
# incidents dans le bruit.
ORIGINE_COLLECTE = "collecte"
ORIGINE_RECONSTITUEE = "manifeste_git"


def _maintenant() -> str:
    """Horodatage UTC ISO 8601, À LA MICROSECONDE — et ce n'est pas du zèle.

    Les intervalles de connaissance sont semi-ouverts : `[first_observed_at ; superseded_at[`.
    Deux versions observées dans la même seconde produiraient, à la seconde près, un
    intervalle de LARGEUR NULLE — c'est-à-dire une version que la chaîne n'aurait
    « jamais détenue », qu'une interrogation par instant sauterait en silence. Le cron
    passe toutes les 6 h et n'y arriverait jamais ; un rattrapage manuel, deux runs
    concurrents ou un test, si. La précision coûte six caractères par horodatage.

    Elle est FORCÉE, jamais laissée à `isoformat()`, qui omet les microsecondes quand
    elles valent exactement zéro. Une fois sur un million le registre porterait alors un
    instant plus court que ses voisins — et `version_connue_a` compare ses bornes comme du
    TEXTE, où `'.'` (0x2E) précède `'Z'` (0x5A) : `...:21.999999Z` passerait AVANT
    `...:21Z`, qu'il suit pourtant d'une seconde presque entière. Largeur fixe, toujours.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def politique(meta: dict) -> str:
    """Politique de révision déclarée, `unknown` à défaut.

    Volontairement distincte de `glissant`, qui répond à une autre question. `glissant`
    dit « re-télécharger à chaque run » (propriété de collecte) ; `revision_policy` dit
    « les valeurs passées peuvent-elles changer » (propriété de la donnée). Une fenêtre
    glissante purement additive n'est pas révisable, et une série mensuelle figée entre
    deux publications peut l'être.
    """
    valeur = meta.get("revision_policy", "unknown")
    return valeur if valeur in POLITIQUES else "unknown"


def archive_demandee(meta: dict) -> bool:
    """Faut-il conserver les versions SUCCESSIVES de cette source ?

    Ne décide PAS s'il faut déposer la source : TOUTE source reçoit une copie initiale
    dans le dépôt durable, y compris figée ou `immutable`. Jusqu'ici son unique copie était
    `data/raw/<filename>`, c'est-à-dire, en CI, un cache d'Actions — et un cache n'est pas
    une archive patrimoniale. Cette fonction ne décide que de la SUITE.

    `archive_versions` tranche s'il est déclaré. Sinon :

    - une source NON glissante n'est téléchargée qu'une fois et jamais re-confrontée à son
      producteur : elle ne peut pas produire de deuxième version ;
    - une source glissante conserve ses versions, sauf politique `immutable` (le contenu
      ne bouge pas) ou `append_only` (l'état passé se reconstitue par troncature à la date
      voulue).

    Le défaut reste donc `unknown` -> conserver, mais seulement là où une deuxième version
    est possible.

    CONSÉQUENCE À CONNAÎTRE : hors de ce périmètre, l'entrée d'index reste ouverte
    indéfiniment (`superseded_at` nul) et ne suit pas les changements de contenu. Elle dit
    vrai sur ce que nous DÉTENONS — la copie déposée — pas sur ce que la source publie
    aujourd'hui, qui est l'affaire du manifeste.
    """
    explicite = meta.get("archive_versions")
    if explicite is not None:
        return bool(explicite)
    if not meta.get("glissant"):
        return False
    return politique(meta) not in _SANS_ARCHIVE


class RegistreIllisible(RuntimeError):
    """L'index des millésimes ne se lit pas — la chaîne s'arrête plutôt que de le remplacer."""


def _charger(fichier: Path) -> dict:
    """Lit un index JSON. STRICT PAR DÉFAUT : un contenu invalide lève, il ne se tait pas.

    Jusqu'au 30/08/2026 cette fonction avalait un `JSONDecodeError` et rendait `{}` —
    « on repart d'un index vide plutôt que d'interrompre la chaîne ». La suite était
    mécanique et silencieuse : chaque `enregistrer_version` ré-observait toutes les
    sources « pour la première fois », redéposait leurs octets sous des clés NEUVES
    (l'instant fait partie de la clé), et le cron committait le registre reconstruit. Les
    intervalles de connaissance — la seule partie qui ne se reconstruit pas après coup —
    quittaient le fichier vivant sans un avertissement. Le commentaire d'alors affirmait
    que « la perte est signalée par l'absence d'historique » : aucun code ne regardait
    cette absence.

    Rien n'était irréversible — le fichier est versionné — mais rien ne le SIGNALAIT,
    l'inverse exact du disjoncteur de volume, qui rougit un run pour bien moins. L'erreur
    remonte donc, et `fetch` s'arrête AVANT de collecter.

    Strict par défaut, et c'est la propriété qui fait tenir le correctif : un futur
    appelant qui oublierait de choisir hérite de la prudence, pas du silence. Le seul
    fichier tolérant est le cache, par `_charger_tolerant`.
    """
    if not fichier.exists():
        return {}
    contenu = fichier.read_text(encoding="utf-8")
    try:
        return json.loads(contenu)
    except json.JSONDecodeError as exc:
        raise RegistreIllisible(
            f"{fichier} : JSON invalide à la ligne {exc.lineno}, colonne {exc.colno} "
            f"({exc.msg}) — {len(contenu)} octets lus. Ce fichier est VERSIONNÉ et fait "
            "foi : le restaurer depuis Git (git checkout -- data/archive/_versions.json) "
            "plutôt que le laisser se reconstruire, ce qui perdrait les intervalles de "
            "connaissance qu'aucune reprise ne recalcule."
        ) from exc


def _charger_tolerant(fichier: Path) -> dict:
    """Idem, pour un fichier dont la perte est SANS CONSÉQUENCE et voulue.

    Réservé à `_last_checked.json`, qui n'est pas versionné (délibérément, pour que le
    cron « ne committe que ce qui a réellement changé ») et ne porte rien qui ne se
    retrouve : c'est un cache de dates de contrôle. Faire échouer une collecte pour un
    cache tronqué serait la faute inverse de celle qu'on vient de corriger.
    """
    try:
        return _charger(fichier)
    except RegistreIllisible:
        return {}


def _sauver(fichier: Path, contenu: dict) -> None:
    """Écriture ATOMIQUE : fichier temporaire, puis remplacement d'un bloc.

    L'écriture directe précédente était la MOITIÉ MANQUANTE du défaut ci-dessus : un
    processus tué en pleine écriture laissait exactement le JSON tronqué que `_charger`
    avalait au run suivant. Corriger la lecture sans corriger l'écriture aurait changé une
    perte silencieuse en arrêt de chaîne régulier ; les deux vont ensemble.

    Même geste que `prepare._ecrire_lignee`. Le `.tmp` reste gitignoré : `data/archive/*`
    l'est, `_versions.json` étant la seule exception.
    """
    fichier.parent.mkdir(parents=True, exist_ok=True)
    tmp = fichier.with_name(fichier.name + ".tmp")
    tmp.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(fichier)


def _extension(filename: str) -> str:
    """Chaîne complète des suffixes (`.csv.gz` et pas seulement `.gz`)."""
    suffixes = Path(filename).suffixes
    return "".join(suffixes[-2:]) if suffixes[-2:] == [".csv", ".gz"] else (
        suffixes[-1] if suffixes else ""
    )


def noter_controle(source_id: str) -> None:
    """Enregistre que la source a été examinée maintenant (fichier NON versionné).

    Distingue « aucune version nouvelle parce que rien n'a changé » de « aucune version
    nouvelle parce que nous ne regardions pas ». Le backtest a besoin de cette différence :
    un trou dans les millésimes n'a pas le même sens dans les deux cas.
    """
    index = _charger_tolerant(LAST_CHECKED_FILE)
    index[source_id] = _maintenant()
    _sauver(LAST_CHECKED_FILE, index)


@lru_cache(maxsize=1)
def _depot_durable() -> depot.Depot | None:
    """Dépôt distant du run, résolu une seule fois — et annoncé une seule fois s'il manque."""
    try:
        distant = depot.configurer()
    except depot.DepotMalConfigure as exc:
        print(f"[!] Dépôt durable NON utilisé — {exc}")
        return None
    if distant is None:
        print("[i] Dépôt durable non configuré (ARCHIVE_BUCKET) : les millésimes sont "
              "indexés, leurs octets restent locaux et seront déposés plus tard.")
    return distant


# État du disjoncteur de volume, pour la DURÉE D'UN RUN. Deux variables et pas une :
# `_VOLUME_DEPOSE` est une mesure — les octets que le stockage détient déjà —, `_DISJONCTEUR`
# est une décision, celle de ne plus rien envoyer. Une fois la décision prise on ne remesure
# pas : un run qui redéposerait « les petits fichiers seulement » après un refus laisserait
# un état que personne ne saurait relire, alors qu'un disjoncteur se voit d'un bloc.
_VOLUME_DEPOSE: int | None = None
_DISJONCTEUR: str | None = None
# Second verrou de run, même forme et raison OPPOSÉE. Le disjoncteur arrête un dépôt qui
# marche trop ; celui-ci arrête un dépôt qui ne peut pas marcher. Une configuration
# refusée le sera pour toutes les sources du run : continuer à essayer, c'est produire
# cinquante-trois fois le même message et trois cents secondes de pauses inutiles — c'est
# ce qu'a fait le run 33318617637 du 30/08/2026, en restant vert.
_MAL_CONFIGURE: str | None = None


def volume_depose() -> int:
    """Octets que le dépôt distant détient, d'après l'index — la seule mesure sans réseau.

    Ne compte QUE `payload_archived: true`, et c'est le point : une version indexée dont
    les octets ne sont jamais partis n'occupe rien chez l'hébergeur, et les millésimes
    reconstitués depuis Git (`origine: manifeste_git`) n'ont pas d'octets du tout — 1 445
    d'entre eux au 29/08/2026. Les compter fermerait le robinet sur un volume imaginaire.
    """
    index = _charger(VERSIONS_FILE)
    return sum(
        version.get("taille_octets") or 0
        for versions in index.values()
        for version in versions
        if version.get("payload_archived")
    )


def verifier_registre() -> None:
    """Lit l'index UNE fois, pour échouer avant que quoi que ce soit ne soit collecté.

    L'erreur remonterait de toute façon du premier `enregistrer_version`, mais tard : des
    sources auraient déjà été téléchargées, le manifeste écrit, et l'arrêt surviendrait
    au milieu d'un run à moitié fait. Le contrôle en tête coûte une lecture de fichier et
    rend l'échec propre : rien n'a bougé, il n'y a qu'à restaurer et relancer.

    Lève `RegistreIllisible` ; ne rend rien, l'index n'étant pas gardé en mémoire (chaque
    appelant le relit, et c'est ce qui évite deux vues divergentes dans le même run).
    """
    _charger(VERSIONS_FILE)


def seuil_franchi() -> str | None:
    """Message du refus si le disjoncteur a sauté pendant ce run, sinon None.

    `fetch` s'en sert pour ROUGIR le run sans l'interrompre. L'arbitrage est celui de tout
    ce module : le dépôt s'arrête, la collecte continue — des octets se redéposent, un
    intervalle de connaissance ne se rattrape pas — mais un changement de régime ne doit
    pas s'installer derrière un cron vert.
    """
    return _DISJONCTEUR


def configuration_refusee() -> str | None:
    """Message si le dépôt a été refusé pour cause de CONFIGURATION pendant ce run.

    Jumeau de `seuil_franchi`, et même usage dans `fetch` : rougir le run sans interrompre
    la collecte. Ce qui les sépare est ce qu'il faut faire ensuite — un seuil se rediscute,
    une configuration se corrige — et c'est pourquoi les deux messages ne se mélangent pas.

    Sans lui, une clé malformée était indiscernable d'une coupure réseau : elle aurait
    échoué à chaque run, indéfiniment, derrière un cron vert, pendant que les versions
    dépassées perdaient leurs octets pour de bon (47 le matin du 30/08/2026, 86 le soir).
    """
    return _MAL_CONFIGURE


def _deposer(source_id: str, cle: str, fichier: Path) -> bool:
    """Dépose les octets. True SEULEMENT si le stockage distant les détient à coup sûr.

    Ne lève jamais : une collecte n'a pas à échouer parce qu'un stockage est indisponible,
    ni parce qu'un seuil de volume est atteint. L'échec se lit dans l'index
    (`payload_archived: false`), donc il se retente — une exception ici perdrait en plus
    l'intervalle de connaissance, qui, lui, est irremplaçable.

    DEUX REFUS DE NATURES DIFFÉRENTES y mènent, et ils ne se confondent pas : la panne se
    retente au run suivant, le seuil franchi ferme le robinet pour tout le run et se
    rediscute avant de rouvrir.
    """
    global _VOLUME_DEPOSE, _DISJONCTEUR, _MAL_CONFIGURE

    distant = _depot_durable()
    if distant is None:
        return False
    if _DISJONCTEUR is not None or _MAL_CONFIGURE is not None:
        # Déjà refusé ce run : on ne mesure même plus, et surtout on n'envoie rien.
        return False

    if _VOLUME_DEPOSE is None:
        _VOLUME_DEPOSE = volume_depose()
    taille = fichier.stat().st_size
    try:
        depot.verifier_seuil(_VOLUME_DEPOSE, taille)
    except depot.SeuilArchiveAtteint as exc:
        _DISJONCTEUR = str(exc)
        print(f"[!] {source_id} : dépôt REFUSÉ — {exc}")
        print("[!] Plus aucun octet ne partira pendant ce run. Les versions restent "
              "indexées `payload_archived: false` : rien n'est perdu, tout est suspendu.")
        return False

    try:
        distant.deposer(cle, fichier)
    except depot.DepotMalConfigure as exc:
        # AVANT `DepotIndisponible`, dont il descend. Et le message ne promet PAS de
        # reprise : il n'y en aura pas tant que la configuration n'aura pas changé.
        _MAL_CONFIGURE = str(exc)
        print(f"[!] {source_id} : dépôt REFUSÉ — {exc}")
        print("[!] Configuration en cause : plus aucun octet ne partira pendant ce run, et "
              "aucune reprise n'y changera rien. Les versions restent indexées "
              "`payload_archived: false` ; le run se termine en ÉCHEC.")
        return False
    except depot.DepotIndisponible as exc:
        print(f"[!] {source_id} : octets NON déposés ({exc}) — version indexée "
              "`payload_archived: false`, reprise au prochain run.")
        return False
    # Après le retour de `deposer`, donc après vérification par le stockage : le volume ne
    # s'incrémente que d'octets réellement détenus, comme `payload_archived`.
    _VOLUME_DEPOSE += taille
    return True


def _copier_localement(source_id: str, meta: dict, fichier: Path,
                       instant: str, sha: str) -> str | None:
    """Copie de service sous `data/archive/<source_id>/`. Retourne son nom, ou None.

    Porte le même horodatage que la clé distante : un millésime se reconnaît des deux
    côtés sans table de correspondance.
    """
    if not archive_demandee(meta):
        return None
    nom = f"{depot.horodatage_compact(instant)}_{sha[:8]}{_extension(meta['filename'])}"
    dossier = DATA_ARCHIVE / source_id
    dossier.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(fichier, dossier / nom)
    except OSError as exc:  # noqa: BLE001
        # Disque plein, permission refusée : on perd le filet de reprise, jamais
        # l'intervalle de connaissance.
        print(f"[!] {source_id} : copie locale impossible ({exc}).")
        return None
    return nom


def _retenter_depot(source_id: str, version: dict, fichier: Path, index: dict) -> bool:
    """Redépose les octets d'une version déjà indexée mais jamais parvenue au stockage.

    `fichier` doit porter EXACTEMENT le contenu de cette version — l'appelant l'établit en
    comparant les empreintes, jamais en le supposant. Déposer sous la clé d'une version des
    octets qui n'en sont pas serait pire que l'absence : l'index cesserait de dire vrai, et
    rien ne le signalerait.
    """
    if version.get("payload_archived") or not version.get("payload_key"):
        return False
    if not fichier.exists():
        return False
    if not _deposer(source_id, version["payload_key"], fichier):
        return False
    version["payload_archived"] = True
    _sauver(VERSIONS_FILE, index)
    print(f"[ok] {source_id} : octets rattrapés — {version['payload_key']}")
    return True


def enregistrer_version(source_id: str, meta: dict, fichier: Path, sha: str) -> dict | None:
    """Enregistre `fichier` comme millésime s'il porte une empreinte encore jamais observée.

    Retourne l'entrée d'index créée, ou None si la version était déjà connue (cas ordinaire
    d'un run qui ne trouve rien de neuf) ou si la source ne conserve pas ses versions
    successives.

    L'ORDRE DES ÉCRITURES EST LE POINT DÉLICAT, et il est celui-ci : octets d'abord, index
    ensuite. Un index écrit avant le dépôt annoncerait une version dont les octets ne sont
    peut-être jamais arrivés — et l'empreinte n'étant plus nouvelle au run suivant,
    personne ne repasserait les chercher. Dans l'autre sens, le pire des cas est une
    version déposée mais non indexée : un objet orphelin, que le run suivant réécrira à
    l'identique sous la même clé. On préfère de loin l'orphelin au trou.

    Pose sur la version précédente son `superseded_at`. Chaque version connue porte donc
    un intervalle de connaissance `[first_observed_at ; superseded_at[` — la version
    courante ayant `superseded_at` nul. C'est ce qui permettra de demander, à une origine
    de prévision donnée, quelle version cette chaîne détenait à cet instant.
    """
    noter_controle(source_id)

    index = _charger(VERSIONS_FILE)
    versions: list[dict] = index.get(source_id, [])

    if versions and versions[-1].get("sha256") == sha:
        # Rien de neuf — sauf, peut-être, des octets qui n'ont jamais atteint le stockage.
        # C'est ici, et nulle part ailleurs, qu'on tient encore le contenu de cette
        # version : `fichier` vient d'être téléchargé ou revérifié sous cette empreinte.
        _retenter_depot(source_id, versions[-1], fichier, index)
        return None

    if versions and not archive_demandee(meta):
        # Contenu nouveau, mais cette source ne conserve pas ses millésimes : sa copie
        # initiale suffit (cf. `archive_demandee`).
        return None

    instant = _maintenant()
    cle = depot.cle_objet(source_id, instant, sha, _extension(meta["filename"]))
    # Copie locale avant le réseau : si le processus meurt pendant l'envoi, le filet de
    # reprise existe déjà.
    copie = _copier_localement(source_id, meta, fichier, instant, sha)
    depose = _deposer(source_id, cle, fichier)

    if versions:
        versions[-1]["superseded_at"] = instant
    entree = {
        "sha256": sha,
        # L'url RÉSOLUE (jetons {AAAA}/{MM}/{JJ} expansés, secrets encore sous forme de
        # gabarit `${NOM}` — même régime que le manifeste, aucune valeur de jeton ici).
        # C'est elle qui distingue deux choses que l'empreinte seule confond :
        #   même url + empreinte nouvelle  -> RÉVISION de la même période de référence ;
        #   url différente                 -> période de référence SUIVANTE (LCSQA publie
        #                                     un fichier par jour, cf. `date_url`).
        # Les deux méritent d'être conservées, mais elles ne veulent pas dire la même
        # chose pour un backtest, et rien d'autre dans l'index ne permet de les séparer.
        # CANDIDAT, et pas règle : une source peut garder son url pendant que la période
        # de référence glisse à l'intérieur du contenu.
        "resolved_url": meta["url"],
        "first_observed_at": instant,
        "superseded_at": None,
        "fichier_archive": copie,
        "payload_key": cle,
        "payload_archived": depose,
        "taille_octets": fichier.stat().st_size,
        "revision_policy": politique(meta),
        "origine": ORIGINE_COLLECTE,
    }
    versions.append(entree)
    index[source_id] = versions
    _sauver(VERSIONS_FILE, index)
    return entree


def retenter_depots_en_attente() -> list[str]:
    """Redépose les versions DÉPASSÉES dont les octets n'ont jamais atteint le stockage.

    La reprise ordinaire a lieu dans `enregistrer_version` : la version courante est
    reproposée à chaque run, puisque `fetch` en retélécharge ou en revérifie les octets.
    Reste le cas d'une version dépassée entre-temps — ses octets ont quitté `data/raw`,
    mais la copie locale les tient encore. Sans cette reprise, un incident réseau suivi
    d'une révision de la source rendrait définitivement manquante une version que l'index
    dit pourtant connaître.

    Retourne les clés effectivement déposées.
    """
    index = _charger(VERSIONS_FILE)
    deposees: list[str] = []
    for source_id, versions in index.items():
        for version in versions:
            if version.get("payload_archived") or not version.get("payload_key"):
                continue
            nom = version.get("fichier_archive")
            if not nom:
                # Sans copie locale, seuls les octets courants pourraient servir — et eux
                # ne passent que par `enregistrer_version`, qui vérifie l'empreinte.
                continue
            copie = DATA_ARCHIVE / source_id / nom
            if copie.exists() and _deposer(source_id, version["payload_key"], copie):
                version["payload_archived"] = True
                deposees.append(version["payload_key"])
    if deposees:
        _sauver(VERSIONS_FILE, index)
    return deposees


def _redeposable(source_id: str, version: dict) -> bool:
    """Une reprise peut-elle encore déposer les octets de cette version ?

    La question n'est pas « manque-t-il des octets » mais « peut-on encore les fournir »,
    et la réponse suit EXACTEMENT ce que `retenter_depots_en_attente` sait faire — sans
    quoi l'avertissement annonce des reprises que la reprise ne fera jamais.

    Deux chemins, et deux seulement : la version COURANTE repasse par
    `enregistrer_version`, puisque `fetch` en retélécharge ou en revérifie les octets à
    chaque run ; une version DÉPASSÉE n'a plus que sa copie de service. Si cette copie
    n'existe pas, personne ne produira jamais ces octets — `data/archive/` n'est ni
    versionné ni transporté par le cache d'Actions, qui ne porte que `data/raw`.
    """
    if version.get("payload_archived") or not version.get("payload_key"):
        return False
    if version.get("superseded_at") is None:
        return True
    nom = version.get("fichier_archive")
    return bool(nom) and (DATA_ARCHIVE / source_id / nom).exists()


def _millesimes(predicat) -> list[tuple[str, str]]:
    """(source_id, sha256) des versions que `predicat(source_id, version)` retient."""
    return [
        (source_id, version.get("sha256", ""))
        for source_id, versions in _charger(VERSIONS_FILE).items()
        for version in versions
        if predicat(source_id, version)
    ]


def versions_non_deposees() -> list[tuple[str, str]]:
    """Les versions dont les octets manquent ET qu'une reprise peut encore déposer.

    C'est l'INCIDENT ACTIF : cette liste non vide veut dire qu'il reste quelque chose à
    faire, et qu'une reprise le fera.

    Elle a compté trop large jusqu'au 30/08/2026, ne filtrant que sur `payload_key`. Ce
    jour-là elle annonçait 86 reprises dues dont AUCUNE n'était possible : des versions
    dépassées avant l'ouverture du bucket, dont la copie de service avait disparu avec le
    runner. Un compteur qui ne descend jamais à zéro cesse d'être lu — et c'est
    précisément derrière ce bruit que la clé malformée a tenu une journée.

    Trois listes, trois questions qui ne se répondent pas l'une l'autre :
    celle-ci « que reste-t-il à faire », `versions_octets_perdus` « qu'avons-nous perdu
    et ne retrouverons pas », `versions_sans_octets` « que n'avons-nous jamais eu ».
    """
    return _millesimes(_redeposable)


def versions_courantes_sans_octets() -> list[tuple[str, str]]:
    """Les versions VIVANTES dont le stockage durable n'a pas les octets.

    Le critère d'exploitation, et le seul qui réponde « l'archive fonctionne-t-elle » :
    zéro veut dire que tout contenu actuellement détenu par la chaîne est durable. Une
    dette historique, si lourde soit-elle, ne dit rien sur cette question-là.
    """
    return _millesimes(
        lambda sid, v: (not v.get("payload_archived") and v.get("payload_key")
                        and v.get("superseded_at") is None)
    )


def versions_octets_perdus() -> list[tuple[str, str]]:
    """Les versions COLLECTÉES dont les octets n'existent plus nulle part.

    La chaîne les a bel et bien détenues — l'intervalle de connaissance est sûr — mais
    elles ont été dépassées avant que leurs octets n'atteignent le stockage durable, et
    leur copie de service n'a pas survécu au runner. Aucune reprise ne les sauvera : c'est
    un CONSTAT, stable et non bloquant, pas une tâche en attente.

    À distinguer de `versions_sans_octets`, qui liste ce que la chaîne n'a jamais détenu
    (versions reconstituées depuis l'historique du manifeste). Ici nous les avions.

    86 au 30/08/2026, contre 47 le matin du même jour : l'écart est le coût mesuré d'une
    journée où le dépôt échouait derrière un cron vert.
    """
    return _millesimes(
        lambda sid, v: (not v.get("payload_archived") and v.get("payload_key")
                        and v.get("superseded_at") is not None
                        and not _redeposable(sid, v))
    )


def versions_sans_octets() -> list[tuple[str, str]]:
    """(source_id, sha256) des versions dont les octets n'existent NULLE PART, définitivement.

    L'autre moitié de `versions_non_deposees` : celle-ci liste ce qu'une reprise peut encore
    sauver, celle-là ce qu'aucune reprise ne sauvera. Ce sont les versions reconstituées
    après coup depuis l'historique du manifeste — la chaîne les a bel et bien détenues,
    l'intervalle de connaissance est sûr, mais leur contenu a été écrasé dans `data/raw/`
    avant que l'archive n'existe, et `data/raw/` n'est pas versionné.

    Un backtest qui a besoin des octets consulte cette liste : il y voit la limite de ce que
    la chaîne peut rejouer, au lieu de la découvrir en cherchant un fichier absent.
    """
    return [
        (source_id, version.get("sha256", ""))
        for source_id, versions in _charger(VERSIONS_FILE).items()
        for version in versions
        if version.get("origine") == ORIGINE_RECONSTITUEE
    ]


def version_connue_a(source_id: str, instant: str) -> dict | None:
    """Quelle version cette chaîne détenait-elle à `instant` (ISO 8601 UTC) ?

    Le cœur de l'usage : à `forecast_origin = 2026-10-15T08:00:00Z`, retourne la version
    dont l'intervalle `[first_observed_at ; superseded_at[` contient cet instant — et
    non la meilleure version connue aujourd'hui. Retourne None si la chaîne ne détenait
    rien à cette date, ce qui est une réponse, pas une erreur : une variable que nous
    n'observions pas encore ne pouvait pas nourrir une prévision.

    Vérifier `payload_archived` avant d'aller chercher les octets : une version peut être
    connue sans que son contenu soit disponible.

    CE QU'ELLE NE DIT PAS — et la distinction est tout sauf théorique : elle répond
    « quelle version DÉTENIONS-NOUS », jamais « la source figurait-elle au manifeste, et
    y était-elle certifiée, à cet instant ». Les deux se séparent quand une source
    disparaît du manifeste puis revient : l'intervalle reste ouvert (cf. `reconstituer`),
    donc l'interrogation continue de rendre le dernier contenu détenu pendant le trou.
    C'est arrivé le 20/07/2026, où six sources ENTSO-E ont quitté le manifeste le temps
    d'un run avant d'y revenir avec d'autres empreintes. Répondre None aurait été faux
    aussi : nous détenions bien ces octets. Un usage qui exige la certification — et non
    la détention — doit croiser avec le manifeste de la date voulue, que
    `reconstitution.instantanes` sait rendre.
    """
    for version in _charger(VERSIONS_FILE).get(source_id, []):
        debut = version["first_observed_at"]
        fin = version.get("superseded_at")
        if debut <= instant and (fin is None or instant < fin):
            return version
    return None
