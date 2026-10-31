"""Une source figée absente de data/raw se RESTAURE, elle ne se réadopte pas.

Cache d'Actions évincé, poste neuf : l'entrée du manifeste est là, le fichier non. Jusqu'au
31/10/2026, `fetch` la traitait en source neuve et adoptait le contenu du jour sans le
comparer — quatre années ENTSO-E le 22/07/2026, la tranche météo 2020-2024 le 04/08. Et un
téléchargement raté retirait l'entrée, ce qui ouvrait la même porte au run suivant.

Changer de contenu reste possible, mais par DÉCISION : `contenu_adopte` dans sources.yaml
nomme le seul contenu admis, et l'index des millésimes en garde la trace.
"""

import gzip
import json

import pytest
import yaml

from demonstrateur import archive, depot, fetch
from demonstrateur.provenance import empreinte

CONTENU = b"NUM_POSTE;NOM_USUEL;AAAAMMJJHH;T;QT\n" + b"20004002;AJACCIO;2024123123;9.1;1\n" * 500
REVISE = CONTENU.replace(b";9.1;1\n", b";9.2;1\n", 1)
SEPTEMBRE, OCTOBRE = 1788242673, 1790841119
TRANCHE = {
    "url": "https://exemple.test/tranche.csv.gz",
    "filename": "tranche.csv.gz",
    "format": "csv.gz",
    "delimiter": ";",
    "empreinte_decompressee": True,
}


def _gz(contenu: bytes, instant: int) -> bytes:
    return gzip.compress(contenu, mtime=instant)


@pytest.fixture
def chaine(tmp_path, monkeypatch):
    """Une tranche certifiée, un producteur réglable, et sources.yaml modifiable.

    `certifier(octets, regle, garder=False)` pose l'entrée de manifeste sous la règle
    voulue, puis retire le fichier sauf `garder` ; `servi["octets"]` est ce que le
    producteur rend (absent : injoignable) ; `declarer(**cles)` réécrit la déclaration.
    """
    monkeypatch.setattr(archive, "_depot_durable", lambda: None)
    monkeypatch.setattr(fetch, "DATA_RAW", tmp_path)
    manifeste = tmp_path / "_manifest.json"
    monkeypatch.setattr(fetch, "MANIFEST_FILE", manifeste)
    sources = tmp_path / "sources.yaml"
    monkeypatch.setattr(fetch, "SOURCES_FILE", sources)
    brut = tmp_path / TRANCHE["filename"]
    servi: dict = {}

    def declarer(**cles):
        sources.write_text(
            yaml.safe_dump({"sources": {"tranche": {**TRANCHE, **cles}}}), encoding="utf-8"
        )

    declarer()

    def telecharger(_url, dest, _entetes=None):
        if "octets" not in servi:
            raise ConnectionError("producteur injoignable")
        dest.write_bytes(servi["octets"])
        return "application/gzip"

    monkeypatch.setattr(fetch, "_download", telecharger)

    def certifier(octets: bytes, regle: dict, garder: bool = False) -> None:
        brut.write_bytes(octets)
        meta = {**{k: v for k, v in TRANCHE.items() if k != "empreinte_decompressee"}, **regle}
        entree = fetch._entree_certifiee(
            {}, meta, brut, empreinte(brut, meta),
            content_type="application/gzip", date_collecte="2026-08-04",
        )
        manifeste.write_text(
            json.dumps({"tranche": entree}, indent=2, ensure_ascii=False),
            encoding="utf-8", newline="\n",
        )
        if not garder:
            brut.unlink()

    def entree() -> dict:
        return json.loads(manifeste.read_text(encoding="utf-8"))["tranche"]

    return certifier, servi, brut, manifeste, entree, declarer


def test_le_contenu_certifie_se_restaure(chaine):
    """Le producteur sert le même contenu, recompressé : le fichier revient, l'empreinte
    reste."""
    certifier, servi, brut, _, entree, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    attendue = entree()["sha256"]
    servi["octets"] = _gz(CONTENU, OCTOBRE)

    assert fetch.main([]) == 0
    assert brut.read_bytes() == servi["octets"]
    assert entree()["sha256"] == attendue


