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
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import httpx
import yaml

from .config import DATA_RAW, MANIFEST_FILE, SOURCES_FILE
from .provenance import empreinte

_HTML_TYPES = {"text/html", "application/xhtml+xml"}
_VAR_ENV_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


def _load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
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


def _download(url: str, dest: Path) -> str:
    """Télécharge url vers dest en streaming. Retourne le content-type du serveur.

    L'empreinte n'est plus calculée ici : elle l'est par provenance.empreinte APRÈS
    validation, car pour certaines sources (ENTSO-E) elle porte sur une forme canonique
    du fichier et non sur les octets bruts reçus.
    """
    with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as r:
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return content_type


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
    return modifies


def _format(meta: dict) -> str:
    """Format déclaré, sinon déduit de l'extension du filename."""
    if meta.get("format"):
        return str(meta["format"]).lower()
    nom = meta["filename"].lower()
    for ext in ("csv.gz", "geojson", "json", "xml", "csv"):
        if nom.endswith("." + ext):
            return ext
    return ""


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
        cols = [c.strip() for c in entete.split(delim)]
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
            print(f"[=] {source_id} : présent et vérifié ({dest.name}){suffixe}.")
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
            content_type = _download(url_reelle, part)
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

        # _entree_certifiee n'utilise que meta["url"] (le gabarit ${...}), jamais l'url
        # expansée : aucun secret n'atterrit dans le manifeste versionné.
        manifest[source_id] = _entree_certifiee(
            already, meta, dest, sha,
            content_type=content_type, date_collecte=date.today().isoformat(),
        )
        _save_manifest(manifest)
        print(f"[ok] {source_id} : {dest.name} ({dest.stat().st_size:,} octets, {content_type})")

    # Réécrit le manifeste même sans téléchargement : resynchronisations de métadonnées
    # (licences…) et re-certifications doivent être visibles à chaque run.
    _save_manifest(manifest)

    if failures:
        print(f"\n{len(failures)} source(s) en échec : {', '.join(failures)}")
        if not recertifier:
            print("Vérifier les URL / formats dans sources.yaml (ils peuvent avoir changé), "
                  "ou une empreinte divergente signalée ci-dessus.")
        return 1

    action = "Re-certification" if recertifier else "Collecte"
    print(f"\n{action} terminée. Traçabilité : data/raw/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
