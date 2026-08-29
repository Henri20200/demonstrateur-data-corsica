"""Reconstituer un registre depuis Git : ce qui doit en sortir, et ce qui ne doit pas.

La reconstitution touche à un fichier VERSIONNÉ qui fait foi. Elle mérite les mêmes
verrous que la collecte vivante, et pour des raisons qui ne se voient pas à l'œil sur une
sortie de 940 lignes :

1. **une version par changement d'empreinte, jamais par passage du cron** — sinon un
   registre de millésimes devient un journal de scrutation, avec quatre entrées par jour
   et par source qui disent toutes la même chose ;
2. **les intervalles s'enchaînent bord à bord** — `superseded_at` de l'une est
   `first_observed_at` de la suivante, la dernière restant ouverte. C'est ce qui permet à
   `version_connue_a` de répondre pour n'importe quel instant, sans trou ni recouvrement ;
3. **une version reconstituée n'a AUCUNE adresse de dépôt** — ses octets n'existent nulle
   part et n'existeront jamais. La confondre avec un dépôt raté ferait retenter l'
   impossible à chaque run, et noierait l'avertissement qui compte ;
4. **les instants sont en UTC et de largeur fixe** — le registre compare ses bornes comme
   du texte ; un décalage horaire ou des microsecondes manquantes y font un ordre faux ;
5. **la ligne de travail n'entre pas dans le registre** — un manifeste committé sur une
   branche est un état que la chaîne d'intégration n'a jamais eu, et l'y faire entrer
   fabrique des retours en arrière qui n'ont pas eu lieu ;
6. **rien n'est écrit sans `--ecrire`**, et rien du tout si une anomalie rendrait le
   registre faux.

Chaque test construit un dépôt Git jetable dans `tmp_path` et n'y committe que le
manifeste : rien ne touche au dépôt réel, ni à son registre — que la redirection de
`conftest.py` met de toute façon hors de portée.
"""

import json
import os
import subprocess

import pytest

from demonstrateur import archive, reconstitution

A, B, C = "sha_aaa", "sha_bbb", "sha_ccc"


def _git(repo, *args, quand: str | None = None, tolerant: bool = False) -> None:
    """`tolerant` sert au seul cas d'une fusion en conflit, qui rend 1 sans être un échec."""
    horloge = {"GIT_AUTHOR_DATE": quand, "GIT_COMMITTER_DATE": quand} if quand else {}
    subprocess.run(
        ["git", *args], cwd=repo, check=not tolerant, capture_output=True,
        env={**os.environ, **horloge},
    )


def _manifeste(**empreintes) -> dict:
    return {
        source_id: {
            "url": f"https://exemple.test/{source_id}.csv.gz",
            "filename": f"{source_id}.csv.gz",
            "sha256": sha,
            "taille_octets": 42,
            "date_collecte": "2026-07-19",
        }
        for source_id, sha in empreintes.items()
    }


def _committer(repo, quand: str, sujet: str = "millésime", **empreintes) -> None:
    fichier = repo / "data" / "raw" / "_manifest.json"
    fichier.write_text(json.dumps(_manifeste(**empreintes), indent=2), encoding="utf-8")
    _git(repo, "add", "data/raw/_manifest.json")
    _git(repo, "commit", "-m", sujet, quand=quand)


@pytest.fixture
def depot_jetable(tmp_path, monkeypatch):
    """Dépôt Git jetable, avec les chemins du module détournés vers lui.

    `VERSIONS_FILE` pointe sur celui de `archive`, déjà redirigé hors du dépôt réel par
    `conftest.py` : les deux modules doivent viser le MÊME fichier, sans quoi le test
    vérifierait une écriture que la collecte vivante ne relirait jamais.
    """
    racine = tmp_path / "depot_jetable"
    (racine / "data" / "raw").mkdir(parents=True)
    _git(racine, "init", "-b", "master")
    _git(racine, "config", "user.email", "verrou@exemple.test")
    _git(racine, "config", "user.name", "Verrou")
    _git(racine, "config", "commit.gpgsign", "false")
    monkeypatch.setattr(reconstitution, "ROOT", racine)
    monkeypatch.setattr(reconstitution, "VERSIONS_FILE", archive.VERSIONS_FILE)
    return racine


