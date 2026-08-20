"""Dépôt durable : mettre les OCTETS d'une version hors de portée de Git et du cache CI.

`archive.py` sait quelle version cette chaîne détenait et entre quand et quand — c'est
`_versions.json`, versionné, donc à l'abri de tout. Il ne dit pas où sont les octets de
ces versions. En local ils vivent sous `data/archive/` ; en CI, dans un cache d'Actions
dont la clé est indexée sur `sources.yaml`, avec quota et éviction. Un cache n'est pas une
archive patrimoniale : il existe pour éviter un retéléchargement, pas pour conserver ce
qu'un producteur ne republiera jamais. Sans ce module, l'index promet une version dont
plus personne ne peut produire le contenu.

Trois propriétés voulues, et elles se lisent dans le code plutôt que dans une consigne :

- **append-only** : rien que des PUT de clés neuves. Aucune synchronisation, aucun
  `--delete`, aucun miroir. Le bucket n'a pas de notion de « refléter un dossier » — il
  accumule. C'est exactement ce que la vitrine, elle, ne fait PAS : `aws s3 sync --delete`
  tient le bucket public comme reflet exact d'`outputs/`. Les deux régimes ne peuvent pas
  cohabiter dans un même bucket, d'où le garde-fou de `configurer()` ;
- **clés immuables** : `archive/<source_id>/<AAAA>/<MM>/<instant>_<sha256>.<ext>`. Une clé
  désigne un contenu et un seul, pour toujours. Redéposer la même version retombe sur la
  même clé et réécrit les mêmes octets : la reprise après échec est donc idempotente ;
- **privé** : aucun en-tête `x-amz-acl` n'est envoyé, l'objet naît privé. C'est de la
  donnée brute de producteurs tiers, pas une vitrine.

PAS DE BOTO3 : botocore pèse une trentaine de mégaoctets installés pour, ici, un unique
PUT sans multipart. La signature SigV4 tient en quarante lignes de `hmac`/`hashlib`
(stdlib) et le transport est `httpx`, déjà dépendance du projet.

Configuration, par l'environnement — rien n'est écrit en dur, et le bucket n'a AUCUNE
valeur par défaut : pointer l'archive sur le mauvais bucket doit demander un geste.

    ARCHIVE_BUCKET      bucket de l'archive. DISTINCT de celui de la vitrine.
    ARCHIVE_ENDPOINT    défaut https://s3.fr-par.scw.cloud
    ARCHIVE_REGION      défaut fr-par
    ARCHIVE_ACCESS_KEY  clé propre à l'archive, si elle existe
    ARCHIVE_SECRET_KEY
    SCW_ACCESS_KEY      sinon, la clé du dépôt (ou AWS_ACCESS_KEY_ID)
    SCW_SECRET_KEY      (ou AWS_SECRET_ACCESS_KEY)

UNE CLÉ PROPRE À L'ARCHIVE EST PRÉFÉRABLE, et pour la même raison que le garde-fou sur le
bucket : la clé qui déploie la vitrine peut la synchroniser avec `--delete`. Restreinte au
seul bucket d'archive, elle ne peut pas l'effacer même par accident de configuration — le
garde-fou n'est plus une condition dans du code, mais une propriété du compte. À défaut,
`SCW_*` sert aux deux, ce qui marche et se surveille.

Absente, la collecte continue : les versions sont indexées `payload_archived: false` et
le premier run qui en a les moyens les dépose.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from .config import BUCKET_VITRINE

ALGORITHME = "AWS4-HMAC-SHA256"
SERVICE = "s3"
PREFIXE = "archive"
ENDPOINT_DEFAUT = "https://s3.fr-par.scw.cloud"
REGION_DEFAUT = "fr-par"

_TAILLE_BLOC = 1 << 20
# Connexion courte, transfert long : une tranche close pèse plusieurs dizaines de Mo et
# n'a aucune raison de tenir dans le délai de lecture d'une requête ordinaire.
_DELAI = httpx.Timeout(30.0, read=300.0, write=600.0)
# Retentables : la panne est du côté du stockage ou du réseau, pas de la requête. Un 403
# (clé fausse) ou un 404 (bucket inexistant) ne s'arrangera pas en insistant — insister ne
# ferait que retarder le message qui dit quoi corriger.
_STATUTS_RETENTABLES = frozenset({408, 429, 500, 502, 503, 504})
_PAUSE = 2.0  # secondes, multipliées par le rang de la tentative


class DepotIndisponible(RuntimeError):
    """Les octets n'ont pas pu être déposés — la version reste connue, son contenu non."""


class DepotMalConfigure(DepotIndisponible):
    """Configuration refusée : à corriger, pas à retenter."""


