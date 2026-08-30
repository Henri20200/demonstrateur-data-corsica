"""Dépôt durable : l'adressage, la signature, et les pannes qu'il faut distinguer.

Ce module est celui qu'on ne peut pas vérifier à l'œil. Une erreur de signature se voit
tout de suite (403), mais deux défauts silencieux ne se voient jamais depuis un poste :

- un envoi en `Transfer-Encoding: chunked`, que le stockage refuse pour une requête dont
  la charge est signée d'un bloc — tout marcherait en local, rien ne monterait en CI ;
- une reprise qui rejoue un flux DÉJÀ CONSOMMÉ, donc un corps vide : l'objet est accepté,
  et l'index jure ensuite que la version est déposée alors qu'elle pèse zéro octet.

Les deux sont tenus ici par un transport simulé — aucun octet ne sort de la machine.
"""

from datetime import datetime, timezone

import httpx
import pytest

from demonstrateur import depot
from demonstrateur.config import BUCKET_VITRINE

INSTANT = "2026-08-19T06:00:11.123456Z"


def _fichier(tmp_path, contenu: bytes = b"a,b\n1,2\n"):
    chemin = tmp_path / "mix.csv.gz"
    chemin.write_bytes(contenu)
    return chemin


def _depot() -> depot.Depot:
    return depot.Depot(
        bucket="archive-corse", endpoint="https://s3.fr-par.scw.cloud", region="fr-par",
        cle_acces="SCWAAAAAAAAAAAAAAAAA", cle_secrete="secret-de-test",
    )


def _client(repondre) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(repondre))


def test_la_cle_situe_le_contenu_dans_le_temps_et_ne_bouge_plus():
    """Une clé désigne un contenu et un seul, pour toujours — d'où l'idempotence."""
    cle = depot.cle_objet("mix_temps_reel", INSTANT, "ab12cd34", ".csv.gz")
    assert cle == "archive/mix_temps_reel/2026/08/20260819T060011Z_ab12cd34.csv.gz"
    assert depot.cle_objet("mix_temps_reel", INSTANT, "ab12cd34", ".csv.gz") == cle


def test_deux_contenus_de_la_meme_seconde_ne_partagent_pas_de_cle():
    """L'unicité tient à l'empreinte, pas à l'horodatage — qui, lui, n'a que la seconde."""
    assert depot.cle_objet("mix", INSTANT, "aaa", ".csv") != depot.cle_objet(
        "mix", INSTANT, "bbb", ".csv"
    )


def test_la_requete_est_signee_et_annonce_sa_longueur(tmp_path):
    """Sans `Content-Length` explicite, httpx passerait en chunked — refusé, et en silence."""
    chemin = _fichier(tmp_path)
    vues = []

    with _client(lambda requete: (vues.append(requete), httpx.Response(200))[1]) as client:
        _depot().deposer("archive/mix/2026/08/x.csv.gz", chemin, client=client)

    (requete,) = vues
    assert requete.method == "PUT"
    assert str(requete.url) == (
        "https://archive-corse.s3.fr-par.scw.cloud/archive/mix/2026/08/x.csv.gz"
    )
    assert requete.headers["content-length"] == str(chemin.stat().st_size)
    assert "transfer-encoding" not in requete.headers
    assert requete.headers["x-amz-content-sha256"] == depot.empreinte_octets(chemin)
    autorisation = requete.headers["authorization"]
    assert autorisation.startswith("AWS4-HMAC-SHA256 Credential=SCWAAAAAAAAAAAAAAAAA/")
    assert "/fr-par/s3/aws4_request" in autorisation
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date" in autorisation
    assert "Signature=" in autorisation