def _registre(ref: str = "HEAD", premier_parent: bool = True):
    vus, rapport = reconstitution.instantanes(ref, premier_parent=premier_parent)
    return reconstitution.reconstituer(vus, rapport)


def test_une_source_immobile_ne_gagne_pas_de_version_quand_sa_voisine_bouge(depot_jetable):
    """Le manifeste est réécrit ENTIER à chaque run : il change dès qu'une seule source change.

    Trente-huit sources y cohabitent, dont beaucoup de tranches closes qui ne bougeront
    plus jamais. Dater une version par commit du manifeste leur en donnerait une par
    passage du cron — un journal de scrutation là où on veut un registre de millésimes.
    C'est l'empreinte de CHAQUE source qui décide, jamais le commit.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A, tranche=A)
    _committer(depot_jetable, "2026-07-19T12:00:00+00:00", mix=B, tranche=A)
    _committer(depot_jetable, "2026-07-19T18:00:00+00:00", mix=C, tranche=A)

    index, _ = _registre()
    assert [v["sha256"] for v in index["mix"]] == [A, B, C]
    assert [v["sha256"] for v in index["tranche"]] == [A], "la tranche close n'a pas bougé"
    assert index["tranche"][0]["superseded_at"] is None


def test_les_intervalles_s_enchainent_bord_a_bord_et_le_dernier_reste_ouvert(depot_jetable):
    """`[first_observed_at ; superseded_at[` : sans recouvrement, et sans trou.

    Un trou ferait répondre None à `version_connue_a` pour un instant que la chaîne
    couvrait pourtant ; un recouvrement lui ferait rendre la première des deux, au hasard
    de l'ordre. Les deux sont des réponses fausses à la seule question qui compte.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    _committer(depot_jetable, "2026-07-19T12:00:00+00:00", mix=B)
    _committer(depot_jetable, "2026-07-19T18:00:00+00:00", mix=C)

    versions = _registre()[0]["mix"]
    assert versions[0]["superseded_at"] == versions[1]["first_observed_at"]
    assert versions[1]["superseded_at"] == versions[2]["first_observed_at"]
    assert versions[2]["superseded_at"] is None, "la version courante n'est pas dépassée"


def test_un_contenu_qui_revient_ouvre_une_nouvelle_version(depot_jetable):
    """A, puis B, puis A de nouveau : trois versions, pas deux.

    Même règle que la collecte vivante, qui ne compare qu'à la DERNIÈRE version connue.
    Ce n'est pas un cas d'école : le 22/07/2026, la fusion d'une branche a ramené sur
    master un manifeste antérieur à un rafraîchissement du cron. Reconnaître le contenu et
    rouvrir l'intervalle de la première version prétendrait que la chaîne l'a détenu sans
    interruption — c'est faux, et un backtest en tirerait une donnée qu'il n'avait pas.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    _committer(depot_jetable, "2026-07-19T12:00:00+00:00", mix=B)
    _committer(depot_jetable, "2026-07-19T18:00:00+00:00", mix=A)

    versions = _registre()[0]["mix"]
    assert [v["sha256"] for v in versions] == [A, B, A]
    assert versions[0]["superseded_at"] == versions[1]["first_observed_at"]
    assert versions[2]["superseded_at"] is None


def test_une_version_reconstituee_n_a_aucune_adresse_de_depot(depot_jetable):
    """Ses octets ont disparu avant l'archive : rien ne les rattrapera, il faut le dire.

    `payload_key` nul est ce qui empêche `retenter_depots_en_attente` de s'y essayer, et
    `versions_non_deposees` de la compter parmi les reprises dues. Sans cette distinction,
    le CI avertirait toutes les six heures de mille versions qu'aucune reprise ne peut
    sauver, et l'avertissement d'une vraie panne réseau se perdrait dedans.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    assert reconstitution.main(["--ecrire"]) == 0

    version = json.loads(archive.VERSIONS_FILE.read_text(encoding="utf-8"))["mix"][0]
    assert version["origine"] == archive.ORIGINE_RECONSTITUEE
    assert version["payload_key"] is None
    assert version["payload_archived"] is False
    assert version["fichier_archive"] is None

    assert archive.versions_non_deposees() == [], "une reprise impossible n'est pas une reprise due"
    assert archive.versions_sans_octets() == [("mix", A)], "le trou définitif doit rester visible"
    assert archive.retenter_depots_en_attente() == []


