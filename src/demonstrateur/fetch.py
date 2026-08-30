"""Téléchargement traçable des sources déclarées dans sources.yaml.

Usage :
    fetch-data                     (script installé via pyproject)
    python -m demonstrateur.fetch  (équivalent)

Pour chaque source : téléchargement en streaming, empreinte SHA-256,
content-type et date de collecte enregistrés dans data/raw/_manifest.json.

Politique de fraîcheur (audit du 19/07/2026 — un succès ne doit jamais
signifier « données anciennes ignorées ») :
 - source `glissant: true` (fenêtre glissante, ex. mix temps réel) :
   re-téléchargée à CHAQUE run — le cache n'est jamais un succès pour un
   jeu périssable ;
 - source figée déjà présente avec empreinte : pas de re-téléchargement,
   mais ses champs déclaratifs (url, licence, producteur, format) sont
   resynchronisés depuis sources.yaml ;
 - le manifeste est réécrit à chaque run, cache valide compris ;
 - téléchargement en `.part` puis remplacement atomique : un
   rafraîchissement qui échoue CONSERVE le fichier et l'entrée de
   manifeste précédents (et le run termine en code 1).

Garde-fou (raison d'être du projet : "IA sourcée") : le contenu téléchargé
est VALIDÉ (cf. _valider) avant d'être certifié dans le manifeste. Une page
d'erreur HTML renvoyée en HTTP 200 ne doit jamais recevoir un SHA-256
d'apparence légitime — un tel faux positif est pire que pas d'entrée du tout.

Secrets : une url de sources.yaml peut référencer une variable d'environnement
avec `${NOM}` (ex. jeton d'API ENTSO-E). L'expansion n'a lieu qu'au moment du
téléchargement : le manifeste et les messages d'erreur ne contiennent JAMAIS la
valeur du secret (seulement le gabarit `${NOM}`). Variable absente ou vide =
échec de la source, sans interrompre les autres.

Le même `${NOM}` vaut pour les **en-têtes HTTP**, déclarés dans `entetes:` — tous
les producteurs ne mettent pas leur jeton dans l'url (Geod'air attend un `apikey:`).
Un en-tête n'est pas moins secret parce qu'il ne se voit pas dans une url : il suit
exactement le même régime, expansion tardive et masquage de la valeur partout. Le
manifeste enregistre le NOM de l'en-tête et le gabarit — savoir qu'une source est
entrée sous authentification fait partie de sa traçabilité, connaître le jeton non.

Sources publiées par jour : certains producteurs (LCSQA) n'exposent aucune url
stable, seulement un fichier par journée. L'url peut alors porter les jetons
`{AAAA}`, `{MM}`, `{JJ}`, résolus par `date_url: hier | aujourdhui`. À l'inverse
d'un secret, la date résolue EST écrite dans le manifeste : savoir quelle journée
a été certifiée est le cœur de la traçabilité. `hier` est le choix sûr pour un
fichier qui se remplit au fil des heures — il garantit 24 h complètes.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import httpx
import yaml

from . import archive
from .config import DATA_RAW, MANIFEST_FILE, SOURCES_FILE
from .provenance import empreinte

_HTML_TYPES = {"text/html", "application/xhtml+xml"}
_VAR_ENV_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
# Accolades SIMPLES, distinctes du `${NOM}` des secrets : les deux syntaxes ne peuvent
# pas se confondre, et un `%` d'url encodée (%2F) n'est jamais interprété au passage.
_JETON_DATE_RE = re.compile(r"\{(AAAA|MM|JJ)\}")
_MAX_REDIRECTIONS = 10
# Journée visée par `date_url`, en jours de recul. « avant-hier » n'est pas un excès de
# prudence : il ALIGNE deux producteurs qui ne publient pas au même rythme. Le fichier
# météo est réécrit au petit matin et sa dernière journée, tronquée, est coupée par
# prepare — sa dernière journée complète est donc J-2 quand le flux d'air offre J-1. À
# « hier », les deux sources ne partagent JAMAIS une journée, et le croisement promis par
# le BRIEF (l'ozone et la chaleur du même jour) est hors d'atteinte. Cf. docs/BRIEF_AIR.md.
_DECALAGE_JOUR = {"avant-hier": 2, "hier": 1, "aujourdhui": 0}


def _load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict) -> None:
    # newline="\n" : le manifeste est le SEUL fichier de data/ versionné. Écrit sous
    # Windows sans cette précaution, il diffère du même manifeste écrit par le runner
    # Linux sur chacune de ses lignes — un diff entier sur un contenu identique.
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
    )


def _expanser_env(url: str) -> tuple[str, list[str]]:
    """Remplace les `${NOM}` d'une url par les variables d'environnement.

    Renvoie (url expansée, valeurs de secrets injectées — à masquer dans tout
    message). Lève ValueError si une variable est absente ou vide : l'erreur ne
    cite que le NOM de la variable, jamais une valeur.
    """
    secrets: list[str] = []

    def _rempl(m: re.Match) -> str:
        nom = m.group(1)
        # .strip() : un secret collé depuis l'UI GitHub peut traîner un retour à la
        # ligne ; on ne peut pas deviner un préfixe parasite (« valeur = … »), mais on
        # retire au moins les blancs de bord.
        val = os.environ.get(nom, "").strip()
        if not val:
            raise ValueError(
                f"variable d'environnement ${{{nom}}} absente ou vide — "
                "définir le secret avant de lancer fetch-data"
            )
        secrets.append(val)
        return val

    return _VAR_ENV_RE.sub(_rempl, url), secrets


def _expanser_entetes(entetes: dict | None) -> tuple[dict[str, str], list[str]]:
    """Expanse les `${NOM}` des valeurs d'en-têtes HTTP, comme pour une url.

    Renvoie (en-têtes prêts pour httpx, valeurs de secrets injectées — à masquer
    dans tout message). Une déclaration mal formée (autre chose qu'un dictionnaire,
    valeur non textuelle) est une erreur de configuration, pas un en-tête à deviner :
    envoyer un jeton tronqué obtiendrait un 401 dont la cause serait introuvable.
    """
    if not entetes:
        return {}, []
    if not isinstance(entetes, dict):
        raise ValueError(
            f"entetes doit être un dictionnaire nom: valeur (reçu {type(entetes).__name__})"
        )
    prets: dict[str, str] = {}
    secrets: list[str] = []
    for nom, valeur in entetes.items():
        if not isinstance(valeur, str):
            raise ValueError(
                f"en-tête {nom!r} : valeur textuelle attendue (reçu {type(valeur).__name__}) — "
                "un jeton se déclare entre guillemets dans sources.yaml"
            )
        valeur_reelle, trouves = _expanser_env(valeur)
        prets[str(nom)] = valeur_reelle
        secrets.extend(trouves)
    return prets, secrets


def _expanser_date(url: str, quand: str | None) -> str:
    """Remplace les jetons `{AAAA}`/`{MM}`/`{JJ}` d'une url par la date demandée.

    `quand` vaut « aujourdhui » (fichier encore en cours de remplissage), « hier »
    (journée close, donc complète) ou « avant-hier » (journée close ET déjà publiée par
    les producteurs plus lents — cf. `_DECALAGE_JOUR`). Les deux déclarations doivent
    être cohérentes : un `date_url` sans jeton dans l'url, ou l'inverse, est une erreur
    de configuration — pas un silence qui téléchargerait la mauvaise chose.
    """
    porte_jetons = bool(_JETON_DATE_RE.search(url))
    if not porte_jetons and not quand:
        return url
    if not porte_jetons:
        raise ValueError(
            f"date_url={quand!r} déclaré mais l'url ne porte aucun jeton "
            "{AAAA}/{MM}/{JJ} — déclaration incohérente"
        )
    if quand is None:
        raise ValueError(
            "l'url porte des jetons {AAAA}/{MM}/{JJ} mais date_url n'est pas déclaré "
            "(attendu : hier | aujourdhui)"
        )
    if quand not in _DECALAGE_JOUR:
        raise ValueError(
            f"date_url={quand!r} inconnu — attendu : {' | '.join(_DECALAGE_JOUR)}"
        )
    jour = date.today() - timedelta(days=_DECALAGE_JOUR[quand])
    valeurs = {"AAAA": f"{jour.year:04d}", "MM": f"{jour.month:02d}", "JJ": f"{jour.day:02d}"}
    return _JETON_DATE_RE.sub(lambda m: valeurs[m.group(1)], url)


def _masquer(texte: str, secrets: list[str]) -> str:
    """Neutralise tout secret dans un message d'erreur (httpx cite l'url complète).

    Deux défenses : (1) on caviarde n'importe quel `securityToken=…` de l'url — robuste
    quelle que soit l'URL-encodage appliqué par httpx (le %20 avait déjoué le simple
    remplacement de valeur) ; (2) on remplace aussi la valeur brute du secret et sa
    forme percent-encodée, pour les jetons portés autrement que par ce paramètre.
    """
    from urllib.parse import quote

    texte = re.sub(r"(?i)(securityToken=)[^&\s'\"]+", r"\1•••", texte)
    for val in secrets:
        for forme in (val, quote(val), quote(val, safe="")):
            texte = texte.replace(forme, "•••")
    return texte


def _download(url: str, dest: Path, entetes: dict[str, str] | None = None) -> str:
    """Télécharge url vers dest en streaming. Retourne le content-type du serveur.

    L'empreinte n'est plus calculée ici : elle l'est par provenance.empreinte APRÈS
    validation, car pour certaines sources (ENTSO-E) elle porte sur une forme canonique
    du fichier et non sur les octets bruts reçus.

    `entetes` porte les en-têtes déjà expansés (cf. _expanser_entetes). Ils ne sont
    jamais journalisés ici : c'est l'appelant qui masque, avec la liste des secrets.

    Les redirections sont suivies à la main, et non par `follow_redirects`, pour une
    raison de sécurité : httpx retire de lui-même l'en-tête `Authorization` quand
    l'origine change, mais pas un en-tête maison comme `apikey:`. Un producteur qui
    renvoie vers un stockage tiers livrerait le jeton à ce tiers — fuite silencieuse,
    aucun message d'erreur. Ici, un en-tête déclaré ne franchit jamais un changement
    d'hôte ; le permalien data.gouv de l'écrêtement EDF, lui, continue de rediriger
    sans rien à perdre, faute d'en-tête.

    **LE SCHÉMA FAIT PARTIE DE L'ORIGINE** (30/08/2026). La comparaison portait sur le
    seul `netloc` : une réponse `302` vers `http://<même hôte>/...` restait « même
    origine », et le jeton repartait EN CLAIR. C'est la fuite silencieuse par excellence
    — personne n'a besoin de détourner le trafic vers un autre hôte, il suffit de faire
    dégrader le sien, et la collecte réussit sans un message. Un hôte compromis y suffit,
    un intermédiaire aussi. La condition est donc double : même hôte, même schéma, et ce
    schéma est `https` — la dernière clause vise le cas où la source elle-même partirait
    en clair, que `tests/test_smoke.py` interdit par ailleurs à la déclaration.
    """
    depart = httpx.URL(url)
    origine = (depart.scheme, depart.netloc)
    courant = url
    with httpx.Client(timeout=180.0, follow_redirects=False) as client:
        for _ in range(_MAX_REDIRECTIONS):
            ici = httpx.URL(courant)
            porte_secret = (bool(entetes) and (ici.scheme, ici.netloc) == origine
                            and ici.scheme == "https")
            with client.stream("GET", courant, headers=entetes if porte_secret else None) as r:
                if r.is_redirect:
                    courant = str(httpx.URL(courant).join(r.headers["location"]))
                    continue
                if r.status_code // 100 == 3:
                    raise ValueError(
                        f"redirection HTTP {r.status_code} sans en-tête Location — "
                        "réponse inexploitable"
                    )
                r.raise_for_status()
                content_type = r.headers.get("content-type", "")
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
                return content_type
    raise ValueError(f"plus de {_MAX_REDIRECTIONS} redirections — boucle probable")


def _sync_declaratif(entry: dict, meta: dict) -> list[str]:
    """Resynchronise les champs déclaratifs d'une entrée de manifeste depuis sources.yaml.

    L'empreinte, la date de collecte et la taille restent celles de la donnée
    réellement téléchargée ; seuls url / licence / producteur / format suivent
    la déclaration courante. Renvoie la liste des champs modifiés.
    """
    modifies = []
    for champ in ("url", "licence", "producteur"):
        val = meta.get(champ, "")
        if entry.get(champ) != val:
            entry[champ] = val
            modifies.append(champ)
    fmt = _format(meta)
    if entry.get("format") != fmt:
        entry["format"] = fmt
        modifies.append("format")
    # Les en-têtes suivent la déclaration comme le reste : une source figée dont le
    # producteur change de nom d'en-tête ne doit pas garder l'ancien au manifeste.
    entetes = _gabarit_entetes(meta)
    if entetes != (entry.get("entetes") or {}):
        if entetes:
            entry["entetes"] = entetes
        else:
            entry.pop("entetes", None)
        modifies.append("entetes")
    return modifies


def _format(meta: dict) -> str:
    """Format déclaré, sinon déduit de l'extension du filename."""
    if meta.get("format"):
        return str(meta["format"]).lower()
    nom = meta["filename"].lower()
    for ext in ("csv.gz", "geojson", "json", "xml", "csv", "parquet"):
        if nom.endswith("." + ext):
            return ext
    return ""


