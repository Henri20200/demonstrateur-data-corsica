"""Millésimes : ce qui doit être conservé, ce qui ne doit pas l'être, et l'intervalle.

Cinq propriétés tiennent tout l'intérêt de `archive.py`, et aucune ne se vérifie à l'œil
sur un run de six heures :

1. **une archive n'est écrite QUE si l'empreinte change** — sinon le cron transforme un
   registre de millésimes en journal de scrutation (quatre copies identiques par jour) ;
2. **une source figée reçoit une copie initiale, et une seule** — son unique exemplaire
   était `data/raw`, c'est-à-dire un cache d'Actions en CI, et un cache n'est pas une
   archive patrimoniale. Mais elle n'a pas de versions successives à suivre ;
3. **l'intervalle de connaissance est exact** — `[first_observed_at ; superseded_at[`
   est ce qui permettra de demander « que détenions-nous à cet instant ? » plutôt que
   « quelle est aujourd'hui la meilleure version ? ». C'est la question qui sépare un
   backtest honnête d'une fuite temporelle ;
4. **les octets partent AVANT que l'index ne les annonce** — dans l'autre ordre, une panne
   réseau laisserait un index qui jure connaître une version que personne ne peut plus
   produire, et que personne ne repasserait chercher ;
5. **un dépôt raté se reprend** — au run suivant l'empreinte n'est plus nouvelle, donc le
   chemin ordinaire ne fait rien. Sans reprise explicite, l'incident passager devient une
   perte définitive.

Les tests réécrivent les chemins du module (`DATA_ARCHIVE`, `VERSIONS_FILE`,
`LAST_CHECKED_FILE`) vers un tmp_path, et remplacent le dépôt distant par un faux : rien
n'est écrit dans le vrai `data/`, rien ne sort sur le réseau.
"""

import json

import pytest
from conftest import SOURCES_FICTIVES

from demonstrateur import archive, config, depot


class DepotFactice:
    """Stockage en mémoire — et, au besoin, stockage en panne.

    `avant_depot` est appelé au moment précis du dépôt : c'est ce qui permet d'observer
    l'état de l'index À CET INSTANT, donc de vérifier un ordre d'écriture plutôt que de
    le supposer.
    """

    def __init__(self, en_panne: bool = False, avant_depot=None):
        self.objets: dict[str, bytes] = {}
        self.en_panne = en_panne
        self.avant_depot = avant_depot

    def deposer(self, cle: str, chemin, **_):
        if self.avant_depot is not None:
            self.avant_depot(cle)
        if self.en_panne:
            raise depot.DepotIndisponible("stockage injoignable (simulé)")
        self.objets[cle] = chemin.read_bytes()
        return cle


@pytest.fixture
def archive_isolee(tmp_path, monkeypatch):
    """Redirige l'archive vers un dossier temporaire, sans aucun dépôt distant."""
    monkeypatch.setattr(archive, "DATA_ARCHIVE", tmp_path / "archive")
    monkeypatch.setattr(archive, "VERSIONS_FILE", tmp_path / "archive" / "_versions.json")
    monkeypatch.setattr(archive, "LAST_CHECKED_FILE", tmp_path / "archive" / "_last_checked.json")
    monkeypatch.setattr(archive, "_depot_durable", lambda: None)
    return tmp_path


def _source(tmp_path, contenu: str, nom: str = "mix.csv.gz"):
    fichier = tmp_path / nom
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


def _versions(source_id: str = "mix") -> list[dict]:
    return json.loads(archive.VERSIONS_FILE.read_text(encoding="utf-8"))[source_id]


GLISSANT = {
    "url": "https://exemple.test/mix.csv.gz",
    "filename": "mix.csv.gz",
    "glissant": True,
}
FIGE = {
    "url": "https://exemple.test/tranche_close.csv.gz",
    "filename": "tranche_close.csv.gz",
}


def test_une_empreinte_inchangee_n_ecrit_pas_de_millesime(archive_isolee):
    """Le cas ordinaire : le cron passe, la donnée n'a pas bougé, rien ne s'accumule."""
    fichier = _source(archive_isolee, "a,b\n1,2\n")

    premier = archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    assert premier is not None, "la toute première version doit être conservée"

    for _ in range(4):  # quatre passages du cron dans la journée
        assert archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa") is None

    assert len(_versions()) == 1, "une seule version pour une seule empreinte"
    fichiers = list((archive.DATA_ARCHIVE / "mix").iterdir())
    assert len(fichiers) == 1, "aucune copie identique ne doit s'ajouter"


