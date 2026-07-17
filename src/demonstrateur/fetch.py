"""Téléchargement traçable des sources déclarées dans sources.yaml.

Usage :
    fetch-data                     (script installé via pyproject)
    python -m demonstrateur.fetch  (équivalent)

Pour chaque source : téléchargement en streaming, empreinte SHA-256,
date de collecte enregistrée dans data/raw/_manifest.json.
Un fichier déjà présent avec la même empreinte n'est pas retéléchargé.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date

import httpx
import yaml

from .config import DATA_RAW, MANIFEST_FILE, SOURCES_FILE


def _load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _download(url: str, dest) -> str:
    """Télécharge url vers dest en streaming. Retourne l'empreinte SHA-256."""
    h = hashlib.sha256()
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
                h.update(chunk)
    return h.hexdigest()


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
            sha = _download(meta["url"], dest)
        except Exception as exc:  # noqa: BLE001 — on continue avec les autres sources
            print(f"[!] {source_id} : ÉCHEC — {exc}")
            failures.append(source_id)
            continue

        manifest[source_id] = {
            "url": meta["url"],
            "filename": meta["filename"],
            "producteur": meta.get("producteur", ""),
            "licence": meta.get("licence", ""),
            "sha256": sha,
            "date_collecte": date.today().isoformat(),
            "taille_octets": dest.stat().st_size,
        }
        _save_manifest(manifest)
        print(f"[ok] {source_id} : {dest.name} ({dest.stat().st_size:,} octets)")

    if failures:
        print(f"\n{len(failures)} source(s) en échec : {', '.join(failures)}")
        print("Vérifier les URL dans sources.yaml (elles peuvent avoir changé).")
        return 1

    print("\nCollecte terminée. Traçabilité : data/raw/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