def _gabarit_entetes(meta: dict) -> dict[str, str]:
    """En-têtes TELS QUE DÉCLARÉS dans sources.yaml — `${NOM}` non expansé.

    C'est cette forme, et elle seule, qui a le droit d'entrer dans le manifeste
    versionné : elle dit qu'une source exige une authentification, et par quelle
    variable d'environnement elle passe, sans jamais dire le jeton.
    """
    return {str(nom): str(valeur) for nom, valeur in (meta.get("entetes") or {}).items()}


def _entree_certifiee(already: dict, meta: dict, dest: Path, sha: str,
                      content_type: str = "", date_collecte: str | None = None,
                      recertifie: bool = False) -> dict:
    """Construit/rafraîchit l'entrée de manifeste d'une source certifiée.

    Une re-certification conserve la date de collecte existante (la donnée n'est pas
    re-téléchargée, seule l'empreinte est ré-exprimée) et pose `recertifie_le` = aujourd'hui
    (QUAND l'empreinte a été ré-adoptée, distinct de QUAND la donnée a été recueillie) ; un
    téléchargement pose une date de collecte neuve et efface toute `recertifie_le`. Enregistre
    `empreinte_ignore_xml` quand l'empreinte est canonique : le manifeste documente ainsi
    lui-même que son SHA-256 ne porte pas sur les octets bruts.
    """
    entree = {
        "url": meta["url"],
        "filename": meta["filename"],
        "producteur": meta.get("producteur", ""),
        "licence": meta.get("licence", ""),
        "format": _format(meta),
        "content_type": content_type or already.get("content_type", ""),
        "sha256": sha,
    }
    # En-têtes : le GABARIT, jamais la valeur expansée — meta porte la déclaration de
    # sources.yaml, l'expansion vit dans une variable locale de main() qui meurt avec elle.
    entetes = _gabarit_entetes(meta)
    if entetes:
        entree["entetes"] = entetes
    ignore = meta.get("empreinte_ignore_xml")
    if ignore:
        entree["empreinte_ignore_xml"] = list(ignore)
    entree["date_collecte"] = (
        date_collecte or already.get("date_collecte") or date.today().isoformat()
    )
    if recertifie:
        entree["recertifie_le"] = date.today().isoformat()
    entree["taille_octets"] = dest.stat().st_size
    return entree