def test_une_empreinte_nouvelle_clot_la_precedente(archive_isolee):
    """L'intervalle de connaissance se referme quand la version suivante est observée."""
    fichier = _source(archive_isolee, "a,b\n1,2\n")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")

    fichier.write_text("a,b\n1,3\n", encoding="utf-8")
    assert archive.enregistrer_version("mix", GLISSANT, fichier, "sha_bbb") is not None

    versions = _versions()
    assert [v["sha256"] for v in versions] == ["sha_aaa", "sha_bbb"]
    assert versions[0]["superseded_at"] is not None, "la version dépassée doit être close"
    assert versions[1]["superseded_at"] is None, "la version courante reste ouverte"
    assert versions[0]["superseded_at"] == versions[1]["first_observed_at"], (
        "aucun trou ni recouvrement entre deux intervalles consécutifs"
    )
    assert versions[0]["first_observed_at"] < versions[0]["superseded_at"], (
        "un intervalle de largeur nulle signifierait une version jamais détenue — "
        "c'est ce que la précision à la microseconde empêche"
    )


def test_une_source_figee_recoit_une_copie_initiale_et_une_seule(archive_isolee, monkeypatch):
    """Correction du 20/08/2026 : jusqu'ici elle n'était pas archivée du tout.

    L'argument tenait pour la copie LOCALE — `data/raw` la porte déjà, sur le même
    disque — mais pas pour le dépôt durable, où elle n'existait nulle part. En CI son seul
    exemplaire vit derrière un cache d'Actions, qui s'évince. Elle est donc déposée. Une
    fois : une source figée n'a pas de versions successives à suivre.
    """
    faux = DepotFactice()
    monkeypatch.setattr(archive, "_depot_durable", lambda: faux)
    fichier = _source(archive_isolee, "figé\n", nom="tranche_close.csv.gz")

    premiere = archive.enregistrer_version("tranche", FIGE, fichier, "sha_aaa")
    assert premiere is not None and premiere["payload_archived"] is True
    assert len(faux.objets) == 1

    fichier.write_text("autre\n", encoding="utf-8")
    assert archive.enregistrer_version("tranche", FIGE, fichier, "sha_bbb") is None
    assert len(_versions("tranche")) == 1, "pas de millésimes pour une source figée"
    assert len(faux.objets) == 1, "et pas de deuxième dépôt non plus"


def test_une_source_figee_n_a_pas_de_copie_locale(archive_isolee, monkeypatch):
    """La dupliquer sur le même disque coûterait ~150 Mo de tranches closes pour rien."""
    monkeypatch.setattr(archive, "_depot_durable", lambda: DepotFactice())
    fichier = _source(archive_isolee, "figé\n", nom="tranche_close.csv.gz")

    entree = archive.enregistrer_version("tranche", FIGE, fichier, "sha_aaa")
    assert entree["fichier_archive"] is None
    assert not (archive.DATA_ARCHIVE / "tranche").exists()


def test_politique_immutable_et_append_only_ne_suivent_pas_les_versions(archive_isolee):
    """Contenu qui ne bouge pas, ou passé reconstituable par troncature : rien à suivre."""
    for politique in ("immutable", "append_only"):
        assert not archive.archive_demandee({**GLISSANT, "revision_policy": politique})
    for politique in ("revisable", "unknown"):
        assert archive.archive_demandee({**GLISSANT, "revision_policy": politique})


def test_unknown_est_le_defaut_et_conserve_les_versions(archive_isolee):
    """Nous croyons savoir aujourd'hui quelles sources se révisent. Prudence par défaut."""
    assert archive.politique({}) == "unknown"
    assert archive.politique({"revision_policy": "n_importe_quoi"}) == "unknown"
    assert archive.archive_demandee(GLISSANT), "une glissante non déclarée conserve"


def test_archive_versions_explicite_prime_sur_la_politique(archive_isolee):
    assert not archive.archive_demandee({**GLISSANT, "archive_versions": False})
    assert archive.archive_demandee({"filename": "x.csv", "archive_versions": True})


def test_version_connue_a_repond_selon_l_instant_pas_selon_aujourdhui(archive_isolee):
    """LE point du module : rejouer ce que la chaîne détenait, pas ce qu'elle sait."""
    fichier = _source(archive_isolee, "v1\n")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    debut_v1 = _versions()[0]["first_observed_at"]

    fichier.write_text("v2\n", encoding="utf-8")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_bbb")
    bascule = _versions()[0]["superseded_at"]

    assert archive.version_connue_a("mix", debut_v1)["sha256"] == "sha_aaa"
    assert archive.version_connue_a("mix", bascule)["sha256"] == "sha_bbb", (
        "à l'instant exact de la bascule, c'est la NOUVELLE version qui est détenue"
    )
    assert archive.version_connue_a("mix", "1999-01-01T00:00:00Z") is None, (
        "avant la première observation, la chaîne ne détenait rien — et c'est une réponse"
    )


