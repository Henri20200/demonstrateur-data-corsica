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

import gzip
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import yaml

from .config import DATA_RAW, MANIFEST_FILE, SOURCES_FILE

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
        val = os.environ.get(nom, "")
        if not val:
            raise ValueError(
                f"variable d'environnement ${{{nom}}} absente ou vide — "
                "définir le secret avant de lancer fetch-data"
            )
        secrets.append(val)
        return val

    return _VAR_ENV_RE.sub(_rempl, url), secrets


def _masquer(texte: str, secrets: list[str]) -> str:
    """Remplace toute valeur de secret par ••• (les erreurs httpx citent l'url)."""
    for val in secrets:
        texte = texte.replace(val, "•••")
    return texte


def _download(url: str, dest: Path) -> tuple[str, str]:
    """Télécharge url vers dest en streaming.

    Retourne (empreinte SHA-256, content-type renvoyé par le serveur).
    """
    h = hashlib.sha256()
    with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as r:
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
                h.update(chunk)
    return h.hexdigest(), content_type


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
    for ext in ("csv.gz", "geojson", "json", "csv"):
        if nom.endswith("." + ext):
            return ext
    return ""


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
    # format inconnu : on s'en tient au rideau HTML ci-dessus.


def main() -> int:
    cfg = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    sources: dict = cfg.get("sources") or {}
    if not sources:
        print("sources.yaml ne déclare aucune source.")
        return 1

    manifest = _load_manifest()
    failures = []

    for source_id, meta in sources.items():
        dest = DATA_RAW / meta["filename"]
        already = manifest.get(source_id, {})
        glissant = bool(meta.get("glissant"))
        certifie = dest.exists() and bool(already.get("sha256"))

        if certifie and not glissant:
            # Cache valide pour une source figée : pas de re-téléchargement, mais
            # les métadonnées déclaratives suivent toujours sources.yaml.
            modifies = _sync_declaratif(already, meta)
            suffixe = f" — métadonnées resynchronisées ({', '.join(modifies)})" if modifies else ""
            print(f"[=] {source_id} : déjà présent ({dest.name}), empreinte conservée{suffixe}.")
            continue

        verbe = "rafraîchissement (jeu glissant)" if certifie else "téléchargement"
        print(f"[>] {source_id} : {verbe}…")
        # Téléchargement en .part puis remplacement atomique : un échec ne doit
        # jamais détruire une donnée déjà certifiée (cas du rafraîchissement).
        part = dest.with_name(dest.name + ".part")
        secrets: list[str] = []
        try:
            url_reelle, secrets = _expanser_env(meta["url"])
            sha, content_type = _download(url_reelle, part)
            _valider(part, meta, content_type)
        except Exception as exc:  # noqa: BLE001 — on continue avec les autres sources
            part.unlink(missing_ok=True)
            if not certifie:
                # Premier téléchargement raté : aucune entrée trompeuse ne subsiste.
                manifest.pop(source_id, None)
            print(f"[!] {source_id} : ÉCHEC — {_masquer(str(exc), secrets)}")
            failures.append(source_id)
            continue
        part.replace(dest)

        manifest[source_id] = {
            # Toujours le gabarit de sources.yaml, jamais l'url expansée :
            # aucun secret ne doit atterrir dans le manifeste versionné.
            "url": meta["url"],
            "filename": meta["filename"],
            "producteur": meta.get("producteur", ""),
            "licence": meta.get("licence", ""),
            "format": _format(meta),
            "content_type": content_type,
            "sha256": sha,
            "date_collecte": date.today().isoformat(),
            "taille_octets": dest.stat().st_size,
        }
        _save_manifest(manifest)
        print(f"[ok] {source_id} : {dest.name} ({dest.stat().st_size:,} octets, {content_type})")

    # Réécrit le manifeste même sans re-téléchargement : les resynchronisations
    # de métadonnées (licences…) doivent être visibles à chaque run.
    _save_manifest(manifest)

    if failures:
        print(f"\n{len(failures)} source(s) en échec : {', '.join(failures)}")
        print("Vérifier les URL / formats dans sources.yaml (ils peuvent avoir changé).")
        return 1

    print("\nCollecte terminée. Traçabilité : data/raw/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
