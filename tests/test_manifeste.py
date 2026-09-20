"""Vérifie la conservation du manifeste après une interruption et son format exact.

`data/raw/_manifest.json` est versionné et relie les fichiers collectés à leurs sources.
Une écriture directe interrompue peut le tronquer et bloquer les traitements suivants.
Le test interrompt l'écriture après avoir déposé une partie du contenu. Une erreur dans
`json.dumps` ne suffirait pas : la sérialisation termine avant l'appel à `write_text`,
donc cette erreur préserverait déjà le manifeste avec l'ancienne implémentation.

Les autres tests vérifient le remplacement du temporaire après succès et le format
conservé : ordre d'insertion, fins de ligne LF, aucun saut de ligne final. Ce format
diffère de celui du registre d'archive, dont les clés sont triées et qui termine par LF.

La cohérence entre le brut et le manifeste relève d'un problème distinct, décrit dans
la docstring de `_save_manifest`.
"""

import json
import pathlib

import pytest

from demonstrateur import fetch

MANIFESTE = {
    "edf_mix_temps_reel": {
        "filename": "mix_temps_reel.csv",
        "sha256": "a" * 64,
        "producteur": "EDF — Open Data Groupe EDF",
        "licence": "Licence Ouverte 2.0",
        "date_collecte": "2026-09-20",
    },
    "aee_o3_ajaccio": {
        "filename": "aee_o3_ajaccio.parquet",
        "sha256": "b" * 64,
        "producteur": "Agence européenne pour l'environnement",
        "licence": "Licence Ouverte 2.0",
        "date_collecte": "2026-09-20",
    },
}


@pytest.fixture
def manifeste(tmp_path, monkeypatch) -> pathlib.Path:
    """Un manifeste valide, hors du dépôt, sur lequel `fetch` écrira."""
    chemin = tmp_path / "_manifest.json"
    chemin.write_text(json.dumps({"ancien": {"sha256": "c" * 64}}, indent=2),
                      encoding="utf-8", newline="\n")
    monkeypatch.setattr(fetch, "MANIFEST_FILE", chemin)
    return chemin


def test_une_ecriture_interrompue_laisse_le_manifeste_intact(manifeste, monkeypatch):
    """Coupée en pleine écriture, l'opération ne touche pas au manifeste en place.

    La fausse écriture dépose une partie du contenu, puis lève une exception. La
    comparaison des octets garantit la conservation exacte du manifeste précédent.
    """
    avant = manifeste.read_bytes()
    ecrire_reel = pathlib.Path.write_text

    def _ecriture_coupee(self, contenu, *args, **kwargs):
        ecrire_reel(self, contenu[: len(contenu) // 2], *args, **kwargs)
        raise OSError("écriture interrompue (simulée)")

    monkeypatch.setattr(pathlib.Path, "write_text", _ecriture_coupee)
    with pytest.raises(OSError):
        fetch._save_manifest(MANIFESTE)

    assert manifeste.read_bytes() == avant, (
        "le manifeste en place a été modifié par une écriture interrompue — la chaîne "
        "entière (fetch, prepare, viz) le relit par un json.loads nu"
    )


def test_une_ecriture_reussie_ne_laisse_aucun_temporaire(manifeste):
    """Après succès, le contenu est enregistré et le temporaire a disparu."""
    fetch._save_manifest(MANIFESTE)
    residus = list(manifeste.parent.glob("*.tmp"))
    assert not residus, f"temporaire(s) laissé(s) après une écriture réussie : {residus}"
    assert json.loads(manifeste.read_text(encoding="utf-8")) == MANIFESTE


def test_le_format_du_manifeste_ne_bouge_pas(manifeste):
    """Ordre d'insertion, pas de saut de ligne final, fins de ligne LF.

    Une fonction partagée avec `archive._sauver` doit préserver ces choix : le registre
    d'archive trie ses clés et ajoute un saut de ligne final, contrairement au manifeste.
    """
    fetch._save_manifest(MANIFESTE)
    octets = manifeste.read_bytes()

    assert octets == json.dumps(MANIFESTE, indent=2, ensure_ascii=False).encode("utf-8"), (
        "le format du manifeste a changé"
    )
    assert b"\r\n" not in octets, "fins de ligne CRLF : diff intégral face au runner Linux"
    assert not octets.endswith(b"\n"), "saut de ligne final ajouté au manifeste"
    assert list(json.loads(octets)) == list(MANIFESTE), (
        "l'ordre d'insertion des clés du manifeste a changé"
    )