def _racine_xml(dest: Path) -> str:
    """Nom local (sans namespace) de l'élément racine d'un XML."""
    # iterparse 'start' : lit juste la balise ouvrante, sans charger tout l'arbre.
    _, elem = next(ET.iterparse(dest, events=("start",)))
    return elem.tag.split("}")[-1]


def _entete_csv(dest: Path, gz: bool) -> str:
    opener = gzip.open if gz else open
    with opener(dest, "rt", encoding="utf-8-sig", newline="") as f:  # -sig retire le BOM
        return f.readline().strip()


def _valider(dest: Path, meta: dict, content_type: str) -> None:
    """Vérifie que le fichier téléchargé EST bien la donnée attendue.

    Lève ValueError sinon. Objectif : qu'une page d'erreur (HTML, portail SPA)
    ne puisse jamais être certifiée comme donnée dans le manifeste.
    """
    # 1) Rideau universel : ici, une page HTML n'est jamais une donnée.
    ct = content_type.split(";")[0].strip().lower()
    if ct in _HTML_TYPES:
        raise ValueError(f"réponse HTML (content-type={content_type!r}) — donnée attendue")

    fmt = _format(meta)

    # 2) Contrôle par format : l'en-tête doit être tabulaire et contenir les
    #    colonnes attendues (CSV), ou le JSON doit porter sa clé racine.
    if fmt in {"csv", "csv.gz"}:
        entete = _entete_csv(dest, gz=(fmt == "csv.gz"))
        delim = meta.get("delimiter", ",")
        # .strip('"') : les producteurs qui citent leurs en-têtes ("Polluant";"valeur",
        # cas du flux E2) ne doivent pas obliger à déclarer les guillemets dans sources.yaml.
        cols = [c.strip().strip('"') for c in entete.split(delim)]
        if len(cols) < 2:
            raise ValueError(
                f"en-tête non tabulaire avec le délimiteur {delim!r} : {entete[:80]!r}"
            )
        manquantes = [c for c in meta.get("colonnes_attendues", []) if c not in cols]
        if manquantes:
            raise ValueError(f"colonnes attendues absentes {manquantes} — trouvé {cols[:8]}…")
    elif fmt in {"geojson", "json"}:
        try:
            obj = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON invalide : {exc}") from exc
        cle = meta.get("cle_attendue")
        if cle and (not isinstance(obj, dict) or cle not in obj):
            raise ValueError(f"clé racine {cle!r} absente du JSON")
    elif fmt == "parquet":
        # Un fichier Parquet s'ouvre ET se referme par le nombre magique « PAR1 » : le
        # contrôle coûte huit octets et attrape aussi bien une page d'erreur qu'un
        # téléchargement tronqué, cas qu'un simple contrôle de taille laisserait passer.
        if dest.stat().st_size < 8:
            raise ValueError(f"fichier Parquet trop court ({dest.stat().st_size} octets)")
        with open(dest, "rb") as f:
            tete = f.read(4)
            f.seek(-4, 2)
            pied = f.read(4)
        if tete != b"PAR1" or pied != b"PAR1":
            raise ValueError(
                f"nombre magique Parquet absent (début {tete!r}, fin {pied!r}) — "
                "réponse d'erreur ou fichier tronqué"
            )
        attendues = meta.get("colonnes_attendues", [])
        if attendues:
            # DuckDB lit le seul schéma, sans charger les données : il est déjà une
            # dépendance du projet, autant s'en servir plutôt que décoder le pied Thrift.
            import duckdb

            # `read_parquet(...)` explicite, et non `FROM '...'` : la validation porte sur
            # le fichier de travail `.parquet.part`, dont DuckDB ne reconnaîtrait pas
            # l'extension pour choisir son lecteur.
            cols = [
                r[0]
                for r in duckdb.connect()
                .execute(f"DESCRIBE SELECT * FROM read_parquet('{dest.as_posix()}')")
                .fetchall()
            ]
            manquantes = [c for c in attendues if c not in cols]
            if manquantes:
                raise ValueError(
                    f"colonnes attendues absentes du Parquet {manquantes} — trouvé {cols[:8]}…"
                )
    elif fmt == "xml":
        # Piège ENTSO-E : une requête en erreur (jeton, pas de données, période)
        # renvoie HTTP 200 + un `Acknowledgement_MarketDocument` — jamais l'empreinter
        # comme donnée. On exige donc la racine attendue (ex. GL_MarketDocument).
        try:
            racine = _racine_xml(dest)
        except ET.ParseError as exc:
            raise ValueError(f"XML invalide : {exc}") from exc
        attendue = meta.get("racine_attendue")
        if attendue and racine != attendue:
            raise ValueError(
                f"racine XML {racine!r} (attendu {attendue!r}) — réponse d'erreur "
                "probable (Acknowledgement), pas la donnée"
            )
    # format inconnu : on s'en tient au rideau HTML ci-dessus.