def test_le_registre_reconstitue_repond_a_version_connue_a(depot_jetable):
    """Le but de l'exercice : rendre l'historique INTERROGEABLE, pas seulement présent.

    Le fichier doit sortir sous une forme que la chaîne vivante relit sans conversion —
    même clés, mêmes types, mêmes bornes. Ce test est le seul qui vérifie que les deux
    moitiés se parlent.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    _committer(depot_jetable, "2026-07-19T18:00:00+00:00", mix=B)
    assert reconstitution.main(["--ecrire"]) == 0

    assert archive.version_connue_a("mix", "2026-07-19T09:00:00.000000Z")["sha256"] == A
    assert archive.version_connue_a("mix", "2026-07-19T23:00:00.000000Z")["sha256"] == B
    assert archive.version_connue_a("mix", "2026-07-01T00:00:00.000000Z") is None, (
        "avant la première collecte, la chaîne ne détenait rien — c'est une réponse"
    )


def test_les_instants_sont_en_utc_et_toujours_de_largeur_fixe(depot_jetable):
    """Git date en heure locale ; le registre compare ses bornes comme du TEXTE.

    Un `+02:00` laissé tel quel décalerait l'ordre de deux heures. Et des microsecondes
    omises parce qu'elles valent zéro raccourciraient la chaîne : `'.'` (0x2E) précède
    `'Z'` (0x5A), donc `...:00.500000Z` passerait AVANT `...:00Z` qu'il suit pourtant.
    Largeur fixe, sinon l'ordre du texte cesse d'être l'ordre du temps.
    """
    _committer(depot_jetable, "2026-07-19T08:00:00+02:00", mix=A)

    debut = _registre()[0]["mix"][0]["first_observed_at"]
    assert debut == "2026-07-19T06:00:00.000000Z"
    assert len(debut) == len(archive._maintenant()), (
        "un instant reconstitué et un instant vivant doivent avoir la même largeur"
    )


def test_une_source_disparue_du_manifeste_garde_son_intervalle_ouvert(depot_jetable):
    """Retirée de `sources.yaml`, elle cesse d'être suivie — pas d'avoir été détenue.

    Le registre vivant ne refermerait pas davantage l'intervalle : il ne sait rien d'une
    source que `fetch` ne lui présente plus. Et son retour avec le même contenu ne doit
    pas fabriquer une deuxième version, sans quoi tout aller-retour dans `sources.yaml`
    gonflerait le registre d'entrées qui ne disent rien de la donnée.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A, tranche=A)
    _committer(depot_jetable, "2026-07-19T12:00:00+00:00", mix=B)
    _committer(depot_jetable, "2026-07-19T18:00:00+00:00", mix=B, tranche=A)

    index, rapport = _registre()
    assert [v["sha256"] for v in index["tranche"]] == [A]
    assert index["tranche"][0]["superseded_at"] is None
    assert rapport.disparitions["tranche"] == 1, "la disparition doit être signalée, pas tue"


