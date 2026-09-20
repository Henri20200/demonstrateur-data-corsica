"""L'écriture du manifeste : atomique, et de format figé.

`data/raw/_manifest.json` est le seul fichier de `data/` versionné et le cœur de la
traçabilité. Deux propriétés le tiennent, et aucune des deux ne se voit à la lecture du
code appelant — d'où ces verrous.

ATOMIQUE. Le manifeste est réécrit en entier après chaque source téléchargée : 27 fois
pour un run nominal, 54 quand `data/raw` est vide. Une écriture directe interrompue
laissait un JSON tronqué que personne ne rattrape — `_load_manifest`,
`prepare._verifier_bruts` et `viz.date_collecte` font tous un `json.loads` nu — donc la
chaîne entière s'arrêtait jusqu'à un `git checkout`. C'est la moitié écriture du défaut
que `archive._sauver` a corrigé pour le registre des millésimes le 30/08/2026, et
qu'AUD-09 réclamait pour le manifeste depuis le 05/08.

Le test d'interruption doit couper l'écriture ELLE-MÊME, et c'est le point délicat :
`json.dumps(...)` est un argument, donc il s'achève avant que `write_text` ne commence.
Un test qui ne ferait échouer que la sérialisation passerait au vert sur le code
défectueux — il attesterait une propriété que le défaut ne contredit pas. La fausse
écriture ci-dessous dépose donc une charge TRONQUÉE sur le chemin qu'on lui passe avant
de lever : sur l'ancien code elle mutilait le manifeste, sur le nouveau elle ne salit
qu'un `.tmp`.

FORMAT FIGÉ. Ordre d'insertion et pas de saut de ligne final : ce sont ceux du fichier
versionné. `archive._sauver`, lui, trie ses clés et termine par un saut de ligne — un
helper commun qui harmoniserait les deux réécrirait le manifeste de bout en bout, pour un
contenu identique. Le cron s'interdit ce genre de diff ; le verrou de format est là pour
que l'harmonisation ne se fasse pas par distraction.

Ce que ces verrous NE couvrent PAS : le couple (brut, manifeste), dont la fenêtre reste
ouverte — cf. la docstring de `_save_manifest`.
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

    Le processus est simulé au plus près de ce qui arrive : des octets partent, puis tout
    s'arrête. Sur une écriture directe, ces octets-là atterrissent dans le manifeste et le
    mutilent ; sur une écriture en temporaire, ils n'atteignent jamais le fichier que la
    chaîne relira. L'assertion porte sur les OCTETS et pas sur la lecture JSON : un
    manifeste tronqué pile sur une frontière de ligne resterait peut-être lisible tout en
    ayant perdu des sources, et c'est le pire des cas, pas le meilleur.
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
    """Le temporaire est un moyen, pas une trace : après succès, il a disparu.

    `Path.replace` déplace, il ne copie pas — mais une implémentation qui écrirait le
    temporaire puis le RECOPIERAIT laisserait un résidu dans `data/raw/`, et le prochain
    lecteur du dossier n'a pas à trier entre un manifeste et ses brouillons.
    """
    fetch._save_manifest(MANIFESTE)
    residus = list(manifeste.parent.glob("*.tmp"))
    assert not residus, f"temporaire(s) laissé(s) après une écriture réussie : {residus}"
    assert json.loads(manifeste.read_text(encoding="utf-8")) == MANIFESTE


def test_le_format_du_manifeste_ne_bouge_pas(manifeste):
    """Ordre d'insertion, pas de saut de ligne final, fins de ligne LF.

    Les trois ensemble, parce qu'il suffit d'en perdre une pour réécrire les 39 000 octets
    du fichier versionné sans qu'une seule source ait changé. C'est le risque concret d'un
    helper d'écriture partagé avec `archive._sauver`, qui trie ses clés et ajoute un saut
    de ligne : les deux fichiers sont versionnés, leurs formats ne sont pas les mêmes.
    """
    fetch._save_manifest(MANIFESTE)
    octets = manifeste.read_bytes()

    assert octets == json.dumps(MANIFESTE, indent=2, ensure_ascii=False).encode("utf-8"), (
        "la sérialisation du manifeste a changé — tout écart réécrit le fichier versionné "
        "en entier, pour un contenu identique"
    )
    assert b"\r\n" not in octets, "fins de ligne CRLF : diff intégral face au runner Linux"
    assert not octets.endswith(b"\n"), "saut de ligne final ajouté — diff sur tout le fichier"
    assert list(json.loads(octets)) == list(MANIFESTE), (
        "l'ordre des clés n'est plus celui de sources.yaml (sort_keys ?) — le manifeste "
        "versionné serait réordonné de bout en bout"
    )