def test_la_signature_est_conforme_a_sigv4(tmp_path, monkeypatch):
    """Vecteur figé, obtenu de botocore le 20/08/2026 — sans en faire une dépendance.

    La signature est la seule partie du module que personne ne peut relire à l'œil, et son
    échec en production est un 403 laconique six heures plus tard. Le vecteur verrouille la
    requête canonique autant que la dérivation de clé : intervertir deux en-têtes signés,
    oublier la ligne vide qui termine les en-têtes canoniques ou laisser un en-tête de plus
    entrer dans `SignedHeaders` casse ici, sur un poste, en une demi-seconde.
    """
    class Horloge:
        """Fige `datetime.now` — une signature dépend de l'instant, un vecteur non."""

        @staticmethod
        def now(_tz=None):
            return datetime(2026, 8, 19, 6, 0, 11, tzinfo=timezone.utc)

    monkeypatch.setattr(depot, "datetime", Horloge)
    vues = []

    with _client(lambda requete: (vues.append(requete), httpx.Response(200))[1]) as client:
        _depot().deposer("archive/mix/2026/08/20260819T060011Z_ab12cd34.csv.gz",
                         _fichier(tmp_path), client=client)

    assert vues[0].headers["authorization"] == (
        "AWS4-HMAC-SHA256 Credential=SCWAAAAAAAAAAAAAAAAA/20260819/fr-par/s3/aws4_request, "
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, "
        "Signature=ba072aba0e0e486149a2d7ee9453fd7e90ca2c7d45364c7f29d7bca7381940ee"
    )


def test_aucun_acl_public_n_est_envoye(tmp_path):
    """C'est de la donnée brute de producteurs tiers. L'objet naît privé, et le reste."""
    vues = []
    with _client(lambda requete: (vues.append(requete), httpx.Response(200))[1]) as client:
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client)

    assert not [nom for nom in vues[0].headers if nom.lower().startswith("x-amz-acl")]


def test_une_panne_passagere_est_retentee_avec_le_corps_complet(tmp_path, monkeypatch):
    """La reprise doit rejouer les OCTETS, pas un flux déjà consommé.

    Un corps vide serait accepté par le stockage, et l'index jurerait ensuite que la
    version est déposée. C'est le défaut le plus coûteux du module, et le plus discret.
    """
    monkeypatch.setattr(depot, "_PAUSE", 0.0)
    chemin = _fichier(tmp_path, b"des octets qui comptent\n")
    corps = []

    def repondre(requete):
        corps.append(requete.read())
        return httpx.Response(503 if len(corps) == 1 else 200)

    with _client(repondre) as client:
        assert _depot().deposer("archive/mix/x.csv.gz", chemin, client=client) == (
            "archive/mix/x.csv.gz"
        )

    assert len(corps) == 2, "un 503 doit être retenté"
    assert corps[0] == corps[1] == chemin.read_bytes()


def test_une_erreur_definitive_n_est_pas_retentee(tmp_path, monkeypatch):
    """Insister sur un 403 ne fait que retarder le message qui dit quoi corriger.

    Et depuis le 30/08/2026 le TYPE le dit aussi : un 403 est un refus d'identifiants ou
    de politique, donc `DepotMalConfigure`. Le distinguer d'une panne n'est pas cosmétique
    — c'est ce qui décide si `archive` promet une reprise ou réclame une correction.
    """
    monkeypatch.setattr(depot, "_PAUSE", 0.0)
    appels = []

    def repondre(requete):
        appels.append(requete)
        return httpx.Response(403, text="AccessDenied")

    with _client(repondre) as client, pytest.raises(depot.DepotMalConfigure, match="403"):
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client)

    assert len(appels) == 1


def test_une_requete_impossible_a_former_ne_se_retente_pas(tmp_path, monkeypatch):
    """LE défaut du 30/08/2026, et il ne tenait qu'à un ordre de `except`.

    `httpx.LocalProtocolError` descend de `httpx.HTTPError`. Il tombait donc dans la
    branche des pannes réseau : trois tentatives, des pauses, puis un `DepotIndisponible`
    qu'`archive` indexait en « reprise au prochain run ». Or rien n'était parti sur le
    réseau — h11 refusait d'écrire l'en-tête `authorization`, la clé d'accès portant un
    caractère de contrôle (il n'en refuse que cinq : NUL, LF, VT, FF, CR). Un échec qui
    ne peut pas ne pas se reproduire était traité comme un incident passager : 71 dépôts
    tentés, 0 réussi, run VERT.

    Le message doit nommer ce qu'il faut aller corriger : c'est tout ce qui reste pour
    diagnostiquer, le log masquant la clé fautive par `***`.
    """
    monkeypatch.setattr(depot, "_PAUSE", 0.0)
    appels = []

    def repondre(requete):
        appels.append(requete)
        raise httpx.LocalProtocolError("Illegal header value (retour chariot dans la clé)")

    with _client(repondre) as client, pytest.raises(depot.DepotMalConfigure) as leve:
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client)

    assert len(appels) == 1, (
        "une requête impossible à former a été retentée — elle ne peut pas réussir, et "
        "chaque reprise coûte une pause pour rien"
    )
    assert "ARCHIVE_ACCESS_KEY" in str(leve.value), (
        "le message doit nommer la variable à corriger : le log masque la clé par ***, "
        "il ne reste que ce texte pour savoir où chercher"
    )


