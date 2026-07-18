"""Téléchargement traçable des sources déclarées dans sources.yaml.

Usage :
    fetch-data                     (script installé via pyproject)
    python -m demonstrateur.fetch  (équivalent)

Pour chaque source : téléchargement en streaming, empreinte SHA-256,
content-type et date de collecte enregistrés dans data/raw/_manifest.json.
Un fichier déjà présent avec la même empreinte n'est pas retéléchargé.

Garde-fou (raison d'être du projet : "IA sourcée") : le contenu téléchargé
est VALIDÉ (cf. _valider) avant d'être certifié dans le manifeste. Une page
d'erreur HTML renvoyée en HTTP 200 ne doit jamais recevoir un SHA-256
d'apparence légitime — un tel faux positif est pire que pas d'entrée du tout.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import httpx
import yaml

from .config import DATA_RAW, MANIFEST_FILE, SOURCES_FILE

_HTML_TYPES = {"text/html", "application/xhtml+xml"}


def _load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


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

        if dest.exists() and already.get("sha256"):
            print(f"[=] {source_id} : déjà présent ({dest.name}), ignoré.")
            continue

        print(f"[>] {source_id} : téléchargement…")
        try:
            sha, content_type = _download(meta["url"], dest)
            _valider(dest, meta, content_type)
        except Exception as exc:  # noqa: BLE001 — on continue avec les autres sources
            # Ne jamais laisser un fichier douteux ni une entrée de manifeste
            # trompeuse : on supprime ce qui a pu être écrit.
            dest.unlink(missing_ok=True)
            manifest.pop(source_id, None)
            print(f"[!] {source_id} : ÉCHEC — {exc}")
            failures.append(source_id)
            continue

        manifest[source_id] = {
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

    if failures:
        print(f"\n{len(failures)} source(s) en échec : {', '.join(failures)}")
        print("Vérifier les URL / formats dans sources.yaml (ils peuvent avoir changé).")
        return 1

    print("\nCollecte terminée. Traçabilité : data/raw/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