def _suffixe_millesime(entree: dict | None) -> str:
    """Ce qu'un run a retenu d'une version, pour la ligne de log.

    Dire « archivé » quand seul l'index a été écrit serait un mensonge de journal : les
    octets peuvent n'être nulle part. L'état se lit donc en toutes lettres.
    """
    if not entree:
        return ""
    etat = "déposé" if entree["payload_archived"] else "octets NON déposés, à reprendre"
    return f" — millésime {entree['sha256'][:8]} conservé ({etat})"


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(
        prog="fetch-data",
        description="Télécharge les sources de sources.yaml et certifie leur empreinte.",
    )
    parseur.add_argument(
        "--recertifier",
        nargs="*",
        metavar="SOURCE_ID",
        default=None,
        help="Ne télécharge RIEN : re-VALIDE puis recalcule l'empreinte depuis le fichier "
        "LOCAL et l'adopte dans le manifeste (avec la date de re-certification). Sans argument "
        "= toutes les sources présentes ; sinon, seulement les SOURCE_ID listées. À utiliser "
        "après une révision volontaire de la donnée ou une migration d'empreinte.",
    )
    args = parseur.parse_args(argv)
    recertifier = args.recertifier is not None
    cibles = set(args.recertifier) if args.recertifier else None  # None = toutes les présentes

    cfg = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    sources: dict = cfg.get("sources") or {}
    if not sources:
        print("sources.yaml ne déclare aucune source.")
        return 1
    if cibles:
        inconnues = cibles - set(sources)
        if inconnues:
            print(f"Source(s) inconnue(s) à re-certifier : {', '.join(sorted(inconnues))}")
            return 1

    manifest = _load_manifest()
    failures = []

    for source_id, meta in sources.items():
        # Date résolue AVANT tout le reste : contrairement à un secret, elle fait partie
        # de l'IDENTITÉ de la donnée et doit donc figurer dans le manifeste. Une
        # déclaration incohérente échoue ici, sans toucher aux autres sources.
        try:
            meta = {**meta, "url": _expanser_date(meta["url"], meta.get("date_url"))}
        except ValueError as exc:
            print(f"[!] {source_id} : ÉCHEC — {exc}")
            failures.append(source_id)
            continue
        dest = DATA_RAW / meta["filename"]
        already = manifest.get(source_id, {})
        glissant = bool(meta.get("glissant"))
        certifie = dest.exists() and bool(already.get("sha256"))

        # --- Re-certification (hors-ligne) : le fichier LOCAL fait foi ---------------
        if recertifier:
            if cibles is not None and source_id not in cibles:
                continue  # ciblage : source non demandée, laissée telle quelle
            if not dest.exists():
                print(f"[!] {source_id} : absent de data/raw — rien à re-certifier.")
                failures.append(source_id)
                continue
            try:
                # Re-VALIDER avant de certifier : un fichier local corrompu (mauvais en-tête,
                # page d'erreur, XML cassé) ne doit jamais recevoir une empreinte légitime.
                _valider(dest, meta, already.get("content_type", ""))
                sha = empreinte(dest, meta)
            except Exception as exc:  # noqa: BLE001
                print(f"[!] {source_id} : NON re-certifié — {exc}")
                failures.append(source_id)
                continue
            ancienne = already.get("sha256")
            manifest[source_id] = _entree_certifiee(already, meta, dest, sha, recertifie=True)
            etat = "inchangée" if sha == ancienne else "MISE À JOUR"
            print(f"[±] {source_id} : re-certifié (empreinte {etat}) "
                  f"le {manifest[source_id]['recertifie_le']}.")
            continue

        # --- Source figée certifiée : on VÉRIFIE (AUD-01), plus de confiance aveugle --
        if certifie and not glissant:
            # Une empreinte n'est probante que RE-VÉRIFIÉE : la seule présence du fichier
            # ne suffit plus. On recalcule (forme canonique si déclarée) et on compare —
            # une donnée qui aurait dérivé sous le manifeste est ainsi attrapée, pas subie.
            try:
                obtenue = empreinte(dest, meta)
            except Exception as exc:  # noqa: BLE001
                print(f"[!] {source_id} : ÉCHEC vérification — fichier illisible : {exc}")
                failures.append(source_id)
                continue
            if obtenue != already["sha256"]:
                print(
                    f"[!] {source_id} : ÉCHEC — l'empreinte du fichier local ne correspond "
                    f"plus au manifeste (attendu {already['sha256'][:12]}…, obtenu "
                    f"{obtenue[:12]}…). Restaurer la donnée certifiée (supprimer "
                    f"data/raw/{dest.name} puis relancer) ou, si le changement est voulu, "
                    "fetch-data --recertifier."
                )
                failures.append(source_id)
                continue
            modifies = _sync_declaratif(already, meta)
            suffixe = f" — métadonnées resynchronisées ({', '.join(modifies)})" if modifies else ""
            # Vérifiée sans être re-téléchargée : rien de neuf à conserver, mais la
            # chaîne a bien REGARDÉ, et `enregistrer_version` note ce contrôle — sans cette
            # trace, un trou dans les millésimes serait ambigu (source inchangée, ou source
            # non consultée ?). Elle fait deux autres choses ici, et c'est voulu : elle
            # dépose la COPIE INITIALE d'une source figée, dont l'unique exemplaire était
            # jusqu'ici data/raw — soit, en CI, un cache d'Actions ; et elle retente le
            # dépôt d'une version que le stockage n'aurait pas reçue. Aucune deuxième
            # entrée à craindre : l'empreinte vient d'être vérifiée identique.
            millesime = archive.enregistrer_version(source_id, meta, dest, obtenue)
            print(f"[=] {source_id} : présent et vérifié ({dest.name}){suffixe}"
                  f"{_suffixe_millesime(millesime)}.")
            continue

        # --- Téléchargement (source neuve, ou rafraîchissement d'un jeu glissant) ----
        verbe = "rafraîchissement (jeu glissant)" if certifie else "téléchargement"
        print(f"[>] {source_id} : {verbe}…")
        # Téléchargement en .part puis remplacement atomique : un échec ne doit jamais
        # détruire une donnée déjà certifiée (cas du rafraîchissement).
        part = dest.with_name(dest.name + ".part")
        secrets: list[str] = []
        try:
            url_reelle, secrets = _expanser_env(meta["url"])
            entetes_reels, secrets_entetes = _expanser_entetes(meta.get("entetes"))
            secrets += secrets_entetes
            content_type = _download(url_reelle, part, entetes_reels)
            _valider(part, meta, content_type)
            sha = empreinte(part, meta)  # canonique si empreinte_ignore_xml, sinon octets bruts
        except Exception as exc:  # noqa: BLE001 — on continue avec les autres sources
            part.unlink(missing_ok=True)
            if not certifie:
                # Premier téléchargement raté : aucune entrée trompeuse ne subsiste.
                manifest.pop(source_id, None)
            print(f"[!] {source_id} : ÉCHEC — {_masquer(str(exc), secrets)}")
            failures.append(source_id)
            continue
        part.replace(dest)

        # _entree_certifiee ne lit que `meta` — le gabarit ${...}, url comme en-têtes —
        # jamais `url_reelle` ni `entetes_reels` : aucun secret n'atterrit dans le
        # manifeste versionné. Les deux formes expansées meurent avec cette itération.
        manifest[source_id] = _entree_certifiee(
            already, meta, dest, sha,
            content_type=content_type, date_collecte=date.today().isoformat(),
        )
        _save_manifest(manifest)
        # Millésime : le fichier qu'on vient de remplacer n'existe plus, mais celui qu'on
        # vient d'écrire, lui, peut encore être conservé — et daté de l'instant où NOTRE
        # chaîne l'a observé pour la première fois. N'écrit rien si l'empreinte est déjà
        # connue : le cron passe toutes les 6 h, archiver à chaque passage ferait quatre
        # copies identiques par jour. Purement additif — `dest` est intouché.
        millesime = archive.enregistrer_version(source_id, meta, dest, sha)
        print(f"[ok] {source_id} : {dest.name} ({dest.stat().st_size:,} octets, "
              f"{content_type}){_suffixe_millesime(millesime)}")

    # Réécrit le manifeste même sans téléchargement : resynchronisations de métadonnées
    # (licences…) et re-certifications doivent être visibles à chaque run.
    _save_manifest(manifest)

    # Dernier filet, et le seul qui couvre une version DÉPASSÉE dont les octets ne sont
    # jamais partis : sa copie locale existe encore, le stockage est peut-être revenu.
    # C'est l'unique occasion de les réunir avant que la copie disparaisse à son tour.
    archive.retenter_depots_en_attente()

    # Le disjoncteur de volume n'interrompt pas la collecte — les versions restent indexées,
    # et un intervalle de connaissance ne se rattrape pas quand des octets, eux, se
    # redéposent — mais il ROUGIT le run : un changement de régime de volume ne doit pas
    # s'installer derrière un cron vert, où personne ne le verrait avant la facture.
    suspension = archive.seuil_franchi()
    if suspension:
        print(f"[!] DÉPÔT D'ARCHIVE SUSPENDU — {suspension}")

    # Même arbitrage, autre cause — et celle-ci ne se résout pas toute seule. Un stockage
    # injoignable revient ; une clé malformée reste malformée. Tant que ce cas se rendait
    # comme une panne passagère, il tenait derrière un cron vert : le 30/08/2026, 71 dépôts
    # tentés, 0 réussi, run en succès, et les versions dépassées perdant leurs octets
    # pendant ce temps (47 le matin, 86 le soir).
    mauvaise_conf = archive.configuration_refusee()
    if mauvaise_conf:
        print(f"[!] DÉPÔT D'ARCHIVE MAL CONFIGURÉ — {mauvaise_conf}")
        print("[!] Ce n'est PAS une panne : aucun run suivant ne le corrigera de lui-même. "
              "La collecte, elle, est allée à son terme et l'index est à jour.")

    if failures:
        print(f"\n{len(failures)} source(s) en échec : {', '.join(failures)}")
        if not recertifier:
            print("Vérifier les URL / formats dans sources.yaml (ils peuvent avoir changé), "
                  "ou une empreinte divergente signalée ci-dessus.")
        return 1
    if suspension or mauvaise_conf:
        return 1

    action = "Re-certification" if recertifier else "Collecte"
    print(f"\n{action} terminée. Traçabilité : data/raw/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