def empreinte_octets(chemin: Path) -> str:
    """SHA-256 des octets bruts, lu par blocs.

    À NE PAS CONFONDRE avec `provenance.empreinte`, qui calcule l'empreinte d'IDENTITÉ
    d'une source — canonique là où `empreinte_ignore_xml` est déclaré. Ici on signe ce
    qu'on envoie réellement sur le fil, donc les octets, sans interprétation.
    """
    somme = hashlib.sha256()
    with chemin.open("rb") as flux:
        for bloc in iter(lambda: flux.read(_TAILLE_BLOC), b""):
            somme.update(bloc)
    return somme.hexdigest()


def cle_objet(source_id: str, instant: str, sha: str, extension: str) -> str:
    """Adresse immuable d'un contenu : `archive/<source_id>/<AAAA>/<MM>/<instant>_<sha>.<ext>`.

    `instant` est le `first_observed_at` de l'index (ISO 8601 UTC, à la microseconde),
    rendu ici à la seconde et sans séparateurs : une clé se lit et se trie à l'œil, et les
    deux-points d'un horodatage ISO demandent un échappement dans une URL. L'unicité ne
    repose pas sur lui mais sur `sha` — deux contenus distincts observés dans la même
    seconde portent deux empreintes distinctes, donc deux clés distinctes. Le même contenu
    redéposé retombe sur la MÊME clé : c'est ce qui rend la reprise après échec sûre.

    ATTENTION : `sha` est l'empreinte d'identité de la version, celle du manifeste — donc
    la forme CANONIQUE là où `empreinte_ignore_xml` est déclaré (ENTSO-E réestampille son
    enveloppe à chaque téléchargement). Elle ne coïncide alors pas avec un `sha256sum` de
    l'objet rapatrié : c'est `provenance.empreinte` qui le vérifie, pas `sha256sum`.
    """
    return (f"{PREFIXE}/{source_id}/{instant[:4]}/{instant[5:7]}/"
            f"{horodatage_compact(instant)}_{sha}{extension}")


def horodatage_compact(instant: str) -> str:
    """`2026-08-19T06:00:11.123456Z` -> `20260819T060011Z`.

    Utilisé par les clés du dépôt ET par les noms de la copie locale, pour qu'un même
    millésime se reconnaisse d'un côté comme de l'autre sans table de correspondance.
    """
    return instant[:19].replace("-", "").replace(":", "") + "Z"


def _hmac(cle: bytes, message: str) -> bytes:
    return hmac.new(cle, message.encode("utf-8"), hashlib.sha256).digest()


def _cle_de_signature(cle_secrete: str, jour: str, region: str) -> bytes:
    """Clé dérivée SigV4 : secret -> jour -> région -> service -> requête."""
    derivee = _hmac(f"AWS4{cle_secrete}".encode(), jour)
    derivee = _hmac(derivee, region)
    derivee = _hmac(derivee, SERVICE)
    return _hmac(derivee, "aws4_request")