def test_le_dernier_controle_est_note_meme_sans_nouvelle_version(archive_isolee):
    """Distingue « rien n'a changé » de « nous ne regardions pas »."""
    fichier = _source(archive_isolee, "a\n")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")

    controles = json.loads(archive.LAST_CHECKED_FILE.read_text(encoding="utf-8"))
    assert "mix" in controles


def test_l_index_des_versions_ne_porte_aucun_contenu(archive_isolee):
    """Il est VERSIONNÉ : il ne doit transporter que des métadonnées, jamais de donnée."""
    fichier = _source(archive_isolee, "secret_metier,42\n")
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")

    brut = archive.VERSIONS_FILE.read_text(encoding="utf-8")
    assert "secret_metier" not in brut
    attendus = {
        "sha256", "resolved_url", "first_observed_at", "superseded_at",
        "fichier_archive", "payload_key", "payload_archived", "taille_octets",
        "revision_policy",
    }
    assert set(json.loads(brut)["mix"][0]) == attendus


def test_l_index_ne_porte_jamais_la_valeur_d_un_jeton(archive_isolee):
    """L'index est versionné et part sur GitHub : même régime que le manifeste.

    `meta["url"]` porte le GABARIT `${NOM}` — l'expansion vit dans une variable locale de
    `fetch.main()`. Ce test tient la promesse plutôt que la vigilance, comme test_secrets.
    """
    fichier = _source(archive_isolee, "a\n")
    avec_jeton = {**GLISSANT, "url": "https://api.exemple/data?securityToken=${ENTSOE_TOKEN}"}
    archive.enregistrer_version("mix", avec_jeton, fichier, "sha_aaa")

    brut = archive.VERSIONS_FILE.read_text(encoding="utf-8")
    assert "${ENTSOE_TOKEN}" in brut, "le gabarit documente que la source est authentifiée"
    assert "7a5e6020" not in brut  # aucune valeur de jeton, sous aucune forme


def test_les_octets_partent_avant_que_l_index_ne_les_annonce(archive_isolee, monkeypatch):
    """L'ordre, et c'est LE point de ce module.

    Un index écrit d'abord annoncerait une version dont les octets ne sont peut-être
    jamais arrivés — et l'empreinte n'étant plus nouvelle au run suivant, personne ne
    repasserait les chercher. Le test observe l'index AU MOMENT du dépôt.
    """
    vu = {}

    def au_moment_du_depot(_cle):
        vu["index_ecrit"] = (
            archive.VERSIONS_FILE.exists()
            and "sha_aaa" in archive.VERSIONS_FILE.read_text(encoding="utf-8")
        )

    faux = DepotFactice(avant_depot=au_moment_du_depot)
    monkeypatch.setattr(archive, "_depot_durable", lambda: faux)
    fichier = _source(archive_isolee, "a\n")

    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    assert vu["index_ecrit"] is False, "l'index a annoncé la version avant de l'avoir déposée"
    assert _versions()[0]["payload_archived"] is True


def test_un_depot_en_echec_indexe_quand_meme_la_version(archive_isolee, monkeypatch):
    """L'intervalle de connaissance ne se reconstruit pas : il ne se perd pas pour un réseau."""
    monkeypatch.setattr(archive, "_depot_durable", lambda: DepotFactice(en_panne=True))
    fichier = _source(archive_isolee, "a\n")

    entree = archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    assert entree["payload_archived"] is False
    assert entree["payload_key"], "la clé est promise même quand les octets n'arrivent pas"
    assert archive.versions_non_deposees() == [("mix", "sha_aaa")]


def test_la_version_courante_non_deposee_est_reprise_au_run_suivant(archive_isolee, monkeypatch):
    """Le piège : au run suivant, l'empreinte n'est plus nouvelle.

    Sans reprise ici, une panne de trente secondes rendrait la version définitivement
    manquante, avec un index qui continuerait d'affirmer la connaître.
    """
    fichier = _source(archive_isolee, "a\n")
    monkeypatch.setattr(archive, "_depot_durable", lambda: DepotFactice(en_panne=True))
    entree = archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")
    cle = entree["payload_key"]

    revenu = DepotFactice()
    monkeypatch.setattr(archive, "_depot_durable", lambda: revenu)
    assert archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa") is None

    versions = _versions()
    assert len(versions) == 1, "la reprise ne doit pas fabriquer une deuxième version"
    assert versions[0]["payload_archived"] is True
    assert versions[0]["payload_key"] == cle, "la clé d'une version ne bouge jamais"
    assert cle in revenu.objets
    assert archive.versions_non_deposees() == []