def test_la_ligne_de_travail_n_entre_pas_dans_le_registre(depot_jetable):
    """Un manifeste committé sur une branche est un état que l'intégration n'a jamais eu.

    Construction : master passe de A à B pendant qu'une branche pose C, puis la branche
    est fusionnée en gardant B. La chaîne d'intégration n'a détenu que A puis B — C n'a
    existé que sur le poste de travail. Le premier parent le dit ; `--toutes-branches`
    intercale C entre les deux et fabriquerait, au commit suivant, un « retour » à B que
    personne n'a fait.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A, tranche=A)
    _git(depot_jetable, "checkout", "-b", "travail")
    _committer(depot_jetable, "2026-07-19T09:00:00+00:00", mix=C, tranche=A,
               sujet="fetch local sur la branche")
    _git(depot_jetable, "checkout", "master")
    _committer(depot_jetable, "2026-07-19T12:00:00+00:00", mix=B, tranche=A)
    # La fusion conflicte sur le manifeste : on la résout comme l'a fait le 22/07/2026 la
    # fusion qui a ramené le manifeste de la branche par-dessus un run du cron.
    _git(depot_jetable, "merge", "travail", "--no-ff", "--no-commit", tolerant=True)
    _committer(depot_jetable, "2026-07-19T15:00:00+00:00", mix=C, tranche=B, sujet="fusion")

    integration, _ = _registre(premier_parent=True)
    empreintes = [v["sha256"] for v in integration["mix"]]
    assert empreintes == [A, B, C]
    assert len(empreintes) == len(set(empreintes)), "la ligne d'intégration n'est jamais revenue"
    assert integration["mix"][-1]["first_observed_at"] == "2026-07-19T15:00:00.000000Z", (
        "C entre sur la ligne d'intégration à la fusion, pas au fetch local qui l'a produit"
    )

    tout, _ = _registre(premier_parent=False)
    assert [v["sha256"] for v in tout["mix"]] == [A, C, B, C], (
        "en mêlant les branches, le registre affirmerait un retour à C qui n'a pas eu lieu"
    )


def test_l_ecriture_depuis_toutes_les_branches_est_refusee(depot_jetable):
    """`--toutes-branches` sert à regarder. L'écrire poserait un registre faux."""
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)

    assert reconstitution.main(["--ecrire", "--toutes-branches"]) == 1
    assert not archive.VERSIONS_FILE.exists()


def test_deux_commits_au_meme_instant_bloquent_l_ecriture(depot_jetable):
    """Un intervalle de largeur nulle rend une version invisible, en silence.

    `version_connue_a` cherche `debut <= instant < fin` : si les deux bornes coïncident,
    aucun instant ne satisfait la condition, et la version existe dans le fichier sans
    jamais pouvoir être rendue. Mieux vaut refuser d'écrire et montrer les deux commits
    que poser un registre qui saute une version sans le dire.
    """
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=B)

    _, rapport = _registre()
    assert rapport.intervalles_plats, "la collision d'instants doit être vue"
    assert reconstitution.main(["--ecrire"]) == 1
    assert not archive.VERSIONS_FILE.exists()


def test_sans_ecrire_rien_n_est_ecrit(depot_jetable, capsys):
    """Le rapport se lit avant d'écrire : un registre qui fait foi ne se pose pas par défaut."""
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)

    assert reconstitution.main([]) == 0
    assert not archive.VERSIONS_FILE.exists()
    assert "Rien n'a été écrit" in capsys.readouterr().out


def test_la_fusion_ne_retire_aucune_version_vivante(depot_jetable):
    """Le registre vivant est intouchable, à une exception près, et elle est encadrée.

    Une version observée pour de vrai porte des octets et une adresse ; la reconstitution
    n'a ni l'un ni l'autre à lui apporter. Elle vient DEVANT elle. Le seul cas où elle la
    touche : même empreinte de part et d'autre, donc une seule et même version, dont on
    apprend qu'elle commençait plus tôt — sa date de début recule, son dépôt reste.
    """
    vivant = {
        "mix": [{
            "sha256": B, "resolved_url": "https://exemple.test/mix.csv.gz",
            "first_observed_at": "2026-07-19T12:00:00.000000Z", "superseded_at": None,
            "fichier_archive": "20260719T120000Z_sha_bbbb.csv.gz",
            "payload_key": "archive/mix/2026/07/20260719T120000Z_sha_bbb.csv.gz",
            "payload_archived": True, "taille_octets": 42, "revision_policy": "unknown",
            "origine": archive.ORIGINE_COLLECTE,
        }],
    }
    _committer(depot_jetable, "2026-07-19T06:00:00+00:00", mix=A)
    _committer(depot_jetable, "2026-07-19T09:00:00+00:00", mix=B)

    reconstitue, rapport = _registre()
    fusionne = reconstitution.fusionner(vivant, reconstitue, rapport)

    assert [v["sha256"] for v in fusionne["mix"]] == [A, B]
    ancienne, courante = fusionne["mix"]
    assert courante["payload_archived"] is True, "le dépôt d'une version vivante ne se perd pas"
    assert courante["origine"] == archive.ORIGINE_COLLECTE
    assert courante["first_observed_at"] == "2026-07-19T09:00:00.000000Z", (
        "même empreinte des deux côtés : la version vivante commençait plus tôt"
    )
    assert ancienne["superseded_at"] == courante["first_observed_at"]