@dataclass(frozen=True)
class Depot:
    """Un bucket S3 et de quoi y écrire. Sans état : rien à ouvrir, rien à réutiliser."""

    bucket: str
    endpoint: str
    region: str
    cle_acces: str
    cle_secrete: str

    @property
    def hote(self) -> str:
        """Style « virtual-hosted » : le bucket vit dans le nom d'hôte, pas dans le chemin."""
        return f"{self.bucket}.{urlsplit(self.endpoint).netloc}"

    def _envoyer(self, cle: str, chemin: Path, empreinte: str,
                 client: httpx.Client) -> httpx.Response:
        """Une tentative : signature SigV4 puis PUT streamé. Rouvre le fichier à chaque appel.

        Rouvrir n'est pas une précaution de style : un flux consommé par une tentative
        ratée rejouerait un corps VIDE à la suivante, et le stockage accepterait poliment
        un objet de zéro octet dont l'index jurerait qu'il porte la version.
        """
        maintenant = datetime.now(timezone.utc)
        horodatage = maintenant.strftime("%Y%m%dT%H%M%SZ")
        jour = horodatage[:8]
        chemin_canonique = "/" + quote(cle, safe="/")

        entetes_signes = {
            "host": self.hote,
            "x-amz-content-sha256": empreinte,
            "x-amz-date": horodatage,
        }
        noms_signes = ";".join(sorted(entetes_signes))
        requete_canonique = "\n".join([
            "PUT",
            chemin_canonique,
            "",  # aucun paramètre de requête
            *(f"{nom}:{entetes_signes[nom]}" for nom in sorted(entetes_signes)),
            "",  # ligne vide obligatoire après les en-têtes canoniques
            noms_signes,
            empreinte,
        ])
        portee = f"{jour}/{self.region}/{SERVICE}/aws4_request"
        a_signer = "\n".join([
            ALGORITHME,
            horodatage,
            portee,
            hashlib.sha256(requete_canonique.encode("utf-8")).hexdigest(),
        ])
        signature = _hmac(_cle_de_signature(self.cle_secrete, jour, self.region), a_signer).hex()

        entetes = {
            **entetes_signes,
            "authorization": (
                f"{ALGORITHME} Credential={self.cle_acces}/{portee}, "
                f"SignedHeaders={noms_signes}, Signature={signature}"
            ),
            # Content-Length EXPLICITE, et ce n'est pas un détail de politesse : sans lui,
            # httpx envoie un fichier ouvert en `Transfer-Encoding: chunked`, que S3 refuse
            # pour une requête dont la charge est signée d'un bloc. httpx laisse la main dès
            # que l'en-tête est posé (`Request._prepare`) — le fichier reste donc streamé,
            # jamais chargé en mémoire.
            "content-length": str(chemin.stat().st_size),
        }
        with chemin.open("rb") as flux:
            return client.put(f"https://{self.hote}{chemin_canonique}",
                              content=flux, headers=entetes)

    def deposer(self, cle: str, chemin: Path, *,
                client: httpx.Client | None = None, essais: int = 3) -> str:
        """Dépose `chemin` sous `cle`. Retourne la clé, ou lève `DepotIndisponible`.

        LA PERSISTANCE EST VÉRIFIÉE, PAS SUPPOSÉE : `x-amz-content-sha256` porte
        l'empreinte des octets envoyés, et le stockage recalcule la sienne avant d'accuser
        réception. Un 2xx signifie donc qu'il détient exactement ces octets-là, pas
        seulement qu'il a reçu quelque chose. C'est ce qui autorise `archive.py` à n'écrire
        `payload_archived: true` qu'après retour de cette méthode.

        `essais` couvre la panne passagère — celle qui, sans reprise, rendrait
        définitivement manquante une version que l'index dit pourtant connaître.
        """
        empreinte = empreinte_octets(chemin)
        session = client or httpx.Client(timeout=_DELAI)
        try:
            for tentative in range(1, essais + 1):
                try:
                    reponse = self._envoyer(cle, chemin, empreinte, session)
                except httpx.HTTPError as exc:
                    echec = DepotIndisponible(f"{type(exc).__name__} : {exc}")
                else:
                    if reponse.status_code < 300:
                        return cle
                    echec = DepotIndisponible(
                        f"HTTP {reponse.status_code} — {reponse.text[:300].strip()}"
                    )
                    if reponse.status_code not in _STATUTS_RETENTABLES:
                        raise echec
                if tentative < essais:
                    time.sleep(_PAUSE * tentative)
            raise echec
        finally:
            if client is None:
                session.close()


def configurer() -> Depot | None:
    """Dépôt décrit par l'environnement, ou None s'il n'est pas configuré.

    None N'EST PAS UNE ERREUR : en local, personne n'a de raison de porter les clés du
    stockage, et la collecte doit marcher sans elles. Les versions sont alors indexées
    `payload_archived: false`, et déposées au premier run qui en aura les moyens.
    """
    bucket = os.environ.get("ARCHIVE_BUCKET", "").strip()
    # Une clé dédiée à l'archive prime sur la clé générale du dépôt : c'est elle qu'on veut
    # restreinte au seul bucket d'archive. L'ordre compte — si les deux sont posées, c'est
    # la plus étroite qui sert.
    acces = (os.environ.get("ARCHIVE_ACCESS_KEY") or os.environ.get("SCW_ACCESS_KEY")
             or os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
    secret = (os.environ.get("ARCHIVE_SECRET_KEY") or os.environ.get("SCW_SECRET_KEY")
              or os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()
    if not bucket or not acces or not secret:
        return None
    if bucket == BUCKET_VITRINE:
        # Le déploiement de la vitrine fait `aws s3 sync outputs/ --delete` : il tient ce
        # bucket-là comme reflet exact d'outputs/. Y écrire l'archive, c'est la faire
        # effacer au run suivant — et une archive effacée ne se signale pas, elle manque.
        raise DepotMalConfigure(
            f"ARCHIVE_BUCKET={bucket!r} est le bucket de la vitrine, synchronisé avec "
            "--delete : l'archive y serait effacée au déploiement suivant. Utiliser un "
            "bucket dédié, privé, et jamais synchronisé."
        )
    return Depot(
        bucket=bucket,
        endpoint=os.environ.get("ARCHIVE_ENDPOINT", "").strip() or ENDPOINT_DEFAUT,
        region=os.environ.get("ARCHIVE_REGION", "").strip() or REGION_DEFAUT,
        cle_acces=acces,
        cle_secrete=secret,
    )