@pytest.mark.parametrize(
    "regle, octets_servis",
    [
        # Le cas de la tranche météo d'août à septembre 2026 : le contenu a changé.
        ({"empreinte_decompressee": True}, _gz(REVISE, OCTOBRE)),
        # Même contenu, mais certifié sur ses octets bruts : l'ancienne empreinte ne
        # couvre pas la recompression, et la règle de sources.yaml n'y change rien.
        ({}, _gz(CONTENU, OCTOBRE)),
    ],
    ids=["contenu_revise", "regle_changee"],
)
def test_un_autre_contenu_n_est_pas_adopte(chaine, regle, octets_servis):
    certifier, servi, brut, manifeste, _, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), regle)
    avant = manifeste.read_bytes()
    servi["octets"] = octets_servis

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant, "l'entrée certifiée doit rester telle quelle"
    assert not brut.exists(), "un contenu refusé ne doit pas être posé dans data/raw"
    assert not brut.with_name(brut.name + ".part").exists()


def test_un_telechargement_rate_ne_retire_pas_l_entree(chaine):
    """Le chemin du 20/07/2026 : entrée retirée sur un échec, contenu adopté au run
    suivant. L'entrée reste, et le run suivant refuse encore le contenu révisé."""
    certifier, servi, brut, manifeste, _, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    avant = manifeste.read_bytes()

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant

    servi["octets"] = _gz(REVISE, OCTOBRE)
    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant
    assert not brut.exists()


def _versions() -> list[dict]:
    return json.loads(archive.VERSIONS_FILE.read_text(encoding="utf-8"))["tranche"]


def test_le_contenu_adopte_remplace_le_certifie_et_fait_un_millesime(chaine, monkeypatch):
    """La voie de la décision : le contenu déclaré, servi par le producteur, prend la
    place du certifié — et l'index dit désormais détenir celui-là, plus l'ancien."""
    certifier, servi, brut, _, entree, declarer = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True}, garder=True)
    assert fetch.main([]) == 0, "premier passage : copie initiale indexée"
    ancien = entree()["sha256"]

    servi["octets"] = _gz(REVISE, OCTOBRE)
    adopte = empreinte(_ecrire(brut.with_name("revise.csv.gz"), servi["octets"]), TRANCHE)
    declarer(contenu_adopte=adopte)
    assert fetch.main([]) == 0
    assert brut.read_bytes() == servi["octets"]
    assert entree()["sha256"] == adopte
    assert entree()["date_collecte"] != "2026-08-04", "un contenu adopté est collecté ce jour"
    versions = _versions()
    assert [v["sha256"] for v in versions] == [ancien, adopte]
    assert versions[0]["superseded_at"] == versions[1]["first_observed_at"]
    assert versions[1]["superseded_at"] is None

    # Adoption faite : la déclaration ne fait plus rien, la source redevient figée.
    def _interdit(*_args, **_kwargs):
        raise AssertionError("une adoption faite ne se retélécharge pas")

    monkeypatch.setattr(fetch, "_download", _interdit)
    assert fetch.main([]) == 0
    assert len(_versions()) == 2


def test_un_contenu_autre_que_celui_adopte_est_refuse(chaine):
    """Le producteur a encore révisé depuis la mesure : on n'adopte pas un contenu que
    personne n'a regardé. Le certifié reste en place, fichier compris."""
    certifier, servi, brut, manifeste, _, declarer = chaine
    certifie = _gz(CONTENU, SEPTEMBRE)
    certifier(certifie, {"empreinte_decompressee": True}, garder=True)
    avant = manifeste.read_bytes()
    adopte = empreinte(_ecrire(brut.with_name("revise.csv.gz"), _gz(REVISE, OCTOBRE)), TRANCHE)
    declarer(contenu_adopte=adopte)
    servi["octets"] = _gz(REVISE + b"20004002;AJACCIO;2024123123;9.3;1\n", OCTOBRE)

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant
    assert brut.read_bytes() == certifie
    assert not brut.with_name(brut.name + ".part").exists()


def _ecrire(chemin, octets):
    chemin.write_bytes(octets)
    return chemin


# --- L'archive d'abord : elle détient les octets certifiés eux-mêmes (31/10/2026) -----

CLE = "archive/tranche/2026/08/20260829T123345Z_x.csv.gz"


class DepotSimule:
    """Un stockage qui rend `objets[cle]`, ou lève `refus` ; il note chaque lecture."""

    def __init__(self, objets: dict, refus: Exception | None = None):
        self.objets, self.refus, self.lectures = objets, refus, []

    def recuperer(self, cle, dest, *, plage=None):
        self.lectures.append((cle, plage))
        if self.refus:
            raise self.refus
        octets = self.objets[cle]
        dest.write_bytes(octets[:1] if plage else octets)

    def deposer(self, cle, chemin):
        self.objets[cle] = chemin.read_bytes()
        return cle