def test_une_panne_reseau_reste_une_panne_et_se_retente(tmp_path, monkeypatch):
    """Le pendant du précédent, et la moitié qu'il ne faut pas casser en le corrigeant.

    Un stockage injoignable revient : il doit continuer d'être retenté, et de se rendre
    comme une indisponibilité SANS être une mauvaise configuration — sans quoi la
    première coupure réseau ferait rougir le cron et réclamerait une correction qui n'a
    pas lieu d'être.
    """
    monkeypatch.setattr(depot, "_PAUSE", 0.0)
    appels = []

    def repondre(requete):
        appels.append(requete)
        raise httpx.ConnectError("stockage injoignable")

    with _client(repondre) as client, pytest.raises(depot.DepotIndisponible) as leve:
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client, essais=3)

    assert len(appels) == 3, "une panne réseau doit être retentée"
    assert not isinstance(leve.value, depot.DepotMalConfigure), (
        "une coupure réseau n'est pas une configuration à corriger"
    )


def test_une_panne_persistante_finit_par_etre_signalee(tmp_path, monkeypatch):
    """Elle ne lève pas dans le vide : `archive.py` en fait un `payload_archived: false`."""
    monkeypatch.setattr(depot, "_PAUSE", 0.0)
    appels = []

    def repondre(requete):
        appels.append(requete)
        return httpx.Response(503)

    with _client(repondre) as client, pytest.raises(depot.DepotIndisponible):
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client, essais=2)

    assert len(appels) == 2


def test_une_erreur_reseau_est_convertie_pas_propagee(tmp_path, monkeypatch):
    """`archive.py` n'attrape qu'un type d'exception, et c'est celui-là."""
    monkeypatch.setattr(depot, "_PAUSE", 0.0)

    def repondre(_requete):
        raise httpx.ConnectError("réseau injoignable")

    with _client(repondre) as client, pytest.raises(depot.DepotIndisponible):
        _depot().deposer("archive/mix/x.csv.gz", _fichier(tmp_path), client=client, essais=1)


def test_le_bucket_de_la_vitrine_est_refuse(monkeypatch):
    """Il est synchronisé avec `--delete` : l'archive y serait effacée au run suivant.

    Et une archive effacée ne se signale pas — elle manque. Le refus est donc bruyant.
    """
    monkeypatch.setenv("ARCHIVE_BUCKET", BUCKET_VITRINE)
    monkeypatch.setenv("SCW_ACCESS_KEY", "cle")
    monkeypatch.setenv("SCW_SECRET_KEY", "secret")

    with pytest.raises(depot.DepotMalConfigure, match="vitrine"):
        depot.configurer()