def test_une_version_depassee_est_reprise_depuis_sa_copie_locale(archive_isolee, monkeypatch):
    """Ses octets ont quitté data/raw ; seule la copie locale les tient encore.

    C'est le cas que la reprise ordinaire ne couvre pas : `enregistrer_version` ne revoit
    jamais une empreinte dépassée.
    """
    fichier = _source(archive_isolee, "v1\n")
    monkeypatch.setattr(archive, "_depot_durable", lambda: DepotFactice(en_panne=True))
    v1 = archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")

    fichier.write_text("v2\n", encoding="utf-8")
    revenu = DepotFactice()
    monkeypatch.setattr(archive, "_depot_durable", lambda: revenu)
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_bbb")
    assert v1["payload_key"] not in revenu.objets, "rien ne rattrape v1 sur le chemin ordinaire"

    assert archive.retenter_depots_en_attente() == [v1["payload_key"]]
    assert b"v1" in revenu.objets[v1["payload_key"]], "ce sont bien les octets de v1"
    assert b"v2" not in revenu.objets[v1["payload_key"]]
    assert archive.versions_non_deposees() == []


def test_la_reprise_ne_depose_jamais_les_octets_d_une_autre_version(archive_isolee, monkeypatch):
    """Un contenu déposé sous la clé d'une autre version serait pire que l'absence.

    L'index cesserait de dire vrai, et rien ne le signalerait : les deux empreintes
    existent, les deux objets existent, seul leur contenu est faux.
    """
    fichier = _source(archive_isolee, "v1\n")
    monkeypatch.setattr(archive, "_depot_durable", lambda: DepotFactice(en_panne=True))
    v1 = archive.enregistrer_version("mix", GLISSANT, fichier, "sha_aaa")

    # La source a changé : `fichier` ne porte plus les octets de v1.
    fichier.write_text("v2\n", encoding="utf-8")
    revenu = DepotFactice()
    monkeypatch.setattr(archive, "_depot_durable", lambda: revenu)
    archive.enregistrer_version("mix", GLISSANT, fichier, "sha_bbb")

    assert v1["payload_key"] not in revenu.objets
    v2 = _versions()[1]
    assert revenu.objets[v2["payload_key"]] == fichier.read_bytes()


def test_aucun_test_n_ecrit_dans_le_vrai_registre():
    """Invariant de la chaîne, et pas un confort de test.

    Ce test ne prend AUCUNE fixture d'isolation : il vérifie la garantie que
    `tests/conftest.py` donne à toute la suite, y compris aux tests qui ne demandent
    rien. Supprimer la redirection casse ici, pas six heures plus tard dans un commit
    du cron.
    """
    assert archive.VERSIONS_FILE != config.VERSIONS_FILE
    assert config.DATA_ARCHIVE not in archive.VERSIONS_FILE.parents
    assert config.DATA_ARCHIVE not in archive.LAST_CHECKED_FILE.parents


def test_le_registre_reel_ne_contient_aucune_source_fictive():
    """L'index est VERSIONNÉ : une donnée synthétique qui y entre devient un fait.

    C'est ce qui s'est produit le 20/08/2026 — `faux_geodair`, source inventée par
    `test_secrets.py`, écrite dans le vrai `_versions.json`. Le cron lance pytest AVANT
    `git add data/archive/_versions.json` : elle serait partie sur GitHub, où plus rien
    ne l'aurait distinguée d'un millésime réellement observé. Un registre historique ne
    se corrige pas après coup, il fait foi.

    Le verrou porte sur le RÉSULTAT, là où `conftest.py` porte sur la cause : il
    attraperait aussi une contamination arrivée par un chemin non prévu — sous-processus,
    écriture directe par `config`, exécution manuelle.
    """
    reel = config.VERSIONS_FILE
    if not reel.exists():
        pytest.skip("aucun registre de millésimes sur ce poste — rien à contaminer")
    intruses = SOURCES_FICTIVES & set(json.loads(reel.read_text(encoding="utf-8")))
    assert not intruses, (
        f"sources fictives dans le registre versionné : {sorted(intruses)}. "
        f"Les retirer de {reel} AVANT tout commit — elles ne se distingueront plus "
        "d'un millésime réel une fois dans l'historique Git."
    )