def _archiver(sha: str, octets: bytes, monkeypatch, refus=None) -> DepotSimule:
    """Indexe une version déposée de `tranche` et branche un stockage qui la détient."""
    archive.VERSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    archive.VERSIONS_FILE.write_text(json.dumps({"tranche": [{
        "sha256": sha, "payload_key": CLE, "payload_archived": True,
        "first_observed_at": "2026-08-29T12:33:45Z", "superseded_at": None,
        "taille_octets": len(octets),
    }]}), encoding="utf-8")
    simule = DepotSimule({CLE: octets}, refus)
    monkeypatch.setattr(archive, "_depot_durable", lambda: simule)
    return simule


def _producteur_interdit(monkeypatch):
    def _interdit(*_args, **_kwargs):
        raise AssertionError("l'archive suffisait : le producteur n'avait pas à servir")

    monkeypatch.setattr(fetch, "_download", _interdit)


def test_l_archive_restaure_les_octets_certifies(chaine, monkeypatch):
    """Le producteur ne sert plus ce contenu ; l'archive le rend à l'octet. L'entrée du
    manifeste reste vraie telle quelle : mêmes octets, même date de collecte."""
    certifier, _, brut, manifeste, entree, _ = chaine
    certifies = _gz(CONTENU, SEPTEMBRE)
    certifier(certifies, {"empreinte_decompressee": True})
    avant = manifeste.read_bytes()
    simule = _archiver(entree()["sha256"], certifies, monkeypatch)
    _producteur_interdit(monkeypatch)

    assert fetch.main([]) == 0
    assert brut.read_bytes() == certifies
    assert manifeste.read_bytes() == avant
    assert (CLE, None) in simule.lectures


def test_l_archive_sous_une_autre_empreinte_est_verifiee_sous_celle_de_l_entree(
    chaine, monkeypatch
):
    """L'index peut tenir les mêmes octets sous l'ANCIENNE règle (empreinte brute),
    comme la tranche météo le 31/10/2026 : le candidat est essayé et vérifié quand même."""
    certifier, _, brut, _, _, _ = chaine
    certifies = _gz(CONTENU, SEPTEMBRE)
    certifier(certifies, {"empreinte_decompressee": True})
    _archiver(empreinte(_ecrire(brut.with_name("brut.gz"), certifies), {}), certifies,
              monkeypatch)
    _producteur_interdit(monkeypatch)

    assert fetch.main([]) == 0
    assert brut.read_bytes() == certifies


def test_une_copie_d_archive_non_conforme_n_est_pas_posee(chaine, monkeypatch):
    """L'objet archivé ne porte pas le contenu certifié : il n'est pas posé, et le
    producteur, qui ne le sert pas non plus, est refusé à son tour."""
    certifier, servi, brut, manifeste, entree, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    avant = manifeste.read_bytes()
    _archiver(entree()["sha256"], _gz(REVISE, SEPTEMBRE), monkeypatch)
    servi["octets"] = _gz(REVISE, OCTOBRE)

    assert fetch.main([]) == 1
    assert manifeste.read_bytes() == avant
    assert not brut.exists()


def test_une_archive_refusee_retombe_sur_le_producteur(chaine, monkeypatch):
    """Lecture refusée : la restauration passe au producteur, sous comparaison — et la
    sonde de fin de run rougit le run, puisque le filet ne tient plus."""
    certifier, servi, brut, _, entree, _ = chaine
    certifier(_gz(CONTENU, SEPTEMBRE), {"empreinte_decompressee": True})
    _archiver(entree()["sha256"], b"", monkeypatch,
              refus=depot.DepotMalConfigure("HTTP 403 — AccessDenied"))
    servi["octets"] = _gz(CONTENU, OCTOBRE)

    assert fetch.main([]) == 1, "le filet ne tient plus : le run doit le dire"
    assert brut.read_bytes() == servi["octets"], "la restauration, elle, a eu lieu"


def test_la_lecture_de_l_archive_est_sondee_a_chaque_run(chaine, monkeypatch):
    """Un octet du dernier dépôt, lu à chaque run : le filet est prouvé avant l'éviction
    qui le rendrait nécessaire, pas le jour même."""
    certifier, _, _, _, entree, _ = chaine
    certifies = _gz(CONTENU, SEPTEMBRE)
    certifier(certifies, {"empreinte_decompressee": True}, garder=True)
    simule = _archiver(entree()["sha256"], certifies, monkeypatch)
    _producteur_interdit(monkeypatch)

    assert fetch.main([]) == 0
    assert simule.lectures == [(CLE, "bytes=0-0")]