def test_sans_configuration_le_depot_est_simplement_absent(monkeypatch):
    """Absent n'est pas en erreur : en local, personne n'a de raison de porter les clés."""
    for nom in ("ARCHIVE_BUCKET", "ARCHIVE_ACCESS_KEY", "ARCHIVE_SECRET_KEY",
                "SCW_ACCESS_KEY", "SCW_SECRET_KEY",
                "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(nom, raising=False)
    assert depot.configurer() is None

    monkeypatch.setenv("ARCHIVE_BUCKET", "archive-corse")
    assert depot.configurer() is None, "un bucket sans clés ne suffit pas"


def test_une_cle_dediee_a_l_archive_prime_sur_celle_du_depot(monkeypatch):
    """C'est le garde-fou du bucket, mais côté compte plutôt que côté code.

    Une clé restreinte au seul bucket d'archive ne peut pas effacer la vitrine, ni être
    effacée par le `--delete` qui la synchronise. La condition dans `configurer()` devient
    alors une deuxième ceinture, pas la seule.
    """
    monkeypatch.setenv("ARCHIVE_BUCKET", "archive-corse")
    monkeypatch.setenv("SCW_ACCESS_KEY", "cle-du-depot")
    monkeypatch.setenv("SCW_SECRET_KEY", "secret-du-depot")
    monkeypatch.setenv("ARCHIVE_ACCESS_KEY", "cle-etroite")
    monkeypatch.setenv("ARCHIVE_SECRET_KEY", "secret-etroit")

    configure = depot.configurer()
    assert configure.cle_acces == "cle-etroite"
    assert configure.cle_secrete == "secret-etroit"

    monkeypatch.delenv("ARCHIVE_ACCESS_KEY")
    monkeypatch.delenv("ARCHIVE_SECRET_KEY")
    assert depot.configurer().cle_acces == "cle-du-depot", "sans clé dédiée, celle du dépôt sert"


def test_la_configuration_se_lit_dans_l_environnement(monkeypatch):
    monkeypatch.setenv("ARCHIVE_BUCKET", "archive-corse")
    monkeypatch.setenv("SCW_ACCESS_KEY", "cle")
    monkeypatch.setenv("SCW_SECRET_KEY", "secret")
    monkeypatch.delenv("ARCHIVE_ENDPOINT", raising=False)
    monkeypatch.delenv("ARCHIVE_REGION", raising=False)

    configure = depot.configurer()
    assert configure.bucket == "archive-corse"
    assert configure.region == depot.REGION_DEFAUT
    assert configure.hote == "archive-corse.s3.fr-par.scw.cloud", (
        "style virtual-hosted : le bucket est dans l'hôte, pas dans le chemin"
    )


def test_un_client_inconstructible_est_converti_pas_propage(tmp_path, monkeypatch):
    """L'environnement peut casser AVANT qu'une seule requête ne parte.

    `httpx.Client()` lève sur un `SSL_CERT_FILE` introuvable ou une variable de proxy mal
    formée. Cette construction était hors du `try` : l'exception traversait alors
    `archive._deposer`, qui ne rattrape que `DepotIndisponible`, et emportait la collecte
    — donc l'intervalle de connaissance, la seule chose qui ne se rattrape jamais. C'est
    la famille de panne du 28/08/2026 : le code n'a pas bougé, l'environnement si.
    """
    def refuser(*_args, **_kwargs):
        raise httpx.ConnectError("SSL_CERT_FILE introuvable")

    monkeypatch.setattr(depot.httpx, "Client", refuser)

    with pytest.raises(depot.DepotIndisponible, match="inconstructible"):
        _depot().deposer("archive/mix/2026/08/20260819T060011Z_abc.csv.gz",
                         _fichier(tmp_path))


# --- Le disjoncteur de volume ------------------------------------------------------------


def test_le_seuil_se_compte_en_gigaoctets_du_facturier():
    """250 Go décimaux, pas 250 Gio.

    Le seuil existe pour se comparer à une facture ; lu en 2^30 il vaudrait 268 Go
    facturés, soit 7 % de plus que ce qui a été arbitré — et personne ne le verrait.
    """
    assert depot.SEUIL_ARCHIVE_OCTETS == 250_000_000_000


def test_le_seuil_tranche_sur_l_etat_apres_ajout():
    """Ce qui tient exactement dans le seuil passe ; l'octet suivant, non."""
    depot.verifier_seuil(depot.SEUIL_ARCHIVE_OCTETS - 8, 8)

    with pytest.raises(depot.SeuilArchiveAtteint) as refus:
        depot.verifier_seuil(depot.SEUIL_ARCHIVE_OCTETS - 8, 9)
    assert "réévaluer coût/prix/politique" in str(refus.value), (
        "le refus doit dire quoi faire, pas seulement qu'il refuse"
    )


def test_un_seuil_franchi_ne_se_confond_pas_avec_une_panne():
    """La propriété qui empêche le disjoncteur d'être avalé.

    `archive._deposer` rattrape `DepotIndisponible` pour indexer et retenter au run
    suivant. Si le seuil en héritait, la chaîne réessaierait indéfiniment de dépasser une
    limite posée exprès, et le refus se lirait comme une panne réseau de plus.
    """
    assert not issubclass(depot.SeuilArchiveAtteint, depot.DepotIndisponible)
